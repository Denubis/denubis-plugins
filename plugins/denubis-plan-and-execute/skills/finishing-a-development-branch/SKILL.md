---
name: finishing-a-development-branch
description: Use when verified branch work is ready for a human-selected integration route - reports current state and delegates only the requested PR or local-merge action
user-invocable: false
---

# Finish a Development Branch

## Purpose

Route verified branch work to the integration action the human actually wants. This skill
does not add another review gate, discard work, or treat cleanup as part of integration.

## Establish readiness

Inspect branch status and verification evidence:

- current branch, upstream, remote, base, and worktree path;
- staged, unstaged, and untracked files;
- commits and diff relative to the intended base. Treat an upstream `ahead` count only as
  divergence from that configured ref; before calling commits unpushed or at risk, check
  whether the intended base or any remote ref already contains them;
- fresh required test and operational results; and
- unresolved human UAT or documented blockers.

Do not call the branch complete because a task label, reviewer, or implementation report
says so. If required evidence is missing, return to verification. Preserve unrelated and
pre-existing changes.

## Route

If the human already requested a pull request or local merge, do not ask again. Invoke the
corresponding owner with the exact repository, branch, base, and verification evidence:

- `denubis-plan-and-execute:make-pr` for a pushed branch and one pull request;
- `denubis-plan-and-execute:merge-to-main` for one verified local integration.

If no integration action was specified, ask one pointed question whether they want a pull
request, a local merge, or the branch left as-is. State any concrete consequence such as
an unpushed branch or pending UAT. Leaving the branch and worktree unchanged is the safe
default when no answer is available.

Do not delete a branch or worktree, discard commits, force-push, or clean untracked files.
Those are separate destructive actions and require exact targets plus explicit authority.
