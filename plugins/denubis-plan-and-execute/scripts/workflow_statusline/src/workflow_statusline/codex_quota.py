#!/usr/bin/env python3
"""Render Codex's cached seven-day quota against an active-hours pace target."""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


type QuotaSnapshot = tuple[float, int, int]

_SEVEN_DAY_MINUTES = 7 * 24 * 60
_ACTIVE_START_HOUR = 7
_ACTIVE_END_HOUR = 22
_RECENT_THREAD_COUNT = 16
_REVERSE_READ_BLOCK_BYTES = 64 * 1024


def quota_from_event(event: object) -> QuotaSnapshot | None:
    """Extract the seven-day quota from one Codex token-count event."""
    if not isinstance(event, dict) or event.get("type") != "event_msg":
        return None
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "token_count":
        return None
    rate_limits = payload.get("rate_limits")
    if not isinstance(rate_limits, dict):
        return None
    # Model-specific pools (such as Spark) have independent usage and resets.
    # Older rollouts omit the bucket ID or use null for the main Codex quota.
    if rate_limits.get("limit_id") not in (None, "codex"):
        return None

    for name in ("primary", "secondary"):
        window = rate_limits.get(name)
        if not isinstance(window, dict):
            continue
        used = window.get("used_percent")
        minutes = window.get("window_minutes")
        resets_at = window.get("resets_at")
        if (
            isinstance(used, (int, float))
            and not isinstance(used, bool)
            and isinstance(minutes, int)
            and not isinstance(minutes, bool)
            and isinstance(resets_at, int)
            and not isinstance(resets_at, bool)
            and 0 <= used <= 100
            and minutes == _SEVEN_DAY_MINUTES
            and resets_at > 0
        ):
            return float(used), minutes, resets_at
    return None


def active_seconds_in_range(
    start_ts: float,
    end_ts: float,
    *,
    active_start_hour: int = _ACTIVE_START_HOUR,
    active_end_hour: int = _ACTIVE_END_HOUR,
) -> float:
    """Count local-time seconds in the configured daily active-hours range."""
    if end_ts <= start_ts:
        return 0.0

    start = datetime.datetime.fromtimestamp(start_ts)
    end = datetime.datetime.fromtimestamp(end_ts)
    total = 0.0
    day = start.date()
    while day <= end.date():
        active_start = datetime.datetime.combine(
            day, datetime.time(active_start_hour, 0)
        )
        active_end = datetime.datetime.combine(day, datetime.time(active_end_hour, 0))
        overlap_start = max(active_start, start)
        overlap_end = min(active_end, end)
        if overlap_end > overlap_start:
            total += (overlap_end - overlap_start).total_seconds()
        day += datetime.timedelta(days=1)
    return total


def pace_percent(*, now: float, resets_at: float, window_minutes: int) -> float:
    """Return the active-hours-scaled target percentage for this instant."""
    window_seconds = window_minutes * 60.0
    window_start = resets_at - window_seconds
    active_total = active_seconds_in_range(window_start, resets_at)
    if active_total <= 0:
        return 0.0
    active_elapsed = active_seconds_in_range(window_start, now)
    return min(max(active_elapsed / active_total * 100.0, 0.0), 100.0)


def reset_label(resets_at: float, *, now: float) -> str:
    """Show the local reset weekday, or clock time in the final 24 hours."""
    reset = datetime.datetime.fromtimestamp(resets_at)
    return reset.strftime("%H:%M" if resets_at - now <= 86_400 else "%a")


def render_quota(
    used_percent: float, pace: float, resets_at: float, *, now: float | None = None
) -> str:
    """Render used percentage, pace target, and reset as a compact tmux cell."""
    colour = "green" if used_percent < pace else "red"
    reset = reset_label(resets_at, now=time.time() if now is None else now)
    return f"#[fg={colour}]{round(used_percent)} {round(pace)} {reset}#[default]"


def reversed_lines(path: Path) -> Iterator[str]:
    """Yield a JSONL file from newest line to oldest without reading it all."""
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        position = stream.tell()
        remainder = b""
        while position > 0:
            read_size = min(_REVERSE_READ_BLOCK_BYTES, position)
            position -= read_size
            stream.seek(position)
            parts = (stream.read(read_size) + remainder).split(b"\n")
            remainder = parts[0]
            for line in reversed(parts[1:]):
                if line:
                    yield line.decode("utf-8", errors="replace")
        if remainder:
            yield remainder.decode("utf-8", errors="replace")


def quota_from_rollout(path: Path) -> QuotaSnapshot | None:
    """Read the newest valid main seven-day quota snapshot from one rollout."""
    result = _dated_quota_from_rollout(path)
    return result[1] if result is not None else None


def _dated_quota_from_rollout(
    path: Path, *, newer_than: float | None = None
) -> tuple[float, QuotaSnapshot] | None:
    """Read quota evidence with its timestamp, stopping at already-older events."""
    try:
        for line in reversed_lines(path):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            timestamp = event.get("timestamp")
            observed_at = None
            if isinstance(timestamp, str):
                try:
                    observed_at = datetime.datetime.fromisoformat(timestamp).timestamp()
                except ValueError:
                    continue
            # Rollouts append events chronologically. Once we reach older data,
            # nothing earlier in this file can replace the current best snapshot.
            if (
                newer_than is not None
                and observed_at is not None
                and observed_at <= newer_than
            ):
                return None
            snapshot = quota_from_event(event)
            if snapshot is not None and (observed_at is not None or newer_than is None):
                return observed_at if observed_at is not None else 0.0, snapshot
    except OSError:
        return None
    return None


def _state_databases(codex_home: Path) -> list[Path]:
    def version(path: Path) -> int:
        suffix = path.stem.removeprefix("state_")
        return int(suffix) if suffix.isdigit() else -1

    return sorted(codex_home.glob("state_*.sqlite"), key=version, reverse=True)


def latest_quota(codex_home: Path) -> QuotaSnapshot | None:
    """Read the newest cached quota from recent local Codex threads."""
    newest: tuple[float, QuotaSnapshot] | None = None
    for database_path in _state_databases(codex_home):
        try:
            connection = sqlite3.connect(
                f"file:{database_path}?mode=ro",
                uri=True,
                timeout=0.2,
            )
            try:
                rows = connection.execute(
                    "SELECT rollout_path FROM threads "
                    "ORDER BY updated_at_ms DESC LIMIT ?",
                    (_RECENT_THREAD_COUNT,),
                ).fetchall()
            finally:
                connection.close()
        except sqlite3.Error:
            continue

        for (rollout_path,) in rows:
            if not isinstance(rollout_path, str):
                continue
            result = _dated_quota_from_rollout(
                Path(rollout_path), newer_than=newest[0] if newest else None
            )
            if result is not None:
                newest = result
    return newest[1] if newest is not None else None


def status_text(
    codex_home: Path,
    *,
    now: float | None = None,
    snapshot: QuotaSnapshot | None = None,
) -> str:
    """Build the status cell, suppressing absent or already-expired data."""
    current_time = time.time() if now is None else now
    current = latest_quota(codex_home) if snapshot is None else snapshot
    if current is None:
        return ""
    used, window_minutes, resets_at = current
    if resets_at <= current_time:
        return ""
    pace = pace_percent(
        now=current_time,
        resets_at=resets_at,
        window_minutes=window_minutes,
    )
    return render_quota(used, pace, resets_at, now=current_time)


def main() -> None:
    """Print the latest local Codex quota cell for Byobu."""
    configured_home = os.environ.get("CODEX_HOME")
    codex_home = (
        Path(configured_home).expanduser()
        if configured_home
        else Path.home() / ".codex"
    )
    rendered = status_text(codex_home)
    if rendered:
        print(rendered)


if __name__ == "__main__":
    main()
