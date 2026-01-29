## Phase 3: Human UAT Gate Skill

**Goal:** Create explicit human verification gate after code review

**Dependencies:** None (can be developed in parallel with Phases 1-2)

**Done when:** Skill provides clear template for presenting acceptance criteria and waiting for human response

---

<!-- START_TASK_1 -->
### Task 1: Create Human UAT Gate Skill

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/human-uat-gate/SKILL.md`

**Step 1: Create directory and skill file**

```markdown
---
name: human-uat-gate
description: Use after code review passes to present acceptance criteria and wait for explicit human verification - stops workflow until human confirms implementation meets requirements
---

# Human UAT Gate

## Overview

Present acceptance criteria to the human and wait for explicit verification before proceeding. No automatic continuation.

**Core principle:** Humans verify implementations meet their actual needs, not just automated checks.

**Announce at start:** "I'm using the human-uat-gate skill to verify the implementation meets your requirements."

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

### Step 1: Locate Definition of Done

Find the acceptance criteria from earlier in the workflow:
- For design work: Definition of Done from Phase 3 of starting-a-design-plan
- For implementation: Definition of Done from the design document
- For features: Requirements from the original request

If no formal Definition of Done exists, construct one from the original request.

### Step 2: Present UAT to Human

Use this exact format:

```markdown
## User Acceptance Testing

Code review has passed. Before proceeding, please verify the implementation meets your requirements.

### Definition of Done

[List each acceptance criterion as a checkbox]

- [ ] Criterion 1: [Description]
- [ ] Criterion 2: [Description]
- [ ] Criterion 3: [Description]
...

### How to Verify

[Provide specific steps the human should take to verify each criterion]

1. **[Criterion 1]**: [How to test it - commands, UI actions, etc.]
2. **[Criterion 2]**: [How to test it]
...

### Your Verification Required

Please verify these criteria and respond with one of:
- **"Confirmed"** - All criteria met, proceed
- **"[Criterion N] not met: [reason]"** - Specific failure, will fix and re-verify
- **"Need clarification: [question]"** - Unclear on how to verify

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

## Definition of Done Sources

| Workflow Stage | Where to Find Definition of Done |
|----------------|----------------------------------|
| Design completion | Phase 3 of starting-a-design-plan created the document |
| Implementation phase | Design document's Definition of Done section |
| Feature completion | Original user request + any clarifications |
| Bug fix | "Bug is fixed when [specific behavior] works" |

## Constructing Definition of Done

If no formal Definition of Done exists:

1. Review the original request
2. Extract testable criteria
3. Present to human: "I've constructed these acceptance criteria from your request. Are these correct?"
4. Wait for confirmation before proceeding with UAT

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "Tests pass, UAT is redundant" | Tests verify code, UAT verifies requirements |
| "User already knows it works" | Explicit verification prevents assumptions |
| "We're running late" | Skipped UAT = shipped bugs |
| "Code review was thorough" | Code review checks quality, UAT checks fitness |
| "User can test later" | UAT now catches issues before they compound |
| "Criteria seem obvious" | Obvious to you ≠ obvious to user |

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

Automated checks verify correctness. UAT verifies fitness for purpose. Both are required.
```

**Step 2: Verify the skill was created**

```bash
# Verify file exists and has correct frontmatter
head -5 plugins/denubis-plan-and-execute/skills/human-uat-gate/SKILL.md
```

Expected: YAML frontmatter with name: human-uat-gate, description

**Step 3: Commit the skill**

```bash
git add plugins/denubis-plan-and-execute/skills/human-uat-gate/SKILL.md
git commit -m "feat(plan-and-execute): add human-uat-gate skill

Presents acceptance criteria and waits for explicit human verification
after code review passes. Rejection loops back to fix and re-verify.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_1 -->
