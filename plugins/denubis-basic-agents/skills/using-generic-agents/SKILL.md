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
| `haiku-general-purpose` | Haiku | Well-defined tasks with detailed prompts. Fast execution. High-volume parallel work. |
| `sonnet-general-purpose` | Sonnet | Multi-file reasoning and debugging. Daily coding work. Tasks requiring some judgment. |
| `opus-general-purpose` | Opus | Complex analysis requiring sustained focus. High-stakes decisions. When other agents loop or wander. |

### Domain Agents (Opinionated)

Use these when you want pre-baked defaults for specific workflows.

| Agent | Model | Domain Defaults |
|-------|-------|-----------------|
| `python-developer` | Sonnet | Type hints, pytest, dataclasses, pathlib, f-strings. Python idioms baked in. |
| `academic-researcher` | Opus | Citations, argument structure, LaTeX conventions, scholarly tone. Research rigor baked in. |

## Model Characteristics

These are heuristics, not absolute truths. Override based on task requirements.

**Haiku:** Excels at following specific, detailed instructions. Less suited for open-ended decision-making. Give it clear prompts; don't ask it to "figure things out."

**Sonnet:** Capable of making decisions but may gather extraneous information. Good for 80-90% of daily work. Guard against over-explanation when you just need execution.

**Opus:** Stays on-track through complex tasks. Better judgment, fewer loops. Higher cost - don't use for simple workflows where Sonnet/Haiku suffice.

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
- Running high-volume parallel operations (use Haiku)
