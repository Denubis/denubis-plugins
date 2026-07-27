"""Tests for tmux window rename with caching and lock file deference."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest import mock

import pytest
from workflow_statusline import tmux


@pytest.fixture
def tmux_env(monkeypatch, tmp_path):
    """Set TMUX and TMUX_PANE env vars with a unique pane ID to avoid collisions."""
    # Use tmp_path hash as pane ID so cache/lock files are unique per test run.
    pane_id = f"test-{hash(tmp_path) % 100000}"
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")
    monkeypatch.setenv("TMUX_PANE", f"%{pane_id}")
    cache_file = f"/tmp/claude-statusline-tmux-{pane_id}"
    lock_file = f"/tmp/claude-statusline-tmux-lock-{pane_id}"
    yield pane_id, cache_file, lock_file
    # Cleanup any files created during test
    for f in (cache_file, lock_file):
        with contextlib.suppress(FileNotFoundError):
            Path(f).unlink()


class TestMaybeRename:
    def test_registered_owner_flag_skips_only_legacy_title_writer(
        self, tmux_env, monkeypatch
    ):
        """Registered ownership disables this legacy rename side effect."""
        monkeypatch.setenv(
            "TMUX_AGENT_ATTENTION_RUN_ID",
            "00000000-0000-0000-0000-000000000601",
        )
        monkeypatch.setenv("TMUX_AGENT_ATTENTION_OWNS_WINDOW_TITLE", "1")

        with (
            mock.patch("workflow_statusline.tmux.subprocess") as mock_sub,
            mock.patch("workflow_statusline.tmux.cache") as mock_cache,
        ):
            tmux.maybe_rename("testrepo")

        mock_sub.run.assert_not_called()
        mock_cache.read_if_fresh.assert_not_called()
        mock_cache.write.assert_not_called()

    def test_renames_window_when_no_cache_or_lock(self, tmux_env):
        """AC4.1: TMUX set, no lock, no cache -> targets the exact tmux pane."""
        pane_id, _cache_file, _lock_file = tmux_env
        with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
            tmux.maybe_rename("testrepo")
            mock_sub.run.assert_called_once_with(
                ["tmux", "rename-window", "-t", f"%{pane_id}", "Cl:testrepo"],
                check=False,
                capture_output=True,
            )

    def test_skips_rename_when_cache_matches(self, tmux_env):
        """AC4.2: Cached name matches -> subprocess NOT called."""
        _pane_id, cache_file, _lock_file = tmux_env
        with Path(cache_file).open("w") as f:
            f.write("testrepo")

        with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
            tmux.maybe_rename("testrepo")
            mock_sub.run.assert_not_called()

    def test_skips_rename_when_lock_file_exists(self, tmux_env):
        """AC4.3: Lock file exists -> subprocess NOT called."""
        _pane_id, _cache_file, lock_file = tmux_env
        with Path(lock_file).open("w") as f:
            f.write("")

        with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
            tmux.maybe_rename("testrepo")
            mock_sub.run.assert_not_called()

    def test_noop_when_tmux_not_set(self, monkeypatch):
        """AC4.4: TMUX not in env -> no subprocess call, no exception."""
        monkeypatch.delenv("TMUX", raising=False)
        monkeypatch.delenv("TMUX_PANE", raising=False)

        with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
            tmux.maybe_rename("testrepo")
            mock_sub.run.assert_not_called()
