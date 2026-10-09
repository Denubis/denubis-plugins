# ADR 0013 — A driving supervisor answers only what its own task narrowly needs; anything with other implications pauses and escalates

**Status:** Accepted (2026-10-09).

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 709, record `1d1f1749-c724-4e6d-8c21-c2e7628c5833` (2026-10-09T02:07:13Z),
  answering ticket M3 ("when you tell a session it may drive another, what does that
  permission cover?" with options A, today's blanket narrow-dialog grant, and B, a listed
  class per pair):
  "may drive: \"Does this request fufill my request, as narrowly scoped as posssible?\"
  because there's friction between the approver and my intention."
- Line 716, record `f03dede0-1fff-4275-869d-142bd6fc1c93` (2026-10-09T02:07:40Z),
  continuing the same answer:
  "anything that may have implications other than what I intended, should have a pause
  and query, and there's nothing wrong with hitting the e-stop and escalating to me
  (including by the supervisor itself)"

Exact raw-record resolver:

```sh
sed -n '709p;716p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

Function 6 (Authority) of the 2026-10-09 messaging design asked whether a "may drive"
grant keeps today's meaning (the supervisor answers every narrow one-command dialog,
minus approver-marked danger) or becomes a listed request class per supervisor and
supervisee pair. Brian chose neither: the grant is a judgment the supervisor makes
against its own assigned task.

## Decision

- A supervisor that has been told it may drive a supervisee answers a supervisee's
  approval request only when the request fulfils the supervisor's own task, read as
  narrowly as possible. The question it asks is Brian's: "Does this request fulfil my
  request, as narrowly scoped as possible?"
- Any request that may have implications beyond what Brian intended is not answered. The
  supervisor pauses, records the question, and escalates to Brian. Escalation is never a
  failure; the supervisor may stop itself at any point.
- This replaces the class-list and blanket-template readings. The approver's own policy
  still runs first (ADR 0012 context; DR12 of the August design): a policy deny is
  terminal, and only requests the approver leaves to judgement reach the supervisor.
- Brian names the reason: there is friction between the approver's rules and his
  intention. The supervisor's judgement is scoped by intention, not by rule category.

## Consequences

- Function 6's mandate record carries the supervisor's task statement, because that is
  what "my request" resolves against. A mandate without a task statement grants nothing.
- Every supervisor-answered approval records the request, the task it was judged
  against, and the one-line reason; that is the audit for "narrowly scoped".
- A supervisor's escalation goes to the needs-Brian list on the surface (ADR 0012) and
  to the open-questions file where it is a question rather than a keypress.
- The friction Brian names between the approver and his intention is not resolved here;
  it is an input to the approver project, recorded by this citation.
