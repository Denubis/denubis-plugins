# ADR 0016 — The escalation ladder's clocks run only while the supervisee is idle and unblocked; a block is listed, not nudged

**Status:** Accepted (2026-10-09). Qualifies ADR 0015 and reaffirms property 6 of the
2026-08-09 design and ADR 0009's finding that every repeated reminder had been waiting
behind a permission prompt. Amended the same day by ADR 0021: the clocks run while the
supervisee is unblocked, whether idle or working, not only while idle.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 823, record `21641918-a9d2-47ee-8b59-4370549ea0f1` (2026-10-09T02:28:50Z),
  answering ticket M6 (the table of ladder timings: idle grace, nudge count and gap,
  interrupt, stuck, stale):
  "well, it depends if it's stuck in an approver conga, because none of these make any
  sense if there's a block"

Exact raw-record resolver:

```sh
sed -n '823p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

ADR 0015 set the ladder (nudge, interrupt, escalate to Brian). Ticket M6 asked for its
timings. Brian's answer is that no timing applies while the supervisee is blocked: a
pane waiting on an approval dialog, a question, or a running tool is not idle, and
nudging it is the behaviour ADR 0009 removed.

## Decision

- Every ladder clock (idle grace, nudge gap, interrupt, stuck) runs only while the
  Record holds positive evidence that the supervisee is idle: its last event is a Stop
  with no prompt since, no approval or question is pending for it, and no tool is
  running. The evidence sources are function 5's idle predicate per vendor.
- When a block appears, the clocks pause and the block is the item on the needs-Brian
  list (an approval under ADR 0012, a question as a ticket). When the block clears, the
  clocks resume from where they paused; they do not restart.
- A chain of approvals ("an approver conga") is one block after another; the mail
  ladder never fires inside it.

## Consequences

- Function 4's resurfacing and function 5's nudge intent both read the same idle
  predicate; neither may use elapsed wall time alone.
- The numbers themselves (ticket M6) remain Brian's to set, now with the condition that
  they measure unblocked idle time only.
