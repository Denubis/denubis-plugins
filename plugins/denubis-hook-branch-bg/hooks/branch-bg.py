#!/usr/bin/env python3
"""Set terminal background colour based on git repo and branch via OSC 11.

Repo (via git-common-dir) sets the base hue at L=0.15, S=0.60.
Branch hash offsets hue (±40°), lightness (±0.03), and saturation (±0.10)
to create visually related but distinct colours per worktree.
"""

import colorsys
import hashlib
import json
import os
import subprocess
import sys


def get_git_info() -> tuple[str | None, str | None]:
    """Return (common_dir, branch_name) or (None, None) if not in a git repo.

    Uses --git-common-dir so all worktrees of the same repo share an identity.
    """
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if common.returncode == 0 and branch.returncode == 0:
            # Resolve to absolute so the hash is stable regardless of cwd
            common_dir = os.path.realpath(common.stdout.strip())
            return common_dir, branch.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None, None


def git_info_to_colour(repo_id: str, branch: str) -> str:
    """Map repo to base hue, branch to offsets in hue/lightness/saturation.

    main/master sits at the exact base colour (H=base, L=0.15, S=0.60).
    All other branches offset from that centre point.
    """
    repo_hash = hashlib.sha256(repo_id.encode()).hexdigest()

    # Repo -> base hue (0-360°)
    base_hue = int(repo_hash[:8], 16) % 360

    if branch in ("main", "master"):
        hue = base_hue / 360.0
        lightness = 0.15
        sat = 0.60
    else:
        branch_hash = hashlib.sha256(branch.encode()).hexdigest()
        bh = int(branch_hash[:8], 16)
        hue_offset = (bh % 81) - 40            # -40 to +40 degrees
        lightness_offset = ((bh >> 8) % 7 - 3) * 0.01  # -0.03 to +0.03
        sat_offset = ((bh >> 16) % 21 - 10) * 0.01     # -0.10 to +0.10

        hue = ((base_hue + hue_offset) % 360) / 360.0
        lightness = max(0.11, min(0.19, 0.15 + lightness_offset))
        sat = max(0.40, min(0.80, 0.60 + sat_offset))

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
    repo_id, branch = get_git_info()

    if repo_id and branch:
        colour = git_info_to_colour(repo_id, branch)
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
