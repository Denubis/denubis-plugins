---
name: human-uat-gate
description: Use after code review passes to present acceptance criteria and wait for explicit human verification - stops workflow until human confirms implementation meets requirements
---

# Human UAT Gate

## Overview

Present acceptance criteria to the human and wait for explicit verification before proceeding. No automatic continuation.

**Core principle:** UAT is human-falsifiable verification. Simple claims get simple confirmation. Claims with real implications — auth, validation, data integrity, external integration — get boundary probing: where does the implementation's model of reality stop holding? The human doesn't re-run automated tests. The human engages with what only a human can judge.

**Announce at start:** "I'm using the human-uat-gate skill to verify the implementation meets your requirements."

## Workflow Status Line

**On entry** (before presenting UAT):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --skill "human-uat-gate" --context "TEST: verify acceptance criteria"
```

**After human confirms** (UAT passed):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --context ""
```

This tells the human they need to leave the terminal and test the implementation themselves.

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

If no formal falsification tests exist, construct them. For each acceptance criterion, decide:
- **Simple claim** (CRUD, configuration, display): state what to verify and how
- **Boundary-rich claim** (auth, validation, data integrity, concurrency, external integration): identify where the claim stops holding and what to test at the edges

### Step 2: Present UAT to Human

Use this exact format:

```markdown
## User Acceptance Testing

Code review passed. Automated tests cover the happy paths. Below: simple items to confirm, then boundary-rich items to probe.

### Confirm These

[Straightforward claims — CRUD, config, display. Quick verification.]

- [ ] [Claim]: [How to verify — command, UI action, expected result]
- [ ] [Claim]: [How to verify]
...

### Probe These Boundaries

[Claims with real implications — auth, validation, data integrity, external integration. Where does it stop working?]

- [ ] **Claim:** [What the implementation handles]
  **Border:** [Where valid input/state ends]
  **Probe:** [What to try at and beyond the edge — empty input, malformed data, expired state, concurrent access]
  **Should see:** [Graceful failure — error message, rejection, safe fallback. NOT crash, data leak, silent corruption]
- [ ] **Claim:** [...]
  ...

### Your Verification Required

Please confirm the simple items and probe the boundaries. Respond:
- **"Confirmed"** - Everything holds
- **"[Claim] broke at [boundary]: [what you observed]"** - Will fix and re-verify

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

## Constructing Tests

If no formal Popper tests exist in the implementation plan:

1. Review the acceptance criteria
2. **Triage each claim:**

| Claim involves... | Tier | Format |
|-------------------|------|--------|
| CRUD, config, display, scaffolding | Simple | Confirm: [action] → [expected] |
| Auth, permissions, access control | Boundary | Probe edges: wrong credentials, expired tokens, privilege escalation |
| Validation, data integrity | Boundary | Probe edges: empty input, malformed data, boundary values, injection |
| External integration, concurrency | Boundary | Probe edges: service down, timeout, race conditions, partial failure |
| Error handling, recovery | Boundary | Probe edges: cascading failures, corrupt state, retry behaviour |

3. Present to human: "I've split these into simple confirmations and boundary probes. Are there borders I'm missing?"
4. Wait for confirmation before proceeding

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "Tests pass, UAT is redundant" | Tests verify code. Humans verify fitness and find borders automated tests can't reach. |
| "User already knows it works" | Working ≠ knowing where it stops working. Boundaries are invisible until probed. |
| "We're running late" | Skipped UAT = shipped bugs |
| "Code review was thorough" | Code review checks quality, UAT checks fitness |
| "All claims are simple, no boundaries" | If nothing has auth, validation, or data integrity implications, fine — but verify that's actually true. |

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

Automated tests verify correctness. UAT verifies fitness — and for boundary-rich claims, probes where the implementation stops holding. A claim that survives honest attempts at falsification is one you can trust.
