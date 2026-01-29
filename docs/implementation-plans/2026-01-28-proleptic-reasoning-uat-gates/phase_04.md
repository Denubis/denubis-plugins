## Phase 4: Integrate Proleptic Challenge into Existing Skills

**Goal:** Update existing skills to invoke proleptic challenger before phase transitions

**Dependencies:** Phases 1, 2 (challenger and skill exist)

**Done when:** Each skill invokes proleptic challenger at appropriate phase transitions

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Add Proleptic Challenge to writing-design-plans

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`

**Location:** After the "## After Writing: Generating Summary and Glossary" section (ends around line 498), before the "## After Summary and Glossary: Commit" section (starts at line 500).

**Step 1: Add proleptic challenge section**

Insert this section BEFORE the commit step (after Summary/Glossary are generated):

```markdown
## Before Commit: Proleptic Challenge

**REQUIRED:** Before committing the design, invoke proleptic challenge.

This is a phase transition (design → implementation). Challenge the design before it becomes permanent.

**Dispatch proleptic-challenger:**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:proleptic-challenger</parameter>
<parameter name="description">Proleptic challenge: design finalisation</parameter>
<parameter name="prompt">
PROPOSAL:
The design document at [file path] is about to be committed. Key decisions:
- Architecture: [summarise]
- Phases: [count] implementation phases
- Key components: [list]

TRIGGER: Design finalisation

CONTEXT:
Definition of Done:
[paste from document]

This design will guide implementation. Once committed, changes require revisiting the design process.
</parameter>
</invoke>
```

**Present counterarguments to user:**

"Before committing this design, here are counterarguments to consider:"

[Insert agent output]

"Your judgement is required. Evaluate these concerns and let me know how to proceed."

**Wait for human response before committing.**
```

**Step 2: Update the commit section to reference the proleptic challenge**

Modify the existing commit section header to:

```markdown
## After Proleptic Challenge: Commit

**Only commit after human has evaluated proleptic challenge.**
```

**Step 3: Verify the modification**

```bash
grep -n "Proleptic Challenge" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md
```

Expected: Shows the new section around line 500-530

**Step 4: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md
git commit -m "feat(plan-and-execute): add proleptic challenge to writing-design-plans

Invoke proleptic-challenger before committing design document.
Forces deliberate evaluation at design→implementation transition.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add Proleptic Challenge to requesting-code-review

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md`

**Location:** After "### If Zero Issues" section (around line 79-80), add proleptic challenge step.

**Step 1: Modify the zero issues handling**

Replace the existing "### If Zero Issues" section:

```markdown
### If Zero Issues

All categories empty → proceed to proleptic challenge.

**REQUIRED SUB-SKILL:** Use denubis-plan-and-execute:proleptic-challenge

Before proceeding to UAT or next task:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:proleptic-challenger</parameter>
<parameter name="description">Proleptic challenge: code review passed</parameter>
<parameter name="prompt">
PROPOSAL:
Code review passed with zero issues for:
[summary of what was reviewed]

Changes: BASE_SHA to HEAD_SHA
Requirements: [plan or requirements reference]

TRIGGER: Phase transition (code review → UAT)

CONTEXT:
The code review verified:
- Tests pass
- Code quality standards met
- Requirements aligned

This code is about to be accepted as complete for this phase.
</parameter>
</invoke>
```

Present counterarguments to human. Wait for response before proceeding.

**After human evaluates counterarguments:** Proceed to human-uat-gate skill for acceptance verification.
```

**Step 2: Update Integration section**

Add to the Integration section at the end of the file:

```markdown
**Leads to:**
- proleptic-challenge (after zero issues)
- human-uat-gate (after proleptic challenge addressed)
```

**Step 3: Verify the modification**

```bash
grep -n "proleptic" plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md
```

Expected: Shows references to proleptic challenge

**Step 4: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md
git commit -m "feat(plan-and-execute): add proleptic challenge to requesting-code-review

After code review passes with zero issues, invoke proleptic-challenger
before proceeding to UAT gate.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add Proleptic Challenge to executing-an-implementation-plan (between phases)

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md`

**Location:** In section "#### 3c. Code Review for Phase" (around line 199), after "Mark 'Phase Nc: Code review' as complete." (line 261) and before "#### 3d. Move to Next Phase" (line 263).

**Step 1: Add proleptic challenge between phases**

Insert after "Mark 'Phase Nc: Code review' as complete." and before "#### 3d. Move to Next Phase":

```markdown
### After Phase Code Review Passes

**REQUIRED:** Invoke proleptic challenge before proceeding to next phase.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:proleptic-challenger</parameter>
<parameter name="description">Proleptic challenge: Phase N complete</parameter>
<parameter name="prompt">
PROPOSAL:
Phase [N]: [Phase Name] is complete.

What was built:
[summary of phase deliverables]

Code review status: APPROVED with zero issues

TRIGGER: Phase transition (Phase N → Phase N+1)

CONTEXT:
Remaining phases: [list]
Definition of Done for overall implementation: [reference]

This phase is about to be marked complete. The next phase depends on this work.
</parameter>
</invoke>
```

Present counterarguments to human. Wait for response.

**After human evaluates counterarguments:** Proceed to human-uat-gate for phase acceptance.

**Only after UAT confirmed:** Mark phase complete and proceed to next phase.
```

**Step 3: Update the flow diagram**

Update any existing flow diagrams to show:
```
Phase code review passes
    ↓
Proleptic challenge
    ↓
Human evaluates counterarguments
    ↓
UAT gate (human-uat-gate skill)
    ↓
Human confirms phase complete
    ↓
Proceed to next phase
```

**Step 4: Verify the modification**

```bash
grep -n "proleptic" plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
```

Expected: Shows references to proleptic challenge in phase completion

**Step 5: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
git commit -m "feat(plan-and-execute): add proleptic challenge between implementation phases

After phase code review passes, invoke proleptic-challenger before
proceeding to UAT gate and next phase.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
