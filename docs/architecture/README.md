# Architecture — brian-ed3d-plugins

Architecture is indexed first by behavioural system boundary. Plugin pages are
subsidiary packaging views: they show what a deployable bundle ships, but a marketplace
or plugin boundary is not assumed to be the right axis for a cross-cutting behaviour.

## Cross-cutting systems

- [`instruction-control/0-context.md`](instruction-control/0-context.md) — how global and
  project instructions, output style, hooks, skills, project memory, transcripts,
  documentary authority, and external evidence combine in live Claude Code and Codex
  sessions.

## Plugin packaging views (14)

### Event hooks

- [`denubis-hook-branch-bg/0-context.md`](plugins/denubis-hook-branch-bg/0-context.md) —
  `SessionStart`: recolours the terminal from repository and branch identity.
- [`denubis-hook-gh-fork-guard/0-context.md`](plugins/denubis-hook-gh-fork-guard/0-context.md)
  — `PreToolUse:Bash`, through the dispatcher: blocks `gh` against a non-fork target.
- [`denubis-hook-pretooluse-dispatcher/0-context.md`](plugins/denubis-hook-pretooluse-dispatcher/0-context.md)
  — `PreToolUse:Bash`: discovers sibling Bash guards and merges their outputs.
### Workflow and delegated work

- [`denubis-plan-and-execute/0-context.md`](plugins/denubis-plan-and-execute/0-context.md)
  — 33 shared skills, thin Claude role and command adapters, Codex discovery metadata,
  one Claude-only live-marker hook, the workflow statusline, and the Claude wrapper.
- [`denubis-basic-agents/0-context.md`](plugins/denubis-basic-agents/0-context.md) — five
  general-purpose or domain agents and one situational selection skill.
- [`denubis-research-agents/0-context.md`](plugins/denubis-research-agents/0-context.md) —
  four research agents and three companion skills.
- [`denubis-external-agents/0-context.md`](plugins/denubis-external-agents/0-context.md) —
  three procedures and their scripts for Codex review/supervision and Fable advice.
- [`denubis-extending-claude/0-context.md`](plugins/denubis-extending-claude/0-context.md)
  — ten authoring skills and the `project-claude-librarian` agent.
- [`denubis-git-commit/0-context.md`](plugins/denubis-git-commit/0-context.md) — one
  commit procedure.

### Knowledge, research, and measurement

- [`denubis-project-notes/0-context.md`](plugins/denubis-project-notes/0-context.md) —
  explicit main-agent recovery of named project memory and relevant prior chats.
- [`denubis-academic/0-context.md`](plugins/denubis-academic/0-context.md) — three
  academic skills, one output style, and bibliography helper scripts.
- [`denubis-token-estimator/0-context.md`](plugins/denubis-token-estimator/0-context.md)
  — one shared methodology skill, provider entry points, and read-only Claude/Codex log
  analysis.
- [`denubis-crash-recovery/0-context.md`](plugins/denubis-crash-recovery/0-context.md) —
  deterministic session classification, rendering, and triage over its SQLite state.

### Onboarding

- [`denubis-00-getting-started/0-context.md`](plugins/denubis-00-getting-started/0-context.md)
  — two onboarding commands and one npm install-script policy skill.

## Shared documents

- [`glossary.md`](glossary.md) — ubiquitous language.
- [`personae.md`](personae.md) — human users, goals, and access patterns.
- [`constraints.md`](constraints.md) — current repository and runtime constraints,
  separated by how they are verified.
- [`database.md`](database.md) — schema, relationships, and migration strategy for the
  crash-recovery SQLite database.

## Conventions

- **Citation format:** factual repository claims cite a real file at a real commit in the
  form `(path/to/file::SymbolName, abc1234)` or `(path/to/file.json, abc1234)`.
- **External observations:** machine-local or external facts name the artifact, the
  observation date, and an identity such as a digest. They are snapshots, not source
  truth.
- **Scope:** living architecture describes the implemented system. Prospective contracts
  stay in design plans until implementation lands.
- **Decomposition:** use the boundary that owns the behaviour or design decision. A
  plugin page is appropriate for a deployable bundle; it does not replace a cross-cutting
  map.
- **Numbering:** a system or plugin context is `0-context.md`. Add deeper levels only
  when they protect a useful design boundary.
