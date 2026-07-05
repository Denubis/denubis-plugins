"""Tests for denubis-hook-claudemd-reminder/hooks/git-command-reminder.py."""

import json
import subprocess
import sys
from pathlib import Path

_HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-hook-claudemd-reminder"
    / "hooks"
    / "git-command-reminder.py"
)


def _run(input_data: dict) -> tuple[int, dict | None]:
    result = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps(input_data).encode(),
        capture_output=True,
        timeout=10,
    )
    stdout = result.stdout.decode().strip()
    parsed = json.loads(stdout) if stdout else None
    return result.returncode, parsed


def _bash_input(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ---------------------------------------------------------------------------
# Commands that SHOULD trigger the reminder
# ---------------------------------------------------------------------------
class TestMatchingCommands:
    def test_git_status(self):
        _, output = _run(_bash_input("git status"))
        assert output is not None
        assert "additionalContext" in output["hookSpecificOutput"]
        assert (
            "project-claude-librarian"
            in output["hookSpecificOutput"]["additionalContext"]
        )

    def test_git_log(self):
        _, output = _run(_bash_input("git log"))
        assert output is not None

    def test_git_log_verbose(self):
        _, output = _run(_bash_input("git log --stat"))
        assert output is not None


# ---------------------------------------------------------------------------
# Commands that should NOT trigger the reminder
# ---------------------------------------------------------------------------
class TestNonMatchingCommands:
    def test_git_log_oneline_short(self):
        """Quick one-liners like git log --oneline -3 should not trigger."""
        _, output = _run(_bash_input("git log --oneline -3"))
        assert output is None

    def test_git_commit(self):
        _, output = _run(_bash_input("git commit -m 'msg'"))
        assert output is None

    def test_git_diff(self):
        _, output = _run(_bash_input("git diff"))
        assert output is None

    def test_non_git_command(self):
        _, output = _run(_bash_input("ls -la"))
        assert output is None

    def test_non_bash_tool(self):
        _, output = _run({"tool_name": "Read", "tool_input": {}})
        assert output is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_bad_json_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input=b"not json",
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.decode().strip() == ""

    def test_empty_command(self):
        _, output = _run(_bash_input(""))
        assert output is None

    def test_output_is_valid_json(self):
        _, output = _run(_bash_input("git status"))
        assert output is not None
        assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
