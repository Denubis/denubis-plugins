"""Review and human acceptance are bounded tools, not workflow certificates."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "denubis-plan-and-execute" / "skills"


def _skill(name: str) -> str:
    return " ".join((SKILLS / name / "SKILL.md").read_text(encoding="utf-8").split())


def test_code_review_produces_leads_without_mandatory_transition_status() -> None:
    text = _skill("requesting-code-review")

    for scar in {
        "Two mandatory triggers",
        "Fix ALL issues",
        "APPROVED status",
        "proleptic challenge",
        "exec-uat-gate",
        "Turn Budgets",
        "Common Rationalizations",
    }:
        assert scar not in text
    assert "Review is invoked only when" in text
    assert "Every finding is a lead" in text
    assert "The caller verifies confirmed findings against observable evidence" in text
    assert "Do not write a review certificate" in text


def test_coherence_review_is_optional_and_not_the_no_uat_fallback() -> None:
    text = _skill("exec-coherence-review")

    for scar in {
        "in place of `exec-uat-gate`",
        "If no notable findings",
        "No Findings",
        "Announce at start",
        "coherence-reviewer agent",
    }:
        assert scar not in text
    assert "Use only when a design-conformance question remains" in text
    assert "It is not a substitute for an empty UAT plan" in text
    assert "Open every cited source" in text
    assert "does not certify conformance" in text


def test_uat_owns_only_irreducible_human_judgment() -> None:
    text = _skill("exec-uat-gate")

    for scar in {
        "After code review passes",
        "proleptic challenge",
        "exec-coherence-review",
        "Announce at start",
        "Common Rationalizations",
    }:
        assert scar not in text
    assert "one entry at a time" in text
    assert "Do not ask the human to rerun an automated or operational check" in text
    assert "The human's response is the authority" in text
    assert "exact source locator and resolver" in text
    assert "Acceptance does not grant authority to commit, publish, or deploy" in text


def test_execution_routes_real_uat_to_its_single_owner() -> None:
    text = _skill("executing-an-implementation-plan")

    assert "denubis-plan-and-execute:exec-uat-gate" in text


def test_proleptic_challenge_anticipates_real_risks_without_burdening_human() -> None:
    text = _skill("proleptic-challenge")

    for scar in {
        "fires at design finalisation, between implementation phases, and before acceptance",
        "Announce at start",
        "Present ALL counterarguments",
        "Dismissal requires evidence",
        "Common Rationalizations",
        "after each phase's code review passes",
        "code review returns APPROVED",
    }:
        assert scar not in text
    assert "Use when a consequential decision has a named uncertainty" in text
    assert "A counterargument is a lead" in text
    assert "Verify it before presenting it" in text
    assert "Discard objections that are unsupported" in text
    assert "ask one pointed question at a time" in text
    assert "The human may dismiss a concern" in text
    assert "does not grant authority to commit" in text
