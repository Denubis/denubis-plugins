"""Bounded PermissionRequest experiment; no live hook registration or pane input."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

ACTIVE = {"pending", "decided"}
OBSERVATIONS = ("pane-denied", "pane-allowed", "command-observed", "operator-note")


class QueueError(Exception):
    """The fixture operation could not safely proceed."""


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def locked(run_dir: Path, deadline: float | None = None):
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    (run_dir / "requests").mkdir(exist_ok=True, mode=0o700)
    (run_dir / "live").mkdir(exist_ok=True, mode=0o700)
    deadline = time.monotonic() + 3 if deadline is None else deadline
    with (run_dir / ".lock").open("a") as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise QueueError("fixture state lock remained busy") from None
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def request_path(run_dir: Path, request_id: str) -> Path:
    try:
        canonical = str(uuid.UUID(request_id))
    except ValueError:
        raise QueueError("--request must be a complete UUID") from None
    return run_dir / "requests" / f"{canonical}.json"


def read_request(run_dir: Path, request_id: str) -> dict:
    path = request_path(run_dir, request_id)
    if not path.is_file():
        raise QueueError(f"unknown request {request_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_request(run_dir: Path, request: dict) -> None:
    path = request_path(run_dir, request["request_id"])
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        json.dump(request, temporary, ensure_ascii=True, indent=2)
        temporary.write("\n")
    temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def record_event(run_dir: Path, request_id: str, event: str, **details: object) -> None:
    entry = {
        "at": timestamp(),
        "monotonic_s": time.monotonic(),
        "pid": os.getpid(),
        "request_id": request_id,
        "event": event,
        **details,
    }
    with (run_dir / "evidence.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=True) + "\n")


def hook_alive(run_dir: Path, request_id: str) -> bool:
    # The hook holds this OS lock throughout its life. A kill releases it without
    # relying on a recyclable PID or on a process that merely looks like a hook.
    with (run_dir / "live" / f"{request_id}.lock").open("a") as live:
        try:
            fcntl.flock(live, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(live, fcntl.LOCK_UN)
        return False


def refresh(run_dir: Path, request: dict) -> dict:
    if request["state"] not in ACTIVE:
        return request
    state = None
    if time.monotonic() >= request["expires_monotonic_s"]:
        state = "expired"
    elif not hook_alive(run_dir, request["request_id"]):
        state = "unknown"
    if state is not None:
        request["state"] = state
        request["closed_at"] = timestamp()
        write_request(run_dir, request)
        record_event(run_dir, request["request_id"], state)
    return request


def hook(run_dir: Path, vendor: str, vendor_version: str, hold: float) -> int:
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise QueueError("hook input must be a JSON object")
    if payload.get("hook_event_name") != "PermissionRequest":
        raise QueueError("only PermissionRequest is supported")
    if not isinstance(payload.get("tool_name"), str) or not payload["tool_name"]:
        raise QueueError("tool_name must be a nonempty string")
    if not isinstance(payload.get("tool_input"), dict):
        raise QueueError("tool_input must be a JSON object")
    request_id = str(uuid.uuid4())
    started = time.monotonic()
    deadline = started + hold
    request = {
        "request_id": request_id,
        "vendor": vendor,
        "vendor_version": vendor_version,
        "session_id": payload.get("session_id"),
        "cwd": payload.get("cwd"),
        "tool_name": payload["tool_name"],
        "tool_input": payload["tool_input"],
        "payload": payload,
        "pane": os.environ.get("TMUX_PANE"),
        "hook_pid": os.getpid(),
        "opened_at": timestamp(),
        "opened_monotonic_s": started,
        "expires_monotonic_s": deadline,
        "hold_seconds": hold,
        "state": "pending",
        "decision": None,
    }
    with locked(run_dir, deadline):
        live = (run_dir / "live" / f"{request_id}.lock").open("a")
        fcntl.flock(live, fcntl.LOCK_EX)
        write_request(run_dir, request)
        record_event(run_dir, request_id, "hook_opened", request=request)
    with live:
        while True:
            with locked(run_dir, deadline):
                request = refresh(run_dir, read_request(run_dir, request_id))
                if request["state"] not in ACTIVE:
                    return 0
                if request["state"] == "decided":
                    choice = request["decision"]
                    decision = {"behavior": choice["behavior"]}
                    if choice["behavior"] == "deny":
                        decision["message"] = choice["reason"]
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "PermissionRequest",
                            "decision": decision,
                        }
                    }
                    print(json.dumps(output), flush=True)
                    request["state"] = "returned"
                    request["closed_at"] = timestamp()
                    write_request(run_dir, request)
                    record_event(
                        run_dir, request_id, "hook_stdout_written", output=output
                    )
                    return 0
            time.sleep(min(0.025, max(0, deadline - time.monotonic())))


def list_requests(run_dir: Path) -> list[dict]:
    if not run_dir.exists():
        return []
    with locked(run_dir):
        return [
            refresh(run_dir, json.loads(path.read_text(encoding="utf-8")))
            for path in sorted((run_dir / "requests").glob("*.json"))
        ]


def change_request(run_dir: Path, args: argparse.Namespace) -> None:
    with locked(run_dir):
        request = refresh(run_dir, read_request(run_dir, args.request))
        request_id = request["request_id"]
        if args.command == "note":
            record_event(run_dir, request_id, args.event, detail=args.detail)
            print(json.dumps({"request_id": request_id, "observation": args.event}))
            return
        if request["state"] != "pending":
            record_event(run_dir, request_id, "answer_refused", state=request["state"])
            raise QueueError(
                f"request {request_id} is {request['state']}; answer refused"
            )
        if args.command == "decide":
            request["decision"] = {
                "behavior": args.decision,
                "reason": args.reason,
                "at": timestamp(),
            }
            request["state"] = "decided"
            event = "decision_accepted"
        else:
            request["state"] = "retired"
            request["closed_at"] = timestamp()
            event = "operator_retired"
        write_request(run_dir, request)
        record_event(run_dir, request_id, event, reason=args.reason)
        print(json.dumps({"request_id": request_id, "state": request["state"]}))


def bounded_hold(value: str) -> float:
    hold = float(value)
    if not math.isfinite(hold) or not 0 < hold <= 600:
        raise argparse.ArgumentTypeError(
            "hold must be finite and between 0 and 600 seconds"
        )
    return hold


def nonempty(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("a nonempty explanation is required")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subcommands = result.add_subparsers(dest="command", required=True)
    for name in ("hook", "list", "decide", "retire", "note"):
        command = subcommands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
        if name == "hook":
            command.add_argument("--vendor", choices=("claude", "codex"), required=True)
            command.add_argument("--vendor-version", default="unknown")
            command.add_argument("--hold-seconds", type=bounded_hold, default=45)
        elif name == "list":
            command.add_argument("--json", action="store_true")
        else:
            command.add_argument("--request", required=True)
            if name == "note":
                command.add_argument("--event", choices=OBSERVATIONS, required=True)
                command.add_argument("--detail", type=nonempty, required=True)
            else:
                command.add_argument("--reason", type=nonempty, required=True)
                if name == "decide":
                    command.add_argument(
                        "--decision", choices=("allow", "deny"), required=True
                    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "hook":
            return hook(
                args.run_dir, args.vendor, args.vendor_version, args.hold_seconds
            )
        if args.command == "list":
            found = list_requests(args.run_dir)
            if args.json:
                print(json.dumps(found, ensure_ascii=True))
            else:
                for request in found:
                    print(f"REQUEST {request['request_id']} [{request['state']}]")
                    print(json.dumps(request, ensure_ascii=True, indent=2))
            return 0
        change_request(args.run_dir, args)
        return 0
    except QueueError as error:
        print(f"permission-queue: {error}", file=sys.stderr)
    except OSError as error:
        print(f"permission-queue: {error}", file=sys.stderr)
    except json.JSONDecodeError as error:
        print(f"permission-queue: invalid fixture JSON: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
