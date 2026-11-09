"""One locked, atomic enrollment record per app-server endpoint."""

import fcntl
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from .core import ThreadState, digest


class StateStore:
    def __init__(self, data_root: Path, endpoint: str | None):
        # None opens an already-derived endpoint directory for local cleanup signals.
        self.root = data_root if endpoint is None else data_root / digest(endpoint)[:16]
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "state.json"

    def _read(self) -> dict[str, ThreadState]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text())
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("unsupported carry-on state format")
        sessions = data.get("sessions")
        if not isinstance(sessions, dict):
            raise ValueError("invalid carry-on enrollment records")
        result = {}
        for key, value in sessions.items():
            if not isinstance(value, dict) or value.get("thread_id") != key:
                raise ValueError("invalid carry-on thread record")
            result[key] = ThreadState(**value)
        return result

    def transaction(self, update: Callable[[dict[str, ThreadState]], None]) -> None:
        with (self.root / "state.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            sessions = self._read()
            update(sessions)
            data = {
                "version": 1,
                "sessions": {k: asdict(v) for k, v in sessions.items()},
            }
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", dir=self.root, delete=False
                ) as out:
                    temporary = Path(out.name)
                    json.dump(data, out)
                    out.flush()
                    os.fsync(out.fileno())
                temporary.replace(self.path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)

    def sessions(self) -> dict[str, ThreadState]:
        with (self.root / "state.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            return self._read()

    def signal(self, thread_id: str, cwd: str, event: str) -> None:
        def update(sessions: dict[str, ThreadState]) -> None:
            if thread_id not in sessions:
                if event not in {"SessionStart", "Stop"}:
                    return
                sessions[thread_id] = ThreadState(thread_id, cwd)
            state = sessions[thread_id]
            state.generation += 1
            if event == "Interrupt":
                state.paused = True
            elif event == "UserPromptSubmit":
                state.paused = False
                state.stalls = 0
            elif event == "SessionEnd":
                state.ended = True
            elif event == "SessionStart":
                state.ended = False
                state.cwd = cwd
            elif event == "Stop":
                state.signal = "stop"
            elif event == "SubagentStop":
                state.signal = "workers_done"

        self.transaction(update)

    def current(self, state: ThreadState) -> bool:
        latest = self.sessions().get(state.thread_id)
        return latest is not None and latest.generation == state.generation

    def save_if_current(self, state: ThreadState) -> None:
        self.reserve(state)

    def reserve(self, state: ThreadState) -> bool:
        saved = False

        def update(sessions: dict[str, ThreadState]) -> None:
            nonlocal saved
            latest = sessions.get(state.thread_id)
            if latest is not None and latest.generation == state.generation:
                sessions[state.thread_id] = state
                saved = True

        self.transaction(update)
        return saved
