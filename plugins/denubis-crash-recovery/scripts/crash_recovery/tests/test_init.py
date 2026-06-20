"""Tests for db.init and the ``crash-recovery init`` subcommand.

Covers AC2.3 (schema created) and AC2.4 (idempotent re-runs). Tests touch
real SQLite — no mocks — because correctness depends on actual SQLite
behaviour (WAL mode, PRAGMA enforcement, IF NOT EXISTS semantics).
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from crash_recovery import db

if TYPE_CHECKING:
    from pathlib import Path

# Columns documented in the design's Data Model. Each tuple is
# ``(name, type, notnull)`` where ``notnull`` is 1 if the column is NOT NULL.
# PRAGMA table_info returns rows shaped as
# (cid, name, type, notnull, dflt_value, pk); we project the three we care
# about. SQLite does NOT enforce NOT NULL on TEXT PRIMARY KEY by default
# (documented quirk: only INTEGER PRIMARY KEY is implicitly NOT NULL).
# We explicitly declare NOT NULL on ``uuid`` *because of* this quirk, to make
# the invariant visible in the schema and enforceable by the DB engine.
# As a result ``uuid`` shows notnull=1 in PRAGMA table_info.
_EXPECTED_SESSIONS_COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("uuid", "TEXT", 1),
    ("project_path", "TEXT", 1),
    ("cwd", "TEXT", 1),
    ("jsonl_path", "TEXT", 0),
    ("jsonl_mtime", "INTEGER", 0),
    ("jsonl_last_ts", "INTEGER", 0),
    ("classification", "TEXT", 1),
    ("classification_reason", "TEXT", 0),
    ("classifier_version", "INTEGER", 1),
    ("state_summary", "TEXT", 0),
    ("first_seen", "INTEGER", 1),
    ("last_scanned", "INTEGER", 1),
    ("user_notes", "TEXT", 0),
)


# ---------------------------------------------------------------------------
# AC2.3 — init creates the documented schema
# ---------------------------------------------------------------------------
class TestInitCreatesSchema:
    def test_init_creates_documented_schema(self, tmp_db_path: Path) -> None:
        """All three tables exist and ``sessions`` has every documented column."""
        db.init(tmp_db_path)

        conn = sqlite3.connect(tmp_db_path)
        try:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            ]
            assert tables == ["classification_history", "scan_runs", "sessions"], tables

            cols = conn.execute("PRAGMA table_info(sessions)").fetchall()
            # Project (name, type, notnull) for comparison.
            projected = tuple((row[1], row[2], row[3]) for row in cols)
            assert projected == _EXPECTED_SESSIONS_COLUMNS, projected
        finally:
            conn.close()

    def test_init_sets_wal_mode(self, tmp_db_path: Path) -> None:
        """WAL is persistent and survives reconnects (the whole point of WAL)."""
        db.init(tmp_db_path)
        conn = sqlite3.connect(tmp_db_path)
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal", mode
        finally:
            conn.close()

    def test_init_creates_parent_directory(self, tmp_path: Path) -> None:
        """``init`` creates missing parents so first-run users don't need to mkdir."""
        nested = tmp_path / "a" / "b" / "c" / "crash-recovery.db"
        db.init(nested)
        assert nested.exists()


# ---------------------------------------------------------------------------
# AC2.4 — idempotency
# ---------------------------------------------------------------------------
class TestInitIsIdempotent:
    def test_init_is_idempotent(self, tmp_db_path: Path) -> None:
        """Schema hash and row counts are stable across repeat init calls."""
        db.init(tmp_db_path)

        conn = db.open_db(tmp_db_path)
        try:
            first_hash = db._schema_hash(conn)
            first_counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("sessions", "scan_runs", "classification_history")
            }
        finally:
            conn.close()

        assert first_counts == {
            "sessions": 0,
            "scan_runs": 0,
            "classification_history": 0,
        }

        # Re-run init on the same path. Should be a no-op.
        db.init(tmp_db_path)

        conn = db.open_db(tmp_db_path)
        try:
            second_hash = db._schema_hash(conn)
            second_counts = {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("sessions", "scan_runs", "classification_history")
            }
        finally:
            conn.close()

        assert second_hash == first_hash, (first_hash, second_hash)
        assert second_counts == first_counts


# ---------------------------------------------------------------------------
# open_db boundary check
# ---------------------------------------------------------------------------
class TestOpenDb:
    def test_open_db_requires_wal_mode(self, tmp_path: Path) -> None:
        """A DB not in WAL mode is rejected with a clear error pointing at init."""
        path = tmp_path / "not-wal.db"
        # Create a DB explicitly in the default ``delete`` journal mode so
        # ``open_db`` should refuse to operate on it.
        conn = sqlite3.connect(path)
        try:
            conn.execute("PRAGMA journal_mode = DELETE")
            conn.execute("CREATE TABLE t (x INTEGER)")
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(RuntimeError, match="not in WAL mode"):
            db.open_db(path)

    def test_open_db_enables_foreign_keys(self, tmp_db_path: Path) -> None:
        """FK enforcement is on per-connection so cascades fire as designed."""
        db.init(tmp_db_path)
        conn = db.open_db(tmp_db_path)
        try:
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1, fk
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# AC2.3 at the CLI layer — subprocess + env-var override
# ---------------------------------------------------------------------------
class TestCliInit:
    def test_cli_init_writes_db_at_env_var_path(self, tmp_path: Path) -> None:
        """``CRASH_RECOVERY_DB=...`` redirects the DB to the requested path."""
        db_path = tmp_path / "env-redirect.db"
        env = {"CRASH_RECOVERY_DB": str(db_path), "PATH": ""}
        # Preserve PATH from the parent so subprocess can find python/system libs.
        import os as _os

        env["PATH"] = _os.environ.get("PATH", "")
        # HOME is needed because Path.expanduser falls back to it on some shells.
        env["HOME"] = _os.environ.get("HOME", str(tmp_path))

        result = subprocess.run(
            [sys.executable, "-m", "crash_recovery", "init"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert db_path.exists(), f"DB not created at {db_path}"

        conn = sqlite3.connect(db_path)
        try:
            tables = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            ]
            assert tables == ["classification_history", "scan_runs", "sessions"], tables
        finally:
            conn.close()

    def test_cli_init_respects_db_option(self, tmp_path: Path) -> None:
        """``--db PATH`` overrides the env var (option beats env)."""
        env_path = tmp_path / "env.db"
        opt_path = tmp_path / "opt.db"
        import os as _os

        env = {
            "CRASH_RECOVERY_DB": str(env_path),
            "PATH": _os.environ.get("PATH", ""),
            "HOME": _os.environ.get("HOME", str(tmp_path)),
        }

        result = subprocess.run(
            [sys.executable, "-m", "crash_recovery", "init", "--db", str(opt_path)],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert opt_path.exists(), f"DB not created at --db path {opt_path}"
        assert not env_path.exists(), "Env var path should have been overridden"


# ---------------------------------------------------------------------------
# Constraint enforcement
# ---------------------------------------------------------------------------
class TestConstraints:
    def test_sessions_classification_check_rejects_invalid_value(
        self, tmp_db_path: Path
    ) -> None:
        """CHECK on sessions.classification rejects values not in
        CLASSIFICATION_VALUES."""
        db.init(tmp_db_path)
        conn = db.open_db(tmp_db_path)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO sessions (
                        uuid, project_path, cwd, classification,
                        classifier_version, first_seen, last_scanned
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "test-uuid-1",
                        "/some/project",
                        "/some/cwd",
                        "hard-crash",  # typo: hyphen instead of underscore
                        1,
                        1_000_000,
                        1_000_000,
                    ),
                )
        finally:
            conn.close()

    def test_classification_history_classification_check_rejects_invalid_value(
        self, tmp_db_path: Path
    ) -> None:
        """CHECK on classification_history.classification rejects invalid values."""
        db.init(tmp_db_path)
        conn = db.open_db(tmp_db_path)
        try:
            # Insert prerequisite session and scan_runs rows.
            conn.execute(
                """
                INSERT INTO sessions (
                    uuid, project_path, cwd, classification,
                    classifier_version, first_seen, last_scanned
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("test-uuid-2", "/p", "/c", "live", 1, 1_000_000, 1_000_000),
            )
            conn.execute(
                "INSERT INTO scan_runs (ts, classifier_version) VALUES (?, ?)",
                (1_000_000, 1),
            )
            scan_id = conn.execute(
                "SELECT id FROM scan_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            conn.commit()

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO classification_history
                        (uuid, scan_id, classification, classifier_version)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("test-uuid-2", scan_id, "LIVE", 1),  # wrong case
                )
        finally:
            conn.close()

    def test_classification_history_scan_id_fk_is_restrict(
        self, tmp_db_path: Path
    ) -> None:
        """ON DELETE RESTRICT on scan_id prevents deleting a scan_runs row
        that has history."""
        db.init(tmp_db_path)
        conn = db.open_db(tmp_db_path)
        try:
            conn.execute(
                """
                INSERT INTO sessions (
                    uuid, project_path, cwd, classification,
                    classifier_version, first_seen, last_scanned
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("test-uuid-3", "/p", "/c", "live", 1, 1_000_000, 1_000_000),
            )
            conn.execute(
                "INSERT INTO scan_runs (ts, classifier_version) VALUES (?, ?)",
                (1_000_000, 1),
            )
            scan_id = conn.execute(
                "SELECT id FROM scan_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO classification_history
                    (uuid, scan_id, classification, classifier_version)
                VALUES (?, ?, ?, ?)
                """,
                ("test-uuid-3", scan_id, "live", 1),
            )
            conn.commit()

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM scan_runs WHERE id = ?", (scan_id,))
        finally:
            conn.close()

    def test_classification_history_cascades_on_session_delete(
        self, tmp_db_path: Path
    ) -> None:
        """ON DELETE CASCADE on uuid removes history rows when the parent
        session is deleted."""
        db.init(tmp_db_path)
        conn = db.open_db(tmp_db_path)
        try:
            conn.execute(
                """
                INSERT INTO sessions (
                    uuid, project_path, cwd, classification,
                    classifier_version, first_seen, last_scanned
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "11111111-1111-1111-1111-111111111111",
                    "/p",
                    "/c",
                    "concluded",
                    1,
                    1_000_000,
                    1_000_000,
                ),
            )
            conn.execute(
                "INSERT INTO scan_runs (ts, classifier_version) VALUES (?, ?)",
                (1_000_000, 1),
            )
            scan_id = conn.execute(
                "SELECT id FROM scan_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
            conn.execute(
                """
                INSERT INTO classification_history
                    (uuid, scan_id, classification, classifier_version)
                VALUES (?, ?, ?, ?)
                """,
                ("11111111-1111-1111-1111-111111111111", scan_id, "concluded", 1),
            )
            conn.commit()

            # Sanity check: the history row is present.
            row = conn.execute(
                "SELECT uuid FROM classification_history WHERE uuid = ?",
                ("11111111-1111-1111-1111-111111111111",),
            ).fetchone()
            assert row is not None, "history row must exist before CASCADE test"

            conn.execute(
                "DELETE FROM sessions WHERE uuid = ?",
                ("11111111-1111-1111-1111-111111111111",),
            )
            conn.commit()

            # CASCADE must have removed the history row.
            row = conn.execute(
                "SELECT uuid FROM classification_history WHERE uuid = ?",
                ("11111111-1111-1111-1111-111111111111",),
            ).fetchone()
            assert row is None, (
                "CASCADE on sessions.uuid must delete child history rows"
            )
        finally:
            conn.close()
