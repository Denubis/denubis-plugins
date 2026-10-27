"""Hook launchers report a hook that could not start; a started hook's status passes.

ADR 0046 decision 8: when ``uv run --script`` cannot start a hook, the launcher prints
one JSON object whose ``systemMessage`` names the plugin, the hook, uv's exit status and
the setup command that checks and repairs plugin environments, then exits 0 so Claude
Code shows the warning. A hook that did start keeps its own exit status, stdout and
stderr, so a PreToolUse guard's deliberate exit 2 still blocks with its own reason.

Every Claude ``uv run --script`` launcher runs in a real shell with
``CLAUDE_PLUGIN_ROOT`` pointing at a temporary plugin copy whose hook script is a
fixture. The two start-failure fixtures fail inside uv before the hook body runs: an
unresolvable path dependency, and malformed script metadata. uv exits 2 for the
second, the same status a blocking hook returns, so that pair is the case exit status
alone cannot separate. Each start-failure fixture is first run under uv directly as a
control: that run must fail without executing the body, and its exit status is the one
the message must carry.

Launchers run from a directory holding a conflict-marked ``pyproject.toml``, which
wedged uv's settings discovery in the 2026-07-13 incident, and a conflict-marked
``uv.toml``, so a launch or classification step that reads the caller's project or
configuration fails these tests.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PLUGINS = _ROOT / "plugins"
_FLOOR = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["requires-python"]
_REPAIR = (
    "run /denubis-00-getting-started:setup to check and repair plugin environments"
)
_SCRIPT = re.compile(r"/hooks/([a-z-]+)\.py")
_UV_RUN_SCRIPT = re.compile(r"\buv run [^;]*--script\b")
_HOOK_INPUT = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"})
# First run may provision an interpreter via uv; later runs hit the cache.
_TIMEOUT_S = 180

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
_MALFORMED_UV_TOML = """\
<<<<<<< HEAD
link-mode = "copy"
=======
link-mode = "hardlink"
>>>>>>> other
"""

# The body records that it ran, so a start-failure fixture can prove it never did.
_MARK_RUN = (
    "import os, pathlib, sys\n"
    "pathlib.Path(os.environ['HOOK_FIXTURE_MARKER']).write_text('ran')\n"
)
_START_FAILURES = {
    "unresolvable-dependency": (
        "# /// script\n"
        f'# requires-python = "{_FLOOR}"\n'
        '# dependencies = ["denubis-absent @ file:///nonexistent/denubis-absent"]\n'
        "# ///\n" + _MARK_RUN
    ),
    "malformed-metadata": (
        "# /// script\n"
        f'# requires-python = "{_FLOOR}"\n'
        "# dependencies = [\n"
        "# ///\n" + _MARK_RUN
    ),
}


@dataclass(frozen=True)
class Launcher:
    plugin: str
    registration: Path
    command: str

    @property
    def hook(self) -> str:
        match = _SCRIPT.search(self.command)
        assert match is not None, f"{self.registration}: no hook script reference"
        return match[1]

    @property
    def label(self) -> str:
        return f"{self.plugin}/{self.hook}"


def _uv_script_commands(registration: Path) -> list[str]:
    data = json.loads(registration.read_text(encoding="utf-8"))
    # A mod manifest registers `modules` and carries no command hooks.
    return [
        handler["command"]
        for groups in data.get("hooks", {}).values()
        for group in groups
        for handler in group["hooks"]
        if handler["type"] == "command" and _UV_RUN_SCRIPT.search(handler["command"])
    ]


def _claude_launchers() -> list[Launcher]:
    """Launchers Claude Code runs, read through each plugin's Claude manifest."""
    launchers = []
    for plugin_root in sorted(path for path in _PLUGINS.iterdir() if path.is_dir()):
        manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        registration = plugin_root / manifest.get("hooks", "hooks/hooks.json")
        if not registration.is_file():
            continue
        launchers.extend(
            Launcher(plugin_root.name, registration.resolve(), command)
            for command in _uv_script_commands(registration)
        )
    return launchers


_LAUNCHERS = _claude_launchers()


def _require_uv() -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv unavailable; behavioural launcher checks need it")


def _caller_directory(tmp_path: Path) -> Path:
    caller = tmp_path / "caller"
    caller.mkdir()
    (caller / "pyproject.toml").write_text(_CONFLICTED_PYPROJECT, encoding="utf-8")
    (caller / "uv.toml").write_text(_MALFORMED_UV_TOML, encoding="utf-8")
    return caller


def _plugin_copy(tmp_path: Path, launcher: Launcher, source: str) -> Path:
    plugin_root = tmp_path / launcher.plugin
    hooks = plugin_root / "hooks"
    hooks.mkdir(parents=True)
    (hooks / f"{launcher.hook}.py").write_text(source, encoding="utf-8")
    return plugin_root


def _environment(plugin_root: Path, marker: Path) -> dict[str, str]:
    return {
        **os.environ,
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "HOOK_FIXTURE_MARKER": str(marker),
    }


def _run(
    argv: list[str], cwd: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=environment,
        input=_HOOK_INPUT,
        text=True,
        capture_output=True,
        check=False,
        timeout=_TIMEOUT_S,
    )


def test_discovery_finds_every_claude_uv_launcher() -> None:
    """The manifest route and a direct registration scan agree and are non-empty."""
    scanned = {
        path.resolve()
        for path in _PLUGINS.glob("*/hooks/*.json")
        if path.name != "codex-hooks.json" and _uv_script_commands(path)
    }
    assert scanned, "no Claude uv run --script registrations found"
    assert {launcher.registration for launcher in _LAUNCHERS} == scanned


@pytest.mark.parametrize("fixture", sorted(_START_FAILURES))
@pytest.mark.parametrize(
    "launcher", _LAUNCHERS, ids=[launcher.label for launcher in _LAUNCHERS]
)
def test_start_failure_reports_plugin_hook_status_and_repair(
    launcher: Launcher, fixture: str, tmp_path: Path
) -> None:
    _require_uv()
    caller = _caller_directory(tmp_path)
    plugin_root = _plugin_copy(tmp_path, launcher, _START_FAILURES[fixture])
    marker = tmp_path / "ran"
    environment = _environment(plugin_root, marker)

    control = _run(
        [
            "uv",
            "run",
            "--project",
            str(plugin_root),
            "--script",
            "--python",
            _FLOOR,
            "--no-project",
            str(plugin_root / "hooks" / f"{launcher.hook}.py"),
        ],
        caller,
        environment,
    )
    assert control.returncode != 0, control
    assert control.stderr.strip(), control
    assert not marker.exists(), "the start-failure fixture ran its body under uv"

    result = _run(["/bin/sh", "-c", launcher.command], caller, environment)

    assert not marker.exists(), "the launcher ran the start-failure fixture's body"
    assert result.returncode == 0, result
    assert json.loads(result.stdout) == {
        "systemMessage": (
            f"{launcher.plugin}: {launcher.hook} could not run "
            f"(uv exit {control.returncode}); {_REPAIR}"
        )
    }
    assert control.stderr.strip() in result.stderr


@pytest.mark.parametrize(
    "launcher", _LAUNCHERS, ids=[launcher.label for launcher in _LAUNCHERS]
)
def test_launcher_reads_user_level_uv_configuration(
    launcher: Launcher, tmp_path: Path
) -> None:
    """The launcher reads ``$XDG_CONFIG_HOME/uv/uv.toml``, so its settings apply.

    A malformed user-level file makes uv fail before the hook starts, which the
    launcher reports. A launcher passing ``--no-config`` would skip the file and run
    the hook, leaving the user's cache directory and other settings unread.
    """
    _require_uv()
    caller = _caller_directory(tmp_path)
    config_home = tmp_path / "config-home"
    (config_home / "uv").mkdir(parents=True)
    (config_home / "uv" / "uv.toml").write_text(_MALFORMED_UV_TOML, encoding="utf-8")
    source = (
        "# /// script\n"
        f'# requires-python = "{_FLOOR}"\n'
        "# dependencies = []\n"
        "# ///\n" + _MARK_RUN
    )
    plugin_root = _plugin_copy(tmp_path, launcher, source)
    marker = tmp_path / "ran"
    environment = {
        **_environment(plugin_root, marker),
        "XDG_CONFIG_HOME": str(config_home),
    }

    control = _run(
        [
            "uv",
            "run",
            "--script",
            "--python",
            _FLOOR,
            "--no-project",
            str(plugin_root / "hooks" / f"{launcher.hook}.py"),
        ],
        caller,
        environment,
    )
    assert control.returncode != 0, control
    assert str(config_home / "uv" / "uv.toml") in control.stderr, control
    assert not marker.exists(), "uv ran the hook despite the malformed user config"

    result = _run(["/bin/sh", "-c", launcher.command], caller, environment)

    assert not marker.exists(), "the launcher ran the hook without reading uv.toml"
    assert result.returncode == 0, result
    assert json.loads(result.stdout) == {
        "systemMessage": (
            f"{launcher.plugin}: {launcher.hook} could not run "
            f"(uv exit {control.returncode}); {_REPAIR}"
        )
    }


@pytest.mark.parametrize("status", [0, 1, 2])
@pytest.mark.parametrize(
    "launcher", _LAUNCHERS, ids=[launcher.label for launcher in _LAUNCHERS]
)
def test_started_hook_status_and_output_pass_through(
    launcher: Launcher, status: int, tmp_path: Path
) -> None:
    _require_uv()
    caller = _caller_directory(tmp_path)
    source = (
        "# /// script\n"
        f'# requires-python = "{_FLOOR}"\n'
        "# dependencies = []\n"
        "# ///\n" + _MARK_RUN + "sys.stdout.write('stdout:' + sys.stdin.read())\n"
        f"sys.stderr.write('stderr: status {status}\\n')\n"
        f"sys.exit({status})\n"
    )
    plugin_root = _plugin_copy(tmp_path, launcher, source)
    marker = tmp_path / "ran"

    result = _run(
        ["/bin/sh", "-c", launcher.command],
        caller,
        _environment(plugin_root, marker),
    )

    assert marker.read_text(encoding="utf-8") == "ran"
    assert result.returncode == status, result
    assert result.stdout == f"stdout:{_HOOK_INPUT}"
    assert result.stderr == f"stderr: status {status}\n"
