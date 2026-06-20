#!/usr/bin/env bats
# Tests for the codex-peer-review skill's runner script.
#
# `codex` is stubbed on PATH so nothing reaches OpenAI. The stub records its
# argv and stdin, writes a dummy review to the -o path, and tracks the -C work
# dir for cleanup. The script runs with cwd = TEST_DIR so the `.review/` output
# directory lands in the sandbox, not the repo.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SKILL_DIR="$REPO_ROOT/plugins/denubis-external-agents/skills/codex-peer-review"
SCRIPT="$SKILL_DIR/codex-peer-review.sh"
RUBRIC_SRC="$SKILL_DIR/review-method.md"

setup() {
    export TEST_DIR="$(mktemp -d)"
    export CODEX_ARGS_FILE="$TEST_DIR/codex-args"
    export CODEX_STDIN_FILE="$TEST_DIR/codex-stdin"
    export CODEX_WORK_TRACK="$TEST_DIR/codex-workdirs"

    local stub_bin="$TEST_DIR/bin"
    mkdir -p "$stub_bin"
    cat > "$stub_bin/codex" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CODEX_ARGS_FILE"
cat > "$CODEX_STDIN_FILE"
out="" work="" prev=""
for a in "$@"; do
    [ "$prev" = "-o" ] && out="$a"
    [ "$prev" = "-C" ] && work="$a"
    prev="$a"
done
[ -n "$work" ] && echo "$work" >> "$CODEX_WORK_TRACK"
[ -n "$out" ] && echo "# Critical Peer Review: stub" > "$out"
exit 0
STUB
    chmod +x "$stub_bin/codex"
    export PATH="$stub_bin:$PATH"

    # Run the script from the sandbox so .review/ is created there.
    cd "$TEST_DIR"
}

teardown() {
    cd "$REPO_ROOT" 2>/dev/null || cd /
    if [ -f "$CODEX_WORK_TRACK" ]; then
        while read -r w; do
            [ -n "$w" ] && rm -rf "$w" "$w.REVIEW.md"
        done < "$CODEX_WORK_TRACK"
    fi
    rm -rf "$TEST_DIR"
}

# Pull a printed "label:  value" off the script's stdout.
field() { echo "$output" | sed -n "s/^$1:[[:space:]]*//p"; }

# ── Preflight ──

@test "no target arg: exits non-zero with usage" {
    run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" == *"usage"* ]]
}

@test "nonexistent target: exits 1 with 'target not found'" {
    run bash "$SCRIPT" "$TEST_DIR/nope.md"
    [ "$status" -eq 1 ]
    [[ "$output" == *"target not found"* ]]
}

# ── Staging (throwaway bundle in /tmp) ──

@test "valid file target: stages bundled rubric and target verbatim" {
    printf 'load-bearing line one\nline two\n' > "$TEST_DIR/sample.md"

    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [ "$status" -eq 0 ]

    local pkg; pkg="$(field package)"
    [ -n "$pkg" ]
    [ -f "$pkg/REVIEW-METHOD.md" ]
    [ -f "$pkg/under-review/sample.md" ]
    diff "$pkg/REVIEW-METHOD.md" "$RUBRIC_SRC"
    diff "$pkg/under-review/sample.md" "$TEST_DIR/sample.md"
}

@test "directory target is staged recursively" {
    mkdir -p "$TEST_DIR/proj/sub"
    echo a > "$TEST_DIR/proj/a.md"; echo b > "$TEST_DIR/proj/sub/b.md"
    run bash "$SCRIPT" "$TEST_DIR/proj"
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/under-review/proj/a.md" ]
    [ -f "$pkg/under-review/proj/sub/b.md" ]
}

# ── Review output lands in .review/ (gitignored by design) ──

@test "review is written into ./.review/ in the cwd" {
    echo x > "$TEST_DIR/sample.md"
    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [ "$status" -eq 0 ]
    local rev; rev="$(field review)"
    [ -n "$rev" ]
    [ -f "$rev" ]
    [[ "$rev" == *"/.review/"* ]]
    [[ "$rev" == *"sample.md"* ]]
    [[ "$rev" == *".REVIEW.md" ]]
}

@test "auto-creates a self-ignoring .review/.gitignore when absent" {
    echo x > "$TEST_DIR/sample.md"
    [ ! -e "$TEST_DIR/.review/.gitignore" ]
    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/.review/.gitignore" ]
    grep -qx -- '*'          "$TEST_DIR/.review/.gitignore"
    grep -qx -- '!.gitignore' "$TEST_DIR/.review/.gitignore"
}

@test "does not clobber an existing .review/.gitignore" {
    echo x > "$TEST_DIR/sample.md"
    mkdir -p "$TEST_DIR/.review"
    printf 'SENTINEL-DO-NOT-TOUCH\n' > "$TEST_DIR/.review/.gitignore"
    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [ "$status" -eq 0 ]
    grep -qx -- 'SENTINEL-DO-NOT-TOUCH' "$TEST_DIR/.review/.gitignore"
}

# ── Invocation contract ──

@test "codex runs read-only, ignores user config, with -C, -o, and gpt-5.5" {
    echo x > "$TEST_DIR/sample.md"
    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [ "$status" -eq 0 ]
    [ -f "$CODEX_ARGS_FILE" ]
    grep -qx -- "exec"                 "$CODEX_ARGS_FILE"
    grep -qx -- "read-only"            "$CODEX_ARGS_FILE"
    grep -qx -- "--ignore-user-config" "$CODEX_ARGS_FILE"
    grep -qx -- "-C"                   "$CODEX_ARGS_FILE"
    grep -qx -- "-o"                   "$CODEX_ARGS_FILE"
    grep -qx -- "gpt-5.5"              "$CODEX_ARGS_FILE"
}

@test "the grounding prompt is piped to codex on stdin" {
    echo x > "$TEST_DIR/sample.md"
    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [ "$status" -eq 0 ]
    [ -f "$CODEX_STDIN_FILE" ]
    grep -q "under-review"    "$CODEX_STDIN_FILE"
    grep -q "NO TARGET FOUND" "$CODEX_STDIN_FILE"
}

# ── Provenance smoke-check guidance ──

@test "prints a provenance grep referencing the real target" {
    echo x > "$TEST_DIR/sample.md"
    run bash "$SCRIPT" "$TEST_DIR/sample.md"
    [[ "$output" == *"grep -nF"* ]]
    [[ "$output" == *"sample.md"* ]]
}
