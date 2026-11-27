# Workflow Status Line

Two-line status bar for Claude Code and Antigravity CLI (`agy`). Line 1 shows location, git changes, and agent/churn context. Line 2 shows a boss HP context bar, rate limits, cost, and (for Claude Code) session duration. All data is derived from the session JSON piped on stdin.

## What It Looks Like

```text
ed3d@feat +2~3 | +156/-23
████████████████▒▒▒▒ 80% | 5h:23% < 40% | 7d:48% ≮ 42% | DayStop:9pm | $4.56 | 12m 0s
```

When on main/master outside a worktree, line 1 appends a red `✗MAIN` warning after the location.

When an agent is active: `ed3d@feat +2~3 | agt:researcher`

### Line 1: Project Context

- **Location** — worktree name if in a worktree, repo basename otherwise, with `@branch` appended when the branch differs from the directory name (worktrees) or isn't main/master (normal repos)
- **`✗MAIN` warning** — red, bold. Shown when on main/master in a non-worktree repo
- **Git changes** — staged (`+N`) and modified (`~N`) file counts (cached 5s)
- **Agent or churn** — `agt:<name>` (cyan) when an agent is active; otherwise session-level `+N/-N` lines added/removed

### Line 2: Resource Usage

- **Boss HP bar + used %** — 20-char progress bar followed by percentage consumed. For 1M context (>=500k tokens): segment colours at 20% boundaries (green → cyan → yellow → magenta → red). For smaller contexts: simple green → yellow (70%) → red (90%) gradient
- **Rate limits** — `5h:23% < 40%` and `7d:48% ≮ 42%` compare each window's consumed percentage with the even-consumption pace line scaled over local active hours (07:00–22:00). Green `<` when below pace; red `≮` at or above pace
- **DayStop / WeekStop** — derived from the 7d window via Theil-Sen median slope over up to 24h of recent samples (requiring at least 30 samples spanning 2h). Shows projected clock-time to cross today's 22:00 active-hours target (`DayStop:go to sleep!` when already past) or 100% before reset (`WeekStop`)
- **Cost** — session API cost in USD (`cost.total_cost_usd` in Claude Code; `cost.total_usd` in Antigravity when reported)
- **Duration** — wall-clock time since session start (Claude Code)

### tmux Window Rename

Automatically renames the tmux window to `Cl:<location>` (Claude Code) or `Ag:<location>` (Antigravity CLI). Skipped when unchanged (cached 24h), when `tmux-agent-attention` owns the window title, or when a lock file exists at `/tmp/claude-statusline-tmux-lock-<pane_id>`. Create the lock file to prevent renames.

### Session Naming

The `exec-session-naming` skill (invoked by design plan, implementation plan, execution, and debugging skills) spawns a Sonnet subagent to generate a domain-specific slug, renames the tmux window to `Cl:<slug>`, writes a lock file to prevent statusline from overwriting the name, and prompts the user with `/rename <slug>`.

## Setup

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run --frozen --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow_statusline --package workflow-statusline workflow-statusline",
    "refreshInterval": 30
  }
}
```

`refreshInterval: 30` re-runs the statusline every 30 seconds. Without it, the script only fires on Claude Code redraw events (tool calls, messages), so rate-limit samples are collected irregularly — making burn-rate forecasts unreliable across idle stretches. The 30 s cadence matches the minimum sample interval used by `append_rate_sample`.

### Antigravity CLI

Add to `~/.gemini/antigravity-cli/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run --frozen --project /path/to/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow_statusline --package workflow-statusline workflow-statusline"
  }
}
```

Antigravity sends `product: "antigravity"` and `quota.gemini-5h` / `quota.gemini-weekly` on stdin. The statusline writes Antigravity's rate history and quota snapshots under `$XDG_CACHE_HOME/agy-statusline/` (separate from Claude's cache) so `byobu-agy-quota` can render the weekly ratio pill, and renames the tmux window to `Ag:<location>`.

### Verify

Test with mock input:

```bash
echo '{"cwd":"'$PWD'","context_window":{"used_percentage":42,"remaining_percentage":58,"context_window_size":1000000},"cost":{"total_cost_usd":1.23,"total_duration_ms":185000,"total_lines_added":156,"total_lines_removed":23}}' \
  | uv run --frozen --project plugins/denubis-plan-and-execute/scripts/workflow_statusline --package workflow-statusline workflow-statusline
```

## Package Structure

Located at `scripts/workflow_statusline/`. Modules and launchers:

| Module / path | Purpose |
|---------------|---------|
| `__main__` | Entry point: parse Claude Code or Antigravity JSON, persist quota caches, compose lines, print |
| `agy_quota` | Byobu weekly quota pill (`byobu-agy-quota`, `Ʌ` on dark cerulean) reading `$XDG_CACHE_HOME/agy-statusline/quota-seven_day` |
| `bar` | Boss HP bar rendering with context-size-aware colouring |
| `cache` | Namespaced file-based caching and atomic quota snapshots |
| `claude_quota` | Byobu weekly quota pill (`byobu-claude-quota`, `*` on dark terracotta) reading `$XDG_CACHE_HOME/claude-statusline/quota-seven_day` |
| `codex_quota` | Byobu weekly quota pill (`byobu-codex-quota`, `§` on dark graphite) reading Codex state SQLite and rollouts |
| `colours` | ANSI colour constants |
| `git` | Location detection (worktree-aware) and change counts |
| `quota_cell` | Shared Byobu brand-pill renderer, active-hours pace, reset label, and validated snapshot parser |
| `ratelimit` | Active-hours pace and Theil-Sen burn-rate forecasting |
| `tmux` | Window rename with lock file and title-owner deference |
| `byobu/30_*_quota` | Executable 30-second Byobu launchers for Claude, Codex, and Antigravity |

## Requires

- Python >= 3.14
- `uv` (for package execution)
- `git` (for branch/status display)
