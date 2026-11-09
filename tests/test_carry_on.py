"""Continuation behavior through fake Codex and reviewer I/O boundaries."""

import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "plugins/denubis-hook-carry-on/hooks"
sys.path.insert(0, str(HOOKS))

from carry_on.core import (  # noqa: E402
    Review,
    ReviewError,
    Snapshot,
    ThreadState,
    check_thread,
)
from carry_on.reviewer import (  # noqa: E402
    TerraReviewer,
    parse_review,
    review_evidence,
)
from carry_on.runtime import hook, main  # noqa: E402
from carry_on.store import StateStore  # noqa: E402
from carry_on.transport import CodexBackend, ProtocolError, Proxy  # noqa: E402


class Codex:
    def __init__(self, *snapshots: Snapshot):
        self.snapshots = list(snapshots)
        self.messages: list[tuple[str, str]] = []

    def snapshot(self, thread_id: str) -> Snapshot:
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]

    def wake(self, thread_id: str, message: str) -> None:
        self.messages.append((thread_id, message))


def snapshot(
    *,
    status: str = "idle",
    history: list[dict[str, Any]] | None = None,
    workers: dict[str, str] | None = None,
    complete: bool = True,
) -> Snapshot:
    return Snapshot(
        "parent",
        "/project",
        status,
        [{"type": "userMessage", "content": "Finish the build"}]
        if history is None
        else history,
        workers or {},
        complete,
    )


def unfinished(view: Snapshot, reason: str) -> Review:
    return Review(
        "continue", "Build remains unverified", ["Build requested"], "Run build"
    )


@pytest.mark.parametrize("trigger", ["stop", "idle", "workers_done"])
def test_each_trigger_continues_unfinished_authorized_work(trigger: str) -> None:
    state = ThreadState("parent", "/project", signal=trigger)
    codex = Codex(snapshot())

    assert check_thread(state, codex, unfinished, now=100) == "continued"
    assert len(codex.messages) == 1
    assert "Run build" in codex.messages[0][1]


@pytest.mark.parametrize(
    "status", ["active", "waiting", "interrupted", "closed", "unknown"]
)
def test_non_idle_parent_is_never_reviewed_or_resumed(status: str) -> None:
    state = ThreadState("parent", "/project", signal="stop")
    codex = Codex(snapshot(status=status))
    calls = []

    def review(view, reason):
        calls.append(view)
        return unfinished(view, reason)

    assert check_thread(state, codex, review, now=100) == "inactive"
    assert calls == []
    assert codex.messages == []


@pytest.mark.parametrize("flag", ["paused", "ended"])
def test_user_interrupt_and_session_end_remain_stopped(flag: str) -> None:
    state = ThreadState(
        "parent", "/project", paused=flag == "paused", ended=flag == "ended"
    )
    codex = Codex(snapshot())

    assert check_thread(state, codex, unfinished, now=100) == "inactive"
    assert codex.messages == []


def test_unchanged_stop_events_are_deduplicated() -> None:
    state = ThreadState("parent", "/project", signal="stop")
    codex = Codex(snapshot())

    assert check_thread(state, codex, unfinished, now=100) == "continued"
    assert check_thread(state, codex, unfinished, now=105) == "unchanged"
    assert len(codex.messages) == 1


def test_new_user_input_can_resume_after_interrupt() -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot(status="active"))
    check_thread(state, codex, unfinished, now=100)
    state.paused = True
    codex.snapshots = [snapshot(history=[{"type": "userMessage", "content": "Resume"}])]

    assert check_thread(state, codex, unfinished, now=101) == "continued"
    assert not state.paused


def test_idle_watch_does_not_mistake_running_workers_for_nothing_happening() -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot(workers={"worker": "active"}))

    assert check_thread(state, codex, unfinished, now=100) == "workers_running"
    assert codex.messages == []


def test_last_worker_done_after_parent_stopped_rechecks_previous_wait() -> None:
    state = ThreadState("parent", "/project", signal="stop")
    codex = Codex(snapshot(workers={"worker": "active"}))

    def wait(view, reason):
        return Review("wait", "Worker still running", ["worker active"], "")

    assert check_thread(state, codex, wait, now=100) == "wait"
    codex.snapshots = [snapshot(workers={"worker": "done"})]
    reasons = []

    def review(view, reason):
        reasons.append(reason)
        return unfinished(view, reason)

    assert check_thread(state, codex, review, now=110) == "continued"
    assert reasons == ["workers_done"]


def test_user_or_worker_progress_during_review_discards_stale_continuation() -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot(), snapshot(status="active"))

    assert check_thread(state, codex, unfinished, now=100) == "stale"
    assert codex.messages == []


def test_hook_interrupt_during_review_discards_result() -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot())

    def review(view, reason):
        state.paused = True
        state.generation += 1
        return unfinished(view, reason)

    assert check_thread(state, codex, review, now=100) == "stale"
    assert codex.messages == []


@pytest.mark.parametrize(
    "history,complete", [([], True), ([{"type": "userMessage"}], False)]
)
def test_missing_or_truncated_context_cannot_establish_completion(
    history, complete
) -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot(history=history, complete=complete))

    assert check_thread(state, codex, unfinished, now=100) == "insufficient_context"
    assert codex.messages == []


def test_repeated_assistant_promises_without_actions_eventually_stop_auto_wakes() -> (
    None
):
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot())
    assert check_thread(state, codex, unfinished, now=100) == "continued"
    for index in range(2):
        codex.snapshots = [
            snapshot(
                history=[
                    {"type": "userMessage", "content": "Finish the build"},
                    {"type": "agentMessage", "text": f"I will build it {index}"},
                ]
            )
        ]
        outcome = check_thread(state, codex, unfinished, now=110 + index)
    assert outcome == "no_progress"
    assert len(codex.messages) == 2


def test_real_tool_progress_resets_no_progress_guard() -> None:
    state = ThreadState("parent", "/project", stalls=2, progress="old")
    codex = Codex(
        snapshot(
            history=[
                {"type": "userMessage", "content": "Finish the build"},
                {"type": "commandExecution", "command": "build", "exitCode": 1},
            ]
        )
    )

    assert check_thread(state, codex, unfinished, now=100) == "continued"
    assert state.stalls == 1


def test_failed_reviewer_is_visible_and_retries_are_bounded() -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot())

    def fail(view, reason):
        raise ReviewError("reviewer unavailable")

    assert check_thread(state, codex, fail, now=100) == "review_failed"
    assert state.last_error == "reviewer unavailable"
    assert check_thread(state, codex, fail, now=101) == "retry_limited"
    assert check_thread(state, codex, fail, now=110) == "review_failed"
    assert check_thread(state, codex, fail, now=130) == "review_failed"
    assert check_thread(state, codex, fail, now=500) == "retry_limited"
    assert codex.messages == []


@pytest.mark.parametrize("decision", ["wait", "stop"])
def test_wait_or_complete_decision_never_wakes_parent(decision: str) -> None:
    state = ThreadState("parent", "/project")
    codex = Codex(snapshot())

    def review(view, reason):
        return Review(decision, "No authorized action", ["User input required"], "")

    assert check_thread(state, codex, review, now=100) == decision
    assert check_thread(state, codex, review, now=200) == "unchanged"
    assert codex.messages == []


@pytest.mark.parametrize(
    "changes",
    [
        {"decision": "maybe"},
        {"reason": ""},
        {"evidence": []},
        {"evidence": [1]},
        {"next_action": ""},
        {"decision": 1},
    ],
)
def test_invalid_reviewer_decision_cannot_continue(changes) -> None:
    data = {
        "decision": "continue",
        "reason": "Remaining work",
        "evidence": ["Request"],
        "next_action": "Build",
        **changes,
    }
    with pytest.raises(ReviewError):
        parse_review(json.dumps(data))


@pytest.mark.parametrize("text", ["", "not json", "[]", '{"decision":"stop"}'])
def test_malformed_reviewer_response_is_an_explicit_failure(text) -> None:
    with pytest.raises(ReviewError):
        parse_review(text)


def test_review_includes_original_request_later_decisions_and_actions() -> None:
    view = snapshot(
        history=[
            {"type": "userMessage", "content": "Build it"},
            {"type": "agentMessage", "text": "Plan"},
            {"type": "userMessage", "content": "Also keep Python 3.14"},
            {"type": "commandExecution", "command": "build", "exitCode": 1},
        ],
        workers={"worker": "done"},
    )
    payload = json.loads(review_evidence(view, "workers_done"))

    assert payload["human_messages"] == [view.history[0], view.history[2]]
    assert view.history[-1] in payload["recent_actions"]
    assert payload["workers"] == {"worker": "done"}


def test_store_preserves_interrupt_arriving_while_reviewer_was_running(
    tmp_path: Path,
) -> None:
    store = StateStore(tmp_path, "socket")
    store.signal("parent", "/project", "SessionStart")
    reviewing = store.sessions()["parent"]
    store.signal("parent", "/project", "Interrupt")
    reviewing.reviewed = "stale review"
    store.save_if_current(reviewing)

    assert not store.current(reviewing)
    assert store.sessions()["parent"].paused
    assert store.sessions()["parent"].reviewed == ""


def test_store_scopes_enrollment_to_endpoint_and_never_enrolls_worker_stop(
    tmp_path: Path,
) -> None:
    store = StateStore(tmp_path, "socket-a")
    store.signal("worker", "/project", "SubagentStop")
    store.signal("parent", "/project", "SessionStart")

    assert set(store.sessions()) == {"parent"}
    assert StateStore(tmp_path, "socket-b").sessions() == {}


def test_corrupt_persistent_state_is_reported_instead_of_treated_as_empty(
    tmp_path: Path,
) -> None:
    store = StateStore(tmp_path, "socket")
    store.path.write_text("truncated{")

    with pytest.raises(ValueError):
        store.sessions()


def test_human_correction_mentioning_plugin_marker_remains_human_authority() -> None:
    view = snapshot(
        history=[
            {"type": "userMessage", "content": "Finish the build"},
            {
                "type": "userMessage",
                "content": "The [carry-on] nudge was wrong; resume testing",
            },
        ]
    )

    assert json.loads(review_evidence(view, "idle"))["human_messages"] == view.history


def test_large_context_keeps_late_human_correction_and_marks_omitted_evidence() -> None:
    history = [{"type": "userMessage", "content": "Build a plugin"}]
    history += [{"type": "commandExecution", "output": "x" * 10000}] * 1000
    history += [{"type": "userMessage", "content": "Cancel deployment; tests only"}]
    evidence = review_evidence(snapshot(history=history), "idle")
    payload = json.loads(evidence)

    assert len(evidence) < 220000
    assert payload["human_messages"] == [history[0], history[-1]]
    assert payload["context_omitted"]
    assert not payload["completion_provable"]


def test_lost_wake_response_is_visible_and_never_retried_for_same_snapshot() -> None:
    state = ThreadState("parent", "/project")

    class LostResponse(Codex):
        def wake(self, thread_id, message):
            super().wake(thread_id, message)
            raise RuntimeError("response lost after acceptance")

    codex = LostResponse(snapshot())

    assert check_thread(state, codex, unfinished, now=100) == "delivery_uncertain"
    assert check_thread(state, codex, unfinished, now=200) == "delivery_uncertain"
    assert len(codex.messages) == 1
    assert state.stalls == 1


def test_wake_attempt_is_persisted_before_delivery_and_survives_restart(
    tmp_path: Path,
) -> None:
    store = StateStore(tmp_path, "socket")
    store.signal("parent", "/project", "SessionStart")
    state = store.sessions()["parent"]

    class Crash(Codex):
        def wake(self, thread_id, message):
            assert store.sessions()[thread_id].pending_wake
            raise SystemExit("crash after persisted reservation")

    codex = Crash(snapshot())
    with pytest.raises(SystemExit):
        check_thread(state, codex, unfinished, now=100, reserve=store.reserve)
    restarted = store.sessions()["parent"]

    assert (
        check_thread(restarted, Codex(snapshot()), unfinished, now=200)
        == "delivery_uncertain"
    )
    assert restarted.stalls == 1


class Native(Proxy):
    def __init__(self, *, parent_status="idle", turn_status="completed", children=None):
        self.calls = []
        self.parent_status = parent_status
        self.turn_status = turn_status
        self.children = children or []
        self.watched = set()

    def request(self, method, params, *, timeout=20):
        self.calls.append((method, params))
        if method == "thread/read":
            return {
                "thread": {
                    "id": "parent",
                    "sessionId": "parent",
                    "source": "vscode",
                    "cwd": "/project",
                    "updatedAt": 1,
                    "status": {"type": self.parent_status},
                }
            }
        if method == "thread/turns/list":
            return {"data": [{"id": "turn", "status": self.turn_status}]}
        if method == "thread/list":
            return {"data": self.children, "nextCursor": None}
        if method == "thread/items/list":
            return {
                "data": [
                    {
                        "turnId": "turn",
                        "item": {"type": "userMessage", "content": "Finish the build"},
                    }
                ],
                "nextCursor": None,
            }
        if method == "turn/start":
            return {"turn": {"id": "wake", "status": "inProgress"}}
        raise AssertionError(method)


@pytest.mark.parametrize(
    "status,turn", [("active", "inProgress"), ("idle", "inProgress")]
)
def test_native_busy_or_queued_turn_never_loads_large_history(status, turn) -> None:
    native = Native(parent_status=status, turn_status=turn)

    assert CodexBackend(native).snapshot("parent").status == "active"
    assert [method for method, _ in native.calls] == [
        "thread/read",
        "thread/turns/list",
    ]


@pytest.mark.parametrize(
    "child_status,expected", [("active", "active"), ("notLoaded", "done")]
)
def test_native_child_status_never_replaces_idle_parent_status(
    child_status, expected
) -> None:
    native = Native(
        children=[
            {
                "id": "child",
                "sessionId": "child",
                "parentThreadId": "parent",
                "status": {"type": child_status},
            }
        ]
    )

    view = CodexBackend(native).snapshot("parent")

    assert view.status == "idle"
    assert view.workers == {"child": expected}


def test_native_descendant_results_cannot_include_unrelated_session() -> None:
    native = Native(
        children=[{"id": "stranger", "sessionId": "other", "status": {"type": "idle"}}]
    )

    with pytest.raises(ProtocolError, match="unrelated"):
        CodexBackend(native).snapshot("parent")


def test_native_worker_uses_its_own_session_identity_with_authoritative_parent() -> (
    None
):
    native = Native(
        children=[
            {
                "id": "child",
                "sessionId": "child",
                "parentThreadId": "parent",
                "source": {
                    "subAgent": {
                        "thread_spawn": {
                            "parent_thread_id": "parent",
                            "depth": 1,
                            "agent_path": "/root/delayed_result",
                        }
                    }
                },
                "status": {"type": "active", "activeFlags": []},
            }
        ]
    )

    view = CodexBackend(native).snapshot("parent")

    assert view.status == "idle"
    assert view.workers == {"child": "active"}


def test_native_descendant_ancestry_is_validated_after_all_pages() -> None:
    child = {
        "id": "child",
        "sessionId": "child",
        "parentThreadId": "parent",
        "status": {"type": "active", "activeFlags": []},
    }
    grandchild = {
        "id": "grandchild",
        "sessionId": "grandchild",
        "parentThreadId": "child",
        "status": {"type": "active", "activeFlags": []},
    }

    class PagedTree(Native):
        def request(self, method, params, *, timeout=20):
            if method == "thread/list":
                if params["cursor"] is None:
                    return {"data": [grandchild], "nextCursor": "next"}
                return {"data": [child], "nextCursor": None}
            return super().request(method, params, timeout=timeout)

    assert CodexBackend(PagedTree()).snapshot("parent").workers == {
        "grandchild": "active",
        "child": "active",
    }


@pytest.mark.parametrize(
    "child",
    [
        {"id": "stranger", "sessionId": "parent", "parentThreadId": "other"},
        {
            "id": "stranger",
            "sessionId": "stranger",
            "parentThreadId": "other",
            "source": {"subAgent": {"thread_spawn": {"parent_thread_id": "parent"}}},
        },
        {"id": "stranger", "sessionId": "stranger", "parentThreadId": "stranger"},
    ],
)
def test_unrelated_conflicting_or_cyclic_worker_ancestry_is_rejected(child) -> None:
    native = Native(children=[{**child, "status": {"type": "idle"}}])

    with pytest.raises(ProtocolError):
        CodexBackend(native).snapshot("parent")


def test_native_wake_is_tool_output_and_never_impersonates_a_human() -> None:
    native = Native()

    CodexBackend(native).wake("parent", "Run the build")

    method, params = native.calls[-1]
    assert method == "turn/start"
    assert params["threadId"] == "parent"
    assert params["input"] == []
    assert params["toolOutput"] == {
        "name": "continuation_review",
        "namespace": "carry_on",
        "output": "Run the build",
    }


def test_reviewer_disables_effective_mcp_and_cleans_up_ephemeral_thread() -> None:
    class ReviewDaemon(Native):
        def request(self, method, params, *, timeout=20):
            self.calls.append((method, params))
            if method == "config/read":
                return {
                    "config": {"mcp_servers": {"private-server": {"enabled": True}}}
                }
            if method == "thread/start":
                return {"thread": {"id": "review"}, "sandbox": {"type": "readOnly"}}
            if method == "turn/start":
                return {"turn": {"id": "review-turn"}}
            if method == "thread/unsubscribe":
                return {}
            raise AssertionError(method)

        def collect_review(self, thread_id, turn_id, timeout):
            return json.dumps(
                {
                    "decision": "continue",
                    "reason": "Unfinished",
                    "evidence": ["Build pending"],
                    "next_action": "Run build",
                }
            )

    native = ReviewDaemon()

    assert TerraReviewer(native)(snapshot(), "idle").decision == "continue"
    creation = next(
        params for method, params in native.calls if method == "thread/start"
    )
    assert creation["ephemeral"]
    assert creation["config"]["features.hooks"] is False
    assert creation["config"]["features.sleep_tool"] is False
    assert creation["config"]["mcp_servers"] == {"private-server": {"enabled": False}}
    assert creation["dynamicTools"] == []
    assert native.calls[-1] == ("thread/unsubscribe", {"threadId": "review"})
    assert native.watched == set()


@pytest.mark.parametrize(
    "prompt,agent_id,resumes",
    [
        ("Resume the work", None, True),
        ("", None, False),
        ("Worker task", "child", False),
    ],
)
def test_real_root_prompt_rearms_interrupt_before_first_idle_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    prompt,
    agent_id,
    resumes,
) -> None:
    store = StateStore(tmp_path, "socket")
    store.signal("parent", "/project", "SessionStart")
    state = store.sessions()["parent"]
    check_thread(
        state, CodexBackend(Native(parent_status="active")), unfinished, now=100
    )
    store.save_if_current(state)
    assert state.users == ""
    store.signal("parent", "/project", "Interrupt")
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "parent",
                    "cwd": "/project",
                    "prompt": prompt,
                    "agent_id": agent_id,
                }
            )
        ),
    )

    hook(store, "UserPromptSubmit")

    assert store.sessions()["parent"].paused is not resumes


def test_disabled_control_blocks_later_hooks_without_spawning_watcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["carry-on.py", "--socket", "socket", "--stop"])
    assert main() == 0
    capsys.readouterr()
    monkeypatch.setattr(
        sys, "argv", ["carry-on.py", "--socket", "socket", "--event", "SessionStart"]
    )
    monkeypatch.setattr(
        sys, "stdin", io.StringIO('{"session_id":"parent","cwd":"/project"}')
    )
    assert main() == 0
    assert StateStore(tmp_path, "socket").sessions() == {}
    monkeypatch.setattr(sys, "argv", ["carry-on.py", "--socket", "socket", "--status"])
    assert main() == 0
    status = json.loads(capsys.readouterr().out)
    assert status["disabled"]
    assert status["watcher_pid"] is None


def test_truncated_worker_report_cannot_establish_completion() -> None:
    view = snapshot()
    from dataclasses import replace

    view = replace(
        view,
        worker_evidence={
            "child": [
                {"type": "agentMessage", "text": "x" * 10000},
            ]
        },
    )

    payload = json.loads(review_evidence(view, "workers_done"))

    assert payload["context_omitted"]
    assert not payload["completion_provable"]


def test_many_worker_reports_share_one_aggregate_context_budget() -> None:
    from dataclasses import replace

    view = replace(
        snapshot(),
        worker_evidence={
            str(index): [{"type": "agentMessage", "text": "x" * 5000}] * 10
            for index in range(200)
        },
    )

    evidence = review_evidence(view, "workers_done")

    assert len(evidence) < 50000
    assert json.loads(evidence)["context_omitted"]


def test_native_hook_event_payload_enrolls_parent_without_launcher_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from carry_on import runtime

    launches = []
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path))
    monkeypatch.setenv("CARRY_ON_SOCKET", "socket")
    monkeypatch.setattr(sys, "argv", ["carry-on.py"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "hook_event_name": "SessionStart",
                    "session_id": "parent",
                    "cwd": "/project",
                }
            )
        ),
    )
    monkeypatch.setattr(
        runtime.subprocess, "Popen", lambda *args, **kwargs: launches.append(args)
    )

    assert main() == 0

    assert set(StateStore(tmp_path, "socket").sessions()) == {"parent"}
    assert len(launches) == 1


def test_identical_failed_build_attempts_stop_automatic_nudges() -> None:
    state = ThreadState("parent", "/project")
    history = [{"type": "userMessage", "content": "Run the build"}]
    codex = Codex(snapshot(history=history))
    outcomes = []
    for index in range(6):
        if index:
            history.append(
                {
                    "type": "commandExecution",
                    "id": str(index),
                    "command": "build",
                    "exitCode": 1,
                    "aggregatedOutput": "Dependency unavailable",
                    "durationMs": index * 10,
                    "processId": f"process-{index}",
                }
            )
        codex.snapshots = [snapshot(history=history.copy())]
        outcomes.append(check_thread(state, codex, unfinished, now=index * 10))

    assert outcomes[-1] == "no_progress"
    assert len(codex.messages) == 3
    assert state.stalls == 2


@pytest.mark.parametrize(
    "changed",
    [
        {
            "type": "commandExecution",
            "id": "new",
            "command": "build",
            "exitCode": 1,
            "aggregatedOutput": "Different missing dependency",
        },
        {
            "type": "commandExecution",
            "id": "new",
            "command": "build",
            "exitCode": 0,
            "aggregatedOutput": "Build succeeded",
        },
        {
            "type": "fileChange",
            "id": "new",
            "status": "completed",
            "changes": [{"path": "/project/build.py", "diff": "+fix dependency"}],
        },
        {"type": "userMessage", "id": "new", "content": "Retry the build now"},
    ],
)
def test_changed_action_result_or_user_input_resets_stalled_build_guard(
    changed,
) -> None:
    state = ThreadState("parent", "/project")
    history = [
        {"type": "userMessage", "content": "Run the build"},
        {
            "type": "commandExecution",
            "id": "old",
            "command": "build",
            "exitCode": 1,
            "aggregatedOutput": "Dependency unavailable",
        },
    ]
    codex = Codex(snapshot(history=history))
    assert check_thread(state, codex, unfinished, now=100) == "continued"
    history.append({"type": "agentMessage", "text": "I will retry"})
    codex.snapshots = [snapshot(history=history.copy())]
    assert check_thread(state, codex, unfinished, now=110) == "continued"
    history.append({"type": "agentMessage", "text": "I will retry again"})
    codex.snapshots = [snapshot(history=history.copy())]
    assert check_thread(state, codex, unfinished, now=120) == "no_progress"
    history.append(changed)
    codex.snapshots = [snapshot(history=history.copy())]

    assert check_thread(state, codex, unfinished, now=130) == "continued"
    assert state.stalls == 1


@pytest.mark.parametrize(
    "report,expected",
    [("Same failed build", "no_progress"), ("Build now succeeded", "continued")],
)
def test_worker_report_metadata_does_not_reset_guard_but_new_result_does(
    report, expected
) -> None:
    from dataclasses import replace

    state = ThreadState("parent", "/project")
    view = replace(
        snapshot(),
        worker_evidence={
            "child": [
                {"type": "agentMessage", "id": "old", "text": "Same failed build"},
            ]
        },
    )
    codex = Codex(view)
    assert check_thread(state, codex, unfinished, now=100) == "continued"
    view = replace(
        view, history=[*view.history, {"type": "agentMessage", "text": "Retry"}]
    )
    codex.snapshots = [view]
    assert check_thread(state, codex, unfinished, now=110) == "continued"
    codex.snapshots = [
        replace(
            view,
            worker_evidence={
                "child": [
                    {"type": "agentMessage", "id": "new", "text": report},
                ]
            },
        )
    ]

    assert check_thread(state, codex, unfinished, now=120) == expected


@pytest.mark.parametrize(
    "event,flag", [("Interrupt", "paused"), ("SessionEnd", "ended")]
)
def test_cleanup_hook_persists_before_any_daemon_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event,
    flag,
) -> None:
    from carry_on import runtime

    stores = [StateStore(tmp_path, "socket-a"), StateStore(tmp_path, "socket-b")]
    stores[0].signal("parent", "/project", "SessionStart")
    stores[1].signal("stranger", "/other", "SessionStart")
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["carry-on.py"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "hook_event_name": event,
                    "session_id": "parent",
                    "cwd": "/project",
                }
            )
        ),
    )

    def discovery_must_not_run():
        raise AssertionError("cleanup must not wait for daemon discovery")

    monkeypatch.setattr(runtime, "endpoint", discovery_must_not_run)

    assert main() == 0
    assert getattr(stores[0].sessions()["parent"], flag)
    assert not getattr(stores[1].sessions()["stranger"], flag)
