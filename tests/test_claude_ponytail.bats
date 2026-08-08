#!/usr/bin/env bats
# Tests for the claude-ponytail worktree launcher.
#
# Hermetic: no test touches the network or the operator's real cache. The
# ponytail upstream is replaced by a local git repo via CLAUDE_PONYTAIL_URL /
# CLAUDE_PONYTAIL_SHA, the claude wrapper is a stub, and XDG_CACHE_HOME points
# into a temp dir.
#
# Regression tests include failures found by falsifying the script's boundary
# handling. Each one asserts the safe behaviour rather than preserving the bug.
#
# The single-quoted printf arguments below intentionally write literal shell
# variables into fake executables. Bats also runs each @test in a subshell, which
# ShellCheck does not model when tracking exported test-fixture variables.
# shellcheck disable=SC2016,SC2030,SC2031

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="$REPO_ROOT/plugins/denubis-external-agents/scripts/claude-ponytail"

make_repo() {
    local r="$1"
    git init -q -b main "$r"
    git -C "$r" config user.email t@e.st
    git -C "$r" config user.name test
    printf '.worktrees/\n' > "$r/.gitignore"
    echo hi > "$r/file.txt"
    git -C "$r" add -A
    git -C "$r" commit -qm init
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

    # The operator's global gitignore lists .worktrees/, which silently satisfied
    # the script's gitignore precondition and made an early version of the
    # "refuses when not gitignored" test unfalsifiable. Neutralise global and
    # system git config so every test sees only the repo it builds.
    export GIT_CONFIG_GLOBAL=/dev/null
    export GIT_CONFIG_SYSTEM=/dev/null

    # The script only requires the wrapper to be executable; it embeds the path
    # in the command it prints rather than running it.
    export CLAUDE_PONYTAIL_WRAPPER="$TEST_DIR/claude-wrapper"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$CLAUDE_PONYTAIL_WRAPPER"
    chmod +x "$CLAUDE_PONYTAIL_WRAPPER"

    # Stand-in for github.com/DietrichGebert/ponytail.
    FAKE_PONYTAIL="$TEST_DIR/fake-ponytail"
    git init -q -b main "$FAKE_PONYTAIL"
    git -C "$FAKE_PONYTAIL" config user.email t@e.st
    git -C "$FAKE_PONYTAIL" config user.name test
    mkdir -p "$FAKE_PONYTAIL/skills/ponytail"
    echo stub > "$FAKE_PONYTAIL/skills/ponytail/SKILL.md"
    git -C "$FAKE_PONYTAIL" add -A
    git -C "$FAKE_PONYTAIL" commit -qm init
    export CLAUDE_PONYTAIL_URL="$FAKE_PONYTAIL"
    CLAUDE_PONYTAIL_SHA="$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)"
    export CLAUDE_PONYTAIL_SHA

    WORK="$TEST_DIR/work"
    export WORK
    make_repo "$WORK"
    cd "$WORK" || return
}

teardown() {
    cd / || true
    rm -rf "$TEST_DIR"
}

# ── Argument handling ──────────────────────────────────────────────────────

@test "--help exits zero and shows the usage line" {
    run "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"claude-ponytail <name> [<base-ref>]"* ]]
}

@test "no arguments refuses" {
    run "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" == *"need a worktree name"* ]]
}

@test "unknown option refuses and names the offending flag" {
    run "$SCRIPT" --bogus
    [ "$status" -ne 0 ]
    [[ "$output" == *"--bogus"* ]]
}

@test "surplus positional arguments refuse" {
    run "$SCRIPT" one two three
    [ "$status" -ne 0 ]
    [[ "$output" == *"too many arguments"* ]]
}

# ── Preconditions ──────────────────────────────────────────────────────────

@test "outside a git repository refuses" {
    cd "$TEST_DIR"
    run "$SCRIPT" feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"not inside a git repository"* ]]
}

@test "reports failure when the main checkout cannot be resolved" {
    local real_git
    real_git="$(command -v git)"
    mkdir "$TEST_DIR/fake-bin"
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'if [ "${1:-}" = rev-parse ] && [ "${2:-}" = --git-common-dir ]; then' \
        '    printf "%s\n" /definitely/missing/claude-ponytail/.git' \
        '    exit 0' \
        'fi' \
        'exec "$REAL_GIT" "$@"' > "$TEST_DIR/fake-bin/git"
    chmod +x "$TEST_DIR/fake-bin/git"
    export REAL_GIT="$real_git"
    export PATH="$TEST_DIR/fake-bin:$PATH"

    run "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"could not resolve main checkout"* ]]
}

@test "refuses when .worktrees is not gitignored, and creates nothing" {
    rm "$WORK/.gitignore"
    git -C "$WORK" add -A
    git -C "$WORK" commit -qm drop-gitignore
    run "$SCRIPT" feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"not gitignored"* ]]
    [ ! -d "$WORK/.worktrees/feature" ]
}

@test "reports a gitignore check error instead of calling it an unignored path" {
    mkdir "$TEST_DIR/excludes-dir"
    git -C "$WORK" config core.excludesFile "$TEST_DIR/excludes-dir"

    run "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"could not check whether .worktrees is ignored"* ]]
    [[ "$output" == *"fatal: cannot use"* ]]
}

@test "refuses when the claude wrapper is missing" {
    export CLAUDE_PONYTAIL_WRAPPER="$TEST_DIR/does-not-exist"
    run "$SCRIPT" feature
    [ "$status" -ne 0 ]
    [[ "$output" == *"wrapper"* ]]
    [ ! -e "$XDG_CACHE_HOME/claude-ponytail" ]
}

# ── Worktree creation ──────────────────────────────────────────────────────

@test "creates the worktree directory and the branch" {
    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [ -d "$WORK/.worktrees/feature" ]
    git -C "$WORK" show-ref --verify --quiet refs/heads/feature
}

@test "a nested branch name creates a nested worktree" {
    run "$SCRIPT" feat/thing

    [ "$status" -eq 0 ]
    [ -d "$WORK/.worktrees/feat/thing" ]
    [ "$(git -C "$WORK/.worktrees/feat/thing" branch --show-current)" = "feat/thing" ]
}

@test "branches from the given base ref rather than HEAD" {
    local first
    first="$(git -C "$WORK" rev-parse HEAD)"
    echo second > "$WORK/second.txt"
    git -C "$WORK" add -A
    git -C "$WORK" commit -qm second

    run "$SCRIPT" fromfirst "$first"
    [ "$status" -eq 0 ]
    [ "$(git -C "$WORK/.worktrees/fromfirst" rev-parse HEAD)" = "$first" ]
}

@test "prints a command naming the plugin dir and the worktree path" {
    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [[ "$output" == *"--plugin-dir"* ]]
    [[ "$output" == *"$WORK/.worktrees/feature"* ]]
}

@test "the printed command is valid fish syntax when the checkout path has a newline" {
    local newline_work="$TEST_DIR/"$'work\nnewline' command
    make_repo "$newline_work"
    cd "$newline_work"

    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    command="${output##*$'run this in the window you want it in:\n\n  '}"

    run fish --no-config -n -c "$command"
    [ "$status" -eq 0 ]
}

@test "the printed command round-trips an apostrophe path through fish and bash" {
    local apostrophe_work="$TEST_DIR/work's path" command expected
    make_repo "$apostrophe_work"
    cd "$apostrophe_work"
    printf '#!/usr/bin/env bash\npwd -P\n' > "$CLAUDE_PONYTAIL_WRAPPER"

    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    command="${output##*$'run this in the window you want it in:\n\n  '}"
    expected="$apostrophe_work/.worktrees/feature"

    run fish --no-config -c "$command"
    [ "$status" -eq 0 ]
    [ "$output" = "$expected" ]

    run bash -c "$command"
    [ "$status" -eq 0 ]
    [ "$output" = "$expected" ]
}

@test "rerunning with the same name reuses the worktree instead of failing" {
    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [[ "$output" == *"reusing existing worktree"* ]]
}

@test "an ordinary directory is not reused as a git worktree" {
    mkdir -p "$WORK/.worktrees/feature"

    run "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"not a registered git worktree"* ]]
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

@test "a worktree on a different branch is not silently reused" {
    git -C "$WORK" worktree add -q "$WORK/.worktrees/feature" -b other

    run "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"uses branch 'other', expected 'feature'"* ]]
}

@test "an existing branch without a worktree is attached instead of recreated" {
    git -C "$WORK" branch feature

    run "$SCRIPT" feature

    [ "$status" -eq 0 ]
    [ -d "$WORK/.worktrees/feature" ]
    [ "$(git -C "$WORK/.worktrees/feature" branch --show-current)" = "feature" ]
}

@test "lfs guard handles a modified filename containing a newline" {
    local filename=$'asset\nname.bin' real_git
    real_git="$(command -v git)"
    printf '*.bin filter=lfs\n' > "$WORK/.gitattributes"
    printf 'original\n' > "$WORK/$filename"
    git -C "$WORK" add -A
    git -C "$WORK" commit -qm lfs-file

    mkdir "$TEST_DIR/fake-bin"
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'if [ "${3:-}" = lfs ] && [ "${4:-}" = env ]; then exit 0; fi' \
        'exec "$REAL_GIT" "$@"' > "$TEST_DIR/fake-bin/git"
    chmod +x "$TEST_DIR/fake-bin/git"
    export REAL_GIT="$real_git"
    export PATH="$TEST_DIR/fake-bin:$PATH"

    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf 'changed\n' > "$WORK/.worktrees/feature/$filename"

    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [[ "$(git -C "$WORK/.worktrees/feature" ls-files -v -- "$filename")" == h\ * ]]
}

@test "--dry-run creates neither worktree nor branch" {
    local launcher_output
    run "$SCRIPT" --dry-run feature
    [ "$status" -eq 0 ]
    launcher_output="$output"
    [ ! -d "$WORK/.worktrees/feature" ]
    run git -C "$WORK" show-ref --verify --quiet refs/heads/feature
    [ "$status" -ne 0 ]
    [[ "$launcher_output" == *"dry run"* ]]
    [[ "$launcher_output" == *"illustrative"* ]]
}

# ── Ponytail cache ─────────────────────────────────────────────────────────

@test "an already-pinned cache is reused rather than re-cloned" {
    run "$SCRIPT" one
    [ "$status" -eq 0 ]

    # Make any clone impossible. Success now proves the cache short-circuited
    # rather than merely that a clone happened to succeed again.
    export CLAUDE_PONYTAIL_URL="$TEST_DIR/definitely-not-a-repo"
    run "$SCRIPT" two
    [ "$status" -eq 0 ]
}

@test "a cache at the wrong sha is refreshed to the pinned one" {
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail"
    mkdir -p "$(dirname "$cached")"
    git init -q -b main "$cached"
    git -C "$cached" config user.email t@e.st
    git -C "$cached" config user.name test
    echo wrong > "$cached/wrong.txt"
    git -C "$cached" add -A
    git -C "$cached" commit -qm wrong

    run "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [ "$(git -C "$cached" rev-parse HEAD)" = "$CLAUDE_PONYTAIL_SHA" ]
}

@test "a modified cache at the pinned sha is replaced before it is loaded" {
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail"
    run "$SCRIPT" one
    [ "$status" -eq 0 ]
    printf 'tampered\n' > "$cached/skills/ponytail/SKILL.md"

    run "$SCRIPT" two

    [ "$status" -eq 0 ]
    [ "$(cat "$cached/skills/ponytail/SKILL.md")" = stub ]
    [ -z "$(git -C "$cached" status --porcelain --untracked-files=all)" ]
}

@test "a failed fetch does not destroy a good cached clone" {
    run "$SCRIPT" one
    [ "$status" -eq 0 ]
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail"
    [ -d "$cached/.git" ]

    # Force a refresh that cannot succeed.
    export CLAUDE_PONYTAIL_SHA="0000000000000000000000000000000000000000"
    export CLAUDE_PONYTAIL_URL="$TEST_DIR/definitely-not-a-repo"
    run "$SCRIPT" two
    [ "$status" -ne 0 ]

    [ -d "$cached/.git" ]
    [ "$(git -C "$cached" rev-parse HEAD)" = "$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)" ]
}

@test "a failed fetch leaves no staging directory behind" {
    run "$SCRIPT" one
    [ "$status" -eq 0 ]

    export CLAUDE_PONYTAIL_SHA="0000000000000000000000000000000000000000"
    export CLAUDE_PONYTAIL_URL="$TEST_DIR/definitely-not-a-repo"
    run "$SCRIPT" two
    [ "$status" -ne 0 ]

    run find "$XDG_CACHE_HOME/claude-ponytail" -maxdepth 1 -name '.staging.*'
    [ -z "$output" ]
}

@test "a failed cache swap restores the previous pinned clone" {
    local cached="$XDG_CACHE_HOME/claude-ponytail/ponytail" old_sha real_mv
    run "$SCRIPT" one
    [ "$status" -eq 0 ]
    old_sha="$(git -C "$cached" rev-parse HEAD)"

    printf 'new\n' > "$FAKE_PONYTAIL/new.txt"
    git -C "$FAKE_PONYTAIL" add -A
    git -C "$FAKE_PONYTAIL" commit -qm new
    CLAUDE_PONYTAIL_SHA="$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)"
    export CLAUDE_PONYTAIL_SHA

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
    CLAUDE_PONYTAIL_SHA="$(git -C "$FAKE_PONYTAIL" rev-parse HEAD)"
    export CLAUDE_PONYTAIL_SHA

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

@test "concurrent launches serialize cache installation" {
    local real_git first_pid second_pid first_status second_status
    real_git="$(command -v git)"
    make_repo "$TEST_DIR/work-two"
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
    (cd "$TEST_DIR/work-two" && "$SCRIPT" two > "$TEST_DIR/two.out" 2>&1) &
    second_pid=$!

    if wait "$first_pid"; then first_status=0; else first_status=$?; fi
    if wait "$second_pid"; then second_status=0; else second_status=$?; fi

    [ "$first_status" -eq 0 ]
    [ "$second_status" -eq 0 ]
    [ "$(wc -l < "$CLONE_LOG")" -eq 1 ]
    [ "$(git -C "$XDG_CACHE_HOME/claude-ponytail/ponytail" rev-parse HEAD)" = "$CLAUDE_PONYTAIL_SHA" ]
}

@test "a name containing .. creates nothing outside .worktrees" {
    run "$SCRIPT" ../escaped
    [ "$status" -ne 0 ]
    [ ! -e "$WORK/escaped" ]
    [ ! -e "$TEST_DIR/escaped" ]
}

@test "previous-checkout syntax is rejected as the literal worktree name" {
    git -C "$WORK" switch -qc other
    git -C "$WORK" switch -q main

    run "$SCRIPT" '@{-1}'

    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid worktree name '@{-1}'"* ]]
    [[ "$output" != *"branch named 'other' already exists"* ]]
    [ ! -e "$XDG_CACHE_HOME/claude-ponytail" ]
    [ ! -e "$WORK/.worktrees/@{-1}" ]
}

@test "the reserved HEAD name is rejected before side effects" {
    run "$SCRIPT" HEAD

    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid worktree name 'HEAD'"* ]]
    [ ! -e "$XDG_CACHE_HOME/claude-ponytail" ]
    [ ! -e "$WORK/.worktrees/HEAD" ]
}

@test "an existing directory cannot bypass worktree name validation" {
    mkdir -p "$WORK/.worktrees" "$WORK/escaped"

    run "$SCRIPT" ../escaped

    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid worktree name"* ]]
}
