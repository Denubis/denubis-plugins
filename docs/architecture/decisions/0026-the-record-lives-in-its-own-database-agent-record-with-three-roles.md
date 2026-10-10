# ADR 0026 — The record lives in its own database, `agent_record`, with owner, app, and reader roles; `local_mail` is left untouched

**Status:** Accepted (2026-10-10). Implementation-time permission for the cross-provider
messaging design (2026-10-09 synthesis, function 1).

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 1479 (2026-10-10), answering ticket M15 ("New database, or a schema inside the
  existing one?"): "yes new db"

Exact raw-record resolver:

```sh
awk 'NR==1479' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Decision

- An agent may create database `agent_record` on the localhost Postgres server, with
  three roles: an owner that runs migrations, an app role that agents, hooks, and the
  actuator connect as, and a read-only role for the human surface.
- The August `local_mail` database is not modified, migrated, or dropped by this work.
  Dropping it is a separate action Brian takes.
- Per ADR 0024 the roles separate concerns and make the audit trail legible; they are not
  a security boundary and no server authentication change accompanies them.

## Consequences

- Migration 1 and live tests T1, T3, and T4 run against `agent_record` (T2 was dropped by
  ADR 0024).
- The synthesis design's "schema beside local_mail" alternative is removed.
- Credentials for the three roles are local peer-auth or a local-only password file;
  nothing leaves the box, consistent with ADR 0020's Tailscale-only reach.
