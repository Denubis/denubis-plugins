---
description: Verify and configure denubis-plugins setup — status line, plugin enablement, version sync
allowed-tools: Read, Edit, Write, Bash, Glob, Grep, AskUserQuestion
---

# denubis-plugins Setup

Run all setup verification and configuration steps for the denubis-plugins ecosystem.

## Steps

### 0. Detect platform

Run `uname -s` via Bash. Check the output:
- If it contains `MINGW`, `MSYS`, or `CYGWIN`: this is **Windows (Git Bash)**. Set a mental flag `IS_WINDOWS=true`.
- Otherwise: this is **Linux/macOS**. Set `IS_WINDOWS=false`.

Report the detected platform to the user.

### 1. Locate the marketplace directory

The denubis-plugins marketplace should be at `~/.claude/plugins/marketplaces/denubis-plugins/`. Verify it exists and has a valid `.claude-plugin/marketplace.json`.

### 2. Verify all plugins are enabled

Read `~/.claude/settings.json` and check that every plugin listed in `.claude-plugin/marketplace.json` has a corresponding `true` entry in `enabledPlugins` (except `denubis-00-getting-started` which may be `false`).

**On Windows:** Skip enabling these plugins (they require bash/Unix tooling):
- `denubis-hook-pretooluse-dispatcher`
- `denubis-hook-rtk-rewrite`
- `denubis-hook-gh-fork-guard`
- `denubis-hook-branch-bg`

If any applicable plugins are missing, add them with `true` and tell the user what you added.

### 3. Check version sync

For each plugin in `marketplace.json`, verify that its `version` matches the `version` in the plugin's own `plugin.json` file. Report any mismatches.

Plugin locations follow one of two patterns:
- `plugins/<name>/.claude-plugin/plugin.json`
- `plugins/<name>/hooks/.claude-plugin/plugin.json` (for hook plugins)

### 4. Check prerequisites

**4a. Check for uv:**

Run `uv --version` via Bash. If not found:
- On Linux/macOS: suggest `curl -LsSf https://astral.sh/uv/install.sh | sh`
- On Windows: suggest `irm https://astral.sh/uv/install.ps1 | iex` (in PowerShell, outside Claude Code)

Several hooks (shortcut-detection, claudemd-reminder, code-quality-guard) require `uv` to run their Python scripts.

**4b. Check line endings (Windows only):**

If `IS_WINDOWS=true`, run `git config --global core.autocrlf` via Bash. If the result is `true`, warn:

> Your `core.autocrlf` is set to `true`. This converts LF to CRLF on checkout, which can break shell hook scripts with "bad interpreter" errors. The denubis-plugins repo includes a `.gitattributes` that forces `*.sh` and `*.py` files to LF, so you should be fine for this repo — but if you see hook errors, run: `git config --global core.autocrlf input`

### 5. Configure the status line

**Skip on Windows** — the status line uses tmux integration which is not available on Windows.

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

### 6. Configure PreToolUse:Bash dispatcher (Linux/macOS only)

**Skip entirely on Windows.**

The dispatcher plugin auto-discovers plugin hooks and runs hooks from a drop directory, solving Claude Code's parallel hook execution conflict.

**6a. Verify the dispatcher plugin is enabled:**

The `denubis-hook-pretooluse-dispatcher` plugin registers itself via its own `hooks.json`. Verify it's enabled in settings.json. If not, enable it.

**6b. Verify plugin convention files:**

Plugin hooks are auto-discovered. The dispatcher finds any enabled plugin with an executable `hooks/pretooluse-bash.sh`. Check that the fork-guard plugin has this file and it's executable (`chmod +x` if needed).

**6c. Create the drop directory for non-plugin hooks:**
```bash
mkdir -p ~/.claude/hooks/pretooluse-bash.d
```

**6d. Set up RTK (if installed):**

Check if `rtk` is installed by running `rtk --version` via Bash. If not found, warn:

> RTK is not installed. RTK (Rust Token Killer) reduces token usage by 60-90% on dev tool output. Install from https://github.com/rtk-ai/rtk

If installed, verify `~/.claude/hooks/rtk-rewrite.sh` exists, then symlink it into the drop directory:
```bash
ln -sf ~/.claude/hooks/rtk-rewrite.sh ~/.claude/hooks/pretooluse-bash.d/50-rtk-rewrite
```

**6e. Remove standalone PreToolUse:Bash hooks from settings.json:**

Check `~/.claude/settings.json` for any `PreToolUse` hooks with matcher `Bash`. The dispatcher replaces these — they must be removed or they will conflict. Specifically look for:
- `rtk-rewrite.sh` registered directly in settings.json hooks
- Any other PreToolUse:Bash entries

Remove them from settings.json (the dispatcher calls them via the drop directory instead).

**6f. Verify with diagnostics:**

Run the dispatcher's `--list` flag to verify all hooks are discovered correctly:
```bash
<dispatcher-path>/pretooluse-bash-dispatcher.sh --list
```

### 7. Verify cc-search-chats (if present)

If `~/.claude/plugins/marketplaces/cc-search-chats-marketplace/` exists, check that `cc-search-chats@cc-search-chats-marketplace` is enabled in settings.json.

### 8. Report

Summarise what was verified and what was changed. Include:
- Detected platform
- Plugin enablement status (noting any skipped on Windows)
- Version sync results
- Prerequisites check (uv, line endings)
- Status line configuration (or skipped on Windows)
- Dispatcher configuration (or skipped on Windows)
- Any issues found and fixed
