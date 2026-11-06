# ADR 0049 — quiet-agents nudges only after an answered turn

**Status:** Accepted (2026-10-24). Applied in `denubis-hook-quiet-agents` 0.1.0
(`b329741`). Recorded first in the untracked `.notes/decisions/0003`; moved here
2026-10-25.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl`:

- Line 562, human, record `e0043f1f-2cbd-48ad-a064-d1d490b7b61b`
  (2026-10-24T04:36:50.376Z): "fire only when the turn ended with an answer, yes"

Exact raw-record resolver:

```sh
sed -n '562p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl
```

## Context

The question as recorded: should the turn-end nudge also fire when the main loop's turn
ended because the person interrupted it (`aborted`) or an API error ended it (`error`),
or only when the model answered? Which record put the question to the human is not
recorded.

## Decision

The turn-end nudge fires only when the turn ended with an answer.

## Consequences

Applied in `plugins/denubis-hook-quiet-agents/hooks/register.tsx`, the `turn.complete`
hook (`e.reason === 'answer'`), and established by the test "a turn the person
interrupted or an error ended raises no nudge; the next answered turn does"
(`plugins/denubis-hook-quiet-agents/tests/quiet-agents.test.ts`). No further
consequences were recorded.
