# ADR 0025 — Identity follows the pane: anything with its own pane is itself; a paneless sub-agent is not a messaging participant, and an attempt is an anomaly

**Status:** Accepted (2026-10-10). Amends ADR 0019 clause (a), which is withdrawn; closes
ticket M14 (a sub-agent's acknowledgement does not count because it must not occur).

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 1434 (2026-10-10), on ADR 0019(a): "so first off, why do sub-agents send as their
  parent? sorry, when did I ever actually approve that?"
- Line 1457 (2026-10-10), answering the re-asked question ("Does a sub-agent send as its
  parent, or get its own address?"): "I mean, I'd prefer that anything that has its own
  pane is itself, and anything that is paneless .... uh... probably isn't engaging in
  message-passing, but I'd be concerned if they were engaged in messaging"

Exact raw-record resolver:

```sh
awk 'NR==1434 || NR==1457' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

ADR 0019's clause (a), sub-agents send as their parent with a `via` stamp, rested on a
bundled three-part ask (ticket M8, line 965) that Brian answered "yes" while commenting
only on part (b). Asked on its own, Brian ruled differently. The dispatcher's bundling was
the defect; ADR 0019's clauses (b) and (c) stand.

## Decision

- **Identity follows the pane.** Every agent that owns a tmux pane (a hand-launched or
  spawned Claude, Codex, or agy session; a Claude teammate running in its own pane) is a
  participant with its own address.
- **Paneless agents are not participants.** In-process sub-agents on every vendor
  (Claude's Agent tool, Codex sub-agents, agy sub-agents) have no address, no mailbox,
  and no standing to send, acknowledge, pull, or reply. Pings are delivered only to a
  pane.
- **An attempt is an anomaly, not a message.** Where a hook or tool can tell the caller
  is a sub-agent (Claude exposes this in hook payloads), the send, acknowledge, and reply
  verbs refuse, the attempt is recorded against the parent's address, and it appears on
  the needs-Brian list as an anomaly. It is never silently attributed to the parent.
- **Detection is best effort and is a recorded limit.** Codex and agy may not let a hook
  distinguish a sub-agent from its parent. There the guard is structural (no sub-agent is
  ever pinged) rather than enforced at the verb.

## Consequences

- ADR 0019(a)'s `via` stamp is removed from the message schema; a Claude teammate's
  parent link stays, derived from its pane's spawn record.
- Ticket M14 is closed: an acknowledgement from a detected sub-agent is refused and
  reported, so "acknowledged" always means a pane-owning session saw the message.
- Function 2's `whoami` returns an error, not an identity, when called from a detected
  sub-agent, so the model learns it is not a participant.
- Live test T20 (sub-agent acknowledgement) changes its expected result from "accepted
  with via" to "refused and listed as anomaly" on Claude, and to "cannot be distinguished;
  documented limit" on Codex and agy if that is what the test finds.
- The dispatcher's lesson is already a standing rule (one question per ask); this ADR
  records the instance so that ADR 0019 is read with its clause (a) withdrawn.
