"""Bounded JSON-RPC connection to the already-running local Codex daemon."""

import json
import time
from collections import deque
from typing import Any

from websockets.exceptions import WebSocketException
from websockets.sync.client import unix_connect

from .core import Unavailable


class Proxy:
    def __init__(self, endpoint: str, deadline: float):
        self.deadline = deadline
        self.sequence = 0
        self.thread_id: str | None = None
        self.events: deque[dict[str, Any]] = deque()
        try:
            self.socket = unix_connect(
                endpoint,
                uri="ws://localhost/",
                open_timeout=min(10, self.remaining()),
                close_timeout=1,
                max_size=4 * 1024 * 1024,
            )
        except (OSError, TimeoutError, WebSocketException) as error:
            raise Unavailable(f"cannot connect to Codex daemon: {error}") from error
        try:
            self.request(
                "initialize",
                {
                    "clientInfo": {"name": "denubis_question_zone", "version": "0.2.2"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            self.send({"method": "initialized"})
        except Unavailable:
            self.close()
            raise

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Unavailable("question check exceeded its deadline")
        return remaining

    def send(self, message: dict[str, Any]) -> None:
        try:
            self.socket.send(json.dumps(message))
        except (OSError, WebSocketException) as error:
            raise Unavailable(f"cannot send app-server request: {error}") from error

    def receive(self) -> dict[str, Any]:
        try:
            message = json.loads(self.socket.recv(timeout=self.remaining()))
        except (OSError, TimeoutError, WebSocketException, ValueError) as error:
            raise Unavailable(f"app-server response unavailable: {error}") from error
        if not isinstance(message, dict):
            raise Unavailable("app-server returned a non-object message")
        return message

    def route(self, message: dict[str, Any]) -> None:
        params = message.get("params", {})
        if not isinstance(params, dict) or params.get("threadId") != self.thread_id:
            return
        if "id" in message:
            command = params.get("command")
            asked = f" for {command}" if isinstance(command, str) and command else ""
            raise Unavailable(
                f"The searcher asked for permission or user input{asked}, which the "
                "adapter never grants; run that search with normal approval."
            )
        if message.get("method") in {"item/completed", "turn/completed"}:
            self.events.append(message)

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        while True:
            message = self.receive()
            if message.get("id") != request_id or "method" in message:
                self.route(message)
                continue
            if "error" in message:
                raise Unavailable(f"{method}: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise Unavailable(f"{method}: expected an object result")
            return result

    def close(self) -> None:
        self.socket.close()
