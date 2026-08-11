"""Decision-surface contract for impl-plan-write."""

from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-plan-and-execute"
    / "skills"
    / "impl-plan-write"
    / "SKILL.md"
)
STARTING_SKILL = SKILL.parents[1] / "starting-an-implementation-plan" / "SKILL.md"


def test_impl_plan_write_has_one_review_route() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "There is one route" in text
    assert "Review Mode Selection" not in text
    assert "Write all phases to disk, I'll review afterwards" not in text
    assert "Review each phase interactively before writing" not in text


def test_only_genuine_open_decisions_reach_the_human() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "Most phases surface none" in text
    assert "Restatement." in text
    assert "Invented alternative." in text
    assert "Obvious default." in text
    assert "What it implies:" in text


def test_uat_collation_consumes_both_decisions_and_unmapped_criteria() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "Input 1, the accumulated entries." in text
    assert "Input 2, the acceptance criteria no decision covered." in text
    assert "A phase that produced zero entries is normal" in text


def test_impl_plan_has_no_self_certifying_or_correction_ceremony() -> None:
    text = SKILL.read_text(encoding="utf-8")

    for scar in {
        "Announce at start",
        "questionable taste",
        "Frequent commits",
        "DO NOT verify codebase yourself",
        "Each step is one action (2-5 minutes)",
        "Common Rationalizations",
        "collation-audit:",
        "provenance stamp",
        "trusted as-is",
    }:
        assert scar not in text
    assert "No model-authored stamp" in text
    assert "A review finding is a lead, not a completion certificate" in text


def test_impl_plan_keeps_direct_work_and_commit_authority_explicit() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "The main session may inspect the codebase directly" in text
    assert "Delegation is optional" in text
    assert "Never put a commit step in a task unless the human authorised commits" in text
    assert "<!-- START_TASK_1 -->" in text
    assert "**Phase Type:**" in text


def test_starting_impl_plan_does_not_force_coordination_ceremony() -> None:
    text = STARTING_SKILL.read_text(encoding="utf-8")

    for scar in {
        "Announce at start",
        "Do you want to use a git worktree",
        "Label GitHub Issue",
        "Re-read starting-an-implementation-plan skill",
        "Critical peer review of implementation plan",
        "The user needs to /clear context first",
    }:
        assert scar not in text
    assert "Use the current workspace unless" in text
    assert "ask one pointed question" in text
    assert "denubis-plan-and-execute:impl-plan-write" in text
    assert "denubis-plan-and-execute:executing-an-implementation-plan" in text
