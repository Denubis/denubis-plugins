"""Entry point: parse session JSON, compose two status lines, print them."""

from __future__ import annotations

import json
import sys
import time

from workflow_statusline import cache
from workflow_statusline.ratelimit import format_rate_limit

from workflow_statusline.bar import boss_hp_bar
from workflow_statusline.colours import (
    BLUE,
    BOLD,
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

    agent_name = data.get("agent", {}).get("name", "")
    ctx = data.get("context_window", {})
    context_window_tokens = ctx.get("context_window_size", 200_000)
    pct = int(ctx.get("used_percentage") or 0)
    cost_data = data.get("cost", {})
    cost = cost_data.get("total_cost_usd") or 0
    duration_ms = cost_data.get("total_duration_ms") or 0
    lines_added = cost_data.get("total_lines_added") or 0
    lines_removed = cost_data.get("total_lines_removed") or 0

    session_id = data.get("session_id", "")
    rate_limits = data.get("rate_limits")

    # ── Location ──────────────────────────────────────────────────────
    location = git_location(cwd)
    staged, modified = git_changes(cwd)

    # ── Line 1: location, git changes, agent or churn ─────────────────
    if location.is_on_main and not location.is_worktree:
        line1 = f"{RED}{BOLD}\u2717MAIN{RST}"
    else:
        line1 = f"{BLUE}{location.display}{RST}"

    git_extra = ""
    if staged > 0:
        git_extra += f"{GREEN}+{staged}{RST}"
    if modified > 0:
        git_extra += f"{YELLOW}~{modified}{RST}"
    if git_extra:
        line1 += f" {git_extra}"

    if agent_name:
        line1 += f" {DIM}|{RST} {CYAN}agt:{agent_name}{RST}"
    elif lines_added or lines_removed:
        line1 += f" {DIM}|{RST} {GREEN}+{lines_added}{RST}/{RED}-{lines_removed}{RST}"

    # ── Rate limits ────────────────────────────────────────────────────
    rate_parts: list[str] = []
    if rate_limits and session_id:
        now = time.time()
        for window_key, label in [("five_hour", "5h"), ("seven_day", "7d")]:
            window = rate_limits.get(window_key)
            if not window:
                continue
            used_pct = window.get("used_percentage", 0)
            resets_at = window.get("resets_at", 0)
            cache_file = f"/tmp/claude-statusline-rate-{session_id}-{window_key}"
            cache.append_rate_sample(cache_file, now, used_pct)
            samples = cache.read_rate_samples(cache_file)
            display = format_rate_limit(label, used_pct, resets_at, samples, now)

            if display.is_exhausting:
                rate_parts.append(f"{RED}{label}:{display.pct}%{RST} {display.time_str}")
            elif display.time_str:
                rate_parts.append(f"{label}:{display.pct}% {display.time_str}")
            else:
                rate_parts.append(f"{label}:{display.pct}%")

    # ── Line 2: context bar, rate limits, cost, duration ─────────────
    bar = boss_hp_bar(pct, context_window_tokens)

    mins = duration_ms // 60000
    secs = (duration_ms % 60000) // 1000

    line2 = f"{bar} {pct}%"
    if rate_parts:
        line2 += f" {DIM}|{RST} {' '.join(rate_parts)}"
    line2 += f" {DIM}|{RST} {YELLOW}${cost:.2f}{RST} {DIM}|{RST} {mins}m {secs}s"

    print(line1)
    print(line2)


if __name__ == "__main__":
    main()
