"""Correlate a liveness record to candidate session UUIDs.

The Phase 3 correlator decides which JSONL session a recovered liveness file
points at. Three strategies, in order:

1. **Session direct match** — if ``liveness.session_id`` identifies an
   existing JSONL in the project directory, return ``DIRECT_MATCH``.

2. **Legacy argv direct match** — if optional ``liveness.argv`` contains
   ``--resume <uuid>``
   AND ``<uuid>.jsonl`` exists in the project directory whose JSONLs declare
   ``liveness.cwd``, return ``DIRECT_MATCH``.

3. **mtime-window fallback** — enumerate JSONLs in the project directory,
   filter to those whose filesystem mtime *and* first-entry timestamp are
   ≥ ``liveness.started`` (with a 60-second clock-skew grace), and report
   ``MTIME_MATCH`` (one survivor), ``AMBIGUOUS`` (multiple), or ``NO_MATCH``
   (none). The argv path falls *through* to mtime when the argv-named UUID's
   JSONL has been deleted — still useful to report something rather than
   nothing.

Project directory resolution is deliberately by-content, not by-name. Claude
Code's directory encoding (``~/.claude/projects/-encoded-name/``) is lossy:
``/`` and ``.`` both collapse to ``-``, so the encoding is not
round-trippable. The canonical lookup reads the first JSONL entry's ``cwd``
field — see :func:`_project_dir_for_cwd`.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from crash_recovery.jsonl import first_record_field

if TYPE_CHECKING:
    from pathlib import Path

    from crash_recovery.liveness import Liveness


class CorrelationKind(StrEnum):
    """Outcomes for a single correlate() call."""

    DIRECT_MATCH = "direct_match"
    MTIME_MATCH = "mtime_match"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


@dataclass(frozen=True)
class CorrelationResult:
    """The verdict produced by :func:`correlate`.

    Attributes
    ----------
    kind
        Discriminator. ``DIRECT_MATCH`` and ``MTIME_MATCH`` carry a single
        ``uuid``; ``AMBIGUOUS`` carries the full list in ``candidates``;
        ``NO_MATCH`` carries neither.
    uuid
        The matched session UUID for ``DIRECT_MATCH`` / ``MTIME_MATCH``;
        ``None`` otherwise.
    candidates
        Full list of in-window UUIDs for ``AMBIGUOUS``; empty tuple
        otherwise.
    """

    kind: CorrelationKind
    uuid: str | None = None
    candidates: tuple[str, ...] = field(default_factory=tuple)


# Strict UUID match — five hex groups joined by dashes. Used to guard
# ``--resume <token>`` so we don't accept a non-UUID positional that
# happened to follow ``--resume``.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Clock-skew grace for the first-entry-timestamp filter. Wrappers may run on
# machines whose clocks differ from the JSONL writer by a small amount;
# a 60-second window swallows that without admitting hour-old false
# positives.
_CLOCK_SKEW_GRACE_SECONDS = 60

# Upper bound of the tight first-entry-ts window (Phase 3). A JSONL whose first
# real entry begins more than this many seconds after the wrapper's ``started``
# was a *separate* session that opened later in the same cwd, not the wrapper's
# own session — so it is excluded. Resumed sessions (whose first-entry-ts
# predates ``started``) are handled by the session_id / --resume direct paths
# ahead of this scan, so the lower bound staying at ``started - grace`` is safe.
_TIGHT_WINDOW_SECONDS = 120


def _cwd_matches_any_jsonl_in(child: Path, cwd: str) -> bool:
    """Return whether any ``.jsonl`` in ``child`` declares the given ``cwd``.

    Iterates every ``.jsonl`` file in ``child``, using
    :func:`crash_recovery.jsonl.first_record_field` to scan forward past
    snapshot/bookkeeping records so that modern transcripts (where ``cwd``
    sits on line 2 or later) are read correctly. Returns ``True`` on the
    first match; returns ``False`` only after scanning every JSONL.

    Why scan every JSONL rather than short-circuit after the first read:
    Claude Code's encoded-directory naming is lossy — ``/`` and ``.`` both
    collapse to ``-``, so two distinct cwds (e.g. ``/home/x/y-z`` and
    ``/home/x-y/z``) can share one encoded directory. A non-matching first
    record does NOT mean this directory is irrelevant; a later JSONL may
    match. An earlier version of the parent function broke out of the
    inner loop after one read; the optimisation was unsafe and was
    removed after Phase 3 proleptic challenge CA1 (2026-05-16). Full-scan
    cost is microseconds at realistic scale.
    """
    for jsonl in child.glob("*.jsonl"):
        if first_record_field(jsonl, "cwd") == cwd:
            return True
    return False


def _project_dir_for_cwd(projects_root: Path, cwd: str) -> Path | None:
    """Return the ``~/.claude/projects/<encoded>/`` dir whose JSONLs declare ``cwd``.

    Iterates children of ``projects_root`` and returns the first child whose
    JSONLs declare the requested ``cwd`` (see
    :func:`_cwd_matches_any_jsonl_in` for the per-child scan semantics).
    Returns ``None`` if no directory matches.

    Parameters
    ----------
    projects_root
        The ``~/.claude/projects/`` analogue (callers pass the resolved
        path, typically from ``~/.claude/projects``).
    cwd
        The cwd value (verbatim, as written by Claude Code) to look up.

    Returns
    -------
    Path | None
        The matching child directory or ``None``.
    """
    if not projects_root.exists() or not projects_root.is_dir():
        return None
    for child in sorted(projects_root.iterdir()):
        if not child.is_dir():
            continue
        if _cwd_matches_any_jsonl_in(child, cwd):
            return child
    return None


def _extract_resume_uuid(argv: str | None) -> str | None:
    """Return the UUID following ``--resume`` in ``argv``, or ``None``.

    Uses :func:`shlex.split` (not regex) so the parser tolerates shell-quoted
    fragments and the ``=`` signs the wrapper preserves verbatim in argv
    (e.g. ``--resume db0... --extra=value=with=signs``). The trailing
    :data:`_UUID_RE` match guards against accepting a non-UUID token that
    happened to sit immediately after ``--resume``.
    """
    if argv is None:
        return None
    try:
        tokens = shlex.split(argv)
    except ValueError:
        return None
    for i, arg in enumerate(tokens):
        if arg == "--resume" and i + 1 < len(tokens):
            candidate = tokens[i + 1]
            if _UUID_RE.match(candidate):
                return candidate.lower()
    return None


def _jsonl_first_entry_ts_in_tight_window(jsonl: Path, started: int) -> bool:
    """Return whether the JSONL's first real entry's timestamp is in the tight window.

    The tight window is ``[started - _CLOCK_SKEW_GRACE_SECONDS,
    started + _TIGHT_WINDOW_SECONDS]``. The lower bound (Phase 1) absorbs
    clock skew between the wrapper and the JSONL writer; the upper bound
    (Phase 3) excludes a *later* session that opened in the same cwd well
    after the wrapper started. Resumed sessions (first-entry-ts predating
    ``started``) are caught by the session_id / --resume direct paths ahead
    of the scan, so the lower bound is safe.

    Uses :func:`crash_recovery.jsonl.first_record_field` to scan forward past
    snapshot/bookkeeping records so that modern transcripts (where
    ``timestamp`` sits on line 2 or later) are read correctly.

    Conservatively returns ``False`` on any parsing error (missing file,
    unreadable file, no parseable ``timestamp`` within the scan window, or
    unparseable ISO-8601 value). Excluding a candidate is safer than admitting
    one with an indeterminate start time — false negatives only widen the
    AMBIGUOUS / NO_MATCH classes; false positives could cause hard_crash to be
    declared on a session that was never the wrapper's.
    """
    raw_ts = first_record_field(jsonl, "timestamp")
    if raw_ts is None:
        return False
    # JSONL timestamps are ISO-8601 with a trailing "Z" (the Claude Code
    # writer's convention). datetime.fromisoformat() accepts "+00:00" but
    # not "Z" directly until 3.11+; normalise to be safe across runtimes.
    try:
        entry_dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    entry_ts = int(entry_dt.timestamp())
    return (
        started - _CLOCK_SKEW_GRACE_SECONDS
        <= entry_ts
        <= started + _TIGHT_WINDOW_SECONDS
    )


def _apply_corroboration(
    candidates: list[str],
    candidate_cwd: dict[str, str | None],
    corroborated_cwds: frozenset[str] | None,
) -> CorrelationResult:
    """Resolve a >1-candidate set via resurrect corroboration.

    Given a tight-window candidate set with more than one member, narrow it
    using ``corroborated_cwds`` (the pane cwds live at crash time, from
    :mod:`crash_recovery.resurrect`). Each candidate's own first-entry cwd is
    matched against the corroborated set. If exactly one candidate survives,
    the verdict is ``MTIME_MATCH``; otherwise (zero survivors, more than one
    survivor, or ``corroborated_cwds is None``) the verdict is ``AMBIGUOUS``
    carrying the **full** candidate tuple — corroboration narrows to a single
    winner or it reports everything; it never silently drops a candidate from
    the reported set.
    """
    if corroborated_cwds is not None:
        survivors = [
            stem
            for stem in candidates
            if candidate_cwd[stem] is not None
            and candidate_cwd[stem] in corroborated_cwds
        ]
        if len(survivors) == 1:
            return CorrelationResult(
                kind=CorrelationKind.MTIME_MATCH,
                uuid=survivors[0],
            )
        # 0 or >1 survivors → fall through to AMBIGUOUS with the FULL set
        # (all-means-all: never report the filtered subset).

    return CorrelationResult(
        kind=CorrelationKind.AMBIGUOUS,
        candidates=tuple(candidates),
    )


def correlate(
    liveness: Liveness,
    projects_root: Path,
    *,
    corroborated_cwds: frozenset[str] | None = None,
) -> CorrelationResult:
    """Resolve ``liveness`` to a candidate session UUID.

    Strategy:

    1. Try the direct ``session_id`` match and confirm the JSONL exists in the
       project directory for ``liveness.cwd``.
    2. Try the optional legacy argv fallback: parse ``--resume <uuid>`` out of
       ``liveness.argv`` and confirm its JSONL exists.
    3. If the project directory doesn't exist, return ``NO_MATCH``.
    4. Otherwise enumerate JSONLs in the project directory whose mtime is
       ≥ ``liveness.started`` AND whose first-entry timestamp lies in the
       tight window ``[started - grace, started + _TIGHT_WINDOW_SECONDS]``.
       Report ``MTIME_MATCH`` (one), ``AMBIGUOUS`` (multiple), or
       ``NO_MATCH`` (none).

    Resurrect corroboration (Phase 3): when the tight window yields more than
    one candidate AND ``corroborated_cwds`` is provided, the candidates are
    filtered to those whose own first-entry ``cwd`` is in ``corroborated_cwds``
    (the pane cwds live at crash time, from :mod:`crash_recovery.resurrect`).
    If exactly one candidate survives that filter, it resolves to
    ``MTIME_MATCH``. Otherwise (zero survivors, more than one survivor, or
    ``corroborated_cwds is None``) the verdict is ``AMBIGUOUS`` carrying the
    **full** tight-window candidate tuple — corroboration narrows to a single
    winner or it reports everything; it never silently drops a candidate from
    the reported set. The per-candidate cwd is read from each JSONL's own
    forward-scan, NOT from ``liveness.cwd`` — under a lossy encoded-directory
    collision two candidates in one directory can declare distinct cwds, and
    that distinction is exactly what corroboration disambiguates.

    The argv path *falls through* to mtime when the argv-claimed UUID's
    JSONL is gone — this is intentional. The wrapper hint was the best
    available signal; we still try to report something useful before giving
    up. See ``test_correlate_argv_uuid_but_jsonl_missing_falls_back_to_mtime``.

    Conservative argv-without-project-dir handling (Phase 3 coherence
    review M4, 2026-05-16): when ``argv`` carries ``--resume <uuid>`` but
    ``_project_dir_for_cwd`` returns ``None`` (the cwd cannot be located
    on disk), we return ``NO_MATCH`` and drop the wrapper hint rather than
    surfacing the unverified UUID. The wrapper's claim could refer to a
    JSONL anywhere on disk; without a project directory we cannot confirm
    the UUID maps to a real session. Conservative is correct here:
    misattributing a UUID to a session whose files we cannot find would
    poison downstream classification. See
    ``test_correlate_argv_uuid_but_no_project_dir_is_no_match``.
    """
    project_dir = _project_dir_for_cwd(projects_root, liveness.cwd)

    # 0. Exact session_id match (Phase 2). Highest confidence: the wrapper
    #    stamped the effective session UUID directly into the marker.
    if liveness.session_id is not None and project_dir is not None:
        sid = liveness.session_id.lower()
        if _UUID_RE.match(sid) and (project_dir / f"{sid}.jsonl").exists():
            return CorrelationResult(
                kind=CorrelationKind.DIRECT_MATCH,
                uuid=sid,
            )
        # session_id present but unusable (bad shape or JSONL gone) — fall
        # through to the --resume / mtime paths rather than fabricate a match.

    # 1. Optional legacy argv direct match.
    resume_uuid = _extract_resume_uuid(liveness.argv)
    if resume_uuid is not None and project_dir is not None:
        jsonl_path = project_dir / f"{resume_uuid}.jsonl"
        if jsonl_path.exists():
            return CorrelationResult(
                kind=CorrelationKind.DIRECT_MATCH,
                uuid=resume_uuid,
            )
        # argv claimed a UUID but the JSONL is gone — fall through to mtime
        # so we still report something useful.

    if project_dir is None:
        # See docstring: conservative drop of the wrapper hint when we
        # cannot locate the project directory on disk (coherence review M4).
        return CorrelationResult(kind=CorrelationKind.NO_MATCH)

    # 2. tight-window scan over JSONLs in project_dir. Track each candidate's
    #    own first-entry cwd alongside its UUID so corroboration can filter by
    #    the candidate's *own* cwd (not liveness.cwd — see docstring).
    candidates: list[str] = []
    candidate_cwd: dict[str, str | None] = {}
    for jsonl in sorted(project_dir.glob("*.jsonl")):
        try:
            stat = jsonl.stat()
        except OSError:
            continue
        if stat.st_mtime < liveness.started:
            continue
        if not _jsonl_first_entry_ts_in_tight_window(jsonl, liveness.started):
            continue
        stem = jsonl.stem
        candidates.append(stem)
        candidate_cwd[stem] = first_record_field(jsonl, "cwd")

    if not candidates:
        return CorrelationResult(kind=CorrelationKind.NO_MATCH)
    if len(candidates) == 1:
        return CorrelationResult(
            kind=CorrelationKind.MTIME_MATCH,
            uuid=candidates[0],
        )

    # >1 candidate. Try resurrect corroboration to pick a single winner.
    return _apply_corroboration(candidates, candidate_cwd, corroborated_cwds)
