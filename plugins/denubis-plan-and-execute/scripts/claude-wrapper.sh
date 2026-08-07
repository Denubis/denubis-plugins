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
#   ALSO set in ~/.claude/settings.json under env, which covers bare `claude`
#   as well as claudew. The export below is therefore redundant today and is
#   kept because the architecture docs describe it as a wrapper property.
#   To turn agent teams off you must change BOTH places.
#
# Post-session transcript:
#   Fresh interactive sessions get a pre-assigned --session-id. After exit,
#   prompts "Press Enter to archive transcript" only if the project already
#   does transcripting (ai_transcripts/ or .ai-transcripts/ exists in PWD or
#   git root). On Enter, invokes claude-research-transcript directly — no
#   second claude session. Ctrl-C skips. Resumed/print/bare sessions are
#   excluded (resumed sessions get the reminder only when in a transcripting
#   project).
#
# Usage:
#   Fish: alias claude '~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh'
#   Or via delegator: alias claude '~/.claude/bin/claude-wrapper'

set -euo pipefail

DISALLOWED_TOOLS="NotebookEdit,EnterPlanMode,ExitPlanMode,EnterWorktree,ExitWorktree,ListMcpResourcesTool,ReadMcpResourceTool,RemoteTrigger,CronCreate,CronDelete,CronList"

# Enable experimental agent teams (also set in ~/.claude/settings.json env —
# change both to disable)
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

# True when the current project already does transcripting.
has_transcripts_dir() {
    local dir
    for dir in "$PWD/ai_transcripts" "$PWD/.ai-transcripts"; do
        [[ -d "$dir" ]] && return 0
    done
    local git_root
    git_root="$(git rev-parse --show-toplevel 2>/dev/null)" || return 1
    [[ -n "$git_root" ]] || return 1
    for dir in "$git_root/ai_transcripts" "$git_root/.ai-transcripts"; do
        [[ -d "$dir" ]] && return 0
    done
    return 1
}

# --- crash-recovery liveness file write (atomic) ---
CR_RUN_DIR="${CRASH_RECOVERY_RUN_DIR:-$HOME/.claude/run}"
mkdir -p "$CR_RUN_DIR"
# Exported so the SessionStart marker-update hook (update-live-marker.py), a
# descendant of this wrapper via claude, inherits it and knows which marker to
# rewrite. The child inherits $$ → value is <wrapper_pid>.live.
export CR_LIVE_FILE="$CR_RUN_DIR/$$.live"
CR_LIVE_TMP="$CR_RUN_DIR/$$.live.tmp"

# Comm-safe /proc/<pid>/stat starttime (field 22). field 2 (comm) may contain
# spaces/parens, so strip through the last ") " before tokenising; starttime is
# then the 20th token of the remainder (fields 3..22). See DR4.
_proc_starttime() {  # $1 = pid; echoes field-22 starttime or nothing
    local stat rest
    stat=$(cat "/proc/$1/stat" 2>/dev/null) || return 0
    rest=${stat##*) }          # strip through the last ") " — defeats comm-with-spaces
    # shellcheck disable=SC2086
    set -- $rest               # $1=state(field3) ... $20=starttime(field22)
    printf '%s' "${20-}"
}

# Effective session id for the marker: a --resume/-r uuid, else a --session-id
# uuid, else (fresh interactive — we generated SESSION_ID into EXTRA_ARGS) the
# generated uuid, else empty (line omitted). Loose validation; reader revalidates.
CR_SESSION_ID=""
_cr_prev=""
for _cr_arg in "$@"; do
    case "$_cr_prev" in --resume|-r) CR_SESSION_ID="$_cr_arg"; break ;; esac
    _cr_prev="$_cr_arg"
done
if [ -z "$CR_SESSION_ID" ]; then
    _cr_prev=""
    for _cr_arg in "$@"; do
        case "$_cr_prev" in --session-id) CR_SESSION_ID="$_cr_arg"; break ;; esac
        _cr_prev="$_cr_arg"
    done
fi
if [ -z "$CR_SESSION_ID" ] && [ "${#EXTRA_ARGS[@]}" -gt 0 ]; then
    CR_SESSION_ID="$SESSION_ID"
fi

{
    printf 'cwd=%s\n' "$PWD"
    printf 'started=%s\n' "$(date +%s)"
    printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)"
    [ -n "$CR_SESSION_ID" ] && printf 'session_id=%s\n' "$CR_SESSION_ID"
    CR_START_TIME="$(_proc_starttime $$)"
    [ -n "$CR_START_TIME" ] && printf 'start_time=%s\n' "$CR_START_TIME"
} > "$CR_LIVE_TMP"
mv "$CR_LIVE_TMP" "$CR_LIVE_FILE"  # atomic via rename(2) on the same filesystem
# --- end crash-recovery liveness file write ---

"$REAL_CLAUDE" --disallowedTools "$DISALLOWED_TOOLS" --teammate-mode=auto "${EXTRA_ARGS[@]}" "$@" || EXIT_CODE=$?
EXIT_CODE=${EXIT_CODE:-0}

# --- crash-recovery liveness file cleanup (DR8) ---
# Remove the marker on clean (0) or Ctrl-C (130) exit; any other code (137
# SIGKILL, 139 SIGSEGV, generic non-zero) leaves it in place as evidence of an
# abnormal termination. This MUST run BEFORE the transcript-archive prompt
# below: that prompt blocks on `read`, and a terminal closed at the prompt would
# otherwise strand the marker on a cleanly-concluded session — which triage then
# misreads as a crash (the archive-prompt-close false positive). Archiving keys
# off SESSION_ID/TRANSCRIPT_PATH, not the marker, so removing it here is safe.
if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 130 ]; then
    rm -f "$CR_LIVE_FILE"
fi
# --- end crash-recovery liveness file cleanup ---

# The transcript-archive prompt only makes sense for clean exits. Before the
# || EXIT_CODE=$? fix at line 103, set -e made these blocks unreachable on
# non-zero exits; that guard is now explicit to preserve the intended contract.
if [[ "$EXIT_CODE" -eq 0 ]]; then
    if [[ "$SHOULD_TRANSCRIPT" == true ]] && has_transcripts_dir; then
        # Locate the JSONL by exact session_id match — deterministic against
        # concurrent sessions in other worktrees.
        TRANSCRIPT_PATH=""
        for f in "$HOME"/.claude/projects/*/"$SESSION_ID".jsonl; do
            if [[ -f "$f" ]]; then
                TRANSCRIPT_PATH="$f"
                break
            fi
        done

        if [[ -n "$TRANSCRIPT_PATH" ]]; then
            echo ""
            echo "Press Enter to archive transcript, or Ctrl-C to skip."
            if read -r 2>/dev/null; then
                if command -v claude-research-transcript >/dev/null 2>&1; then
                    claude-research-transcript archive \
                        --transcript "$TRANSCRIPT_PATH" \
                        --session-id "$SESSION_ID"
                else
                    echo "warning: claude-research-transcript not on PATH; skipping archive." >&2
                fi
            fi
        fi
    elif [[ "$IS_RESUMED" == true ]] && has_transcripts_dir; then
        echo ""
        echo "Reminder: resumed sessions aren't auto-archived. Run /transcript before exiting next time."
    fi
fi

exit $EXIT_CODE
