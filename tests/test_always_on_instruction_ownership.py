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
DIRECTIVE_SKILL = (
    REPO_ROOT
    / "plugins"
    / "denubis-extending-claude"
    / "skills"
    / "writing-claude-directives"
    / "SKILL.md"
)


def _headings(path: Path) -> set[str]:
    return {
        line.removeprefix("## ")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_global_candidate_contains_only_continuous_instruction_sections() -> None:
    headings = _headings(GLOBAL_CANDIDATE)

    assert {
        "Working relationship",
        "Request boundary",
        "Engineering invariants",
        "Evidence and authority",
        "Documents and memory",
        "Communication",
        "Environment",
    } <= headings
    assert headings.isdisjoint(
        {
            "Git Commits",
            "Settings Sync",
            "Repository Search",
            "Writing prose",
            "Memory: the `.notes/` scheme",
            "Halting on Reviewer Findings",
        }
    )


def test_global_candidate_retires_known_situational_and_stale_procedures() -> None:
    text = GLOBAL_CANDIDATE.read_text(encoding="utf-8")

    assert "claude-sync" not in text
    assert "3+ files" not in text
    assert "keywords:" not in text
    assert "UserPromptSubmit" not in text
    assert "SessionStart" not in text
    assert "Do not generate embeddings" not in text


def test_global_candidate_preserves_cross_project_boundaries() -> None:
    text = GLOBAL_CANDIDATE.read_text(encoding="utf-8")

    assert "configured cache" in text
    assert "Never commit unless explicitly requested" in text
    assert "one pointed question" in text
    assert "original human record" in text
    assert "No palimpsests" in text
    assert "No archaeology" in text
    assert "three consecutive failed attempts" in text


def test_project_claude_contains_project_rules_not_incident_history() -> None:
    headings = _headings(PROJECT_CLAUDE)
    text = PROJECT_CLAUDE.read_text(encoding="utf-8")

    assert headings == {
        "Runtime boundaries",
        "Repository contracts",
        "Finding aids",
    }
    assert "Phase 1 review" not in text
    assert "repeated sessions" not in text
    assert "HALT When Things Feel Sideways" not in text


def test_task_invocation_format_is_owned_by_directive_authoring_skill() -> None:
    text = DIRECTIVE_SKILL.read_text(encoding="utf-8")

    assert '<invoke name="Task">' in text
    assert '<parameter name="subagent_type">' in text
    assert "When documenting a Task invocation" in text


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

    assert "outputStyle" not in settings
    assert "SessionStart" not in settings["hooks"]
    for plugin_id in {
        "denubis-hook-skill-reinforcement@denubis-plugins",
        "denubis-hook-claudemd-reminder@denubis-plugins",
        "denubis-notes-advisory@denubis-plugins",
        "denubis-bibliography@denubis-plugins",
    }:
        assert plugin_id not in enabled
    assert "Bash(~/.claude/bin/claude-sync:*)" not in allowed
    assert "Skill(denubis-bibliography:*)" not in allowed


def test_settings_candidate_keeps_independent_controls_and_new_owners() -> None:
    settings = json.loads(SETTINGS_CANDIDATE.read_text(encoding="utf-8"))
    enabled = settings["enabledPlugins"]
    allowed = settings["permissions"]["allow"]

    for plugin_id in {
        "denubis-plan-and-execute@denubis-plugins",
        "denubis-project-notes@denubis-plugins",
        "denubis-academic@denubis-plugins",
        "denubis-hook-branch-bg@denubis-plugins",
        "denubis-hook-pretooluse-dispatcher@denubis-plugins",
        "denubis-hook-gh-fork-guard@denubis-plugins",
    }:
        assert enabled[plugin_id] is True
    assert "Skill(denubis-plan-and-execute:*)" in allowed
    assert "Skill(denubis-project-notes:*)" in allowed
    assert "Skill(denubis-academic:*)" in allowed
    assert {"PreToolUse", "PostToolUse", "Notification"} <= settings["hooks"].keys()
