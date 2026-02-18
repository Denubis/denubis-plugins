"""Shared fixtures for hook testing."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"


@pytest.fixture
def run_hook():
    """Run a hook script as a subprocess, feeding JSON on stdin.

    Returns a helper that takes (script_path, input_dict) and returns
    (returncode, parsed_stdout_or_None, raw_stdout).
    """

    def _run(script_path: Path, input_data: dict | None = None) -> tuple[int, dict | None, str]:
        stdin_bytes = json.dumps(input_data).encode() if input_data else b""
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=stdin_bytes,
            capture_output=True,
            text=False,
            timeout=10,
        )
        stdout = result.stdout.decode()
        try:
            parsed = json.loads(stdout) if stdout.strip() else None
        except json.JSONDecodeError:
            parsed = None
        return result.returncode, parsed, stdout

    return _run


@pytest.fixture
def bash_input():
    """Build a standard Bash PreToolUse/PostToolUse hook input dict."""

    def _build(command: str) -> dict:
        return {
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }

    return _build


@pytest.fixture
def write_input():
    """Build a standard Write PreToolUse hook input dict."""

    def _build(file_path: str, content: str) -> dict:
        return {
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": content},
        }

    return _build


@pytest.fixture
def edit_input():
    """Build a standard Edit PreToolUse hook input dict."""

    def _build(file_path: str, new_string: str) -> dict:
        return {
            "tool_name": "Edit",
            "tool_input": {"file_path": file_path, "new_string": new_string},
        }

    return _build
