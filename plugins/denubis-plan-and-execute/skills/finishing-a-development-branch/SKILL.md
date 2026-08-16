---
name: finishing-a-development-branch
description: Use when accepted and normalized branch work is ready for a human-selected integration route
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

## Route only the selected integration

If the human already requested a pull request or local merge, invoke the owner with the
exact repository, branch, base, accepted tree, and verification evidence:

- `denubis-plan-and-execute:make-pr` for a pushed branch and one pull request;
- `denubis-plan-and-execute:merge-to-main` for one verified local integration.

If no integration action was specified, ask one pointed question whether to open a pull
request, merge locally, or leave the branch as-is. State a concrete consequence such as
an unpushed branch. Leaving the branch unchanged is the safe default without an answer.

Do not delete a branch or worktree, discard commits, force-push, clean untracked files,
publish, or deploy. Those are separate actions with their own exact targets and authority.
