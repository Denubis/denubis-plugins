# ADR 0048 — quiet-agents takes an idle notice by the report-received rule, not a time window

**Status:** Accepted (2026-10-24). Applied in `denubis-hook-quiet-agents` 0.1.0
(`b329741`); the send-time mark added in 0.1.1 (`cee8d18`) is the dispatcher's
mechanism, not a human ruling. Recorded first in the untracked `.notes/decisions/0002`;
moved here 2026-10-25.

## Authority evidence

Records in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl`.
"Human" marks an original human message; "dispatcher" marks the team lead's assistant
record, which states the rule and rules nothing itself.

- Line 373, human, record `899f0c7e-9480-4832-85fc-3ef793fd2174`
  (2026-10-24T03:41:52.418Z): "so that's unacceptable. specifically that only matters
  if ... idle needs to be aware of what's going on. I don't like "idle idle" either the
  supervisor is waiting on me"
- Line 394, dispatcher, record `0c248f9c-e00b-44ce-92a3-5075303d4cc3`
  (2026-10-24T03:53:59.174Z): the statement of the rule, ending "That is the whole rule.
  No timer."
- Line 397, human, record `a28de245-80bc-486a-ab64-1ed0afd37bd0`
  (2026-10-24T03:59:43.369Z), answering line 394: "yes"

Exact raw-record resolver:

```sh
sed -n '373p;394p;397p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl
```

## Context

The question as recorded: quiet-agents took a teammate's idle notice when it arrived
within 120 seconds of that teammate's last message. Confirm 120 seconds, or name another
value. Which record put that question to the human is not recorded.

## Decision

The rule, in the dispatcher's terms that "yes" accepted:

- a teammate's report sets a mark;
- its idle notice is taken out while the mark stands;
- a new instruction to it clears the mark;
- a teammate that never reported gets its notice through.

There is no timer.

## Consequences

Applied in `plugins/denubis-hook-quiet-agents/hooks/register.tsx`. The `session.receive`
hook marks and consumes; the `session.send` and SendMessage `tool.call` hooks clear the
mark. From 0.1.1 an agent's delivered send to the main conversation also sets the mark.
That door was the dispatcher's choice of mechanism on 2026-10-25, not a human ruling.
