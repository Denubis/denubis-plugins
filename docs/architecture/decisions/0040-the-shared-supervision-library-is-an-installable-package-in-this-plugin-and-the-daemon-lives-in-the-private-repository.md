# ADR 0040 — The shared supervision library is an installable package in this plugin; the daemon lives in the private repository and depends on it, never the reverse

**Status:** Accepted (2026-10-24). Rules where ADR 0039's local service lives and
answers the ADR 0034 question of how the private repository reaches the Codex classifier.
Extends ADR 0037's package into something the private repository can depend on.

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 1561, `user` record `61032644-c726-48c3-940f-c8836dce4b16` (2026-10-23T23:34:39Z,
  2026-10-24 10:34 Australia/Sydney), answering "Does the daemon live in the private
  permission-queue repository, with this plugin shipping only the hook clients and the
  driver verbs?": "I mean, there or here is fine, noting that we're building infra here
  that depends on there? or vice versa? So long as we're consistent, and building a
  library that handles common things, rather than a bunch of oneoff scripts"
- Line 1571, `user` record `2d4947e5-5805-4a98-9475-c09df5915509` (2026-10-23T23:35:27Z),
  answering "Is that the ruling: shared library in this plugin as an installable package,
  daemon in the private repository depending on it, and the private repo's path-load of
  `codex_supervisor.py` replaced by that dependency?": "ok, that's fine."

Exact raw-record resolver:

```sh
sed -n '1561p;1571p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

The first answer was indifferent on the address and firm on the principle; the second
accepted the concrete direction derived from that principle, which is what this ADR
records.

## Context

ADR 0039 rules that supervision events and mail go through one local Postgres-backed
service, with hooks making one call each. ADR 0034 moved the permission-queue
experiment, which reads Claude's session registry, to Brian's private repository
because it is deployment-specific; that repository still path-loads
`codex_supervisor.py` from this checkout as a single standard-library script (open
ticket raised during the move). A colleague runs this plugin on a Mac and must get a
working plugin without any private repository. The plugin's skills already depend on uv.

## Decision

1. The shared library is an installable Python package inside this plugin, a uv
   workspace member of this repository, growing out of ADR 0037's package. It owns:
   the service protocol and message types; the Record schema and its migrations; tmux and
   pane inspection; Claude and Codex session-registry reading and screen classification;
   the hook client; and the driver verbs behind `codex_supervisor.py` and
   `claude_supervisor.py`.
2. The daemon lives in the private repository and depends on that package. It adds only
   what is deployment-specific: Postgres credentials, the systemd user unit, the
   configured socket path, and the permission-queue viewer already there.
3. The dependency runs one way. The private repository depends on this plugin's package,
   pinned by path or git reference. Nothing in this plugin imports from the private
   repository.
4. The private repository's path-load of `codex_supervisor.py` is replaced by that
   dependency. The Codex screen classifier (`BUSY_SPINNERS`, `classify_snapshot`,
   `ObservationKind`, `held_sessions`, `_main_rollout`) has one owner, the package, and
   no copies.
5. Anything a hook, driver, or the daemon needs twice is written once, in the package.
   One-off scripts are not the pattern.

## Consequences

- The package needs a version the private repository can pin; the repository's existing
  plugin version-bump contract (plugin.json, marketplace.json, CHANGELOG together) covers
  it, and the package version moves with the plugin's.
- `codex_supervisor.py` and `claude_supervisor.py` are thin entry points, so the
  `supervising-codex` skill's invocation, `uv run --no-project --no-config python
  plugins/denubis-external-agents/scripts/codex_supervisor.py`, keeps working; whether
  that invocation becomes a console entry point is an implementation choice.
- The ADR 0034 question "should permission-queue keep loading `codex_supervisor.py` from
  this checkout" is answered: no, it depends on the package.
- The daemon's own design, schema and tests are the private repository's work; this
  plugin's work is the package, the hooks, and the drivers as clients of a protocol the
  package defines.
