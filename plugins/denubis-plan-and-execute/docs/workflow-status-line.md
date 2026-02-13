# Workflow Status Line

Two-line status bar for Claude Code. Line 1 shows project context (model, location, git changes, workflow breadcrumb). Line 2 shows resource usage (context window, cost, duration). When running multiple tabs on different features, tells you at a glance what each session is doing and where it is in the process.

## What It Looks Like

```
[Opus] worktree-auth +2~3 | CRDT ❯ executing-impl ❯ Phase 2 Step 3: auth middleware
████████░░ 85% (15% left) | $4.56 | 12m 0s
```

### Line 1: Project Context

- **Model** — which Claude model is active
- **Location** — smart: worktree name if in a worktree, repo basename otherwise, with `@branch` appended when the branch differs from the directory name (worktrees) or isn't main/master (normal repos)
- **Git changes** — staged (+N) and modified (~N) file counts (cached, refreshes every 5s)
- **Workflow breadcrumb** — only appears when a plan-and-execute skill is active

### Line 2: Resource Usage

- **Context bar** — 10-char progress bar, green < 70%, yellow 70-89%, red 90%+
- **Remaining %** — how much context window is left
- **Cost** — session API cost in USD
- **Duration** — wall-clock time since session start

### Workflow Breadcrumb Segments

1. **Feature** — short project/feature name (optional, set by orchestrating skills)
2. **Skill** — which skill is currently active (brainstorming, executing-impl, debugging, etc.)
3. **Context** — free-text description of current position in the process

Skill colours by category:

| Category | Skills | Colour |
|----------|--------|--------|
| Design | brainstorming, asking-clarifying-questions, writing-design-plans, starting-a-design-plan | blue |
| Planning | starting-an-implementation-plan, writing-implementation-plans | magenta |
| Execution | executing-impl, executing-an-implementation-plan | green |
| Review | code-review, requesting-code-review | cyan |
| Defensive | systematic-debugging, controlled-dependency-upgrade, restate-our-assumptions, proleptic-challenge | yellow |
| Gates | human-uat-gate, finishing-a-development-branch | cyan |

Context appears dimmed — it's the detail, not the headline.

## Setup

### Configure the status line

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-statusline.py"
  }
}
```

That's it. The script lives in the plugin directory and references are direct — no symlinks, no copies, no `~/.claude/bin`.

### Verify

Test with mock input:

```bash
echo '{"cwd":"'$PWD'","model":{"display_name":"Opus"},"context_window":{"used_percentage":42,"remaining_percentage":58},"cost":{"total_cost_usd":1.23,"total_duration_ms":185000}}' | python3 ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-statusline.py
```

Test with workflow state:

```bash
python3 -c "
import hashlib, json, os
cwd = os.getcwd()
h = hashlib.md5(cwd.encode()).hexdigest()
d = os.path.expanduser('~/.claude/workflow-state')
os.makedirs(d, exist_ok=True)
with open(f'{d}/{h}.json', 'w') as f:
    json.dump({'feature': 'test', 'skill': 'executing-impl', 'context': 'Phase 2 Step 3: auth middleware'}, f)
"
echo '{"cwd":"'$PWD'","model":{"display_name":"Opus"},"context_window":{"used_percentage":85,"remaining_percentage":15},"cost":{"total_cost_usd":4.56,"total_duration_ms":720000}}' | python3 ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-statusline.py
# Should show: [Opus] dir | test ❯ executing-impl ❯ Phase 2 Step 3: auth middleware
# Clean up:
python3 -c "import hashlib, os; os.remove(os.path.expanduser(f'~/.claude/workflow-state/{hashlib.md5(os.getcwd().encode()).hexdigest()}.json'))"
```

## How It Works

**Status line** (`workflow-statusline.py`): Python script that reads Claude Code's session JSON from stdin. Extracts model, directory, and cost info directly from the JSON. Detects worktrees vs normal repos for smart location display. Reads workflow state from `~/.claude/workflow-state/<md5-of-cwd>.json`. Renders two lines with ANSI colours.

**State writer** (`workflow-state.sh`): Bash script called by plan-and-execute skills at workflow transitions. Accepts `--skill`, `--context`, and `--feature` args. Writes JSON state keyed by working directory hash. If not installed, updates are silently skipped — the workflow works identically, you just don't see the breadcrumb.

Each skill has a "Workflow Status Line" section documenting its transitions.

## Requires

- Python 3 (for the status line renderer — stdlib only, no dependencies)
- `git` (for branch/status display)

### Optional

- `workflow-state.sh` installed for breadcrumb display. Without it, line 1 still shows model, location, and git info. Line 2 still shows context/cost/duration. Only the workflow breadcrumb is absent.
