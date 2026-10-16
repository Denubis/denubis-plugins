"""Check native pane state and honest historical-time evidence."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments/permission-queue/codex_pane_state.py"
)
SPEC = importlib.util.spec_from_file_location("permission_codex_pane_state", PATH)
assert SPEC is not None and SPEC.loader is not None
STATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STATE
SPEC.loader.exec_module(STATE)

THREAD = "01a13dd3-e299-7e30-9cfa-3ab647121e1f"


def pane(title="Ready | project | main | Review changes | GPT-6.1 Sol xhigh"):
    return {
        "pane_title": title,
        "pane_current_command": "codex",
        "pane_current_path": "/repo/project",
    }


def thread(**overrides):
    fields = {
        "thread_id": THREAD,
        "title": "Review changes",
        "cwd": "/repo/project",
        "state": "idle",
        "state_since": 1000.0,
        "state_since_source": "Codex turn completedAt",
        "parent_thread_id": None,
    }
    return SimpleNamespace(**(fields | overrides))


@pytest.fixture(autouse=True)
def no_host_process_scan(monkeypatch):
    monkeypatch.setattr(STATE.policy(), "held_sessions", lambda pid: None)


def test_native_ready_question_stays_idle_without_inventing_startup_age():
    result = STATE.observe(pane(), "• Is this acceptable?\n\u203a ", (), None)
    assert (result.state, result.since, result.approximate) == ("idle", None, False)


@pytest.mark.parametrize(
    "words", ["Fix working directory", "Review action required wording"]
)
def test_task_words_do_not_spoof_native_state(words):
    result = STATE.observe(
        pane(f"Ready | project | main | {words} | GPT-6.1 Sol xhigh"), "", (), None
    )
    assert result.state == "idle"


@pytest.mark.parametrize(
    "lead,state",
    [
        ("Working", "running"),
        ("Thinking", "running"),
        ("Starting", "running"),
        ("Action Required", "blocked"),
    ],
)
def test_explicit_native_leading_state(lead, state):
    result = STATE.observe(
        pane(f"{lead} | project | main | Task | GPT-6.1 Sol xhigh"), "", (), None
    )
    assert result.state == state
    assert result.since is None


def test_visible_pending_approval_preempts_ready_but_never_uses_turn_age():
    result = STATE.observe(
        pane(),
        "Would you like to run this command?\n1. Yes\n2. No\n",
        [thread(state="blocked")],
        None,
    )
    assert result.state == "blocked"
    assert result.since is None


def test_native_bracket_bang_action_required_stays_blocked():
    result = STATE.observe(
        pane("[ ! ] Action Required | project | main | Task | GPT-6.1 Sol xhigh"),
        "",
        (),
        None,
    )
    assert result.state == "blocked"


def test_unknown_title_or_shell_never_defaults_to_running():
    assert STATE.observe(pane("Unrecognized"), "", (), None).state == "unknown"
    data = pane()
    data["pane_current_command"] = "fish"
    assert STATE.observe(data, "", [thread()], None).state == "unknown"


def test_exact_cwd_and_complete_task_match_gives_labelled_display_correlation():
    result = STATE.observe(pane(), "", {THREAD: thread()}, None)
    assert (result.state, result.since, result.approximate) == ("idle", 1000.0, True)
    assert THREAD in result.source


@pytest.mark.parametrize(
    "changes",
    [
        {"cwd": "/repo/other"},
        {"title": "Review changes later"},
        {"state": "running"},
        {"parent_thread_id": "parent"},
    ],
)
def test_nonmatching_or_disagreeing_thread_does_not_supply_age(changes):
    result = STATE.observe(pane(), "", [thread(**changes)], None)
    assert result.state == "idle"
    assert result.since is None


def test_duplicate_task_and_cwd_are_ambiguous_even_if_only_one_state_agrees():
    result = STATE.observe(
        pane(), "", [thread(), thread(thread_id="other", state="running")], None
    )
    assert result.since is None


@pytest.mark.parametrize(
    "task", ["Review changes...", "Review changes…", "Review | changes"]
)
def test_truncated_or_separator_ambiguous_native_task_never_correlates(task):
    result = STATE.observe(
        pane(f"Ready | project | main | {task} | GPT-6.1 Sol xhigh"),
        "",
        [thread(title=task)],
        None,
    )
    assert result.since is None


def test_canonical_cwd_matches_symlink_without_basename_guess(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    data = pane()
    data["pane_current_path"] = str(alias)
    result = STATE.observe(data, "", [thread(cwd=str(actual))], None)
    assert result.since == 1000.0


def rollout(tmp_path, events):
    path = tmp_path / "rollout.jsonl"
    records = [
        {"type": "session_meta", "payload": {"id": THREAD, "session_id": THREAD}}
    ]
    records.extend({"type": "event_msg", "payload": payload} for payload in events)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def own(monkeypatch, path):
    held = STATE.policy().HeldSessions(frozenset({THREAD}), {THREAD: path})
    monkeypatch.setattr(STATE.policy(), "held_sessions", lambda pid: held)


def test_owned_main_rollout_completion_beats_correlated_daemon_age(
    monkeypatch, tmp_path
):
    path = rollout(
        tmp_path,
        [
            {"type": "task_started", "started_at": 900},
            {"type": "task_complete", "completed_at": 950},
        ],
    )
    own(monkeypatch, path)
    result = STATE.observe(pane(), "", [thread()], 42)
    assert (result.state, result.since, result.approximate) == ("idle", 950.0, False)


def test_latest_owned_turn_must_agree_with_live_state(monkeypatch, tmp_path):
    path = rollout(
        tmp_path,
        [
            {"type": "task_complete", "completed_at": 950},
            {"type": "task_started", "started_at": 975},
        ],
    )
    own(monkeypatch, path)
    result = STATE.observe(
        pane("Working | project | main | Task | GPT-6.1 Sol xhigh"), "", (), 42
    )
    assert (result.state, result.since) == ("running", 975.0)
    assert STATE.observe(pane(), "", (), 42).since is None


def test_missing_latest_timestamp_never_restores_older_turn_age(monkeypatch, tmp_path):
    path = rollout(
        tmp_path,
        [{"type": "task_complete", "completed_at": 950}, {"type": "task_started"}],
    )
    own(monkeypatch, path)
    result = STATE.observe(
        pane("Working | project | main | Task | GPT-6.1 Sol xhigh"), "", (), 42
    )
    assert result.since is None


def test_rollout_clear_ambiguity_does_not_use_old_main(monkeypatch, tmp_path):
    path = rollout(tmp_path, [{"type": "task_complete", "completed_at": 950}])
    held = STATE.policy().HeldSessions(
        frozenset({THREAD, "new-unwritten"}), {THREAD: path}
    )
    monkeypatch.setattr(STATE.policy(), "held_sessions", lambda pid: held)
    assert STATE.observe(pane(), "", (), 42).since is None


def test_partial_last_rollout_record_cannot_restore_earlier_completion(
    monkeypatch, tmp_path
):
    path = rollout(tmp_path, [{"type": "task_complete", "completed_at": 950}])
    with path.open("a") as stream:
        stream.write('{"type":"event_msg","payload":{"type":"task_started"')
    own(monkeypatch, path)
    assert STATE.observe(pane(), "", (), 42).since is None


def test_rollout_tail_is_bounded_even_when_latest_transition_is_too_old(
    monkeypatch, tmp_path
):
    path = rollout(tmp_path, [{"type": "task_complete", "completed_at": 950}])
    with path.open("a") as stream:
        stream.write(json.dumps({"padding": "x" * (STATE.TAIL_LIMIT + 10)}) + "\n")
    own(monkeypatch, path)
    assert STATE.observe(pane(), "", (), 42).since is None


def test_owned_rollout_is_revalidated_after_reading_history(monkeypatch, tmp_path):
    path = rollout(tmp_path, [{"type": "task_complete", "completed_at": 950}])
    held = STATE.policy().HeldSessions(frozenset({THREAD}), {THREAD: path})
    observations = iter([held, None])
    monkeypatch.setattr(STATE.policy(), "held_sessions", lambda pid: next(observations))
    assert STATE.observe(pane(), "", (), 42).since is None
