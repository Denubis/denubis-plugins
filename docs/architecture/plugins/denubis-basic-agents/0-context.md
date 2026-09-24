# denubis-basic-agents — Context (Level 0)

> System boundary: five Claude agent definitions and one situational selection skill.

## Context

```mermaid
flowchart LR
    H[Human task]
    C[Calling skill or main session]
    S[using-generic-agents]
    A[Selected agent]
    R[Result]

    H --> C
    C -->|model/domain selection needed| S
    S -->|subagent_type| A
    A --> R
    R --> C
```

## Current contracts

| Surface | Responsibility |
|---|---|
| `using-generic-agents` | Select a domain-specific or generic agent and the appropriate model tier when delegation is already warranted. |
| `general-purpose` | General delegated work at the suite's normal floor. |
| `deep-judgment` | Delegated work requiring deeper reasoning or judgment. |
| `haiku-general-purpose` | Callable but has no default dispatch site; use needs a positive bounded justification. |
| `python-developer` | Python implementation with the repository's modern-Python defaults. |
| `academic-researcher` | Academic research and writing with citation discipline. |

The plugin does not run at SessionStart. Agent selection is useful only at the point
where a caller has already decided to delegate.

## Boundary and failure modes

- The plugin supplies agents; it does not decide that delegation is needed.
- The selection skill supplies a procedure, not evidence that the selected agent's
  result is correct.
- The shared role selection skill maps deep judgment to Claude Opus 5.5 or Codex
  GPT-6 Sol at xhigh, subject to explicit human overrides and runtime availability.
- Claude agent files configure Claude only; Codex callers use their native delegation API.
- Model availability and installed versions are deployment concerns.

## Cross-references

- **Plugin manifest:** `plugins/denubis-basic-agents/.claude-plugin/plugin.json`, with provider-specific packaging alongside it.
- **Marketplace entry:** `.claude-plugin/marketplace.json`.
- **Primary consumers:** plan-and-execute skills and agents.
