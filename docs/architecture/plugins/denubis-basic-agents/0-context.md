# denubis-basic-agents — Context (Level 0)

> System boundary: a content-bundle plugin shipping five Task-dispatchable agents (three model-tier generic + two domain-specific), one selection skill, and a `SessionStart` hook that injects a reminder to use the selection skill.

## Diagram

```mermaid
flowchart LR
    User[Human user]
    CC[Claude Code host]
    Caller[Dispatching skill / agent\n(in any other plugin)]

    Plugin((0.0\ndenubis-basic-agents))

    User -->|"requests via\nprompts / slash commands"| CC
    CC -->|"SessionStart event"| Plugin
    Plugin -->|"hookSpecificOutput:\nadditionalContext naming\nusing-generic-agents skill"| CC
    Caller -->|"Task tool dispatch:\nsubagent_type =\ndenubis-basic-agents:<agent>"| CC
    CC -->|"loads agent .md\nas subagent system prompt"| Plugin
    Plugin -->|"subagent return value"| CC
```

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|------------------|---------------------|
| Human user | Triggers agent dispatch indirectly by interacting with skills/agents in other plugins. Does not call `denubis-basic-agents` agents directly. | Prompts that reach a dispatching caller | Subagent results that bubble back through the caller |
| Claude Code host | Loads agent markdown files when the `Task` tool is invoked with `subagent_type: denubis-basic-agents:<agent-name>`. Fires `SessionStart` events. | `SessionStart` event; `Task` dispatches naming this plugin's agents | Subagent prompt + tool set per agent; `additionalContext` from the SessionStart hook (`plugins/denubis-basic-agents/hooks/session-start.sh`, `507f421`) |
| Dispatching skill / agent | Any other plugin's skill or agent that uses `Task` to spawn one of this plugin's agents. The `using-generic-agents` skill (`plugins/denubis-basic-agents/skills/using-generic-agents/SKILL.md`, `ed25712`) is the documented selection guide. | Caller-supplied task prompt | Generic subagent execution under the chosen model tier (`plugins/denubis-basic-agents/agents/{haiku,sonnet,opus}-general-purpose.md`, `3918fe9`) |

## System Boundary

**In scope:**
- Provide three model-tier generic agents (`haiku-general-purpose`, `sonnet-general-purpose`, `opus-general-purpose`) whose only system-prompt content is a skills-checklist preamble + "execute caller's prompt exactly" (`plugins/denubis-basic-agents/agents/haiku-general-purpose.md`, `plugins/denubis-basic-agents/agents/sonnet-general-purpose.md`, `plugins/denubis-basic-agents/agents/opus-general-purpose.md`, `3918fe9`).
- Provide two domain agents: `python-developer` (Sonnet, Python 3.14+ defaults — type hints, dataclasses/Pydantic, pytest, pathlib, FCIS) (`plugins/denubis-basic-agents/agents/python-developer.md`, `e947de8`) and `academic-researcher` (Opus, citation discipline, LaTeX conventions, scholarly tone) (`plugins/denubis-basic-agents/agents/academic-researcher.md`, `e947de8`).
- Provide the `using-generic-agents` skill — a model-selection table that distinguishes generic vs domain agents and surfaces the user's standing rule about which model tier suits which workload (`plugins/denubis-basic-agents/skills/using-generic-agents/SKILL.md`, `ed25712`).
- Emit a `SessionStart` `additionalContext` instructing the model to invoke the `using-generic-agents` skill whenever a generic agent is being chosen (`plugins/denubis-basic-agents/hooks/session-start.sh`, `507f421`).

**Out of scope:**
- Dispatching the agents itself — agents are passive resources loaded by Claude Code on `Task` invocation.
- Inter-agent communication — each agent runs as an isolated sub-conversation.
- Tool gating — the agents do not declare tool restrictions in their frontmatter beyond what Claude Code's default toolset provides.

## What This Plugin Ships

### Agents (`plugins/denubis-basic-agents/agents/`)

| Agent | Model | Purpose (frontmatter) |
|-------|-------|-----------------------|
| `haiku-general-purpose` | haiku | Unprompted generic subagent with no currently sanctioned use. Kept callable so the decision stays open, but the 2026-07-25 floor ruling leaves it zero dispatch sites, and dispatching it needs a positive justification naming a bounded mechanical task (`haiku-general-purpose.md`, `3e28e44`). |
| `sonnet-general-purpose` | sonnet | Unprompted generic subagent for attention-to-detail work (`sonnet-general-purpose.md`, `3918fe9`). |
| `opus-general-purpose` | opus | Unprompted generic subagent for deep reasoning, complex analysis, nuanced judgement (`opus-general-purpose.md`, `3918fe9`). |
| `python-developer` | sonnet | Python 3.14+ developer defaults: type hints, dataclasses/Pydantic, pytest, pathlib, modern idioms (`python-developer.md`, `e947de8`). |
| `academic-researcher` | opus | Academic research/writing/LaTeX with citation discipline (`academic-researcher.md`, `e947de8`). |

### Skills (`plugins/denubis-basic-agents/skills/`)

| Skill | Description (frontmatter) |
|-------|---------------------------|
| `using-generic-agents` | Use to decide what kind of agent you should use — generic or domain-specific (`using-generic-agents/SKILL.md`, `ed25712`). |

### Hooks (`plugins/denubis-basic-agents/hooks/`)

| Hook | Event | Behaviour |
|------|-------|-----------|
| `session-start.sh` (`507f421`) registered via `hooks.json` (`a8dad2c`) | `SessionStart` (matcher `startup|resume|clear|compact`), `suppressOutput: true` | Emits a fixed `additionalContext` telling the model to invoke `using-generic-agents` when instructed to use a 'general-purpose' agent. |

## Cross-References

- **Plugin manifest:** `plugins/denubis-basic-agents/.claude-plugin/plugin.json` (`668e965`), version 2.0.1. Manifest description: *"Core agents for general-purpose tasks with Python/academic domain variants. Other plugins expect this to exist."*
- **Marketplace entry:** `.claude-plugin/marketplace.json` (`18f3b80`).
- **Plugins that dispatch these agents:** primarily `denubis-plan-and-execute`'s skills and agents.
- **Shared docs:** `../../README.md`, `../../glossary.md`, `../../constraints.md`.
