#!/usr/bin/env bash
# workflow-statusline.sh — Claude Code status line renderer.
#
# Two-line display:
#   Line 1: [Model] location | skill ❯ context
#   Line 2: context bar pct% | $cost | duration
#
# Location logic:
#   - Worktree: show worktree dir name
#   - Normal repo: show repo basename
#   - Append @branch if branch differs from displayed name
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

# ── Smart location (worktree-aware) ──────────────────────────────────

LOCATION="${CWD##*/}"
GIT_STAGED=0
GIT_MODIFIED=0

if git -C "$CWD" rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || echo "")

    # Detect worktree
    TOPLEVEL=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "$CWD")
    COMMON_DIR=$(git -C "$CWD" rev-parse --git-common-dir 2>/dev/null || echo "")
    DISPLAY_NAME="${TOPLEVEL##*/}"

    IS_WORKTREE=false
    if [[ -n "$COMMON_DIR" ]]; then
        REAL_COMMON=$(realpath "$COMMON_DIR" 2>/dev/null || echo "$COMMON_DIR")
        REAL_GITDIR=$(realpath "$TOPLEVEL/.git" 2>/dev/null || echo "$TOPLEVEL/.git")
        if [[ "$REAL_COMMON" != "$REAL_GITDIR" && -d "$REAL_COMMON" ]]; then
            IS_WORKTREE=true
        fi
    fi

    if $IS_WORKTREE; then
        LOCATION="$DISPLAY_NAME"
        if [[ -n "$BRANCH" && "$BRANCH" != "$DISPLAY_NAME" ]]; then
            LOCATION="${DISPLAY_NAME}@${BRANCH}"
        fi
    else
        LOCATION="$DISPLAY_NAME"
        if [[ -n "$BRANCH" && "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
            LOCATION="${DISPLAY_NAME}@${BRANCH}"
        fi
    fi

    # Git changes (cached)
    GIT_CACHE="/tmp/claude-statusline-git-cache-$(echo -n "$CWD" | md5sum | cut -d' ' -f1)"
    GIT_CACHE_MAX_AGE=5

    git_cache_stale() {
        [[ ! -f "$GIT_CACHE" ]] || \
        [[ $(($(date +%s) - $(stat -c %Y "$GIT_CACHE" 2>/dev/null || echo 0))) -gt $GIT_CACHE_MAX_AGE ]]
    }

    if git_cache_stale; then
        STAGED=$(git -C "$CWD" diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')
        MODIFIED=$(git -C "$CWD" diff --numstat 2>/dev/null | wc -l | tr -d ' ')
        echo "$STAGED|$MODIFIED" > "$GIT_CACHE"
    fi

    IFS='|' read -r GIT_STAGED GIT_MODIFIED < "$GIT_CACHE"
fi

# ── Workflow state ───────────────────────────────────────────────────

STATE_DIR="$HOME/.claude/workflow-state"
DIR_HASH=$(echo -n "$CWD" | md5sum | cut -d' ' -f1)
STATE_FILE="$STATE_DIR/$DIR_HASH.json"
CRUMB=""

if [[ -f "$STATE_FILE" ]]; then
    STATE=$(cat "$STATE_FILE")
    FEATURE=$(echo "$STATE" | jq -r '.feature // ""')
    SKILL_NAME=$(echo "$STATE" | jq -r '.skill // ""')
    CONTEXT=$(echo "$STATE" | jq -r '.context // ""')

    # Skill colours by category
    declare -A SKILL_COLOUR
    # Design — blue
    SKILL_COLOUR[brainstorming]="$BLUE"
    SKILL_COLOUR[asking-clarifying-questions]="$BLUE"
    SKILL_COLOUR[writing-design-plans]="$BLUE"
    SKILL_COLOUR[starting-a-design-plan]="$BLUE"
    SKILL_COLOUR[flesh-it-out]="$BLUE"
    # Planning — magenta
    SKILL_COLOUR[starting-an-implementation-plan]="$MAGENTA"
    SKILL_COLOUR[writing-implementation-plans]="$MAGENTA"
    # Execution — green
    SKILL_COLOUR[executing-impl]="$GREEN"
    SKILL_COLOUR[executing-an-implementation-plan]="$GREEN"
    SKILL_COLOUR[code-review]="$CYAN"
    SKILL_COLOUR[requesting-code-review]="$CYAN"
    # Defensive — yellow
    SKILL_COLOUR[systematic-debugging]="$YELLOW"
    SKILL_COLOUR[controlled-dependency-upgrade]="$YELLOW"
    SKILL_COLOUR[restate-our-assumptions]="$YELLOW"
    SKILL_COLOUR[proleptic-challenge]="$YELLOW"
    # Gates — cyan
    SKILL_COLOUR[human-uat-gate]="$CYAN"
    SKILL_COLOUR[finishing-a-development-branch]="$CYAN"
    SKILL_COLOUR[finishing]="$CYAN"

    SEP="${DIM} ❯ ${RST}"

    if [[ -n "$FEATURE" || -n "$SKILL_NAME" || -n "$CONTEXT" ]]; then
        [[ -n "$FEATURE" ]] && CRUMB="${BOLD}${WHITE}${FEATURE}${RST}"
        if [[ -n "$SKILL_NAME" ]]; then
            [[ -n "$CRUMB" ]] && CRUMB="${CRUMB}${SEP}"
            COLOUR="${SKILL_COLOUR[$SKILL_NAME]:-$WHITE}"
            CRUMB="${CRUMB}${COLOUR}${SKILL_NAME}${RST}"
        fi
        if [[ -n "$CONTEXT" ]]; then
            [[ -n "$CRUMB" ]] && CRUMB="${CRUMB}${SEP}"
            CRUMB="${CRUMB}${DIM}${CONTEXT}${RST}"
        fi
    fi
fi

# ── Line 1: model, location, git changes, workflow ────────────────────

LINE1="${CYAN}[${MODEL}]${RST} ${BLUE}${LOCATION}${RST}"

GIT_EXTRA=""
[[ "$GIT_STAGED" -gt 0 ]] 2>/dev/null && GIT_EXTRA="${GREEN}+${GIT_STAGED}${RST}"
[[ "$GIT_MODIFIED" -gt 0 ]] 2>/dev/null && GIT_EXTRA="${GIT_EXTRA}${YELLOW}~${GIT_MODIFIED}${RST}"
[[ -n "$GIT_EXTRA" ]] && LINE1="${LINE1} ${GIT_EXTRA}"

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
