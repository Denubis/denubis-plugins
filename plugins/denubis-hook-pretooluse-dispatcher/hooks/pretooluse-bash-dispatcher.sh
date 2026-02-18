#!/usr/bin/env bash
# PreToolUse:Bash dispatcher — auto-discovers and runs hooks sequentially,
# merging their outputs with defined priority.
#
# Hook sources (in priority order):
#   1. Plugin convention files: hooks/pretooluse-bash.sh in enabled marketplace plugins
#      Declare priority via comment: # dispatcher-priority: N (default 50)
#   2. Drop directory: ~/.claude/hooks/pretooluse-bash.d/ for non-plugin hooks
#      Numeric prefix = priority: 10-fork-guard runs at priority 10
#
# Merge rules:
#   - deny wins immediately (stops processing, returns deny)
#   - updatedInput: last hook's value wins (security hooks run first)
#   - additionalContext: concatenated from all hooks
#   - permissionDecision "allow": preserved if any hook sets it
#
# Each hook receives the ORIGINAL stdin (not modified by prior hooks).
#
# Diagnostics: pass --list to show discovered hooks and cache state.
#
# All paths are configurable via environment variables for testing:
#   DISPATCHER_DROP_DIR, DISPATCHER_MARKETPLACE_DIR,
#   DISPATCHER_SETTINGS_FILE, DISPATCHER_CACHE_FILE

set -euo pipefail

: "${DISPATCHER_DROP_DIR:=$HOME/.claude/hooks/pretooluse-bash.d}"
: "${DISPATCHER_MARKETPLACE_DIR:=$HOME/.claude/plugins/marketplaces}"
: "${DISPATCHER_SETTINGS_FILE:=$HOME/.claude/settings.json}"
: "${DISPATCHER_CACHE_FILE:=$HOME/.claude/hooks/.pretooluse-bash-cache}"

CONVENTION_FILE="pretooluse-bash.sh"

# ── Discovery ─────────────────────────────────────────────────────────

discover_hooks() {
    local -a hooks=()

    # 1. Scan marketplace plugins for convention files
    if [[ -d "$DISPATCHER_MARKETPLACE_DIR" ]]; then
        for conv_file in "$DISPATCHER_MARKETPLACE_DIR"/*/plugins/*/hooks/"$CONVENTION_FILE"; do
            [[ -f "$conv_file" && -x "$conv_file" ]] || continue

            # Extract marketplace and plugin name from path
            local rel="${conv_file#"$DISPATCHER_MARKETPLACE_DIR"/}"
            local marketplace="${rel%%/*}"
            local remainder="${rel#*/plugins/}"
            local plugin="${remainder%%/*}"
            local key="${plugin}@${marketplace}"

            # Check if plugin is enabled in settings
            if [[ -f "$DISPATCHER_SETTINGS_FILE" ]]; then
                local enabled
                enabled=$(jq -r --arg k "$key" '.enabledPlugins[$k] // false' "$DISPATCHER_SETTINGS_FILE" 2>/dev/null)
                [[ "$enabled" == "true" ]] || continue
            fi

            # Extract priority from first 5 lines (default 50)
            local priority
            priority=$(head -5 "$conv_file" | grep -oP '#\s*dispatcher-priority:\s*\K\d+' || echo "50")

            hooks+=("${priority}:plugin:${key}:${conv_file}")
        done
    fi

    # 2. Scan drop directory for non-plugin hooks
    if [[ -d "$DISPATCHER_DROP_DIR" ]]; then
        for hook in "$DISPATCHER_DROP_DIR"/*; do
            [[ -f "$hook" && -x "$hook" ]] || continue
            local name
            name=$(basename "$hook")
            local priority
            priority=$(echo "$name" | grep -oP '^\d+' || echo "50")
            hooks+=("${priority}:drop:${name}:${hook}")
        done
    fi

    # Sort by priority (numeric) and output
    if [[ ${#hooks[@]} -gt 0 ]]; then
        printf '%s\n' "${hooks[@]}" | sort -t: -k1 -n
    fi
}

# ── Caching ───────────────────────────────────────────────────────────

compute_cache_key() {
    {
        # Convention files: list with sizes and mtimes
        ls -l "$DISPATCHER_MARKETPLACE_DIR"/*/plugins/*/hooks/"$CONVENTION_FILE" 2>/dev/null || true
        # Drop directory contents
        ls -l "$DISPATCHER_DROP_DIR"/ 2>/dev/null || true
        # Settings file mtime (enabledPlugins may change)
        stat -c %Y "$DISPATCHER_SETTINGS_FILE" 2>/dev/null || true
    } | md5sum | cut -d' ' -f1
}

get_hook_list() {
    local current_key
    current_key=$(compute_cache_key)

    if [[ -f "$DISPATCHER_CACHE_FILE" ]]; then
        local cached_key
        cached_key=$(head -1 "$DISPATCHER_CACHE_FILE" 2>/dev/null | sed 's/^HASH://')
        if [[ "$cached_key" == "$current_key" ]]; then
            tail -n +2 "$DISPATCHER_CACHE_FILE"
            return
        fi
    fi

    # Cache miss — rebuild
    local hooks_list
    hooks_list=$(discover_hooks)
    {
        echo "HASH:$current_key"
        echo "$hooks_list"
    } > "$DISPATCHER_CACHE_FILE" 2>/dev/null || true  # Ignore write errors
    echo "$hooks_list"
}

# ── Diagnostics ───────────────────────────────────────────────────────

if [[ "${1:-}" == "--list" ]]; then
    echo "Discovered hooks (execution order):"
    hook_list=$(get_hook_list)
    if [[ -z "$hook_list" ]]; then
        echo "  (none)"
    else
        while IFS=: read -r priority source name path; do
            printf "  [%02d] %s:%s\n       %s\n" "$priority" "$source" "$name" "$path"
        done <<< "$hook_list"
    fi
    echo
    echo "Sources:"
    echo "  Marketplace: $DISPATCHER_MARKETPLACE_DIR"
    echo "  Drop dir:    $DISPATCHER_DROP_DIR"
    echo "  Settings:    $DISPATCHER_SETTINGS_FILE"
    echo "  Convention:  hooks/$CONVENTION_FILE"
    echo
    if [[ -f "$DISPATCHER_CACHE_FILE" ]]; then
        echo "Cache: $DISPATCHER_CACHE_FILE"
        echo "  Key: $(head -1 "$DISPATCHER_CACHE_FILE" 2>/dev/null)"
    else
        echo "Cache: not yet created"
    fi
    exit 0
fi

# ── Main dispatch ─────────────────────────────────────────────────────

hook_list=$(get_hook_list)

# If no hooks discovered, pass through
if [[ -z "$hook_list" ]]; then
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

while IFS=: read -r priority source name path; do
    [[ -f "$path" && -x "$path" ]] || continue

    # Run hook with original input, capture output
    hook_output=""
    hook_exit=0
    hook_output=$(echo "$INPUT" | "$path" 2>/dev/null) || hook_exit=$?

    # Skip hooks that produce no output
    [[ -n "$hook_output" ]] || continue

    # Parse hook output with jq
    if ! echo "$hook_output" | jq empty 2>/dev/null; then
        continue  # Invalid JSON, skip
    fi

    # Check for deny — wins immediately
    decision=$(echo "$hook_output" | jq -r '.hookSpecificOutput.permissionDecision // empty')
    if [[ "$decision" == "deny" ]]; then
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
done <<< "$hook_list"

# If nothing to report, exit silently
if [[ -z "$FINAL_DECISION" && -z "$FINAL_UPDATED_INPUT" && -z "$FINAL_ADDITIONAL_CONTEXT" && -z "$FINAL_SYSTEM_MESSAGE" ]]; then
    exit 0
fi

# Build merged output using jq
OUTPUT='{}'
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
