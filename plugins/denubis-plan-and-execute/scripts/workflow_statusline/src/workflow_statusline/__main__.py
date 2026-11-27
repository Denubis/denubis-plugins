"""Entry point: parse session JSON, compose two status lines, print them."""

from __future__ import annotations

import datetime
import json
import math
import sys
import time
from typing import TypeIs

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
from workflow_statusline.quota_cell import is_valid_timestamp
from workflow_statusline.ratelimit import (
    elapsed_active_fraction,
    format_clock_time,
    next_active_end,
    theil_sen_slope,
)
from workflow_statusline.tmux import maybe_rename

type RateWindow = tuple[int | float, int | float]

_FIVE_HOUR_WINDOW = 5 * 3600.0
_SEVEN_DAY_WINDOW = 7 * 86400.0
_SAMPLE_MAX_AGE = 48 * 3600.0  # 48h storage retention
_ACTIVE_START_HOUR = 7  # 07:00 local — pace starts advancing
_ACTIVE_END_HOUR = 22  # 22:00 local — pace stops advancing
_FORECAST_LOOKBACK = 24 * 3600.0  # Theil-Sen lookback (24h of samples)
_FORECAST_MIN_SAMPLES = 30  # minimum sample count gate
_FORECAST_MIN_SPAN = 2 * 3600.0  # minimum real-time span — 2h of history
# before extrapolating a 7d forecast


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _is_antigravity_payload(data: dict[str, object]) -> bool:
    """Return True when stdin JSON came from Antigravity CLI."""
    if data.get("product") == "antigravity":
        return True
    return "rate_limits" not in data and isinstance(data.get("quota"), dict)


def _is_real_number(value: object) -> TypeIs[int | float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _parse_agy_resets_at(bucket: dict[str, object], *, now: float) -> float | None:
    reset_time = bucket.get("reset_time")
    if isinstance(reset_time, str) and reset_time:
        try:
            parsed = datetime.datetime.fromisoformat(reset_time)
        except ValueError:
            parsed = None
        if parsed is not None and parsed.tzinfo is not None:
            resets_at = parsed.timestamp()
            if is_valid_timestamp(resets_at):
                return resets_at

    reset_in = bucket.get("reset_in_seconds")
    if _is_real_number(reset_in) and reset_in > 0:
        resets_at = now + float(reset_in)
        if is_valid_timestamp(resets_at):
            return resets_at
    return None


def _parse_agy_window(bucket: object, *, now: float) -> RateWindow | None:
    """Convert one Antigravity quota bucket into ``(used_pct, resets_at)``."""
    if not isinstance(bucket, dict) or bucket.get("disabled") is True:
        return None
    remaining = bucket.get("remaining_fraction")
    if not _is_real_number(remaining):
        return None
    remaining_f = float(remaining)
    if not (0.0 <= remaining_f <= 1.0):
        return None
    resets_at = _parse_agy_resets_at(bucket, now=now)
    if resets_at is None:
        return None
    used_pct = max(0.0, min(100.0, (1.0 - remaining_f) * 100.0))
    return used_pct, resets_at


def _parse_claude_window(window: object) -> RateWindow | None:
    if not isinstance(window, dict) or not window:
        return None
    used = window.get("used_percentage", 0)
    resets = window.get("resets_at", 0)
    if not (_is_real_number(used) and _is_real_number(resets)):
        return None
    if not (0 <= used <= 100 and is_valid_timestamp(float(resets))):
        return None
    return used, resets


def _extract_rate_windows(
    data: dict[str, object], *, now: float, is_antigravity: bool
) -> tuple[RateWindow | None, RateWindow | None]:
    if is_antigravity:
        quota = data.get("quota")
        if not isinstance(quota, dict):
            return None, None
        return (
            _parse_agy_window(quota.get("gemini-5h"), now=now),
            _parse_agy_window(quota.get("gemini-weekly"), now=now),
        )

    rate_limits = data.get("rate_limits")
    if not isinstance(rate_limits, dict):
        return None, None
    return (
        _parse_claude_window(rate_limits.get("five_hour")),
        _parse_claude_window(rate_limits.get("seven_day")),
    )


def _record_and_render_rates(
    five_hour: RateWindow | None,
    seven_day: RateWindow | None,
    *,
    now: float,
    session_id: str,
    namespace: str,
) -> list[str]:
    rate_parts: list[str] = []
    if five_hour is not None:
        used, resets = five_hour
        cache_file = cache.rate_cache_path("five_hour", namespace=namespace)
        cache.append_rate_sample(
            cache_file,
            now,
            used,
            max_age_seconds=_SAMPLE_MAX_AGE,
            session_id=session_id,
        )
        cache.write_quota_snapshot(
            cache.quota_snapshot_path("five_hour", namespace=namespace),
            timestamp=now,
            used_pct=used,
            resets_at=resets,
        )
        rate_parts.append(_window_cell("5h", used, resets, now, _FIVE_HOUR_WINDOW))

    if seven_day is not None:
        used, resets = seven_day
        cache_file = cache.rate_cache_path("seven_day", namespace=namespace)
        cache.append_rate_sample(
            cache_file,
            now,
            used,
            max_age_seconds=_SAMPLE_MAX_AGE,
            session_id=session_id,
        )
        cache.write_quota_snapshot(
            cache.quota_snapshot_path("seven_day", namespace=namespace),
            timestamp=now,
            used_pct=used,
            resets_at=resets,
        )
        rate_parts.append(_window_cell("7d", used, resets, now, _SEVEN_DAY_WINDOW))
        seven_day_samples = cache.read_rate_samples(cache_file)
        rate_parts.extend(_forecast_cells(used, resets, seven_day_samples, now))
    return rate_parts


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
    pace_pct = (
        elapsed_active_fraction(
            now,
            resets_at,
            window_length,
            active_start_hour=_ACTIVE_START_HOUR,
            active_end_hour=_ACTIVE_END_HOUR,
        )
        * 100.0
    )
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
    day_target_pct = (
        elapsed_active_fraction(
            day_end_ts,
            resets_at,
            _SEVEN_DAY_WINDOW,
            active_start_hour=_ACTIVE_START_HOUR,
            active_end_hour=_ACTIVE_END_HOUR,
        )
        * 100.0
    )

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
    # (no else branch: the 7d window resets before exhaustion)

    return cells


def _compose_line1(
    location_display: str,
    *,
    show_main_warning: bool,
    staged: int,
    modified: int,
    agent_name: str,
    lines_added: int,
    lines_removed: int,
) -> str:
    line1 = f"{BLUE}{location_display}{RST}"
    if show_main_warning:
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
    return line1


def _compose_line2(
    *,
    pct: int,
    context_window_tokens: int,
    rate_parts: list[str],
    cost: float | None,
    duration_ms: int | None,
    model: str,
) -> str:
    bar = boss_hp_bar(pct, context_window_tokens)
    line2 = f"{bar} {pct}%"
    if rate_parts:
        line2 += f" {DIM}|{RST} {f' {DIM}|{RST} '.join(rate_parts)}"
    if cost is not None:
        line2 += f" {DIM}|{RST} {YELLOW}${cost:.2f}{RST}"
    if duration_ms is not None:
        mins = duration_ms // 60000
        secs = (duration_ms % 60000) // 1000
        line2 += f" {DIM}|{RST} {mins}m {secs}s"
    if model:
        line2 += f" {DIM}{model}{RST}"
    return line2


def _int_or_default(value: object, default: int) -> int:
    return int(value) if _is_real_number(value) else default


def _str_or_empty(value: object) -> str:
    return value if isinstance(value, str) else ""


def _extract_cost_and_duration(
    cost_data: dict[str, object], *, is_antigravity: bool
) -> tuple[float | None, int | None]:
    raw_cost = (
        cost_data.get("total_cost_usd")
        if "total_cost_usd" in cost_data
        else cost_data.get("total_usd")
    )
    if _is_real_number(raw_cost):
        cost: float | None = float(raw_cost)
    else:
        cost = None if is_antigravity else 0.0

    raw_duration = cost_data.get("total_duration_ms")
    if _is_real_number(raw_duration):
        duration_ms: int | None = int(raw_duration)
    else:
        duration_ms = None if is_antigravity else 0
    return cost, duration_ms


def main() -> None:
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        return

    cwd = _str_or_empty(data.get("cwd"))
    if not cwd:
        return

    is_antigravity = _is_antigravity_payload(data)
    namespace = cache.AGY_NAMESPACE if is_antigravity else cache.DEFAULT_NAMESPACE

    agent_name = _str_or_empty(_as_dict(data.get("agent")).get("name"))
    model = _str_or_empty(_as_dict(data.get("model")).get("display_name"))
    ctx = _as_dict(data.get("context_window"))
    raw_ctx_size = _int_or_default(ctx.get("context_window_size"), 0)
    context_window_tokens = raw_ctx_size if raw_ctx_size > 0 else 200_000
    pct = _int_or_default(ctx.get("used_percentage"), 0)
    cost_data = _as_dict(data.get("cost"))
    cost, duration_ms = _extract_cost_and_duration(
        cost_data, is_antigravity=is_antigravity
    )
    session_id = _str_or_empty(data.get("session_id")) or _str_or_empty(
        data.get("conversation_id")
    )

    location = git_location(cwd)
    staged, modified = git_changes(cwd)

    now = time.time()
    five_hour, seven_day = _extract_rate_windows(
        data, now=now, is_antigravity=is_antigravity
    )
    rate_parts = _record_and_render_rates(
        five_hour, seven_day, now=now, session_id=session_id, namespace=namespace
    )

    line1 = _compose_line1(
        location.display,
        show_main_warning=location.is_on_main and not location.is_worktree,
        staged=staged,
        modified=modified,
        agent_name=agent_name,
        lines_added=_int_or_default(cost_data.get("total_lines_added"), 0),
        lines_removed=_int_or_default(cost_data.get("total_lines_removed"), 0),
    )
    line2 = _compose_line2(
        pct=pct,
        context_window_tokens=context_window_tokens,
        rate_parts=rate_parts,
        cost=cost,
        duration_ms=duration_ms,
        model=model,
    )

    print(line1)
    print(line2)

    if is_antigravity:
        maybe_rename(location.display, prefix="Ag")
    else:
        maybe_rename(location.display)


if __name__ == "__main__":
    main()
