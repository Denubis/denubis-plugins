"""Tests for rate limit burn rate projection."""

from __future__ import annotations

from workflow_statusline.ratelimit import (
    RateLimitDisplay,
    format_rate_limit,
    linear_regression_slope,
)


# ---------------------------------------------------------------------------
# linear_regression_slope — direct tests
# ---------------------------------------------------------------------------
class TestLinearRegressionSlope:
    def test_returns_none_for_empty(self) -> None:
        assert linear_regression_slope([]) is None

    def test_returns_none_for_single_point(self) -> None:
        assert linear_regression_slope([(100.0, 50.0)]) is None

    def test_known_slope(self) -> None:
        # y = 2x + 0 → slope should be 2.0
        samples = [(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]
        slope = linear_regression_slope(samples)
        assert slope is not None
        assert abs(slope - 2.0) < 1e-9

    def test_negative_slope(self) -> None:
        # y = -1x + 10 → slope should be -1.0
        samples = [(0.0, 10.0), (5.0, 5.0), (10.0, 0.0)]
        slope = linear_regression_slope(samples)
        assert slope is not None
        assert abs(slope - (-1.0)) < 1e-9

    def test_zero_denominator_returns_none(self) -> None:
        # All x values the same → denominator is zero
        samples = [(5.0, 10.0), (5.0, 20.0)]
        assert linear_regression_slope(samples) is None


# ---------------------------------------------------------------------------
# AC3.5 — 0 or 1 samples → time_str=""
# ---------------------------------------------------------------------------
class TestNoSamples:
    def test_zero_samples(self) -> None:
        result = format_rate_limit("5h", 30.0, 1000.0, [], now=500.0)
        assert result.time_str == ""
        assert result.is_exhausting is False

    def test_one_sample(self) -> None:
        result = format_rate_limit("5h", 30.0, 1000.0, [(500.0, 30.0)], now=500.0)
        assert result.time_str == ""
        assert result.is_exhausting is False


# ---------------------------------------------------------------------------
# AC3.2 — steady burn with 5 samples → non-empty time_str
# ---------------------------------------------------------------------------
class TestSteadyBurn:
    def test_five_samples_steady_burn(self) -> None:
        # 60s apart, pct going 10→20→30→40→50 → slope ~0.1667 pct/s
        # At pct=50, (100-50)/0.1667 ≈ 300s to exhaust
        # Reset in 600s → won't exhaust before reset → show reset time
        base_t = 1000.0
        samples = [
            (base_t, 10.0),
            (base_t + 60, 20.0),
            (base_t + 120, 30.0),
            (base_t + 180, 40.0),
            (base_t + 240, 50.0),
        ]
        now = base_t + 240
        resets_at = now + 600  # reset in 10 minutes

        result = format_rate_limit("5h", 50.0, resets_at, samples, now=now)
        assert isinstance(result, RateLimitDisplay)
        assert result.label == "5h"
        assert result.pct == 50
        assert result.time_str != ""
        # slope ~0.1667 pct/s, (100-50)/0.1667 ≈ 300s = 5m
        # 300s < 600s reset → exhausting!
        assert result.is_exhausting is True
        assert result.time_str.endswith("!")


# ---------------------------------------------------------------------------
# AC3.3 — fast burn exhausting before reset
# ---------------------------------------------------------------------------
class TestFastBurnExhaustion:
    def test_exhausts_before_reset(self) -> None:
        # High slope: 80% consumed in 4 samples over 60s
        # slope ≈ 1.0 pct/s, remaining = 10%, exhaustion in ~10s
        # Reset far in future (3600s)
        base_t = 5000.0
        samples = [
            (base_t, 10.0),
            (base_t + 20, 30.0),
            (base_t + 40, 50.0),
            (base_t + 60, 70.0),
        ]
        now = base_t + 80
        resets_at = now + 3600

        result = format_rate_limit("7d", 90.0, resets_at, samples, now=now)
        assert result.is_exhausting is True
        assert result.time_str.endswith("!")
        assert result.pct == 90


# ---------------------------------------------------------------------------
# Sustainable rate — won't exhaust before reset
# ---------------------------------------------------------------------------
class TestSustainableRate:
    def test_sustainable_shows_reset_time(self) -> None:
        # Slow slope: 5% over 300s = 0.0167 pct/s
        # At 20%, (100-20)/0.0167 ≈ 4800s to exhaust
        # Reset in 120s → reset comes first → sustainable
        base_t = 2000.0
        samples = [
            (base_t, 15.0),
            (base_t + 150, 17.5),
            (base_t + 300, 20.0),
        ]
        now = base_t + 300
        resets_at = now + 120  # resets in 2 minutes

        result = format_rate_limit("5h", 20.0, resets_at, samples, now=now)
        assert result.is_exhausting is False
        assert result.time_str != ""
        assert not result.time_str.endswith("!")
        assert "2m" in result.time_str


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_slope_negative_shows_reset_time(self) -> None:
        # Usage going down → sustainable
        base_t = 1000.0
        samples = [(base_t, 50.0), (base_t + 60, 40.0)]
        now = base_t + 60
        resets_at = now + 300

        result = format_rate_limit("5h", 40.0, resets_at, samples, now=now)
        assert result.is_exhausting is False
        assert result.time_str != ""

    def test_reset_in_past(self) -> None:
        base_t = 1000.0
        samples = [(base_t, 50.0), (base_t + 60, 60.0)]
        now = base_t + 120
        resets_at = now - 10  # already past

        result = format_rate_limit("5h", 60.0, resets_at, samples, now=now)
        # Exhausting (slope > 0, but reset already passed)
        # time_to_reset is negative, time_to_exhaustion is positive
        # time_to_exhaustion < time_to_reset is false (positive < negative)
        # So falls to else: resets_at <= now → time_str=""
        assert result.time_str == ""

    def test_pct_rounded(self) -> None:
        result = format_rate_limit("5h", 33.7, 2000.0, [], now=1000.0)
        assert result.pct == 34

    def test_resets_at_past_with_negative_slope(self) -> None:
        samples = [(100.0, 50.0), (200.0, 40.0)]
        result = format_rate_limit("5h", 40.0, 150.0, samples, now=200.0)
        assert result.time_str == ""
        assert result.is_exhausting is False
