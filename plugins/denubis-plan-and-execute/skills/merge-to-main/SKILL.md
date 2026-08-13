---
name: merge-to-main
description: Use when the human requests local integration - verifies the feature and main worktrees, performs one permitted merge, and reruns project gates on the resulting main tree
user-invocable: true
disable-model-invocation: true
---

# Merge to Main Locally

## Authority

Invoking this skill authorises one local merge of the named feature branch into the
repository's main branch. It does not authorise a push, rebase, history rewrite, branch or
worktree deletion, issue mutation, publication, or deployment.

## Resolve both sides

Resolve the repository common directory, feature branch and worktree, main branch name,
main worktree, remote tracking state, and current object IDs. Require clean working trees
for both feature and main; preserve all unrelated and untracked files.

Read project merge policy and test guidance. If local main differs from its remote tracking
branch, report the exact ahead/behind state. Updating local main from the remote or pushing
it afterward is a separate action unless project policy and the human request explicitly
include it.

Determine whether main is an ancestor of the feature branch. Use a fast-forward merge when
it is. If the histories diverged, ask one pointed question about the desired merge or
rebase policy; do not select or perform a history-changing strategy silently.

## Verify, merge, verify

Discover required gates from project instructions, configured task runners, and CI. Run
the required gates before the merge on the exact feature commit that would become main.
Confirm each command exercised the intended target and produced its positive signal.

In the resolved main worktree, recheck that main's object ID and clean status have not
changed since preflight. Perform the single permitted merge using the selected project
policy. Stop on conflict; do not auto-resolve or broaden the merge.

Run them again after the merge from the main worktree. The resulting tree must match the
tree that passed pre-merge verification. If a post-merge gate fails, do not push or add
other changes. Report the old and new main object IDs, exact failure, and ask before any
rollback because that is a separate destructive action.

Return the resulting main object ID and both sets of gate evidence. Do not delete the
feature branch or worktree, mutate issue labels, push main, or claim deployment.
