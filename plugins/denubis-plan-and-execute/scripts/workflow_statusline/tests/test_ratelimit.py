"""Tests for rate limit burn rate projection."""

from __future__ import annotations

import datetime

from workflow_statusline.ratelimit import (
    active_seconds_in_range,
    active_time_rate,
    blended_rate,
    day_stop_target,
    elapsed_active_fraction,
    elapsed_fraction,
    eta_to_pct,
    filter_by_lookback,
    format_clock_time,
    is_fast_burn,
    linear_regression_slope,
    next_active_end,
    theil_sen_slope,
)


class TestTheilSenSlope:
    def test_empty_samples_returns_none(self) -> None:
        assert theil_sen_slope([]) is None

    def test_single_sample_returns_none(self) -> None:
        assert theil_sen_slope([(100.0, 42.0)]) is None

    def test_all_duplicate_timestamps_returns_none(self) -> None:
        # All pairs have dt=0, so no slopes computable
        assert theil_sen_slope([(100.0, 1.0), (100.0, 2.0)]) is None

    def test_linear_monotonic(self) -> None:
        # y = 2x → slope 2
        samples = [(0.0, 0.0), (1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]
        slope = theil_sen_slope(samples)
        assert slope is not None
        assert abs(slope - 2.0) < 1e-9

    def test_robust_to_single_outlier(self) -> None:
        # Steady y = x, with one big spike
        samples = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 99.0), (4.0, 4.0), (5.0, 5.0)]
        slope = theil_sen_slope(samples)
        assert slope is not None
        # True slope is 1.0; median should reject the spike
        assert abs(slope - 1.0) < 0.5  # robust but allow slight shift

    def test_robust_to_sawtooth_drops(self) -> None:
        """Sliding-window-counter shape: slow climb punctuated by drops.

        Theil-Sen median of pairwise slopes should recover the underlying
        upward trend despite periodic negative segments.
        """
        # Construct climbs of +1 per unit time with a -5 drop every 10 units.
        # Overall trend: start at 0, end at (say) 50 after 100 units → avg slope 0.5
        samples = []
        val = 0.0
        for t in range(0, 101):
            if t > 0 and t % 10 == 0:
                val -= 5.0  # reset drop
            else:
                val += 1.0  # climb
            samples.append((float(t), val))
        slope = theil_sen_slope(samples)
        assert slope is not None
        assert slope > 0, "Should recover positive trend despite drops"
        # Expected net slope ≈ (final - initial)/span ≈ 0.5
        assert 0.3 < slope < 0.8

    def test_flat_overnight_samples_pull_slope_toward_daytime_average(self) -> None:
        """If half the samples are flat (overnight) and half climb, the slope
        reflects the 24h-average rate, not the daytime-only rate.

        This is the semantic we want: the slope is used directly as
        pct-per-clock-second for clock-time ETA extrapolation.
        """
        # 10 samples daytime climbing 0→10 over 10 units, then 10 flat at 10
        samples = [(float(t), float(t)) for t in range(11)]
        samples += [(float(11 + t), 10.0) for t in range(10)]
        slope = theil_sen_slope(samples)
        assert slope is not None
        # Slope should be less than the daytime-only 1.0 (there's dilution from flats)
        # and more than 0 (real burn exists)
        assert 0 < slope < 1.0

    def test_cap_argument_subsamples_large_inputs(self) -> None:
        # Provide 1000 samples but request max_pairs via a cap=100
        samples = [(float(t), float(t)) for t in range(1000)]
        slope = theil_sen_slope(samples, cap=100)
        assert slope is not None
        # Trend is 1.0 pct/unit regardless of subsampling
        assert abs(slope - 1.0) < 0.05


def _ts(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> float:
    import datetime as _dt
    return _dt.datetime(year, month, day, hour, minute).timestamp()


class TestNextActiveEnd:
    def test_midday_returns_today_end(self) -> None:
        # noon local → next active end is today at 22:00
        now = _ts(2026, 4, 18, 12, 0)
        expected = _ts(2026, 4, 18, 22, 0)
        assert next_active_end(now, active_end_hour=22) == expected

    def test_already_past_end_returns_tomorrow(self) -> None:
        # 23:00 → next active end is tomorrow at 22:00
        now = _ts(2026, 4, 18, 23, 0)
        expected = _ts(2026, 4, 19, 22, 0)
        assert next_active_end(now, active_end_hour=22) == expected

    def test_exact_boundary_rolls_forward(self) -> None:
        # At 22:00 exactly, "end of today" is already reached → roll to tomorrow
        now = _ts(2026, 4, 18, 22, 0)
        expected = _ts(2026, 4, 19, 22, 0)
        assert next_active_end(now, active_end_hour=22) == expected

    def test_early_morning_returns_today_end(self) -> None:
        # 03:00 → today's 22:00 is still in the future
        now = _ts(2026, 4, 18, 3, 0)
        expected = _ts(2026, 4, 18, 22, 0)
        assert next_active_end(now, active_end_hour=22) == expected


def _ts(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> float:
    """Local-time epoch helper for active-hours tests."""
    return datetime.datetime(year, month, day, hour, minute).timestamp()


class TestActiveSecondsInRange:
    def test_full_active_day(self) -> None:
        # 7am to 10pm on one day = 15h
        start = _ts(2026, 4, 18, 7, 0)
        end = _ts(2026, 4, 18, 22, 0)
        assert active_seconds_in_range(start, end) == 15 * 3600

    def test_midnight_to_midnight_spans_one_active_block(self) -> None:
        # 00:00 to 24:00 same day = 15h active
        start = _ts(2026, 4, 18, 0, 0)
        end = _ts(2026, 4, 19, 0, 0)
        assert active_seconds_in_range(start, end) == 15 * 3600

    def test_range_entirely_inside_inactive_hours(self) -> None:
        # 23:00 to 06:00 = all inactive
        start = _ts(2026, 4, 18, 23, 0)
        end = _ts(2026, 4, 19, 6, 0)
        assert active_seconds_in_range(start, end) == 0

    def test_spans_partial_active_at_each_end(self) -> None:
        # 2pm to 8am next day = 8h (2pm-10pm) + 1h (7am-8am) = 9h
        start = _ts(2026, 4, 18, 14, 0)
        end = _ts(2026, 4, 19, 8, 0)
        assert active_seconds_in_range(start, end) == 9 * 3600

    def test_seven_days_exact(self) -> None:
        # 7 × 15h = 105h
        start = _ts(2026, 4, 11, 7, 0)
        end = _ts(2026, 4, 18, 7, 0)
        assert active_seconds_in_range(start, end) == 7 * 15 * 3600

    def test_custom_active_hours(self) -> None:
        # 9am-5pm = 8h per day
        start = _ts(2026, 4, 18, 0, 0)
        end = _ts(2026, 4, 19, 0, 0)
        assert active_seconds_in_range(
            start, end, active_start_hour=9, active_end_hour=17
        ) == 8 * 3600


class TestElapsedActiveFraction:
    def test_zero_at_window_start(self) -> None:
        start = _ts(2026, 4, 11, 14, 0)
        window_length = 7 * 86400.0
        resets_at = start + window_length
        assert elapsed_active_fraction(now=start, resets_at=resets_at, window_length=window_length) == 0.0

    def test_one_at_window_end(self) -> None:
        start = _ts(2026, 4, 11, 14, 0)
        window_length = 7 * 86400.0
        resets_at = start + window_length
        assert elapsed_active_fraction(now=resets_at, resets_at=resets_at, window_length=window_length) == 1.0

    def test_midnight_does_not_advance_pace(self) -> None:
        """From 10pm to 7am next day, pace stays flat (no active seconds elapse)."""
        start = _ts(2026, 4, 11, 14, 0)  # window start 2pm
        window_length = 7 * 86400.0
        resets_at = start + window_length

        # Compare pace at 10pm day 0 vs 7am day 1 — both should equal the same fraction.
        frac_at_22 = elapsed_active_fraction(
            now=_ts(2026, 4, 11, 22, 0), resets_at=resets_at, window_length=window_length,
        )
        frac_at_7_next = elapsed_active_fraction(
            now=_ts(2026, 4, 12, 7, 0), resets_at=resets_at, window_length=window_length,
        )
        assert frac_at_22 == frac_at_7_next

    def test_during_day_advances_smoothly(self) -> None:
        """1 hour of activity during daytime increments pace by 1/105 of the week."""
        start = _ts(2026, 4, 11, 7, 0)  # window start at 7am so first day is clean 15h
        window_length = 7 * 86400.0
        resets_at = start + window_length

        frac_at_8am = elapsed_active_fraction(
            now=_ts(2026, 4, 11, 8, 0), resets_at=resets_at, window_length=window_length,
        )
        # 1 hour of active time out of 7 × 15 = 105
        assert abs(frac_at_8am - 1.0 / 105.0) < 1e-9


class TestElapsedFraction:
    def test_start_of_window(self) -> None:
        assert elapsed_fraction(now=0.0, resets_at=3600.0, window_length=3600.0) == 0.0

    def test_halfway_through_window(self) -> None:
        assert elapsed_fraction(now=1800.0, resets_at=3600.0, window_length=3600.0) == 0.5

    def test_end_of_window(self) -> None:
        assert elapsed_fraction(now=3600.0, resets_at=3600.0, window_length=3600.0) == 1.0

    def test_clamped_below_zero(self) -> None:
        # now is before window_start — clamp to 0
        assert elapsed_fraction(now=-100.0, resets_at=3600.0, window_length=3600.0) == 0.0

    def test_clamped_above_one(self) -> None:
        # now is past resets_at — clamp to 1
        assert elapsed_fraction(now=7200.0, resets_at=3600.0, window_length=3600.0) == 1.0

    def test_seven_day_window_quarter(self) -> None:
        # 7d window, 1.75 days elapsed out of 7 → 0.25
        frac = elapsed_fraction(
            now=1.75 * 86400,
            resets_at=7 * 86400.0,
            window_length=7 * 86400.0,
        )
        assert abs(frac - 0.25) < 1e-9


# ---------------------------------------------------------------------------
# linear_regression_slope — retained for compatibility / tests
# ---------------------------------------------------------------------------
class TestLinearRegressionSlope:
    def test_returns_none_for_empty(self) -> None:
        assert linear_regression_slope([]) is None

    def test_returns_none_for_single_point(self) -> None:
        assert linear_regression_slope([(100.0, 50.0)]) is None

    def test_known_slope(self) -> None:
        samples = [(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]
        slope = linear_regression_slope(samples)
        assert slope is not None
        assert abs(slope - 2.0) < 1e-9


# ---------------------------------------------------------------------------
# filter_by_lookback
# ---------------------------------------------------------------------------
class TestFilterByLookback:
    def test_keeps_samples_within_lookback(self) -> None:
        samples = [(100.0, 1.0), (200.0, 2.0), (300.0, 3.0)]
        # now=300, lookback=150 → keep samples with ts >= 150
        assert filter_by_lookback(samples, now=300.0, lookback=150.0) == [
            (200.0, 2.0),
            (300.0, 3.0),
        ]

    def test_drops_all_when_lookback_too_short(self) -> None:
        samples = [(100.0, 1.0), (200.0, 2.0)]
        assert filter_by_lookback(samples, now=1000.0, lookback=10.0) == []

    def test_empty_input_returns_empty(self) -> None:
        assert filter_by_lookback([], now=100.0, lookback=50.0) == []


# ---------------------------------------------------------------------------
# active_time_rate — idle-trimmed burn rate
# ---------------------------------------------------------------------------
class TestActiveTimeRate:
    def test_zero_or_one_sample_returns_none(self) -> None:
        assert active_time_rate([]) is None
        assert active_time_rate([(100.0, 50.0)]) is None

    def test_steady_active_burn(self) -> None:
        # 10%/60s increments = 1/6 %/s
        samples = [(0.0, 10.0), (60.0, 20.0), (120.0, 30.0)]
        rate = active_time_rate(samples)
        assert rate is not None
        assert abs(rate - (10.0 / 60.0)) < 1e-9

    def test_idle_interval_excluded(self) -> None:
        # 10→20 over 60s (active), then 20→20 over 3600s (idle), then 20→30 over 60s (active)
        # Expected rate = (10 + 10) / (60 + 60) = 20/120 = 1/6 %/s
        # Without idle trimming it would be 20/3720 ≈ 0.0054 %/s
        samples = [
            (0.0, 10.0),
            (60.0, 20.0),
            (3660.0, 20.0),
            (3720.0, 30.0),
        ]
        rate = active_time_rate(samples)
        assert rate is not None
        assert abs(rate - (20.0 / 120.0)) < 1e-9

    def test_all_idle_returns_none(self) -> None:
        samples = [(0.0, 50.0), (60.0, 50.0), (120.0, 50.0)]
        assert active_time_rate(samples) is None


# ---------------------------------------------------------------------------
# blended_rate
# ---------------------------------------------------------------------------
class TestBlendedRate:
    def test_returns_none_when_insufficient_data(self) -> None:
        assert blended_rate([], now=100.0, short_lookback=60.0, long_lookback=3600.0) is None

    def test_blends_short_and_long(self) -> None:
        # Samples spanning enough time for both windows.
        # Short window (last 60s): burn 10%/60s = 1/6 %/s.
        # Long window (last 1200s): uniform 20% over 1200s = 1/60 %/s.
        samples = [
            (0.0, 0.0),
            (600.0, 10.0),
            (1140.0, 10.0),    # idle interval inside long window
            (1200.0, 20.0),    # inside short window (last 60s)
        ]
        rate = blended_rate(samples, now=1200.0, short_lookback=60.0, long_lookback=1200.0)
        assert rate is not None
        # Short rate: only the last interval (1140→1200, 10→20) = 1/6 %/s
        # Long rate (idle-trimmed): burn 20 / active 660 = 1/33 %/s
        # Blend: 0.3 × 1/6 + 0.7 × 1/33
        expected = 0.3 * (1.0 / 6.0) + 0.7 * (10.0 / 330.0)
        assert abs(rate - expected) < 1e-9

    def test_falls_back_to_long_when_short_empty(self) -> None:
        samples = [(0.0, 0.0), (600.0, 10.0), (1200.0, 20.0)]
        # Short lookback 30s — no samples inside (last sample at 1200, two within 30s required).
        rate = blended_rate(samples, now=1260.0, short_lookback=30.0, long_lookback=1300.0)
        assert rate is not None
        # Only long rate available: 20 / 1200 = 1/60 %/s
        assert abs(rate - (20.0 / 1200.0)) < 1e-9


# ---------------------------------------------------------------------------
# eta_to_pct
# ---------------------------------------------------------------------------
class TestEtaToPct:
    def test_returns_now_when_already_past_target(self) -> None:
        assert eta_to_pct(used_pct=60.0, target_pct=50.0, rate=0.1, now=1000.0) == 1000.0

    def test_none_when_rate_is_none(self) -> None:
        assert eta_to_pct(used_pct=10.0, target_pct=100.0, rate=None, now=1000.0) is None

    def test_none_when_rate_zero_or_negative(self) -> None:
        assert eta_to_pct(used_pct=10.0, target_pct=100.0, rate=0.0, now=1000.0) is None
        assert eta_to_pct(used_pct=10.0, target_pct=100.0, rate=-0.5, now=1000.0) is None

    def test_projects_clock_time(self) -> None:
        # 50% to go, rate 0.1 %/s → 500s from now
        assert eta_to_pct(used_pct=50.0, target_pct=100.0, rate=0.1, now=1000.0) == 1500.0


# ---------------------------------------------------------------------------
# day_stop_target
# ---------------------------------------------------------------------------
class TestDayStopTarget:
    WINDOW_7D = 7 * 86400

    def test_middle_of_day_3(self) -> None:
        # Window resets at t=7d. Now = 2.5 days in → we're inside day 3 (1-indexed).
        # Target for end of day 3 = 3/7 × 100 ≈ 42.857%.
        resets_at = 7 * 86400.0
        now = 2.5 * 86400.0
        day_num, target = day_stop_target(now=now, resets_at=resets_at, window_length=self.WINDOW_7D)
        assert day_num == 3
        assert abs(target - (3.0 / 7.0 * 100.0)) < 1e-9

    def test_start_of_day_1(self) -> None:
        resets_at = 7 * 86400.0
        now = 0.0
        day_num, target = day_stop_target(now=now, resets_at=resets_at, window_length=self.WINDOW_7D)
        assert day_num == 1
        assert abs(target - (1.0 / 7.0 * 100.0)) < 1e-9

    def test_last_day_caps_at_seven(self) -> None:
        resets_at = 7 * 86400.0
        # 6.5 days in → inside day 7.
        now = 6.5 * 86400.0
        day_num, target = day_stop_target(now=now, resets_at=resets_at, window_length=self.WINDOW_7D)
        assert day_num == 7
        assert abs(target - 100.0) < 1e-9


# ---------------------------------------------------------------------------
# is_fast_burn — SRE multi-window gate
# ---------------------------------------------------------------------------
class TestIsFastBurn:
    def test_false_when_insufficient_data(self) -> None:
        assert not is_fast_burn(
            samples=[],
            now=1000.0,
            short_lookback=60.0,
            long_lookback=3600.0,
            used_pct=50.0,
            resets_at=2000.0,
        )

    def test_true_when_both_windows_project_before_reset(self) -> None:
        # Heavy burn: 50% over 300s in both short and long window.
        samples = [(0.0, 0.0), (300.0, 50.0)]
        # used=50, remaining=50. Rate=50/300=1/6 %/s.
        # Time to exhaust = 50/(1/6) = 300s.
        # Reset = 3600s from now → exhaustion (300s) < reset (3600s) → fast burn.
        assert is_fast_burn(
            samples=samples,
            now=300.0,
            short_lookback=300.0,
            long_lookback=300.0,
            used_pct=50.0,
            resets_at=300.0 + 3600.0,
        )

    def test_false_when_reset_beats_exhaustion(self) -> None:
        # Very slow burn: 5% over 3000s.
        samples = [(0.0, 0.0), (3000.0, 5.0)]
        # Rate = 5/3000 = 1/600 %/s → time to exhaust = 95 * 600 = 57000s.
        # Reset in 60s → reset wins.
        assert not is_fast_burn(
            samples=samples,
            now=3000.0,
            short_lookback=3000.0,
            long_lookback=3000.0,
            used_pct=5.0,
            resets_at=3000.0 + 60.0,
        )


# ---------------------------------------------------------------------------
# format_clock_time
# ---------------------------------------------------------------------------
class TestFormatClockTime:
    def test_none_returns_empty(self) -> None:
        assert format_clock_time(None, now=0.0) == ""

    def test_same_day_shows_time_only(self) -> None:
        # Epoch 1700000000 = 2023-11-14 22:13:20 UTC. Don't assume TZ in the test —
        # just test that same-day output has no weekday prefix.
        import time as _time

        now = _time.time()
        later = now + 60 * 60  # 1h from now
        result = format_clock_time(later, now=now)
        # Either the hour or ":00" should appear, and no weekday prefix
        assert not any(day in result for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        assert result  # non-empty

    def test_other_day_includes_weekday(self) -> None:
        import time as _time

        now = _time.time()
        three_days = now + 3 * 86400
        result = format_clock_time(three_days, now=now)
        assert any(day in result for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
