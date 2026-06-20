#!/usr/bin/env bats
# Phase 2b Task 1 (REVISED 2026-06-17 — stdlib Python) — SessionStart hook keeps
# the .live marker's session_id pointed at the live transcript. The hook rewrites
# ONLY the session_id= line to basename(transcript_path); every other line (esp.
# the load-bearing start_time=) is preserved byte-for-byte. It must always exit 0
# and never touch an unowned/absent marker. Keys off transcript_path, NOT the
# stdin session_id (ADR 0003).

bats_require_minimum_version 1.5.0

HOOK="$BATS_TEST_DIRNAME/../plugins/denubis-plan-and-execute/hooks/update-live-marker.py"

setup() {
  export CR_TEST_DIR="$(mktemp -d)"
  export CR_LIVE_FILE="$CR_TEST_DIR/12345.live"
}

teardown() {
  rm -rf "$CR_TEST_DIR"
}

# Write a marker carrying every key the wrapper writes, including the optional
# session_id= and the load-bearing start_time=. $1 = the session_id value.
_write_full_marker() {
  printf 'cwd=%s\nstarted=%s\nargv=%s\nboot_id=%s\nsession_id=%s\nstart_time=%s\n' \
    "/home/brian/work" "1718000000" "--resume $1" \
    "0fa3c1de-1111-2222-3333-444455556666" "$1" "987654" \
    > "$CR_LIVE_FILE"
}

# JSON SessionStart payload naming a live transcript whose basename is $1.jsonl.
# session_id and transcript_path basename are the SAME uuid here.
_payload_for() {
  printf '{"hook_event_name":"SessionStart","session_id":"%s","transcript_path":"/home/brian/.claude/projects/-home-brian-work/%s.jsonl","source":"clear"}' \
    "$1" "$1"
}

@test "AC4.6 replace — session_id= rewritten to basename(transcript_path)" {
  OLD="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  NEW="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
  _write_full_marker "$OLD"
  python3 "$HOOK" <<<"$(_payload_for "$NEW")"
  # New value present; old value gone.
  grep -q "^session_id=$NEW\$" "$CR_LIVE_FILE"
  ! grep -q "$OLD" "$CR_LIVE_FILE"
  # Exactly one session_id= line.
  [ "$(grep -c '^session_id=' "$CR_LIVE_FILE")" -eq 1 ]
}

@test "AC4.6 replace — every non-session_id line preserved byte-for-byte" {
  OLD="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  NEW="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
  _write_full_marker "$OLD"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  python3 "$HOOK" <<<"$(_payload_for "$NEW")"
  # Strip the session_id= line from both sides: the remainder must be identical
  # (proves nothing else moved, was dropped, or had whitespace mangled).
  run diff <(grep -v '^session_id=' "$CR_TEST_DIR/before") \
           <(grep -v '^session_id=' "$CR_LIVE_FILE")
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "AC4.6 start_time preserved — load-bearing field byte-identical after rewrite" {
  OLD="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  NEW="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
  _write_full_marker "$OLD"
  before_start_time="$(grep '^start_time=' "$CR_LIVE_FILE")"
  python3 "$HOOK" <<<"$(_payload_for "$NEW")"
  after_start_time="$(grep '^start_time=' "$CR_LIVE_FILE")"
  [ "$before_start_time" = "$after_start_time" ]
  grep -q "^start_time=987654\$" "$CR_LIVE_FILE"
}

@test "AC4.6 append — legacy 4-key marker gains a session_id= line, others intact" {
  NEW="cccccccc-cccc-cccc-cccc-cccccccccccc"
  # Legacy marker: no session_id=, no start_time= (the optional lines).
  printf 'cwd=%s\nstarted=%s\nargv=%s\nboot_id=%s\n' \
    "/home/brian/work" "1718000000" "--print hi" \
    "0fa3c1de-1111-2222-3333-444455556666" \
    > "$CR_LIVE_FILE"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  python3 "$HOOK" <<<"$(_payload_for "$NEW")"
  grep -q "^session_id=$NEW\$" "$CR_LIVE_FILE"
  [ "$(grep -c '^session_id=' "$CR_LIVE_FILE")" -eq 1 ]
  # Removing the (single) appended session_id= line returns the original file.
  run diff "$CR_TEST_DIR/before" <(grep -v '^session_id=' "$CR_LIVE_FILE")
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "AC4.6 multi-clear — A then B then C leaves a single session_id=C" {
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  B="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
  C="cccccccc-cccc-cccc-cccc-cccccccccccc"
  python3 "$HOOK" <<<"$(_payload_for "$B")"
  python3 "$HOOK" <<<"$(_payload_for "$C")"
  grep -q "^session_id=$C\$" "$CR_LIVE_FILE"
  [ "$(grep -c '^session_id=' "$CR_LIVE_FILE")" -eq 1 ]
  ! grep -q "bbbbbbbb" "$CR_LIVE_FILE"
}

@test "proleptic #1 discriminating — reads transcript_path, NOT session_id" {
  # session_id and transcript_path carry DISTINCT valid uuids. The marker must
  # take the transcript_path value (B), proving the hook keys off transcript_path
  # (ADR 0003). This FAILS if the hook is ever changed to read session_id.
  SID="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  TPATH_UUID="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
  _write_full_marker "cccccccc-cccc-cccc-cccc-cccccccccccc"
  payload="$(printf '{"hook_event_name":"SessionStart","session_id":"%s","transcript_path":"/home/brian/.claude/projects/p/%s.jsonl","source":"clear"}' \
    "$SID" "$TPATH_UUID")"
  python3 "$HOOK" <<<"$payload"
  grep -q "^session_id=$TPATH_UUID\$" "$CR_LIVE_FILE"   # took transcript_path (B)
  ! grep -q "$SID" "$CR_LIVE_FILE"                      # NOT the stdin session_id (A)
  [ "$(grep -c '^session_id=' "$CR_LIVE_FILE")" -eq 1 ]
}

@test "AC4.7 unset — no CR_LIVE_FILE: exit 0, write nothing" {
  unset CR_LIVE_FILE
  run python3 "$HOOK" <<<'{"transcript_path":"/x/abc.jsonl"}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  # Nothing created anywhere under the test dir.
  [ -z "$(ls -A "$CR_TEST_DIR")" ]
}

@test "AC4.7 empty — empty CR_LIVE_FILE: exit 0, write nothing" {
  export CR_LIVE_FILE=""
  run python3 "$HOOK" <<<'{"transcript_path":"/x/abc.jsonl"}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ -z "$(ls -A "$CR_TEST_DIR")" ]
}

@test "AC4.7 missing marker — never creates an absent marker" {
  export CR_LIVE_FILE="$CR_TEST_DIR/nonexistent/55555.live"
  run python3 "$HOOK" <<<'{"transcript_path":"/x/abc.jsonl"}'
  [ "$status" -eq 0 ]
  [ ! -e "$CR_LIVE_FILE" ]
  [ ! -d "$CR_TEST_DIR/nonexistent" ]
}

@test "AC4.7 empty transcript_path — marker unchanged, exit 0" {
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  run python3 "$HOOK" <<<'{"transcript_path":""}'
  [ "$status" -eq 0 ]
  run diff "$CR_TEST_DIR/before" "$CR_LIVE_FILE"
  [ "$status" -eq 0 ]
}

@test "AC4.7 missing transcript_path key — marker unchanged, exit 0" {
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  run python3 "$HOOK" <<<'{"session_id":"x","source":"clear"}'
  [ "$status" -eq 0 ]
  run diff "$CR_TEST_DIR/before" "$CR_LIVE_FILE"
  [ "$status" -eq 0 ]
}

@test "AC4.7 malformed JSON — marker unchanged, exit 0, diagnostic on stderr" {
  # proleptic #2: a parse failure must NOT block session start (exit 0) and must
  # leave the marker untouched, but it SHOULD surface one diagnostic line on
  # stderr (silence would hide a real misconfiguration).
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  # Redirect stderr OUTSIDE `run`: bats' `run` captures the child's stderr
  # internally, so a `2>file` attached to `run` itself never sees it.
  status=0
  python3 "$HOOK" 2>"$CR_TEST_DIR/err" <<<'{not valid json at all' || status=$?
  [ "$status" -eq 0 ]
  run diff "$CR_TEST_DIR/before" "$CR_LIVE_FILE"
  [ "$status" -eq 0 ]
  # A non-empty diagnostic line was written to stderr.
  [ -s "$CR_TEST_DIR/err" ]
}

@test "AC4.7 non-.jsonl transcript_path — marker unchanged, exit 0" {
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  run python3 "$HOOK" <<<'{"transcript_path":"/home/brian/.claude/projects/p/notjson.txt"}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  run diff "$CR_TEST_DIR/before" "$CR_LIVE_FILE"
  [ "$status" -eq 0 ]
}

@test "no temp-file residue after a successful rewrite — dir holds only the marker" {
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  python3 "$HOOK" <<<"$(_payload_for "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")"
  # The marker dir contains exactly one entry: the marker itself. mkstemp temp
  # files (if any leaked) would show up here.
  [ "$(ls -A "$CR_TEST_DIR" | wc -l)" -eq 1 ]
  [ -f "$CR_LIVE_FILE" ]
}

@test "marker permission bits preserved across the atomic replace" {
  # mkstemp creates 0600 and os.replace swaps the inode; without restoring the
  # original mode, the marker would silently narrow to 0600. The wrapper writes
  # the marker 0644-ish; preserve whatever mode it had (no behavioral delta from
  # the old bash mv-of-redirected-temp).
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  chmod 0644 "$CR_LIVE_FILE"
  before_mode="$(stat -c '%a' "$CR_LIVE_FILE")"
  python3 "$HOOK" <<<"$(_payload_for "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")"
  after_mode="$(stat -c '%a' "$CR_LIVE_FILE")"
  [ "$before_mode" = "$after_mode" ]
  [ "$after_mode" = "644" ]
}

@test "emits nothing on stdout for a successful rewrite" {
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  run python3 "$HOOK" 2>/dev/null <<<"$(_payload_for "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "AC4.7 ampersand in transcript basename — UUID regex rejects, marker unchanged, exit 0" {
  # basename "a&b" fails the UUID regex, so the marker is a no-op. (Under the old
  # sed hook this was the &-expansion corruption case; the regex makes it a clean
  # rejection.) A diagnostic line is written to stderr — assert marker-unchanged
  # + exit 0, not empty output (stderr would fold into $output under `run`).
  _write_full_marker "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
  cp "$CR_LIVE_FILE" "$CR_TEST_DIR/before"
  status=0
  python3 "$HOOK" 2>"$CR_TEST_DIR/err" <<<'{"transcript_path":"/p/a&b.jsonl"}' || status=$?
  [ "$status" -eq 0 ]
  run diff "$CR_TEST_DIR/before" "$CR_LIVE_FILE"
  [ "$status" -eq 0 ]
  # The UUID-regex rejection surfaces a diagnostic on stderr.
  [ -s "$CR_TEST_DIR/err" ]
}
