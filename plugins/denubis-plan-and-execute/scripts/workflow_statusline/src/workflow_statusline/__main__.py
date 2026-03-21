"""Entry point: parse session JSON, compose two status lines, print them."""

from __future__ import annotations

import json
import sys

from workflow_statusline.colours import (
    BLUE,
    CYAN,
    DIM,
    GREEN,
    RED,
    RST,
    YELLOW,
)
from workflow_statusline.git import git_changes, git_location


def main() -> None:
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

    # ── Location ──────────────────────────────────────────────────────
    location = git_location(cwd)
    staged, modified = git_changes(cwd)

    # ── Line 1: model, location, git changes, code churn ──────────────
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

    # ── Line 2: context bar, cost, duration ──────────────────────────
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
