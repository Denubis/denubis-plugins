# Project Context Inventory Implementation Plan

**Goal:** Create a project context inventory system that helps Claude Code subagents discover project-specific conventions

**Architecture:** Python discovery script scans project for CLAUDE.md files, MCP configs, and installed plugins, then outputs structured markdown. Command invokes script, wrapper skill filters and injects context into subagent prompts.

**Tech Stack:** Python 3.13+, shell scripts, Claude Code skills/commands

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-30

---

## Phase 2: Command Integration

**Goal:** `/inventory-project` command that invokes discovery script

**Codebase verification findings:**
- Commands directory exists at `plugins/denubis-plan-and-execute/commands/`
- Command files use YAML frontmatter (`description:`, optional `argument-hint:`) + Markdown content
- Most commands invoke skills rather than directly calling scripts
- Working directory handling is documented explicitly when needed
- Pattern established: commands describe purpose, invoke skills for execution

---

<!-- START_TASK_1 -->
### Task 1: Create the inventory-project command

**Files:**
- Create: `plugins/denubis-plan-and-execute/commands/inventory-project.md`

**Step 1: Create the command file**

```markdown
---
description: Generate project context inventory with discovered conventions
---

Generate a project context inventory file at `.ed3d/project-inventory.md`.

This command discovers:
- CLAUDE.md and AGENTS.md file locations with their sections
- Command patterns extracted from documentation (uv run, pytest, ruff, etc.)
- MCP server configurations from .mcp.json files
- Installed Claude Code plugins

The inventory file is used by skills to inject project context into subagent prompts.

## Prerequisites

You must be in a git repository. The discovery script uses git root as the project boundary.

## Execute

Run the Python discovery script using the Bash tool:

```bash
# Get project root
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# Find script in installed plugin location
# CLAUDE_PLUGIN_ROOT is available in hooks but not commands
# Use find to locate the most recently modified version
SCRIPT_PATH=$(find ~/.claude/plugins/cache -path "*denubis-plan-and-execute*/scripts/inventory-project.py" -type f 2>/dev/null | head -1)

# Fallback for development/local plugin
if [[ -z "$SCRIPT_PATH" ]]; then
  # Check if running from plugin source directory
  SCRIPT_PATH=$(find . -path "*/denubis-plan-and-execute/scripts/inventory-project.py" -type f 2>/dev/null | head -1)
fi

# Run discovery
python3 "$SCRIPT_PATH" --project-root "$PROJECT_ROOT" -o "$PROJECT_ROOT/.ed3d/project-inventory.md"
```

**Note:** Commands in Claude Code plugins don't have access to `CLAUDE_PLUGIN_ROOT` environment variable (only hooks do). The script path discovery uses `find` to locate the installed script.

## After Running

Report what was discovered to the user:

1. Read the generated `.ed3d/project-inventory.md` file
2. Summarize:
   - Number of CLAUDE.md files found
   - Number of AGENTS.md files found
   - Number of command patterns extracted
   - Number of MCP servers configured
   - Number of plugins installed
3. Note the commit SHA recorded for staleness detection

Example output:
```
Inventory generated at `.ed3d/project-inventory.md`

Discovered:
- 1 CLAUDE.md file (CLAUDE.md)
- 0 AGENTS.md files
- 3 command patterns (uv run pytest, ruff check, etc.)
- 0 MCP servers
- 8 installed plugins

Recorded at commit: abc1234

Skills can now access this context via the inject-project-context skill.
```
```

**Step 2: Verify file location**

```bash
ls -la /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/commands/inventory-project.md
```

Expected: File exists with correct content.

**Step 3: Commit**

```bash
git add plugins/denubis-plan-and-execute/commands/inventory-project.md
git commit -m "feat(plan-and-execute): add /inventory-project command"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Test the command end-to-end

**Files:**
- Execute: `plugins/denubis-plan-and-execute/scripts/inventory-project.py`
- Create: `.ed3d/project-inventory.md` (generated)

**Step 1: Ensure .ed3d directory exists**

```bash
mkdir -p /home/brian/people/Brian/brian-ed3d-plugins/.ed3d
```

**Step 2: Run the discovery script manually**

```bash
python3 /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/scripts/inventory-project.py \
  --project-root /home/brian/people/Brian/brian-ed3d-plugins \
  -o /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md
```

Expected stderr: `Wrote inventory to /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md`

**Step 3: Verify generated file**

```bash
cat /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md
```

Expected: Complete inventory with all sections (CLAUDE.md files, AGENTS.md files, Command Patterns, MCP Servers, Installed Plugins).

**Step 4: Verify commit SHA in output**

```bash
head -5 /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md
```

Expected: Shows `Generated at commit: \`<sha>\`` line with valid commit hash.

**Step 5: Clean up test file (don't commit generated inventory)**

```bash
rm /home/brian/people/Brian/brian-ed3d-plugins/.ed3d/project-inventory.md
```

**Step 6: Verify Phase 2 complete**

Check:
- [x] Command file exists at correct location
- [x] Script runs and produces output
- [x] Output file is written to correct location
- [x] Commit SHA is recorded
- [x] All sections are present

Phase 2 is complete when the command definition exists and the script can be invoked to generate the inventory file.
<!-- END_TASK_2 -->
