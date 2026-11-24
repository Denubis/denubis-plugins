# ADR 2026-11-24-bbs-compact-nag-compaction-is-not-a-pause — A session compact-nag compacts says in its handover reply that it will carry on by itself, and no resume prompt is sent once another turn has begun

**Status:** Proposed (2026-11-24). Records a human report and two answers on the
`compact-nag` mod. Applied in `denubis-hook-compact-nag` 0.1.2. Amends ADR
2026-11-16-bbs-compact-nag-resumes-after-its-compaction, which stands for everything else
it says. ADR 2026-11-10-bbs-compact-nag-leaves-engine-threshold still holds.

## Authority evidence

Claude Code session `4508c81e-d079-4469-a8e7-aaaa7b0469e2`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/4508c81e-d079-4469-a8e7-aaaa7b0469e2.jsonl`.
Times are UTC on 2026-11-24.

- Line 1765, `attachment` record `401b2cda-8a07-4255-9898-79d61d44516f`, a
  `queued_command` with origin `human` (01:14:46.585Z), sent while the assistant was
  working. Brian, verbatim: "oh, and can we get the auto-compact nag to fire off a
  post-nag message to resume work?"
- Line 1927, human, record `d0bd5c70-225a-4dbb-bb8d-eb6d2b597a86` (01:19:22.804Z). It holds
  the question as the question zone put it, then Brian's answer. The question: "Did you
  see a session sit idle after the plugin compacted it at its own request, or do you want
  a resume message added after Claude Code's own automatic compaction?" Brian, verbatim:
  "yes, subagents just sit idle -- supervising sessions complaint"
- Line 2103, human, record `fad86a55-088e-4728-9073-9d0dd3ccc561` (02:21:08.752Z). The
  question: "Were the idle agents you saw workers running in their own panes, rather than
  subagents started inside a session with the Agent tool?" Brian, verbatim: "I don't have
  the faintest idea of what you're asking. Go search chats. They were not started by me"

Exact raw resolver:

```sh
sed -n '1765p;1927p;2103p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/4508c81e-d079-4469-a8e7-aaaa7b0469e2.jsonl
```

Brian sees the idling only as supervising sessions report it. The supervisor of session
`4508c81e` read his report as the case of a worker in its own pane that the mod compacts,
from the transcript evidence below. That reading is the supervisor's inference, not a
ruling of Brian's on the mechanism.

## Context

Transcripts are this machine's, under `/home/brian/.claude/projects/`, checked on
2026-11-24.

- A subagent started with the Agent tool is never compacted by the mod: `$.session.compact`
  takes no agent. In the 10 compactions Claude Code made of such subagents since 2026-11-10,
  each subagent responded again within 54 seconds, with no prompt.
- A worker in its own pane is the main loop of its own process, so the mod compacts it and
  then submits the resume prompt of ADR 2026-11-16. All 68 resume prompts found were
  followed by a response within 11 seconds.
- The handover turn's end sends the supervisor Claude Code's idle notice, which carries the
  worker's final reply as `result` (project `-home-brian-people-Brian-Ars-charsheet`,
  session `31a556fe-6264-46fc-a78e-f7532c5a45be` line 3543; session
  `de54918e-0297-4ebd-aec9-9e9a74c843a0` line 9750). The compaction then takes about 80
  seconds. In `de54918e` the supervisor sent "carry on" at 07:37:00.697 (line 9762) and
  told Brian "It paused while its working memory was condensed, and I've told it to carry
  on" (line 9767). The worker, session `56d86e4e-db92-45df-99a8-9110d44fb9d2`, finished
  compacting at 07:38:08.635 (line 1305).
- That message, waiting when the compaction ended, took the first turn 0.4 seconds later
  (`56d86e4e` line 1322). The resume prompt waited behind it and arrived 87 minutes later,
  at the end of the worker's next handover (line 2841). It said the session "has just been
  compacted", quoted the earlier cycle's brief, and its turn put off the compaction the
  worker had just asked for (line 2849).

## Decision

1. When `ready_to_compact` accepts the main session's handover, it tells the session that
   it carries on by itself after the compaction, and to end its reply by saying it is being
   compacted at its own request and will carry on by itself, so nobody needs to nudge it.
2. The resume prompt goes out 2 seconds after the mod's own compaction, and only if no
   main-loop turn has begun since the compaction returned to the mod. Of 69 compactions by
   the mod, found from 15 to 23 November, whose first turn was not the resume, 46 began that
   turn within 0.8 seconds (at most 0.755), one after 6.93 seconds, and 22 after 10 seconds
   or more, as messages sent after the compaction ended would.

   Method, rerunnable from the transcripts: take each `*.jsonl` file at most two levels
   under `/home/brian/.claude/projects/` modified after 2026-11-16T10:00 that holds a
   `compact_boundary` row. A boundary counts when its `compactMetadata.trigger` is `manual`,
   an assistant row among the 80 before it calls
   `mcp__denubis-hook-compact-nag__ready_to_compact`, and no `/compact` command lies within
   6 rows of it. Its first turn is the first later user row that is not meta, not the
   compaction summary, not a tool result and not command output; keep the boundaries whose
   first turn is not the mod's resume prompt, and take the seconds between the two rows'
   timestamps. The scripts that did this, `/tmp/claude-1000/cn-diag/teammate_after.py` and
   a reviewer's `/tmp/cnrev/tally.py`, are temporary.

Not chosen:
- A message from the mod to the supervisor. The supervisor's quiet-agents mod takes out a
  teammate's idle notice once that teammate has sent a message since the supervisor last
  wrote to it (`plugins/denubis-hook-quiet-agents/hooks/register.tsx`, `judgeDelivery`).
  The handover reply would go with it, and supervisors answer it: line 9762 of `de54918e`
  answers three questions from one.
- Rewriting the reply row as it is stored. Whether the idle notice reads the rewritten row
  is not known without a live teammate session.
- Dropping the prompt in a `prompt.submit` hook. In the test kit a plugin prompt's
  `prompt.submit` hooks run when it is submitted, and Claude Code's declarations do not
  settle whether they run then or once the session is idle.
- Reading the count of turns before the compaction. If a compaction raised a main-loop
  turn of its own, every resume would stop, and a worker left idle is worse than a late
  prompt.
- Any change to quiet-agents, to Claude Code's own compactions, or to the thresholds.

## Consequences

- Applied in `plugins/denubis-hook-compact-nag/hooks/register.ts` (`RESUME_AFTER_MS`, a
  count of main-loop turns begun, the accepted text), tested in
  `plugins/denubis-hook-compact-nag/tests/compact-nag.test.ts`.
- The reply line is an instruction to the model. It holds only as far as the worker writes
  it and the supervisor heeds it. A person reading a main session's reply sees it too.
- Decision 2 stops the late prompt only if the waiting message's turn begins after the
  compaction returns to the mod, where the count is read. If that turn begins first, the
  count already holds it, and the resume waits behind it and arrives late, as in 0.1.1.
  Which comes first is unproven. The transcripts record no `turn.start`. In the 25 of the
  46 quick first turns that have a queue record within 0.1 seconds of the message (in
  0.1.1, the mod queueing its resume once it had reset its record; 0.1.2 reads its count
  just before that reset), the message's row is stamped from 84 ms before that record to
  7 ms after it, and its turn's
  first attachment 16 to 250 ms after it (temporary script
  `/tmp/claude-1000/cn-diag/order2.py`): the two run at the same moment. Claude Code's
  declarations place `turn.start` after the prompt's `prompt.submit` and UserPromptSubmit
  hooks and before its first model call, and do not order it against the return of
  `$.session.compact`. The test stand-in starts the waiting turn after the return. What
  would settle it: a pane worker on 0.1.2 that its supervisor messages during the mod's own
  compaction, run several times. A resume prompt row after that message's turn in the
  worker's transcript shows the other order.
- A message queued ahead of the resume whose turn begins more than 2 seconds after the
  compaction still overtakes it, and a reload of the mod in those 2 seconds loses the
  resume.
- If a plugin vetoes the compaction, the reply has already said the session carries on
  by itself, and no resume follows.
- Tickets C1 and C2 in the main repository's open-questions file are untouched.
- Verification. Decision 2 is established by the mod's tests, in the order the stand-in
  gives. Decision 1 is wording to the model; it is judged by review against
  `docs/review-rubrics/instruction-control.md` and by live use, not by automation, since a
  test that locked its words would break that rubric's Testing rules. As of 2026-11-24 no
  live session has run 0.1.2.
