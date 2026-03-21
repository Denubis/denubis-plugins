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
    with open(cache_file, "w") as f:
        f.write(data)
