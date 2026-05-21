"""Git location and change detection for statusline."""

from __future__ import annotations

import hashlib
import os
import subprocess
from typing import NamedTuple

from workflow_statusline import cache


class LocationInfo(NamedTuple):
    display: str       # e.g., "ed3d@feat" or "ed3d"
    is_on_main: bool   # True if branch is main/master
    is_worktree: bool  # True if in a git worktree


def _git(cwd: str, *args: str) -> str:
    """Run a git command and return stripped stdout. Raises on failure."""
    return subprocess.check_output(
        ["git", "-C", cwd, *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _should_show_branch(branch: str, display_name: str, is_worktree: bool) -> bool:
    """Decide whether to append @branch to the display name."""
    if not branch:
        return False
    if is_worktree:
        return branch != display_name
    return branch not in ("main", "master")


def git_location(cwd: str) -> LocationInfo:
    """Determine smart location string: worktree name, repo@branch, or dir."""
    try:
        _git(cwd, "rev-parse", "--git-dir")
    except Exception:
        return LocationInfo(
            display=os.path.basename(cwd), is_on_main=False, is_worktree=False
        )

    try:
        branch = _git(cwd, "branch", "--show-current")
    except Exception:
        branch = ""

    try:
        toplevel = _git(cwd, "rev-parse", "--show-toplevel")
        # git-common-dir is relative to cwd when not a worktree; resolve against
        # cwd, not Python's CWD, or we mis-detect when Python runs from a dir
        # that happens to have its own .git.
        common_dir = os.path.realpath(
            os.path.join(cwd, _git(cwd, "rev-parse", "--git-common-dir"))
        )
        is_worktree = (
            common_dir != os.path.realpath(os.path.join(toplevel, ".git"))
            and os.path.isdir(common_dir)
        )
    except Exception:
        is_worktree = False
        toplevel = cwd

    display_name = os.path.basename(toplevel)
    is_on_main = branch in ("main", "master")

    if _should_show_branch(branch, display_name, is_worktree):
        display = f"{display_name}@{branch}"
    else:
        display = display_name

    return LocationInfo(display=display, is_on_main=is_on_main, is_worktree=is_worktree)


def _count_lines(output: str) -> int:
    """Count non-empty lines in git numstat output."""
    return len(output.split("\n")) if output else 0


def _parse_cached_changes(cached: str) -> tuple[int, int]:
    """Parse a 'staged|modified' cache string into counts."""
    parts = cached.split("|")
    staged = int(parts[0]) if parts[0] else 0
    modified = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    return staged, modified


def git_changes(cwd: str) -> tuple[int, int]:
    """Get staged count and modified count. Cached to /tmp with 5s TTL."""
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()
    cache_file = f"/tmp/claude-statusline-git-cache-{dir_hash}"

    cached = cache.read_if_fresh(cache_file, max_age=5)
    if cached is not None:
        return _parse_cached_changes(cached)

    try:
        staged = _count_lines(_git(cwd, "diff", "--cached", "--numstat"))
        modified = _count_lines(_git(cwd, "diff", "--numstat"))
    except Exception:
        staged, modified = 0, 0

    cache.write(cache_file, f"{staged}|{modified}")
    return staged, modified
