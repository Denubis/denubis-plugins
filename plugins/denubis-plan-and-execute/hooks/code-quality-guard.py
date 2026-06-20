#!/usr/bin/env python3
"""PreToolUse hook: code quality guards.

Checks file writes/edits against project-specific rules and denies
or warns when violations are detected.

Input (stdin JSON):
  tool_name: "Write" | "Edit"
  tool_input.file_path: absolute path to file
  tool_input.content: (Write) full file content
  tool_input.new_string: (Edit) replacement text

Output (stdout JSON):
  For deny:  {"hookSpecificOutput": {"permissionDecision": "deny"},
              "systemMessage": "..."}
  For warn:  {"hookSpecificOutput": {"additionalContext": "..."}}
  For pass:  (empty stdout, exit 0)

Exit codes:
  0 = allow (with optional warning)
  2 = deny (block the tool call)
"""

import json
import re
import sys


def get_new_text(input_data: dict) -> str:
    """Extract the text being written from Write or Edit tool input."""
    tool_input = input_data.get("tool_input", {})
    return tool_input.get("content", "") or tool_input.get("new_string", "")


def get_file_path(input_data: dict) -> str:
    return input_data.get("tool_input", {}).get("file_path", "")


# ---------------------------------------------------------------------------
# Blocking checks (exit 2, permissionDecision: deny)
# ---------------------------------------------------------------------------


def check_e2e_js_injection(file_path: str, new_text: str) -> str | None:
    """Block JavaScript injection in E2E/integration tests.

    E2E tests must simulate real user behavior through Playwright's native
    APIs, not bypass the UI with JavaScript injection.
    """
    if not re.search(r"tests?/(e2e|playwright|integration)/.*\.(py|ts|js)$", file_path):
        return None

    patterns = [
        r"page\.evaluate\(",
        r"ui\.run_javascript\(",
        r"page\.add_script_tag\(",
        r"page\.add_init_script\(",
    ]
    if not any(re.search(p, new_text) for p in patterns):
        return None

    return """BLOCKED: JavaScript injection in E2E test.

E2E tests must use Playwright's native APIs to simulate real user behavior:
- Text selection: page.mouse (move, down, move, up) to drag-select
- Keyboard input: page.keyboard.press() or locator.press()
- Clicks: locator.click() with modifiers
- Assertions: expect() from playwright.sync_api
- Scroll: locator.scroll_into_view_if_needed()
- DOM queries: locator.get_by_role(), locator.get_by_text()

page.evaluate() and run_javascript() bypass the browser event pipeline,
making tests pass for the wrong reasons."""


def check_create_all(file_path: str, new_text: str) -> str | None:
    """Block SQLModel.metadata.create_all() outside Alembic migrations.

    Schema changes MUST go through Alembic migrations for tracking,
    reproducibility, and safe rollback.
    """
    if "alembic/versions/" in file_path:
        return None

    if not re.search(r"(SQLModel\.)?metadata\.create_all\(", new_text):
        return None

    return """BLOCKED: metadata.create_all() outside Alembic migrations.

Alembic is the ONLY way to create or modify database schema. create_all()
bypasses migration history and causes schema drift.

Correct approach:
1. Create migration: alembic revision --autogenerate -m "description"
2. Review the generated migration file
3. Apply: alembic upgrade head
4. Verify: alembic downgrade -1 then upgrade head"""


# ---------------------------------------------------------------------------
# Warning checks (additionalContext, exit 0)
# ---------------------------------------------------------------------------


def check_migration_edit(file_path: str, _new_text: str) -> str | None:
    """Warn when editing Alembic migration files.

    Applied migrations are immutable history. Editing them after they've
    been applied to any environment causes schema divergence.
    """
    if not re.search(r"alembic/versions/.*\.py$", file_path):
        return None

    return """WARNING: You are editing an Alembic migration file.

Before proceeding, verify:
- This migration has NOT been applied to production or shared environments
- If already applied anywhere, create a NEW migration instead of editing
- The upgrade() and downgrade() functions are exact inverses of each other

Never edit applied migrations. Create new corrective migrations instead."""


def check_debug_statements(file_path: str, new_text: str) -> str | None:
    """Warn on debug statements in production (non-test) Python code.

    print(), breakpoint(), and pdb calls in production code risk leaking
    sensitive data, degrading performance, and breaking structured logging.
    """
    if not file_path.endswith(".py"):
        return None

    # Allow in test files and scripts
    if re.search(r"(tests?/|scripts?/|cli/)", file_path):
        return None

    patterns = [
        (r"\bbreakpoint\(\)", "breakpoint()"),
        (r"\bpdb\.set_trace\(\)", "pdb.set_trace()"),
        (r"\bimport\s+pdb\b", "import pdb"),
    ]

    # print() only flagged when a logging import exists nearby,
    # suggesting structured logging is the project convention
    if re.search(r"\bimport\s+logging\b|\bfrom\s+logging\b|\blogger\s*=", new_text):
        patterns.append((r"\bprint\(", "print() (use logger instead)"))

    found = [name for pat, name in patterns if re.search(pat, new_text)]
    if not found:
        return None

    return f"""WARNING: Debug statement detected in production code: {", ".join(found)}

- Convert to proper logging (logger.debug/info/warning) if output is needed
- Remove if this is temporary debugging
- Debug statements in production code can expose sensitive data and
  break structured logging pipelines"""


def check_easy_mode(file_path: str, new_text: str) -> str | None:
    """Warn on placeholder/shortcut patterns that defer real implementation.

    These patterns signal that complexity was encountered and the response
    was to simplify or defer rather than implement properly.
    """
    if not file_path.endswith(".py"):
        return None

    # Allow in type stubs
    if file_path.endswith(".pyi"):
        return None

    patterns = [
        (
            r"#\s*(TODO|FIXME|HACK|XXX):?\s*"
            r"(for now|later|simplif|temporary|workaround)",
            "TODO/FIXME deferral",
        ),
        (r"#\s*simplified|#\s*easy", "simplification comment"),
        (r"pass\s*#", "pass with comment (stub)"),
        (r"\braise\s+NotImplementedError\b", "NotImplementedError stub"),
        (r"#\s*(skip|ignore|remove)\s*(this|for now|later)", "skip/ignore comment"),
    ]

    found = [name for pat, name in patterns if re.search(pat, new_text)]
    if not found:
        return None

    return f"""WARNING: Shortcut/deferral pattern detected: {", ".join(found)}

You may be simplifying or deferring instead of implementing properly.

Before proceeding, pause and answer honestly:
1. Is this simplification what the user actually requested?
2. Did you hit complexity and choose "easy" over "correct"?
3. Should you implement the full solution instead?

When facing a hard problem, don't silently simplify. Ask the user:
"This is complex - would you prefer I implement it fully or use a
simpler approach for now?" """


def check_spec_weakening(file_path: str, new_text: str) -> str | None:
    """Warn on patterns that weaken tests to make them pass.

    The TDD contract is: fix the CODE to pass the test, not the TEST to
    pass the code.
    """
    if not re.search(r"tests?/.*\.py$", file_path):
        return None

    patterns = [
        (r"pytest\.mark\.skip\b", "pytest.mark.skip"),
        (r"@pytest\.mark\.xfail\b", "pytest.mark.xfail"),
        (r"# TODO:?\s*(fix|skip|ignore)", "TODO skip/ignore comment"),
    ]

    found = [name for pat, name in patterns if re.search(pat, new_text)]
    if not found:
        return None

    return f"""WARNING: Potential test weakening detected: {", ".join(found)}

You may be making a test pass by lowering expectations instead of fixing
the underlying code.

Red flags:
- Adding skip/xfail markers to avoid failing tests
- Inverting assertions (== to !=, assertTrue to assertFalse)
- Adding TODO comments about "fixing later"

TDD principle: Fix the code to pass the test, not the test to pass the
code. If the test expectation is genuinely wrong, explain why before
changing it."""


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------

BLOCKING_CHECKS = [
    check_e2e_js_injection,
    check_create_all,
]

WARNING_CHECKS = [
    check_migration_edit,
    check_debug_statements,
    check_easy_mode,
    check_spec_weakening,
]


def main() -> int:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError, EOFError:
        return 0

    file_path = get_file_path(input_data)
    new_text = get_new_text(input_data)

    if not file_path or not new_text:
        return 0

    # Check blocking rules first
    for check in BLOCKING_CHECKS:
        result = check(file_path, new_text)
        if result:
            output = {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                },
                "systemMessage": result,
            }
            print(json.dumps(output))
            return 2

    # Then check warning rules (collect all)
    warnings = []
    for check in WARNING_CHECKS:
        result = check(file_path, new_text)
        if result:
            warnings.append(result)

    if warnings:
        combined = "\n\n---\n\n".join(warnings)
        output = {
            "hookSpecificOutput": {
                "additionalContext": combined,
            }
        }
        print(json.dumps(output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
