#!/usr/bin/env bash
# dispatcher-priority: 20
# PreToolUse:Bash route for concrete code-quality checks.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
exec python3 "$SCRIPT_DIR/code-quality-guard.py"
