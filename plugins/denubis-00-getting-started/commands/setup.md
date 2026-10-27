---
description: Verify and configure denubis-plugins setup — status line, plugin enablement, version sync, script environment check and repair
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

**5d. Remove standalone PreToolUse:Bash hooks from settings.json:**

Check `~/.claude/settings.json` for any `PreToolUse` hooks with matcher `Bash` other than the approver (`approver.py`), which is intentionally standalone. The dispatcher replaces non-plugin rewrite hooks — any such entries must be removed or they will conflict. Remove them from settings.json (the dispatcher calls them via the drop directory instead).

**5e. Verify with diagnostics:**

Run the dispatcher's `--list` flag to verify all hooks are discovered correctly:
```bash
uv run python <dispatcher-path>/pretooluse-bash-dispatcher.py --list
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

### 8. Check and repair plugin script environments

If step 7 found no `uv`, skip this step and report it as skipped.

A hook launcher that cannot start its hook shows `<plugin>: <hook> could not run (uv exit N); run /denubis-00-getting-started:setup to check and repair plugin environments`. This step finds the script environment that fails, shows uv's error, and repairs what a network fetch can repair. It changes only uv's cache. Do not delete, move or redirect the uv cache, and do not edit any script. Run every `uv` command in this step from the session's working directory, as hooks and skills are run.

**8a. List the installed copies of enabled plugins.**

Read `~/.claude/settings.json` and `~/.claude/plugins/installed_plugins.json`. Take every `enabledPlugins` key that ends in `@denubis-plugins` and is `true`. Look up the same key under `plugins` in `installed_plugins.json`. Its value is a list of install records; take the `installPath` of every record. Report these without checking them further:
- an enabled key with no entry under `plugins`, as "enabled but not installed";
- an `installPath` that does not exist on disk, as "install record points at a missing directory".

**8b. Find and group each copy's PEP 723 scripts.**

For each `installPath`, use the Grep tool with pattern `^# /// script$`, glob `*.py`, path set to the `installPath`, and output mode `files_with_matches`. List each plugin with its count of matched scripts. A count of zero means no `.py` file in that copy has a PEP 723 header line; files without the `.py` suffix are not scanned.

Put each matched script in one group by its path inside the `installPath`:
- **Hook and tool scripts:** the path starts with `hooks/` or `scripts/`. Hooks run at every session or tool call and must work, and these scripts are light, so step 8c resolves them without asking.
- **Skill scripts:** every other path, for example `skills/using-bibliography/ingest.py`. Some declare large dependencies; the bibliography scripts include `docling`, `easyocr` and `pymupdf`, which can take gigabytes on a fresh cache. Step 8d resolves them only after the user agrees.

`uv sync --script` builds or updates a script's cached environment without running the script. `--offline` restricts it to locally cached data, and `--check` exits with an error when the environment is not up to date without changing anything.

**8c. Resolve hook and tool scripts: offline, then online.**

For a script whose parent directory is `<installPath>/hooks`, copy the flags its hook launcher passes to `uv run`, except `--no-project`, which `uv sync` rejects, and write the `installPath` where the launcher has its plugin-root variable. The launcher is the `command` string in the hooks file that the plugin's `.claude-plugin/plugin.json` names in `hooks` (default `hooks/hooks.json`). For the current launchers this is:

```bash
uv sync --project "<installPath>" --script "<script>" --python '>=3.14' --offline
```

`--project` makes uv read `pyproject.toml` and `uv.toml` from the plugin directory upward, plus the user's own `uv.toml`, exactly as the hook does; the session's working directory is not read.

For every other hook or tool script:

```bash
uv sync --script "<script>" --offline
```

Exit 0 means the environment builds from the local uv cache. For each script that fails offline:
1. Run the same command without `--offline`. This fetches what is missing.
2. If that online run fails, keep uv's complete stderr for the report, unshortened. The script is still failing.
3. If it succeeds, run the offline command once more. Passing now means the environment was repaired. Failing again means the environment resolves only with network access; ADR 0046 records a git dependency pinned by a short hash as one cause.

**8d. List skill scripts, then resolve them only with consent.**

1. For each skill script, Read its `# /// script` block and note its `dependencies` list. Then check its environment without building it:

   ```bash
   uv sync --script "<script>" --check --offline
   ```

2. Classify each script from that command's exit status and output:
   - **ready**: exit 0. uv prints `Would make no changes`.
   - **needs download**: non-zero exit, and the output has a `Would download N packages` line (`package` when N is 1).
   - **builds from cache**: non-zero exit, a `Would install` line, and no `Would download` line.
   - **cannot resolve offline**: any other non-zero exit. Keep uv's error.
3. If every skill script is ready, report that and skip the question.
4. Otherwise ask the user once with AskUserQuestion. List every script that is not ready, with its plugin, path, `dependencies` and classification. Offer three answers: resolve all of them; resolve only those that build from cache; resolve none.
5. For each script the user chose, run `uv sync --script "<script>"` without `--offline`. Report a failure with uv's complete stderr, unshortened.

Report every skill script the user did not choose as "not resolved: skipped by choice", with its classification. A line saying environments resolved covers only the scripts this step resolved. It says nothing about skipped skill scripts, which can still fail the first time their skill runs.

**8e. Check shared-library pins (this repository only).**

Run this sub-step only when `<marketplace>/pyproject.toml`, where `<marketplace>` is the directory from step 1, contains a `[tool.uv.workspace]` table. Otherwise report "pin check skipped: the marketplace checkout has no uv workspace".

1. Read the `members` list from that table. Each member is a path relative to `<marketplace>`.
2. Use the Grep tool with glob `*.py`, path `<marketplace>` and output mode `files_with_matches` twice: once with pattern `^# /// script$` to count the checkout's PEP 723 scripts, and once with pattern `^# .*\bsubdirectory\s*=` to find candidate consumers. Report both counts, so that zero consumers is distinguishable from a scan that saw no scripts.
3. Read the `# /// script` block of each candidate. A `[tool.uv.sources]` entry is either an inline table, `name = { git = "...", rev = "...", subdirectory = "..." }`, or a `[tool.uv.sources.<name>]` table with the same keys. Keep the entries whose `subdirectory` equals one of `members`. List every other entry that has a `subdirectory` as outside this check.
4. For each kept entry, print the last commit that touched the library:

   ```bash
   git -C "<marketplace>" log -1 --format=%H -- "<subdirectory>"
   ```

5. Classify the entry:
   - **current**: `rev` has 40 characters and equals the printed hash.
   - **short hash**: `rev` has fewer than 40 characters. ADR 0046 records that uv 0.13.5 fetches such a pin on every run, so it fails offline.
   - **stale pin**: the printed hash does not start with `rev`.
   - **missing rev**: the entry has no `rev` key.
   - **no library history**: the git command printed nothing.

   A short `rev` that is also not a prefix of the printed hash is both short and stale. Report every entry that is not current with the consumer path, `rev`, and printed hash. Do not edit pins here. A pin moves only through the release procedure in `denubis-extending-agents:maintaining-a-marketplace`.

### 9. Verify cc-search-chats (if present)

If `~/.claude/plugins/marketplaces/cc-search-chats-marketplace/` exists, check that `cc-search-chats@cc-search-chats-marketplace` is enabled in settings.json.

### 10. Report

Summarize what was verified and what was changed. Include:
- Detected platform
- Plugin enablement status (and any Windows-skipped plugins)
- Version sync results
- Status line configuration (or "skipped on Windows")
- Dispatcher configuration (or "skipped on Windows")
- Line ending configuration (Windows only)
- uv availability
- Script environments (or "skipped: uv not found"):
  - per plugin, the number of hook and tool scripts and of skill scripts found;
  - each hook or tool script repaired online, resolving only online, or still failing, with uv's complete error for a failing script;
  - each skill script's classification, the user's answer, and each skill script resolved, failed with uv's complete error, or "not resolved: skipped by choice";
  - enabled plugins that are not installed, and install records that point at a missing directory
- Shared-library pins: the two scan counts and every entry that is not current, with its classification (or "pin check skipped: the marketplace checkout has no uv workspace")
- Any issues found and fixed
