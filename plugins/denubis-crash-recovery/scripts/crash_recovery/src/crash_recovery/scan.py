"""End-to-end scan orchestration for crash-recovery.

``run_scan(ctx)`` performs all read-only work first (filesystem walk, tail
parse, liveness parse, correlate, classify) into an in-memory list of
:class:`SessionFact` records. It then opens one SQLite transaction and writes
every sessions upsert, classification_history append, and the closing
scan_runs row in that single transaction. A second pass (the orphan sweep)
finds rows in the DB whose UUIDs were not seen on the filesystem this run,
re-classifies them (typically as ``irrecoverable`` if the JSONL is gone),
and updates them inside the same transaction.

The walk is functional-core (no DB I/O); the write block is the imperative
shell. WAL journal mode (set in :mod:`crash_recovery.db`) lets concurrent
readers proceed unblocked; concurrent scans serialise at the write lock.
"""

from __future__ import annotations

import json
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from crash_recovery import db
from crash_recovery.classify import (
    CLASSIFIER_VERSION,
    Classification,
    ClassificationValue,
    LivenessState,
    classify,
)
from crash_recovery.correlate import CorrelationKind, _project_dir_for_cwd, correlate
from crash_recovery.jsonl import TailKind, TailSummary, parse_tail
from crash_recovery.liveness import (
    Liveness,
    current_boot_id,
    list_liveness_files,
    pid_alive,
)


@dataclass(frozen=True)
class ScanContext:
    """Frozen I/O configuration for one ``run_scan`` invocation.

    ``now`` is injected (not read from ``time.time()`` inside the scan) so
    tests can pin the ``last_scanned`` and ``scan_runs.ts`` values.
    """

    db_path: Path
    run_dir: Path
    projects_root: Path
    now: int


@dataclass(frozen=True)
class ScanRunResult:
    """Return value of :func:`run_scan`.

    ``sessions_scanned`` counts facts emitted by the filesystem walk (one
    per touched UUID, including each AMBIGUOUS candidate). ``sessions_reclassified``
    counts orphan-sweep rows updated.
    """

    scan_run_id: int
    sessions_scanned: int
    sessions_reclassified: int


@dataclass(frozen=True)
class SessionFact:
    """One read-only fact produced by the filesystem walk.

    Pre-classified inputs to :func:`_classify_fact`. Liveness-dependent
    fields are computed at construction time so the classification step
    is pure.
    """

    uuid: str
    project_path: str
    cwd: str
    jsonl_path: str | None
    jsonl_mtime: int | None
    tail_summary: TailSummary
    liveness: Liveness | None
    pid_alive_value: bool | None
    boot_id_current: bool = False
    ambiguity_candidates: tuple[str, ...] = ()


def _jsonl_path_and_mtime(
    project_dir: Path | None, uuid: str
) -> tuple[str | None, int | None]:
    """Return absolute path string and mtime of ``<project_dir>/<uuid>.jsonl``.

    ``(None, None)`` if ``project_dir`` is ``None`` or the file does not exist.
    """
    if project_dir is None:
        return None, None
    candidate = project_dir / f"{uuid}.jsonl"
    if not candidate.exists():
        return None, None
    try:
        return str(candidate), int(candidate.stat().st_mtime)
    except OSError:
        return str(candidate), None


def _walk_sessions(ctx: ScanContext) -> list[SessionFact]:
    """Read-only filesystem walk producing one :class:`SessionFact` per UUID.

    Strategy:

    1. Iterate liveness files in ``ctx.run_dir``. For each, ``correlate``
       against ``ctx.projects_root``:

       * ``DIRECT_MATCH`` / ``MTIME_MATCH`` → one fact for the matched UUID.
       * ``AMBIGUOUS`` → one fact per candidate UUID, each carrying the full
         candidate list. ``_classify_fact`` short-circuits these to
         ``BORDERLINE/ambiguous_match`` per AC6.3.
       * ``NO_MATCH`` → skip; no DB row to write.

    2. Iterate ``ctx.projects_root.glob("*/*.jsonl")`` and collect any UUIDs
       not already produced by the liveness walk. JSONL-only facts have
       ``liveness=None``, ``pid_alive_value=None``, ``boot_id_current=False``.

    The current kernel boot_id is cached once at entry — boot_id is stable per
    kernel uptime, but caching is cheaper than N reads and simplifies fixture
    mocking.

    Does NOT touch the DB.
    """
    current_bid = current_boot_id()
    facts: list[SessionFact] = []
    seen: set[str] = set()

    for liveness in list_liveness_files(ctx.run_dir):
        correlation = correlate(liveness, ctx.projects_root)
        if correlation.kind is CorrelationKind.NO_MATCH:
            continue

        # Resolve project_dir once for path/mtime lookups for this liveness.
        # correlate has already located it (or we'd be in NO_MATCH); re-look
        # it up by content for the path string we store. We reuse the
        # correlation's uuid/candidates to derive the JSONL filenames.
        project_dir = _project_dir_for_cwd(ctx.projects_root, liveness.cwd)
        project_path = str(project_dir) if project_dir is not None else ""
        pid_alive_value = pid_alive(liveness.pid)
        boot_match = liveness.boot_id == current_bid

        if correlation.kind in (
            CorrelationKind.DIRECT_MATCH,
            CorrelationKind.MTIME_MATCH,
        ):
            resolved_uuid = correlation.uuid
            assert resolved_uuid is not None  # invariant of the kinds above
            jsonl_path_str, jsonl_mtime = _jsonl_path_and_mtime(
                project_dir, resolved_uuid
            )
            tail_summary = (
                parse_tail(Path(jsonl_path_str))
                if jsonl_path_str is not None
                else TailSummary(
                    kind=TailKind.MISSING_FILE,
                    last_ts=None,
                    total_entries=0,
                    state_summary="jsonl missing on disk",
                )
            )
            facts.append(
                SessionFact(
                    uuid=resolved_uuid,
                    project_path=project_path,
                    cwd=liveness.cwd,
                    jsonl_path=jsonl_path_str,
                    jsonl_mtime=jsonl_mtime,
                    tail_summary=tail_summary,
                    liveness=liveness,
                    pid_alive_value=pid_alive_value,
                    boot_id_current=boot_match,
                    ambiguity_candidates=(),
                )
            )
            seen.add(resolved_uuid)
            continue

        # AMBIGUOUS — one fact per candidate UUID. Construct a synthetic
        # TailSummary at fact-construction time (TailSummary is frozen — no
        # mutation). The override in _classify_fact bypasses Phase 2's RULES
        # and emits Classification(BORDERLINE, "ambiguous_match") per AC6.3.
        candidates_str = ", ".join(correlation.candidates)
        for candidate_uuid in correlation.candidates:
            jsonl_path_str, jsonl_mtime = _jsonl_path_and_mtime(
                project_dir, candidate_uuid
            )
            synthetic_tail = TailSummary(
                kind=TailKind.UNKNOWN,
                last_ts=None,
                total_entries=0,
                state_summary=f"ambiguous match: {candidates_str}",
            )
            facts.append(
                SessionFact(
                    uuid=candidate_uuid,
                    project_path=project_path,
                    cwd=liveness.cwd,
                    jsonl_path=jsonl_path_str,
                    jsonl_mtime=jsonl_mtime,
                    tail_summary=synthetic_tail,
                    liveness=liveness,
                    pid_alive_value=pid_alive_value,
                    boot_id_current=boot_match,
                    ambiguity_candidates=correlation.candidates,
                )
            )
            seen.add(candidate_uuid)

    # JSONL-only walk: any UUID with a JSONL on disk but not produced above.
    if ctx.projects_root.exists() and ctx.projects_root.is_dir():
        for jsonl_path in sorted(ctx.projects_root.glob("*/*.jsonl")):
            uuid = jsonl_path.stem
            if uuid in seen:
                continue
            try:
                jsonl_mtime = int(jsonl_path.stat().st_mtime)
            except OSError:
                jsonl_mtime = None
            tail_summary = parse_tail(jsonl_path)
            # Best-effort cwd: read it from the JSONL's first entry. The
            # encoded directory name is lossy, so the JSONL's own ``cwd`` is
            # the canonical source.
            cwd = _first_entry_cwd(jsonl_path)
            facts.append(
                SessionFact(
                    uuid=uuid,
                    project_path=str(jsonl_path.parent),
                    cwd=cwd,
                    jsonl_path=str(jsonl_path),
                    jsonl_mtime=jsonl_mtime,
                    tail_summary=tail_summary,
                    liveness=None,
                    pid_alive_value=None,
                    boot_id_current=False,
                    ambiguity_candidates=(),
                )
            )
            seen.add(uuid)

    return facts


def _first_entry_cwd(jsonl_path: Path) -> str:
    """Return ``cwd`` from the first JSON line of ``jsonl_path``, or ``""``.

    Best-effort: empty string on any parse error. The encoded directory
    name is lossy so this is the canonical cwd source; an empty string
    just means "we couldn't read it" — the DB column is NOT NULL but
    accepts ``""``.
    """
    try:
        with jsonl_path.open("r", encoding="utf-8") as handle:
            first = handle.readline()
        if not first.strip():
            return ""
        entry = json.loads(first)
    except (OSError, json.JSONDecodeError):
        return ""
    cwd_value = entry.get("cwd")
    return cwd_value if isinstance(cwd_value, str) else ""


def _classify_fact(fact: SessionFact) -> Classification:
    """Map a :class:`SessionFact` to its :class:`Classification`.

    AC6.3 short-circuit: ambiguous correlation gets a hardcoded
    ``BORDERLINE/ambiguous_match`` without consulting Phase 2's RULES. The
    rule table catalogues tail-shape-driven outcomes; correlation
    ambiguity is a different category entirely.

    The non-ambiguous path delegates to Phase 2's :func:`classify`. The
    caller (``_walk_sessions``) guarantees ``LivenessState.present=True``
    implies ``pid_alive_value`` is a concrete ``bool`` (Phase 3 contract);
    a violation surfaces as the boundary ``ValueError`` from
    :func:`classify` and crashes the scan loudly.
    """
    if fact.ambiguity_candidates:
        return Classification(
            value=ClassificationValue.BORDERLINE,
            reason="ambiguous_match",
        )
    liveness_state = LivenessState(
        present=fact.liveness is not None,
        boot_id_current=fact.boot_id_current,
    )
    return classify(fact.tail_summary, liveness_state, fact.pid_alive_value)


def _write_scan_run(
    conn,
    ctx: ScanContext,
    *,
    sessions_scanned: int,
    live_pids: list[int],
) -> int:
    """Insert one row into ``scan_runs`` and return its ``rowid``.

    Called BEFORE the per-session upserts so the returned ``run_id`` is
    available for :func:`_append_history`. ``live_pids`` is serialised via
    :func:`json.dumps`; the empty-list case serialises as ``"[]"`` (the
    column is TEXT and the design's convention is non-null TEXT — empty
    array is the natural empty value).
    """
    cur = conn.execute(
        "INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version) "
        "VALUES (?, ?, ?, ?)",
        (ctx.now, json.dumps(live_pids), sessions_scanned, CLASSIFIER_VERSION),
    )
    return cur.lastrowid


def _upsert_session(
    conn,
    fact: SessionFact,
    classification: Classification,
    ctx: ScanContext,
    scan_run_id: int,
) -> None:
    """INSERT ... ON CONFLICT(uuid) DO UPDATE one row in ``sessions``.

    ``first_seen`` is preserved on conflict (set only on the initial INSERT
    to ``ctx.now``). ``user_notes`` is NEVER touched on conflict — user
    annotations persist across scans per Phase 6's contract. All other
    fields are refreshed with the current scan's values.
    """
    conn.execute(
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
            ctx.now,
            ctx.now,
        ),
    )


def _append_history(
    conn,
    uuid: str,
    scan_run_id: int,
    classification: Classification,
) -> None:
    """INSERT one row into ``classification_history``.

    Primary key is ``(uuid, scan_id)``: re-running with the same
    ``scan_run_id`` raises ``sqlite3.IntegrityError`` — that's a programmer
    error guard (each scan_run should produce at most one history row per
    UUID).
    """
    conn.execute(
        "INSERT INTO classification_history "
        "(uuid, scan_id, classification, reason, classifier_version) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            uuid,
            scan_run_id,
            classification.value,
            classification.reason,
            CLASSIFIER_VERSION,
        ),
    )


def _orphan_sweep(
    conn,
    ctx: ScanContext,
    scan_run_id: int,
    seen_uuids: set[str],
) -> int:
    """Re-classify DB rows whose UUIDs were not seen in this scan's walk.

    AC3.6: even if ``classifier_version`` is already current, orphans are
    re-considered because their JSONL may have been deleted since the last
    scan. On every orphan we write ``classifier_version = CLASSIFIER_VERSION``
    (a no-op when the row was already current; the AC3.6 win is the rows
    seeded at lower versions in tests).

    Algorithm:

    1. Query all rows.
    2. Skip rows whose UUID was seen this scan (handled by upsert).
    3. If ``jsonl_path`` is NULL or points to a now-missing file: classify
       as ``IRRECOVERABLE`` with reason ``missing_jsonl_on_disk``.
    4. Otherwise: re-parse the JSONL tail and classify with a no-liveness
       :class:`LivenessState`. This handles the case where a previous scan
       saw a liveness file that has since been cleaned up — the session
       itself may still have a JSONL on disk.
    5. UPDATE the row and append history. Return count of rows updated.
    """
    rows = conn.execute(
        "SELECT uuid, jsonl_path, classifier_version FROM sessions"
    ).fetchall()
    updated = 0
    for uuid, jsonl_path_str, _stored_version in rows:
        if uuid in seen_uuids:
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
        conn.execute(
            "UPDATE sessions SET classification = ?, classification_reason = ?, "
            "classifier_version = ?, state_summary = ?, last_scanned = ? "
            "WHERE uuid = ?",
            (
                new_classification.value,
                new_classification.reason,
                CLASSIFIER_VERSION,
                tail_summary.state_summary,
                ctx.now,
                uuid,
            ),
        )
        _append_history(conn, uuid, scan_run_id, new_classification)
        updated += 1
    return updated


def run_scan(ctx: ScanContext) -> ScanRunResult:
    """Walk the filesystem, classify, and write one transaction to the DB.

    Order is load-bearing:

    1. Read-only walk + classify (no DB I/O).
    2. Open the DB once, enter a ``with conn:`` block (single transaction).
    3. Write the ``scan_runs`` row first so its id is available for the
       history appends.
    4. Per fact: upsert into ``sessions`` and append to
       ``classification_history``.
    5. Orphan sweep: re-classify any row not seen this walk.
    6. Context-manager exit commits the entire transaction (or rolls back
       on exception).

    Returns
    -------
    ScanRunResult
        Containing the new ``scan_runs`` rowid, the count of facts emitted
        by the walk, and the count of orphan-sweep rows updated.
    """
    facts = _walk_sessions(ctx)
    classifications = [(fact, _classify_fact(fact)) for fact in facts]
    seen_uuids = {fact.uuid for fact in facts}
    # Sorted for determinism so identical inputs produce identical DB content.
    live_pids: list[int] = sorted(
        {
            fact.liveness.pid
            for fact in facts
            if fact.liveness is not None and fact.pid_alive_value is True
        }
    )
    with closing(db.open_db(ctx.db_path)) as conn:
        with conn:
            run_id = _write_scan_run(
                conn,
                ctx,
                sessions_scanned=len(facts),
                live_pids=live_pids,
            )
            for fact, classification in classifications:
                _upsert_session(conn, fact, classification, ctx, run_id)
                _append_history(conn, fact.uuid, run_id, classification)
            reclassified = _orphan_sweep(conn, ctx, run_id, seen_uuids)
    return ScanRunResult(
        scan_run_id=run_id,
        sessions_scanned=len(facts),
        sessions_reclassified=reclassified,
    )
