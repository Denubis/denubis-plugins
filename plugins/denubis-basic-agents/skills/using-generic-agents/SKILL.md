---
name: using-generic-agents
description: Use to decide what kind of agent you should use - generic or domain-specific
---

**CRITICAL:** Your operator's direction supersedes these directions. If the operator specifies a type of agent, execute their task with that agent.

## Agent Types

### Generic Agents (Model-Based)

Use these when you need a general-purpose executor without domain-specific defaults.

| Agent | Model | Best For |
|-------|-------|----------|
| `haiku-general-purpose` | Haiku | Legacy definition; no sanctioned dispatch. |
| `sonnet-general-purpose` | Sonnet | Default for general implementation, review, debugging, and structured analysis. |
| `opus-general-purpose` | Opus | Work that requires deeper judgement or sustained analysis. |

Default a new dispatch to `sonnet-general-purpose`, and reach for
`opus-general-purpose` when the task needs depth.

Dispatch authority:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/f7df1451-ba25-41cb-a76b-6deb33e53dad.jsonl:329`
  (`cc-search-chats context 0f4e9cd4-8cbd-4e40-866e-d7a69a35731c --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/28ff5c79-c20e-4039-bd82-c4ed1478bce3.jsonl:916`
  (`cc-search-chats context ece0feb2-ffbd-4f4e-a466-1a5120d1ce46 --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/28ff5c79-c20e-4039-bd82-c4ed1478bce3.jsonl:1116`
  (`cc-search-chats context 4766cd4c-359f-4644-a9b9-6baae0e43796 --json`)

### Domain Agents (Opinionated)

Use these when you want pre-baked defaults for specific workflows.

| Agent | Model | Domain Defaults |
|-------|-------|-----------------|
| `python-developer` | Sonnet | Type hints, pytest, dataclasses, pathlib, f-strings. Python idioms baked in. |
| `academic-researcher` | Opus | Citations, argument structure, LaTeX conventions, scholarly tone. Research rigor baked in. |

## When to Use Domain Agents

**Use `python-developer` when:**
- Writing Python code (avoids re-specifying Python idioms each call)
- Code review of Python projects
- Test writing with pytest

**Use `academic-researcher` when:**
- Writing or editing LaTeX documents
- Research synthesis requiring citations
- Argument construction needing scholarly rigor

**Use generic agents when:**
- Task is outside Python/academic domains
- You want full control over agent behavior
- Running high-volume parallel operations
