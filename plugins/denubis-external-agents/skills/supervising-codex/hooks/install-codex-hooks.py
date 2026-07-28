# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Merge the Codex supervision relay into the user's global Codex hooks.

The relay belongs in `~/.codex/hooks.json` rather than in each project. A
project-local `.codex/hooks.json` only wakes the monitor in directories somebody
set up in advance, so a Codex started in a fresh directory is unsupervised
exactly when nobody was thinking about supervision. The relay was project-local
upstream only because the script it called lived in the project; that script now
sits at a stable path in the installed plugin, so nothing project-shaped is left
to justify per-project wiring.

Leaving it wired everywhere is cheap and safe. The relay addresses a per-pane
socket derived from its inherited `$TMUX_PANE`, so it only ever reaches the
monitor watching that exact pane, and with no monitor listening it prints
nothing and exits 0. The cost is one short-lived process per hook event.

Idempotent. Running it twice adds nothing the second time, it preserves every
hook it did not write, and it backs the file up before touching it.

Written to parse on 3.9 for the same reason the hook entry point is: it runs on
whatever interpreter the machine offers.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

RELAYED_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PermissionRequest",
    "PostToolUse",
    "Stop",
)
TIMEOUT_SECONDS = 5
MARKER = "codex_supervisor.py"


def relay_command() -> str:
    """Build the hook command, resolved from this script's own location."""
    # hooks/ -> supervising-codex/ -> skills/ -> the plugin root.
    script = Path(__file__).resolve().parents[3] / "scripts" / "codex_supervisor.py"
    if not script.is_file():
        raise SystemExit(
            f"cannot find the supervisor beside this installer (looked for {script})"
        )
    return f'uv run --no-project --no-config python "{script}" --hook'


def reconcile(entries: list, command: str) -> str:
    """Bring this event's relay into line, and say what that took.

    Matching on presence alone is not enough. The relay names an absolute path, so
    moving or reinstalling the plugin leaves a stale command that still contains the
    marker; a check that only asked "is it there?" would skip it and leave every hook
    on the machine pointing at a script that is gone.
    """
    for group in entries:
        for hook in group.get("hooks", []):
            if MARKER not in str(hook.get("command", "")):
                continue
            if hook.get("command") == command:
                return "present"
            hook["command"] = command
            hook["timeout"] = TIMEOUT_SECONDS
            return "updated"
    entries.append(
        {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": TIMEOUT_SECONDS,
                }
            ]
        }
    )
    return "added"


def main() -> int:
    target = Path.home() / ".codex" / "hooks.json"
    command = relay_command()

    if target.is_file():
        document = json.loads(target.read_text() or "{}")
        backup = target.with_suffix(f".json.bak-{int(time.time())}")
        shutil.copy2(target, backup)
        print(f"backed up {target} -> {backup.name}")
    else:
        document = {}
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        print(f"creating {target}")

    hooks = document.setdefault("hooks", {})
    outcomes = {"added": [], "updated": [], "present": []}
    for event in RELAYED_EVENTS:
        outcomes[reconcile(hooks.setdefault(event, []), command)].append(event)

    target.write_text(json.dumps(document, indent=2) + "\n")

    for label in ("added", "updated", "present"):
        if outcomes[label]:
            print("{}: {}".format(label, ", ".join(outcomes[label])))
    preserved = sum(
        len(g.get("hooks", [])) for entries in hooks.values() for g in entries
    ) - len(RELAYED_EVENTS)
    print(f"other hooks preserved: {preserved}")
    print("relay -> {}".format(command.split('"')[1]))
    print("\nNow run /hooks in Codex to trust them, and restart running sessions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
