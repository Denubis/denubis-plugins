"""DB-writer helpers for the crash-recovery scan transaction.

Extracted from :mod:`crash_recovery.scan` so the walk/classify pure core
and the DB-write imperative shell live in separate modules. ``scan.py``
remains the orchestrator (``run_scan``) plus the read-only walk;
``scan_db.py`` owns the four helpers that touch ``conn`` and the
:class:`WriteContext` bundle they share.

All helpers expect to run inside the ``with conn:`` transaction that
``run_scan`` opens — they do not commit; the outer context manager does.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from crash_recovery.classify import (
    CLASSIFIER_VERSION,
    Classification,
    ClassificationValue,
    LivenessState,
    classify,
)
from crash_recovery.jsonl import TailKind, TailSummary, parse_tail

if TYPE_CHECKING:
    from crash_recovery.scan import ScanContext, SessionFact


@dataclass(frozen=True)
class WriteContext:
    """Bundle of arguments shared across DB-writer helpers.

    Each per-session write (``_upsert_session``, ``_append_history``) and the
    closing orphan sweep (``_orphan_sweep``) need the open ``conn``, the
    frozen :class:`ScanContext`, and the row id of the in-progress
    ``scan_runs`` row. Bundling them keeps writer signatures compact and
    makes it impossible to call a writer with a mismatched ``ctx``/``conn``
    pair. Created by :func:`_write_scan_run`, which is the helper that
    allocates ``scan_run_id``.
    """

    conn: object
    ctx: ScanContext
    scan_run_id: int


def _write_scan_run(
    conn,
    ctx: ScanContext,
    *,
    sessions_scanned: int,
    live_pids: list[int],
) -> WriteContext:
    """Insert one row into ``scan_runs`` and return a :class:`WriteContext`.

    Called BEFORE the per-session upserts so the returned ``scan_run_id`` is
    available for :func:`_append_history`. ``live_pids`` is serialised via
    :func:`json.dumps`; the empty-list case serialises as ``"[]"`` (the
    column is TEXT and the design's convention is non-null TEXT — empty
    array is the natural empty value). Returns the bundled
    ``(conn, ctx, scan_run_id)`` triple that the per-session writers and
    the orphan sweep consume.
    """
    cur = conn.execute(
        "INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version) "
        "VALUES (?, ?, ?, ?)",
        (ctx.now, json.dumps(live_pids), sessions_scanned, CLASSIFIER_VERSION),
    )
    return WriteContext(conn=conn, ctx=ctx, scan_run_id=cur.lastrowid)


def _upsert_session(
    wctx: WriteContext,
    fact: SessionFact,
    classification: Classification,
) -> None:
    """INSERT ... ON CONFLICT(uuid) DO UPDATE one row in ``sessions``.

    ``first_seen`` is preserved on conflict (set only on the initial INSERT
    to ``wctx.ctx.now``). ``user_notes`` is NEVER touched on conflict — user
    annotations persist across scans per Phase 6's contract. All other
    fields are refreshed with the current scan's values.
    """
    wctx.conn.execute(
        """
        INSERT INTO sessions (
            uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
            classification, classification_reason, classifier_version, state_summary,
            first_seen, last_scanned, user_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        ON CONFLICT(uuid) DO UPDATE SET
            project_path = excluded.project_path,
            cwd = excluded.cwd,
            jsonl_path = excluded.jsonl_path,
            jsonl_mtime = excluded.jsonl_mtime,
            jsonl_last_ts = excluded.jsonl_last_ts,
            classification = excluded.classification,
            classification_reason = excluded.classification_reason,
            classifier_version = excluded.classifier_version,
            state_summary = excluded.state_summary,
            last_scanned = excluded.last_scanned
        """,
        (
            fact.uuid,
            fact.project_path,
            fact.cwd,
            fact.jsonl_path,
            fact.jsonl_mtime,
            fact.tail_summary.last_ts,
            classification.value,
            classification.reason,
            CLASSIFIER_VERSION,
            fact.tail_summary.state_summary,
            wctx.ctx.now,
            wctx.ctx.now,
        ),
    )


def _append_history(
    wctx: WriteContext,
    uuid: str,
    classification: Classification,
) -> None:
    """INSERT one row into ``classification_history``.

    Primary key is ``(uuid, scan_id)``: re-running with the same
    ``wctx.scan_run_id`` raises ``sqlite3.IntegrityError`` — that's a
    programmer error guard (each scan_run should produce at most one
    history row per UUID).
    """
    wctx.conn.execute(
        "INSERT INTO classification_history "
        "(uuid, scan_id, classification, reason, classifier_version) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            uuid,
            wctx.scan_run_id,
            classification.value,
            classification.reason,
            CLASSIFIER_VERSION,
        ),
    )


def _orphan_sweep(
    wctx: WriteContext,
    seen_uuids: set[str],
) -> int:
    """Re-classify DB rows whose UUIDs were not seen in this scan's walk.

    AC3.6: even if ``classifier_version`` is already current, orphans are
    re-considered because their JSONL may have been deleted since the last
    scan. On every orphan we write ``classifier_version = CLASSIFIER_VERSION``
    (a no-op when the row was already current; the AC3.6 win is the rows
    seeded at lower versions in tests).

    Algorithm:

    1. Query all rows (uuid, jsonl_path, classifier_version, classification,
       classification_reason).
    2. Skip rows whose UUID was seen this scan (handled by upsert).
    3. If ``jsonl_path`` is NULL or points to a now-missing file: classify
       as ``IRRECOVERABLE`` with reason ``missing_jsonl_on_disk``.
    4. Otherwise: re-parse the JSONL tail and classify with a no-liveness
       :class:`LivenessState`. This handles the case where a previous scan
       saw a liveness file that has since been cleaned up — the session
       itself may still have a JSONL on disk.
    5. UPDATE the row's fields (refreshes ``last_scanned`` and
       ``classifier_version`` every scan). M4: only append a
       classification_history row when the new classification + reason
       differ from the stored values — repeated orphan sweeps over an
       unchanged row no longer accumulate redundant "still irrecoverable"
       history entries. Return count of rows updated.
    """
    rows = wctx.conn.execute(
        "SELECT uuid, jsonl_path, classifier_version, "
        "classification, classification_reason, user_notes FROM sessions"
    ).fetchall()
    updated = 0
    for (
        uuid,
        jsonl_path_str,
        _stored_version,
        stored_classification,
        stored_reason,
        user_notes,
    ) in rows:
        if uuid in seen_uuids:
            continue
        if user_notes is not None:
            # Annotation-preserves-classification (Phase 6 Task 0; deferred
            # from Phase 4 proleptic review, 2026-05-17). ``user_notes IS
            # NOT NULL`` signals the user wants this row kept; preserve both
            # ``classification`` and ``classifier_version`` so a transiently
            # absent JSONL (unmounted volume, network FS hiccup) cannot
            # silently flip the row to ``irrecoverable`` and contradict the
            # user's annotation. ``last_scanned`` is bookkeeping but the
            # simplest correct implementation is to skip the row entirely:
            # no UPDATE, no ``classification_history`` append.
            continue
        if not jsonl_path_str or not Path(jsonl_path_str).exists():
            new_classification = Classification(
                value=ClassificationValue.IRRECOVERABLE,
                reason="missing_jsonl_on_disk",
            )
            tail_summary = TailSummary(
                kind=TailKind.MISSING_FILE,
                last_ts=None,
                total_entries=0,
                state_summary="jsonl missing on disk",
            )
        else:
            tail_summary = parse_tail(Path(jsonl_path_str))
            liveness_state = LivenessState(
                present=False, boot_id_current=False
            )
            new_classification = classify(
                tail_summary, liveness_state, pid_alive=None
            )
        wctx.conn.execute(
            "UPDATE sessions SET classification = ?, classification_reason = ?, "
            "classifier_version = ?, state_summary = ?, last_scanned = ? "
            "WHERE uuid = ?",
            (
                new_classification.value,
                new_classification.reason,
                CLASSIFIER_VERSION,
                tail_summary.state_summary,
                wctx.ctx.now,
                uuid,
            ),
        )
        if (
            new_classification.value != stored_classification
            or new_classification.reason != stored_reason
        ):
            _append_history(wctx, uuid, new_classification)
        updated += 1
    return updated
