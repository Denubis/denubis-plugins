#!/usr/bin/env bash
# dispatcher-priority: 10
# PreToolUse:Bash hook for gh-fork-guard — blocks gh commands targeting non-fork repos.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
exec uv run python3 "$SCRIPT_DIR/gh-fork-guard.py"
