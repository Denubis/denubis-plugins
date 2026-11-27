"""Shared Byobu quota cell formatting and snapshot parsing.

Renders compact, high-contrast brand-tinted tmux pills for Claude, Codex, and
Antigravity weekly quotas using the shared active-hours (07:00-22:00) pace
model. Each pill uses a distinct dark background so adjacent toolbar cells
stay visually separated while preserving WCAG AA+ contrast for both under-pace
(green) and at/over-pace (red) states.
"""

from __future__ import annotations

import datetime
import math
import time
from typing import TYPE_CHECKING

from workflow_statusline.ratelimit import elapsed_active_fraction

if TYPE_CHECKING:
    from pathlib import Path

type QuotaSnapshot = tuple[float, float, float]

SEVEN_DAY_MINUTES = 7 * 24 * 60
_ACTIVE_START_HOUR = 7
_ACTIVE_END_HOUR = 22

# Foreground colours tuned for >= 5.7:1 (red) and >= 9.6:1 (green) WCAG contrast
# across all three dark brand pill backgrounds.
GOOD_FG = "#86efac"
BAD_FG = "#ff8585"

# Distinct dark brand-tinted pill backgrounds (all separate from Byobu #1b136e).
CLAUDE_BG = "#421e0f"
CODEX_BG = "#26282e"
AGY_BG = "#0e3147"

CLAUDE_SEP = "*"
CODEX_SEP = "\u00a7"  # §
AGY_SEP = "\u0245"  # Ʌ

_SHORT_WEEKDAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


def is_valid_timestamp(value: int | float) -> bool:
    """Return True when ``value`` is a positive finite Unix timestamp."""
    try:
        ts = float(value)
    except OverflowError:
        return False
    if not (math.isfinite(ts) and ts > 0):
        return False
    try:
        datetime.datetime.fromtimestamp(ts)
    except OverflowError, OSError, ValueError:
        return False
    return True


def parse_snapshot(text: str) -> QuotaSnapshot | None:
    """Parse ``timestamp|used_pct|resets_at`` into validated floats, or None."""
    parts = text.strip().split("|")
    if len(parts) != 3:
        return None
    try:
        timestamp, used, resets_at = (float(p) for p in parts)
    except ValueError:
        return None
    if not (math.isfinite(timestamp) and math.isfinite(used)):
        return None
    if not (0 <= used <= 100 and is_valid_timestamp(resets_at)):
        return None
    return timestamp, used, resets_at


def pace_percent(*, now: float, resets_at: float, window_minutes: int) -> float:
    """Return the active-hours-scaled target percentage for this instant."""
    fraction = elapsed_active_fraction(
        now,
        resets_at,
        window_minutes * 60.0,
        active_start_hour=_ACTIVE_START_HOUR,
        active_end_hour=_ACTIVE_END_HOUR,
    )
    return fraction * 100.0


def reset_label(resets_at: float, *, now: float) -> str:
    """Show 2-char weekday, 24h hour in the final 24h, and HH:MM in the final hour."""
    reset = datetime.datetime.fromtimestamp(resets_at)
    remaining = resets_at - now
    if remaining <= 3_600:
        return reset.strftime("%H:%M")
    if remaining <= 86_400:
        return reset.strftime("%Hh")
    return _SHORT_WEEKDAYS[reset.weekday()]


def render_pill(
    used_percent: float,
    pace: float,
    resets_at: float,
    *,
    now: float,
    separator: str,
    background: str,
) -> str:
    """Render used percentage, pace target, and reset as a brand-tinted pill."""
    fg = GOOD_FG if used_percent < pace else BAD_FG
    reset = reset_label(resets_at, now=now)
    ratio = f"{round(used_percent)}{separator}{round(pace)}"
    return f"#[bg={background},fg={fg}]{ratio} {reset}#[default]"


def snapshot_status_text(
    path: Path,
    *,
    separator: str,
    background: str,
    now: float | None = None,
) -> str:
    """Build a snapshot-backed pill, suppressing absent, malformed, or expired data."""
    current_time = time.time() if now is None else now
    try:
        text = path.read_text()
    except OSError, UnicodeDecodeError:
        return ""
    snapshot = parse_snapshot(text)
    if snapshot is None:
        return ""
    _timestamp, used, resets_at = snapshot
    if resets_at <= current_time:
        return ""
    try:
        pace = pace_percent(
            now=current_time,
            resets_at=resets_at,
            window_minutes=SEVEN_DAY_MINUTES,
        )
        return render_pill(
            used,
            pace,
            resets_at,
            now=current_time,
            separator=separator,
            background=background,
        )
    except OverflowError, OSError, ValueError:
        return ""
