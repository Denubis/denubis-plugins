# ADR 0047 — agent-notice-log appends without a size limit

**Status:** Accepted (2026-10-24). Applied in `denubis-hook-agent-notice-log` 0.1.0
(`b329741`). Recorded first in the untracked `.notes/decisions/0001`; moved here
2026-10-25.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl`:

- Line 691, human, record `a4d8a3aa-f17a-4756-8a1e-89e13cf5b574`
  (2026-10-24T04:40:51.974Z): "oh, that's so frustrating, yes, we need proper ability
  to move reports. Specifically, can we not emit a file anyways?"

Exact raw-record resolver:

```sh
sed -n '691p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl
```

## Context

The question as recorded: when the agent-notice-log file reaches 4 MiB, should the mod
stop logging, rotate, or truncate? `$.fs` refuses reads and writes over 4 MiB, and the
mod appended by reading and rewriting the whole file. Which record put the question to
the human is not recorded.

## Decision

The premise was removed. The mod appends through `tee -a` with no size cap and no
read-back.

## Consequences

Applied in `plugins/denubis-hook-agent-notice-log/hooks/register.tsx`, `appendLine`.
No further consequences were recorded.
