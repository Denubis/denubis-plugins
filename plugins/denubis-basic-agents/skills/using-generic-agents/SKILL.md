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
| `haiku-general-purpose` | Haiku | Tool-heavy search, summarisation, and compilation. High-volume parallel work where prompts are detailed and decisions are few. |
| `sonnet-general-purpose` | Sonnet | Default for most work. Code review, debugging, implementation, structured analysis. Near Opus-level on software engineering tasks at 1/5 the cost. |
| `opus-general-purpose` | Opus | Deep scientific reasoning, sustained multi-step analysis, high-stakes architectural decisions. When the task needs genuine depth, not just breadth. |

### Domain Agents (Opinionated)

Use these when you want pre-baked defaults for specific workflows.

| Agent | Model | Domain Defaults |
|-------|-------|-----------------|
| `python-developer` | Sonnet | Type hints, pytest, dataclasses, pathlib, f-strings. Python idioms baked in. |
| `academic-researcher` | Opus | Citations, argument structure, LaTeX conventions, scholarly tone. Research rigor baked in. |

## Model Characteristics (Sonnet 4.6 era)

These are heuristics, not absolute truths. Override based on task requirements.

**Haiku:** Excels at following specific, detailed instructions with tool calls. Best for search-compile-summarise workflows where the prompt does the thinking. Don't ask it to make judgement calls or debug root causes.

**Sonnet 4.6:** The daily driver. Near-parity with Opus on SWE-bench (79.6% vs 80.8%). Handles code review, implementation, debugging, and structured analysis well. **Caveat:** can be more verbose than Opus — may use significantly more tokens on complex tasks, partially offsetting the 5x price advantage. Guard against over-explanation when you just need execution.

**Opus:** Strongest at deep reasoning (17-point lead over Sonnet on GPQA Diamond). Use for: scientific analysis, complex architectural decisions, tasks where Sonnet loops or wanders, and sustained multi-step reasoning over large context. The gap with Sonnet has narrowed — don't default to Opus out of habit.

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
