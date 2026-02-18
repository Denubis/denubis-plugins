---
description: Verify and configure denubis-plugins setup — status line, plugin enablement, version sync
allowed-tools: Read, Edit, Write, Bash, Glob, Grep, AskUserQuestion
---

# denubis-plugins Setup

Run all setup verification and configuration steps for the denubis-plugins ecosystem.

## Steps

### 1. Locate the marketplace directory

The denubis-plugins marketplace should be at `~/.claude/plugins/marketplaces/denubis-plugins/`. Verify it exists and has a valid `.claude-plugin/marketplace.json`.

### 2. Verify all plugins are enabled

Read `~/.claude/settings.json` and check that every plugin listed in `.claude-plugin/marketplace.json` has a corresponding `true` entry in `enabledPlugins` (except `denubis-00-getting-started` which may be `false`).

If any are missing, add them with `true` and tell the user what you added.

### 3. Check version sync

For each plugin in `marketplace.json`, verify that its `version` matches the `version` in the plugin's own `plugin.json` file. Report any mismatches.

Plugin locations follow one of two patterns:
- `plugins/<name>/.claude-plugin/plugin.json`
- `plugins/<name>/hooks/.claude-plugin/plugin.json` (for hook plugins)

### 4. Configure the status line

Check if `~/.claude/settings.json` has a `statusLine` entry. If not, or if it points to the old `.sh` script, update it to:

```json
{
  "statusLine": {
    "type": "command",
    "command": "<marketplace-path>/plugins/denubis-plan-and-execute/scripts/workflow-statusline.py"
  }
}
```

Where `<marketplace-path>` is the **absolute path** to the denubis-plugins marketplace directory.

Verify the Python script exists and is executable (`chmod +x` if needed).

### 5. Configure PreToolUse:Bash dispatcher

The dispatcher plugin runs all PreToolUse:Bash hooks sequentially from a drop directory, solving Claude Code's parallel hook execution conflict.

**5a. Create the drop directory:**
```bash
mkdir -p ~/.claude/hooks/pretooluse-bash.d
```

**5b. Set up the fork-guard hook:**

Find the fork-guard wrapper script. It will be at one of:
- `<marketplace-path>/plugins/denubis-hook-gh-fork-guard/hooks/gh-fork-guard-wrapper.sh`

Create a symlink:
```bash
ln -sf <path-to-wrapper>/gh-fork-guard-wrapper.sh ~/.claude/hooks/pretooluse-bash.d/10-fork-guard
```

Verify the wrapper and Python script are both executable (`chmod +x` if needed).

**5c. Set up RTK (if installed):**

Check if `rtk` is installed by running `rtk --version` via Bash. If not found, warn:

> RTK is not installed. RTK (Rust Token Killer) reduces token usage by 60-90% on dev tool output. Install from https://github.com/rtk-ai/rtk

If installed, verify `~/.claude/hooks/rtk-rewrite.sh` exists, then symlink it:
```bash
ln -sf ~/.claude/hooks/rtk-rewrite.sh ~/.claude/hooks/pretooluse-bash.d/50-rtk-rewrite
```

**5d. Remove standalone PreToolUse:Bash hooks from settings.json:**

Check `~/.claude/settings.json` for any `PreToolUse` hooks with matcher `Bash`. The dispatcher replaces these — they must be removed or they will conflict. Specifically look for:
- `rtk-rewrite.sh` registered directly in settings.json hooks
- Any other PreToolUse:Bash entries

Remove them from settings.json (the dispatcher calls them via the drop directory instead).

**5e. Verify the dispatcher is registered:**

The `denubis-hook-pretooluse-dispatcher` plugin registers itself via its own `hooks.json`. Verify the plugin is enabled in settings.json. If not, enable it.

### 6. Verify cc-search-chats (if present)

If `~/.claude/plugins/marketplaces/cc-search-chats-marketplace/` exists, check that `cc-search-chats@cc-search-chats-marketplace` is enabled in settings.json.

### 7. Report

Summarize what was verified and what was changed. Include:
- Plugin enablement status
- Version sync results
- Status line configuration
- Any issues found and fixed
