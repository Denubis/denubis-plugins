#!/usr/bin/env bash
# Launch a human-triggered Fable consultation beside the caller's tmux pane.
#
# Authority:
# /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-skill-skills-upstream-sync/e4421bb3-2615-4b37-944c-86e5dd65eccc.jsonl:12
# Resolve with:
# cc-search-chats context 0a1beea2-2d45-455f-9ced-9ec278afb8e8 --json
#
# The deny list removes the known mutation, orchestration, network, and MCP
# surfaces. It is not a permanent proof because the upstream tool namespace can
# change. Verify the observed tool surface before giving the advisor repository
# work. Read the response from the JSONL transcript, not the TUI viewport. No
# fallback model is selected automatically.
#
# Usage: fable-advisor-spawn.sh [cwd] [model]
#          cwd    directory the advisor starts in (default: $PWD)
#          model  advisor model (default: claude-fable-5)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cwd="${1:-$PWD}"
model="${2:-claude-fable-5}"

[ -d "$cwd" ] || { echo "cwd not found: $cwd" >&2; exit 1; }
[ -n "${TMUX:-}" ] || { echo "not inside tmux — the advisor needs a pane" >&2; exit 1; }
command -v claude >/dev/null 2>&1 || { echo "claude not on PATH" >&2; exit 1; }

# This list fails open when upstream adds or renames a tool. The launcher's
# verification prompt is therefore part of the boundary.
DENIED=(Bash BashOutput KillShell
        Write Edit NotebookEdit
        Task Agent Workflow
        CronCreate CronDelete CronList ScheduleWakeup RemoteTrigger
        Skill DesignSync
        EnterWorktree ExitWorktree EnterPlanMode ExitPlanMode
        Artifact AskUserQuestion SendMessage
        Monitor PushNotification TaskOutput TaskStop
        WebFetch WebSearch
        TodoWrite TaskCreate TaskUpdate
        # MCP tools can disclose repository content or expose new callable tools.
        "mcp__*"
        # Built-in MCP resource tools do not match the mcp__* namespace.
        ListMcpResourcesTool ReadMcpResourceTool ReadMcpResourceDirTool)

BRIEF="You are a consulted advisor, not the implementer. Advise; do not modify files, run commands, delegate work, or broaden the task. The operator will verify your callable tool surface before substantive work.

Review the supplied question against the repository as it exists now. Treat agent statements as claims to test. Treat a human ruling as authority to act, but return contradictions or ambiguity to the human instead of silently working around them.

Report only findings that could change the decision. For each, state the consequence, cite the exact file and line, and distinguish direct observation from inference. If the evidence is sufficient and no finding changes the decision, say so plainly. Do not narrate your reasoning or perform generic self-critique."

# Target the caller's pane; tmux's active window may be unrelated.
pane="$(tmux split-window -h -c "$cwd" -P -F '#{pane_id}' \
  ${TMUX_PANE:+-t "$TMUX_PANE"} \
  claude --model "$model" \
         --disallowed-tools "${DENIED[@]}" \
         --disable-slash-commands \
         --append-system-prompt "$BRIEF")"

# Give the session a moment to start or fail, then confirm it is actually alive.
# An unavailable model exits early; a dead pane means no advisor, and saying so
# is the point.
sleep 6
if ! tmux list-panes -a -F '#{pane_id}' 2>/dev/null | grep -qx -- "$pane"; then
  echo "advisor pane died on startup — '$model' is likely unavailable" >&2
  echo "No fallback model was selected. Choose one explicitly, re-run with its" >&2
  echo "model identifier, and label the consultation with the model used." >&2
  exit 2
fi

echo "pane:     $pane"
echo "model:    $model"
echo "cwd:      $cwd"
echo "denied:   ${#DENIED[@]} tools incl. Bash/Write/Edit/Workflow/Cron*/Skill"
echo "VERIFY:   ask the advisor to enumerate its surface and attempt a write."
echo "          Continue only when the observed surface matches the boundary."
echo
echo "drive it with the bundled sender:"
echo "  $SCRIPT_DIR/advisor-send.sh $pane 'your consultation'"
echo "  $SCRIPT_DIR/advisor-send.sh $pane - < brief.md   # multi-line from stdin"
echo
echo "ARM A MONITOR — a pane advisor finishes silently, with no notification:"
echo "  watch its transcript stop growing, or poll the pane title for idle."
echo
echo "READ ITS REPLY FROM ITS TRANSCRIPT, NOT THE PANE — the TUI redraws in"
echo "place, so capture-pane returns the viewport, not what it said:"
echo "  ls -t ~/.claude/projects/\$(pwd | sed 's#/#-#g')/*.jsonl | head -1"
