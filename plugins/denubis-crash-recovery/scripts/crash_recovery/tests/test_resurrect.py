"""Tests for crash_recovery.resurrect — tmux-resurrect snapshot parsing (AC6.4).

The resurrect parser turns a ``~/.byobu-sessions/tmux_resurrect_*.txt`` save
into a :class:`Snapshot` of :class:`Pane`s. correlate's corroboration filter
(Phase 3 Task 2/3) consumes the pane cwds to disambiguate id-less backlog
markers; Phase 4 consumes the labels.

Every fixture writes a temp snapshot file mirroring the real TAB layout
confirmed against ``~/.byobu-sessions`` on 2026-06-17: each ``pane`` line is
TAB-separated with the path (field 7) and shell (field 10) carrying a leading
``:``. No test reads the operator's real snapshots — all data is synthesised
under ``tmp_path``.

The field layout (0-indexed) is::

    [0]=pane [1]=session [2]=window [3]=pane-idx [4]=flags(:*) [5]=1
    [6]=<window title> [7]=:<cwd> [8]=1 [9]=<command/shell> [10]=:<shell>

Timestamp handling is deliberately tested by *relative ordering*, not absolute
epoch: ``Snapshot.ts`` is parsed from the filename's naive ``YYYYMMDDTHHMMSS``
via ``datetime.timestamp()``, which is local-time dependent. Hardcoding an
epoch would make the suite TZ-fragile.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from crash_recovery.resurrect import (
    Pane,
    Snapshot,
    corroborating_cwds,
    label_for_cwd,
    load_snapshots,
    parse_snapshot_file,
    snapshot_near,
)

# The U+2733 glyph the exec-session-naming prefix stamps on an idle claude
# pane title. (A *busy* pane shows a volatile braille spinner instead — so
# corroboration is path-based, never glyph-based; the glyph only picks the
# best label among same-cwd panes.)
_STAR = "✳"
_SPINNER = "⠐"  # one frame of the volatile busy spinner (braille range)

_PROJ = "/home/brian/people/Brian/brian-ed3d-plugins"
_OTHER = "/home/brian/people/Jodie/some-other-project"


def _pane_line(
    *,
    session: str = "1",
    window: str = "1",
    pane_idx: str = "1",
    flags: str = ":*",
    title: str,
    cwd: str,
    command: str = "bash",
    shell: str = "/usr/bin/fish -l",
) -> str:
    """Build one real-format TAB-separated ``pane`` line.

    The path (field 7) and shell (field 10) carry a leading ``:`` exactly as
    tmux-resurrect writes them; the parser strips the path's leading ``:``.
    """
    return "\t".join(
        [
            "pane",
            session,
            window,
            pane_idx,
            flags,
            "1",
            title,
            f":{cwd}",
            "1",
            command,
            f":{shell}",
        ]
    )


def _write_snapshot(dir_: Path, stamp: str, lines: list[str]) -> Path:
    """Write a ``tmux_resurrect_<stamp>.txt`` file with the given lines."""
    path = dir_ / f"tmux_resurrect_{stamp}.txt"
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# parse_snapshot_file — AC6.4 parse
# ---------------------------------------------------------------------------


def test_parse_snapshot_file_extracts_panes_verbatim(tmp_path: Path) -> None:
    """AC6.4: title verbatim, cwd with leading ':' stripped, command = shell.

    Two panes mirroring the real format: one busy-spinner-titled and one
    star-titled, both sharing the project cwd, plus a third in another cwd.
    """
    lines = [
        "state\t1",  # a non-pane line — must be ignored
        _pane_line(title=f"{_SPINNER} crash-detection", cwd=_PROJ, command="bash"),
        _pane_line(title=f"{_STAR} crash-detection", cwd=_PROJ, command="bash"),
        _pane_line(title=f"{_STAR} other work", cwd=_OTHER, command="bash"),
    ]
    path = _write_snapshot(tmp_path, "20260617T155114", lines)

    snap = parse_snapshot_file(path)

    assert isinstance(snap, Snapshot)
    assert len(snap.panes) == 3
    first = snap.panes[0]
    assert isinstance(first, Pane)
    # Title is verbatim, including the volatile spinner glyph.
    assert first.window_title == f"{_SPINNER} crash-detection"
    # cwd had its leading ':' stripped.
    assert first.cwd == _PROJ
    # command is the shell (field 9), not "claude".
    assert first.command == "bash"


def test_parse_snapshot_file_parses_ts_from_filename(tmp_path: Path) -> None:
    """AC6.4: ts comes from the filename's YYYYMMDDTHHMMSS, not file mtime.

    TZ-robust: rather than assert an absolute epoch (local-time dependent),
    assert that two filenames an hour apart yield ts values one hour apart.
    """
    line = [_pane_line(title=f"{_STAR} x", cwd=_PROJ)]
    earlier = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T150000", line))
    later = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T160000", line))
    assert later.ts - earlier.ts == 3600


def test_parse_snapshot_file_skips_non_pane_lines(tmp_path: Path) -> None:
    """Non-``pane`` lines (window/state/grp/etc.) are ignored, not parsed."""
    lines = [
        "window\t1\t1\t:foo",
        "grp\t1\t1",
        _pane_line(title=f"{_STAR} only pane", cwd=_PROJ),
        "state\tclient",
    ]
    snap = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T155114", lines))
    assert len(snap.panes) == 1
    assert snap.panes[0].window_title == f"{_STAR} only pane"


def test_parse_snapshot_file_malformed_pane_line_skipped_with_warning(
    tmp_path: Path,
) -> None:
    """A ``pane`` line with <11 fields is skipped with a UserWarning; others survive.

    Per spec the malformed threshold is <11 fields even though only indices
    6/7/9 are read — a truncated line cannot be trusted. The valid pane in the
    same file must still parse, proving the loop continues past the bad line.
    """
    malformed = "\t".join(["pane", "1", "1", "1", ":*", "1"])  # 6 fields, truncated
    lines = [
        malformed,
        _pane_line(title=f"{_STAR} good", cwd=_PROJ),
    ]
    path = _write_snapshot(tmp_path, "20260617T155114", lines)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        snap = parse_snapshot_file(path)

    assert any(issubclass(w.category, UserWarning) for w in caught)
    # The valid pane still parsed.
    assert len(snap.panes) == 1
    assert snap.panes[0].window_title == f"{_STAR} good"


# ---------------------------------------------------------------------------
# load_snapshots
# ---------------------------------------------------------------------------


def test_load_snapshots_sorted_by_ts(tmp_path: Path) -> None:
    """All ``tmux_resurrect_*.txt`` parsed, returned sorted ascending by ts."""
    line = [_pane_line(title=f"{_STAR} x", cwd=_PROJ)]
    # Write out of order on disk.
    _write_snapshot(tmp_path, "20260617T160000", line)
    _write_snapshot(tmp_path, "20260617T140000", line)
    _write_snapshot(tmp_path, "20260617T150000", line)

    snaps = load_snapshots(tmp_path)
    assert [s.ts for s in snaps] == sorted(s.ts for s in snaps)
    assert len(snaps) == 3


def test_load_snapshots_missing_dir_is_empty(tmp_path: Path) -> None:
    """A non-existent resurrect dir → empty list (corroboration no-op)."""
    assert load_snapshots(tmp_path / "does-not-exist") == []


def test_load_snapshots_empty_dir_is_empty(tmp_path: Path) -> None:
    """An existing but empty dir → empty list."""
    assert load_snapshots(tmp_path) == []


# ---------------------------------------------------------------------------
# snapshot_near — AC6.4 selection
# ---------------------------------------------------------------------------


def test_snapshot_near_picks_latest_at_or_before_started(tmp_path: Path) -> None:
    """The pre-crash save: greatest ts <= started is chosen.

    Selection is asserted by *which* snapshot is returned (relative ordering),
    not by an absolute epoch — keeps the test TZ-robust.
    """
    line_a = [_pane_line(title=f"{_STAR} a", cwd="/cwd/a")]
    line_b = [_pane_line(title=f"{_STAR} b", cwd="/cwd/b")]
    line_c = [_pane_line(title=f"{_STAR} c", cwd="/cwd/c")]
    early = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T140000", line_a))
    mid = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T150000", line_b))
    late = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T160000", line_c))
    snaps = [early, mid, late]

    # started sits between mid and late → mid is the pre-crash save.
    started = mid.ts + 60
    chosen = snapshot_near(snaps, started)
    assert chosen is mid


def test_snapshot_near_returns_none_when_all_later(tmp_path: Path) -> None:
    """started precedes every snapshot → None (no pre-crash save exists)."""
    line = [_pane_line(title=f"{_STAR} x", cwd=_PROJ)]
    s = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T160000", line))
    assert snapshot_near([s], s.ts - 60) is None


def test_snapshot_near_empty_list_is_none() -> None:
    """No snapshots → None."""
    assert snapshot_near([], 1_700_000_000) is None


def test_snapshot_near_grace_admits_just_after_started(tmp_path: Path) -> None:
    """A snapshot saved within ``grace`` seconds after ``started`` still qualifies.

    Continuum saves on a timer; the save bracketing a marker can land a few
    seconds after the wrapper's ``started``. ``grace`` widens the upper bound
    to ``started + grace``.
    """
    line = [_pane_line(title=f"{_STAR} x", cwd=_PROJ)]
    s = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T160000", line))
    # started is 30s before the snapshot; without grace → None, with grace → s.
    started = s.ts - 30
    assert snapshot_near([s], started) is None
    assert snapshot_near([s], started, grace=60) is s


# ---------------------------------------------------------------------------
# corroborating_cwds / label_for_cwd
# ---------------------------------------------------------------------------


def test_corroborating_cwds_collects_all_pane_paths(tmp_path: Path) -> None:
    """Corroboration is path-based: every pane cwd is included, regardless of glyph."""
    lines = [
        _pane_line(title=f"{_SPINNER} busy", cwd=_PROJ),  # busy spinner, still counts
        _pane_line(title="plain no-glyph", cwd=_OTHER),  # no star, still counts
    ]
    snap = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T155114", lines))
    assert corroborating_cwds(snap) == {_PROJ, _OTHER}


def test_label_for_cwd_prefers_star_titled_pane(tmp_path: Path) -> None:
    """Among same-cwd panes, the ``✳``-prefixed title wins as the label."""
    lines = [
        _pane_line(title=f"{_SPINNER} busy frame", cwd=_PROJ),
        _pane_line(title=f"{_STAR} the real label", cwd=_PROJ),
    ]
    snap = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T155114", lines))
    assert label_for_cwd(snap, _PROJ) == f"{_STAR} the real label"


def test_label_for_cwd_falls_back_to_any_title_without_star(tmp_path: Path) -> None:
    """No star-titled pane at the cwd → return some (non-None) title for it."""
    lines = [_pane_line(title=f"{_SPINNER} busy only", cwd=_PROJ)]
    snap = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T155114", lines))
    assert label_for_cwd(snap, _PROJ) == f"{_SPINNER} busy only"


def test_label_for_cwd_none_when_cwd_absent(tmp_path: Path) -> None:
    """No pane at the requested cwd → None."""
    lines = [_pane_line(title=f"{_STAR} x", cwd=_PROJ)]
    snap = parse_snapshot_file(_write_snapshot(tmp_path, "20260617T155114", lines))
    assert label_for_cwd(snap, "/nowhere") is None


def test_label_for_cwd_none_snapshot_returns_none() -> None:
    """A ``None`` snapshot degrades to ``None`` rather than raising.

    ``label_for_cwd``'s natural partner is ``snapshot_near``, which returns
    ``Snapshot | None`` (``None`` when the resurrect dir is empty or every
    save predates ``started``). Passing that result straight through must
    yield ``None`` — mirroring ``load_snapshots`` → ``[]`` and
    ``snapshot_near`` → ``None`` — not raise ``AttributeError`` on
    ``None.panes``. The Phase 4 render call site relies on this.
    """
    assert label_for_cwd(None, "/any/cwd") is None
