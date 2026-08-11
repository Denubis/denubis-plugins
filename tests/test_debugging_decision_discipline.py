"""Debugging should investigate and test causes without self-critique ceremony."""

from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-plan-and-execute"
    / "skills"
    / "systematic-debugging"
    / "SKILL.md"
)


def _text() -> str:
    return " ".join(SKILL.read_text(encoding="utf-8").split())


def test_debugging_has_no_forced_self_review_or_context_reset() -> None:
    text = _text()

    for scar in {
        "MANDATORY: Context Clear",
        "SELF-AUDIT",
        "Hostile Peer Review",
        "Common Rationalizations",
        "Your Human Partner's Signals You're Doing It Wrong",
        "FULL EXECUTION PATH AUDIT",
        "read EVERY function",
        "every claim must",
        "Run `/clear`",
    }:
        assert scar not in text
    assert "Direct investigation is the default" in text
    assert "Delegation and independent review are optional" in text
    assert "Do not write an investigation document unless" in text


def test_debugging_uses_bounded_causal_experiments() -> None:
    text = _text()

    assert "Reproduce the failure or establish the strongest observable boundary" in text
    assert "Choose a reference state relevant to this failure" in text
    assert "Do not assume every bug was introduced by the current Git diff" in text
    assert "State one causal hypothesis and its falsifier" in text
    assert "Change one variable" in text
    assert "A diagnostic experiment is not automatically the fix" in text
    assert "Separate observation from inference" in text


def test_debugging_fixes_minimally_and_stops_after_three_failures() -> None:
    text = _text()

    assert "Observe the regression test fail for the intended reason" in text
    assert "Make the smallest fix at the earliest reliable boundary" in text
    assert "After three failed fixes for the same condition" in text
    assert "restore the last verified state" in text
    assert "ask one pointed question" in text
    assert "Do not commit, publish, or deploy" in text
