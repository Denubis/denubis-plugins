#!/usr/bin/env bash
# Claude Code wrapper — applies --disallowedTools and agent team config.
# Source of truth: managed in denubis-plan-and-execute plugin.
#
# Tools disabled:
#   NotebookEdit       — no Jupyter notebook usage in plugin workflows
#   EnterPlanMode      — replaced by skill-based planning (starting-a-design-plan)
#   ExitPlanMode       — paired with EnterPlanMode, also replaced
#   EnterWorktree      — skills use 'git worktree add' via Bash directly
#   ExitWorktree       — paired with EnterWorktree
#   ListMcpResourcesTool — meta-tool, rarely needed
#   ReadMcpResourceTool  — meta-tool, rarely needed
#   RemoteTrigger        — cloud cron, not used
#   CronCreate/Delete/List — session-scoped cron, not used
#
# Agent teams:
#   Enabled via CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
#   teammate-mode=auto — detects $TMUX (byobu) and uses split panes if available
#
# Post-session transcript:
#   Fresh interactive sessions get a pre-assigned --session-id. After exit,
#   prompts "Press Enter to archive transcript" which launches a new interactive
#   session running /transcript <uuid>. Ctrl-C skips. Resumed/print/bare
#   sessions are excluded (resumed sessions get a reminder instead).
#
# Usage:
#   Fish: alias claude '~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh'
#   Or via delegator: alias claude '~/.claude/bin/claude-wrapper'

set -euo pipefail

DISALLOWED_TOOLS="NotebookEdit,EnterPlanMode,ExitPlanMode,EnterWorktree,ExitWorktree,ListMcpResourcesTool,ReadMcpResourceTool,RemoteTrigger,CronCreate,CronDelete,CronList"

# Enable experimental agent teams
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Find real claude binary — standard install location, overridable via env
REAL_CLAUDE="${CLAUDE_REAL_BINARY:-$HOME/.local/bin/claude}"

if [[ ! -x "$REAL_CLAUDE" ]]; then
    echo "error: claude binary not found at $REAL_CLAUDE" >&2
    echo "Set CLAUDE_REAL_BINARY to the correct path." >&2
    exit 1
fi

# --- Post-session transcript archival ---
# Only auto-archive fresh interactive sessions. Resume/continue/print sessions
# get a reminder instead.
SHOULD_TRANSCRIPT=true
IS_RESUMED=false
SESSION_ID="$(uuidgen)"
EXTRA_ARGS=("--session-id" "$SESSION_ID")

for arg in "$@"; do
    case "$arg" in
        --resume|-r|--continue|-c)
            SHOULD_TRANSCRIPT=false
            IS_RESUMED=true
            EXTRA_ARGS=()
            break
            ;;
        -p|--print|--session-id|--bare|--no-session-persistence)
            SHOULD_TRANSCRIPT=false
            IS_RESUMED=false
            EXTRA_ARGS=()
            break
            ;;
    esac
done

"$REAL_CLAUDE" --disallowedTools "$DISALLOWED_TOOLS" --teammate-mode=auto "${EXTRA_ARGS[@]}" "$@"
EXIT_CODE=$?

if [[ "$SHOULD_TRANSCRIPT" == true ]]; then
    echo ""
    echo "Press Enter to archive transcript, or Ctrl-C to skip."
    if read -r 2>/dev/null; then
        # Launch a fresh interactive session with /transcript and the session UUID.
        # The transcript skill reads the JSONL directly — no --resume needed.
        "$REAL_CLAUDE" --disallowedTools "$DISALLOWED_TOOLS" "/transcript $SESSION_ID"
    fi
elif [[ "$IS_RESUMED" == true ]]; then
    # TODO: resume-aware archiving — extract session ID from args or use --continue's session
    echo ""
    echo "Reminder: resumed sessions aren't auto-archived. Run /transcript before exiting next time."
fi

exit $EXIT_CODE
