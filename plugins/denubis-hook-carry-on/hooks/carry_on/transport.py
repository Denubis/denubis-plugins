"""Synchronous WebSocket JSON-RPC client for an existing Codex daemon."""

import json
import time
from collections import deque
from typing import Any

from websockets.exceptions import WebSocketException
from websockets.sync.client import unix_connect

from .core import Snapshot, digest


class ProtocolError(RuntimeError):
    """The daemon connection or its response did not satisfy the protocol."""


class Proxy:
    def __init__(self, endpoint: str):
        try:
            self.socket = unix_connect(
                endpoint,
                uri="ws://localhost/",
                open_timeout=10,
                close_timeout=3,
                max_size=32 * 1024 * 1024,
            )
        except (OSError, TimeoutError, WebSocketException) as error:
            raise ProtocolError(f"cannot connect to Codex daemon: {error}") from error
        self.sequence = 0
        self.watched: set[str] = set()
        self.events: deque[dict[str, Any]] = deque()
        try:
            self.request(
                "initialize",
                {
                    "clientInfo": {"name": "denubis_carry_on", "version": "0.1.0"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            self.send({"method": "initialized"})
        except ProtocolError:
            self.close()
            raise

    def send(self, message: dict[str, Any]) -> None:
        try:
            self.socket.send(json.dumps(message))
        except (OSError, WebSocketException) as error:
            raise ProtocolError(f"cannot write app-server request: {error}") from error

    def _message(self, deadline: float) -> dict[str, Any]:
        try:
            line = self.socket.recv(timeout=max(0, deadline - time.monotonic()))
            message = json.loads(line)
        except (OSError, TimeoutError, WebSocketException) as error:
            raise ProtocolError(f"app-server connection failed: {error}") from error
        except ValueError as error:
            raise ProtocolError("app-server emitted invalid JSON") from error
        if not isinstance(message, dict):
            raise ProtocolError("app-server emitted a non-object message")
        return message

    def request(
        self, method: str, params: dict[str, Any], *, timeout: float = 20
    ) -> dict[str, Any]:
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            message = self._message(deadline)
            if message.get("id") != request_id or "method" in message:
                # Other clients own their requests, including approval decisions.
                self._route(message)
                continue
            if "error" in message:
                raise ProtocolError(f"{method}: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise ProtocolError(f"{method}: missing object result")
            return result

    def _route(self, message: dict[str, Any]) -> None:
        params = message.get("params", {})
        if not isinstance(params, dict) or params.get("threadId") not in self.watched:
            return
        if "id" in message:
            raise ProtocolError(
                "isolated reviewer attempted an interactive tool request"
            )
        if message.get("method") in {"item/completed", "turn/completed"}:
            self.events.append(message)

    def collect_review(self, thread_id: str, turn_id: str, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        response = None
        while True:
            if not self.events:
                self._route(self._message(deadline))
                continue
            event = self.events.popleft()
            params = event["params"]
            if params.get("threadId") != thread_id:
                continue
            item = params.get("item", {})
            if (
                event["method"] == "item/completed"
                and params.get("turnId") == turn_id
                and item.get("type") == "agentMessage"
            ):
                response = item.get("text")
                if not isinstance(response, str) or len(response) > 8192:
                    raise ProtocolError(
                        "reviewer returned an invalid or oversized message"
                    )
            turn = params.get("turn", {})
            if event["method"] == "turn/completed" and turn.get("id") == turn_id:
                if turn.get("status") != "completed" or response is None:
                    raise ProtocolError(
                        "reviewer turn did not complete with a response"
                    )
                return response

    def close(self) -> None:
        self.socket.close()


def runtime_status(thread: dict[str, Any]) -> str:
    status = thread.get("status", {})
    kind = status.get("type") if isinstance(status, dict) else None
    if kind == "active":
        return "active"
    if kind != "idle":
        return "unknown"
    turns = thread.get("turns", [])
    if turns and turns[-1].get("status") == "interrupted":
        return "interrupted"
    if turns and turns[-1].get("status") == "inProgress":
        return "active"
    return "idle"


def _parent_thread(child: dict[str, Any]) -> str:
    parent = child.get("parentThreadId")
    source = child.get("source")
    subagent = source.get("subAgent") if isinstance(source, dict) else None
    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
    source_parent = spawn.get("parent_thread_id") if isinstance(spawn, dict) else None
    if parent is not None and source_parent is not None and parent != source_parent:
        raise ProtocolError("thread/list returned conflicting parent relationships")
    relationship = parent if parent is not None else source_parent
    if not isinstance(relationship, str) or not relationship:
        raise ProtocolError(
            "thread/list returned an unrelated descendant without a parent"
        )
    return relationship


def _validate_descendants(root: str, children: list[dict[str, Any]]) -> None:
    parents = {}
    for child in children:
        child_id = child.get("id")
        if not isinstance(child_id, str) or not child_id or child_id == root:
            raise ProtocolError("thread/list returned an unrelated descendant identity")
        parents[child_id] = _parent_thread(child)
    for child_id in parents:
        current = child_id
        seen = set()
        while current != root:
            if current in seen or current not in parents:
                raise ProtocolError("thread/list returned an unrelated descendant tree")
            seen.add(current)
            current = parents[current]


class CodexBackend:
    def __init__(self, proxy: Proxy):
        self.proxy = proxy
        self.history_cache: dict[
            str, tuple[tuple[Any, ...], list[dict[str, Any]], str]
        ] = {}

    def read(self, thread_id: str) -> dict[str, Any]:
        response = self.proxy.request(
            "thread/read",
            {
                "threadId": thread_id,
                "includeTurns": False,
            },
        )
        thread = response.get("thread")
        if not isinstance(thread, dict):
            raise ProtocolError("thread/read omitted thread")
        return thread

    def latest_turn(self, thread_id: str) -> dict[str, Any]:
        response = self.proxy.request(
            "thread/turns/list",
            {
                "threadId": thread_id,
                "limit": 1,
                "itemsView": "notLoaded",
                "sortDirection": "desc",
            },
        )
        turns = response.get("data")
        if not isinstance(turns, list):
            raise ProtocolError("thread/turns/list omitted turn records")
        return turns[0] if turns else {}

    def history(
        self, thread: dict[str, Any], latest: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str]:
        thread_id = thread["id"]
        revision = (thread.get("updatedAt"), latest.get("id"), latest.get("status"))
        previous = self.history_cache.get(thread_id)
        if previous is not None and previous[0] == revision:
            return previous[1], previous[2]
        history = []
        cursor = None
        while True:
            response = self.proxy.request(
                "thread/items/list",
                {
                    "threadId": thread_id,
                    "limit": 100,
                    "cursor": cursor,
                    "sortDirection": "asc",
                },
            )
            entries = response.get("data")
            if not isinstance(entries, list):
                raise ProtocolError("thread/items/list omitted history records")
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(
                    entry.get("item"), dict
                ):
                    raise ProtocolError(
                        "thread/items/list returned an invalid history item"
                    )
                history.append(entry["item"])
            cursor = response.get("nextCursor")
            if cursor is None:
                break
        key = digest(history)
        self.history_cache[thread_id] = (revision, history, key)
        return history, key

    def descendants(self, thread_id: str) -> list[dict[str, Any]]:
        result = []
        cursor = None
        while True:
            response = self.proxy.request(
                "thread/list",
                {
                    "ancestorThreadId": thread_id,
                    "sourceKinds": ["subAgent"],
                    "limit": 100,
                    "cursor": cursor,
                },
            )
            data = response.get("data")
            if not isinstance(data, list):
                raise ProtocolError("thread/list omitted descendant records")
            for item in data:
                if not isinstance(item, dict):
                    raise ProtocolError(
                        "thread/list returned an invalid descendant record"
                    )
                result.append(item)
            cursor = response.get("nextCursor")
            if cursor is None:
                _validate_descendants(thread_id, result)
                return result

    def snapshot(self, thread_id: str) -> Snapshot:
        thread = self.read(thread_id)
        latest = self.latest_turn(thread_id)
        thread["turns"] = [latest] if latest else []
        status = runtime_status(thread)
        source = thread.get("source")
        parent = thread.get("parentThreadId") or (
            isinstance(source, dict) and "subAgent" in source
        )
        root_identity = thread.get("id") == thread.get("sessionId") == thread_id
        if parent or not root_identity:
            status = "closed"
        if status != "idle":
            previous = self.history_cache.get(thread_id)
            history = previous[1] if previous else []
            key = previous[2] if previous else ""
            return Snapshot(
                thread_id,
                str(thread.get("cwd", "")),
                status,
                history,
                complete=bool(history),
                latest_turn_id=str(latest.get("id", "")),
                history_key=key,
            )
        history, history_key = self.history(thread, latest)
        workers = {}
        worker_evidence = {}
        for child in self.descendants(thread_id):
            child_id = child.get("id")
            if isinstance(child_id, str):
                child_status = runtime_status(child)
                if child_status == "unknown":
                    child_turn = self.latest_turn(child_id)
                    if child_turn.get("status") in {
                        "completed",
                        "failed",
                        "interrupted",
                    }:
                        child_status = "idle"
                workers[child_id] = "done" if child_status == "idle" else child_status
                if child_status == "idle":
                    response = self.proxy.request(
                        "thread/items/list",
                        {
                            "threadId": child_id,
                            "limit": 10,
                            "sortDirection": "desc",
                        },
                    )
                    entries = response.get("data")
                    if not isinstance(entries, list):
                        raise ProtocolError("worker history unavailable")
                    worker_evidence[child_id] = [
                        entry["item"] for entry in reversed(entries)
                    ]
        return Snapshot(
            thread_id,
            str(thread.get("cwd", "")),
            status,
            history,
            workers,
            bool(history),
            str(latest.get("id", "")),
            history_key,
            worker_evidence,
        )

    def wake(self, thread_id: str, message: str) -> None:
        self.proxy.request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [],
                "toolOutput": {
                    "namespace": "carry_on",
                    "name": "continuation_review",
                    "output": message,
                },
                "turnTrigger": "carry_on",
            },
        )
