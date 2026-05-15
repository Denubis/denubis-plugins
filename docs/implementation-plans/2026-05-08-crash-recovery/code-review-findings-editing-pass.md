# Code Review Findings — editing-pass

Reviewed commit: `03c6526 docs(crash-recovery): apply critical-peer-review findings to plan`
Branch: `crash-recovery`
Scope: light structural sweep of the 12-fix editing pass across 11 files.

## Status: CHANGES REQUIRED

**Critical: 0 | Important: 0 | Minor: 2**

## Verification

No executable code was changed in this commit (documentation-only editing pass). Verification step is N/A; the per-plugin pytest invocation and bats tests apply at implementation time, not at plan-document stage.

## Plan Alignment

Checked against the 14 fix decisions in RESUME.md:

- Task #3 (H1 — boot_id_current wiring): ✓ phase_04.md now shows `current_bid = current_boot_id()` cached once at walk start, with `boot_id_current=(liveness.boot_id == current_bid)` at every SessionFact construction site including the AMBIGUOUS branch.
- Task #4 (H2 — non-Linux fail-fast): ✓ phase_04.md scan CLI has `sys.platform != "linux"` guard exiting code 2; phase_08.md CHANGELOG Compatibility section updated; "non-Linux classifies as boot-mismatched" claim retired.
- Task #5 (H3 — wrapper rm-logic placement): ✓ Block B moved to "immediately BEFORE `exit $EXIT_CODE` at line 121"; "Why insert at line 121" paragraph added; known-limitation note about bats fixture not exercising transcript-archive path added.
- Task #6 (H4 — DR-rot sweep): ✓ bats test names "DR3 — ..." and "DR2 — ..." renamed to plain descriptions. Phase 7 "DR3 in Phase 6" citation replaced with plain-language description. Phase 8 Done-When DR-label list replaced with AC-label list. Remaining DR references in phase files (DR8 in phase_08 comments, DR7 in uat-requirements, DR1/DR9 in phase_02/phase_04) are legitimate citations of actual design plan DRs (confirmed against `grep -n "^### DR" docs/design-plans/2026-05-08-crash-recovery.md`).
- Task #7 (H5 — unmatched reframe): ✓ "defensive fallback" language replaced throughout phase_02; "Something fucky — let's go look" render message added to phase_05; [manual review] tag added to phase_07 triage skill; test renamed to `test_unmatched_route_returns_borderline_unmatched`; `test_rules_table_partition_documents_unmatched_cases` added.
- Task #8 (M1 — network-FS refuse): ✓ `assert_local_filesystem()` function fully specified in phase_03 with implementation pseudocode, refused fstype list, and three tests. Phase_04 scan CLI calls it after the platform guard. Phase_08 Compatibility section updated.
- Task #9 (M3 — FK cascade): ✓ `FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE` added to `CLASSIFICATION_HISTORY_DDL` in phase_01. `test_prune_cascades_classification_history_deletion` added to phase_06.
- Task #10 (M6 — concurrent-scan test): ✓ scan_runs count assertion changed to `== 2` with explanatory prose that documents both scans complete their own transaction. "1 or 2" narrative removed.
- Task #11 (M4 — testpaths reversal): ✓ Step 2 (widening) deleted from Task 3 in phase_01. Steps 3–6 renumbered to 2–5. Per-plugin convention section added at top of phase_01. Design plan Phase 1 Done When updated. test-requirements.md "How to run the tests" section added. Phase_08 CHANGELOG entry no longer mentions widened testpaths. Root pyproject.toml confirmed unchanged (`testpaths = ["tests"]`).
- Task #12 (M2 — $* rationale): ✓ "matches Phase 3's _extract_resume_uuid expectation" replaced with "Either $* or $@ works inside double-quoted printf %s; $* is chosen for explicit single-string semantics."
- Task #13 (M5 — DR2 authorised widening citation): ✓ No remaining reference to "DR2 authorised widening" in any active phase file.
- Task #14 (L1–L5): ✓ L1 (Phase 7 DR3 in Phase 6) — removed. L2 (Phase 4 import block) — extended imports added. L3 (Phase 8 Done-When DR labels) — replaced with AC labels. L4 (commit hash 8c10b95) — stripped from phase_01.md codebase-verified line; hash does not exist in worktree (`git cat-file -t 8c10b95` → error), so strip was correct. L5 — no-op as expected.

## Falsification Anchors (RESUME.md "Things to watch for")

All nine anchors verified:

1. **`unmatched` render message + triage manual-review tag** — phase_05.md has `"Something fucky — let's go look"` render message; phase_07.md has `[manual review]` tag surfacing `unmatched` entries first. PASS.
2. **`boot_id_current` comparison site visible** — phase_04.md shows `current_bid = current_boot_id()` at walk start and `boot_id_current=(liveness.boot_id == current_bid)` at every SessionFact construction site. PASS.
3. **No bats test / README sentence starts with `"DR<n> —"` except valid design-plan DRs** — verified: remaining DR references in active phase files are DR1, DR7, DR8, DR9, all of which correspond to real `### DR` sections in the design plan. PASS.
4. **Root `pyproject.toml` testpaths unchanged** — `/home/brian/people/Brian/brian-ed3d-plugins/pyproject.toml` reads `testpaths = ["tests"]`. PASS.
5. **`classification_history` FK with `ON DELETE CASCADE`** — phase_01.md `CLASSIFICATION_HISTORY_DDL` at line 342 contains the FK. PASS.
6. **Phase 4 concurrent-scan test asserts `== 2` rows** — `scan_runs row count is exactly 2` assertion confirmed in diff. PASS.
7. **No `current_boot_id()` returning `"unknown"` survives** — zero matches for `current_boot_id.*unknown` in active phase files. Wrapper-side `boot_id=unknown` fallback is correctly preserved in phase_08. PASS.
8. **`crash-recovery scan` has `sys.platform == "linux"` guard** — phase_04.md scan CLI pseudocode confirmed at the entry point. PASS.
9. **`CR_RUN_DIR`/`$HOME` network-FS check** — `assert_local_filesystem()` specified in phase_03.md; called from scan CLI in phase_04.md immediately after platform guard. PASS.

## Issues

### Minor (count: 2)

**Minor-1: test-requirements.md line 38 references stale step number**

- **Issue:** The AC1.3 entry says "Phase 1 Task 3 Step 5 inline verification (asserts version equality across plugin.json and marketplace.json)." After the editing pass removed Step 2 (testpaths widening) from Task 3 and renumbered, the version-sync verification is now **Step 4**, not Step 5. Step 5 is now the commit step.
- **Location:** `docs/implementation-plans/2026-05-08-crash-recovery/test-requirements.md:38`
- **Fix:** Change "Phase 1 Task 3 Step 5" to "Phase 1 Task 3 Step 4" at that line.

**Minor-2: test-requirements.md line 105 references stale test name**

- **Issue:** AC3.3's test name list includes `test_defensive_fallback_returns_borderline_unmatched`. Task #7 (H5) renamed this test to `test_unmatched_route_returns_borderline_unmatched` in phase_02.md, but test-requirements.md was not updated to match. The AC3.3 entry also uses the old framing ("asserts non-empty reason even when no rule matches") rather than the new framing ("deliberate review-queue route").
- **Location:** `docs/implementation-plans/2026-05-08-crash-recovery/test-requirements.md:105`
- **Fix:** Replace `test_defensive_fallback_returns_borderline_unmatched` with `test_unmatched_route_returns_borderline_unmatched`. Update the parenthetical to match the reframing: "asserts non-empty reason for the deliberate review-queue route (AC3.3 guard)".

## AC-to-Test Mapping for New Tests

The seven new tests added by the editing pass are regression guards rather than new AC obligations. The question raised in the review brief is whether test-requirements.md needs updates for them. Assessment:

- `test_prune_cascades_classification_history_deletion` — guard for the new FK CASCADE. No existing AC covers FK cascade behaviour specifically; this is an implementation invariant. No test-requirements update needed.
- `test_unmatched_route_returns_borderline_unmatched` — replaces the renamed old test. Already listed in AC3.3; update needed (Minor-2 above).
- `test_rules_table_partition_documents_unmatched_cases` — documents the `unmatched` input space. No existing AC directly maps to "partition exhaustiveness"; it is a sub-property of AC3.1 (every rule classifies its fixture). No additional entry needed.
- `test_scan_cli_refuses_to_run_on_non_linux` and `test_scan_cli_refuses_when_run_dir_is_on_network_fs` — guard for the new platform guard and network-FS guard. No AC is defined for these; they are implementation guards for design decisions (non-Linux fail-fast = H2 resolution; network-FS = M1 resolution). No test-requirements entry needed; the tests are self-documenting.
- `test_unmatched_reason_emits_review_queue_message` — render behaviour guard. No existing AC covers the specific text of the `unmatched` render message. No test-requirements entry needed.
- `test_assert_local_filesystem_{accepts_tmp_path,refuses_simulated_nfs,silent_when_fstype_undetectable}` — unit tests for the new `assert_local_filesystem()` helper. No AC covers network-FS detection specifically. No test-requirements entry needed.

## Phase 8 Narrative Coherence

Block A description, bats-test list, Done-When count, Compatibility section, and README troubleshooting are all internally consistent after the editing pass:

- Block B insertion point changed from "after line 90" to "before line 121"; the "Why" paragraph explains the transcript-archive `read -r` motivation.
- Known-limitation note (bats fixture never exercises the transcript-archive path) is present and scoped to "Accepted gap for v1.0.0."
- Compatibility section correctly describes wrapper as cross-platform with `boot_id=unknown` fallback; scan as Linux-only; network-FS check as scan-side only.
- Done-When bats count = 10; the 10 `@test` blocks in the phase confirm this. The renamed tests (dropping DR2/DR3 prefixes) are reflected in the Done-When narrative.
- Phase 8 End section correctly says "Phase 7 prune-prompt clarity" rather than "Phase 7 DR2."

## Decision: APPROVED — FIX MINOR FINDINGS BEFORE EXECUTION HANDOFF

Two stale cross-references in `test-requirements.md`. Both are minor: a wrong step number (Minor-1) and a stale test name (Minor-2). Neither affects the executable plan — they only create confusion for a test-analyst reading test-requirements.md during execution. Fix before handing off to `executing-an-implementation-plan`.
