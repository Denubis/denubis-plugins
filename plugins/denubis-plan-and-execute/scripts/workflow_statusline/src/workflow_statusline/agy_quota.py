#!/usr/bin/env python3
"""Render Antigravity's cached weekly quota against an active-hours pace target.

Reads the one-line snapshot ``timestamp|used_pct|resets_at`` that the
workflow-statusline package writes to
``$XDG_CACHE_HOME/agy-statusline/quota-seven_day`` on every Antigravity
statusline render. Client-only: no API calls, no CLI invocation.
"""

from __future__ import annotations

from pathlib import Path

from workflow_statusline import cache
from workflow_statusline.quota_cell import (
    AGY_BG,
    AGY_SEP,
    snapshot_status_text,
)


def snapshot_path() -> Path:
    """Return Antigravity's seven-day snapshot file path."""
    return Path(cache.quota_snapshot_path("seven_day", namespace=cache.AGY_NAMESPACE))


def status_text(path: Path, *, now: float | None = None) -> str:
    """Build the status cell, suppressing absent, malformed, or expired data."""
    return snapshot_status_text(path, separator=AGY_SEP, background=AGY_BG, now=now)


def main() -> None:
    """Print the latest cached Antigravity weekly quota cell for Byobu."""
    rendered = status_text(snapshot_path())
    if rendered:
        print(rendered)


if __name__ == "__main__":
    main()
