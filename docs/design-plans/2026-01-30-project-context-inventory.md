# Project Context Inventory Design

## Summary

This design introduces a project context inventory system to help Claude Code subagents discover and use project-specific conventions. Currently, subagents spawned by skills have no visibility into how to run tests, what tools are configured, or where to find project documentation—forcing users to manually explain common patterns repeatedly. The inventory system solves this by scanning the project once (via `/inventory-project` command) to extract command patterns from CLAUDE.md, locate documentation files, enumerate MCP servers and installed plugins, then writing this information to `.ed3d/project-inventory.md`.

Skills that spawn subagents call a new `inject-project-context` wrapper skill before constructing their prompts. The wrapper reads the inventory file, applies the requested filter (full context, commands only, or tools only), and returns a formatted block ready for inclusion in the subagent prompt. This allows implementation agents to discover `uv run pytest` automatically, brainstorming agents to understand available tooling, and code reviewers to follow project conventions—all without manual user intervention each time.

## Definition of Done

Skills and subagents can access project-specific context (command patterns like `uv run pytest`, MCP servers, installed plugins, CLAUDE.md locations) through a generated inventory file and wrapper skill. The `/inventory-project` command generates `.ed3d/project-inventory.md`, and the `inject-project-context` skill provides filtered context blocks for subagent prompts. Key skills (executing-an-implementation-plan, brainstorming, writing-implementation-plans, requesting-code-review) integrate with this system. Graceful degradation when no inventory exists.

## Glossary

- **Subagent**: An isolated Claude instance spawned by a skill to perform a specific task (e.g., implementing code, reviewing changes). Subagents don't inherit context from their parent skill.
- **Skill**: A reusable Claude Code capability defined in a plugin's `skills/` directory. Skills can invoke tools, spawn subagents, and be called by users or other skills.
- **MCP server**: Model Context Protocol server that exposes tools, resources, or prompts to Claude Code. Projects can register local or global MCP servers via `.mcp.json` files.
- **Plugin**: A packaged collection of skills and commands installed in Claude Code. Lives in `~/.claude/plugins/` or project-local directories.
- **Wrapper skill**: A skill whose primary purpose is to encapsulate reusable logic for other skills (here: reading and filtering inventory data).
- **CLAUDE.md**: Project-specific instructions file read by Claude Code sessions. Often contains command patterns like "run tests with `uv run pytest`".
- **AGENTS.md**: Project-specific file documenting subagent configurations, often stored in `.ed3d/AGENTS.md`.
- **Filter parameter**: Argument passed to `inject-project-context` skill to control which inventory sections are included (`full`, `commands-only`, `tools-only`).
- **Graceful degradation**: System behavior where missing optional components (like the inventory file) don't cause errors—the system proceeds with reduced capability.

## Architecture

Project context discovery and injection system with three components:

**1. `/inventory-project` command**
Entry point for users. Invokes Python discovery script, writes `.ed3d/project-inventory.md`. Run on-demand when project context changes.

**2. `.ed3d/project-inventory.md` file**
Generated file containing discovered context:
- Command patterns extracted from CLAUDE.md (e.g., `uv run pytest`)
- CLAUDE.md/AGENTS.md file locations (paths and section headers)
- MCP servers from `.mcp.json` files (project and global)
- Installed plugins from `~/.claude/plugins/installed_plugins.json`

**3. `inject-project-context` skill**
Wrapper skill called by other skills before spawning subagents. Reads inventory file, accepts filter parameter (`full`, `commands-only`, `tools-only`), returns formatted context block for inclusion in subagent prompts.

**Data flow:**
```
User runs /inventory-project
    → Python script discovers context sources
    → Writes .ed3d/project-inventory.md

Skill prepares to spawn subagent
    → Calls inject-project-context skill with filter
    → Skill reads .ed3d/project-inventory.md
    → Returns formatted context block
    → Skill includes block in subagent prompt
```

## Existing Patterns

Investigation found existing context injection pattern via `.ed3d/` guidance files:
- `.ed3d/design-plan-guidance.md` loaded by `starting-a-design-plan`
- `.ed3d/implementation-plan-guidance.md` loaded by `starting-an-implementation-plan` and passed to code reviewers

This design extends that pattern:
- Same `.ed3d/` directory convention
- Same "read file, include in prompt" approach
- New: centralised wrapper skill for consistent injection
- New: auto-generated content (not hand-written)

Subagent prompts currently pass context via `<parameter name="prompt">` template variables. This design follows that pattern, adding `${PROJECT_CONTEXT}` variable populated by the wrapper skill.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Discovery Script

**Goal:** Python script that discovers and extracts project context

**Components:**
- `plugins/denubis-plan-and-execute/scripts/inventory-project.py` — main discovery script
  - Finds CLAUDE.md/AGENTS.md files recursively
  - Extracts command patterns via regex (uv run, pytest, ruff, etc.)
  - Reads `.mcp.json` files (project-local and global)
  - Reads `~/.claude/plugins/installed_plugins.json`
  - Outputs structured markdown to stdout or file

**Dependencies:** None

**Done when:** Script runs successfully, outputs valid markdown with all four context sections
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Command Integration

**Goal:** `/inventory-project` command that invokes discovery script

**Components:**
- `plugins/denubis-plan-and-execute/commands/inventory-project.md` — command definition
  - Invokes Python script
  - Writes output to `.ed3d/project-inventory.md`
  - Reports what was discovered

**Dependencies:** Phase 1 (discovery script)

**Done when:** `/inventory-project` command generates `.ed3d/project-inventory.md` with correct content
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Wrapper Skill

**Goal:** `inject-project-context` skill for filtered context injection

**Components:**
- `plugins/denubis-plan-and-execute/skills/inject-project-context/SKILL.md` — wrapper skill
  - Reads `.ed3d/project-inventory.md`
  - Accepts filter parameter: `full`, `commands-only`, `tools-only`
  - Returns formatted context block ready for subagent prompts
  - Handles missing inventory gracefully (returns empty or warning)

**Dependencies:** Phase 2 (inventory file must exist)

**Done when:** Skill returns appropriate filtered context for each filter option
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Skill Integration

**Goal:** Key skills call wrapper before spawning subagents

**Components:**
- `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md` — add context injection (filter: `full`)
- `plugins/denubis-plan-and-execute/skills/brainstorming/SKILL.md` — add context injection (filter: `commands-only`)
- `plugins/denubis-plan-and-execute/skills/writing-implementation-plans/SKILL.md` — add context injection (filter: `commands-only`)
- `plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md` — add context injection (filter: `full`)

**Dependencies:** Phase 3 (wrapper skill)

**Done when:** All four skills include project context in subagent prompts when inventory exists
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Staleness Detection Hook

**Goal:** Session hook that suggests refresh when inventory is stale

**Components:**
- `plugins/denubis-plan-and-execute/hooks/inventory-staleness.sh` — session start hook
  - Reads commit SHA from `.ed3d/project-inventory.md`
  - Compares against current HEAD
  - If >20 commits behind, outputs reminder to run `/inventory-project`
- `plugins/denubis-plan-and-execute/hooks/hooks.json` — register the hook

**Dependencies:** Phase 2 (inventory file format must include commit SHA)

**Done when:** Hook fires on session start and warns when inventory is stale
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Documentation and Version Bump

**Goal:** Update plugin documentation and version

**Components:**
- `plugins/denubis-plan-and-execute/README.md` — document new command, skill, and staleness hook
- `plugins/denubis-plan-and-execute/commands/how-to-customize.md` — reference inventory system
- `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — version bump
- `CHANGELOG.md` — release notes

**Dependencies:** Phase 5 (all features complete)

**Done when:** Documentation complete, version bumped, changelog updated
<!-- END_PHASE_6 -->

## Additional Considerations

**Staleness detection:** Inventory file includes generation commit SHA. A session start hook can compare current HEAD against the stored SHA - if >20 commits behind, suggest running `/inventory-project`. This catches config file changes (CLAUDE.md, .mcp.json, pyproject.toml) without time-based expiry. Hook lives in `denubis-plan-and-execute/hooks/`.

**Gitignore:** `.ed3d/project-inventory.md` is auto-generated. Users may want to gitignore it. Document this option but don't enforce.

**Graceful degradation:** If `.ed3d/project-inventory.md` doesn't exist, skills proceed without project context. No errors, just reduced capability.
