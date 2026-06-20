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


def _build_liveness_fact_direct_or_mtime(
    liveness: Liveness,
    correlation,
    ctx: ScanContext,
    current_bid: str | None,
) -> SessionFact:
    """Build one :class:`SessionFact` for a DIRECT_MATCH / MTIME_MATCH liveness.

    Caller (``_walk_sessions``) has already verified the correlation kind
    is DIRECT or MTIME — the ``assert`` below documents the invariant for
    type-narrowing readers.
    """
    project_dir = _project_dir_for_cwd(ctx.projects_root, liveness.cwd)
    project_path = liveness.cwd
    pid_alive_value = pid_alive(liveness.pid)
    boot_match = liveness.boot_id == current_bid
    resolved_uuid = correlation.uuid
    assert resolved_uuid is not None  # noqa: S101 (invariant of DIRECT/MTIME kinds)
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
    )


def _build_ambiguous_facts(
    liveness: Liveness,
    correlation,
    ctx: ScanContext,
    current_bid: str | None,
) -> list[SessionFact]:
    """Build one :class:`SessionFact` per AMBIGUOUS candidate UUID.

    Each fact carries the full candidate tuple so ``_classify_fact`` can
    short-circuit to ``BORDERLINE/ambiguous_match`` per AC6.3 without
    consulting Phase 2's RULES. The synthetic :class:`TailSummary` records
    the candidate list in ``state_summary`` for downstream triage.
    """
    project_dir = _project_dir_for_cwd(ctx.projects_root, liveness.cwd)
    project_path = liveness.cwd
    pid_alive_value = pid_alive(liveness.pid)
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
            )
        )
        seen_uuids.add(uuid)
    return facts


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
        if correlation.kind in (
            CorrelationKind.DIRECT_MATCH,
            CorrelationKind.MTIME_MATCH,
        ):
            fact = _build_liveness_fact_direct_or_mtime(
                liveness, correlation, ctx, current_bid
            )
            facts.append(fact)
            seen.add(fact.uuid)
            continue
        # AMBIGUOUS — one fact per candidate UUID.
        ambiguous_facts = _build_ambiguous_facts(
            liveness, correlation, ctx, current_bid
        )
        facts.extend(ambiguous_facts)
        for fact in ambiguous_facts:
            seen.add(fact.uuid)

    facts.extend(_walk_jsonl_only(ctx, seen))
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
    except OSError, json.JSONDecodeError:
        return ""
    cwd_value = entry.get("cwd")
    return cwd_value if isinstance(cwd_value, str) else ""


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
    return ScanRunResult(
        scan_run_id=wctx.scan_run_id,
        sessions_scanned=len(facts),
        sessions_reclassified=reclassified,
    )
