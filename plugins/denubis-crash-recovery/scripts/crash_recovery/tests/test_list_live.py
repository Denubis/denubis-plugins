"""Tests for ``crash_recovery.list_live`` and the ``list-live`` subcommand.

Covers the diagnostic ``crash-recovery list-live`` surface (Phase 6 Task 6):
``survey_live`` filters dead PIDs out of the liveness-file enumeration and
marks ``boot_id_current`` based on the live kernel boot id. The CLI test
pair exercises the plain-text and ``--json`` rendering paths via subprocess
so CLI parsing, typer wiring, and JSON serialisation are all in scope.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from crash_recovery.list_live import LiveEntry, survey_live

# pytest injects tests/ onto sys.path when tests/__init__.py is absent (a
# deliberate Phase 1 decision for workspace-wide collection), so the
# fixtures package is addressable as top-level "fixtures", not "tests.fixtures".
from fixtures.jsonl_builder import make_liveness_file

# ---------------------------------------------------------------------------
# Module-level tests
# ---------------------------------------------------------------------------


def test_list_live_empty_run_dir_returns_empty_tuple(tmp_path: Path) -> None:
    """Non-existent ``run_dir`` → ``survey_live`` returns ``()``.

    Matches the legitimate pre-wrapper state where no liveness files have
    ever been written. ``list_liveness_files`` short-circuits on a missing
    directory; ``survey_live`` propagates that as an empty tuple rather than
    raising.
    """
    missing = tmp_path / "does-not-exist"
    result = survey_live(missing)
    assert result == ()


def test_list_live_filters_dead_pids(tmp_path: Path) -> None:
    """Dead PIDs are filtered out; only alive PIDs surface as ``LiveEntry``.

    Seeds two liveness files: one with the current test runner's PID (alive
    by construction) and one with ``2**30`` (almost certainly dead — well
    above ``/proc/sys/kernel/pid_max`` on every default-configured Linux).
    The result must contain exactly the alive entry.
    """
    alive_pid = os.getpid()
    dead_pid = 2**30
    make_liveness_file(tmp_path, pid=alive_pid)
    make_liveness_file(tmp_path, pid=dead_pid)

    result = survey_live(tmp_path)
    assert len(result) == 1
    (entry,) = result
    assert entry.pid == alive_pid


def test_list_live_marks_boot_id_mismatch(tmp_path: Path) -> None:
    """A liveness file with a non-current ``boot_id`` → ``boot_id_current=False``.

    Uses the all-zeros uuid for the file's ``boot_id``; the current kernel
    boot id is never all zeros, so the comparison must yield ``False``. The
    PID is ``os.getpid()`` so the dead-PID filter does not skip the row.
    """
    make_liveness_file(
        tmp_path,
        pid=os.getpid(),
        boot_id="00000000-0000-0000-0000-000000000000",
    )
    result = survey_live(tmp_path)
    assert len(result) == 1
    (entry,) = result
    assert isinstance(entry, LiveEntry)
    assert entry.boot_id_current is False


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


def _run_cli(*args: str, run_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python -m crash_recovery list-live <args>``.

    The test run directory is injected through the supported environment variable.
    """
    env = {**os.environ, "CRASH_RECOVERY_RUN_DIR": str(run_dir)}
    return subprocess.run(
        [sys.executable, "-m", "crash_recovery", "list-live", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_list_live_cli_plain_text(tmp_path: Path) -> None:
    """``list-live`` plain output contains the column headers and the alive PID.

    Seeds one alive liveness file under ``run_dir``, invokes the CLI without
    ``--json``, and pins that the column-header row is present plus the
    alive PID surfaces in stdout. The header row is the part most likely to
    drift across phases; pinning it keeps the user-facing diagnostic stable.
    """
    pid = os.getpid()
    make_liveness_file(tmp_path, pid=pid, cwd="/tmp/list-live-fixture")

    result = _run_cli(run_dir=tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "pid" in result.stdout
    assert "started" in result.stdout
    assert "boot_ok" in result.stdout
    assert "cwd" in result.stdout
    assert "argv" not in result.stdout
    assert str(pid) in result.stdout


def test_list_live_cli_json(tmp_path: Path) -> None:
    """``list-live --json`` emits a JSON array of objects with the documented fields.

    Seeds one alive liveness file under ``run_dir``, invokes the CLI with
    ``--json``, parses stdout as JSON, and asserts the resulting object is
    a list of one dict carrying the five documented fields with the values
    the fixture wrote. Pins both the schema (so downstream tools can rely on
    it) and the happy-path values.
    """
    pid = os.getpid()
    make_liveness_file(
        tmp_path,
        pid=pid,
        cwd="/tmp/list-live-json",
        started=1715151234,
        argv="--resume private-legacy-value",
    )

    result = _run_cli("--json", run_dir=tmp_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 1
    (entry,) = payload
    assert set(entry.keys()) == {"pid", "cwd", "started", "boot_id_current"}
    assert entry["pid"] == pid
    assert entry["cwd"] == "/tmp/list-live-json"
    assert entry["started"] == 1715151234
    assert "private-legacy-value" not in result.stdout
    assert isinstance(entry["boot_id_current"], bool)
