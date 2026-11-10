# ADR 2026-11-10-bbs-compact-nag-leaves-engine-threshold — The compact-nag mod leaves Claude Code's own compaction point alone; it notes the need to prepare at 40% and the session asks for a compaction when it is ready

**Status:** Accepted (2026-11-10). Records two human rulings on the `compact-nag` mod,
made minutes apart.

## Authority evidence

Claude Code session `d4590dde-909a-4cc7-a999-be56c975149c`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d4590dde-909a-4cc7-a999-be56c975149c.jsonl`.
The timestamp is UTC on 2026-11-10.

- Line 699 (`attachment` record `97f87105-e87a-4406-b237-19783a2d694b`, a
  `queued_command` with origin `human`, 00:01:34.640Z). It holds the question as the
  question zone put it, followed by Brian's answer:
  - Question: "Should the mod itself lower Claude Code's automatic compaction point to
    about half the context window, for the main session and subagents alike?"
  - Brian, verbatim: "no, it should inject a note that we need to prepare for compact at
    40% and let the session call for a compact when it's ready"

- Line 794 (`attachment` record `58780c7e-a3c6-4b43-a6fa-5139428b329a`, a
  `queued_command` with origin `human`, 00:03:51.065Z):
  - Question: "If the main session passes 50% context without having said it is ready,
    should the mod still compact it at the end of that turn?"
  - Brian, verbatim: "no, but it should fire a more urgent nag each stop after 50%"
- Line 871 (`attachment` record `4e449354-3185-4a4c-b7fc-defa05861f94`, a
  `queued_command` with origin `human`, 00:05:24.155Z), sent unprompted while the mod
  was being built. Brian, verbatim: "(also, if there's now a trivial way of surfacing
  the heads-up alerts in subagents to main, include that, since we're touching the same
  surface area, if not, it's fine)"

Exact raw resolver:

```sh
sed -n '699p;794p;871p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d4590dde-909a-4cc7-a999-be56c975149c.jsonl
```

## Context

Brian asked for a mod that nags a session to compact at 40% of its context and compacts
it at 50%, or sooner when the session says it is ready. In build 2.1.321 a mod can
compact the main session only between turns (`$.session.compact`). It cannot compact a
subagent on request: a subagent compacts only when Claude Code's own auto-compaction
fires. The one way to make subagents compact near 50% would have been to lower that
point through the `autoCompactWindow` setting. That would apply to every loop and would
also compact the main session mid-turn.

## Decision

1. The mod does not lower Claude Code's own automatic compaction point. It does not set
   or override `autoCompactWindow` or `CLAUDE_CODE_AUTO_COMPACT_WINDOW`.
2. At 40% the mod injects a note that the session needs to prepare for compaction.
3. The session asks for a compaction when it is ready.
4. The mod never compacts on a threshold alone. Past 50%, if the main session has not
   said it is ready, the mod gives it a more urgent note at each stop (line 794).
5. When a subagent is given a note, the main conversation also gets a one-line notice
   naming that subagent (line 871).

## Consequences

- Subagents get the prepare-for-compaction note. If a subagent states it is ready, its
  brief is used when Claude Code's own compaction fires, but nothing compacts a subagent
  early.
- For the main session, the mod compacts between turns once the session has asked for
  it, and at no other time. Without that request, the only compaction is Claude Code's
  own near the full window.
- The notes and the notice are rows the model reads (`session.append`). Under ADR
  0051's instruction-delivery contract, `tests/test_instruction_delivery.py` lists this
  delivery as permitted, citing lines 699, 794 and 871. Reading those lines as that
  permission is the implementing session's reading.
- Whether the urgent note at a stop should also make the session continue straight away,
  as a blocking Stop hook does, was not asked. As built, the note is read at the
  session's next turn.
