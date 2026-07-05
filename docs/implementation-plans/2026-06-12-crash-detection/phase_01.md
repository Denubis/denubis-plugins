# Post-mortem crash detection — Phase 1: Stage-1 cwd forward-scan + dedup-safe scan

**Goal:** Replace the line-1-only `cwd` read with a bounded forward scan (shared by scan + correlate), and make the scan dedup-safe so two `.live` files resolving to one UUID cannot crash `triage`.

**Architecture:** A single pure helper in `jsonl.py` returns the first JSONL record carrying a given field, scanning forward past snapshot/sidecar records. `scan.py` and `correlate.py` consume it for `cwd` and `timestamp`. `scan._walk_sessions` deduplicates facts by UUID before the write loop with deterministic precedence.

**Tech Stack:** Python 3.14+ stdlib (json, pathlib), pytest.

**Scope:** Phase 1 of 5 from `docs/design-plans/2026-06-12-crash-detection.md`.

**Codebase verified:** 2026-06-12 (read at commit 03b97f2; test conventions confirmed via codebase-investigator).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

### crash-detection.AC1: Crash victims surface as hard_crash
- **crash-detection.AC1.1 Success:** A `.live` that is present, PID-dead, boot-current, with a dead-pid tail kind classifies as `hard_crash` (end-to-end, including a snapshot-prefixed transcript — Task 6).

### crash-detection.AC2: Forward cwd read repairs correlation and the missing_cwd mislabel
- **crash-detection.AC2.1 Success:** A JSONL whose `cwd` is on a later line (line 1 a snapshot record) yields its real cwd, not `""`, and is not classified `irrecoverable/missing_cwd`.
- **crash-detection.AC2.2 Success:** A `.live` whose session's cwd is on a later line correlates (DIRECT or MTIME), not `no_match`.
- **crash-detection.AC2.3 Edge:** A JSONL with no `cwd` anywhere in the scan window still classifies `irrecoverable/missing_cwd` (genuine case preserved).

### crash-detection.AC3: Dedup-safe scan
- **crash-detection.AC3.1 Success:** A scan where two `.live` files resolve to the same UUID completes without `IntegrityError` and writes one `sessions` row.
- **crash-detection.AC3.2 Success:** Deterministic precedence — when one UUID is both a direct-match and an ambiguous candidate, the direct-match fact wins.

---

## Context for the implementer

- **Run the suite** from the worktree root: `uv run pytest` (179 tests must stay green; add new ones). Single module: `uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py`.
- **Root cause being fixed:** modern transcripts open with a `{"type":"snapshot",...}` record carrying no `cwd`; 957/1301 real transcripts put `cwd` on a *later* line. `scan._first_entry_cwd` and `correlate._cwd_matches_any_jsonl_in`/`_jsonl_first_entry_ts_meets_threshold` read only line 1, so they fail → 1013 false `missing_cwd` and 33/36 `.live` `no_match`.
- **Fixture builder:** `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py`. `make_full_fixture(tmp_path, [FixtureSession(...)])` returns `(db_dir, run_dir, projects_root)`; today it writes each JSONL with `cwd`+`timestamp` on the FIRST line. You will add a way to push `cwd` onto a later line behind a snapshot record.
- **NEVER** point tests at the real `~/.claude/run` or `~/.claude/projects`; always use `tmp_path` / the fixture builder.

---

<!-- START_SUBCOMPONENT_A (tasks 1-4) -->

<!-- START_TASK_1 -->
### Task 1: Add a snapshot-prefixed JSONL option to the fixture builder

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py`

**Implementation:**
Add a `cwd_on_first_line: bool = True` (or `snapshot_prefix_lines: int = 0`) parameter to the JSONL-writing path used by `make_full_fixture` and add a standalone builder `make_snapshot_prefixed_jsonl(path, cwd, first_ts, *, tail_kind)` that writes, in order:
1. one snapshot/bookkeeping record with NO `cwd` and NO `timestamp` — shape `{"type": "snapshot", "messageId": "...", "snapshot": {...}, "isSnapshotUpdate": false}` (mirror the real shape: top-level keys `type,messageId,snapshot,isSnapshotUpdate`, `type` value `snapshot` so it is filtered by `_REAL_TYPES`);
2. the normal first real record carrying `cwd` and `timestamp`;
3. the tail entries for `tail_kind`.

Keep the existing default (`cwd` on line 1) so current tests are unaffected. This builder is the fixture for AC2.1/AC2.2.

**Consumer:** Tasks 2-4 tests use this builder; `make_full_fixture` gains the option so `FixtureSession`-driven scan tests (Task 3) can request a later-line cwd.

**Testing:** No test for the fixture builder itself (test infrastructure). Verified by its consumers in Tasks 2-4.

**Verification:** `uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/ -q` still green (no behaviour change yet).

**Commit:** `test(crash-recovery): snapshot-prefixed JSONL fixture builder`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Bounded forward-scan helper in jsonl.py

**Verifies:** crash-detection.AC2.1, crash-detection.AC2.3 (helper level)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/jsonl.py`
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_jsonl_tail.py` (unit)

**Implementation:**
Add a module constant and a pure helper:

```python
# Bound the forward scan: a real session's first cwd/timestamp record sits within
# the first few lines (after the snapshot prefix). 50 is generous headroom; it
# caps cost on pathological files and keeps the read memory-bounded.
_FIRST_FIELD_SCAN_LIMIT = 50


def first_record_field(path: Path, field: str, limit: int = _FIRST_FIELD_SCAN_LIMIT):
    """Return the value of ``field`` from the first JSONL record that carries it
    as a non-empty value, scanning forward up to ``limit`` parseable records.

    Best-effort: returns ``None`` on missing file, unreadable file, or no record
    carrying the field within the window. Never raises. Blank lines and lines
    that fail to JSON-decode are skipped (they do not consume the record budget
    is a design choice — count only parseable dict records toward ``limit``).
    """
```

Behaviour:
- Open with `encoding="utf-8", errors="replace"`; on `OSError` return `None`.
- Iterate lines; skip blank/unparseable; for each parseable dict, if `d.get(field)` is a non-empty `str`, return it; count parseable dict records and stop after `limit`.
- For `field="cwd"` and `field="timestamp"` the value is a `str`; the non-empty-str check is correct for both.

(Do **not** delete `parse_tail`; this helper is additive.)

**Testing (test_jsonl_tail.py):**
- AC2.1: a JSONL built by `make_snapshot_prefixed_jsonl` (snapshot line 1, cwd on line 2) → `first_record_field(path, "cwd")` returns the real cwd.
- AC2.3: a JSONL whose records never carry `cwd` (only snapshot/bookkeeping) → returns `None`.
- timestamp variant: snapshot-prefixed JSONL → `first_record_field(path, "timestamp")` returns the first real timestamp string.
- bound: a JSONL with cwd only beyond `limit` records → returns `None` (document the bound).

**Verification:** `uv run pytest .../tests/test_jsonl_tail.py -q` green.

**Commit:** `feat(crash-recovery): forward-scan helper for first cwd/timestamp record`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: scan._first_entry_cwd uses the forward scan

**Verifies:** crash-detection.AC2.1, crash-detection.AC2.3

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py` (`_first_entry_cwd`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py` (integration)

**Implementation:**
Replace the line-1-only body of `_first_entry_cwd` with `return first_record_field(jsonl_path, "cwd") or ""` (import `first_record_field` from `crash_recovery.jsonl`). Preserve the existing contract: returns `""` when no cwd is found (the DB column is NOT NULL but accepts `""`, and `_classify_fact` maps empty cwd → `irrecoverable/missing_cwd`).

**Testing (test_scan.py):**
- AC2.1: `make_full_fixture` with a session whose JSONL has cwd on a later line (snapshot prefix) → after `run_scan`, that session's row is NOT `irrecoverable/missing_cwd`; its `cwd` column equals the real cwd.
- AC2.3: a JSONL-only session whose JSONL never carries cwd → still `irrecoverable/missing_cwd` (genuine case preserved).

**Verification:** `uv run pytest .../tests/test_scan.py -q` green.

**Commit:** `fix(crash-recovery): scan reads cwd via forward scan, not line 1`
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: correlate uses the forward scan for cwd and timestamp

**Verifies:** crash-detection.AC2.2

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py` (`_cwd_matches_any_jsonl_in`, `_jsonl_first_entry_ts_meets_threshold`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_correlate.py` (unit)

**Implementation:**
- `_cwd_matches_any_jsonl_in(child, cwd)`: for each `*.jsonl` in `child`, compare `first_record_field(jsonl, "cwd") == cwd` (was: read only first line). Keep full-scan-of-all-jsonls semantics (the lossy-encoding rationale in the docstring still holds).
- `_jsonl_first_entry_ts_meets_threshold(jsonl, threshold)`: derive the timestamp via `first_record_field(jsonl, "timestamp")` then apply the existing `datetime.fromisoformat(raw.replace("Z","+00:00"))` + `>= threshold - _CLOCK_SKEW_GRACE_SECONDS` logic. Preserve the conservative `False`-on-any-error behaviour.

**Testing (test_correlate.py):**
- AC2.2 (project-dir lookup): `_project_dir_for_cwd(projects_root, cwd)` finds the dir when the matching JSONL has cwd on a later line (previously returned `None`).
- AC2.2 (correlation end-to-end): a `Liveness` (cwd on a later-line JSONL, `--resume <uuid>` argv, that `<uuid>.jsonl` present) → `correlate(...)` returns `DIRECT_MATCH`, not `NO_MATCH`. And a fresh-style marker (no `--resume`) whose single in-window JSONL has a later-line timestamp → `MTIME_MATCH`.

**Verification:** `uv run pytest .../tests/test_correlate.py -q` green.

**Commit:** `fix(crash-recovery): correlate reads cwd/timestamp via forward scan`
<!-- END_TASK_4 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (task 5) -->

<!-- START_TASK_5 -->
### Task 5: Dedup-safe scan

**Verifies:** crash-detection.AC3.1, crash-detection.AC3.2

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py` (`_walk_sessions`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py` (integration)

**Implementation:**
Today `_walk_sessions` appends one fact per DIRECT/MTIME match and one fact per AMBIGUOUS *candidate*, calling `seen.add(...)` but never checking `seen` within the liveness loop. Once correlation succeeds, two same-cwd `.live` files can yield two facts for one UUID (e.g. a direct-match for UUID X from marker A and an ambiguous-candidate for X from marker B) → `run_scan`'s per-fact `_append_history(uuid, scan_id)` hits the `(uuid, scan_id)` UNIQUE constraint and crashes.

Make the liveness walk emit at most one fact per UUID, deterministically:
- Assign each candidate fact a precedence rank from its correlation kind: `DIRECT_MATCH/session_id → 0`, `MTIME_MATCH → 1`, `AMBIGUOUS candidate → 2`.
- Keep a `dict[str, tuple[int, str, SessionFact]]` keyed by UUID holding `(rank, liveness_path_str, fact)`. On collision, keep the lower `rank`; tie-break on the lexicographically smaller `liveness_path_str` (markers are already iterated in sorted path order, so first-wins within a rank is deterministic — but compare explicitly so order-independence holds).
- After the liveness loop, the deduped facts are `dict.values()`'s `fact`s; `seen` is their UUID set; then run the existing `_walk_jsonl_only(ctx, seen)`.

Keep the change confined to `_walk_sessions`; `run_scan`/`scan_db` are unchanged. Preserve existing determinism (sorted iteration; the `live_pids` set in `run_scan` still derives from the deduped facts).

**Testing (test_scan.py):**
- AC3.1: build a fixture (you may need to extend `make_full_fixture` to write two `.live` files in one cwd, or write the two markers directly into `run_dir`) where two markers resolve to the same UUID — at least one via an AMBIGUOUS correlation. `run_scan` completes without `sqlite3.IntegrityError`; the DB has exactly one `sessions` row and one `classification_history` row for that UUID in the scan.
- AC3.2: construct a case where UUID X is a DIRECT_MATCH from marker A and an AMBIGUOUS candidate from marker B → the persisted row reflects the direct-match fact (e.g. its `classification`/`liveness` is the direct one, not `borderline/ambiguous_match`).

**Verification:** `uv run pytest .../tests/test_scan.py -q` green; full `uv run pytest` still green (AC9.1).

**Commit:** `fix(crash-recovery): dedup scan facts by uuid to prevent history UNIQUE crash`
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_TASK_6 -->
### Task 6: End-to-end — snapshot-prefixed crash victim surfaces as hard_crash

**Verifies:** crash-detection.AC1.1

**Files:**
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py` (integration)

**Implementation:**
No production code — this is the capstone integration test proving the Phase 1 chain (`first_record_field` → `_first_entry_cwd` / `correlate` → `classify`) actually surfaces a crash victim. Use `make_full_fixture` with a single `FixtureSession(has_liveness=True, pid_alive=False, boot_id_current=True, tail_kind=TailKind.TOOL_USE_NO_RESULT, ...)` whose JSONL is **snapshot-prefixed** (cwd on a later line, via the Task 1 option). The fixture's marker carries `--resume <uuid>` argv (the existing DIRECT_MATCH path), so correlation succeeds via the Task 4 forward-cwd fix.

**Testing:** after `run_scan`, that session's row classifies `hard_crash` (reason `liveness_dead_pid_tool_use_no_result`) — proving a snapshot-prefixed transcript no longer buries the victim. Contrast the pre-fix behaviour (would have been `irrecoverable/missing_cwd` or `unknown_tail_kind`).

**Verification:** `uv run pytest .../tests/test_scan.py -q` green.

**Commit:** `test(crash-recovery): end-to-end snapshot-prefixed crash victim → hard_crash`
<!-- END_TASK_6 -->

## Phase 1 done when

- `first_record_field` covered (AC2.1/AC2.3 helper level).
- Later-line-cwd sessions classify correctly, not `missing_cwd` (AC2.1); genuine no-cwd still `missing_cwd` (AC2.3).
- Later-line-cwd `.live` files correlate, not `no_match` (AC2.2).
- Two markers → one UUID scan completes without `IntegrityError`, one row, direct-match precedence honoured (AC3.1, AC3.2).
- A snapshot-prefixed crash victim surfaces end-to-end as `hard_crash` (AC1.1, Task 6).
- Full `uv run pytest` green (AC9.1).
