#!/usr/bin/env python3
"""Set terminal background colour based on git repo path and branch via OSC 11.

Path controls hue (project identity), branch controls saturation (branch differentiation).
Lightness is fixed dark for terminal readability.
"""

import colorsys
import hashlib
import json
import os
import subprocess
import sys


def get_git_info() -> tuple[str | None, str | None]:
    """Return (repo_root, branch_name) or (None, None) if not in a git repo."""
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if root.returncode == 0 and branch.returncode == 0:
            return root.stdout.strip(), branch.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None, None


def git_info_to_colour(repo_path: str, branch: str) -> str:
    """Map repo path to hue, branch to saturation, fixed dark lightness."""
    path_hash = hashlib.sha256(repo_path.encode()).hexdigest()
    branch_hash = hashlib.sha256(branch.encode()).hexdigest()

    # Path -> hue (0.0-1.0)
    hue = int(path_hash[:8], 16) % 360 / 360.0

    # Branch -> saturation (0.20-0.70)
    sat = 0.20 + (int(branch_hash[:8], 16) % 50) / 100.0

    # Fixed dark lightness for terminal backgrounds
    lightness = 0.10

    r, g, b = colorsys.hls_to_rgb(hue, lightness, sat)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def find_terminal() -> str | None:
    """Walk up process tree to find the controlling terminal device."""
    pid = os.getpid()
    while pid > 1:
        try:
            fd0 = os.readlink(f"/proc/{pid}/fd/0")
            if fd0.startswith("/dev/pts/") or fd0.startswith("/dev/tty"):
                return fd0
        except (OSError, PermissionError):
            pass
        try:
            with open(f"/proc/{pid}/stat") as f:
                parts = f.read().split()
                pid = int(parts[3])  # ppid
        except (OSError, ValueError):
            break
    return None


def set_terminal_bg(colour: str) -> None:
    """Set terminal background via OSC 11, walking process tree to find TTY."""
    tty_path = find_terminal()
    if not tty_path:
        return
    try:
        with open(tty_path, "w") as tty:
            tty.write(f"\033]11;{colour}\007")
    except OSError:
        pass


def main() -> None:
    repo_path, branch = get_git_info()

    if repo_path and branch:
        colour = git_info_to_colour(repo_path, branch)
        set_terminal_bg(colour)

    # Hook JSON output
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "Success",
        },
    }, sys.stdout)


if __name__ == "__main__":
    main()
