"""Open an independent terminal client for the native attention viewer."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


class ViewError(RuntimeError):
    """The requested terminal or existing source server is unavailable."""


def source_socket(explicit: Path | None, session: str) -> Path:
    socket = explicit
    inherited = os.environ.get("TMUX")
    if socket is None and inherited:
        parts = inherited.rsplit(",", 2)
        if len(parts) != 3:
            raise ViewError(
                "the current TMUX socket identity is malformed; use --socket"
            )
        socket = Path(parts[0])
    prefix = ["tmux"] + (["-S", str(socket.resolve())] if socket else [])
    existing = subprocess.run(
        [*prefix, "has-session", "-t", f"={session}"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if existing.returncode:
        detail = existing.stderr.strip()
        raise ViewError(f"source tmux session {session!r} is unavailable: {detail}")
    resolved = subprocess.run(
        [*prefix, "display-message", "-p", "#{socket_path}"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if resolved.returncode or not resolved.stdout.strip():
        raise ViewError(resolved.stderr.strip() or "tmux did not identify its socket")
    return Path(resolved.stdout.strip()).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ghostty", action="store_true", help="open a new local Ghostty"
    )
    parser.add_argument("--watch-session", default="main")
    parser.add_argument("--session", help="reuse an explicitly named owned viewer")
    parser.add_argument("--socket", type=Path)
    args = parser.parse_args(argv)
    if args.session and re.fullmatch(r"[A-Za-z0-9_-]+", args.session) is None:
        parser.error(
            "--session must contain only letters, digits, underscores, or hyphens"
        )
    try:
        ghostty = shutil.which("ghostty") if args.ghostty else None
        if args.ghostty and ghostty is None:
            raise ViewError(
                "ghostty is not on PATH; use this helper in an existing terminal"
            )
        socket = source_socket(args.socket, args.watch_session)
        session = args.session or "permission-queue-view-" + uuid.uuid4().hex
        environment = dict(os.environ)
        environment.pop("TMUX", None)
        environment.pop("TMUX_PANE", None)
        options = [
            "--socket",
            str(socket),
            "--watch-session",
            args.watch_session,
            "--session",
            session,
        ]
        if ghostty:
            subprocess.Popen(
                [
                    ghostty,
                    "--gtk-single-instance=false",
                    "-e",
                    sys.executable,
                    "-P",
                    str(Path(__file__).resolve()),
                    *options,
                ],
                env=environment,
                start_new_session=True,
            )
            print(f"Opened viewer {session} in a new Ghostty")
            return 0
        launched = subprocess.run(
            [
                sys.executable,
                "-P",
                str(Path(__file__).with_name("launch.py")),
                *options,
                "--return-session",
                args.watch_session,
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if launched.returncode:
            raise ViewError(launched.stderr.strip() or launched.stdout.strip())
        # Replace this helper with the terminal client; arguments never enter a shell.
        os.execvpe(  # noqa: S606
            "tmux",
            ["tmux", "-S", str(socket), "attach-session", "-t", f"={session}"],
            environment,
        )
    except (ViewError, OSError, subprocess.TimeoutExpired) as error:
        print(f"open-viewer: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
