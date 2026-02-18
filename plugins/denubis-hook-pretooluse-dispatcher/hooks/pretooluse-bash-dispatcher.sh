#!/usr/bin/env bash
# PreToolUse:Bash dispatcher — runs hooks from a drop directory sequentially
# and merges their outputs with defined priority.
#
# Drop directory: ~/.claude/hooks/pretooluse-bash.d/
# Scripts are run in sorted order (use numeric prefixes: 10-fork-guard, 50-rtk-rewrite).
#
# Merge rules:
#   - deny wins immediately (stops processing, returns deny)
#   - updatedInput: last hook's value wins (later hooks see the original input,
#     but can override the rewrite — security hooks should run first)
#   - additionalContext: concatenated from all hooks
#   - permissionDecision "allow": preserved if any hook sets it
#
# Each hook receives the ORIGINAL stdin (not modified by prior hooks).
# This matches Claude Code's native parallel execution model, but with
# sequential ordering and deterministic merge.

set -euo pipefail

DROP_DIR="$HOME/.claude/hooks/pretooluse-bash.d"

# If no drop directory or it's empty, pass through
if [[ ! -d "$DROP_DIR" ]] || [[ -z "$(ls "$DROP_DIR"/ 2>/dev/null)" ]]; then
    exit 0
fi

# Capture stdin once — all hooks get the same input
INPUT=$(cat)

# Accumulator state
FINAL_DECISION=""
FINAL_REASON=""
FINAL_UPDATED_INPUT=""
FINAL_ADDITIONAL_CONTEXT=""
FINAL_SYSTEM_MESSAGE=""

for hook in "$DROP_DIR"/*; do
    [[ -x "$hook" ]] || continue

    # Run hook with original input, capture output
    hook_output=""
    hook_exit=0
    hook_output=$(echo "$INPUT" | "$hook" 2>/dev/null) || hook_exit=$?

    # Skip hooks that produce no output
    [[ -n "$hook_output" ]] || continue

    # Parse hook output with jq
    if ! echo "$hook_output" | jq empty 2>/dev/null; then
        continue  # Invalid JSON, skip
    fi

    # Check for deny — wins immediately
    decision=$(echo "$hook_output" | jq -r '.hookSpecificOutput.permissionDecision // empty')
    if [[ "$decision" == "deny" ]]; then
        # Deny wins. Output the deny response and stop.
        echo "$hook_output"
        exit 0
    fi

    # Collect allow decision
    if [[ "$decision" == "allow" ]]; then
        FINAL_DECISION="allow"
        reason=$(echo "$hook_output" | jq -r '.hookSpecificOutput.permissionDecisionReason // empty')
        [[ -z "$reason" ]] || FINAL_REASON="$reason"
    fi

    # Collect updatedInput (last one wins)
    updated=$(echo "$hook_output" | jq -c '.hookSpecificOutput.updatedInput // empty')
    if [[ "$updated" != "" && "$updated" != "null" ]]; then
        FINAL_UPDATED_INPUT="$updated"
    fi

    # Collect additionalContext (concatenate)
    context=$(echo "$hook_output" | jq -r '.hookSpecificOutput.additionalContext // empty')
    if [[ -n "$context" ]]; then
        if [[ -n "$FINAL_ADDITIONAL_CONTEXT" ]]; then
            FINAL_ADDITIONAL_CONTEXT="${FINAL_ADDITIONAL_CONTEXT}\n\n${context}"
        else
            FINAL_ADDITIONAL_CONTEXT="$context"
        fi
    fi

    # Collect systemMessage (concatenate)
    sys_msg=$(echo "$hook_output" | jq -r '.systemMessage // empty')
    if [[ -n "$sys_msg" ]]; then
        if [[ -n "$FINAL_SYSTEM_MESSAGE" ]]; then
            FINAL_SYSTEM_MESSAGE="${FINAL_SYSTEM_MESSAGE}\n\n${sys_msg}"
        else
            FINAL_SYSTEM_MESSAGE="$sys_msg"
        fi
    fi
done

# If nothing to report, exit silently
if [[ -z "$FINAL_DECISION" && -z "$FINAL_UPDATED_INPUT" && -z "$FINAL_ADDITIONAL_CONTEXT" && -z "$FINAL_SYSTEM_MESSAGE" ]]; then
    exit 0
fi

# Build merged output using jq
OUTPUT='{}'

# Build hookSpecificOutput
HOOK_OUTPUT='{}'

if [[ -n "$FINAL_DECISION" ]]; then
    HOOK_OUTPUT=$(echo "$HOOK_OUTPUT" | jq --arg d "$FINAL_DECISION" '.permissionDecision = $d')
    HOOK_OUTPUT=$(echo "$HOOK_OUTPUT" | jq '.hookEventName = "PreToolUse"')
    if [[ -n "$FINAL_REASON" ]]; then
        HOOK_OUTPUT=$(echo "$HOOK_OUTPUT" | jq --arg r "$FINAL_REASON" '.permissionDecisionReason = $r')
    fi
fi

if [[ -n "$FINAL_UPDATED_INPUT" ]]; then
    HOOK_OUTPUT=$(echo "$HOOK_OUTPUT" | jq --argjson u "$FINAL_UPDATED_INPUT" '.updatedInput = $u')
fi

if [[ -n "$FINAL_ADDITIONAL_CONTEXT" ]]; then
    HOOK_OUTPUT=$(echo "$HOOK_OUTPUT" | jq --arg c "$FINAL_ADDITIONAL_CONTEXT" '.additionalContext = $c')
fi

OUTPUT=$(echo "$OUTPUT" | jq --argjson h "$HOOK_OUTPUT" '.hookSpecificOutput = $h')

if [[ -n "$FINAL_SYSTEM_MESSAGE" ]]; then
    OUTPUT=$(echo "$OUTPUT" | jq --arg m "$FINAL_SYSTEM_MESSAGE" '.systemMessage = $m')
fi

echo "$OUTPUT"
