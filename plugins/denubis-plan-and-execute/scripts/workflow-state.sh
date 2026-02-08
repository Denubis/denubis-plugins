#!/usr/bin/env bash
# workflow-state.sh — Update workflow state for the current Claude session.
#
# Used by plan-and-execute skills to signal the current workflow phase
# to the status line. Each working directory gets its own state file
# under ~/.claude/workflow-state/ (keyed by md5 of $PWD).
#
# Usage:
#   workflow-state.sh --step "Implementing" --human "engage"
#   workflow-state.sh --feature "94" --phase "CRDT" --step "Design"
#   workflow-state.sh --human null          # clear the human action (Claude is working)
#   workflow-state.sh --clear               # remove state entirely
#
# Arguments (all optional, only provided args are updated):
#   --feature NAME    Short project/feature name (e.g. "94", "milkdown-crdt")
#   --phase   NAME    Current design phase name (e.g. "CRDT Cloning", "Auth")
#   --step    NAME    Workflow step: Design, Clarification, Brainstorming,
#                     Impl Planning, Implementing, Code Review, Finishing,
#                     Debugging, Dep Review
#   --human   ACTION  Human action required: approve, review, respond, think,
#                     engage, or "null" to clear
#   --clear           Remove the state file entirely

set -euo pipefail

STATE_DIR="$HOME/.claude/workflow-state"
mkdir -p "$STATE_DIR"

# Key the state file by working directory
DIR_HASH=$(echo -n "$PWD" | md5sum | cut -d' ' -f1)
STATE_FILE="$STATE_DIR/$DIR_HASH.json"

# Parse arguments
FEATURE=""
PHASE=""
STEP=""
HUMAN=""
CLEAR=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --feature) FEATURE="$2"; shift 2 ;;
        --phase)   PHASE="$2";   shift 2 ;;
        --step)    STEP="$2";    shift 2 ;;
        --human)   HUMAN="$2";   shift 2 ;;
        --clear)   CLEAR=true;   shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if $CLEAR; then
    rm -f "$STATE_FILE"
    exit 0
fi

# Read existing state (if any)
if [[ -f "$STATE_FILE" ]]; then
    EXISTING=$(cat "$STATE_FILE")
else
    EXISTING='{"feature":"","phase":"","step":"","human":null,"pwd":"","updated":""}'
fi

# Helper: extract a JSON string value (basic, no jq dependency)
json_get() {
    echo "$EXISTING" | grep -oP "\"$1\"\\s*:\\s*\"\\K[^\"]*" || echo ""
}

# Merge: only update fields that were provided
OLD_FEATURE=$(json_get feature)
OLD_PHASE=$(json_get phase)
OLD_STEP=$(json_get step)
# human needs special handling for null
OLD_HUMAN=$(echo "$EXISTING" | grep -oP '"human"\s*:\s*\K[^,}]*' | tr -d ' "' || echo "null")

NEW_FEATURE="${FEATURE:-$OLD_FEATURE}"
NEW_PHASE="${PHASE:-$OLD_PHASE}"
NEW_STEP="${STEP:-$OLD_STEP}"

if [[ -n "$HUMAN" ]]; then
    if [[ "$HUMAN" == "null" ]]; then
        NEW_HUMAN="null"
    else
        NEW_HUMAN="\"$HUMAN\""
    fi
else
    if [[ "$OLD_HUMAN" == "null" ]]; then
        NEW_HUMAN="null"
    else
        NEW_HUMAN="\"$OLD_HUMAN\""
    fi
fi

UPDATED=$(date -Iseconds)

# Write atomically (temp file + rename)
TMP_FILE=$(mktemp "$STATE_DIR/.tmp.XXXXXX")
cat > "$TMP_FILE" <<EOF
{"feature":"$NEW_FEATURE","phase":"$NEW_PHASE","step":"$NEW_STEP","human":$NEW_HUMAN,"pwd":"$PWD","updated":"$UPDATED"}
EOF
mv "$TMP_FILE" "$STATE_FILE"
