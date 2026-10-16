"""Read Claude's native per-process session state without changing a session."""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

REGISTRY_LIMIT = 512
RECORD_LIMIT = 256 * 1024
HUMAN_WAITS = frozenset(
    {
        "permission prompt",
        "input needed",
        "dialog open",
        "sandbox request",
        "worker request",
        "goal proposal",
    }
)


class PaneIdentity(Protocol):
    session_name: str
    window_id: str
    pane_id: str
    foreground_pid: int | None
    foreground_start_ticks: int | None


@dataclass(frozen=True)
class ClaudePaneState:
    session_id: str
    state: str
    state_since: float | None
    state_since_source: str
    status_detail: str
    approximate: bool = False


class ClaudeState:
    """Observe installed Claude 2.1.301's native session registry.

    The registry's statusUpdatedAt is a native status/reason update, not a
    transcript mtime. A change of waiting reason can reset it while still
    blocked, so its age is a lower bound on time in the displayed state.
    Missing identity or ambiguous owners remain unavailable; no hook is added.
    """

    def __init__(
        self,
        claude_home: Path | None = None,
        *,
        proc_root: Path = Path("/proc"),
        machine_id_path: Path = Path("/etc/machine-id"),
    ) -> None:
        configured = os.environ.get("CLAUDE_CONFIG_DIR")
        self.claude_home = claude_home or (
            Path(configured).expanduser() if configured else Path.home() / ".claude"
        )
        self.proc_root = proc_root
        self.machine_id_path = machine_id_path

    def process(self, pid: int) -> tuple[str, int] | None:
        try:
            fields = (
                (self.proc_root / str(pid) / "stat")
                .read_text()
                .rsplit(")", 1)[1]
                .split()
            )
            if fields[0] in {"Z", "X"}:
                return None
            return fields[19], int(fields[2])
        except OSError, ValueError, IndexError:
            return None

    def domain(self) -> str | None:
        try:
            machine = self.machine_id_path.read_text().strip()
            namespace = (self.proc_root / "self/ns/pid").readlink()
            return f"linux:{machine}:{namespace}" if machine else None
        except OSError:
            return None

    @staticmethod
    def record(path: Path) -> dict | None:
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    return None
                data = stream.read(RECORD_LIMIT + 1)
            if len(data) > RECORD_LIMIT:
                return None
            value = json.loads(data)
            return value if isinstance(value, dict) else None
        except OSError, ValueError:
            return None

    def candidate(
        self, path: Path, pane: PaneIdentity, domain: str
    ) -> tuple[int, tuple[str, int], dict] | None:
        pid = int(path.stem)
        record = self.record(path)
        process = self.process(pid)
        locator = f"{pane.session_name}:{pane.window_id}.{pane.pane_id}"
        if (
            record is None
            or process is None
            or process[1] != pane.foreground_pid
            or type(record.get("pid")) is not int
            or record["pid"] != pid
            or record.get("procStart") != process[0]
            or record.get("pidDomain") != domain
            or record.get("kind") != "interactive"
            or record.get("tmux") != locator
            or not isinstance(record.get("sessionId"), str)
            or not record["sessionId"]
        ):
            return None
        return pid, process, record

    def for_pane(self, pane: PaneIdentity) -> ClaudePaneState | None:
        if pane.foreground_pid is None or pane.foreground_start_ticks is None:
            return None
        foreground = self.process(pane.foreground_pid)
        if foreground is None or foreground[0] != str(pane.foreground_start_ticks):
            return None
        domain, paths = self.domain(), self.registry_paths()
        if domain is None or paths is None:
            return None
        matches = [
            candidate
            for path in paths
            if (candidate := self.candidate(path, pane, domain)) is not None
        ]
        if len(matches) != 1:
            return None
        pid, process, record = matches[0]
        if (
            self.process(pid) != process
            or self.process(pane.foreground_pid) != foreground
        ):
            return None
        return observed_state(record)

    def registry_paths(self) -> list[Path] | None:
        try:
            paths = []
            for path in (self.claude_home / "sessions").iterdir():
                if (
                    path.suffix == ".json"
                    and path.stem.isascii()
                    and path.stem.isdecimal()
                ):
                    paths.append(path)
                    if len(paths) > REGISTRY_LIMIT:
                        return None
        except OSError:
            return None
        return paths


def state_timestamp(record: dict) -> float | None:
    updated = record.get("statusUpdatedAt")
    started = record.get("startedAt")
    if (
        type(updated) not in {int, float}
        or type(started) not in {int, float}
        or not 0 < started <= updated <= time.time() * 1000
    ):
        return None
    return updated / 1000


def observed_state(record: dict) -> ClaudePaneState:
    raw = record.get("status")
    native = raw if isinstance(raw, str) else "unrecognized"
    reason = record.get("waitingFor")
    state = {"busy": "running", "shell": "running", "idle": "idle"}.get(
        native, "unknown"
    )
    if native == "waiting" and isinstance(reason, str) and reason in HUMAN_WAITS:
        state = "blocked"
    since = state_timestamp(record) if state != "unknown" else None
    detail = f"Claude native {native}"
    if native == "shell":
        detail += "; background shell task still active"
    if isinstance(reason, str):
        detail += f"; {reason}"
    if since is not None:
        detail += "; age is since the last native status/reason update"
    return ClaudePaneState(
        session_id=record["sessionId"],
        state=state,
        state_since=since,
        state_since_source=(
            "Claude native session registry statusUpdatedAt"
            if since is not None
            else ""
        ),
        status_detail=detail,
        approximate=since is not None,
    )
