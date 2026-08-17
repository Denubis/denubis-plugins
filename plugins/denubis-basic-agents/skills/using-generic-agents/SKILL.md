---
name: using-generic-agents
description: Use to decide what kind of agent you should use - generic or domain-specific
---

The operator's direction supersedes these defaults. If the operator specifies an available
agent, use it.

## Agent Types

Choose a functional role first, then map that role onto the current provider's native
subagent surface. Claude Code's packaged agent names are implementations of the roles,
not portable identities that Codex or Antigravity should pretend to provide.

### Generic roles

Use these when you need a general-purpose executor without domain-specific defaults.

| Functional role | Claude Code implementation | Codex / Antigravity implementation |
|---|---|---|
| General-purpose | `sonnet-general-purpose` | Native general-purpose subagent |
| Deep-judgment | `opus-general-purpose` | Native subagent with the strongest available reasoning configuration |

Default to the general-purpose role. Use the deep-judgment role when the task needs
sustained analysis or a consequential qualitative judgment. The legacy
`haiku-general-purpose` definition has no sanctioned dispatch.

Dispatch authority:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/f7df1451-ba25-41cb-a76b-6deb33e53dad.jsonl:329`
  (`cc-search-chats context 0f4e9cd4-8cbd-4e40-866e-d7a69a35731c --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/28ff5c79-c20e-4039-bd82-c4ed1478bce3.jsonl:916`
  (`cc-search-chats context ece0feb2-ffbd-4f4e-a466-1a5120d1ce46 --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/28ff5c79-c20e-4039-bd82-c4ed1478bce3.jsonl:1116`
  (`cc-search-chats context 4766cd4c-359f-4644-a9b9-6baae0e43796 --json`)

### Domain roles

Use these when you want pre-baked defaults for specific workflows.

| Functional role | Claude Code implementation | Other providers |
|---|---|---|
| Python developer | `python-developer` | Native subagent briefed with the project's Python rules and test harness |
| Academic researcher | `academic-researcher` | Native subagent briefed with the bibliography workflow, citation rules, and scholarly task |

## When to Use Domain Agents

**Use the Python-developer role when:**
- Writing Python code (avoids re-specifying Python idioms each call)
- Code review of Python projects
- Test writing with pytest

**Use the academic-researcher role when:**
- Writing or editing LaTeX documents
- Research synthesis requiring citations
- Argument construction needing scholarly rigor

**Use generic agents when:**
- Task is outside Python/academic domains
- You want full control over agent behavior
- Running high-volume parallel operations

If the current provider has no delegation surface, do the work in the current session and
state that no isolated agent was available. Do not invent a Claude agent name or claim a
separate review occurred.
