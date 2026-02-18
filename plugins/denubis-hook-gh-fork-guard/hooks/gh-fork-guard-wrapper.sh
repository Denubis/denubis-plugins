#!/usr/bin/env bash
# Wrapper for gh-fork-guard.py — used by the pretooluse-bash dispatcher.
# Reads JSON from stdin, passes to the Python script, outputs JSON to stdout.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
exec uv run python3 "$SCRIPT_DIR/gh-fork-guard.py"
