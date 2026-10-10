# ADR 0022 — A supervisor's mandate carries expiry and a directory root as hard stops, no decision count; the screen-reading `--approve` keypress is soft-retired pending the hooks

**Status:** Accepted (2026-10-09). Qualifies ADR 0013.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`, answering ticket M11:

- Line 1269, record `477a48f3-7cf9-4b0d-94c6-ab29b7104eca` (2026-10-09T06:15:10Z), on
  the proposed maximum-decisions cap: "um, the fuck is going on there? That's not a good
  heuristic."
- Line 1297, record `f952c56d-e9b8-4f27-97fb-4bdcaadfa114` (2026-10-09T06:18:27Z), on
  whether the old keypress stays as a Codex-only fallback: "retire but... soft because
  we'll see how well the hooks work"

Exact raw-record resolver:

```sh
awk 'NR==1269 || NR==1297' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

Context for the second answer, from the same exchange: Brian asked how approvals can
be done "by reference" and whether the hooks genuinely exist. The dispatcher's answer:
the vendor's PermissionRequest hook is held open, the intake records the request with an
id, a decision row against that id is returned as the hook's typed allow or deny, and
nothing is typed; Codex already has two such hooks registered by the approver, Claude's
would be a new registration, agy has none.

## Decision

- A mandate (ADR 0013) carries two mechanical hard stops beside the task statement: an
  expiry time, and a directory root the supervisee's requests must stay inside. A
  request outside either is escalated to Brian regardless of judgement.
- There is no maximum-decisions count. A count is not a safety property; the narrow-task
  judgement bounds each answer and the expiry bounds the grant in time.
- The screen-reading keypress (`codex_supervisor.py --approve` as it exists today) is
  retired for agents in favour of decisions by reference through held hooks, softly:
  it remains in the tool until the hook route has been shown to work on the installed
  Codex and Claude versions (phase 0 live tests), and its removal is a separate change
  Brian makes once the hooks are trusted. While it remains, every use is logged as a
  keypress approval against the request id it was answering, so the two routes are
  comparable.

## Consequences

- Function 6's mandate schema: `task_statement`, `expires_at`, `cwd_root`; no
  `max_decisions`.
- Function 5 keeps the `--approve` verb and marks it deprecated in its help text, with a
  pointer to `decide --request <id>`; the synthesis design's M11 fork collapses to this.
- The soft retirement is reviewed when phase 0's hook tests pass; that review is a
  ticket to raise then, not now.
