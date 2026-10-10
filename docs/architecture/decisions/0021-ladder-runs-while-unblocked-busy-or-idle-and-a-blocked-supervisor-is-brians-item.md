# ADR 0021 — The ladder runs whenever the supervisee is unblocked, busy or idle; an agent that keeps working past two nudges is interrupted; a blocked supervisor is Brian's item

**Status:** Accepted (2026-10-09). Amends ADR 0016, which said the clocks run only
while the supervisee is idle; they run while it is unblocked, whether idle or working.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 1220, record `d79e50d2-3fc3-4582-b094-f93fa6d80bfd` (2026-10-09T06:12:19Z),
  answering ticket M10 ("(a) the ladder also covers a busy agent ignoring its mail and
  the supervisor interrupts that work so it reads; (b) the ladder only covers idle agents
  and the interrupt rung goes. (a) or (b)?"):
  "you were saying something about not acknowledging and it just keeps going, that's an
  interrupt. If the supervisor is blocked then that's a me problem"

Exact raw-record resolver:

```sh
awk 'NR==1220' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

Verification 04 found that ADR 0015's interrupt rung and ADR 0016's idle-only clocks
cannot both hold: an idle pane has no turn to interrupt. Ticket M10 put the fork to
Brian.

## Decision

- The ladder's clocks run whenever the supervisee is not blocked: idle or working. A
  block (an open approval, an open question, a pending dialog) still pauses them, per
  ADR 0016.
- A supervisee that keeps working through the nudges without acknowledging its mail is
  interrupted by its supervisor at the interrupt rung: Escape or the vendor's
  equivalent through the guarded actuator, which then re-pings. The interrupt is the
  supervisor's act under its own task (ADR 0013).
- A supervisee with no supervisor has no interrupt rung and goes straight to Brian's
  list as stuck.
- If the supervisor itself is blocked, nothing substitutes for it. The supervisor's
  block is the item on Brian's needs-Brian list; no daemon runs the ladder on its behalf.

## Consequences

- Function 4's idle predicate becomes an unblocked predicate for clock purposes; idle
  evidence is still recorded, because the pointer-line nudge through the actuator needs
  an empty composer and the interrupt needs a running turn.
- Function 5's `interrupt` verb must confirm the turn stopped (Claude: the busy
  spinner line gone; Codex: its `Interrupt` hook event, named in verification 03) before
  the re-ping, and must refuse on a pending dialog like every other keystroke.
- ADR 0017's numbers are unchanged; they now measure unblocked time rather than idle
  time.
- The synthesis design's M10 fork collapses to branch (a); its configuration row for
  the fork can be removed.
