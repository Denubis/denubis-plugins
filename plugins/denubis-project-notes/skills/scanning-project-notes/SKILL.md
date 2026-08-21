---
name: scanning-project-notes
description: Use before consequential project work to inspect relevant project-owned .notes, and after durable findings to propose evidence-linked note or ADR changes; prior-chat recovery stays conditional
---

# Scanning Project Notes

Use project memory as a task loop: inspect it before the first consequential project
action, apply relevant records during the work, and maintain a durable owner only when
the work changes what future work should know. Keep local retrieval bounded: inventory
every note, read enough frontmatter to select by the current task, and open only relevant
bodies. Prior-chat recovery is a separate, conditional action.

Ordinary repository instructions, current code, and an accepted plan remain the first
owners of implementation facts. Notes carry durable project facts, preferences,
references, and feedback.

Notes do not create authority or decisions: resolve any human instruction they rely on to
the original human record. Do not dispatch an advisor and do not wait for a SessionStart
reminder.

## 1. Resolve the notes universe

Run `git rev-parse --git-common-dir`. In a Git repository, resolve that path to an
absolute directory and use its parent as the main repository root; this makes every
worktree share the main checkout's `.notes/`. Outside Git, use the current project root.

Use `<main-repository-root>/.notes/` as the notes directory. List its Markdown files by
name with hidden and ignored paths included. If the directory is absent, record that
bounded result and continue the ordinary task unless prior-chat recovery is independently
required.

## 2. Read before selecting

Read enough frontmatter to identify the notes that could change this task, then open those
notes completely. Keep the inventory and selection boundary available as working
evidence; do not bulk-load unrelated bodies or turn the scan into a ceremonial report.

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

## 6. Close the memory loop

After a failure, correction, or newly verified constraint, decide whether the evidence
changes durable project knowledge. Routine debugging, transient state, and facts already
owned by code or tests do not earn a memory record.

Choose the current semantic owner:

- revise an existing `.notes/` record for a durable project fact, preference, reference,
  or feedback;
- revise an existing ADR for a current architectural decision and its rationale; or
- when no existing owner fits, propose one new `.notes/` path and use
  `denubis-project-notes:recording-project-notes` only after the user approves it; or
- use code, tests, or ordinary documentation when they already reveal the fact.

Prefer revising the existing owner over appending a new lesson. Before changing a note or
ADR, present one maintenance proposal containing:

1. the exact owner path and whether it exists;
2. the exact semantic change or proposed wording;
3. why the change would alter future work; and
4. the resolvable evidence to link, such as a focused test result, log, diff, current
   source, or original human instruction.

Wait for the user to approve that proposal before editing the note or ADR. After approval,
apply only the agreed change and verify every evidence pointer. If no durable change clears
this gate, finish without proposing or writing project memory.

## Completion check

- The main-repository notes path is explicit.
- The note inventory and selection boundary are explicit.
- Relevant note bodies were opened.
- Prior chats were searched only when independently required, with reported coverage.
- Every relied-on pointer resolves exactly.
- An absent or irrelevant notes set did not stop the ordinary task.
- Any note or ADR maintenance proposal names its owner, change, consequence, and evidence.
- The user approved the maintenance proposal before its owner was edited.
- Routine failures did not produce performative memory records.
- No advisor or SessionStart request stands between the task and retrieval.
