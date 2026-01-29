# Project Context Inventory Implementation Plan

**Goal:** Create a project context inventory system that helps Claude Code subagents discover project-specific conventions

**Architecture:** Python discovery script scans project for CLAUDE.md files, MCP configs, and installed plugins, then outputs structured markdown. Command invokes script, wrapper skill filters and injects context into subagent prompts.

**Tech Stack:** Python 3.13+, shell scripts, Claude Code skills/commands

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-30

---

## Phase 5: Staleness Detection Hook

**Goal:** Session hook that suggests refresh when inventory is stale

**Codebase verification findings:**
- `plugins/denubis-plan-and-execute/hooks/` exists with `hooks.json` and `session-start.sh`
- hooks.json format: `{"hooks": {"SessionStart": [{"matcher": "...", "hooks": [{"type": "command", "command": "..."}]}]}}`
- Session start hooks use `"SessionStart"` event type with optional `matcher` for conditions
- Shell scripts use `#!/usr/bin/env bash` with `set -euo pipefail`
- Output via JSON to stdout with `hookSpecificOutput` containing `hookEventName` and `additionalContext`
- Existing session-start.sh hook already registered - new hook will be added alongside it

---

<!-- START_TASK_1 -->
### Task 1: Create the staleness detection shell script

**Files:**
- Create: `plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh`

**Step 1: Create the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Check if .ed3d/project-inventory.md exists and is stale
# Stale = generated at a commit that is >20 commits behind current HEAD

# Find project root (git root)
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
INVENTORY_FILE="${PROJECT_ROOT}/.ed3d/project-inventory.md"

# If no inventory file, exit silently
if [[ ! -f "${INVENTORY_FILE}" ]]; then
    exit 0
fi

# Extract the commit SHA from the inventory file
# Format: "Generated at commit: `<sha>`"
INVENTORY_SHA=$(grep -oP 'Generated at commit: `\K[a-f0-9]+' "${INVENTORY_FILE}" 2>/dev/null || echo "")

# If no SHA found or invalid, exit silently
if [[ -z "${INVENTORY_SHA}" ]]; then
    exit 0
fi

# Get current HEAD SHA
CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null) || exit 0

# If same commit, inventory is fresh
if [[ "${INVENTORY_SHA}" == "${CURRENT_SHA}" ]]; then
    exit 0
fi

# Count commits between inventory SHA and current HEAD
# Use git rev-list to count commits
COMMITS_BEHIND=$(git rev-list --count "${INVENTORY_SHA}..HEAD" 2>/dev/null || echo "0")

# If more than 20 commits behind, warn user
if [[ "${COMMITS_BEHIND}" -gt 20 ]]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Project inventory is stale (${COMMITS_BEHIND} commits behind). Consider running /inventory-project to refresh."
  }
}
EOF
fi

exit 0
```

**Step 2: Make script executable**

```bash
chmod +x /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh
```

**Step 3: Test script manually**

First, create a test inventory file:
```bash
mkdir -p /home/brian/people/Brian/brian-ed3d-plugins/.ed3d
echo "Generated at commit: \`$(git -C /home/brian/people/Brian/brian-ed3d-plugins rev-parse HEAD~25 2>/dev/null || echo 'abc1234')\`" > /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md
```

Run the script:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && ./plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh
```

Expected: JSON output with staleness warning (if commit history allows), or silent exit if not enough commits.

**Step 4: Clean up test file**

```bash
rm /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md
```

**Step 5: Commit**

```bash
git add plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh
git commit -m "feat(plan-and-execute): add inventory staleness detection hook"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Register the hook in hooks.json

**Files:**
- Modify: `plugins/denubis-plan-and-execute/hooks/hooks.json`

**Step 1: Read current hooks.json**

```bash
cat /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/hooks/hooks.json
```

Current content (from investigation):
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

**Step 2: Add staleness hook to SessionStart array**

Update the file to add the new hook as a second entry in the SessionStart array:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh"
          }
        ]
      },
      {
        "matcher": "startup|resume|clear",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/inventory-staleness.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Note:** Using `"startup|resume|clear"` matcher (without `compact`) because:
- On startup: Check for stale inventory
- On resume: Check for stale inventory
- On clear: Check for stale inventory
- On compact: Skip (compaction doesn't change project state, just conversation state)

**Step 3: Verify JSON is valid**

```bash
python3 -m json.tool /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/hooks/hooks.json
```

Expected: Valid JSON output with no errors.

**Step 4: Commit**

```bash
git add plugins/denubis-plan-and-execute/hooks/hooks.json
git commit -m "feat(plan-and-execute): register inventory staleness hook"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Verify Phase 5 complete

**Files:**
- Read: `plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh`
- Read: `plugins/denubis-plan-and-execute/hooks/hooks.json`

**Step 1: Verify hook script exists and is executable**

```bash
ls -la /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh
```

Expected: File exists with executable permission (`-rwxr-xr-x` or similar).

**Step 2: Verify hook is registered**

```bash
grep "inventory-staleness" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/hooks/hooks.json
```

Expected: Line showing `"command": "${CLAUDE_PLUGIN_ROOT}/hooks/inventory-staleness.sh"`.

**Step 3: Verify Phase 5 complete**

Check:
- [x] inventory-staleness.sh script exists and is executable
- [x] Script reads commit SHA from inventory file
- [x] Script compares against current HEAD
- [x] Script outputs JSON warning if >20 commits behind
- [x] Hook is registered in hooks.json with SessionStart event
- [x] Hook uses appropriate matcher (startup|resume|clear)

Phase 5 is complete when the staleness detection hook fires on session start and warns when inventory is stale.
<!-- END_TASK_3 -->
