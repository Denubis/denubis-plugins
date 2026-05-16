"""Correlate a liveness record to candidate session UUIDs.

The Phase 3 correlator decides which JSONL session a recovered liveness file
points at. Two strategies, in order:

1. **Argv direct match** — if ``liveness.argv`` contains ``--resume <uuid>``
   AND ``<uuid>.jsonl`` exists in the project directory whose JSONLs declare
   ``liveness.cwd``, return ``DIRECT_MATCH``. This is the high-confidence
   path; the wrapper invocation explicitly named the session.

2. **mtime-window fallback** — enumerate JSONLs in the project directory,
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

import json
import re
import shlex
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
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


def _project_dir_for_cwd(projects_root: Path, cwd: str) -> Path | None:
    """Return the ``~/.claude/projects/<encoded>/`` dir whose JSONLs declare ``cwd``.

    Iterates children of ``projects_root``. For each child directory, reads
    the first valid JSON line of every ``.jsonl`` file until one matches the
    requested ``cwd``. Returns the first matching directory, or ``None``
    if no directory matches.

    Why scan every JSONL rather than short-circuit after the first: Claude
    Code's encoded-directory naming is lossy — ``/`` and ``.`` both collapse
    to ``-``, so two distinct cwds (e.g. ``/home/x/y-z`` and ``/home/x-y/z``)
    can share one encoded directory. The first JSONL's ``cwd`` is therefore
    NOT authoritative for the whole directory under collision. An earlier
    version of this function broke out of the inner loop after one read;
    the optimisation was unsafe and was removed after Phase 3 proleptic
    challenge CA1 (2026-05-16). Full-scan cost is microseconds at realistic
    scale (dozens of dirs × dozens of JSONLs).

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
        for jsonl in child.glob("*.jsonl"):
            try:
                with jsonl.open("r", encoding="utf-8") as handle:
                    first = handle.readline()
                if not first.strip():
                    continue
                entry = json.loads(first)
            except (OSError, json.JSONDecodeError):
                continue
            entry_cwd = entry.get("cwd")
            if isinstance(entry_cwd, str) and entry_cwd == cwd:
                return child
            # Non-matching cwd here does NOT mean this directory is irrelevant.
            # Claude Code's encoded-directory naming is lossy (`/` and `.` both
            # collapse to `-`), so two distinct cwds can share one encoded
            # directory (e.g. `/home/x/y-z` and `/home/x-y/z`). Continue
            # scanning the rest of the directory; a later JSONL may match.
            # See phase_03.md proleptic CA1 (2026-05-16).
            continue
    return None


def _extract_resume_uuid(argv: str) -> str | None:
    """Return the UUID following ``--resume`` in ``argv``, or ``None``.

    Uses :func:`shlex.split` (not regex) so the parser tolerates shell-quoted
    fragments and the ``=`` signs the wrapper preserves verbatim in argv
    (e.g. ``--resume db0... --extra=value=with=signs``). The trailing
    :data:`_UUID_RE` match guards against accepting a non-UUID token that
    happened to sit immediately after ``--resume``.
    """
    try:
        tokens = shlex.split(argv)
    except ValueError:
        return None
    for i, token in enumerate(tokens):
        if token == "--resume" and i + 1 < len(tokens):
            candidate = tokens[i + 1]
            if _UUID_RE.match(candidate):
                return candidate.lower()
    return None


def _jsonl_first_entry_ts_meets_threshold(jsonl: Path, threshold: int) -> bool:
    """Return whether the JSONL's first entry's timestamp is ≥ ``threshold - 60``.

    Conservatively returns ``False`` on any parsing error (missing file,
    blank first line, invalid JSON, missing/unparseable ``timestamp``
    field). Excluding a candidate is safer than admitting one with an
    indeterminate start time — false negatives only widen the AMBIGUOUS
    / NO_MATCH classes; false positives could cause hard_crash to be
    declared on a session that was never the wrapper's.
    """
    try:
        with jsonl.open("r", encoding="utf-8") as handle:
            first = handle.readline()
        if not first.strip():
            return False
        entry = json.loads(first)
    except (OSError, json.JSONDecodeError):
        return False
    raw_ts = entry.get("timestamp")
    if not isinstance(raw_ts, str):
        return False
    # JSONL timestamps are ISO-8601 with a trailing "Z" (the Claude Code
    # writer's convention). datetime.fromisoformat() accepts "+00:00" but
    # not "Z" directly until 3.11+; normalise to be safe across runtimes.
    try:
        entry_dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    entry_ts = int(entry_dt.timestamp())
    return entry_ts >= threshold - _CLOCK_SKEW_GRACE_SECONDS


def correlate(liveness: Liveness, projects_root: Path) -> CorrelationResult:
    """Resolve ``liveness`` to a candidate session UUID.

    Strategy:

    1. Try argv direct match: parse ``--resume <uuid>`` out of
       ``liveness.argv`` and confirm ``<uuid>.jsonl`` exists in the project
       directory for ``liveness.cwd``.
    2. If the project directory doesn't exist, return ``NO_MATCH``.
    3. Otherwise enumerate JSONLs in the project directory whose mtime AND
       first-entry timestamp are ≥ ``liveness.started`` (minus a 60-second
       clock-skew grace). Report ``MTIME_MATCH`` (one), ``AMBIGUOUS``
       (multiple), or ``NO_MATCH`` (none).

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
    resume_uuid = _extract_resume_uuid(liveness.argv)
    project_dir = _project_dir_for_cwd(projects_root, liveness.cwd)

    # 1. Argv direct match.
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

    # 2. mtime-window scan over JSONLs in project_dir.
    candidates: list[str] = []
    for jsonl in sorted(project_dir.glob("*.jsonl")):
        try:
            stat = jsonl.stat()
        except OSError:
            continue
        if stat.st_mtime < liveness.started:
            continue
        if not _jsonl_first_entry_ts_meets_threshold(jsonl, liveness.started):
            continue
        candidates.append(jsonl.stem)

    if not candidates:
        return CorrelationResult(kind=CorrelationKind.NO_MATCH)
    if len(candidates) == 1:
        return CorrelationResult(
            kind=CorrelationKind.MTIME_MATCH,
            uuid=candidates[0],
        )
    return CorrelationResult(
        kind=CorrelationKind.AMBIGUOUS,
        candidates=tuple(candidates),
    )
