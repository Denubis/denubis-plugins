"""Tests for denubis-plan-and-execute/hooks/code-quality-guard.py."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-plan-and-execute"
    / "hooks"
    / "code-quality-guard.py"
)
_spec = importlib.util.spec_from_file_location("code_quality_guard", _HOOK_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

check_e2e_js_injection = _mod.check_e2e_js_injection
check_create_all = _mod.check_create_all
check_migration_edit = _mod.check_migration_edit
check_debug_statements = _mod.check_debug_statements
check_easy_mode = _mod.check_easy_mode
check_spec_weakening = _mod.check_spec_weakening


# ---------------------------------------------------------------------------
# check_e2e_js_injection
# ---------------------------------------------------------------------------
class TestE2eJsInjection:
    def test_blocks_page_evaluate_in_e2e(self):
        result = check_e2e_js_injection(
            "tests/e2e/test_login.py",
            'await page.evaluate("document.querySelector(...)")',
        )
        assert result is not None
        assert "BLOCKED" in result

    def test_blocks_run_javascript_in_e2e(self):
        result = check_e2e_js_injection(
            "tests/e2e/test_login.py",
            'ui.run_javascript("alert(1)")',
        )
        assert result is not None

    def test_blocks_in_integration_dir(self):
        result = check_e2e_js_injection(
            "tests/integration/test_flow.ts",
            "page.evaluate(() => {})",
        )
        assert result is not None

    def test_blocks_in_playwright_dir(self):
        result = check_e2e_js_injection(
            "test/playwright/test_ui.js",
            "page.add_script_tag()",
        )
        assert result is not None

    def test_allows_page_evaluate_outside_e2e(self):
        result = check_e2e_js_injection(
            "src/utils/helpers.py",
            'page.evaluate("something")',
        )
        assert result is None

    def test_allows_e2e_without_js_injection(self):
        result = check_e2e_js_injection(
            "tests/e2e/test_login.py",
            "await page.click('button')",
        )
        assert result is None


# ---------------------------------------------------------------------------
# check_create_all
# ---------------------------------------------------------------------------
class TestCreateAll:
    def test_blocks_create_all_in_app_code(self):
        result = check_create_all(
            "src/db/setup.py",
            "SQLModel.metadata.create_all(engine)",
        )
        assert result is not None
        assert "BLOCKED" in result

    def test_blocks_bare_metadata_create_all(self):
        result = check_create_all(
            "src/main.py",
            "metadata.create_all(bind=engine)",
        )
        assert result is not None

    def test_allows_in_alembic_migration(self):
        result = check_create_all(
            "alembic/versions/abc123_init.py",
            "metadata.create_all(engine)",
        )
        assert result is None

    def test_allows_without_create_all(self):
        result = check_create_all(
            "src/db/setup.py",
            "session.execute(query)",
        )
        assert result is None


# ---------------------------------------------------------------------------
# check_migration_edit
# ---------------------------------------------------------------------------
class TestMigrationEdit:
    def test_warns_on_alembic_version_edit(self):
        result = check_migration_edit(
            "alembic/versions/abc123_init.py",
            "def upgrade(): pass",
        )
        assert result is not None
        assert "WARNING" in result

    def test_no_warn_on_non_migration(self):
        result = check_migration_edit(
            "src/models.py",
            "class User: pass",
        )
        assert result is None

    def test_no_warn_on_alembic_env(self):
        result = check_migration_edit(
            "alembic/env.py",
            "target_metadata = Base.metadata",
        )
        assert result is None


# ---------------------------------------------------------------------------
# check_debug_statements
# ---------------------------------------------------------------------------
class TestDebugStatements:
    def test_warns_on_breakpoint(self):
        result = check_debug_statements("src/app.py", "breakpoint()")
        assert result is not None
        assert "breakpoint()" in result

    def test_warns_on_pdb(self):
        result = check_debug_statements("src/app.py", "import pdb\npdb.set_trace()")
        assert result is not None

    def test_print_only_warns_with_logging(self):
        code = "import logging\nlogger = logging.getLogger()\nprint('debug')"
        result = check_debug_statements("src/app.py", code)
        assert result is not None
        assert "print()" in result

    def test_print_allowed_without_logging(self):
        result = check_debug_statements("src/app.py", "print('hello')")
        assert result is None

    def test_allowed_in_test_files(self):
        result = check_debug_statements("tests/test_app.py", "breakpoint()")
        assert result is None

    def test_allowed_in_scripts(self):
        result = check_debug_statements("scripts/migrate.py", "breakpoint()")
        assert result is None

    def test_non_python_ignored(self):
        result = check_debug_statements("src/app.ts", "breakpoint()")
        assert result is None


# ---------------------------------------------------------------------------
# check_easy_mode
# ---------------------------------------------------------------------------
class TestEasyMode:
    def test_warns_on_todo_deferral(self):
        result = check_easy_mode("src/app.py", "# TODO: for now, skip validation")
        assert result is not None

    def test_warns_on_not_implemented_error(self):
        result = check_easy_mode("src/app.py", "raise NotImplementedError")
        assert result is not None

    def test_warns_on_pass_with_comment(self):
        result = check_easy_mode("src/app.py", "pass  # placeholder")
        assert result is not None

    def test_warns_on_simplification_comment(self):
        result = check_easy_mode("src/app.py", "# simplified version")
        assert result is not None

    def test_allows_clean_code(self):
        result = check_easy_mode("src/app.py", "def process(): return data")
        assert result is None

    def test_allows_pyi_stubs(self):
        result = check_easy_mode("src/app.pyi", "raise NotImplementedError")
        assert result is None

    def test_non_python_ignored(self):
        result = check_easy_mode("src/app.ts", "raise NotImplementedError")
        assert result is None


# ---------------------------------------------------------------------------
# check_spec_weakening
# ---------------------------------------------------------------------------
class TestSpecWeakening:
    def test_warns_on_skip_marker(self):
        result = check_spec_weakening("tests/test_app.py", "@pytest.mark.skip")
        assert result is not None
        assert "pytest.mark.skip" in result

    def test_warns_on_xfail_marker(self):
        result = check_spec_weakening("tests/test_app.py", "@pytest.mark.xfail")
        assert result is not None

    def test_warns_on_todo_skip_comment(self):
        result = check_spec_weakening("tests/test_app.py", "# TODO: skip for now")
        assert result is not None

    def test_allows_clean_tests(self):
        result = check_spec_weakening("tests/test_app.py", "def test_foo(): assert True")
        assert result is None

    def test_non_test_file_ignored(self):
        result = check_spec_weakening("src/app.py", "@pytest.mark.skip")
        assert result is None


# ---------------------------------------------------------------------------
# Integration: main() via subprocess
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def _run(self, input_data: dict) -> tuple[int, dict | None, str]:
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=json.dumps(input_data).encode(),
            capture_output=True,
            timeout=10,
        )
        stdout = result.stdout.decode().strip()
        parsed = json.loads(stdout) if stdout else None
        return result.returncode, parsed, stdout

    def test_write_tool_with_violation_denies(self):
        rc, output, _ = self._run({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "tests/e2e/test_login.py",
                "content": 'page.evaluate("document.title")',
            },
        })
        assert rc == 2
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_edit_tool_with_violation_denies(self):
        rc, output, _ = self._run({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "src/db.py",
                "new_string": "metadata.create_all(engine)",
            },
        })
        assert rc == 2
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_warning_returns_additional_context(self):
        rc, output, _ = self._run({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "src/app.py",
                "content": "breakpoint()",
            },
        })
        assert rc == 0
        assert output is not None
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_multiple_warnings_combined(self):
        code = "breakpoint()\nraise NotImplementedError\n# TODO: for now"
        rc, output, _ = self._run({
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py", "content": code},
        })
        assert rc == 0
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "---" in ctx  # separator between combined warnings

    def test_clean_code_passes_silently(self):
        rc, output, _ = self._run({
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py", "content": "def foo(): return 42"},
        })
        assert rc == 0
        assert output is None

    def test_non_write_edit_tool_passes(self):
        rc, output, _ = self._run({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        assert rc == 0
        assert output is None

    def test_blocking_check_takes_priority(self):
        """If both blocking and warning checks trigger, blocking wins."""
        code = 'page.evaluate("x")\nbreakpoint()'
        rc, output, _ = self._run({
            "tool_name": "Write",
            "tool_input": {"file_path": "tests/e2e/test_app.py", "content": code},
        })
        assert rc == 2
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_bad_json_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=b"not json",
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0
