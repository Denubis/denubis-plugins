"""Open an independent terminal client for the native attention viewer."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
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
    parser.add_argument("--session", help=argparse.SUPPRESS)
    parser.add_argument("--socket", type=Path)
    args = parser.parse_args(argv)
    if args.session is not None:
        parser.error(
            "--session was removed: standalone viewers do not create tmux sessions"
        )
    try:
        ghostty = shutil.which("ghostty") if args.ghostty else None
        if args.ghostty and ghostty is None:
            raise ViewError(
                "ghostty is not on PATH; use this helper in an existing terminal"
            )
        socket = source_socket(args.socket, args.watch_session)
        environment = dict(os.environ)
        environment.pop("TMUX", None)
        environment.pop("TMUX_PANE", None)
        options = [
            "--socket",
            str(socket),
            "--watch-session",
            args.watch_session,
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
            print("Started Ghostty for the standalone viewer")
            return 0
        # Run the TUI directly; no viewer tmux session or client is created.
        os.execve(  # noqa: S606
            sys.executable,
            [sys.executable, "-P", str(Path(__file__).with_name("board.py")), *options],
            environment,
        )
    except (ViewError, OSError, subprocess.TimeoutExpired) as error:
        print(f"open-viewer: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
