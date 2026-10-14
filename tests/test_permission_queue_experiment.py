"""Exercise the experiment through the operator CLI and hook stdin/stdout."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "permission-queue" / "queue.py"
PAYLOAD = {
    "session_id": "fixture-session",
    "cwd": "/fixture/worktree",
    "hook_event_name": "PermissionRequest",
    "tool_name": "Bash",
    "tool_input": {
        "command": "printf 'explicit experiment control\\n'",
        "description": "Observable harmless control",
    },
}


def invoke(
    run_dir: Path, command: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), command, "--run-dir", str(run_dir), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )


def requests(run_dir: Path) -> list[dict]:
    result = invoke(run_dir, "list", "--json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def wait_requests(run_dir: Path, count: int) -> list[dict]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        found = requests(run_dir)
        if len(found) == count:
            return found
        time.sleep(0.01)
    pytest.fail(f"held hook did not publish {count} request(s); last result: {found}")


@pytest.fixture
def hook_factory(tmp_path: Path):
    children: list[subprocess.Popen[str]] = []

    def launch(payload: dict | None = None, hold: float = 5, vendor: str = "claude"):
        child = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                "hook",
                "--run-dir",
                str(tmp_path),
                "--vendor",
                vendor,
                "--hold-seconds",
                str(hold),
            ],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert child.stdin is not None
        child.stdin.write(json.dumps(PAYLOAD if payload is None else payload))
        child.stdin.close()
        child.stdin = None
        children.append(child)
        return child

    yield launch
    for child in children:
        if child.poll() is None:
            child.terminate()
        child.communicate(timeout=5)


@pytest.mark.parametrize("vendor", ["claude", "codex"])
def test_explicit_request_answer_returns_typed_hook_output(
    tmp_path, hook_factory, vendor
):
    child = hook_factory(vendor=vendor)
    request = wait_requests(tmp_path, 1)[0]
    assert child.poll() is None, "hook must remain held until explicitly answered"
    assert request["tool_input"] == PAYLOAD["tool_input"]
    answer = invoke(
        tmp_path,
        "decide",
        "--request",
        request["request_id"],
        "--decision",
        "allow",
        "--reason",
        "Operator approved this occurrence",
    )
    assert answer.returncode == 0, answer.stderr
    stdout, stderr = child.communicate(timeout=3)
    assert child.returncode == 0, stderr
    assert json.loads(stdout) == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        }
    }
    assert requests(tmp_path)[0]["state"] == "returned"
    events = evidence(tmp_path)
    assert [event["event"] for event in events] == [
        "hook_opened",
        "decision_accepted",
        "hook_stdout_written",
    ]
    assert all(event["request_id"] == request["request_id"] for event in events)
    assert events[-1]["output"] == json.loads(stdout)


def evidence(run_dir: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_dir / "evidence.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]


def decide(run_dir: Path, request_id: str, choice: str = "allow"):
    return invoke(
        run_dir,
        "decide",
        "--request",
        request_id,
        "--decision",
        choice,
        "--reason",
        f"Explicit operator {choice} for this occurrence",
    )


def test_deny_returns_reason_without_standing_grant(tmp_path, hook_factory):
    child = hook_factory()
    request_id = wait_requests(tmp_path, 1)[0]["request_id"]
    result = decide(tmp_path, request_id, "deny")
    assert result.returncode == 0, result.stderr
    stdout, stderr = child.communicate(timeout=3)
    assert child.returncode == 0, stderr
    assert json.loads(stdout) == {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": "deny",
                "message": "Explicit operator deny for this occurrence",
            },
        }
    }


def test_timeout_emits_no_decision_and_remains_unanswerable(tmp_path, hook_factory):
    started = time.monotonic()
    child = hook_factory(hold=0.2)
    stdout, stderr = child.communicate(timeout=3)
    elapsed = time.monotonic() - started
    assert child.returncode == 0, stderr
    assert stdout == ""
    assert 0.1 <= elapsed < 2, f"bounded hold took {elapsed:.3f}s"
    request = requests(tmp_path)[0]
    assert request["state"] == "expired"
    refused = decide(tmp_path, request["request_id"])
    assert refused.returncode != 0
    assert "expired" in refused.stderr
    assert evidence(tmp_path)[-1]["event"] == "answer_refused"


def test_decision_checks_expiry_even_when_hook_cannot_advance(tmp_path, hook_factory):
    child = hook_factory(hold=0.3)
    request = wait_requests(tmp_path, 1)[0]
    # Do not freeze the hook while it owns the fixture state lock: that would
    # exercise lock contention instead of the decision CLI's expiry check.
    with (tmp_path / ".lock").open("a") as state_lock:
        fcntl.flock(state_lock, fcntl.LOCK_EX)
        os.kill(child.pid, signal.SIGSTOP)
        fcntl.flock(state_lock, fcntl.LOCK_UN)
    try:
        # This delay tests the elapsed-time contract, rather than guessing readiness.
        delay = max(0, request["expires_monotonic_s"] - time.monotonic() + 0.02)
        time.sleep(delay)
        assert child.poll() is None
        refused = decide(tmp_path, request["request_id"])
        assert refused.returncode != 0
        assert "expired" in refused.stderr
    finally:
        os.kill(child.pid, signal.SIGCONT)
    stdout, stderr = child.communicate(timeout=3)
    assert child.returncode == 0, stderr
    assert stdout == ""


def test_dead_hook_is_unknown_and_cannot_accept_answer(tmp_path, hook_factory):
    child = hook_factory()
    request = wait_requests(tmp_path, 1)[0]
    child.kill()
    child.communicate(timeout=3)
    refused = decide(tmp_path, request["request_id"])
    assert refused.returncode != 0
    assert "unknown" in refused.stderr
    record = requests(tmp_path)[0]
    assert record["state"] == "unknown"
    assert record["decision"] is None
    assert evidence(tmp_path)[-1]["event"] == "answer_refused"


def test_retired_occurrence_cannot_answer_next_identical_request(
    tmp_path, hook_factory
):
    first = hook_factory()
    request_a = wait_requests(tmp_path, 1)[0]
    retired = invoke(
        tmp_path,
        "retire",
        "--request",
        request_a["request_id"],
        "--reason",
        "Operator observed this occurrence answered at its pane",
    )
    assert retired.returncode == 0, retired.stderr
    stdout_a, stderr_a = first.communicate(timeout=3)
    assert first.returncode == 0, stderr_a
    assert stdout_a == ""
    second = hook_factory()
    both = wait_requests(tmp_path, 2)
    request_b = next(
        item for item in both if item["request_id"] != request_a["request_id"]
    )
    assert request_a["tool_input"] == request_b["tool_input"]
    stale = decide(tmp_path, request_a["request_id"])
    assert stale.returncode != 0
    assert "retired" in stale.stderr
    assert second.poll() is None
    answer = decide(tmp_path, request_b["request_id"])
    assert answer.returncode == 0, answer.stderr
    stdout_b, stderr_b = second.communicate(timeout=3)
    assert second.returncode == 0, stderr_b
    assert json.loads(stdout_b)["hookSpecificOutput"]["decision"]["behavior"] == "allow"
    states = {item["request_id"]: item["state"] for item in requests(tmp_path)}
    assert states == {
        request_a["request_id"]: "retired",
        request_b["request_id"]: "returned",
    }


def test_simultaneous_identical_requests_are_decided_separately(tmp_path, hook_factory):
    first = hook_factory()
    first_request = wait_requests(tmp_path, 1)[0]
    second = hook_factory()
    both = wait_requests(tmp_path, 2)
    second_request = next(
        item for item in both if item["request_id"] != first_request["request_id"]
    )
    assert first_request["tool_input"] == second_request["tool_input"]
    answer = decide(tmp_path, first_request["request_id"], "deny")
    assert answer.returncode == 0, answer.stderr
    first_stdout, _ = first.communicate(timeout=3)
    assert (
        json.loads(first_stdout)["hookSpecificOutput"]["decision"]["behavior"] == "deny"
    )
    assert second.poll() is None
    assert decide(tmp_path, second_request["request_id"]).returncode == 0
    second_stdout, _ = second.communicate(timeout=3)
    assert (
        json.loads(second_stdout)["hookSpecificOutput"]["decision"]["behavior"]
        == "allow"
    )


def test_two_competing_answers_accept_exactly_one_and_return_its_choice(
    tmp_path, hook_factory
):
    child = hook_factory()
    request_id = wait_requests(tmp_path, 1)[0]["request_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        choices = ["allow", "deny"]
        results = list(
            pool.map(lambda choice: decide(tmp_path, request_id, choice), choices)
        )
    winners = [
        choice
        for choice, result in zip(choices, results, strict=True)
        if result.returncode == 0
    ]
    assert len(winners) == 1, [(result.returncode, result.stderr) for result in results]
    stdout, stderr = child.communicate(timeout=3)
    assert child.returncode == 0, stderr
    assert (
        json.loads(stdout)["hookSpecificOutput"]["decision"]["behavior"] == winners[0]
    )
    events = [event["event"] for event in evidence(tmp_path)]
    assert events.count("decision_accepted") == 1
    assert events.count("answer_refused") == 1


def test_pane_denial_note_does_not_suppress_deliberate_late_allow_probe(
    tmp_path, hook_factory
):
    child = hook_factory()
    request_id = wait_requests(tmp_path, 1)[0]["request_id"]
    note = invoke(
        tmp_path,
        "note",
        "--request",
        request_id,
        "--event",
        "pane-denied",
        "--detail",
        "Fixture only: operator would now inspect the real vendor pane",
    )
    assert note.returncode == 0, note.stderr
    assert requests(tmp_path)[0]["state"] == "pending"
    assert decide(tmp_path, request_id).returncode == 0
    stdout, stderr = child.communicate(timeout=3)
    assert child.returncode == 0, stderr
    assert json.loads(stdout)["hookSpecificOutput"]["decision"]["behavior"] == "allow"
    assert [event["event"] for event in evidence(tmp_path)] == [
        "hook_opened",
        "pane-denied",
        "decision_accepted",
        "hook_stdout_written",
    ]


def test_full_input_is_visible_and_control_characters_are_escaped(
    tmp_path, hook_factory
):
    payload = {
        **PAYLOAD,
        "tool_input": {
            "command": "printf '" + "x" * 2000 + "'\n\x1b[2J\r\u202e",
            "description": "\x07description",
        },
    }
    child = hook_factory(payload)
    request_id = wait_requests(tmp_path, 1)[0]["request_id"]
    view = invoke(tmp_path, "list")
    assert view.returncode == 0, view.stderr
    assert json.dumps(payload["tool_input"]["command"]) in view.stdout
    assert "\x1b" not in view.stdout
    assert "\x07" not in view.stdout
    assert "\u202e" not in view.stdout
    assert requests(tmp_path)[0]["payload"] == payload
    assert decide(tmp_path, request_id, "deny").returncode == 0
    child.communicate(timeout=3)


def test_unknown_request_does_not_settle_the_known_request(tmp_path, hook_factory):
    child = hook_factory()
    known = wait_requests(tmp_path, 1)[0]
    result = decide(tmp_path, str(uuid.uuid4()))
    assert result.returncode != 0
    assert "unknown request" in result.stderr
    assert requests(tmp_path)[0]["state"] == "pending"
    assert child.poll() is None
    assert decide(tmp_path, known["request_id"], "deny").returncode == 0
    child.communicate(timeout=3)


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        [],
        {**PAYLOAD, "hook_event_name": "PreToolUse"},
        {**PAYLOAD, "tool_input": "printf no"},
    ],
)
def test_invalid_hook_payload_is_rejected_without_decision(tmp_path, invalid):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "hook",
            "--run-dir",
            str(tmp_path),
            "--vendor",
            "claude",
            "--hold-seconds",
            "0.1",
        ],
        input=json.dumps(invalid),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=3,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "permission-queue:" in result.stderr
    assert requests(tmp_path) == []


@pytest.mark.parametrize("hold", ["0", "-1", "nan", "inf", "601"])
def test_hold_must_be_finite_positive_and_bounded(tmp_path, hold):
    result = invoke(tmp_path, "hook", "--vendor", "claude", "--hold-seconds", hold)
    assert result.returncode != 0
    assert "hold must be finite" in result.stderr
    assert requests(tmp_path) == []
