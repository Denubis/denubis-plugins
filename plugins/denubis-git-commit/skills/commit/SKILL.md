---
name: commit
description: Use when the human asks to commit, or an approved execution lifecycle authorises a private checkpoint - stages owned changes and records coherent outcomes without publishing
user-invocable: true
---

# Create Git Commits

## Authority

An explicit commit request authorises local commits for the named work. Executing an
approved implementation plan authorises private checkpoint commits on its isolated task branch
without routine prompts when that plan's lifecycle says so. Neither route authorises
pushing, publishing, deploying, force-rewriting published history, or committing unrelated
work.

Before the first project edit, a session on the default branch must warn the human and
obtain assent to work there; concurrent agents, overlapping files, or unrelated dirty
state instead require task-owned isolation. At commit time, do not invent a feature branch
to relocate work already completed on the default branch. Disclose the branch, preserve
pre-existing changes, and apply the authority the human actually granted.

A combined skill/plugin request such as `commit, marketplace, push`, `release`, or `ship`
is broader than this local commit procedure. Complete the release metadata here, then hand
the accepted tree to the integration workflow; never interpret it as permission to push
the current non-default branch.

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

Pass the message as literal data. In a Bash execution tool, use a quoted heredoc directly
on Git's standard input:

```bash
git commit -F - <<'COMMIT_MESSAGE'
Describe the coherent outcome
COMMIT_MESSAGE
```

Choose a delimiter that does not occur as a complete line in the message. Quoting it
preserves backticks, dollar signs, and command substitutions as text. Do not embed the
message in an interpolated shell argument. This Bash example is for the execution tool;
fish has no heredoc syntax. For a fish terminal or a runtime without stdin support, write
the literal message to a task-owned file using an available editor or quoted heredoc in
Bash, then use `git commit -F <path>`. Preserve a pre-existing file, and remove only your
own message file after success.

Heredocs, patches, and native file editors are valid authoring routes under the host's
destination permissions. No particular provider's Write/Edit tool is required. Loading
this discoverable skill supplies a procedure, not permission to commit.

Do not bypass hooks, disable signing, amend, or rewrite history unless the human named that
action. A rejected commit never existed; fix the demonstrated cause, restage, and create
the intended commit normally.

## Read back

Inspect the new commit, its tree and diff, and current status. Confirm only intended files
landed and report any remaining staged, unstaged, or untracked work. A commit proves a tree
was recorded; it does not replace tests, UAT, or integration evidence.
