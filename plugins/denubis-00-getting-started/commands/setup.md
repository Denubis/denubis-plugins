---
description: Verify and configure denubis-plugins setup — status line, plugin enablement, version sync
allowed-tools: Read, Edit, Write, Bash, Glob, Grep, AskUserQuestion
---

# denubis-plugins Setup

Run all setup verification and configuration steps for the denubis-plugins ecosystem.

## Step 0. Detect platform

Run `uname -s` via Bash. Set a mental flag:
- Output contains `MINGW` or `MSYS` → **Windows (Git Bash)**
- Output is `Darwin` → **macOS**
- Output is `Linux` → **Linux**

Report the detected platform to the user before continuing.

On **Windows (Git Bash)**, steps 4 (status line) and 5 (dispatcher) are skipped — they require Unix-only tooling. Note this when reporting.

## Steps

### 1. Locate the marketplace directory

The denubis-plugins marketplace should be at `~/.claude/plugins/marketplaces/denubis-plugins/`. Verify it exists and has a valid `.claude-plugin/marketplace.json`.

**Windows note:** Git Bash expands `~` to the Windows user profile (e.g. `C:/Users/Name`). This is correct.

### 2. Verify all plugins are enabled

Read `~/.claude/settings.json` and check that every plugin listed in `.claude-plugin/marketplace.json` has a corresponding `true` entry in `enabledPlugins` (except `denubis-00-getting-started` which may be `false`).

**Windows (Git Bash):** The following plugins should be **disabled** (`false`) because they require Unix-only tooling:
- `denubis-hook-pretooluse-dispatcher`
- `denubis-hook-rtk-rewrite`
- `denubis-hook-gh-fork-guard`
- `denubis-hook-branch-bg`

If any of these are enabled on Windows, warn the user and offer to disable them.

If any cross-platform plugins are missing, add them with `true` and tell the user what you added.

### 3. Check version sync

For each plugin in `marketplace.json`, verify that its `version` matches the `version` in the plugin's own `plugin.json` file. Report any mismatches.

Plugin locations follow one of two patterns:
- `plugins/<name>/.claude-plugin/plugin.json`
- `plugins/<name>/hooks/.claude-plugin/plugin.json` (for hook plugins)

### 4. Configure the status line (Linux/macOS only)

> **Windows:** Skip this step. The status line script depends on tmux integration that is not available on Windows.

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

### 5. Configure PreToolUse:Bash dispatcher (Linux/macOS only)

> **Windows:** Skip this step entirely. The dispatcher is a bash script that uses Unix paths and tools not available in Git Bash.

The dispatcher plugin auto-discovers plugin hooks and runs hooks from a drop directory, solving Claude Code's parallel hook execution conflict.

**5a. Verify the dispatcher plugin is enabled:**

The `denubis-hook-pretooluse-dispatcher` plugin registers itself via its own `hooks.json`. Verify it's enabled in settings.json. If not, enable it.

**5b. Verify plugin convention files:**

Plugin hooks are auto-discovered. The dispatcher finds any enabled plugin with an executable `hooks/pretooluse-bash.sh`. Check that the fork-guard plugin has this file and it's executable (`chmod +x` if needed).

**5c. Create the drop directory for non-plugin hooks:**
```bash
mkdir -p ~/.claude/hooks/pretooluse-bash.d
```

**5d. Set up RTK (if installed):**

Check if `rtk` is installed by running `rtk --version` via Bash. If not found, warn:

> RTK is not installed. RTK (Rust Token Killer) reduces token usage by 60-90% on dev tool output. Install from https://github.com/rtk-ai/rtk

If installed, verify `~/.claude/hooks/rtk-rewrite.sh` exists, then symlink it into the drop directory:
```bash
ln -sf ~/.claude/hooks/rtk-rewrite.sh ~/.claude/hooks/pretooluse-bash.d/50-rtk-rewrite
```

**5e. Remove standalone PreToolUse:Bash hooks from settings.json:**

Check `~/.claude/settings.json` for any `PreToolUse` hooks with matcher `Bash`. The dispatcher replaces these — they must be removed or they will conflict. Specifically look for:
- `rtk-rewrite.sh` registered directly in settings.json hooks
- Any other PreToolUse:Bash entries

Remove them from settings.json (the dispatcher calls them via the drop directory instead).

**5f. Verify with diagnostics:**

Run the dispatcher's `--list` flag to verify all hooks are discovered correctly:
```bash
<dispatcher-path>/pretooluse-bash-dispatcher.sh --list
```

### 6. Check line endings (Windows only)

> **Linux/macOS:** Skip this step.

Run `git config --global core.autocrlf` via Bash.

- If the output is `true`, warn the user:

> **Line ending problem detected.** `core.autocrlf=true` converts LF to CRLF, which breaks bash shebangs in hook scripts. Run:
> ```bash
> git config --global core.autocrlf input
> ```
> Then re-checkout the marketplace to fix existing files:
> ```bash
> cd ~/.claude/plugins/marketplaces/denubis-plugins && git checkout -- .
> ```

- If the output is `input` or `false`, line endings are fine.

### 7. Check uv availability

Run `uv --version` via Bash. If not found, warn:

> **uv is not installed.** Several hook scripts (shortcut detection, CLAUDE.md reminder, code quality guard) require `uv` to run Python. Install from https://docs.astral.sh/uv/

On Windows, if uv is not found in Git Bash but might be installed for PowerShell, suggest:

> If you installed uv via PowerShell, you may need to add its directory to your Windows PATH so Git Bash can find it. Typically: `%USERPROFILE%\.local\bin`

### 8. Verify cc-search-chats (if present)

If `~/.claude/plugins/marketplaces/cc-search-chats-marketplace/` exists, check that `cc-search-chats@cc-search-chats-marketplace` is enabled in settings.json.

### 9. Report

Summarize what was verified and what was changed. Include:
- Detected platform
- Plugin enablement status (and any Windows-skipped plugins)
- Version sync results
- Status line configuration (or "skipped on Windows")
- Dispatcher configuration (or "skipped on Windows")
- Line ending configuration (Windows only)
- uv availability
- Any issues found and fixed
