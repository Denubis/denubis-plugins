---
name: make-pr
description: Use when the human requests a pull request - verifies the exact branch, runs project gates, pushes it, creates one PR, and verifies the resulting remote record
user-invocable: true
disable-model-invocation: true
---

# Create a Pull Request

## Authority

Invoking this skill authorises pushing the current feature branch and creating one pull
request against the resolved base. It does not authorise rebasing, force-pushing, editing
issues or labels, deleting branches or worktrees, merging the PR, or changing unrelated
repository state.

## Preflight

Resolve the repository root, current branch, `origin` URL, intended base branch, existing
upstream, and any existing PR for the branch. Confirm the remote is the intended fork or
repository. If a PR already exists, report its URL and do not create another.

Require a clean working tree: no staged, unstaged, or in-scope untracked changes. A PR
contains commits, not the current model's intention. If changes remain, ask whether the
human wants the separate commit workflow; do not create a commit here.

Fetch remote references, then compare the feature branch with the actual remote base. If
the branch is behind or diverged, report the ahead/behind counts and ask one pointed
question about the intended integration method. Do not rewrite history or merge the base
without that answer. Never force-push unless the human separately names that action.

## Discover and run gates

Read project instructions and explicit test guidance first. Then inspect configured task
runners and CI definitions (`pyproject.toml`, `package.json`, `Makefile`, `justfile`, and
workflow files as applicable) for the gates that protect this change. Use the project's
own commands and configured environment.

Do not fall back blindly to a language-default command. If no required gate can be
established, report the inspected sources and ask one pointed question rather than
pretending an unrelated command is sufficient.

Run every discovered required gate on the exact commit to be pushed. Record command, exit
status, target exercised, and positive result. Any failure blocks the push. Investigate a
possibly pre-existing or intermittent failure; do not hide it with a stash, retry-until-
green, or “mostly passing” summary.

Review is optional when requested, required by project policy, or aimed at a concrete
risk. A model review does not replace the gates.

## Draft from the diff

Read all commits and the complete diff from remote base to `HEAD`. Draft a concise title
and body describing current behavior and why it changed. Include exact verification
commands and any genuine human testing still pending. Do not paste model review status or
claim that unrun checks passed.

## Push, create, verify

Push the current branch without force and create one PR against the resolved base. Use the
repository's PR template when present. Then read the created PR back and verify its URL,
head repository and branch, base branch, title, and draft state against the request.

If push succeeds but PR creation fails, report the pushed ref and error; retry only the PR
operation after correcting the demonstrated cause. If the returned PR targets the wrong
repository or base, stop and report the mismatch before any further remote mutation.

Return the PR URL and fresh gate evidence. Do not mutate issue labels, merge the PR, or
remove the branch or worktree as post-processing.
