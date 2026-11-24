# ADR 2026-11-16-bbs-compact-nag-resumes-after-its-compaction — After its own compaction of the main session, compact-nag starts the next turn, quoting the session's brief and its handover reply

**Status:** Accepted (2026-11-16). Records a human request and a human ruling on the
`compact-nag` mod. Applied in `denubis-hook-compact-nag` 0.1.1. ADR
2026-11-10-bbs-compact-nag-leaves-engine-threshold still holds: the mod compacts the
main session only once it says it is ready. Amended 2026-11-24 (proposed) by ADR
2026-11-24-bbs-compact-nag-compaction-is-not-a-pause: the prompt goes out 2 seconds after
the compaction and only if no turn has begun since.

## Authority evidence

Claude Code session `867062b5-221f-407a-8be7-efd5cf13e3af`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/867062b5-221f-407a-8be7-efd5cf13e3af.jsonl`.
Times are UTC on 2026-11-16.

- Line 13, human, record `247f60ff-75b4-47cf-bbfa-7ba4f000a2a0` (09:23:40.649Z): "small
  task, when autocompact happens via nag, can we have a ping post-compact to get the
  worker resuming from it's last command to itself?"
- Line 490, `attachment` record `ea28f8c4-2f5a-40b2-a2a6-b5db539704a4`, a
  `queued_command` with origin `human` (09:41:30.153Z), sent while the assistant was
  working: "(and also, we need to collect the pre-commpact turn's message to it's future
  self"
- Line 698, assistant, record `9b29178a-360f-43d1-b414-70f8b7516569` (09:51:01.738Z): the
  question as put through the question zone, after a fresh review found that a deferred
  compaction would quote a later turn's reply. Lines 790 and 801 quote its context and
  question in full:

  > I'm changing the compact-nag mod so that after it compacts a session (once the session has saved its handover and said it is ready), it starts a new turn. That turn tells the session to resume and quotes its last reply from before the compaction. Usually the compaction happens right after the turn where the session wrote its handover. Sometimes a message arrives first, though, such as a teammate's message to a worker. Then the session keeps working, maybe for ten minutes, and the compaction happens only when a later turn ends. That was seen in a worker session on 15 November. As built now, the resume prompt quotes the reply from that later turn. If the answer is yes, I'll save the handover reply when the session says it is ready, and quote that instead.
  >
  > When the compaction happens a few turns late, should the resume prompt quote the reply the session wrote when it handed over, rather than its most recent reply?

- Line 790, human, record `83b36e97-68ec-4f31-b4a5-373755222876` (09:59:27.321Z), after
  the quoted question. Brian, verbatim: "yep"
- Line 801, human, record `23420568-6c18-4400-875e-1dbb1c18552d` (09:59:42.423Z), after
  the same quoted question. Brian, verbatim: "yep the prod should be after it's "stop" and
  compacted?"
- Line 953, human, record `4277c87d-d894-4917-b7f9-cf5dd517463b` (10:13:33.573Z): "ok,
  commit and push"

Exact raw resolver:

```sh
sed -n '13p;490p;698p;790p;801p;953p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/867062b5-221f-407a-8be7-efd5cf13e3af.jsonl
```

## Context

In 0.1.0, once the main session's `ready_to_compact` call was accepted, the mod
compacted it 500 ms after that turn ended. The session then sat idle; only the person's
next message started another turn. In session `c06f9205-3224-4dbf-b681-82abb13bdb37` (this repository's transcripts),
the compaction record at line 2032 is at 05:37:44.142Z on 2026-11-15, and the person's
next message, "um... ok?", is at line 2053, 21 seconds later.

The mod's compaction is refused while a turn is running. When a message arrives first,
such as a teammate's, the session works on and the mod tries again at each later turn
end. In session `0ce875ec-294e-46e9-bc51-f067551d52a2` (project
`-media-brian-storage-people-Adela-melica`), `ready_to_compact` was called at line 1467
and accepted at line 1468, the handover reply is at line 1469 (10:33:55.487Z), a
team-lead message started a new turn at line 1471, and the compaction was refused at
line 1479. That turn ended about ten minutes later with a different reply, at line 1846
(10:43:46.464Z).

## Decision

Once the mod's own compaction of the main session goes ahead, the mod submits a prompt
that starts the next turn, after the stop and the compaction (line 801). The prompt tells
the session to re-read the handover files it saved and take the next step they name, or,
if that step waits on the person, to say what it needs and stop. It quotes the session's
brief and its reply at the end of the turn in which it said it was ready (lines 490 and
790), not the reply of a later turn.

## Consequences

- Applied in `plugins/denubis-hook-compact-nag/hooks/register.ts`. The first main-loop
  turn end after an accepted `ready_to_compact` stores that turn's reply in the loop
  record (`handoverReply`, under the shape tag `loops-2`). `compactMain` sends the prompt
  only after the compaction resolves without a skip.
- No prompt follows a refused or vetoed compaction, `/compact`, or Claude Code's own
  compaction.
- The prompt goes in framed as the plugin's message, not as the person's words.
- When the compaction runs turns late, the session may have done work since the handover
  files and the reply it is pointed back to.
- The first load of 0.1.1 reads what 0.1.0 stored as empty, so a session part-way
  through a handover is nagged again.
- Established by the mod's tests. As of 2026-11-16 no live session has shown the prompt.
