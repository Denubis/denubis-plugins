"""Rate-limit burn-rate forecasting.

Implements an idle-trimmed, multi-window blended-rate forecaster inspired by
the Google SRE multi-window multi-burn-rate alerting pattern. The core idea:

* Idle gaps (intervals where ``used_pct`` did not change) are excluded from
  the rate calculation — they are treated as missing data, not as zero-rate
  observations, so overnight silence does not drag the slope to flat.
* Rate is blended between a short window (recent behaviour) and a long
  window (baseline pace) to damp noise while remaining responsive.
* The "fast-burn" colour gate fires only when BOTH the short and long windows
  independently project exhaustion before reset — single bursts do not alone
  flip the signal red.
"""

from __future__ import annotations

import datetime
import time
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Active-hours pace — advance only during the configured working window
# ---------------------------------------------------------------------------
def active_seconds_in_range(
    start_ts: float,
    end_ts: float,
    active_start_hour: int = 7,
    active_end_hour: int = 22,
) -> float:
    """Return seconds between ``start_ts`` and ``end_ts`` that fall within
    ``[active_start_hour, active_end_hour)`` in local time.

    Walks day-by-day in local time; handles DST transitions via
    :func:`datetime.datetime.timestamp`. Returns 0 if the range is empty or
    inverted.
    """
    if end_ts <= start_ts:
        return 0.0

    start_dt = datetime.datetime.fromtimestamp(start_ts)
    end_dt = datetime.datetime.fromtimestamp(end_ts)

    total = 0.0
    day = start_dt.date()
    while day <= end_dt.date():
        day_active_start = datetime.datetime.combine(
            day, datetime.time(active_start_hour, 0, 0)
        )
        day_active_end = datetime.datetime.combine(
            day, datetime.time(active_end_hour, 0, 0)
        )
        overlap_start = max(day_active_start, start_dt)
        overlap_end = min(day_active_end, end_dt)
        if overlap_end > overlap_start:
            total += (overlap_end - overlap_start).total_seconds()
        day += datetime.timedelta(days=1)

    return total


def next_active_end(now: float, active_end_hour: int = 22) -> float:
    """Return the next clock time at which active hours end, as Unix seconds.

    If ``now`` is strictly before today's ``active_end_hour``, returns today's
    boundary. Otherwise returns tomorrow's.
    """
    dt = datetime.datetime.fromtimestamp(now)
    today_end = datetime.datetime.combine(
        dt.date(), datetime.time(active_end_hour, 0, 0)
    )
    if dt < today_end:
        return today_end.timestamp()
    return (today_end + datetime.timedelta(days=1)).timestamp()


def theil_sen_slope(
    samples: list[tuple[float, float]], cap: int = 500
) -> float | None:
    """Theil-Sen robust slope estimator: median of pairwise slopes.

    Returns slope in ``pct/second`` (units determined by the input).
    Returns ``None`` when fewer than 2 distinct-time samples are available.

    The sliding-window counter's periodic downward drops are a minority of
    pairwise slopes, so the median remains positive and reflects the net
    climb — no outlier-detection heuristic required.

    ``cap`` limits input size via deterministic even subsampling so the
    O(n^2) pair count stays bounded at ~``cap^2 / 2``.
    """
    if len(samples) < 2:
        return None

    # Subsample if over cap, preserving even stride.
    if len(samples) > cap:
        stride = len(samples) / cap
        indices = sorted({int(i * stride) for i in range(cap)})
        samples = [samples[i] for i in indices if i < len(samples)]

    slopes: list[float] = []
    n = len(samples)
    for i in range(n):
        t_i, v_i = samples[i]
        for j in range(i + 1, n):
            t_j, v_j = samples[j]
            dt = t_j - t_i
            if dt > 0:
                slopes.append((v_j - v_i) / dt)

    if not slopes:
        return None

    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 1:
        return slopes[mid]
    return (slopes[mid - 1] + slopes[mid]) / 2.0


def elapsed_active_fraction(
    now: float,
    resets_at: float,
    window_length: float,
    active_start_hour: int = 7,
    active_end_hour: int = 22,
) -> float:
    """Return the fraction of the rate-limit window that has elapsed during
    active hours, clamped to [0, 1].

    Pace advances only during ``[active_start_hour, active_end_hour)`` local
    time. At steady even consumption *across working hours*, ``used_pct``
    should equal ``elapsed_active_fraction * 100``.
    """
    window_start = resets_at - window_length
    active_total = active_seconds_in_range(
        window_start, resets_at, active_start_hour, active_end_hour
    )
    if active_total <= 0:
        return 0.0
    active_elapsed = active_seconds_in_range(
        window_start, now, active_start_hour, active_end_hour
    )
    frac = active_elapsed / active_total
    if frac < 0.0:
        return 0.0
    if frac > 1.0:
        return 1.0
    return frac


# ---------------------------------------------------------------------------
# Legacy linear regression — retained for tests / back-compat
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Sample filtering and idle-trimmed rate
# ---------------------------------------------------------------------------
def filter_by_lookback(
    samples: list[tuple[float, float]], now: float, lookback: float
) -> list[tuple[float, float]]:
    """Return samples whose timestamp falls within ``lookback`` seconds of ``now``."""
    cutoff = now - lookback
    return [s for s in samples if s[0] >= cutoff]


def active_time_rate(samples: list[tuple[float, float]]) -> float | None:
    """Return %/second burn rate counting only intervals where usage increased.

    Idle intervals (``used_pct`` unchanged) are excluded from both numerator
    and denominator — they are missing data, not zero-rate observations.
    Returns None if there is no active movement.
    """
    if len(samples) < 2:
        return None

    active_time = 0.0
    total_burn = 0.0
    for i in range(1, len(samples)):
        dt = samples[i][0] - samples[i - 1][0]
        dp = samples[i][1] - samples[i - 1][1]
        if dt > 0 and dp > 0:
            active_time += dt
            total_burn += dp

    if active_time == 0.0:
        return None
    return total_burn / active_time


def blended_rate(
    samples: list[tuple[float, float]],
    now: float,
    short_lookback: float,
    long_lookback: float,
    short_weight: float = 0.3,
) -> float | None:
    """Return a weighted blend of short- and long-window active-time rates.

    Falls back to whichever window is available if only one yields a rate.
    Returns None when neither window has enough data.
    """
    short_samples = filter_by_lookback(samples, now, short_lookback)
    long_samples = filter_by_lookback(samples, now, long_lookback)
    short_rate = active_time_rate(short_samples)
    long_rate = active_time_rate(long_samples)

    if short_rate is None and long_rate is None:
        return None
    if short_rate is None:
        return long_rate
    if long_rate is None:
        return short_rate
    return short_weight * short_rate + (1.0 - short_weight) * long_rate


# ---------------------------------------------------------------------------
# Projections
# ---------------------------------------------------------------------------
def eta_to_pct(
    used_pct: float, target_pct: float, rate: float | None, now: float
) -> float | None:
    """Return the clock-time (unix seconds) at which usage will hit ``target_pct``.

    Returns ``now`` if ``used_pct`` is already at or past the target.
    Returns None if the rate is unusable (None, zero, or negative).
    """
    if used_pct >= target_pct:
        return now
    if rate is None or rate <= 0:
        return None
    return now + (target_pct - used_pct) / rate


def elapsed_fraction(
    now: float, resets_at: float, window_length: float
) -> float:
    """Return fraction of the rate-limit window elapsed (0.0..1.0).

    Clamped to [0.0, 1.0]. This is the "pace line" — at steady even
    consumption, ``used_pct`` should equal ``elapsed_fraction * 100``.
    """
    window_start = resets_at - window_length
    if window_length <= 0:
        return 0.0
    frac = (now - window_start) / window_length
    if frac < 0.0:
        return 0.0
    if frac > 1.0:
        return 1.0
    return frac


def day_stop_target(
    now: float, resets_at: float, window_length: float
) -> tuple[int, float]:
    """Return (day_in_window, target_pct) for self-paced daily stop.

    ``day_in_window`` is 1-indexed, increments at each 24h boundary from the
    window start (``resets_at − window_length``), and caps at the number of
    whole days in the window. ``target_pct`` is ``day_in_window / days × 100``
    — the pace line you should be at by the end of that day.
    """
    window_start = resets_at - window_length
    elapsed = max(now - window_start, 0.0)
    days_in_window = int(window_length / 86400.0)
    day_in_window = int(elapsed // 86400) + 1
    day_in_window = max(1, min(day_in_window, days_in_window))
    target = (day_in_window / days_in_window) * 100.0
    return day_in_window, target


def is_fast_burn(
    samples: list[tuple[float, float]],
    now: float,
    short_lookback: float,
    long_lookback: float,
    used_pct: float,
    resets_at: float,
) -> bool:
    """Google SRE multi-window gate: True only when both windows project
    exhaustion before reset."""
    short_samples = filter_by_lookback(samples, now, short_lookback)
    long_samples = filter_by_lookback(samples, now, long_lookback)
    short_rate = active_time_rate(short_samples)
    long_rate = active_time_rate(long_samples)

    if short_rate is None or long_rate is None:
        return False
    if short_rate <= 0 or long_rate <= 0:
        return False

    remaining = 100.0 - used_pct
    if remaining <= 0:
        return True  # already exhausted

    time_to_reset = resets_at - now
    if time_to_reset <= 0:
        return False

    short_eta = remaining / short_rate
    long_eta = remaining / long_rate
    return short_eta < time_to_reset and long_eta < time_to_reset


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def format_clock_time(ts: float | None, now: float) -> str:
    """Format a projected clock-time relative to ``now``.

    Same local day → ``"3pm"`` / ``"3:30pm"``.
    Other day within a week → ``"Fri 3pm"``.
    Empty string when ``ts`` is None.
    """
    if ts is None:
        return ""

    local_ts = time.localtime(ts)
    local_now = time.localtime(now)

    hour = local_ts.tm_hour
    minute = local_ts.tm_min
    suffix = "am" if hour < 12 else "pm"
    disp_hour = hour % 12
    if disp_hour == 0:
        disp_hour = 12
    time_str = f"{disp_hour}{suffix}" if minute == 0 else f"{disp_hour}:{minute:02d}{suffix}"

    same_day = (
        local_ts.tm_year == local_now.tm_year
        and local_ts.tm_yday == local_now.tm_yday
    )
    if same_day:
        return time_str

    weekday = _WEEKDAYS[local_ts.tm_wday]
    return f"{weekday} {time_str}"


# ---------------------------------------------------------------------------
# Back-compat NamedTuple (still imported by older tests / callers)
# ---------------------------------------------------------------------------
class RateLimitDisplay(NamedTuple):
    label: str
    pct: int
    time_str: str
    is_exhausting: bool
