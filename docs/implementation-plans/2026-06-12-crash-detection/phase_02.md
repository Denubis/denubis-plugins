# Post-mortem crash detection — Phase 2: wrapper stamps + start-time-checked liveness

**Goal:** Stamp `session_id` and `start_time` into every `.live`; teach `liveness.py` to read them and to reject PID reuse via a start-time-checked liveness probe; teach `correlate.py` to prefer the exact `session_id`.

**Architecture:** The wrapper computes the effective session UUID and its own process start time and writes two additive `.live` lines. `liveness.py` parses the optional keys and adds `_proc_start_time(pid)` + `pid_alive_checked(pid, expected)`. `scan.py` uses the checked probe; `correlate.py` adds a `session_id` exact-match branch ahead of the `--resume` path.

**Tech Stack:** bash (`claude-wrapper.sh`), Python 3.14+ stdlib, pytest, bats.

**Scope:** Phase 2 of 5 from `docs/design-plans/2026-06-12-crash-detection.md`. Depends on Phase 1.

**Codebase verified:** 2026-06-12 (commit 03b97f2; bats harness + liveness/correlate read this session).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

### crash-detection.AC4: Wrapper stamps and start-time-checked liveness
- **crash-detection.AC4.1 Success:** The wrapper writes `session_id=` and `start_time=` into the `.live` at startup, for both fresh and resumed sessions.
- **crash-detection.AC4.2 Success:** A marker whose stored `start_time` matches `/proc/<pid>/stat` is alive; a recycled-PID marker (mismatched `start_time`) is dead.
- **crash-detection.AC4.3 Success:** A `session_id`-bearing marker direct-matches `<session_id>.jsonl`.
- **crash-detection.AC4.4 Back-compat:** A legacy marker without `start_time` falls back to `kill -0`; without `session_id` falls to Stage-2.
- **crash-detection.AC4.5 Regression:** Clean exit (0/130) still removes the `.live`; abnormal exit (137/139/non-zero) preserves it.

---

## Context for the implementer

- **Wrapper:** `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh`. It currently writes `cwd`, `started`, `argv`, `boot_id` (lines ~89-101) and removes the file only on exit 0/130 (lines ~140-147). It generates `SESSION_ID=$(uuidgen)` and passes `--session-id "$SESSION_ID"` via `EXTRA_ARGS` for fresh interactive sessions; for `--resume/-r/--continue/-c` and `-p/--print/--session-id/--bare/--no-session-persistence` it sets `EXTRA_ARGS=()`.
- **`/proc/<pid>/stat` trap (DR4):** field 2 (`comm`) can contain spaces/parens (`(sd-pam)`, `(kworker/0:1H-kblockd)`). A naive `split()[21]`/`$22` reads the wrong field. **Always** parse the substring AFTER the last `)`; `starttime` (field 22) is then the 20th token of that remainder (fields 3..22).
- **bats harness:** `tests/test_claude_wrapper_liveness.bats` — `setup()` exports `CR_TEST_DIR`, `CRASH_RECOVERY_RUN_DIR`, a `fake-claude.sh` stub via `CLAUDE_REAL_BINARY`, `FAKE_CLAUDE_EXIT_CODE`. The sleep-claude pattern inspects the `.live` mid-run. `$wrapper_pid.live` is the marker.
- **Liveness fixture:** `make_liveness_file(run_dir, pid, cwd, started, argv, boot_id)` writes the four-key file. Extend it with optional `session_id` / `start_time` kwargs (omit the line when `None`, so legacy fixtures stay four-key).

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Wrapper writes session_id + start_time

**Verifies:** crash-detection.AC4.1, crash-detection.AC4.2 (write side), crash-detection.AC4.5 (regression)

**Files:**
- Modify: `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` (the liveness-write block, ~89-101)
- Test: `tests/test_claude_wrapper_liveness.bats` (bats)

**Implementation:**
In the liveness-write block, before writing the file, compute two values:

1. **Effective session id** (omit the line if not determinable):
   - If the user args contain `--resume <uuid>` or `-r <uuid>`: that uuid.
   - Else if the user args contain `--session-id <uuid>`: that uuid.
   - Else if this is a fresh interactive session (we generated `SESSION_ID` and put it in `EXTRA_ARGS`): `$SESSION_ID`.
   - Else (e.g. `--continue` with no uuid, `--print` with no session): omit `session_id`.
   Validate the uuid shape loosely (non-empty); the reader re-validates.

2. **start_time** of the wrapper process (`$$`), comm-safe:
   ```bash
   _proc_starttime() {  # $1 = pid; echoes field-22 starttime or nothing
     local stat rest
     stat=$(cat "/proc/$1/stat" 2>/dev/null) || return 0
     rest=${stat##*) }          # strip through the last ") " — defeats comm-with-spaces
     # shellcheck disable=SC2086
     set -- $rest               # $1=state(field3) ... $20=starttime(field22)
     printf '%s' "${20-}"
   }
   ```
   Add `start_time` to the heredoc only when `_proc_starttime $$` is non-empty.

Append to the existing `{ ... } > "$CR_LIVE_TMP"` block:
```bash
    [ -n "$CR_SESSION_ID" ] && printf 'session_id=%s\n' "$CR_SESSION_ID"
    CR_START_TIME="$(_proc_starttime $$)"
    [ -n "$CR_START_TIME" ] && printf 'start_time=%s\n' "$CR_START_TIME"
```
Keep the atomic `mv` and the unchanged cleanup block (exit 0/130 removal).

**Testing (bats):**
- AC4.1 (resumed): invoke the wrapper (sleep-claude) with `--resume <uuid>` → `$wrapper_pid.live` has `session_id=<uuid>` and a `start_time=<int>` line.
- AC4.1 (fresh): invoke with no resume/print flags (sleep-claude) → `.live` has a `session_id=` that is a valid UUID, and `start_time=<int>`.
- AC4.2 (write correctness): the written `start_time` equals the wrapper's real start time — compare against `_proc_starttime $wrapper_pid` computed in the test (same rpartition logic), proving the comm-safe parse.
- AC4.5 (regression, already covered): the existing clean-exit-removes / abnormal-exit-preserves tests stay green.

**Verification:** `bats tests/test_claude_wrapper_liveness.bats` — all green (13 existing + new).

**Commit:** `feat(plan-and-execute): wrapper stamps session_id + start_time in .live`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: liveness.py parses the keys and adds start-time-checked liveness

**Verifies:** crash-detection.AC4.2, crash-detection.AC4.4 (start_time half)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/liveness.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py` (extend `make_liveness_file`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_liveness.py` (unit)

**Implementation:**
- Add `session_id: str | None` and `start_time: int | None` to the frozen `Liveness` dataclass.
- In `read_liveness`: after the required-key loop, read optional `session_id` (str or None) and `start_time` (int via tolerant parse — wrap `ValueError` to `None` rather than raising, since legacy/odd files must not break enumeration). `_REQUIRED_KEYS` stays the four; do not add these.
- Add `_proc_start_time(pid)`:
  ```python
  def _proc_start_time(pid: int) -> int | None:
      try:
          data = Path(f"/proc/{pid}/stat").read_text()
      except OSError:
          return None
      try:
          after = data.rsplit(")", 1)[1]      # comm-safe: split on the LAST ')'
          return int(after.split()[19])        # field 22 = index 19 after the ')'
      except (IndexError, ValueError):
          return None
  ```
- Add `pid_alive_checked(pid, expected_start_time)`:
  ```python
  def pid_alive_checked(pid: int, expected_start_time: int | None) -> bool:
      if not pid_alive(pid):
          return False
      if expected_start_time is None:
          return True                          # back-compat: legacy marker, bare kill -0
      actual = _proc_start_time(pid)
      return actual is not None and actual == expected_start_time
  ```
  Keep `pid_alive` unchanged (still used as the primitive).
- Extend `make_liveness_file` with `session_id: str | None = None`, `start_time: int | None = None`; append the lines only when provided.

**Testing (test_liveness.py):**
- AC4.2: `pid_alive_checked(os.getpid(), _proc_start_time(os.getpid()))` is `True`; with a deliberately wrong `expected_start_time` (e.g. `... + 1`) it is `False`; for a dead pid (`_pick_dead_pid()`) it is `False` regardless.
- AC4.4: `pid_alive_checked(os.getpid(), None)` falls back to bare liveness → `True` (and dead pid + None → `False`).
- read_liveness: a `.live` with `session_id`/`start_time` → parsed onto the dataclass; a legacy four-key file → both `None`, no error.

**Verification:** `uv run pytest .../tests/test_liveness.py -q` green.

**Commit:** `feat(crash-recovery): liveness parses session_id/start_time; start-time-checked probe`
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-4) -->

<!-- START_TASK_3 -->
### Task 3: scan uses the start-time-checked probe

**Verifies:** crash-detection.AC4.2 (scan integration)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py` (`_build_liveness_fact_direct_or_mtime`, `_build_ambiguous_facts`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py` (integration)

**Implementation:**
Replace `pid_alive(liveness.pid)` with `pid_alive_checked(liveness.pid, liveness.start_time)` in both fact builders (import `pid_alive_checked`). This makes a recycled PID (start_time mismatch) classify dead → the session reaches `hard_crash` instead of being pinned `live`. Legacy markers (`start_time is None`) keep current behaviour.

**Testing (test_scan.py):**
- AC4.2: a fixture marker whose PID is alive (e.g. `os.getpid()`) but whose `start_time` is wrong → the session is treated as dead (not classified `live`). A marker with the correct `start_time` (use `_proc_start_time(os.getpid())`) and a live-shaped tail → `live`. (Extend `FixtureSession`/`make_full_fixture` to thread `start_time` into the written marker.)

**Verification:** `uv run pytest .../tests/test_scan.py -q` green.

**Commit:** `fix(crash-recovery): scan rejects PID reuse via start-time-checked liveness`
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: correlate prefers the exact session_id

**Verifies:** crash-detection.AC4.3, crash-detection.AC4.4 (session_id half)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py` (`correlate`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_correlate.py` (unit)

**Implementation:**
At the top of `correlate()`, before the `--resume` argv branch: if `liveness.session_id` is set, matches `_UUID_RE`, and `project_dir` is not `None` and `<session_id>.jsonl` exists in it → return `DIRECT_MATCH(uuid=session_id)`. Then fall through to the existing `--resume` and mtime-window logic for markers without a usable `session_id` (back-compat). Precedence: `session_id` → `--resume <uuid>` → mtime window.

**Testing (test_correlate.py):**
- AC4.3: a `Liveness` with `session_id=<uuid>` and `<uuid>.jsonl` present in the cwd's project dir → `DIRECT_MATCH`, `result.uuid == <uuid>` (even if argv lacks `--resume`).
- AC4.4: a `Liveness` with `session_id=None` (legacy) → behaviour unchanged (resume/window path); a `session_id` whose JSONL is missing → falls through (not a false direct match).

**Verification:** `uv run pytest .../tests/test_correlate.py -q` green; full `uv run pytest` green (AC9.1); `bats tests/test_claude_wrapper_liveness.bats` green (AC9.2).

**Commit:** `feat(crash-recovery): correlate prefers exact session_id match`
<!-- END_TASK_4 -->

<!-- END_SUBCOMPONENT_B -->

## Phase 2 done when

- Wrapper writes `session_id` (when determinable) + `start_time` for fresh and resumed sessions; written `start_time` matches the comm-safe `/proc` parse (AC4.1, AC4.2 write side).
- `pid_alive_checked` is True on matching start_time, False on mismatch, falls back to bare liveness when `start_time` absent (AC4.2, AC4.4).
- scan rejects recycled PIDs (AC4.2 integration).
- correlate direct-matches on `session_id`, falls through for legacy markers (AC4.3, AC4.4).
- Clean/abnormal exit cleanup unchanged (AC4.5); full pytest + bats green (AC9).
