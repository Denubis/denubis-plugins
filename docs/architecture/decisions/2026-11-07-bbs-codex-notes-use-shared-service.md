# ADR 2026-11-07-bbs-codex-notes-use-shared-service — Codex's hook sends its notes through the shared local service, not straight into the supervisor's inbox

**Status:** Accepted (2026-11-07). Applies ADR 0039 item 4 to the Claude-drives-Codex work.

## Authority evidence

Session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`):

- Line 3231, the supervisor's question (`assistant` record
  `20adae60-e36c-4f69-b7f7-1f158b862761`, 2026-11-07T06:44:45Z): "should Codex's hook post
  its "done" and "needs approval" notes straight into the supervising Claude session's inbox
  now? Or should they wait for the shared local service that ADR 0039 says every hook calls?
  That service doesn't run on this machine yet."
- Line 3234, Brian's answer (`user` record `077c5ec3-27d4-4e47-a44d-dc99cac3d541`,
  2026-11-07T06:49:44Z, 17:49 Australia/Sydney): "shared local, it's fine. new worker is
  new. get sonnet on renaming." The first sentence answers this question; the second is
  recorded in ADR 2026-11-07-bbs-new-codex-worker-starts-fresh.

```sh
sed -n '3231p;3234p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

The open-questions ticket it closes, raised 2026-11-07 as A1, asked:
"Should Codex's hook post its "done" and "needs approval" notes straight into the
supervising Claude session's inbox now, or wait for the one Postgres-backed local service
ADR 0039 item 4 rules every hook calls?"

## Context

On 2026-11-02 Brian chose hook-based posting to a side channel over reading the Codex pane
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f31135e5-0253-441f-8140-bdd86e8940bc.jsonl`
lines 1270 and 1293). On 2026-11-07 he approved a proposal for the hook and a quiet-agents
mod change (same file, line 2185, "yes?") that did not mention ADR 0039 item 4, which rules
that hooks make exactly one call to one local, Postgres-backed service for supervision
events and mail. No such service ran on this machine on 2026-11-07.

## Decision

Codex's hook sends its "done" and "needs approval" notes through the shared local service
of ADR 0039 item 4. It does not post them straight into the supervising session's inbox,
even while that service does not exist.

## Consequences

- The Codex hook and the quiet-agents mod change approved on 2026-11-07 depend on that
  service and are built on it, not ahead of it. The adapter tool, which does not depend
  on the hook, proceeds.
- Reading "it's fine" as accepting that wait is the supervisor's interpretation, not
  Brian's wording.
