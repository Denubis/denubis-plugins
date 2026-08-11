"""Optional analysis skills answer bounded questions without manufacturing ceremony."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "denubis-plan-and-execute" / "skills"


def _skill(name: str) -> str:
    return " ".join((SKILLS / name / "SKILL.md").read_text(encoding="utf-8").split())


def test_critical_review_audits_artifact_not_user_frustration() -> None:
    text = _skill("critical-peer-review")

    for scar in {
        "Search for frustration signals",
        "Swearing",
        '"mate"',
        "Build the ACH matrix",
        "Overall Assessment",
        "self-audit",
        "mandatory",
    }:
        assert scar not in text
    assert "Resolve the exact artifact and evidence universe" in text
    assert "Every finding remains a lead" in text
    assert "Do not write a review file unless" in text
    assert "Do not infer anything from the human's tone" in text


def test_refactoring_rubric_requires_a_concrete_cost_and_coverage() -> None:
    text = _skill("exec-refactoring-rubric")

    for scar in {
        "Tier 3 Deferred Smells Registry",
        "Evidence Grading Criteria",
        "clean commit boundary",
        "Below Threshold",
        "future skill would need",
    }:
        assert scar not in text
    assert "A smell name is a lead" in text
    assert "concrete maintenance cost" in text
    assert "behavioral coverage" in text
    assert "Metrics and thresholds cannot authorise" in text
    assert "This rubric does not edit code" in text


def test_assumption_review_uses_lenses_only_when_they_change_action() -> None:
    text = _skill("restate-our-assumptions")

    for scar in {
        "TaskCreate",
        "apply all three lenses",
        "Always include",
        "Red Flags",
        "Present the full report",
    }:
        assert scar not in text
    assert "Test each scoped assumption against current evidence" in text
    assert "Use a conceptual lens only when" in text
    assert "state the action that changes" in text
    assert "ask one pointed question" in text
    assert "Do not edit rationale or dependency files unless" in text
