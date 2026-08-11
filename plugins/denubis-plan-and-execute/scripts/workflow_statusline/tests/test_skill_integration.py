"""Static integration tests verifying SKILL.md files contain expected strings."""

from __future__ import annotations

from pathlib import Path

import pytest

_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"


# ---------------------------------------------------------------------------
# AC6.1 — Each of 4 target skills invokes exec-session-naming
# ---------------------------------------------------------------------------
_SESSION_NAMING_SKILLS = [
    "starting-a-design-plan",
    "starting-an-implementation-plan",
    "executing-an-implementation-plan",
    "systematic-debugging",
]


class TestSessionNamingInvocation:
    @pytest.mark.parametrize("skill", _SESSION_NAMING_SKILLS)
    def test_skill_invokes_session_naming(self, skill: str) -> None:
        md = (_SKILLS_DIR / skill / "SKILL.md").read_text()
        assert "denubis-plan-and-execute:exec-session-naming" in md, (
            f"{skill}/SKILL.md does not invoke exec-session-naming"
        )


# ---------------------------------------------------------------------------
# Review and context changes are evidence-bound, not mandatory transitions
# ---------------------------------------------------------------------------
class TestOptionalTransitions:
    def test_execution_makes_independent_review_conditional(self) -> None:
        md = (_SKILLS_DIR / "executing-an-implementation-plan" / "SKILL.md").read_text()
        assert "Review is useful when required by the plan or project" in md
        assert "It is not a fixed transition ritual" in md

    def test_debugging_does_not_force_context_clear(self) -> None:
        md = (_SKILLS_DIR / "systematic-debugging" / "SKILL.md").read_text()
        assert "/clear" not in md
        assert "Do not force a fresh context" in md
