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

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from crash_recovery import db, resurrect
from crash_recovery.classify import (
    Classification,
    ClassificationValue,
    LivenessState,
    classify,
)
from crash_recovery.correlate import CorrelationKind, _project_dir_for_cwd, correlate
from crash_recovery.jsonl import (
    TailKind,
    TailSummary,
    first_record_field,
    last_substantive_text,
    parse_tail,
)
from crash_recovery.liveness import (
    Liveness,
    current_boot_id,
    list_liveness_files,
    pid_alive_checked,
)
from crash_recovery.scan_db import (
    WriteContext,
    _append_history,
    _orphan_sweep,
    _upsert_session,
    _write_scan_run,
)

__all__ = [
    "AMBIGUOUS_STATE_SUMMARY_PREFIX",
    "ScanContext",
    "ScanRunResult",
    "SessionFact",
    "WriteContext",
    "run_scan",
]

# Pinned format for the AMBIGUOUS state_summary so downstream consumers
# (Phase 5's reader / triage CLI) can recognise an ambiguous row by
# prefix rather than depending on the free-form f-string body. NOT
# underscore-prefixed: this is part of the module's public surface.
AMBIGUOUS_STATE_SUMMARY_PREFIX = "ambiguous match: "


@dataclass(frozen=True)
class ScanContext:
    """Frozen I/O configuration for one ``run_scan`` invocation.

    ``now`` is injected (not read from ``time.time()`` inside the scan) so
    tests can pin the ``last_scanned`` and ``scan_runs.ts`` values.

    ``resurrect_dir`` is the tmux-resurrect snapshot directory
    (``~/.byobu-sessions`` by default). ``_walk_sessions`` loads its snapshots
    once and corroborates id-less backlog markers against the pane cwds live at
    crash time (Phase 3). A missing or empty directory makes corroboration a
    no-op — multi-candidate markers stay ``borderline/ambiguous_match``.
    """

    db_path: Path
    run_dir: Path
    projects_root: Path
    now: int
    resurrect_dir: Path


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
    pane_title: str | None = None
    last_substantive: str | None = None


@dataclass(frozen=True)
class UncorrelatedMarker:
    """An abnormal-exit ``.live`` marker that ``correlate`` could not map to a session.

    Not a session (no UUID, no transcript). Produced by ``_walk_sessions`` only
    when a NO_MATCH marker is evidence of an abnormal exit — its pid is dead, or
    its ``boot_id`` no longer matches the current boot. A NO_MATCH marker whose
    pid is alive on the current boot is a running session whose transcript was
    simply not located yet, so it is left out. ``reason`` is ``"dead_pid"`` or
    ``"boot_mismatch"``.
    """

    boot_id: str
    pid: int
    cwd: str
    started: int
    reason: str


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


def _pane_title_for(
    jsonl_path_str: str | None, snapshot: resurrect.Snapshot | None
) -> str | None:
    """Return the resurrect pane label for the session at ``jsonl_path_str``.

    CA2 (per-candidate cwd): the label is keyed on the session's OWN first-entry
    ``cwd`` — read from THIS JSONL via :func:`_first_entry_cwd` — never on
    ``liveness.cwd``. Under a lossy encoded-dir collision two candidates share
    one directory but declare distinct cwds; labelling by the marker's cwd would
    attach the wrong pane's title to the candidate whose cwd differs.

    ``snapshot`` may be ``None`` (empty/old resurrect dir → ``snapshot_near`` is
    ``None``); :func:`resurrect.label_for_cwd` tolerates it and returns ``None``.
    A missing ``jsonl_path_str`` yields an empty cwd, and no pane sits at ``""``,
    so the label is ``None``.
    """
    session_cwd = _first_entry_cwd(Path(jsonl_path_str)) if jsonl_path_str else ""
    return resurrect.label_for_cwd(snapshot, session_cwd)


def _build_liveness_fact_direct_or_mtime(
    liveness: Liveness,
    correlation,
    ctx: ScanContext,
    current_bid: str | None,
    snapshot: resurrect.Snapshot | None,
) -> SessionFact:
    """Build one :class:`SessionFact` for a DIRECT_MATCH / MTIME_MATCH liveness.

    Caller (``_walk_sessions``) has already verified the correlation kind
    is DIRECT or MTIME — the ``assert`` below documents the invariant for
    type-narrowing readers. ``snapshot`` is the resurrect snapshot nearest the
    marker's ``started`` (already resolved by the caller) used to label
    ``pane_title``.
    """
    project_dir = _project_dir_for_cwd(ctx.projects_root, liveness.cwd)
    project_path = liveness.cwd
    pid_alive_value = pid_alive_checked(liveness.pid, liveness.start_time)
    boot_match = liveness.boot_id == current_bid
    resolved_uuid = correlation.uuid
    if resolved_uuid is None:
        raise AssertionError("invariant of DIRECT/MTIME kinds")
    jsonl_path_str, jsonl_mtime = _jsonl_path_and_mtime(project_dir, resolved_uuid)
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
    last_substantive = (
        last_substantive_text(Path(jsonl_path_str))
        if jsonl_path_str is not None
        else None
    )
    return SessionFact(
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
        pane_title=_pane_title_for(jsonl_path_str, snapshot),
        last_substantive=last_substantive,
    )


def _build_ambiguous_facts(
    liveness: Liveness,
    correlation,
    ctx: ScanContext,
    current_bid: str | None,
    snapshot: resurrect.Snapshot | None,
) -> list[SessionFact]:
    """Build one :class:`SessionFact` per AMBIGUOUS candidate UUID.

    Each fact carries the full candidate tuple so ``_classify_fact`` can
    short-circuit to ``BORDERLINE/ambiguous_match`` per AC6.3 without
    consulting Phase 2's RULES. The synthetic :class:`TailSummary` records
    the candidate list in ``state_summary`` for downstream triage.

    ``pane_title`` is labelled PER CANDIDATE from each candidate's OWN
    first-entry cwd (CA2): under a lossy encoded-dir collision the candidates
    share ``liveness.cwd`` but declare distinct cwds, so labelling by
    ``liveness.cwd`` would attach the wrong pane's title to the candidate whose
    cwd differs. ``snapshot`` is the resurrect snapshot nearest the marker's
    ``started`` (already resolved by the caller).
    """
    project_dir = _project_dir_for_cwd(ctx.projects_root, liveness.cwd)
    project_path = liveness.cwd
    pid_alive_value = pid_alive_checked(liveness.pid, liveness.start_time)
    boot_match = liveness.boot_id == current_bid
    candidates_str = ", ".join(correlation.candidates)
    facts: list[SessionFact] = []
    for candidate_uuid in correlation.candidates:
        jsonl_path_str, jsonl_mtime = _jsonl_path_and_mtime(project_dir, candidate_uuid)
        synthetic_tail = TailSummary(
            kind=TailKind.UNKNOWN,
            last_ts=None,
            total_entries=0,
            state_summary=f"{AMBIGUOUS_STATE_SUMMARY_PREFIX}{candidates_str}",
        )
        last_substantive = (
            last_substantive_text(Path(jsonl_path_str))
            if jsonl_path_str is not None
            else None
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
                pane_title=_pane_title_for(jsonl_path_str, snapshot),
                last_substantive=last_substantive,
            )
        )
    return facts


def _walk_jsonl_only(ctx: ScanContext, seen_uuids: set[str]) -> list[SessionFact]:
    """Enumerate JSONL files under ``ctx.projects_root`` not yet ``seen_uuids``.

    JSONL-only facts have ``liveness=None``, ``pid_alive_value=None``,
    ``boot_id_current=False``. The first-entry ``cwd`` is the canonical
    source for ``project_path``/``cwd`` because the encoded directory name
    is lossy.
    """
    facts: list[SessionFact] = []
    if not (ctx.projects_root.exists() and ctx.projects_root.is_dir()):
        return facts
    for jsonl_path in sorted(ctx.projects_root.glob("*/*.jsonl")):
        uuid = jsonl_path.stem
        if uuid in seen_uuids:
            continue
        try:
            jsonl_mtime = int(jsonl_path.stat().st_mtime)
        except OSError:
            jsonl_mtime = None
        tail_summary = parse_tail(jsonl_path)
        cwd = _first_entry_cwd(jsonl_path)
        facts.append(
            SessionFact(
                uuid=uuid,
                project_path=cwd,
                cwd=cwd,
                jsonl_path=str(jsonl_path),
                jsonl_mtime=jsonl_mtime,
                tail_summary=tail_summary,
                liveness=None,
                pid_alive_value=None,
                boot_id_current=False,
                ambiguity_candidates=(),
                # No liveness marker → no ``started`` anchor for ``snapshot_near``
                # → ``pane_title`` is unconditionally NULL. ``last_substantive``
                # still comes from the JSONL.
                pane_title=None,
                last_substantive=last_substantive_text(jsonl_path),
            )
        )
        seen_uuids.add(uuid)
    return facts


def _is_live_fact(fact: SessionFact) -> bool:
    """True when ``fact`` represents a session running *now* — its pid is alive on
    the current boot.

    Used by ``_walk_sessions`` dedup: on a same-rank, same-UUID collision a live
    fact must displace a dead one, so a running session (e.g. a crashed session
    that has since been resumed and is alive again) is never persisted as a crash
    victim merely because a stale dead marker's path sorts first.
    """
    return fact.pid_alive_value is True and fact.boot_id_current


def _walk_sessions(
    ctx: ScanContext,
) -> tuple[list[SessionFact], list[UncorrelatedMarker]]:
    """Read-only filesystem walk producing one :class:`SessionFact` per UUID.

    Strategy:

    1. Iterate liveness files in ``ctx.run_dir``. For each, ``correlate``
       against ``ctx.projects_root``:

       * ``DIRECT_MATCH`` / ``MTIME_MATCH`` → one fact for the matched UUID.
       * ``AMBIGUOUS`` → one fact per candidate UUID, each carrying the full
         candidate list. ``_classify_fact`` short-circuits these to
         ``BORDERLINE/ambiguous_match`` per AC6.3.
       * ``NO_MATCH`` → no session fact. If the marker is abnormal-exit evidence
         (dead pid, or boot_id mismatch) it is collected as an
         :class:`UncorrelatedMarker` so it is surfaced rather than silently
         dropped (Gap A). A live marker on the current boot is left out.

    Returns ``(session_facts, uncorrelated_markers)``.

    2. Deduplicate facts by UUID before the write loop. Two ``.live`` files
       can resolve to the same UUID (e.g. a DIRECT_MATCH from marker A and
       an AMBIGUOUS candidate from marker B), which would crash ``run_scan``
       with a ``sqlite3.IntegrityError`` on the ``(uuid, scan_id)`` UNIQUE
       constraint in ``classification_history``. Dedup selects the winner by
       precedence rank: ``DIRECT_MATCH/session_id → 0``, ``MTIME_MATCH → 1``,
       ``AMBIGUOUS candidate → 2`` — lower rank wins. Within a rank, a live fact
       (pid alive on the current boot) beats a dead one, so a running session is
       never displaced by a crashed sibling for the same UUID. Remaining ties are
       broken by the lexicographically smaller liveness path string, making the
       selection order-independent regardless of ``list_liveness_files`` order.

    3. Iterate ``ctx.projects_root.glob("*/*.jsonl")`` and collect any UUIDs
       not already produced by the liveness walk. JSONL-only facts have
       ``liveness=None``, ``pid_alive_value=None``, ``boot_id_current=False``.

    The current kernel boot_id is cached once at entry — boot_id is stable per
    kernel uptime, but caching is cheaper than N reads and simplifies fixture
    mocking.

    Does NOT touch the DB.
    """
    current_bid = current_boot_id()

    # Phase 3: load tmux-resurrect snapshots once. Per liveness we pick the
    # snapshot nearest its ``started`` and pass that snapshot's pane cwds into
    # ``correlate`` so a multi-candidate backlog marker can be narrowed to the
    # single pane that was live at crash time. Empty/missing dir → [] → every
    # ``snapshot_near`` is None → empty frozenset → corroboration is a no-op.
    snapshots = resurrect.load_snapshots(ctx.resurrect_dir)

    # Precedence rank per correlation kind (lower wins).
    _RANK = {
        CorrelationKind.DIRECT_MATCH: 0,
        CorrelationKind.MTIME_MATCH: 1,
        CorrelationKind.AMBIGUOUS: 2,
    }

    # keyed by UUID → (rank, live_rank, liveness_path_str, fact)
    deduped: dict[str, tuple[int, int, str, SessionFact]] = {}
    # Abnormal-exit markers that correlate could not map to any session (Gap A).
    uncorrelated: list[UncorrelatedMarker] = []

    def _consider(rank: int, liveness_path_str: str, fact: SessionFact) -> None:
        """Insert or replace the entry for ``fact.uuid`` if this one wins.

        Tie-break key (lower wins): correlation ``rank``, then ``live_rank`` — a
        live fact (0) beats a dead one (1) so a running session is never displaced
        by a crashed sibling — then the lexicographically smaller liveness path
        for full order-independence.
        """
        live_rank = 0 if _is_live_fact(fact) else 1
        key = (rank, live_rank, liveness_path_str)
        existing = deduped.get(fact.uuid)
        if existing is None or key < existing[:3]:
            deduped[fact.uuid] = (rank, live_rank, liveness_path_str, fact)

    for liveness in list_liveness_files(ctx.run_dir):
        # Pane cwds from the snapshot nearest this marker's ``started`` (empty
        # frozenset when no snapshot qualifies). Passed unconditionally: the
        # session_id / --resume direct paths in ``correlate`` return before
        # they ever consult ``corroborated_cwds``, so direct matches are
        # unaffected; only the >1-candidate mtime branch uses it.
        near = resurrect.snapshot_near(snapshots, liveness.started)
        corroborated = (
            frozenset(resurrect.corroborating_cwds(near))
            if near is not None
            else frozenset()
        )
        correlation = correlate(
            liveness, ctx.projects_root, corroborated_cwds=corroborated
        )
        if correlation.kind is CorrelationKind.NO_MATCH:
            # Surface abnormal-exit evidence rather than dropping it (Gap A). A
            # boot_id mismatch means the pid belongs to a previous boot (the
            # process is gone); a dead pid on the current boot is an abnormal
            # exit this boot. A live pid on the current boot is a running session
            # whose transcript we have not located yet — not a crash — so it is
            # left for a later scan.
            if liveness.boot_id != current_bid:
                uncorrelated.append(
                    UncorrelatedMarker(
                        boot_id=liveness.boot_id,
                        pid=liveness.pid,
                        cwd=liveness.cwd,
                        started=liveness.started,
                        reason=db.MARKER_REASON_BOOT_MISMATCH,
                    )
                )
            elif pid_alive_checked(liveness.pid, liveness.start_time) is False:
                uncorrelated.append(
                    UncorrelatedMarker(
                        boot_id=liveness.boot_id,
                        pid=liveness.pid,
                        cwd=liveness.cwd,
                        started=liveness.started,
                        reason=db.MARKER_REASON_DEAD_PID,
                    )
                )
            continue
        liveness_path_str = str(liveness.path)
        if correlation.kind in (
            CorrelationKind.DIRECT_MATCH,
            CorrelationKind.MTIME_MATCH,
        ):
            fact = _build_liveness_fact_direct_or_mtime(
                liveness, correlation, ctx, current_bid, near
            )
            _consider(_RANK[correlation.kind], liveness_path_str, fact)
            continue
        # AMBIGUOUS — one fact per candidate UUID.
        ambiguous_facts = _build_ambiguous_facts(
            liveness, correlation, ctx, current_bid, near
        )
        for fact in ambiguous_facts:
            _consider(_RANK[CorrelationKind.AMBIGUOUS], liveness_path_str, fact)

    facts: list[SessionFact] = [entry[3] for entry in deduped.values()]
    seen: set[str] = set(deduped)

    facts.extend(_walk_jsonl_only(ctx, seen))
    return facts, uncorrelated


def _first_entry_cwd(jsonl_path: Path) -> str:
    """Return ``cwd`` from the first JSONL record that carries it, or ``""``.

    Uses :func:`crash_recovery.jsonl.first_record_field` to scan forward past
    snapshot/bookkeeping records (which carry no ``cwd``) so that modern
    transcripts — where ``cwd`` sits on line 2 or later — are read correctly.

    Best-effort: empty string on any parse error or when no record carries
    ``cwd`` within the scan window. The DB column is NOT NULL but accepts
    ``""``, and ``_classify_fact`` maps an empty cwd to
    ``irrecoverable/missing_cwd``.
    """
    return first_record_field(jsonl_path, "cwd") or ""


def _classify_fact(fact: SessionFact) -> Classification:
    """Map a :class:`SessionFact` to its :class:`Classification`.

    Short-circuits (checked before delegating to Phase 2's :func:`classify`):

    * Empty ``cwd`` → ``IRRECOVERABLE/missing_cwd``. Without a cwd, Phase 7's
      ``claudew --resume`` from ``""`` would fail confusingly. The walker
      still writes the row so the user sees the irrecoverable session in
      triage with a clear reason.
    * AC6.3 — ambiguous correlation → hardcoded
      ``BORDERLINE/ambiguous_match`` without consulting Phase 2's RULES. The
      rule table catalogues tail-shape-driven outcomes; correlation
      ambiguity is a different category entirely.

    The non-short-circuit path delegates to Phase 2's :func:`classify`. The
    caller (``_walk_sessions``) guarantees ``LivenessState.present=True``
    implies ``pid_alive_value`` is a concrete ``bool`` (Phase 3 contract);
    a violation surfaces as the boundary ``ValueError`` from
    :func:`classify` and crashes the scan loudly.
    """
    if not fact.cwd:
        return Classification(
            value=ClassificationValue.IRRECOVERABLE,
            reason="missing_cwd",
        )
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
    facts, uncorrelated = _walk_sessions(ctx)
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
    with closing(db.open_db(ctx.db_path)) as conn, conn:
        wctx = _write_scan_run(
            conn,
            ctx,
            sessions_scanned=len(facts),
            live_pids=live_pids,
        )
        for fact, classification in classifications:
            # M4: query existing classification + reason before upsert
            # so we can dedup the history append. The upsert below will
            # overwrite these values; we need the pre-upsert state.
            prior = conn.execute(
                "SELECT classification, classification_reason "
                "FROM sessions WHERE uuid = ?",
                (fact.uuid,),
            ).fetchone()
            _upsert_session(wctx, fact, classification)
            if prior is None or (
                classification.value != prior[0] or classification.reason != prior[1]
            ):
                _append_history(wctx, fact.uuid, classification)
        reclassified = _orphan_sweep(wctx, seen_uuids)
        # Replace the uncorrelated-markers set with this scan's. They are not
        # sessions (no UUID, no transcript, no classification_history), so a
        # full replace each scan keeps the table free of stale rows without
        # needing an orphan sweep of its own.
        conn.execute("DELETE FROM uncorrelated_markers")
        for marker in uncorrelated:
            conn.execute(
                "INSERT INTO uncorrelated_markers "
                "(boot_id, pid, cwd, started, reason, last_scanned) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    marker.boot_id,
                    marker.pid,
                    marker.cwd,
                    marker.started,
                    marker.reason,
                    ctx.now,
                ),
            )
    return ScanRunResult(
        scan_run_id=wctx.scan_run_id,
        sessions_scanned=len(facts),
        sessions_reclassified=reclassified,
    )
