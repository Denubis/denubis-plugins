# ADR 0003 — Crash marker tracks the live transcript

**Status:** Accepted

## Authority evidence

- Runtime-owner direction:
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/80357450-6297-4fd1-a7ec-0a68665e42a8.jsonl:175`
  — `cc-search-chats context 57248254-730e-4d9d-a5b9-27786335231b --json`
- Structured-rewrite direction:
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/80357450-6297-4fd1-a7ec-0a68665e42a8.jsonl:546`
  — `cc-search-chats context 69bf33af-e999-4581-8f31-4a7577c9839c --json`

The resolvers supply the human messages that selected the runtime owner and implementation
substrate. This ADR does not reproduce them.

## Context

The wrapper process and its PID-keyed liveness file survive a Claude `/clear`, while the
live transcript path can change. A launch-time transcript identifier can therefore point
at an abandoned transcript when crash recovery later consumes it.

## Decision

The wrapper exports `CR_LIVE_FILE`. On `SessionStart` events for
`startup|resume|clear|compact`, `update-live-marker.py` takes the basename of the payload's
`transcript_path` and atomically replaces only the marker's `session_id=` line.

The hook uses `transcript_path`, not the payload's `session_id`. It preserves every other
line and the file mode. It exits successfully without writing when the environment path,
marker, or canonical transcript UUID is absent. `correlate()` consumes this exact marker
match before weaker recovery paths.

## Consequences

- Runtime observation owns the current transcript identity; crash-time code does not
  reconstruct a handoff from timestamps.
- Multiple transcript rotations update the same PID-keyed marker.
- Sessions launched without the wrapper receive no marker update.
- SessionStart retains this mechanical side effect but supplies no generic workflow
  prose.

## Verification

- Hook: `plugins/denubis-plan-and-execute/hooks/update-live-marker.py`.
- Registration: `plugins/denubis-plan-and-execute/hooks/hooks.json`.
- Boundary tests: `tests/test_update_live_marker.bats` and
  `tests/test_claude_wrapper_liveness.bats`.
- Paired current constraint: `../constraints.md`, “Live-transcript marker maintenance”.
