"""Tests for ``crash_recovery.history`` and the ``crash-recovery history`` CLI.

Phase 6, Task 3. ``history`` is the audit readback over
``classification_history`` joined with ``scan_runs``: given a UUID it returns
every classification recorded for that session, chronologically by
``scan_id``. The CLI prints a plain-text table; an unknown UUID exits non-zero
with a stderr message so callers can distinguish "no history" from "history
fetched, table empty".

These tests exercise the contract at both the module boundary
(:func:`crash_recovery.history.fetch_history`) and the CLI boundary
(``python -m crash_recovery history <uuid>``). The module-level tests pin
the SQL ordering and tuple/dataclass shape; the CLI test pins the exit-code
and stderr-message surface that scripts and humans will rely on.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from crash_recovery import db as db_mod
from crash_recovery import history as history_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_db(tmp_path: Path) -> Path:
    """Create a fresh crash-recovery DB at ``tmp_path/history-test.db``."""
    db_path = tmp_path / "history-test.db"
    db_mod.init(db_path)
    return db_path


def _seed_session(db_path: Path, uuid: str) -> None:
    """Insert one minimal ``concluded`` row so foreign-key constraints from
    ``classification_history`` to ``sessions`` are satisfied.

    Mirrors the column set used in ``test_note.py`` so the inserted row passes
    the CLASSIFICATION CHECK constraint without depending on Phase 4's
    ``_upsert_session`` writer.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, '/p', '/c', '/no/such.jsonl', NULL, NULL,
                      'concluded', 'no_liveness_clean_end_turn', 1,
                      'end_turn observed', 1, 1, NULL)
            """,
            (uuid,),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_scan_run(db_path: Path, ts: int, classifier_version: int = 1) -> int:
    """Insert a ``scan_runs`` row and return its autoincrement id."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version) "
            "VALUES (?, '[]', 0, ?)",
            (ts, classifier_version),
        )
        conn.commit()
        scan_id = cur.lastrowid
    finally:
        conn.close()
    assert scan_id is not None
    return scan_id


def _seed_history(
    db_path: Path,
    *,
    uuid: str,
    scan_id: int,
    classification: str,
    reason: str | None,
    classifier_version: int,
) -> None:
    """Insert one ``classification_history`` row."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "INSERT INTO classification_history "
            "(uuid, scan_id, classification, reason, classifier_version) "
            "VALUES (?, ?, ?, ?, ?)",
            (uuid, scan_id, classification, reason, classifier_version),
        )
        conn.commit()
    finally:
        conn.close()


def _run_cli(*args: str, db_path: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python -m crash_recovery history <args>`` with the test DB injected."""
    env = {**os.environ, "CRASH_RECOVERY_DB": str(db_path)}
    return subprocess.run(
        [sys.executable, "-m", "crash_recovery", "history", *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# Module-level tests
# ---------------------------------------------------------------------------


def test_history_returns_chronological_entries(tmp_path: Path) -> None:
    """``fetch_history`` returns rows in scan_id ASC order.

    Seeds two scan_runs and two history rows for the same UUID; the second
    history row is for a later scan_run. ``fetch_history`` must surface them
    in chronological (scan_id ASC) order regardless of physical insert order.
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-1111-1111-1111-111111111111"
    _seed_session(db_path, uuid)
    scan_a = _seed_scan_run(db_path, ts=1000)
    scan_b = _seed_scan_run(db_path, ts=2000)
    # Insert the later scan's row FIRST so a missing ORDER BY would surface
    # by returning the rows in reverse-chronological order.
    _seed_history(
        db_path,
        uuid=uuid,
        scan_id=scan_b,
        classification="concluded",
        reason="no_liveness_clean_end_turn",
        classifier_version=1,
    )
    _seed_history(
        db_path,
        uuid=uuid,
        scan_id=scan_a,
        classification="borderline",
        reason="no_liveness_dirty_tail",
        classifier_version=1,
    )

    entries = history_mod.fetch_history(db_path, uuid)

    assert len(entries) == 2
    assert entries[0].scan_id == scan_a
    assert entries[0].scan_ts == 1000
    assert entries[0].classification == "borderline"
    assert entries[0].reason == "no_liveness_dirty_tail"
    assert entries[0].classifier_version == 1
    assert entries[1].scan_id == scan_b
    assert entries[1].scan_ts == 2000
    assert entries[1].classification == "concluded"
    assert entries[1].reason == "no_liveness_clean_end_turn"
    assert entries[1].classifier_version == 1


def test_history_for_unknown_uuid_returns_empty(tmp_path: Path) -> None:
    """A UUID with no ``classification_history`` rows yields an empty tuple.

    No exception, no None — just ``()``. The CLI layer is responsible for
    treating empty-history as a non-zero exit; the module call itself is a
    pure readback and stays silent.
    """
    db_path = _init_db(tmp_path)

    entries = history_mod.fetch_history(db_path, "no-such-uuid")

    assert entries == ()


def test_history_includes_classifier_version(tmp_path: Path) -> None:
    """Rows at multiple ``classifier_version``s all surface in the result.

    Pins that ``fetch_history`` reads ``classifier_version`` from
    ``classification_history`` (where it is denormalised per Phase 1's
    schema), not from ``scan_runs``. A row recorded under version 1 and a
    later row recorded under version 2 must BOTH appear with their original
    versions — the field is the per-history-row version, not "current".
    """
    db_path = _init_db(tmp_path)
    uuid = "bbbbbbbb-2222-2222-2222-222222222222"
    _seed_session(db_path, uuid)
    scan_v1 = _seed_scan_run(db_path, ts=1000, classifier_version=1)
    scan_v2 = _seed_scan_run(db_path, ts=2000, classifier_version=2)
    _seed_history(
        db_path,
        uuid=uuid,
        scan_id=scan_v1,
        classification="borderline",
        reason="no_liveness_dirty_tail",
        classifier_version=1,
    )
    _seed_history(
        db_path,
        uuid=uuid,
        scan_id=scan_v2,
        classification="concluded",
        reason="no_liveness_clean_end_turn",
        classifier_version=2,
    )

    entries = history_mod.fetch_history(db_path, uuid)

    versions = tuple(e.classifier_version for e in entries)
    assert versions == (1, 2)


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


def test_history_cli_for_unknown_uuid_exits_nonzero(tmp_path: Path) -> None:
    """An unknown UUID exits 1 and prints a message on stderr.

    The DB is fresh so no history exists for any UUID. The CLI uses exit
    code 1 (rather than 2) to distinguish "no rows found" from harder
    parameter / environment errors; the stderr text gives the caller the
    UUID so log grep stays useful.
    """
    db_path = _init_db(tmp_path)

    result = _run_cli("no-such-uuid", db_path=db_path)

    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "no-such-uuid" in result.stderr
