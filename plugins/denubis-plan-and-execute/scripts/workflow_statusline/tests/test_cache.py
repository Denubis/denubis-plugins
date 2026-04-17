"""Tests for workflow_statusline.cache module."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from workflow_statusline import cache


class TestReadIfFresh:
    def test_returns_contents_when_fresh(self, tmp_path: Path) -> None:
        """Fresh file should return its stripped contents."""
        cache_file = os.path.join(str(tmp_path), "test_cache")
        with open(cache_file, "w") as f:
            f.write("hello\n")
        result = cache.read_if_fresh(cache_file, max_age=10)
        assert result == "hello"

    def test_returns_none_when_stale(self, tmp_path: Path) -> None:
        """File older than max_age should return None."""
        cache_file = os.path.join(str(tmp_path), "test_cache")
        with open(cache_file, "w") as f:
            f.write("old data")
        # Set mtime to 20 seconds ago
        old_time = time.time() - 20
        os.utime(cache_file, (old_time, old_time))
        result = cache.read_if_fresh(cache_file, max_age=5)
        assert result is None

    def test_returns_none_when_missing(self) -> None:
        """Non-existent file should return None."""
        result = cache.read_if_fresh("/tmp/nonexistent_cache_file_xyz", max_age=10)
        assert result is None

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """Contents should be stripped of leading/trailing whitespace."""
        cache_file = os.path.join(str(tmp_path), "test_cache")
        with open(cache_file, "w") as f:
            f.write("  data  \n")
        result = cache.read_if_fresh(cache_file, max_age=10)
        assert result == "data"


class TestWrite:
    def test_writes_data(self, tmp_path: Path) -> None:
        """Write should create a file with the given data."""
        cache_file = os.path.join(str(tmp_path), "test_cache")
        cache.write(cache_file, "test_data")
        with open(cache_file) as f:
            assert f.read() == "test_data"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Write should overwrite existing file contents."""
        cache_file = os.path.join(str(tmp_path), "test_cache")
        cache.write(cache_file, "old")
        cache.write(cache_file, "new")
        with open(cache_file) as f:
            assert f.read() == "new"


class TestReadRateSamples:
    def test_returns_empty_for_missing_file(self) -> None:
        """Non-existent file should return empty list."""
        result = cache.read_rate_samples("/tmp/nonexistent_rate_samples_xyz")
        assert result == []

    def test_returns_empty_for_empty_file(self, tmp_path: Path) -> None:
        """Empty file should return empty list."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        with open(cache_file, "w") as f:
            f.write("")
        result = cache.read_rate_samples(cache_file)
        assert result == []

    def test_parses_entries(self, tmp_path: Path) -> None:
        """Should parse pipe-separated timestamp|used_pct lines."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        with open(cache_file, "w") as f:
            f.write("1000.0|50.5\n2000.0|75.0\n")
        result = cache.read_rate_samples(cache_file)
        assert result == [(1000.0, 50.5), (2000.0, 75.0)]

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        """Malformed lines should be silently skipped."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        with open(cache_file, "w") as f:
            f.write("1000.0|50.5\nbadline\n2000.0|75.0\n")
        result = cache.read_rate_samples(cache_file)
        assert result == [(1000.0, 50.5), (2000.0, 75.0)]


class TestAppendRateSample:
    def test_writes_and_reads_back(self, tmp_path: Path) -> None:
        """Append should write an entry that read_rate_samples can parse."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        cache.append_rate_sample(cache_file, 1000.0, 50.5)
        cache.append_rate_sample(cache_file, 1050.0, 60.0)
        result = cache.read_rate_samples(cache_file)
        assert result == [(1000.0, 50.5), (1050.0, 60.0)]

    def test_min_interval_enforcement(self, tmp_path: Path) -> None:
        """Appending within min_interval of last entry should be a no-op."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        cache.append_rate_sample(cache_file, 1000.0, 50.0, min_interval=30.0)
        cache.append_rate_sample(cache_file, 1020.0, 55.0, min_interval=30.0)  # within 30s
        result = cache.read_rate_samples(cache_file)
        assert result == [(1000.0, 50.0)]

    def test_max_entries_trimming(self, tmp_path: Path) -> None:
        """Writing more than max_entries should keep only the most recent."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        for i in range(25):
            ts = 1000.0 + i * 60.0  # 60s apart to pass min_interval
            cache.append_rate_sample(cache_file, ts, float(i), max_entries=20)
        result = cache.read_rate_samples(cache_file)
        assert len(result) == 20
        # Should keep entries 5..24 (most recent 20)
        assert result[0] == (1000.0 + 5 * 60.0, 5.0)
        assert result[-1] == (1000.0 + 24 * 60.0, 24.0)

    def test_max_age_trimming(self, tmp_path: Path) -> None:
        """Samples older than max_age_seconds should be dropped on write."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        base = 1000.0
        # Write samples across a 50h span, 1h apart.
        for i in range(50):
            cache.append_rate_sample(
                cache_file,
                base + i * 3600.0,
                float(i),
                max_entries=10_000,
                max_age_seconds=48 * 3600,
            )
        result = cache.read_rate_samples(cache_file)
        # Last write is at base + 49*3600. 48h cutoff → keeps samples with ts >= base + 1*3600.
        assert result[0][0] == base + 1 * 3600.0
        assert result[-1][0] == base + 49 * 3600.0


class TestProvenance:
    def test_append_records_pid_and_session(self, tmp_path: Path) -> None:
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        cache.append_rate_sample(
            cache_file, 1000.0, 42.0, pid=12345, session_id="sess-abc"
        )
        full = cache.read_rate_samples_full(cache_file)
        assert full == [(1000.0, 42.0, 12345, "sess-abc")]

    def test_read_rate_samples_ignores_provenance_fields(self, tmp_path: Path) -> None:
        """read_rate_samples must still return (ts, pct) regardless of extra fields."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        with open(cache_file, "w") as f:
            f.write("1000.0|50.0|111|sess-x\n")
            f.write("1060.0|55.0|222|sess-y\n")
        assert cache.read_rate_samples(cache_file) == [
            (1000.0, 50.0),
            (1060.0, 55.0),
        ]

    def test_read_rate_samples_full_handles_legacy_two_field_lines(
        self, tmp_path: Path
    ) -> None:
        """Older 2-field lines must parse with empty pid/session_id for back-compat."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        with open(cache_file, "w") as f:
            f.write("1000.0|50.0\n")
            f.write("1060.0|55.0|333|sess-z\n")
        full = cache.read_rate_samples_full(cache_file)
        assert full == [
            (1000.0, 50.0, 0, ""),
            (1060.0, 55.0, 333, "sess-z"),
        ]


class TestDiscardBeforeReset:
    def test_no_reset_returns_unchanged(self) -> None:
        samples = [(100.0, 10.0), (200.0, 20.0), (300.0, 30.0)]
        assert cache.discard_before_reset(samples) == samples

    def test_drops_samples_before_monotonic_decrease(self) -> None:
        # Index 3 is a reset (50 → 5). Keep only samples from the reset onward.
        samples = [
            (100.0, 40.0),
            (200.0, 45.0),
            (300.0, 50.0),
            (400.0, 5.0),
            (500.0, 10.0),
        ]
        result = cache.discard_before_reset(samples)
        assert result == [(400.0, 5.0), (500.0, 10.0)]

    def test_multiple_resets_keeps_after_last(self) -> None:
        samples = [
            (100.0, 10.0),
            (200.0, 20.0),
            (300.0, 5.0),   # first reset
            (400.0, 15.0),
            (500.0, 2.0),   # second reset
            (600.0, 8.0),
        ]
        result = cache.discard_before_reset(samples)
        assert result == [(500.0, 2.0), (600.0, 8.0)]

    def test_empty_list_returns_empty(self) -> None:
        assert cache.discard_before_reset([]) == []

    def test_single_sample_returns_as_is(self) -> None:
        assert cache.discard_before_reset([(100.0, 50.0)]) == [(100.0, 50.0)]


class TestConcurrency:
    def test_skips_cleanly_when_lock_is_held(self, tmp_path: Path) -> None:
        """If another writer holds the lock, append_rate_sample must no-op (not hang, not raise)."""
        import fcntl as _fcntl

        cache_file = os.path.join(str(tmp_path), "rate_samples")
        # Seed with one entry so we can detect whether the skipped call wrote.
        cache.append_rate_sample(cache_file, 1000.0, 10.0)

        lock_path = cache_file + ".lock"
        with open(lock_path, "w") as lf:
            _fcntl.flock(lf.fileno(), _fcntl.LOCK_EX)
            # Inside the held lock — this call must skip without hanging.
            cache.append_rate_sample(cache_file, 2000.0, 20.0)

        entries = cache.read_rate_samples(cache_file)
        assert entries == [(1000.0, 10.0)], (
            f"skipped call must not have written; got {entries}"
        )

    def test_atomic_rename_no_partial_writes(self, tmp_path: Path) -> None:
        """After each append, the file should be parseable (no partial lines)."""
        cache_file = os.path.join(str(tmp_path), "rate_samples")
        for i in range(50):
            cache.append_rate_sample(cache_file, 1000.0 + i * 60, float(i))
            # Read between each write — should always be well-formed
            entries = cache.read_rate_samples(cache_file)
            # Every entry must have parsed (no junk lines from partial writes)
            for ts, pct in entries:
                assert isinstance(ts, float)
                assert isinstance(pct, float)

    def test_parallel_subprocess_writes_all_land_or_skip(self, tmp_path: Path) -> None:
        """Many concurrent writers must either land a valid sample or skip cleanly.

        File must remain parseable and never corrupted.
        """
        import subprocess
        import sys as _sys

        cache_file = os.path.join(str(tmp_path), "rate_samples")
        # Spawn 10 subprocesses, each calling append_rate_sample once with a unique ts.
        # All pass min_interval=0 so min_interval is not the gate.
        snippet = (
            "import sys; sys.path.insert(0, {src!r});"
            "from workflow_statusline import cache;"
            "cache.append_rate_sample({file!r}, float(sys.argv[1]), float(sys.argv[2]),"
            " min_interval=0.0)"
        ).format(
            src=str(Path(__file__).resolve().parents[1] / "src"),
            file=cache_file,
        )

        procs = []
        for i in range(10):
            procs.append(
                subprocess.Popen(
                    [_sys.executable, "-c", snippet, str(1000 + i), str(i)],
                )
            )
        for p in procs:
            p.wait(timeout=10)

        # File must be readable and every line parseable
        entries = cache.read_rate_samples(cache_file)
        assert 1 <= len(entries) <= 10, (
            f"Expected 1..10 entries after concurrent appends; got {len(entries)}"
        )
        # No duplicates by (ts, pct) pair should be present (same-pid safeguard)
        assert len(entries) == len(set(entries))


class TestDefaultCachePath:
    def test_returns_path_under_xdg_cache(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        path = cache.rate_cache_path("five_hour")
        assert str(tmp_path) in path
        assert "claude-statusline" in path
        assert "rate-five_hour" in path

    def test_respects_xdg_cache_home(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        xdg = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CACHE_HOME", str(xdg))
        path = cache.rate_cache_path("seven_day")
        assert str(xdg) in path
        assert "rate-seven_day" in path
