# Workflow Status Line

Two-line status bar for Claude Code. Line 1 shows project context (model, location, git changes, code churn). Line 2 shows resource usage (context window, cost, duration). All data derived from the session JSON that Claude Code passes on stdin — no external state files, no permissions required.

## What It Looks Like

```
[Opus] worktree-auth +2~3 | +156/-23
████████░░ 85% (15% left) | $4.56 | 12m 0s
```

### Line 1: Project Context

- **Model** — which Claude model is active
- **Location** — smart: worktree name if in a worktree, repo basename otherwise, with `@branch` appended when the branch differs from the directory name (worktrees) or isn't main/master (normal repos)
- **Git changes** — staged (+N) and modified (~N) file counts (cached, refreshes every 5s)
- **Code churn** — session-level lines added/removed (+N/-N), from session JSON

### Line 2: Resource Usage

- **Context bar** — 10-char progress bar, green < 70%, yellow 70-89%, red 90%+
- **Remaining %** — how much context window is left
- **Cost** — session API cost in USD
- **Duration** — wall-clock time since session start

## Setup

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-statusline.py"
  }
}
```

### Verify

Test with mock input:

```bash
echo '{"cwd":"'$PWD'","model":{"display_name":"Opus"},"context_window":{"used_percentage":42,"remaining_percentage":58},"cost":{"total_cost_usd":1.23,"total_duration_ms":185000,"total_lines_added":156,"total_lines_removed":23}}' | python3 ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-statusline.py
```

## How It Works

**Status line** (`workflow-statusline.py`): Python script that reads Claude Code's session JSON from stdin. Extracts model, directory, cost, and code churn directly from the JSON. Detects worktrees vs normal repos for smart location display. Runs git commands for branch detection and staged/modified file counts (cached 5s). Renders two lines with ANSI colours.

No external state files. No Bash permission prompts. Everything comes from the session JSON or cached git queries run by the script itself (outside Claude's sandbox).

## Requires

- Python 3 (stdlib only, no dependencies)
- `git` (for branch/status display)
