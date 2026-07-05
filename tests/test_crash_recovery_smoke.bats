#!/usr/bin/env bats
# Smoke test for the denubis-crash-recovery CLI.
#
# Verifies the commands the triage skill invokes (init / triage / regenerate /
# prune) run without error and produce expected scaffolding, plus a
# marketplace-listing assertion (closest automatable proxy for AC1.2).
# Regression guard for future refactors.
#
# Scope note: these tests exercise CLI plumbing on an empty filesystem. They
# do NOT verify crash-detection capability — that requires liveness files,
# which only exist after Phase 8 ships the wrapper patch. Detection-level
# tests are part of Phase 8's lifecycle suite, not this smoke suite.

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

@test "triage (lean) on empty filesystem shows actionable sections, collapses bulk" {
  $CR init
  run $CR triage
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "Probable system-crash victims"
  echo "$output" | grep -q "Currently unfinished"
  echo "$output" | grep -q "Ambiguous correlation"
  echo "$output" | grep -q "Needs investigation"
  # Lean view: with nothing on the filesystem there is no bulk, so the
  # concluded/irrecoverable sections are absent and there is no Collapsed summary.
  ! echo "$output" | grep -q "Recently concluded"
  ! echo "$output" | grep -q "Irrecoverable"
}

@test "triage --all on empty filesystem prints the full six-section roster" {
  $CR init
  run $CR triage --all
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "Probable system-crash victims"
  echo "$output" | grep -q "Currently unfinished"
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
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "confirm"
}

@test "denubis-crash-recovery is listed in marketplace.json" {
  python3 -c "
import json
m = json.load(open('${BATS_TEST_DIRNAME}/../.claude-plugin/marketplace.json'))
assert any(p['name'] == 'denubis-crash-recovery' for p in m['plugins'])
"
}

@test "README documents the sibling-plugin dependency (AC8.1)" {
  grep -q 'denubis-plan-and-execute' "${BATS_TEST_DIRNAME}/../plugins/denubis-crash-recovery/README.md"
}
