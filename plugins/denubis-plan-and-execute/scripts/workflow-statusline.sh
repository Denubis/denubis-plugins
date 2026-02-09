#!/usr/bin/env bash
# workflow-statusline.sh — Claude Code status line renderer.
#
# Two-line display:
#   Line 1: [Model] dir | git branch +staged ~modified | workflow breadcrumb
#   Line 2: context bar pct% | $cost | duration
#
# Workflow breadcrumb (when active):
#   feature ❯ phase ❯ step ❯ human action
#
# Configure in ~/.claude/settings.json:
#   "statusLine": {
#     "type": "command",
#     "command": "/path/to/workflow-statusline.sh"
#   }

set -euo pipefail

# ── Read session JSON from stdin ──────────────────────────────────────

INPUT=$(cat)

CWD=$(echo "$INPUT" | jq -r '.cwd // ""')
MODEL=$(echo "$INPUT" | jq -r '.model.display_name // "?"')
PCT=$(echo "$INPUT" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
REMAINING=$(echo "$INPUT" | jq -r '.context_window.remaining_percentage // ""' | cut -d. -f1)
COST=$(echo "$INPUT" | jq -r '.cost.total_cost_usd // 0')
DURATION_MS=$(echo "$INPUT" | jq -r '.cost.total_duration_ms // 0')

if [[ -z "$CWD" ]]; then
    exit 0
fi

# ── ANSI 16 colour codes (theme-adaptive) ────────────────────────────

RST='\033[0m'
DIM='\033[2m'
BOLD='\033[1m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
MAGENTA='\033[35m'
WHITE='\033[37m'

# ── Git info (cached) ────────────────────────────────────────────────

GIT_CACHE="/tmp/claude-statusline-git-cache-$(echo -n "$CWD" | md5sum | cut -d' ' -f1)"
GIT_CACHE_MAX_AGE=5

git_cache_stale() {
    [[ ! -f "$GIT_CACHE" ]] || \
    [[ $(($(date +%s) - $(stat -c %Y "$GIT_CACHE" 2>/dev/null || echo 0))) -gt $GIT_CACHE_MAX_AGE ]]
}

if git_cache_stale; then
    if git -C "$CWD" rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || echo "")
        STAGED=$(git -C "$CWD" diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')
        MODIFIED=$(git -C "$CWD" diff --numstat 2>/dev/null | wc -l | tr -d ' ')
        echo "$BRANCH|$STAGED|$MODIFIED" > "$GIT_CACHE"
    else
        echo "||" > "$GIT_CACHE"
    fi
fi

IFS='|' read -r GIT_BRANCH GIT_STAGED GIT_MODIFIED < "$GIT_CACHE"

# ── Workflow state ───────────────────────────────────────────────────

STATE_DIR="$HOME/.claude/workflow-state"
DIR_HASH=$(echo -n "$CWD" | md5sum | cut -d' ' -f1)
STATE_FILE="$STATE_DIR/$DIR_HASH.json"
CRUMB=""

if [[ -f "$STATE_FILE" ]]; then
    STATE=$(cat "$STATE_FILE")
    FEATURE=$(echo "$STATE" | jq -r '.feature // ""')
    PHASE=$(echo "$STATE" | jq -r '.phase // ""')
    STEP=$(echo "$STATE" | jq -r '.step // ""')
    HUMAN=$(echo "$STATE" | jq -r '.human // empty')

    # Step colours
    declare -A STEP_COLOUR
    STEP_COLOUR[Design]="$BLUE"
    STEP_COLOUR[Clarification]="$CYAN"
    STEP_COLOUR[Brainstorming]="$BLUE"
    STEP_COLOUR[Impl\ Planning]="$MAGENTA"
    STEP_COLOUR[Implementing]="$GREEN"
    STEP_COLOUR[Code\ Review]="$CYAN"
    STEP_COLOUR[Finishing]="$WHITE"
    STEP_COLOUR[Debugging]="$YELLOW"
    STEP_COLOUR[Dep\ Review]="$WHITE"

    # Human action styles (escalating intensity)
    declare -A HUMAN_STYLE
    HUMAN_STYLE[approve]="${DIM}${WHITE}"
    HUMAN_STYLE[review]="$CYAN"
    HUMAN_STYLE[respond]="$YELLOW"
    HUMAN_STYLE[think]="${BOLD}${MAGENTA}"
    HUMAN_STYLE[engage]="${BOLD}\033[41;37m"

    declare -A HUMAN_LABEL
    HUMAN_LABEL[approve]='Approve'
    HUMAN_LABEL[review]='Review'
    HUMAN_LABEL[respond]='Respond'
    HUMAN_LABEL[think]='Think'
    HUMAN_LABEL[engage]='ENGAGE'

    SEP="${DIM} ❯ ${RST}"

    if [[ -n "$FEATURE" || -n "$PHASE" || -n "$STEP" ]]; then
        [[ -n "$FEATURE" ]] && CRUMB="${BOLD}${WHITE}${FEATURE}${RST}"
        if [[ -n "$PHASE" ]]; then
            [[ -n "$CRUMB" ]] && CRUMB="${CRUMB}${SEP}"
            CRUMB="${CRUMB}${WHITE}${PHASE}${RST}"
        fi
        if [[ -n "$STEP" ]]; then
            [[ -n "$CRUMB" ]] && CRUMB="${CRUMB}${SEP}"
            COLOUR="${STEP_COLOUR[$STEP]:-$WHITE}"
            CRUMB="${CRUMB}${COLOUR}${STEP}${RST}"
        fi
        if [[ -n "$HUMAN" && "$HUMAN" != "null" ]]; then
            [[ -n "$CRUMB" ]] && CRUMB="${CRUMB}${SEP}"
            STYLE="${HUMAN_STYLE[$HUMAN]:-$WHITE}"
            LABEL="${HUMAN_LABEL[$HUMAN]:-$HUMAN}"
            CRUMB="${CRUMB}${STYLE} ${LABEL} ${RST}"
        fi
    fi
fi

# ── Line 1: model, dir, git, workflow ────────────────────────────────

DIR_NAME="${CWD##*/}"
LINE1="${CYAN}[${MODEL}]${RST} ${BLUE}${DIR_NAME}${RST}"

if [[ -n "$GIT_BRANCH" ]]; then
    GIT_EXTRA=""
    [[ "$GIT_STAGED" -gt 0 ]] 2>/dev/null && GIT_EXTRA="${GREEN}+${GIT_STAGED}${RST}"
    [[ "$GIT_MODIFIED" -gt 0 ]] 2>/dev/null && GIT_EXTRA="${GIT_EXTRA}${YELLOW}~${GIT_MODIFIED}${RST}"
    LINE1="${LINE1} ${DIM}|${RST} ${WHITE}${GIT_BRANCH}${RST} ${GIT_EXTRA}"
fi

if [[ -n "$CRUMB" ]]; then
    LINE1="${LINE1} ${DIM}|${RST} ${CRUMB}"
fi

# ── Line 2: context bar, cost, duration ──────────────────────────────

# Context bar colour
if [[ "$PCT" -ge 90 ]]; then BAR_COLOR="$RED"
elif [[ "$PCT" -ge 70 ]]; then BAR_COLOR="$YELLOW"
else BAR_COLOR="$GREEN"; fi

BAR_WIDTH=10
FILLED=$((PCT * BAR_WIDTH / 100))
EMPTY=$((BAR_WIDTH - FILLED))
BAR=""
[[ "$FILLED" -gt 0 ]] && BAR=$(printf "%${FILLED}s" | tr ' ' '█')
[[ "$EMPTY" -gt 0 ]] && BAR="${BAR}$(printf "%${EMPTY}s" | tr ' ' '░')"

COST_FMT=$(printf '$%.2f' "$COST")
MINS=$((DURATION_MS / 60000))
SECS=$(((DURATION_MS % 60000) / 1000))

LINE2="${BAR_COLOR}${BAR}${RST} ${PCT}%"
[[ -n "$REMAINING" ]] && LINE2="${LINE2} ${DIM}(${REMAINING}% left)${RST}"
LINE2="${LINE2} ${DIM}|${RST} ${YELLOW}${COST_FMT}${RST} ${DIM}|${RST} ${MINS}m ${SECS}s"

# ── Output ───────────────────────────────────────────────────────────

echo -e "$LINE1"
echo -e "$LINE2"
