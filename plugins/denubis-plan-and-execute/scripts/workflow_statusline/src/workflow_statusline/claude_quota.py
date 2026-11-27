#!/usr/bin/env python3
"""Render Claude Code's cached seven-day quota against an active-hours pace target.

Reads the one-line snapshot ``timestamp|used_pct|resets_at`` that the
workflow-statusline package writes to
``$XDG_CACHE_HOME/claude-statusline/quota-seven_day`` on every statusline
render. Client-only: no API calls, no Claude invocation.
"""

from __future__ import annotations

from pathlib import Path

from workflow_statusline import cache
from workflow_statusline.quota_cell import (
    CLAUDE_BG,
    CLAUDE_SEP,
    QuotaSnapshot,
    parse_snapshot,
    render_pill,
    snapshot_status_text,
)

__all__ = [
    "QuotaSnapshot",
    "main",
    "parse_snapshot",
    "render_quota",
    "snapshot_path",
    "status_text",
]


def snapshot_path() -> Path:
    """Return the statusline's seven-day snapshot file path."""
    return Path(
        cache.quota_snapshot_path("seven_day", namespace=cache.DEFAULT_NAMESPACE)
    )


def render_quota(
    used_percent: float, pace: float, resets_at: float, *, now: float
) -> str:
    """Render used percentage, pace target, and reset as a Claude brand pill."""
    return render_pill(
        used_percent,
        pace,
        resets_at,
        now=now,
        separator=CLAUDE_SEP,
        background=CLAUDE_BG,
    )


def status_text(path: Path, *, now: float | None = None) -> str:
    """Build the status cell, suppressing absent, malformed, or expired data."""
    return snapshot_status_text(
        path, separator=CLAUDE_SEP, background=CLAUDE_BG, now=now
    )


def main() -> None:
    """Print the latest cached Claude seven-day quota cell for Byobu."""
    rendered = status_text(snapshot_path())
    if rendered:
        print(rendered)


if __name__ == "__main__":
    main()
