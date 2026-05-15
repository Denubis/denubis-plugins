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

ALL_DDL: tuple[str, ...] = (SESSIONS_DDL, SCAN_RUNS_DDL, CLASSIFICATION_HISTORY_DDL)


def default_db_path() -> Path:
    """Return the DB path from ``CRASH_RECOVERY_DB`` env or the documented default.

    The env var lets tests and power users redirect the DB without rewriting
    config; the default lives under ``~/.claude/`` next to other plugin state.
    """
    return Path(os.environ.get("CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")).expanduser()


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
        conn.commit()
    finally:
        conn.close()


def open_db(path: Path) -> sqlite3.Connection:
    """Open a connection to ``path``, asserting WAL mode and enabling FK enforcement.

    Defensive boundary: a DB that is not in WAL mode was not produced by
    ``init()``. Surfacing this as a ``RuntimeError`` here keeps every downstream
    caller (scan, render, note, prune) from having to re-check.

    The caller owns the returned connection and must close it.
    """
    conn = sqlite3.connect(path)
    mode_row = conn.execute("PRAGMA journal_mode").fetchone()
    mode = (mode_row[0] if mode_row else "").lower()
    if mode != "wal":
        conn.close()
        raise RuntimeError(
            f"crash-recovery DB at {path} is not in WAL mode; re-run `crash-recovery init`"
        )
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def schema_hash(conn: sqlite3.Connection) -> str:
    """Test-time helper. Returns SHA-256 hex of (name, sql) pairs from sqlite_master.

    Rows are ordered by ``name`` and joined by null bytes for a deterministic
    digest. Used by ``test_init_is_idempotent`` to assert that re-running
    ``init()`` against an existing DB does not perturb the schema.

    Not a production invariant — no runtime code compares ``schema_hash()``
    against a stored baseline.
    """
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master ORDER BY name"
    ).fetchall()
    digest = hashlib.sha256()
    for name, sql in rows:
        digest.update((name or "").encode("utf-8"))
        digest.update(b"\x00")
        digest.update((sql or "").encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()
