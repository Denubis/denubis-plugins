---
name: human-uat-gate
description: Use after code review passes for phases where human judgment adds signal automation cannot - presents genuinely falsifiable claims for human interaction and verification
---

# Human UAT Gate

## Overview

Present acceptance criteria to the human and wait for explicit verification before proceeding. No automatic continuation.

**Core principle:** UAT is human-falsifiable verification — the human interacts with the built thing and exercises judgment that automated tests cannot capture. The human doesn't re-run automated tests. The human engages with what only a human can judge.

**This skill is ONLY for phases where human judgment adds signal.** If the phase has no user-facing surface — no UI to navigate, no workflow to evaluate, no output to assess against domain knowledge — use the `coherence-review` skill instead. The orchestrator (executing-an-implementation-plan) handles this routing.

**The test:** "Would a human learn something by doing this that the automated test suite cannot already prove?" If yes for any item in the phase, this skill applies. If no for every item, use `coherence-review`.

**Announce at start:** "I'm using the human-uat-gate skill to verify the implementation meets your requirements."

## When to Invoke

Invoke the UAT gate:
- After code review passes (APPROVED status)
- After proleptic challenge has been presented and addressed
- **Only** when the phase produces something a human can interact with and form a judgment about

**The gate is mandatory for qualifying phases.** Do not skip it because:
- Tests pass
- Code review approved
- User seems satisfied
- Time pressure

## The Gate Process

### Step 1: Locate Falsification Tests

Find the Popper falsification tests from the implementation plan — these are the "**Popper (your UAT):**" entries that describe human interactions requiring judgment. They define what the human should be able to experience and evaluate.

**Sources (in order of preference):**
- Implementation plan's Popper falsification tests (primary — these ARE the UAT)
- Design document's Definition of Done
- For design work: Phase 3 of starting-a-design-plan
- For features: Requirements from the original request

If no formal falsification tests exist, construct them from the acceptance criteria. Every UAT item must describe a human interaction where judgment is required — not a command to run and output to compare.

### Step 2: Present UAT to Human

```markdown
## User Acceptance Testing

Code review passed. Automated tests cover correctness. Below: items where your judgment is needed — things you can interact with, evaluate, and form an opinion about that tests cannot capture.

### Interact and Evaluate

- [ ] **Try:** [Human interaction — use the UI, run the workflow, read the output]
  **Judge:** [What requires human assessment — does it make sense? Is the workflow natural? Does the output look right for the domain?]
  **If wrong:** [What you'd expect to see instead, and what that would mean about the design]

- [ ] **Try:** [Another interaction]
  **Judge:** [What requires human assessment]
  **If wrong:** [What that would mean]
...

### Probe These Boundaries

[For claims with real implications — auth, external integration, data integrity. Where does it stop working?]

- [ ] **Claim:** [What the implementation handles]
  **Border:** [Where valid input/state ends]
  **Probe:** [What to try at and beyond the edge]
  **Should see:** [Graceful failure — NOT crash, data leak, silent corruption]
- [ ] **Claim:** [...]
  ...

### Your Verification Required

Interact with the items above and exercise your judgment. Respond:
- **"Confirmed"** — Everything holds
- **"[Item] doesn't meet expectations: [what you observed vs what you expected]"** — Will fix and re-verify

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
| "All claims are simple, no boundaries" | If no item in this phase requires human judgment, this skill shouldn't have been invoked — use coherence-review instead. But verify that's actually true. |
| "Run this command and see OK" | That's re-running the test suite by hand. If automated tests already verify it, the human gains nothing. This is a sign the phase doesn't qualify for UAT — use coherence-review. |
| "Curl this endpoint and check the response" | Unless the human is evaluating something subjective about the response, that's an integration test. Write the test instead. |

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
