#!/usr/bin/env bash

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "<EXTREMELY_IMPORTANT>\nBefore responding to this prompt, consider whether you have any skills in <available_skills /> that apply. If you do and they have not been activated in this session, use the Skill tool to activate them.\n</EXTREMELY_IMPORTANT>"
  }
}
EOF

exit 0
