# Code Review Findings — phase-2b

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 0**

## Verification

```
Tests (hook):    bats tests/test_update_live_marker.bats                         → 17/17 passed
Tests (wrapper): bats tests/test_claude_wrapper_liveness.bats                   → 19/19 passed
Tests (Python):  uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest
                   plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ → 210/210 passed
Lint:            n/a (no linter in this repo)
```

## Prior Findings Verification

### Important — sed `&`-unsafety in `update-live-marker.sh`: **Moot by deletion**

The file `plugins/denubis-plan-and-execute/hooks/update-live-marker.sh` no longer
exists in HEAD_SHA (3c22114). The finding applied to a `sed` replacement path
that has been entirely removed. The replacement `update-live-marker.py` uses
`re.sub()` with a UUID-gated replacement string containing only hex digits and
hyphens — the `sed` injection class is absent, not patched. There is no residual
`sed` call and no analogous injection surface.

## Plan Alignment

The Task 1 revision banner in `phase_02b.md` ("REVISED 2026-06-17 — implemented
in Python") governs. All contract requirements are met:

- AC4.6 marker stays live: `rewritten_marker()` rewrites only `session_id=`,
  confirmed by test 2 (byte-for-byte diff of non-session_id lines).
- AC4.6 start_time preserved: test 3 asserts the `start_time=` line is byte-
  identical before and after.
- AC4.6 append (legacy 4-key marker): test 4 confirms `session_id=` appended when
  absent; test 5 (multi-clear) confirms exactly one `session_id=` line after
  successive rewrites.
- AC4.7 safety/no-op: tests 7–13 cover unset, empty, missing marker, empty
  transcript_path, missing key, malformed JSON, non-.jsonl path.
- Atomicity: same-dir `mkstemp` + `os.replace`; mode preserved before replace
  (test 15); no temp residue on success (test 14).
- Always exit 0: `__main__` last-resort guard catches any non-`SystemExit`
  exception and exits 0; `main()` returns 0 on every branch including all
  error paths.
- `hooks.json` wired correctly: second SessionStart command is
  `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/update-live-marker.py"`.
- `claude-wrapper.sh`: comment-only change updating `.sh` → `.py`; no behaviour
  change; wrapper tests 13–19 green confirm AC4.1/AC4.5 regression-free.
- End-to-end UAT: correctly deferred to Phase 4 DR1/DR9.

Stale `.sh` references in `phase_02b.md` (original spec prose, superseded by
revision banner) and in a comment in `test_claude_wrapper_liveness.bats` line 235
are documentation/comments outside the executable path. Not a code defect.

## Issues

None.

## Review Notes

**`rewritten_marker()` correctness:** `_SESSION_ID_LINE = re.compile(r"^session_id=.*$",
re.MULTILINE)` — the `^` anchor under `MULTILINE` matches only at the start of a
line, so a value field whose content happens to begin with `session_id=` (e.g.
`argv=session_id=foo`) does not match. `count=1` ensures only the first match is
touched. The replacement string `f"session_id={uuid}"` contains no backslash
sequences, and `uuid` is gated by `_UUID.match()` in `main()` before
`rewritten_marker()` is ever called, so no `re.sub` replacement injection is
possible.

**Discriminating test (proleptic #1) is non-vacuous:** test 6 feeds distinct UUIDs
in `session_id` (A) and `transcript_path` (B), then asserts the marker carries B
and not A. This test would fail if the hook were changed to read `session_id` from
the payload — the ADR 0003 keying is asserted, not assumed.

**Parse-failure test (proleptic #2) is non-vacuous:** test 12 captures stderr
outside `run` (the bats `run` wrapper swallows stderr), feeds malformed JSON,
asserts exit 0 + marker unchanged + stderr non-empty. The pattern is correct for
bats stderr capture.

**Mode-preservation test:** test 15 sets `0644` explicitly, runs the hook, then
asserts `after_mode = "644"`. The `os.chmod(tmp_name, original_mode)` call before
`os.replace` ensures `mkstemp`'s `0600` default is overwritten on the temp file
before the inode swap.

## Decision: APPROVED FOR MERGE
