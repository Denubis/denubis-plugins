#!/usr/bin/env bats

WRAPPER="$BATS_TEST_DIRNAME/../plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh"

setup() {
  export CR_TEST_DIR="$(mktemp -d)"
  export CRASH_RECOVERY_RUN_DIR="$CR_TEST_DIR/run"
  mkdir -p "$CRASH_RECOVERY_RUN_DIR"
  # Stub claude binary: behaviour controlled by FAKE_CLAUDE_EXIT_CODE env var.
  cat > "$CR_TEST_DIR/fake-claude.sh" <<'EOF'
#!/usr/bin/env bash
exit "${FAKE_CLAUDE_EXIT_CODE:-0}"
EOF
  chmod +x "$CR_TEST_DIR/fake-claude.sh"
  export CLAUDE_REAL_BINARY="$CR_TEST_DIR/fake-claude.sh"
}

teardown() {
  rm -rf "$CR_TEST_DIR"
}

@test "AC5.1 — wrapper writes liveness file with four required keys at startup" {
  # Stub claude that sleeps so we can inspect the liveness file mid-run.
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "test" &
  wrapper_pid=$!
  sleep 0.5  # let the wrapper write the liveness file
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]
  grep -q "^cwd=" "$live_file"
  grep -q "^started=" "$live_file"
  grep -q "^argv=" "$live_file"
  grep -q "^boot_id=" "$live_file"
  # boot_id value matches the system's current boot_id
  expected_boot_id=$(cat /proc/sys/kernel/random/boot_id)
  grep -q "^boot_id=$expected_boot_id\$" "$live_file"
  wait "$wrapper_pid"
}

@test "AC5.2 — clean exit (0) removes the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=0 "$WRAPPER" --print "test"
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]
}

@test "AC5.2 — Ctrl-C exit (130) removes the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=130 "$WRAPPER" --print "test" || true  # wrapper exits non-zero
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]
}

@test "AC5.5 — Claude exit 137 (SIGKILL) preserves the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=137 "$WRAPPER" --print "test" || true
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 1 ]
}

@test "AC5.5 — Claude exit 139 (SIGSEGV) preserves the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=139 "$WRAPPER" --print "test" || true
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 1 ]
}

@test "AC5.5 — Claude generic non-zero exit (1) preserves the liveness file" {
  FAKE_CLAUDE_EXIT_CODE=1 "$WRAPPER" --print "test" || true
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 1 ]
}

@test "AC5.3 — kill -9 of wrapper preserves the liveness file" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 10
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "test" &
  wrapper_pid=$!
  sleep 0.5
  # Verify file exists pre-kill
  [ -f "$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live" ]
  kill -9 "$wrapper_pid"
  wait "$wrapper_pid" 2>/dev/null || true
  # File must still exist (wrapper had no chance to clean up)
  [ -f "$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live" ]
}

@test "AC5.4 — concurrent wrappers write distinct liveness files" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "first" &
  pid1=$!
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --print "second" &
  pid2=$!
  sleep 0.5
  [ "$pid1" != "$pid2" ]
  [ -f "$CRASH_RECOVERY_RUN_DIR/$pid1.live" ]
  [ -f "$CRASH_RECOVERY_RUN_DIR/$pid2.live" ]
  wait "$pid1" "$pid2"
  # Both should be cleaned (both exited 0)
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]
}

@test "wrapper records user-supplied argv verbatim in the liveness file" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b &
  wrapper_pid=$!
  sleep 0.5
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  grep -q "argv=.*--resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b" "$live_file"
  wait "$wrapper_pid"
}

@test "no .tmp residue after clean completion" {
  # Asserts no .tmp file persists at the target path under any timing.
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/fake-claude.sh" FAKE_CLAUDE_EXIT_CODE=0 "$WRAPPER" --print "test"
  # After completion, no .tmp leftovers
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.tmp 2>/dev/null | wc -l)" -eq 0 ]
}

@test "M3 — wrapper liveness format flows through scan → render to Idle-live killed" {
  # Closes Phase 8 coherence-review gap: no automated test pins the chain
  # "wrapper writes <pid>.live → crash-recovery scan reads it → render emits
  # the UUID in the right section". Each layer is tested separately; this
  # test exercises the full path so a format-skew regression on either side
  # is caught immediately.
  #
  # Flow:
  #   1. Run the wrapper to clean completion so AC5.2 lifecycle is observed
  #      (file written, then removed on exit 0).
  #   2. Synthesise a post-crash liveness file by hand, using the exact
  #      key=value format the wrapper writes (cwd / started / argv / boot_id),
  #      a dead PID in the filename, and the current kernel boot_id.
  #   3. Build a matching JSONL under projects_root with a TOOL_USE_NO_RESULT
  #      tail so the classifier returns hard_crash via the dead-pid rule.
  #   4. Drive `crash-recovery init`, `scan`, `render` from the same dirs.
  #   5. Assert the rendered markdown shows the UUID under "Idle-live killed".
  FAKE_CLAUDE_EXIT_CODE=0 "$WRAPPER" --print "lifecycle-warmup"
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.live 2>/dev/null | wc -l)" -eq 0 ]

  # Hand-crafted post-crash liveness file.
  CRASHED_UUID="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
  CRASHED_CWD="/tmp/crash-recovery-m3-cwd"
  STARTED=$(($(date +%s) - 3600))
  BOOT_ID=$(cat /proc/sys/kernel/random/boot_id)
  # Dead PID: large number unlikely to be in use; bats teardown will not
  # collide because the file is under the per-test CR_TEST_DIR.
  DEAD_PID=999999
  printf 'cwd=%s\nstarted=%s\nargv=--resume %s\nboot_id=%s\n' \
    "$CRASHED_CWD" "$STARTED" "$CRASHED_UUID" "$BOOT_ID" \
    > "$CRASH_RECOVERY_RUN_DIR/$DEAD_PID.live"

  # Matching JSONL with cwd header + tool_use-no-result tail.
  PROJECTS_ROOT="$CR_TEST_DIR/projects"
  ENCODED_DIR="$PROJECTS_ROOT/-tmp-crash-recovery-m3-cwd"
  mkdir -p "$ENCODED_DIR"
  JSONL="$ENCODED_DIR/$CRASHED_UUID.jsonl"
  # ISO-8601 UTC with millisecond precision; entry timestamp >= started.
  ISO_TS=$(date -u -d "@$((STARTED + 1))" '+%Y-%m-%dT%H:%M:%S.000Z')
  printf '%s\n%s\n' \
    "{\"type\":\"user\",\"cwd\":\"$CRASHED_CWD\",\"timestamp\":\"$ISO_TS\",\"message\":{\"content\":[]}}" \
    "{\"type\":\"assistant\",\"timestamp\":\"$ISO_TS\",\"message\":{\"stop_reason\":\"tool_use\",\"content\":[{\"type\":\"tool_use\",\"id\":\"toolu_m3_001\",\"name\":\"Bash\",\"input\":{}}]}}" \
    > "$JSONL"

  # Run init → scan → render via the same CLI invocation form the smoke
  # bats test uses (uv run --project ... crash-recovery).
  CR_CLI="uv run --project ${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"
  DB_PATH="$CR_TEST_DIR/crash-recovery.db"
  RESUME_PATH="$CR_TEST_DIR/llm-resume.md"

  run $CR_CLI init --db "$DB_PATH"
  [ "$status" -eq 0 ]

  run $CR_CLI scan --db "$DB_PATH" --run-dir "$CRASH_RECOVERY_RUN_DIR" --projects-root "$PROJECTS_ROOT"
  [ "$status" -eq 0 ]

  run $CR_CLI render --db "$DB_PATH" --output "$RESUME_PATH"
  [ "$status" -eq 0 ]

  # The synthesised session must appear under "Idle-live killed".
  grep -q "^## Idle-live killed" "$RESUME_PATH"
  # awk extracts the body of the section: lines after the "Idle-live killed"
  # header and before the next "## " heading. A naive range pattern
  # /header/,/^## / would stop at the header line itself; this flag-based
  # form is the conventional awk idiom for "everything between two headings".
  section=$(awk '/^## Idle-live killed/{flag=1; next} /^## /{flag=0} flag' "$RESUME_PATH")
  echo "$section" | grep -q "${CRASHED_UUID:0:8}"
  echo "$section" | grep -q "$CRASHED_UUID"
}

@test "M4 — user-supplied argv reaches the real claude binary intact" {
  # Closes Phase 8 coherence-review gap: the wrapper invokes
  #   "$REAL_CLAUDE" --disallowedTools ... --teammate-mode=auto "${EXTRA_ARGS[@]}" "$@"
  # but no test asserts that "$@" actually arrives at the real binary. A
  # regression that dropped or mangled "$@" would be invisible. This test
  # replaces the fake-claude stub with one that captures argv to a file,
  # then asserts the user-supplied tokens are present.
  CAPTURE_FILE="$BATS_TEST_TMPDIR/captured-argv.txt"
  cat > "$CR_TEST_DIR/capture-claude.sh" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$@" > "$CAPTURE_FILE"
exit 0
EOF
  chmod +x "$CR_TEST_DIR/capture-claude.sh"

  # --resume short-circuits the wrapper's EXTRA_ARGS so the captured argv
  # mirrors the user's tokens cleanly (no injected --session-id). The
  # primary assertion is that --resume + its UUID + --print + "hello world"
  # all survive verbatim.
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/capture-claude.sh" \
    "$WRAPPER" --resume db0cc58f-dc30-4195-a64a-4f25a5c19d6b --print "hello world"
  [ -f "$CAPTURE_FILE" ]

  # Positive: user-supplied tokens survive verbatim.
  grep -qx -- "--resume" "$CAPTURE_FILE"
  grep -qx "db0cc58f-dc30-4195-a64a-4f25a5c19d6b" "$CAPTURE_FILE"
  grep -qx -- "--print" "$CAPTURE_FILE"
  grep -qx "hello world" "$CAPTURE_FILE"

  # Positive evidence the wrapper also injected its own flags ahead of "$@".
  grep -qx -- "--disallowedTools" "$CAPTURE_FILE"
  grep -qx -- "--teammate-mode=auto" "$CAPTURE_FILE"
}

@test "M1 fitness — abnormal claude exit skips transcript-archive prompt" {
  # Phase 8 coherence-review M1: the `|| EXIT_CODE=$?` fix made the transcript-archive
  # block structurally reachable for non-zero exits, where pre-Phase-8 `set -e` would
  # have aborted before reaching it. The exit-0 gate preserves the pre-Phase-8
  # effective contract. This test locks the gate: on a non-zero claude exit, the
  # "Press Enter to archive transcript" prompt MUST NOT fire even when the cwd is a
  # transcripting project and a transcript JSONL exists.
  export HOME="$CR_TEST_DIR/home"
  mkdir -p "$HOME/.claude/projects/test-project"

  PROJECT_DIR="$CR_TEST_DIR/project"
  mkdir -p "$PROJECT_DIR/.ai-transcripts"

  # Stub that creates the JSONL the wrapper's transcript-lookup expects, then exits 1.
  cat > "$CR_TEST_DIR/jsonl-claude.sh" <<'EOF'
#!/usr/bin/env bash
session_id=""
prev=""
for arg in "$@"; do
  [[ "$prev" == "--session-id" ]] && { session_id="$arg"; break; }
  prev="$arg"
done
[[ -n "$session_id" ]] && touch "$HOME/.claude/projects/test-project/${session_id}.jsonl"
exit 1
EOF
  chmod +x "$CR_TEST_DIR/jsonl-claude.sh"

  cd "$PROJECT_DIR"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/jsonl-claude.sh" run "$WRAPPER"

  [ "$status" -eq 1 ]
  ! echo "$output" | grep -q "Press Enter to archive transcript"
}
