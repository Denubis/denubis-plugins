"""Git location and change detection for statusline."""

from __future__ import annotations

import hashlib
import os
import subprocess

from workflow_statusline import cache


def _git(cwd: str, *args: str) -> str:
    """Run a git command and return stripped stdout. Raises on failure."""
    return subprocess.check_output(
        ["git", "-C", cwd, *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def git_location(cwd: str) -> str:
    """Determine smart location string: worktree name, repo@branch, or dir."""
    try:
        _git(cwd, "rev-parse", "--git-dir")
    except Exception:
        return os.path.basename(cwd)

    # Get branch
    try:
        branch = _git(cwd, "branch", "--show-current")
    except Exception:
        branch = ""

    # Detect worktree: compare toplevel to common dir
    try:
        toplevel = _git(cwd, "rev-parse", "--show-toplevel")
        common_dir = _git(cwd, "rev-parse", "--git-common-dir")
        common_dir = os.path.realpath(common_dir)

        is_worktree = os.path.realpath(common_dir) != os.path.realpath(
            os.path.join(toplevel, ".git")
        ) and os.path.isdir(common_dir)
    except Exception:
        is_worktree = False
        toplevel = cwd

    display_name = os.path.basename(toplevel)

    if is_worktree:
        if branch and branch != display_name:
            return f"{display_name}@{branch}"
        return display_name
    else:
        if branch and branch not in ("main", "master"):
            return f"{display_name}@{branch}"
        return display_name


def git_changes(cwd: str) -> tuple[int, int]:
    """Get staged count and modified count. Cached to /tmp with 5s TTL."""
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()
    cache_file = f"/tmp/claude-statusline-git-cache-{dir_hash}"

    cached = cache.read_if_fresh(cache_file, max_age=5)
    if cached is None:
        try:
            staged_out = _git(cwd, "diff", "--cached", "--numstat")
            modified_out = _git(cwd, "diff", "--numstat")
            staged = len(staged_out.split("\n")) if staged_out else 0
            modified = len(modified_out.split("\n")) if modified_out else 0
            cache.write(cache_file, f"{staged}|{modified}")
        except Exception:
            cache.write(cache_file, "0|0")

        cached = cache.read_if_fresh(cache_file, max_age=5)
        if cached is None:
            return 0, 0

    parts = cached.split("|")
    staged = int(parts[0]) if len(parts) > 0 and parts[0] else 0
    modified = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    return staged, modified
