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

## Turn Budgets

**The `max_turns` values in the invocation templates below are calibrated minimums. Use them exactly as written. Do NOT reduce them.**

| Agent | max_turns | Used for |
|-------|-----------|----------|
| task-implementor | 150 | Implementing tasks/subcomponents |
| task-bug-fixer | 150 | Fixing review issues |
| code-reviewer | 150 | Phase code review (via requesting-code-review skill) |
| proleptic-challenger | 150 | Phase transition challenge |
| smell-assessor | 150 | Post-phase smell assessment |
| critical-peer-review | 150 | Smell report review (scoped: evidence grading only) |
| refactoring-executor | 150 | Post-phase refactoring execution |
| project-claude-librarian | 150 | Updating project context |
| test-analyst | 150 | Test coverage analysis |

**Why this matters:** Agents that exhaust their turn budget return empty responses, wasting the entire run. These values are set high as circuit breakers for genuinely runaway agents, not as routine constraints on normal work. Do not "optimise" by lowering them.

## Null / Empty Subagent Response (Turn Exhaustion)

**A null or empty response from any subagent (task-implementor, bug-fixer, smell-assessor, etc.) means it ran out of turns.**

This is NOT a transient error and retrying with the same budget will produce the same result.

**Recovery — check for checkpointed state before halting:**

1. **For code-producing agents** (task-implementor, task-bug-fixer, refactoring-executor):
   - Run `rtk git log -1 --oneline` to check for a WIP commit
   - Run `rtk git diff --stat HEAD~1..HEAD` to see what work was preserved
   - If a WIP commit exists, the agent made partial progress — report what was saved

2. **For analysis agents** (code-reviewer, test-analyst, smell-assessor, critical-peer-review):
   - Check for `review-wip.md`, `test-analysis-wip.md`, or `smell-report-wip.md` in the scratchpad directory
   - For critical-peer-review: check for `reviewed-smell-report.md` — if present, review completed (executor can proceed); if absent, review exhausted with no output
   - If a checkpoint file exists, read it and report the partial findings

3. **Report to the human** with recovery information:
   ```
   "[Agent name] exhausted its turn budget (150 turns).
   Checkpoint state: [WIP commit found with N files changed / checkpoint file found with partial findings / no checkpoint found]
   [Summary of what was preserved]
   How should we proceed?"
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

### 0. Create Session-Isolated Scratchpad

```bash
# Extract slug from plan directory name (last path component)
SLUG=$(basename "[plan-directory]")
# Generate unique session ID
SESSION_ID=$(printf '%04x%04x' $RANDOM $RANDOM)
# Create scratchpad path
SCRATCHPAD_DIR="/tmp/exec-${SLUG}-${SESSION_ID}"
mkdir -p "${SCRATCHPAD_DIR}"
echo "${SCRATCHPAD_DIR}"
```

Pass `SCRATCHPAD_DIR` to all code review invocations. This prevents file collisions when multiple planning or execution sessions run in parallel.

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

**Session naming:** After discovering phases, invoke `denubis-plan-and-execute:session-naming` to generate a domain-specific session name from the implementation plan context.

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
<parameter name="max_turns">150</parameter>
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
<parameter name="max_turns">150</parameter>
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
<parameter name="max_turns">150</parameter>
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
<parameter name="max_turns">150</parameter>
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

**Rules:** No features, no behaviour changes. If tests break, revert.

##### 3d.1: Measurement (orchestrator runs directly)

Before dispatching any agent, run three measurement commands on the phase's files and write results to SCRATCHPAD_DIR:

```bash
# Collect phase files (files touched by this phase's implementation)
PHASE_FILES="[list of files from phase task, space-separated]"

# 1. Line counts
wc -l ${PHASE_FILES} > "${SCRATCHPAD_DIR}/line-counts.txt"

# 2. Cognitive complexity
uvx complexipy ${PHASE_FILES} --max-complexity-allowed 15 > "${SCRATCHPAD_DIR}/complexipy-output.txt" 2>&1 || true

# 3. Structural smell detection (ast-grep rules from refactoring-rubric)
# Write one JSON file per rule to avoid concatenated/malformed JSON
RULES_DIR="$(git rev-parse --show-toplevel)/plugins/denubis-plan-and-execute/skills/refactoring-rubric/rules"
for rule in "${RULES_DIR}"/*.yaml; do
  rulename=$(basename "$rule" .yaml)
  ast-grep scan --rule "$rule" ${PHASE_FILES} --json > "${SCRATCHPAD_DIR}/structural-smells-${rulename}.json" 2>&1 || true
done
```

Note: `|| true` on complexipy and ast-grep ensures the pipeline continues even if tools are unavailable. The smell-assessor handles missing data gracefully.

##### 3d.2: Dispatch smell-assessor

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:smell-assessor</parameter>
<parameter name="description">Phase [N] smell assessment</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
Assess code quality for phase [N] files.

PHASE_FILES: [absolute paths to all phase files, one per line]
MEASUREMENT_DATA_PATH: ${SCRATCHPAD_DIR}
  - ${SCRATCHPAD_DIR}/line-counts.txt
  - ${SCRATCHPAD_DIR}/complexipy-output.txt
  - ${SCRATCHPAD_DIR}/structural-smells-*.json (one file per ast-grep rule)
SCRATCHPAD_DIR: ${SCRATCHPAD_DIR}
DESIGN_PLAN_PATH: [absolute path to design plan]
PHASE_REFERENCE: Phase [N]: [Phase Name]
</parameter>
</invoke>
```

**Print the full smell-assessor response** (transparency rules).

##### 3d.3: Gate check — no findings

After smell-assessor completes, check the response:

- Read `${SCRATCHPAD_DIR}/smell-report.md`
- If the Findings section is empty (only "No Action Needed" entries): announce "No smells detected in phase [N] files. Skipping refactoring." and proceed to 3d.7 (final verification).
- If findings exist: proceed to critical review.

**If smell-assessor returns null/empty:** Check for `${SCRATCHPAD_DIR}/smell-report-wip.md`. If found, read partial findings and report to human. If not found, report turn exhaustion with no checkpoint. Ask human how to proceed.

##### 3d.4: Dispatch critical-peer-review (scoped)

The critical-peer-review agent is dispatched with a scoped briefing. Only evidence grading and overclaiming detection apply. Suppress ACH matrix, pre-mortem, and timeline verification as inapplicable to smell reports.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:critical-peer-review</parameter>
<parameter name="description">Review smell assessment for Phase [N]</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
Review the smell assessment report for overclaiming and evidence-grade violations.

DOCUMENT: ${SCRATCHPAD_DIR}/smell-report.md
CONTEXT: Phase [N] code files and design plan.
  Phase code: [absolute paths to phase files, one per line]
  Design plan: [absolute path to design plan]

SCOPED REVIEW — apply ONLY these checks:
1. Evidence grading: Does each finding's grade match the evidence provided?
   - "Demonstrated" must cite specific tool output (metric value, ast-grep match)
   - "Plausible" must have reasonable LLM reasoning, not just assertion
   - "Possible" is acceptable only with explicit uncertainty acknowledgment
2. Overclaiming: Are any findings overstated relative to their evidence?
3. Speculative Generality: For any finding claiming Speculative Generality, check the design plan — if the design calls for the abstraction, REJECT the finding
4. Rule of Three: For Duplicate Code findings, verify 3+ instances cited

DO NOT apply: ACH matrix, pre-mortem analysis, timeline verification, or other checks designed for debugging/postmortem artifacts.

OUTPUT: Write reviewed-smell-report.md to ${SCRATCHPAD_DIR} with:
- For each finding: verdict (proceed / downgrade / reject) with one-line justification
- Summary: counts of proceed/downgrade/reject
</parameter>
</invoke>
```

**Print the full critical-peer-review response** (transparency rules).

##### 3d.5: Gate check — all findings rejected

After critical review completes, check the response:

- Read `${SCRATCHPAD_DIR}/reviewed-smell-report.md`
- Count findings with "proceed" verdict
- If zero proceed verdicts: announce "Critical review rejected all [N] findings. Reasons: [summary of rejection reasons]. No refactoring will be performed. Review the rejected findings above if you disagree." Proceed to 3d.7 (final verification).
- If any proceed verdicts: proceed to refactoring executor.

**If critical-peer-review returns null/empty:** Report turn exhaustion. The smell report still exists — ask human whether to skip refactoring or dispatch executor with unreviewed findings (not recommended).

##### 3d.6: Dispatch refactoring-executor

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:refactoring-executor</parameter>
<parameter name="description">Phase [N] refactoring execution</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
Apply reviewed refactoring prescriptions to phase [N] files.

REVIEWED_REPORT_PATH: ${SCRATCHPAD_DIR}/reviewed-smell-report.md
PHASE_FILES: [absolute paths to phase files, one per line]
WORKING_DIRECTORY: [absolute path to working directory]
PHASE_REFERENCE: Phase [N]: [Phase Name]

Apply only findings with "proceed" verdict. One transformation at a time.
Tests green after each. Revert on red — do not fix tests.
Commit refactoring separately from implementation.
</parameter>
</invoke>
```

**Print the full refactoring-executor response** (transparency rules).

**If refactoring-executor returns null/empty:** Check for WIP commit (`rtk git log -1 --oneline`). If WIP commit exists, partial refactoring was applied. Report to human with what was saved.

##### 3d.7: After refactoring (final verification)

Run tests as final safety net:
- If green: mark phase complete
- If tests fail: revert refactoring commit and proceed without. Announce: "Refactoring broke tests despite per-transformation verification. Reverted refactoring commit. Proceeding with implementation as-is."

**Phase completion flow:**
```
Code review → Proleptic → UAT → Measure → Assess → [Gate] → Review → [Gate] → Refactor → Verify green → Next phase
```

#### 3e. Context Management Between Phases

**Before loading the next phase, assess context pressure.** Phase execution accumulates subagent responses, review output, and fix cycles. This is the optimal moment to reclaim context — the work is committed, reviewed, and UAT-confirmed.

**Decision logic:**

| Condition | Action |
|-----------|--------|
| No complex cross-phase state accumulated (no mid-plan decisions, workarounds, or unresolved concerns) | Suggest `/clear` — task list has remaining phases with absolute paths, git has the work, SessionStart hook re-injects skill context |
| Cross-phase decisions, constraints, or workarounds were discovered that aren't captured in task descriptions or commits | Suggest `/compact` with preservation instructions |
| First phase just completed (minimal context used) | Skip — not worth the interruption yet |

**When suggesting `/clear`:**

Construct a resume prompt the user can paste after `/clear`. It must be self-contained — after `/clear`, the model has zero prior context.

```
Phase N complete and committed. Context is heavy from subagent output and review cycles.

All remaining work is tracked in the task list with absolute paths. The git history has everything.

Suggest: /clear then paste this to resume:

---
/executing-an-implementation-plan

Plan directory: [absolute path to implementation plan directory]
Completed phases: 1 through N
Next phase: N+1 of M
Working directory: [absolute worktree path]
Implementation guidance: [absolute path, or "none"]
Test requirements: [absolute path, or "none"]

The task list has remaining phases with absolute paths. Check it with TaskList.
---

This gives a fresh context window. The SessionStart hook will re-inject skill context,
and the task list persists across /clear.
```

**When suggesting `/compact`:**

```
Phase N complete. Context is heavy but there's cross-phase state worth preserving:
- [list what needs preserving: decisions, constraints, workarounds]

Suggest: /compact Preserve: (1) implementation plan path: [path], (2) current phase: N of M,
(3) [specific decisions/constraints to preserve], (4) task list has remaining phases.
Discard: all subagent output, review details, and fix cycle content — work is committed.
```

**Wait for the user to act.** Do not proceed to the next phase until the user either runs the suggested command or explicitly says to continue without it.

#### 3f. Move to Next Phase

Proceed to the next phase's "Read" step. Repeat 3a-3e for each phase.

### 4. Update Project Context

After all phases complete, invoke the `denubis-extending-claude:project-claude-librarian` subagent (when available) to review changes and update CLAUDE.md files if needed.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-extending-claude:project-claude-librarian</parameter>
<parameter name="description">Updating project context after implementation</parameter>
<parameter name="max_turns">150</parameter>
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
<parameter name="max_turns">150</parameter>
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
   <parameter name="max_turns">150</parameter>
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
# e.g., impl plan dir: docs/implementation-plans/2025-01-24-oauth-99/
#       test plan:     docs/test-plans/2025-01-24-oauth-99.md
```

Write the test plan content to `docs/test-plans/[impl-plan-dir-name].md`, then commit:

```bash
git add docs/test-plans/[impl-plan-dir-name].md
git commit -m "docs: add test plan for [feature name]"
```

Announce: "Human test plan written to `docs/test-plans/[impl-plan-dir-name].md`"

**Critical peer review:** After all phases are implemented and reviewed, invoke `denubis-plan-and-execute:critical-peer-review` to subject the completed implementation to falsification-first analysis before declaring completion.

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

--- Context management ---

[Phase 1 complete, context heavy from subagent output]
[No cross-phase state — suggest /clear]
[User runs /clear, resumes with "Continue executing the implementation plan"]

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
