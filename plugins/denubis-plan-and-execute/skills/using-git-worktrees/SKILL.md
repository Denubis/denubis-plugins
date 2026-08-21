---
name: using-git-worktrees
description: Use when the human requests isolation or concurrent agents, overlapping changes, or unrelated dirty state require a separate worktree - selects, creates, and verifies the exact checkout
user-invocable: true
argument-hint: "[task, branch, or exact worktree path]"
---

# Create an Isolated Git Worktree

## Decide whether isolation is required

Inspect the current branch, worktrees, status, active task ownership, and known concurrent
agents before the first project edit.

| Observed state | Action |
|---|---|
| Another agent may edit the same repository, files overlap, or unrelated changes occupy the checkout | Create or reuse a task-owned worktree. |
| A clean existing branch or worktree already belongs to this task and no concurrent writer shares it | Continue there. |
| The only checkout is the default branch and no isolation trigger exists | Warn that work would occur on the default branch and wait for explicit human assent. |
| The human explicitly requested the default branch after that warning | Stay there; do not create a ceremonial branch. |

Do not treat a current non-default branch as task-owned merely because it is checked out.
Resolve its purpose and diff first. When several agents are active, prefer separate
worktrees even if their intended file sets appear disjoint; hidden generated or metadata
surfaces can still overlap.

## Resolve the target

Resolve the main repository through `git rev-parse --git-common-dir`, list existing
worktrees, inspect current branches, and identify the requested base. Derive the branch and
directory name directly from the human's task unless they supplied exact values. Use a
short lowercase kebab-case slug; do not query a remote issue merely to decorate it.

Default to the repository-local `.worktrees/<slug>` convention. Before creating it, verify
that the parent directory is ignored from the main repository using `git check-ignore` and
a positive control. If it is not ignored, ask before editing `.gitignore` or choose an
explicit out-of-tree path supplied by the human.

Resolve the intended integration branch as well as the exact target path and task branch.
Record both so the delivery workflow can return the accepted tree and clean the temporary
checkout. Refuse an existing non-worktree directory, an
already-checked-out branch, a missing base, or a path outside the authorised location.
Do not remove an existing worktree or repurpose it for a different branch.

## Create

Use `git worktree add` with the resolved base and either the requested existing branch or
a newly created feature branch. Record the new `HEAD`, branch, common Git directory, and
absolute path immediately after creation.

If Git LFS is configured, use the project's documented LFS procedure and verify pointer
materialization. Do not rewrite attributes or fetch unrelated LFS objects merely because
the repository contains LFS metadata.

## Apply documented local setup

Read `.ed3d/worktree-setup.md` when present and run only its current project-specific
steps. If `.worktreeinclude` exists, treat it as an explicit list of local files that may
be copied from the main worktree; validate each source and destination and never invent or
write that control file as setup.

For dependency setup, use the project's lockfile and native sync command. Use the
configured package-manager caches exactly as provided. Never redirect or override uv,
pip, npm, Hugging Face, Torch, or other caches. If a configured cache is absent, read-only,
or outside the permitted filesystem, stop and ask for the environment or sandbox to be
fixed before installing anything.

Do not copy credentials or machine-specific configuration unless the documented setup
names the exact file and the human-authorised environment permits it.

## Verify and return

Run the documented baseline checks from the new worktree. If they fail, compare with the
base checkout only through safe read-only evidence; do not start feature fixes inside the
setup task.

Report the exact worktree path, task branch, intended integration branch, base object ID,
setup actions, and baseline results.
Leave the caller able to change into that path. Do not commit setup files, remove another
worktree, or imply future cleanup authority.
