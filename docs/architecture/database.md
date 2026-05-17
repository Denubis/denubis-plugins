# Database Architecture — denubis-crash-recovery

## Universe of Discourse

The crash-recovery database (`~/.claude/crash-recovery.db`, override via `CRASH_RECOVERY_DB`) records the state of Claude Code sessions and their classifications across scanner runs. A session is a single invocation of `claudew` — identified by its UUID — that may have ended cleanly, crashed, or still be running. The database is the source of truth: `~/llm-resume.md` is a regenerated view of database state and is never edited directly.

## Tables

Source file: `crash_recovery/db.py`. DDL constants: `db.py::SESSIONS_DDL`, `db.py::SCAN_RUNS_DDL`, `db.py::CLASSIFICATION_HISTORY_DDL`.

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

## Relationships

- `classification_history.uuid` → `sessions.uuid` **ON DELETE CASCADE**: deleting a session row removes all its history. This is the Phase 6 `prune` behaviour — `prune` deletes from `sessions` and the cascade cleans up history automatically. Source: `db.py::CLASSIFICATION_HISTORY_DDL`.

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

The rendered markdown output groups sessions into sections whose headings combine classification and reason (e.g. `borderline+ambiguous_match`, `borderline+malformed_tail`). These compound section keys are a rendering concept only — they are derived at render time from `(classification, reason)` tuples stored in separate columns. The DB stores only the bare classification value; the `reason` column holds the distinguishing reason string.

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

## Schema Migration Strategy

Schema changes are coupled to `CLASSIFIER_VERSION` (defined in Phase 2's `crash_recovery/classify.py`). When a future classifier_version introduces a new classification value:

1. Add the new value to `db.py::CLASSIFICATION_VALUES`.
2. Provide an `ALTER TABLE` migration that recreates the CHECK constraint from the updated `_CLASSIFICATION_CHECK`. SQLite supports CHECK changes only via table-rebuild (create temp table with the new CHECK, copy rows, drop original, rename) — `init()` is not the migration mechanism.
3. Bump `CLASSIFIER_VERSION`; existing rows stamped with the old version are flagged stale by Phase 4's orphan sweep and re-classified on next `scan`.
4. `_schema_hash()` will change after the migration — that's expected. It's a test-time helper (underscore prefix marks it module-private), not a production invariant; only the idempotency test in `tests/test_init.py` consults it, and a migration test should treat `_schema_hash` as a fingerprint that changes when the schema changes (which is the desired behaviour).

`init()` itself remains idempotent across re-runs of the same schema version. Migrations are a separate code path tied to version bumps and live alongside the version that introduces them.

**Known v0.1.0 gap (CLASSIFIER_VERSION ↔ CHECK decoupling)**: `classifier_version` is logically coupled to the CHECK list — a future version may introduce new values — but the schema does not enforce that coupling. A row with `(classifier_version=1, classification="value_only_valid_in_v2")` would pass the CHECK as long as the value is in `CLASSIFICATION_VALUES` at write time. Only the classifier code prevents this. Accepted because nothing in v0.1.0 produces rows of that shape; the orphan sweep + classifier rule table together preserve the invariant in practice.

## Future Tuning (Explicit Non-Goals for v0.1.0)

**Secondary indexes:** At current expected scale (hundreds to thousands of sessions), no secondary indexes are needed. Full-table scans on `sessions` and `classification_history` are fast. Revisit at 100k+ rows using `EXPLAIN QUERY PLAN` on the Phase 4 stale-row query and the Phase 6 prune query.

**`PRAGMA synchronous`:** The default (`FULL`) is appropriate for a personal-use DB where losing the most recent scan would require a re-scan (fast, non-destructive). `PRAGMA synchronous = NORMAL` is an option for write-heavy workloads where that trade-off is acceptable. Not set in v0.1.0.
