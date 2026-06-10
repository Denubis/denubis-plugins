---
name: requesting-code-review
family: executing-an-implementation-plan,finishing-a-development-branch,make-pr,merge-to-main
description: Use after each implementation phase and before merging - dispatches the code-reviewer subagent, writes a findings file, runs at most one fix-then-re-review cycle
user-invocable: false
---

# Requesting Code Review

Dispatch denubis-plan-and-execute:code-reviewer subagent to catch issues before they cascade.

**Core principle:** Review early, review often. Fix ALL issues before proceeding.

## When to Request Review

**Two mandatory triggers with different scopes:**

| Trigger | Scope | BASE_SHA | Called by |
|---------|-------|----------|----------|
| **Per-phase** | Changes within one implementation phase | Commit before phase started | executing-an-implementation-plan (after each phase) |
| **Pre-merge** | All changes since branch diverged from main | `git merge-base HEAD main` | finishing-a-development-branch (before presenting options) |

Per-phase reviews catch phase-level issues. Pre-merge reviews catch cross-phase issues, integration problems, and drift that accumulates across phases. Both are mandatory -- neither replaces the other.

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## The Review Loop (Bounded — One Fix Cycle, Then HALT)

The review process is **at most one fix-then-re-review cycle**, then HALT for human direction.

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   Dispatch code-reviewer                         │
│   (writes code-review-findings-{SCOPE}.md        │
│    to the plan directory)                        │
│         │                                        │
│         ▼                                        │
│   Issues found? ──No──► Proceed                  │
│         │                                        │
│        Yes                                       │
│         │                                        │
│         ▼                                        │
│   Dispatch bug-fixer                             │
│         │                                        │
│         ▼                                        │
│   Re-review (verifies against findings file)    │
│         │                                        │
│         ▼                                        │
│   All resolved & no new issues? ──Yes──► Proceed │
│         │                                        │
│        No                                        │
│         │                                        │
│         ▼                                        │
│   HALT — present result to user, ask direction   │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Exit conditions (only these — never auto-dispatch a third review):**
- Zero issues on initial review → proceed.
- Zero issues on first re-review (all prior findings resolved, no new issues) → proceed.
- Any unresolved or new issues after the first re-review → **HALT** and ask the user.

**Why bounded:** Multi-cycle review loops compound agent ceremony for diminishing returns. The findings file makes review state inspectable, so the user can decide whether further cycles are warranted, accept remaining issues, or change approach.

## Step 1: Initial Review

**Get git SHAs (scope determines BASE_SHA):**
```bash
# Per-phase scope: commit before phase started
BASE_SHA=<commit before phase started>

# Pre-merge scope: branch divergence point
BASE_SHA=$(git merge-base HEAD main)

HEAD_SHA=$(git rev-parse HEAD)
```

**Dispatch code-reviewer subagent:**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:code-reviewer</parameter>
<parameter name="description">Reviewing [what was implemented]</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: [summary of implementation]
  PLAN_OR_REQUIREMENTS: [task/requirements reference]
  BASE_SHA: [commit before work]
  HEAD_SHA: [current commit]
  DESCRIPTION: [brief summary]
  SCOPE: [phase-N, pre-merge, task-N — used to name code-review-findings-{SCOPE}.md so per-phase findings don't clobber each other]
  SCRATCHPAD_DIR: [path from caller, if provided]
</parameter>
</invoke>
```

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment.

**Side effect:** The reviewer writes its full findings to `code-review-findings-{SCOPE}.md` in the plan/design-doc directory (e.g. `code-review-findings-phase-2.md`). This file is the persistent record for that scope — re-review consults it instead of re-deriving issues from scratch, and per-phase files coexist rather than clobbering each other.

## Step 1b: Parallel DBA Review (Conditional)

**If the changes include database schema work** (model definitions, migrations, seed data, foreign key changes), dispatch the DBA reviewer **in parallel with the code reviewer** in Step 1.

**Detection heuristic:** Check if any of these are in the changeset:
- Files matching `models.py`, `**/models/*.py`, `schema.py`
- Migration files (`alembic/versions/`, `migrations/`)
- Files containing `SQLModel`, `Base`, `mapped_column`, `ForeignKey`, `PrimaryKeyConstraint`
- Seed data or reference table definitions

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:dba-reviewer</parameter>
<parameter name="description">DBA review: [what schema changes were made]</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
Review the database schema changes in this implementation.

WHAT_CHANGED: [summary of schema changes — new tables, modified columns, new relationships]
FILES_TO_REVIEW: [list model/migration files]
WORKING_DIRECTORY: [directory]

Read each file and review for:
1. Normalisation (1NF through BCNF)
2. Key selection (natural vs surrogate, appropriate for data type)
3. Constraint completeness (NOT NULL, UNIQUE, CHECK, FK)
4. Relationship correctness
5. PostgreSQL anti-patterns

HALT and ask the human if anything is uncertain.
</parameter>
</invoke>
```

**Dispatch both reviewers in parallel** (single message with two Task calls) to minimise wall-clock time.

**Handling DBA review results:**

| DBA Result | Action |
|-----------|--------|
| APPROVED | Proceed (combine with code review result) |
| CHANGES REQUIRED | Treat same as code review issues — dispatch bug-fixer, re-review |
| HALTED — DECISION NEEDED | **STOP everything.** Present the halt to the human. Do not proceed with code review fixes until the DBA halt is resolved. |

**DBA HALTs take priority over code review issues.** Schema design decisions must be resolved before fixing code-level issues, because schema changes may invalidate code fixes.

**If no database changes detected:** Skip this step entirely. Do not dispatch the DBA reviewer for non-database work.

## Step 2: Handle Reviewer Response

### If Zero Issues

All categories empty → proceed to proleptic challenge.

**REQUIRED:** Invoke proleptic challenge before proceeding.

Before proceeding to UAT or next task:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:proleptic-challenger</parameter>
<parameter name="description">Proleptic challenge: code review passed</parameter>
<parameter name="max_turns">150</parameter>
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

**After human evaluates counterarguments:** Proceed to exec-uat-gate skill for acceptance verification.

### If Any Issues Found
Regardless of category (Critical, Important, or Minor), dispatch bug-fixer:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:task-bug-fixer</parameter>
<parameter name="description">Fixing review issues</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
  Fix issues from code review.

  Code reviewer found these issues:
  [list all issues - Critical, Important, and Minor]

  Your job is to:
  1. Understand root cause of each issue
  2. Apply fixes systematically (Critical → Important → Minor)
  3. Verify with tests/build/lint
  4. Commit your fixes
  5. Report back with evidence

  Work from: [directory]

  Fix ALL issues — including every Minor issue. The goal is ZERO issues on re-review.
  Minor issues are not optional. Do not skip them.

  IMPORTANT: Fix issues with targeted, minimal edits. Do NOT
  wholesale-regenerate files to address review comments — this makes
  iterative review impossible. Each fix should be traceable to the
  specific issue it addresses. If a fix requires restructuring a file,
  explain why in your commit message.
</parameter>
</invoke>
```

After fixes, proceed to Step 3.

## Step 3: Re-Review After Fixes (One Cycle Only)

**This is the only re-review the skill performs automatically. After this, HALT.**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:code-reviewer</parameter>
<parameter name="description">Re-reviewing after fixes</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: [from bug-fixer's report]
  PLAN_OR_REQUIREMENTS: [original task/requirements]
  BASE_SHA: [commit before this fix cycle]
  HEAD_SHA: [current commit after fixes]
  DESCRIPTION: Re-review after bug fixes
  SCOPE: [same SCOPE used in initial review — e.g. phase-2]
  PRIOR_FINDINGS_FILE: [absolute path to code-review-findings-{SCOPE}.md from the initial review]

  This is a re-review. Read the prior findings file first, then for each prior issue
  report Resolved / Partially resolved / Unresolved with evidence. Then surface any
  new issues in the changed code. Overwrite code-review-findings-{SCOPE}.md with the
  new structured review.
</parameter>
</invoke>
```

### Step 3a: HALT — Decide With the User

**Do NOT auto-loop back to Step 2.** Read the updated `code-review-findings-{SCOPE}.md` and present its summary to the user.

| Re-review outcome | Action |
|-------------------|--------|
| All prior issues resolved, no new issues | Proceed to proleptic challenge (zero-issues path) |
| Anything else (unresolved, partial, or new issues) | **HALT and ask the user**, offering the options below |

**Options to present to the user when halting:**

1. **Fix now** — dispatch bug-fixer for another cycle (user-authorised — the skill itself never auto-dispatches a second fix cycle).
2. **Defer to a future phase** — the issues are real but belong to a later phase. Ask the user *which* implementation plan file should record them. With user approval, append the deferred issues to that plan file (under a clearly labelled "Deferred from {SCOPE} review" section, with file:line references and the reviewer's suggested fix). Once the plan is updated, **the current code review is considered complete** and you proceed to proleptic challenge.
3. **Accept the remaining issues** — user explicitly accepts them as out-of-scope or false positives; document the acceptance and proceed.
4. **Halt for discussion** — substantial revision needed; stop the workflow and reopen at the next session.

The findings file remains on disk regardless of which option is chosen, so the audit trail survives.

## Handling Failures

### Operational Errors
If reviewer reports operational errors (can't run tests, missing scripts):
1. **STOP** - do not continue
2. Report to human
3. When told to continue, re-execute same review

### Turn Budgets

**The `max_turns` values in the invocation templates above are calibrated minimums. Use them exactly as written. Do NOT reduce them.**

| Agent | max_turns | Used for |
|-------|-----------|----------|
| code-reviewer (initial) | 150 | Initial diff-focused review |
| code-reviewer (re-review) | 150 | Verifying fixes against prior issues |
| dba-reviewer | 150 | Parallel database review |
| proleptic-challenger | 150 | Post-review challenge |
| task-bug-fixer | 150 | Fixing review issues |

**Why this matters:** Agents that exhaust their turn budget return empty responses, wasting the entire run. These values are set high as circuit breakers for genuinely runaway agents, not as routine constraints on normal work. Do not "optimise" by lowering them.

### Null / Empty Response (Turn Exhaustion)

**A null or empty response from any subagent means it ran out of turns.**

This is NOT a transient error. Do NOT retry with the same budget — the agent will exhaust again.

**Recovery — check for checkpointed state before halting:**

1. **For code-reviewer**: Check for `review-wip.md` in the plan directory — if it exists, read it for partial findings
2. **For task-bug-fixer**: Run `git log -1 --oneline` to check for a WIP commit with partial fixes
3. **For other agents**: Check for `*-wip.md` checkpoint files in the plan directory

**Report to the human** with recovery information:
```
"[Agent name] exhausted its turn budget (150 turns).
Checkpoint state: [checkpoint file found with partial findings / WIP commit found / no checkpoint found]
[Summary of what was preserved]
How should we proceed?"
```

**Do not** silently retry, skip the review, or proceed without the review result.

### Context Limit / Timeout
Usually means the changeset is too large for a single review. Retry with focused scope:

**First retry:** Narrow to changed files only:
```
FOCUSED REVIEW - Context was too large.

Review ONLY the diff between BASE_SHA and HEAD_SHA.
Focus on: [list only files actually modified]

Skip: broad architectural analysis, unchanged files, tangential concerns.

WHAT_WAS_IMPLEMENTED: [summary]
PLAN_OR_REQUIREMENTS: [reference]
BASE_SHA: [sha]
HEAD_SHA: [sha]
```

**Second retry:** Split into multiple smaller reviews (one per file or logical group).

**Third failure:** Stop and ask human for help.

## Quick Reference

| Situation | Action |
|-----------|--------|
| Zero issues | Proceed |
| Any issues | Fix, re-review (or accept per workflow) |
| Operational error | Stop, report, wait |
| Timeout | Retry with focused scope |
| 3 failed retries | Ask human |

## Red Flags

**Never:**
- Skip review because "it's simple"
- Proceed with ANY unfixed issues (Critical, Important, OR Minor)
- Argue with valid technical feedback without evidence
- Rationalize skipping Minor issues ("they're just style", "we can fix later")
- Wholesale-regenerate files to address review comments (makes iterative review impossible — fixes must be targeted edits traceable to specific issues)

**Minor issues are NOT optional.** The code reviewer flagged them for a reason. Fix all of them. "Minor" means lower severity, not "ignorable."

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification on unclear feedback

## Integration

**Called by:**
- executing-an-implementation-plan (per-phase scope, after each phase's tasks complete)
- finishing-a-development-branch (pre-merge scope, full branch diff before presenting options)
- Ad-hoc when you need a review

**Leads to:**
- proleptic-challenge (after zero issues)
- exec-uat-gate (after proleptic challenge addressed)

**Template location:** requesting-code-review/code-reviewer.md
