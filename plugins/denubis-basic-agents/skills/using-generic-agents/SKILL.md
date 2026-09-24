---
name: using-generic-agents
description: Use when selecting delegated roles or translating Opus and Sonnet subagent requests across providers
---

The operator's direction supersedes these defaults. If the operator specifies an available
agent, use it.

## Agent Types

Choose a functional role first, then map that role onto the current provider's native
subagent surface. Claude Code's packaged agent names are implementations of the roles,
not portable identities that Codex or Antigravity should pretend to provide.

### Generic roles

Use these when you need a general-purpose executor without domain-specific defaults.

| Functional role | Claude Code implementation | Codex implementation |
|---|---|---|
| General-purpose | `general-purpose` | Native general-purpose subagent using `gpt-6-sol` at `xhigh` |
| Deep-judgment | `deep-judgment`, using `claude-opus-5-5` | Native subagent using `gpt-6-sol` with `xhigh` reasoning |

Default to the general-purpose role. Use the deep-judgment role when the task needs
sustained analysis or a consequential qualitative judgment. The legacy
`haiku-general-purpose` definition has no sanctioned dispatch.

### Astra and Fable require a specific human request

Never select Astra or Fable automatically. The human must explicitly request the model
and effort for the particular task, for example "Go run this at Astra on medium".
A generic request for review, deeper judgment, the strongest model, or a different model
does not authorize either. Neither parent-model inheritance nor a configured default
supplies that authorization. A request naming only Astra or Fable is incomplete: ask
for the effort level before dispatching. Do not infer, increase, or default that level.
Carry the human's exact request in the scoped brief. If the host cannot select and
confirm both settings, stop that dispatch and report the limitation.

These are operator defaults as of 2026-09-24, not capability rankings or a request to
choose the most expensive model. A request for an "Opus subagent" means the deep-judgment
role on the current provider unless the human explicitly requests a Claude process.
Use the runtime's actual delegation API and explicit model/effort controls. In Codex,
where a full-history fork cannot override model settings, use a scoped brief with an
override-compatible fork. State an unavailable model or control rather than silently
substituting another model.

On Antigravity or another host, select an available native agent for the same role;
the Claude and Codex model identifiers are not portable to other providers. If the role
requires a model the host cannot supply, surface that limitation.

The role is separate from review independence. Two sessions of the same model provide
process separation. When the task specifically requires a different model, establish
that difference before dispatch; changing an agent's name does not provide it.

Model fields and identifiers: [Claude subagents](https://code.claude.com/docs/en/sub-agents)
and [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol), checked
2026-09-24. Task-specific human instructions override this dated routing policy.

Earlier dispatch authority:

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
