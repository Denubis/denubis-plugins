#!/usr/bin/env bats
# Tests for the session-scoped Codex ponytail worktree launcher.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/codex-ponytail"

make_repo() {
    local repo="$1"
    git init -q -b main "$repo"
    git -C "$repo" config user.email t@e.st
    git -C "$repo" config user.name test
    printf '.worktrees/\n' > "$repo/.gitignore"
    printf 'hello\n' > "$repo/file.txt"
    git -C "$repo" add -A
    git -C "$repo" commit -qm init
}

setup() {
    TEST_DIR="$(mktemp -d)"
    export TEST_DIR
    export XDG_CACHE_HOME="$TEST_DIR/cache"
    export GIT_CONFIG_GLOBAL=/dev/null
    export GIT_CONFIG_SYSTEM=/dev/null

    export CODEX_ARGS_FILE="$TEST_DIR/codex-args"
    export CODEX_PONYTAIL_BINARY="$TEST_DIR/fake-codex"
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'printf "%s\0" "$@" > "$CODEX_ARGS_FILE"' > "$CODEX_PONYTAIL_BINARY"
    chmod +x "$CODEX_PONYTAIL_BINARY"

    FAKE_PONYTAIL="$TEST_DIR/fake-ponytail"
    git init -q -b main "$FAKE_PONYTAIL"
    git -C "$FAKE_PONYTAIL" config user.email t@e.st
    git -C "$FAKE_PONYTAIL" config user.name test
    mkdir -p "$FAKE_PONYTAIL/skills/ponytail"
    printf '%s\n' \
        '---' \
        'name: ponytail' \
        'description: test instructions' \
        '---' \
        "PONYTAIL TEST: don't overbuild." > "$FAKE_PONYTAIL/skills/ponytail/SKILL.md"
    git -C "$FAKE_PONYTAIL" add -A
    git -C "$FAKE_PONYTAIL" commit -qm init
    export CODEX_PONYTAIL_URL="$FAKE_PONYTAIL"
    CODEX_PONYTAIL_SHA="$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)"
    export CODEX_PONYTAIL_SHA

    WORK="$TEST_DIR/work"
    export WORK
    make_repo "$WORK"
    cd "$WORK"
}

teardown() {
    cd / || true
    rm -rf "$TEST_DIR"
}

printed_command() {
    local text="$1"
    printf '%s' "${text##*$'run this in the window you want it in:\n\n  '}"
}

@test "--help identifies the Codex launcher" {
    run "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"codex-ponytail <name> [<base-ref>]"* ]]
}

@test "creates a worktree and prints a session-scoped Codex command" {
    run "$SCRIPT" feature

    [ "$status" -eq 0 ]
    [ -d "$WORK/.worktrees/feature" ]
    [[ "$output" == *"$CODEX_PONYTAIL_BINARY"* ]]
    [[ "$output" == *"developer_instructions="* ]]
    [[ "$output" != *"codex plugin add"* ]]
}

@test "the printed Fish command passes the worktree and pinned instructions to Codex" {
    local command
    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    command="$(printed_command "$output")"

    run fish -c "$command"
    [ "$status" -eq 0 ]

    mapfile -d '' args < "$CODEX_ARGS_FILE"
    [ "${args[0]}" = "-C" ]
    [ "${args[1]}" = "$WORK/.worktrees/feature" ]
    [ "${args[2]}" = "-c" ]
    [[ "${args[3]}" == developer_instructions=* ]]
    [[ "${args[3]}" == *"PONYTAIL TEST: don't overbuild."* ]]
}

@test "the printed Codex command remains valid Fish syntax for a newline path" {
    local newline_work="$TEST_DIR/"$'work\nnewline' command
    make_repo "$newline_work"
    cd "$newline_work"

    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    command="$(printed_command "$output")"

    run fish -n -c "$command"
    [ "$status" -eq 0 ]
}
