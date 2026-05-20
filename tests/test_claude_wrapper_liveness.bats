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

@test "wrapper writes liveness file atomically via tempfile + mv (no .tmp residue)" {
  # Asserts no .tmp file persists at the target path under any timing.
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/fake-claude.sh" FAKE_CLAUDE_EXIT_CODE=0 "$WRAPPER" --print "test"
  # After completion, no .tmp leftovers
  [ "$(ls -1 "$CRASH_RECOVERY_RUN_DIR"/*.tmp 2>/dev/null | wc -l)" -eq 0 ]
}
