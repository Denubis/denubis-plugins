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

@test "AC5.7 — clean exit removes the marker BEFORE the archive-prompt block" {
  # A clean claude exit (0) in a transcripting project makes the wrapper block on
  # "Press Enter to archive transcript". The marker cleanup MUST happen before that
  # blocking prompt, not after it — otherwise closing the terminal at the prompt
  # strands a dead-PID marker that triage reads as a crash (the archive-prompt-close
  # false positive: a concluded session that looks abnormal). This pins the ordering
  # by holding the wrapper at the prompt and asserting the marker is already gone.
  export HOME="$CR_TEST_DIR/home"
  mkdir -p "$HOME/.claude/projects/test-project"
  PROJECT_DIR="$CR_TEST_DIR/project"
  mkdir -p "$PROJECT_DIR/ai_transcripts"   # transcripting project → prompt fires

  # Stub: touch the JSONL for the injected --session-id, then exit 0 (clean).
  cat > "$CR_TEST_DIR/jsonl-claude.sh" <<'EOF'
#!/usr/bin/env bash
session_id=""
prev=""
for arg in "$@"; do
  [[ "$prev" == "--session-id" ]] && { session_id="$arg"; break; }
  prev="$arg"
done
[[ -n "$session_id" ]] && touch "$HOME/.claude/projects/test-project/${session_id}.jsonl"
exit 0
EOF
  chmod +x "$CR_TEST_DIR/jsonl-claude.sh"

  # FIFO as the wrapper's stdin so the archive prompt's `read -r` BLOCKS: fd 9 is
  # held open for writing, so the reader sees no EOF and waits.
  fifo="$CR_TEST_DIR/prompt.fifo"
  mkfifo "$fifo"
  exec 9<>"$fifo"

  # No flags → fresh interactive (SHOULD_TRANSCRIPT=true), so the prompt path runs.
  cd "$PROJECT_DIR"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/jsonl-claude.sh" "$WRAPPER" <"$fifo" &
  wrapper_pid=$!
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  # The FIFO holds the wrapper blocked at the archive prompt (no input). The fixed
  # wrapper removes the marker BEFORE that prompt; the old one only after it. Poll
  # for the marker to be gone rather than a fixed sleep, so the test stays robust
  # on a loaded machine. Up to ~5s.
  removed=0
  for _ in $(seq 1 50); do
    if [ ! -f "$live_file" ]; then removed=1; break; fi
    sleep 0.1
  done
  # The wrapper must still be alive — i.e. blocked at the prompt — which proves it
  # actually reached the prompt path and removed the marker before it, rather than
  # dying before writing (which would make absence a false pass).
  kill -0 "$wrapper_pid" 2>/dev/null
  [ "$removed" -eq 1 ]

  # Unblock the prompt and reap the wrapper.
  printf '\n' >&9
  exec 9>&-
  wait "$wrapper_pid" 2>/dev/null || true
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

@test "M3 — wrapper liveness format flows through scan → render to Probable system-crash victims" {
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
  #   5. Assert the rendered markdown shows the UUID under "Probable system-crash victims".
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

  # The synthesised session must appear under "Probable system-crash victims".
  grep -q "^## Probable system-crash victims" "$RESUME_PATH"
  # awk extracts the body of the section: lines after the "Probable system-crash victims"
  # header and before the next "## " heading. A naive range pattern
  # /header/,/^## / would stop at the header line itself; this flag-based
  # form is the conventional awk idiom for "everything between two headings".
  section=$(awk '/^## Probable system-crash victims/{flag=1; next} /^## /{flag=0} flag' "$RESUME_PATH")
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

@test "AC4.6 integration — wrapper exports CR_LIVE_FILE into the child environment" {
  # Phase 2b Task 2: the SessionStart hook (update-live-marker.sh) runs as a
  # descendant of the wrapper via claude and must inherit CR_LIVE_FILE to know
  # which marker to rewrite. A real /clear round-trip is not unit-testable
  # (Phase 4 DR1/DR9 UAT); this test pins the necessary precondition — the env
  # var is EXPORTED, not merely a local var — by having the stub child record
  # what it sees in its environment.
  #
  # The ${CR_LIVE_FILE:-} guard in the stub is load-bearing for a clean RED:
  # before the export is added the child sees it unset, so the capture is empty
  # and the assertion fails as a value mismatch, not as a set -u abort.
  CAPTURE_FILE="$BATS_TEST_TMPDIR/captured-cr-live-file.txt"
  cat > "$CR_TEST_DIR/capture-env-claude.sh" <<EOF
#!/usr/bin/env bash
printf '%s' "\${CR_LIVE_FILE:-}" > "$CAPTURE_FILE"
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/capture-env-claude.sh"

  CLAUDE_REAL_BINARY="$CR_TEST_DIR/capture-env-claude.sh" "$WRAPPER" --print "test" &
  wrapper_pid=$!
  sleep 0.5  # let the wrapper exec the child, which records its environment
  [ -f "$CAPTURE_FILE" ]
  # The child inherits the wrapper's $$, so CR_LIVE_FILE is <wrapper_pid>.live.
  [ "$(cat "$CAPTURE_FILE")" = "$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live" ]
  wait "$wrapper_pid"
}

@test "AC4.1 — resumed session stamps session_id=<uuid> and start_time=<int>" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  RESUME_UUID="db0cc58f-dc30-4195-a64a-4f25a5c19d6b"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --resume "$RESUME_UUID" &
  wrapper_pid=$!
  sleep 0.5
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]
  grep -q "^session_id=$RESUME_UUID\$" "$live_file"
  grep -qE "^start_time=[0-9]+\$" "$live_file"
  wait "$wrapper_pid"
}

@test "AC4.1 — fresh interactive session stamps a UUID-shaped session_id and start_time" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  # No resume/print/session-id flags → fresh interactive: wrapper-generated
  # SESSION_ID is in EXTRA_ARGS and must be stamped. cd to a non-transcripting
  # dir so the clean-exit transcript path stays inert.
  cd "$CR_TEST_DIR"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" &
  wrapper_pid=$!
  sleep 0.5
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]
  grep -qE "^session_id=[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\$" "$live_file"
  grep -qE "^start_time=[0-9]+\$" "$live_file"
  wait "$wrapper_pid"
}

@test "AC4.2 — written start_time equals the wrapper's real comm-safe /proc start time" {
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 2
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"
  cd "$CR_TEST_DIR"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" &
  wrapper_pid=$!
  sleep 0.5
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]
  # Independently compute the wrapper's start time with the SAME comm-safe
  # rpartition logic (strip through the last ") ", starttime is the 20th token).
  stat=$(cat "/proc/$wrapper_pid/stat")
  rest=${stat##*) }
  # shellcheck disable=SC2086
  set -- $rest
  expected_start_time="${20-}"
  [ -n "$expected_start_time" ]
  grep -q "^start_time=$expected_start_time\$" "$live_file"
  wait "$wrapper_pid"
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

# ---------------------------------------------------------------------------
# Cross-language start_time seam (Phase 2). The wrapper (bash) writes
# start_time from /proc/<pid>/stat field 22 via _proc_starttime; the reader
# (python liveness.py::_proc_start_time) parses the same field and
# pid_alive_checked() compares the stored value against a fresh /proc read for
# a LIVE pid. If the two parsers ever disagreed on the field index, every live
# session's stored start_time would mismatch on read-back, pid_alive_checked
# would return False, and live sessions would mass-misclassify as crashed.
#
# Existing coverage does NOT exercise the MATCHING/True round-trip THROUGH the
# wrapper: the M3 test uses a hand-synthesised DEAD pid (pid_alive_checked
# short-circuits before comparing start_time), and Task 3's python positive
# control (test_scan_live_pid_with_correct_start_time_is_live) generated the
# fixture start_time with python's own _proc_start_time, not the wrapper's bash.
#
# These two tests pin the seam as a self-certifying pair:
#   (a) real live wrapper + correlatable live-shaped JSONL → classifies LIVE,
#       and the marker contains a start_time= line (so the comparison branch,
#       not the start_time-is-None back-compat branch, is exercised).
#   (b) identical setup, but the marker's start_time= line is mutated to a
#       different integer while the pid stays alive → classifies CRASHED.
# (b) passing proves start_time is consulted (load-bearing), so (a)'s "live"
# is via the genuine comparison through the wrapper-written value — not a
# vacuous green where start_time is ignored.
#
# Live-shaped tail = TOOL_USE_NO_RESULT (the same shape Task 3's
# test_scan_live_pid_with_correct_start_time_is_live and the M3 test use). It
# is load-bearing for the pair: the LIVE rule (classify.py RULES) takes any
# trailing_kind when pid_alive=True+boot_current=True, but the matching
# HARD_CRASH fallback for a DEAD pid requires a dead-pid tail kind —
# TOOL_USE_NO_RESULT routes to liveness_dead_pid_tool_use_no_result. A
# CONCLUDED tail would fall through to borderline/unmatched in (b), not crash.
#
# Authoritative live classification value: db.py CLASSIFICATION_VALUES ("live");
# render.py _section_for_row maps "live" → "## Currently unfinished" and
# "hard_crash" → "## Probable system-crash victims".

# Helper: build a correlatable live-shaped JSONL whose first record's cwd
# equals $1 (the wrapper's cwd, used by correlate._project_dir_for_cwd) and
# whose tail is a dangling tool_use (TOOL_USE_NO_RESULT). $2 = lowercase uuid,
# $3 = projects-root dir. Mirrors the M3 test's two-line hand-rolled JSONL.
_cr_build_live_jsonl() {
  local cwd="$1" uuid="$2" projects_root="$3"
  # Encoded dir name is lossy and resolution is by-content, so the exact
  # directory name is irrelevant — _project_dir_for_cwd matches on the
  # first-record cwd. Use a fixed encoded-style name.
  local encoded_dir="$projects_root/-cr-seam-live"
  mkdir -p "$encoded_dir"
  local jsonl="$encoded_dir/$uuid.jsonl"
  local iso_ts
  iso_ts=$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')
  printf '%s\n%s\n' \
    "{\"type\":\"user\",\"cwd\":\"$cwd\",\"timestamp\":\"$iso_ts\",\"message\":{\"content\":[]}}" \
    "{\"type\":\"assistant\",\"timestamp\":\"$iso_ts\",\"message\":{\"stop_reason\":\"tool_use\",\"content\":[{\"type\":\"tool_use\",\"id\":\"toolu_seam_001\",\"name\":\"Bash\",\"input\":{}}]}}" \
    > "$jsonl"
}

@test "seam — wrapper-written start_time round-trips so a live session classifies LIVE" {
  # Long-lived stub: the wrapper pid must stay alive THROUGH the scan, which
  # reads /proc/<wrapper_pid>/stat for the start_time comparison. Three cold
  # `uv run` invocations can exceed a short sleep, so use a generous one.
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 120
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"

  SEAM_UUID="db0cc58f-dc30-4195-a64a-4f25a5c19d6b"  # lowercase: correlate lowercases session_id
  WORK_CWD="$CR_TEST_DIR/work"
  mkdir -p "$WORK_CWD"
  PROJECTS_ROOT="$CR_TEST_DIR/projects"
  DB_PATH="$CR_TEST_DIR/crash-recovery.db"
  RESUME_PATH="$CR_TEST_DIR/llm-resume.md"
  CR_CLI="uv run --project ${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"

  # init BEFORE launching so the slow cold-start is outside the live window.
  run $CR_CLI init --db "$DB_PATH"
  [ "$status" -eq 0 ]

  # Launch the REAL wrapper from WORK_CWD with --resume <uuid>. The wrapper
  # stamps session_id=<uuid>, argv=--resume <uuid>, and start_time from its
  # own /proc via bash _proc_starttime, then writes the marker via atomic mv.
  # cd in the test body (NOT a subshell) so $! is the wrapper's own pid — the
  # marker filename is <wrapper_pid>.live ($$ inside the wrapper). A
  # ( cd ... && wrapper ) & subshell would make $! the subshell's pid, not the
  # wrapper's, and the marker lookup would miss. bats runs each test in its own
  # subshell, so this cd does not leak; the CLI calls below use absolute paths.
  cd "$WORK_CWD"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --resume "$SEAM_UUID" &
  wrapper_pid=$!
  sleep 0.5  # let the wrapper write the marker
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]
  # The comparison branch (not the start_time-is-None back-compat branch) must
  # be the one exercised: the marker must carry a start_time= line.
  grep -qE "^start_time=[0-9]+\$" "$live_file"

  # Correlatable live-shaped JSONL: first-record cwd == wrapper cwd, dangling
  # tool_use tail. session_id DIRECT_MATCH then resolves the project dir by
  # content and finds <uuid>.jsonl.
  _cr_build_live_jsonl "$WORK_CWD" "$SEAM_UUID" "$PROJECTS_ROOT"

  # Drive scan → render WHILE the wrapper is still alive.
  run $CR_CLI scan --db "$DB_PATH" --run-dir "$CRASH_RECOVERY_RUN_DIR" --projects-root "$PROJECTS_ROOT"
  [ "$status" -eq 0 ]
  run $CR_CLI render --db "$DB_PATH" --output "$RESUME_PATH"
  [ "$status" -eq 0 ]

  # Tear the wrapper down now that the live window is no longer needed.
  kill "$wrapper_pid" 2>/dev/null || true
  wait "$wrapper_pid" 2>/dev/null || true

  # Section-scoped assertions. render emits EVERY section header (empty ones
  # get an empty_message), so a bare file-wide grep would pass vacuously.
  # Extract each section body with the M3 awk idiom and assert per-section.
  unfinished=$(awk '/^## Currently unfinished/{flag=1; next} /^## /{flag=0} flag' "$RESUME_PATH")
  killed=$(awk '/^## Probable system-crash victims/{flag=1; next} /^## /{flag=0} flag' "$RESUME_PATH")
  # LIVE → "## Currently unfinished".
  echo "$unfinished" | grep -q "$SEAM_UUID"
  echo "$unfinished" | grep -q "live_pid_present_boot_current"
  # And NOT under "## Probable system-crash victims".
  ! echo "$killed" | grep -q "$SEAM_UUID"
}

@test "seam — mutating the wrapper-written start_time flips a live session to CRASHED" {
  # Non-vacuity proof: same live wrapper + same correlatable live-shaped JSONL
  # as the round-trip test, but after the marker is written we mutate ONLY the
  # start_time= line to real+1 while the pid stays alive. The wrapper writes
  # the marker once at startup (atomic mv) and never rewrites it, so the
  # mutation is stable. pid_alive_checked then sees a live pid whose real
  # /proc start_time no longer matches the stored value → False → the dead-pid
  # rule fires → hard_crash → "## Probable system-crash victims".
  cat > "$CR_TEST_DIR/sleep-claude.sh" <<'EOF'
#!/usr/bin/env bash
sleep 120
exit 0
EOF
  chmod +x "$CR_TEST_DIR/sleep-claude.sh"

  SEAM_UUID="db0cc58f-dc30-4195-a64a-4f25a5c19d6b"
  WORK_CWD="$CR_TEST_DIR/work"
  mkdir -p "$WORK_CWD"
  PROJECTS_ROOT="$CR_TEST_DIR/projects"
  DB_PATH="$CR_TEST_DIR/crash-recovery.db"
  RESUME_PATH="$CR_TEST_DIR/llm-resume.md"
  CR_CLI="uv run --project ${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"

  run $CR_CLI init --db "$DB_PATH"
  [ "$status" -eq 0 ]

  # cd in the test body (not a subshell) so $! is the wrapper's own pid; see
  # the round-trip test for why a subshell would break the marker lookup.
  cd "$WORK_CWD"
  CLAUDE_REAL_BINARY="$CR_TEST_DIR/sleep-claude.sh" "$WRAPPER" --resume "$SEAM_UUID" &
  wrapper_pid=$!
  sleep 0.5
  live_file="$CRASH_RECOVERY_RUN_DIR/$wrapper_pid.live"
  [ -f "$live_file" ]

  # Read the real wrapper-written start_time, then rewrite that line to real+1.
  real_start_time=$(grep -oE "^start_time=[0-9]+\$" "$live_file" | cut -d= -f2)
  [ -n "$real_start_time" ]
  mutated_start_time=$((real_start_time + 1))
  # Replace only the start_time= line; leave every other key untouched.
  sed -i "s/^start_time=.*\$/start_time=$mutated_start_time/" "$live_file"
  grep -q "^start_time=$mutated_start_time\$" "$live_file"

  _cr_build_live_jsonl "$WORK_CWD" "$SEAM_UUID" "$PROJECTS_ROOT"

  run $CR_CLI scan --db "$DB_PATH" --run-dir "$CRASH_RECOVERY_RUN_DIR" --projects-root "$PROJECTS_ROOT"
  [ "$status" -eq 0 ]
  run $CR_CLI render --db "$DB_PATH" --output "$RESUME_PATH"
  [ "$status" -eq 0 ]

  kill "$wrapper_pid" 2>/dev/null || true
  wait "$wrapper_pid" 2>/dev/null || true

  # CRASHED → hard_crash → "## Probable system-crash victims"; NOT under "Currently unfinished".
  unfinished=$(awk '/^## Currently unfinished/{flag=1; next} /^## /{flag=0} flag' "$RESUME_PATH")
  killed=$(awk '/^## Probable system-crash victims/{flag=1; next} /^## /{flag=0} flag' "$RESUME_PATH")
  echo "$killed" | grep -q "$SEAM_UUID"
  echo "$killed" | grep -q "liveness_dead_pid_tool_use_no_result"
  ! echo "$unfinished" | grep -q "$SEAM_UUID"
}
