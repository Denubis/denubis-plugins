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
    with open("/proc/sys/kernel/pid_max") as f:
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
    db_path: Path, run_dir: Path, projects_root: Path, now: int | None = None
) -> scan_mod.ScanContext:
    return scan_mod.ScanContext(
        db_path=db_path,
        run_dir=run_dir,
        projects_root=projects_root,
        now=now if now is not None else int(time.time()),
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
        r[0]: r[1]
        for r in _rows(db_path, "SELECT uuid, first_seen FROM sessions")
    }

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=2_000_000))

    # Same 3 sessions rows.
    count_rows = _rows(db_path, "SELECT COUNT(*) FROM sessions")
    assert count_rows == [(3,)]
    # first_seen preserved.
    first_seen_after = {
        r[0]: r[1]
        for r in _rows(db_path, "SELECT uuid, first_seen FROM sessions")
    }
    assert first_seen_after == first_seen_before
    # last_scanned advanced to the second scan's now.
    last_scanned_after = {
        r[0]: r[1]
        for r in _rows(db_path, "SELECT uuid, last_scanned FROM sessions")
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
    """Live PID + boot_id current → ``live`` / ``live_pid_present_boot_current`` (AC6.2)."""
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
    """``run_scan`` deduplicates PIDs via ``sorted({...})`` when two facts share one PID.

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

    monkeypatch.setattr(scan_mod, "_walk_sessions", lambda _ctx: list(_facts))

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
    assert isinstance(live_pids, list), "live_pids must be a list (JSON array), not a set"
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
    # Both JSONLs have first_entry_ts comfortably in the mtime window:
    # started = now - 3600, so any ts >= now - 3660 is admitted.
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd,
        first_entry_epoch=now_epoch - 100,
        tail_kind=TailKind.CONCLUDED,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd,
        first_entry_epoch=now_epoch - 50,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=os.getpid(),
        cwd=cwd,
        started=now_epoch - 3600,
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

    rows = _rows(
        db_path, "SELECT classifier_version, last_scanned FROM sessions"
    )
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
    jsonl_path.write_text(
        json.dumps({"role": "assistant", "content": "hi"}) + "\n"
    )

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
    history_after_first = _rows(
        db_path, "SELECT COUNT(*) FROM classification_history"
    )
    assert history_after_first == [(2,)]

    scan_mod.run_scan(_make_ctx(db_path, run_dir, projects_root, now=2_000_000))

    # No new history rows because nothing changed
    history_after_second = _rows(
        db_path, "SELECT COUNT(*) FROM classification_history"
    )
    assert history_after_second == [(2,)]
    # last_scanned still advanced
    last_scanned = {
        r[0]: r[1]
        for r in _rows(db_path, "SELECT uuid, last_scanned FROM sessions")
    }
    assert all(v == 2_000_000 for v in last_scanned.values())


def test_classification_history_appends_when_classification_changes(
    tmp_path: Path,
) -> None:
    """Seed a row with one classification; scan produces a different one → history grows.

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
    _write_session_jsonl(
        project_dir / f"{uuid_a}.jsonl",
        cwd=cwd,
        first_entry_epoch=now_epoch - 100,
        tail_kind=TailKind.CONCLUDED,
    )
    _write_session_jsonl(
        project_dir / f"{uuid_b}.jsonl",
        cwd=cwd,
        first_entry_epoch=now_epoch - 50,
        tail_kind=TailKind.CONCLUDED,
    )
    make_liveness_file(
        run_dir=run_dir,
        pid=os.getpid(),
        cwd=cwd,
        started=now_epoch - 3600,
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
