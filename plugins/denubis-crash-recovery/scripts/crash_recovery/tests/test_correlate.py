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
    argv: str | None = None,
    pid: int = 1234,
    session_id: str | None = None,
) -> Liveness:
    """Construct a Liveness directly (no on-disk file) — correlate doesn't read it."""
    return Liveness(
        path=Path(f"/tmp/{pid}.live"),
        pid=pid,
        cwd=cwd,
        started=started,
        argv=argv,
        boot_id=_BOOT,
        session_id=session_id,
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
# correlate — exact session_id direct match (Phase 2, AC4.3 / AC4.4)
# ---------------------------------------------------------------------------


def test_correlate_direct_match_via_session_id_without_resume(tmp_path: Path) -> None:
    """AC4.3: session_id set + <uuid>.jsonl present, argv lacks --resume → DIRECT_MATCH.

    The mtime window would *also* admit this JSONL (in-window first_entry_ts and
    mtime), so without the session_id branch the pre-impl baseline is
    MTIME_MATCH. Asserting ``kind == DIRECT_MATCH`` is therefore load-bearing:
    asserting only ``uuid`` would false-green via the mtime path. This proves
    the session_id stamp drives a *direct* (highest-confidence) match, not
    merely that some match happens.

    The marker carries an UPPERCASE session_id while the on-disk JSONL is the
    lowercase ``<uuid>.jsonl`` Claude Code writes. This pins the load-bearing
    ``.lower()`` normalisation (mirroring ``_extract_resume_uuid``) on both the
    path-match side and the returned ``uuid``: drop the ``.lower()`` and this
    test goes red (the uppercase path would not find the lowercase file).
    """
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A],  # lowercase on disk, as Claude Code writes it
        first_entry_ts=started + 10,
    )
    # Make the JSONL deterministically in-window so the no-session_id baseline
    # is MTIME_MATCH (mirrors test_correlate_single_mtime_match).
    jsonl = project / f"{_UUID_A}.jsonl"
    os.utime(jsonl, (started + 10, started + 10))

    liveness = _make_liveness(
        cwd="/home/user/proj",
        started=started,
        argv="",  # no --resume
        session_id=_UUID_A.upper(),  # marker may stamp upper; impl lowercases
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.DIRECT_MATCH
    assert result.uuid == _UUID_A  # returned lowercased to match on-disk name


def test_correlate_session_id_beats_resume_uuid(tmp_path: Path) -> None:
    """Precedence: session_id=A AND --resume B (both JSONLs present) → A wins.

    The Phase-1 lesson made concrete: prove session_id takes *precedence* over
    the --resume hint, not merely that "a match happens". Both A.jsonl and
    B.jsonl exist in the project dir; the result must be DIRECT_MATCH on A
    (session_id), NOT B (--resume). ``kind`` is DIRECT_MATCH on both the
    session_id path and the resume path, so the discriminating assertion is
    ``uuid == _UUID_A`` — the resume branch would have returned _UUID_B.
    """
    started = 1_715_000_000
    make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A, _UUID_B],
        first_entry_ts=started + 10,
    )
    liveness = _make_liveness(
        cwd="/home/user/proj",
        started=started,
        argv=f"--resume {_UUID_B}",
        session_id=_UUID_A,
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.DIRECT_MATCH
    assert result.uuid == _UUID_A  # session_id wins, not the --resume uuid


def test_correlate_session_id_missing_jsonl_falls_through_to_mtime(
    tmp_path: Path,
) -> None:
    """AC4.4: session_id set but <uuid>.jsonl absent → fall through, no false match.

    session_id=A, but A.jsonl does NOT exist; B.jsonl exists and sits inside the
    mtime window. The result must be MTIME_MATCH(B) — the existing mtime path
    decides. Asserting MTIME_MATCH(B) (not a bare NO_MATCH) catches an
    implementation that dropped the ``.exists()`` guard and would wrongly return
    a fabricated DIRECT_MATCH(A) on the missing UUID.
    """
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_B],  # only B; A.jsonl is absent
        first_entry_ts=started + 10,
    )
    jsonl = project / f"{_UUID_B}.jsonl"
    os.utime(jsonl, (started + 10, started + 10))

    liveness = _make_liveness(
        cwd="/home/user/proj",
        started=started,
        argv="",  # no --resume either
        session_id=_UUID_A,  # JSONL for A does not exist
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_B  # NOT a fabricated DIRECT_MATCH on _UUID_A


def test_correlate_legacy_session_id_none_unchanged(tmp_path: Path) -> None:
    """AC4.4 (legacy): session_id=None → mtime path decides exactly as before.

    A legacy marker (no session_id) with one in-window JSONL must still produce
    MTIME_MATCH via the unchanged fallback — the session_id branch is inert when
    session_id is None.
    """
    started = 1_715_000_000
    project = make_project_dir(
        tmp_path,
        cwd="/home/user/proj",
        uuids=[_UUID_A],
        first_entry_ts=started + 10,
    )
    jsonl = project / f"{_UUID_A}.jsonl"
    os.utime(jsonl, (started + 10, started + 10))

    liveness = _make_liveness(
        cwd="/home/user/proj",
        started=started,
        session_id=None,  # legacy marker
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_A


def test_correlate_session_id_but_no_project_dir_is_no_match(tmp_path: Path) -> None:
    """Edge: session_id set but liveness.cwd has no project dir → NO_MATCH.

    Guards the ``project_dir is not None`` clause: the M4 conservative drop is
    preserved. A.jsonl exists under a *different* cwd's project dir, but the
    liveness cwd locates no project dir at all. correlate must NOT fish for the
    session_id's JSONL outside the located project dir — it returns NO_MATCH and
    discards the unverified session_id hint.
    """
    # A.jsonl exists, but only under a DIFFERENT cwd's project dir.
    make_project_dir(tmp_path, cwd="/home/user/elsewhere", uuids=[_UUID_A])

    liveness = _make_liveness(
        cwd="/home/user/never-existed",  # locates no project dir
        started=1_715_000_000,
        session_id=_UUID_A,  # a JSONL for A exists, but not in our cwd's dir
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.NO_MATCH
    assert result.uuid is None  # session_id hint discarded (M4 conservative)


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


# ---------------------------------------------------------------------------
# AC2.2 — forward-scan cwd/timestamp repair in correlate
# ---------------------------------------------------------------------------


def test_project_dir_for_cwd_finds_match_when_cwd_on_later_line(
    tmp_path: Path,
) -> None:
    """AC2.2 (project-dir lookup): snapshot-prefixed JSONL (cwd on line 2) is found.

    Before the fix, ``_cwd_matches_any_jsonl_in`` read only line 1 and saw the
    snapshot record which carries no ``cwd``, so ``_project_dir_for_cwd``
    returned ``None``. After the fix, the forward scan finds the cwd on line 2.
    """
    import json as _json

    from fixtures.jsonl_builder import _snapshot_record

    cwd = "/home/user/snapshot-prefixed-project"
    project_dir = tmp_path / "-snapshot-prefixed-dir"
    project_dir.mkdir()

    # Write a snapshot-prefixed JSONL: line 1 = snapshot record (no cwd),
    # line 2 = real entry with cwd.
    jsonl_path = project_dir / f"{_UUID_A}.jsonl"
    snapshot = _snapshot_record()
    real_entry = {
        "type": "user",
        "cwd": cwd,
        "timestamp": "2026-06-12T00:00:00.000Z",
        "message": {"content": []},
    }
    jsonl_path.write_text(_json.dumps(snapshot) + "\n" + _json.dumps(real_entry) + "\n")

    result = _project_dir_for_cwd(tmp_path, cwd)
    assert result == project_dir, (
        f"Expected project_dir to be found when cwd is on line 2, got {result!r}. "
        "The forward scan must look past the snapshot record on line 1."
    )


def test_correlate_direct_match_when_cwd_on_later_line(tmp_path: Path) -> None:
    """AC2.2 (correlation end-to-end DIRECT_MATCH): snapshot-prefixed JSONL correlates.

    A liveness file with ``--resume <uuid>`` and a matching JSONL whose cwd
    is on line 2 (snapshot-prefixed) must produce DIRECT_MATCH. Before the fix
    ``_project_dir_for_cwd`` returned ``None`` (cwd not found on line 1) and
    the result was NO_MATCH.
    """
    import json as _json
    import time as _time

    from fixtures.jsonl_builder import _snapshot_record

    cwd = "/home/user/direct-match-snapshot"
    started = int(_time.time()) - 3600

    # Build snapshot-prefixed JSONL under a project dir.
    project_dir = tmp_path / "-direct-match-snapshot-dir"
    project_dir.mkdir()
    jsonl_path = project_dir / f"{_UUID_A}.jsonl"
    iso_ts = "2026-06-12T01:00:00.000Z"
    snapshot = _snapshot_record()
    real_entry = {
        "type": "user",
        "cwd": cwd,
        "timestamp": iso_ts,
        "message": {"content": []},
    }
    jsonl_path.write_text(_json.dumps(snapshot) + "\n" + _json.dumps(real_entry) + "\n")

    liveness = _make_liveness(
        cwd=cwd,
        started=started,
        argv=f"--resume {_UUID_A}",
    )
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.DIRECT_MATCH, (
        f"Expected DIRECT_MATCH for snapshot-prefixed JSONL, got {result.kind}. "
        "correlate must find the cwd via forward scan, not line-1-only read."
    )
    assert result.uuid == _UUID_A


def test_correlate_mtime_match_when_timestamp_on_later_line(tmp_path: Path) -> None:
    """AC2.2 (correlation end-to-end MTIME_MATCH): snapshot-prefixed timestamp is read.

    A fresh-style liveness file (no ``--resume``) with a single in-window JSONL
    whose timestamp is on line 2 must produce MTIME_MATCH. Before the fix,
    ``_jsonl_first_entry_ts_in_tight_window`` read only line 1 (snapshot record,
    no timestamp), returned ``False``, and the result was NO_MATCH.
    """
    import json as _json
    import time as _time

    from fixtures.jsonl_builder import _snapshot_record

    cwd = "/home/user/mtime-match-snapshot"
    started = int(_time.time()) - 3600
    # Timestamp just after liveness.started (well within the grace window).
    entry_epoch = started + 10
    from datetime import UTC, datetime

    iso_ts = datetime.fromtimestamp(entry_epoch, tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    # Build snapshot-prefixed JSONL: snapshot on line 1, real entry with
    # cwd + timestamp on line 2.
    project_dir = tmp_path / "-mtime-match-snapshot-dir"
    project_dir.mkdir()
    jsonl_path = project_dir / f"{_UUID_A}.jsonl"
    snapshot = _snapshot_record()
    real_entry = {
        "type": "user",
        "cwd": cwd,
        "timestamp": iso_ts,
        "message": {"content": []},
    }
    jsonl_path.write_text(_json.dumps(snapshot) + "\n" + _json.dumps(real_entry) + "\n")
    # Set mtime to also be in the window.
    os.utime(jsonl_path, (entry_epoch, entry_epoch))

    liveness = _make_liveness(cwd=cwd, started=started, argv="")  # no --resume
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.MTIME_MATCH, (
        f"Expected MTIME_MATCH for snapshot-prefixed JSONL, got {result.kind}. "
        "correlate must read timestamp via forward scan, not line-1-only read."
    )
    assert result.uuid == _UUID_A


# ---------------------------------------------------------------------------
# AC6.1 — tight window upper bound
# ---------------------------------------------------------------------------


def _write_jsonl_with_cwd_and_ts(
    project_dir: Path, uuid: str, cwd: str, first_entry_ts: int
) -> Path:
    """Write a single-entry JSONL under ``project_dir`` and set its mtime in-window.

    The entry carries ``cwd`` and an ISO-8601 ``timestamp`` derived from
    ``first_entry_ts``. mtime is forced to ``first_entry_ts`` so the candidate
    deterministically passes the mtime ≥ started lower bound regardless of when
    the test runs; whether it survives the *tight* upper bound is governed
    solely by ``first_entry_ts`` relative to ``started``.
    """
    import json as _json
    from datetime import UTC, datetime

    iso_ts = datetime.fromtimestamp(first_entry_ts, tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    entry = {
        "type": "user",
        "cwd": cwd,
        "timestamp": iso_ts,
        "message": {"content": []},
    }
    jsonl = project_dir / f"{uuid}.jsonl"
    jsonl.write_text(_json.dumps(entry) + "\n")
    return jsonl


def test_correlate_tight_window_excludes_far_candidate(tmp_path: Path) -> None:
    """AC6.1: of two same-cwd JSONLs, only the one within the tight window survives.

    Both JSONLs have mtime ≥ started (so both pass the original lower-bound-only
    filter, which would report AMBIGUOUS — that is the RED state). The near one's
    first-entry ts is +10s from ``started``; the far one's is +9999s, well past
    ``_TIGHT_WINDOW_SECONDS``. The tight upper bound must drop the far one,
    leaving exactly one candidate → MTIME_MATCH on the near one.
    """
    started = 1_715_000_000
    project = make_project_dir(tmp_path, cwd="/home/user/proj", uuids=[])
    near = _write_jsonl_with_cwd_and_ts(
        project, _UUID_A, "/home/user/proj", started + 10
    )
    far = _write_jsonl_with_cwd_and_ts(
        project, _UUID_B, "/home/user/proj", started + 9999
    )
    # Both mtimes ≥ started so both clear the lower bound.
    os.utime(near, (started + 10, started + 10))
    os.utime(far, (started + 9999, started + 9999))

    liveness = _make_liveness(cwd="/home/user/proj", started=started)
    result = correlate(liveness, tmp_path)
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_A  # the far candidate is excluded by the tight window


# ---------------------------------------------------------------------------
# AC6.2 / AC6.3 — resurrect corroboration of multi-candidate sets
# ---------------------------------------------------------------------------


def _make_collision_dir_with_two_cwds(
    tmp_path: Path, started: int
) -> tuple[Path, str, str]:
    """Build one lossy-encoded dir holding two in-tight-window JSONLs, distinct cwds.

    Mirrors ``test_project_dir_for_cwd_handles_encoding_collision``: ``/`` and
    ``.`` both collapse to ``-`` so two distinct cwds can share one encoded
    directory. _UUID_A declares ``cwd_a``; _UUID_B declares ``cwd_b``. Both are
    within the tight window (ts = started + 10) and have in-window mtimes, so
    both are candidates. ``liveness.cwd`` is set to ``cwd_a`` by callers, but
    correlate finds this collision dir via cwd_a and then scans every JSONL —
    so cwd_b's JSONL is also a candidate even though it declares a different cwd.

    Returns ``(collision_dir, cwd_a, cwd_b)``.
    """
    cwd_a = "/home/x/y-z"  # collapses to -home-x-y-z
    cwd_b = "/home/x-y/z"  # collapses to -home-x-y-z too
    collision_dir = tmp_path / "-home-x-y-z"
    collision_dir.mkdir()
    a = _write_jsonl_with_cwd_and_ts(collision_dir, _UUID_A, cwd_a, started + 10)
    b = _write_jsonl_with_cwd_and_ts(collision_dir, _UUID_B, cwd_b, started + 10)
    os.utime(a, (started + 10, started + 10))
    os.utime(b, (started + 10, started + 10))
    return collision_dir, cwd_a, cwd_b


def test_correlate_corroboration_resolves_multi_candidate(tmp_path: Path) -> None:
    """AC6.2: two in-window candidates, distinct cwds; corroborated_cwds={cwd_a} → A.

    Without corroboration this set is AMBIGUOUS (both _UUID_A and _UUID_B sit in
    the tight window). With ``corroborated_cwds`` naming only cwd_a, the filter —
    which reads each candidate's OWN first-entry cwd — keeps only _UUID_A (whose
    JSONL declares cwd_a) and drops _UUID_B (declares cwd_b). Exactly one
    survives → MTIME_MATCH on A.
    """
    started = 1_715_000_000
    _, cwd_a, _cwd_b = _make_collision_dir_with_two_cwds(tmp_path, started)

    liveness = _make_liveness(cwd=cwd_a, started=started)
    result = correlate(liveness, tmp_path, corroborated_cwds=frozenset({cwd_a}))
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_A


def test_correlate_corroboration_matching_both_stays_ambiguous(tmp_path: Path) -> None:
    """AC6.3: corroborated_cwds covers BOTH candidate cwds → AMBIGUOUS, all listed.

    When more than one candidate survives the corroboration filter, the verdict
    is AMBIGUOUS and the reported candidates are the FULL tight-window set
    (all-means-all), not the filtered subset.
    """
    started = 1_715_000_000
    _, cwd_a, cwd_b = _make_collision_dir_with_two_cwds(tmp_path, started)

    liveness = _make_liveness(cwd=cwd_a, started=started)
    result = correlate(liveness, tmp_path, corroborated_cwds=frozenset({cwd_a, cwd_b}))
    assert result.kind == CorrelationKind.AMBIGUOUS
    assert set(result.candidates) == {_UUID_A, _UUID_B}


def test_correlate_corroboration_empty_stays_ambiguous_with_all(tmp_path: Path) -> None:
    """AC6.3: empty corroborated_cwds → no survivor → AMBIGUOUS with full set.

    An empty frozenset (the no-snapshot-near case Task 3 passes) filters every
    candidate out (0 survivors). The verdict must be AMBIGUOUS carrying the full
    tight-window candidate tuple — never silently NO_MATCH, never the empty
    survivor subset.
    """
    started = 1_715_000_000
    _, cwd_a, _cwd_b = _make_collision_dir_with_two_cwds(tmp_path, started)

    liveness = _make_liveness(cwd=cwd_a, started=started)
    result = correlate(liveness, tmp_path, corroborated_cwds=frozenset())
    assert result.kind == CorrelationKind.AMBIGUOUS
    assert set(result.candidates) == {_UUID_A, _UUID_B}


def test_correlate_corroboration_none_is_tight_window_only(tmp_path: Path) -> None:
    """AC6.3: corroborated_cwds=None + two candidates → AMBIGUOUS (tight-window only).

    The default (no corroboration provided) must behave exactly as the
    tight-window-only path: two in-window candidates → AMBIGUOUS with both.
    """
    started = 1_715_000_000
    _, cwd_a, _cwd_b = _make_collision_dir_with_two_cwds(tmp_path, started)

    liveness = _make_liveness(cwd=cwd_a, started=started)
    result = correlate(liveness, tmp_path, corroborated_cwds=None)
    assert result.kind == CorrelationKind.AMBIGUOUS
    assert set(result.candidates) == {_UUID_A, _UUID_B}


def test_correlate_corroboration_single_candidate_unaffected(tmp_path: Path) -> None:
    """A single in-window candidate is MTIME_MATCH regardless of corroborated_cwds.

    Corroboration only kicks in for >1 candidate. With exactly one candidate the
    result is MTIME_MATCH even when corroborated_cwds is empty (it does not
    filter the lone survivor away).
    """
    started = 1_715_000_000
    project = make_project_dir(tmp_path, cwd="/home/user/solo", uuids=[])
    only = _write_jsonl_with_cwd_and_ts(
        project, _UUID_A, "/home/user/solo", started + 10
    )
    os.utime(only, (started + 10, started + 10))

    liveness = _make_liveness(cwd="/home/user/solo", started=started)
    result = correlate(liveness, tmp_path, corroborated_cwds=frozenset())
    assert result.kind == CorrelationKind.MTIME_MATCH
    assert result.uuid == _UUID_A
