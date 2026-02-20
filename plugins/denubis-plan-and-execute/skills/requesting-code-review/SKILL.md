---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements - dispatches code-reviewer subagent, handles retries and timeouts, manages review-fix loop until zero issues
user-invocable: false
---

# Requesting Code Review

Dispatch denubis-plan-and-execute:code-reviewer subagent to catch issues before they cascade.

**Core principle:** Review early, review often. Fix ALL issues before proceeding.

## Workflow Status Line

**On entry** (review dispatched):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --skill "code-review" --context "reviewing"
```

**Operational error or 3 failures** (need human help):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --context "BLOCKED: 3 failures — need direction"
```

**After review passes** (before proleptic/UAT — those skills set their own state):
```bash
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh --skill "executing-impl" --context ""
```

## When to Request Review

**Mandatory:**
- After each task in plan execution
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## The Review Loop

The review process is a loop: review → fix → re-review → until zero issues.

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   Dispatch code-reviewer                         │
│         │                                        │
│         ▼                                        │
│   Issues found? ──No──► Done (proceed)           │
│         │                                        │
│        Yes                                       │
│         │                                        │
│         ▼                                        │
│   Dispatch bug-fixer                             │
│         │                                        │
│         ▼                                        │
│   Re-review with prior issues ◄──────────────────┘
│
└──────────────────────────────────────────────────┘
```

**Exit condition:** Zero issues, or issues accepted per your workflow's policy.

## Step 1: Initial Review

**Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or commit before task
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
</parameter>
</invoke>
```

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment

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

**After human evaluates counterarguments:** Proceed to human-uat-gate skill for acceptance verification.

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
</parameter>
</invoke>
```

After fixes, proceed to Step 3.

## Step 3: Re-Review After Fixes

**CRITICAL:** Track prior issues across review cycles.

```
<invoke name="Task">
<parameter name="subagent_type">denubis-plan-and-execute:code-reviewer</parameter>
<parameter name="description">Re-reviewing after fixes (cycle N)</parameter>
<parameter name="max_turns">150</parameter>
<parameter name="prompt">
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: [from bug-fixer's report]
  PLAN_OR_REQUIREMENTS: [original task/requirements]
  BASE_SHA: [commit before this fix cycle]
  HEAD_SHA: [current commit after fixes]
  DESCRIPTION: Re-review after bug fixes (review cycle N)

  PRIOR_ISSUES_TO_VERIFY_FIXED:
  [list all outstanding issues from previous reviews]

  Verify:
  1. Each prior issue listed above is actually resolved
  2. No regressions introduced by the fixes
  3. Any new issues in the changed code

  Report which prior issues are now fixed and which (if any) remain.
</parameter>
</invoke>
```

**Tracking prior issues:**
- When re-reviewer explicitly confirms fixed → remove from list
- When re-reviewer doesn't mention an issue → keep on list (silence ≠ fixed)
- When re-reviewer finds new issues → add to list

Loop back to Step 2 if any issues remain.

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
2. **For task-bug-fixer**: Run `rtk git log -1 --oneline` to check for a WIP commit with partial fixes
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

**Minor issues are NOT optional.** The code reviewer flagged them for a reason. Fix all of them. "Minor" means lower severity, not "ignorable."

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification on unclear feedback

## Integration

**Called by:**
- executing-an-implementation-plan (after each task)
- finishing-a-development-branch (final review)
- Ad-hoc when you need a review

**Leads to:**
- proleptic-challenge (after zero issues)
- human-uat-gate (after proleptic challenge addressed)

**Template location:** requesting-code-review/code-reviewer.md
