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

The main session executes directly by default. Delegation is optional. Model reports,
review verdicts, task labels, and commits are not correctness evidence. Session naming is
an optional convenience, not an execution prerequisite.

This skill is self-contained for ordinary plan execution. Scale investigation, tracking,
specialist guidance, verification, and communication to the change's actual uncertainty
and consequence. Do not load general coding, testing, language, verification, project
memory, or UAT skills merely because their topic overlaps this workflow. Load another
procedure only when the plan or project explicitly requires it, or when a concrete
unresolved condition makes its additional method necessary.

Use the approved plan as the tracker for a single short outcome. Create or update another
tracker only when it protects recovery across several outcomes, a long interruption, or
genuine context loss. Report decisions, results, and blockers; group routine operations
instead of narrating every transition or command.

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
4. Inspect branch, worktree, status, base, and affected files. Preserve pre-existing and
   unrelated changes.
5. Confirm the requested operations fit granted authority.

Use the current workspace unless isolation was requested, project instructions require
it, or overlapping changes make isolation necessary. If the needed base or isolation
cannot be resolved safely, ask one pointed question before mutation.

“Execute this approved plan” authorises local private checkpoint commits on the feature
branch for work owned by the plan, unless the human or project explicitly prohibits them.
It does not authorise pushing, publishing, deploying, mutating unrelated external state,
or rewriting inherited or published history. Never checkpoint directly on the protected
base branch.

If a path, criterion, prerequisite, or authority source does not resolve, repair settled
implementation detail. Stop only when the missing fact changes design, scope, authority,
or external state.

## Execute coherent outcomes

Read enough of the whole plan to understand dependencies and final implications, then
load one outcome's implementation detail at a time. Track durable state only when it
materially improves recovery. Track outcomes and blockers, not chat turns.

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
checkpoints remain provisional; they will fold into the outcome after UAT.

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
5. Perform an independent sanity review targeted at plausible mistakes: exercise the
   finished public surface, relevant failure path, adjacent behavior, and documentation
   as a consumer would. This is agent verification, not human UAT.
6. Inspect the complete diff, status, and private log. Separate pre-existing changes and
   identify untracked or generated files. Confirm documentation describes current truth.

Use code or design review when risk or a specific uncertainty makes an independent
reading informative. Give it a falsifiable claim and bounded surface. Verify every
finding against current artifacts; never treat a green model verdict as evidence.

Any failure returns to the owning outcome. Rerun the affected focused checks and every
complete-surface check whose evidence the fix could invalidate.

## Human UAT on the finished implication

Only after all implementation, mechanical checks, independent sanity checks, diff/status
inspection, and documentation reconciliation pass, present the irreducible human
judgment. Name the finished surface, one concrete interaction, the implication being
judged, and what experience would falsify acceptance. The human touches the finished
public surface and its implications; they do not merely read a report or repeat a
unit-test assertion.

If UAT fails, record the exact observation, return to implementation, and repeat relevant
mechanical and sanity checks before presenting UAT again. Silence, model agreement, or a
commit is not acceptance.

## Normalize after accepted UAT

Final history normalization happens only after explicit human acceptance of all required
finished-work UAT. Before rewriting, record the accepted tree identifier and current
private series. Fold superseded checkpoints, fix rounds, and review-response commits into
the coherent outcome they serve. Keep a checkpoint only if it matured into an
independently understandable and reversible outcome. There is no commit-count target.

Do not rewrite inherited or published history. If the branch was published, stop and ask
for the appropriate integration strategy instead of force-rewriting it.

After normalization:

1. Confirm the rewritten series produces exactly the accepted tree.
2. Reinspect each outcome diff and the aggregate diff from the intended base.
3. Rerun the checks needed to establish that the rewritten checkout still matches the
   accepted behavior.
4. Confirm status contains no unexplained owned changes.

Only then invoke `denubis-plan-and-execute:finishing-a-development-branch` for the
already-authorised integration route, or ask one pointed integration question. Report
implemented outcomes, changed scope, exact evidence, accepted UAT, normalized history,
and any blocker. Do not publish or deploy unless separately authorised.

If context becomes genuinely depleted, update the existing durable plan or tracker with
the current outcome, owned changes, last positive evidence, provisional commits, UAT
state, and next unresolved condition. On resume, re-resolve paths, status, and evidence.
