"""Launch the attention view or fixture board detached on the current tmux server."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

OWNER_OPTION = "@permission-queue-launcher"
OWNER = "permission-queue-experiment-v1"
VIEW_OPTION = "@permission-queue-view"


def tmux(prefix: list[str], *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*prefix, *arguments], capture_output=True, text=True, timeout=5, check=False
    )


def switch_if_attached(
    prefix: list[str], client: str, session_name: str, *arguments: str
) -> subprocess.CompletedProcess[str]:
    # Evaluate attachment and switch in one server command. A client that leaves
    # while the board closes must not be moved by an earlier list snapshot.
    attached = (
        "#{L:#{?#{&&:#{==:#{client_name},"
        + client
        + "},#{==:#{client_session},"
        + session_name
        + "}},1,}}"
    )
    return tmux(
        prefix,
        "if-shell",
        "-F",
        attached,
        shlex.join(["switch-client", "-c", client, *arguments]),
    )


def serve(prefix: list[str], args: argparse.Namespace) -> int:
    pane = os.environ.get("TMUX_PANE")
    if pane is None:
        print(
            "permission-queue: the board runner requires its owned tmux pane",
            file=sys.stderr,
        )
        return 1
    identity = tmux(
        prefix, "display-message", "-p", "-t", pane, "#{session_id}\t#{session_name}"
    )
    if identity.returncode:
        print(identity.stderr.strip(), file=sys.stderr)
        return identity.returncode
    session_id, session_name = identity.stdout.strip().split("\t")
    command = [
        sys.executable,
        "-P",
        str(Path(__file__).with_name("board.py")),
    ]
    if args.watch_session:
        command += ["--watch-session", args.watch_session]
        if args.socket:
            command += ["--socket", str(args.socket.resolve())]
    else:
        command += ["--demo"]
    if args.run_dir and not args.watch_session:
        command += ["--run-dir", str(args.run_dir.resolve())]
    try:
        outcome = subprocess.run(command, check=False).returncode
    finally:
        clients = tmux(prefix, "list-clients", "-t", session_id, "-F", "#{client_name}")
        for client in clients.stdout.splitlines():
            returned = switch_if_attached(prefix, client, session_name, "-l")
            if returned.returncode and args.return_session:
                switch_if_attached(
                    prefix, client, session_name, "-t", f"={args.return_session}"
                )
    return outcome


def launch(prefix: list[str], args: argparse.Namespace) -> int:
    target = f"={args.session}"
    view = f"watch:{args.watch_session}" if args.watch_session else "demo"
    if tmux(prefix, "has-session", "-t", target).returncode == 0:
        marker = tmux(prefix, "show-options", "-qv", "-t", args.session, OWNER_OPTION)
        if marker.stdout.strip() != OWNER:
            print(
                f"permission-queue: session {args.session} already exists "
                "and is not owned by this launcher; leaving it unchanged",
                file=sys.stderr,
            )
            return 1
        existing_view = tmux(
            prefix, "show-options", "-qv", "-t", args.session, VIEW_OPTION
        )
        if existing_view.stdout.strip() != view:
            print(
                "permission-queue: a different view is already running; "
                "close that view before relaunching",
                file=sys.stderr,
            )
            return 1
        print(f"View already running: {args.session}")
        return 0
    command = [
        sys.executable,
        "-P",
        str(Path(__file__).resolve()),
        "--serve",
        "--session",
        args.session,
    ]
    if args.socket:
        command += ["--socket", str(args.socket.resolve())]
    if args.run_dir:
        command += ["--run-dir", str(args.run_dir.resolve())]
    if args.return_session:
        command += ["--return-session", args.return_session]
    if args.watch_session:
        command += ["--watch-session", args.watch_session]
    started = tmux(
        prefix,
        "new-session",
        "-d",
        "-s",
        args.session,
        "exec " + shlex.join(command),
        ";",
        "set-option",
        "-t",
        args.session,
        OWNER_OPTION,
        OWNER,
        ";",
        "set-option",
        "-t",
        args.session,
        VIEW_OPTION,
        view,
        ";",
        "set-option",
        "-t",
        args.session,
        "detach-on-destroy",
        "off",
        ";",
        "set-window-option",
        "-t",
        args.session,
        "remain-on-exit",
        "off",
    )
    if started.returncode:
        print(started.stderr.strip(), file=sys.stderr)
    else:
        print(f"View ready: {args.session}; your current session stays selected")
    return started.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--return-session")
    parser.add_argument("--watch-session")
    parser.add_argument("--session", default="permission-queue-demo")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if re.fullmatch(r"[A-Za-z0-9_-]+", args.session) is None:
        parser.error(
            "--session must contain only letters, digits, underscores, or hyphens"
        )
    prefix = ["tmux"] + (["-S", str(args.socket.resolve())] if args.socket else [])
    try:
        return serve(prefix, args) if args.serve else launch(prefix, args)
    except OSError as error:
        print(f"permission-queue: {error}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired as error:
        print(f"permission-queue: tmux did not respond: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
