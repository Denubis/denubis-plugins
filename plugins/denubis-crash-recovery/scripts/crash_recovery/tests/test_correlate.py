"""Tests for crash_recovery.correlate — argv-resume, mtime-window, ambiguous, no-match.

Covers the correlate side of AC6.1: a liveness record either resolves to a
session UUID (DIRECT_MATCH via argv ``--resume``; MTIME_MATCH via single
candidate within the mtime window) or surfaces an explicit AMBIGUOUS /
NO_MATCH verdict for the scan caller to act on. The Phase 3 plan's
``_project_dir_for_cwd`` helper is exercised independently so future changes
to its directory-lookup heuristic don't accidentally regress correlate
behaviour.
"""

from __future__ import annotations

import os
from pathlib import Path

from crash_recovery.correlate import (
    CorrelationKind,
    CorrelationResult,
    _extract_resume_uuid,
    _project_dir_for_cwd,
    correlate,
)
from crash_recovery.liveness import Liveness

# pytest injects tests/ onto sys.path (see test_liveness.py for the same
# rationale — Phase 1 omitted tests/__init__.py to keep the package
# importable as a top-level "fixtures").
from fixtures.jsonl_builder import make_project_dir

# Stable UUIDs used across tests so assertions stay readable.
_UUID_A = "db0cc58f-dc30-4195-a64a-4f25a5c19d6b"
_UUID_B = "11111111-2222-3333-4444-555555555555"
_UUID_C = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

_BOOT = "8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d"


def _make_liveness(
    *,
    cwd: str,
    started: int,
    argv: str = "",
    pid: int = 1234,
) -> Liveness:
    """Construct a Liveness directly (no on-disk file) — correlate doesn't read it."""
    return Liveness(
        path=Path(f"/tmp/{pid}.live"),
        pid=pid,
        cwd=cwd,
        started=started,
        argv=argv,
        boot_id=_BOOT,
    )


# ---------------------------------------------------------------------------
# _project_dir_for_cwd
# ---------------------------------------------------------------------------


def test_project_dir_for_cwd_finds_match_among_multiple_dirs(tmp_path: Path) -> None:
    """Of three project dirs declaring different cwds, the matching one wins."""
    make_project_dir(tmp_path, cwd="/home/user/alpha", uuids=[_UUID_A])
    target = make_project_dir(tmp_path, cwd="/home/user/target", uuids=[_UUID_B])
    make_project_dir(tmp_path, cwd="/home/user/gamma", uuids=[_UUID_C])
    assert _project_dir_for_cwd(tmp_path, "/home/user/target") == target


def test_project_dir_for_cwd_returns_none_for_no_match(tmp_path: Path) -> None:
    """No project dir declares the requested cwd → helper returns None."""
    make_project_dir(tmp_path, cwd="/home/user/alpha", uuids=[_UUID_A])
    make_project_dir(tmp_path, cwd="/home/user/beta", uuids=[_UUID_B])
    make_project_dir(tmp_path, cwd="/home/user/gamma", uuids=[_UUID_C])
    assert _project_dir_for_cwd(tmp_path, "/home/user/missing") is None


def test_project_dir_for_cwd_skips_blank_first_jsonl_and_finds_match_in_second(
    tmp_path: Path,
) -> None:
    """First JSONL in dir is blank; second has matching cwd → dir is returned.

    Exercises the ``continue`` branch in :func:`_project_dir_for_cwd`: when
    ``first.strip()`` is empty the file is skipped and the inner loop moves on
    to the next ``.jsonl``.  Without this path exercised, a directory whose
    earliest JSONL is blank (e.g. a zero-byte file left by an interrupted write)
    would silently drop the whole directory even when a valid second JSONL holds
    the authoritative cwd.
    """
    import json

    project_dir = tmp_path / "-encoded-blank-first-test"
    project_dir.mkdir()

    # Lexicographically first: UUID starting with 0 — empty content.
    blank_jsonl = project_dir / f"0{_UUID_A[1:]}.jsonl"
    blank_jsonl.write_text("")

    # Lexicographically second: UUID_B — valid first entry with the target cwd.
    target_cwd = "/home/user/blank-first-target"
    valid_entry = {
        "type": "user",
        "cwd": target_cwd,
        "timestamp": "2026-05-16T00:00:00.000Z",
        "message": {"content": []},
    }
    valid_jsonl = project_dir / f"{_UUID_B}.jsonl"
    valid_jsonl.write_text(json.dumps(valid_entry) + "\n")

    result = _project_dir_for_cwd(tmp_path, target_cwd)
    assert result == project_dir


def test_project_dir_for_cwd_handles_encoding_collision(tmp_path: Path) -> None:
    """One encoded dir holds JSONLs from two distinct cwds → both are findable.

    Claude Code's encoded-directory naming is lossy: `/` and `.` both collapse
    to `-`, so distinct cwds (e.g. `/home/x/y-z` and `/home/x-y/z`) can share
    one encoded directory. Under collision the first JSONL's cwd is NOT
    authoritative for the whole directory. Pins the post-CA1 (2026-05-16)
    collision-safe behaviour: `_project_dir_for_cwd` must scan past a
    non-matching first JSONL to find a matching later one in the same dir.
    """
    import json

    collision_dir = tmp_path / "-home-x-y-z"
    collision_dir.mkdir()

    cwd_one = "/home/x/y-z"
    cwd_two = "/home/x-y/z"

    # Lexicographically first JSONL: declares cwd_one (non-matching for our query).
    entry_one = {
        "type": "user",
        "cwd": cwd_one,
        "timestamp": "2026-05-16T00:00:00.000Z",
        "message": {"content": []},
    }
    (collision_dir / f"{_UUID_A}.jsonl").write_text(json.dumps(entry_one) + "\n")

    # Lexicographically second JSONL: declares cwd_two (the target).
    entry_two = {
        "type": "user",
        "cwd": cwd_two,
        "timestamp": "2026-05-16T00:00:00.000Z",
        "message": {"content": []},
    }
    (collision_dir / f"{_UUID_B}.jsonl").write_text(json.dumps(entry_two) + "\n")

    # cwd_two is reachable even though cwd_one's JSONL sorts first.
    assert _project_dir_for_cwd(tmp_path, cwd_two) == collision_dir
    # And cwd_one is still reachable on its own (sanity check — first-match wins).
    assert _project_dir_for_cwd(tmp_path, cwd_one) == collision_dir


# ---------------------------------------------------------------------------
# correlate — argv direct match
# ---------------------------------------------------------------------------


def test_correlate_direct_match_via_argv_resume(tmp_path: Path) -> None:
    """argv carries --resume <uuid> AND that <uuid>.jsonl exists → DIRECT_MATCH."""
    make_project_dir(tmp_path, cwd="/home/user/proj", uuids=[_UUID_A])
    liveness = _make_liveness(
        cwd="/home/user/proj",
        started=1_715_000_000,
        argv=f"--resume {_UUID_A}",
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.DIRECT_MATCH
    assert result.uuid == _UUID_A


# ---------------------------------------------------------------------------
# correlate — mtime-window
# ---------------------------------------------------------------------------


def test_correlate_single_mtime_match(tmp_path: Path) -> None:
    """No --resume; one JSONL in window (mtime + first-entry ts both ≥ started)."""
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A],
        first_entry_ts=started + 10,
    )
    # Force mtime to be after started (make_project_dir writes "now"; we be
    # explicit so the assertion doesn't depend on test-run timing).
    jsonl = project / f"{_UUID_A}.jsonl"
    os.utime(jsonl, (started + 10, started + 10))

    liveness = _make_liveness(cwd="/home/user/proj", started=started)
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_A


def test_correlate_multiple_mtime_candidates_is_ambiguous(tmp_path: Path) -> None:
    """Two JSONLs both inside the mtime window → AMBIGUOUS with both UUIDs."""
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A, _UUID_B],
        first_entry_ts=started + 10,
    )
    for uuid in (_UUID_A, _UUID_B):
        path = project / f"{uuid}.jsonl"
        os.utime(path, (started + 10, started + 10))

    liveness = _make_liveness(cwd="/home/user/proj", started=started)
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.AMBIGUOUS
    assert len(result.candidates) == 2
    assert set(result.candidates) == {_UUID_A, _UUID_B}


def test_correlate_zero_candidates_is_no_match(tmp_path: Path) -> None:
    """One JSONL but its mtime is BEFORE liveness.started → NO_MATCH."""
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A],
        first_entry_ts=started - 3600,  # entry is hour-old
    )
    jsonl = project / f"{_UUID_A}.jsonl"
    # Pre-started mtime so the JSONL falls out of the window.
    os.utime(jsonl, (started - 3600, started - 3600))

    liveness = _make_liveness(cwd="/home/user/proj", started=started)
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.NO_MATCH
    assert result.uuid is None
    assert result.candidates == ()


def test_correlate_no_project_dir_is_no_match(tmp_path: Path) -> None:
    """Empty projects_root → no directory matches liveness.cwd → NO_MATCH."""
    liveness = _make_liveness(cwd="/home/user/proj", started=1_715_000_000)
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.NO_MATCH
    assert result.uuid is None


# ---------------------------------------------------------------------------
# correlate — argv UUID fall-through
# ---------------------------------------------------------------------------


def test_correlate_argv_uuid_but_jsonl_missing_falls_back_to_mtime(
    tmp_path: Path,
) -> None:
    """argv claims --resume <X> but X.jsonl is gone; another JSONL is in window.

    The plan's correlate() comment is normative: "argv claimed a UUID but the
    JSONL is gone — fall through to mtime so we still report something
    useful." This test pins that fall-through semantics — without it the
    function would silently swallow the argv hint and still scan, but a
    future refactor might "fix" the fall-through to NO_MATCH and silently
    regress the useful-fallback property.
    """
    started = 1_715_000_000
    # Project dir exists with UUID_B's JSONL, NOT UUID_A's.
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_B],
        first_entry_ts=started + 10,
    )
    jsonl = project / f"{_UUID_B}.jsonl"
    os.utime(jsonl, (started + 10, started + 10))

    liveness = _make_liveness(
        cwd="/home/user/proj",
        started=started,
        argv=f"--resume {_UUID_A}",
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_B


def test_correlate_filters_out_jsonl_with_old_first_entry(tmp_path: Path) -> None:
    """JSONL with recent mtime but old first-entry ts → excluded → NO_MATCH.

    Guards against false positives: the same cwd may have had a long-running
    session before the wrapper started. Filesystem mtime can be touched by
    auxiliary writes (compaction, sidecar updates), so the first-entry
    timestamp is the authoritative session-start signal.
    """
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A],
        first_entry_ts=started - 86400,  # entry is a day old
    )
    jsonl = project / f"{_UUID_A}.jsonl"
    # Touch mtime so it APPEARS recent (passes the first filter)…
    os.utime(jsonl, (started + 100, started + 100))

    liveness = _make_liveness(cwd="/home/user/proj", started=started)
    result = correlate(liveness, tmp_path)
    # …but the first-entry-ts check excludes it.
    assert result.kind == CorrelationKind.NO_MATCH


def test_correlate_argv_uuid_but_no_project_dir_is_no_match(tmp_path: Path) -> None:
    """argv carries --resume <uuid> AND the cwd has no project dir → NO_MATCH.

    Pins the conservative argv-without-project-dir decision (coherence
    review M4, 2026-05-16): when ``_project_dir_for_cwd`` returns ``None``
    the wrapper's UUID hint is dropped rather than surfaced. The UUID could
    refer to a JSONL anywhere on disk and we cannot disk-verify it without
    a project directory; misattribution would poison downstream
    classification. Conservative is the right call.
    """
    # tmp_path has no project dirs at all.
    liveness = _make_liveness(
        cwd="/home/user/never-existed",
        started=1_715_000_000,
        argv=f"--resume {_UUID_A}",
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.NO_MATCH
    assert result.uuid is None  # wrapper hint discarded


# ---------------------------------------------------------------------------
# _extract_resume_uuid
# ---------------------------------------------------------------------------


def test_extract_resume_uuid_returns_none_for_malformed_shlex() -> None:
    """argv with unbalanced quotes triggers shlex.split ValueError → None.

    ``_extract_resume_uuid`` catches ``ValueError`` from ``shlex.split`` and
    returns ``None`` rather than propagating. Coherence review L2
    (2026-05-16): the malformed-shell-string branch was untested.
    """
    # Single unterminated double-quote — shlex.split raises ValueError.
    assert _extract_resume_uuid('--resume "unterminated') is None
    # Single unterminated single-quote — same.
    assert _extract_resume_uuid("--resume 'also-unterminated") is None


# ---------------------------------------------------------------------------
# CorrelationResult invariants
# ---------------------------------------------------------------------------


def test_correlation_result_default_uuid_and_candidates() -> None:
    """A bare NO_MATCH result has uuid=None and empty candidates tuple."""
    result = CorrelationResult(kind=CorrelationKind.NO_MATCH)
    assert result.uuid is None
    assert result.candidates == ()
