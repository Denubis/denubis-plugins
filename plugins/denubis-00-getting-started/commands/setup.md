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

### 5. Verify RTK (token minimisation)

Check if `rtk` is installed by running `rtk --version` via Bash. If it's not found, warn the user:

> RTK is not installed. RTK (Rust Token Killer) reduces token usage by 60-90% on dev tool output. Install from https://github.com/rtk-ai/rtk

If `rtk` is installed, verify the rewrite hook exists at `~/.claude/hooks/rtk-rewrite.sh`. If the hook file is missing, warn the user:

> RTK is installed but the auto-rewrite hook is missing at `~/.claude/hooks/rtk-rewrite.sh`. Without this hook, commands won't be automatically rewritten to use RTK.

Then check `~/.claude/settings.json` has a PreToolUse hook entry for the rtk-rewrite script. Look for a hook with command matching `rtk-rewrite.sh`. If missing, warn the user that the hook needs to be registered.

### 6. Verify cc-search-chats (if present)

If `~/.claude/plugins/marketplaces/cc-search-chats-marketplace/` exists, check that `cc-search-chats@cc-search-chats-marketplace` is enabled in settings.json.

### 7. Report

Summarize what was verified and what was changed. Include:
- Plugin enablement status
- Version sync results
- Status line configuration
- Any issues found and fixed
