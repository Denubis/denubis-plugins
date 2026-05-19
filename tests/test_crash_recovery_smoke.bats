#!/usr/bin/env bats
# End-to-end smoke test for the denubis-crash-recovery CLI pipeline.
#
# Exercises the same commands the triage skill invokes (init, triage,
# regenerate, prune) plus a marketplace-listing assertion (closest automatable
# proxy for AC1.2). Regression guard for future refactors.

setup() {
  export CRASH_RECOVERY_TEST_TMP="$(mktemp -d)"
  export CRASH_RECOVERY_DB="$CRASH_RECOVERY_TEST_TMP/x.db"
  export CRASH_RECOVERY_RUN_DIR="$CRASH_RECOVERY_TEST_TMP/run"
  export CRASH_RECOVERY_PROJECTS_ROOT="$CRASH_RECOVERY_TEST_TMP/projects"
  export CRASH_RECOVERY_RESUME_PATH="$CRASH_RECOVERY_TEST_TMP/llm-resume.md"
  mkdir -p "$CRASH_RECOVERY_RUN_DIR" "$CRASH_RECOVERY_PROJECTS_ROOT"
}

teardown() {
  rm -rf "$CRASH_RECOVERY_TEST_TMP"
}

CR="uv run --project ${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery"

@test "init creates the database" {
  run $CR init
  [ "$status" -eq 0 ]
  [ -f "$CRASH_RECOVERY_DB" ]
}

@test "triage on empty filesystem prints minimal render with six sections" {
  $CR init
  run $CR triage
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "Currently unfinished"
  echo "$output" | grep -q "Idle-live killed"
  echo "$output" | grep -q "Ambiguous correlation"
  echo "$output" | grep -q "Needs investigation"
  echo "$output" | grep -q "Recently concluded"
  echo "$output" | grep -q "Irrecoverable"
}

@test "regenerate writes file at CRASH_RECOVERY_RESUME_PATH" {
  $CR init
  $CR regenerate
  [ -f "$CRASH_RECOVERY_RESUME_PATH" ]
  grep -q "# Claude Code session resume" "$CRASH_RECOVERY_RESUME_PATH"
}

@test "render is byte-identical across two calls (AC3.2 smoke)" {
  $CR init
  $CR regenerate
  first_hash=$(sha256sum "$CRASH_RECOVERY_RESUME_PATH" | cut -d' ' -f1)
  $CR regenerate
  second_hash=$(sha256sum "$CRASH_RECOVERY_RESUME_PATH" | cut -d' ' -f1)
  [ "$first_hash" = "$second_hash" ]
}

@test "prune without --confirm refuses (AC7.3 smoke)" {
  $CR init
  run $CR prune
  [ "$status" -ne 0 ]
  echo "$output" | grep -q "confirm"
}

@test "denubis-crash-recovery is listed in marketplace.json" {
  python3 -c "
import json
m = json.load(open('${BATS_TEST_DIRNAME}/../.claude-plugin/marketplace.json'))
assert any(p['name'] == 'denubis-crash-recovery' for p in m['plugins'])
"
}
