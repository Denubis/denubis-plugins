"""Behavioral contracts for the concrete code-quality write guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = (
    REPO_ROOT
    / "plugins"
    / "denubis-hook-code-quality-guard"
    / "hooks"
    / "code-quality-guard.py"
)
BASH_WRAPPER_PATH = HOOK_PATH.with_name("pretooluse-bash.sh")
PLUGIN_ROOT = HOOK_PATH.parents[1]
CODEX_MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CODEX_HOOKS_PATH = PLUGIN_ROOT / "hooks" / "codex-hooks.json"
CODEX_MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"


def _run_hook(
    file_path: str,
    text: str,
    *,
    tool_name: str = "Edit",
) -> subprocess.CompletedProcess[str]:
    text_field = "content" if tool_name == "Write" else "new_string"
    hook_input = {
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path, text_field: text},
    }
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_codex_hook(patch: str) -> subprocess.CompletedProcess[str]:
    hook_input = {
        "tool_name": "apply_patch",
        "tool_input": {"command": patch},
    }
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_bash_hook(command: str) -> subprocess.CompletedProcess[str]:
    hook_input = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    return subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_explained_deny(
    result: subprocess.CompletedProcess[str],
    *,
    expects_system_message: bool = True,
    expected_returncode: int = 2,
) -> str:
    assert result.returncode == expected_returncode
    output = json.loads(result.stdout)
    hook_output = output["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "PreToolUse"
    assert hook_output["permissionDecision"] == "deny"
    reason = hook_output["permissionDecisionReason"]
    assert isinstance(reason, str) and reason
    if expects_system_message:
        assert output["systemMessage"] == reason
    else:
        assert "systemMessage" not in output
    return reason


@pytest.mark.parametrize(
    ("file_path", "injection"),
    [
        (
            "/project/tests/e2e/test_editor.py",
            'await page.evaluate("document.body.dataset.probe = 1")',
        ),
        (
            "/project/test/playwright/editor.ts",
            'ui.run_javascript("document.body.dataset.probe = 1")',
        ),
        (
            "/project/tests/integration/editor.js",
            'await page.add_script_tag({ content: "window.probe = 1" })',
        ),
        (
            "/project/tests/e2e/test_boot.py",
            'await page.add_init_script("window.probe = 1")',
        ),
    ],
)
@pytest.mark.parametrize("tool_name", ["Write", "Edit"])
def test_javascript_injection_in_user_surface_tests_is_explained_and_denied(
    file_path: str,
    injection: str,
    tool_name: str,
) -> None:
    result = _run_hook(
        file_path,
        injection,
        tool_name=tool_name,
    )

    reason = _assert_explained_deny(result)
    assert "JavaScript injection" in reason


def test_native_playwright_interaction_is_allowed() -> None:
    result = _run_hook(
        "/project/tests/e2e/test_editor.py",
        'await page.get_by_role("button", name="Save").click()',
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_production_browser_code_is_outside_the_test_methodology_policy() -> None:
    result = _run_hook(
        "/project/src/browser.ts",
        'await page.evaluate("document.title")',
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_similarly_named_browser_method_is_allowed() -> None:
    result = _run_hook(
        "/project/tests/e2e/test_editor.py",
        'await homepage.evaluate("document.title")',
    )

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize(
    "call",
    ["SQLModel.metadata.create_all(engine)", "metadata.create_all(engine)"],
)
def test_direct_schema_creation_outside_migrations_is_explained_and_denied(
    call: str,
) -> None:
    result = _run_hook("/project/src/database.py", call)

    reason = _assert_explained_deny(result)
    assert "create_all" in reason


def test_alembic_migration_is_outside_the_direct_schema_creation_policy() -> None:
    result = _run_hook(
        "/project/alembic/versions/20260816_create_tables.py",
        "metadata.create_all(engine)",
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_similarly_named_metadata_owner_is_allowed() -> None:
    result = _run_hook(
        "/project/src/database.py",
        "somemetadata.create_all(engine)",
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_unrelated_tool_and_malformed_input_are_side_effect_free() -> None:
    unrelated = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps({"tool_name": "Read", "tool_input": {}}),
        text=True,
        capture_output=True,
        check=False,
    )
    malformed = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )

    assert (unrelated.returncode, unrelated.stdout) == (0, "")
    assert (malformed.returncode, malformed.stdout) == (0, "")


@pytest.mark.parametrize(
    "command",
    [
        "cat >> evidence.txt <<'EOF'\nmodel-authored evidence\nEOF",
        "cat <<'EOF' > evidence.txt\nmodel-authored evidence\nEOF",
        "tee evidence.txt <<'EOF'\nmodel-authored evidence\nEOF",
        "tee -a evidence.txt <<'EOF'\nmodel-authored evidence\nEOF",
        "cat <<'EOF' | tee evidence.txt\nmodel-authored evidence\nEOF",
    ],
)
def test_bash_heredoc_file_write_is_explained_and_denied(command: str) -> None:
    result = _run_bash_hook(command)

    reason = _assert_explained_deny(result)
    assert "structured Write/Edit" in reason


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest -q > .test-results.txt",
        "cat existing-evidence.txt",
        "python3 - <<'PY'\nprint('probe')\nPY",
        "python3 - <<'PY' | tee\nprint('probe')\nPY",
        "python3 - <<'PY' | tee /dev/null\nprint('probe')\nPY",
    ],
)
def test_non_authoring_shell_io_is_allowed(command: str) -> None:
    result = _run_bash_hook(command)

    assert result.returncode == 0
    assert result.stdout == ""


def test_dispatcher_wrapper_routes_bash_payload_to_shared_guard() -> None:
    hook_input = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "cat <<'EOF' > evidence.txt\nmodel-authored evidence\nEOF"
        },
    }

    result = subprocess.run(
        [str(BASH_WRAPPER_PATH)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
        check=False,
    )

    reason = _assert_explained_deny(result)
    assert "structured Write/Edit" in reason


def test_codex_patch_denies_javascript_injection_in_user_surface_test() -> None:
    result = _run_codex_hook(
        """*** Begin Patch
*** Update File: tests/e2e/test_editor.py
@@
+await page.evaluate("document.body.dataset.probe = 1")
*** End Patch
"""
    )

    reason = _assert_explained_deny(
        result,
        expects_system_message=False,
        expected_returncode=0,
    )
    assert "JavaScript injection" in reason


def test_codex_patch_denies_schema_creation_in_any_added_file() -> None:
    result = _run_codex_hook(
        """*** Begin Patch
*** Update File: src/database.py
@@
+metadata.create_all(engine)
*** Update File: src/other.py
@@
+SAFE = True
*** End Patch
"""
    )

    reason = _assert_explained_deny(
        result,
        expects_system_message=False,
        expected_returncode=0,
    )
    assert "create_all" in reason


def test_codex_patch_ignores_context_and_removed_violations() -> None:
    result = _run_codex_hook(
        """*** Begin Patch
*** Update File: tests/e2e/test_editor.py
@@
-await page.evaluate("legacy")
 await page.evaluate("context only")
+await page.get_by_role("button", name="Save").click()
*** End Patch
"""
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_codex_patch_allows_schema_creation_inside_migration() -> None:
    result = _run_codex_hook(
        """*** Begin Patch
*** Add File: alembic/versions/20260817_create_tables.py
+metadata.create_all(engine)
*** End Patch
"""
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_codex_plugin_routes_apply_patch_to_shared_guard() -> None:
    manifest = json.loads(CODEX_MANIFEST_PATH.read_text(encoding="utf-8"))
    hooks = json.loads(CODEX_HOOKS_PATH.read_text(encoding="utf-8"))

    assert manifest["name"] == "denubis-hook-code-quality-guard"
    assert PLUGIN_ROOT / manifest["hooks"] == CODEX_HOOKS_PATH
    assert hooks == {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "apply_patch",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "".join(
                                (
                                    'python3 "${PLUGIN_ROOT}/hooks/',
                                    'code-quality-guard.py"',
                                )
                            ),
                            "timeout": 5,
                        }
                    ],
                }
            ]
        }
    }


def test_codex_marketplace_exposes_code_quality_guard() -> None:
    marketplace = json.loads(CODEX_MARKETPLACE_PATH.read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}

    assert entries["denubis-hook-code-quality-guard"]["source"] == {
        "source": "local",
        "path": "./plugins/denubis-hook-code-quality-guard",
    }
