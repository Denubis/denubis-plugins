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

  * a static check that every `uv run` launcher declared by a Claude plugin manifest
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

Since 2026-10-27 (ADR 0046) the launchers drop `--no-config`, which also skipped
the user's `~/.config/uv/uv.toml`, and pass `--project` with the plugin root
instead. uv then discovers `pyproject.toml` and `uv.toml` by walking up from the
plugin directory, never from the caller's cwd, while the hook keeps the caller's
cwd. Claude and Codex launchers are both checked, and a malformed `uv.toml` in the
caller's cwd is now a second wedge case.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

# tests/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PLUGINS_DIR = _REPO_ROOT / "plugins"
_FLOOR = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["requires-python"]

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

# A uv.toml a merge left mid-conflict. uv names a uv.toml found in its cwd by the
# bare file name, and one found elsewhere by its full path.
_MALFORMED_UV_TOML = """\
<<<<<<< HEAD
link-mode = "copy"
=======
link-mode = "hardlink"
>>>>>>> other
"""
_CWD_UV_TOML_WEDGE = re.compile(r"Failed to parse: `?uv\.toml")
# `--project` with the plugin root as Claude or Codex names it.
_ANCHOR = re.compile(r'--project "\$\{(?:CLAUDE_)?PLUGIN_ROOT\}"')

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
    """(command, plugin_root) for every Claude and Codex ``uv run`` launcher.

    plugin_root is the manifest's plugin directory, i.e. the value the hook
    receives as CLAUDE_PLUGIN_ROOT (Claude) or PLUGIN_ROOT (Codex) at runtime.
    A Codex manifest names its hooks file explicitly; it has no default.
    """
    launchers: list[tuple[str, Path]] = []
    for plugin_root in sorted(path for path in _PLUGINS_DIR.iterdir() if path.is_dir()):
        for manifest_dir, default in (
            (".claude-plugin", "hooks/hooks.json"),
            (".codex-plugin", None),
        ):
            manifest_path = plugin_root / manifest_dir / "plugin.json"
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except OSError, json.JSONDecodeError:
                continue
            hooks_name = manifest.get("hooks", default)
            if hooks_name is None:
                continue
            try:
                data = json.loads(
                    (plugin_root / hooks_name).read_text(encoding="utf-8")
                )
            except OSError, json.JSONDecodeError:
                continue
            for command in _iter_commands(data):
                if "uv run" in command:
                    launchers.append((command, plugin_root))
    return launchers


def _launcher_id(entry: tuple[str, Path]) -> str:
    """Readable id: '<plugin>/<script>', with a Codex suffix for Codex launchers."""
    command, plugin_root = entry
    script = re.search(r"/hooks/([a-z-]+)\.py", command)
    provider = "" if "CLAUDE_PLUGIN_ROOT" in command else "[codex]"
    return f"{plugin_root.name}/{script[1] if script else command}{provider}"


_LAUNCHERS = _uv_run_launchers()


def _run_from(cwd: Path, command: str, plugin_root: Path) -> subprocess.CompletedProcess[str]:
    """Run a launcher command from ``cwd`` with a neutralised hook environment.

    ``${CLAUDE_PLUGIN_ROOT}`` and the Codex ``${PLUGIN_ROOT}`` are expanded by
    the shell from the env. The DISPATCHER_* overrides point the PreToolUse
    dispatcher at empty temp paths so it discovers and dispatches nothing (no reach
    into the real ~/.claude).
    """
    empty = cwd / "_empty"
    empty.mkdir(exist_ok=True)
    env = {
        "PATH": _os_path(),
        "HOME": str(cwd),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "PLUGIN_ROOT": str(plugin_root),
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
    """Sanity: manifest discovery finds uv launchers."""
    assert _LAUNCHERS, f"no Claude `uv run` hook launchers found under {_PLUGINS_DIR}"


@pytest.mark.parametrize("entry", _LAUNCHERS, ids=_launcher_id)
def test_launcher_carries_wedge_flags(entry: tuple[str, Path]) -> None:
    """Every uv launcher must be independent of the caller's project + config.

    Static, uv-free guard: each uv invocation must pass `--project` with the plugin
    root, so configuration discovery starts there rather than in the caller's cwd,
    and `uv run` must pass `--no-project`. `--no-config` is absent so the user's
    uv.toml applies.
    """
    command, _ = entry
    invocations = re.findall(r"\buv (?:run|sync) [^;]*", command)
    assert invocations, f"no uv run or uv sync invocation found:\n  {command}"
    unanchored = [
        invocation for invocation in invocations if not _ANCHOR.search(invocation)
    ]
    assert not unanchored, (
        f"uv invocations without `--project` at the plugin root read the caller's "
        f"cwd for configuration:\n  {unanchored}"
    )
    assert "--no-project" in command, f"launcher lacks --no-project:\n  {command}"
    assert "--no-config" not in command, (
        f"launcher passes --no-config, which skips the user's uv.toml:\n  {command}"
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
def test_launcher_runs_hook_in_callers_cwd(
    entry: tuple[str, Path], tmp_path: Path
) -> None:
    """The hook process starts in the caller's cwd, not the plugin directory.

    branch-bg reads `Path.cwd()`, gh-fork-guard runs `git remote` without a `cwd`,
    and the dispatcher's child hooks inherit its cwd, so anchoring configuration
    discovery must not move the process. A fixture stands in for the hook in a
    temporary plugin copy and records `os.getcwd()`.
    """
    _require_uv()
    command, plugin_root = entry
    script = re.search(r"/hooks/([a-z-]+)\.py", command)
    assert script is not None, command
    copy = tmp_path / plugin_root.name
    (copy / "hooks").mkdir(parents=True)
    (copy / "hooks" / f"{script[1]}.py").write_text(
        "# /// script\n"
        f'# requires-python = "{_FLOOR}"\n'
        "# dependencies = []\n"
        "# ///\n"
        "import os, pathlib\n"
        "pathlib.Path(os.environ['HOOK_FIXTURE_CWD']).write_text(os.getcwd())\n",
        encoding="utf-8",
    )
    caller = tmp_path / "caller"
    caller.mkdir()
    (caller / "pyproject.toml").write_text(_CONFLICTED_PYPROJECT, encoding="utf-8")
    (caller / "uv.toml").write_text(_MALFORMED_UV_TOML, encoding="utf-8")
    record = tmp_path / "cwd.txt"
    proc = subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=caller,
        env={
            **os.environ,
            "CLAUDE_PLUGIN_ROOT": str(copy),
            "PLUGIN_ROOT": str(copy),
            "HOOK_FIXTURE_CWD": str(record),
        },
        input="{}",
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        check=False,
    )
    assert proc.returncode == 0, proc
    assert record.read_text(encoding="utf-8") == str(caller)


def test_bare_uv_run_wedges_on_malformed_uv_toml(tmp_path: Path) -> None:
    """Teeth: a bare `uv run` dies parsing a malformed `uv.toml` in its cwd."""
    _require_uv()
    (tmp_path / "uv.toml").write_text(_MALFORMED_UV_TOML, encoding="utf-8")
    proc = subprocess.run(
        ["uv", "run", "python", "-c", "print('ran')"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        check=False,
    )
    assert proc.returncode != 0 and _CWD_UV_TOML_WEDGE.search(proc.stderr), (
        "bare `uv run` was expected to fail parsing the cwd's uv.toml, so the "
        "behavioural guard has teeth. It did not:\n"
        f"exit={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


@pytest.mark.parametrize("entry", _LAUNCHERS, ids=_launcher_id)
def test_launcher_survives_malformed_uv_toml(
    entry: tuple[str, Path], tmp_path: Path
) -> None:
    """Each launcher runs from a cwd holding a malformed uv.toml without reading it.

    With configuration discovery on, the launcher must anchor discovery at the
    plugin directory. uv 0.13.5 already starts script-mode discovery at the
    script's directory, so on that version this passes without the anchor; uv
    0.11.0 read the caller's uv.toml (observed 2026-10-27).
    """
    _require_uv()
    (tmp_path / "uv.toml").write_text(_MALFORMED_UV_TOML, encoding="utf-8")
    command, plugin_root = entry
    proc = _run_from(tmp_path, command, plugin_root)
    assert not _CWD_UV_TOML_WEDGE.search(proc.stderr), (
        f"{_launcher_id(entry)} parsed the caller's uv.toml when launched from a "
        f"directory holding a malformed one.\nstderr:\n{proc.stderr}"
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
