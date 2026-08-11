# denubis-research-agents — Context (Level 0)

> System boundary: a content-bundle plugin shipping four Task-dispatchable research agents and three companion skills for codebase + internet investigation.

## Diagram

```mermaid
flowchart LR
    Caller[Dispatching skill / agent\n(in any other plugin)]
    CC[Claude Code host]
    Net[(Internet via WebSearch /\nWebFetch / Context7 MCP)]
    Repos[(External git repositories\nfor remote-code-researcher)]
    Local@{ shape: das, label: "Local working directory\nand project files" }

    Plugin((0.0\ndenubis-research-agents))

    Caller -->|"Task tool dispatch:\nsubagent_type =\ndenubis-research-agents:<agent>"| CC
    CC -->|"loads agent .md\nas subagent system prompt"| Plugin
    Plugin -->|"reads source files"| Local
    Plugin -->|"WebSearch / WebFetch"| Net
    Plugin -->|"git clone to temp dir\n(remote-code-researcher only)"| Repos
    Plugin -->|"findings text only\n(no files written)"| CC
    CC -->|"subagent return value"| Caller
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| Dispatching skill / agent | Any other plugin's skill or agent that uses `Task` to spawn one of these research agents. The `using-research-agents` skill (`plugins/denubis-research-agents/skills/using-research-agents/SKILL.md`, `ebfc608`) documents how to choose between them. | Caller-supplied research question or task | Research findings as text in the subagent return message (`plugins/denubis-research-agents/agents/codebase-investigator.md`, `internet-researcher.md`, `combined-researcher.md`, `remote-code-researcher.md`, `ebfc608`) |
| Claude Code host | Loads agent markdown when `Task` is invoked with `subagent_type: denubis-research-agents:<agent-name>`. | `Task` dispatches | Subagent prompt + caller-defined toolset per agent |
| Internet | `WebSearch`/`WebFetch` for current docs and patterns; `mcp__context7__*` tools for library documentation lookups. | URLs and search queries from the running agent | Pages, docs, code snippets |
| External git repositories | Cloned to a temp directory by `remote-code-researcher` to read library internals locally (`plugins/denubis-research-agents/agents/remote-code-researcher.md`, `5bfcd99`). | `git clone` invocations | Source files for inspection |
| Local working directory | Source of truth for `codebase-investigator` and `combined-researcher` when answering questions about the current project. | Read-only file access | (none) |

## System Boundary

**In scope:**
- Provide four research agents, each with a `REQUIRED SKILL` line pointing at the corresponding investigation skill: `codebase-investigator` → `investigating-a-codebase`; `internet-researcher` → `researching-on-the-internet`; `combined-researcher` → both; `remote-code-researcher` → both (clones external repos to a temp dir first) (`plugins/denubis-research-agents/agents/`, `ebfc608`).
- Provide three companion skills: `using-research-agents` (`ebfc608`), `investigating-a-codebase` (`ea1cd49`), and `researching-on-the-internet` (`8498518`) under `plugins/denubis-research-agents/skills/`.
- Require findings to return through the calling conversation unless the caller explicitly names a file target (`plugins/denubis-research-agents/agents/`, `ebfc608`).

**Out of scope:**
- Implementation / refactoring — these agents are read-only research roles.
- Running long-lived processes — each invocation is a single subagent turn that returns a text answer.
- Hosting documentation or caching results — `WebFetch`'s 15-minute cache is the only persistence; otherwise stateless.

## What This Plugin Ships

### Agents (`plugins/denubis-research-agents/agents/`)

| Agent | Model | Purpose (frontmatter) |
|-------|-------|-----------------------|
| `codebase-investigator` | sonnet | Investigate the current codebase to find existing patterns, verify assumptions, ground plans in reality (`codebase-investigator.md`, `ebfc608`). |
| `internet-researcher` | sonnet | Internet-based research: current API docs, library patterns, external knowledge (`internet-researcher.md`, `ebfc608`). |
| `combined-researcher` | sonnet | Both local and internet research synthesised into one answer (`combined-researcher.md`, `ebfc608`). |
| `remote-code-researcher` | sonnet | Examine library internals by cloning external repos to a temp directory and reading actual source code (`remote-code-researcher.md`, `ebfc608`). |

### Skills (`plugins/denubis-research-agents/skills/`)

| Skill | Description (frontmatter) |
|-------|---------------------------|
| `using-research-agents` | Agent selection across internet/codebase/combined/remote-code, academic-research protocol with DOI citations, and anti-patterns (`using-research-agents/SKILL.md`, `8498518`). |
| `investigating-a-codebase` | Use when planning a feature and need to understand current codebase state, find existing patterns, or verify assumptions about what exists (`investigating-a-codebase/SKILL.md`, `8498518`). |
| `researching-on-the-internet` | Use when planning a feature and need current API docs, library patterns, or external knowledge to verify technology choices or assumptions (`researching-on-the-internet/SKILL.md`, `8498518`). |

## Cross-References

- **Plugin manifest:** `plugins/denubis-research-agents/.claude-plugin/plugin.json` (`63c0f42`), version 1.3.1. Manifest description: *"Agents for codebase investigation and internet research. Other plugins expect this one to be enabled."*
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **Plugins that dispatch these agents:** primarily `denubis-plan-and-execute`'s skills (e.g. `brainstorming`, `starting-a-design-plan`).
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
