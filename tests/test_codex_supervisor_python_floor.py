"""The supervisor script must load on the oldest Python its hook relay may run under.

`--hook` makes `codex_supervisor.py` a Codex hook entry point, run through whatever
Python `uv run --no-project` resolves on the consuming machine, with no project
environment to pin the version. The script's floor is therefore a contract of its own,
separate from the project's `requires-python`. The floor is 3.12: `StrEnum` needs 3.11,
and the nested-quote f-strings the file uses need 3.12.

`ast.parse(feature_version=...)` cannot stand in for the floor interpreter: on 3.14 it
accepts a nested-quote f-string under `feature_version=(3, 11)`, so it would have
missed the break that made this file stop parsing on 3.11. Only the real interpreter
can say, so the check runs under one, found through `uv` without downloading anything,
and skips with the reason stated when the machine has none.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "plugins" / "denubis-external-agents" / "scripts" / "codex_supervisor.py"
)
FLOOR = "3.12"

# Syntax that only a newer Python accepts: the parenthesis-free multi-exception clause
# that `ruff format` produces under the project's 3.14 target. The floor interpreter
# must reject it, or it is not proving anything about the script.
NEWER_THAN_FLOOR = "try:\n    pass\nexcept KeyError, TypeError:\n    pass\n"


def _floor_interpreter() -> str:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not on PATH, so no floor interpreter can be located")
    found = subprocess.run(
        [uv, "python", "find", "--no-config", FLOOR],
        capture_output=True,
        text=True,
        check=False,
    )
    if found.returncode != 0 or not found.stdout.strip():
        pytest.skip(f"no Python {FLOOR} interpreter is installed for uv to find")
    return found.stdout.strip()


def _parse_under(
    interpreter: str, source_path: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [interpreter, "-c", "import ast, sys; ast.parse(sys.stdin.read())"],
        input=source_path.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_floor_interpreter_rejects_newer_syntax(tmp_path: Path) -> None:
    """Control: the detector fires on syntax the floor does not have."""
    interpreter = _floor_interpreter()
    newer = tmp_path / "newer.py"
    newer.write_text(NEWER_THAN_FLOOR, encoding="utf-8")
    result = _parse_under(interpreter, newer)
    assert result.returncode != 0
    assert "SyntaxError" in result.stderr


def test_the_script_parses_on_the_floor_python() -> None:
    interpreter = _floor_interpreter()
    result = _parse_under(interpreter, SCRIPT)
    assert result.returncode == 0, result.stderr


def test_the_script_imports_on_the_floor_python() -> None:
    """Parsing is not enough: a stdlib name missing at the floor fails at import."""
    interpreter = _floor_interpreter()
    result = subprocess.run(
        [
            interpreter,
            "-c",
            # The documented recipe for loading a module from a path: it must be in
            # `sys.modules` before it executes, or `dataclasses` on 3.12 and 3.13
            # cannot resolve the file's deferred annotations and fails on a module
            # that imports cleanly when run as a script.
            "import importlib.util, sys\n"
            "spec = importlib.util.spec_from_file_location("
            f"'codex_supervisor', {str(SCRIPT)!r})\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "sys.modules[spec.name] = module\n"
            "spec.loader.exec_module(module)\n"
            "print(sys.version_info[:2])\n",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(tuple(int(part) for part in FLOOR.split(".")))


def test_this_suite_runs_above_the_floor() -> None:
    """The project itself targets 3.14; the floor is a separate, lower contract."""
    assert sys.version_info[:2] >= tuple(int(part) for part in FLOOR.split("."))
