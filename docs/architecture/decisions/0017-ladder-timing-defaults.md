# ADR 0017 — Escalation ladder timing defaults, accepted as revisable

**Status:** Accepted (2026-10-09), as adopted defaults Brian expects to revise.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 859, record `3a32907b-963a-470d-965e-9d1b535b3de8` (2026-10-09T02:34:17Z),
  answering ticket M6 ("120 s grace, 2 nudges 10 min apart, then interrupt, stuck at
  30 min of unblocked idle, stale at 2 h for an acknowledged but unanswered question.
  Accept as revisable defaults, or change a number?"):
  "yes, that's fine, just... that feels like it's going to be horribly frustrating, but
  sure"

Exact raw-record resolver:

```sh
sed -n '859p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Decision

All clocks measure unblocked idle time only (ADR 0016).

| Rung | Default |
|---|---|
| Idle grace before the first nudge after a message lands | 120 seconds |
| Nudges per context, minimum gap | 2 nudges, 10 minutes apart |
| Interrupt (Escape or vendor equivalent) if still unacknowledged | after the second nudge's gap elapses |
| Listed for Brian as "stuck" | 30 minutes after the first nudge, or at once if the interrupt is refused |
| Acknowledged but unanswered question listed as "stale" | 2 hours |

The numbers were proposed by agents (proposals 04 and 05) and accepted by Brian; they
are not derived from measurement. They live in one configuration owner, not scattered
as literals.

## Consequences

- Brian expects these to be frustrating in use. The first field period should log every
  nudge, interrupt, and listing with its elapsed unblocked time so the numbers can be
  retuned from evidence rather than re-guessed.
- A change to any value is a revision of this ADR, not a new ruling.
