"""Tests for crash_recovery.liveness — parser, boot-id, pid-alive, enumeration.

Covers parser-side of AC5.1 (four required keys), AC5.4 (per-PID enumeration),
AC5.6 (boot-id readable for downstream comparison). The CA2 (2026-05-16) pin
tests on ``pid_alive`` document the load-bearing contract that the function
always returns a ``bool``, never ``None`` — propagation of ``OSError`` from
``os.kill(pid, 0)`` would crash Phase 4's scan via Phase 2's boundary check
in ``classify()`` (which raises ``ValueError`` when ``liveness_state.present``
is True paired with ``pid_alive=None``).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from crash_recovery.liveness import (
    Liveness,
    _proc_start_time,
    assert_local_filesystem,
    current_boot_id,
    list_liveness_files,
    pid_alive,
    pid_alive_checked,
    read_liveness,
)

# pytest injects tests/ onto sys.path when tests/__init__.py is absent (a
# deliberate Phase 1 decision for workspace-wide collection), so the
# fixtures package is addressable as top-level "fixtures", not "tests.fixtures".
from fixtures.jsonl_builder import _pick_dead_pid, make_liveness_file

# ---------------------------------------------------------------------------
# read_liveness
# ---------------------------------------------------------------------------


def test_read_liveness_parses_four_keys(tmp_path: Path) -> None:
    """Well-formed file — all four required fields surface verbatim. (AC5.1)"""
    path = make_liveness_file(
        tmp_path,
        pid=4242,
        cwd="/home/user/proj",
        started=1715151234,
        argv="--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b",
        boot_id="8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d",
    )
    liveness = read_liveness(path)
    assert isinstance(liveness, Liveness)
    assert liveness.path == path
    assert liveness.pid == 4242
    assert liveness.cwd == "/home/user/proj"
    assert liveness.started == 1715151234
    assert liveness.argv == "--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b"
    assert liveness.boot_id == "8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d"


def test_read_liveness_extracts_pid_from_filename(tmp_path: Path) -> None:
    """The pid field comes from the filename stem, not any in-file key."""
    path = make_liveness_file(tmp_path, pid=99999)
    assert read_liveness(path).pid == 99999


def test_read_liveness_rejects_non_numeric_filename(tmp_path: Path) -> None:
    """Filenames whose stem is not all-digit are not <pid>.live files."""
    bad = tmp_path / "wibble.live"
    bad.write_text(
        "cwd=/tmp\nstarted=1\nargv=\nboot_id=00000000-0000-0000-0000-000000000000\n"
    )
    with pytest.raises(ValueError, match=str(bad)):
        read_liveness(bad)


def test_read_liveness_missing_key_raises(tmp_path: Path) -> None:
    """Each of the four required keys must be present; first miss raises."""
    path = tmp_path / "12345.live"
    # boot_id deliberately omitted.
    path.write_text("cwd=/tmp\nstarted=1\nargv=\n")
    with pytest.raises(ValueError, match="boot_id"):
        read_liveness(path)


def test_read_liveness_ignores_extra_keys(tmp_path: Path) -> None:
    """Unknown keys are tolerated for forward-compatibility with Phase 8."""
    path = tmp_path / "12345.live"
    path.write_text(
        "cwd=/tmp\nstarted=1\nargv=\n"
        "boot_id=00000000-0000-0000-0000-000000000000\n"
        "future_key=foo\n"
    )
    liveness = read_liveness(path)
    assert liveness.cwd == "/tmp"


def test_read_liveness_handles_equals_in_argv(tmp_path: Path) -> None:
    """argv values can contain ``=`` signs; only the first ``=`` splits k/v."""
    argv = "--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b --extra=value=with=signs"
    path = make_liveness_file(tmp_path, pid=12345, argv=argv)
    assert read_liveness(path).argv == argv


def test_read_liveness_started_not_int_raises_value_error(tmp_path: Path) -> None:
    """started must coerce to int; non-int raises a wrapped ValueError."""
    path = tmp_path / "12345.live"
    path.write_text(
        "cwd=/tmp\nstarted=not-an-int\nargv=\n"
        "boot_id=00000000-0000-0000-0000-000000000000\n"
    )
    with pytest.raises(ValueError, match="started"):
        read_liveness(path)


def test_read_liveness_lowercases_boot_id(tmp_path: Path) -> None:
    """boot_id is normalised to lowercase for deterministic comparison."""
    path = tmp_path / "12345.live"
    path.write_text(
        "cwd=/tmp\nstarted=1\nargv=\nboot_id=8B2F4A3D-6C0E-4F1A-9D2B-7E3C5A8B1C4D\n"
    )
    assert read_liveness(path).boot_id == "8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d"


def test_read_liveness_parses_optional_session_id_and_start_time(
    tmp_path: Path,
) -> None:
    """A .live carrying session_id/start_time surfaces both on the dataclass.
    (AC4.2/AC4.4)"""
    path = make_liveness_file(
        tmp_path,
        pid=4242,
        session_id="db0cc58f-dc30-4195-a64a-4f25a5c19d6b",
        start_time=218236304,
    )
    liveness = read_liveness(path)
    assert liveness.session_id == "db0cc58f-dc30-4195-a64a-4f25a5c19d6b"
    assert liveness.start_time == 218236304


def test_read_liveness_legacy_file_has_none_optional_fields(tmp_path: Path) -> None:
    """A four-key legacy marker parses with session_id/start_time both None, no error.
    """
    path = make_liveness_file(tmp_path, pid=4242)
    liveness = read_liveness(path)
    assert liveness.session_id is None
    assert liveness.start_time is None


def test_read_liveness_start_time_non_int_is_tolerant_none(tmp_path: Path) -> None:
    """A non-integer start_time tolerantly yields None (must NOT raise —
    legacy/odd files)."""
    path = tmp_path / "12345.live"
    path.write_text(
        "cwd=/tmp\nstarted=1\nargv=\n"
        "boot_id=00000000-0000-0000-0000-000000000000\n"
        "start_time=not-an-int\n"
    )
    liveness = read_liveness(path)
    assert liveness.start_time is None


# ---------------------------------------------------------------------------
# current_boot_id
# ---------------------------------------------------------------------------


def test_current_boot_id_returns_kernel_value() -> None:
    """The returned value matches /proc/sys/kernel/random/boot_id verbatim.
    (AC5.6 read side)"""
    expected = Path("/proc/sys/kernel/random/boot_id").read_text().strip().lower()
    assert current_boot_id() == expected


def test_current_boot_id_lowercases_uppercase_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defensive normalisation: an uppercase kernel value is lowercased on return.

    The kernel writes the boot-id lowercase in practice, so the live-value
    test above can only confirm "happens to be lowercase". Patch the path
    read to return an uppercase synthetic UUID and confirm the function's
    own ``.lower()`` actually runs. Replaces a prior tautological assertion
    (``value == value.lower()`` is trivially true for any already-lowercase
    string). Coherence review L1 (2026-05-16).
    """
    upper_uuid = "8B2F4A3D-6C0E-4F1A-9D2B-7E3C5A8B1C4D"
    monkeypatch.setattr(Path, "read_text", lambda self, *_a, **_kw: upper_uuid + "\n")
    assert current_boot_id() == upper_uuid.lower()


# ---------------------------------------------------------------------------
# pid_alive
# ---------------------------------------------------------------------------


def test_pid_alive_self_is_true() -> None:
    """The current process is, by definition, alive."""
    assert pid_alive(os.getpid()) is True


def test_pid_alive_sentinel_is_false() -> None:
    """A PID far above any reasonable kernel pid_max is dead by construction."""
    assert pid_alive(2**30) is False


def test_pid_alive_permission_error_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins return-False + UserWarning emitted + non-propagation; symmetric with
    test_pid_alive_unexpected_oserror_returns_false_with_warning.

    CA2 (2026-05-16) falsification anchor. Without this contract a recycled
    PID would silently return ``None`` (or propagate) and Phase 2's
    ``classify()`` boundary check would raise ``ValueError`` on the next scan
    pass, crashing the whole scan rather than classifying one row as a
    casualty. The wrapper itself is gone; treat-as-dead is the conservative
    and correct choice. ``PermissionError`` is caught by the shared
    ``except OSError`` handler, so the warning fires just as it does for any
    other ``OSError`` subclass — both pin tests now assert it.
    """

    def _raise_perm(pid: int, sig: int) -> None:
        raise PermissionError("Operation not permitted")

    monkeypatch.setattr(os, "kill", _raise_perm)
    with pytest.warns(UserWarning) as record:
        result = pid_alive(12345)
    assert result is False
    assert len(record) == 1


def test_pid_alive_unexpected_oserror_returns_false_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-PermissionError OSError → log-and-return-False, never propagate.

    CA2 (2026-05-16) pin for the wider error contract: ``pid_alive`` swallows
    every ``OSError`` subclass with a single ``warnings.warn(UserWarning)``,
    so callers can rely on a real ``bool``. Pairs with the boundary check in
    ``classify()`` which raises if ``pid_alive=None`` arrives alongside a
    present liveness file.
    """

    def _raise_oserror(pid: int, sig: int) -> None:
        raise OSError("simulated platform failure")

    monkeypatch.setattr(os, "kill", _raise_oserror)
    with pytest.warns(UserWarning):
        assert pid_alive(12345) is False


# ---------------------------------------------------------------------------
# _proc_start_time / pid_alive_checked
# ---------------------------------------------------------------------------


def test_proc_start_time_self_is_int() -> None:
    """Reading the current process's start_time yields a positive int."""
    value = _proc_start_time(os.getpid())
    assert isinstance(value, int)
    assert value > 0


def test_proc_start_time_dead_pid_is_none() -> None:
    """A pid with no /proc/<pid>/stat returns None (OSError swallowed)."""
    assert _proc_start_time(_pick_dead_pid()) is None


def test_pid_alive_checked_matching_start_time_is_true() -> None:
    """Matching stored start_time against /proc → alive. (AC4.2)"""
    pid = os.getpid()
    assert pid_alive_checked(pid, _proc_start_time(pid)) is True


def test_pid_alive_checked_mismatched_start_time_is_false() -> None:
    """A recycled-PID marker (wrong start_time) classifies dead. (AC4.2)"""
    pid = os.getpid()
    actual = _proc_start_time(pid)
    assert actual is not None
    assert pid_alive_checked(pid, actual + 1) is False


def test_pid_alive_checked_dead_pid_is_false_regardless_of_expected() -> None:
    """A dead pid is dead whether or not an expected start_time is supplied. (AC4.2)"""
    dead = _pick_dead_pid()
    assert pid_alive_checked(dead, 12345) is False
    assert pid_alive_checked(dead, None) is False


def test_pid_alive_checked_none_falls_back_to_bare_liveness() -> None:
    """expected=None → legacy back-compat: bare kill -0. (AC4.4)"""
    assert pid_alive_checked(os.getpid(), None) is True
    assert pid_alive_checked(_pick_dead_pid(), None) is False


# ---------------------------------------------------------------------------
# list_liveness_files
# ---------------------------------------------------------------------------


def test_list_liveness_files_tolerates_missing_directory(tmp_path: Path) -> None:
    """A non-existent run_dir yields nothing — never the wrapper's first boot."""
    missing = tmp_path / "does-not-exist"
    assert list(list_liveness_files(missing)) == []


def test_list_liveness_files_enumerates_distinct_pids(tmp_path: Path) -> None:
    """Three distinct .live files surface as three distinct Liveness records. (AC5.4)"""
    for pid in (100, 200, 300):
        make_liveness_file(tmp_path, pid=pid)
    yielded = list(list_liveness_files(tmp_path))
    assert sorted(rec.pid for rec in yielded) == [100, 200, 300]


def test_list_liveness_files_skips_malformed_with_warning(tmp_path: Path) -> None:
    """A malformed file is skipped with UserWarning; iteration continues."""
    make_liveness_file(tmp_path, pid=100)
    bad = tmp_path / "200.live"
    bad.write_text("cwd=/tmp\nstarted=1\nargv=\n")  # boot_id missing
    with pytest.warns(UserWarning):
        records = list(list_liveness_files(tmp_path))
    assert [rec.pid for rec in records] == [100]


# ---------------------------------------------------------------------------
# assert_local_filesystem
# ---------------------------------------------------------------------------


def test_assert_local_filesystem_accepts_tmp_path(tmp_path: Path) -> None:
    """Happy path — tmp_path is on tmpfs/ext4/btrfs/xfs/zfs; no exception."""
    assert_local_filesystem(tmp_path)  # must not raise


_REFUSED_FSTYPE_SAMPLES = [
    "nfs",
    "nfs4",
    "cifs",
    "smb3",
    "sshfs",
    "fuse.gvfsd",
    "fuse.sshfs",
]


@pytest.mark.parametrize("fstype", _REFUSED_FSTYPE_SAMPLES)
def test_assert_local_filesystem_refuses_simulated_nfs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fstype: str,
) -> None:
    """Each refused fstype raises RuntimeError naming the env-var escape hatch."""
    import crash_recovery.liveness as liveness_mod

    def _fake_detect(path: Path) -> str:
        return fstype

    monkeypatch.setattr(liveness_mod, "_detect_fstype", _fake_detect)
    with pytest.raises(RuntimeError) as excinfo:
        assert_local_filesystem(tmp_path)
    msg = str(excinfo.value)
    assert "CRASH_RECOVERY_RUN_DIR" in msg
    assert fstype in msg


def test_assert_local_filesystem_silent_when_fstype_undetectable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Undetectable fstype → allow rather than spuriously refuse."""
    import crash_recovery.liveness as liveness_mod

    def _fake_detect(path: Path) -> Any:
        return None

    monkeypatch.setattr(liveness_mod, "_detect_fstype", _fake_detect)
    assert_local_filesystem(tmp_path)  # must not raise
