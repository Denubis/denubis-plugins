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
