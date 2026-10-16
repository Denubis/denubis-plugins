"""Observe native Claude registry records against isolated Linux process fixtures."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments" / "permission-queue" / "claude_state.py"
SPEC = importlib.util.spec_from_file_location("permission_claude_state", MODULE)
assert SPEC is not None and SPEC.loader is not None
STATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STATE
SPEC.loader.exec_module(STATE)


@pytest.fixture
def registry(tmp_path):
    class Registry:
        def __init__(self):
            self.home = tmp_path / "claude"
            self.sessions = self.home / "sessions"
            self.sessions.mkdir(parents=True)
            self.proc = tmp_path / "proc"
            (self.proc / "self/ns").mkdir(parents=True)
            (self.proc / "self/ns/pid").symlink_to("pid:[42]")
            self.machine_id = tmp_path / "machine-id"
            self.machine_id.write_text("fixture-machine\n")
            self.pane = SimpleNamespace(
                session_name="main",
                window_id="@64",
                pane_id="%86",
                foreground_pid=100,
                foreground_start_ticks=1234,
            )
            self.process(100, 1234)
            self.adapter = STATE.ClaudeState(
                self.home,
                proc_root=self.proc,
                machine_id_path=self.machine_id,
            )

        def process(self, pid, ticks, pgid=100):
            path = self.proc / str(pid)
            path.mkdir(exist_ok=True)
            fields = ["S", "1", str(pgid), "1", "34816", "100"] + ["0"] * 13
            fields.append(str(ticks))
            (path / "stat").write_text(f"{pid} (claude (native)) " + " ".join(fields))

        def write(self, file_pid=100, **changes):
            record = {
                "pid": file_pid,
                "sessionId": "f693c4b7-aaf8-4268-89a7-6ff8f27f9921",
                "cwd": "/fixture/project",
                "startedAt": 1_792_113_000_000,
                "procStart": "1234",
                "pidDomain": "linux:fixture-machine:pid:[42]",
                "version": "2.1.301",
                "kind": "interactive",
                "tmux": "main:@64.%86",
                "status": "idle",
                "updatedAt": 1_792_114_000_000,
                "statusUpdatedAt": 1_792_113_500_125,
            }
            record.update(changes)
            path = self.sessions / f"{file_pid}.json"
            path.write_text(json.dumps(record))
            return path

    return Registry()


def test_native_idle_timestamp_is_distinct_from_other_registry_updates(registry):
    path = registry.write()
    before = path.read_bytes()
    observed = registry.adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == "idle"
    assert observed.state_since == 1_792_113_500.125
    assert observed.session_id == "f693c4b7-aaf8-4268-89a7-6ff8f27f9921"
    assert observed.state_since_source
    assert observed.approximate is True
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("native", "waiting_for", "expected"),
    [
        ("busy", None, "running"),
        ("shell", None, "running"),
        ("waiting", "permission prompt", "blocked"),
        ("waiting", "input needed", "blocked"),
        ("waiting", "dialog open", "blocked"),
        ("waiting", "sandbox request", "blocked"),
        ("waiting", "worker request", "blocked"),
        ("waiting", "goal proposal", "blocked"),
        ("waiting", "unrecognized future reason", "unknown"),
        ("waiting", None, "unknown"),
        ("future status", None, "unknown"),
    ],
)
def test_native_states_only_mark_verified_human_waits_blocked(
    registry, native, waiting_for, expected
):
    registry.write(status=native, waitingFor=waiting_for)
    observed = registry.adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == expected
    assert observed.status_detail
    if expected == "unknown":
        assert observed.state_since is None


def test_native_child_in_same_foreground_group_is_resolved(registry):
    registry.process(101, 2345)
    registry.write(101, procStart="2345", status="busy")
    observed = registry.adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == "running"


@pytest.mark.parametrize(
    "changes",
    [
        {"procStart": "9999"},
        {"procStart": None},
        {"pid": 99},
        {"pidDomain": "linux:other-machine:pid:[42]"},
        {"pidDomain": "linux:fixture-machine:pid:[99]"},
        {"pidDomain": None},
        {"kind": "bg"},
        {"tmux": "main:@64.%85"},
        {"tmux": "main:@99.%86"},
        {"tmux": "elsewhere:@64.%86"},
        {"sessionId": None},
    ],
)
def test_stale_or_different_native_identity_is_not_attached(registry, changes):
    registry.write()
    assert registry.adapter.for_pane(registry.pane) is not None
    registry.write(**changes)
    assert registry.adapter.for_pane(registry.pane) is None


def test_matching_locator_in_different_process_group_is_not_attached(registry):
    registry.process(101, 2345, pgid=999)
    registry.write(101, procStart="2345")
    assert registry.adapter.for_pane(registry.pane) is None


def test_two_interactive_owners_are_ambiguous(registry):
    registry.write()
    assert registry.adapter.for_pane(registry.pane) is not None
    registry.process(101, 2345)
    registry.write(101, procStart="2345")
    assert registry.adapter.for_pane(registry.pane) is None


def test_reused_foreground_group_cannot_receive_old_state(registry):
    registry.write()
    assert registry.adapter.for_pane(registry.pane) is not None
    registry.process(100, 3456)
    assert registry.adapter.for_pane(registry.pane) is None


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        -1,
        True,
        "1792113500125",
        float("nan"),
        float("inf"),
        4_000_000_000_000_000,
        1_000,
    ],
)
def test_missing_or_invalid_state_time_does_not_invent_age(registry, timestamp):
    registry.write(statusUpdatedAt=timestamp)
    observed = registry.adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == "idle"
    assert observed.state_since is None
    assert observed.state_since_source == ""


def test_partial_native_write_is_unavailable_then_next_read_recovers(registry):
    path = registry.write()
    path.write_text('{"pid":')
    assert registry.adapter.for_pane(registry.pane) is None
    registry.write(status="busy")
    observed = registry.adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == "running"


@pytest.mark.parametrize("native", [[], {}, 123, None])
def test_malformed_status_remains_unknown_without_crashing(registry, native):
    registry.write(status=native)
    observed = registry.adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == "unknown"
    assert observed.state_since is None


def test_configured_claude_directory_is_used_without_settings_changes(
    registry, monkeypatch
):
    registry.write(status="busy")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(registry.home))
    adapter = STATE.ClaudeState(
        proc_root=registry.proc, machine_id_path=registry.machine_id
    )
    observed = adapter.for_pane(registry.pane)
    assert observed is not None
    assert observed.state == "running"


def test_real_process_identity_expires_after_fixture_process_exits(tmp_path):
    """Use a harmless kernel process, not a Claude or model launch."""
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    with subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.read()"],
        stdin=subprocess.PIPE,
        start_new_session=True,
    ) as process:
        stat = Path(f"/proc/{process.pid}/stat").read_text().rsplit(")", 1)[1].split()
        machine = Path("/etc/machine-id").read_text().strip()
        domain = f"linux:{machine}:{Path('/proc/self/ns/pid').readlink()}"
        pane = SimpleNamespace(
            session_name="fixture",
            window_id="@1",
            pane_id="%1",
            foreground_pid=process.pid,
            foreground_start_ticks=int(stat[19]),
        )
        (sessions / f"{process.pid}.json").write_text(
            json.dumps(
                {
                    "pid": process.pid,
                    "procStart": stat[19],
                    "pidDomain": domain,
                    "sessionId": "fixture-session",
                    "kind": "interactive",
                    "tmux": "fixture:@1.%1",
                    "status": "idle",
                    "startedAt": 1_792_113_000_000,
                    "statusUpdatedAt": 1_792_113_500_125,
                }
            )
        )
        adapter = STATE.ClaudeState(tmp_path)
        observed = adapter.for_pane(pane)
        assert observed is not None
        assert observed.state == "idle"
        process.communicate(timeout=5)
        assert adapter.for_pane(pane) is None
