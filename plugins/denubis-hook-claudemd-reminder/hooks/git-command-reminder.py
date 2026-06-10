#!/usr/bin/env python3
"""
PostToolUse hook that reminds to invoke project-claude-librarian
before committing when git status or git log shows changes.
"""
import json
import sys
import re

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    # Invalid input, exit silently
    sys.exit(0)

# Only process Bash tool
tool_name = input_data.get("tool_name", "")
if tool_name != "Bash":
    sys.exit(0)

tool_input = input_data.get("tool_input", {})
command = tool_input.get("command", "")

# Match git status or git log (but not quick one-liners like git log --oneline -3)
# We want to trigger on substantive git status/log commands
if re.match(r"^git\s+(status|log(?!\s+--oneline\s+-\d+$))", command):
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "Reminder: If you're about to commit changes that affect contracts, "
                "APIs, or domain structure, consider invoking `project-claude-librarian` "
                "(denubis-extending-claude:project-claude-librarian) to review and update "
                "CLAUDE.md files before committing."
            )
        }
    }
    print(json.dumps(output))

sys.exit(0)
