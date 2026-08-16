---
name: commit
description: Use when the human asks to commit, or an approved execution lifecycle authorises a private checkpoint - stages owned changes intentionally and records coherent outcomes without publishing
user-invocable: true
---

# Create Git Commits

## Authority

An explicit commit request authorises local commits for the named work. Executing an
approved implementation plan authorises private checkpoint commits on its feature branch
without routine prompts when that plan's lifecycle says so. Neither route authorises
pushing, publishing, deploying, force-rewriting published history, or committing unrelated
work.

Do not commit on a protected base branch unless the human explicitly named that branch and
action. Preserve pre-existing changes.

## Inspect the real scope

Resolve repository root, branch, base, upstream, worktree, status, staged and unstaged
diffs, untracked files, and recent message style. Determine which changes this task owns.
Inspect likely secrets, generated binaries, caches, and editor files before staging.

Read project instructions and configured test or commit-hook guidance. Run the smallest
fresh gates needed for the changed boundary. Do not invent a fallback language command:
if no gate is configured, state the evidence available rather than running an unrelated
suite. A failing required gate blocks the commit.

Update current architecture, directives, runbooks, or user documentation only when the
implemented contract changed and those files own it. Historical plans do not need
palimpsest edits.

## Choose coherent boundaries

A durable commit is one independently understandable and reversible outcome. Keep its
behavior, first consumer, tests, migration, and documentation together. Split unrelated
outcomes even when they share a file; do not split design, setup, implementation, fixes,
tests, and docs merely because they occurred at different times.

There is no target count. Private checkpoints may be frequent. Fix rounds, review-response
commits, and superseded checkpoints fold into the outcome they serve during the
post-acceptance normalization lifecycle. Accepted design plans normally land with their
implementation; an accepted ADR may stand alone because the decision is itself durable.

Ask one pointed question only when ownership or the intended split would materially change
what is committed. A direct request with one coherent owned outcome needs no ceremonial
confirmation.

## Stage and commit

Stage exact owned paths or patch hunks. Never use broad staging when unowned, untracked, or
sensitive files could be included. Inspect the staged diff and staged name/status list
before committing.

Match the repository's message convention. Name the outcome concisely; put design
reasoning, alternatives, review findings, and verification narratives in project
documentation rather than the subject line. Do not add a provider-specific co-author
unless the project or human requires it.

Pass varying commit text through a file created by the runtime's structured file-editing
primitive, then use git commit -F with that exact file. Do not interpolate untrusted or
model-generated text into a shell command. Remove only the temporary file this operation
created after the commit succeeds.

Do not bypass hooks, disable signing, amend, or rewrite history unless the human named that
action. A rejected commit never existed; fix the demonstrated cause, restage, and create
the intended commit normally.

## Read back

Inspect the new commit, its tree and diff, and current status. Confirm only intended files
landed and report any remaining staged, unstaged, or untracked work. A commit proves a tree
was recorded; it does not replace tests, UAT, or integration evidence.
