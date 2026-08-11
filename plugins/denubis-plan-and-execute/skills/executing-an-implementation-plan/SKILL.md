---
name: executing-an-implementation-plan
description: Use when executing a reviewed implementation plan - performs each phase against its acceptance criteria, verifies observable results, and requests only irreducible human judgment
user-invocable: true
argument-hint: "[absolute-plan-dir] [absolute-working-dir]"
---

# Executing an Implementation Plan

## Purpose

Turn an implementation plan into verified repository state. The plan owns scope and
acceptance criteria; repository instructions own local engineering constraints; observed
test and operational results own completion claims.

The main session executes tasks directly by default. Delegation is optional. Model reports,
review verdicts, task-state labels, and workflow narration do not establish that work is
correct.

At the start, use `denubis-plan-and-execute:exec-session-naming` so concurrent terminal
sessions expose this work's repository and purpose to the human.

## Resolve the execution boundary

Require the absolute plan directory and working directory from the invocation.
Use the absolute working directory from the invocation; do not infer another checkout
from the current shell.

Before editing:

1. Resolve both paths and confirm the plan directory belongs to the intended project.
2. Read the project `AGENTS.md` or `CLAUDE.md`, tool and test configuration, and any
   implementation guidance named by the plan.
3. Inventory `phase_##.md`, `test-requirements.md`, and `uat-requirements.md`. Confirm task
   markers are balanced and every acceptance criterion has an owner.
4. Inspect repository status and the files the current phase will touch. Preserve
   pre-existing changes; do not overwrite, revert, include, or certify them as this work.
5. Confirm the requested operations fit the authority already granted.

Do not create a branch or worktree unless the human requested one, project instructions
require one, or overlapping changes make isolation necessary. If the needed isolation or
base cannot be resolved safely, ask one pointed question before changing state.

Do not commit, push, publish, deploy, or mutate external systems unless the human has
authorised that action. A plan containing such a step does not itself grant authority.

If a path, criterion, prerequisite, or authority source does not resolve, treat it as an
integrity defect. Repair implementation detail when the design already determines the
answer. When the missing fact changes scope, design, external state, or human authority,
stop that branch and ask one pointed question.

## Load work just in time

Read one phase at a time. Read the whole current phase before its first edit, but do not
load later phase bodies merely to narrate what will happen. Look ahead only far enough to
confirm that a new interface has a real consumer and that the current change does not make
the next phase impossible.

Use the existing task tracker or durable checklist required by the workflow entry skill.
Track outcomes, not chat turns. Do not create review receipts, transition certificates, or
extra progress documents whose only consumer is the model.

For the current phase:

1. Resolve every named file, symbol, test, command, dependency, and source pointer.
2. Compare the phase assumptions with current code.
   A review finding is a lead, not verification evidence; open the cited artifact before
   acting on it.
3. Order tasks by dependency while preserving the phase's acceptance ownership.
4. Execute each coherent task, then verify the criterion it owns.
5. Finish the phase verification before loading the next phase.

The main session may inspect, edit, and test directly. Delegation is optional for a bounded
independent investigation or implementation when it genuinely reduces contention or
context pressure. Give a delegate an exact scope and no broader authority. Inspect its
diff and rerun its evidence in the main session; never continue solely because it reported
success. Surface the verified delegated result that changes the work; do not substitute
the delegate's narrative for that result.

## Implement each task

Read the target and two or three relevant local examples before adopting a pattern. Follow
the repository's configured formatter, type checker, and test runner. Do not introduce a
new convention merely because the plan omitted an implementation detail.

For a feature, bug fix, or behavioural refactor:

1. State the observable behaviour and the acceptance criterion it serves.
2. Write or identify the smallest test that fails for the intended reason.
3. Observe the failing check before implementation. A malformed command, missing fixture,
   or empty search is not a useful red state.
4. Make the smallest coherent implementation that passes.
5. Rerun the focused check and inspect its positive signal.
6. Clean up only within the tested behaviour, then rerun the check.

For infrastructure, documentation, generated metadata, or another change without a useful
unit-test red state, use the plan's operational check. It must produce a positive signal
that distinguishes the intended result from a command that never exercised it.

Keep new interfaces with their first real consumer. Do not add speculative abstractions,
unrequested compatibility layers, aliases for retired names, or explanation of superseded
behavior in living documents. Things state what they are now; historical argument belongs
in version history or an explicit archive.

For a behavior-preserving refactor beyond local cleanup, use
`denubis-plan-and-execute:exec-refactoring-rubric` before editing. Establish the concrete
maintenance cost, current consumers, behavioral coverage, and one bounded transformation.
Do not route a required behavior change through a refactoring procedure.

Do not broaden a bug fix into a refactor. Do not refactor untested code. If the current
repository contradicts a task, determine whether the plan's detail is stale or its design
is invalid before editing either.

## Respond to failures

Read the complete failure and relevant source before changing code.
State one causal hypothesis and its falsifier, make one targeted change, and compare the
result with the prediction. A contradicted prediction returns to investigation; it does
not license a second random edit.

After three failed fixes for the same condition, stop. Preserve pre-existing work, restore
the last verified repository state for changes owned by this execution using a recoverable
method, record the commands and observations that failed, and ask the human before another
approach. Difficulty, a long task, or an incomplete phase is not itself a blocker.
Stop sooner if an attempted fix expands the failure surface, threatens data, or invalidates
the recovery path; do not spend the remaining attempts increasing the blast radius.

## Close a phase

Run the focused and phase-level checks assigned in `test-requirements.md`. Confirm each
command exercised the intended target and produced the named positive signal. Reinspect
the diff for scope, accidental changes, stale documentation, unresolved placeholders, and
new interfaces without consumers.

Review is useful when required by the plan or project, when risk is high, or when an
independent reading could falsify a specific claim. It is not a fixed transition ritual.
Run a required or risk-targeted review through
`denubis-plan-and-execute:requesting-code-review` with the bounded claim and surface. If a
specific design-conformance uncertainty remains after ordinary verification, use
`denubis-plan-and-execute:exec-coherence-review` for that question only.
Verify every actionable review finding against code, tests, logs, or current documentation.
A green review verdict cannot replace those checks, and repeated model reviews do not turn
agreement into external evidence.

Human UAT is required only for entries assigned to the phase in `uat-requirements.md`.
Complete all automatable verification first, then present the built surface, the action the
human should perform, the judgment only they can make, and the result that would falsify
acceptance through `denubis-plan-and-execute:exec-uat-gate`. Wait for their observation.
If there are no UAT entries, do not invent a human gate or ask them to rerun deterministic
checks.

Do not mark a phase complete while one of its owned criteria is failing, unobserved, or
blocked. Record the exact unresolved condition in the current phase file or existing
project tracker and leave later dependent work pending.

## Finish the plan

After the final phase:

1. Run the complete verification set from `test-requirements.md` plus the project's
   ordinary whole-repository gates appropriate to the change.
2. Recompute final acceptance-criterion coverage from the design through the phase files
   to current evidence. Missing or duplicate ownership is a defect, not a paperwork gap.
3. Confirm every required UAT entry has the human's actual observation; do not infer
   acceptance from silence or from a model summary.
4. Inspect the final diff and repository status. Separate pre-existing changes from this
   execution and identify anything untracked, generated, or not yet verified.
5. When the plan is verified and no owned criterion remains open, invoke
   `denubis-plan-and-execute:finishing-a-development-branch` to report the branch state and
   route only the integration action already authorised or selected by the human.
6. Check living architecture, ADRs, notes, and runbooks touched by the change for current
   truth and resolvable source pointers. Do not append correction narratives.
7. Re-run any check affected by the final cleanup.

Report the implemented outcomes, changed-file scope, exact verification commands and
results, remaining blockers, and any human UAT still required. Do not claim completion
from a model report, a task label, a commit, or the existence of a generated record.

If context is genuinely depleted before completion, update the existing durable checklist
with the current phase, owned changes, last positive evidence, and next unresolved task.
On resume, re-resolve the absolute working directory, plan, repository status, and last
evidence before continuing. Do not force a context clear when the current session can
finish safely.
