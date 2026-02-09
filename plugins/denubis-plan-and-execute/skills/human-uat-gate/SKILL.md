---
name: human-uat-gate
description: Use after code review passes to present acceptance criteria and wait for explicit human verification - stops workflow until human confirms implementation meets requirements
---

# Human UAT Gate

## Overview

Present acceptance criteria to the human and wait for explicit verification before proceeding. No automatic continuation.

**Core principle:** UAT is Popper falsification — probing the epistemological boundaries of the implementation. The human doesn't confirm the happy path works (automated tests already do that). The human tests WHERE the implementation's claims about reality stop holding: boundary conditions, edge cases, graceful degradation. "This works" is confirmation. "This is where it stops working, and it fails safely" is falsification.

**Announce at start:** "I'm using the human-uat-gate skill to verify the implementation meets your requirements."

## Workflow Status Line

**On entry** (before presenting UAT):
```bash
[ -x ~/.claude/bin/workflow-state ] && ~/.claude/bin/workflow-state --human "engage"
```

**After human confirms** (UAT passed):
```bash
[ -x ~/.claude/bin/workflow-state ] && ~/.claude/bin/workflow-state --human null
```

This sets the status line to red "ENGAGE" — the strongest signal that the human must leave the terminal and test the implementation themselves.

## When to Invoke

Invoke the UAT gate:
- After code review passes (APPROVED status)
- After proleptic challenge has been presented and addressed
- Before declaring a phase or feature complete

**The gate is mandatory.** Do not skip it because:
- Tests pass
- Code review approved
- User seems satisfied
- Time pressure

## The Gate Process

### Step 1: Locate Falsification Tests

Find the Popper falsification tests from the implementation plan — these are the "**Popper (your UAT):**" entries that accompany each design decision. They define what the human should be able to observe if the implementation is correct.

**Sources (in order of preference):**
- Implementation plan's Popper falsification tests (primary — these ARE the UAT)
- Design document's Definition of Done
- For design work: Phase 3 of starting-a-design-plan
- For features: Requirements from the original request

If no formal falsification tests exist, construct them. For each acceptance criterion, identify:
1. **The claim** — what the implementation says it handles
2. **The boundary** — where the claim stops holding (edge of valid input, resource limits, error conditions)
3. **The test** — what the human does AT and BEYOND the boundary to see if the implementation fails gracefully

### Step 2: Present UAT to Human

Use this exact format:

```markdown
## User Acceptance Testing (Popper Falsification)

Code review passed. Automated tests confirm the happy paths work. Your job is different: **probe the boundaries.** Where does the implementation's model of reality stop matching actual reality?

For each claim below, the implementation asserts it handles the main case AND fails gracefully at the borders. Try to prove it wrong.

### Boundary Tests

[For each Popper test, show the claim AND its borders]

- [ ] **Claim:** [What the implementation handles]
  **Border:** [Where the claim stops — edge of valid input, resource limit, error condition]
  **Test at border:** [What to do AT the boundary]
  **Expected at border:** [Graceful behaviour — error message, rejection, fallback]
  **Test beyond border:** [What to do PAST the boundary — malformed input, missing data, impossible state]
  **Expected beyond:** [Safe failure — no crash, no data leak, no silent corruption]

- [ ] **Claim:** [...]
  **Border:** [...]
  ...

### Probing Steps

[Concrete actions. Not "test login" but "enter empty password, enter SQL in username field, submit with expired session token"]

1. **[Claim 1 — main case]**: [Quick confirmation it works at all]
2. **[Claim 1 — boundary]**: [Steps to push to the edge]
3. **[Claim 1 — beyond]**: [Steps to push past the edge]
4. **[Claim 2 — main case]**: [...]
...

### Your Verification Required

Please probe each boundary and respond:
- **"Confirmed"** - All claims survived falsification at and beyond borders
- **"[Claim] broke at [boundary]: [what you observed]"** - Will fix and re-verify
- **"Need clarification: [question]"** - Unclear on what a boundary should be

I'll wait for your response before proceeding.
```

### Step 3: Wait for Human Response

**DO NOT:**
- Proceed automatically after presenting
- Assume silence means approval
- Prompt user to hurry
- Suggest they skip verification

**DO:**
- Wait patiently for response
- Answer clarifying questions if asked
- Provide additional verification steps if requested

### Step 4: Handle Response

| Human Response | Action |
|----------------|--------|
| "Confirmed" or equivalent | Mark UAT passed, proceed to next phase |
| Specific criterion failed | Fix the issue → Re-run code review → Re-present proleptic challenge → Re-present UAT |
| Clarification needed | Answer question, wait for verification |
| Partial confirmation | Address unconfirmed items before proceeding |

**UAT rejection loops back to fix.** The flow is:
```
UAT rejected
    → Fix issues
    → Re-run code review
    → Proleptic challenge again
    → Re-present UAT
    → Repeat until confirmed
```

## Falsification Test Sources

| Workflow Stage | Where to Find Tests |
|----------------|---------------------|
| Implementation phase | **Popper (your UAT)** entries in the implementation plan (primary source) |
| Design completion | Definition of Done from Phase 3 of starting-a-design-plan |
| Feature completion | Original user request + any clarifications |
| Bug fix | "Bug is fixed when [specific behavior] works — verify by [action]" |

## Constructing Falsification Tests

If no formal Popper tests exist in the implementation plan:

1. Review the original request and design decisions
2. For each acceptance criterion, identify:
   - **The claim**: what the implementation handles
   - **The boundary**: where valid input/state ends — empty strings, zero values, max lengths, missing fields, expired tokens, concurrent access, permission edges
   - **Beyond the boundary**: malformed data, injection attempts, impossible states, resource exhaustion
3. Write tests that probe AT and BEYOND each boundary, not just the main case
4. Present to human: "I've identified these boundaries for testing. Are there borders I'm missing?"
5. Wait for confirmation before proceeding with UAT

**The human should find the borders, not confirm the centre.**

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "Tests pass, UAT is redundant" | Tests confirm the centre. UAT probes the borders. Automated tests verify the happy path; the human finds where the model breaks. Different epistemics. |
| "User already knows it works" | Knowing it works is not knowing WHERE it stops working. Boundaries are invisible until probed. |
| "We're running late" | Skipped UAT = shipped bugs |
| "Code review was thorough" | Code review checks quality, UAT checks fitness |
| "User can test later" | UAT now catches issues before they compound |
| "Criteria seem obvious" | The centre seems obvious. The borders never are. That's why you test them. |

## Integration with Workflow

```
Code review passes (APPROVED)
    ↓
Proleptic challenge (skill: proleptic-challenge)
    ↓
Human evaluates counterarguments
    ↓
UAT gate (this skill)
    ↓
Human verifies acceptance criteria
    ├─ Confirmed → Proceed to next phase
    └─ Rejected → Fix → Code review → Proleptic → UAT (loop)
```

## Remember

**The human is the final arbiter of whether work is complete.**

Automated tests verify the code is correct (does it work?). UAT falsifies claims about fitness for purpose (does it solve the problem?). Both are required. Popper: a claim that survives honest attempts at falsification is one you can trust.
