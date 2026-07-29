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

wait_for_path() {
    local path="$1"
    for _ in {1..200}; do
        [ -e "$path" ] && return 0
        sleep 0.01
    done
    return 1
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

@test "previous-checkout syntax is rejected as the literal worktree name" {
    git -C "$WORK" switch -qc other
    git -C "$WORK" switch -q main

    run "$SCRIPT" '@{-1}'

    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid worktree name '@{-1}'"* ]]
    [[ "$output" != *"branch named 'other' already exists"* ]]
    [ ! -e "$XDG_CACHE_HOME/claude-ponytail" ]
}

@test "an unrelated repository is not reused as this repository's worktree" {
    local unrelated="$WORK/.worktrees/feature"
    git init -q -b feature "$unrelated"
    git -C "$unrelated" config user.email t@e.st
    git -C "$unrelated" config user.name test
    printf 'unrelated\n' > "$unrelated/file.txt"
    git -C "$unrelated" add -A
    git -C "$unrelated" commit -qm unrelated

    run "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"not a registered git worktree"* ]]
}

@test "Codex and Claude launches serialize shared cache installation" {
    local claude_script="$REPO_ROOT/scripts/claude-ponytail"
    local real_git first_pid second_pid first_status second_status
    real_git="$(command -v git)"
    make_repo "$TEST_DIR/work-two"
    export CLAUDE_PONYTAIL_WRAPPER="$TEST_DIR/claude-wrapper"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$CLAUDE_PONYTAIL_WRAPPER"
    chmod +x "$CLAUDE_PONYTAIL_WRAPPER"
    export CLAUDE_PONYTAIL_URL="$FAKE_PONYTAIL"
    export CLAUDE_PONYTAIL_SHA="$CODEX_PONYTAIL_SHA"
    mkdir "$TEST_DIR/fake-bin"
    export CLONE_LOG="$TEST_DIR/clone.log"
    export CLONE_STARTED="$TEST_DIR/clone.started"
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'if [ "${1:-}" = clone ]; then' \
        '    printf "clone\n" >> "$CLONE_LOG"' \
        '    : > "$CLONE_STARTED"' \
        '    sleep 0.25' \
        'fi' \
        'exec "$REAL_GIT" "$@"' > "$TEST_DIR/fake-bin/git"
    chmod +x "$TEST_DIR/fake-bin/git"
    export REAL_GIT="$real_git"
    export PATH="$TEST_DIR/fake-bin:$PATH"

    (cd "$WORK" && "$SCRIPT" one > "$TEST_DIR/one.out" 2>&1) &
    first_pid=$!
    wait_for_path "$CLONE_STARTED"
    (cd "$TEST_DIR/work-two" && "$claude_script" two > "$TEST_DIR/two.out" 2>&1) &
    second_pid=$!

    if wait "$first_pid"; then first_status=0; else first_status=$?; fi
    if wait "$second_pid"; then second_status=0; else second_status=$?; fi

    [ "$first_status" -eq 0 ]
    [ "$second_status" -eq 0 ]
    [ "$(wc -l < "$CLONE_LOG")" -eq 1 ]
    [ "$(git -C "$XDG_CACHE_HOME/claude-ponytail/ponytail" rev-parse HEAD)" = "$CODEX_PONYTAIL_SHA" ]
    run find "$XDG_CACHE_HOME/claude-ponytail" -maxdepth 1 -name '.staging.*'
    [ -z "$output" ]
}

@test "a modified cache at the pinned sha is replaced before it is loaded" {
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail"
    run "$SCRIPT" one
    [ "$status" -eq 0 ]
    printf 'tampered\n' > "$cached/skills/ponytail/SKILL.md"

    run "$SCRIPT" two

    [ "$status" -eq 0 ]
    [[ "$(cat "$cached/skills/ponytail/SKILL.md")" == *"PONYTAIL TEST: don't overbuild."* ]]
    [ -z "$(git -C "$cached" status --porcelain --untracked-files=all)" ]
}

@test "a failed cache swap restores the previous pinned clone" {
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail" old_sha real_mv
    run "$SCRIPT" one
    [ "$status" -eq 0 ]
    old_sha="$(git -C "$cached" rev-parse HEAD)"

    printf 'new\n' > "$FAKE_PONYTAIL/new.txt"
    git -C "$FAKE_PONYTAIL" add -A
    git -C "$FAKE_PONYTAIL" commit -qm new
    CODEX_PONYTAIL_SHA="$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)"
    export CODEX_PONYTAIL_SHA

    real_mv="$(command -v mv)"
    mkdir "$TEST_DIR/fake-bin"
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'source_path="${@: -2:1}"' \
        'target_path="${@: -1}"' \
        'if [[ "$source_path" == */new && "$target_path" == */ponytail ]]; then exit 75; fi' \
        'exec "$REAL_MV" "$@"' > "$TEST_DIR/fake-bin/mv"
    chmod +x "$TEST_DIR/fake-bin/mv"
    export REAL_MV="$real_mv"
    export PATH="$TEST_DIR/fake-bin:$PATH"

    run "$SCRIPT" two

    [ "$status" -ne 0 ]
    [ "$(git -C "$cached" rev-parse HEAD)" = "$old_sha" ]
    run find "$XDG_CACHE_HOME/claude-ponytail" -maxdepth 1 -name '.staging.*'
    [ -z "$output" ]
}

@test "an interrupted cache swap restores the previous pinned clone" {
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail" old_sha real_mv
    run "$SCRIPT" one
    [ "$status" -eq 0 ]
    old_sha="$(git -C "$cached" rev-parse HEAD)"

    printf 'new\n' > "$FAKE_PONYTAIL/new.txt"
    git -C "$FAKE_PONYTAIL" add -A
    git -C "$FAKE_PONYTAIL" commit -qm new
    CODEX_PONYTAIL_SHA="$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)"
    export CODEX_PONYTAIL_SHA

    real_mv="$(command -v mv)"
    mkdir "$TEST_DIR/fake-bin"
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'source_path="${@: -2:1}"' \
        'target_path="${@: -1}"' \
        'if [[ "$source_path" == */new && "$target_path" == */ponytail ]]; then' \
        '    kill -TERM "$PPID"' \
        '    sleep 0.05' \
        '    exit 75' \
        'fi' \
        'exec "$REAL_MV" "$@"' > "$TEST_DIR/fake-bin/mv"
    chmod +x "$TEST_DIR/fake-bin/mv"
    export REAL_MV="$real_mv"
    export PATH="$TEST_DIR/fake-bin:$PATH"

    run "$SCRIPT" two

    [ "$status" -ne 0 ]
    [ "$(git -C "$cached" rev-parse HEAD)" = "$old_sha" ]
    run find "$XDG_CACHE_HOME/claude-ponytail" -maxdepth 1 -name '.staging.*'
    [ -z "$output" ]
}
