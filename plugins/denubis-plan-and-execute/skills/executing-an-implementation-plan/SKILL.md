---
name: executing-an-implementation-plan
description: Use when executing an approved implementation plan - builds coherent outcomes, verifies the finished surface, obtains human UAT, then normalizes private history
user-invocable: true
argument-hint: "[absolute-plan-path] [absolute-working-dir]"
---

# Executing an Implementation Plan

## Purpose

Turn an approved plan into verified repository state. The plan owns scope and acceptance
criteria; project instructions own engineering constraints; observed tests, operational
results, and final human interaction own completion claims.

Whether the main session executes directly or delegates follows the global instruction
files; the plan's execution layout says how the work divides between agents. Whoever does
the work, a second fresh worker, never the proposer, verifies it before it reaches the
human (below). Model reports, review verdicts, task labels, and
commits are not correctness evidence. Session naming is
an optional convenience, not an execution prerequisite.

This skill is self-contained for ordinary plan execution. Scale investigation, tracking,
specialist guidance, verification, and communication to the change's actual uncertainty
and consequence. Do not load general coding, testing, language, verification, project
memory, or UAT skills merely because their topic overlaps this workflow. Load another
procedure only when the plan or project explicitly requires it, or when a concrete
unresolved condition makes its additional method necessary.

Use the plan directory's owners directly. `plan.md` or `index.md` holds stable outcomes;
`todo.md` holds only pending, in-progress, or blocked work; `worklog.md` holds completed
work, changed surfaces, and exact evidence. When a task completes, remove it from
`todo.md` and append its result to `worklog.md`. Never retain a checked-off duplicate or
copy the plan narrative into either file. Report decisions, results, and blockers; group
routine operations instead of narrating every transition or command.

## Resolve the boundary

Require the absolute plan path and working directory. The plan may be one file, a current
directory with `index.md` and outcome files, or a legacy directory containing
`phase_##.md` plus shared verification artifacts. Legacy layout changes how the plan is
read, not the lifecycle below.

Before editing:

1. Resolve both paths and confirm the plan belongs to the intended project.
2. Read project instructions, the accepted design, the affected files, and only the tool,
   test, or implementation guidance needed to resolve this change.
3. Inventory the complete outcomes, acceptance criteria, dependencies, consumers,
   verification, boundary changes, and finished-work UAT. For a legacy plan, translate
   phase files into coherent outcomes before executing; do not preserve a chronology-only
   split in the implementation or commit history.
4. Inspect branch, worktrees, status, intended integration branch, concurrent task
   ownership, and affected files. Preserve pre-existing and unrelated changes.
5. Confirm the requested operations fit granted authority.

Choose the workspace before mutation:

- concurrent agents, overlapping files, or unrelated dirty state require a task-owned
  worktree;
- a clean existing branch or worktree already owned by this task is suitable;
- if the only suitable checkout is the default branch, warn the human and wait for
  explicit assent before the first edit there; and
- after that assent, stay on the default branch rather than creating a ceremonial branch.

Create the task worktree through `denubis-plan-and-execute:using-git-worktrees` only when
the rubric selects isolation and no suitable task-owned worktree exists; the agent
worktrees the layout names are created through it unless the plan records why not
(below). Record the intended
integration branch before checkpointing. If the base, ownership, or isolation cannot be
resolved safely, ask one pointed question before mutation.

“Execute this approved plan” authorises, without further prompts, local private checkpoint
commits on the isolated task branch and in the agent worktrees the plan names, the joins
and agent-branch cleanup the plan's layout names, and the commits and squashes on the task
branch that keep it to a few coherent commits (ruled 2026-11-15), unless the human or
project explicitly prohibits them. These come before integration testing, because the
combined tree cannot be tested without merging, nor merged without committing.
It does not authorise the final merge into the intended integration branch, which waits
for the human's authorisation at that point (below), pushing, publishing, deploying,
deleting the task branch, mutating unrelated external state, or rewriting inherited or
published history. Never checkpoint directly on the protected base branch.

If a path, criterion, prerequisite, or authority source does not resolve, repair settled
implementation detail. Stop only when the missing fact changes design, scope, authority,
or external state.

## Execute coherent outcomes

Read enough of the whole plan to understand dependencies and final implications. Each
implementer loads only its own outcome's implementation detail. Track durable state only
when it materially improves recovery. Track outcomes and blockers, not chat turns.

Follow the plan's execution layout:

- Start together the work the layout lets run at the same time. Create each concurrent
  implementer's worktree and branch from the task branch's current tip through
  `denubis-plan-and-execute:using-git-worktrees`, not with a runtime's own agent
  worktrees unless the plan records why, and give the implementer its outcome, its
  worktree path, the files it owns, and the checks it runs. The new worktree runs the
  setup's install steps and only the narrowest check that shows its environment works; it
  relies on the task branch's recorded baseline for that same tree rather than rerunning
  the expensive suite.
- Send each finished piece to its named checker before it joins. Return the checker's
  demonstrated findings to the implementer.
- Join verified branches into the task branch one at a time in the layout's order, without
  asking. Before a branch joins, squash its checkpoints into the few coherent commits of
  the outcome it serves, so the join keeps those commits and `git branch -d` still finds
  the branch merged. After each join, run the combined checks the layout names, and tell
  implementers still working what has landed. Return a conflict to the implementer whose
  branch conflicts.
- Once a join's combined checks pass, carry out its cleanup step: confirm the worktree is
  clean and its branch has no commit the task branch lacks, remove the worktree from
  outside it, delete the branch with `git branch -d`, and confirm with `git worktree list`
  and `git branch --list`. Record the removal in `worklog.md`.

A plan without a layout runs as one implementer in the task checkout.

For each outcome:

1. Resolve every named file, symbol, consumer, dependency, command, and source pointer.
2. Compare the plan with current code and any nearby example needed to resolve an actual
   convention choice. Do not manufacture an example quota when the owner and pattern are
   already unambiguous. Correct stale implementation detail without silently changing
   accepted behavior.
3. For a feature, bug fix, or behavioral refactor, state the behavior, write or identify
   the smallest test that should fail, and observe it fail for the intended reason. A
   malformed command, missing fixture, empty search, or phrase detector is not useful red
   evidence.
4. Implement the smallest complete behavior with its first real consumer, failure path,
   tests, and user or operator documentation.
5. Run the focused check and confirm its positive signal. Clean up only inside covered
   behavior, then rerun it.
6. For infrastructure, generated metadata, or documentation without a useful unit-test
   red state, use an operational probe through the real consumer. It must distinguish a
   working result from a command that exercised nothing.
7. Inspect the owned diff for scope, unresolved placeholders, stale documentation, and
   new interfaces without consumers.

Do not broaden a bug fix into a refactor or refactor uncovered code. Do not add speculative
compatibility layers or narrate superseded behavior in living documentation.

Create a private checkpoint whenever it materially protects recoverable work or makes an
outcome inspectable. Stage only files owned by this execution. Checkpoints may be frequent
and do not require routine human prompts. Fix rounds, review responses, and superseded
checkpoints remain provisional; they fold into the outcome they serve on the task branch
without a human prompt (see “Normalize the task branch”). Do not publish
an internal checkpoint ref or present its commit list as the delivered result.

After each completed task or outcome, update the durable owners: remove completed work
from `todo.md`, append the completed state and fresh evidence to `worklog.md`, and leave
only unresolved work and blockers in the todo.

## Fail deliberately

Read the full failure and relevant source. State one causal hypothesis and its falsifier,
make one targeted change, and compare the result with the prediction. After three failed
fixes for the same condition, restore changes owned by this execution to the last verified
state using a recoverable method, record the commands and observations, and ask before a
new approach. Stop sooner if the recovery path or unrelated data is threatened.

## Verify the complete implementation

Do not present UAT after an intermediate outcome. Once all outcomes are assembled:

1. Run every focused and cross-outcome check in the plan, followed by the project's
   ordinary whole-repository gates appropriate to the change.
2. Confirm each command exercised its intended target and produced the named positive
   signal. If a decisive check succeeds only by returning nothing, establish its scope
   and detection path with a positive control. For a routine secondary hygiene check,
   state the bounded observation instead of manufacturing a disposable defect solely to
   re-prove a mature tool's semantics.
3. Recompute acceptance-criterion coverage from the accepted design to current behavior.
4. Account for changed code, schema, configuration, generated surfaces, tests, and runtime
   effects. Perform a full implementation-first boundary comparison only when the design
   predicts meaningful changes in participants, meaning, consumers, effects, persistence,
   ordering, control, or failure behavior. Do not create architecture ceremony for a
   local behavior whose owner and consumers are already explicit. Update living
   architecture or an accepted ADR only when those artifacts genuinely own the result.
5. Inspect the complete diff, status, and private log. Separate pre-existing changes and
   identify untracked or generated files. Confirm documentation describes current truth.
   Confirm with `git worktree list` that no worktree the plan created remains besides
   the task's own.
6. Send the finished work to a second fresh worker, never the proposer, to verify it.
   Give it a full checklist that names what to check and never an expected defect or
   outcome: the accepted requirements and acceptance criteria, the gates above, the
   sources, and the finished public surface, relevant failure path, adjacent behavior,
   and documentation, exercised as a consumer would. Act on what it reports only when it
   shows a flaw that exists now. This is agent verification, not human UAT.

Use code or design review when risk or a specific uncertainty makes an independent
reading informative. Give it a falsifiable claim and bounded surface, never an expected
defect. Verify every finding against current artifacts; never treat a green model verdict
as evidence.

Any failure returns to the owning outcome. Rerun the affected focused checks and every
complete-surface check whose evidence the fix could invalidate, then have a fresh worker
verify the changed result before UAT.

## Human UAT on the finished implication

Only after all implementation, mechanical checks, diff/status inspection, documentation
reconciliation, and the fresh worker's verification pass, present the irreducible human
judgment. Name the finished surface, one concrete interaction, the implication being
judged, and what experience would falsify acceptance. The human touches the finished
public surface and its implications; they do not merely read a report or repeat a
unit-test assertion.

If UAT fails, record the exact observation, return to implementation, and repeat relevant
mechanical checks and the fresh worker's verification before presenting UAT again. Silence, model agreement, or a
commit is not acceptance.

Keep the isolated task branch unmerged through UAT. The human is judging the finished
implication, not accepting an integration target or a checkpoint series.

## Normalize the task branch

Keep the task branch to a few coherent commits without asking the human (ruled
2026-11-15): squash agents' checkpoints as their branches join (above), before the
combined checks, and after accepted UAT fold any fix rounds it caused. Before rewriting,
record the current tree identifier and private series. Fold superseded checkpoints, fix
rounds, and review-response commits into the coherent outcome they serve. Keep a
checkpoint only if it matured into an independently understandable and reversible
outcome. There is no commit-count target.

Do not rewrite inherited or published history. If the branch was published, stop and ask
for the appropriate integration strategy instead of force-rewriting it.

After normalization:

1. Confirm the rewritten series produces exactly the tree it started from; after UAT, the
   accepted tree.
2. Reinspect each outcome diff and the aggregate diff from the intended base.
3. Rerun the checks needed to establish that the rewritten checkout still matches the
   verified behavior; after UAT, the accepted behavior.
4. Confirm status contains no unexplained owned changes.

Only then invoke `denubis-plan-and-execute:finishing-a-development-branch`. The final merge
into the intended integration branch is never automatic and the plan's approval does not
grant it: it happens only when the human authorises it at that point, after discussing the
finished work, and that authorisation also permits the merge's commit. Unless the human
types one of the direct-delivery routes below, the human starts it by running
`/denubis-plan-and-execute:merge-to-main`; hand the human that command and do not run the
merge yourself (ruled 2026-11-15). The task worktree and branch are removed
only as the human names then. Ask one pointed question when no
route was given. For skill or plugin development, `commit, marketplace, push`, `release`,
and `ship` are direct-delivery routes:
finish release metadata, integrate into the intended default branch, push and verify that
branch, then clean the task-owned branch or worktree. They never mean “push whichever
branch is currently checked out.” Report
implemented outcomes, changed scope, exact evidence, accepted UAT, normalized history,
and any blocker. Do not publish or deploy unless separately authorised.

If context becomes genuinely depleted, update `todo.md` with unresolved work and
`worklog.md` with completed work, last positive evidence, provisional commits, and UAT
state. Return only a pointer-style resume instruction naming the absolute working root,
plan, todo, and worklog paths plus this skill invocation. Do not restate their contents in
the resume text. On resume, re-resolve paths, status, worktrees, and evidence.
