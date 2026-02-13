#!/usr/bin/env bash
# workflow-state.sh — Update workflow state for the current Claude session.
#
# Used by plan-and-execute skills to signal the current workflow position
# to the status line. Each working directory gets its own state file
# under ~/.claude/workflow-state/ (keyed by md5 of $PWD).
#
# Usage:
#   workflow-state.sh --skill "brainstorming" --context "exploring OAuth vs JWT"
#   workflow-state.sh --feature "94" --skill "executing-impl" --context "Phase 2 Step 3: auth middleware"
#   workflow-state.sh --context ""           # clear context (Claude is working autonomously)
#   workflow-state.sh --clear                # remove state entirely
#
# Arguments (all optional, only provided args are updated):
#   --feature NAME    Short project/feature name (e.g. "94", "milkdown-crdt")
#   --skill   NAME    Active skill name (e.g. "brainstorming", "systematic-debugging",
#                     "executing-impl", "writing-design-plans", "code-review")
#   --context TEXT    Free-text description of current position in process
#                     (e.g. "Phase 2 Step 3: auth middleware", "hypothesis: race condition")
#                     Use "" to clear (Claude working autonomously)
#   --issue   REF     GitHub issue reference (e.g. "#123", "org/repo#123")
#   --clear           Remove the state file entirely

set -euo pipefail

STATE_DIR="$HOME/.claude/workflow-state"
mkdir -p "$STATE_DIR"

# Key the state file by working directory
DIR_HASH=$(echo -n "$PWD" | md5sum | cut -d' ' -f1)
STATE_FILE="$STATE_DIR/$DIR_HASH.json"

# Parse arguments
FEATURE=""
SKILL=""
CONTEXT=""
CONTEXT_SET=false
ISSUE=""
CLEAR=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --feature) FEATURE="$2"; shift 2 ;;
        --skill)   SKILL="$2";   shift 2 ;;
        --context) CONTEXT="$2"; CONTEXT_SET=true; shift 2 ;;
        --issue)   ISSUE="$2";   shift 2 ;;
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
    EXISTING='{"feature":"","skill":"","context":"","issue":"","pwd":"","updated":""}'
fi

# Helper: extract a JSON string value (basic, no jq dependency)
json_get() {
    echo "$EXISTING" | grep -oP "\"$1\"\\s*:\\s*\"\\K[^\"]*" || echo ""
}

# Merge: only update fields that were provided
OLD_FEATURE=$(json_get feature)
OLD_SKILL=$(json_get skill)
OLD_CONTEXT=$(json_get context)
OLD_ISSUE=$(json_get issue)

NEW_FEATURE="${FEATURE:-$OLD_FEATURE}"
NEW_SKILL="${SKILL:-$OLD_SKILL}"
NEW_ISSUE="${ISSUE:-$OLD_ISSUE}"

if $CONTEXT_SET; then
    NEW_CONTEXT="$CONTEXT"
else
    NEW_CONTEXT="$OLD_CONTEXT"
fi

UPDATED=$(date -Iseconds)

# Write atomically (temp file + rename)
TMP_FILE=$(mktemp "$STATE_DIR/.tmp.XXXXXX")
cat > "$TMP_FILE" <<EOF
{"feature":"$NEW_FEATURE","skill":"$NEW_SKILL","context":"$NEW_CONTEXT","issue":"$NEW_ISSUE","pwd":"$PWD","updated":"$UPDATED"}
EOF
mv "$TMP_FILE" "$STATE_FILE"
