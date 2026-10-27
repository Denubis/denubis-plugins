"""Hooks declare and launch at the repository floor (ADR 0038).

The June 2026 Mac incident happened because the old launcher ignored script
metadata and ran a 3.9 interpreter. Check the PEP 723 declaration and the complete
registration consumed by each host, including the explicit interpreter request
that overrides UV_PYTHON. The missing-uv diagnostic is exercised in a real shell.
A Claude launcher also reports a hook uv could not start (ADR 0046 decision 8); that
behaviour is exercised in `test_hook_launcher_failure_report.py`.
"""

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PROJECT = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
_FLOOR = _PROJECT["project"]["requires-python"]
_TY_VERSION = _PROJECT["tool"]["ty"]["environment"]["python-version"]
_INSTALL_URL = "https://docs.astral.sh/uv/getting-started/installation/"
_HOOKS = sorted((_ROOT / "plugins").glob("*/hooks/*.py"))
_REGISTRATIONS = sorted((_ROOT / "plugins").glob("*/hooks/*.json"))
_SCRIPT_REFERENCE = re.compile(r"hooks/([a-z-]+\.py)")


def _commands(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    # A mod manifest registers `modules` and carries no command hooks.
    return [
        handler["command"]
        for groups in data.get("hooks", {}).values()
        for group in groups
        for handler in group["hooks"]
        if handler["type"] == "command" and ".py" in handler["command"]
    ]


_ENTRIES = [(path, command) for path in _REGISTRATIONS for command in _commands(path)]


def _assert_metadata(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    blocks = re.findall(r"(?ms)^# /// script\n(.*?)^# ///$", source)
    assert len(blocks) == 1, f"{path}: expected one PEP 723 script block"
    lines = blocks[0].splitlines()
    assert all(line == "#" or line.startswith("# ") for line in lines)
    metadata = tomllib.loads("\n".join(line[2:] for line in lines))
    assert metadata.get("requires-python") == _FLOOR, (
        f"{path}: script requires-python must equal repository floor {_FLOOR}"
    )
    assert isinstance(metadata.get("dependencies"), list)
    assert (
        metadata.get("tool", {})
        .get("ty", {})
        .get("environment", {})
        .get("python-version")
        == _TY_VERSION
    ), f"{path}: script ty environment must match the root standards"


def _assert_registration(path: Path, command: str) -> None:
    reference = _SCRIPT_REFERENCE.search(command)
    assert reference is not None, f"{path}: missing hook script reference"
    script = reference[1]
    name = script.removesuffix(".py")
    provider = "codex" if path.name == "codex-hooks.json" else "claude"
    root = "PLUGIN_ROOT" if provider == "codex" else "CLAUDE_PLUGIN_ROOT"
    environment = (
        "DENUBIS_HOOK_PROVIDER=codex "
        if name == "gh-fork-guard" and provider == "codex"
        else ""
    )
    arguments = f" --provider {provider}" if name == "instruction-budget" else ""
    preflight = (
        "command -v uv >/dev/null 2>&1 || { "
        f'echo "{name}: uv is required to run this hook; '
        f'install it from {_INSTALL_URL}" >&2; exit 1; }}; '
    )
    # `--project` anchors uv's configuration discovery at the plugin directory, so
    # the user's uv.toml applies and the caller's cwd is never read (ADR 0046).
    anchor = f'--project "${{{root}}}"'
    if provider == "codex":
        expected = (
            f"{preflight}{environment}uv run {anchor} --script --python '{_FLOOR}' "
            f'--no-project "${{{root}}}/hooks/{script}"{arguments}'
        )
    else:
        plugin = path.parents[1].name
        expected = (
            f'{preflight}hook="${{{root}}}/hooks/{script}"; '
            f"uv run {anchor} --script --python '{_FLOOR}' "
            f'--no-project "$hook"{arguments}; '
            'rc=$?; [ "$rc" -eq 0 ] && exit 0; '
            f"uv sync {anchor} --script \"$hook\" --python '{_FLOOR}' --offline "
            '>/dev/null 2>&1 && exit "$rc"; '
            f'printf \'{{"systemMessage": "{plugin}: {name} could not run '
            "(uv exit %d); run /denubis-00-getting-started:setup to check and "
            'repair plugin environments"}\\n\' "$rc"; exit 0'
        )
    assert command == expected, (
        f"{path}: expected the fixed preflight and uv script launcher at {_FLOOR}\n"
        f"expected: {expected}\nactual: {command}"
    )


def test_hook_and_registration_discovery_is_nonempty_and_complete() -> None:
    assert _HOOKS, "no Python hooks discovered"
    assert _ENTRIES, "no Python hook registration commands discovered"
    registered = set()
    for path, command in _ENTRIES:
        reference = _SCRIPT_REFERENCE.search(command)
        assert reference is not None, f"{path}: missing hook script reference"
        registered.add(path.parent / reference[1])
    assert registered == set(_HOOKS)


@pytest.mark.parametrize("hook", _HOOKS, ids=lambda path: str(path.relative_to(_ROOT)))
def test_each_hook_declares_repository_python_floor(hook: Path) -> None:
    _assert_metadata(hook)


@pytest.mark.parametrize(
    ("path", "command"),
    _ENTRIES,
    ids=[str(path.relative_to(_ROOT)) for path, _ in _ENTRIES],
)
def test_every_registration_has_fixed_preflight_and_floor_launcher(
    path: Path, command: str
) -> None:
    _assert_registration(path, command)


@pytest.mark.parametrize(
    ("path", "command"),
    _ENTRIES,
    ids=[str(path.relative_to(_ROOT)) for path, _ in _ENTRIES],
)
def test_missing_uv_reports_one_corrective_line_and_nonblocking_status(
    path: Path, command: str, tmp_path: Path
) -> None:
    environment = {**os.environ, "PATH": str(tmp_path)}
    result = subprocess.run(
        ["/bin/sh", "-c", command],
        env=environment,
        input="{}",
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    reference = _SCRIPT_REFERENCE.search(command)
    assert reference is not None
    name = reference[1].removesuffix(".py")
    assert result.returncode == 1, (path, result.stderr)
    assert result.stdout == ""
    assert result.stderr == (
        f"{name}: uv is required to run this hook; install it from {_INSTALL_URL}\n"
    )


@pytest.mark.parametrize("has_block", [True, False])
def test_metadata_gate_accepts_valid_script_and_rejects_missing_block(
    tmp_path: Path, has_block: bool
) -> None:
    hook = tmp_path / "example.py"
    header = (
        f'# /// script\n# requires-python = "{_FLOOR}"\n# dependencies = []\n'
        f'# [tool.ty.environment]\n# python-version = "{_TY_VERSION}"\n# ///\n'
    )
    hook.write_text((header if has_block else "") + "print('example')\n")
    if has_block:
        _assert_metadata(hook)
    else:
        with pytest.raises(AssertionError, match="PEP 723 script block"):
            _assert_metadata(hook)


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "bare-python",
        "wrong-floor",
        "no-preflight",
        "no-failure-report",
        "caller-config",
    ],
)
def test_registration_gate_accepts_valid_launcher_and_rejects_regressions(
    defect: str | None,
) -> None:
    path = Path("plugins/example-plugin/hooks/hooks.json")
    preflight = (
        "command -v uv >/dev/null 2>&1 || { "
        'echo "example: uv is required to run this hook; '
        'install it from https://docs.astral.sh/uv/getting-started/installation/" '
        ">&2; exit 1; }; "
    )
    command = (
        preflight + 'hook="${CLAUDE_PLUGIN_ROOT}/hooks/example.py"; '
        'uv run --project "${CLAUDE_PLUGIN_ROOT}" '
        f"--script --python '{_FLOOR}' --no-project \"$hook\"; "
        'rc=$?; [ "$rc" -eq 0 ] && exit 0; '
        'uv sync --project "${CLAUDE_PLUGIN_ROOT}" '
        f"--script \"$hook\" --python '{_FLOOR}' --offline "
        '>/dev/null 2>&1 && exit "$rc"; '
        'printf \'{"systemMessage": "example-plugin: example could not run '
        "(uv exit %d); run /denubis-00-getting-started:setup to check and repair "
        'plugin environments"}\\n\' "$rc"; exit 0'
    )
    if defect == "bare-python":
        command = 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/example.py"'
    elif defect == "wrong-floor":
        command = command.replace(f"--python '{_FLOOR}'", "--python '>=3.9'")
    elif defect == "no-preflight":
        command = command.split("}; ", 1)[1]
    elif defect == "no-failure-report":
        command = (
            preflight + 'uv run --project "${CLAUDE_PLUGIN_ROOT}" '
            f"--script --python '{_FLOOR}' --no-project "
            '"${CLAUDE_PLUGIN_ROOT}/hooks/example.py"'
        )
    elif defect == "caller-config":
        command = command.replace('--project "${CLAUDE_PLUGIN_ROOT}" ', "")
    if defect is None:
        _assert_registration(path, command)
    else:
        with pytest.raises(
            AssertionError, match="fixed preflight and uv script launcher"
        ):
            _assert_registration(path, command)
