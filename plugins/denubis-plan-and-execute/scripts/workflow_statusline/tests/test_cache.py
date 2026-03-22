"""Tests for workflow_statusline.cache module."""

from __future__ import annotations

import os
import time
from pathlib import Path

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
