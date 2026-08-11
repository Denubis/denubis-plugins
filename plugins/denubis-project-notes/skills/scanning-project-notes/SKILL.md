---
name: scanning-project-notes
description: Use when a task's purpose is clear and before changing project files, to retrieve relevant project memory and prior chat work directly.
---

# Scanning Project Notes

Retrieve project memory as main-agent task-entry work. Do not dispatch an advisor and do
not wait for a SessionStart reminder.

## 1. Resolve the notes universe

Run `git rev-parse --git-common-dir`. In a Git repository, resolve that path to an
absolute directory and use its parent as the main repository root; this makes every
worktree share the main checkout's `.notes/`. Outside Git, use the current project root.

Use `<main-repository-root>/.notes/` as the notes directory. List its Markdown files by
name with hidden and ignored paths included. Record the count before judging relevance.
If the directory is absent, say only that it is absent at the resolved path.

## 2. Read before selecting

Read every note's frontmatter yourself. Compare the number read with the inventory count.
A partial read is not a completed scan. Open the full body of each note whose description,
type, or evidence could change the task.

Do not select notes with a keyword grep. Keywords are finding aids written for an earlier
task, not the boundary of the current task's subject.

## 3. Search prior chats

Run several differently framed `cc-search-chats search "<terms>" --json` searches for
the task. Use `--all` when it spans projects and `--everything` when normal coverage is
too narrow. Treat an empty result as bounded by the command's reported coverage.

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
- Inventory count and frontmatter-read count agree.
- Relevant note bodies were opened.
- Chat searches report their coverage.
- Every relied-on pointer resolves exactly.
- No advisor or SessionStart request stands between the task and retrieval.
