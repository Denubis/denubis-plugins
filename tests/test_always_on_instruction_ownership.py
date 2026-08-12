"""Ownership contracts for global and project always-on instructions."""

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_CANDIDATE = (
    REPO_ROOT / "deployment" / "instruction-control" / "foa4008439" / "CLAUDE.md"
)
PROJECT_CLAUDE = REPO_ROOT / "CLAUDE.md"
CANDIDATE_MANIFEST = GLOBAL_CANDIDATE.with_name("candidate-manifest.json")
SETTINGS_CANDIDATE = GLOBAL_CANDIDATE.with_name("settings.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_candidate_manifest_binds_the_files_a_deployer_will_consume() -> None:
    manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert manifest["host"] == "foa4008439"
    assert manifest["state"] == "source-candidate"
    for name, expected_path in {
        "global_claude": GLOBAL_CANDIDATE,
        "project_claude": PROJECT_CLAUDE,
        "settings": SETTINGS_CANDIDATE,
    }.items():
        record = manifest["candidates"][name]
        path = REPO_ROOT / record["path"]
        assert path == expected_path
        assert record["bytes"] == path.stat().st_size
        assert record["sha256"] == _sha256(path)

    assert manifest["baselines"]["global_claude"]["sha256"] != (
        manifest["candidates"]["global_claude"]["sha256"]
    )


def test_settings_candidate_removes_retired_instruction_surfaces() -> None:
    settings = json.loads(SETTINGS_CANDIDATE.read_text(encoding="utf-8"))
    enabled = settings["enabledPlugins"]
    allowed = settings["permissions"]["allow"]

    for plugin_id in (
        "denubis-hook-skill-reinforcement@denubis-plugins",
        "denubis-hook-claudemd-reminder@denubis-plugins",
        "denubis-notes-advisory@denubis-plugins",
        "denubis-bibliography@denubis-plugins",
    ):
        assert plugin_id not in enabled
    assert "Bash(~/.claude/bin/claude-sync:*)" not in allowed
    assert "Skill(denubis-bibliography:*)" not in allowed


def test_settings_candidate_keeps_independent_controls_and_new_owners() -> None:
    settings = json.loads(SETTINGS_CANDIDATE.read_text(encoding="utf-8"))
    manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    enabled = settings["enabledPlugins"]
    allowed = settings["permissions"]["allow"]

    for plugin_id in (
        "denubis-plan-and-execute@denubis-plugins",
        "denubis-academic@denubis-plugins",
        "denubis-hook-branch-bg@denubis-plugins",
        "denubis-hook-pretooluse-dispatcher@denubis-plugins",
        "denubis-hook-gh-fork-guard@denubis-plugins",
    ):
        assert enabled[plugin_id] is True
    assert "Skill(denubis-plan-and-execute:*)" in allowed
    assert "Skill(denubis-academic:*)" in allowed
    assert {"SessionStart", "PreToolUse", "PostToolUse", "Notification"} <= settings[
        "hooks"
    ].keys()
    assert isinstance(settings["model"], str) and settings["model"]
    assert isinstance(settings["outputStyle"], str) and settings["outputStyle"]

    installed = {
        release["name"] for release in manifest["plugin_releases"]["install"]
    }
    assert "denubis-project-notes" not in installed
    assert "denubis-project-notes@denubis-plugins" not in enabled
