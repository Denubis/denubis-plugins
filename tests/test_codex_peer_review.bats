#!/usr/bin/env bats
# Tests for the codex-peer-review runner.
#
# codex is stubbed on PATH (nothing reaches OpenAI). The script stages the
# target's git repo MINUS gitignored files into a throwaway dir and points codex
# at it, so the review has cross-reference context while gitignored files (raw
# data, secrets) are absent from codex's working tree.

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
}

teardown() {
    cd "$REPO_ROOT" 2>/dev/null || cd /
    if [ -f "$CODEX_WORK_TRACK" ]; then
        while read -r w; do [ -n "$w" ] && rm -rf "$w" "$w.REVIEW.md"; done < "$CODEX_WORK_TRACK"
    fi
    rm -rf "$TEST_DIR"
}

field() { echo "$output" | sed -n "s/^$1:[[:space:]]*//p"; }

# A git repo with a target, a non-ignored ref, and a gitignored secret.
make_repo() {
    local repo="$1"
    mkdir -p "$repo/docs" "$repo/data"
    ( cd "$repo" && git init -q && git config user.email t@t && git config user.name t )
    printf 'review me; analysis lives in code.py\n' > "$repo/docs/target.md"
    printf 'def analyze(): return 1\n'              > "$repo/code.py"
    printf 'PARTICIPANT,SECRET\n1,sensitive\n'       > "$repo/data/raw.csv"
    printf 'data/\n'                                 > "$repo/.gitignore"
}

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

# ── Staging: repo minus gitignored (the core safety behaviour) ──

@test "git repo: non-ignored context staged, gitignored files ABSENT" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/REVIEW-METHOD.md" ]
    [ -f "$pkg/context/docs/target.md" ]
    [ -f "$pkg/context/code.py" ]
    # the safety guarantee — gitignored data is not in codex's tree:
    [ ! -e "$pkg/context/data/raw.csv" ]
    [ ! -e "$pkg/context/data" ]
}

@test "git repo: staged target and rubric are byte-identical to source" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    diff "$pkg/context/docs/target.md" "$TEST_DIR/repo/docs/target.md"
    diff "$pkg/REVIEW-METHOD.md" "$RUBRIC_SRC"
}

@test "git repo: a gitignored TARGET is still staged (explicit choice overrides ignore)" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'secret/\n' >> .gitignore
    mkdir -p secret; printf 'review this ignored file\n' > secret/note.md
    run bash "$SCRIPT" secret/note.md
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/context/secret/note.md" ]
}

@test "git repo: binary files (e.g. PDFs) are skipped from context" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'PDF\000\001\002binary\000content\n' > "$TEST_DIR/repo/docs/paper.pdf"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/context/docs/target.md" ]    # text kept
    [ ! -e "$pkg/context/docs/paper.pdf" ]  # binary skipped
}

@test "git repo: prompt names the target and scopes the rest as context" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    grep -q 'docs/target.md'  "$CODEX_STDIN_FILE"
    grep -qi 'context'        "$CODEX_STDIN_FILE"
    grep -q 'NO TARGET FOUND' "$CODEX_STDIN_FILE"
}

# ── Non-git fallback ──

@test "non-git target: reviews the file alone with a warning" {
    echo x > "$TEST_DIR/loose.md"; cd "$TEST_DIR"
    run bash "$SCRIPT" loose.md
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/context/loose.md" ]
    [[ "$output" == *"not a git repo"* ]]
}

# ── Review output → .review/ (gitignored) ──

@test "review is written into ./.review/ in the cwd" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    local rev; rev="$(field review)"
    [ -f "$rev" ]
    [[ "$rev" == *"/.review/"* ]]
    [[ "$rev" == *".REVIEW.md" ]]
}

@test "auto-creates a self-ignoring .review/.gitignore when absent" {
    echo x > "$TEST_DIR/loose.md"; cd "$TEST_DIR"
    [ ! -e "$TEST_DIR/.review/.gitignore" ]
    run bash "$SCRIPT" loose.md
    [ "$status" -eq 0 ]
    grep -qx -- '*'          "$TEST_DIR/.review/.gitignore"
    grep -qx -- '!.gitignore' "$TEST_DIR/.review/.gitignore"
}

@test "does not clobber an existing .review/.gitignore" {
    echo x > "$TEST_DIR/loose.md"; cd "$TEST_DIR"
    mkdir -p .review; printf 'SENTINEL\n' > .review/.gitignore
    run bash "$SCRIPT" loose.md
    [ "$status" -eq 0 ]
    grep -qx -- 'SENTINEL' .review/.gitignore
}

# ── Invocation contract ──

@test "codex runs read-only, ignores user config, with -C, -o, gpt-5.5" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    grep -qx -- "exec"                 "$CODEX_ARGS_FILE"
    grep -qx -- "read-only"            "$CODEX_ARGS_FILE"
    grep -qx -- "--ignore-user-config" "$CODEX_ARGS_FILE"
    grep -qx -- "-C"                   "$CODEX_ARGS_FILE"
    grep -qx -- "-o"                   "$CODEX_ARGS_FILE"
    grep -qx -- "gpt-5.5"              "$CODEX_ARGS_FILE"
}

# ── Provenance smoke-check ──

@test "prints a provenance grep referencing the real target" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [[ "$output" == *"grep -nF"* ]]
    [[ "$output" == *"target.md"* ]]
}
