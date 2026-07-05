# Post-mortem crash detection — Phase 2b: marker tracks the live transcript (SessionStart hook)

**Goal:** Keep the `.live` marker's `session_id` pointed at the **live** transcript across `/clear` rotation, so `correlate()`'s exact match is correct (not merely exact). The wrapper stamps a bootstrap `session_id` at launch; a `SessionStart` hook rewrites it to `basename(transcript_path)` on every `startup`/`resume`/`clear`/`compact`. `correlate.py` is unchanged — Phase 2 Task 4 closes as correct-as-built.

**Why this phase exists:** ADR 0003. A read-only diagnostic proved the marker goes stale: `/clear` spawns a new session id + a new `<uuid>.jsonl`, the once-at-launch stamp names the abandoned transcript, and on crash the `hard_crash` flag binds to the cleared session while the live work shows only as a quieter row (worst on reboot). The forensic correlation revision was retired in favour of keeping the marker honest at runtime.

**RED-before-build confirmation (done 2026-06-16):** isolated probe at `/tmp/ss-probe` showed `SessionStart` on `/clear` delivers `transcript_path` whose basename is the NEW live uuid (`3efc902e → 7c8c00d2`). `basename(transcript_path)` is the live file by construction — the key we write. (Stdin `session_id` also tracked the rotation in the probe, but `transcript_path` is the principled, unambiguous source; a launch-pinned id namespace exists elsewhere, e.g. the `/tmp` task-dir, that does not track rotation.)

**Architecture:** `denubis-plan-and-execute` owns the wrapper and the marker write/format, so it also owns the marker-update hook. A new standalone script `hooks/update-live-marker.py` is registered as a **second** `SessionStart` command (the existing `session-start.sh` skill-injection hook is untouched — each command receives the same stdin payload). The hook is global (fires for every session) and no-ops unless `CR_LIVE_FILE` is set, so non-claudew sessions are unaffected.

**Tech Stack:** bash hook (with a one-line `python3` JSON extraction — `python3` is guaranteed in this repo), bats. No change to the Python `crash_recovery` package or `correlate.py`.

**Scope:** Closes the Phase 2 marker work reopened by the correlation revision. Depends on Phase 2 (wrapper writes `session_id`/`start_time`; `pid_alive_checked`).

**Codebase verified:** 2026-06-16 (commit 368ca55). `plugins/denubis-plan-and-execute/hooks/hooks.json` already registers a `SessionStart` hook with matcher `startup|resume|clear|compact` → `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` (skill injection; ignores stdin). The wrapper writes `CR_LIVE_FILE="$CR_RUN_DIR/$$.live"` as a **local** var.

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

- **crash-detection.AC4.6 (marker stays live):** `SessionStart` rewrites the marker's `session_id=` line to `basename(transcript_path)`, preserving every other line and the PID-keyed filename; survives multi-clear A→B→C (ends at C).
- **crash-detection.AC4.7 (safety):** no-op + exit 0 when `CR_LIVE_FILE` is unset/empty or the marker is absent, or `transcript_path` is empty — never blocks session start, never touches an unowned marker.
- **Regression:** AC4.1 (wrapper still writes a bootstrap `session_id`/`start_time` at startup) and AC4.5 (clean/abnormal-exit cleanup) stay green.

---

## Context for the implementer

- **Marker format** (verbatim, written by the wrapper): newline-terminated `key=value` lines — `cwd=`, `started=`, `argv=`, `boot_id=`, optional `session_id=`, optional `start_time=`. Only the `session_id=` line may change here.
- **`start_time` is load-bearing:** it drives `pid_alive_checked` (PID-reuse rejection). A naive "regenerate the marker" would recompute or drop it. **Replace only the `session_id=` line; copy the rest byte-for-byte.**
- **SessionStart payload (stdin JSON):** carries `transcript_path` (absolute path to the live `<uuid>.jsonl`) and `session_id`. Use `transcript_path`.
- **bats harness:** `tests/test_claude_wrapper_liveness.bats` `setup()` exports `CR_TEST_DIR`, `CRASH_RECOVERY_RUN_DIR`, a `fake-claude.sh` stub via `CLAUDE_REAL_BINARY`. New hook is invokable directly: `CR_LIVE_FILE=<marker> bash <hook> <<<"$json"`.
- **NO linter in this repo.** Gates: `bats tests/test_claude_wrapper_liveness.bats` and `uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/` (the latter must stay green; this phase does not touch it). Never run ruff.

---

<!-- START_TASK_1 -->
### Task 1: `update-live-marker` SessionStart hook (TDD)

**Verifies:** crash-detection.AC4.6 (core), crash-detection.AC4.7

> **REVISED 2026-06-17 — implemented in Python (stdlib), not bash/`sed`.** The original bash/`sed` spec below is superseded. Rationale: the `sed` replacement bred a `&`-expansion corruption bug (caught in phase-2b review) and required a hex shape-guard *crutch*; the hook already shelled out to `python3` for JSON parsing, so a pure stdlib-Python rewrite eliminates the entire `sed`-injection class. Package home (`crash_recovery` CLI) rejected: `crash-recovery` is not on PATH and `uv run` per-SessionStart is too fragile/slow; `liveness.py` has no marker-write helper to reuse. **New form:** `plugins/denubis-plan-and-execute/hooks/update-live-marker.py`, invoked via plain `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/update-live-marker.py"` (stdlib only — `json`, `os`, `re`, `pathlib`, `tempfile`). **Contract unchanged** (rewrite ONLY the `session_id=` line to `basename(transcript_path .jsonl)`, preserve every other line incl. `start_time` byte-for-byte, atomic `os.replace`, always exit 0, no-op when `CR_LIVE_FILE` unset/missing or `transcript_path` empty/non-`.jsonl`/not-a-UUID). **Added** (folding in phase-2b proleptic concerns #1/#2): a discriminating test with *distinct* uuids in `session_id` vs `transcript_path` asserting the marker takes the `transcript_path` value; a stderr diagnostic line on JSON-parse failure (still exit 0). The `a&b.jsonl` test stays as a no-op (now rejected by the UUID regex, not a sed crutch).

**Files:**
- Create: `plugins/denubis-plan-and-execute/hooks/update-live-marker.py`
- Test: `tests/test_update_live_marker.bats` (new bats file in the repo-root `tests/` dir, alongside `test_claude_wrapper_liveness.bats`; mirror the existing suite's `setup()` patterns where useful)

**Implementation (contract — implement exactly, robustly):**
The script reads the SessionStart JSON on stdin and updates `$CR_LIVE_FILE`:

1. Read all of stdin into a variable.
2. No-op + `exit 0` if `CR_LIVE_FILE` is unset or empty, or the file `$CR_LIVE_FILE` does not exist. (Never create a marker; never touch an unowned one.)
3. Extract `transcript_path` from the JSON with a `python3` one-liner:
   `python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("transcript_path") or "")'` (feed it the captured payload). On any parse error → empty.
4. No-op + `exit 0` if `transcript_path` is empty or does not end in `.jsonl`.
5. `uuid="$(basename "$transcript_path" .jsonl)"`; no-op + `exit 0` if empty.
6. Rewrite **only** the `session_id=` line of the marker, preserving all other lines verbatim and their order:
   - if a `^session_id=` line exists → replace its value (use `sed` with `|` delimiter; the uuid is hex+dashes, delimiter-safe);
   - else → append `session_id=<uuid>\n`.
   Write to a temp file in the same dir, then atomic `mv` over `$CR_LIVE_FILE`.
7. Always `exit 0`. No internal failure may propagate non-zero or leave the marker partially written (only the atomic `mv` mutates it). Emit nothing on stdout (registered with `suppressOutput`, but don't rely on it).

**Testing (bats, RED first):**
- AC4.6 replace: marker with `session_id=AAAA…` (+ `cwd`/`started`/`argv`/`boot_id`/`start_time`); feed JSON `{"transcript_path":".../BBBB….jsonl",...}`; assert marker `session_id=BBBB…` AND every other line byte-identical (grep each).
- AC4.6 append: marker WITHOUT a `session_id=` line (legacy 4-key) → after hook, `session_id=<uuid>` appended, other lines intact.
- AC4.6 multi-clear: run the hook twice (B then C) → marker ends `session_id=C`; one `session_id=` line only.
- AC4.6 `start_time` preserved: assert the `start_time=` line is byte-identical after the rewrite (guards the load-bearing field).
- AC4.7 unset: `unset CR_LIVE_FILE`; hook exits 0, writes nothing.
- AC4.7 missing marker: `CR_LIVE_FILE=/nonexistent/x.live`; hook exits 0, creates nothing.
- AC4.7 empty/garbage transcript_path: `{"transcript_path":""}` and malformed JSON → marker unchanged, exit 0.

**Verification:** `bats tests/test_update_live_marker.bats` all green. Show the RED (pre-implementation failing run) then GREEN.

**Commit:** `feat(plan-and-execute): SessionStart hook keeps .live session_id on the live transcript`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Wire the hook — wrapper exports `CR_LIVE_FILE`, register in hooks.json

**Verifies:** crash-detection.AC4.6 (integration), AC4.1/AC4.5 regression

**Files:**
- Modify: `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` (export `CR_LIVE_FILE`)
- Modify: `plugins/denubis-plan-and-execute/hooks/hooks.json` (add the second SessionStart command)
- Test: `tests/test_claude_wrapper_liveness.bats` (integration assertions)

**Implementation:**
1. Wrapper: change `CR_LIVE_FILE="$CR_RUN_DIR/$$.live"` to also `export CR_LIVE_FILE` so the hook subprocess (a descendant of the wrapper via claude) inherits it. Keep the existing bootstrap `session_id` derivation and `start_time` write as-is (AC4.1 stays green) — the hook makes steady-state correct; the wrapper bootstrap keeps the marker valid before the first `SessionStart` fires. Do NOT remove the launch-time `CR_SESSION_ID` block (its bats tests are load-bearing); only add the `export`.
2. `hooks.json`: add a second command to the existing `SessionStart` matcher block, after `session-start.sh`:
   `{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/update-live-marker.py", "suppressOutput": true }`.

**Testing (bats):**
- AC4.6 integration: through the wrapper (sleep-claude pattern), confirm `CR_LIVE_FILE` is exported into the child environment (e.g. the fake-claude stub records `$CR_LIVE_FILE`, or assert via a hook-style invocation that the env var is visible). A full real-`/clear` round-trip is NOT unit-testable here — it folds into the Phase 4 DR1/DR9 UAT.
- AC4.1 / AC4.5 regression: the existing wrapper tests stay green (bootstrap `session_id`/`start_time` still written; clean/abnormal-exit cleanup unchanged).

**Verification:** `bats tests/test_claude_wrapper_liveness.bats` all green (18 existing + new); `bats tests/test_update_live_marker.bats` green; `uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/` still 210 green (untouched).

**Commit:** `feat(plan-and-execute): export CR_LIVE_FILE and register the marker-update SessionStart hook`
<!-- END_TASK_2 -->

## Phase 2b done when

- The hook rewrites only `session_id=` to `basename(transcript_path)`, preserving all other lines incl. `start_time`; no-ops safely when unowned (AC4.6, AC4.7).
- The wrapper exports `CR_LIVE_FILE`; the hook is registered as a second SessionStart command; bootstrap stamp + cleanup unchanged (AC4.1, AC4.5).
- bats green (wrapper suite + new hook suite); crash_recovery pytest still 210 green; `correlate.py` untouched.
- The end-to-end "real `/clear` → crash → triage points at the live session" claim is recorded as DR1/DR9 UAT, not asserted by units.
