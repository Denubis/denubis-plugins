#!/usr/bin/env bash
# Run every lint, format, type and complexity check over the tree and report.
#
# Warn-only by default (Brian, 2026-10-21: "I suspect we'll need to be warn
# only before we have a massive refactor"): each tool's result is printed and
# the script exits 0. Set LINT_STRICT=1 to exit non-zero when any tool fails;
# that is the switch to flip once the baseline recorded in pyproject.toml is
# paid down. The blocking commit gates (plugin validation, pytest, gitleaks,
# broken-file checks) live in .pre-commit-config.yaml and do not call this.
#
# Every tool runs through the uv-locked dev group so the versions here can
# never disagree with uv.lock. Nothing here autofixes: `ruff format` only
# checks, so the py314 formatter never rewrites a py311 script by surprise
# (the per-file-target-version table in pyproject.toml is the real guard).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT="${LINT_STRICT:-0}"
failed=()

run() {
    local name="$1"
    shift
    printf '\n== %s\n' "$name"
    if "$@"; then
        printf -- '-- %s: ok\n' "$name"
    else
        printf -- '-- %s: FAILED (exit %s)\n' "$name" "$?"
        failed+=("$name")
    fi
}

cd "$ROOT"

run "ruff check" uv run --frozen ruff check .
run "ruff format --check" uv run --frozen ruff format --check .
# ty resolves the workspace members (crash_recovery, workflow_statusline) and
# their dependencies only when they are installed; --all-packages installs them.
run "ty check" uv run --frozen --all-packages ty check
run "complexipy (max 15)" uv run --frozen complexipy --failed --plain .
run "vulture" uv run --frozen vulture

printf '\n== summary\n'
if [ "${#failed[@]}" -eq 0 ]; then
    printf 'all checks passed\n'
    exit 0
fi
printf 'failed: %s\n' "${failed[*]}"
if [ "$STRICT" = "1" ]; then
    exit 1
fi
printf 'warn-only mode (LINT_STRICT=1 to fail)\n'
exit 0
