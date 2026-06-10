---
name: exec-coherence-review
family: executing-an-implementation-plan
description: Use after code review for phases without human-judgment UAT - verifies implementation coheres with design intent and surfaces baked-in assumptions
user-invocable: false
---

# Coherence Review

## Overview

Verify that an implementation phase coheres with its design intent and will support future human acceptance testing. This replaces the UAT gate for phases that have no human-judgment UAT of their own.

**When to use:** After code review passes and proleptic challenge is presented, for phases where human judgment does not add signal that automation cannot provide. Most implementation phases fall into this category — data models, validators, infrastructure, internal services, APIs without a client to exercise them.

**When NOT to use:** When the phase produces something a human can interact with and form a judgment about — a UI to navigate, a workflow to evaluate, extracted data to assess against domain knowledge, a report to read. Those phases use the `exec-uat-gate` skill instead.

**The test:** For each potential verification item, ask: "Would a human learn something by doing this that the automated test suite cannot already prove?" If the answer is no for every item in the phase, use this skill. If yes for any item, use `exec-uat-gate`.

**Announce at start:** "I'm using the exec-coherence-review skill to verify this phase's implementation matches the design intent."

## The Dispatch

After proleptic challenge has been presented and the human has evaluated counterarguments, dispatch the coherence-reviewer agent:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:coherence-reviewer</parameter>
<parameter name="description">Coherence review: Phase [N] — [Phase Name]</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
Review whether Phase [N]'s implementation coheres with the design intent.

DIFF_RANGE: [BASE_SHA]..[HEAD_SHA]
DESIGN_PLAN: [absolute path to design plan]
PHASE_FILE: [absolute path to implementation plan phase file]
ARCH_DOCS: [absolute path to architecture docs directory, or "none"]
FUTURE_PHASES: [list remaining phase titles and their goals, extracted from phase headers]
WORKING_DIRECTORY: [absolute path]
SCRATCHPAD_DIR: ${SCRATCHPAD_DIR}

Check all six dimensions:
1. Conformance — does the implementation match the design's architectural intent?
2. Traceability — decision → code → test → doc chain, with gaps flagged
3. Baked-in assumptions — decisions the implementation made where the design was silent
4. Forward fitness — will this support the future human-judgment UAT?
5. Situated accountability — whose perspective shaped these decisions? who's absent?
6. Architecture doc updates — do the docs need updating based on this phase's work?

Write findings to ${SCRATCHPAD_DIR}/exec-coherence-review.md
</parameter>
</invoke>
```

**Print the full coherence-reviewer response** (transparency rules from executing-an-implementation-plan).

## Presenting to the Human

After the coherence reviewer completes, present the findings to the human. The presentation format depends on what was found:

### If findings exist (any severity):

```markdown
## Phase [N] Coherence Review

Code review passed. Proleptic challenge evaluated. This phase has no human-judgment UAT — the real acceptance testing comes in Phase [M] when [what the human will actually do].

### What Was Built vs What Was Designed
[Conformance findings — erosion and drift]

### Baked-In Assumptions
[Decisions the implementation made that the design was silent on. For each:]
- **Design said:** [what] → **Implementation chose:** [what] — [benign/notable/concerning]

### Forward Fitness
[Will this support Phase [M]'s human-judgment UAT?]
[What a hostile reviewer would flag]

### Situated Accountability
[Whose perspective? Who's absent? — only if non-trivial]

### Architecture Doc Updates
[Specific updates proposed, if any]

### Your Review Required

These are the structural decisions underlying the work. The code is correct (tests pass, code review approved). The question is whether the *understanding* is right.

- **"Confirmed"** — decisions and assumptions match your intent
- **"[Assumption] doesn't match my intent: [what you expected]"** — will revise and re-review
- **"[Architecture doc update] needs change: [what]"** — will revise docs

I'll wait for your response before proceeding.
```

### If no notable findings:

```markdown
## Phase [N] Coherence Review — No Findings

Coherence reviewer checked [N files, M-line diff] against [design plan name]:
- **Conformance:** [one sentence — e.g. "Implementation follows design's module structure. No structural divergence."]
- **Traceability:** [one sentence — e.g. "3 design decisions traced to code and tests. No gaps." OR "No Decision Records in design plan — traceability check limited to AC coverage."]
- **Baked-in assumptions:** [list any benign ones briefly, or "None — implementation matched design specification exactly."]
- **Forward fitness:** [one sentence — e.g. "Phase 3 needs TokenService interface; confirmed present with expected signature."]

No findings above benign. The real acceptance testing comes in Phase [M] when [what the human will actually do].

Proceeding to refactoring.
```

**Why enumerate what was checked:** If the reviewer found nothing, the human should see WHAT was checked and WHY nothing stood out — not just "all clear." A blank report gives no confidence. A report that says "I checked these 4 things and here's why each was fine" gives the human a reason to trust the result or to push back ("you didn't check X").

## Handling Responses

| Human Response | Action |
|----------------|--------|
| "Confirmed" or equivalent | Proceed to phase refactor |
| Specific assumption doesn't match intent | Fix the implementation → Re-run code review → Proleptic challenge → Coherence review (loop) |
| Architecture doc update needs change | Revise the doc update, present again |
| "Proceed but note [concern]" | Record the concern (it may affect future phases), proceed to refactor |

## Integration with Execution Flow

This skill is invoked by `executing-an-implementation-plan` in place of `exec-uat-gate` when the phase has no human-judgment UAT.

**Phase completion flow (phases without human-judgment UAT):**
```
Code review → Proleptic → Coherence review → Human confirms → Refactor → Next phase
```

**Phase completion flow (phases with human-judgment UAT):**
```
Code review → Proleptic → UAT gate (exec-uat-gate skill) → Human confirms → Refactor → Next phase
```

The orchestrator determines which path to take using the deterministic routing rubric in executing-an-implementation-plan (based on Phase Type and Popper UAT entry presence, not LLM judgment).
