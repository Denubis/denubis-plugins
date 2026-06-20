# Database Architecture — denubis-crash-recovery

## Universe of Discourse

The crash-recovery database (`~/.claude/crash-recovery.db`, override via `CRASH_RECOVERY_DB`) records the state of Claude Code sessions and their classifications across scanner runs. A session is a single invocation of `claudew` — identified by its UUID — that may have ended cleanly, crashed, or still be running. The database is the source of truth: `~/llm-resume.md` is a regenerated view of database state and is never edited directly.

## Tables

Source file: `crash_recovery/db.py`. DDL constants: `db.py::SESSIONS_DDL`, `db.py::SCAN_RUNS_DDL`, `db.py::CLASSIFICATION_HISTORY_DDL`, `db.py::UNCORRELATED_MARKERS_DDL`.

### sessions

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| uuid | TEXT | PRIMARY KEY NOT NULL | Claude session UUID. NOT NULL declared explicitly — SQLite does not enforce NOT NULL on TEXT PRIMARY KEY by default (documented quirk). |
| project_path | TEXT | NOT NULL | Decoded `~/.claude/projects/<encoded>/` path. |
| cwd | TEXT | NOT NULL | Working directory used for `claudew --resume`. |
| jsonl_path | TEXT | | Absolute path to session JSONL; NULL if no JSONL ever written. |
| jsonl_mtime | INTEGER | | Unix epoch of last JSONL modification; used for cache invalidation. |
| jsonl_last_ts | INTEGER | | Timestamp of the last entry inside the JSONL. |
| classification | TEXT | NOT NULL, CHECK | Allowed values defined in `db.py::CLASSIFICATION_VALUES`. |
| classification_reason | TEXT | | Short machine-generated reason string. |
| classifier_version | INTEGER | NOT NULL | Version of the rule table used. `scan` re-classifies rows whose stored version is below the current `CLASSIFIER_VERSION`. |
| state_summary | TEXT | | One-line render of the last few JSONL entries. |
| first_seen | INTEGER | NOT NULL | Unix epoch when this plugin first indexed the session. |
| last_scanned | INTEGER | NOT NULL | Unix epoch of the last `scan` that touched this row. |
| user_notes | TEXT | | User-owned annotation; preserved across regen via `crash-recovery note`. |
| pane_title | TEXT | | tmux-resurrect window-title slug (`✳ …`) for the session's pane; render display label. Added by additive migration via `init()`, NULL on legacy rows (`docs/design-plans/2026-06-12-crash-detection.md`, DR7). |
| last_substantive | TEXT | | Last real human/assistant text from the JSONL, skipping content-level bookkeeping; render display field (`docs/design-plans/2026-06-12-crash-detection.md`, DR7). Added by additive migration via `init()`, NULL on legacy rows. |

### scan_runs

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | INTEGER | PRIMARY KEY | Auto-increment scan identifier. |
| ts | INTEGER | NOT NULL | Unix epoch when the scan started. |
| live_pids | TEXT | | JSON-encoded array of integers — PIDs alive at scan time. Write-only audit field; never queried per-element. Stored as TEXT for pragmatic simplicity (see Denormalisation Rationale). |
| sessions_scanned | INTEGER | | Count of sessions processed in this scan. |
| classifier_version | INTEGER | NOT NULL | Rule-table version active during this scan. Denormalised onto `classification_history` rows so stale-row detection can skip a join (see Denormalisation Rationale). |

### classification_history

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| uuid | TEXT | NOT NULL | References `sessions.uuid`. |
| scan_id | INTEGER | NOT NULL | References `scan_runs.id`. |
| classification | TEXT | NOT NULL, CHECK | Same allowed values as `sessions.classification` (`db.py::CLASSIFICATION_VALUES`). |
| reason | TEXT | | Classification reason at the time of this scan. |
| classifier_version | INTEGER | NOT NULL | Denormalised from `scan_runs.classifier_version` (see Denormalisation Rationale). |
| (uuid, scan_id) | — | PRIMARY KEY | Composite key; one row per session per scan. |

**Dedup invariant (write-side protection of this PK):** `scan` writes at most one `classification_history` row per `(uuid, scan_id)` because `_walk_sessions` deduplicates facts by UUID before the write loop. Once correlation succeeds, two `.live` markers can resolve to one UUID; without the dedup the second insert would violate this composite primary key and crash `triage`. The retained fact is chosen by precedence rank (exact > window > ambiguous-candidate), then live-over-dead, then sorted liveness path (design DR5/DR10). Source: `scan.py::_walk_sessions`. Pinned by `tests/test_scan.py::test_scan_dedup_two_markers_same_uuid_no_integrity_error` and `::test_scan_dedup_same_rank_live_beats_dead_order_independent`.

### uncorrelated_markers

A `.live` marker whose process has abnormally exited (dead PID, or a `boot_id` that no longer matches the current boot) that `correlate` could **not** map to any session JSONL. These are not sessions — no UUID, no transcript — so they live in their own table rather than as synthetic rows in `sessions` (which would distort prune, note, and the session count). They are crash evidence the tool must surface rather than silently drop (the never-silently-drop principle that motivated the 2026-06-12 overhaul). Source: `db.py::UNCORRELATED_MARKERS_DDL`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| boot_id | TEXT | NOT NULL | Kernel boot_id recorded in the marker. Part of the PK. |
| pid | INTEGER | NOT NULL | Marker filename PID. Part of the PK — one live marker per PID at a time; `boot_id` disambiguates PID reuse across boots. |
| cwd | TEXT | NOT NULL | Working directory from the marker; the only human anchor for an uncorrelated marker. |
| started | INTEGER | NOT NULL | Unix epoch the session started (from the marker). NOT NULL — the writer builds the marker from `liveness.started`, a required int key (a malformed marker raises and is skipped upstream by `list_liveness_files`), so a NULL `started` is unreachable. Rendered as the "Started" line. |
| reason | TEXT | NOT NULL, CHECK | Why it is abnormal-exit evidence. Closed domain enforced by a CHECK generated from `db.py::MARKER_REASON_VALUES` (`"dead_pid"`, `"boot_mismatch"`) — the same single-source-of-truth pattern as `classification`. The scan-time writer (`scan.py::_walk_sessions`) sets it from the `db.MARKER_REASON_*` constants. |
| last_scanned | INTEGER | NOT NULL | Unix epoch of the scan that recorded this marker. |
| (boot_id, pid) | — | PRIMARY KEY | Composite key. |

**Full-replace write model:** `run_scan` does `DELETE FROM uncorrelated_markers` then re-inserts the current abnormal NO_MATCH set inside the same transaction. Because these rows have no UUID, no `classification_history`, and no foreign keys, a full replace each scan keeps the table free of stale rows without a dedicated orphan sweep. Only NO_MATCH markers that are *abnormal* are recorded — a live-PID marker on the current boot is a running session whose transcript was simply not located yet and is left out. Source: `scan.py::run_scan`, `scan.py::_walk_sessions`. Pinned by `tests/test_scan.py::test_scan_records_uncorrelated_dead_marker` and `::test_scan_does_not_record_uncorrelated_live_marker`.

## Relationships

- `classification_history.uuid` → `sessions.uuid` **ON DELETE CASCADE**: deleting a session row removes all its history. This is the Phase 6 `prune` behaviour — `prune` deletes from `sessions` and the cascade cleans up history automatically. Source: `db.py::CLASSIFICATION_HISTORY_DDL`. Phase 6's `prune` exercises this cascade for the first time in production code; the cascade is tested by `tests/test_prune.py::test_prune_cascades_classification_history_deletion`.

- `classification_history.scan_id` → `scan_runs.id` **ON DELETE RESTRICT**: scan_runs rows are never deleted in normal operation. RESTRICT documents this intent structurally — any future retention feature must consciously address existing history before removing a scan_runs row. Source: `db.py::CLASSIFICATION_HISTORY_DDL`.

## Persistent Invariants

### WAL journal mode

Set once by `db.py::init`, outside any transaction. SQLite requires journal-mode changes to occur outside a transaction; `init` issues `PRAGMA journal_mode = WAL` before opening any transaction. WAL mode is persistent — it survives reconnects. `db.py::open_db` asserts WAL mode on every connection to guard against out-of-band downgrade.

### PRAGMA foreign_keys = ON

SQLite does not enable foreign key enforcement by default. It is a per-connection setting. Both `db.py::init` and `db.py::open_db` execute `PRAGMA foreign_keys = ON` to ensure enforcement is active for every connection that writes or reads the schema. Source: `db.py::init`, `db.py::open_db`.

### Classification values

Allowed values for `sessions.classification` and `classification_history.classification` are defined in `db.py::CLASSIFICATION_VALUES`:

```
"live", "hard_crash", "borderline", "concluded", "irrecoverable"
```

Both `SESSIONS_DDL` and `CLASSIFICATION_HISTORY_DDL` reference this constant to generate their CHECK constraints. Phase 2's `classify` module re-exports this constant so the classifier and the schema share one source of truth.

The rendered markdown output groups sessions into fixed sections in document order, each backed by a `SectionKey` StrEnum value (`render.py::SectionKey`): `Probable system-crash victims`, `Currently unfinished`, `Ambiguous correlation`, `Needs investigation`, `Recently concluded`, `Irrecoverable`. The `Probable system-crash victims` section leads the report — `hard_crash` rows route there — with the full roster preserved below, all-means-all (`docs/design-plans/2026-06-12-crash-detection.md`, DR9 / Phase 4). Section assignment is a pure function of `(classification, classification_reason)` performed by `_section_for_row` at render time; the DB stores only the bare classification value and the distinguishing reason string in separate columns. See `glossary.md` for the `SectionKey`, `Section`, and `SECTIONS` entries.

One supplementary section, `Uncorrelated crash markers`, is appended after the six session sections **only when the `uncorrelated_markers` table holds rows** (it is evidence, not a roster, so an empty report omits it entirely rather than printing an empty header). It is sourced from `uncorrelated_markers`, not `sessions`, and carries no `claudew --resume` line — there is nothing to resume. Source: `render.py::render`, `render.py::_render_marker`.

The `borderline/liveness_dead_pid_concluded_tail` reason (classifier v2) names the "finished a turn, then the process was killed" case — a live marker, dead PID, current boot, but a concluded tail. It routes to `Needs investigation` with a calm explanation rather than the generic `unmatched` "Something fucky" review-queue prompt, which is now a defensive-only fallback reachable by no realistic input. Source: `classify.py::RULES`, `render.py::_reduced_confidence_text`.

### Scan transaction model

`run_scan` opens one SQLite connection via `db.open_db()` and wraps its entire write block in a single `with conn:` transaction. Inside that transaction, in order:

1. `_write_scan_run(conn, ctx, sessions_scanned, live_pids)` inserts the `scan_runs` row first so the returned rowid is available for `classification_history` appends.
2. For each `SessionFact` from the read-only filesystem walk: `_upsert_session(conn, fact, classification, ctx, run_id)` performs the `INSERT … ON CONFLICT(uuid) DO UPDATE` and (conditionally, when classification changed) `_append_history(conn, fact.uuid, run_id, classification)` writes the history row.
3. `_orphan_sweep(conn, ctx, run_id, seen_uuids)` iterates `sessions` rows not seen in the walk and applies the same update + conditional history-append pattern.

On any uncaught exception the entire transaction rolls back atomically: no `scan_runs` row, no partial `sessions` updates, no orphan `classification_history` entries. WAL mode (set by `db.py::init`) admits concurrent readers throughout; concurrent `scan` invocations serialize at the SQLite write lock, both completing successfully with one `scan_runs` row each (the default 5s busy timeout absorbs the contention). Source: `scan.py::run_scan`. Atomicity pin: `tests/test_scan.py::test_scan_atomic_on_simulated_failure`. Concurrency pin: `tests/test_scan.py::test_scan_two_concurrent_invocations_do_not_corrupt_db`.

## Denormalisation Rationale

**`scan_runs.live_pids` stored as JSON TEXT** (`db.py::SCAN_RUNS_DDL`): This column is a write-only audit field capturing the PID snapshot at scan time. No query ever filters or aggregates on individual PIDs. Storing as a JSON-encoded TEXT array is pragmatic — it avoids a separate `scan_live_pids` junction table for a field that is read back only as a whole blob (if at all).

**`classifier_version` on `classification_history`** (`db.py::CLASSIFICATION_HISTORY_DDL`): Denormalised from `scan_runs`. The Phase 4 stale-row detection query — "find all history rows whose `classifier_version` is below the current constant" — can be expressed as a single-table scan without joining `scan_runs`. This keeps the query simple and avoids an index on a join column for what is expected to be a common operation (every scan checks for stale rows).

## Concurrency Model

SQLite WAL mode serialises concurrent writers at the database level. The design's concurrent-scan model (two simultaneous `crash-recovery scan` invocations) relies on this: each scan acquires a write lock for its `scan_runs` INSERT and subsequent `classification_history` INSERTs. WAL readers are never blocked by writers. The Phase 4 `_write_scan_run` function and the Phase 6 `prune` command both wrap their mutations in transactions; any FK CASCADE (uuid delete → history delete) fires inside the transaction boundary.

## Constraint Summary

| Constraint | Table | Column | Type | Declared? |
|-----------|-------|--------|------|-----------|
| PRIMARY KEY | sessions | uuid | PK | Yes |
| NOT NULL | sessions | uuid | NOT NULL | Yes — explicit (SQLite quirk) |
| CHECK (classification) | sessions | classification | CHECK | Yes — via `CLASSIFICATION_VALUES` |
| PRIMARY KEY | scan_runs | id | PK | Yes |
| PRIMARY KEY | classification_history | (uuid, scan_id) | Composite PK | Yes |
| FK → sessions(uuid) ON DELETE CASCADE | classification_history | uuid | FK | Yes |
| FK → scan_runs(id) ON DELETE RESTRICT | classification_history | scan_id | FK | Yes |
| CHECK (classification) | classification_history | classification | CHECK | Yes — via `CLASSIFICATION_VALUES` |
| PRIMARY KEY | uncorrelated_markers | (boot_id, pid) | Composite PK | Yes |
| NOT NULL | uncorrelated_markers | boot_id, pid, cwd, started, reason, last_scanned | NOT NULL | Yes — all columns (only the PK members are implicitly required; the rest explicit) |
| CHECK (reason) | uncorrelated_markers | reason | CHECK | Yes — via `MARKER_REASON_VALUES` |

## Schema Migration Strategy

Schema changes are coupled to `CLASSIFIER_VERSION` (defined in Phase 2's `crash_recovery/classify.py`). When a future classifier_version introduces a new classification value:

1. Add the new value to `db.py::CLASSIFICATION_VALUES`.
2. Provide an `ALTER TABLE` migration that recreates the CHECK constraint from the updated `_CLASSIFICATION_CHECK`. SQLite supports CHECK changes only via table-rebuild (create temp table with the new CHECK, copy rows, drop original, rename) — `init()` is not the migration mechanism.
3. Bump `CLASSIFIER_VERSION`; existing rows stamped with the old version are flagged stale by Phase 4's orphan sweep and re-classified on next `scan`.
4. `_schema_hash()` will change after the migration — that's expected. It's a test-time helper (underscore prefix marks it module-private), not a production invariant; only the idempotency test in `tests/test_init.py` consults it, and a migration test should treat `_schema_hash` as a fingerprint that changes when the schema changes (which is the desired behaviour).

`init()` itself remains idempotent across re-runs of the same schema version. CHECK-changing migrations are a separate code path tied to version bumps and live alongside the version that introduces them.

**Additive-column migrations (`docs/design-plans/2026-06-12-crash-detection.md`, DR7).** The above strategy governs CHECK-constraint changes (new classification values), which SQLite only supports via table-rebuild and which couple to `CLASSIFIER_VERSION`. Adding a *nullable* column is a simpler, orthogonal class: an idempotent `ALTER TABLE ADD COLUMN` guarded by `PRAGMA table_info`, fired exclusively from `init()` — the deliberate, operator-invoked upgrade command. It is **not** coupled to `CLASSIFIER_VERSION` because a display-only column does not change classification semantics or trigger stale-row reclassification. `pane_title` and `last_substantive` are the first columns added this way.

`open_db()` asserts that all additive columns are present **and that the `uncorrelated_markers` table exists**, raising `RuntimeError` (directing the operator to run `crash-recovery init`) if either is absent. It does **not** run `ALTER TABLE` or `CREATE TABLE` — keeping DDL off the per-command hot path avoids the concurrency race that arises when multiple concurrent openers each attempt the same migration. The `uncorrelated_markers` table is created by `init()` via `CREATE TABLE IF NOT EXISTS` (idempotent), the same deliberate-upgrade contract as the additive columns. `render()` opens read-only via `file:{db}?mode=ro` and bypasses `open_db()` entirely; it checks `PRAGMA table_info` and selects absent columns as `NULL`, and checks `sqlite_master` before reading `uncorrelated_markers` — a render-only call on a not-yet-migrated DB must not raise `no such column` or `no such table` (AC7.3).

**`CLASSIFIER_VERSION` is 2** as of 2026-06-20: bumped per the convention when the `liveness_dead_pid_concluded_tail` rule was added (a rule-table shape change, not a new CHECK value). The bump stamps the ruleset version onto rows and re-considers version-stale orphans; it is **not** the mechanism that migrates existing data. An on-disk session is re-derived from its tail + liveness on every `scan` via `_upsert_session`, so a row stored `borderline/unmatched` by v1 picks up the calm reason on the next scan through the normal walk regardless of the version stamp.

**Known v0.1.0 gap (CLASSIFIER_VERSION ↔ CHECK decoupling)**: `classifier_version` is logically coupled to the CHECK list — a future version may introduce new values — but the schema does not enforce that coupling. A row with `(classifier_version=1, classification="value_only_valid_in_v2")` would pass the CHECK as long as the value is in `CLASSIFICATION_VALUES` at write time. Only the classifier code prevents this. Accepted because nothing in v0.1.0 produces rows of that shape; the orphan sweep + classifier rule table together preserve the invariant in practice.

## Future Tuning (Explicit Non-Goals for v0.1.0)

**Secondary indexes:** At current expected scale (hundreds to thousands of sessions), no secondary indexes are needed. Full-table scans on `sessions` and `classification_history` are fast. Revisit at 100k+ rows using `EXPLAIN QUERY PLAN` on the Phase 4 stale-row query and the Phase 6 prune query.

**`PRAGMA synchronous`:** The default (`FULL`) is appropriate for a personal-use DB where losing the most recent scan would require a re-scan (fast, non-destructive). `PRAGMA synchronous = NORMAL` is an option for write-heavy workloads where that trade-off is acceptable. Not set in v0.1.0.
