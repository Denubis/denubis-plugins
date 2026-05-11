# denubis-plan-and-execute — Context (Level 0)

> System boundary: the largest plugin in the marketplace. It ships the design → plan → execute workflow stack (skills, agents, commands), the `code-quality-guard` and `using-plan-and-execute` hooks, the `workflow_statusline` Python package that emits the tmux statusline string, and the `claude-wrapper.sh` shell entry-point that runs `claude` with disabled tools and agent teams enabled.

## Diagram

```mermaid
flowchart LR
    User[Human user]
    CC[Claude Code host]
    Claude[claude binary]
    Tmux[tmux / terminal]
    Sibling[Sibling plugins\n(denubis-basic-agents,\ndenubis-research-agents)]
    GitHub[git / gh CLI]
    FS@{ shape: das, label: "Project filesystem\n(docs/design-plans/,\ndocs/implementation-plans/,\ndocs/test-plans/,\ndocs/architecture/,\nCLAUDE.md, AGENTS.md,\npyproject.toml, .claude/settings.json)" }

    Plugin((0.0\ndenubis-plan-and-execute))

    User -->|"claudew (wrapper);\nslash commands;\nskill invocations"| CC
    User -->|"shell invocation"| Plugin
    Plugin -->|"exec claude\n--disallowedTools=...\nCLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1"| Claude
    Claude -->|"statusline tick\n(every prompt)"| Plugin
    Plugin -->|"statusline string\n(branch, tokens, rate-limit,\nskills-active bar)"| Tmux
    CC -->|"SessionStart event"| Plugin
    Plugin -->|"using-plan-and-execute\nSKILL.md as additionalContext"| CC
    CC -->|"PreToolUse:Write|Edit"| Plugin
    Plugin -->|"deny / additionalContext\nbased on code-quality-guard rules"| CC
    CC -->|"loads SKILL.md /\nagent .md /\ncommand .md"| Plugin
    Plugin <-->|"Task dispatch to\nbasic-agents +\nresearch-agents"| Sibling
    CC <-->|"reads / writes"| FS
    CC -->|"git commit / merge / pr"| GitHub
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| Human user | Invokes `claudew` (the wrapper), slash commands, and skill workflows. Author of this marketplace. | Shell invocation of `claudew`; `/<command>` invocations; conversational prompts | Wrapped `claude` process; statusline content on every prompt; behavioural workflows in the conversation |
| Claude Code host | Loads skills/agents/commands; fires `SessionStart` and `PreToolUse:Write|Edit` events into this plugin's hooks; runs `Task` dispatches naming this plugin's agents. | Events: `SessionStart` (matcher `startup|resume|clear|compact`) and `PreToolUse:Write|Edit` (`plugins/denubis-plan-and-execute/hooks/hooks.json`, `22d2148`); skill/agent/command load requests | `additionalContext` from `SessionStart` injecting the `using-plan-and-execute` skill body (`plugins/denubis-plan-and-execute/hooks/session-start.sh`, `4598b54`); deny/warn JSON from `code-quality-guard.py` (`plugins/denubis-plan-and-execute/hooks/code-quality-guard.py`, `9bac7ed`); skill/agent prompts injected into model context |
| `claude` binary | The underlying Claude Code CLI binary. Wrapped by `claude-wrapper.sh` which applies `--disallowedTools` and sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` before exec (`plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`, `31e42d0`). | All `claudew` invocations | A `claude` process with `NotebookEdit`, `EnterPlanMode`, `ExitPlanMode`, `EnterWorktree`, `ExitWorktree`, `ListMcpResourcesTool`, `ReadMcpResourceTool`, `RemoteTrigger`, `CronCreate/Delete/List` disabled (`claude-wrapper.sh`, `31e42d0`) |
| tmux / terminal | Consumer of the statusline string. The `workflow_statusline` Python package is invoked by Claude Code on every prompt and emits a one-line summary (`plugins/denubis-plan-and-execute/scripts/workflow_statusline/`, `4359ab2`). | Statusline tick events (each Claude Code prompt) | Status line text rendered by Claude Code in its UI (and reflected into tmux if configured) |
| `denubis-basic-agents` + `denubis-research-agents` | Sibling plugins whose agents this plugin's skills dispatch via the `Task` tool — typically `sonnet-general-purpose`, `opus-general-purpose`, `codebase-investigator`, `internet-researcher`. | `Task` dispatches | Subagent returns |
| git / gh CLI | Used by the worktree, PR, merge, and commit skills/agents to manage version control. | `git status/diff/log/worktree add/commit/merge/push`; `gh pr create` | Worktrees, commits, PRs |
| Project filesystem | Where the workflows read and write: `docs/design-plans/<date>-<slug>.md`, `docs/implementation-plans/<plan>/`, `docs/test-plans/`, `docs/architecture/` (this directory), `CLAUDE.md`, `AGENTS.md`, `pyproject.toml`, `.claude/settings.json`. | Reads by skills/agents (Read, Grep, Glob); edits by `task-implementor`, `refactoring-executor`, etc. | Design plans, implementation plans, test plans, architecture docs, commits, configuration changes |

## System Boundary

**In scope:**
- The disciplined workflow: brainstorm → clarify → design → proleptic-challenge → impl-plan → execute → review → uat → merge (`plugins/denubis-plan-and-execute/skills/`, manifest `1ef36f5`).
- Code-quality enforcement at write time: `code-quality-guard.py` denies or warns on patterns the user has banned (`plugins/denubis-plan-and-execute/hooks/code-quality-guard.py`, `9bac7ed`).
- Statusline rendering: `workflow_statusline` is a uv-managed Python package with `[project.scripts] workflow-statusline = "workflow_statusline.__main__:main"` (`pyproject.toml`, `4359ab2`); modules `cache.py`, `bar.py`, `colours.py`, `ratelimit.py`, `tmux.py`, `git.py`, `__main__.py` (`plugins/denubis-plan-and-execute/scripts/workflow_statusline/src/workflow_statusline/`).
- Wrapping `claude` with the user's standing tool-disable policy and the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env var (`scripts/claude-wrapper.sh`, `31e42d0`).
- Multi-agent code review, coherence review, refactoring, debugging, and bug-fix loops driven by the 10 agents in `agents/`.

**Out of scope:**
- The model itself — this plugin ships behavioural prompts and tooling, not model weights.
- Hosting the marketplace remote or shipping non-Brian plugins.
- Running outside Linux + fish + tmux + ghostty assumptions encoded in the wrapper and statusline (`scripts/claude-wrapper.sh`, `scripts/workflow_statusline/src/workflow_statusline/tmux.py`).
- Database hosting (the `dba-reviewer` agent reviews PostgreSQL schemas but the plugin does not host or migrate a database itself).

## What This Plugin Ships

### Skills (`plugins/denubis-plan-and-execute/skills/`, **34 total**)

Counts and groupings (each is a `<name>/SKILL.md`). Manifest commit `1ef36f5`.

| Group | Count | Skills |
|-------|------:|--------|
| Workflow orchestration | 5 | `using-plan-and-execute`, `starting-a-design-plan`, `starting-an-implementation-plan`, `executing-an-implementation-plan`, `finishing-a-development-branch` |
| Design / brainstorm | 7 | `brainstorming`, `design-clarify`, `design-write`, `impl-plan-write`, `proleptic-challenge`, `maintain-architecture`, `architecture-update` |
| Implementation discipline | 10 | `coding-tdd`, `coding-effectively`, `coding-fcis`, `coding-good-tests`, `coding-property-testing`, `coding-python-idioms`, `coding-verify`, `defense-in-depth`, `systematic-debugging`, `howto-develop-with-postgres` |
| Review / verification | 5 | `requesting-code-review`, `critical-peer-review`, `exec-coherence-review`, `exec-uat-gate`, `exec-refactoring-rubric` |
| Git + branch lifecycle | 3 | `using-git-worktrees`, `make-pr`, `merge-to-main` |
| Misc utilities | 4 | `controlled-dependency-upgrade`, `exec-session-naming`, `restate-our-assumptions`, `using-ast-grep` |

### Agents (`plugins/denubis-plan-and-execute/agents/`, **10 total**)

| Agent | Description (frontmatter, abbreviated) |
|-------|----------------------------------------|
| `code-reviewer` | Reviews completed plan steps against the plan; blocks merges for Minor/Important/Critical issues. |
| `coherence-reviewer` | Reviews whether implementation coheres with design intent and supports future human UAT. |
| `critical-peer-review` | Falsification-first audit of debugging analyses, postmortems, design plans, technical reasoning. |
| `dba-reviewer` | Reviews PostgreSQL schemas + migrations; validates and updates `docs/architecture/database.md`. |
| `proleptic-challenger` | Generates counterarguments before phase transitions; based on Kudina, Ballsun-Stanton & Alfano (2025), DOI 10.1007/s44204-025-00247-1. |
| `refactoring-executor` | Applies reviewed refactoring prescriptions one finding at a time, prefers ast-grep, reverts on test failure. |
| `smell-assessor` | Assesses code for refactoring opportunities using Mantyla smell taxonomy. Read-only. |
| `task-bug-fixer` | Fixes issues identified by `code-reviewer` and triggers re-review. |
| `task-implementor` | Implements individual tasks from plans with TDD and halt-on-failure. |
| `test-analyst` | After code-review passes, validates test coverage and generates a human test plan. |

(Descriptions from frontmatter at manifest commit `1ef36f5`; individual agent files visible under `agents/`.)

### Commands (`plugins/denubis-plan-and-execute/commands/`, **6 total**)

| Command | Purpose |
|---------|---------|
| `/starting-a-design-plan` | Invokes the design-plan workflow. |
| `/starting-an-implementation-plan` | Invokes the implementation-plan workflow. |
| `/executing-an-implementation-plan` | Drives execution of an existing implementation plan. |
| `/maintain-architecture` | Runs an architecture-doc maintenance pass. |
| `/flesh-it-out` | Expands a thin sketch into a fuller description. |
| `/how-to-customize` | Explains how to customise design + implementation plans with project-specific guidance. |

### Hooks (`plugins/denubis-plan-and-execute/hooks/`, registered in `hooks.json` at `22d2148`)

| Hook | Event | Behaviour |
|------|-------|-----------|
| `session-start.sh` (`4598b54`) | `SessionStart` (matcher `startup|resume|clear|compact`), `suppressOutput: true` | Reads `skills/using-plan-and-execute/SKILL.md` and emits its contents as `additionalContext` so every new session loads the meta-skill that announces all other skills. |
| `code-quality-guard.py` (`9bac7ed`) | `PreToolUse:Write|Edit`, timeout 5s | Inspects the file path + new content; denies or warns on patterns the user has banned (`check_e2e_js_injection`, `check_create_all`, `check_migration_edit`, `check_debug_statements`, `check_easy_mode`, `check_spec_weakening` — module-level functions in `code-quality-guard.py`, `9bac7ed`). Outputs deny JSON with `systemMessage` or warn JSON with `additionalContext`. |

### Scripts (`plugins/denubis-plan-and-execute/scripts/`)

| Script | Form | Purpose |
|--------|------|---------|
| `workflow_statusline/` (`4359ab2`) | uv-managed Python package (project name `workflow-statusline`, version 0.1.0, `requires-python >=3.12`). Modules in `src/workflow_statusline/`: `cache.py`, `bar.py`, `colours.py`, `ratelimit.py`, `tmux.py`, `git.py`, `__main__.py`. Tests in `tests/`. | Generates the statusline string Claude Code renders on every prompt — branch, token usage, rate-limit, active skill bar. Invoked as `uv run --project <path>/workflow_statusline workflow-statusline`. |
| `claude-wrapper.sh` (`31e42d0`) | Bash script | The user's primary entry point. `exec`s `claude` with a list of `--disallowedTools` (`NotebookEdit`, `EnterPlanMode`, `ExitPlanMode`, `EnterWorktree`, `ExitWorktree`, `ListMcpResourcesTool`, `ReadMcpResourceTool`, `RemoteTrigger`, `CronCreate`, `CronDelete`, `CronList`) and exports `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Header notes `teammate-mode=auto` detects `$TMUX` for split-pane teaming. |

### Docs (`plugins/denubis-plan-and-execute/docs/`, 2 files)

| Doc | Hash | Purpose |
|-----|------|---------|
| `coding-effectively-design.md` | `b9bed28` | Design notes underpinning the `coding-effectively` skill family. |
| `workflow-status-line.md` | `24a7848` | Documentation for the statusline tool. |

## Cross-References

- **Plugin manifest:** `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` (`1ef36f5`), version 2.32.1. Manifest description: *"Planning and execution workflows for Claude Code. Slow and steady. Based on obra/superpowers."*
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **README:** `plugins/denubis-plan-and-execute/README.md` (`894c66b`).
- **Sibling plugins this plugin dispatches:** `denubis-basic-agents`, `denubis-research-agents`.
- **Sibling hook that reminds about this plugin's `project-claude-librarian` agent:** `denubis-hook-claudemd-reminder` (the agent itself lives in `denubis-extending-claude`, not here).
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
