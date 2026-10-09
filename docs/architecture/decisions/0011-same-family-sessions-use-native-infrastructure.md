# ADR 0011 — Same-family sessions use their native infrastructure; the messaging system is cross-provider

**Status:** Accepted (2026-10-09). Reaffirms property 7 and DR11 of the paused
2026-08-09 cross-model coordination design against the 2026-10-09 "any supervises any"
goal. Qualified the same day by ADR 0018: native infrastructure carries supervision
mechanics and the mail ping; mail content for every pair, same-family included, goes
through the record.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 614, record `bf8cd154-c680-4f66-8490-7d74fc825f82` (2026-10-09T01:52:40Z),
  answering ticket M1 ("when a Claude session supervises another Claude session, or
  Codex supervises Codex, does 'any supervises any' put that pair through the tmux
  actuator and the approval-mandate model too, or do same-family pairs stay on the
  vendor's native channel?"):
  "I would yes, like that same-model family just use their normal infra, this is for
  cross-provider."

Exact raw-record resolver:

```sh
sed -n '614p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

The goal it qualifies is in the same session: "I want any [codex,claude,agy] to be able
to supervise any other, and I want messages to be able to be exchanged properly between
sessions."

## Context

The 2026-10-09 design fanout (seven proposer agents, in the gitignored
`codex-prompts/out/2026-10-09-messaging/`) asked whether "any supervises any" overrides
the August rulings that same-family pairs use native facilities (DR11) and that "this
system never makes Claude an approver for Claude" (property 7). Proposal 05 (Supervise)
and proposal 06 (Authority) both stopped on it.

## Decision

- A Claude session supervising a Claude session, or Codex supervising Codex, uses the
  vendor's own channel: Claude's SendMessage and ListAgents, agent teams, and sub-agents;
  Codex's native sub-agents. The cross-provider messaging and supervision system is not
  used for those pairs.
- The tmux actuator, the Record's supervision edges, and approval mandates are for
  cross-provider relationships only.
- No same-family supervisor holds an approval mandate; property 7 stands.

## Consequences

- Function 5's vendor adapters implement cross-provider pairs only; a same-family edge
  is refused rather than actuated.
- Whether the tmux actuator may still serve a same-family pair for the few acts native
  cannot do (clear, compact, spawn) was not ruled. Treat it as not permitted until asked.
- The Record may still carry same-family messages if a vendor's native channel is the
  transport and the sender chooses to log them; that is a function 1 question, not a
  reopening of this one.
