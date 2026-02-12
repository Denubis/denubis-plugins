---
name: proleptic-challenge
description: Use before phase transitions to generate counterarguments and force deliberate evaluation - fires at design finalisation, between implementation phases, and during UAT
---

# Proleptic Challenge

## Overview

Generate counterarguments before committing to decisions. Force deliberate evaluation rather than premature consensus.

**Core principle:** The value is in the evaluation, not the counterarguments.

**Announce at start:** "I'm using the proleptic-challenge skill to generate counterarguments before we proceed."

## Theoretical Foundation

Based on proleptic reasoning from argumentation theory—anticipating objections, articulating them charitably, and responding preemptively.

**Reference:** Kudina, O., Ballsun-Stanton, B., & Alfano, M. (2025). The use of large language models as scaffolds for proleptic reasoning. *Asian Journal of Philosophy*, 4, 24. DOI: 10.1007/s44204-025-00247-1

## Workflow Status Line

**Before presenting counterarguments to human:**
```bash
WS=~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state.sh
[ -x "$WS" ] && "$WS" --human "think"
```

**After human responds** (and you proceed):
```bash
WS=~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state.sh
[ -x "$WS" ] && "$WS" --human null
```

This sets the status line to bold magenta "Think" — signalling the human needs to evaluate critically, not just approve.

## When to Invoke

Proleptic challenges fire **before phase transitions**, not at every decision point:

| Trigger | When | What Gets Challenged |
|---------|------|---------------------|
| Design finalisation | After writing-design-plans completes, before commit | The design about to be committed |
| Between implementation phases | After phase code review passes | The completed phase before moving to next |
| During UAT | Before human-uat-gate presents acceptance criteria | The implementation before declaring complete |

**DO NOT invoke:**
- After every user message
- For routine confirmations ("yes, proceed")
- For trivial decisions
- When user explicitly skips ("I've already considered this")

## Invocation Template

Dispatch the proleptic-challenger agent:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:proleptic-challenger</parameter>
<parameter name="description">Proleptic challenge: [brief description]</parameter>
<parameter name="prompt">
PROPOSAL:
[The decision, design, or completed work being challenged]

TRIGGER: [Design finalisation | Phase transition | UAT]

CONTEXT:
[Any relevant background - Definition of Done, design constraints, etc.]
</parameter>
</invoke>
```

## Presenting Results to Human

After receiving counterarguments from the agent, present them with this framing:

```markdown
## Proleptic Challenge

Before proceeding, here are counterarguments to consider:

[Insert agent's counterargument output]

---

**Your judgement is required.** These counterarguments may or may not be valid. Evaluate them and either:
- Dismiss concerns that don't apply (briefly note why)
- Address concerns that do apply (adjust the proposal)
- Proceed with awareness (acknowledge the tradeoff)

When ready, let me know how you'd like to proceed.
```

## After Human Responds

| Human Response | Action |
|----------------|--------|
| Dismisses concerns with reasoning | Proceed to next step |
| Addresses concerns by adjusting proposal | Update proposal, then proceed |
| Acknowledges tradeoff and proceeds | Proceed with noted risk |
| Identifies new issues | Discuss further, do NOT proceed until resolved |

**DO NOT proceed automatically.** Wait for human response.

## The "Drunk Tutor" Framing

Both the proposal AND the counterarguments may be flawed:
- The proposal may have unconsidered risks
- The counterarguments may be based on misunderstanding
- The human must evaluate BOTH critically

**Never present counterarguments as definitive objections.** They are considerations for evaluation.

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "User seems confident, skip challenge" | Confidence ≠ correctness. Challenge anyway. |
| "Design is simple, no need for counterarguments" | Simple designs can have hidden assumptions. |
| "We're running behind, skip this step" | Skipping now = fixing later at higher cost. |
| "Counterarguments seem weak, don't present" | Human judges strength, not you. Present them. |
| "User already addressed these concerns" | Present anyway. Fresh eyes may see new angles. |
| "This is just busywork" | Forcing evaluation prevents premature consensus. |

## Integration with Other Skills

**writing-design-plans:** Invoke proleptic challenge before committing design document.

**executing-an-implementation-plan:** Invoke proleptic challenge after each phase's code review passes, before proceeding to next phase or UAT.

**requesting-code-review:** After code review returns APPROVED, invoke proleptic challenge before UAT gate.

## Remember

**You are a scaffold for thinking, not a gatekeeper.**

The goal is not to block progress but to ensure decisions are made deliberately. Even if all counterarguments are dismissed, the act of evaluation strengthens confidence in the decision.
