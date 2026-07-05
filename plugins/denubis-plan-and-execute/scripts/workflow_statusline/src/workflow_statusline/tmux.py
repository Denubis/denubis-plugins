"""tmux window rename with caching and lock file deference."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from workflow_statusline import cache


def maybe_rename(name: str) -> None:
    """Rename tmux window to 'Cl:<name>' if name changed and no lock file."""
    if "TMUX" not in os.environ:
        return

    tmux_pane = os.environ.get("TMUX_PANE")
    if not tmux_pane:
        return

    pane_id = tmux_pane.lstrip("%")

    lock_file = f"/tmp/claude-statusline-tmux-lock-{pane_id}"
    if Path(lock_file).exists():
        return

    cache_file = f"/tmp/claude-statusline-tmux-{pane_id}"
    cached_name = cache.read_if_fresh(cache_file, max_age=86400)
    if cached_name == name:
        return

    subprocess.run(
        ["tmux", "rename-window", f"Cl:{name}"], check=False, capture_output=True
    )
    cache.write(cache_file, name)
