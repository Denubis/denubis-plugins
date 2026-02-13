#!/usr/bin/env bash
# workflow-state-wrapper.sh — Thin wrapper for workflow-state.sh.
#
# Resolves the real script path and checks it exists before calling.
# Skills call this directly instead of the WS=...; [ -x "$WS" ] && "$WS"
# compound command, so a single Bash permission allow rule can cover it.
#
# Usage (same args as workflow-state.sh):
#   workflow-state-wrapper.sh --skill "brainstorming" --context "exploring"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
WS="${SCRIPT_DIR}/workflow-state.sh"
[ -x "$WS" ] && exec "$WS" "$@"
