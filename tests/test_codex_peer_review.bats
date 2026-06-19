#!/usr/bin/env bats
# Tests for the codex-peer-review skill's runner script.
#
# `codex` is stubbed on PATH so nothing reaches OpenAI. The stub records its
# argv and stdin, writes a dummy review to the -o path, and tracks the -C work
# dir for cleanup. Tests pin the script's preflight checks, its staging of the
# rubric + target, the codex invocation contract, and the piped prompt.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SKILL_DIR="$REPO_ROOT/plugins/denubis-external-agents/skills/codex-peer-review"
SCRIPT="$SKILL_DIR/codex-peer-review.sh"
RUBRIC_SRC="$SKILL_DIR/review-method.md"

setup() {
    export TEST_DIR="$(mktemp -d)"
    export CODEX_ARGS_FILE="$TEST_DIR/codex-args"
    export CODEX_STDIN_FILE="$TEST_DIR/codex-stdin"
    export CODEX_WORK_TRACK="$TEST_DIR/codex-workdirs"

    # Stub codex on PATH: record argv + stdin, write a dummy review to -o,
    # track the -C work dir so teardown can remove it without clobbering
    # any real run.
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
}

teardown() {
    # Remove only the throwaway work dirs this test's stub was told about.
    if [ -f "$CODEX_WORK_TRACK" ]; then
        while read -r w; do
            [ -n "$w" ] && rm -rf "$w" "$w.REVIEW.md"
        done < "$CODEX_WORK_TRACK"
    fi
    rm -rf "$TEST_DIR"
}

# Pull a printed "label:  /path" value off the script's stdout.
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

# ── Staging ──

@test "valid file target: stages bundled rubric and target verbatim" {
    local tgt="$TEST_DIR/sample.md"
    printf 'load-bearing line one\nline two\n' > "$tgt"

    run bash "$SCRIPT" "$tgt"
    [ "$status" -eq 0 ]

    local pkg; pkg="$(field package)"
    [ -n "$pkg" ]
    [ -f "$pkg/REVIEW-METHOD.md" ]
    [ -f "$pkg/under-review/sample.md" ]
    # Staged rubric is the bundled rubric; staged target is byte-identical.
    diff "$pkg/REVIEW-METHOD.md" "$RUBRIC_SRC"
    diff "$pkg/under-review/sample.md" "$tgt"
}

@test "valid target: codex writes a review and the path is reported" {
    local tgt="$TEST_DIR/sample.md"; echo x > "$tgt"
    run bash "$SCRIPT" "$tgt"
    [ "$status" -eq 0 ]
    local rev; rev="$(field review)"
    [ -n "$rev" ]
    [ -f "$rev" ]
}

@test "directory target is staged recursively" {
    local d="$TEST_DIR/proj"; mkdir -p "$d/sub"
    echo a > "$d/a.md"; echo b > "$d/sub/b.md"
    run bash "$SCRIPT" "$d"
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/under-review/proj/a.md" ]
    [ -f "$pkg/under-review/proj/sub/b.md" ]
}

# ── Invocation contract ──

@test "codex runs read-only, ignores user config, with -C, -o, and gpt-5.5" {
    local tgt="$TEST_DIR/sample.md"; echo x > "$tgt"
    run bash "$SCRIPT" "$tgt"
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
    local tgt="$TEST_DIR/sample.md"; echo x > "$tgt"
    run bash "$SCRIPT" "$tgt"
    [ "$status" -eq 0 ]
    [ -f "$CODEX_STDIN_FILE" ]
    grep -q "under-review"    "$CODEX_STDIN_FILE"   # review only the staged target
    grep -q "NO TARGET FOUND" "$CODEX_STDIN_FILE"   # the anti-confabulation rule
}

# ── Provenance smoke-check guidance ──

@test "prints a provenance grep referencing the staged target" {
    local tgt="$TEST_DIR/sample.md"; echo x > "$tgt"
    run bash "$SCRIPT" "$tgt"
    [[ "$output" == *"grep -nF"* ]]
    [[ "$output" == *"under-review/sample.md"* ]]
}
