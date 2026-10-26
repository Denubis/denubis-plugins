# ADR 0044 — The ticket file stays in the notes directory: an open question is situational, and its answer moves to a record about its subject

**Status:** Accepted (2026-10-26). Confirms ADR 0005 and ADR 0008 against a reading of ADR
0043 that would have moved the ticket file into `docs/`.

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 5376, `user` record `dc846076-0fac-4dc8-9139-da706793e0c2` (2026-10-26T04:38:03Z,
  2026-10-26 15:38 Australia/Sydney), asked whether the global instruction (a ticket file
  under `docs/`) or ADRs 0005 and 0008 (the ticket file in the notes directory) governs: "fix the ADRs please, and get a sonnet to global scan ADRs in projects/ for bad
  directions into .notes"
- Line 5638, `user` record `422e4b7c-bffd-4a4a-8027-7c6f079b49ed` (2026-10-26T05:01:01Z,
  16:01 Australia/Sydney), after the supervisor had recorded the first reading and asked
  again: "it's a list of questions, not their answers, to things being worked on? Does this
  not properly represent a note? However, if the open questions are in fact registers of
  answered questions then we both need to fix that and properly move them to ADRs or docs
  as needed to represent the things they are about, not the fact they are a question"

```sh
sed -n '5376p;5638p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

## Context

ADR 0043 ruled that the notes directory holds nothing durable that other machines rely on.
The supervisor read that as covering the open-questions ticket file, since workers on other
machines append to it, and the global instructions of 2026-10-25 name an `open-questions`
file under `docs/` instead.
Brian's first answer ("fix the ADRs") was taken as agreement, and a first version of this ADR
moved the file. His second message corrects the premise: a list of unanswered questions about
work in progress is situational memory, which is what a note is. What must not sit in the
notes directory is the durable thing, the answer, and a ticket file that has accumulated
answered questions is the actual defect.

## Decision

1. The open-questions ticket file stays where ADR 0005 put it, `project_open-questions.md` in
   the main checkout's notes directory. ADR 0008's content rule stands: open questions only.
2. An answered question leaves the ticket file for a record about its subject: a decision
   record for a ruling, or the document that now owns the fact. The record is about the
   thing decided, not about the fact that it was once a question. Status prose describing
   where answered tickets went does not belong in the ticket file either.
3. A ticket file found to hold answered questions is repaired by moving that content into the
   records it belongs to and deleting it from the file. The survey of Brian's other
   repositories (ADR 0043 and the 2026-10-26 scan) includes this audit for each ticket file.
4. The global instruction naming a ticket file under `docs/` is corrected to match; until then
   this ADR and ADR 0005 govern in any repository that follows this register.

## Consequences

- The commit-skill checker keeps reading the ticket file from the notes directory and keeps
  its open-questions check (ADR 0042 decision 3).
- The move of this repository's ticket file into `docs/` made under the first reading is
  reversed; the status prose about answered tickets at the top of the file is removed under
  decision 2.
- The three skills that name the notes-directory path for tickets remain correct.

## Amendment (2026-10-26): the approver project keeps its ticket file under `docs/`

The approver project tracks its notes directory in Git (ignoring only its Local Mail
subtree) and runs on two machines, so its ticket file travels with the repository either
way. Asked whether it follows this ADR into the notes directory, Brian ruled: "approver
should be in docs, two machines." (line 6876, `user` record
`ad21b911-d207-4365-b938-53333c699b7e`, 2026-10-26T06:34:53Z, same session). That project's
own register and instructions govern its ticket-file location; decision 1 applies to
repositories that follow this register.

```sh
sed -n '6876p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```
