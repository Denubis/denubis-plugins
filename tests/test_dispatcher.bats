#!/usr/bin/env bats
# Tests for the PreToolUse:Bash dispatcher.
# Uses environment variable overrides to isolate from real hooks.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
# The dispatcher is a pure-stdlib Python script; invoke via `uv run python`
# (the same entrypoint hooks.json uses). uv is silent on stderr in a synced
# project, so the `[ -z "$output" ]` assertions stay valid.
DISPATCHER="$REPO_ROOT/plugins/denubis-hook-pretooluse-dispatcher/hooks/pretooluse-bash-dispatcher.py"

setup() {
    export TEST_DIR="$(mktemp -d)"
    export DISPATCHER_DROP_DIR="$TEST_DIR/drop"
    export DISPATCHER_MARKETPLACE_DIR="$TEST_DIR/marketplaces"
    export DISPATCHER_SETTINGS_FILE="$TEST_DIR/settings.json"
    export DISPATCHER_CACHE_FILE="$TEST_DIR/cache"

    mkdir -p "$DISPATCHER_DROP_DIR"
    mkdir -p "$DISPATCHER_MARKETPLACE_DIR"

    # Default settings — no enabled plugins
    echo '{"enabledPlugins":{}}' > "$DISPATCHER_SETTINGS_FILE"
}

teardown() {
    rm -rf "$TEST_DIR"
}

SAMPLE_INPUT='{"tool_name":"Bash","tool_input":{"command":"git status"}}'

# ── Helper: create a plugin convention file ──

create_plugin_hook() {
    local marketplace="$1" plugin="$2" priority="$3" script_body="$4"
    local dir="$DISPATCHER_MARKETPLACE_DIR/$marketplace/plugins/$plugin/hooks"
    mkdir -p "$dir"
    cat > "$dir/pretooluse-bash.sh" <<HOOK
#!/usr/bin/env bash
# dispatcher-priority: $priority
$script_body
HOOK
    chmod +x "$dir/pretooluse-bash.sh"
}

enable_plugin() {
    local plugin="$1" marketplace="$2"
    local key="${plugin}@${marketplace}"
    local tmp
    tmp=$(jq --arg k "$key" '.enabledPlugins[$k] = true' "$DISPATCHER_SETTINGS_FILE")
    echo "$tmp" > "$DISPATCHER_SETTINGS_FILE"
}

# ═══════════════════════════════════════════════════════════════════════
# Drop directory tests (backwards compatibility)
# ═══════════════════════════════════════════════════════════════════════

@test "empty state exits silently" {
    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "drop dir: hook that exits 0 with no output passes through" {
    cat > "$DISPATCHER_DROP_DIR/10-noop" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
exit 0
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/10-noop"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "drop dir: deny hook returns deny immediately" {
    cat > "$DISPATCHER_DROP_DIR/10-deny" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"deny"},"systemMessage":"blocked by test"}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/10-deny"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    result=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$result" = "deny" ]
}

@test "drop dir: allow hook with updatedInput passes through" {
    cat > "$DISPATCHER_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"test rewrite","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-rewrite"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    decision=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$decision" = "allow" ]
    cmd=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.command')
    [ "$cmd" = "rtk git status" ]
}

@test "drop dir: deny stops processing before allow" {
    cat > "$DISPATCHER_DROP_DIR/10-deny" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"deny"},"systemMessage":"denied"}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/10-deny"

    cat > "$DISPATCHER_DROP_DIR/50-allow" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"allow","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-allow"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    decision=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$decision" = "deny" ]
}

@test "drop dir: advisory context and updatedInput merge" {
    cat > "$DISPATCHER_DROP_DIR/10-advisory" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"additionalContext":"fork policy reminder"}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/10-advisory"

    cat > "$DISPATCHER_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"allow","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-rewrite"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"fork policy"* ]]
    cmd=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.command')
    [ "$cmd" = "rtk git status" ]
}

@test "drop dir: non-executable files are skipped" {
    echo "This is not a hook script." > "$DISPATCHER_DROP_DIR/README"
    # Deliberately NOT chmod +x

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "drop dir: invalid JSON output is skipped" {
    cat > "$DISPATCHER_DROP_DIR/10-bad" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo "not json"
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/10-bad"

    cat > "$DISPATCHER_DROP_DIR/50-good" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"additionalContext":"from good hook"}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-good"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"from good hook"* ]]
}

# ═══════════════════════════════════════════════════════════════════════
# Plugin auto-discovery tests
# ═══════════════════════════════════════════════════════════════════════

@test "plugin: disabled plugin convention file is not discovered" {
    create_plugin_hook "test-mp" "test-plugin" 10 \
        'cat > /dev/null; echo "{\"hookSpecificOutput\":{\"additionalContext\":\"should not appear\"}}"'
    # Plugin NOT enabled in settings

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "plugin: enabled plugin convention file is discovered and run" {
    create_plugin_hook "test-mp" "test-plugin" 10 \
        'cat > /dev/null; echo "{\"hookSpecificOutput\":{\"additionalContext\":\"from plugin\"}}"'
    enable_plugin "test-plugin" "test-mp"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"from plugin"* ]]
}

@test "plugin: priority ordering — low-priority plugin runs before high-priority drop dir" {
    # Plugin at priority 10 (deny)
    create_plugin_hook "test-mp" "guard" 10 \
        'cat > /dev/null; echo "{\"hookSpecificOutput\":{\"permissionDecision\":\"deny\"},\"systemMessage\":\"blocked by plugin\"}"'
    enable_plugin "guard" "test-mp"

    # Drop dir at priority 50 (allow + rewrite)
    cat > "$DISPATCHER_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"allow","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-rewrite"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    # Deny from plugin at priority 10 should win
    decision=$(echo "$output" | jq -r '.hookSpecificOutput.permissionDecision')
    [ "$decision" = "deny" ]
}

@test "plugin: mixed sources merge — plugin advisory + drop dir rewrite" {
    # Plugin at priority 10 (advisory)
    create_plugin_hook "test-mp" "advisor" 10 \
        'cat > /dev/null; echo "{\"hookSpecificOutput\":{\"additionalContext\":\"plugin advisory\"}}"'
    enable_plugin "advisor" "test-mp"

    # Drop dir at priority 50 (rewrite)
    cat > "$DISPATCHER_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"permissionDecision":"allow","updatedInput":{"command":"rtk git status"}}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-rewrite"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"plugin advisory"* ]]
    cmd=$(echo "$output" | jq -r '.hookSpecificOutput.updatedInput.command')
    [ "$cmd" = "rtk git status" ]
}

@test "plugin: convention file without priority comment defaults to 50" {
    # Create a convention file with no priority comment
    local dir="$DISPATCHER_MARKETPLACE_DIR/test-mp/plugins/no-priority/hooks"
    mkdir -p "$dir"
    cat > "$dir/pretooluse-bash.sh" <<'HOOK'
#!/usr/bin/env bash
# No dispatcher-priority comment here
cat > /dev/null
echo '{"hookSpecificOutput":{"additionalContext":"default priority hook"}}'
HOOK
    chmod +x "$dir/pretooluse-bash.sh"
    enable_plugin "no-priority" "test-mp"

    # Drop dir at priority 10 (runs first)
    cat > "$DISPATCHER_DROP_DIR/10-first" <<'HOOK'
#!/usr/bin/env bash
cat > /dev/null
echo '{"hookSpecificOutput":{"additionalContext":"first hook"}}'
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/10-first"

    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    # Both should appear in context (concatenated)
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"first hook"* ]]
    [[ "$context" == *"default priority"* ]]
}

# ═══════════════════════════════════════════════════════════════════════
# Caching tests
# ═══════════════════════════════════════════════════════════════════════

@test "cache: second invocation uses cache" {
    create_plugin_hook "test-mp" "cached" 10 \
        'cat > /dev/null; echo "{\"hookSpecificOutput\":{\"additionalContext\":\"cached result\"}}"'
    enable_plugin "cached" "test-mp"

    # First run — builds cache
    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    [ -f "$DISPATCHER_CACHE_FILE" ]

    # Verify cache has a HASH line
    head -1 "$DISPATCHER_CACHE_FILE" | grep -q "^HASH:"

    # Second run — should use cache (same result)
    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"cached result"* ]]
}

@test "cache: invalidated when settings change" {
    create_plugin_hook "test-mp" "cached" 10 \
        'cat > /dev/null; echo "{\"hookSpecificOutput\":{\"additionalContext\":\"should appear\"}}"'

    # First run — plugin not enabled, cache built with no hooks
    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]

    local old_hash
    old_hash=$(head -1 "$DISPATCHER_CACHE_FILE")

    # Enable the plugin (changes settings.json mtime)
    sleep 1  # Ensure mtime differs
    enable_plugin "cached" "test-mp"

    # Second run — cache should be invalidated, plugin discovered
    run uv run python "$DISPATCHER" <<< "$SAMPLE_INPUT"
    [ "$status" -eq 0 ]
    context=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$context" == *"should appear"* ]]
}

# ═══════════════════════════════════════════════════════════════════════
# Diagnostics tests
# ═══════════════════════════════════════════════════════════════════════

@test "--list shows discovered hooks" {
    create_plugin_hook "test-mp" "guard" 10 'exit 0'
    enable_plugin "guard" "test-mp"

    cat > "$DISPATCHER_DROP_DIR/50-rewrite" <<'HOOK'
#!/usr/bin/env bash
exit 0
HOOK
    chmod +x "$DISPATCHER_DROP_DIR/50-rewrite"

    run uv run python "$DISPATCHER" --list
    [ "$status" -eq 0 ]
    [[ "$output" == *"plugin:guard@test-mp"* ]]
    [[ "$output" == *"drop:50-rewrite"* ]]
    [[ "$output" == *"Marketplace:"* ]]
}

@test "--list shows empty state" {
    run uv run python "$DISPATCHER" --list
    [ "$status" -eq 0 ]
    [[ "$output" == *"(none)"* ]]
}
