#!/usr/bin/env bats
# Hermetic tests for the isolated native Codex Ponytail launcher.
# Bats runs each @test in a subshell, which ShellCheck does not model when
# tracking exported test-fixture variables.
# shellcheck disable=SC2030,SC2031

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="$REPO_ROOT/plugins/denubis-external-agents/scripts/codex-ponytail"
COMPLETION="$REPO_ROOT/plugins/denubis-external-agents/completions/codex-ponytail.fish"
COMPLETION_INSTALLER="$REPO_ROOT/plugins/denubis-external-agents/scripts/install-ponytail-fish-completions"
FAKE_CODEX_FIXTURE="$REPO_ROOT/tests/fixtures/fake_codex"

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
    export HOME="$TEST_DIR/user-home"
    export CODEX_PONYTAIL_TESTING=1
    export CODEX_PONYTAIL_HOME="$TEST_DIR/ponytail-home"
    FAKE_CODEX="$TEST_DIR/fake-codex"
    cp "$FAKE_CODEX_FIXTURE" "$FAKE_CODEX"
    chmod +x "$FAKE_CODEX"
    export FAKE_CODEX
    export CODEX_PONYTAIL_BINARY="$FAKE_CODEX"
    export CODEX_PONYTAIL_MARKETPLACE="$TEST_DIR/upstream-ponytail"
    export CODEX_PONYTAIL_SHA="0123456789abcdef0123456789abcdef01234567"
    export FAKE_CODEX_CALLS="$TEST_DIR/codex-calls"
    export FAKE_CODEX_SESSION_ARGS="$TEST_DIR/session-args"
    export FAKE_CODEX_SESSION_HOME="$TEST_DIR/session-home"
    export FAKE_CODEX_SESSION_XDG="$TEST_DIR/session-xdg"
    export FAKE_CODEX_SESSION_OPENAI_KEY="$TEST_DIR/session-openai-key"
    export FAKE_CODEX_SESSION_CODEX_KEY="$TEST_DIR/session-codex-key"
    export GIT_CONFIG_GLOBAL=/dev/null
    export GIT_CONFIG_SYSTEM=/dev/null

    # The sandbox-cache-root resolution reads these from the environment, so an
    # operator shell that happens to export any of them (as this one does, for
    # UV_CACHE_DIR and PIP_CACHE_DIR) would otherwise leak real host paths into
    # what is meant to be a hermetic test.
    unset UV_CACHE_DIR PIP_CACHE_DIR HF_HOME TORCH_HOME CARGO_HOME \
        XDG_CACHE_HOME NPM_CONFIG_CACHE npm_config_cache

    mkdir -p "$HOME/.agents/skills"
    WORK="$TEST_DIR/work"
    export WORK
    make_repo "$WORK"
    cd "$WORK" || return
}

teardown() {
    cd / || true
    rm -rf "$TEST_DIR"
}

@test "--help identifies the isolated native launcher" {
    run bash "$SCRIPT" --help

    [ "$status" -eq 0 ]
    [[ "$output" == *"codex-ponytail <name> [<codex-args>...]"* ]]
    [[ "$output" == *"CODEX_HOME"* ]]
    [[ "$output" == *"One-time setup"* ]]
}

@test "Fish completes registered worktree branches after launcher options" {
    mkdir -p "$TEST_DIR/bin" "$WORK/.worktrees/ordinary"
    ln -s "$SCRIPT" "$TEST_DIR/bin/codex-ponytail"
    git -C "$WORK" branch parked
    git -C "$WORK" worktree add -q -b research/topic "$WORK/.worktrees/feature"

    run env PATH="$TEST_DIR/bin:$PATH" fish --no-config -c \
        "source '$COMPLETION'; complete -C 'codex-ponytail --dry-run '"

    [ "$status" -eq 0 ]
    [ "$output" = $'research/topic\tExisting worktree' ]
}

@test "Fish completion installer writes relocatable regular files" {
    local config_home="$TEST_DIR/config"
    mkdir -p "$config_home/fish/completions"
    ln -s "$COMPLETION" \
        "$config_home/fish/completions/codex-ponytail.fish"
    ln -s "$REPO_ROOT/plugins/denubis-external-agents/completions/claude-ponytail.fish" \
        "$config_home/fish/completions/claude-ponytail.fish"

    run env XDG_CONFIG_HOME="$config_home" "$COMPLETION_INSTALLER"

    [ "$status" -eq 0 ]
    [ -f "$config_home/fish/completions/codex-ponytail.fish" ]
    [ ! -L "$config_home/fish/completions/codex-ponytail.fish" ]
    [ -f "$config_home/fish/completions/claude-ponytail.fish" ]
    [ ! -L "$config_home/fish/completions/claude-ponytail.fish" ]
    cmp "$COMPLETION" \
        "$config_home/fish/completions/codex-ponytail.fish"
    cmp "$REPO_ROOT/plugins/denubis-external-agents/completions/claude-ponytail.fish" \
        "$config_home/fish/completions/claude-ponytail.fish"
}

@test "literal branch validation rejects revision syntax and HEAD" {
    run bash "$SCRIPT" '@{-1}'
    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid worktree name"* ]]
    [ ! -e "$CODEX_PONYTAIL_HOME" ]

    run bash "$SCRIPT" HEAD
    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid worktree name"* ]]
    [ ! -e "$CODEX_PONYTAIL_HOME" ]
}

@test "production mode ignores test-only source and home overrides" {
    unset CODEX_PONYTAIL_TESTING

    run bash "$SCRIPT" --dry-run feature

    [ "$status" -eq 0 ]
    [[ "$output" == *"$HOME/.codex-ponytail"* ]]
    [[ "$output" == *"DietrichGebert/ponytail"* ]]
    [[ "$output" == *"16f29800fd2681bdf24f3eb4ccffe38be3baec6b"* ]]
    [[ "$output" != *"$CODEX_PONYTAIL_HOME"* ]]
    [[ "$output" != *"$CODEX_PONYTAIL_MARKETPLACE"* ]]
    [[ "$output" != *"$CODEX_PONYTAIL_SHA"* ]]
}

@test "unsafe worktree preflight happens before isolated-home mutation" {
    rm "$WORK/.gitignore"
    git -C "$WORK" add -A
    git -C "$WORK" commit -qm drop-ignore

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"not gitignored"* ]]
    [ ! -e "$CODEX_PONYTAIL_HOME" ]
    [ ! -e "$WORK/.worktrees/feature" ]
}

@test "branch already checked out elsewhere is rejected before home mutation" {
    run bash "$SCRIPT" main

    [ "$status" -ne 0 ]
    [[ "$output" == *"already checked out"* ]]
    [ ! -e "$CODEX_PONYTAIL_HOME" ]
}

# A main checkout can be bare while all work happens in linked worktrees.
# check-ignore cannot run in the bare root at all, so asking it there conflates
# "cannot answer" with "not ignored" and rejects a repository that qualifies.
make_bare_main() {
    git -C "$WORK" worktree add -q "$TEST_DIR/linked" -b linked
    git -C "$WORK" config core.bare true
    cd "$TEST_DIR/linked" || return 1
}

@test "a bare main checkout resolves the gitignore guard from a linked worktree" {
    make_bare_main

    run bash "$SCRIPT" --dry-run feature

    [ "$status" -eq 0 ]
    [[ "$output" == *"$WORK/.worktrees/feature"* ]]
}

@test "a bare main checkout still rejects a repository that does not ignore worktrees" {
    rm "$WORK/.gitignore"
    git -C "$WORK" add -A
    git -C "$WORK" commit -qm drop-ignore
    make_bare_main

    run bash "$SCRIPT" --dry-run feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"not gitignored"* ]]
}

@test "a bare main checkout falls back to a linked worktree when the caller is in neither" {
    make_bare_main
    cd "$WORK" || return

    run bash "$SCRIPT" --dry-run feature

    [ "$status" -eq 0 ]
    [[ "$output" == *"$WORK/.worktrees/feature"* ]]
}

@test "symlinked isolated home is rejected without following it" {
    local redirected="$TEST_DIR/redirected"
    mkdir "$redirected"
    ln -s "$redirected" "$CODEX_PONYTAIL_HOME"

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"must not be a symlink"* ]]
    [ ! -e "$redirected/config.toml" ]
    [ ! -e "$WORK/.worktrees/feature" ]
}

@test "symlinked base config cannot redirect plugin state" {
    local normal_config="$HOME/.codex/config.toml"
    mkdir -p "$CODEX_PONYTAIL_HOME" "$(dirname "$normal_config")"
    printf 'cli_auth_credentials_store = "file"\n' > "$normal_config"
    ln -s "$normal_config" "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"base Codex config must not be a symlink"* ]]
    [ "$(cat "$normal_config")" = 'cli_auth_credentials_store = "file"' ]
    [ ! -e "$WORK/.worktrees/feature" ]
}

@test "symlink at requested worktree path is not treated as registered" {
    git -C "$WORK" worktree add -q -b feature "$TEST_DIR/actual-worktree"
    mkdir -p "$WORK/.worktrees"
    ln -s "$TEST_DIR/actual-worktree" "$WORK/.worktrees/feature"

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"not a registered git worktree"* ]]
    [ ! -e "$CODEX_PONYTAIL_HOME" ]
}

@test "symlinked managed profile cannot redirect writes" {
    local redirected="$TEST_DIR/redirected-profile"
    mkdir -p "$CODEX_PONYTAIL_HOME" "$redirected"
    ln -s "$redirected" "$CODEX_PONYTAIL_HOME/ponytail.config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"managed profile must not be a symlink"* ]]
    [ -z "$(find "$redirected" -mindepth 1 -maxdepth 1 -print -quit)" ]
    [ ! -e "$WORK/.worktrees/feature" ]
}

@test "symlinked lock cannot redirect or truncate writes" {
    local redirected="$HOME/.codex/lock-target"
    mkdir -p "$CODEX_PONYTAIL_HOME" "$(dirname "$redirected")"
    printf 'preserve lock target\n' > "$redirected"
    ln -s "$redirected" "$CODEX_PONYTAIL_HOME/.codex-ponytail.lock"

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"lock must not be a symlink"* ]]
    [ "$(cat "$redirected")" = "preserve lock target" ]
    [ ! -e "$WORK/.worktrees/feature" ]
}

@test "fresh invocation bootstraps pinned native Ponytail before the worktree" {
    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    [ -d "$WORK/.worktrees/feature" ]
    [ -f "$CODEX_PONYTAIL_HOME/config.toml" ]
    [ -f "$CODEX_PONYTAIL_HOME/ponytail.config.toml" ]
    [ -f "$CODEX_PONYTAIL_HOME/fake-codex-state/plugin" ]
    [ "$(stat -c %a "$CODEX_PONYTAIL_HOME")" = "700" ]
    [ "$(stat -c %a "$CODEX_PONYTAIL_HOME/xdg-config")" = "700" ]
    [ "$(stat -c %a "$CODEX_PONYTAIL_HOME/.codex-ponytail.lock")" = "600" ]
    grep -F -- "plugin marketplace add" "$FAKE_CODEX_CALLS"
    grep -F -- "$CODEX_PONYTAIL_MARKETPLACE --ref $CODEX_PONYTAIL_SHA" \
        "$FAKE_CODEX_CALLS"
    grep -F -- "plugin add ponytail@ponytail --json" \
        "$FAKE_CODEX_CALLS"
    [ -f "$FAKE_CODEX_SESSION_ARGS" ]
}

@test "rerun preserves base config state while replacing only the profile" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '\n[hooks.state.test]\ntrusted = true\n' >> "$CODEX_PONYTAIL_HOME/config.toml"
    printf 'session\n' > "$CODEX_PONYTAIL_HOME/session-sentinel"
    printf 'stale profile\n' > "$CODEX_PONYTAIL_HOME/ponytail.config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "[plugins.\"ponytail@ponytail\"]" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "[hooks.state.test]" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$(cat "$CODEX_PONYTAIL_HOME/session-sentinel")" = "session" ]
    run grep -F -- "stale profile" "$CODEX_PONYTAIL_HOME/ponytail.config.toml"
    [ "$status" -eq 1 ]
}

# A supervising process reads Codex's status out of the terminal title, so an
# isolated home that configures no title produces a pane nothing can drive.
@test "a fresh isolated home configures a terminal title carrying status" {
    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "[tui]" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "terminal_title" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- '"status"' "$CODEX_PONYTAIL_HOME/config.toml"
    # A supervisor reads the remaining-context percentage off the status line to
    # honour its dispatch floor, so a title alone leaves it unable to check.
    grep -F -- "status_line" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- '"context-remaining"' "$CODEX_PONYTAIL_HOME/config.toml"
}

@test "an isolated home predating the title setting gains it on the next run" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '%s\n' \
        '# Initialized by codex-ponytail; Codex owns subsequent plugin and hook state.' \
        'cli_auth_credentials_store = "file"' \
        > "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "terminal_title" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- 'cli_auth_credentials_store = "file"' "$CODEX_PONYTAIL_HOME/config.toml"
}

@test "an existing tui section is left alone rather than duplicated" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '%s\n' \
        'cli_auth_credentials_store = "file"' \
        '[tui]' \
        'terminal_title = ["status", "chosen-by-hand"]' \
        > "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "chosen-by-hand" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$(grep -c -F -- "[tui]" "$CODEX_PONYTAIL_HOME/config.toml")" -eq 1 ]
}

# Codex's built-in sandbox default is network_access = false for workspace-write,
# which blocks the isolated home from reaching a package index (e.g. `uv sync`)
# even though the operator's normal Codex home grants it.
@test "a fresh isolated home configures workspace-write network access" {
    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "[sandbox_workspace_write]" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "network_access = true" "$CODEX_PONYTAIL_HOME/config.toml"
}

@test "an isolated home predating the network access setting gains it on the next run" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '%s\n' \
        '# Initialized by codex-ponytail; Codex owns subsequent plugin and hook state.' \
        'cli_auth_credentials_store = "file"' \
        '' \
        '[tui]' \
        'terminal_title = ["status"]' \
        > "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "[sandbox_workspace_write]" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "network_access = true" "$CODEX_PONYTAIL_HOME/config.toml"
}

@test "an existing sandbox_workspace_write section is left alone rather than duplicated" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '%s\n' \
        'cli_auth_credentials_store = "file"' \
        '[sandbox_workspace_write]' \
        'network_access = false' \
        'writable_roots = ["chosen-by-hand"]' \
        > "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "chosen-by-hand" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "network_access = false" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$(grep -c -F -- "[sandbox_workspace_write]" "$CODEX_PONYTAIL_HOME/config.toml")" -eq 1 ]
}

# The status line is where context-remaining lives, and the context floor reads
# it. A [tui] section this script wrote before the status line was part of the
# block therefore leaves the floor unable to see the meter, which is a refusal to
# dispatch rather than a cosmetic gap.
@test "a codex-ponytail tui section missing the status line gains it" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '%s\n' \
        'cli_auth_credentials_store = "file"' \
        '' \
        '# Added by codex-ponytail so a supervisor can read Codex status.' \
        '[tui]' \
        'terminal_title = ["status"]' \
        > "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "status_line" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "context-remaining" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- 'terminal_title = ["status"]' "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$(grep -c -F -- "[tui]" "$CODEX_PONYTAIL_HOME/config.toml")" -eq 1 ]
}

# A section this script wrote itself is not the operator's choice, so leaving it
# alone strands every home initialized before the cache grant existed: the grant
# lands in the script and can never reach the config. The marker comment the
# script already writes is what tells its own output apart from a hand-written
# section, which the test above still leaves untouched.
@test "a codex-ponytail sandbox section predating the cache grant gains writable roots" {
    local uv_cache="$TEST_DIR/uv cache" npm_cache="$TEST_DIR/npm cache"
    export UV_CACHE_DIR="$uv_cache"
    export npm_config_cache="$npm_cache"
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    printf '%s\n' \
        '# Initialized by codex-ponytail; Codex owns subsequent plugin and hook state.' \
        'cli_auth_credentials_store = "file"' \
        '' \
        '# Added by codex-ponytail so the isolated sandbox can reach a package index.' \
        '[sandbox_workspace_write]' \
        'network_access = true' \
        > "$CODEX_PONYTAIL_HOME/config.toml"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "writable_roots" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "$uv_cache" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "$npm_cache" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "network_access = true" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$(grep -c -F -- "[sandbox_workspace_write]" "$CODEX_PONYTAIL_HOME/config.toml")" -eq 1 ]
}

@test "printed invocation restricts the sandbox to workspace-write with on-request approval" {
    run bash "$SCRIPT" --dry-run feature

    [ "$status" -eq 0 ]
    [[ "$output" == *"-s workspace-write"* ]]
    [[ "$output" == *"-a on-request"* ]]
}

# uv and npm caches are required grants, not existence-gated candidates: the
# operator wants them present unconditionally, so a directory that has never
# been created yet (a brand-new machine, before either tool has run) is
# granted the same as one that already exists.
@test "uv and npm caches are granted at their override paths even before the directory exists" {
    local uv_cache="$TEST_DIR/uv cache" npm_cache="$TEST_DIR/npm cache"
    export UV_CACHE_DIR="$uv_cache"
    export npm_config_cache="$npm_cache"
    [ ! -e "$uv_cache" ]
    [ ! -e "$npm_cache" ]

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "writable_roots" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "$uv_cache" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "$npm_cache" "$CODEX_PONYTAIL_HOME/config.toml"
}

# With no override set, each tool's own documented default is resolved and
# granted just the same — proving the fallback computation runs, not just
# override-variable passthrough. Neither default directory is pre-created
# here, for the same unconditional-grant reason as above.
@test "uv and npm caches are granted at their documented defaults with no override set" {
    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "$HOME/.cache/uv" "$CODEX_PONYTAIL_HOME/config.toml"
    grep -F -- "$HOME/.npm" "$CODEX_PONYTAIL_HOME/config.toml"
}

# pip, Hugging Face, torch, cargo, and a bare XDG_CACHE_HOME grant were all
# candidates at one point; none of them ships because no concrete need for
# this launcher's actual workloads was found. Setting their env vars (even to
# directories that exist) must not smuggle them into writable_roots.
@test "sandbox writable roots are limited to uv and npm, not every cache-shaped env var" {
    local pip_cache="$TEST_DIR/pip" hf_cache="$TEST_DIR/hf" torch_cache="$TEST_DIR/torch"
    local cargo_home="$TEST_DIR/cargo" xdg_cache="$TEST_DIR/xdg"
    mkdir -p "$pip_cache" "$hf_cache" "$torch_cache" "$cargo_home" "$xdg_cache"
    export PIP_CACHE_DIR="$pip_cache" HF_HOME="$hf_cache" TORCH_HOME="$torch_cache"
    export CARGO_HOME="$cargo_home" XDG_CACHE_HOME="$xdg_cache"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    run grep -F -- "$pip_cache" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$status" -eq 1 ]
    run grep -F -- "$hf_cache" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$status" -eq 1 ]
    run grep -F -- "$torch_cache" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$status" -eq 1 ]
    run grep -F -- "$cargo_home" "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$status" -eq 1 ]
    # $xdg_cache is checked as an exact array entry, not a substring: with
    # UV_CACHE_DIR unset, uv's own default legitimately resolves to
    # "$xdg_cache/uv", which correctly does contain $xdg_cache as a prefix.
    run grep -F -- "\"$xdg_cache\"," "$CODEX_PONYTAIL_HOME/config.toml"
    [ "$status" -eq 1 ]
}

@test "the printed invocation no longer carries a cache directory flag" {
    export UV_CACHE_DIR="$TEST_DIR/uv-cache"
    mkdir -p "$UV_CACHE_DIR"

    run bash "$SCRIPT" --dry-run feature

    [ "$status" -eq 0 ]
    [[ "$output" != *"--add-dir"* ]]
}

@test "profile disables real and symlinked global skills by SKILL.md path" {
    mkdir -p "$HOME/.agents/skills/real"
    printf '%s\n' '---' 'name: real' 'description: test' '---' \
        > "$HOME/.agents/skills/real/SKILL.md"
    mkdir -p "$TEST_DIR/symlink-target"
    printf '%s\n' '---' 'name: linked' 'description: test' '---' \
        > "$TEST_DIR/symlink-target/SKILL.md"
    ln -s "$TEST_DIR/symlink-target" "$HOME/.agents/skills/linked"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "path = \"$HOME/.agents/skills/real/SKILL.md\"" \
        "$CODEX_PONYTAIL_HOME/ponytail.config.toml"
    grep -F -- "path = \"$HOME/.agents/skills/linked/SKILL.md\"" \
        "$CODEX_PONYTAIL_HOME/ponytail.config.toml"
    [ "$(grep -cF 'enabled = false' "$CODEX_PONYTAIL_HOME/ponytail.config.toml")" -eq 2 ]
}

@test "new global skill is denied on the following invocation" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    run grep -F -- "/later/SKILL.md" "$CODEX_PONYTAIL_HOME/ponytail.config.toml"
    [ "$status" -eq 1 ]
    mkdir -p "$HOME/.agents/skills/later"
    printf '%s\n' '---' 'name: later' 'description: test' '---' \
        > "$HOME/.agents/skills/later/SKILL.md"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    grep -F -- "path = \"$HOME/.agents/skills/later/SKILL.md\"" \
        "$CODEX_PONYTAIL_HOME/ponytail.config.toml"
}

@test "bootstrap failure creates no worktree and does not launch Codex" {
    export FAKE_CODEX_FAIL_PLUGIN=1

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [ ! -e "$WORK/.worktrees/feature" ]
    [ ! -e "$FAKE_CODEX_SESSION_ARGS" ]
}

@test "existing marketplace at another revision fails instead of repinning" {
    mkdir -p "$CODEX_PONYTAIL_HOME/fake-codex-state"
    printf '%s\n%s\n' "$CODEX_PONYTAIL_MARKETPLACE" "another-revision" \
        > "$CODEX_PONYTAIL_HOME/fake-codex-state/marketplace"

    run bash "$SCRIPT" feature

    [ "$status" -ne 0 ]
    [[ "$output" == *"marketplace source or revision mismatch"* ]]
    [ ! -e "$WORK/.worktrees/feature" ]
}

@test "dry run creates neither isolated state nor worktree" {
    run bash "$SCRIPT" --dry-run feature

    [ "$status" -eq 0 ]
    [ ! -e "$CODEX_PONYTAIL_HOME" ]
    [ ! -e "$WORK/.worktrees/feature" ]
    [[ "$output" == *"dry run"* ]]
    [[ "$output" == *"CODEX_HOME"* ]]
}

@test "direct Codex launch isolates config and handles an apostrophe path" {
    local apostrophe_work="$TEST_DIR/work's path"
    make_repo "$apostrophe_work"
    cd "$apostrophe_work"
    export OPENAI_API_KEY="normal-openai-key"
    export CODEX_API_KEY="normal-codex-key"

    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [ "$(cat "$FAKE_CODEX_SESSION_HOME")" = "$CODEX_PONYTAIL_HOME" ]
    [ "$(cat "$FAKE_CODEX_SESSION_XDG")" = "$CODEX_PONYTAIL_HOME/xdg-config" ]
    [ "$(cat "$FAKE_CODEX_SESSION_OPENAI_KEY")" = "unset" ]
    [ "$(cat "$FAKE_CODEX_SESSION_CODEX_KEY")" = "unset" ]
    grep -F -- "--profile ponytail -C" "$FAKE_CODEX_CALLS"
    mapfile -d '' args < "$FAKE_CODEX_SESSION_ARGS"
    [ "${args[0]}" = "-C" ]
    [ "${args[1]}" = "$apostrophe_work/.worktrees/feature" ]
}

@test "launches Codex and passes every argument after the worktree unchanged" {
    git -C "$WORK" worktree add -q -b feature "$WORK/.worktrees/feature"
    export OPENAI_API_KEY="normal-openai-key"
    export CODEX_API_KEY="normal-codex-key"

    run bash "$SCRIPT" feature resume --last

    [ "$status" -eq 0 ]
    mapfile -d '' args < "$FAKE_CODEX_SESSION_ARGS"
    [ "${args[0]}" = "-C" ]
    [ "${args[1]}" = "$WORK/.worktrees/feature" ]
    [ "${args[2]}" = "-s" ]
    [ "${args[3]}" = "workspace-write" ]
    [ "${args[4]}" = "-a" ]
    [ "${args[5]}" = "on-request" ]
    [ "${args[6]}" = "resume" ]
    [ "${args[7]}" = "--last" ]
    [ "$(cat "$FAKE_CODEX_SESSION_OPENAI_KEY")" = "unset" ]
    [ "$(cat "$FAKE_CODEX_SESSION_CODEX_KEY")" = "unset" ]
}

@test "a new worktree branches from the caller worktree HEAD" {
    git -C "$WORK" worktree add -q -b caller "$WORK/.worktrees/caller"
    printf 'caller commit\n' > "$WORK/.worktrees/caller/caller.txt"
    git -C "$WORK/.worktrees/caller" add caller.txt
    git -C "$WORK/.worktrees/caller" commit -qm caller
    local caller_head main_head
    caller_head="$(git -C "$WORK/.worktrees/caller" rev-parse HEAD)"
    main_head="$(git -C "$WORK" rev-parse HEAD)"
    [ "$caller_head" != "$main_head" ]
    cd "$WORK/.worktrees/caller"

    run bash "$SCRIPT" child

    [ "$status" -eq 0 ]
    [ "$(git -C "$WORK/.worktrees/child" rev-parse HEAD)" = "$caller_head" ]
}

@test "direct Codex launch handles a newline worktree path" {
    local newline_work="$TEST_DIR/"$'work\nnewline'
    make_repo "$newline_work"
    cd "$newline_work"

    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    mapfile -d '' args < "$FAKE_CODEX_SESSION_ARGS"
    [ "${args[0]}" = "-C" ]
    [ "${args[1]}" = "$newline_work/.worktrees/feature" ]
}

@test "registered worktree is reused but an ordinary directory is rejected" {
    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]

    run bash "$SCRIPT" feature
    [ "$status" -eq 0 ]
    [[ "$output" == *"reusing existing worktree"* ]]

    mkdir -p "$WORK/.worktrees/ordinary"
    run bash "$SCRIPT" ordinary
    [ "$status" -ne 0 ]
    [[ "$output" == *"not a registered git worktree"* ]]
}

@test "a registered branch reuses its differently named worktree path" {
    git -C "$WORK" worktree add -q -b research/topic \
        "$WORK/.worktrees/research-topic"

    run bash "$SCRIPT" research/topic

    [ "$status" -eq 0 ]
    [[ "$output" == *"reusing existing worktree $WORK/.worktrees/research-topic"* ]]
}

@test "normal Codex, global skills, and Claude state remain untouched" {
    mkdir -p "$HOME/.codex" "$HOME/.claude" "$HOME/.cache/claude-ponytail"
    printf 'normal codex\n' > "$HOME/.codex/sentinel"
    printf 'global skills\n' > "$HOME/.agents/skills/sentinel"
    printf 'claude\n' > "$HOME/.claude/sentinel"
    printf 'claude ponytail\n' > "$HOME/.cache/claude-ponytail/sentinel"

    run bash "$SCRIPT" feature

    [ "$status" -eq 0 ]
    [ "$(cat "$HOME/.codex/sentinel")" = "normal codex" ]
    [ "$(cat "$HOME/.agents/skills/sentinel")" = "global skills" ]
    [ "$(cat "$HOME/.claude/sentinel")" = "claude" ]
    [ "$(cat "$HOME/.cache/claude-ponytail/sentinel")" = "claude ponytail" ]
    run grep -F -- "brian-ed3d" "$FAKE_CODEX_CALLS"
    [ "$status" -eq 1 ]
}
