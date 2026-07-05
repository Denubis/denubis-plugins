"""Tests for __main__.main() output composition."""

from __future__ import annotations

import io
import json
import os
import re
import sys
from unittest import mock

from workflow_statusline.__main__ import main
from workflow_statusline.colours import BOLD, CYAN, RED
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
        mock.patch("workflow_statusline.__main__.git_location", return_value=location),
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
        assert visible.startswith("testrepo"), (
            f"Expected location start, got: {visible!r}"
        )
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
        assert "+156/-23" not in visible, (
            f"churn should be hidden when agent present: {visible!r}"
        )
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
        assert visible.startswith("myrepo"), (
            f"Expected location start, got: {visible!r}"
        )
        assert "\u2717MAIN" in visible, (
            f"Expected ✗MAIN after location, got: {visible!r}"
        )

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
        assert "agt:" not in visible, (
            f"agt: should not appear without agent: {visible!r}"
        )


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
# New forecaster: ETA clock-time and DayStop appear with sufficient samples
# ---------------------------------------------------------------------------
class TestLine2PaceDisplay:
    @staticmethod
    def _local_ts(
        year: int, month: int, day: int, hour: int = 0, minute: int = 0
    ) -> float:
        import datetime as _dt

        return _dt.datetime(year, month, day, hour, minute).timestamp()

    def test_pace_displayed_for_seven_day_under_pace(self) -> None:
        """7d window under pace — green, shows `used% / pace%`.

        Window aligned to the active-hours grid so the pace is deterministic
        regardless of local timezone: start at 07:00 local on day 1, now at
        07:00 local on day 2 = exactly 15 active-hours elapsed of 105 active
        hours total = 14%.
        """
        window_start = self._local_ts(2026, 4, 11, 7, 0)
        now_ts = self._local_ts(2026, 4, 12, 7, 0)  # +1 day
        seven_day_resets = window_start + 7 * 86400
        payload = _base_payload(
            rate_limits={
                "seven_day": {"used_percentage": 10, "resets_at": seven_day_resets},
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
            mock_time.time.return_value = now_ts
            mock_cache.rate_cache_path.side_effect = lambda k: f"/tmp/t-{k}"
            main()
        line2 = _strip_ansi(buf.getvalue().splitlines()[1])
        # 1 day (15 active h) / 7 days (105 active h) = 14.3% → rounds to 14%
        assert "7d:10% < 14%" in line2, f"expected proportional display: {line2!r}"

    def test_pace_over_is_red(self) -> None:
        """Used > pace → cell rendered with RED colour code."""
        window_start = self._local_ts(2026, 4, 11, 7, 0)
        now_ts = self._local_ts(2026, 4, 12, 7, 0)  # pace = 14%
        seven_day_resets = window_start + 7 * 86400
        payload = _base_payload(
            rate_limits={
                "seven_day": {"used_percentage": 80, "resets_at": seven_day_resets},
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
            mock_time.time.return_value = now_ts
            mock_cache.rate_cache_path.side_effect = lambda k: f"/tmp/t-{k}"
            main()
        line2 = buf.getvalue().splitlines()[1]
        # 1 day elapsed → pace ≈ 14%. Must contain RED before "7d:".
        assert RED + "7d:80% \u226e 14%" in line2, (
            f"expected RED colour before cell: {line2!r}"
        )


class TestLine2ForecastCells:
    """Tests for DayStop / WeekStop cells driven by Theil-Sen slope."""

    @staticmethod
    def _local_ts(
        year: int, month: int, day: int, hour: int = 0, minute: int = 0
    ) -> float:
        import datetime as _dt

        return _dt.datetime(year, month, day, hour, minute).timestamp()

    def _run(
        self, now_ts: float, payload: dict, samples: list[tuple[float, float]]
    ) -> str:
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
            mock_time.time.return_value = now_ts
            mock_cache.rate_cache_path.side_effect = lambda k: f"/tmp/t-{k}"
            mock_cache.read_rate_samples.return_value = samples
            main()
        return _strip_ansi(buf.getvalue().splitlines()[1])

    def test_no_forecast_when_insufficient_samples(self) -> None:
        now = self._local_ts(2026, 4, 18, 12, 0)
        resets = now + 6 * 86400
        payload = _base_payload(
            rate_limits={"seven_day": {"used_percentage": 20, "resets_at": resets}},
        )
        # Only 5 samples — below min threshold of 30
        samples = [(now - (5 - i) * 30, 20.0) for i in range(5)]
        line2 = self._run(now, payload, samples)
        assert "DayStop" not in line2
        assert "WeekStop" not in line2

    def test_no_forecast_when_span_too_short(self) -> None:
        """Enough sample count but samples cover less than the minimum span."""
        now = self._local_ts(2026, 4, 18, 12, 0)
        resets = now + 6 * 86400
        payload = _base_payload(
            rate_limits={"seven_day": {"used_percentage": 40, "resets_at": resets}},
        )
        # 60 samples compressed into 15 min (not the 30-min+ you'd normally get
        # at 30s cadence — simulate rapid-fire statusline invocations). Span
        # of 15min is well below the 2h gate.
        samples = [(now - (60 - i) * 15.0, 10.0 + i * 0.5) for i in range(60)]
        line2 = self._run(now, payload, samples)
        assert "DayStop" not in line2
        assert "WeekStop" not in line2

    def test_weekstop_appears_when_on_track_to_exhaust(self) -> None:
        now = self._local_ts(2026, 4, 18, 12, 0)
        resets = now + 3 * 86400  # 3 days to reset
        # 120 samples spanning 4h (> 2h min span), climbing 10 -> 70.
        samples = [(now - (120 - i) * 120.0, 10.0 + i * 0.5) for i in range(120)]
        payload = _base_payload(
            rate_limits={"seven_day": {"used_percentage": 40, "resets_at": resets}},
        )
        line2 = self._run(now, payload, samples)
        assert "WeekStop:" in line2, f"expected WeekStop cell: {line2!r}"

    def test_daystop_go_to_sleep_when_already_past_target(self) -> None:
        # On day 1 of 7d window: target at 22:00 today = 1 full day active hours
        # = 15/105 ≈ 14.3%. Use 50% → clearly past.
        now = self._local_ts(2026, 4, 18, 9, 0)
        window_start = self._local_ts(2026, 4, 18, 8, 0)  # started 1 hour ago
        resets = window_start + 7 * 86400
        # 100 samples spanning 2.5h so min-span gate passes
        samples = [(now - (100 - i) * 90.0, 48.0 + i * 0.05) for i in range(100)]
        payload = _base_payload(
            rate_limits={"seven_day": {"used_percentage": 50, "resets_at": resets}},
        )
        line2 = self._run(now, payload, samples)
        assert "DayStop:go to sleep!" in line2, f"expected go-to-sleep: {line2!r}"

    def test_no_weekstop_when_reset_beats_exhaustion(self) -> None:
        # Slow burn, plenty of time left in window
        now = self._local_ts(2026, 4, 18, 12, 0)
        resets = now + 3600  # resets in 1 hour
        # Very slow burn: 10% over 1h = 0.00278 pct/s.
        # 90% to go → 32400s = 9h to exhaust. Reset comes first → no WeekStop.
        samples = [(now - (60 - i) * 60.0, 10.0 + i * (10.0 / 60.0)) for i in range(60)]
        payload = _base_payload(
            rate_limits={"seven_day": {"used_percentage": 20, "resets_at": resets}},
        )
        line2 = self._run(now, payload, samples)
        assert "WeekStop:" not in line2, f"WeekStop should be suppressed: {line2!r}"


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
            mock.patch.dict(
                os.environ,
                {"TMUX": "/tmp/tmux-1000/default,12345,0", "TMUX_PANE": "%42"},
            ),
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
