---
name: scanning-project-notes
description: Use when explicitly asked to recover project notes or prior work, or when a task depends on a named historical decision that current repository artifacts cannot resolve
---

# Scanning Project Notes

Retrieve project memory and feedback as main-agent work when the task actually depends on
them. Do not run this as an ambient pre-edit ritual. Ordinary repository instructions,
current code, and a supplied plan remain the first owners of ordinary implementation
facts.

Notes do not create authority or decisions: resolve any human instruction they rely on to
the original human record. Do not dispatch an advisor and do not wait for a SessionStart
reminder.

## 1. Resolve the notes universe

Run `git rev-parse --git-common-dir`. In a Git repository, resolve that path to an
absolute directory and use its parent as the main repository root; this makes every
worktree share the main checkout's `.notes/`. Outside Git, use the current project root.

Use `<main-repository-root>/.notes/` as the notes directory. List its Markdown files by
name with hidden and ignored paths included. If the directory is absent, say only that it
is absent at the resolved path and stop unless prior-chat recovery is independently
required.

## 2. Read before selecting

Read enough frontmatter to identify the notes that could change this task, then open those
notes completely. State the inventory and the selection boundary; do not bulk-load
unrelated bodies merely to complete a count.

Do not select notes with a keyword grep. Keywords are finding aids written for an earlier
task, not the boundary of the current task's subject.

## 3. Search prior chats

Search prior chats only when the user requested prior-work recovery or the current task
depends on a historical decision that notes and repository artifacts do not resolve. Run
one narrowly scoped search first. Reframe or widen it only when a concrete unresolved
question remains; do not search the whole task in several ways by default. Use `--all` or
`--everything` only when the required source is known to cross those boundaries. Treat an
empty result as bounded by the command's reported coverage.

Resolve a relevant message with `cc-search-chats context <full-message-id> --json` before
using it. Prefer provider-qualified exact locators when the installed resolver supports
them. A ranked search hit is a lead, not the authority record itself.

## 4. Check reference integrity

Open every note or document pointer on which the task would rely. For a human-derived
claim, the pointer must resolve to the original human message; a note, ADR, quotation, or
paraphrase does not substitute for it.

If a pointer is missing, ambiguous, stale, or resolves to the wrong role, stop the
dependent action and repair the reference. If the source cannot be recovered, write a
focused prompt for the human to open in a new session, resolve, and return with a new
authority record.

## 5. Use the result

Carry relevant findings into the work itself. Do not produce a ceremonial advisory report
unless the user asked for one. If sources disagree or a note is stale, raise the one
decision that changes the next action.

Do not create or update `.notes/` merely because the scan found something. Project memory
is written only after the user agrees to the durable wording.

## Completion check

- The main-repository notes path is explicit.
- The note inventory and selection boundary are explicit.
- Relevant note bodies were opened.
- Any necessary chat search reports its coverage.
- Every relied-on pointer resolves exactly.
- No advisor or SessionStart request stands between the task and retrieval.
