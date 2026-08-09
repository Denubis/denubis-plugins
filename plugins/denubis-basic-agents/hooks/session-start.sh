#!/usr/bin/env bash

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<agents>\nWhen a task calls for a general-purpose agent, invoke the 'using-generic-agents' skill before dispatching. It carries the model-tier floor and the domain-specific alternatives, so choosing without it tends to land on a tier that cannot carry the task's judgement and returns an answer that reads plausible.\n</agents>"
  }
}
EOF

exit 0
