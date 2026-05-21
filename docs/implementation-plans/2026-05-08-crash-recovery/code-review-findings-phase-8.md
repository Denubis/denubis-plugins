# Code Review Findings — phase-8

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Prior Findings Verification

### Important #1 — Stale README Status section
**Status: Resolved**

The Status section at `plugins/denubis-crash-recovery/README.md:168–175` now reads:

> v1.0.0 ships the plugin, the SQLite schema, the full classification pipeline… Crash detection is operational end-to-end as of 1.0.0; requires `denubis-plan-and-execute >= 2.32.2` for the wrapper that writes liveness files.

Both false claims eliminated: "v0.1.0" → "v1.0.0", and the "lands in Phase 8" forward-reference replaced with a present-tense operational statement and version requirement. No new unsupported claims introduced.

### Minor #1 — Transcript-archive block reachability change
**Status: Resolved**

Both the `SHOULD_TRANSCRIPT` branch and the `IS_RESUMED` branch are inside the `if [[ "$EXIT_CODE" -eq 0 ]]; then … fi` outer guard at `scripts/claude-wrapper.sh:109–140`. The liveness cleanup block at lines 140–147 (which fires on exit 0 OR 130) remains outside and after the gate. Structure confirmed correct. The explanatory comment at lines 106–108 accurately cites the `|| EXIT_CODE=$?` fix at line 103.

### Minor #2 — Version qualifier in Troubleshooting
**Status: Resolved**

`plugins/denubis-crash-recovery/README.md:123` now reads "There is no audit trail by design" — the "in v0.1.0" qualifier is gone.

### Minor #3 — Atomic-write test name overclaims (two-part fix)
**Status: Resolved**

Part 1: `mv "$CR_LIVE_TMP" "$CR_LIVE_FILE"` at `scripts/claude-wrapper.sh:100` now has the trailing comment `# atomic via rename(2) on the same filesystem`.

Part 2: The bats test at `tests/test_claude_wrapper_liveness.bats:123` is now named `"no .tmp residue after clean completion"`. The test body is byte-identical to the pre-fix version — name-only change confirmed. Test 10 in the suite.

## Verification

```
Tests: uv run pytest -q → 782 passed in 3.40s
Bats (liveness): bats tests/test_claude_wrapper_liveness.bats → 10/10 ok
  (test 10: "no .tmp residue after clean completion")
Bats (smoke): bats tests/test_crash_recovery_smoke.bats → 7/7 ok
```

## Plan Alignment

All AC items remain in the same state as the initial review. The two fix commits address documentation and wrapper-script behaviour only; no AC items were reopened or regressed.

## Issues

None.

## Decision: APPROVED FOR MERGE
