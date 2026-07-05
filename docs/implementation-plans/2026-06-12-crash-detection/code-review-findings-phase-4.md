# Code Review Findings — phase-4

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification

```
Tests: uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q → 256 passed in 2.87s
Bats:  bats tests/ → 70 tests, exit 0
```

## Prior Findings Verification

### Important (prior cycle) — stale docs under old section name

- **Status: Resolved.**
- Evidence (this diff):
  - `docs/architecture/glossary.md` line 45: `IDLE_LIVE_KILLED` → `PROBABLE_CRASH_VICTIMS`; doc note updated to flag that SECTIONS tuple — not the enum declaration order — sets document order.
  - `docs/architecture/database.md` lines 20–32: section list reordered to place `Probable system-crash victims` first; "planned" qualifier and stale `Idle-live killed` reference both removed; additive-migration paragraph rewritten to describe the init-only DDL + open_db assertion contract (matches shipped code).
  - `plugins/denubis-crash-recovery/skills/triage/SKILL.md` lines 2146 and 2155: both section-name references updated.
  - `plugins/denubis-crash-recovery/README.md` lines 108 and 117: UAT walkthrough lines updated.

### Minor (prior cycle) — ON CONFLICT UPDATE path untested for new columns

- **Status: Resolved.**
- Evidence: `test_rescan_refreshes_pane_title_and_last_substantive` (test_scan.py lines 1709–1838 in the diff) scans the same session twice with changed inputs between scans and asserts the second scan's `pane_title` and `last_substantive` land in the DB, overwriting the first scan's values. The mutation check (B ≠ A, Y ≠ X) gives the test real teeth.

### DBA M2 (prior cycle) — no schema_version / duplicated table_info probes

- **Status: Deferred by maintainer.** Not re-raised.

## Plan Alignment

- **AC7.1 (reworded)** — `init()` migrates old-shape DB without data loss; re-run is a no-op; `open_db()` refuses un-migrated DB (RuntimeError → `crash-recovery init`), schema left untouched: ✓ Three new tests (`test_init_migrates_old_shape_without_data_loss`, `test_open_db_does_not_migrate_and_refuses_unmigrated_db`, `test_scan_refuses_unmigrated_db_with_clean_error`) cover all three branches. `open_db()` implementation: `PRAGMA table_info` read → missing column list → close + RuntimeError; no ALTER TABLE call on the hot path anywhere in the diff.
- **AC7.2** — fresh `init()` creates columns from DDL: ✓ `test_fresh_init_creates_new_columns` unchanged from prior cycle.
- **AC7.3** — render on un-migrated DB does not raise: ✓ `test_render_old_shape_db_does_not_raise` unchanged from prior cycle; render bypasses `open_db()` entirely and uses defensive `NULL AS pane_title` / `NULL AS last_substantive` SELECT.
- **AC1.2, AC5.1, AC5.2, AC5.3** — carry-forward from prior cycle, all still passing.

## New-Issue Hunt (fix cycle scope)

The prompt asked focused investigation of two questions:

**1. Does the `open_db` schema-current assertion harm legitimate callers?**

`note`, `prune`, and `scan` all call `open_db`. On an un-migrated DB they now fail with a RuntimeError before touching any data. This is coherent: the prior contract was "run `init` first"; the new contract adds "and re-run `init` after a Phase-4 upgrade." `render()` intentionally bypasses `open_db` and opens a direct read-only connection — AC7.3 graceful degradation is structurally preserved and tested. There is no caller that legitimately has a migrated WAL DB but missing Phase-4 columns; the only path to that state is skipping `init` after upgrade, and the RuntimeError message directs the operator exactly there.

One real-world nuance: an operator who upgrades the plugin without re-running `init` will see `crash-recovery scan` (or `note`, `prune`) raise `RuntimeError` while `crash-recovery triage` (render) continues to work silently with `NULL` new fields. This asymmetry is intentional and documented. The test `test_scan_refuses_unmigrated_db_with_clean_error` pins the clean-error shape.

**2. Does DDL run anywhere except `init()`?**

Confirmed. `_migrate_additive_columns` is defined in `db.py` and called in exactly one place: `init()` (diff line 176). No call site in `open_db`, `scan`, `scan_db`, `render`, `note`, or `prune`. The doc-string on `_migrate_additive_columns` explicitly prohibits hot-path calls. The `open_db` implementation contains only `PRAGMA table_info` reads and a conditional `conn.close() + raise`; no `ALTER TABLE` anywhere on the hot path.

## Issues

None.

## Decision: APPROVED FOR MERGE

All prior findings are resolved. Both gates pass (256 pytest, 70 bats). The init-only DDL design is coherent, the open_db assertion contract is sound and tested, DDL is confirmed absent from the hot path, and AC7.3 graceful read-only degradation is structurally intact via render's independent connection. No new issues introduced by the fix cycle.
