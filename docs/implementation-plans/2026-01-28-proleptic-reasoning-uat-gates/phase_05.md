## Phase 5: Integrate UAT Gate into Execution Workflow

**Goal:** Add mandatory human verification after code review in implementation execution

**Dependencies:** Phase 3 (UAT gate skill exists)

**Done when:** Execution workflow stops after code review and waits for human UAT verification

---

<!-- START_TASK_1 -->
### Task 1: Add Human UAT Gate to executing-an-implementation-plan

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md`

**Location:** After the proleptic challenge section added in Phase 4, before proceeding to next phase.

**Step 1: Add UAT gate invocation**

Insert after the proleptic challenge section (from Phase 4 Task 3):

```markdown
### After Proleptic Challenge: Human UAT Gate

**REQUIRED SUB-SKILL:** Use denubis-plan-and-execute:human-uat-gate

After human has evaluated proleptic counterarguments, present UAT:

Announce: "I'm using the human-uat-gate skill to verify this phase meets your requirements."

**Locate Definition of Done:**
- For this phase: from the implementation plan's phase description
- For overall implementation: from the design document's Definition of Done

**Present UAT:**

```markdown
## User Acceptance Testing: Phase [N]

Code review passed. Proleptic counterarguments evaluated. Please verify this phase meets requirements.

### Phase [N] Definition of Done

- [ ] [Criterion from phase description]
- [ ] [Criterion from phase description]
...

### How to Verify

1. [Specific verification step]
2. [Specific verification step]
...

### Your Verification Required

Please verify and respond:
- **"Confirmed"** - Phase complete, proceed to next phase
- **"[Criterion] not met: [reason]"** - Will fix and re-verify

I'll wait for your response.
```

**Handle UAT Response:**

| Response | Action |
|----------|--------|
| Confirmed | Mark phase complete, proceed to next phase |
| Criterion not met | Fix issue → Re-run code review → Proleptic challenge → UAT (loop) |

**UAT rejection flow:**
```
UAT rejected
    → Fix issues
    → Re-run phase code review
    → Proleptic challenge again
    → Re-present UAT
    → Repeat until confirmed
```

**Only after UAT confirmed:** Mark phase tasks complete. Proceed to next phase.
```

**Step 2: Update the phase completion summary**

Ensure the phase flow shows:
```
Phase implementation complete
    ↓
Code review (requesting-code-review skill)
    ↓
Zero issues
    ↓
Proleptic challenge (proleptic-challenge skill)
    ↓
Human evaluates counterarguments
    ↓
UAT gate (human-uat-gate skill)
    ↓
Human confirms
    ↓
Mark phase complete
    ↓
Next phase
```

**Step 3: Verify the modification**

```bash
grep -n "human-uat-gate" plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
```

Expected: Shows references to UAT gate skill

**Step 4: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
git commit -m "feat(plan-and-execute): add human UAT gate to execution workflow

After proleptic challenge, present UAT for explicit human verification.
Rejection loops back to fix and re-verify.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_1 -->
