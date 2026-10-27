"""Where Claude Code and Codex keep their session logs.

Each root is resolved in the same order: an explicit path from the caller, taken
as given; else the tool's configuration-directory variable, with ``~`` expanded;
else the default under the home directory. An empty variable counts as unset.
"""

from __future__ import annotations

import os
from pathlib import Path


def _configured_dir(variable: str, default_name: str) -> Path:
    configured = os.environ.get(variable)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / default_name


def claude_projects_root(override: str | os.PathLike[str] | None = None) -> Path:
    """Return the directory holding Claude Code's per-project transcripts.

    ``$CLAUDE_CONFIG_DIR/projects`` when the variable is set, else
    ``~/.claude/projects``.
    """
    if override is not None:
        return Path(override)
    return _configured_dir("CLAUDE_CONFIG_DIR", ".claude") / "projects"


def codex_sessions_root(override: str | os.PathLike[str] | None = None) -> Path:
    """Return the directory holding Codex rollout files.

    ``$CODEX_HOME/sessions`` when the variable is set, else ``~/.codex/sessions``.
    """
    if override is not None:
        return Path(override)
    return _configured_dir("CODEX_HOME", ".codex") / "sessions"
