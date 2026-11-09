"""Hook enrollment and the independent watcher process lifecycle."""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .core import ThreadState, check_thread
from .reviewer import TerraReviewer
from .store import StateStore
from .transport import CodexBackend, ProtocolError, Proxy


def endpoint() -> str:
    override = os.environ.get("CARRY_ON_SOCKET")
    if override:
        return override
    result = subprocess.run(
        ["codex", "app-server", "daemon", "version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode:
        raise RuntimeError("Codex daemon is unavailable: " + result.stderr.strip())
    info = json.loads(result.stdout)
    socket = info.get("socketPath")
    if not isinstance(socket, str) or not socket:
        raise RuntimeError("Codex daemon version did not report its control socket")
    return socket


def data_root() -> Path:
    value = os.environ.get("PLUGIN_DATA")
    if not value:
        raise RuntimeError("PLUGIN_DATA is required for carry-on state")
    return Path(value)


def spawn_watch(store: StateStore, socket: str) -> None:
    if (store.root / "disabled").exists():
        return
    entry = Path(__file__).resolve().parents[1] / "carry-on.py"
    with (store.root / "watcher.log").open("ab") as log:
        subprocess.Popen(
            [sys.executable, str(entry), "--watch", "--socket", socket],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
            close_fds=True,
        )


def check_sessions(
    store: StateStore,
    sessions: dict[str, ThreadState],
    backend: CodexBackend,
    reviewer: TerraReviewer,
) -> None:
    for state in sessions.values():
        if state.ended or (store.root / "disabled").exists():
            continue
        outcome = check_thread(
            state,
            backend,
            reviewer,
            now=time.time(),
            still_current=lambda current: (
                store.current(current) and not (store.root / "disabled").exists()
            ),
            reserve=store.reserve,
        )
        if outcome != state.last_outcome and outcome not in {
            "inactive",
            "unchanged",
            "workers_running",
            "retry_limited",
        }:
            print(
                json.dumps(
                    {
                        "thread": state.thread_id,
                        "outcome": outcome,
                        "error": state.last_error,
                    }
                ),
                flush=True,
            )
        state.last_outcome = outcome
        store.save_if_current(state)


def watch(store: StateStore, socket: str) -> None:
    with (store.root / "watcher.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        (store.root / "watcher.pid").write_text(str(os.getpid()))
        proxy = None
        backend = None
        failures = 0
        try:
            while not (store.root / "disabled").exists():
                sessions = store.sessions()
                if not any(not state.ended for state in sessions.values()):
                    return
                try:
                    if proxy is None:
                        proxy = Proxy(socket)
                        backend = CodexBackend(proxy)
                    if backend is None:
                        raise ProtocolError("daemon backend was not initialized")
                    check_sessions(store, sessions, backend, TerraReviewer(proxy))
                    failures = 0
                except (ProtocolError, OSError) as error:
                    failures += 1
                    print(f"carry-on: daemon error ({failures}/3): {error}", flush=True)
                    if proxy is not None:
                        proxy.close()
                        proxy = None
                    if failures >= 3:
                        return
                time.sleep(5)
        finally:
            if proxy is not None:
                proxy.close()
            (store.root / "watcher.pid").unlink(missing_ok=True)


def read_hook_payload(payload: dict | None = None) -> dict:
    if payload is None:
        payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("hook input must be a JSON object")
    return payload


def hook(store: StateStore, event: str, payload: dict | None = None) -> None:
    if (store.root / "disabled").exists():
        return
    payload = read_hook_payload(payload)
    if payload.get("agent_id") and event in {
        "SessionStart",
        "Stop",
        "UserPromptSubmit",
    }:
        return
    if event == "UserPromptSubmit":
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return
    thread_id = payload.get("session_id")
    cwd = payload.get("cwd")
    if not isinstance(thread_id, str) or not isinstance(cwd, str):
        raise ValueError("hook input is missing session_id or cwd")
    store.signal(thread_id, cwd, event)


def cleanup_hook(root: Path, event: str, payload: dict) -> None:
    """Persist root pause/end signals without discovering or contacting a daemon."""
    if payload.get("agent_id"):
        return
    thread_id, cwd = payload.get("session_id"), payload.get("cwd")
    if not isinstance(thread_id, str) or not isinstance(cwd, str):
        raise ValueError("hook input is missing session_id or cwd")
    for path in root.glob("*/state.json"):
        directory = path.parent
        if directory.is_symlink() or path.is_symlink():
            continue
        if len(directory.name) != 16 or any(
            c not in "0123456789abcdef" for c in directory.name
        ):
            continue
        store = StateStore(directory, None)
        if thread_id in store.sessions():
            store.signal(thread_id, cwd, event)


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex continuation watcher controls")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--event",
        choices=[
            "SessionStart",
            "Stop",
            "SubagentStop",
            "Interrupt",
            "SessionEnd",
            "UserPromptSubmit",
        ],
    )
    mode.add_argument("--watch", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--stop", action="store_true")
    mode.add_argument("--start", action="store_true")
    parser.add_argument("--socket")
    args = parser.parse_args()
    hook_mode = args.event is not None or not any(
        [args.watch, args.status, args.stop, args.start]
    )
    try:
        payload = None
        if hook_mode and args.event is None:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict):
                raise ValueError("hook input must be a JSON object")
            args.event = payload.get("hook_event_name")
            if args.event not in {
                "SessionStart",
                "Stop",
                "SubagentStop",
                "Interrupt",
                "SessionEnd",
                "UserPromptSubmit",
            }:
                raise ValueError("hook input has an unsupported hook_event_name")
        if hook_mode and args.event in {"Interrupt", "SessionEnd"}:
            cleanup_hook(data_root(), args.event, read_hook_payload(payload))
            return 0
        socket = args.socket or endpoint()
        store = StateStore(data_root(), socket)
        if args.watch:
            watch(store, socket)
        elif args.stop:
            (store.root / "disabled").touch()
            print("carry-on disabled; watcher exits after its current bounded check")
        elif args.status:
            pid = store.root / "watcher.pid"
            print(
                json.dumps(
                    {
                        "disabled": (store.root / "disabled").exists(),
                        "watcher_pid": pid.read_text().strip()
                        if pid.exists()
                        else None,
                        "state_directory": str(store.root),
                        "sessions": {
                            key: asdict(value)
                            for key, value in store.sessions().items()
                        },
                    },
                    indent=2,
                )
            )
        else:
            if args.start:
                (store.root / "disabled").unlink(missing_ok=True)
            else:
                hook(store, args.event, payload)
            spawn_watch(store, socket)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"carry-on: {error}", file=sys.stderr)
        return 0 if hook_mode else 1
    return 0
