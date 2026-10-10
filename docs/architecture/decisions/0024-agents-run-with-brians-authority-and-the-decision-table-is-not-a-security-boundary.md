# ADR 0024 — Agents on this box act with Brian's authority; the record's decision table is not a security boundary against them, and no Postgres authentication change is made

**Status:** Accepted (2026-10-10).

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 1413, answering ticket M13 ("(a) the approver's shell rules only; (b) the database
  refuses agents, with a server authentication change"):
  "um... that's... really stupid? If I'm able to approve things, then... an agent can just
  tmux approve things. Thi s is a really bad question"

Exact raw-record resolver:

```sh
awk 'NR==1413' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

Ticket M13 asked whether Postgres should be hardened so an agent, running as OS user
`brian` and therefore a peer-authenticated superuser, could not write its own approval
row. Brian's answer identifies the false premise: the design requires a tmux actuator
(function 3's universal fallback, ADR 0021's interrupt rung) through which any agent can
press y on any dialog. Every agent session already runs with Brian's full authority on
this machine. Hardening one table against a party that can type at the pane protects
nothing.

## Decision

- Agents are trusted as Brian's own user. The record's decision table, mandates, and
  roles are not an adversarial security boundary and the design does not claim they are.
- The guards on approvals are behavioural: ADR 0013's narrow-task judgement, ADR 0022's
  expiry and directory rails, and the approver's existing command review. Their purpose
  is to catch mistakes and over-reach, not a hostile agent.
- No `pg_hba` or server authentication change is made for this system. Database roles
  (reader, writer, surface) exist to prevent accidents and to make the audit trail
  legible, nothing more.
- Live test T2 (verify `pg_hba` state) is dropped from the design's gate list.

## Consequences

- Phase 0 has no server-administration prerequisite; the build can create its roles and
  proceed (subject to ticket M15).
- Proposal 01 Q4 and proposal 06 section 2.3 are answered: approver deny rules over the
  decision table are optional hygiene, not a required control.
- A future need for real agent isolation is a different system (separate OS user or
  container), to be raised as its own ticket if it ever matters.
