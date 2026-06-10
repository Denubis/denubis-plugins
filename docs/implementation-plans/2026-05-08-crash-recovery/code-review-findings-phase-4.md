# Code Review Findings — phase-4

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification

```
Tests (module): uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest tests/ -q → 457 passed
Tests (full repo): uv run pytest -q → 716 passed (up from 715; one new test added)
Lint: uv tool run ruff check src/ tests/ → All checks passed
```

## Prior Findings Verification

### Important #1 — live_pids fixture collision: RESOLVED

The original test `test_scan_writes_scan_runs_with_live_pids` has been simplified to one live session and one crashed session. The docstring now explicitly states the deduplication path is not exercised here and cross-references the new test. The second `FixtureSession` with `pid_alive=True` (uuid `22222222-...`) has been removed from the fixture list.

A new test `test_run_scan_deduplicates_live_pids_across_facts` monkey-patches `scan_mod._walk_sessions` to inject two `SessionFact` objects sharing `liveness.pid=12345` and `pid_alive_value=True`. The test asserts `live_pids == [12345]`. This correctly exercises the `sorted({fact.liveness.pid for fact in facts if ...})` set comprehension in `run_scan`: the set collapses both `12345` entries to one before sorting. The test would fail with `[12345, 12345]` if the set were replaced with a list — the structural regression guard is genuine.

The new test also calls through to `_classify_fact` with `liveness is not None`, `pid_alive_value=True`, and `boot_id_current=True` — `LivenessState(present=True, boot_id_current=True)` — which hits the `classify()` path without triggering the ValueError boundary guard. The test writes a real DB row and reads it back. No mock-only verification.

Evidence: `tests/test_scan.py:412–452` (simplified integration test); `tests/test_scan.py:455–527` (new dedup test); `src/crash_recovery/scan.py:493–499` (production set comprehension).

### Minor #1 — private import inside function body: RESOLVED

`from crash_recovery.correlate import _project_dir_for_cwd` has been hoisted to the module-level import block at `src/crash_recovery/scan.py:32`, alongside the existing `correlate` import. The in-function import at line 146 (pre-fix) is gone.

Evidence: `src/crash_recovery/scan.py:32` — `from crash_recovery.correlate import CorrelationKind, _project_dir_for_cwd, correlate`.

### Minor #2 — CLI summary missing "(orphans/version-stale)" qualifier: RESOLVED

The format string at `src/crash_recovery/__main__.py:115` now reads `re-classified (orphans/version-stale);`, matching the plan's Task 4 spec exactly.

Evidence: `src/crash_recovery/__main__.py:115`.

## Plan Alignment

All ACs from the prior review remain satisfied. No plan requirements were touched by the fix commits. No new deviations introduced.

## Issues

None.

## Decision: APPROVED FOR MERGE

All three prior findings are resolved. No new issues introduced by the fixes. The new dedup test is structurally sound: it exercises the production set-comprehension path end-to-end (real DB write, real read-back), the structural regression guard is genuine, and the simplified integration test's docstring accurately describes what it now tests.
