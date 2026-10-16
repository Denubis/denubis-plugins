"""Structured access to an existing Codex 0.162.1 daemon over Unix WebSocket."""

from __future__ import annotations

import json
import math
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.sync.client import unix_connect

if TYPE_CHECKING:
    from websockets.sync.client import ClientConnection

# Native string variants in Codex 0.162.1 approval response schemas. Policy
# amendment objects remain unsupported; they must never become implied grants.
NATIVE_DECISIONS = ("accept", "acceptForSession", "decline", "cancel")
MAX_MESSAGES = 512


class CodexError(RuntimeError):
    """A bounded daemon operation failed or a request is no longer actionable."""


@dataclass(frozen=True)
class RequestOccurrence:
    occurrence_id: str
    request_id: str | int
    thread_id: str
    turn_id: str | None
    item_id: str | None
    method: str
    params: dict
    started_at: float | None
    decisions: tuple[str, ...]


@dataclass(frozen=True)
class ThreadSnapshot:
    thread_id: str
    session_id: str
    title: str
    cwd: str
    state: str
    state_since: float | None
    state_since_source: str
    recent_turns: tuple[dict, ...]
    requests: tuple[RequestOccurrence, ...]
    history_error: str = ""
    parent_thread_id: str | None = None
    source: str | dict = "unknown"


@dataclass(frozen=True)
class AnswerResult:
    occurrence_id: str
    status: str


def default_socket_path() -> Path:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return home / "app-server-control" / "app-server-control.sock"


class CodexRpcError(CodexError):
    """The daemon returned an explicit JSON-RPC error."""


class _Disconnected(CodexError):
    """The transport failed; only read operations may retry."""


def timestamp(value: object, *, milliseconds: bool = False) -> float | None:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        return None
    return value / 1000 if milliseconds else float(value)


def decisions_for(method: str, params: dict) -> tuple[str, ...]:
    if method == "item/fileChange/requestApproval":
        return NATIVE_DECISIONS
    if method != "item/commandExecution/requestApproval":
        return ()
    offered = params.get("availableDecisions")
    if offered is None:
        # No standing grant is implied when the server omits offered choices.
        return ("accept", "decline", "cancel")
    if not isinstance(offered, list):
        raise CodexError("Invalid approval decisions from daemon")
    return tuple(
        dict.fromkeys(
            value
            for value in offered
            if isinstance(value, str) and value in NATIVE_DECISIONS
        )
    )


class CodexServer:
    """Serialize bounded reads and explicit approval participation on one connection.

    A read can reconnect once. Reconnection invalidates occurrences and attachment;
    it never replays a resume or an answer. Call select explicitly to participate.
    """

    def __init__(
        self,
        socket_path: Path | None = None,
        *,
        timeout: float = 2,
        snapshot_timeout: float = 5,
    ):
        if timeout <= 0 or snapshot_timeout <= 0:
            raise ValueError("Daemon timeouts must be positive")
        self.socket_path = Path(socket_path or default_socket_path())
        self.timeout = timeout
        self.snapshot_timeout = snapshot_timeout
        self._lock = threading.RLock()
        self._ws: ClientConnection | None = None
        self._sequence = 0
        self._generation = ""
        self._attached: str | None = None
        self._pending: dict[str, RequestOccurrence] = {}
        self._resolved: dict[str, None] = {}
        self._sent: dict[str, RequestOccurrence] = {}

    def _reset(self) -> None:
        connection, self._ws = self._ws, None
        self._attached = None
        self._pending.clear()
        self._resolved.clear()
        self._sent.clear()
        self._generation = ""
        if connection is not None:
            connection.close()

    def _remaining(self, deadline: float) -> float:
        remaining = min(self.timeout, deadline - time.monotonic())
        if remaining <= 0:
            raise CodexError("Daemon operation timed out")
        return remaining

    def _connect(self, deadline: float) -> None:
        if self._ws is not None:
            return
        try:
            self._ws = unix_connect(
                str(self.socket_path),
                open_timeout=self._remaining(deadline),
                close_timeout=min(self.timeout, 0.2),
                max_size=4 * 1024 * 1024,
                max_queue=32,
                ping_interval=20,
                ping_timeout=20,
                compression=None,
                proxy=None,
            )
            self._generation = uuid.uuid4().hex
            self._call(
                "initialize",
                {
                    "clientInfo": {"name": "permission_queue", "version": "0.1.0"},
                    "capabilities": {"experimentalApi": True},
                },
                deadline,
            )
            self._ws.send(json.dumps({"method": "initialized"}))
        except (OSError, TimeoutError, WebSocketException) as error:
            self._reset()
            raise _Disconnected(
                f"Could not connect to Codex daemon: {error}"
            ) from error
        except CodexError:
            self._reset()
            raise

    def _receive(self, timeout: float) -> dict:
        if self._ws is None:
            raise _Disconnected("Codex daemon disconnected")
        raw = self._ws.recv(timeout=timeout)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise CodexError("Invalid JSON from Codex daemon") from error
        if not isinstance(value, dict):
            raise CodexError("Invalid daemon message: expected an object")
        return value

    def _occurrence_id(self, request_id: str | int) -> str:
        return f"{self._generation}:{json.dumps(request_id)}"

    def _handle(self, message: dict) -> None:
        method, params = message.get("method"), message.get("params", {})
        if not isinstance(params, dict):
            raise CodexError("Invalid daemon message parameters")
        if method == "serverRequest/resolved":
            request_id = message["params"].get("requestId")
            if type(request_id) not in (int, str):
                raise CodexError("Invalid resolved request identifier")
            occurrence = self._occurrence_id(request_id)
            pending = self._pending.get(occurrence) or self._sent.get(occurrence)
            if pending is not None and pending.thread_id != params.get("threadId"):
                raise CodexError("Resolved request thread does not match")
            self._pending.pop(occurrence, None)
            self._sent.pop(occurrence, None)
            self._resolved[occurrence] = None
            while len(self._resolved) > MAX_MESSAGES:
                del self._resolved[next(iter(self._resolved))]
        elif method and "id" in message:
            request_id, thread_id = message["id"], params.get("threadId")
            if type(request_id) not in (int, str):
                raise CodexError("Invalid server request identifier")
            # Account/tool/time requests outside a thread are never auto-answered.
            if not isinstance(thread_id, str):
                return
            occurrence = self._occurrence_id(request_id)
            if occurrence in self._resolved or occurrence in self._sent:
                return
            request = RequestOccurrence(
                occurrence,
                request_id,
                thread_id,
                params.get("turnId"),
                params.get("itemId"),
                method,
                params,
                timestamp(params.get("startedAtMs"), milliseconds=True),
                decisions_for(method, params),
            )
            previous = self._pending.get(occurrence)
            if previous is not None and previous != request:
                raise CodexError(
                    "Daemon reused a pending request ID with changed details"
                )
            self._pending[occurrence] = request
            if len(self._pending) > MAX_MESSAGES:
                raise CodexError("Too many pending daemon requests")

    def _call(self, method: str, params: dict, deadline: float) -> dict:
        self._sequence += 1
        identifier = self._sequence
        if self._ws is None:
            raise _Disconnected("Codex daemon disconnected")
        try:
            self._ws.send(
                json.dumps({"id": identifier, "method": method, "params": params})
            )
            for _ in range(MAX_MESSAGES):
                message = self._receive(self._remaining(deadline))
                if "method" not in message and message.get("id") == identifier:
                    if "error" in message:
                        raise CodexRpcError(f"{method}: {message['error']}")
                    result = message.get("result")
                    if not isinstance(result, dict):
                        raise CodexError(f"Invalid {method} response")
                    return result
                self._handle(message)
            raise CodexError("Daemon notification limit exceeded")
        except TimeoutError as error:
            self._reset()
            raise CodexError(f"{method} timed out") from error
        except (OSError, ConnectionClosed) as error:
            self._reset()
            raise _Disconnected(f"Codex daemon disconnected during {method}") from error
        except CodexRpcError:
            raise
        except CodexError:
            self._reset()
            raise

    def _read(self, method: str, params: dict, deadline: float) -> dict:
        for attempt in range(2):
            try:
                self._connect(deadline)
                return self._call(method, params, deadline)
            except _Disconnected:
                if attempt:
                    raise
        raise CodexError("Could not read Codex daemon")

    def _loaded(self, deadline: float) -> list[str]:
        threads, cursor = [], None
        for _ in range(16):
            result = self._read(
                "thread/loaded/list", {"limit": 100, "cursor": cursor}, deadline
            )
            data = result.get("data")
            if not isinstance(data, list) or not all(
                isinstance(value, str) for value in data
            ):
                raise CodexError("Invalid loaded thread list")
            threads.extend(data)
            next_cursor = result.get("nextCursor")
            if next_cursor is None:
                return list(dict.fromkeys(threads))
            if not isinstance(next_cursor, str) or next_cursor == cursor:
                raise CodexError("Invalid loaded thread pagination")
            cursor = next_cursor
        raise CodexError("Loaded thread pagination limit exceeded")

    def loaded_threads(self) -> list[str]:
        with self._lock:
            return self._loaded(time.monotonic() + self.snapshot_timeout)

    def _snapshot(self, thread_id: str, deadline: float) -> ThreadSnapshot:
        result = self._read(
            "thread/read", {"threadId": thread_id, "includeTurns": False}, deadline
        )
        thread = result.get("thread")
        if not isinstance(thread, dict) or thread.get("id") != thread_id:
            raise CodexError("Thread identity mismatch in daemon response")
        history_error = ""
        try:
            history = self._read(
                "thread/turns/list",
                {
                    "threadId": thread_id,
                    "limit": 4,
                    "sortDirection": "desc",
                    "itemsView": "full",
                },
                deadline,
            )
            turns = history.get("data")
            if not isinstance(turns, list) or not all(
                isinstance(turn, dict) for turn in turns
            ):
                raise CodexError("Invalid daemon turn history")
        except CodexRpcError as error:
            history_error, turns = str(error), []
        status = thread.get("status", {})
        if not isinstance(status, dict):
            raise CodexError("Invalid daemon thread status")
        flags = status.get("activeFlags", [])
        state = {"idle": "idle", "active": "running"}.get(status.get("type"), "unknown")
        if state == "running" and any(
            flag in flags for flag in ("waitingOnApproval", "waitingOnUserInput")
        ):
            state = "blocked"
        requests = tuple(
            sorted(
                (
                    request
                    for request in self._pending.values()
                    if request.thread_id == thread_id and self._attached == thread_id
                ),
                key=lambda request: -(request.started_at or 0),
            )
        )
        since, provenance = None, ""
        if state == "blocked":
            dates = [
                request.started_at
                for request in requests
                if request.started_at is not None
            ]
            if dates:
                since, provenance = max(dates), "Codex pending request startedAtMs"
        elif turns:
            field = "completedAt" if state == "idle" else "startedAt"
            turn = turns[0]
            if (
                state == "idle"
                and turn.get("status") in ("completed", "interrupted", "failed")
            ) or (state == "running" and turn.get("status") == "inProgress"):
                since = timestamp(turn.get(field))
                provenance = f"Codex turn {turn.get('id', '')} {field}" if since else ""
        source = thread.get("source", "unknown")
        parent = thread.get("parentThreadId")
        if not parent and isinstance(source, dict):
            subagent = source.get("subAgent")
            if isinstance(subagent, dict):
                spawn = subagent.get("thread_spawn", {})
                if isinstance(spawn, dict):
                    parent = spawn.get("parent_thread_id")
        return ThreadSnapshot(
            thread_id,
            thread.get("sessionId", ""),
            thread.get("name") or thread.get("preview", ""),
            thread.get("cwd", ""),
            state,
            since,
            provenance,
            tuple(turns),
            requests,
            history_error,
            parent,
            source,
        )

    def snapshot(self, thread_id: str) -> ThreadSnapshot:
        with self._lock:
            return self._snapshot(thread_id, time.monotonic() + self.snapshot_timeout)

    def select(self, thread_id: str) -> ThreadSnapshot:
        with self._lock:
            deadline = time.monotonic() + self.snapshot_timeout
            self._connect(deadline)
            if self._attached != thread_id:
                if thread_id not in self._loaded(deadline):
                    raise CodexError(
                        "Selected thread is no longer loaded; no resume sent"
                    )
                if self._attached is not None:
                    previous = self._attached
                    self._call("thread/unsubscribe", {"threadId": previous}, deadline)
                    self._attached = None
                    self._pending = {
                        key: request
                        for key, request in self._pending.items()
                        if request.thread_id != previous
                    }
                self._call(
                    "thread/resume",
                    {"threadId": thread_id, "excludeTurns": True},
                    deadline,
                )
                self._attached = thread_id
            return self._snapshot(thread_id, deadline)

    def _drain(self) -> None:
        for _ in range(MAX_MESSAGES):
            try:
                message = self._receive(0)
            except TimeoutError:
                return
            self._handle(message)
        raise CodexError("Daemon notification limit exceeded")

    def answer(self, occurrence_id: str, decision: str) -> AnswerResult:
        with self._lock:
            sent = False
            if occurrence_id not in self._pending or self._ws is None:
                raise CodexError("Request is stale or already resolved")
            try:
                self._drain()
                request = self._pending.get(occurrence_id)
                if request is None or request.thread_id != self._attached:
                    raise CodexError("Request is stale or already resolved")
                if decision not in request.decisions:
                    raise CodexError("Decision was not offered for this request")
                if self._ws is None:
                    raise CodexError("Request is stale after daemon disconnected")
                self._pending.pop(occurrence_id)
                self._sent[occurrence_id] = request
                sent = True
                self._ws.send(
                    json.dumps(
                        {"id": request.request_id, "result": {"decision": decision}}
                    )
                )
                deadline = time.monotonic() + self.timeout
                for _ in range(MAX_MESSAGES):
                    if occurrence_id in self._resolved:
                        return AnswerResult(occurrence_id, "resolved")
                    self._handle(self._receive(self._remaining(deadline)))
                raise CodexError("Daemon notification limit exceeded after answer")
            except (TimeoutError, OSError, ConnectionClosed) as error:
                self._reset()
                raise CodexError(
                    "Answer outcome unknown; connection ended or timed out. "
                    "Do not retry."
                ) from error
            except CodexError as error:
                if sent:
                    self._reset()
                    raise CodexError(
                        "Answer outcome unknown; no resolution confirmed. Do not retry."
                    ) from error
                raise

    def close(self) -> None:
        with self._lock:
            self._reset()

    def __enter__(self) -> CodexServer:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
