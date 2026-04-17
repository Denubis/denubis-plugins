# Workflow Status Line

Two-line status bar for Claude Code. Line 1 shows location, git changes, and agent/churn context. Line 2 shows a boss HP context bar, rate limits, cost, and duration. All data derived from the session JSON that Claude Code passes on stdin.

## What It Looks Like

```
ed3d@feat +2~3 | +156/-23
████████████████▒▒▒▒ 80% | 5h:23% 3pm | 7d:48% Fri 8pm | DayStop:9pm | $4.56 | 12m 0s
```

When on main/master outside a worktree, line 1 shows a red `✗MAIN` warning instead of the location.

When an agent is active: `ed3d@feat +2~3 | agt:researcher`

### Line 1: Project Context

- **Location** — worktree name if in a worktree, repo basename otherwise, with `@branch` appended when the branch differs from the directory name (worktrees) or isn't main/master (normal repos)
- **`✗MAIN` warning** — red, bold. Shown when on main/master in a non-worktree repo
- **Git changes** — staged (`+N`) and modified (`~N`) file counts (cached 5s)
- **Agent or churn** — `agt:<name>` (cyan) when an agent is active; otherwise session-level `+N/-N` lines added/removed

### Line 2: Resource Usage

- **Boss HP bar + used %** — 20-char progress bar followed by percentage consumed. For 1M context (>=500k tokens): segment colours at 20% boundaries (green → cyan → yellow → magenta → red). For smaller contexts: simple green → yellow (70%) → red (90%) gradient
- **Rate limits** — `5h:23% 3pm` and `7d:48% Fri 8pm` report each Anthropic window's used percentage and the projected clock-time of 100% ("when *they* stop you"). Projection uses an idle-trimmed active-time rate, blended between a short window (10 min for 5h, 1 h for 7d) and a long window (5 h and 24 h respectively). Red when both windows agree the window will exhaust before reset (Google SRE multi-window gate); green when ETA is defined and the SRE gate is cool; yellow when there is no defined ETA yet
- **DayStop** — derived from the 7d window: "when *should I* stop today". Target is `(day_in_window / 7) × 100%` anchored to the reset hour. Shows the clock-time your current burn rate will cross today's pace target. Displays `DayStop:go to sleep!` when already past the target
- **Cost** — session API cost in USD
- **Duration** — wall-clock time since session start

### tmux Window Rename

Automatically renames the tmux window to `Cl:<location>`. Skipped when unchanged (cached 24h) or when a lock file exists at `/tmp/claude-statusline-tmux-lock-<pane_id>`. Create the lock file to prevent renames.

### Session Naming

The `exec-session-naming` skill (invoked by design plan, implementation plan, execution, and debugging skills) spawns a Haiku subagent to generate a domain-specific slug, renames the tmux window to `Cl:<slug>`, writes a lock file to prevent statusline from overwriting the name, and prompts the user with `/rename <slug>`.

## Setup

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow_statusline workflow-statusline",
    "refreshInterval": 30
  }
}
```

`refreshInterval: 30` re-runs the statusline every 30 seconds. Without it, the script only fires on Claude Code redraw events (tool calls, messages), so rate-limit samples are collected irregularly — making burn-rate forecasts unreliable across idle stretches. The 30 s cadence matches the minimum sample interval used by `append_rate_sample`.

### Migration from v1

If your `statusLine` command points to the old script path (`scripts/workflow-statusline.py`), update it to the `uv run` command above. The old single-file script has been replaced by a uv-managed package.

### Verify

Test with mock input:

```bash
echo '{"cwd":"'$PWD'","context_window":{"used_percentage":42,"remaining_percentage":58,"context_window_size":1000000},"cost":{"total_cost_usd":1.23,"total_duration_ms":185000,"total_lines_added":156,"total_lines_removed":23}}' \
  | uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow_statusline workflow-statusline
```

## Package Structure

Located at `scripts/workflow_statusline/`. Modules:

| Module | Purpose |
|--------|---------|
| `__main__` | Entry point: parse session JSON, compose lines, print |
| `bar` | Boss HP bar rendering with context-size-aware colouring |
| `cache` | File-based caching (read/write with TTL) |
| `colours` | ANSI colour constants |
| `git` | Location detection (worktree-aware) and change counts |
| `ratelimit` | Idle-trimmed multi-window burn-rate forecasting (SRE multi-window gate, DayStop pace target, clock-time formatter) |
| `tmux` | Window rename with lock file deference |

## Requires

- Python >= 3.12
- `uv` (for package execution)
- `git` (for branch/status display)
