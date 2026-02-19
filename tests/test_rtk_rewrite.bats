#!/usr/bin/env bats
# Tests for the RTK auto-rewrite PreToolUse:Bash hook.
# Feeds JSON to stdin and asserts on the rewritten command in output.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$REPO_ROOT/plugins/denubis-hook-rtk-rewrite/hooks/pretooluse-bash.sh"

# Helper: build JSON input for a command
make_input() {
    local cmd="$1"
    jq -n --arg c "$cmd" '{"tool_input":{"command":$c,"description":"test"}}'
}

# Helper: extract rewritten command from hook output
get_rewritten() {
    jq -r '.hookSpecificOutput.updatedInput.command // empty'
}

# ═══════════════════════════════════════════════════════════════════════
# Skip conditions
# ═══════════════════════════════════════════════════════════════════════

@test "skip: already using rtk" {
    run bash "$HOOK" <<< "$(make_input 'rtk git status')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skip: heredoc commands" {
    run bash "$HOOK" <<< "$(make_input 'git commit -m "$(cat <<EOF
message
EOF
)"')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skip: compound command starting with cd" {
    run bash "$HOOK" <<< "$(make_input 'cd /tmp && uv run pytest tests/')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skip: unrecognised command" {
    run bash "$HOOK" <<< "$(make_input 'whoami')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ═══════════════════════════════════════════════════════════════════════
# Git rewrites
# ═══════════════════════════════════════════════════════════════════════

@test "git: status" {
    result=$(make_input 'git status' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk git status" ]
}

@test "git: diff with args" {
    result=$(make_input 'git diff HEAD~3' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk git diff HEAD~3" ]
}

@test "git: log" {
    result=$(make_input 'git log --oneline -15' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk git log --oneline -15" ]
}

@test "git: non-matching subcommand passes through" {
    run bash "$HOOK" <<< "$(make_input 'git worktree list')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ═══════════════════════════════════════════════════════════════════════
# Python tooling — uv run preservation (regression tests for the venv bug)
# ═══════════════════════════════════════════════════════════════════════

@test "python: bare pytest" {
    result=$(make_input 'pytest tests/ -xvs' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk pytest tests/ -xvs" ]
}

@test "python: python -m pytest" {
    result=$(make_input 'python -m pytest tests/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk pytest tests/" ]
}

@test "python: uv run pytest preserves uv run" {
    result=$(make_input 'uv run pytest tests/test_foo.py -xvs' | bash "$HOOK" | get_rewritten)
    [ "$result" = "uv run rtk pytest tests/test_foo.py -xvs" ]
}

@test "python: bare ruff check" {
    result=$(make_input 'ruff check src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk ruff check src/" ]
}

@test "python: uv run ruff preserves uv run" {
    result=$(make_input 'uv run ruff check src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "uv run rtk ruff check src/" ]
}

@test "python: uv run ruff format preserves uv run" {
    result=$(make_input 'uv run ruff format --check src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "uv run rtk ruff format --check src/" ]
}

@test "python: uv run playwright preserves uv run" {
    result=$(make_input 'uv run playwright test' | bash "$HOOK" | get_rewritten)
    [ "$result" = "uv run rtk playwright test" ]
}

# ═══════════════════════════════════════════════════════════════════════
# Python tooling — ty and bandit
# ═══════════════════════════════════════════════════════════════════════

@test "python: uvx ty check" {
    result=$(make_input 'uvx ty check src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk err uvx ty check src/" ]
}

@test "python: uv run ty check preserves uv run" {
    result=$(make_input 'uv run ty check src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "uv run rtk err ty check src/" ]
}

@test "python: bare bandit" {
    result=$(make_input 'bandit -r src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk err bandit -r src/" ]
}

@test "python: uv run bandit preserves uv run" {
    result=$(make_input 'uv run bandit -r src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "uv run rtk err bandit -r src/" ]
}

@test "python: uvx bandit" {
    result=$(make_input 'uvx bandit -r src/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk err uvx bandit -r src/" ]
}

# ═══════════════════════════════════════════════════════════════════════
# Python tooling — uv subcommands (not uv run)
# ═══════════════════════════════════════════════════════════════════════

@test "python: uv pip list preserves uv" {
    result=$(make_input 'uv pip list' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk uv pip list" ]
}

@test "python: uv pip install preserves uv" {
    result=$(make_input 'uv pip install requests' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk uv pip install requests" ]
}

@test "python: uv sync" {
    result=$(make_input 'uv sync' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk summary uv sync" ]
}

@test "python: bare pip list" {
    result=$(make_input 'pip list' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk pip list" ]
}

# ═══════════════════════════════════════════════════════════════════════
# Environment variable prefix preservation
# ═══════════════════════════════════════════════════════════════════════

@test "env prefix: preserved on rewrite" {
    result=$(make_input 'TEST_SESSION_ID=2 pytest tests/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "TEST_SESSION_ID=2 rtk pytest tests/" ]
}

@test "env prefix: preserved with uv run" {
    result=$(make_input 'PYTHONDONTWRITEBYTECODE=1 uv run pytest tests/' | bash "$HOOK" | get_rewritten)
    [ "$result" = "PYTHONDONTWRITEBYTECODE=1 uv run rtk pytest tests/" ]
}

# ═══════════════════════════════════════════════════════════════════════
# GitHub CLI
# ═══════════════════════════════════════════════════════════════════════

@test "gh: pr view" {
    result=$(make_input 'gh pr view 123' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk gh pr view 123" ]
}

@test "gh: non-matching subcommand passes through" {
    run bash "$HOOK" <<< "$(make_input 'gh auth login')"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ═══════════════════════════════════════════════════════════════════════
# File operations
# ═══════════════════════════════════════════════════════════════════════

@test "file: cat → rtk read" {
    result=$(make_input 'cat README.md' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk read README.md" ]
}

@test "file: head -10 → rtk read --max-lines" {
    result=$(make_input 'head -10 README.md' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk read README.md --max-lines 10" ]
}

@test "file: ls" {
    result=$(make_input 'ls -la' | bash "$HOOK" | get_rewritten)
    [ "$result" = "rtk ls -la" ]
}

# ═══════════════════════════════════════════════════════════════════════
# Output structure
# ═══════════════════════════════════════════════════════════════════════

@test "output: valid JSON with correct structure" {
    output=$(make_input 'git status' | bash "$HOOK")
    echo "$output" | jq empty
    decision=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$decision" = "allow" ]
    reason=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecisionReason')
    [ "$reason" = "RTK auto-rewrite" ]
    event=$(echo "$output" | jq -r '.hookSpecificOutput.hookEventName')
    [ "$event" = "PreToolUse" ]
}

@test "output: updatedInput preserves non-command fields" {
    input='{"tool_input":{"command":"git status","description":"check status","timeout":5000}}'
    output=$(echo "$input" | bash "$HOOK")
    desc=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.description')
    [ "$desc" = "check status" ]
    timeout=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.timeout')
    [ "$timeout" = "5000" ]
}
