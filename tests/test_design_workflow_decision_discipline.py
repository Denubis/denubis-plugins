"""Design workflow should discover and decide without coordination ceremony."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "denubis-plan-and-execute" / "skills"


def _skill(name: str) -> str:
    return " ".join((SKILLS / name / "SKILL.md").read_text(encoding="utf-8").split())


def test_design_entry_has_one_direct_pipeline_and_no_external_side_effects() -> None:
    text = _skill("starting-a-design-plan")

    for scar in {
        "Announce at start",
        "Use TaskCreate to create todos for each phase",
        "Use subagents to try to disambiguate",
        "Design document committed",
        "Label GitHub Issue",
        "Common Rationalizations",
    }:
        assert scar not in text
    assert "Use the current workspace unless" in text
    assert "ask one pointed question" in text
    assert "denubis-plan-and-execute:design-clarify" in text
    assert "denubis-plan-and-execute:brainstorming" in text
    assert "denubis-plan-and-execute:design-write" in text
    assert "exact human source locator and resolver" in text
    assert "Do not commit, publish, label an issue, or begin implementation" in text


def test_clarification_asks_only_for_unrecoverable_intent() -> None:
    text = _skill("design-clarify")

    for scar in {"Common Mistakes", "Use AskUserQuestion for Choices", "Research Agents"}:
        assert scar not in text
    assert "Inspect before asking" in text
    assert "Do not ask the human for a fact" in text
    assert "Ask one pointed question at a time" in text
    assert "contradiction" in text.lower()
    assert "authority source" in text


def test_brainstorming_compares_only_genuine_alternatives() -> None:
    text = _skill("brainstorming")

    for scar in {
        "Announce at start",
        "Research Agents",
        "Present 2-3 different approaches",
        "Common Rationalizations",
    }:
        assert scar not in text
    assert "Direct inspection is the default" in text
    assert "Delegation is optional" in text
    assert "Do not invent alternatives" in text
    assert "Recommend one design" in text
    assert "observable consequence" in text


def test_design_writer_owns_current_document_without_commit_ceremony() -> None:
    text = _skill("design-write")

    for scar in {
        "Announce at start",
        "git commit",
        "gh issue edit",
        "Omitted Terms",
        "Present counterarguments to user",
        "Common Rationalizations",
        "Before Commit",
    }:
        assert scar not in text
    assert "## Authority Sources" in text
    assert "exact locator and resolver invocation" in text
    assert "Living architecture describes implemented state" in text
    assert "Every acceptance criterion" in text
    assert "No model-authored approval" in text
    assert "Do not commit, publish, deploy, or mutate GitHub" in text
