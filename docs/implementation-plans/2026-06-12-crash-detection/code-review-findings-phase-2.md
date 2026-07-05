# Code Review Findings — phase-2

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification

```
Tests: uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q → 210 passed
Bats:  bats tests/test_claude_wrapper_liveness.bats → 1..18, all ok
```

Both suites green. No pre-existing failures in scope; the 6 unrelated collection errors in
`plugins/denubis-plan-and-execute/scripts/workflow_statusline/` were not run and are not
reported.

## Plan Alignment

- AC4.1 — wrapper writes `session_id=` (fresh + resumed) and `start_time=<int>` ✓
- AC4.2 — `pid_alive_checked` returns True on matching start_time, False on mismatch;
  scan's both fact-builders use `pid_alive_checked` ✓
- AC4.3 — `correlate` direct-matches on `session_id` (precedence 0, before `--resume`) ✓
- AC4.4 — legacy marker (start_time=None) falls back to bare `kill -0`; session_id=None
  falls through to stage-2 unchanged ✓
- AC4.5 — cleanup block unchanged; clean/abnormal exit behaviour confirmed by existing
  bats tests 1–10, still green ✓

All five acceptance criteria implemented and covered.

## Issues

None.

## Strengths worth recording

**Comm-safe parse agreement.** Both the bash `_proc_starttime` and Python `_proc_start_time`
strip through the LAST `)` before tokenising, then index the same field (20th token in bash
positional, index 19 in Python split). The AC4.2 bats test independently recomputes the
wrapper's start_time using the same rpartition logic and asserts byte-for-byte agreement with
the written marker — this is a genuine cross-language seam test, not a vacuous echo.

**Non-vacuous seam pair.** The two bats seam tests (tests 17–18) form a self-certifying pair:
test 17 (round-trip → LIVE) proves the correct start_time passes; test 18 (mutated start_time
→ CRASHED) proves start_time is actually consulted in the comparison branch, not silently
bypassed via the `None` back-compat path. Without test 18, test 17 could green even if
`pid_alive_checked` always returned True.

**Load-bearing `kind == DIRECT_MATCH` assertion.** `test_correlate_direct_match_via_session_id_without_resume`
asserts `result.kind == CorrelationKind.DIRECT_MATCH`, not just `result.uuid`. The comment
explains why: the JSONL is deliberately in the mtime window, so asserting only uuid would
false-green via the mtime path. Asserting kind pins that the session_id branch, not the mtime
fallback, produced the result.

**Precedence test.** `test_correlate_session_id_beats_resume_uuid` explicitly places both
A.jsonl and B.jsonl in the project dir and verifies `uuid == _UUID_A` (session_id wins over
`--resume B`). The discriminating assertion is uuid, not kind (both paths return DIRECT_MATCH).

**`_UUID_RE` anchoring.** The regex (`^[0-9a-f]{8}-...-[0-9a-f]{12}$` + IGNORECASE) is
fully anchored and applied to a lowercased input, so no partial-match path injection is
possible despite `session_id` arriving from an operator-controlled `.live` file.

**EXTRA_ARGS coupling is correct.** The wrapper clears `EXTRA_ARGS=()` for every non-fresh
branch (`--resume/-r`, `--continue/-c`, `-p/--print/--session-id/--bare/--no-session-persistence`),
so the third branch (`EXTRA_ARGS non-empty → CR_SESSION_ID="$SESSION_ID"`) fires only on
genuine fresh interactive sessions. No risk of stamping the generated UUID over a real
resume uuid.

**Tolerant `start_time` parse.** Non-integer `start_time` values yield `None` rather than
raising, preventing an odd/legacy marker from breaking enumeration of all other markers.

## Decision: APPROVED FOR MERGE
