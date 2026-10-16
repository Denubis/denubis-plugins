"""Read Codex pane state; historical-time correlations never authorize actions."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
MODEL = re.compile(r"^(?:GPT-|gpt-|o[0-9])")
TAIL_LIMIT = 1024 * 1024


@dataclass(frozen=True)
class PaneState:
    state: str
    since: float | None
    source: str
    approximate: bool = False


@lru_cache(maxsize=1)
def policy():
    path = (
        Path(__file__).resolve().parents[2]
        / "plugins/denubis-external-agents/scripts/codex_supervisor.py"
    )
    spec = importlib.util.spec_from_file_location("permission_codex_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Codex native state classifier is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def timestamp(value: object) -> float | None:
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 < value <= time.time()
    ):
        return None
    return float(value)


def title_parts(title: str) -> list[str]:
    parts = title.split(" | ")
    # The optional configured activity spinner is its own leading segment.
    if len(parts) > 1 and parts[0] in policy().BUSY_SPINNERS:
        parts = parts[1:]
    return parts


def native_state(data: dict, preview: str) -> str:
    if data.get("pane_current_command") != "codex":
        return "unknown"
    lead = title_parts(data.get("pane_title", ""))[0]
    lead = re.sub(r"^\[\s*!\s*\]\s*", "", lead)
    normalized = re.sub(r"\s", "", lead).casefold()
    if normalized not in {
        "ready",
        "working",
        "thinking",
        "waiting",
        "starting",
        "actionrequired",
    }:
        return "unknown"
    observed = policy().classify_snapshot(
        "Action Required" if normalized == "actionrequired" else lead,
        CSI.sub("", preview),
    )
    if (
        normalized == "actionrequired"
        or observed.kind == policy().ObservationKind.APPROVAL
    ):
        return "blocked"
    if observed.kind == policy().ObservationKind.CRASH:
        return "unknown"
    return "idle" if normalized == "ready" else "running"


def rollout_time(path: Path, state: str) -> float | None:
    """Read only a stable bounded tail and the most recent native turn transition."""
    try:
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            offset = max(0, before.st_size - TAIL_LIMIT)
            stream.seek(offset)
            raw = stream.read(TAIL_LIMIT)
            after = os.fstat(stream.fileno())
    except OSError:
        return None
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        return None
    if not raw.endswith(b"\n"):
        return None
    if offset:
        raw = raw.partition(b"\n")[2]
    latest = None
    for line in raw.splitlines():
        try:
            record = json.loads(line)
        except ValueError, UnicodeError:
            continue
        if not isinstance(record, dict) or record.get("type") != "event_msg":
            continue
        payload = record.get("payload")
        if isinstance(payload, dict) and payload.get("type") in {
            "task_started",
            "task_complete",
            "turn_aborted",
        }:
            latest = payload
    if latest is None:
        return None
    active = latest["type"] == "task_started"
    if (state == "running" and active) or (state == "idle" and not active):
        return timestamp(latest.get("started_at" if active else "completed_at"))
    return None


def owned_time(foreground_pid: int | None, state: str) -> tuple[float | None, str]:
    if foreground_pid is None or state not in {"idle", "running"}:
        return None, ""
    held = policy().held_sessions(foreground_pid)
    path = policy()._main_rollout(held) if held is not None else None
    if path is None:
        return None, ""
    since = rollout_time(path, state)
    held = policy().held_sessions(foreground_pid)
    current = policy()._main_rollout(held) if held is not None else None
    if current != path:
        return None, ""
    return since, f"Codex process-owned main rollout {path.name}" if since else ""


def canonical_cwd(value: str) -> str | None:
    if not value or not Path(value).is_absolute():
        return None
    try:
        return str(Path(value).resolve())
    except OSError, RuntimeError, ValueError:
        return None


def correlated_time(data: dict, threads, state: str) -> tuple[float | None, str]:
    title = data.get("pane_title", "")
    parts = title_parts(title)
    # The observed current preset is state | project | branch | thread | model.
    # Hidden/extra fields, unescaped delimiters and either title cap fail closed.
    if len(parts) != 5 or len(title) >= 240 or MODEL.match(parts[-1]) is None:
        return None, ""
    task = parts[-2]
    if not task or len(task) > 48 or "|" in task or task.endswith(("...", "…")):
        return None, ""
    cwd = canonical_cwd(data.get("pane_current_path", ""))
    if cwd is None:
        return None, ""
    values = threads.values() if isinstance(threads, Mapping) else threads
    matches = [
        thread
        for thread in values
        if not getattr(thread, "parent_thread_id", None)
        and getattr(thread, "title", "") == task
        and "|" not in getattr(thread, "title", "")
        and canonical_cwd(getattr(thread, "cwd", "")) == cwd
    ]
    if len(matches) != 1 or matches[0].state != state:
        return None, ""
    thread = matches[0]
    since = timestamp(thread.state_since)
    source = (
        f"Display-only correlation to Codex thread {thread.thread_id}; "
        f"exact cwd and complete task title; {thread.state_since_source}"
    )
    return since, source if since else ""


def observe(data: dict, preview: str, threads, foreground_pid: int | None) -> PaneState:
    state = native_state(data, preview)
    since, source = owned_time(foreground_pid, state)
    if since is not None:
        return PaneState(state, since, source)
    if state in {"idle", "running"}:
        since, source = correlated_time(data, threads, state)
        if since is not None:
            return PaneState(state, since, source, approximate=True)
    return PaneState(state, None, "Native Codex pane; transition time unavailable")
