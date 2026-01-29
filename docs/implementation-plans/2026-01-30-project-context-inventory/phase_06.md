# Project Context Inventory Implementation Plan

**Goal:** Create a project context inventory system that helps Claude Code subagents discover project-specific conventions

**Architecture:** Python discovery script scans project for CLAUDE.md files, MCP configs, and installed plugins, then outputs structured markdown. Command invokes script, wrapper skill filters and injects context into subagent prompts.

**Tech Stack:** Python 3.13+, shell scripts, Claude Code skills/commands

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-30

---

## Phase 6: Documentation and Version Bump

**Goal:** Update plugin documentation and version

**Codebase verification findings:**
- `plugins/denubis-plan-and-execute/README.md` exists with comprehensive documentation
- `plugins/denubis-plan-and-execute/commands/how-to-customize.md` exists with guidance file documentation
- `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` exists, current version 2.1.0
- `.claude-plugin/marketplace.json` exists, version 2.1.0 for this plugin
- `CHANGELOG.md` exists at repo root with `## [plugin-name] [version]` format
- Changelog entries go at top, include New/Changed/Fixed sections as applicable

---

<!-- START_TASK_1 -->
### Task 1: Update README.md with new command and skill

**Files:**
- Modify: `plugins/denubis-plan-and-execute/README.md`

**Step 1: Add new section for /inventory-project command**

Find the "Utility Commands" section (or similar section listing commands like `/flesh-it-out`). Add a new subsection:

```markdown
### /inventory-project

Discover and record project context for subagent injection.

**What it does:**
- Finds CLAUDE.md and AGENTS.md files
- Extracts command patterns (uv run, pytest, ruff, etc.)
- Enumerates MCP servers from .mcp.json files
- Lists installed Claude Code plugins

**Output:** Generates `.ed3d/project-inventory.md` with all discovered context.

**Staleness detection:** A session hook compares the inventory's commit SHA against current HEAD. If >20 commits behind, it suggests refreshing.

**Usage:**
```
/inventory-project
```

Run this when:
- Starting work on a new project
- After significant configuration changes (new CLAUDE.md files, new MCP servers)
- When the staleness warning appears
```

**Step 2: Add section about project context injection**

In the "Project Customization" section (or create one if needed), add:

```markdown
### Project Context Injection

Subagents spawned by plan-and-execute skills automatically receive project context when `.ed3d/project-inventory.md` exists.

**What's injected:**
- Command patterns: How to run tests, linting, etc.
- MCP servers: What tools are available
- Installed plugins: What capabilities exist
- Documentation locations: Where CLAUDE.md/AGENTS.md files are

**Skills that use project context:**
- `executing-an-implementation-plan` - Full context for implementation agents
- `requesting-code-review` - Full context for reviewers
- `writing-implementation-plans` - Command patterns for plan writing
- `brainstorming` - Context awareness during design

**Graceful degradation:** If no inventory exists, skills proceed without project context.
```

**Step 3: Verify changes**

```bash
grep -n "inventory-project\|project-inventory" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/README.md
```

Expected: Multiple lines showing the new documentation.

**Step 4: Commit**

```bash
git add plugins/denubis-plan-and-execute/README.md
git commit -m "docs(plan-and-execute): document /inventory-project command and context injection"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Update how-to-customize.md

**Files:**
- Modify: `plugins/denubis-plan-and-execute/commands/how-to-customize.md`

**Step 1: Add reference to inventory system**

Find the section that discusses `.ed3d/` files. Add a note about the inventory file:

```markdown
### Project Inventory (Auto-generated)

In addition to the guidance files above, you can generate a project context inventory:

```
/inventory-project
```

This creates `.ed3d/project-inventory.md` containing:
- CLAUDE.md and AGENTS.md locations and sections
- Command patterns from documentation
- MCP servers and installed plugins

Unlike guidance files, the inventory is auto-generated. Re-run `/inventory-project` when:
- You add new CLAUDE.md or AGENTS.md files
- You change MCP server configuration
- A staleness warning appears (>20 commits behind)

The inventory is read by skills when spawning subagents, so they inherit project-specific context automatically.
```

**Step 2: Verify changes**

```bash
grep -n "inventory" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/commands/how-to-customize.md
```

Expected: Lines showing the new inventory section.

**Step 3: Commit**

```bash
git add plugins/denubis-plan-and-execute/commands/how-to-customize.md
git commit -m "docs(plan-and-execute): reference inventory system in how-to-customize"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Bump plugin version

**Files:**
- Modify: `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json`

**Step 1: Read current version**

```bash
cat /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
```

Current version: 2.1.0

**Step 2: Bump to 2.2.0**

Update the version field:

Before:
```json
"version": "2.1.0",
```

After:
```json
"version": "2.2.0",
```

**Step 3: Verify JSON is valid**

```bash
python3 -m json.tool /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
```

Expected: Valid JSON output with version 2.2.0.

**Step 4: Commit**

```bash
git add plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
git commit -m "chore(plan-and-execute): bump version to 2.2.0"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Update marketplace.json

**Files:**
- Modify: `.claude-plugin/marketplace.json`

**Step 1: Find denubis-plan-and-execute entry**

```bash
grep -A5 '"denubis-plan-and-execute"' /home/brian/people/Brian/brian-ed3d-plugins/.claude-plugin/marketplace.json
```

**Step 2: Update version to match plugin.json**

Find the denubis-plan-and-execute entry and update:

Before:
```json
"version": "2.1.0",
```

After:
```json
"version": "2.2.0",
```

**Step 3: Verify JSON is valid**

```bash
python3 -m json.tool /home/brian/people/Brian/brian-ed3d-plugins/.claude-plugin/marketplace.json > /dev/null && echo "Valid JSON"
```

Expected: "Valid JSON"

**Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "chore: update marketplace version for denubis-plan-and-execute 2.2.0"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Add changelog entry

**Files:**
- Modify: `CHANGELOG.md`

**Step 1: Add entry at top of file (after # Changelog heading)**

```markdown
## denubis-plan-and-execute 2.2.0

Added project context inventory system for subagent context injection.

**New:**
- `/inventory-project` command - Discovers CLAUDE.md files, command patterns, MCP servers, and plugins
- `inject-project-context` skill - Wrapper skill for filtering and injecting inventory into subagent prompts
- Staleness detection hook - Warns on session start when inventory is >20 commits behind HEAD
- Project context injection in `executing-an-implementation-plan`, `requesting-code-review`, `writing-implementation-plans`, and `brainstorming` skills

**Changed:**
- `how-to-customize` command now references the inventory system
```

**Step 2: Verify entry is at top**

```bash
head -20 /home/brian/people/Brian/brian-ed3d-plugins/CHANGELOG.md
```

Expected: New entry appears after `# Changelog` heading.

**Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add changelog entry for denubis-plan-and-execute 2.2.0"
```
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Verify Phase 6 complete

**Step 1: Verify all files updated**

```bash
echo "=== README.md ===" && grep -c "inventory-project" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/README.md
echo "=== how-to-customize.md ===" && grep -c "inventory" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/commands/how-to-customize.md
echo "=== plugin.json ===" && grep '"version"' /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
echo "=== marketplace.json ===" && grep -A1 '"denubis-plan-and-execute"' /home/brian/people/Brian/brian-ed3d-plugins/.claude-plugin/marketplace.json | grep version
echo "=== CHANGELOG.md ===" && head -5 /home/brian/people/Brian/brian-ed3d-plugins/CHANGELOG.md
```

Expected:
- README.md: Shows count of "inventory-project" mentions
- how-to-customize.md: Shows count of "inventory" mentions
- plugin.json: Shows `"version": "2.2.0"`
- marketplace.json: Shows version 2.2.0 for denubis-plan-and-execute
- CHANGELOG.md: Shows new entry at top

**Step 2: Verify Phase 6 complete**

Check:
- [x] README.md documents /inventory-project command
- [x] README.md documents project context injection
- [x] how-to-customize.md references inventory system
- [x] plugin.json version bumped to 2.2.0
- [x] marketplace.json version matches plugin.json
- [x] CHANGELOG.md has new entry at top

Phase 6 is complete when documentation is updated and versions are synchronized.
<!-- END_TASK_6 -->
