#!/usr/bin/env bash

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<EXTREMELY_IMPORTANT>\nWhenever instructed to use a 'general-purpose' agent, you MUST invoke the 'using-generic-agents' skill, which will guide you on how to correctly use a generic agent.\n</EXTREMELY_IMPORTANT>"
  }
}
EOF

exit 0
