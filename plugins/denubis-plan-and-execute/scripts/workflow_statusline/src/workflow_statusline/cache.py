"""Generic TTL file cache for statusline data."""

from __future__ import annotations

import contextlib
import fcntl
import os
import time
from pathlib import Path


def rate_cache_path(window_key: str) -> str:
    """Return the per-user cache file path for a rate-limit window.

    Uses $XDG_CACHE_HOME if set, else $HOME/.cache. Shared across sessions
    so samples persist across restarts.
    """
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = xdg or str(Path(os.environ.get("HOME", "/tmp")) / ".cache")
    return str(Path(base) / "claude-statusline" / f"rate-{window_key}")


def read_if_fresh(cache_file: str, max_age: float) -> str | None:
    """Return file contents if the file exists and is younger than max_age seconds.

    Returns None if the file is missing or stale.
    """
    try:
        if (time.time() - Path(cache_file).stat().st_mtime) <= max_age:
            with Path(cache_file).open() as f:
                return f.read().strip()
    except OSError:
        pass
    return None


def write(cache_file: str, data: str) -> None:
    """Write data to cache file, creating parent dirs if needed."""
    Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
    with Path(cache_file).open("w") as f:
        f.write(data)


def read_rate_samples(cache_file: str) -> list[tuple[float, float]]:
    """Read all (timestamp, used_pct) entries from the cache file.

    Tolerates both legacy 2-field lines (``ts|pct``) and provenance-bearing
    4-field lines (``ts|pct|pid|session_id``). Ignores any extra fields.
    Returns empty list if file doesn't exist or is empty; skips malformed
    lines silently.
    """
    try:
        with Path(cache_file).open() as f:
            content = f.read()
    except OSError:
        return []

    samples: list[tuple[float, float]] = []
    for line in content.splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        try:
            samples.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    return samples


def read_rate_samples_full(
    cache_file: str,
) -> list[tuple[float, float, int, str]]:
    """Read entries with full provenance: (timestamp, used_pct, pid, session_id).

    Legacy 2-field lines parse with ``pid=0`` and ``session_id=""``.
    """
    try:
        with Path(cache_file).open() as f:
            content = f.read()
    except OSError:
        return []

    samples: list[tuple[float, float, int, str]] = []
    for line in content.splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        try:
            ts = float(parts[0])
            pct = float(parts[1])
        except ValueError:
            continue
        pid = 0
        session_id = ""
        if len(parts) >= 3:
            try:
                pid = int(parts[2])
            except ValueError:
                pid = 0
        if len(parts) >= 4:
            session_id = parts[3]
        samples.append((ts, pct, pid, session_id))
    return samples


def append_rate_sample(
    cache_file: str,
    timestamp: float,
    used_pct: float,
    min_interval: float = 30.0,
    max_entries: int = 10_000,
    max_age_seconds: float | None = None,
    pid: int | None = None,
    session_id: str = "",
) -> None:
    """Append a rate sample to the rolling buffer, safe under concurrent writers.

    Lines are written as ``timestamp|used_pct|pid|session_id`` so every entry
    carries provenance. Readers that don't need provenance (``read_rate_samples``)
    ignore the extra fields.

    Acquires an exclusive non-blocking flock on ``<cache_file>.lock``. If the
    lock is contended, this call is a no-op — a concurrent writer will produce
    the next sample.

    Writes the new buffer to a temp file and atomic-renames into place, so the
    cache file is never observed in a partially-written state by readers.

    No-ops if ``timestamp`` is within ``min_interval`` of the last entry.
    Trims to the most recent ``max_entries`` and, if ``max_age_seconds`` is
    given, drops entries older than that horizon.
    """
    Path(cache_file).parent.mkdir(parents=True, exist_ok=True)

    if pid is None:
        pid = os.getpid()

    lock_file = cache_file + ".lock"
    try:
        # The lock fd is closed in the finally below; a with-block here would
        # tangle the two-stage open-then-flock-or-skip control flow.
        lf = Path(lock_file).open("w")  # noqa: SIM115
    except OSError:
        return

    try:
        try:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError, OSError:
            return  # Another writer holds the lock — skip this sample

        entries = read_rate_samples_full(cache_file)

        if entries and (timestamp - entries[-1][0]) < min_interval:
            return

        entries.append((timestamp, used_pct, pid, session_id))

        if max_age_seconds is not None:
            cutoff = timestamp - max_age_seconds
            entries = [e for e in entries if e[0] >= cutoff]

        if len(entries) > max_entries:
            entries = entries[-max_entries:]

        tmp = cache_file + ".tmp"
        with Path(tmp).open("w") as f:
            for ts, pct, p, sid in entries:
                f.write(f"{ts}|{pct}|{p}|{sid}\n")
        Path(tmp).replace(cache_file)
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        lf.close()


def discard_before_reset(
    samples: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Drop samples preceding the most recent window reset.

    A reset is detected by a monotonic decrease in used_pct between adjacent
    samples (rate-limit window rolled over and Anthropic's used% dropped).
    Only samples from the most recent reset onward are returned.
    """
    if len(samples) < 2:
        return list(samples)

    last_reset_idx = 0
    for i in range(1, len(samples)):
        if samples[i][1] < samples[i - 1][1]:
            last_reset_idx = i
    return list(samples[last_reset_idx:])
