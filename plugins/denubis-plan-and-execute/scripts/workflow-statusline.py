#!/usr/bin/env python3
"""Claude Code status line renderer.

Two-line display:
  Line 1: [Model] dir | git branch +staged ~modified | workflow breadcrumb
  Line 2: context bar pct% | $cost | duration

Workflow breadcrumb (when active):
  feature > phase > step > human action

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

STEP_COLOUR = {
    "Design": BLUE,
    "Clarification": CYAN,
    "Brainstorming": BLUE,
    "Impl Planning": MAGENTA,
    "Implementing": GREEN,
    "Code Review": CYAN,
    "Finishing": WHITE,
    "Debugging": YELLOW,
    "Dep Review": WHITE,
}

HUMAN_STYLE = {
    "approve": f"{DIM}{WHITE}",
    "review": CYAN,
    "respond": YELLOW,
    "think": f"{BOLD}{MAGENTA}",
    "engage": f"{BOLD}\033[41;37m",
}

HUMAN_LABEL = {
    "approve": "Approve",
    "review": "Review",
    "respond": "Respond",
    "think": "Think",
    "engage": "ENGAGE",
}


def git_info(cwd: str) -> tuple[str, int, int]:
    """Get git branch, staged count, modified count. Cached to /tmp."""
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()
    cache_file = f"/tmp/claude-statusline-git-cache-{dir_hash}"
    cache_max_age = 5

    stale = True
    if os.path.exists(cache_file):
        stale = (time.time() - os.path.getmtime(cache_file)) > cache_max_age

    if stale:
        try:
            subprocess.check_output(
                ["git", "-C", cwd, "rev-parse", "--git-dir"],
                stderr=subprocess.DEVNULL,
            )
            branch = subprocess.check_output(
                ["git", "-C", cwd, "branch", "--show-current"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
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
                f.write(f"{branch}|{staged}|{modified}")
        except Exception:
            with open(cache_file, "w") as f:
                f.write("||")

    with open(cache_file) as f:
        parts = f.read().strip().split("|")

    branch = parts[0] if len(parts) > 0 else ""
    staged = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    modified = int(parts[2]) if len(parts) > 2 and parts[2] else 0
    return branch, staged, modified


def workflow_crumb(cwd: str) -> str:
    """Read workflow state and render breadcrumb."""
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()
    state_file = os.path.expanduser(f"~/.claude/workflow-state/{dir_hash}.json")

    if not os.path.exists(state_file):
        return ""

    with open(state_file) as f:
        state = json.load(f)

    feature = state.get("feature", "")
    phase = state.get("phase", "")
    step = state.get("step", "")
    human = state.get("human")

    if not feature and not phase and not step:
        return ""

    sep = f"{DIM} \u276f {RST}"
    parts = []

    if feature:
        parts.append(f"{BOLD}{WHITE}{feature}{RST}")
    if phase:
        parts.append(f"{WHITE}{phase}{RST}")
    if step:
        colour = STEP_COLOUR.get(step, WHITE)
        parts.append(f"{colour}{step}{RST}")
    if human and human != "null":
        style = HUMAN_STYLE.get(human, WHITE)
        label = HUMAN_LABEL.get(human, human)
        parts.append(f"{style} {label} {RST}")

    return sep.join(parts)


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

    # ── Git ───────────────────────────────────────────────────────────
    branch, staged, modified = git_info(cwd)

    # ── Workflow ──────────────────────────────────────────────────────
    crumb = workflow_crumb(cwd)

    # ── Line 1: model, dir, git, workflow ─────────────────────────────
    dir_name = os.path.basename(cwd)
    line1 = f"{CYAN}[{model}]{RST} {BLUE}{dir_name}{RST}"

    if branch:
        git_extra = ""
        if staged > 0:
            git_extra += f"{GREEN}+{staged}{RST}"
        if modified > 0:
            git_extra += f"{YELLOW}~{modified}{RST}"
        line1 += f" {DIM}|{RST} {WHITE}{branch}{RST} {git_extra}"

    if crumb:
        line1 += f" {DIM}|{RST} {crumb}"

    # ── Line 2: context bar, cost, duration ───────────────────────────
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
