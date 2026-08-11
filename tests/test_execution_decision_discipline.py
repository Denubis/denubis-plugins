"""Execution should perform the plan without mandatory model ceremony."""

from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-plan-and-execute"
    / "skills"
    / "executing-an-implementation-plan"
    / "SKILL.md"
)


def test_execution_has_no_forced_coordination_pipeline() -> None:
    text = " ".join(SKILL.read_text(encoding="utf-8").split())

    for scar in {
        "dispatches a fresh subagent per task",
        "REQUIRED SKILL",
        "Precondition: Worktree Required",
        "Post-Resume Verification",
        "MANDATORY: Human Transparency",
        "Turn Budgets",
        "Null / Empty Subagent Response",
        "Create Session-Isolated Scratchpad",
        "Post-Implementation Stages (Mandatory)",
        "Print the full",
        "Common Rationalizations",
    }:
        assert scar not in text

    assert "The main session executes tasks directly by default" in text
    assert "Delegation is optional" in text
    assert "A review finding is a lead, not verification evidence" in text


def test_execution_preserves_workspace_and_human_authority() -> None:
    text = " ".join(SKILL.read_text(encoding="utf-8").split())

    assert "Use the absolute working directory from the invocation" in text
    assert "Preserve pre-existing changes" in text
    assert "Do not create a branch or worktree unless" in text
    assert "Do not commit, push, publish, deploy, or mutate external systems unless" in text
    assert "ask one pointed question" in text


def test_execution_uses_plan_owned_evidence_and_uat() -> None:
    text = " ".join(SKILL.read_text(encoding="utf-8").split())

    assert "Read one phase at a time" in text
    assert "test-requirements.md" in text
    assert "uat-requirements.md" in text
    assert "Observe the failing check before implementation" in text
    assert "positive signal" in text
    assert "Human UAT is required only for entries" in text
    assert "If there are no UAT entries, do not invent a human gate" in text
    assert "Recompute final acceptance-criterion coverage" in text
    assert "Do not claim completion from a model report" in text


def test_execution_keeps_failure_recovery_without_cut_and_try() -> None:
    text = " ".join(SKILL.read_text(encoding="utf-8").split())

    assert "State one causal hypothesis and its falsifier" in text
    assert "After three failed fixes" in text
    assert "restore the last verified repository state" in text
