# denubis-extending-claude — Context (Level 0)

> System boundary: a knowledge-skill plugin shipping ten `SKILL.md` files plus one agent that together describe how to author, test, screen, and maintain Claude Code plugins (skills, agents, marketplaces, CLAUDE.md files, upstream syncs, project context).

## Diagram

```mermaid
flowchart LR
    User[Human user]
    Caller[Dispatching skill / agent\n(in this or another plugin)]
    CC[Claude Code host]
    Repo@{ shape: das, label: "Plugin source trees,\nCLAUDE.md / AGENTS.md files,\nmarketplace.json, plugin.json,\nupstream fork remote" }

    Plugin((0.0\ndenubis-extending-claude))

    User -->|"prompts hinting at\nskill/agent/marketplace work"| CC
    Caller -->|"Task tool dispatch:\nsubagent_type =\ndenubis-extending-claude:project-claude-librarian"| CC
    CC -->|"loads SKILL.md or agent.md\ninto model / subagent context"| Plugin
    Plugin -.->|"behavioural prompts\nfor authoring + reviewing"| CC
    CC <-->|"reads + edits"| Repo
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| Human user | Triggers the skills by writing/editing skills, agents, plugins, marketplace entries, CLAUDE.md files, or asking to sync from upstream. | Author/edit prompts | Resulting markdown / JSON edits in the working repo (made by Claude executing the skill body) |
| Dispatching caller | Any skill or agent that uses `Task` to dispatch `project-claude-librarian` for a CLAUDE.md/AGENTS.md freshness pass. | Caller-supplied task (typically "review what changed and propose CLAUDE.md updates") | Subagent return value with proposed changes (`plugins/denubis-extending-claude/agents/project-claude-librarian.md`, `6b88e1d`) |
| Claude Code host | Loads `SKILL.md` and agent `.md` files into the appropriate context. | Skill invocation or `Task` dispatch | Behavioural prompt injected into context |
| Repo state | The artifacts the skills act on: plugin source trees, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CLAUDE.md`, `AGENTS.md`, upstream fork remote (for `syncing-with-upstream`). | Reads via Read/Grep/Glob; edits via Edit/Write/Bash | Plugin scaffolding, version bumps, changelog entries, CLAUDE.md updates, merged upstream commits |

## System Boundary

**In scope:**
- Authoring skills (`writing-skills`, `testing-skills-with-subagents`, `writing-claude-directives`) (`plugins/denubis-extending-claude/skills/{writing-skills,testing-skills-with-subagents,writing-claude-directives}/SKILL.md`, `8498518`/`8498518`/`2a3f5ff`).
- Authoring agents (`creating-an-agent`) (`creating-an-agent/SKILL.md`, `2a3f5ff`).
- Screening whether a proposed skill, agent scaffold, or automated task earns its existence (`epistemic-humility`) (`epistemic-humility/SKILL.md`, `6077868`).
- Authoring plugins (`creating-a-plugin`) (`creating-a-plugin/SKILL.md`, `8498518`).
- Maintaining the marketplace + per-plugin manifests (`maintaining-a-marketplace`) (`maintaining-a-marketplace/SKILL.md`, `8498518`).
- Writing and maintaining CLAUDE.md/AGENTS.md files (`writing-claude-md-files`, `maintaining-project-context`) (`writing-claude-md-files/SKILL.md`, `maintaining-project-context/SKILL.md`, `8498518`).
- Syncing this fork from upstream `ed3d-plugins` while preserving the `denubis-` rename (`syncing-with-upstream/SKILL.md`, `7bee729`). This skill is `user-invocable: true`.
- Dispatching the `project-claude-librarian` agent (Opus) to review and update CLAUDE.md/AGENTS.md files at phase boundaries (`agents/project-claude-librarian.md`, `6b88e1d`).

**Out of scope:**
- Running other plugins' code or directly editing other repos.
- Continuous CI — these skills are invoked on-demand, not on every change.
- Plugin install/uninstall — handled by Claude Code's `/plugin` command, not by this plugin.

## What This Plugin Ships

### Skills (`plugins/denubis-extending-claude/skills/`, 10 total)

| Skill | User-invocable? | Description (frontmatter, abbreviated to one line) |
|-------|-----------------|---------------------------------------------------|
| `creating-a-plugin` | no | Use when creating a new Claude Code plugin — covers file structure, manifest format, and component definitions (`creating-a-plugin/SKILL.md`, `8498518`). |
| `creating-an-agent` | no | Use when creating specialised subagents — covers description writing for auto-delegation, tool selection, prompt structure, testing (`creating-an-agent/SKILL.md`, `2a3f5ff`). |
| `epistemic-humility` | no | Use when assessing whether a proposed skill, agent scaffold, or automated task earns its existence — screens scope, observability, reflective process, and failure patterns before building (`epistemic-humility/SKILL.md`, `6077868`). |
| `maintaining-a-marketplace` | no | Use when creating, releasing, or maintaining a Claude Code Plugin Marketplace — covers marketplace.json schema, version sync, changelog, release validation (`maintaining-a-marketplace/SKILL.md`, `8498518`). |
| `maintaining-project-context` | no | Use when completing development phases to identify and update stale CLAUDE.md or AGENTS.md files against code changes (`maintaining-project-context/SKILL.md`, `8498518`). |
| `syncing-with-upstream` | **yes** | Use when integrating changes from upstream ed3d-plugins into this fork — handles the ed3d→denubis rename, conflict resolution, merge workflow (`syncing-with-upstream/SKILL.md`, `7bee729`). |
| `testing-skills-with-subagents` | no | Use when creating or editing skills to verify they work under pressure — applies RED-GREEN-REFACTOR with subagents to find rationalisation loopholes (`testing-skills-with-subagents/SKILL.md`, `8498518`). |
| `writing-claude-directives` | no | Use when writing instructions that guide Claude behaviour — skills, CLAUDE.md, agent prompts. Covers token efficiency, compliance techniques, discovery optimisation (`writing-claude-directives/SKILL.md`, `2a3f5ff`). |
| `writing-claude-md-files` | no | Use when creating or updating CLAUDE.md files — top-level vs domain-level scope, architectural intent, freshness stamps (`writing-claude-md-files/SKILL.md`, `8498518`). |
| `writing-skills` | no | Use when creating or editing skills — applies TDD with subagent testing to find rationalisation loopholes (`writing-skills/SKILL.md`, `8498518`). |

Skill-adjacent files: `writing-claude-directives/graphviz-conventions.dot`, `writing-claude-directives/long-running-state-patterns.md`, and `writing-claude-directives/model-tier-notes.md` (per-model behavioural specifics on its own refresh cycle, `a97b0f3`) are reference assets the skill points to; `epistemic-humility/absencejudgement-citations.md` and `epistemic-humility/self-application.md` are that skill's citation index and self-screen record (`6077868`).

### Agents (`plugins/denubis-extending-claude/agents/`, 1 total)

| Agent | Model | Description (frontmatter, abbreviated) |
|-------|-------|----------------------------------------|
| `project-claude-librarian` | opus | Use when completing development phases and project context files may need updating — analyses changes, identifies affected CLAUDE.md / AGENTS.md files, coordinates updates (`agents/project-claude-librarian.md`, `6b88e1d`). |

## Cross-References

- **Plugin manifest:** `plugins/denubis-extending-claude/.claude-plugin/plugin.json` (`1ef36f5`), version 1.7.2. Manifest description: *"Knowledge skills for extending Claude Code: creating plugins, agents, skills, and maintaining CLAUDE.md."*
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **Hook that invokes `project-claude-librarian`:** `denubis-hook-claudemd-reminder` emits a reminder after git status/log to consider dispatching this agent before commits.
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
