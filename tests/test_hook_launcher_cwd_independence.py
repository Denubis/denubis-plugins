"""Repo-wide fitness function: uv-launched hooks must ignore the caller's cwd.

Incident (2026-07-13, reproduced live): plugin hooks are launched from
`hooks.json` as `uv run python "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"`. `uv`
performs configuration ("settings") discovery by walking up from the *calling*
process's cwd, so when that directory holds an unparseable `pyproject.toml` —
e.g. a file carrying git conflict markers mid-merge — `uv` fails before it ever
launches the interpreter:

    warning: Failed to parse `pyproject.toml` during settings discovery: ...
    error: Failed to parse: `pyproject.toml`

Exit code 2, the hook never runs. Because the PreToolUse dispatcher is one of
the wedged hooks, the very tool calls that would fix the conflict are blocked: a
deadlock. The remedy is to make each `uv run` launcher independent of the
caller's project *and* configuration state with `--no-project --no-config`,
which was verified to run the hook cleanly (exit 0, no warning) from exactly
such a directory. All five affected hooks are stdlib-only, so neither flag costs
them anything.

This test lifts that remedy from reviewer-eye to an automated guard (Ford et
al., Building Evolutionary Architectures), as the sibling `test_hook_portability`
does for the 3.14-syntax class. Two teeth:

  * a static check that every `uv run` launcher in `plugins/*/hooks/hooks.json`
    carries both flags (runs without uv, so it guards even where uv is absent);
  * a behavioural check that each launcher, invoked from a conflict-marked cwd,
    does not die in settings discovery — paired with a teeth test proving a bare
    `uv run` genuinely wedges on the same directory, so the guard cannot pass
    trivially against a fixture that is not actually malformed.

The behavioural assertion is deliberately narrow: it asserts only that uv's
settings-discovery failure is absent from stderr, the one property the launcher
flags change. Each hook's own logic is covered by that plugin's tests and by
`test_hook_portability`; conflating the two here would couple this guard to hook
behaviour it does not own.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

# tests/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PLUGINS_DIR = _REPO_ROOT / "plugins"

# uv's configuration-discovery failure signature. Present when uv chokes on the
# caller's malformed pyproject; absent once `--no-config` takes it out of the
# discovery path. This exact phrase is uv's, not any hook's.
_WEDGE_SIGNATURE = "during settings discovery"

# A pyproject.toml a merge left mid-conflict: unmergeable markers plus the
# missing-comma array that first surfaced the incident. TOML-invalid either way.
_CONFLICTED_PYPROJECT = """\
[project]
name = "victim"
version = "0.1.0"
dependencies = [
    "foo"
    "bar"
]
<<<<<<< HEAD
description = "ours"
=======
description = "theirs"
>>>>>>> other
"""

# First run may provision an interpreter via uv; later runs hit the cache.
_TIMEOUT_S = 180


def _uv() -> str | None:
    return shutil.which("uv")


def _require_uv() -> None:
    if _uv() is None:
        pytest.skip("uv unavailable; behavioural launcher checks need it")


def _iter_commands(node: object) -> list[str]:
    """Every ``command`` string anywhere in a parsed hooks.json structure."""
    found: list[str] = []
    if isinstance(node, dict):
        command = node.get("command")
        if isinstance(command, str):
            found.append(command)
        for value in node.values():
            found.extend(_iter_commands(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_commands(item))
    return found


def _uv_run_launchers() -> list[tuple[str, Path]]:
    """(command, plugin_root) for every ``uv run`` launcher in main-tree hooks.

    plugin_root is the hooks.json's plugin directory, i.e. the value the hook
    receives as CLAUDE_PLUGIN_ROOT at runtime.
    """
    launchers: list[tuple[str, Path]] = []
    for hooks_json in sorted(_PLUGINS_DIR.glob("*/hooks/hooks.json")):
        try:
            data = json.loads(hooks_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        plugin_root = hooks_json.parent.parent
        for command in _iter_commands(data):
            if "uv run" in command:
                launchers.append((command, plugin_root))
    return launchers


def _launcher_id(entry: tuple[str, Path]) -> str:
    """Readable id: '<plugin>/<script>'."""
    command, plugin_root = entry
    tail = command.rsplit("/", 1)[-1].rstrip('"').removesuffix(".py")
    return f"{plugin_root.name}/{tail}"


_LAUNCHERS = _uv_run_launchers()


def _run_from(cwd: Path, command: str, plugin_root: Path) -> subprocess.CompletedProcess[str]:
    """Run a launcher command from ``cwd`` with a neutralised hook environment.

    ``${CLAUDE_PLUGIN_ROOT}`` is expanded by the shell from the env. The
    DISPATCHER_* overrides point the PreToolUse dispatcher at empty temp paths so
    it discovers and dispatches nothing (no reach into the real ~/.claude).
    """
    empty = cwd / "_empty"
    empty.mkdir(exist_ok=True)
    env = {
        "PATH": _os_path(),
        "HOME": str(cwd),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "DISPATCHER_DROP_DIR": str(empty),
        "DISPATCHER_MARKETPLACE_DIR": str(empty),
        "DISPATCHER_SETTINGS_FILE": str(cwd / "settings.json"),
        "DISPATCHER_CACHE_FILE": str(cwd / "cache"),
    }
    return subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        env=env,
        input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"}),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        check=False,
    )


def _os_path() -> str:
    import os

    return os.environ.get("PATH", "")


def test_at_least_one_uv_launcher_discovered() -> None:
    """Sanity: the glob finds uv launchers. Catches a silent layout regression."""
    assert _LAUNCHERS, f"no `uv run` launchers found under {_PLUGINS_DIR}/*/hooks/hooks.json"


@pytest.mark.parametrize("entry", _LAUNCHERS, ids=_launcher_id)
def test_launcher_carries_wedge_flags(entry: tuple[str, Path]) -> None:
    """Every uv launcher must be independent of the caller's project + config.

    Static, uv-free guard: a launcher missing either flag will wedge when the
    caller's cwd holds a malformed pyproject.
    """
    command, _ = entry
    missing = [flag for flag in ("--no-project", "--no-config") if flag not in command]
    assert not missing, (
        f"launcher is missing {missing}; a `uv run` hook must carry "
        f"`--no-project --no-config` so a malformed pyproject.toml in the "
        f"caller's cwd cannot wedge it:\n  {command}"
    )


def test_bare_uv_run_wedges_on_conflicted_pyproject(tmp_path: Path) -> None:
    """Teeth: a bare `uv run` genuinely dies in settings discovery here.

    Without this, the behavioural guard below could pass against a fixture that
    is not actually malformed, giving false confidence.
    """
    _require_uv()
    (tmp_path / "pyproject.toml").write_text(_CONFLICTED_PYPROJECT, encoding="utf-8")
    proc = subprocess.run(
        ["uv", "run", "python", "-c", "print('ran')"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        check=False,
    )
    assert proc.returncode != 0 and _WEDGE_SIGNATURE in proc.stderr, (
        "bare `uv run` was expected to wedge on the conflicted pyproject, so the "
        "behavioural guard has teeth. It did not:\n"
        f"exit={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


@pytest.mark.parametrize("entry", _LAUNCHERS, ids=_launcher_id)
def test_launcher_survives_conflicted_pyproject(entry: tuple[str, Path], tmp_path: Path) -> None:
    """Each launcher runs from a conflict-marked cwd without dying in discovery."""
    _require_uv()
    (tmp_path / "pyproject.toml").write_text(_CONFLICTED_PYPROJECT, encoding="utf-8")
    command, plugin_root = entry
    proc = _run_from(tmp_path, command, plugin_root)
    assert _WEDGE_SIGNATURE not in proc.stderr, (
        f"{_launcher_id(entry)} died in uv settings discovery when launched from a "
        f"directory with a malformed pyproject.toml. Add `--no-project --no-config` "
        f"to the launcher.\nstderr:\n{proc.stderr}"
    )
