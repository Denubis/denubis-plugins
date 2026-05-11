# Architecture — brian-ed3d-plugins

Per-plugin context diagrams + shared glossary, personae, and constraints. Each plugin is its own system with its own boundary. There is no marketplace-level Level-0 because the marketplace decomposes recursively into plugins and the plugins themselves are the right unit of analysis.

## Plugin Contexts (14)

Hook plugins:
- [`denubis-hook-branch-bg/0-context.md`](plugins/denubis-hook-branch-bg/0-context.md) — `SessionStart`: recolours terminal background based on git repo (hue) + branch (offsets).
- [`denubis-hook-claudemd-reminder/0-context.md`](plugins/denubis-hook-claudemd-reminder/0-context.md) — `PostToolUse:Bash`: reminds to update CLAUDE.md after `git status`/`git log`.
- [`denubis-hook-gh-fork-guard/0-context.md`](plugins/denubis-hook-gh-fork-guard/0-context.md) — `PreToolUse:Bash` (via dispatcher): blocks `gh` against non-fork repos.
- [`denubis-hook-pretooluse-dispatcher/0-context.md`](plugins/denubis-hook-pretooluse-dispatcher/0-context.md) — `PreToolUse:Bash`: discovers and runs sibling `pretooluse-bash.sh` hooks, merges outputs.
- [`denubis-hook-rtk-rewrite/0-context.md`](plugins/denubis-hook-rtk-rewrite/0-context.md) — `PreToolUse:Bash` (via dispatcher): rewrites CLI calls to `rtk` equivalents.
- [`denubis-hook-shortcut-detection/0-context.md`](plugins/denubis-hook-shortcut-detection/0-context.md) — `Stop`: scans transcript for shortcut phrases and blocks with E-STOP.
- [`denubis-hook-skill-reinforcement/0-context.md`](plugins/denubis-hook-skill-reinforcement/0-context.md) — `UserPromptSubmit`: reminds the model to invoke applicable skills.

Agent-and-skill plugins:
- [`denubis-basic-agents/0-context.md`](plugins/denubis-basic-agents/0-context.md) — five Task-dispatchable agents (haiku/sonnet/opus general-purpose + python-developer + academic-researcher), one selection skill, one `SessionStart` hook.
- [`denubis-research-agents/0-context.md`](plugins/denubis-research-agents/0-context.md) — four research agents (codebase, internet, combined, remote-code) + three companion skills.

Orchestration:
- [`denubis-plan-and-execute/0-context.md`](plugins/denubis-plan-and-execute/0-context.md) — the largest plugin: 34 skills, 10 agents, 6 commands, 2 hooks (`session-start.sh`, `code-quality-guard.py`), and 2 scripts (`workflow_statusline/`, `claude-wrapper.sh`).

Meta + utility:
- [`denubis-extending-claude/0-context.md`](plugins/denubis-extending-claude/0-context.md) — nine authoring skills + `project-claude-librarian` agent for CLAUDE.md/AGENTS.md upkeep.
- [`denubis-00-getting-started/0-context.md`](plugins/denubis-00-getting-started/0-context.md) — `/getting-started` and `/setup` slash commands.
- [`denubis-git-commit/0-context.md`](plugins/denubis-git-commit/0-context.md) — single skill that handles `/commit`.
- [`denubis-bibliography/0-context.md`](plugins/denubis-bibliography/0-context.md) — Zotero PDF → per-page markdown + page-keyed blockquotes (skill marks itself WIP — only one validated path).

## Shared Documents

- [`glossary.md`](glossary.md) — ubiquitous language for the marketplace.
- [`personae.md`](personae.md) — single human persona.
- [`constraints.md`](constraints.md) — repo conventions (version sync, HALT-when-sideways, per-plugin scope, version-bump cadence).

## Conventions

- **Citation format:** every factual claim in a plugin context cites a real file at a real commit hash, in the form `(path/to/file::SymbolName, abc1234)` for code or `(path/to/file.json, abc1234)` for config.
- **Scope:** these docs describe what exists in the marketplace now. Future or in-development work is not represented here. When a design plan lands and becomes code, its plugin gets a context (or its existing context gets updated).
- **Numbering:** each plugin's level-0 file is `0-context.md`. Decomposition into `1-*.md`, `2-*.md` etc. is added per plugin only when the plugin warrants it; most don't.
