# Workflow Status Line

Show where you are in the plan-and-execute workflow as a breadcrumb in Claude Code's status line. When you're running 4 tabs on different features, this tells you at a glance which one needs you and what kind of engagement it wants.

## What It Looks Like

```
94 ❯ CRDT Cloning ❯ Implementing
94 ❯ CRDT Cloning ❯ Implementing ❯ ENGAGE
94 ❯ CRDT Cloning ❯ Code Review
94 ❯ Auth ❯ Brainstorming ❯ Think
```

Four levels:

1. **Feature** — short project/branch name
2. **Phase** — current implementation phase name (from design doc)
3. **Step** — workflow step (Design, Brainstorming, Implementing, Code Review, etc.)
4. **Human action** — only appears when Claude is waiting for you

Level 4 colours escalate with effort required:

| Action | Treatment | Meaning |
|--------|-----------|---------|
| Approve | dim white | Glance and click |
| Review | cyan | Sit and read |
| Respond | yellow | Type something |
| Think | bold magenta | Evaluate critically |
| **ENGAGE** | **red bg, white fg** | **Leave terminal, go test** |

Level 3 colours distinguish workflow steps:

| Step | Colour |
|------|--------|
| Design | blue |
| Clarification | cyan |
| Brainstorming | blue |
| Impl Planning | magenta |
| Implementing | green |
| Code Review | cyan |
| Finishing | white |
| Debugging | yellow |
| Dep Review | white |

## Setup

### 1. Install the state writer

```bash
mkdir -p ~/.claude/bin
cp plugins/denubis-plan-and-execute/scripts/workflow-state.sh ~/.claude/bin/workflow-state
chmod +x ~/.claude/bin/workflow-state
```

Or symlink if you prefer to track updates:

```bash
mkdir -p ~/.claude/bin
ln -sf "$(pwd)/plugins/denubis-plan-and-execute/scripts/workflow-state.sh" ~/.claude/bin/workflow-state
```

### 2. Configure the status line

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/path/to/plugins/denubis-plan-and-execute/scripts/workflow-statusline.sh"
  }
}
```

Or copy/symlink to a stable location first:

```bash
ln -sf "$(pwd)/plugins/denubis-plan-and-execute/scripts/workflow-statusline.sh" ~/.claude/bin/workflow-statusline
```

Then in settings:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/bin/workflow-statusline"
  }
}
```

### 3. Verify

Start a Claude Code session and check that the status line appears at the bottom. It will be empty until a plan-and-execute skill writes state.

Test manually:

```bash
~/.claude/bin/workflow-state --feature "test" --phase "Setup" --step "Design" --human "engage"
echo '{"cwd":"'$PWD'"}' | ~/.claude/bin/workflow-statusline
# Should show: test ❯ Setup ❯ Design ❯ ENGAGE (with colours)
~/.claude/bin/workflow-state --clear
```

## How It Works

Skills write a JSON state file to `~/.claude/workflow-state/<hash>.json` (keyed by working directory) at each workflow transition. The status line script reads this file and renders the breadcrumb with ANSI colours.

Each skill has a "Workflow Status Line" section documenting its transitions. If `~/.claude/bin/workflow-state` isn't installed, the updates are silently skipped — the workflow works identically either way.

## Requires

- `jq` (for the status line renderer)
- `md5sum` (for directory hashing — standard on Linux, use `md5` on macOS)

### macOS Note

If using macOS, the `md5sum` command may not exist. Replace `md5sum` with `md5 -q` in both scripts, or install `coreutils` via Homebrew.
