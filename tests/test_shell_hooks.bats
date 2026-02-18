#!/usr/bin/env bats
# Tests for shell-based hooks.
# Requires: bats-core, jq

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# ---------------------------------------------------------------------------
# denubis-basic-agents session-start.sh
# ---------------------------------------------------------------------------
@test "basic-agents session-start outputs valid JSON" {
    run bash "$REPO_ROOT/plugins/denubis-basic-agents/hooks/session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | jq . > /dev/null
}

@test "basic-agents session-start has hookEventName SessionStart" {
    run bash "$REPO_ROOT/plugins/denubis-basic-agents/hooks/session-start.sh"
    result=$(echo "$output" | jq -r '.hookSpecificOutput.hookEventName')
    [ "$result" = "SessionStart" ]
}

@test "basic-agents session-start mentions generic agents" {
    run bash "$REPO_ROOT/plugins/denubis-basic-agents/hooks/session-start.sh"
    result=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$result" == *"using-generic-agents"* ]]
}

# ---------------------------------------------------------------------------
# denubis-hook-skill-reinforcement hook-reminder.sh
# ---------------------------------------------------------------------------
@test "hook-reminder outputs valid JSON" {
    run bash "$REPO_ROOT/plugins/denubis-hook-skill-reinforcement/hooks/hook-reminder.sh"
    [ "$status" -eq 0 ]
    echo "$output" | jq . > /dev/null
}

@test "hook-reminder has hookEventName UserPromptSubmit" {
    run bash "$REPO_ROOT/plugins/denubis-hook-skill-reinforcement/hooks/hook-reminder.sh"
    result=$(echo "$output" | jq -r '.hookSpecificOutput.hookEventName')
    [ "$result" = "UserPromptSubmit" ]
}

@test "hook-reminder mentions skills" {
    run bash "$REPO_ROOT/plugins/denubis-hook-skill-reinforcement/hooks/hook-reminder.sh"
    result=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    [[ "$result" == *"skill"* ]]
}

# ---------------------------------------------------------------------------
# denubis-plan-and-execute session-start.sh
# ---------------------------------------------------------------------------
@test "plan-and-execute session-start outputs valid JSON" {
    run bash "$REPO_ROOT/plugins/denubis-plan-and-execute/hooks/session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | jq . > /dev/null
}

@test "plan-and-execute session-start has hookEventName SessionStart" {
    run bash "$REPO_ROOT/plugins/denubis-plan-and-execute/hooks/session-start.sh"
    result=$(echo "$output" | jq -r '.hookSpecificOutput.hookEventName')
    [ "$result" = "SessionStart" ]
}

@test "plan-and-execute session-start includes skill content" {
    run bash "$REPO_ROOT/plugins/denubis-plan-and-execute/hooks/session-start.sh"
    result=$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')
    # Should contain content from the using-plan-and-execute skill
    [[ "$result" == *"EXTREMELY_IMPORTANT"* ]]
    [[ "$result" == *"skill"* ]]
}

@test "plan-and-execute session-start JSON-escapes special characters" {
    # The skill file contains quotes and newlines — verify they survive JSON encoding
    run bash "$REPO_ROOT/plugins/denubis-plan-and-execute/hooks/session-start.sh"
    # If jq can parse it, the escaping worked
    echo "$output" | jq -r '.hookSpecificOutput.additionalContext' > /dev/null
}
