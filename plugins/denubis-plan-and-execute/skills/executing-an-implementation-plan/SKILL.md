---
name: executing-an-implementation-plan
description: Use when executing implementation plans with independent tasks in the current session - dispatches fresh subagent for each task, reviews once per phase, loads phases just-in-time to minimize context usage
user-invocable: true
---

# Executing an Implementation Plan

Execute plan phase-by-phase, loading each phase just-in-time to minimize context usage.

**Core principle:** Red-Green-Refactor at the macro level. Read one phase → execute all tasks → review + UAT (Green) → refactor → move to next phase. Never load all phases upfront.

**REQUIRED SKILL:** `requesting-code-review` - The review loop (dispatch, fix, re-review until zero issues)

## Anti-Pattern: "I Think This Should Work"

A build fails. You change something without reading the error properly. It fails again. You change something else. Three attempts later you've introduced new problems on top of the original one. Each attempt started with "I think this should work" but you never investigated *why the previous attempt failed*.

**When something breaks during implementation:**
1. STOP. Read the error message completely.
2. Read the relevant source code, docs, or prior art in the codebase.
3. State your hypothesis: "I believe X is wrong because Y."
4. State your falsification: "If I change Z, I expect W. If I see V instead, this hypothesis is wrong."
5. Make the single change. Observe against your prediction.

**If your fix fails:** Do NOT try another fix. Investigate why it failed. The failed fix gave you new information — use it. If you skip investigation and jump to attempt #2, you are cut-and-trying.

**If 3 fixes fail:** STOP and invoke `systematic-debugging`. The problem is deeper than you thought.

## Overview

**When NOT to use:**
- No implementation plan exists yet (use writing-implementation-plans first)
- Plan needs revision (brainstorm first)

## Precondition: Worktree Required

**NEVER start implementation on the main/master branch.** Before executing any plan, verify you are in a git worktree (or at minimum a feature branch). If you are on main/master:

1. STOP. Do not proceed.
2. Use `denubis-plan-and-execute:using-git-worktrees` to create an isolated workspace.
3. Resume execution in the worktree.

**Check:** `git branch --show-current` — if it returns `main` or `master`, you are in the wrong place.

## Workflow Status Line

Update the breadcrumb status line at phase transitions so the human knows what's happening when they tab back to this session. If the state script is not installed, skip these silently.

**On entry** (after discovering phases, extract slug from plan directory name):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --feature "<slug>" --skill "executing-impl" --context ""
```

**When reading each phase** (extract phase name from title, e.g. "CRDT Cloning" from "Phase 4: CRDT Cloning"):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --context "Phase N: <Phase Name>"
```

| Transition | `--skill` | `--context` |
|------------|-----------|-------------|
| Executing tasks | `executing-impl` | `Phase N: <name> — Task M` |
| Code review running | `code-review` | `reviewing Phase N` |
| Three-strike help needed | | `BLOCKED: 3 failures — need direction` |
| Proleptic challenge presented | `proleptic-challenge` | sub-skill handles |
| After human evaluates proleptic | `executing-impl` | `Phase N: <name>` |
| UAT gate presented | `human-uat-gate` | sub-skill handles |
| After UAT confirmed | `executing-impl` | `Phase N: <name>` |
| Phase refactor running | `executing-impl` | `refactoring Phase N` |
| Final code review | `code-review` | `final review` |
| Finishing branch | `finishing` | sub-skill handles |

## MANDATORY: Human Transparency

**The human cannot see what subagents return. You are their window into the work.**

After EVERY subagent completes (task-implementor, bug-fixer, code-reviewer), you MUST:

1. **Print the subagent's full response** to the user before taking any other action
2. **Do not summarize or paraphrase** - show them what the subagent actually said
3. **Include all details:** test counts, issue lists, commit hashes, error messages

**Before dispatching any subagent:**
- Briefly explain (2-3 sentences) what you're asking the agent to do
- State which phase this covers

**Why this matters:** When you silently process subagent output without showing the user, they lose visibility into their own codebase. They can't catch errors, learn from the process, or intervene when needed. Transparency is not optional.

**Red flag:** If you find yourself thinking "I'll just move on to the next step" without printing the subagent's response, STOP. Print it first.

## Null / Empty Subagent Response (Turn Exhaustion)

**A null or empty response from any subagent (task-implementor, bug-fixer, code-simplifier, etc.) means it ran out of turns.**

This is NOT a transient error and retrying with the same budget will produce the same result.

**Action:** HALT and tell the human:
```
"[Agent name] returned an empty response — it exhausted its max_turns budget (currently N).
We need to revise max_turns for this agent before continuing."
```

Do not silently retry, skip the task, or proceed without the result.

## No Cut-and-Try

When encountering failures during implementation — build errors, test failures, unexpected behaviour:

**Do not** try random fixes hoping something sticks. Every attempted fix must follow experimental discipline:

1. **Read first:** Understand the error. Read the relevant source, docs, or prior art in the codebase.
2. **State your prediction:** "I believe X is wrong because Y. If I change Z, I expect to see W."
3. **State the falsification:** "If I see V instead of W, this hypothesis is wrong and I need to investigate further."
4. **Make the single change.** Observe the result against your prediction.
5. **Pause for feedback** if the result contradicts your prediction. Report what you predicted, what happened, and what that means — before attempting another fix.

This applies to you AND to subagents. When dispatching task-implementor or bug-fixer, they inherit this discipline through their own skill references.

## REQUIRED: Implementation Plan Path

**DO NOT GUESS.** If the user has not provided a path to an implementation plan directory, you MUST ask for it.

Use AskUserQuestion:
```
Question: "Which implementation plan should I execute?"
Options:
  - [list any plan directories you find in docs/implementation-plans/]
  - "Let me provide the path"
```

If `docs/implementation-plans/` doesn't exist or is empty, ask the user to provide the path directly.

**Never assume, infer, or guess which plan to execute.** The user must explicitly tell you.

## The Process

### 1. Discover Phases

**DO NOT read the full phase files yet.** List them and read only the header and task markers.

```bash
# List phase files
ls [plan-directory]/phase_*.md

# For each file, get the header (first 10 lines include title and Goal)
head -10 [plan-directory]/phase_01.md

# Get task/subcomponent structure without reading full content
grep -E "START_TASK_|START_SUBCOMPONENT_" [plan-directory]/phase_01.md
```

The header includes the title (`# [Phase Title]`) and `**Goal:**` line. Extract the title for the task entry.

The grep output shows the task structure, e.g.:
```
<!-- START_TASK_1 -->
<!-- START_TASK_2 -->
<!-- START_SUBCOMPONENT_A (tasks 3-5) -->
<!-- START_TASK_3 -->
<!-- START_TASK_4 -->
<!-- START_TASK_5 -->
```

Examples of headers you might see:
- `# Document Infrastructure Implementation Plan` — Phase 1 implied
- `# Phase 4: Link Resolution` — Phase number explicit

**Check for implementation guidance:**

After discovering phases, check if `.ed3d/implementation-plan-guidance.md` exists in the project root:

```bash
# Check for implementation guidance (note the absolute path for later use)
ls [project-root]/.ed3d/implementation-plan-guidance.md
```

If the file exists, note its **absolute path** for use during code reviews. If it doesn't exist, proceed without it—do not pass a nonexistent path to reviewers.

**Check for test requirements:**

Check if `test-requirements.md` exists in the plan directory:

```bash
# Check for test requirements (note the absolute path for later use)
ls [plan-directory]/test-requirements.md
```

If the file exists, note its **absolute path** for use during final review. The test requirements document specifies what automated tests must exist for each acceptance criterion.

### 2. Create Phase-Level Task List

Use TaskCreate to create **three task entries per phase**. Include the title from the header:

```
- [ ] Phase 1a: Read /absolute/path/to/phase_01.md — Document Infrastructure Implementation Plan
- [ ] Phase 1b: Execute tasks
- [ ] Phase 1c: Code review
- [ ] Phase 2a: Read /absolute/path/to/phase_02.md — API Integration
- [ ] Phase 2b: Execute tasks
- [ ] Phase 2c: Code review
...
```

**Why absolute paths in task entries:** After compaction, context may be summarized. The absolute path in the task entry ensures you always know exactly which file to read.

**Why include the title:** Gives visibility into what each phase covers without loading full content.

### 3. Execute Each Phase

For each phase, follow this cycle:

#### 3a. Read Phase File (just-in-time)

Mark "Phase Na: Read [path]" as in_progress.

Read ONLY that phase file now. Extract:
- List of tasks in this phase
- Working directory
- Any phase-specific context

Mark "Phase Na: Read" as complete.

#### 3b. Execute All Tasks

Mark "Phase Nb: Execute tasks" as in_progress.

**Before dispatching, verify test coverage for functionality tasks:**

If a functionality task (code that does something) has no tests specified:
1. Check if a subsequent task in the same phase provides tests
2. If no tests exist anywhere for this functionality → **STOP**
3. This is a plan gap. Surface to user: "Task N implements [functionality] but no corresponding tests exist in the plan. This needs tests before implementation."

Do NOT implement functionality without tests. Missing tests = plan gap, not something to skip.

**Execute all tasks in sequence.** For each task, dispatch `task-implementor` with the phase file path:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:task-implementor</parameter>
<parameter name="description">Implementing Phase X, Task Y: [description]</parameter>
<parameter name="max_turns">45</parameter>
<parameter name="prompt">
  Implement Task N from the phase file.

  Phase file: [absolute path to phase file]
  Task number: N

  Read the phase file and implement Task N (look for `<!-- START_TASK_N -->`).

  Your job is to:
  1. Read the phase file to understand context
  2. Apply all relevant skills, such as (if available) coding-effectively
  3. Implement exactly what Task N specifies
  4. Verify with tests/build/lint
  5. Commit your work
  6. Report back with evidence

  Work from: [directory]

  Provide complete report per your agent instructions.
</parameter>
</invoke>
```

**For subcomponents** (grouped tasks), dispatch once for all tasks in the subcomponent:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:task-implementor</parameter>
<parameter name="description">Implementing Phase X, Subcomponent A (Tasks 3-5): [description]</parameter>
<parameter name="max_turns">45</parameter>
<parameter name="prompt">
  Implement Subcomponent A (Tasks 3, 4, 5) from the phase file.

  Phase file: [absolute path to phase file]
  Tasks: 3, 4, 5 (look for `<!-- START_SUBCOMPONENT_A -->`)

  Read the phase file and implement all tasks in this subcomponent.

  Your job is to:
  1. Read the phase file to understand context
  2. Apply all relevant skills, such as (if available) coding-effectively
  3. Implement all tasks in sequence
  4. Verify with tests/build/lint after completing all tasks
  5. Commit your work (one commit per task, or logical commits)
  6. Report back with evidence for each task

  Work from: [directory]

  Provide complete report covering all tasks.
</parameter>
</invoke>
```

**Print each task-implementor's response** before moving to the next task.

**No code review between tasks.** Execute all tasks in the phase first.

After all tasks complete, mark "Phase Nb: Execute tasks" as complete.

#### 3c. Code Review for Phase

Mark "Phase Nc: Code review" as in_progress.

**MANDATORY:** Use the `requesting-code-review` skill for the review loop.

**Context to provide:**
- WHAT_WAS_IMPLEMENTED: Summary of all tasks in this phase
- PLAN_OR_REQUIREMENTS: All tasks from this phase
- BASE_SHA: commit before phase started
- HEAD_SHA: current commit
- IMPLEMENTATION_GUIDANCE: absolute path to `.ed3d/implementation-plan-guidance.md` (**only if it exists**—omit entirely if the file doesn't exist)

The implementation guidance file contains project-specific coding standards, testing requirements, and review criteria. When provided, the code reviewer should read it and apply those standards during review.

**Note:** Test requirements validation happens at final review, not per-phase. Per-phase reviews focus on code quality and whether the phase includes tests for its functionality.

**If code reviewer returns a context limit error:**

The phase changed too much for a single review. Chunk the review:

1. Identify the midpoint of tasks in the phase
2. Run code review for first half of tasks (commits for tasks 1 through N/2)
3. Fix any issues found
4. Run code review for second half of tasks (commits for tasks N/2+1 through N)
5. Fix any issues found

**When issues are found:**

1. **Create a task for EACH issue** (survives compaction):
   ```
   TaskCreate: "Phase N fix [Critical]: <VERBATIM issue description from reviewer>"
   TaskCreate: "Phase N fix [Important]: <VERBATIM issue description from reviewer>"
   TaskCreate: "Phase N fix [Minor]: <VERBATIM issue description from reviewer>"
   ...one task per issue...
   TaskCreate: "Phase N: Re-review after fixes"
   TaskUpdate: set "Re-review" blocked by all fix tasks
   ```

   **Copy issue descriptions VERBATIM**, even if long. After compaction, the task description is all that remains — it must contain the full issue details for the bug-fixer to understand what to fix.

2. **Dispatch `task-bug-fixer`** with the phase file:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:task-bug-fixer</parameter>
<parameter name="description">Fixing review issues for Phase X</parameter>
<parameter name="max_turns">30</parameter>
<parameter name="prompt">
  Fix issues from code review for Phase X.

  Phase file: [absolute path to phase file]

  Code reviewer found these issues:
  [list all issues - Critical, Important, and Minor]

  Read the phase file to understand the tasks and context.

  Your job is to:
  1. Understand root cause of each issue
  2. Apply fixes systematically (Critical → Important → Minor)
  3. Verify with tests/build/lint
  4. Commit your fixes
  5. Report back with evidence

  Work from: [directory]

  Fix ALL issues — including every Minor issue. The goal is ZERO issues on re-review.
  Minor issues are not optional. Do not skip them.
</parameter>
</invoke>
```

3. **Mark "Fix issues" complete**, then re-review per the `requesting-code-review` skill.

4. **If re-review finds more issues**, create new fix/re-review tasks. Continue loop until zero issues.

5. **Mark "Re-review" complete** when zero issues.

**Plan execution policy (stricter than general code review):**
- ALL issues must be fixed (Critical, Important, AND Minor)
- Ignore APPROVED/BLOCKED status - count issues only
- **Three-strike rule:** If same issues persist after three review cycles, stop and ask human for help

**Minor issues are NOT optional.** Do not rationalize skipping them with "they're just style issues" or "we can fix those later." The reviewer flagged them for a reason. Fix every single one.

**Exit condition:** Zero issues in all categories — including Minor.

Mark "Phase Nc: Code review" as complete.

### After Phase Code Review Passes

**REQUIRED:** Invoke proleptic challenge before proceeding to next phase.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:proleptic-challenger</parameter>
<parameter name="description">Proleptic challenge: Phase N complete</parameter>
<parameter name="max_turns">15</parameter>
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

### After Proleptic Challenge: Human UAT Gate

**REQUIRED SUB-SKILL:** Use denubis-plan-and-execute:human-uat-gate

After human has evaluated proleptic counterarguments, present UAT:

Announce: "I'm using the human-uat-gate skill to verify this phase meets your requirements."

**Locate acceptance criteria:**
- Primary: **"Popper (your UAT):"** entries from the implementation plan's design decisions
- Fallback: Phase acceptance criteria from the phase description
- Overall: Definition of Done from the design document

**Triage claims:** Simple items (CRUD, config, display) get quick confirmation. Boundary-rich items (auth, validation, data integrity, external integration) get edge probing. Use the `human-uat-gate` skill's tiered format.

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

**Only after UAT confirmed:** Proceed to phase refactor.

#### 3d. Phase Refactor (Red-Green-**Refactor**)

The phase is Green — tests pass, UAT confirmed. Now clean up before building the next phase on top.

**Scope:** Only files touched by this phase. No cross-module reorganisation.

**What to refactor:**
- Reduce duplication, improve naming, extract helpers
- Simplify overly complex logic from minimal-to-pass implementations
- Fix code smells

**Rules:** No features, no behaviour changes. If tests break, revert.

**If `code-simplifier:code-simplifier` is available**, dispatch it:

```
<invoke name="Task">
<parameter name="subagent_type">code-simplifier:code-simplifier</parameter>
<parameter name="description">Phase [N] refactor</parameter>
<parameter name="max_turns">20</parameter>
<parameter name="prompt">
Simplify code changed in this phase. Files: [list]. Working directory: [dir].
Preserve all functionality. Find the test command in CLAUDE.md and run after changes.
Commit refactoring separately from implementation.
</parameter>
</invoke>
```

**If code-simplifier is not available**, refactor directly — review the phase's files yourself, apply the same criteria, keep tests green, commit separately.

**After refactoring:** Run tests. If green, mark phase complete. If tests fail, revert and proceed without.

**Phase completion flow:**
```
Code review → Proleptic → UAT → Refactor → Verify green → Next phase
```

#### 3e. Move to Next Phase

Proceed to the next phase's "Read" step. Repeat 3a-3d for each phase.

### 4. Update Project Context

After all phases complete, invoke the `denubis-extending-claude:project-claude-librarian` subagent (when available) to review changes and update CLAUDE.md files if needed.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-extending-claude:project-claude-librarian</parameter>
<parameter name="description">Updating project context after implementation</parameter>
<parameter name="max_turns">15</parameter>
<parameter name="prompt">
  Review what changed during this implementation and update CLAUDE.md files if contracts or structure changed.

  Base commit: <commit SHA at start of first phase>
  Current HEAD: <current commit>
  Working directory: <directory>

  Follow the denubis-extending-claude:maintaining-project-context skill to:
  1. Diff against base to see what changed
  2. Identify contract/API/structure changes
  3. Update affected CLAUDE.md files
  4. Commit documentation updates

  Report back with what was updated (or that no updates were needed).
</parameter>
</invoke>
```

**If librarian reports updates:** Review the changes, then proceed to final review.
**If librarian reports no updates needed:** Proceed to final review.
**If librarian subagent is unavailable:** skip this entire step. Say aloud that you're skipping it because the `denubis-extending-claude` plugin is not available.

### 5. Final Review Sequence

After all phases complete, run a sequence of specialized agents:

```
Code Review → Test Analysis (Coverage + Plan)
```

#### 5a. Final Code Review

Use the `requesting-code-review` skill for final code review:

**Context to provide:**
- WHAT_WAS_IMPLEMENTED: Summary of all phases completed
- PLAN_OR_REQUIREMENTS: Reference to the full implementation plan directory
- BASE_SHA: commit before first phase started
- HEAD_SHA: current commit
- IMPLEMENTATION_GUIDANCE: absolute path (if exists)
- AC_COVERAGE_CHECK: "Verify all acceptance criteria (using scoped format `{slug}.AC*`) from the design plan are covered by at least one phase. Flag any ACs not addressed."

Continue the review loop until zero issues remain.

#### 5b. Test Analysis

**Only after final code review passes with zero issues.**

**Skip this step if test-requirements.md does not exist.**

The test-analyst agent performs two sequential tasks with shared analysis:
1. Validate coverage against acceptance criteria
2. Generate human test plan (only if coverage passes)

Dispatch the test-analyst agent:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:test-analyst</parameter>
<parameter name="description">Analyzing test coverage and generating test plan</parameter>
<parameter name="max_turns">20</parameter>
<parameter name="prompt">
Analyze test implementation against acceptance criteria.

TEST_REQUIREMENTS_PATH: [absolute path to test-requirements.md]
WORKING_DIRECTORY: [project root]
BASE_SHA: [commit before first phase]
HEAD_SHA: [current commit]

Phase 1: Validate that automated tests exist for all acceptance criteria.
Phase 2: If coverage passes, generate human test plan using your analysis.

Return coverage validation result. If PASS, include the human test plan.
</parameter>
</invoke>
```

**If analyst returns coverage FAIL:**

1. Dispatch bug-fixer to add missing tests:
   ```
   <invoke name="Task">
   <parameter name="subagent_type">denubis-plan-and-execute:task-bug-fixer</parameter>
   <parameter name="description">Adding missing test coverage</parameter>
   <parameter name="max_turns">30</parameter>
   <parameter name="prompt">
   Add missing tests identified by the test analyst.

   Missing coverage:
   [list from analyst output]

   For each missing test:
   1. Read the acceptance criterion carefully
   2. Create the test file at the expected location
   3. Write tests that verify the criterion's actual behavior—not just code that passes, but code that would fail if the criterion weren't met
   4. Find the test command in CLAUDE.md and run it to confirm they pass
   5. Commit the new tests

   Work from: [directory]
   </parameter>
   </invoke>
   ```

2. Re-run test-analyst
3. Repeat until coverage PASS or three attempts fail (then escalate to human)

**If analyst returns coverage PASS:**

The response will include the human test plan. Extract the "Human Test Plan" section.

**Write the test plan:**

```bash
# Create test-plans directory if needed
mkdir -p docs/test-plans

# The filename uses the implementation plan directory name
# e.g., impl plan dir: docs/implementation-plans/2025-01-24-oauth/
#       test plan:     docs/test-plans/2025-01-24-oauth.md
```

Write the test plan content to `docs/test-plans/[impl-plan-dir-name].md`, then commit:

```bash
git add docs/test-plans/[impl-plan-dir-name].md
git commit -m "docs: add test plan for [feature name]"
```

Announce: "Human test plan written to `docs/test-plans/[impl-plan-dir-name].md`"

### 6. Complete Development

After final review passes:

- Provide a report to the human operator
  - For each phase:
    - How many tasks were implemented
    - How many review cycles were needed
    - Any compromises made (there should be NO compromises, but if any were made). Examples:
      - "I couldn't run the integration tests, so I continued on"
      - "I couldn't generate the client because the dev environment was down"
      - Note that these are PARTIAL FAILURE CASES and explain to the user what the user must do now.
    - Were any code-review issues left outstanding at any point?

- Activate the `finishing-a-development-branch` skill. DO NOT activate it before this point.

## Example Workflow

```
You: I'm using the `executing-an-implementation-plan` skill.

[Discover phases: phase_01.md, phase_02.md, phase_03.md]
[Read first 3 lines of each to get titles]

[Create tasks with TaskCreate:]
- [ ] Phase 1a: Read /path/to/phase_01.md — Project Setup
- [ ] Phase 1b: Execute tasks
- [ ] Phase 1c: Code review + UAT
- [ ] Phase 1d: Refactor
- [ ] Phase 2a: Read /path/to/phase_02.md — Token Service
- [ ] Phase 2b: Execute tasks
- [ ] Phase 2c: Code review + UAT
- [ ] Phase 2d: Refactor
- [ ] Phase 3a: Read /path/to/phase_03.md — API Middleware
- [ ] Phase 3b: Execute tasks
- [ ] Phase 3c: Code review + UAT
- [ ] Phase 3d: Refactor

--- Phase 1 ---

[Mark 1a in_progress, read phase_01.md]
→ Contains 2 tasks: project setup, config files

[Mark 1a complete, 1b in_progress]

[Dispatch task-implementor for Task 1]
→ Created pyproject.toml, ruff.toml.

[Dispatch task-implementor for Task 2]
→ Created config files. Build succeeds.

[Mark 1b complete, 1c in_progress]

[Use requesting-code-review skill for phase 1]
→ Zero issues.

[Mark 1c complete, 1d in_progress]

[Refactor phase 1: minor naming improvements, committed]

[Mark 1d complete]

--- Phase 2 ---

[Mark 2a in_progress, read phase_02.md]
→ Contains 3 tasks: types, service, tests

[Mark 2a complete, 2b in_progress]

[Execute all 3 tasks...]

[Mark 2b complete, 2c in_progress]

[Use requesting-code-review skill for phase 2]
→ Important: 1, Minor: 1
→ Dispatch bug-fixer, re-review
→ Zero issues.

[Mark 2c complete, 2d in_progress]

[Refactor phase 2: extracted shared validator, committed]

[Mark 2d complete]

--- Phase 3 ---

[Similar pattern...]

--- Finalize ---

[Invoke project-claude-librarian subagent]
→ Updated CLAUDE.md.

[Use requesting-code-review skill for final review]
→ All requirements met.

[Transitioning to finishing-a-development-branch]
```

## Integration

**Required workflow skills:**
- **denubis-plan-and-execute:using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **denubis-plan-and-execute:writing-implementation-plans** - Creates the plan this skill executes
- **denubis-plan-and-execute:finishing-a-development-branch** - Complete development after all tasks

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "I'll read all phases upfront to understand the full picture" | No. Read one phase at a time. Context limits are real. |
| "I'll skip the read step, I remember what's in the file" | No. Always read just-in-time. Context may have been compacted. |
| "I'll review after each task to catch issues early" | No. Review once per phase. Task-level review wastes context. |
| "Context error on review, I'll skip the review" | No. Chunk the review into halves. Never skip review. |
| "Minor issues can wait" | No. Fix ALL issues including Minor. |
| "Code is clean enough, skip refactoring" | No. Green means it works; Refactor means it's maintainable. TDD without Refactor accumulates debt. |
| "I'll set up the worktree later" | No. Never execute on main/master. Worktree first, always. |
