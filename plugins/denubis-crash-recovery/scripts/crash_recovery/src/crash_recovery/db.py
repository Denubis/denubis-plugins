"""SQLite schema, connection helpers, and DB-path resolution for crash-recovery.

This module is the single source of truth for the on-disk schema. Phase 1
seeds the three tables (``sessions``, ``scan_runs``, ``classification_history``);
later phases query these columns by name so the DDL must match the design's
Data Model verbatim.

Boundary validation: ``open_db()`` asserts WAL journal mode is set so callers
never operate on a DB that was created without ``crash-recovery init`` (or one
that was downgraded to ``delete`` mode out-of-band).

``scan_runs.live_pids`` is a JSON-encoded array of integers stored as TEXT;
it is a write-only audit field recorded at scan time and never queried per-element.

``classifier_version`` is denormalised onto ``classification_history`` so the
re-classify-stale-rows query (Phase 4) can detect stale rows without joining
``scan_runs``.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

# Allowed values for the ``classification`` column in both ``sessions`` and
# ``classification_history``.  Defined here so CHECK constraints and the Phase 2
# classifier share one source of truth.
CLASSIFICATION_VALUES: tuple[str, ...] = (
    "live",
    "hard_crash",
    "borderline",
    "concluded",
    "irrecoverable",
)

_CLASSIFICATION_CHECK = (
    "CHECK (classification IN ("
    + ", ".join(f"'{v}'" for v in CLASSIFICATION_VALUES)
    + "))"
)

SESSIONS_DDL = f"""
CREATE TABLE IF NOT EXISTS sessions (
    uuid                  TEXT PRIMARY KEY NOT NULL,
    project_path          TEXT NOT NULL,
    cwd                   TEXT NOT NULL,
    jsonl_path            TEXT,
    jsonl_mtime           INTEGER,
    jsonl_last_ts         INTEGER,
    classification        TEXT NOT NULL,
    classification_reason TEXT,
    classifier_version    INTEGER NOT NULL,
    state_summary         TEXT,
    first_seen            INTEGER NOT NULL,
    last_scanned          INTEGER NOT NULL,
    user_notes            TEXT,
    pane_title            TEXT,
    last_substantive      TEXT,
    {_CLASSIFICATION_CHECK}
)
"""

SCAN_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS scan_runs (
    id                    INTEGER PRIMARY KEY,
    ts                    INTEGER NOT NULL,
    live_pids             TEXT,
    sessions_scanned      INTEGER,
    classifier_version    INTEGER NOT NULL
)
"""

CLASSIFICATION_HISTORY_DDL = f"""
CREATE TABLE IF NOT EXISTS classification_history (
    uuid                  TEXT NOT NULL,
    scan_id               INTEGER NOT NULL,
    classification        TEXT NOT NULL,
    reason                TEXT,
    classifier_version    INTEGER NOT NULL,
    PRIMARY KEY (uuid, scan_id),
    FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE,
    FOREIGN KEY (scan_id) REFERENCES scan_runs(id) ON DELETE RESTRICT,
    {_CLASSIFICATION_CHECK}
)
"""

# Allowed values for ``uncorrelated_markers.reason`` — a closed domain set in
# exactly one place (``scan.py``). Defined here as the single authoritative
# source (project CLAUDE.md, "Schema Constants from Authoritative Source"): the
# CHECK below and the scan-time writer both derive from these names, mirroring
# how ``CLASSIFICATION_VALUES`` backs the ``classification`` CHECK.
MARKER_REASON_DEAD_PID = "dead_pid"
MARKER_REASON_BOOT_MISMATCH = "boot_mismatch"
MARKER_REASON_VALUES: tuple[str, ...] = (
    MARKER_REASON_DEAD_PID,
    MARKER_REASON_BOOT_MISMATCH,
)

_MARKER_REASON_CHECK = (
    "CHECK (reason IN (" + ", ".join(f"'{v}'" for v in MARKER_REASON_VALUES) + "))"
)

# Uncorrelated abnormal-exit markers: a ``.live`` marker whose process is dead
# (or whose boot_id mismatches the current boot) that ``correlate`` could not map
# to any session JSONL. These are NOT sessions — they have no UUID and no
# transcript — so they live in their own table rather than polluting ``sessions``
# with synthetic rows. They are crash evidence the tool must surface rather than
# silently drop (the never-silently-drop principle). Keyed on (boot_id, pid): one
# live marker per pid at a time, and boot_id disambiguates pid reuse across boots.
# ``started`` is NOT NULL: the writer builds the marker from ``liveness.started``,
# a required int key (a malformed marker raises and is skipped upstream), so a
# NULL started is unreachable.
UNCORRELATED_MARKERS_DDL = f"""
CREATE TABLE IF NOT EXISTS uncorrelated_markers (
    boot_id      TEXT NOT NULL,
    pid          INTEGER NOT NULL,
    cwd          TEXT NOT NULL,
    started      INTEGER NOT NULL,
    reason       TEXT NOT NULL,
    last_scanned INTEGER NOT NULL,
    PRIMARY KEY (boot_id, pid),
    {_MARKER_REASON_CHECK}
)
"""

ALL_DDL: tuple[str, ...] = (
    SESSIONS_DDL,
    SCAN_RUNS_DDL,
    CLASSIFICATION_HISTORY_DDL,
    UNCORRELATED_MARKERS_DDL,
)

# Columns added after the initial Phase-1 schema. Each entry is
# ``(name, type-declaration)``.  ``init()`` calls ``_migrate_additive_columns``
# to add any that are absent — a deliberate, operator-invoked upgrade.
# ``open_db()`` asserts these columns are present and refuses (RuntimeError)
# if any are missing, directing the operator to run ``crash-recovery init``.
_ADDITIVE_SESSION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("pane_title", "TEXT"),
    ("last_substantive", "TEXT"),
)


def _migrate_additive_columns(conn: sqlite3.Connection) -> None:
    """Add any missing additive ``sessions`` columns; idempotent and lossless.

    Called ONLY from ``init()`` — the deliberate, operator-invoked upgrade
    command.  It must never be called from ``open_db()`` or any per-command hot
    path (scan, note, prune), which would create a concurrency race where
    multiple concurrent openers each attempt the same ``ADD COLUMN``.

    Guarded by ``PRAGMA table_info`` so re-running is a no-op: a column already
    present is skipped, never re-added. ``ALTER TABLE ADD COLUMN`` appends a
    nullable column without rewriting existing rows, so prior data is retained.
    Column names and type declarations are module constants (never user input),
    so interpolating them into the DDL is safe — bound parameters cannot carry
    DDL identifiers.
    """
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
    }
    for name, decl in _ADDITIVE_SESSION_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} {decl}")


def default_db_path() -> Path:
    """Return the DB path from ``CRASH_RECOVERY_DB`` env or the documented default.

    The env var lets tests and power users redirect the DB without rewriting
    config; the default lives under ``~/.claude/`` next to other plugin state.
    """
    return Path(
        os.environ.get("CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    ).expanduser()


def init(path: Path) -> None:
    """Create the parent directory, open ``path``, apply all DDL, set WAL mode.

    Idempotent by virtue of ``CREATE TABLE IF NOT EXISTS``. The WAL ``PRAGMA``
    is issued before any transaction is opened — SQLite refuses to switch
    journal modes inside a transaction. ``PRAGMA foreign_keys`` is per-connection
    so it is set here for completeness and re-set in ``open_db()``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        # WAL journal-mode change MUST happen outside a transaction.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        for ddl in ALL_DDL:
            conn.execute(ddl)
        _migrate_additive_columns(conn)
        conn.commit()
    finally:
        conn.close()


def open_db(path: Path) -> sqlite3.Connection:
    """Open a connection to ``path``, asserting WAL mode and schema-current state.

    Asserts two preconditions before returning:

    1. WAL journal mode — a DB not in WAL mode was not produced by ``init()``.
    2. Schema-current — all columns in ``_ADDITIVE_SESSION_COLUMNS`` are present
       in the ``sessions`` table.  If any are absent the caller is told to run
       ``crash-recovery init`` to upgrade.

    This function does NOT mutate the schema.  ``ALTER TABLE`` DDL runs only
    from ``init()`` — the deliberate, operator-invoked upgrade command.  Keeping
    DDL out of the per-command hot path avoids the concurrency race that arises
    when multiple openers each attempt the same ``ADD COLUMN``.

    The caller owns the returned connection and must close it.
    """
    conn = sqlite3.connect(path)
    mode_row = conn.execute("PRAGMA journal_mode").fetchone()
    mode = (mode_row[0] if mode_row else "").lower()
    if mode != "wal":
        conn.close()
        raise RuntimeError(
            f"crash-recovery DB at {path} is not in WAL mode;"
            " re-run `crash-recovery init`"
        )
    conn.execute("PRAGMA foreign_keys = ON")
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
    }
    missing = [name for name, _ in _ADDITIVE_SESSION_COLUMNS if name not in existing]
    if missing:
        conn.close()
        raise RuntimeError(
            f"crash-recovery DB at {path} is missing migrated columns "
            f"({', '.join(missing)}); run `crash-recovery init` to upgrade"
        )
    # Schema-current also requires the uncorrelated_markers table (added after
    # the initial schema). Same deliberate-upgrade contract as the additive
    # columns: open_db refuses rather than creating it on a hot path.
    has_markers_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='uncorrelated_markers'"
    ).fetchone()
    if has_markers_table is None:
        conn.close()
        raise RuntimeError(
            f"crash-recovery DB at {path} is missing the uncorrelated_markers "
            f"table; run `crash-recovery init` to upgrade"
        )
    return conn


def _schema_hash(conn: sqlite3.Connection) -> str:
    """Test-time helper. Returns SHA-256 hex of (name, sql) pairs from sqlite_master.

    Rows are ordered by ``name`` and joined by null bytes for a deterministic
    digest. Used by ``test_init_is_idempotent`` to assert that re-running
    ``init()`` against an existing DB does not perturb the schema.

    Not a production invariant — no runtime code compares ``_schema_hash()``
    against a stored baseline. The leading underscore marks this as a
    module-private helper consumed only by tests.
    """
    rows = conn.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
    digest = hashlib.sha256()
    for name, sql in rows:
        digest.update((name or "").encode("utf-8"))
        digest.update(b"\x00")
        digest.update((sql or "").encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()
