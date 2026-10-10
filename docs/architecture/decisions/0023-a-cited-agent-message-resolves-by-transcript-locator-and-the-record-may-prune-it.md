# ADR 0023 — A cited agent-to-agent message resolves by transcript locator, like every other citation; the record may prune a cited thread

**Status:** Accepted (2026-10-10). Supersedes property 10 of the 2026-08-09
cross-model-coordination design for the Postgres record (cited mail resolving to a message
file under the primary checkout).

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 1358, record `7c608770-77ad-4b3a-b661-ef3cc39cef62` (2026-10-10T02:58:36Z),
  answering ticket M12 ("(a) the transcript pointer is enough, the pruner may delete a
  cited thread; (b) cited bodies get written to a file under the main checkout before
  pruning"):
  "I mean... is this not a thing in a transcript? I'm so confused. Why would it not be?"

Exact raw-record resolver:

```sh
awk 'NR==1358' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

The earlier ruling the ticket was reconciling, same session, line 614 region (recorded
in ADR 0011's exchange): "if a message appears in a transcript, we can treat it not
important in postgres".

## Context

Property 10 of the August design required a cited message to resolve to a file under the
primary checkout, written when mail was a file-based scheme. Ticket M12 asked whether that
still bound the Postgres record once pruning was allowed. Brian's answer identifies the
ticket's false premise: under ADR 0018 every message body passes through two transcripts,
the sender's (the send tool call carries the body) and the receiver's (the pull returns
it). A pruned thread therefore has the same evidential standing as any human ruling cited
today: a session file and a line number.

## Decision

- A decision record that cites an agent-to-agent message cites it the way ADRs cite
  Brian: raw transcript path, line, record id, and an exact `awk 'NR==n'` resolver.
  Either the sender's or the receiver's transcript is acceptable; prefer the sender's.
- The record (function 1) needs no export path for cited messages, and the pruner may
  delete a cited thread once its body has appeared in a transcript, per the 2026-10-09
  ruling above.
- The dispatcher that writes the ADR is responsible for confirming the locator resolves
  before pruning is relevant, as for any citation.

## Consequences

- The synthesis design's "hold every cited thread from pruning" rule is removed; the
  `cited` flag on threads is unnecessary.
- The Record's pruning predicate is "body observed in a transcript" alone, as function 1
  proposed, with no citation exception.
- A message sent but never pulled (withdrawn, tombstoned) exists in the sender's
  transcript only; that is sufficient for citation.
