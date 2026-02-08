#!/usr/bin/env bash
# workflow-statusline.sh — Claude Code status line renderer.
#
# Reads session JSON from stdin, looks up workflow state for the current
# working directory, and renders a breadcrumb trail showing where you are
# in the plan-and-execute workflow.
#
# Breadcrumb format:
#   feature ❯ phase ❯ step ❯ human action (if paused for you)
#
# Configure in ~/.claude/settings.json:
#   "statusLine": {
#     "type": "command",
#     "command": "/path/to/workflow-statusline.sh"
#   }

set -euo pipefail

STATE_DIR="$HOME/.claude/workflow-state"

# Read session JSON from stdin
INPUT=$(cat)

# Extract working directory
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')
if [[ -z "$CWD" ]]; then
    exit 0
fi

# Find the state file for this working directory
DIR_HASH=$(echo -n "$CWD" | md5sum | cut -d' ' -f1)
STATE_FILE="$STATE_DIR/$DIR_HASH.json"

if [[ ! -f "$STATE_FILE" ]]; then
    # No workflow state — nothing to show
    exit 0
fi

STATE=$(cat "$STATE_FILE")

FEATURE=$(echo "$STATE" | jq -r '.feature // ""')
PHASE=$(echo "$STATE" | jq -r '.phase // ""')
STEP=$(echo "$STATE" | jq -r '.step // ""')
HUMAN=$(echo "$STATE" | jq -r '.human // empty')

# If nothing is set, don't render
if [[ -z "$FEATURE" && -z "$PHASE" && -z "$STEP" ]]; then
    exit 0
fi

# ── ANSI 16 colour codes (theme-adaptive) ──────────────────────────

RST='\033[0m'
DIM='\033[2m'
BOLD='\033[1m'

# Level 3: workflow step colours (foreground only)
declare -A STEP_COLOUR
STEP_COLOUR[Design]='\033[34m'          # blue
STEP_COLOUR[Clarification]='\033[36m'   # cyan
STEP_COLOUR[Brainstorming]='\033[34m'   # blue
STEP_COLOUR[Impl\ Planning]='\033[35m'  # magenta
STEP_COLOUR[Implementing]='\033[32m'    # green
STEP_COLOUR[Code\ Review]='\033[36m'    # cyan
STEP_COLOUR[Finishing]='\033[37m'       # white
STEP_COLOUR[Debugging]='\033[33m'       # yellow
STEP_COLOUR[Dep\ Review]='\033[37m'     # white

# Level 4: human action display (escalating intensity)
# approve  = dim white fg         (glance and click)
# review   = cyan fg              (sit and read)
# respond  = yellow fg            (type something)
# think    = magenta fg bold      (deliberate carefully)
# engage   = red bg, white fg     (get up and go)
declare -A HUMAN_STYLE
HUMAN_STYLE[approve]="${DIM}\033[37m"
HUMAN_STYLE[review]='\033[36m'
HUMAN_STYLE[respond]='\033[33m'
HUMAN_STYLE[think]="${BOLD}\033[35m"
HUMAN_STYLE[engage]="${BOLD}\033[41;37m"

declare -A HUMAN_LABEL
HUMAN_LABEL[approve]='Approve'
HUMAN_LABEL[review]='Review'
HUMAN_LABEL[respond]='Respond'
HUMAN_LABEL[think]='Think'
HUMAN_LABEL[engage]='ENGAGE'

# ── Build the breadcrumb ────────────────────────────────────────────

SEP="${DIM} ❯ ${RST}"
CRUMB=""

# Level 1: feature
if [[ -n "$FEATURE" ]]; then
    CRUMB="${BOLD}\033[37m${FEATURE}${RST}"
fi

# Level 2: phase
if [[ -n "$PHASE" ]]; then
    if [[ -n "$CRUMB" ]]; then
        CRUMB="${CRUMB}${SEP}"
    fi
    CRUMB="${CRUMB}\033[37m${PHASE}${RST}"
fi

# Level 3: workflow step (coloured)
if [[ -n "$STEP" ]]; then
    if [[ -n "$CRUMB" ]]; then
        CRUMB="${CRUMB}${SEP}"
    fi
    COLOUR="${STEP_COLOUR[$STEP]:-\033[37m}"
    CRUMB="${CRUMB}${COLOUR}${STEP}${RST}"
fi

# Level 4: human action (only when paused for the user)
if [[ -n "$HUMAN" && "$HUMAN" != "null" ]]; then
    if [[ -n "$CRUMB" ]]; then
        CRUMB="${CRUMB}${SEP}"
    fi
    STYLE="${HUMAN_STYLE[$HUMAN]:-\033[37m}"
    LABEL="${HUMAN_LABEL[$HUMAN]:-$HUMAN}"
    CRUMB="${CRUMB}${STYLE} ${LABEL} ${RST}"
fi

echo -e "$CRUMB"
