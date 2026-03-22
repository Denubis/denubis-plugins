"""Tests for tmux window rename with caching and lock file deference."""

from __future__ import annotations

from unittest import mock

import pytest

from workflow_statusline import tmux


@pytest.fixture
def tmux_env(monkeypatch):
    """Set TMUX and TMUX_PANE env vars for a typical tmux session."""
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,12345,0")
    monkeypatch.setenv("TMUX_PANE", "%5")


class TestMaybeRename:
    def test_renames_window_when_no_cache_or_lock(self, tmux_env, tmp_path):
        """AC4.1: TMUX set, TMUX_PANE=%5, no lock, no cache -> calls tmux rename-window."""
        with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
            tmux.maybe_rename("testrepo")
            mock_sub.run.assert_called_once_with(
                ["tmux", "rename-window", "Cl:testrepo"],
                check=False,
                capture_output=True,
            )

    def test_skips_rename_when_cache_matches(self, tmux_env, tmp_path):
        """AC4.2: Cached name matches -> subprocess NOT called."""
        # Pre-populate cache so it matches
        cache_file = "/tmp/claude-statusline-tmux-5"
        with open(cache_file, "w") as f:
            f.write("testrepo")

        try:
            with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
                tmux.maybe_rename("testrepo")
                mock_sub.run.assert_not_called()
        finally:
            import os

            os.unlink(cache_file)

    def test_skips_rename_when_lock_file_exists(self, tmux_env, tmp_path):
        """AC4.3: Lock file exists -> subprocess NOT called."""
        lock_file = "/tmp/claude-statusline-tmux-lock-5"
        with open(lock_file, "w") as f:
            f.write("")

        try:
            with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
                tmux.maybe_rename("testrepo")
                mock_sub.run.assert_not_called()
        finally:
            import os

            os.unlink(lock_file)

    def test_noop_when_tmux_not_set(self, monkeypatch):
        """AC4.4: TMUX not in env -> no subprocess call, no exception."""
        monkeypatch.delenv("TMUX", raising=False)
        monkeypatch.delenv("TMUX_PANE", raising=False)

        with mock.patch("workflow_statusline.tmux.subprocess") as mock_sub:
            tmux.maybe_rename("testrepo")
            mock_sub.run.assert_not_called()
