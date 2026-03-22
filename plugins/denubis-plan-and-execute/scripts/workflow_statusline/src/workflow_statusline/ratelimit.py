"""Rate limit burn rate projection."""

from __future__ import annotations

from typing import NamedTuple


class RateLimitDisplay(NamedTuple):
    label: str          # "5h" or "7d"
    pct: int            # current percentage (rounded)
    time_str: str       # e.g., "~1h12m" or "~18m!"
    is_exhausting: bool  # True if projected to exhaust before reset


def _format_duration(seconds: float, exhausting: bool) -> str:
    """Format seconds as ~Xd, ~XhYm, or ~Xm. Append ! if exhausting."""
    seconds = max(seconds, 60.0)  # minimum 1m
    suffix = "!" if exhausting else ""

    if seconds >= 86400:
        days = round(seconds / 86400)
        return f"~{days}d{suffix}"
    elif seconds >= 3600:
        hours = int(seconds // 3600)
        minutes = round((seconds % 3600) / 60)
        return f"~{hours}h{minutes}m{suffix}"
    else:
        minutes = round(seconds / 60)
        minutes = max(minutes, 1)
        return f"~{minutes}m{suffix}"


def linear_regression_slope(samples: list[tuple[float, float]]) -> float | None:
    """Simple least-squares slope of (timestamp, pct) pairs.

    Returns pct/second. None if < 2 points or denominator is zero.
    """
    n = len(samples)
    if n < 2:
        return None

    sum_x = sum(s[0] for s in samples)
    sum_y = sum(s[1] for s in samples)
    sum_xy = sum(s[0] * s[1] for s in samples)
    sum_x2 = sum(s[0] * s[0] for s in samples)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0.0:
        return None

    return (n * sum_xy - sum_x * sum_y) / denom


def format_rate_limit(
    label: str,
    used_pct: float,
    resets_at: float,
    samples: list[tuple[float, float]],
    now: float,
) -> RateLimitDisplay:
    """Format a single rate limit window for display."""
    pct = round(used_pct)

    # Need at least 2 samples for any projection
    if len(samples) < 2:
        return RateLimitDisplay(
            label=label, pct=pct, time_str="", is_exhausting=False
        )

    slope = linear_regression_slope(samples)

    if slope is not None and slope > 0:
        time_to_exhaustion = (100.0 - used_pct) / slope
        time_to_reset = resets_at - now

        if time_to_exhaustion < time_to_reset:
            return RateLimitDisplay(
                label=label,
                pct=pct,
                time_str=_format_duration(time_to_exhaustion, exhausting=True),
                is_exhausting=True,
            )
        else:
            if time_to_reset > 0:
                return RateLimitDisplay(
                    label=label,
                    pct=pct,
                    time_str=_format_duration(time_to_reset, exhausting=False),
                    is_exhausting=False,
                )
            else:
                return RateLimitDisplay(
                    label=label, pct=pct, time_str="", is_exhausting=False
                )
    else:
        # slope is None or <= 0 → sustainable
        if resets_at > now:
            return RateLimitDisplay(
                label=label,
                pct=pct,
                time_str=_format_duration(resets_at - now, exhausting=False),
                is_exhausting=False,
            )
        else:
            return RateLimitDisplay(
                label=label, pct=pct, time_str="", is_exhausting=False
            )
