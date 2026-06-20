# Code Review Findings — phase-3

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification

```
Tests: uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q → 234 passed in 2.39s
Lint: no linter configured (ruff absent from project)
bats: 36 ok (prior cycle; no bats-touching changes in this diff)
```

Test count rose from 233 → 234, confirming the new M2 test is exercised.

## Prior Findings Verification

### M1 — AC6.4 criterion wording contradicts the implementation

**Status: Resolved.**

`phase_03.md` line 23 (confirmed in diff): AC6.4 now reads "collects all pane cwds for path-based corroboration (NOT by command or the volatile `✳`/spinner glyph — see the glyph-volatility note below), and selects the latest snapshot at/just before `started`. The `✳` prefix is used only to pick the best *label* among same-cwd panes, never as a corroboration gate." The false `claude`/`✳` filter claim is gone. The reword is accurate and complete.

### M2 — `--resurrect-dir` / env-var resolution untested

**Status: Resolved.**

`test_resurrect_dir_env_var_is_consumed_end_to_end` added to `test_scan.py`. It drives `crash-recovery scan` via `subprocess` (the real `_resolve` path), sets `CRASH_RECOVERY_RESURRECT_DIR` in the subprocess environment, and verifies the full chain: env var → `_resolve` → `ScanContext.resurrect_dir` → `_walk_sessions` → corroboration result. Discrimination is baked in: empty dir → both candidates `borderline/ambiguous_match`; corroborating dir with one pane at cwd A → A resolves to `hard_crash`. Both assertions run in the same test function against the same DB, so order-dependency between the two subprocess invocations is intentional (the first scan inserts rows; the second scan reclassifies them — consistent with the existing idempotency model). No issue with this pattern; it matches how the prior integration tests exercise rescan behaviour.

### M3 — `_ts_from_filename` local-TZ assumption

**Status: Accepted (operator decision, prior cycle).** No change made or required.

## Plan Alignment

All plan alignment carried forward from prior cycle; no plan-touching changes in this diff beyond the AC6.4 reword already verified above.

- AC6.4: ✓ reworded to match the correct all-panes implementation.
- AC9 (full pytest + bats green): ✓ 234 passed; bats 36 ok.

## Issues

None.

## Decision: APPROVED FOR MERGE

## Disposition (orchestrator + operator, 2026-06-17)

Operator reviewed all three Minor findings (not batch-fixed; discussed per-level per project policy). Decision: **fix M1 + M2, accept M3.**

- **Minor 1 — RESOLVED (doc).** AC6.4 in `phase_03.md` line 23 reworded to remove the false `claude`/`✳` gate claim. Criterion now matches the correct path-based all-panes implementation and points at the glyph-volatility note. Commit e0aec47.
- **Minor 2 — RESOLVED (test).** `test_resurrect_dir_env_var_is_consumed_end_to_end` drives the CLI via subprocess with `CRASH_RECOVERY_RESURRECT_DIR` set, exercises the full env-var → `ScanContext.resurrect_dir` → `_walk_sessions` chain, and discriminates via empty vs. corroborating snapshot dir. 234 tests pass. Commit 6dc77da.
- **Minor 3 — ACCEPTED.** Local-TZ interpretation in `_ts_from_filename` is correct (matches tmux-continuum's writer). Already documented in the module docstring. No defect; no change required.
