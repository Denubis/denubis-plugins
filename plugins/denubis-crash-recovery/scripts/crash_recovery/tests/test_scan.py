"""Integration tests for ``crash_recovery.scan.run_scan`` and the ``scan`` CLI.

Covers crash-recovery.AC3.6 (stale-classifier-version re-classification),
crash-recovery.AC5.6 end-to-end (boot mismatch wins over PID-alive),
crash-recovery.AC6.2 (live PID → ``live`` classification), and
crash-recovery.AC6.3 (ambiguous correlation → ``BORDERLINE``/``ambiguous_match``).

Each test uses :func:`make_full_fixture` to declare a temp filesystem layout
and either calls :func:`run_scan` directly (preferred — exercises the same
code path the CLI invokes) or shells out to ``python -m crash_recovery scan``
(only where the platform-guard or subprocess concurrency is the SUT).
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
import typer
from crash_recovery import db as db_mod
from crash_recovery import liveness as liveness_mod
from crash_recovery import scan as scan_mod
from crash_recovery.__main__ import scan as scan_cmd
from crash_recovery.classify import CLASSIFIER_VERSION
from crash_recovery.jsonl import TailKind, TailSummary
from fixtures.jsonl_builder import (
    FixtureSession,
    make_full_fixture,
)


def test_pick_dead_pid_is_truly_dead_and_above_pid_max():
    """Regression: a `pid_alive=False` fixture PID must never collide with a
    real process. `_pick_dead_pid` used to return max(/proc PIDs)+1 — the next
    PID the kernel hands out — so a subprocess spawned by another test could
    claim it and the 'dead' session read as live (order-dependent flake). It
    must now sit above pid_max, which the kernel can never assign."""
    from fixtures.jsonl_builder import _pick_dead_pid

    pid = _pick_dead_pid()
    with Path("/proc/sys/kernel/pid_max").open() as f:
        pid_max = int(f.read().strip())
    assert pid > pid_max
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def _init_db(db_dir: Path) -> Path:
    """Create the DB file and apply schema; return the path."""
    db_path = db_dir / "crash-recovery.db"
    db_mod.init(db_path)
    return db_path


def _make_ctx(
    db_path: Path,
    run_dir: Path,
    projects_root: Path,
    now: int | None = None,
    resurrect_dir: Path | None = None,
) -> scan_mod.ScanContext:
    return scan_mod.ScanContext(
        db_path=db_path,
        run_dir=run_dir,
        projects_root=projects_root,
        now=now if now is not None else int(time.time()),
        # Default to a non-existent dir so resurrect corroboration is a no-op
        # for every existing test (load_snapshots returns []). ``run_dir.parent``
        # is the per-test ``tmp_path`` (make_full_fixture sets run_dir = tmp/run).
        resurrect_dir=resurrect_dir
        if resurrect_dir is not None
        else run_dir.parent / "no-resurrect",
    )


def _rows(db_path: Path, query: str) -> list[tuple]:
    """Open the DB and return ``query`` result rows. Closes after read."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query).fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Idempotency + shape
# ---------------------------------------------------------------------------


def test_scan_writes_expected_rows(tmp_path: Path) -> None:
    """One CONCLUDED, one HARD_CRASH (dead pid + tool_use_no_result), one LIVE.

    Asserts the basic happy-path shape: 3 sessions rows with the expected
    classifications, one scan_runs row, three classification_history rows.
    """
    sessions = [
        FixtureSession(
            uuid="11111111-1111-1111-1111-111111111111",
            cwd="/tmp/conc",
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        ),
        FixtureSession(
            uuid="22222222-2222-2222-2222-222222222222",
            cwd="/tmp/hardc",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=False,
            boot_id_current=True,
        ),
        FixtureSession(
            uuid="33333333-3333-3333-3333-333333333333",
            cwd="/tmp/live",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,
            boot_id_current=True,
        ),
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    result = scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    assert result.sessions_scanned == 3
    rows = _rows(
        db_path, "SELECT uuid, classification, classification_reason FROM sessions"
    )
    by_uuid = {r[0]: (r[1], r[2]) for r in rows}
    assert by_uuid["11111111-1111-1111-1111-111111111111"] == (
        "concluded",
        "no_liveness_clean_end_turn",
    )
    assert by_uuid["22222222-2222-2222-2222-222222222222"] == (
        "hard_crash",
        "liveness_dead_pid_tool_use_no_result",
    )
    assert by_uuid["33333333-3333-3333-3333-333333333333"] == (
        "live",
        "live_pid_present_boot_current",
    )

    scan_runs = _rows(db_path, "SELECT COUNT(*) FROM scan_runs")
    assert scan_runs == [(1,)]
    history = _rows(db_path, "SELECT COUNT(*) FROM classification_history")
    assert history == [(3,)]


def test_scan_is_idempotent(tmp_path: Path) -> None:
    """Two scans → same sessions rows; first_seen preserved; last_scanned updated."""
    sessions = [
        FixtureSession(
            uuid="11111111-1111-1111-1111-111111111111",
            cwd="/tmp/conc",
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        ),
        FixtureSession(
            uuid="22222222-2222-2222-2222-222222222222",
            cwd="/tmp/hardc",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=False,
            boot_id_current=True,
        ),
        FixtureSession(
            uuid="33333333-3333-3333-3333-333333333333",
            cwd="/tmp/live",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,
            boot_id_current=True,
        ),
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    # ``now`` pinned to two distinct values so we can compare last_scanned
    # before/after without depending on wall-clock resolution.
    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=1_000_000))
    first_seen_before = {
        r[0]: r[1] for r in _rows(db_path, "SELECT uuid, first_seen FROM sessions")
    }

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=2_000_000))

    # Same 3 sessions rows.
    count_rows = _rows(db_path, "SELECT COUNT(*) FROM sessions")
    assert count_rows == [(3,)]
    # first_seen preserved.
    first_seen_after = {
        r[0]: r[1] for r in _rows(db_path, "SELECT uuid, first_seen FROM sessions")
    }
    assert first_seen_after == first_seen_before
    # last_scanned advanced to the second scan's now.
    last_scanned_after = {
        r[0]: r[1] for r in _rows(db_path, "SELECT uuid, last_scanned FROM sessions")
    }
    assert all(v == 2_000_000 for v in last_scanned_after.values())
    # Two scan_runs rows; three history rows (one per session from scan 1;
    # scan 2 dedups because no classification changed — M4).
    assert _rows(db_path, "SELECT COUNT(*) FROM scan_runs") == [(2,)]
    assert _rows(db_path, "SELECT COUNT(*) FROM classification_history") == [(3,)]


# ---------------------------------------------------------------------------
# AC3.6 — stale-classifier-version re-classification
# ---------------------------------------------------------------------------


def test_scan_reclassifies_stale_classifier_version_rows(tmp_path: Path) -> None:
    """Seeded rows at ``CLASSIFIER_VERSION - 1`` with no JSONLs on disk.

    All three rows must end up at ``CLASSIFIER_VERSION`` after scan with
    classification ``irrecoverable`` / ``missing_jsonl_on_disk`` — AC3.6.
    """
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    stale_version = CLASSIFIER_VERSION - 1
    conn = sqlite3.connect(db_path)
    try:
        for i in range(3):
            uuid = f"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa{i}"
            conn.execute(
                """
                INSERT INTO sessions (
                    uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                    classification, classification_reason, classifier_version,
                    state_summary, first_seen, last_scanned, user_notes
                ) VALUES (?, '/p', '/c', '/no/such.jsonl', NULL, NULL,
                          'borderline', 'old_reason', ?, NULL, 1, 1, NULL)
                """,
                (uuid, stale_version),
            )
        conn.commit()
    finally:
        conn.close()

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(
        db_path,
        "SELECT classifier_version, classification, classification_reason "
        "FROM sessions",
    )
    assert len(rows) == 3
    for cv, classification, reason in rows:
        assert cv == CLASSIFIER_VERSION
        assert classification == "irrecoverable"
        assert reason == "missing_jsonl_on_disk"


def test_scan_reclassifies_stale_row_whose_jsonl_still_exists(tmp_path: Path) -> None:
    """Seeded row at stale ``classifier_version`` whose JSONL is on disk.

    Scan finds the JSONL during ``_walk_sessions`` (JSONL-only path), so the
    row is upserted with the current ``classifier_version`` and the
    classification matches what :func:`classify` produces for the CONCLUDED
    tail. The orphan sweep is not the path here — the upsert path is.
    """
    uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    cwd = "/tmp/stillalive"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd=cwd,
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    stale_version = CLASSIFIER_VERSION - 1
    # Find the JSONL path that the fixture wrote.
    jsonl_paths = list(projects_root.glob("*/*.jsonl"))
    assert len(jsonl_paths) == 1
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, ?, ?, ?, NULL, NULL,
                      'borderline', 'old', ?, NULL, 1, 1, NULL)
            """,
            (uuid, str(jsonl_paths[0].parent), cwd, str(jsonl_paths[0]), stale_version),
        )
        conn.commit()
    finally:
        conn.close()

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classifier_version, classification, classification_reason "
            "FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()
    cv, classification, reason = row
    assert cv == CLASSIFIER_VERSION
    assert classification == "concluded"
    assert reason == "no_liveness_clean_end_turn"


# ---------------------------------------------------------------------------
# AC6.2 / AC5.6 / boot-vs-pid precedence
# ---------------------------------------------------------------------------


def test_scan_classifies_live_pid_as_live(tmp_path: Path) -> None:
    """Live PID + boot_id current → ``live`` / ``live_pid_present_boot_current``
    (AC6.2)."""
    uuid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd="/tmp/liveone",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,
            boot_id_current=True,
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("live", "live_pid_present_boot_current")


def test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive(
    tmp_path: Path,
) -> None:
    """Boot mismatch wins over PID-alive — AC5.6 end-to-end.

    The session's liveness file claims a never-matching boot_id but the
    test process's PID is alive. Per RULES ordering, the boot-mismatch
    rule fires first and produces ``hard_crash`` /
    ``liveness_boot_id_mismatch`` regardless of pid_alive=True.
    """
    uuid = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd="/tmp/reboot",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,  # but boot is stale — boot wins
            boot_id_current=False,
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("hard_crash", "liveness_boot_id_mismatch")


# ---------------------------------------------------------------------------
# AC4.2 (scan integration) — recycled PID rejected via start-time-checked probe
# ---------------------------------------------------------------------------


def test_scan_recycled_pid_with_wrong_start_time_is_not_live(tmp_path: Path) -> None:
    """AC4.2: a live PID whose stored ``start_time`` is wrong must NOT classify
    ``live``.

    Recycled-PID scenario. The marker's PID is alive (``os.getpid()``) and the
    boot_id is current, so the *bare* ``kill -0`` liveness check that scan used
    before this task would classify the session ``live`` — the exact bug. The
    tail is the live-shaped ``TOOL_USE_NO_RESULT`` (same shape
    ``test_scan_classifies_live_pid_as_live`` relies on), so the session is
    genuinely live-by-old-logic; only the start-time mismatch can flip it.

    With the start-time-checked probe in scan's fact builders,
    ``pid_alive_checked(pid, wrong_start_time)`` returns ``False`` → the dead-pid
    rule fires on the TOOL_USE_NO_RESULT tail → ``hard_crash`` /
    ``liveness_dead_pid_tool_use_no_result``.

    RED (before the scan fix) prints ``("live", "live_pid_present_boot_current")``
    — proving the fixture would be live without the fix, so the fix is
    demonstrably what flips it.
    """
    base = liveness_mod._proc_start_time(os.getpid())
    assert base is not None, "could not read own /proc start_time — test precondition"
    wrong_start_time = base + 1

    uuid = "44440002-0000-0000-0000-000000000001"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd="/tmp/recycled-pid",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,  # os.getpid() — genuinely alive
            boot_id_current=True,  # boot matches → live-by-old-logic
            start_time=wrong_start_time,  # but start_time mismatches → recycled
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("hard_crash", "liveness_dead_pid_tool_use_no_result")


def test_scan_live_pid_with_correct_start_time_is_live(tmp_path: Path) -> None:
    """AC4.2 over-rejection guard: correct ``start_time`` + live PID still ``live``.

    Positive control for ``test_scan_recycled_pid_with_wrong_start_time_is_not_live``.
    Same live-shaped fixture, but the stored ``start_time`` is the real
    ``/proc/<pid>/stat`` value, so ``pid_alive_checked`` matches and the session
    classifies ``live`` / ``live_pid_present_boot_current``. Proves the fix
    rejects only genuine mismatches, not every start-time-bearing marker.
    """
    correct_start_time = liveness_mod._proc_start_time(os.getpid())
    assert correct_start_time is not None, (
        "could not read own /proc start_time — test precondition"
    )

    uuid = "44440002-0000-0000-0000-000000000002"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd="/tmp/correct-start-time",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,
            boot_id_current=True,
            start_time=correct_start_time,
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("live", "live_pid_present_boot_current")


def test_scan_marks_vanished_jsonl_as_irrecoverable(tmp_path: Path) -> None:
    """Seeded row whose ``jsonl_path`` no longer exists → irrecoverable."""
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)
    uuid = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, '/p', '/c', '/no/such/file.jsonl', NULL, NULL,
                      'borderline', 'before', ?, NULL, 1, 1, NULL)
            """,
            (uuid, CLASSIFIER_VERSION),
        )
        conn.commit()
    finally:
        conn.close()

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("irrecoverable", "missing_jsonl_on_disk")


# ---------------------------------------------------------------------------
# Annotation-preserves-classification (Phase 4 proleptic-review deferral,
# 2026-05-17). Realised in Phase 6, Subcomponent A, Task 0: ``_orphan_sweep``
# skips rows where ``user_notes IS NOT NULL`` so a user's annotation acts as
# a "keep this row" signal that protects both ``classification`` and
# ``classifier_version`` from being silently reset when the JSONL is
# transiently or permanently absent.
# ---------------------------------------------------------------------------


def _seed_orphan_row(
    db_path: Path,
    *,
    uuid: str,
    user_notes: str | None,
    classification: str = "concluded",
    classification_reason: str = "no_liveness_clean_end_turn",
) -> None:
    """Seed a sessions row whose ``jsonl_path`` does not exist on disk.

    Both annotated and unannotated variants share this scaffolding; the only
    difference is ``user_notes``. The seeded row uses the current
    ``CLASSIFIER_VERSION`` so any post-scan version drift is attributable
    to ``_orphan_sweep``'s UPDATE rather than the AC3.6 stale-version path.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, '/p', '/c', '/no/such/orphan.jsonl', NULL, NULL,
                      ?, ?, ?, 'seeded state', 1, 1, ?)
            """,
            (
                uuid,
                classification,
                classification_reason,
                CLASSIFIER_VERSION,
                user_notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_orphan_sweep_preserves_annotated_session_classification(
    tmp_path: Path,
) -> None:
    """Annotated orphans keep their classification + classifier_version.

    Phase 6 contract: ``user_notes IS NOT NULL`` signals user intent to
    preserve a row. ``_orphan_sweep`` must skip those rows entirely — no
    classification flip to ``irrecoverable``/``missing_jsonl_on_disk``, no
    ``classifier_version`` bump, and no ``classification_history`` append.

    Decision documented here: ``last_scanned`` is bookkeeping rather than
    user intent, so in principle it could be refreshed. The simplest
    correct implementation skips the entire UPDATE for annotated orphans,
    which means ``last_scanned`` is also preserved. This test pins that
    end-to-end skip behaviour (no UPDATE, no history append) so any future
    "refresh last_scanned only" optimisation must consciously break this
    test rather than silently re-introduce a partial reset.
    """
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)
    uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    _seed_orphan_row(db_path, uuid=uuid, user_notes="keep this")

    history_before = _rows(
        db_path,
        "SELECT COUNT(*) FROM classification_history WHERE uuid = '" + uuid + "'",
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(
        db_path,
        "SELECT classification, classification_reason, classifier_version, "
        "state_summary, last_scanned "
        "FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert len(rows) == 1
    classification, reason, cv, state_summary, last_scanned = rows[0]
    # Classification + reason unchanged.
    assert classification == "concluded"
    assert reason == "no_liveness_clean_end_turn"
    # classifier_version unchanged (and equal to the value we seeded, which
    # happens to be CLASSIFIER_VERSION — the point is _orphan_sweep did not
    # rewrite it).
    assert cv == CLASSIFIER_VERSION
    # state_summary + last_scanned preserved per the "skip the whole UPDATE"
    # decision documented above.
    assert state_summary == "seeded state"
    assert last_scanned == 1

    history_after = _rows(
        db_path,
        "SELECT COUNT(*) FROM classification_history WHERE uuid = '" + uuid + "'",
    )
    # No reclassification ⇒ no history append.
    assert history_after == history_before


def test_orphan_sweep_reclassifies_unannotated_session(tmp_path: Path) -> None:
    """Unannotated orphans still flip to irrecoverable (re-pins AC3.6).

    Paired with ``test_orphan_sweep_preserves_annotated_session_classification``
    to confirm the new exemption is scoped to rows with ``user_notes IS NOT
    NULL`` and does not loosen the existing AC3.6 behaviour for rows the user
    has not annotated.
    """
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)
    uuid = "ffffffff-1111-2222-3333-444444444444"
    _seed_orphan_row(db_path, uuid=uuid, user_notes=None)

    history_before = _rows(
        db_path,
        "SELECT COUNT(*) FROM classification_history WHERE uuid = '" + uuid + "'",
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(
        db_path,
        "SELECT classification, classification_reason "
        "FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert rows == [("irrecoverable", "missing_jsonl_on_disk")]

    history_after = _rows(
        db_path,
        "SELECT COUNT(*) FROM classification_history WHERE uuid = '" + uuid + "'",
    )
    # AC3.6 reclassification path appends exactly one history row.
    assert history_after[0][0] == history_before[0][0] + 1


# ---------------------------------------------------------------------------
# scan_runs.live_pids serialisation
# ---------------------------------------------------------------------------


def test_scan_writes_scan_runs_with_live_pids(tmp_path: Path) -> None:
    """``scan_runs.live_pids`` is a JSON array containing the alive session's PID.

    One live session (``pid_alive=True`` → ``os.getpid()``) and one crashed
    session → ``live_pids`` is a JSON list containing exactly the test-process
    PID.

    Note: this test does NOT exercise the ``sorted({...})`` deduplication path
    in ``run_scan``. That path is covered by
    ``test_run_scan_deduplicates_live_pids_across_facts``.
    """
    sessions = [
        FixtureSession(
            uuid="11111111-1111-1111-1111-111111111111",
            cwd="/tmp/live1",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=True,
            boot_id_current=True,
        ),
        FixtureSession(
            uuid="33333333-3333-3333-3333-333333333333",
            cwd="/tmp/crashed",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=False,
            boot_id_current=True,
        ),
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(db_path, "SELECT live_pids FROM scan_runs")
    assert len(rows) == 1
    live_pids = json.loads(rows[0][0])
    assert isinstance(live_pids, list)
    assert live_pids == [os.getpid()]


def test_run_scan_deduplicates_live_pids_across_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``run_scan`` deduplicates PIDs via ``sorted({...})`` when two facts
    share one PID.

    Two ``SessionFact`` objects with distinct UUIDs and cwds but the same
    ``liveness.pid`` (12345) and ``pid_alive_value=True`` are injected by
    monkey-patching ``_walk_sessions``. The ``sorted({pid for ...})`` set
    comprehension in ``run_scan`` must collapse the duplicate so
    ``scan_runs.live_pids`` serialises as ``[12345]``, not ``[12345, 12345]``.

    The test is designed to FAIL (red) if ``sorted({...})`` is changed to
    ``sorted([...])`` (list keeps duplicates) — a structural regression guard.
    """
    _synthetic_liveness = liveness_mod.Liveness(
        path=tmp_path / "12345.live",
        pid=12345,
        cwd="/tmp/dedup",
        started=1_000_000,
        argv="--resume 11111111-1111-1111-1111-111111111111",
        boot_id="test-boot-id",
    )
    _tail = TailSummary(
        kind=TailKind.TOOL_USE_NO_RESULT,
        last_ts=None,
        total_entries=0,
        state_summary="tool use pending",
    )
    _facts = [
        scan_mod.SessionFact(
            uuid="11111111-1111-1111-1111-111111111111",
            project_path="/tmp/proj",
            cwd="/tmp/dedup",
            jsonl_path=None,
            jsonl_mtime=None,
            tail_summary=_tail,
            liveness=_synthetic_liveness,
            pid_alive_value=True,
            boot_id_current=True,
        ),
        scan_mod.SessionFact(
            uuid="22222222-2222-2222-2222-222222222222",
            project_path="/tmp/proj",
            cwd="/tmp/dedup",
            jsonl_path=None,
            jsonl_mtime=None,
            tail_summary=_tail,
            liveness=_synthetic_liveness,
            pid_alive_value=True,
            boot_id_current=True,
        ),
    ]

    monkeypatch.setattr(scan_mod, "_walk_sessions", lambda _ctx: (list(_facts), []))

    db_dir = tmp_path / "db"
    db_dir.mkdir()
    db_path = _init_db(db_dir)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(db_path, "SELECT live_pids FROM scan_runs")
    assert len(rows) == 1
    live_pids = json.loads(rows[0][0])
    assert isinstance(live_pids, list), (
        "live_pids must be a list (JSON array), not a set"
    )
    assert live_pids == [12345], (
        f"expected [12345] (deduplicated); got {live_pids!r}. "
        "If this is [12345, 12345], sorted({{...}}) was changed to sorted([...])."
    )


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------


def test_scan_atomic_on_simulated_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure mid-loop rolls back the entire transaction (no partial state).

    Three sessions; patch ``_upsert_session`` to raise after its second call.
    The ``with conn:`` context manager wrapping the entire write block must
    roll back so ``sessions`` and ``scan_runs`` end empty.
    """
    sessions = [
        FixtureSession(
            uuid=f"abcdefab-cdef-abcd-efab-cdefabcdef0{i}",
            cwd=f"/tmp/atomic{i}",
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        )
        for i in range(3)
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    real_upsert = scan_mod._upsert_session
    counter = {"n": 0}

    def flaky_upsert(*args, **kwargs):
        counter["n"] += 1
        if counter["n"] >= 2:
            raise RuntimeError("simulated mid-loop failure")
        return real_upsert(*args, **kwargs)

    monkeypatch.setattr(scan_mod, "_upsert_session", flaky_upsert)

    with pytest.raises(RuntimeError, match="simulated mid-loop failure"):
        scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    assert _rows(db_path, "SELECT COUNT(*) FROM sessions") == [(0,)]
    assert _rows(db_path, "SELECT COUNT(*) FROM scan_runs") == [(0,)]


# ---------------------------------------------------------------------------
# CLI guards: non-Linux + network FS
# ---------------------------------------------------------------------------


def test_scan_cli_refuses_to_run_on_non_linux(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Non-Linux platform → ``typer.Exit(code=2)`` with helpful stderr message.

    Subprocess can't carry the monkeypatch, so we invoke the typer command
    function directly with ``sys.platform`` patched.
    """
    monkeypatch.setattr(sys, "platform", "darwin")
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    with pytest.raises(typer.Exit) as excinfo:
        scan_cmd(db_path=db_path, run_dir=run_dir, projects_root=projects_root)
    assert excinfo.value.exit_code == 2

    captured = capsys.readouterr()
    assert "requires Linux" in captured.err
    assert "/proc/sys/kernel/random/boot_id" in captured.err


@pytest.mark.parametrize("fstype", ["nfs4", "fuse.sshfs"])
def test_scan_cli_refuses_when_run_dir_is_on_network_fs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fstype: str,
) -> None:
    """Refused fstype on ``run_dir`` → ``typer.Exit(2)`` mentioning env var + fstype."""

    def _fake_detect(path: Path) -> str:
        return fstype

    monkeypatch.setattr(liveness_mod, "_detect_fstype", _fake_detect)
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    with pytest.raises(typer.Exit) as excinfo:
        scan_cmd(db_path=db_path, run_dir=run_dir, projects_root=projects_root)
    assert excinfo.value.exit_code == 2

    captured = capsys.readouterr()
    assert "CRASH_RECOVERY_RUN_DIR" in captured.err
    assert fstype in captured.err


# ---------------------------------------------------------------------------
# AC6.3 — ambiguous correlation
# ---------------------------------------------------------------------------


def test_scan_classifies_ambiguous_correlation_as_borderline_ambiguous_match(
    tmp_path: Path,
) -> None:
    """One liveness file (no ``--resume``), two JSONLs in the mtime window.

    Correlate returns ``AMBIGUOUS`` with both UUIDs as candidates; scan
    emits one ``SessionFact`` per candidate, each classified as
    ``borderline`` / ``ambiguous_match`` with ``state_summary`` listing the
    other candidate (AC6.3).
    """
    cwd = "/tmp/ambig"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    # Build two JSONLs in the same project dir + one liveness file with no
    # ``--resume`` flag in argv (correlate must use the mtime window).
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)
    now_epoch = int(time.time())
    uuid_a = "aaaaaaaa-1111-1111-1111-111111111111"
    uuid_b = "bbbbbbbb-2222-2222-2222-222222222222"
    # Both JSONLs have first_entry_ts inside the Phase 3 tight window:
    # started = now - 3600, so the window is [started - 60, started + 120].
    # +10s / +20s past started land both candidates in-window → AMBIGUOUS.
    started = now_epoch - 3600
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 20,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=os.getpid(),
        cwd=cwd,
        started=started,
        argv="",  # no --resume → mtime-window path
        boot_id=liveness_mod.current_boot_id(),
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

    rows = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason, state_summary "
        "FROM sessions",
    )
    by_uuid = {r[0]: (r[1], r[2], r[3]) for r in rows}
    assert set(by_uuid.keys()) == {uuid_a, uuid_b}
    for u in (uuid_a, uuid_b):
        classification, reason, summary = by_uuid[u]
        assert classification == "borderline"
        assert reason == "ambiguous_match"
        assert "ambiguous match:" in summary
        # The other candidate's UUID is in the state_summary
        other = uuid_b if u == uuid_a else uuid_a
        assert other in summary


# ---------------------------------------------------------------------------
# Concurrency — WAL + busy timeout
# ---------------------------------------------------------------------------


def test_scan_two_concurrent_invocations_do_not_corrupt_db(tmp_path: Path) -> None:
    """Two parallel ``crash-recovery scan`` subprocesses → exactly 2 scan_runs.

    Three synthetic sessions, two parallel ``python -m crash_recovery scan``
    invocations. WAL mode + SQLite's 5s default busy timeout serialise the
    two write transactions. Both subprocesses exit 0; sessions count is
    exactly 3; scan_runs count is exactly 2; every sessions row has the
    current ``classifier_version`` and a ``last_scanned`` matching one of
    the two ``scan_runs.ts`` values.
    """
    sessions = [
        FixtureSession(
            uuid=f"abc{i}defa-bcde-fabc-defa-bcdefabcdef{i}",
            cwd=f"/tmp/concurrent{i}",
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        )
        for i in range(3)
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    env = {
        **os.environ,
        "CRASH_RECOVERY_DB": str(db_path),
        "CRASH_RECOVERY_RUN_DIR": str(run_dir),
        "CRASH_RECOVERY_PROJECTS_ROOT": str(projects_root),
    }
    proc_a = subprocess.Popen(
        [sys.executable, "-m", "crash_recovery", "scan"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc_b = subprocess.Popen(
        [sys.executable, "-m", "crash_recovery", "scan"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out_a, err_a = proc_a.communicate(timeout=30)
    out_b, err_b = proc_b.communicate(timeout=30)
    assert proc_a.returncode == 0, (out_a, err_a)
    assert proc_b.returncode == 0, (out_b, err_b)

    sess_count = _rows(db_path, "SELECT COUNT(*) FROM sessions")
    assert sess_count == [(3,)]
    runs = _rows(db_path, "SELECT id, ts FROM scan_runs ORDER BY id")
    assert len(runs) == 2
    run_timestamps = {r[1] for r in runs}

    rows = _rows(db_path, "SELECT classifier_version, last_scanned FROM sessions")
    for cv, ls in rows:
        assert cv == CLASSIFIER_VERSION
        assert ls in run_timestamps


# ---------------------------------------------------------------------------
# M2 — project_path holds the decoded cwd, not the encoded directory name
# ---------------------------------------------------------------------------


def test_walk_project_path_equals_cwd_for_normal_sessions(tmp_path: Path) -> None:
    """``project_path`` and ``cwd`` hold the same decoded path on both walker paths.

    The design plan (line 145) says ``project_path`` is the decoded path —
    i.e. the cwd Claude Code recorded inside the JSONL, not the encoded
    directory name with leading ``-`` and ``/``/``.`` collapsed. This test
    pins both walker paths (liveness-driven and JSONL-only) to that contract.

    Fixture: one session with a liveness file (liveness-walk path) and one
    without (JSONL-only walk path). Both must end up with
    ``project_path == cwd`` and neither must contain the encoded leading
    ``-`` directory-name form.
    """
    liveness_session = FixtureSession(
        uuid="11111111-1111-1111-1111-111111111111",
        cwd="/tmp/with-liveness",
        tail_kind=TailKind.CONCLUDED,
        has_liveness=True,
        pid_alive=True,
        boot_id_current=True,
    )
    jsonl_only_session = FixtureSession(
        uuid="22222222-2222-2222-2222-222222222222",
        cwd="/tmp/jsonl-only",
        tail_kind=TailKind.CONCLUDED,
        has_liveness=False,
        pid_alive=None,
        boot_id_current=False,
    )
    db_dir, run_dir, projects_root = make_full_fixture(
        tmp_path, [liveness_session, jsonl_only_session]
    )
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(db_path, "SELECT uuid, project_path, cwd FROM sessions")
    by_uuid = {r[0]: (r[1], r[2]) for r in rows}
    # Liveness-walk path
    pp_a, cwd_a = by_uuid[liveness_session.uuid]
    assert pp_a == cwd_a == "/tmp/with-liveness"
    # JSONL-only walk path
    pp_b, cwd_b = by_uuid[jsonl_only_session.uuid]
    assert pp_b == cwd_b == "/tmp/jsonl-only"


# ---------------------------------------------------------------------------
# M3 — empty cwd short-circuits to IRRECOVERABLE/missing_cwd
# ---------------------------------------------------------------------------


def test_walk_emits_irrecoverable_missing_cwd_for_unreadable_jsonl(
    tmp_path: Path,
) -> None:
    """JSONL with no ``cwd`` key → classify as ``irrecoverable``/``missing_cwd``.

    ``_first_entry_cwd`` returns ``""`` on parse error, missing-cwd-key, or
    corruption. Without a cwd, Phase 7's ``claudew --resume`` from ``""``
    would fail confusingly. ``_classify_fact`` must short-circuit empty-cwd
    sessions to ``IRRECOVERABLE/missing_cwd`` so the user sees a clear
    reason in triage. ``project_path`` (per M2) is also empty.
    """
    uuid = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    # Synthesise a JSONL under a project_dir but with NO cwd key in the
    # first entry. ``_first_entry_cwd`` returns "".
    project_dir = projects_root / "-no-cwd-fixture"
    project_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = project_dir / f"{uuid}.jsonl"
    jsonl_path.write_text(json.dumps({"role": "assistant", "content": "hi"}) + "\n")

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason, cwd, project_path "
        "FROM sessions",
    )
    assert len(rows) == 1
    row_uuid, classification, reason, cwd_val, pp_val = rows[0]
    assert row_uuid == uuid
    assert classification == "irrecoverable"
    assert reason == "missing_cwd"
    assert cwd_val == ""
    assert pp_val == ""


# ---------------------------------------------------------------------------
# M4 — classification_history dedup
# ---------------------------------------------------------------------------


def test_classification_history_skips_append_when_unchanged(tmp_path: Path) -> None:
    """Running scan twice on the same fixture writes history rows only once.

    M4: classification_history previously accumulated a row per scan per
    session, even when the classification was unchanged. After M4 the
    second scan must skip the history append for any session whose
    classification + reason are unchanged. ``last_scanned`` still
    advances on both rows (refreshed on every scan).
    """
    sessions = [
        FixtureSession(
            uuid="11111111-1111-1111-1111-111111111111",
            cwd="/tmp/conc-dedup",
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        ),
        FixtureSession(
            uuid="22222222-2222-2222-2222-222222222222",
            cwd="/tmp/hardc-dedup",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=False,
            boot_id_current=True,
        ),
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=1_000_000))
    history_after_first = _rows(db_path, "SELECT COUNT(*) FROM classification_history")
    assert history_after_first == [(2,)]

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=2_000_000))

    # No new history rows because nothing changed
    history_after_second = _rows(db_path, "SELECT COUNT(*) FROM classification_history")
    assert history_after_second == [(2,)]
    # last_scanned still advanced
    last_scanned = {
        r[0]: r[1] for r in _rows(db_path, "SELECT uuid, last_scanned FROM sessions")
    }
    assert all(v == 2_000_000 for v in last_scanned.values())


def test_classification_history_appends_when_classification_changes(
    tmp_path: Path,
) -> None:
    """Seed a row with one classification; scan produces a different one
    → history grows.

    M4: when a session's classification + reason genuinely change between
    scans, the append still happens. Seed a row at ``classification=live``
    for a UUID that the fixture actually classifies as ``hard_crash``
    (dead PID + tool_use_no_result, boot current). After scan,
    classification_history must hold 2 rows for that UUID — the seeded
    one and the new change.
    """
    uuid = "44444444-4444-4444-4444-444444444444"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd="/tmp/hardc-change",
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=False,
            boot_id_current=True,
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    # Find the JSONL the fixture wrote so the seeded row references it.
    jsonl_paths = list(projects_root.glob("*/*.jsonl"))
    assert len(jsonl_paths) == 1
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, '/tmp/hardc-change', '/tmp/hardc-change', ?, NULL, NULL,
                      'live', 'live_pid_present_boot_current', ?, NULL, 1, 1, NULL)
            """,
            (uuid, str(jsonl_paths[0]), CLASSIFIER_VERSION),
        )
        # Seed a matching history row for the initial state so we can
        # assert the count grows by exactly one after the change.
        conn.execute(
            """
            INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version)
            VALUES (1, '[]', 1, ?)
            """,
            (CLASSIFIER_VERSION,),
        )
        seeded_run_id = conn.execute(
            "SELECT id FROM scan_runs ORDER BY id LIMIT 1"
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO classification_history
            (uuid, scan_id, classification, reason, classifier_version)
            VALUES (?, ?, 'live', 'live_pid_present_boot_current', ?)
            """,
            (uuid, seeded_run_id, CLASSIFIER_VERSION),
        )
        conn.commit()
    finally:
        conn.close()

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=2_000_000))

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT classification, reason FROM classification_history "
            "WHERE uuid = ? ORDER BY scan_id",
            (uuid,),
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 2
    assert rows[0] == ("live", "live_pid_present_boot_current")
    assert rows[1] == ("hard_crash", "liveness_dead_pid_tool_use_no_result")


# ---------------------------------------------------------------------------
# AC2.1 / AC2.3 — forward-scan cwd repair in scan._first_entry_cwd
# ---------------------------------------------------------------------------


def test_scan_classifies_snapshot_prefixed_jsonl_not_missing_cwd(
    tmp_path: Path,
) -> None:
    """AC2.1: snapshot-prefixed JSONL (cwd on line 2) is NOT irrecoverable/missing_cwd.

    Before the fix, ``_first_entry_cwd`` read only line 1 and saw the snapshot
    record which carries no ``cwd``, so the session was classified as
    ``irrecoverable/missing_cwd``. After the fix, the forward scan finds the
    cwd on line 2 and classifies correctly.
    """
    uuid = "ac210001-0000-0000-0000-000000000001"
    cwd = "/tmp/ac21-snapshot-session"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd=cwd,
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
            cwd_on_first_line=False,  # snapshot-prefixed: cwd on line 2
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason, cwd"
            " FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    classification, reason, cwd_val = row
    # Must NOT be irrecoverable/missing_cwd.
    assert classification != "irrecoverable" or reason != "missing_cwd", (
        f"Expected forward scan to read cwd from line 2,"
        f" but got {classification}/{reason}. "
        "Snapshot-prefixed JSONL should not be classified as missing_cwd."
    )
    assert cwd_val == cwd, f"Expected cwd column to equal '{cwd}', got '{cwd_val}'"


def test_scan_genuine_no_cwd_jsonl_still_classifies_missing_cwd(
    tmp_path: Path,
) -> None:
    """AC2.3: JSONL with no ``cwd`` anywhere still yields irrecoverable/missing_cwd.

    The forward scan must not change behaviour for genuine no-cwd sessions
    — when no record in the scan window carries a ``cwd`` field, the session
    is still irrecoverable (genuine case preserved).
    """
    uuid = "ac230001-0000-0000-0000-000000000001"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    # Write a JSONL with only snapshot records — no cwd field anywhere.
    project_dir = projects_root / "-no-cwd-genuine"
    project_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = project_dir / f"{uuid}.jsonl"
    entries = [
        {
            "type": "snapshot",
            "messageId": f"msg_{i:03d}",
            "snapshot": {},
            "isSnapshotUpdate": False,
        }
        for i in range(3)
    ]
    jsonl_path.write_text("".join(json.dumps(e) + "\n" for e in entries))

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    classification, reason = row
    assert classification == "irrecoverable"
    assert reason == "missing_cwd"


# ---------------------------------------------------------------------------
# M5 — ambiguous state_summary uses pinned AMBIGUOUS_STATE_SUMMARY_PREFIX
# ---------------------------------------------------------------------------


def test_ambiguous_state_summary_uses_pinned_format(tmp_path: Path) -> None:
    """The ambiguous state_summary uses the AMBIGUOUS_STATE_SUMMARY_PREFIX constant.

    M5: phase 5 needs to parse this prefix to recognise an ambiguous row,
    so the format is pinned in a named module-level constant rather than
    a free-form f-string. Existing AC6.3 test only checks substring; this
    one pins the exact prefix + comma-joined candidates.
    """
    cwd = "/tmp/ambig-pinned"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)
    now_epoch = int(time.time())
    uuid_a = "aaaaaaaa-3333-3333-3333-333333333333"
    uuid_b = "bbbbbbbb-4444-4444-4444-444444444444"
    # Both first_entry_ts inside the Phase 3 tight window [started-60, started+120]
    # so the pair stays AMBIGUOUS (the pinned format under test).
    started = now_epoch - 3600
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 20,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=os.getpid(),
        cwd=cwd,
        started=started,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

    rows = _rows(
        db_path,
        "SELECT uuid, state_summary FROM sessions ORDER BY uuid",
    )
    assert len(rows) == 2
    expected = f"{scan_mod.AMBIGUOUS_STATE_SUMMARY_PREFIX}{uuid_a}, {uuid_b}"
    for _uuid, summary in rows:
        assert summary == expected


# ---------------------------------------------------------------------------
# AC3.1 / AC3.2 — dedup-safe scan (two markers resolving to one UUID)
# ---------------------------------------------------------------------------


def test_scan_dedup_two_markers_same_uuid_no_integrity_error(
    tmp_path: Path,
) -> None:
    """AC3.1: two .live files resolving to the same UUID → no IntegrityError, one row.

    Fixture design (following advisor guidance):
    - marker A: ``--resume X`` (DIRECT_MATCH for UUID X, dead pid, boot-current,
      TOOL_USE_NO_RESULT tail → hard_crash)
    - marker B: no ``--resume`` (AMBIGUOUS with candidates (X, Y), different pid)

    UUID X gets DIRECT_MATCH → hard_crash from marker A, and is also an
    AMBIGUOUS candidate from marker B → borderline/ambiguous_match. Before the
    dedup fix, the second ``_append_history(X, scan_id)`` hits the
    ``(uuid, scan_id)`` UNIQUE constraint and raises ``sqlite3.IntegrityError``.
    After the fix, exactly one fact per UUID is emitted, so no IntegrityError
    and exactly one ``sessions`` row + one ``classification_history`` row for X.
    """
    cwd = "/tmp/dedup-ac31"
    now_epoch = int(time.time())

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    from crash_recovery import liveness as liveness_mod
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Valid hex UUIDs (required by _extract_resume_uuid's _UUID_RE).
    uuid_x = "dd310001-0000-0000-0000-000000000001"
    uuid_y = "dd310001-0000-0000-0000-000000000002"

    # Both JSONLs have timestamps in the mtime window.
    first_entry_epoch = now_epoch - 3599  # within the started window
    _write_session_jsonl(
        project_dir / f"{uuid_x}.jsonl",
        cwd=cwd,
        first_entry_epoch=first_entry_epoch,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_y}.jsonl",
        cwd=cwd,
        first_entry_epoch=first_entry_epoch,
        tail_kind=TailKind.CONCLUDED,
    )

    real_boot_id = liveness_mod.current_boot_id()
    dead_pid = _pick_dead_pid()

    # Marker A: --resume uuid_x (DIRECT_MATCH), dead pid, boot current → hard_crash
    make_liveness_file(
        run_dir=run_dir,
        pid=dead_pid,
        cwd=cwd,
        started=now_epoch - 3600,
        argv=f"--resume {uuid_x}",
        boot_id=real_boot_id,
    )

    # Marker B: no --resume (mtime window → AMBIGUOUS with both uuid_x and uuid_y)
    # Use a different (also dead) pid so the .live filenames differ.
    make_liveness_file(
        run_dir=run_dir,
        pid=dead_pid + 1,
        cwd=cwd,
        started=now_epoch - 3600,
        argv="",
        boot_id=real_boot_id,
    )

    # Before dedup fix this raises sqlite3.IntegrityError.
    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

    # Exactly one sessions row for uuid_x.
    count_x = _rows(
        db_path,
        f"SELECT COUNT(*) FROM sessions WHERE uuid = '{uuid_x}'",
    )
    assert count_x == [(1,)], f"expected 1 sessions row for uuid_x, got {count_x}"

    # Exactly one history row for uuid_x in this scan.
    count_hist = _rows(
        db_path,
        f"SELECT COUNT(*) FROM classification_history WHERE uuid = '{uuid_x}'",
    )
    assert count_hist == [(1,)], f"expected 1 history row for uuid_x, got {count_hist}"


def test_scan_dedup_direct_match_wins_over_ambiguous(
    tmp_path: Path,
) -> None:
    """AC3.2: when UUID X is a DIRECT_MATCH from marker A and an AMBIGUOUS
    candidate from marker B, the persisted row reflects the direct-match fact.

    The direct-match classification (hard_crash from dead-pid +
    TOOL_USE_NO_RESULT) must win over the ambiguous-match classification
    (borderline/ambiguous_match). Precedence rank: DIRECT=0, MTIME=1,
    AMBIGUOUS=2 — lower rank wins on collision.
    """
    cwd = "/tmp/dedup-ac32"
    now_epoch = int(time.time())

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    from crash_recovery import liveness as liveness_mod
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Valid hex UUIDs (required by _extract_resume_uuid's _UUID_RE).
    uuid_x = "dd320002-0000-0000-0000-000000000001"
    uuid_y = "dd320002-0000-0000-0000-000000000002"

    first_entry_epoch = now_epoch - 3599
    _write_session_jsonl(
        project_dir / f"{uuid_x}.jsonl",
        cwd=cwd,
        first_entry_epoch=first_entry_epoch,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_y}.jsonl",
        cwd=cwd,
        first_entry_epoch=first_entry_epoch,
        tail_kind=TailKind.CONCLUDED,
    )

    real_boot_id = liveness_mod.current_boot_id()
    dead_pid = _pick_dead_pid()

    # Marker A: DIRECT_MATCH for uuid_x (dead pid, boot current)
    make_liveness_file(
        run_dir=run_dir,
        pid=dead_pid,
        cwd=cwd,
        started=now_epoch - 3600,
        argv=f"--resume {uuid_x}",
        boot_id=real_boot_id,
    )

    # Marker B: AMBIGUOUS (uuid_x and uuid_y are both in the mtime window)
    make_liveness_file(
        run_dir=run_dir,
        pid=dead_pid + 1,
        cwd=cwd,
        started=now_epoch - 3600,
        argv="",
        boot_id=real_boot_id,
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

    row = _rows(
        db_path,
        f"SELECT classification, classification_reason FROM sessions "
        f"WHERE uuid = '{uuid_x}'",
    )
    assert len(row) == 1, f"expected 1 row for uuid_x, got {row}"
    classification, reason = row[0]
    # Direct-match (hard_crash) must win over ambiguous-match (borderline).
    assert classification == "hard_crash", (
        f"Expected direct-match hard_crash to win; got {classification}/{reason}. "
        "AMBIGUOUS precedence must not override DIRECT_MATCH."
    )
    assert reason == "liveness_dead_pid_tool_use_no_result"


def test_scan_dedup_same_rank_live_beats_dead_order_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F1 (coherence review): on a same-rank, same-UUID dedup collision, a LIVE
    fact (pid alive on the current boot) must win over a dead one — a running
    session must never be persisted as ``hard_crash`` because a crashed sibling's
    path sorts first — and the winner must not depend on ``list_liveness_files``
    iteration order (load-bearing for Phase 4's byte-identical render).

    The AC3.1/AC3.2 tests only collide DIRECT_MATCH (rank 0) against AMBIGUOUS
    (rank 2), so the same-rank tie-break never executes. Here both markers are
    ``--resume uuid_x`` → both DIRECT_MATCH (genuine rank-0 vs rank-0). The DEAD
    marker is deliberately given the lexicographically SMALLER path, so a
    path-only tie-break would (wrongly) pick it → ``hard_crash``. The fix must
    instead pick the LIVE marker → ``live``. Liveness objects are built directly
    and the iterator is monkeypatched so path order is decoupled from pid and
    fully controlled.
    """
    cwd = "/tmp/dedup-live-beats-dead"
    now_epoch = int(time.time())
    _db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])

    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)

    uuid_x = "dd440004-0000-0000-0000-000000000001"
    _write_session_jsonl(
        project_dir / f"{uuid_x}.jsonl",
        cwd=cwd,
        first_entry_epoch=now_epoch - 3599,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )

    real_boot_id = liveness_mod.current_boot_id()

    # Both DIRECT_MATCH uuid_x (rank 0). The DEAD marker gets the smaller path so
    # a path-only tie-break picks it (→ hard_crash); the LIVE marker must win.
    dead_lv = liveness_mod.Liveness(
        path=run_dir / "00000001.live",  # sorts first
        pid=_pick_dead_pid(),
        cwd=cwd,
        started=now_epoch - 3600,
        argv=f"--resume {uuid_x}",
        boot_id=real_boot_id,
    )
    live_lv = liveness_mod.Liveness(
        path=run_dir / "99999999.live",  # sorts last
        pid=os.getpid(),  # alive on the current boot
        cwd=cwd,
        started=now_epoch - 3600,
        argv=f"--resume {uuid_x}",
        boot_id=real_boot_id,
    )

    results: list[tuple] = []
    for i, order in enumerate(([dead_lv, live_lv], [live_lv, dead_lv])):
        db_dir = tmp_path / f"db_run_{i}"
        db_dir.mkdir()
        db_path = _init_db(db_dir)
        monkeypatch.setattr(
            scan_mod, "list_liveness_files", lambda _rd, _o=order: iter(_o)
        )
        scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

        rows = _rows(
            db_path,
            "SELECT classification, classification_reason FROM sessions "
            f"WHERE uuid = '{uuid_x}'",
        )
        assert len(rows) == 1, f"run {i}: expected 1 row for uuid_x, got {rows}"
        results.append(rows[0])

    # Order-independence: same winner regardless of iteration order.
    assert results[0] == results[1], (
        f"order-dependent dedup: forward {results[0]!r} vs reversed {results[1]!r}"
    )
    classification, reason = results[0]
    # F1: the LIVE marker must win even though the dead marker's path sorts first.
    assert classification != "hard_crash", (
        "a live session was persisted as a crash victim — the dead sibling won "
        "the same-rank tie-break"
    )
    assert reason == "live_pid_present_boot_current", (
        "expected the live marker to win the same-rank tie; "
        f"got {classification}/{reason}"
    )


# ---------------------------------------------------------------------------
# AC1.1 — end-to-end: snapshot-prefixed crash victim surfaces as hard_crash
# ---------------------------------------------------------------------------


def test_snapshot_prefixed_crash_victim_surfaces_as_hard_crash(
    tmp_path: Path,
) -> None:
    """AC1.1: snapshot-prefixed JSONL + dead-PID/boot-current + --resume marker
    → run_scan → hard_crash (reason liveness_dead_pid_tool_use_no_result).

    This is the Phase 1 capstone integration test. It exercises the full chain:

    1. Task 1 fixture builder: JSONL written with snapshot record on line 1,
       cwd+timestamp on line 2 (``cwd_on_first_line=False``).
    2. Task 3 fix: ``_first_entry_cwd`` forward-scans past the snapshot to
       find cwd on line 2, so the session is NOT classified
       ``irrecoverable/missing_cwd``.
    3. Task 4 fix: ``correlate`` forward-scans the cwd from the JSONL so
       ``_project_dir_for_cwd`` finds the project directory → DIRECT_MATCH
       via ``--resume <uuid>``.
    4. Phase 2 classify: dead PID + boot current + TOOL_USE_NO_RESULT tail
       → ``hard_crash`` / ``liveness_dead_pid_tool_use_no_result``.

    Pre-fix behaviour (Tasks 1-4 not applied): the snapshot record on line 1
    carries no ``cwd``, so ``_first_entry_cwd`` returned ``""`` and the session
    was classified ``irrecoverable/missing_cwd``. With the fix the victim
    surfaces correctly.

    This test passes immediately (no RED phase) because it exercises completed
    functionality from Tasks 1-4 — it is an acceptance test, not a
    regression-guard for new code.
    """
    uuid = "ac110001-0000-0000-0000-000000000001"
    cwd = "/tmp/ac11-crash-victim"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd=cwd,
            tail_kind=TailKind.TOOL_USE_NO_RESULT,
            has_liveness=True,
            pid_alive=False,  # dead PID → not live
            boot_id_current=True,  # boot matches → crash, not stale-boot
            cwd_on_first_line=False,  # snapshot-prefixed: cwd on line 2
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT classification, classification_reason, cwd "
            "FROM sessions WHERE uuid = ?",
            (uuid,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "Expected a sessions row for the crash victim"
    classification, reason, cwd_val = row

    # The victim must NOT be buried as missing_cwd (pre-fix behaviour).
    assert classification != "irrecoverable" or reason != "missing_cwd", (
        f"Snapshot-prefixed crash victim was classified as {classification}/{reason}. "
        "The forward-scan fix should have found cwd on line 2."
    )

    # The victim must surface as hard_crash with the dead-pid tail reason.
    assert classification == "hard_crash", (
        f"Expected hard_crash for dead-pid crash victim; got {classification}/{reason}"
    )
    assert reason == "liveness_dead_pid_tool_use_no_result", (
        f"Expected liveness_dead_pid_tool_use_no_result; got {reason}"
    )

    # The cwd column must hold the real cwd, not empty string.
    assert cwd_val == cwd, f"Expected cwd column '{cwd}', got '{cwd_val}'"


# ---------------------------------------------------------------------------
# AC6.2 — scan integration: tmux-resurrect corroboration resolves a
# multi-cwd backlog candidate set to the single corroborated survivor.
# ---------------------------------------------------------------------------


def _write_resurrect_snapshot(
    resurrect_dir: Path, stamp_epoch: int, pane_cwds: list[str]
) -> Path:
    """Write a temp ``tmux_resurrect_<stamp>.txt`` with one ``pane`` line per cwd.

    The stamp is built from ``stamp_epoch`` as **naive local time** so it round-
    trips through ``resurrect._ts_from_filename`` (which interprets the filename
    stamp in the system local zone). Each pane line mirrors the real TAB layout
    (11 fields, path at index 7 with a leading ``:``); the first pane carries the
    ``✳`` idle-claude title prefix to match real snapshots, though corroboration
    is path-based and never gates on the glyph.
    """
    from datetime import datetime as _dt

    resurrect_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.fromtimestamp(stamp_epoch).strftime("%Y%m%dT%H%M%S")
    lines = []
    for i, cwd in enumerate(pane_cwds):
        title = f"✳ session {i}"
        # [0]pane [1]session [2]window [3]idx [4]flags [5]1 [6]title
        # [7]:cwd [8]1 [9]command [10]:shell
        lines.append(
            "\t".join(
                [
                    "pane",
                    "1",
                    str(i),
                    "1",
                    ":*",
                    "1",
                    title,
                    f":{cwd}",
                    "1",
                    "bash",
                    ":/usr/bin/fish -l",
                ]
            )
        )
    path = resurrect_dir / f"tmux_resurrect_{stamp}.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_scan_corroborates_multi_cwd_candidates_via_resurrect(
    tmp_path: Path,
) -> None:
    """AC6.2: two in-window candidates with distinct cwds share one lossy encoded
    dir; a resurrect snapshot whose only star-pane path matches cwd A resolves the
    backlog marker to candidate A (``hard_crash`` via MTIME_MATCH), not borderline.

    The corroboration filter keeps the candidate whose own first-entry cwd is in
    the snapshot's pane cwds. Only cwd A is present, so exactly one candidate
    survives → the marker resolves to A as a concrete crash (``hard_crash`` /
    ``liveness_dead_pid_tool_use_no_result``), NOT ``borderline/ambiguous_match``.

    Candidate B does not disappear: its JSONL is on disk, so the always-on
    JSONL-only sweep still emits a row for it — but classified on its OWN tail
    shape (no liveness marker), so its reason is NOT ``ambiguous_match``. That is
    the whole point of corroboration: the marker no longer drags B into its
    ambiguity set; B is judged independently.
    """
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _write_session_jsonl,
        make_liveness_file,
    )

    cwd_a = "/tmp/corrob/a-b"
    cwd_b = "/tmp/corrob-a/b"  # distinct cwd, same lossy encoded dir as cwd_a
    assert _encoded_dir_name_for(cwd_a) == _encoded_dir_name_for(cwd_b), (
        "fixture invariant: both cwds must collapse to one encoded dir"
    )

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    project_dir = projects_root / _encoded_dir_name_for(cwd_a)
    project_dir.mkdir(parents=True, exist_ok=True)

    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid_a = "aaaaaaaa-3333-3333-3333-333333333333"
    uuid_b = "bbbbbbbb-4444-4444-4444-444444444444"
    # Both first-entry-ts land inside the tight window [started-60, started+120].
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd_a,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd_b,
        first_entry_epoch=started + 20,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )
    # Liveness marker: dead PID, boot current, no --resume (mtime-window path).
    from fixtures.jsonl_builder import _pick_dead_pid

    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd_a,
        started=started,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    # Resurrect snapshot at/just before started, whose only pane sits at cwd A.
    resurrect_dir = tmp_path / "byobu-sessions"
    _write_resurrect_snapshot(resurrect_dir, started - 60, [cwd_a])

    scan_mod.run_scan(
        _make_ctx(
            db_path, run_dir, projects_root, now=now_epoch, resurrect_dir=resurrect_dir
        )
    )

    rows = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason FROM sessions",
    )
    by_uuid = {r[0]: (r[1], r[2]) for r in rows}
    # The marker resolved to A as a concrete crash via corroboration.
    assert uuid_a in by_uuid, "candidate A must have a sessions row"
    a_classification, a_reason = by_uuid[uuid_a]
    assert a_classification == "hard_crash", (
        f"Expected hard_crash via corroborated MTIME_MATCH for A; "
        f"got {a_classification}/{a_reason}"
    )
    assert a_reason == "liveness_dead_pid_tool_use_no_result", (
        f"Expected dead-pid crash reason for A; got {a_reason}"
    )
    # Neither row is the ambiguous-match verdict: corroboration narrowed the
    # marker to one survivor, so the marker is no longer ambiguous, and B is
    # judged on its own tail shape rather than dragged into A's candidate set.
    for u, (_, reason) in by_uuid.items():
        assert reason != "ambiguous_match", (
            f"{u} was classified ambiguous_match; corroboration should have "
            f"resolved the marker to a single survivor"
        )


def test_scan_no_resurrect_snapshot_stays_ambiguous_all_candidates(
    tmp_path: Path,
) -> None:
    """AC6.3 path under scan: with an empty (non-existent) resurrect dir and two
    in-window candidates, corroboration is a no-op → both stay
    ``borderline/ambiguous_match`` with every candidate listed in state_summary.

    This is the back-compat guarantee: no snapshots → identical behaviour to
    pre-Phase-3 (single → MTIME_MATCH, multiple → ambiguous-all).
    """
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    cwd = "/tmp/corrob-none"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)
    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid_a = "aaaaaaaa-5555-5555-5555-555555555555"
    uuid_b = "bbbbbbbb-6666-6666-6666-666666666666"
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 20,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd,
        started=started,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    # resurrect_dir points at a path that does not exist → load_snapshots == [].
    missing_resurrect = tmp_path / "no-such-byobu-dir"
    scan_mod.run_scan(
        _make_ctx(
            db_path,
            run_dir,
            projects_root,
            now=now_epoch,
            resurrect_dir=missing_resurrect,
        )
    )

    rows = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason, state_summary "
        "FROM sessions",
    )
    by_uuid = {r[0]: (r[1], r[2], r[3]) for r in rows}
    assert set(by_uuid.keys()) == {uuid_a, uuid_b}
    for u in (uuid_a, uuid_b):
        classification, reason, summary = by_uuid[u]
        assert classification == "borderline"
        assert reason == "ambiguous_match"
        other = uuid_b if u == uuid_a else uuid_a
        assert other in summary, "all candidates must be listed (all-means-all)"


# ---------------------------------------------------------------------------
# CRASH_RECOVERY_RESURRECT_DIR env-var / --resurrect-dir CLI resolution
# ---------------------------------------------------------------------------


def test_resurrect_dir_env_var_is_consumed_end_to_end(tmp_path: Path) -> None:
    """CRASH_RECOVERY_RESURRECT_DIR reaches _walk_sessions via the CLI.

    Drives ``crash-recovery scan`` through ``subprocess`` (the real ``_resolve``
    path) rather than constructing a ``ScanContext`` directly, so the env-var →
    ``_resolve`` → ``ScanContext.resurrect_dir`` → ``_walk_sessions`` chain is
    exercised.

    Fixture: two in-window candidates sharing one lossy-encoded project dir
    (``/tmp/rdir-env/a-b`` and ``/tmp/rdir-env-a/b``), a backlog liveness marker
    with a dead PID (no ``--resume``, so the mtime-window path runs), and a
    resurrect snapshot dir containing one pane at cwd A.

    With ``CRASH_RECOVERY_RESURRECT_DIR`` pointing at the snapshot dir,
    corroboration narrows the marker to candidate A → ``hard_crash``.
    With an empty snapshot dir, corroboration is a no-op → both candidates stay
    ``borderline/ambiguous_match``.
    """
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    cwd_a = "/tmp/rdir-env/a-b"
    cwd_b = "/tmp/rdir-env-a/b"  # distinct cwd, same lossy encoded dir as cwd_a
    assert _encoded_dir_name_for(cwd_a) == _encoded_dir_name_for(cwd_b), (
        "fixture invariant: both cwds must collapse to one encoded dir"
    )

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    project_dir = projects_root / _encoded_dir_name_for(cwd_a)
    project_dir.mkdir(parents=True, exist_ok=True)

    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid_a = "aaaaaaaa-7777-7777-7777-777777777777"
    uuid_b = "bbbbbbbb-8888-8888-8888-888888888888"

    # Both first-entry-ts land inside the tight window [started-60, started+120].
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd_a,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd_b,
        first_entry_epoch=started + 20,
        tail_kind=TailKind.TOOL_USE_NO_RESULT,
    )

    # Liveness marker: dead PID, boot current, no --resume (mtime-window path).
    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd_a,
        started=started,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    # Corroborating snapshot dir: one pane at cwd A only.
    resurrect_dir = tmp_path / "byobu-sessions-env"
    _write_resurrect_snapshot(resurrect_dir, started - 60, [cwd_a])

    # Empty dir used for discrimination evidence (no snapshots → ambiguous).
    empty_resurrect_dir = tmp_path / "byobu-sessions-empty"
    empty_resurrect_dir.mkdir(parents=True, exist_ok=True)

    base_env = {
        **os.environ,
        "CRASH_RECOVERY_DB": str(db_path),
        "CRASH_RECOVERY_RUN_DIR": str(run_dir),
        "CRASH_RECOVERY_PROJECTS_ROOT": str(projects_root),
    }

    # --- Discrimination check: empty dir → both stay AMBIGUOUS ---------------
    proc_empty = subprocess.run(
        [sys.executable, "-m", "crash_recovery", "scan"],
        env={**base_env, "CRASH_RECOVERY_RESURRECT_DIR": str(empty_resurrect_dir)},
        capture_output=True,
        timeout=30,
    )
    assert proc_empty.returncode == 0, (proc_empty.stdout, proc_empty.stderr)
    rows_empty = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason FROM sessions",
    )
    by_uuid_empty = {r[0]: (r[1], r[2]) for r in rows_empty}
    assert by_uuid_empty.get(uuid_a, (None,))[0] == "borderline", (
        "empty resurrect dir: expected borderline for A;"
        f" got {by_uuid_empty.get(uuid_a)}"
    )
    assert by_uuid_empty.get(uuid_b, (None,))[0] == "borderline", (
        "empty resurrect dir: expected borderline for B;"
        f" got {by_uuid_empty.get(uuid_b)}"
    )

    # --- Main assertion: corroborating dir → A resolves to hard_crash --------
    proc_corrob = subprocess.run(
        [sys.executable, "-m", "crash_recovery", "scan"],
        env={**base_env, "CRASH_RECOVERY_RESURRECT_DIR": str(resurrect_dir)},
        capture_output=True,
        timeout=30,
    )
    assert proc_corrob.returncode == 0, (proc_corrob.stdout, proc_corrob.stderr)
    rows_corrob = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason FROM sessions",
    )
    by_uuid_corrob = {r[0]: (r[1], r[2]) for r in rows_corrob}
    assert uuid_a in by_uuid_corrob, "candidate A must have a sessions row"
    a_cls, a_reason = by_uuid_corrob[uuid_a]
    assert a_cls == "hard_crash", (
        f"expected hard_crash for A after corroboration via env var; "
        f"got {a_cls}/{a_reason}"
    )
    assert a_reason == "liveness_dead_pid_tool_use_no_result", (
        f"expected dead-pid crash reason; got {a_reason}"
    )
    for u, (_, reason) in by_uuid_corrob.items():
        assert reason != "ambiguous_match", (
            f"{u} still ambiguous_match after env-var-provided corroborating snapshot"
        )


# ---------------------------------------------------------------------------
# AC5.2 (population half) — scan populates pane_title + last_substantive
# (Phase 4 Task 3 / Subcomponent B)
# ---------------------------------------------------------------------------


def test_scan_populates_pane_title_and_last_substantive(tmp_path: Path) -> None:
    """AC5.2: a liveness-matched session with a corroborating snapshot at its cwd
    stores the snapshot's pane label in ``pane_title`` and the JSONL's last real
    text in ``last_substantive``.

    Fixture: one ``--resume <uuid>`` marker (DIRECT_MATCH), a CONCLUDED tail (so
    ``last_substantive_text`` returns the assistant text ``"done"``), and a
    resurrect snapshot whose single pane sits at the session's cwd with the
    ``✳ session 0`` title. After scan, ``pane_title == "✳ session 0"`` and
    ``last_substantive == "done"``.
    """
    cwd = "/tmp/pane-title-match"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)
    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid = "aaaaaaaa-9999-9999-9999-999999999999"
    _write_session_jsonl(
        project_dir / f"{uuid}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd,
        started=started,
        argv=f"--resume {uuid}",
        boot_id=liveness_mod.current_boot_id(),
    )

    resurrect_dir = tmp_path / "byobu-sessions"
    _write_resurrect_snapshot(resurrect_dir, started - 60, [cwd])

    scan_mod.run_scan(
        _make_ctx(
            db_path, run_dir, projects_root, now=now_epoch, resurrect_dir=resurrect_dir
        )
    )

    rows = _rows(
        db_path,
        "SELECT pane_title, last_substantive FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert len(rows) == 1
    pane_title, last_substantive = rows[0]
    assert pane_title == "✳ session 0", (
        f"expected the snapshot pane label; got {pane_title!r}"
    )
    assert last_substantive == "done", (
        f"expected the JSONL's last real text; got {last_substantive!r}"
    )


def test_rescan_refreshes_pane_title_and_last_substantive(tmp_path: Path) -> None:
    """ON CONFLICT(uuid) DO UPDATE refreshes ``pane_title`` + ``last_substantive``.

    Every other scan test does a single scan, so only the INSERT branch of
    ``_upsert_session`` is exercised — the DO UPDATE SET clause for the two
    Phase-4 columns is unproven. This test scans the SAME session twice with
    the inputs changed between scans so a faithful UPDATE must overwrite both
    stored values:

    * Scan 1 derives ``pane_title == "✳ session 0"`` (A) from a resurrect
      snapshot whose single pane sits at the session's cwd, and
      ``last_substantive == "done"`` (X) from the CONCLUDED tail — same shape
      as ``test_scan_populates_pane_title_and_last_substantive``.
    * Between scans the snapshot is rewritten (same stamp, so ``snapshot_near``
      still selects it) with the session's cwd at pane index 1, so
      ``label_for_cwd`` returns ``"✳ session 1"`` (B); and a fresh substantive
      ``end_turn`` turn (text ``"redone"``, Y) is appended to the JSONL so
      ``last_substantive_text`` returns it. The tail stays CONCLUDED and the
      ``--resume`` marker keeps the correlation a DIRECT_MATCH, so the second
      scan upserts the same uuid row → the DO UPDATE SET branch.
    * Scan 2 must leave the row holding B / Y, not the stale A / X.

    If ``pane_title`` / ``last_substantive`` are dropped from the DO UPDATE SET
    clause, the row keeps its first-INSERT A / X and both assertions fail — the
    mutation check that gives this test its teeth.
    """
    cwd = "/tmp/rescan-refresh-match"
    other_cwd = "/tmp/rescan-refresh-other"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)
    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid = "aaaaaaaa-7777-7777-7777-777777777777"
    jsonl_path = project_dir / f"{uuid}.jsonl"
    _write_session_jsonl(
        jsonl_path,
        cwd=cwd,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd,
        started=started,
        argv=f"--resume {uuid}",
        boot_id=liveness_mod.current_boot_id(),
    )

    resurrect_dir = tmp_path / "byobu-sessions"
    # Scan-1 snapshot: cwd at pane index 0 → label "✳ session 0" (A).
    _write_resurrect_snapshot(resurrect_dir, started - 60, [cwd])

    scan_mod.run_scan(
        _make_ctx(
            db_path, run_dir, projects_root, now=now_epoch, resurrect_dir=resurrect_dir
        )
    )

    rows = _rows(
        db_path,
        "SELECT pane_title, last_substantive FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert len(rows) == 1
    pane_title_a, last_substantive_x = rows[0]
    assert pane_title_a == "✳ session 0", (
        f"scan 1 should store the snapshot pane label; got {pane_title_a!r}"
    )
    assert last_substantive_x == "done", (
        f"scan 1 should store the JSONL's last real text; got {last_substantive_x!r}"
    )

    # Change both inputs so a faithful re-scan derives DIFFERENT values.
    # pane_title B: rewrite the snapshot (same stamp → snapshot_near still
    # picks it) with the cwd at pane index 1 so label_for_cwd skips the
    # non-matching other_cwd at index 0 and returns "✳ session 1".
    _write_resurrect_snapshot(resurrect_dir, started - 60, [other_cwd, cwd])
    # last_substantive Y: append a fresh substantive end_turn turn. "redone"
    # is non-empty and not a bookkeeping marker, so last_substantive_text
    # returns it; the end_turn shape keeps the tail CONCLUDED.
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "type": "assistant",
                    "timestamp": "2026-01-01T00:00:00.000Z",
                    "message": {
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": "redone"}],
                    },
                }
            )
            + "\n"
        )

    # Second scan of the SAME session → ON CONFLICT(uuid) DO UPDATE branch.
    scan_mod.run_scan(
        _make_ctx(
            db_path, run_dir, projects_root, now=now_epoch, resurrect_dir=resurrect_dir
        )
    )

    rows = _rows(
        db_path,
        "SELECT pane_title, last_substantive FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert len(rows) == 1, "rescan must update the existing row, not insert a new one"
    pane_title_b, last_substantive_y = rows[0]
    assert pane_title_b == "✳ session 1", (
        f"rescan should refresh pane_title to the new snapshot label (B); "
        f"got {pane_title_b!r} (stale A was {pane_title_a!r})"
    )
    assert last_substantive_y == "redone", (
        f"rescan should refresh last_substantive to the appended turn (Y); "
        f"got {last_substantive_y!r} (stale X was {last_substantive_x!r})"
    )


def test_scan_jsonl_only_session_populates_last_substantive_not_pane_title(
    tmp_path: Path,
) -> None:
    """A JSONL-only session (no liveness marker) gets ``last_substantive`` from the
    JSONL but a NULL ``pane_title`` (no ``started`` anchor → no snapshot).

    The JSONL-only walk has no liveness marker and thus no ``started`` to anchor
    ``snapshot_near``; ``_walk_jsonl_only`` hardcodes ``pane_title=None``.
    ``last_substantive`` is still extracted from the JSONL's CONCLUDED tail.
    """
    uuid = "bbbbbbbb-9999-9999-9999-999999999999"
    cwd = "/tmp/jsonl-only-substantive"
    sessions = [
        FixtureSession(
            uuid=uuid,
            cwd=cwd,
            tail_kind=TailKind.CONCLUDED,
            has_liveness=False,
            pid_alive=None,
            boot_id_current=False,
        )
    ]
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, sessions)
    db_path = _init_db(db_dir)

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root))

    rows = _rows(
        db_path,
        "SELECT pane_title, last_substantive FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert len(rows) == 1
    pane_title, last_substantive = rows[0]
    assert pane_title is None, (
        "jsonl-only session has no snapshot anchor → NULL pane_title;"
        f" got {pane_title!r}"
    )
    assert last_substantive == "done", (
        f"expected the JSONL's last real text; got {last_substantive!r}"
    )


def test_scan_pane_title_is_per_candidate_cwd_not_liveness_cwd(
    tmp_path: Path,
) -> None:
    """AC5.2 (per-candidate cwd, CA2): each AMBIGUOUS candidate's ``pane_title`` is
    labelled by ITS OWN first-entry cwd, never by ``liveness.cwd``.

    Two candidates share one lossy-collided encoded dir but declare distinct cwds
    (``cwd_a``, ``cwd_b``). A resurrect snapshot carries a pane at BOTH cwds, so
    corroboration keeps both survivors → the marker stays AMBIGUOUS (verdict for
    a >1-survivor set, per ``_apply_corroboration``). The snapshot labels each cwd
    differently (``✳ session 0`` for ``cwd_a``, ``✳ session 1`` for ``cwd_b``).

    The regression this guards: labelling by ``liveness.cwd`` (== ``cwd_a``) would
    attach ``✳ session 0`` to BOTH candidate rows. The contract is that candidate
    B's row carries ``✳ session 1`` — its own cwd's label — proving the lookup
    reads each candidate's OWN first-entry cwd.
    """
    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    cwd_a = "/tmp/cand-cwd/a-b"
    cwd_b = "/tmp/cand-cwd-a/b"  # distinct cwd, same lossy encoded dir as cwd_a
    assert _encoded_dir_name_for(cwd_a) == _encoded_dir_name_for(cwd_b), (
        "fixture invariant: both cwds must collapse to one encoded dir"
    )

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    project_dir = projects_root / _encoded_dir_name_for(cwd_a)
    project_dir.mkdir(parents=True, exist_ok=True)

    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid_a = "aaaaaaaa-1212-1212-1212-121212121212"
    uuid_b = "bbbbbbbb-3434-3434-3434-343434343434"
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd_a,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd_b,
        first_entry_epoch=started + 20,
        tail_kind=TailKind.CONCLUDED,
    )
    # Backlog marker (no --resume) whose cwd is cwd_a → liveness.cwd == cwd_a.
    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd_a,
        started=started,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    # Snapshot carries a pane at BOTH cwds, so BOTH candidates survive
    # corroboration → marker stays AMBIGUOUS. Pane index drives the label:
    # cwd_a → "✳ session 0", cwd_b → "✳ session 1".
    resurrect_dir = tmp_path / "byobu-sessions"
    _write_resurrect_snapshot(resurrect_dir, started - 60, [cwd_a, cwd_b])

    scan_mod.run_scan(
        _make_ctx(
            db_path, run_dir, projects_root, now=now_epoch, resurrect_dir=resurrect_dir
        )
    )

    rows = _rows(
        db_path,
        "SELECT uuid, classification, classification_reason, pane_title FROM sessions",
    )
    by_uuid = {r[0]: (r[1], r[2], r[3]) for r in rows}
    assert set(by_uuid.keys()) == {uuid_a, uuid_b}, (
        f"both candidates must stay AMBIGUOUS (two rows); got {set(by_uuid)}"
    )
    # Both candidates are borderline/ambiguous_match (corroboration kept both).
    for u in (uuid_a, uuid_b):
        classification, reason, _ = by_uuid[u]
        assert classification == "borderline" and reason == "ambiguous_match", (
            f"{u}: expected borderline/ambiguous_match; got {classification}/{reason}. "
            "If this is hard_crash or one row only, the CA2 ambiguity setup is broken."
        )
    # CA2 contract: each candidate's pane_title matches ITS OWN cwd's pane label.
    assert by_uuid[uuid_a][2] == "✳ session 0", (
        "candidate A's pane_title should be its own cwd's label;"
        f" got {by_uuid[uuid_a][2]!r}"
    )
    assert by_uuid[uuid_b][2] == "✳ session 1", (
        f"candidate B's pane_title should be its OWN cwd's label (✳ session 1), "
        f"not liveness.cwd's (✳ session 0); got {by_uuid[uuid_b][2]!r}. "
        "A regression to liveness.cwd would label both rows ✳ session 0."
    )


def test_scan_no_snapshot_leaves_pane_title_null_without_crashing(
    tmp_path: Path,
) -> None:
    """No-snapshot safety: a marker with an empty/non-existent resurrect dir →
    ``snapshot_near`` is None → ``label_for_cwd(None, ...)`` → NULL ``pane_title``,
    and scan does not crash.

    Exercises the Phase-3-hardened ``label_for_cwd(None, ...)`` path end-to-end:
    with no resurrect snapshots, the per-candidate label lookup degrades to NULL
    rather than raising. ``last_substantive`` is still populated from the JSONL.
    """
    cwd = "/tmp/no-snapshot-safety"
    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)

    from fixtures.jsonl_builder import (
        _encoded_dir_name_for,
        _pick_dead_pid,
        _write_session_jsonl,
        make_liveness_file,
    )

    project_dir = projects_root / _encoded_dir_name_for(cwd)
    project_dir.mkdir(parents=True, exist_ok=True)
    now_epoch = int(time.time())
    started = now_epoch - 3600
    uuid = "cccccccc-9999-9999-9999-999999999999"
    _write_session_jsonl(
        project_dir / f"{uuid}.jsonl",
        cwd=cwd,
        first_entry_epoch=started + 10,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=_pick_dead_pid(),
        cwd=cwd,
        started=started,
        argv=f"--resume {uuid}",
        boot_id=liveness_mod.current_boot_id(),
    )

    # resurrect_dir points at a path that does not exist → load_snapshots == []
    # → snapshot_near is None → label_for_cwd(None, ...) is None.
    missing_resurrect = tmp_path / "no-such-byobu-dir"
    scan_mod.run_scan(
        _make_ctx(
            db_path,
            run_dir,
            projects_root,
            now=now_epoch,
            resurrect_dir=missing_resurrect,
        )
    )

    rows = _rows(
        db_path,
        "SELECT pane_title, last_substantive FROM sessions WHERE uuid = '" + uuid + "'",
    )
    assert len(rows) == 1
    pane_title, last_substantive = rows[0]
    assert pane_title is None, (
        f"no snapshot → NULL pane_title (no crash); got {pane_title!r}"
    )
    assert last_substantive == "done", (
        f"expected the JSONL's last real text; got {last_substantive!r}"
    )


# ---------------------------------------------------------------------------
# Schema-current assertion: scan refuses un-migrated DB cleanly
# ---------------------------------------------------------------------------

# Old-shape sessions DDL: the column set before pane_title/last_substantive.
# Duplicated from test_init.py deliberately — this test must be self-contained
# and must not import from another test module.
_OLD_SHAPE_SESSIONS_DDL_SCAN = """
CREATE TABLE sessions (
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
    user_notes            TEXT
)
"""


def _build_old_shape_db_for_scan(path: Path) -> None:
    """Create a WAL-mode DB whose ``sessions`` table lacks the new columns."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(_OLD_SHAPE_SESSIONS_DDL_SCAN)
        conn.commit()
    finally:
        conn.close()


def test_scan_refuses_unmigrated_db_with_clean_error(tmp_path: Path) -> None:
    """scan against an un-migrated DB raises a clean RuntimeError, not a raw
    sqlite3.OperationalError, and leaves no partial write.

    The assertion lives in open_db() — scan calls open_db before any write, so
    the RuntimeError fires before any session or scan_runs row is written.
    After the error the schema must be unchanged (open_db did not add columns).
    """
    db_path = tmp_path / "old-shape.db"
    _build_old_shape_db_for_scan(db_path)

    # Empty projects root — scan walk finds nothing, but open_db fires first.
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    projects_root = tmp_path / "projects"
    projects_root.mkdir()

    ctx = scan_mod.ScanContext(
        db_path=db_path,
        run_dir=run_dir,
        projects_root=projects_root,
        now=1_000_000,
        resurrect_dir=tmp_path / "no-resurrect",
    )

    with pytest.raises(RuntimeError, match="crash-recovery init"):
        scan_mod.run_scan(ctx)

    # open_db must not have added the columns — schema on disk untouched.
    raw = sqlite3.connect(db_path)
    try:
        cols = {row[1] for row in raw.execute("PRAGMA table_info(sessions)")}
        # No scan_runs table should exist (was never created in old-shape DB).
        tables = {
            row[0]
            for row in raw.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        raw.close()

    assert "pane_title" not in cols, "open_db must not have migrated pane_title"
    assert "last_substantive" not in cols, (
        "open_db must not have migrated last_substantive"
    )
    assert "scan_runs" not in tables, "no scan_runs row must have been written"


# ---------------------------------------------------------------------------
# Part 3 (Gap A): uncorrelated abnormal-exit markers are surfaced, not dropped.
# ---------------------------------------------------------------------------


def test_scan_records_uncorrelated_dead_marker(tmp_path: Path) -> None:
    """A dead-PID marker that correlate cannot map to any session is recorded in
    ``uncorrelated_markers`` as crash evidence — never silently dropped (Gap A).

    The cwd has no project directory on disk, so ``correlate`` returns NO_MATCH.
    Before this fix the marker was skipped with no DB row at all; now its abnormal
    exit (dead pid) is preserved without fabricating a phantom session row.
    """
    from fixtures.jsonl_builder import _pick_dead_pid, make_liveness_file

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)
    now_epoch = int(time.time())
    started = now_epoch - 3600
    dead_pid = _pick_dead_pid()
    cwd = "/tmp/uncorrelated-no-transcripts"
    make_liveness_file(
        run_dir=run_dir,
        pid=dead_pid,
        cwd=cwd,
        started=started,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

    markers = _rows(
        db_path,
        "SELECT boot_id, pid, cwd, started, reason FROM uncorrelated_markers",
    )
    assert len(markers) == 1
    _boot_id, pid, marker_cwd, marker_started, reason = markers[0]
    assert pid == dead_pid
    assert marker_cwd == cwd
    assert marker_started == started
    assert reason == "dead_pid"
    # It must NOT fabricate a phantom sessions row for an uncorrelated marker.
    assert _rows(db_path, "SELECT uuid FROM sessions") == []


def test_scan_does_not_record_uncorrelated_live_marker(tmp_path: Path) -> None:
    """A live-PID marker on the current boot that correlate cannot map is a running
    session whose transcript was not located yet — not crash evidence. It must not
    be recorded as an uncorrelated marker.
    """
    from fixtures.jsonl_builder import make_liveness_file

    db_dir, run_dir, projects_root = make_full_fixture(tmp_path, [])
    db_path = _init_db(db_dir)
    now_epoch = int(time.time())
    make_liveness_file(
        run_dir=run_dir,
        pid=os.getpid(),  # this test process is alive; no start_time → bare kill -0
        cwd="/tmp/uncorrelated-live-no-transcripts",
        started=now_epoch - 60,
        argv="",
        boot_id=liveness_mod.current_boot_id(),
    )

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=now_epoch))

    assert _rows(db_path, "SELECT pid FROM uncorrelated_markers") == []
