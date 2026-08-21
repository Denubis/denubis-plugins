---
name: merge-to-main
description: Use when the human requests integration into the default branch, optionally including an explicit push and cleanup - verifies both sides, integrates, reruns gates, and reads back every authorized state change
user-invocable: true
disable-model-invocation: true
---

# Merge to Main Locally

## Authority

Invoking this skill authorises one local integration of the named task branch into the
repository's resolved default branch. Push and cleanup remain separate unless the human
request passed to this skill explicitly includes them. For skill or plugin development,
`commit, marketplace, push`, `release`, or `ship` includes one default-branch push and
cleanup of the exact task-owned branch/worktree after remote verification. It never
authorises publishing the task branch.

## Resolve both sides

Resolve the repository common directory, task branch and worktree, default branch and
worktree, remote default branch, tracking state, and current object IDs. Do not assume the
default branch is named `main`. Require clean working trees for both sides; preserve all
unrelated and untracked files.

Read project merge policy and test guidance. If the local default differs from its remote
tracking branch, report the exact ahead/behind state. Updating it from the remote or pushing
it afterward is a separate action unless project policy and the human request explicitly
include it.

Determine whether the default branch is an ancestor of the task branch. Use a fast-forward
merge when
it is. If the histories diverged, ask one pointed question about the desired merge or
rebase policy; do not select or perform a history-changing strategy silently.

## Verify, merge, verify

Discover required gates from project instructions, configured task runners, and CI. Run
the required gates before the merge on the exact feature commit that would become main.
Confirm each command exercised the intended target and produced its positive signal.

In the resolved default-branch worktree, recheck that its object ID and clean status have not
changed since preflight. Perform the single permitted merge using the selected project
policy. Stop on conflict; do not auto-resolve or broaden the merge.

Run them again after the merge from the default-branch worktree. The resulting tree must match the
tree that passed pre-merge verification. If a post-merge gate fails, do not push or add
other changes. Report the old and new main object IDs, exact failure, and ask before any
rollback because that is a separate destructive action.

If push is authorised, name the destination explicitly rather than running a destination-
ambiguous push. Push the integrated commit to the resolved remote default ref, then read
that ref back and require exact object-ID equality.

If cleanup is authorised, prove the default branch contains the accepted tree and the task
branch has no unique commit. Remove the exact task worktree from outside it, then remove
the local task branch. Delete a same-named remote task ref only when the human explicitly
included that published ref in cleanup. Re-list worktrees and refs to verify absence.

Return the resulting default-branch object ID, both sets of gate evidence, remote read-back
when pushed, and exact cleanup results. Do not mutate issue labels, force-push, remove
unrelated isolation, or claim deployment.
