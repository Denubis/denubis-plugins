---
name: finishing-a-development-branch
description: Use after accepted UAT when normalized branch work must be integrated, published through the selected route, verified, and cleaned without exposing private checkpoint refs
user-invocable: false
---

# Finish a Development Branch

## Establish readiness

Inspect rather than infer:

- current branch, upstream, remote, intended base, and worktree path;
- staged, unstaged, and untracked files, separated from pre-existing work;
- commits and aggregate diff relative to the intended base;
- fresh required test, build, lint, type, and operational evidence;
- explicit human observations for every required finished-work UAT entry;
- the accepted tree identifier before normalization and proof that the normalized private
  series produces that exact tree; and
- any blocker or unresolved design, architecture, or documentation inconsistency.

If UAT, normalization, exact-tree comparison, or affected verification is missing, return
to execution. Do not call a branch complete because a task label, reviewer, commit, or
implementation report says so. If the branch was published, do not rewrite it to satisfy
the private-history lifecycle.

## Resolve the delivery request

Resolve project integration policy and the human's latest request. The checkout is state,
not intent; never select a publication target merely because a non-default branch is
current.

- A requested pull request invokes `denubis-plan-and-execute:make-pr` with the exact head
  and base. The branch remains until the PR lifecycle finishes.
- A requested local merge invokes `denubis-plan-and-execute:merge-to-main` without push or
  cleanup authority unless those actions were also named.
- For skill or plugin development, `commit, marketplace, push`, `release`, or `ship`
  authorises direct delivery when project policy permits it: finish the version and
  marketplace metadata, integrate the accepted tree into the intended default branch,
  push and read back that branch, then clean the task-owned branch or worktree.

If no integration or delivery action was specified, ask one pointed question. Leaving the
branch unchanged is safe while awaiting an answer, but it is not completed delivery.

## Verify delivery and clean task-owned isolation

For direct delivery, pass the explicit push and cleanup authority to
`denubis-plan-and-execute:merge-to-main`. Require a positive remote read-back showing the
intended default ref at the integrated commit before cleanup.

Remove only the task-owned worktree and branch, from a checkout outside the worktree being
removed. First prove the integrated branch contains the accepted tree and the task branch
has no unique commit. If an internal branch was accidentally published, delete that exact
remote ref only when the human's cleanup request includes it. Re-list worktrees and local
and remote refs afterward.

Do not discard commits, force-push, clean unrelated or untracked files, delete another
branch or worktree, publish a checkpoint ref, or deploy. A failed cleanup check blocks
cleanup; it does not weaken the evidence requirement.
