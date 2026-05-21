# Code Review Findings — plan-validation

## Status: APPROVED WITH CHANGES REQUIRED

**Critical: 0 | Important: 4 | Minor: 3**

---

## Coverage

All 34 acceptance criteria (AC1.1 through AC8.3) are covered across the eight phase files. The mapping is complete:

| AC | Phase(s) | Mechanism |
|---|---|---|
| AC1.1 | P7 Task 3 (bats) | marketplace.json listing test |
| AC1.2 | P7 Task 3 (bats) | proxy: marketplace.json listing |
| AC1.3 | P1 Task 3 Step 5 | version-sync verification script |
| AC1.4 | P1 Task 6 | `test_plugin_json_is_valid` |
| AC2.1 | P1 (seed) + P5 + P6 | EXPECTED_SUBCOMMANDS grown incrementally |
| AC2.2 | P5, P6 bats smoke | each subcommand accepts `--help` |
| AC2.3 | P1 Task 5/6 | init creates schema |
| AC2.4 | P1 Task 6 | idempotency via schema_hash |
| AC2.5 | P1 Task 6 | `test_unknown_subcommand_exits_nonzero` |
| AC3.1 | P2 Task 5 | parametrised test over RULES |
| AC3.2 | P5 Task 6 snapshots + P7 bats | byte-identical render |
| AC3.3 | P2 Task 5 | reason non-empty assertion per rule |
| AC3.4 | P2 Tasks 2, 5 | malformed_tail fixture |
| AC3.5 | P2 Tasks 2, 5 | empty_file fixture |
| AC3.6 | P4 Task 5 | stale classifier_version re-classification test |
| AC4.1 | P6 Task 2 | note set + regenerate test |
| AC4.2 | P6 Task 2 | note overwrite test |
| AC4.3 | P6 Task 2 | note clear test |
| AC4.4 | P5 Task 6 | `test_render_overwrites_user_edits` |
| AC4.5 | P6 Task 2 | UnknownSessionError + no-insert assertion |
| AC5.1 | P3 (parser), P8 Task 2 (writer bats) | four-key parse + bats four-key write |
| AC5.2 | P8 Task 2 (bats) | exit 0 and exit 130 remove file |
| AC5.3 | P8 Task 2 (bats) | kill -9 wrapper; file persists |
| AC5.4 | P3 (enumerate), P8 Task 2 (bats) | concurrent PID-distinct files |
| AC5.5 | P8 Task 2 (bats) | exit 137, 139, 1 preserve file |
| AC5.6 | P3 (boot_id read), P4 Task 5, P8 Task 2 (bats write), P8 Task 5 (UAT) | boot_id mismatch end-to-end |
| AC6.1 | P3 (correlate), P4 (wiring) | correlation + classify chain |
| AC6.2 | P4 Task 5 | `test_scan_classifies_live_pid_as_live` |
| AC6.3 | P4 Task 5 | `test_scan_classifies_ambiguous_correlation_as_borderline_ambiguous_match` |
| AC6.4 | P8 Task 5 | manual UAT runbook only |
| AC7.1 | P5 Task 6 | `test_regenerate_preserves_concluded_rows` |
| AC7.2 | P6 Task 5 | dry-run read-only test |
| AC7.3 | P6 Task 5 + P7 bats | no-confirm refuses |
| AC7.4 | P6 Task 5 | --confirm deletes matching rows |
| AC7.5 | P6 Task 5 | note acts as preservation marker |
| AC7.6 | P6 Task 5 | extant JSONL preservation |
| AC7.7 | P6 Task 5 | stale classifier_version excluded |
| AC8.1 | P7 Task 2 | README documents sibling dependency |
| AC8.2 | P8 Task 4 | version-sync verification script |
| AC8.3 | P8 Task 4 | CHANGELOG entry-count check |

No AC is orphaned (present in design, absent from implementation). No AC mapping errors remain unacknowledged — the two known design-plan "Covers ACs" errors (Phase 4 listing AC4.* and Phase 6 listing AC2.3) are both explicitly acknowledged and correctly re-mapped in the respective phase files.

---

## Plan Alignment

All architecture decisions from the design are followed:

- SQLite source of truth, markdown as regenerated view: implemented in P1 (schema) + P5 (render).
- Deterministic Python rules, no LLM judgement: RULES tuple in P2, classify() pure function.
- No auto-prune: P6 prune module requires --dry-run + --confirm.
- boot_id-aware liveness: P3 current_boot_id(), P4 LivenessState wiring, P8 wrapper write.
- Plugin directory uses `denubis-crash-recovery` prefix; CLI binary keeps bare `crash-recovery` form: consistent across all phases.
- `uv run --project <abs-path>` invocation form: P7 skill body uses it.
- Testpaths widening: P1 Task 3 Step 2.
- Sibling-plugin version coordination in same PR: P8 Tasks 3 and 4.

---

## Issues

### Important (count: 4)

**I1 — `SessionFact.ambiguity_candidates` field missing from dataclass definition**

- **Location:** Phase 4, Task 1, `SessionFact` field list (the `_walk_sessions` description at lines 75-84 and `_classify_fact` at lines 86-108)
- **Issue:** The `SessionFact` frozen dataclass is described with fields `uuid`, `project_path`, `cwd`, `jsonl_path`, `jsonl_mtime`, `tail_summary`, `liveness`, `pid_alive_value`, `boot_id_current`. The field `ambiguity_candidates: tuple[str, ...]` is referenced in both the walk strategy and `_classify_fact` but never included in the explicit field list. An implementer following the field list to define the dataclass will produce a `SessionFact` that cannot be passed to `_classify_fact` without a `NameError` or `AttributeError`.
- **Fix:** Add `ambiguity_candidates: tuple[str, ...] = ()` to the `SessionFact` frozen dataclass field list in Phase 4 Task 1.

**I2 — `run_scan` skeleton does not show `live_pids` assembly; `_write_scan_run` will receive no list**

- **Location:** Phase 4, Task 1 `run_scan` skeleton (line 119) and Task 2 `_write_scan_run` spec (lines 194-203)
- **Issue:** `_write_scan_run` requires a `live_pids` argument (a sorted JSON array of PIDs that are alive during this scan), but the `run_scan` orchestrator skeleton calls `_write_scan_run(conn, ctx, sessions_scanned=len(facts))` with no `live_pids` argument. The test `test_scan_writes_scan_runs_with_live_pids` in Task 5 asserts the column is populated correctly. The implementer has no specification for when or how the live_pids list is assembled — it is not produced by `_walk_sessions` explicitly, nor collected in any other intermediate step shown in the skeleton.
- **Fix:** Add a `live_pids` assembly step to the `run_scan` skeleton: after `facts = _walk_sessions(ctx)`, collect `sorted({fact.liveness.pid for fact in facts if fact.liveness is not None and fact.pid_alive_value is True})` and pass to `_write_scan_run`.

**I3 — `TailSummary` is frozen; Phase 4 describes "replacing" state_summary for ambiguous facts**

- **Location:** Phase 4, Task 1, line 108: "the `SessionFact.tail_summary.state_summary` is replaced upstream (in `_walk_sessions`) with a string like `"ambiguous match: <uuid1>, <uuid2>, …"`"
- **Issue:** `TailSummary` is a `frozen=True` dataclass (Phase 2 Task 1). A frozen dataclass cannot have a field replaced in place. The word "replaced" implies mutation which is impossible. The only correct approach is to construct the `TailSummary` with the candidate-list string at walk time (when building the ambiguous `SessionFact`). An implementer who reads this as "replace the field after construction" will hit a `FrozenInstanceError` at runtime.
- **Fix:** Rephrase Phase 4 Task 1 line 108 to: "When `AMBIGUOUS` correlation fires, construct the `SessionFact`'s `tail_summary` with `state_summary=f'ambiguous match: {', '.join(candidates)}'` from the start rather than using the JSONL parse result."

**I4 — Design's concurrency test ("Test for this with a fixture that races two scans") has no implementation**

- **Location:** Design plan Additional Considerations: "Two simultaneous `scan` invocations are a real risk … Test for this with a fixture that races two scans." No phase file includes a concurrent-scan race test.
- **Issue:** Phase 4 Task 5 includes `test_scan_atomic_on_simulated_failure` which tests transaction rollback via monkey-patching — this tests atomicity of a single scan's writes, not concurrent writers. SQLite WAL mode is configured but never concurrently exercised in the test suite. The design explicitly called for a racing-scan fixture.
- **Fix:** Add a test to Phase 4 Task 5 (or Phase 7 as a bats integration test): spawn two subprocesses each running `crash-recovery scan` against the same DB and fixture simultaneously; assert that after both complete, the DB row count equals the fixture's session count with no duplicates or constraint errors. This is a required design commitment, not optional.

---

### Minor (count: 3)

**M1 — "Phase 4 DR3" cited in Phase 5 architecture header does not exist in Phase 4**

- **Location:** Phase 5, Architecture header, line 5: "per the design's backward-compatibility consideration (resolved in Phase 4 DR3)"
- **Issue:** Phase 4 contains no section labelled "DR3" or "Decision Record 3". The resolution (derive `liveness_present` from `classification_reason` prefix rather than storing a boolean column) is correct and is implemented correctly via Phase 5's `LIVENESS_REASONS` / `NO_LIVENESS_REASONS` / `JSONL_ONLY_REASONS` constants. The label is phantom. The design plan's Additional Considerations states "Liveness presence/absence is recorded in `sessions` as a boolean flag" — this is the contradiction being resolved — but the resolution is undocumented in Phase 4.
- **Fix:** Either add a brief "DR: liveness_present column dropped; derived from classification_reason prefix" note to Phase 4's architecture block, or remove the "Phase 4 DR3" label from Phase 5 and replace with "resolved by deriving from classification_reason prefix (see Phase 5 LIVENESS_REASONS / NO_LIVENESS_REASONS / JSONL_ONLY_REASONS)".

**M2 — CHANGELOG Task 3 ordering description is misleading**

- **Location:** Phase 8, Task 3, Step 3: "prepend the following block to `CHANGELOG.md` (above the `[denubis-crash-recovery] 1.0.0` entry Task 4 will add)"
- **Issue:** At the time Task 3 runs, Task 4 has not yet run, so there is no `[denubis-crash-recovery] 1.0.0` entry to be "above". The instruction is forward-referencing a commit that hasn't happened. The final order is correct (crash-recovery 1.0.0 on top, plan-and-execute 2.32.2 below) because Task 4 commits after Task 3 and prepends. But the instruction as written is confusing to an implementer who reads it literally.
- **Fix:** Reword to: "prepend the following block to `CHANGELOG.md`. Task 4 will prepend the `denubis-crash-recovery 1.0.0` entry above this, so the final order will be crash-recovery first."

**M3 — `test_reason_prefix_partition_is_exhaustive` spec omits `"unmatched"` (defensive fallback reason)**

- **Location:** Phase 5, Task 6: "`test_reason_prefix_partition_is_exhaustive` — collect every `reason` string from Phase 2's `RULES` plus `'ambiguous_match'`"
- **Issue:** The defensive fallback in `classify()` (Phase 2 Task 4) emits reason `"unmatched"` and is included in Phase 5's `JSONL_ONLY_REASONS`. The exhaustiveness test as specified does not include `"unmatched"` in its input set, so the test would pass even if `"unmatched"` were removed from `JSONL_ONLY_REASONS`. The test is weaker than intended.
- **Fix:** Add `"unmatched"` to the input set in the test spec: "collect every `reason` string from Phase 2's `RULES` plus `'ambiguous_match'` plus `'unmatched'` (the defensive fallback from `classify()`'s final return)."

---

## Specific Consistency Check Results

**Python 3.12 floor (Phase 1 DR2):** `requires-python = ">=3.12"` is correctly set in Phase 1's `pyproject.toml`. No later phase introduces Python 3.13+ syntax (`t-strings`, `match`/`case` expressions, or 3.14-only features). Check passes.

**Phase 2 `RULES` + Phase 4 `ambiguous_match` override documentation:** Phase 4 Task 1 explicitly documents the `ambiguous_match` override in `_classify_fact` with a code comment citing AC6.3. Phase 5 Task 1 includes `"ambiguous_match"` in `JSONL_ONLY_REASONS`. Both cross-references are present. Check passes.

**Phase 4 DR3 resolution / `liveness_present` boolean column:** As documented in M1, the resolution is correct in Phase 5's implementation but the "Phase 4 DR3" citation in Phase 5 is a phantom label. Functionally correct; documentation gap only.

**Phase 5 `LIVENESS_REASONS` / `NO_LIVENESS_REASONS` / `JSONL_ONLY_REASONS` partition exhaustiveness:** Every reason emitted by Phase 2's 14 RULES appears in exactly one of the three sets. Phase 4's `ambiguous_match` override is in `JSONL_ONLY_REASONS`. The defensive fallback `"unmatched"` is in `JSONL_ONLY_REASONS`. The three sets are disjoint. Check passes (with the caveat in M3 that the test spec for the partition test is weaker than it should be).

**Phase 8 placeholder chain:** Phase 7 Task 2 uses `<PHASE-8-VERSION>` placeholder in README. Phase 8 Task 4 Step 4 replaces all occurrences of `<PHASE-8-VERSION>` with `2.32.2`. Phase 8 Task 3 sets denubis-plan-and-execute to version `2.32.2`. The chain is consistent. Check passes.

**Phase 3 `~/.claude/run/` contract + Phase 8 `mkdir -p`:** Phase 3's `list_liveness_files` explicitly tolerates a non-existent `run_dir` (returns immediately with no error). Phase 8's wrapper patch Block A includes `mkdir -p "$CR_RUN_DIR"` so the directory is created before the `.live` file write. The contract holds: Phase 3 is defensive; Phase 8 creates the directory on first wrapper startup. Check passes.

---

## Decision: APPROVED — CHANGES REQUIRED (Important issues must be addressed before execution)

The plan is structurally sound and all 34 ACs have verified coverage paths. The two-phase AC re-mapping corrections (Phase 4 and Phase 6) are correctly acknowledged and re-mapped. The architecture, file paths, module boundaries, and test strategy are consistent with the design.

Four issues require resolution before the plan is handed to an executor:

- **I1** (SessionFact.ambiguity_candidates missing from field list) is the most likely to cause a runtime failure mid-phase.
- **I2** (live_pids assembly not shown in run_scan skeleton) will cause the scan_runs.live_pids test to fail without additional implementer inference.
- **I3** (frozen TailSummary mutation description) will cause a FrozenInstanceError if read literally.
- **I4** (concurrent-scan test missing) is a design commitment not yet represented in any phase.

M1–M3 are documentation clarity issues that should be fixed but will not block the executor.

---

# Re-Review Cycle 2 — 2026-05-14

## Prior Findings Verification

**I1 — `SessionFact.ambiguity_candidates` field missing from dataclass definition**
VERIFIED. `ambiguity_candidates: tuple[str, ...] = ()` is present in the `SessionFact` field list at Phase 4 Task 1 (line 89 of the revised file). The field is in declaration order between `boot_id_current` and the end of the dataclass block.

**I2 — `run_scan` skeleton does not show `live_pids` assembly; `_write_scan_run` will receive no list**
VERIFIED. The `run_scan` skeleton now assembles `live_pids` as a sorted set comprehension after `facts = _walk_sessions(ctx)` and passes `live_pids=live_pids` to `_write_scan_run`. The `_write_scan_run` signature in Task 2 now reads `_write_scan_run(conn, ctx, sessions_scanned, live_pids)`. Both sides of the interface are consistent.

**I3 — `TailSummary` is frozen; Phase 4 describes "replacing" state_summary for ambiguous facts**
VERIFIED. The mutation language is gone. The text now explicitly states "TailSummary is frozen — no mutation possible; the field is set via the constructor." Pseudocode constructs a `synthetic_tail = TailSummary(kind=TailKind.UNKNOWN, last_ts=None, total_entries=0, state_summary=...)` at walk time. All referenced names (`TailKind.UNKNOWN`, `CorrelationKind.AMBIGUOUS`, `correlation.candidates`) are defined in Phases 2 and 3.

**I4 — Design's concurrency test has no implementation**
VERIFIED. `test_scan_two_concurrent_invocations_do_not_corrupt_db` is present in Phase 4 Task 5. The test spawns two `subprocess.Popen([sys.executable, "-m", "crash_recovery", "scan", ...])` invocations against the same DB simultaneously, waits for both, and asserts: both exit 0, `sessions` row count is exactly 3, scan_runs count is 1 or 2 (both valid outcomes), all rows have current `classifier_version`, all rows' `last_scanned` equals one of the two scan_run timestamps.

**M1 — "Phase 4 DR3" cited in Phase 5 architecture header does not exist in Phase 4**
VERIFIED. The "Phase 4 DR3" label is gone. The architecture header now reads: "resolves the design's backward-compatibility wording ('Liveness presence/absence is recorded in `sessions` as a boolean flag') by deriving the boolean from the reason prefix rather than adding a column. See `LIVENESS_REASONS` / `NO_LIVENESS_REASONS` / `JSONL_ONLY_REASONS` in Task 1." No phantom label remains.

**M2 — CHANGELOG Task 3 ordering description is misleading**
VERIFIED. The forward-reference wording is replaced. Step 3 now reads: "(Task 4, executed after this task, will prepend a `[denubis-crash-recovery] 1.0.0` entry above this one. The final order after both tasks complete will be: crash-recovery 1.0.0 first, plan-and-execute 2.32.2 below, then the prior top entry `[denubis-bibliography] 0.1.0`.)" The final-state ordering is stated explicitly.

**M3 — `test_reason_prefix_partition_is_exhaustive` omits `"unmatched"`**
VERIFIED. The test spec in Phase 5 Task 6 now reads: "collect every `reason` string from Phase 2's `RULES` plus `'ambiguous_match'` (Phase 4's override reason) plus `'unmatched'` (Phase 2's defensive fallback emitted when no row matches)." The explicit inclusion of `"unmatched"` closes the gap where removing it from `JSONL_ONLY_REASONS` would not fail the test.

## New Issues Introduced by Fixes

None. Verification of each fix:

- The I3 pseudocode references `TailKind.UNKNOWN` (defined Phase 2 Task 1), `CorrelationKind.AMBIGUOUS` (defined Phase 3 Task 3), and `correlation.candidates` (the `candidates: tuple[str, ...]` field of `CorrelationResult`, defined Phase 3 Task 3). All names are in scope for Phase 4's implementer.
- The I4 test uses `subprocess.Popen`, `sys.executable`, and `Popen.wait()` — all stdlib; no unverified external dependencies.
- The M2 re-wording does not introduce any instruction-ordering ambiguity; it is strictly clearer than the original.

## Overall Verdict: APPROVED

All seven prior findings are resolved. No new issues introduced. The plan is ready for execution handoff.
