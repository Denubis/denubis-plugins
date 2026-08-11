# Project-note reference integrity — 2026-08-11

**Status:** Active integrity defect. This is a bounded audit and repair prompt, not an
authority source or a substitute for the referenced records.

## Authority

The human invocations governing this repair are at lines `314`, `324`, `334`, `352`,
`362`, `383`, and `403` of:

`/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl`

Use the exact one-based resolver in
[`2026-08-11-instruction-control-system.md`](../design-plans/2026-08-11-instruction-control-system.md#authority-evidence).

## Observed universe

The main repository root is
`/home/brian/people/Brian/brian-ed3d-plugins`; its `.notes/` contained 50 top-level
Markdown files at inspection.

- 34 notes declare `originSessionId` across 17 distinct Claude sessions.
- Every one of those 17 identifiers resolves to exactly one file below
  `/home/brian/.claude/projects/`.
- `originSessionId` identifies a session, not the human message on which a note relies.
  None of the 34 is therefore an exact authority pinpoint as written.
- 16 notes declare no origin session.
- `review_run-autoexport-spec-cpr.md` also lacks `description`, so frontmatter-only
  retrieval cannot describe it.

This audit does not classify every note as human-authorised. Reference notes may instead
depend on code, test output, logs, or publications. The defect is that the relied-on
source and exact resolver are not stated.

## Repair prompt

Open a fresh session in the main repository and repair this inventory breadth-first.

For every top-level `.notes/*.md` file:

1. Identify each claim whose use would change an action.
2. If it depends on a human instruction, locate the original human message. Add a flat
   frontmatter `authoritySource` containing an absolute raw-source `path:line` and an
   `authorityResolver` containing a `cc-search-chats context <full-message-uuid> --json`
   invocation when the installed resolver supports that source.
3. If it depends on external evidence instead, add an exact `evidenceSource` that a human
   can open: a current file and symbol/test, a log record, or the project's approved
   publication resolver. Do not use another note or model report as the evidence source.
4. Open every pointer and prove its positive control. A human source must resolve to one
   non-empty human invocation; a code or test pointer must resolve to the claimed
   producer. A session identifier by itself is not enough.
5. Keep the note as memory. Remove copied transcript quotations and paraphrases that are
   presented as evidence; the source pointer, not a model-authored restatement, bears the
   authority.
6. If the original source cannot be located, do not repair the prose by inference. Write
   one focused prompt for the human to invoke in a new session, and leave the dependent
   note explicitly unavailable for action until that record returns.

Repair one note at a time. After each repair, rerun its resolver before moving on. At the
end, inventory the directory again and report exact counts for resolved human authority,
resolved external evidence, unavailable claims, and malformed frontmatter. Do not claim
completion from an empty search result.

## Current consumer boundary

`denubis-project-notes:scanning-project-notes` may treat these files as finding aids and
memory. It must open a relied-on pointer before a note can authorise action. An absent,
session-only, ambiguous, or wrong-role pointer blocks that dependent action; it does not
block unrelated source cleanup or deployment that does not consume the note's claim.
