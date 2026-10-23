"""Executable packaging contracts for the Antigravity CLI plugin surface."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_antigravity_plugins.sh"
CLAUDE_MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _agy_plugin_names() -> tuple[str, ...]:
    marketplace = json.loads(CLAUDE_MARKETPLACE_PATH.read_text(encoding="utf-8"))
    return tuple(
        entry["name"]
        for entry in marketplace["plugins"]
        if (REPO_ROOT / entry["source"] / "plugin.json").is_file()
    )


def _claude_skill_plugin_names() -> tuple[str, ...]:
    marketplace = json.loads(CLAUDE_MARKETPLACE_PATH.read_text(encoding="utf-8"))
    return tuple(
        entry["name"]
        for entry in marketplace["plugins"]
        if list((REPO_ROOT / entry["source"] / "skills").glob("*/SKILL.md"))
    )


PLUGIN_NAMES = _agy_plugin_names()


def _fake_agy(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    call_log = tmp_path / "agy-calls"
    executable = bin_dir / "agy"
    executable.write_text(
        '#!/usr/bin/env bash\n'
        'test -f "$3/plugin.json" || exit 19\n'
        'printf \'%s\\n\' "$*" >> "$DENUBIS_AGY_CALL_LOG"\n'
        'if [[ "${DENUBIS_AGY_FAIL_NAME:-}" == "${3##*/}" ]]; then exit 23; fi\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    uv = bin_dir / "uv"
    uv.write_text(
        '#!/usr/bin/env bash\n'
        '[[ "$1" == run && "$2" == --no-sync && "$3" == --project ]] || exit 29\n'
        'shift 4\n'
        '[[ "$1" == python ]] || exit 29\n'
        'shift\n'
        'exec "$DENUBIS_TEST_PYTHON" "$@"\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)
    return bin_dir, call_log


def _run_installer(
    tmp_path: Path,
    *arguments: str,
    fail_name: str | None = None,
    installer_path: Path = INSTALLER_PATH,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir, call_log = _fake_agy(tmp_path)
    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
    environment["DENUBIS_AGY_CALL_LOG"] = str(call_log)
    environment["DENUBIS_TEST_PYTHON"] = sys.executable
    if fail_name is not None:
        environment["DENUBIS_AGY_FAIL_NAME"] = fail_name
    result = subprocess.run(
        [str(installer_path), *arguments],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    calls = (
        call_log.read_text(encoding="utf-8").splitlines() if call_log.exists() else []
    )
    return result, calls


def test_exposed_plugins_use_their_existing_skill_trees() -> None:
    for plugin_name in _claude_skill_plugin_names():
        plugin_root = REPO_ROOT / "plugins" / plugin_name
        manifest = json.loads((plugin_root / "plugin.json").read_text(encoding="utf-8"))

        assert manifest == {"name": plugin_name}
        assert list((plugin_root / "skills").glob("*/SKILL.md"))


def test_validate_only_does_not_modify_the_live_plugin_install(
    tmp_path: Path,
) -> None:
    result, calls = _run_installer(tmp_path, "--validate-only")

    assert result.returncode == 0, result.stderr
    projected = [Path(call.removeprefix("plugin validate ")) for call in calls]
    assert len(projected) == len(PLUGIN_NAMES)
    assert [path.name for path in projected] == list(PLUGIN_NAMES)
    assert all(path.parent == projected[0].parent for path in projected)
    assert all(path != REPO_ROOT / "plugins" / path.name for path in projected)
    assert all(not path.exists() for path in projected)


def test_install_validates_every_plugin_before_installing_any_plugin(
    tmp_path: Path,
) -> None:
    result, calls = _run_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(calls) == 2 * len(PLUGIN_NAMES)
    validation = calls[: len(PLUGIN_NAMES)]
    installation = calls[len(PLUGIN_NAMES) :]
    assert all(call.startswith("plugin validate ") for call in validation)
    assert installation == [
        call.replace("plugin validate ", "plugin install ", 1) for call in validation
    ]
    assert [
        Path(call.removeprefix("plugin validate ")).name for call in validation
    ] == list(PLUGIN_NAMES)
    assert all(
        Path(call.removeprefix("plugin validate ")) != REPO_ROOT / "plugins" / name
        for call, name in zip(validation, PLUGIN_NAMES, strict=True)
    )


def test_unknown_installer_option_fails_before_calling_agy(tmp_path: Path) -> None:
    result, calls = _run_installer(tmp_path, "--unsupported")

    assert result.returncode != 0
    assert calls == []


def test_failed_validation_never_starts_installation(tmp_path: Path) -> None:
    result, calls = _run_installer(tmp_path, fail_name=PLUGIN_NAMES[1])

    assert result.returncode != 0
    assert calls
    assert all(call.startswith("plugin validate ") for call in calls)
    assert all(
        Path(call.removeprefix("plugin validate ")).parent != REPO_ROOT / "plugins"
        for call in calls
    )


def test_agent_only_plugin_with_manifest_is_selected(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(INSTALLER_PATH, scripts / INSTALLER_PATH.name)
    shutil.copy2(
        REPO_ROOT / "scripts" / "project_antigravity_plugin.py",
        scripts / "project_antigravity_plugin.py",
    )
    marketplace = repository / ".claude-plugin" / "marketplace.json"
    marketplace.parent.mkdir()
    marketplace.write_text(
        json.dumps({"plugins": [{"name": "agent-only", "source": "./plugins/agent-only"}]}),
        encoding="utf-8",
    )
    plugin = repository / "plugins" / "agent-only"
    (plugin / "agents").mkdir(parents=True)
    (plugin / "plugin.json").write_text('{"name":"agent-only"}', encoding="utf-8")
    (plugin / "agents" / "one.md").write_text(
        "---\nname: one\ndescription: One agent\nmodel: sonnet\n---\nBody\n",
        encoding="utf-8",
    )

    result, calls = _run_installer(tmp_path, installer_path=scripts / INSTALLER_PATH.name)

    assert result.returncode == 0, result.stderr
    assert [call.split()[1] for call in calls] == ["validate", "install"]
    assert all(call.endswith("/agent-only") for call in calls)


@pytest.mark.parametrize("argument", ["-h", "--help"])
def test_help_is_side_effect_free(tmp_path: Path, argument: str) -> None:
    result, calls = _run_installer(tmp_path, argument)

    assert result.returncode == 0, result.stderr
    assert calls == []
