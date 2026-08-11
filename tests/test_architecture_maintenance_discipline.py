"""Living architecture follows implemented evidence without review ceremony."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "denubis-plan-and-execute" / "skills"


def _skill(name: str) -> str:
    return " ".join((SKILLS / name / "SKILL.md").read_text(encoding="utf-8").split())


def test_maintenance_maps_current_state_directly() -> None:
    text = _skill("maintain-architecture")

    for scar in {
        "Announce at start",
        "Subagent 1",
        "Subagent 2",
        "Common Rationalizations",
        "suggest commit",
        "design-write (after proleptic challenge)",
    }:
        assert scar not in text
    assert "Inspect the implementation and architecture directly" in text
    assert "implemented state" in text
    assert "ask one pointed question" in text
    assert "denubis-plan-and-execute:architecture-update" in text
    assert "Do not commit" in text


def test_update_writes_current_truth_not_future_design() -> None:
    text = _skill("architecture-update")

    for scar in {
        "Design plan file path",
        "proposals presented to human",
        "approved changes",
        "changes included in design plan commit",
        "Common Rationalizations",
        "Announce at start",
    }:
        assert scar not in text
    assert "Living architecture describes implemented state" in text
    assert "Do not project a future design" in text
    assert "exact current implementation source" in text
    assert "human authority uses an exact source locator and resolver" in text
    assert "No palimpsests" in text
    assert "Verify every link and source pointer" in text
    assert "Do not commit" in text
