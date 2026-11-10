# ADR 2026-11-10-bbs-pre-compaction-worklog-needs-no-approval — Before it compacts, a session may write or update its own worklog note in the notes directory without asking first

**Status:** Accepted (2026-11-10). Records a human ruling. It makes one exception to the
standing rule that a note changes only after Brian approves the proposal. The
instruction files that state that rule are not changed by this record.

## Authority evidence

Claude Code session `d4590dde-909a-4cc7-a999-be56c975149c`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d4590dde-909a-4cc7-a999-be56c975149c.jsonl`.
The timestamp is UTC on 2026-11-09, which was the morning of 2026-11-10 in Sydney.

- Line 532 (`attachment` record `5baf6149-ab19-40f9-b353-c24b987c3451`, a
  `queued_command` with origin `human`, 23:58:42.200Z). It holds the question as the
  question zone put it, followed by Brian's answer. The question:

  > Before it compacts, may a session write or update its own worklog note under .notes/ without first getting your approval for that note?

  Brian, verbatim: "yes"

Exact raw resolver:

```sh
sed -n '532p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d4590dde-909a-4cc7-a999-be56c975149c.jsonl
```

## Context

The `compact-nag` mod reminds a session at 40% context use to save its state before
compaction. Part of that state is a worklog entry covering what is done, the decisions
made, the open questions and the exact next step. The global instructions say a session
may change a file in the notes directory only after Brian approves the proposal, except for
open-question tickets and decision records. Under that rule, a session about to compact
could only propose a worklog, and if Brian was away its state would be lost. This
applies most to subagents and unattended sessions.

## Decision

Before it compacts, a session may write or update its own worklog note in the main
repository's notes directory without first getting Brian's approval for that note.

## Consequences

- The mod's reminder tells sessions to write their worklog in the notes directory directly.
- The exception covers a session's own worklog note written before compaction. It does
  not cover other notes, ADRs or instruction files, which still need an approved
  proposal. A decision that needs approval is written as a proposal or an open-question
  ticket.
- The notes directory stays situational memory under ADR 0043. A worklog cannot be the only home
  of anything another machine or session must cite.
