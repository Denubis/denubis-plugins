"""Coding guidance should load only the procedures relevant to the change."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "denubis-plan-and-execute" / "skills"


def _skill(name: str) -> str:
    return " ".join((SKILLS / name / "SKILL.md").read_text(encoding="utf-8").split())


def test_coding_orchestrator_routes_conditionally_without_writing_tool_memory() -> None:
    text = _skill("coding-effectively")

    for scar in {
        "ALWAYS load when coding",
        "append to `.ed3d/tools.md`",
        "you have pandoc",
        "Quarterly Review",
        "Common Mistakes",
        "Function exceeds ~40 lines",
        "File exceeds ~400 lines",
    }:
        assert scar not in text
    assert "Load only the procedures relevant to the current change" in text
    assert "Read project configuration before selecting tools" in text
    assert "Do not modify a tool registry merely because" in text
    for routed in {
        "coding-tdd",
        "coding-verify",
        "coding-fcis",
        "defense-in-depth",
        "coding-python-idioms",
        "coding-good-tests",
        "coding-property-testing",
        "howto-develop-with-postgres",
    }:
        assert routed in text


def test_tdd_states_the_observable_cycle_without_argument_scar() -> None:
    text = _skill("coding-tdd")

    for scar in {
        "The Iron Law",
        "Violating the letter",
        "Common Rationalizations",
        "Red Flags",
        "Delete means delete",
        "Sunk cost fallacy",
    }:
        assert scar not in text
    assert "RED: write the smallest behavioral test" in text
    assert "Observe it fail for the intended reason" in text
    assert "GREEN: make the smallest coherent implementation" in text
    assert "REFACTOR: improve structure only while the behavior stays green" in text
    assert "A test that passes on its first run provides no red-state evidence" in text


def test_verification_reports_fresh_bounded_evidence_without_moralising() -> None:
    text = _skill("coding-verify")

    for scar in {
        "dishonesty",
        "= lying",
        "you'll be replaced",
        "Rationalization Prevention",
        "Red Flags",
        "expressing satisfaction",
    }:
        assert scar not in text
    assert "For each completion claim" in text
    assert "exact command or observation" in text
    assert "scope and exclusions" in text
    assert "Fresh evidence means" in text
    assert "A delegated report is not evidence" in text


def test_fcis_is_a_design_tool_not_mandatory_source_annotation() -> None:
    text = _skill("coding-fcis")

    for scar in {
        "Add pattern comment to application code files",
        "Contains ONLY",
        "NEVER contains",
        "Common Rationalizations",
        "Red Flags",
    }:
        assert scar not in text
    assert "Use this separation when it improves" in text
    assert "Functional core" in text
    assert "Imperative shell" in text
    assert "Do not refactor untested code merely to fit the pattern" in text


def test_defense_in_depth_uses_distinct_boundary_invariants() -> None:
    text = _skill("defense-in-depth")

    for scar in {"The Four Layers", "Common Mistakes", "The bug isn't fixed until it's impossible"}:
        assert scar not in text
    assert "Validate untrusted data at the earliest owned boundary" in text
    assert "Each additional check must enforce a distinct invariant" in text
    assert "Do not duplicate the same validation" in text
    assert "Test the bypass path" in text
