---
name: recording-project-notes
description: Use after the user approves creating a new project-owned .notes record - writes the agreed filename, flat frontmatter, durable content, and resolvable evidence
user-invocable: false
---

# Record an Approved Project Note

Create one new durable owner only after `scanning-project-notes` has established that no
existing note, ADR, code, test, or ordinary documentation owns the knowledge and the user
has approved the exact proposal. Approval must name the path, semantic content, future
consequence, and resolvable evidence. Without that approval, return to the proposal gate
without writing.

Two records are exempt from the approval gate because they exist so that questions and
rulings reach the human instead of waiting on the human: the open-questions ticket file
and the decision records. See *Open questions and decisions* below. Every other note
waits for approval.

## Resolve the destination

Resolve the main repository root from `git rev-parse --git-common-dir` as the scanning
skill specifies. The destination is `<main-repository-root>/.notes/`, shared by every
worktree. Re-inventory that directory immediately before creation. If the proposed path
now exists or another record owns the same knowledge, stop and propose maintenance of the
current owner instead.

Use the approved filename exactly. New note names follow:

```text
<type>_<kebab-case-slug>.md
```

The type prefix is `feedback`, `project`, `user`, or `reference`. The slug identifies the
knowledge, not the incident that exposed it.

## Write the approved record

Use flat YAML frontmatter:

```yaml
---
name: kebab-case-slug
description: one-line summary
type: feedback | project | user | reference
originSessionId: current-session-uuid
---
```

`originSessionId` is optional when no exact session identifier is available. Do not add
nested metadata, speculative keywords, timestamps, status fields, or workflow state.

Write only the approved durable claim and the context needed to apply it. A feedback note
uses `**Why:**` and `**How to apply:**` prose headings. Add an `**Evidence:**` section when
the approved proposal names paths, commands, logs, diffs, tests, ADRs, or original human
messages; preserve exact locators rather than paraphrasing them into authority.

If the evidence or wording changed after approval, stop and present the changed proposal
instead of widening the authorized write.

## Open questions and decisions

Any agent, including a dispatched subagent, that is unclear about scope, premise, or
approach pauses and records the question rather than assuming. Pausing is always welcome;
silent assumption never resolves anything. The record is a ticket appended to
`<main-repository-root>/.notes/project_open-questions.md`. Create the file, with the
frontmatter below, if it does not exist; no approval is needed for that.

```yaml
---
name: open-questions
description: Durable queue of questions awaiting a human answer, with each answer beside its question
type: project
---
```

Each ticket carries the question, why it blocks, the evidence, and who raised it. A ticket
closes only when the human answers it; write the answer beside the question verbatim, with
the question it answered. Compaction, `/clear`, scroll, elapsed time, or repetition never
closes a ticket. An answered ticket stays in the file as the record.

Anything the human rules is also a decision record. The default register is
`<main-repository-root>/.notes/decisions/`, with an index at
`.notes/decisions/README.md`; a project that already keeps its register elsewhere, such
as `docs/architecture/decisions/`, keeps it there. Follow that register's format and
authority-evidence rule. Creating a decision record needs no approval; the ruling it
records did.

`.notes/` is durable passive memory, never transport. Prompt exchange with an external
agent, mail, and other operational state stay in their own gitignored directories.

## Verify the new owner

- Reopen the exact file and parse its frontmatter as one flat mapping.
- Confirm the filename prefix matches `type` and the frontmatter `name` matches the slug.
- Resolve every evidence pointer on which the note relies.
- Confirm no other note, ADR, code, test, or documentation file was changed.
- Report the created owner and bounded verification; do not treat existence as proof that
  the underlying claim is true.
