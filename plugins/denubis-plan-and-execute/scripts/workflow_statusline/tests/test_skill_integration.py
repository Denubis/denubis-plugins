"""Static integration tests verifying SKILL.md files contain expected strings."""

from __future__ import annotations

from pathlib import Path

import pytest

_SKILLS_DIR = Path(__file__).resolve().parents[3] / "skills"


# ---------------------------------------------------------------------------
# AC6.1 — Each of 4 target skills invokes session-naming
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
        assert "denubis-plan-and-execute:session-naming" in md, (
            f"{skill}/SKILL.md does not invoke session-naming"
        )


# ---------------------------------------------------------------------------
# AC7.1 / AC7.2 — Implementation skills invoke critical-peer-review
# ---------------------------------------------------------------------------
class TestCriticalPeerReviewInvocation:
    def test_starting_implementation_invokes_critical_peer_review(self) -> None:
        md = (_SKILLS_DIR / "starting-an-implementation-plan" / "SKILL.md").read_text()
        assert "denubis-plan-and-execute:critical-peer-review" in md

    def test_executing_implementation_invokes_critical_peer_review(self) -> None:
        md = (_SKILLS_DIR / "executing-an-implementation-plan" / "SKILL.md").read_text()
        assert "denubis-plan-and-execute:critical-peer-review" in md


# ---------------------------------------------------------------------------
# AC8.1 / AC8.2 — systematic-debugging has context clear with copy-then-clear
# ---------------------------------------------------------------------------
class TestContextClearPattern:
    @pytest.fixture
    def debugging_md(self) -> str:
        return (_SKILLS_DIR / "systematic-debugging" / "SKILL.md").read_text()

    def test_contains_clear_command(self, debugging_md: str) -> None:
        """AC8.1: systematic-debugging has a section containing /clear."""
        assert "/clear" in debugging_md

    def test_copy_before_clear(self, debugging_md: str) -> None:
        """AC8.2: 'copy' or 'Copy' appears before the first /clear."""
        clear_idx = debugging_md.index("/clear")
        preceding = debugging_md[:clear_idx].lower()
        assert "copy" in preceding, (
            "Expected 'copy'/'Copy' to appear before /clear in systematic-debugging"
        )
