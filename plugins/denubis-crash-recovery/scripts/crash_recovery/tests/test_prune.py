"""Tests for ``crash_recovery.prune`` and the ``crash-recovery prune`` CLI.

Phase 6, Task 5. ``prune`` is the only Phase 6 writer that can lose user
state, so the test surface is deliberately wide:

* AC7.2 — ``prune --dry-run`` lists candidates without mutating the DB.
* AC7.3 — ``prune`` without ``--confirm`` refuses to delete and tells the
  user how to confirm.
* AC7.4 — ``prune --confirm`` deletes rows that match the four-condition
  guard (concluded + no note + JSONL gone + current classifier_version).
* AC7.5 — annotated rows survive ``prune --confirm`` (note acts as a
  preservation marker; paired with Task 0's ``_orphan_sweep`` exemption on
  the scan side).
* AC7.6 — rows whose JSONL is still on disk survive ``prune --confirm``.
* AC7.7 — rows at a stale ``classifier_version`` are NEVER touched; the
  CLI surfaces a stderr warning so the user knows to run ``scan`` to refresh
  them.

The cascade test pins Phase 1's ``FOREIGN KEY (uuid) REFERENCES sessions(uuid)
ON DELETE CASCADE`` + ``PRAGMA foreign_keys = ON`` from ``db.open_db``; failure
of that test signals a schema regression rather than a prune bug.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from crash_recovery import db as db_mod
from crash_recovery import prune as prune_mod
from crash_recovery.classify import CLASSIFIER_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_db(tmp_path: Path) -> Path:
    """Create a fresh crash-recovery DB at ``tmp_path/prune-test.db``."""
    db_path = tmp_path / "prune-test.db"
    db_mod.init(db_path)
    return db_path


def _seed_concluded_session(
    db_path: Path,
    uuid: str,
    *,
    jsonl_path: str | None,
    user_notes: str | None = None,
    classifier_version: int = CLASSIFIER_VERSION,
) -> None:
    """Insert one ``concluded`` sessions row with parameterised guards.

    The four-condition guard inputs (``user_notes``, ``jsonl_path`` presence
    on disk, ``classifier_version``) are all controllable from the helper so
    tests can encode each AC7.* failure independently.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, '/p', '/c', ?, NULL, NULL,
                      'concluded', 'no_liveness_clean_end_turn', ?,
                      'end_turn observed', 1, 42, ?)
            """,
            (uuid, jsonl_path, classifier_version, user_notes),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_scan_run(db_path: Path, ts: int) -> int:
    """Insert a ``scan_runs`` row so ``classification_history`` rows can
    satisfy their ``FOREIGN KEY (scan_id) REFERENCES scan_runs(id)``
    constraint. Returns the autoincrement id.
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version) "
            "VALUES (?, '[]', 0, ?)",
            (ts, CLASSIFIER_VERSION),
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
    classification: str = "concluded",
    reason: str | None = "no_liveness_clean_end_turn",
    classifier_version: int = CLASSIFIER_VERSION,
) -> None:
    """Insert one ``classification_history`` row for the cascade test."""
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


def _session_count(db_path: Path) -> int:
    """Return the count of rows in ``sessions``."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    finally:
        conn.close()


def _history_count(db_path: Path, uuid: str) -> int:
    """Return the count of ``classification_history`` rows for ``uuid``."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM classification_history WHERE uuid = ?", (uuid,)
        ).fetchone()[0]
    finally:
        conn.close()


def _run_cli(*args: str, db_path: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python -m crash_recovery prune <args>`` with the test DB injected."""
    env = {**os.environ, "CRASH_RECOVERY_DB": str(db_path)}
    return subprocess.run(
        [sys.executable, "-m", "crash_recovery", "prune", *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# AC7.2 — --dry-run is read-only
# ---------------------------------------------------------------------------


def test_prune_dry_run_is_read_only(tmp_path: Path) -> None:
    """AC7.2: ``prune --dry-run`` lists the candidate without mutating the DB.

    Seeds one prune-eligible row (concluded + no note + JSONL absent +
    current classifier_version). Captures the sessions count before the
    invocation, runs ``--dry-run`` via subprocess, asserts the candidate
    UUID appears in stdout, and asserts the sessions count is unchanged.
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-0001-0001-0001-000000000001"
    _seed_concluded_session(db_path, uuid, jsonl_path=str(tmp_path / "missing.jsonl"))
    before = _session_count(db_path)

    result = _run_cli("--dry-run", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert uuid in result.stdout, result.stdout
    assert _session_count(db_path) == before


# ---------------------------------------------------------------------------
# AC7.3 — no --confirm refuses to delete
# ---------------------------------------------------------------------------


def test_prune_without_confirm_refuses(tmp_path: Path) -> None:
    """AC7.3: ``prune`` with no flags exits non-zero and tells the user how
    to confirm. The row count is unchanged.
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-0002-0002-0002-000000000002"
    _seed_concluded_session(db_path, uuid, jsonl_path=str(tmp_path / "gone.jsonl"))
    before = _session_count(db_path)

    result = _run_cli(db_path=db_path)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "--confirm" in result.stderr, result.stderr
    assert _session_count(db_path) == before


# ---------------------------------------------------------------------------
# AC7.4 — --confirm deletes matching rows
# ---------------------------------------------------------------------------


def test_prune_confirm_deletes_matching_rows(tmp_path: Path) -> None:
    """AC7.4: ``prune --confirm`` deletes rows that match the four-condition
    guard. Single-row fixture; row count drops by exactly 1.
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-0003-0003-0003-000000000003"
    _seed_concluded_session(db_path, uuid, jsonl_path=str(tmp_path / "absent.jsonl"))
    before = _session_count(db_path)

    result = _run_cli("--confirm", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert _session_count(db_path) == before - 1


# ---------------------------------------------------------------------------
# AC7.5 — annotated rows are preserved
# ---------------------------------------------------------------------------


def test_prune_preserves_concluded_with_user_note(tmp_path: Path) -> None:
    """AC7.5: a concluded row with a ``user_notes`` value survives
    ``prune --confirm``. Paired with Task 0's ``_orphan_sweep`` exemption
    on the scan side — both encode "user has annotated this, don't touch".
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-0005-0005-0005-000000000005"
    _seed_concluded_session(
        db_path,
        uuid,
        jsonl_path=str(tmp_path / "irrelevant.jsonl"),
        user_notes="important — keep this",
    )

    result = _run_cli("--confirm", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    # The row is still in sessions.
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT user_notes FROM sessions WHERE uuid = ?", (uuid,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "important — keep this"


# ---------------------------------------------------------------------------
# AC7.6 — rows whose JSONL still exists are preserved
# ---------------------------------------------------------------------------


def test_prune_preserves_concluded_with_extant_jsonl(tmp_path: Path) -> None:
    """AC7.6: a concluded row whose ``jsonl_path`` points at an existing
    file survives ``prune --confirm``. The filesystem-presence guard fires
    before the row reaches the delete list.
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-0006-0006-0006-000000000006"
    existing = tmp_path / "still-here.jsonl"
    existing.write_text("{}\n", encoding="utf-8")
    _seed_concluded_session(db_path, uuid, jsonl_path=str(existing))

    result = _run_cli("--confirm", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT uuid FROM sessions WHERE uuid = ?", (uuid,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None


# ---------------------------------------------------------------------------
# AC7.7 — stale classifier_version rows are excluded
# ---------------------------------------------------------------------------


def test_prune_excludes_stale_classifier_version_rows(tmp_path: Path) -> None:
    """AC7.7 (dry-run side): only current-version rows appear in
    ``--dry-run`` output. The stderr warning surfaces with the stale count.

    Two rows: one at ``CLASSIFIER_VERSION`` (eligible), one at
    ``CLASSIFIER_VERSION - 1`` (also concluded + no note + JSONL gone, but
    excluded by AC7.7). Dry-run lists only the current row; stderr names
    the stale count.
    """
    db_path = _init_db(tmp_path)
    current_uuid = "aaaaaaaa-0007-0007-0007-000000000007"
    stale_uuid = "bbbbbbbb-0007-0007-0007-000000000007"
    _seed_concluded_session(
        db_path,
        current_uuid,
        jsonl_path=str(tmp_path / "current-missing.jsonl"),
    )
    _seed_concluded_session(
        db_path,
        stale_uuid,
        jsonl_path=str(tmp_path / "stale-missing.jsonl"),
        classifier_version=CLASSIFIER_VERSION - 1,
    )

    result = _run_cli("--dry-run", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert current_uuid in result.stdout
    assert stale_uuid not in result.stdout
    # AC7.7 warning includes the stale count and a "stale" / "classifier_version"
    # marker the user can grep for.
    assert "stale" in result.stderr.lower()
    assert "classifier_version" in result.stderr


def test_prune_confirm_does_not_delete_stale_rows(tmp_path: Path) -> None:
    """AC7.7 (confirm side): ``--confirm`` deletes the current-version row
    but leaves the stale row in place. Pairs with the dry-run test above
    to pin the guard on both code paths.
    """
    db_path = _init_db(tmp_path)
    current_uuid = "aaaaaaaa-0070-0070-0070-000000000070"
    stale_uuid = "bbbbbbbb-0070-0070-0070-000000000070"
    _seed_concluded_session(
        db_path,
        current_uuid,
        jsonl_path=str(tmp_path / "current-missing.jsonl"),
    )
    _seed_concluded_session(
        db_path,
        stale_uuid,
        jsonl_path=str(tmp_path / "stale-missing.jsonl"),
        classifier_version=CLASSIFIER_VERSION - 1,
    )

    result = _run_cli("--confirm", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    conn = sqlite3.connect(db_path)
    try:
        uuids_remaining = {
            row[0]
            for row in conn.execute("SELECT uuid FROM sessions").fetchall()
        }
    finally:
        conn.close()
    assert current_uuid not in uuids_remaining
    assert stale_uuid in uuids_remaining


# ---------------------------------------------------------------------------
# Flag mutual-exclusion
# ---------------------------------------------------------------------------


def test_prune_dry_run_and_confirm_mutually_exclusive(tmp_path: Path) -> None:
    """``prune --dry-run --confirm`` exits non-zero (typer.BadParameter).

    The two modes are semantically opposed; conflating them in a single
    invocation is always a caller error. Defence-in-depth so a user who
    sets both flags doesn't accidentally trigger a deletion.
    """
    db_path = _init_db(tmp_path)

    result = _run_cli("--dry-run", "--confirm", db_path=db_path)

    assert result.returncode != 0, (result.stdout, result.stderr)


# ---------------------------------------------------------------------------
# Empty DB
# ---------------------------------------------------------------------------


def test_prune_empty_db(tmp_path: Path) -> None:
    """An empty DB prints "No prune candidates." on dry-run and
    "Deleted 0 session(s)." on confirm. No exception, no failure.
    """
    db_path = _init_db(tmp_path)

    dry = _run_cli("--dry-run", db_path=db_path)
    assert dry.returncode == 0, (dry.stdout, dry.stderr)
    assert "No prune candidates" in dry.stdout

    confirm = _run_cli("--confirm", db_path=db_path)
    assert confirm.returncode == 0, (confirm.stdout, confirm.stderr)
    assert "Deleted 0 session(s)" in confirm.stdout


# ---------------------------------------------------------------------------
# Cascade — Phase 1 schema invariant
# ---------------------------------------------------------------------------


def test_prune_cascades_classification_history_deletion(tmp_path: Path) -> None:
    """Pins Phase 1's ON DELETE CASCADE on ``classification_history``.

    Seeds one prune-eligible row plus two ``classification_history`` rows
    for the same UUID (simulating two prior scans). ``prune --confirm``
    deletes the sessions row; the FK cascade fires inside the same
    transaction because :func:`crash_recovery.db.open_db` sets
    ``PRAGMA foreign_keys = ON``.

    Failure of this test signals a Phase 1 schema regression — either the
    ``FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE``
    constraint was loosened, or ``PRAGMA foreign_keys = ON`` is no longer
    set on the connection ``prune`` uses. Do NOT loosen the test in
    response; investigate the schema and the PRAGMA instead.
    """
    db_path = _init_db(tmp_path)
    uuid = "aaaaaaaa-cccc-cccc-cccc-aaaaaaaaaaaa"
    _seed_concluded_session(db_path, uuid, jsonl_path=str(tmp_path / "gone.jsonl"))
    scan_a = _seed_scan_run(db_path, ts=1000)
    scan_b = _seed_scan_run(db_path, ts=2000)
    _seed_history(db_path, uuid=uuid, scan_id=scan_a)
    _seed_history(db_path, uuid=uuid, scan_id=scan_b)

    assert _history_count(db_path, uuid) == 2

    result = _run_cli("--confirm", db_path=db_path)

    assert result.returncode == 0, (result.stdout, result.stderr)
    # sessions row is gone.
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT uuid FROM sessions WHERE uuid = ?", (uuid,)
        ).fetchone()
    finally:
        conn.close()
    assert row is None
    # classification_history rows for this UUID cascaded out.
    assert _history_count(db_path, uuid) == 0
