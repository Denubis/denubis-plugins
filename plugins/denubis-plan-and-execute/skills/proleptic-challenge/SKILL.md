---
name: proleptic-challenge
description: Use before phase transitions to generate counterarguments and force deliberate evaluation - fires at design finalisation, between implementation phases, and before acceptance
---

# Proleptic Challenge

## Overview

Generate counterarguments before committing to decisions. Force deliberate evaluation rather than premature consensus.

**Core principle:** The value is in the evaluation, not the counterarguments.

**Announce at start:** "I'm using the proleptic-challenge skill to generate counterarguments before we proceed."

## Theoretical Foundation

Based on proleptic reasoning from argumentation theory—anticipating objections, articulating them charitably, and responding preemptively.

**Reference:** Kudina, O., Ballsun-Stanton, B., & Alfano, M. (2025). The use of large language models as scaffolds for proleptic reasoning. *Asian Journal of Philosophy*, 4, 24. DOI: 10.1007/s44204-025-00247-1

## When to Invoke

Proleptic challenges fire **before phase transitions**, not at every decision point:

| Trigger | When | What Gets Challenged |
|---------|------|---------------------|
| Design finalisation | After design-write completes, before commit | The design about to be committed |
| Between implementation phases | After phase code review passes, before UAT/coherence routing | The completed phase before moving to next |
| Before acceptance | After code review passes on final phase, before UAT or coherence review | The implementation before declaring complete |

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

## Presenting Findings: No Pre-Filtering

**Present ALL counterarguments to the human.** Do not dismiss, downgrade, or filter findings on the human's behalf. "I think this one is fine" is not dismissal — it is the orchestrator overriding the challenge process.

If the challenger found it worth raising, it goes to the human. The human decides what to dismiss.

## After Human Responds

| Human Response | Action |
|----------------|--------|
| Dismisses with cited evidence | Proceed. Evidence = specific file, design plan section, or test that refutes the concern |
| Addresses concerns by adjusting proposal | Update proposal, then proceed |
| Acknowledges tradeoff and proceeds | Proceed with noted risk |
| Identifies new issues | Discuss further, do NOT proceed until resolved |
| Dismisses without evidence | Ask for evidence. "Which file/test/design section refutes this?" |

**DO NOT proceed automatically.** Wait for human response.

**Dismissal requires evidence.** A dismissed concern must cite the specific code (`file::symbol`), design plan section, or test that makes the concern inapplicable. "I've already considered this" or "that's not relevant" without a citation is not sufficient — ask what specifically refutes it.

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
| "This concern doesn't apply" | Cite the specific code or design section that refutes it, or present it. |
| "User already addressed these concerns" | Present anyway. Fresh eyes may see new angles. |
| "This is just busywork" | Forcing evaluation prevents premature consensus. |

## Integration with Other Skills

**design-write:** Invoke proleptic challenge before committing design document.

**executing-an-implementation-plan:** Invoke proleptic challenge after each phase's code review passes, before proceeding to next phase or UAT.

**requesting-code-review:** After code review returns APPROVED, invoke proleptic challenge before UAT gate.

## Remember

**You are a scaffold for thinking, not a gatekeeper.**

The goal is not to block progress but to ensure decisions are made deliberately. Even if all counterarguments are dismissed, the act of evaluation strengthens confidence in the decision.
