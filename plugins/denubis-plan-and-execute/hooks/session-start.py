#!/usr/bin/env python3
"""SessionStart hook for denubis-plan-and-execute.

Injects the using-plan-and-execute SKILL.md as session context. JSON encoding
is delegated to json.dumps so every control character is escaped correctly —
the prior bash implementation hand-rolled escaping for only \\ " \\n \\r \\t.
"""

import json
import os
from pathlib import Path

# Claude Code sets CLAUDE_PLUGIN_ROOT for hooks; fall back to walking up from
# this file (hooks/ -> plugin root) when run directly, e.g. under test.
_env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
PLUGIN_ROOT = Path(_env_root) if _env_root else Path(__file__).resolve().parent.parent
SKILL_FILE = PLUGIN_ROOT / "skills" / "using-plan-and-execute" / "SKILL.md"

try:
    # rstrip("\n") matches bash $(cat ...), which strips trailing newlines.
    skill_content = SKILL_FILE.read_text(encoding="utf-8").rstrip("\n")
except OSError:
    skill_content = "Error reading using-plan-and-execute skill"

context = (
    "<skills>\n"
    "The content below is skills/using-plan-and-execute/SKILL.md, this"
    " project's skill-first workflow.\n\n"
    f"{skill_content}\n"
    "</skills>"
)

output = {
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context,
    }
}

print(json.dumps(output))
