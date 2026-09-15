#!/usr/bin/env python3
"""Render Claude Code's cached seven-day quota against an active-hours pace target.

Reads the one-line snapshot ``timestamp|used_pct|resets_at`` that the
workflow-statusline package (brian-ed3d-plugins, denubis-plan-and-execute)
writes to ``$XDG_CACHE_HOME/claude-statusline/quota-seven_day`` on every
statusline render. Client-only: no API calls, no Claude invocation.

The cell mirrors codex_quota's ``used pace`` rendering, with ``*`` as the
separator so the two toolbar cells are distinguishable at a glance.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from workflow_statusline.codex_quota import pace_percent, reset_label

_SEVEN_DAY_MINUTES = 7 * 24 * 60

type QuotaSnapshot = tuple[float, float, float]


def snapshot_path() -> Path:
    """Return the statusline's seven-day snapshot file path."""
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "claude-statusline" / "quota-seven_day"


def parse_snapshot(text: str) -> QuotaSnapshot | None:
    """Parse ``timestamp|used_pct|resets_at`` into floats, or None if invalid."""
    parts = text.strip().split("|")
    if len(parts) != 3:
        return None
    try:
        timestamp, used, resets_at = (float(p) for p in parts)
    except ValueError:
        return None
    if not (0 <= used <= 100 and resets_at > 0):
        return None
    return timestamp, used, resets_at


def render_quota(
    used_percent: float, pace: float, resets_at: float, *, now: float
) -> str:
    """Render used percentage, pace target, and reset as a compact tmux cell."""
    colour = "green" if used_percent < pace else "red"
    reset = reset_label(resets_at, now=now)
    return f"#[fg={colour}]{round(used_percent)}*{round(pace)} {reset}#[default]"


def status_text(path: Path, *, now: float | None = None) -> str:
    """Build the status cell, suppressing absent, malformed, or expired data."""
    current_time = time.time() if now is None else now
    try:
        text = path.read_text()
    except OSError:
        return ""
    snapshot = parse_snapshot(text)
    if snapshot is None:
        return ""
    _timestamp, used, resets_at = snapshot
    if resets_at <= current_time:
        return ""
    pace = pace_percent(
        now=current_time,
        resets_at=resets_at,
        window_minutes=_SEVEN_DAY_MINUTES,
    )
    return render_quota(used, pace, resets_at, now=current_time)


def main() -> None:
    """Print the latest cached Claude seven-day quota cell for Byobu."""
    rendered = status_text(snapshot_path())
    if rendered:
        print(rendered)


if __name__ == "__main__":
    main()
