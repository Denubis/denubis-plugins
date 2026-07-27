#!/usr/bin/env bash
# Spawn a Fable advisor in a tmux pane beside the caller's.
#
# The advisor is a full Claude Code session on a different model, briefed to
# advise and denied the tools to implement. That claim is EMPIRICALLY VERIFIED,
# not asserted: the last verification (2026-07-21, second run) confirmed a
# callable surface of Glob, Grep, Read, ReportFindings and EndConversation, with
# Write returning "No such tool available: Write. Write exists but is not
# enabled in this context." Two earlier versions of this header made the same
# claim while it was false.
#
# EndConversation is deliberately available: an advisor that cannot end its own
# session is worse than one that can, so it is a hard include on safety grounds
# (operator ruling, 2026-07-21) and is absent from the deny list below.
#
# The first run of that same verification found EndConversation present in the
# advisor's schema WHILE the deny list still named it — the harness re-injects
# deferred tools, and no flag on the command line governs that. The list had not
# been edited; the surface had moved underneath it. So re-verification cannot be
# keyed to changes in this list, because upstream renames never touch it:
# RE-VERIFY AT THE START OF EACH CONSULTATION. See VERIFY below.
#
# Two mechanisms carry it:
#
#   --disallowed-tools   DENIES the named tools. This is the only flag that
#                        restricts; --allowed-tools means "pre-approve these
#                        without prompting" and does NOT hide anything else.
#                        Getting that backwards was tried, and an advisor under
#                        the resulting "allowlist" wrote a file on its first
#                        attempt.
#   --append-system-prompt  carries the role brief.
#
# This was a blocklist until a Fable advisor, consulted under it, demonstrated
# it was theatre (2026-07-21). It kept Bash, so shell writes succeeded with no
# prompt, and it named twelve tools while missing Workflow (which spawns agents
# inheriting the session model, so both fan-out AND Fable spend multiplication),
# CronCreate and ScheduleWakeup (unattended Fable runs, which the cost gate
# forbids in terms), Skill, DesignSync, and the worktree tools. Four of the
# names it did block do not exist in the advisor's surface at all. A name-based
# blacklist against a moving namespace fails open on every rename and addition.
#
# Bash is NOT granted. The advisor grounds findings with Read and Grep, and its
# output is recovered from its session transcript under ~/.claude/projects/,
# never from the pane: the Claude Code TUI redraws in place, so capture-pane
# yields the viewport and not the transcript, even with `-S -` (verified).
#
# Fable-tier access is intermittent (it lapsed through June 2026), so this
# script never silently substitutes a fallback: if Fable does not come up, it
# says so and exits non-zero, and choosing Opus 4.8 instead is the operator's
# call, taken knowingly. A silently-substituted advisor is worthless, because
# the entire value of the consultation is that it is a different model.
#
# COST: Fable-tier invocations are human-triggered only (the cost gate in
# writing-claude-directives/model-tier-notes.md). This script is invoked by a
# human through its skill. Nothing may call it automatically.
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

# Deny list, derived from an advisor enumerating its own loaded schema
# (2026-07-21) rather than from memory. A blacklist fails open on renames and
# additions, so this is re-verified empirically on every material change: spawn
# an advisor and ask it to enumerate its surface and attempt a write. That
# consultation IS the test, and it has caught two wrong mechanisms already.
#
# KNOWN RESIDUAL HOLE: a PreToolUse hook approver in the advisor's session
# auto-approved a Bash call ("approver: pipeline_safe") independently of these
# flags. Denying Bash outright closes that path here, but the hook pipeline
# remains a second surface no flag on this line controls.
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
        # MCP: the auth stubs are callable, and their own descriptions say a
        # completed OAuth makes "the server's real tools become available
        # automatically" — tools a static name list could never have anticipated.
        # context7 is an outbound channel: query text leaves the machine, which
        # is a disclosure surface when the advisor is reading a private repo.
        "mcp__*"
        # Generic MCP resource tools are built-in, so they do NOT match
        # "mcp__*" and still reach an attached server. An advisor found
        # this residual after the wildcard landed.
        ListMcpResourcesTool ReadMcpResourceTool ReadMcpResourceDirTool)

BRIEF="You are a consulted advisor in a supervised loop, running on a different model from the session that dispatched you. You are neither the implementer nor the verifier; both have already had their turn, and their output is what you are being asked about.

Advise. Do not implement. You have read and search tools only; there is no write or shell surface to work around.

Everything you are told carries provenance, and all of it may be questioned. What differs is how a challenge resolves. A supervisor assertion is a claim to test, not a fact to build on: the supervisor's searches stop one level short routinely, grepping one file instead of following the call chain, or matching its own vocabulary instead of the repository's, so if the repository disagrees the repository wins and finding an assertion wrong is the job. A human ruling is the human's judgement: if it looks unwise, contradicts something else, or is unclear, say so plainly and let it go back to them rather than working around it. Nothing here is beyond question; the human is the source of judgement, not the source of facts.

Ground every finding in the repository as it exists now: cite file:line and quote verbatim. A finding whose citation cannot be resolved will be discarded, so cite precisely rather than broadly. Where you are inferring rather than reading, say so.

Report everything you find, each with a severity and your confidence. Do not filter to what you judge important; filtering happens downstream, and a finding dropped here is not recoverable.

Stay in scope. Do not propose refactors, redesigns, or improvements beyond what you were asked about. 'This is fine' is a complete answer.

Give the findings and the evidence for them. Do not narrate your reasoning process."

# Split the CALLER's pane, not tmux's active one. Without -t, tmux splits
# whatever window is currently active, which is the window the operator happens
# to be looking at rather than the one that ran this script. Since the caller is
# normally a Claude Code session in a background window, the advisor landed on
# top of unrelated work (observed 2026-07-21). $TMUX_PANE is set by tmux in
# every pane, so it names the caller precisely.
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
  echo "Fable access is intermittent. Falling back to Opus 4.8 is the operator's" >&2
  echo "call: re-run as 'fable-advisor-spawn.sh \"$cwd\" claude-opus-4-8' and" >&2
  echo "label the consultation as the fallback model, never as Fable." >&2
  exit 2
fi

echo "pane:     $pane"
echo "model:    $model"
echo "cwd:      $cwd"
echo "denied:   ${#DENIED[@]} tools incl. Bash/Write/Edit/Workflow/Cron*/Skill"
echo "VERIFY:   ask the advisor to enumerate its surface and attempt a write."
echo "          Do this EVERY consultation, not only when the list changes:"
echo "          the harness has re-injected a denied tool with no edit here."
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
