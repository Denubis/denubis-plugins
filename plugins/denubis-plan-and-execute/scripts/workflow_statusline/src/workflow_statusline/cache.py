"""Generic TTL file cache for statusline data."""

from __future__ import annotations

import os
import time


def read_if_fresh(cache_file: str, max_age: float) -> str | None:
    """Return file contents if the file exists and is younger than max_age seconds.

    Returns None if the file is missing or stale.
    """
    try:
        if (time.time() - os.path.getmtime(cache_file)) <= max_age:
            with open(cache_file) as f:
                return f.read().strip()
    except OSError:
        pass
    return None


def write(cache_file: str, data: str) -> None:
    """Write data to cache file, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w") as f:
        f.write(data)


def read_rate_samples(cache_file: str) -> list[tuple[float, float]]:
    """Read all (timestamp, used_pct) entries from the cache file.

    Returns empty list if file doesn't exist or is empty.
    Skips malformed lines silently.
    """
    try:
        with open(cache_file) as f:
            content = f.read()
    except OSError:
        return []

    samples: list[tuple[float, float]] = []
    for line in content.splitlines():
        parts = line.split("|")
        if len(parts) != 2:
            continue
        try:
            samples.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    return samples


def append_rate_sample(
    cache_file: str,
    timestamp: float,
    used_pct: float,
    min_interval: float = 30.0,
    max_entries: int = 20,
) -> None:
    """Append a rate sample to the rolling buffer if min_interval has elapsed since last entry."""
    entries = read_rate_samples(cache_file)

    if entries and (timestamp - entries[-1][0]) < min_interval:
        return

    entries.append((timestamp, used_pct))

    # Trim to most recent max_entries
    if len(entries) > max_entries:
        entries = entries[-max_entries:]

    os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
    with open(cache_file, "w") as f:
        for ts, pct in entries:
            f.write(f"{ts}|{pct}\n")
