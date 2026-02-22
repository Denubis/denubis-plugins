#!/usr/bin/env bash
# Claude Code wrapper — applies --disallowedTools for tools replaced by plugins.
# Source of truth: managed in denubis-plan-and-execute plugin.
#
# Tools disabled:
#   NotebookEdit       — no Jupyter notebook usage in plugin workflows
#   EnterPlanMode      — replaced by skill-based planning (starting-a-design-plan)
#   ExitPlanMode       — paired with EnterPlanMode, also replaced
#   EnterWorktree      — skills use 'git worktree add' via Bash directly
#   ListMcpResourcesTool — meta-tool, rarely needed
#   ReadMcpResourceTool  — meta-tool, rarely needed
#
# Usage:
#   Fish: alias claude '~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh'
#   Or via delegator: alias claude '~/.claude/bin/claude-wrapper'

set -euo pipefail

DISALLOWED_TOOLS="NotebookEdit,EnterPlanMode,ExitPlanMode,EnterWorktree,ListMcpResourcesTool,ReadMcpResourceTool"

# Find real claude binary — standard install location, overridable via env
REAL_CLAUDE="${CLAUDE_REAL_BINARY:-$HOME/.local/bin/claude}"

if [[ ! -x "$REAL_CLAUDE" ]]; then
    echo "error: claude binary not found at $REAL_CLAUDE" >&2
    echo "Set CLAUDE_REAL_BINARY to the correct path." >&2
    exit 1
fi

exec "$REAL_CLAUDE" --disallowedTools "$DISALLOWED_TOOLS" "$@"
