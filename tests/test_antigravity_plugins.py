"""Executable packaging contracts for the Antigravity CLI plugin surface."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "scripts" / "install_antigravity_plugins.sh"
CLAUDE_MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _claude_skill_plugin_names() -> tuple[str, ...]:
    marketplace = json.loads(CLAUDE_MARKETPLACE_PATH.read_text(encoding="utf-8"))
    return tuple(
        entry["name"]
        for entry in marketplace["plugins"]
        if list((REPO_ROOT / entry["source"] / "skills").glob("*/SKILL.md"))
    )


PLUGIN_NAMES = _claude_skill_plugin_names()


def _fake_agy(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    call_log = tmp_path / "agy-calls"
    executable = bin_dir / "agy"
    executable.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "$DENUBIS_AGY_CALL_LOG"\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return bin_dir, call_log


def _run_installer(
    tmp_path: Path,
    *arguments: str,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir, call_log = _fake_agy(tmp_path)
    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
    environment["DENUBIS_AGY_CALL_LOG"] = str(call_log)
    result = subprocess.run(
        [str(INSTALLER_PATH), *arguments],
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
    for plugin_name in PLUGIN_NAMES:
        plugin_root = REPO_ROOT / "plugins" / plugin_name
        manifest = json.loads((plugin_root / "plugin.json").read_text(encoding="utf-8"))

        assert manifest == {"name": plugin_name}
        assert list((plugin_root / "skills").glob("*/SKILL.md"))


def test_validate_only_does_not_modify_the_live_plugin_install(
    tmp_path: Path,
) -> None:
    result, calls = _run_installer(tmp_path, "--validate-only")

    assert result.returncode == 0, result.stderr
    assert calls == [
        f"plugin validate {REPO_ROOT / 'plugins' / name}" for name in PLUGIN_NAMES
    ]


def test_install_validates_every_plugin_before_installing_any_plugin(
    tmp_path: Path,
) -> None:
    result, calls = _run_installer(tmp_path)

    assert result.returncode == 0, result.stderr
    expected_validation = [
        f"plugin validate {REPO_ROOT / 'plugins' / name}" for name in PLUGIN_NAMES
    ]
    expected_installation = [
        f"plugin install {REPO_ROOT / 'plugins' / name}" for name in PLUGIN_NAMES
    ]
    assert calls == [*expected_validation, *expected_installation]


def test_unknown_installer_option_fails_before_calling_agy(tmp_path: Path) -> None:
    result, calls = _run_installer(tmp_path, "--unsupported")

    assert result.returncode != 0
    assert calls == []


@pytest.mark.parametrize("argument", ["-h", "--help"])
def test_help_is_side_effect_free(tmp_path: Path, argument: str) -> None:
    result, calls = _run_installer(tmp_path, argument)

    assert result.returncode == 0, result.stderr
    assert calls == []
