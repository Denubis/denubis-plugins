#!/usr/bin/env python3
"""Claude Code status line renderer.

Two-line display:
  Line 1: [Model] location | git-changes | code-churn
  Line 2: context bar pct% | $cost | duration

Location logic:
  - Worktree: show worktree dir name
  - Normal repo: show repo basename
  - Append @branch if branch differs from displayed name

All data derived from session JSON on stdin — no external state files.

Configure in ~/.claude/settings.json:
  "statusLine": {
    "type": "command",
    "command": "/path/to/workflow-statusline.py"
  }
"""

import hashlib
import json
import os
import subprocess
import sys
import time

# ── ANSI 16 colour codes (theme-adaptive) ────────────────────────────

RST = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"


def git_location(cwd: str) -> str:
    """Determine smart location string: worktree name, repo@branch, or dir."""
    try:
        subprocess.check_output(
            ["git", "-C", cwd, "rev-parse", "--git-dir"],
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return os.path.basename(cwd)

    # Get branch
    try:
        branch = subprocess.check_output(
            ["git", "-C", cwd, "branch", "--show-current"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        branch = ""

    # Detect worktree: compare toplevel to common dir
    try:
        toplevel = subprocess.check_output(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        common_dir = subprocess.check_output(
            ["git", "-C", cwd, "rev-parse", "--git-common-dir"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        # Resolve to absolute for comparison
        common_dir = os.path.realpath(common_dir)

        is_worktree = os.path.realpath(common_dir) != os.path.realpath(
            os.path.join(toplevel, ".git")
        ) and os.path.isdir(common_dir)
    except Exception:
        is_worktree = False
        toplevel = cwd

    display_name = os.path.basename(toplevel)

    if is_worktree:
        # In a worktree — show worktree dir name
        # Append @branch only if branch differs from dir name
        if branch and branch != display_name:
            return f"{display_name}@{branch}"
        return display_name
    else:
        # Normal repo — show repo name, append @branch if not main/master
        if branch and branch not in ("main", "master"):
            return f"{display_name}@{branch}"
        return display_name


def git_changes(cwd: str) -> tuple[int, int]:
    """Get staged count and modified count. Cached to /tmp."""
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()
    cache_file = f"/tmp/claude-statusline-git-cache-{dir_hash}"
    cache_max_age = 5

    stale = True
    if os.path.exists(cache_file):
        stale = (time.time() - os.path.getmtime(cache_file)) > cache_max_age

    if stale:
        try:
            staged_out = subprocess.check_output(
                ["git", "-C", cwd, "diff", "--cached", "--numstat"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            modified_out = subprocess.check_output(
                ["git", "-C", cwd, "diff", "--numstat"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            staged = len(staged_out.split("\n")) if staged_out else 0
            modified = len(modified_out.split("\n")) if modified_out else 0
            with open(cache_file, "w") as f:
                f.write(f"{staged}|{modified}")
        except Exception:
            with open(cache_file, "w") as f:
                f.write("0|0")

    with open(cache_file) as f:
        parts = f.read().strip().split("|")

    staged = int(parts[0]) if len(parts) > 0 and parts[0] else 0
    modified = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    return staged, modified


def main():
    data = json.load(sys.stdin)

    cwd = data.get("cwd", "")
    if not cwd:
        return

    model = data.get("model", {}).get("display_name", "?")
    ctx = data.get("context_window", {})
    pct = int(ctx.get("used_percentage") or 0)
    remaining = ctx.get("remaining_percentage")
    if remaining is not None:
        remaining = int(remaining)
    cost_data = data.get("cost", {})
    cost = cost_data.get("total_cost_usd") or 0
    duration_ms = cost_data.get("total_duration_ms") or 0
    lines_added = cost_data.get("total_lines_added") or 0
    lines_removed = cost_data.get("total_lines_removed") or 0

    # ── Location ────────────────────────────────────────────────────────
    location = git_location(cwd)
    staged, modified = git_changes(cwd)

    # ── Line 1: model, location, git changes, code churn ────────────────
    line1 = f"{CYAN}[{model}]{RST} {BLUE}{location}{RST}"

    git_extra = ""
    if staged > 0:
        git_extra += f"{GREEN}+{staged}{RST}"
    if modified > 0:
        git_extra += f"{YELLOW}~{modified}{RST}"
    if git_extra:
        line1 += f" {git_extra}"

    if lines_added or lines_removed:
        line1 += f" {DIM}|{RST} {GREEN}+{lines_added}{RST}/{RED}-{lines_removed}{RST}"

    # ── Line 2: context bar, cost, duration ──────────────────────────────
    if pct >= 90:
        bar_color = RED
    elif pct >= 70:
        bar_color = YELLOW
    else:
        bar_color = GREEN

    bar_width = 10
    filled = pct * bar_width // 100
    empty = bar_width - filled
    bar = "\u2588" * filled + "\u2591" * empty

    mins = duration_ms // 60000
    secs = (duration_ms % 60000) // 1000

    line2 = f"{bar_color}{bar}{RST} {pct}%"
    if remaining is not None:
        line2 += f" {DIM}({remaining}% left){RST}"
    line2 += f" {DIM}|{RST} {YELLOW}${cost:.2f}{RST} {DIM}|{RST} {mins}m {secs}s"

    print(line1)
    print(line2)


if __name__ == "__main__":
    main()
