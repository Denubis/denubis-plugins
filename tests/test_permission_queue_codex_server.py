"""Exercise the daemon adapter through a real Unix WebSocket server."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import unix_serve

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments" / "permission-queue" / "codex_server.py"


def adapter_module():
    spec = importlib.util.spec_from_file_location(
        "permission_queue_codex_server", MODULE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def daemon(tmp_path):
    class Daemon:
        def __init__(self):
            self.path = tmp_path / "daemon.sock"
            self.connections = []
            self.finished_connections = []
            self.handler_finished = threading.Condition()
            self.calls = []
            self.answers = []
            self.status = {"type": "idle"}
            self.turns = [
                {
                    "id": "turn-1",
                    "status": "completed",
                    "startedAt": 100,
                    "completedAt": 120,
                    "items": [
                        {"type": "agentMessage", "text": "Full conversation context"}
                    ],
                }
            ]
            self.offered = ["accept", "acceptForSession", "decline", "cancel"]
            self.stall = False
            self.generation = 0
            self.history_error = None
            self.resolve_answers = True
            self.command = "printf 'harmless fixture'"
            self.loaded = ["thread-1"]

        def request(self, thread_id="thread-1"):
            return {
                "id": 41 if thread_id == "thread-1" else 42,
                "method": "item/commandExecution/requestApproval",
                "params": {
                    "threadId": thread_id,
                    "turnId": "turn-1",
                    "itemId": "item-1",
                    "startedAtMs": 125000,
                    "command": self.command,
                    "cwd": "/fixture",
                    "availableDecisions": self.offered,
                },
            }

        def broadcast(self, value):
            for connection in self.connections.copy():
                try:
                    connection.send(json.dumps(value))
                except ConnectionClosed:
                    self.connections.remove(connection)

        def resolved(self):
            self.broadcast(
                {
                    "method": "serverRequest/resolved",
                    "params": {"threadId": "thread-1", "requestId": 41},
                }
            )

        def handler(self, connection):
            self.connections.append(connection)
            try:
                for raw in connection:
                    message = json.loads(raw)
                    if "method" not in message:
                        self.answers.append(message)
                        if self.resolve_answers:
                            self.resolved()
                        continue
                    method = message["method"]
                    self.calls.append(message)
                    if method == "initialized" or (
                        self.stall and method == "thread/read"
                    ):
                        continue
                    if method == "initialize":
                        result = {"userAgent": "fixture"}
                    elif method == "thread/loaded/list":
                        result = {"data": self.loaded, "nextCursor": None}
                    elif method == "thread/read":
                        result = {
                            "thread": {
                                "id": message["params"]["threadId"],
                                "sessionId": "root-1",
                                "name": "Fixture task",
                                "cwd": "/fixture",
                                "status": self.status,
                            }
                        }
                    elif method == "thread/turns/list":
                        if self.history_error:
                            connection.send(
                                json.dumps(
                                    {
                                        "id": message["id"],
                                        "error": {
                                            "code": -32600,
                                            "message": self.history_error,
                                        },
                                    }
                                )
                            )
                            continue
                        result = {"data": self.turns, "nextCursor": None}
                    elif method == "thread/resume":
                        connection.send(
                            json.dumps(
                                {
                                    "id": message["id"],
                                    "result": {"thread": {"id": "thread-1"}},
                                }
                            )
                        )
                        connection.ping(b"fixture ping")
                        encoded = json.dumps(
                            self.request(message["params"]["threadId"])
                        )
                        connection.send([encoded[:20], encoded[20:]])
                        continue
                    else:
                        assert method == "thread/unsubscribe"
                        result = {"status": "unsubscribed"}
                    connection.send(json.dumps({"id": message["id"], "result": result}))
            except ConnectionClosed:
                return

        def serve_connection(self, connection):
            try:
                self.handler(connection)
            finally:
                # Iterating a connection stops only once websockets has closed it.
                with self.handler_finished:
                    self.finished_connections.append(connection)
                    self.handler_finished.notify_all()

        def wait_for_handlers(self, timeout=3):
            with self.handler_finished:
                self.handler_finished.wait_for(
                    lambda: all(
                        connection in self.finished_connections
                        for connection in self.connections
                    ),
                    timeout,
                )

    fixture = Daemon()
    with unix_serve(
        fixture.serve_connection, path=str(fixture.path), close_timeout=0.1
    ) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield fixture
        finally:
            for connection in fixture.connections:
                connection.close()
            server.shutdown()
            thread.join(timeout=3)
            assert not thread.is_alive()


def test_read_status_history_is_passive_and_retains_real_timestamps(daemon):
    module = adapter_module()
    with module.CodexServer(daemon.path) as client:
        assert client.loaded_threads() == ["thread-1"]
        snapshot = client.snapshot("thread-1")
        assert snapshot.thread_id == "thread-1"
        assert snapshot.session_id == "root-1"
        assert snapshot.state == "idle"
        assert snapshot.state_since == 120
        assert "completedAt" in snapshot.state_since_source
        assert (
            snapshot.recent_turns[0]["items"][0]["text"] == "Full conversation context"
        )
        assert snapshot.requests == ()
        assert [call["method"] for call in daemon.calls] == [
            "initialize",
            "initialized",
            "thread/loaded/list",
            "thread/read",
            "thread/turns/list",
        ]
        daemon.status = {"type": "active", "activeFlags": []}
        daemon.turns[0]["status"] = "inProgress"
        daemon.turns[0]["completedAt"] = None
        assert client.snapshot("thread-1").state_since == 100


def test_explicit_select_replays_fragmented_request_and_is_idempotent(daemon):
    module = adapter_module()
    daemon.status = {"type": "active", "activeFlags": ["waitingOnApproval"]}
    with module.CodexServer(daemon.path) as client:
        snapshot = client.select("thread-1")
        (request,) = snapshot.requests
        assert snapshot.state == "blocked"
        assert snapshot.state_since == 125
        assert request.params["command"] == "printf 'harmless fixture'"
        assert request.decisions == ("accept", "acceptForSession", "decline", "cancel")
        again = client.select("thread-1")
        assert again.requests[0].occurrence_id == request.occurrence_id
        assert sum(call["method"] == "thread/resume" for call in daemon.calls) == 1
        result = client.answer(request.occurrence_id, "decline")
        assert result.status == "resolved"
        assert daemon.answers == [{"id": 41, "result": {"decision": "decline"}}]
        with pytest.raises(module.CodexError, match=r"stale|resolved"):
            client.answer(request.occurrence_id, "accept")


def test_competing_resolution_and_connection_change_refuse_old_occurrences(daemon):
    module = adapter_module()
    with module.CodexServer(daemon.path) as client:
        (old,) = client.select("thread-1").requests
        daemon.resolved()
        # A read establishes a positive ordering barrier after the remote resolution.
        assert client.snapshot("thread-1").requests == ()
        with pytest.raises(module.CodexError, match=r"stale|resolved"):
            client.answer(old.occurrence_id, "accept")
        daemon.connections[-1].close()
        client.snapshot("thread-1")
        assert client.snapshot("thread-1").requests == ()
        (current,) = client.select("thread-1").requests
        assert current.occurrence_id != old.occurrence_id
        with pytest.raises(module.CodexError, match=r"stale|resolved"):
            client.answer(old.occurrence_id, "accept")
        assert daemon.answers == []


def test_offered_decisions_are_validated_before_sending(daemon):
    module = adapter_module()
    daemon.offered = [
        "decline",
        {"acceptWithExecpolicyAmendment": {"execpolicy_amendment": ["printf"]}},
    ]
    with module.CodexServer(daemon.path) as client:
        (request,) = client.select("thread-1").requests
        assert request.decisions == ("decline",)
        with pytest.raises(module.CodexError, match="offered"):
            client.answer(request.occurrence_id, "acceptForSession")
        assert (
            client.snapshot("thread-1").requests[0].occurrence_id
            == request.occurrence_id
        )
        assert daemon.answers == []


def test_rpc_timeout_is_bounded_and_read_can_reconnect(daemon):
    module = adapter_module()
    daemon.stall = True
    with module.CodexServer(daemon.path, timeout=0.1, snapshot_timeout=0.3) as client:
        with pytest.raises(module.CodexError, match="timed out"):
            client.snapshot("thread-1")
        daemon.stall = False
        assert client.snapshot("thread-1").state == "idle"


def test_default_socket_respects_codex_home(tmp_path, monkeypatch):
    module = adapter_module()
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    assert (
        module.default_socket_path()
        == tmp_path / "app-server-control" / "app-server-control.sock"
    )


def test_history_unavailable_keeps_real_runtime_status_and_explicit_error(daemon):
    module = adapter_module()
    daemon.history_error = "Thread history is not materialized yet"
    with module.CodexServer(daemon.path) as client:
        snapshot = client.snapshot("thread-1")
        assert snapshot.state == "idle"
        assert "not materialized" in snapshot.history_error
        assert snapshot.recent_turns == ()
        assert snapshot.state_since is None


def test_answer_timeout_is_unknown_and_never_retried(daemon):
    module = adapter_module()
    daemon.resolve_answers = False
    with module.CodexServer(daemon.path, timeout=0.1) as client:
        (occurrence,) = client.select("thread-1").requests
        with pytest.raises(module.CodexError, match="outcome unknown"):
            client.answer(occurrence.occurrence_id, "accept")
        with pytest.raises(module.CodexError, match=r"stale|resolved"):
            client.answer(occurrence.occurrence_id, "accept")
        assert daemon.answers == [{"id": 41, "result": {"decision": "accept"}}]


def test_changed_payload_cannot_replace_a_displayed_request_occurrence(daemon):
    module = adapter_module()
    with module.CodexServer(daemon.path) as client:
        (occurrence,) = client.select("thread-1").requests
        daemon.command = "different command must never inherit approval"
        daemon.broadcast(daemon.request())
        with pytest.raises(module.CodexError, match=r"changed|reused"):
            client.snapshot("thread-1")
        with pytest.raises(module.CodexError, match=r"stale|resolved"):
            client.answer(occurrence.occurrence_id, "accept")
        assert daemon.answers == []


def test_switching_selection_releases_only_previous_attachment(daemon):
    module = adapter_module()
    daemon.loaded = ["thread-1", "thread-2"]
    with module.CodexServer(daemon.path) as client:
        (old,) = client.select("thread-1").requests
        (current,) = client.select("thread-2").requests
        assert current.thread_id == "thread-2"
        released = [
            call["params"]["threadId"]
            for call in daemon.calls
            if call["method"] == "thread/unsubscribe"
        ]
        assert released == ["thread-1"]
        with pytest.raises(module.CodexError, match=r"stale|resolved"):
            client.answer(old.occurrence_id, "accept")
        assert daemon.answers == []
