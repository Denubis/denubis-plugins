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
    # Hermetic codex config: the runner reads the operator's default model from
    # $CODEX_HOME/config.toml, so tests must never depend on the real one.
    export CODEX_HOME="$TEST_DIR/codex-home"
    mkdir -p "$CODEX_HOME"
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

@test "include option without a value exits non-zero with a clear message" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md --include
    [ "$status" -ne 0 ]
    [[ "$output" == *"include path required after --include"* ]]
}

@test "nonexistent include exits 1 with 'include not found'" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/missing.md"
    [ "$status" -eq 1 ]
    [[ "$output" == *"include not found: $TEST_DIR/missing.md"* ]]
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

@test "git repo: a DIRECTORY target is staged, not fatal" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/context/docs/target.md" ]
}

@test "git repo: a gitignored DIRECTORY target is staged despite the ignore" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'notes/\n' >> .gitignore
    mkdir -p notes; printf 'ignored but chosen\n' > notes/memo.md
    run bash "$SCRIPT" notes
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/context/notes/memo.md" ]
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

@test "git repo: binary files inside a DIRECTORY target are skipped" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'PDF\000\001\002binary\000content\n' > "$TEST_DIR/repo/docs/paper.pdf"
    run bash "$SCRIPT" docs
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/context/docs/target.md" ]
    [ ! -e "$pkg/context/docs/paper.pdf" ]
}

# ── Explicit evidence inclusion ──

@test "a single included file is staged outside the normal context tree" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'external evidence\n' > "$TEST_DIR/evidence.md"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/evidence.md" --include-confirmed
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    diff "$pkg/included/001/evidence.md" "$TEST_DIR/evidence.md"
}

@test "two include options keep same-named files under distinct ordinals" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    mkdir -p "$TEST_DIR/first" "$TEST_DIR/second"
    printf 'first evidence\n' > "$TEST_DIR/first/evidence.md"
    printf 'second evidence\n' > "$TEST_DIR/second/evidence.md"
    run bash "$SCRIPT" docs/target.md \
        --include "$TEST_DIR/first/evidence.md" \
        --include "$TEST_DIR/second/evidence.md" --include-confirmed
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    diff "$pkg/included/001/evidence.md" "$TEST_DIR/first/evidence.md"
    diff "$pkg/included/002/evidence.md" "$TEST_DIR/second/evidence.md"
}

@test "an included directory stages text recursively but skips binaries" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    mkdir -p "$TEST_DIR/evidence/nested"
    printf 'rendered result\n' > "$TEST_DIR/evidence/nested/result.txt"
    printf 'PDF\000\001\002binary\000content\n' > "$TEST_DIR/evidence/paper.pdf"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/evidence" --include-confirmed
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ -f "$pkg/included/001/evidence/nested/result.txt" ]
    [ ! -e "$pkg/included/001/evidence/paper.pdf" ]
}

@test "an explicitly included gitignored file is force-staged" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md --include data/raw.csv --include-confirmed
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    [ ! -e "$pkg/context/data/raw.csv" ]
    diff "$pkg/included/001/raw.csv" data/raw.csv
}

@test "an explicitly included binary file is staged byte-for-byte" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'PDF\000\001\002binary\000content\n' > "$TEST_DIR/paper.pdf"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/paper.pdf" --include-confirmed
    [ "$status" -eq 0 ]
    local pkg; pkg="$(field package)"
    diff "$pkg/included/001/paper.pdf" "$TEST_DIR/paper.pdf"
}

@test "prints every included source with its staged destination" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'first evidence\n' > "$TEST_DIR/first.md"
    printf 'second evidence\n' > "$TEST_DIR/second.md"
    run bash "$SCRIPT" docs/target.md \
        --include "$TEST_DIR/first.md" --include "$TEST_DIR/second.md" --include-confirmed
    [ "$status" -eq 0 ]
    [[ "$output" == *"include:  $TEST_DIR/first.md -> included/001/first.md"* ]]
    [[ "$output" == *"include:  $TEST_DIR/second.md -> included/002/second.md"* ]]
}

@test "prompt names staged evidence without disclosing its source path" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'external evidence\n' > "$TEST_DIR/evidence.md"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/evidence.md" --include-confirmed
    [ "$status" -eq 0 ]
    grep -Fqx 'INCLUDED EVIDENCE: included/001/evidence.md' "$CODEX_STDIN_FILE"
    ! grep -Fq "$TEST_DIR/evidence.md" "$CODEX_STDIN_FILE"
}

@test "git repo: prompt names the target and scopes the rest as context" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    grep -q 'docs/target.md'  "$CODEX_STDIN_FILE"
    grep -qi 'context'        "$CODEX_STDIN_FILE"
    grep -q 'NO TARGET FOUND' "$CODEX_STDIN_FILE"
}

@test "git repo: directory prompt treats every reviewable text file as the target set" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs
    [ "$status" -eq 0 ]
    grep -Fq \
        'If the named target is a directory, enumerate its files, read every reviewable text file within it, and treat that whole set as the target.' \
        "$CODEX_STDIN_FILE"
    grep -Fq \
        'For a file target, absence means the named file is not present; for a directory target, absence means the named directory is not present or contains no reviewable text files.' \
        "$CODEX_STDIN_FILE"
    grep -Fq \
        'Produce the review in the output format `REVIEW-METHOD.md` specifies, for the target file or target set. Output only the review.' \
        "$CODEX_STDIN_FILE"
}

@test "git repo: directory prompt requires a target-set manifest" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs
    [ "$status" -eq 0 ]
    grep -Fq \
        'For a directory target only, open the review with a target-set manifest before the `Document reviewed:` header.' \
        "$CODEX_STDIN_FILE"
    grep -Fq \
        'List every file in the staged target set exactly once, recursively and in path order, using its path under `./context/`.' \
        "$CODEX_STDIN_FILE"
    grep -Fq -- '- [read] <path>' "$CODEX_STDIN_FILE"
    grep -Fq -- '- [skipped: <one-phrase reason>] <path>' "$CODEX_STDIN_FILE"
    grep -Fq \
        'Skip a staged file only if it is genuinely unreadable or empty.' \
        "$CODEX_STDIN_FILE"
    grep -Fq 'Then write `Document reviewed: <directory path>`.' "$CODEX_STDIN_FILE"
}

@test "git repo: file prompt explicitly omits the target-set manifest" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    grep -Fq \
        'For a file target, do not include a target-set manifest; use `Document reviewed: <file path>` as usual.' \
        "$CODEX_STDIN_FILE"
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

@test "bare second positional remains the focus note when include is absent" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md "prioritise citation checks"
    [ "$status" -eq 0 ]
    [ "$(field focus)" = "prioritise citation checks" ]
    grep -Fq 'prioritise citation checks' "$CODEX_STDIN_FILE"
}

@test "codex runs read-only, ignores user config, with -C and -o" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    grep -qx -- "exec"                 "$CODEX_ARGS_FILE"
    grep -qx -- "read-only"            "$CODEX_ARGS_FILE"
    grep -qx -- "-C"                   "$CODEX_ARGS_FILE"
    grep -qx -- "-o"                   "$CODEX_ARGS_FILE"
}

@test "isolation is preserved: --ignore-user-config is always passed" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'model = "gpt-9.9-fictional"\n' > "$CODEX_HOME/config.toml"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    # The reviewer must stay clear of the operator's MCP servers, hooks and
    # instructions; only the model tracks their config.
    grep -qx -- "--ignore-user-config" "$CODEX_ARGS_FILE"
}

# ── Model resolution: track the operator's codex default, never pin ──

@test "model comes from the operator's codex config, not a hardcoded pin" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'model = "gpt-9.9-fictional"\n' > "$CODEX_HOME/config.toml"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    grep -qx -- "-m"                 "$CODEX_ARGS_FILE"
    grep -qx -- "gpt-9.9-fictional"  "$CODEX_ARGS_FILE"
}

@test "no model key in config: -m is omitted so codex picks its own default" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'model_reasoning_effort = "xhigh"\n' > "$CODEX_HOME/config.toml"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    ! grep -qx -- "-m" "$CODEX_ARGS_FILE"
}

@test "absent config file: -m is omitted rather than erroring" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    [ ! -e "$CODEX_HOME/config.toml" ]
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    ! grep -qx -- "-m" "$CODEX_ARGS_FILE"
}

@test "a model key inside a [section] is not mistaken for the top-level default" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    cat > "$CODEX_HOME/config.toml" <<'TOML'
model_reasoning_effort = "xhigh"

[profiles.other]
model = "gpt-should-not-be-used"
TOML
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    ! grep -qx -- "gpt-should-not-be-used" "$CODEX_ARGS_FILE"
}

@test "reports the resolved model so the review can be labelled accurately" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'model = "gpt-9.9-fictional"\n' > "$CODEX_HOME/config.toml"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    [ "$(field model)" = "gpt-9.9-fictional" ]
}

@test "reports the fallback plainly when no model is configured" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [ "$status" -eq 0 ]
    [[ "$(field model)" == *"codex default"* ]]
}

# ── Provenance smoke-check ──

@test "prints a provenance grep referencing the real target" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [[ "$output" == *"grep -nF"* ]]
    [[ "$output" == *"target.md"* ]]
}

@test "prints the mandatory 2-3 phrase provenance gate" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md
    [[ "$output" == *"2–3 verbatim quoted phrases"* ]]
    [[ "$output" == *"prioritise every High-severity finding"* ]]
    [[ "$output" == *"file its finding attributes it to"* ]]
    [[ "$output" == *"or context"* ]]
    [[ "$output" == *"grep -nF '<quoted phrase>' '<attributed file>'"* ]]
}

# ── Include disclosure gate ──
#
# --include stages a path from anywhere on the filesystem into a package that is
# sent to an external model, deliberately escaping the gitignore boundary the
# default staging enforces. Printing the path after the fact is a receipt, not a
# control, so transmission is gated on explicit confirmation and the manifest
# enumerates what actually goes.

@test "includes abort before codex runs when confirmation is absent" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'evidence\n' > "$TEST_DIR/evidence.md"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/evidence.md" < /dev/null
    [ "$status" -ne 0 ]
    [[ "$output" == *"--include-confirmed"* ]]
    [ ! -f "$CODEX_ARGS_FILE" ]
}

@test "--include-confirmed permits the run to reach codex" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'evidence\n' > "$TEST_DIR/evidence.md"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/evidence.md" \
        --include-confirmed < /dev/null
    [ "$status" -eq 0 ]
    [ -f "$CODEX_ARGS_FILE" ]
}

@test "a directory include enumerates every staged file, not just its name" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    mkdir -p "$TEST_DIR/evidence/nested"
    printf 'one\n' > "$TEST_DIR/evidence/first.txt"
    printf 'two\n' > "$TEST_DIR/evidence/nested/second.txt"
    run bash "$SCRIPT" docs/target.md --include "$TEST_DIR/evidence" \
        --include-confirmed < /dev/null
    [ "$status" -eq 0 ]
    [[ "$output" == *"included/001/evidence/first.txt"* ]]
    [[ "$output" == *"included/001/evidence/nested/second.txt"* ]]
    [[ "$output" == *"2 file"* ]]
}

@test "an unrecognised option is a hard error, never a focus note" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    printf 'evidence\n' > "$TEST_DIR/evidence.md"
    run bash "$SCRIPT" docs/target.md --includ "$TEST_DIR/evidence.md"
    [ "$status" -ne 0 ]
    [[ "$output" == *"unrecognised option: --includ"* ]]
}

@test "a surplus positional is a hard error rather than a silent drop" {
    make_repo "$TEST_DIR/repo"; cd "$TEST_DIR/repo"
    run bash "$SCRIPT" docs/target.md "first note" "second note"
    [ "$status" -ne 0 ]
    [[ "$output" == *"unexpected argument: second note"* ]]
}
