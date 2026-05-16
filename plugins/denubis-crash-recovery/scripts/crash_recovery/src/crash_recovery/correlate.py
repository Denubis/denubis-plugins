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

This module lands across two tasks: Task 3 adds the types and the
``_project_dir_for_cwd`` helper; Task 4 wires :func:`correlate` and its
argv/mtime helpers on top.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


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


def _project_dir_for_cwd(projects_root: Path, cwd: str) -> Path | None:
    """Return the ``~/.claude/projects/<encoded>/`` dir whose JSONLs declare ``cwd``.

    Iterates children of ``projects_root``. For each child directory, reads
    the first JSON line of the first ``.jsonl`` file it finds and checks the
    entry's ``cwd`` field. Returns the first matching directory, or ``None``
    if no directory matches.

    The break-out-of-inner-loop after one JSONL read is deliberate: Claude
    Code groups all sessions for a given cwd under one encoded directory, so
    one JSONL's ``cwd`` is authoritative for the whole directory. Reading
    additional JSONLs in the same directory would waste I/O and tell us
    nothing new.

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
            # First JSONL in this dir didn't match; remaining JSONLs in the
            # same dir have the same cwd by Claude Code's grouping
            # convention, so break out of the inner loop.
            break
    return None
