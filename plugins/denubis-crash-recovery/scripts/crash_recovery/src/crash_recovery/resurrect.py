"""Parse tmux-resurrect snapshots into pane sets for backlog corroboration.

tmux-continuum saves the running tmux/byobu layout roughly every 15 minutes to
``~/.byobu-sessions/tmux_resurrect_<YYYYMMDDTHHMMSS>.txt`` (NOT ``~/.tmux/``).
Each file lists windows and panes; this module reads the ``pane`` lines and
exposes the per-pane current working directory so :mod:`crash_recovery.correlate`
can corroborate an id-less backlog marker against the panes that were live at
crash time.

Why corroboration is **path-based**, not command- or glyph-based
----------------------------------------------------------------
A ``pane`` line's command field (index 9) is the *shell* (``bash``/``fish``),
because the wrapper runs ``claude`` under a shell — it is never literally
``claude``. The window title's leading glyph is also unstable: an idle claude
pane shows ``✳`` (U+2733, the ``exec-session-naming`` prefix), but a *busy*
pane shows a braille-range spinner glyph that changes frame to frame. So the
only stable corroboration signal is :func:`corroborating_cwds` —
``pane_current_path``. The ``✳`` prefix is used solely by
:func:`label_for_cwd` to pick the nicest *label* when several panes share a
path; it is never the gate.

Determinism
-----------
``Snapshot.ts`` is parsed from the filename's ``YYYYMMDDTHHMMSS`` (interpreted
as local time), never from file mtime or a wall-clock read. "Near ``started``"
in :func:`snapshot_near` is computed from stored values only. No argless
``datetime.now()`` anywhere.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# The exec-session-naming prefix stamped on an idle claude pane's window title.
# Used ONLY to pick the best label among same-cwd panes (see label_for_cwd);
# never as a corroboration gate (a busy pane shows a volatile spinner instead).
_CLAUDE_TITLE_PREFIX = "✳"

# Filename stamp format: tmux_resurrect_YYYYMMDDTHHMMSS.txt
_TS_FORMAT = "%Y%m%dT%H%M%S"

# A well-formed ``pane`` line has at least this many TAB fields. We read indices
# 6/7/9, but a line shorter than the full real layout is truncated and cannot be
# trusted, so the threshold is the full field count rather than max-index-read.
_MIN_PANE_FIELDS = 11

# Field indices within a TAB-split ``pane`` line (0-indexed). See module docstring.
_TITLE_FIELD = 6
_CWD_FIELD = 7
_COMMAND_FIELD = 9


@dataclass(frozen=True)
class Pane:
    """One tmux pane from a resurrect snapshot.

    Attributes
    ----------
    window_title
        Field 6, verbatim. May start with ``✳`` (idle claude) or a volatile
        braille spinner glyph (busy claude), or carry no glyph at all.
    cwd
        Field 7 with its leading ``:`` stripped — the pane's current working
        directory, the corroboration signal.
    command
        Field 9 — the shell (``bash``/``fish``), not ``claude``.
    """

    window_title: str
    cwd: str
    command: str


@dataclass(frozen=True)
class Snapshot:
    """A parsed resurrect save: a timestamp plus the panes it recorded.

    Attributes
    ----------
    ts
        Unix epoch parsed from the filename's ``YYYYMMDDTHHMMSS`` (local time).
    panes
        The ``pane`` lines parsed from the file, in file order.
    """

    ts: int
    panes: tuple[Pane, ...]


def _ts_from_filename(path: Path) -> int:
    """Return the unix epoch encoded in ``tmux_resurrect_<stamp>.txt``.

    The stamp is a naive local-time ``YYYYMMDDTHHMMSS``; ``datetime.timestamp()``
    on the naive value interprets it in the system's local zone, matching how
    tmux-continuum wrote it.
    """
    stamp = path.stem.removeprefix("tmux_resurrect_")
    return int(datetime.strptime(stamp, _TS_FORMAT).timestamp())


def parse_snapshot_file(path: Path) -> Snapshot:
    """Parse one resurrect file into a :class:`Snapshot`.

    Reads ``ts`` from the filename, then keeps lines whose first TAB field is
    ``pane``, splitting each on ``\\t`` and building a :class:`Pane` from fields
    6/7/9 (stripping the leading ``:`` on the cwd). Lines that are not ``pane``
    lines (``window``/``state``/``grp``/…) are ignored. A ``pane`` line with
    fewer than :data:`_MIN_PANE_FIELDS` fields is malformed: it is skipped and a
    :class:`UserWarning` is emitted, while well-formed panes in the same file
    still parse.
    """
    ts = _ts_from_filename(path)
    panes: list[Pane] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if not fields or fields[0] != "pane":
            continue
        if len(fields) < _MIN_PANE_FIELDS:
            warnings.warn(
                f"skipping malformed pane line ({len(fields)} fields) in {path}",
                UserWarning,
                stacklevel=2,
            )
            continue
        panes.append(
            Pane(
                window_title=fields[_TITLE_FIELD],
                cwd=fields[_CWD_FIELD].removeprefix(":"),
                command=fields[_COMMAND_FIELD],
            )
        )
    return Snapshot(ts=ts, panes=tuple(panes))


def load_snapshots(resurrect_dir: Path) -> list[Snapshot]:
    """Parse every ``tmux_resurrect_*.txt`` under ``resurrect_dir``, sorted by ts.

    A missing or empty directory yields ``[]`` (corroboration becomes a no-op).
    """
    if not resurrect_dir.exists() or not resurrect_dir.is_dir():
        return []
    snaps = [parse_snapshot_file(p) for p in resurrect_dir.glob("tmux_resurrect_*.txt")]
    return sorted(snaps, key=lambda s: s.ts)


def snapshot_near(
    snapshots: list[Snapshot], started: int, grace: int = 0
) -> Snapshot | None:
    """Return the snapshot with the greatest ``ts <= started + grace``.

    This is the pre-crash save: the most recent continuum save at or just after
    the marker's ``started`` (continuum saves roughly every 15 minutes, so the
    bracketing save usually precedes ``started``; ``grace`` admits a save that
    landed a few seconds after). Returns ``None`` when no snapshot qualifies.
    """
    eligible = [s for s in snapshots if s.ts <= started + grace]
    if not eligible:
        return None
    return max(eligible, key=lambda s: s.ts)


def corroborating_cwds(snapshot: Snapshot) -> set[str]:
    """Return the set of every pane cwd in ``snapshot``.

    Corroboration is path-based (see module docstring), so all pane cwds count
    regardless of the pane's command or window-title glyph.
    """
    return {pane.cwd for pane in snapshot.panes}


def label_for_cwd(snapshot: Snapshot | None, cwd: str) -> str | None:
    """Return a window-title label for panes at ``cwd``, preferring a ``✳`` title.

    Among panes whose cwd matches, a title starting with
    :data:`_CLAUDE_TITLE_PREFIX` is preferred (it names the idle claude
    session); otherwise the first matching pane's title is returned. ``None``
    when no pane sits at ``cwd``. Consumed by Phase 4 for the render label.

    ``snapshot`` may be ``None`` — the natural partner :func:`snapshot_near`
    returns ``Snapshot | None``, so the common call
    ``label_for_cwd(snapshot_near(...), cwd)`` would otherwise raise on an
    empty/old resurrect dir. A ``None`` snapshot degrades to ``None`` here,
    mirroring ``load_snapshots`` → ``[]`` and ``snapshot_near`` → ``None``.
    """
    if snapshot is None:
        return None
    matching = [pane for pane in snapshot.panes if pane.cwd == cwd]
    if not matching:
        return None
    for pane in matching:
        if pane.window_title.startswith(_CLAUDE_TITLE_PREFIX):
            return pane.window_title
    return matching[0].window_title
