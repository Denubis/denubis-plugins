"""Session naming should be a direct terminal side effect, not an agent workflow."""

from pathlib import Path


SKILL = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-plan-and-execute"
    / "skills"
    / "exec-session-naming"
    / "SKILL.md"
)


def test_session_naming_is_direct_deterministic_and_verified() -> None:
    text = " ".join(SKILL.read_text(encoding="utf-8").split())

    for scar in {
        "Announce at start",
        "subagent",
        "max_turns",
        "24-hour",
        "Haiku",
        "Sonnet",
    }:
        assert scar not in text
    assert "Derive the name directly from the current task" in text
    assert 'tmux rename-window -t "$TMUX_PANE"' in text
    assert 'tmux display-message -p -t "$TMUX_PANE"' in text
    assert "If `TMUX_PANE` is absent" in text
    assert "Do not create a cache" in text
