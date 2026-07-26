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
| `haiku-general-purpose` | Haiku | **No currently sanctioned use.** Kept callable because removing it would foreclose a decision that is not ripe. Dispatching it needs a positive justification naming a bounded mechanical task. |
| `sonnet-general-purpose` | Sonnet | Default for most work. Code review, debugging, implementation, structured analysis. Near Opus-level on software engineering tasks at 1/5 the cost. |
| `opus-general-purpose` | Opus | Deep scientific reasoning, sustained multi-step analysis, high-stakes architectural decisions. When the task needs genuine depth, not just breadth. |

**Model floor (operator ruling, 2026-07-25).** Sonnet is the floor for almost everything,
because the hallucination rate below it is unacceptable. Default a new dispatch to
`sonnet-general-purpose`, and reach for `opus-general-purpose` when the task needs depth.
The falsifier is Haiku 5 shipping plus a dated operator trial on it, so no vendor benchmark
or announcement overturns this on its own.

### Domain Agents (Opinionated)

Use these when you want pre-baked defaults for specific workflows.

| Agent | Model | Domain Defaults |
|-------|-------|-----------------|
| `python-developer` | Sonnet | Type hints, pytest, dataclasses, pathlib, f-strings. Python idioms baked in. |
| `academic-researcher` | Opus | Citations, argument structure, LaTeX conventions, scholarly tone. Research rigor baked in. |

## Model Characteristics (Sonnet 4.6 era)

These are heuristics, not absolute truths. Override based on task requirements.

**Haiku:** Follows specific, detailed instructions with tool calls, but its output cannot be trusted without independent verification, so the cost of checking it usually exceeds what the cheaper tier saves. Never for judgement calls or root-cause debugging, and since 2026-07-25 not for research either. See the model floor above.

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
- Running high-volume parallel operations
