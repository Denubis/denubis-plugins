# ADR 0015 — Unacknowledged mail climbs an escalation ladder ending in an interrupt and Brian; a sender may withdraw a mooted message, leaving a tombstone

**Status:** Accepted (2026-10-09).

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 786, record `9cd113e8-ddd1-44f0-ab2b-4f3cd779cacf` (2026-10-09T02:16:32Z),
  answering ticket M5 ("(a) after a small number of nudges the system stops nudging and
  lists the item for you as stuck; (b) may the sender withdraw a message no longer
  needed?"):
  "um it ... so this is where hitting escape is important for a? there's ... there is an
  escalation ladder here and never-acknowledge is a problem and that's what esc or
  equivalent interrupt is for. But yes, a sender may withdraw it if it's mooted.
  Tombstones are important"

Exact raw-record resolver:

```sh
sed -n '786p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

Earlier rulings this reconciles: property 4 of the 2026-08-09 design (retry until the
recipient acknowledges) and ADR 0009 (announce once; an idle pane gets no monitor).

## Context

Proposal 04 (Acknowledge) asked whether "give up" may mean stop nudging and list the
item for Brian, and whether a sender may close its own unanswered message. Brian's
answer is that giving up is not the end of the ladder: a supervisee that never
acknowledges is a problem to be interrupted, not merely reported. The August Local Mail
bug report (`.notes/local-mail/messages/d7bb97bc…`) had already asked for a guarded
interrupt verb that refuses unsafe pane states.

## Decision

- An unacknowledged delivery climbs a ladder: nudge (the hook-path and pointer-line
  reminders, bounded by ticket M6's numbers), then a guarded interrupt of the supervisee
  (Escape or the vendor's equivalent, sent through the single actuator, refused when a
  dialog is pending or the pane state is unreadable), then escalation to Brian as a
  "stuck" item on the needs-Brian list. The item is never auto-acknowledged, expired, or
  dropped.
- The interrupt is a supervisor act on its own supervisee. A session with no supervisor
  skips that rung and goes straight to Brian.
- A sender may withdraw its own message when it is mooted. Withdrawal is a recorded
  event, a tombstone, that keeps the message, its deliveries, and the withdrawal reason;
  it removes the obligation from every list but erases nothing.
- Only the sender or Brian may withdraw. A recipient cannot close an item addressed to
  it except by acknowledging and, where required, answering.

## Consequences

- Function 5 gains an `interrupt` verb with the same guards as `send`; its vendor
  adapters must know each TUI's interrupt key and how to confirm the turn stopped.
- Function 4's state model adds `withdrawn` as a terminal fact with a reason and actor,
  distinct from acknowledged and answered.
- The needs-Brian list (function 7) shows "stuck" only after the interrupt rung has run
  or been refused, with the refusal reason attached.
- How many nudges, how far apart, and when "stuck" is declared are ticket M6.
