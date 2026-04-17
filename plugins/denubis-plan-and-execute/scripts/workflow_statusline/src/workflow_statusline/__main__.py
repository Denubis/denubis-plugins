"""Entry point: parse session JSON, compose two status lines, print them."""

from __future__ import annotations

import json
import sys
import time

from workflow_statusline import cache
from workflow_statusline.bar import boss_hp_bar
from workflow_statusline.colours import (
    BLUE,
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    RST,
    YELLOW,
)
from workflow_statusline.git import git_changes, git_location
from workflow_statusline.ratelimit import (
    elapsed_active_fraction,
    format_clock_time,
    next_active_end,
    theil_sen_slope,
)
from workflow_statusline.tmux import maybe_rename


_FIVE_HOUR_WINDOW = 5 * 3600.0
_SEVEN_DAY_WINDOW = 7 * 86400.0
_SAMPLE_MAX_AGE = 48 * 3600.0          # 48h storage retention
_ACTIVE_START_HOUR = 7                 # 07:00 local — pace starts advancing
_ACTIVE_END_HOUR = 22                  # 22:00 local — pace stops advancing
_FORECAST_LOOKBACK = 24 * 3600.0       # Theil-Sen lookback (24h of samples)
_FORECAST_MIN_SAMPLES = 30             # minimum sample count gate
_FORECAST_MIN_SPAN = 2 * 3600.0        # minimum real-time span — 2h of history
                                       # before extrapolating a 7d forecast


def _window_cell(
    label: str,
    used_pct: float,
    resets_at: float,
    now: float,
    window_length: float,
) -> str:
    """Render `label:used% / pace%` where pace is the even-consumption line
    through the *active hours* of this window. Red when used > pace (ahead
    of pace, borrowing against future budget); green otherwise.
    """
    pace_pct = elapsed_active_fraction(
        now, resets_at, window_length,
        active_start_hour=_ACTIVE_START_HOUR,
        active_end_hour=_ACTIVE_END_HOUR,
    ) * 100.0
    used_int = round(used_pct)
    pace_int = round(pace_pct)
    if used_pct < pace_pct:
        colour = GREEN
        sep = "<"
    else:
        colour = RED
        sep = "\u226e"  # ≮ NOT LESS-THAN
    return f"{colour}{label}:{used_int}% {sep} {pace_int}%{RST}"


def _forecast_cells(
    used_pct: float,
    resets_at: float,
    samples: list[tuple[float, float]],
    now: float,
) -> list[str]:
    """Return DayStop and WeekStop cells for the 7d window.

    Uses Theil-Sen median slope over all recent samples (unfiltered — overnight
    flats are real data, so the slope is pct-per-clock-second). Only displays
    an ETA when it falls within the relevant horizon.
    """
    cutoff = now - _FORECAST_LOOKBACK
    recent = [(t, v) for t, v in samples if t >= cutoff]
    if len(recent) < _FORECAST_MIN_SAMPLES:
        return []
    if recent[-1][0] - recent[0][0] < _FORECAST_MIN_SPAN:
        return []

    slope = theil_sen_slope(recent)
    if slope is None or slope <= 0:
        return []

    cells: list[str] = []

    # DayStop: target = active-fraction at next 22:00 local.
    day_end_ts = next_active_end(now, _ACTIVE_END_HOUR)
    day_target_pct = elapsed_active_fraction(
        day_end_ts, resets_at, _SEVEN_DAY_WINDOW,
        active_start_hour=_ACTIVE_START_HOUR,
        active_end_hour=_ACTIVE_END_HOUR,
    ) * 100.0

    if used_pct >= day_target_pct:
        cells.append(f"{RED}DayStop:go to sleep!{RST}")
    else:
        eta_day = now + (day_target_pct - used_pct) / slope
        if eta_day < day_end_ts:
            cells.append(f"{RED}DayStop:{format_clock_time(eta_day, now)}{RST}")
        # else: under pace for today, no DayStop cell

    # WeekStop: clock-time we'd hit 100% of the 7d window.
    eta_week = now + (100.0 - used_pct) / slope
    if eta_week < resets_at:
        cells.append(f"{RED}WeekStop:{format_clock_time(eta_week, now)}{RST}")
    # else: 7d window will reset before exhaustion

    return cells


def main() -> None:
    data = json.load(sys.stdin)

    cwd = data.get("cwd", "")
    if not cwd:
        return

    agent_name = data.get("agent", {}).get("name", "")
    model = data.get("model", {}).get("display_name", "")
    ctx = data.get("context_window", {})
    context_window_tokens = ctx.get("context_window_size", 200_000)
    pct = int(ctx.get("used_percentage") or 0)
    cost_data = data.get("cost", {})
    cost = cost_data.get("total_cost_usd") or 0
    duration_ms = cost_data.get("total_duration_ms") or 0
    lines_added = cost_data.get("total_lines_added") or 0
    lines_removed = cost_data.get("total_lines_removed") or 0

    rate_limits = data.get("rate_limits")
    session_id = data.get("session_id", "")

    # ── Location ──────────────────────────────────────────────────────
    location = git_location(cwd)
    staged, modified = git_changes(cwd)

    # ── Line 1: location, git changes, agent or churn ─────────────────
    line1 = f"{BLUE}{location.display}{RST}"
    if location.is_on_main and not location.is_worktree:
        line1 += f" {RED}{BOLD}\u2717MAIN{RST}"

    git_extra = ""
    if staged > 0:
        git_extra += f"{GREEN}+{staged}{RST}"
    if modified > 0:
        git_extra += f"{YELLOW}~{modified}{RST}"
    if git_extra:
        line1 += f" {git_extra}"

    if agent_name:
        line1 += f" {DIM}|{RST} {CYAN}agt:{agent_name}{RST}"
    elif lines_added or lines_removed:
        line1 += f" {DIM}|{RST} {GREEN}+{lines_added}{RST}/{RED}-{lines_removed}{RST}"

    # ── Rate limits ────────────────────────────────────────────────────
    rate_parts: list[str] = []
    if rate_limits:
        now = time.time()
        five_hour = rate_limits.get("five_hour")
        seven_day = rate_limits.get("seven_day")

        if five_hour:
            used = five_hour.get("used_percentage", 0)
            resets = five_hour.get("resets_at", 0)
            cache_file = cache.rate_cache_path("five_hour")
            cache.append_rate_sample(
                cache_file, now, used,
                max_age_seconds=_SAMPLE_MAX_AGE,
                session_id=session_id,
            )
            rate_parts.append(_window_cell("5h", used, resets, now, _FIVE_HOUR_WINDOW))

        if seven_day:
            used = seven_day.get("used_percentage", 0)
            resets = seven_day.get("resets_at", 0)
            cache_file = cache.rate_cache_path("seven_day")
            cache.append_rate_sample(
                cache_file, now, used,
                max_age_seconds=_SAMPLE_MAX_AGE,
                session_id=session_id,
            )
            rate_parts.append(_window_cell("7d", used, resets, now, _SEVEN_DAY_WINDOW))
            seven_day_samples = cache.read_rate_samples(cache_file)
            rate_parts.extend(_forecast_cells(used, resets, seven_day_samples, now))

    # ── Line 2: context bar, rate limits, cost, duration ─────────────
    bar = boss_hp_bar(pct, context_window_tokens)

    mins = duration_ms // 60000
    secs = (duration_ms % 60000) // 1000

    line2 = f"{bar} {pct}%"
    if rate_parts:
        line2 += f" {DIM}|{RST} {f' {DIM}|{RST} '.join(rate_parts)}"
    line2 += f" {DIM}|{RST} {YELLOW}${cost:.2f}{RST} {DIM}|{RST} {mins}m {secs}s"
    if model:
        line2 += f" {DIM}{model}{RST}"

    print(line1)
    print(line2)

    # ── Side-effects ─────────────────────────────────────────────────
    maybe_rename(location.display)


if __name__ == "__main__":
    main()
