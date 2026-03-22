"""Tests for __main__.main() output composition."""

from __future__ import annotations

import io
import json
import os
import re
import sys
from unittest import mock

import pytest

from workflow_statusline.__main__ import main
from workflow_statusline.colours import BLUE, BOLD, CYAN, DIM, GREEN, RED, RST, YELLOW
from workflow_statusline.git import LocationInfo

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _run_main(
    payload: dict,
    *,
    location: LocationInfo | None = None,
    staged: int = 0,
    modified: int = 0,
) -> list[str]:
    """Run main() with mocked stdin/stdout/git and cache/time, return output lines."""
    if location is None:
        location = LocationInfo(display="testrepo", is_on_main=False, is_worktree=False)

    fake_stdin = io.StringIO(json.dumps(payload))
    buf = io.StringIO()
    with (
        mock.patch.object(sys, "stdin", fake_stdin),
        mock.patch.object(sys, "stdout", buf),
        mock.patch(
            "workflow_statusline.__main__.git_location", return_value=location
        ),
        mock.patch(
            "workflow_statusline.__main__.git_changes",
            return_value=(staged, modified),
        ),
        mock.patch("workflow_statusline.__main__.time") as mock_time,
        mock.patch("workflow_statusline.__main__.cache") as mock_cache,
    ):
        mock_time.time.return_value = 1000000.0
        mock_cache.read_rate_samples.return_value = []
        main()

    return buf.getvalue().splitlines()


def _base_payload(**overrides: object) -> dict:
    payload: dict = {
        "cwd": "/tmp/fake",
        "model": {"display_name": "opus"},
        "context_window": {
            "used_percentage": 40,
            "remaining_percentage": 60,
            "context_window_size": 1_000_000,
        },
        "cost": {"total_cost_usd": 1.23, "total_duration_ms": 60000},
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# AC1.1 — line 1 starts with location, NOT model prefix
# ---------------------------------------------------------------------------
class TestLine1NoModelPrefix:
    def test_line1_starts_with_location_not_model(self) -> None:
        lines = _run_main(_base_payload())
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert visible.startswith("testrepo"), f"Expected location start, got: {visible!r}"
        assert "[opus]" not in visible, "Model prefix should not appear in line 1"


# ---------------------------------------------------------------------------
# AC1.2 — staged/modified counts appear after location
# ---------------------------------------------------------------------------
class TestLine1GitCounts:
    def test_staged_and_modified_in_line1(self) -> None:
        lines = _run_main(_base_payload(), staged=2, modified=3)
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert "+2" in visible, f"staged count missing: {visible!r}"
        assert "~3" in visible, f"modified count missing: {visible!r}"
        # Counts should appear after location
        loc_end = visible.index("testrepo") + len("testrepo")
        plus_pos = visible.index("+2")
        tilde_pos = visible.index("~3")
        assert plus_pos > loc_end
        assert tilde_pos > loc_end


# ---------------------------------------------------------------------------
# AC1.3 — churn appears without agent; omitted with agent
# ---------------------------------------------------------------------------
class TestLine1Churn:
    def test_churn_appears_without_agent(self) -> None:
        payload = _base_payload()
        payload["cost"]["total_lines_added"] = 156
        payload["cost"]["total_lines_removed"] = 23
        lines = _run_main(payload)
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert "+156/-23" in visible, f"churn missing: {visible!r}"

    def test_churn_omitted_when_agent_present(self) -> None:
        payload = _base_payload(agent={"name": "reviewer"})
        payload["cost"]["total_lines_added"] = 156
        payload["cost"]["total_lines_removed"] = 23
        lines = _run_main(payload)
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert "+156/-23" not in visible, f"churn should be hidden when agent present: {visible!r}"
        assert "agt:reviewer" in visible


# ---------------------------------------------------------------------------
# AC1.4 — on main (not worktree) shows RED+BOLD ✗MAIN
# ---------------------------------------------------------------------------
class TestLine1MainWarning:
    def test_on_main_shows_warning(self) -> None:
        loc = LocationInfo(display="myrepo", is_on_main=True, is_worktree=False)
        lines = _run_main(_base_payload(), location=loc)
        line1 = lines[0]
        # Check ANSI codes
        assert RED in line1, "RED missing for MAIN warning"
        assert BOLD in line1, "BOLD missing for MAIN warning"
        visible = _strip_ansi(line1)
        assert visible.startswith("\u2717MAIN"), f"Expected ✗MAIN start, got: {visible!r}"

    def test_on_main_worktree_uses_display(self) -> None:
        """Worktree on main should NOT show ✗MAIN — uses display instead."""
        loc = LocationInfo(display="myrepo", is_on_main=True, is_worktree=True)
        lines = _run_main(_base_payload(), location=loc)
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert visible.startswith("myrepo"), f"Expected display name, got: {visible!r}"
        assert "\u2717MAIN" not in visible


# ---------------------------------------------------------------------------
# AC1.5 — agent name appears in line 1
# ---------------------------------------------------------------------------
class TestLine1AgentName:
    def test_agent_name_appears(self) -> None:
        payload = _base_payload(agent={"name": "reviewer"})
        lines = _run_main(payload)
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert "agt:reviewer" in visible, f"agent name missing: {visible!r}"
        # Check it uses CYAN
        assert CYAN in line1, "agent name should use CYAN"

    def test_agent_name_absent_when_not_set(self) -> None:
        lines = _run_main(_base_payload())
        line1 = lines[0]
        visible = _strip_ansi(line1)
        assert "agt:" not in visible, f"agt: should not appear without agent: {visible!r}"


# ---------------------------------------------------------------------------
# AC3.1 — rate limits appear in line 2 when present
# ---------------------------------------------------------------------------
class TestLine2RateLimits:
    def test_rate_limits_appear_in_line2(self) -> None:
        payload = _base_payload(
            session_id="test123",
            rate_limits={
                "five_hour": {"used_percentage": 23, "resets_at": 1000000.0 + 3600},
                "seven_day": {"used_percentage": 41, "resets_at": 1000000.0 + 86400},
            },
        )
        lines = _run_main(payload)
        line2 = _strip_ansi(lines[1])
        assert "5h:23%" in line2, f"5h rate limit missing: {line2!r}"
        assert "7d:41%" in line2, f"7d rate limit missing: {line2!r}"

    def test_rate_samples_appended_to_cache(self) -> None:
        """Verify append_rate_sample is called for each rate limit window."""
        payload = _base_payload(
            session_id="test123",
            rate_limits={
                "five_hour": {"used_percentage": 23, "resets_at": 1000000.0 + 3600},
                "seven_day": {"used_percentage": 41, "resets_at": 1000000.0 + 86400},
            },
        )
        fake_stdin = io.StringIO(json.dumps(payload))
        buf = io.StringIO()
        loc = LocationInfo(display="testrepo", is_on_main=False, is_worktree=False)
        with (
            mock.patch.object(sys, "stdin", fake_stdin),
            mock.patch.object(sys, "stdout", buf),
            mock.patch("workflow_statusline.__main__.git_location", return_value=loc),
            mock.patch("workflow_statusline.__main__.git_changes", return_value=(0, 0)),
            mock.patch("workflow_statusline.__main__.time") as mock_time,
            mock.patch("workflow_statusline.__main__.cache") as mock_cache,
        ):
            mock_time.time.return_value = 1000000.0
            mock_cache.read_rate_samples.return_value = []
            main()
            assert mock_cache.append_rate_sample.call_count == 2


# ---------------------------------------------------------------------------
# AC3.4 — no rate limits when key absent
# ---------------------------------------------------------------------------
class TestLine2NoRateLimits:
    def test_no_rate_text_without_rate_limits(self) -> None:
        payload = _base_payload()
        lines = _run_main(payload)
        line2 = _strip_ansi(lines[1])
        assert "5h:" not in line2, f"5h should not appear: {line2!r}"
        assert "7d:" not in line2, f"7d should not appear: {line2!r}"


# ---------------------------------------------------------------------------
# Tmux integration — maybe_rename called after render
# ---------------------------------------------------------------------------
class TestTmuxIntegration:
    def test_tmux_rename_called_with_location_display(self) -> None:
        """main() should call maybe_rename(location.display) after printing."""
        payload = _base_payload()
        loc = LocationInfo(display="testrepo", is_on_main=False, is_worktree=False)
        fake_stdin = io.StringIO(json.dumps(payload))
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "stdin", fake_stdin),
            mock.patch.object(sys, "stdout", buf),
            mock.patch("workflow_statusline.__main__.git_location", return_value=loc),
            mock.patch("workflow_statusline.__main__.git_changes", return_value=(0, 0)),
            mock.patch("workflow_statusline.__main__.time") as mock_time,
            mock.patch("workflow_statusline.__main__.cache") as mock_cache,
            mock.patch("workflow_statusline.tmux.subprocess") as mock_subprocess,
            mock.patch("workflow_statusline.tmux.cache") as mock_tmux_cache,
            mock.patch.dict(os.environ, {"TMUX": "/tmp/tmux-1000/default,12345,0", "TMUX_PANE": "%42"}),
        ):
            mock_time.time.return_value = 1000000.0
            mock_cache.read_rate_samples.return_value = []
            mock_tmux_cache.read_if_fresh.return_value = None
            main()

        mock_subprocess.run.assert_called_once_with(
            ["tmux", "rename-window", "Cl:testrepo"],
            check=False,
            capture_output=True,
        )
        mock_tmux_cache.write.assert_called_once()
