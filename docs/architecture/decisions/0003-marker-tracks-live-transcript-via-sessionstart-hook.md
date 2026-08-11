# ADR 0003 — Crash marker tracks the live transcript

**Status:** Accepted

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
