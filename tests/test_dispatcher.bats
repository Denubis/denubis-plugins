#!/usr/bin/env bats
# Tests for the PreToolUse:Bash dispatcher.
# Uses a temporary drop directory to avoid interfering with real hooks.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
DISPATCHER="$REPO_ROOT/plugins/denubis-hook-pretooluse-dispatcher/hooks/pretooluse-bash-dispatcher.sh"

setup() {
    export DROP_DIR_ORIG="$HOME/.claude/hooks/pretooluse-bash.d"
    export TEST_DROP_DIR="$(mktemp -d)"
    # Override the drop dir by creating a wrapper that sets the var
    export DISPATCHER_WRAPPER="$(mktemp)"
    cat > "$DISPATCHER_WRAPPER" <<WRAPPER
#!/usr/bin/env bash
# Override drop dir for testing
export HOME_BACKUP="\$HOME"
# Create a fake HOME so the dispatcher uses our test drop dir
export FAKE_HOME="\$(mktemp -d)"
mkdir -p "\$FAKE_HOME/.claude/hooks"
ln -sf "$TEST_DROP_DIR" "\$FAKE_HOME/.claude/hooks/pretooluse-bash.d"
export HOME="\$FAKE_HOME"
source "$DISPATCHER"
WRAPPER
    chmod +x "$DISPATCHER_WRAPPER"
}

teardown() {
    rm -rf "$TEST_DROP_DIR" "$DISPATCHER_WRAPPER"
}

SAMPLE_INPUT='{"tool_name":"Bash","tool_input":{"command":"git status"}}'

# ---------------------------------------------------------------------------
# Empty drop directory
# ---------------------------------------------------------------------------
@test "empty drop dir exits silently" {
    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Single hook: pass-through
# ---------------------------------------------------------------------------
@test "hook that exits 0 with no output passes through" {
    cat > "$TEST_DROP_DIR/10-noop" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
exit 0
HOOK
    chmod +x "$TEST_DROP_DIR/10-noop"

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Single hook: deny
# ---------------------------------------------------------------------------
@test "deny hook returns deny immediately" {
    cat > "$TEST_DROP_DIR/10-deny" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
cat <<EOF
{"hookSpecificOutput":{"permissionDecision":"deny"},"systemMessage":"blocked by test"}
EOF
HOOK
    chmod +x "$TEST_DROP_DIR/10-deny"

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    result=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$result" = "deny" ]
}

# ---------------------------------------------------------------------------
# Single hook: allow with updatedInput
# ---------------------------------------------------------------------------
@test "allow hook with updatedInput passes through" {
    cat > "$TEST_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"test rewrite","updatedInput":{"command":"rtk git status"}}}
EOF
HOOK
    chmod +x "$TEST_DROP_DIR/50-rewrite"

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    decision=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$decision" = "allow" ]
    cmd=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.command')
    [ "$cmd" = "rtk git status" ]
}

# ---------------------------------------------------------------------------
# Two hooks: deny takes priority over allow
# ---------------------------------------------------------------------------
@test "deny hook stops processing before allow hook" {
    cat > "$TEST_DROP_DIR/10-deny" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"deny"},"systemMessage":"denied"}'
HOOK
    chmod +x "$TEST_DROP_DIR/10-deny"

    cat > "$TEST_DROP_DIR/50-allow" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"allow","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$TEST_DROP_DIR/50-allow"

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    decision=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$decision" = "deny" ]
}

# ---------------------------------------------------------------------------
# Two hooks: advisory + rewrite merged
# ---------------------------------------------------------------------------
@test "advisory context and updatedInput merge from separate hooks" {
    cat > "$TEST_DROP_DIR/10-advisory" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"additionalContext":"fork policy reminder"}}'
HOOK
    chmod +x "$TEST_DROP_DIR/10-advisory"

    cat > "$TEST_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"allow","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$TEST_DROP_DIR/50-rewrite"

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"fork policy"* ]]
    cmd=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.command')
    [ "$cmd" = "rtk git status" ]
}

# ---------------------------------------------------------------------------
# Non-executable files are skipped
# ---------------------------------------------------------------------------
@test "non-executable files in drop dir are skipped" {
    cat > "$TEST_DROP_DIR/README" <<'HOOK'
This is not a hook script.
HOOK
    # Deliberately NOT chmod +x

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ---------------------------------------------------------------------------
# Hook with invalid JSON output is skipped
# ---------------------------------------------------------------------------
@test "hook with invalid JSON output is skipped" {
    cat > "$TEST_DROP_DIR/10-bad" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo "not json"
HOOK
    chmod +x "$TEST_DROP_DIR/10-bad"

    cat > "$TEST_DROP_DIR/50-good" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"additionalContext":"from good hook"}}'
HOOK
    chmod +x "$TEST_DROP_DIR/50-good"

    run bash -c "echo '$SAMPLE_INPUT' | bash '$DISPATCHER_WRAPPER'"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"from good hook"* ]]
}
