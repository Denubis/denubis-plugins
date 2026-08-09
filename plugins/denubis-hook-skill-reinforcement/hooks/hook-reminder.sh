#!/usr/bin/env bash

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "<skills>\nCheck whether an available skill covers this task before starting it, and invoke any that is not already active with the Skill tool. Skills encode workflows that have already been debugged against this codebase, so working without one usually means re-deriving a solved problem and getting it subtly wrong.\n</skills>"
  }
}
EOF

exit 0
