# Test Requirements — denubis-crash-recovery

This file maps every Acceptance Criterion to its automated test. Human-judgement
ACs (UAT) live in `uat-requirements.md` instead.

The test-analyst agent uses this file during execution to validate that every
AC has a passing test by the time the relevant phase completes.

Test-file paths are abbreviated as `<TESTS>` = `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/`
and `<SRC>` = `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/`.

---

## Phase 1: Plugin scaffold and database schema

### crash-recovery.AC1.1 — `claude plugin install` exits 0
- **Test type:** AUTOMATED (smoke; nearest-automatable proxy)
- **Test file:** `tests/test_crash_recovery_smoke.bats` (Phase 7 Task 3)
- **Test name:** `@test "denubis-crash-recovery is listed in marketplace.json"`
- **Phase:** Phase 7
- **Status:** covered (proxy — true `claude plugin install` requires a live Claude Code instance; the marketplace-listing assertion is the closest automated check)

### crash-recovery.AC1.3 — plugin.json + marketplace.json version-sync, required fields present
- **Test type:** AUTOMATED (unit)
- **Test file:** `<TESTS>test_plugin_manifest.py`
- **Test name:** `test_plugin_json_is_valid` (asserts required fields); Phase 1 Task 3 Step 5 inline verification (asserts version equality across plugin.json and marketplace.json)
- **Phase:** Phase 1 Task 6
- **Status:** covered

### crash-recovery.AC1.4 — Malformed plugin.json exits non-zero with parseable error
- **Test type:** AUTOMATED (unit)
- **Test file:** `<TESTS>test_plugin_manifest.py`
- **Test name:** `test_plugin_json_is_valid` — asserts `json.load` parses; manifest well-formedness gate
- **Phase:** Phase 1 Task 6
- **Status:** covered (well-formedness-gate proxy; install-failure path is owned by Claude Code itself)

---

## Phase 2: JSONL tail parser and classification rule table

### crash-recovery.AC2.1 — `crash-recovery --help` lists every documented subcommand
- **Test type:** AUTOMATED (integration; cross-phase, incremental)
- **Test file:** `<TESTS>test_cli_help.py`
- **Test name:** `test_help_exits_zero` (Phase 1 seed); subcommand-list assertion driven by `EXPECTED_SUBCOMMANDS` constant grown in Phases 1, 4, 5, 6
- **Phases contributing:**
  - Phase 1 Task 6 — seeds `EXPECTED_SUBCOMMANDS = ["init"]`
  - Phase 4 Task 4 — appends `"scan"`
  - Phase 5 Task 4 — appends `"render"`
  - Phase 5 Task 5 — appends `"triage"`, `"regenerate"`
  - Phase 6 Task 2 — appends `"note"`
  - Phase 6 Task 3 — appends `"history"`
  - Phase 6 Task 5 — appends `"prune"`
  - Phase 6 Task 6 — appends `"list-live"`
- **Status:** covered (final assertion fires at end of Phase 6 with all 9 subcommands)

### crash-recovery.AC2.2 — Every subcommand accepts `--help`
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_cli_help.py`
- **Phases contributing:** Phases 1, 4, 5, 6 — `--help` parametrised over `EXPECTED_SUBCOMMANDS`
- **Status:** covered

### crash-recovery.AC2.3 — `crash-recovery init` creates DB with documented schema
- **Test type:** AUTOMATED (unit + integration)
- **Test file:** `<TESTS>test_init.py`
- **Test names:** `test_init_creates_documented_schema` (unit); `test_cli_init_writes_db_at_env_var_path` (integration via subprocess + env var)
- **Phase:** Phase 1 Task 6
- **Status:** covered

### crash-recovery.AC2.4 — Re-running `init` is idempotent (row-count + schema-hash)
- **Test type:** AUTOMATED (unit)
- **Test file:** `<TESTS>test_init.py`
- **Test name:** `test_init_is_idempotent`
- **Phase:** Phase 1 Task 6
- **Status:** covered

### crash-recovery.AC2.5 — Unknown subcommand exits non-zero with `--help` hint
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_init.py`
- **Test name:** `test_unknown_subcommand_exits_nonzero`
- **Phase:** Phase 1 Task 6
- **Status:** covered

### crash-recovery.AC3.1 — Every rule classifies its fixture
- **Test type:** AUTOMATED (unit; parametrised)
- **Test file:** `<TESTS>test_classify.py`
- **Test name:** `test_every_rule_classifies_its_fixture` (parametrised over `RULES`)
- **Phase:** Phase 2 Task 5
- **Status:** covered

### crash-recovery.AC3.3 — Each session row records non-empty `classification_reason`
- **Test type:** AUTOMATED (unit; parametrised)
- **Test file:** `<TESTS>test_classify.py`
- **Test names:** `test_every_rule_classifies_its_fixture` (asserts `.reason` matches per row); `test_defensive_fallback_returns_borderline_unmatched` (asserts non-empty reason even when no rule matches); `test_rules_have_unique_reasons`
- **Phase:** Phase 2 Task 5
- **Status:** covered

### crash-recovery.AC3.4 — Malformed JSONL → `borderline` / `malformed_tail`, no crash
- **Test type:** AUTOMATED (unit)
- **Test file:** `<TESTS>test_jsonl_tail.py` + `<TESTS>test_classify.py`
- **Test names:** `test_parse_tail_classifies_malformed_tail` (parser); `test_malformed_tail_maps_to_borderline_malformed_tail` (classifier)
- **Phase:** Phase 2 Tasks 2 and 5
- **Status:** covered

### crash-recovery.AC3.5 — Empty JSONL → `borderline` / `empty_file`
- **Test type:** AUTOMATED (unit)
- **Test file:** `<TESTS>test_jsonl_tail.py` + `<TESTS>test_classify.py`
- **Test names:** `test_parse_tail_classifies_empty_file_as_empty` (parser); `test_empty_jsonl_maps_to_borderline_empty_file` (classifier)
- **Phase:** Phase 2 Tasks 2 and 5
- **Status:** covered

---

## Phase 3: Liveness file handling, boot awareness, UUID correlation

### crash-recovery.AC5.1 — Liveness file has cwd/started/argv/boot_id keys
- **Test type:** AUTOMATED (unit parser-side + bats writer-side)
- **Test files / names:**
  - Phase 3 Task 2: `<TESTS>test_liveness.py::test_read_liveness_parses_four_keys`, `test_read_liveness_extracts_pid_from_filename`, `test_read_liveness_missing_key_raises`, `test_read_liveness_ignores_extra_keys`, `test_read_liveness_handles_equals_in_argv`
  - Phase 8 Task 2: `tests/test_claude_wrapper_liveness.bats` → `@test "AC5.1 — wrapper writes liveness file with four required keys at startup"`
- **Phases contributing:** Phase 3 (parser side); Phase 8 (writer side, end-to-end)
- **Status:** covered

### crash-recovery.AC5.4 — Concurrent wrappers write distinct PID-keyed files
- **Test type:** AUTOMATED (unit + bats)
- **Test files / names:**
  - Phase 3 Task 2: `<TESTS>test_liveness.py::test_list_liveness_files_enumerates_distinct_pids`
  - Phase 8 Task 2: `tests/test_claude_wrapper_liveness.bats` → `@test "AC5.4 — concurrent wrappers write distinct liveness files"`
- **Phases contributing:** Phase 3 (enumeration); Phase 8 (writer concurrency)
- **Status:** covered

### crash-recovery.AC5.6 — Boot_id mismatch classifies as casualty regardless of PID
- **Test type:** MIXED — automated for the deterministic rule wiring + HUMAN_JUDGEMENT for the post-reboot UAT scenario
- **Test files / names (automated portion):**
  - Phase 3 Task 2: `<TESTS>test_liveness.py::test_current_boot_id_returns_kernel_value`, `test_current_boot_id_is_lowercase`
  - Phase 4 Task 5: `<TESTS>test_scan.py::test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive` — end-to-end, asserts boot mismatch wins over PID-alive
- **Phases contributing:** Phase 3 (boot_id read); Phase 4 (scan wiring); Phase 8 (post-reboot UAT — see uat-requirements.md)
- **Status:** covered (automated portion); UAT portion in `uat-requirements.md`

### crash-recovery.AC6.1 — Dead-PID liveness correlates to UUID → `hard_crash`
- **Test type:** AUTOMATED (unit + integration)
- **Test files / names:**
  - Phase 3 Task 5: `<TESTS>test_correlate.py::test_correlate_direct_match_via_argv_resume`, `test_correlate_single_mtime_match`, `test_correlate_argv_uuid_but_jsonl_missing_falls_back_to_mtime`, `test_correlate_filters_out_jsonl_with_old_first_entry`
  - Phase 4 Task 5: `<TESTS>test_scan.py::test_scan_writes_expected_rows` — exercises dead-PID liveness → `hard_crash` end-to-end
- **Phases contributing:** Phase 3 (correlation); Phase 4 (scan wiring)
- **Status:** covered

---

## Phase 4: `scan` subcommand

### crash-recovery.AC3.6 — Stale `classifier_version` rows re-classified before render/prune
- **Test type:** AUTOMATED (integration; fixture-driven)
- **Test file:** `<TESTS>test_scan.py`
- **Test names:** `test_scan_reclassifies_stale_classifier_version_rows`; `test_scan_reclassifies_stale_row_whose_jsonl_still_exists`
- **Phase:** Phase 4 Task 5
- **Status:** covered

### crash-recovery.AC6.2 — Live PID → `live`, never `hard_crash`
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_scan.py`
- **Test name:** `test_scan_classifies_live_pid_as_live`
- **Phase:** Phase 4 Task 5
- **Status:** covered

### crash-recovery.AC6.3 — Multiple mtime candidates → `borderline` / `ambiguous_match` with candidates in `state_summary`
- **Test type:** AUTOMATED (unit + integration)
- **Test files / names:**
  - Phase 3 Task 5: `<TESTS>test_correlate.py::test_correlate_multiple_mtime_candidates_is_ambiguous`
  - Phase 4 Task 5: `<TESTS>test_scan.py::test_scan_classifies_ambiguous_correlation_as_borderline_ambiguous_match` — asserts both candidate rows produced with `state_summary` containing the candidate UUIDs
- **Phases contributing:** Phase 3 (correlate detection); Phase 4 (scan override + state_summary)
- **Status:** covered

---

## Phase 5: `render` subcommand and markdown contract

### crash-recovery.AC3.2 — `scan` + `render` twice → byte-identical markdown
- **Test type:** AUTOMATED (unit snapshot + bats smoke)
- **Test files / names:**
  - Phase 5 Task 6: `<TESTS>test_render.py::test_render_matches_snapshot[empty]`, `test_render_matches_snapshot[mixed]`, `test_render_matches_snapshot[all_concluded]`, `test_render_is_byte_identical_across_calls`
  - Phase 7 Task 3: `tests/test_crash_recovery_smoke.bats::@test "render is byte-identical across two calls (AC3.2 smoke)"`
- **Phases contributing:** Phase 5 (snapshot tests); Phase 7 (bats sha256 smoke)
- **Status:** covered

### crash-recovery.AC4.4 — Direct edits to `~/llm-resume.md` do NOT persist across `regenerate`
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_render.py`
- **Test name:** `test_render_overwrites_user_edits`
- **Phase:** Phase 5 Task 6
- **Status:** covered

### crash-recovery.AC7.1 — Concluded sessions remain in render after `regenerate`
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_render.py`
- **Test name:** `test_regenerate_preserves_concluded_rows`
- **Phase:** Phase 5 Task 6
- **Status:** covered

---

## Phase 6: `note`, `history`, `prune`, `list-live` subcommands

### crash-recovery.AC4.1 — `note <uuid> "x"` then `regenerate` surfaces "x"
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_note.py`
- **Test name:** `test_note_set_then_regenerate_surfaces_text`
- **Phase:** Phase 6 Task 2
- **Status:** covered

### crash-recovery.AC4.2 — `note <uuid> "y"` overwrites prior text
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_note.py`
- **Test name:** `test_note_overwrites_existing`
- **Phase:** Phase 6 Task 2
- **Status:** covered

### crash-recovery.AC4.3 — `note <uuid> --clear` removes the note
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_note.py`
- **Test name:** `test_note_clear_removes_note`; also `test_note_cli_clear_without_text`
- **Phase:** Phase 6 Task 2
- **Status:** covered

### crash-recovery.AC4.5 — `note` against unknown UUID exits non-zero, no row inserted
- **Test type:** AUTOMATED (unit + integration)
- **Test file:** `<TESTS>test_note.py`
- **Test names:** `test_note_unknown_uuid_raises_and_does_not_insert` (unit); `test_note_cli_unknown_uuid_exits_nonzero_with_error_text` (CLI subprocess)
- **Phase:** Phase 6 Task 2
- **Status:** covered

### crash-recovery.AC7.2 — `prune --dry-run` lists candidates without deleting
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_prune.py`
- **Test name:** `test_prune_dry_run_is_read_only`
- **Phase:** Phase 6 Task 5
- **Status:** covered

### crash-recovery.AC7.3 — `prune` without `--confirm` refuses, prints instructions
- **Test type:** AUTOMATED (integration + bats smoke)
- **Test files / names:**
  - Phase 6 Task 5: `<TESTS>test_prune.py::test_prune_without_confirm_refuses`
  - Phase 7 Task 3: `tests/test_crash_recovery_smoke.bats::@test "prune without --confirm refuses (AC7.3 smoke)"`
- **Phases contributing:** Phase 6 (full coverage); Phase 7 (bats smoke regression guard)
- **Status:** covered

### crash-recovery.AC7.4 — `prune --confirm` deletes only matching rows
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_prune.py`
- **Test name:** `test_prune_confirm_deletes_matching_rows`
- **Phase:** Phase 6 Task 5
- **Status:** covered

### crash-recovery.AC7.5 — Concluded session with user note NOT deleted
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_prune.py`
- **Test name:** `test_prune_preserves_concluded_with_user_note`
- **Phase:** Phase 6 Task 5
- **Status:** covered

### crash-recovery.AC7.6 — Concluded session with extant JSONL NOT deleted
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_prune.py`
- **Test name:** `test_prune_preserves_concluded_with_extant_jsonl`
- **Phase:** Phase 6 Task 5
- **Status:** covered

### crash-recovery.AC7.7 — Stale `classifier_version` rows NOT deleted by `prune --confirm`
- **Test type:** AUTOMATED (integration)
- **Test file:** `<TESTS>test_prune.py`
- **Test names:** `test_prune_excludes_stale_classifier_version_rows` (dry-run path); `test_prune_confirm_does_not_delete_stale_rows` (confirm path)
- **Phase:** Phase 6 Task 5
- **Status:** covered

---

## Phase 7: Skill file and skill ↔ CLI integration

### crash-recovery.AC1.2 — Plugin lists in `/plugin` after install
- **Test type:** AUTOMATED (smoke; nearest-automatable proxy)
- **Test file:** `tests/test_crash_recovery_smoke.bats`
- **Test name:** `@test "denubis-crash-recovery is listed in marketplace.json"`
- **Phase:** Phase 7 Task 3
- **Status:** covered (proxy — true `/plugin` listing requires a live Claude Code instance)

### crash-recovery.AC8.1 — README documents `denubis-plan-and-execute` dependency + version
- **Test type:** AUTOMATED (integration; grep-based)
- **Test file:** Phase 7 Task 2 inline verification (`grep -q "denubis-plan-and-execute"`, `grep -q "AC5.6"`, `grep -q "AC6.4"`); Phase 8 Task 4 placeholder replacement (`grep -v "<PHASE-8-VERSION>"`)
- **Phases contributing:** Phase 7 (README structure); Phase 8 (placeholder fill)
- **Status:** covered (informal grep-based; no dedicated pytest assertion — relies on phase-completion verification steps)

---

## Phase 8: Wrapper patch and version coordination

### crash-recovery.AC5.2 — Clean (0) or Ctrl-C (130) exit removes liveness file
- **Test type:** AUTOMATED (bats)
- **Test file:** `tests/test_claude_wrapper_liveness.bats`
- **Test names:** `@test "AC5.2 — clean exit (0) removes the liveness file"`; `@test "AC5.2 — Ctrl-C exit (130) removes the liveness file"`
- **Phase:** Phase 8 Task 2
- **Status:** covered

### crash-recovery.AC5.3 — `kill -9` of wrapper preserves liveness file
- **Test type:** AUTOMATED (bats)
- **Test file:** `tests/test_claude_wrapper_liveness.bats`
- **Test name:** `@test "AC5.3 — kill -9 of wrapper preserves the liveness file"`
- **Phase:** Phase 8 Task 2
- **Status:** covered

### crash-recovery.AC5.5 — Claude killed independently → wrapper non-zero, file persists
- **Test type:** AUTOMATED (bats)
- **Test file:** `tests/test_claude_wrapper_liveness.bats`
- **Test names:** `@test "AC5.5 — Claude exit 137 (SIGKILL) preserves the liveness file"`; `@test "AC5.5 — Claude exit 139 (SIGSEGV) preserves the liveness file"`; `@test "AC5.5 — Claude generic non-zero exit (1) preserves the liveness file"`
- **Phase:** Phase 8 Task 2
- **Status:** covered

### crash-recovery.AC8.2 — plugin.json + marketplace.json version-sync invariant
- **Test type:** AUTOMATED (integration; inline verification)
- **Test file:** Phase 8 Task 4 Step 5 inline Python verification (combined check for both plugins) — asserts `denubis-plan-and-execute @ 2.32.2` and `denubis-crash-recovery @ 1.0.0` agree across plugin.json and marketplace.json
- **Phase:** Phase 8 Task 4
- **Status:** covered

### crash-recovery.AC8.3 — CHANGELOG.md carries both new entries
- **Test type:** AUTOMATED (integration; inline verification)
- **Test file:** Phase 8 Task 4 Step 6 inline grep verification — asserts top three `## [...]` headings are crash-recovery 1.0.0, plan-and-execute 2.32.2, denubis-bibliography 0.1.0
- **Phase:** Phase 8 Task 4
- **Status:** covered

---

## Coverage Summary

### Bucket counts

- **AUTOMATED:** 31 ACs
- **HUMAN_JUDGEMENT (UAT-only):** 2 ACs — `crash-recovery.AC6.4`, plus Phase 7 DR2 prune-prompt-clarity check (not an AC; called out in plan)
- **MIXED (both test + UAT):** 1 AC — `crash-recovery.AC5.6` (rule-wiring automated, post-reboot scenario human-judged)

Total ACs enumerated: **34** (matches design plan: AC1.1–AC1.4, AC2.1–AC2.5, AC3.1–AC3.6, AC4.1–AC4.5, AC5.1–AC5.6, AC6.1–AC6.4, AC7.1–AC7.7, AC8.1–AC8.3).

### Per-AC bucket index

| AC | Bucket | Notes |
|---|---|---|
| AC1.1 | AUTOMATED | proxy via marketplace.json listing |
| AC1.2 | AUTOMATED | proxy via marketplace.json listing |
| AC1.3 | AUTOMATED | unit + inline check |
| AC1.4 | AUTOMATED | well-formedness gate |
| AC2.1 | AUTOMATED | cross-phase (1, 4, 5, 6) |
| AC2.2 | AUTOMATED | cross-phase |
| AC2.3 | AUTOMATED | Phase 1 |
| AC2.4 | AUTOMATED | Phase 1 |
| AC2.5 | AUTOMATED | Phase 1 |
| AC3.1 | AUTOMATED | Phase 2 |
| AC3.2 | AUTOMATED | Phase 5 (snapshot) + Phase 7 (bats smoke) |
| AC3.3 | AUTOMATED | Phase 2 |
| AC3.4 | AUTOMATED | Phase 2 |
| AC3.5 | AUTOMATED | Phase 2 |
| AC3.6 | AUTOMATED | Phase 4 |
| AC4.1 | AUTOMATED | Phase 6 |
| AC4.2 | AUTOMATED | Phase 6 |
| AC4.3 | AUTOMATED | Phase 6 |
| AC4.4 | AUTOMATED | Phase 5 |
| AC4.5 | AUTOMATED | Phase 6 |
| AC5.1 | AUTOMATED | Phase 3 (parser) + Phase 8 (bats writer) |
| AC5.2 | AUTOMATED | Phase 8 bats |
| AC5.3 | AUTOMATED | Phase 8 bats |
| AC5.4 | AUTOMATED | Phase 3 + Phase 8 |
| AC5.5 | AUTOMATED | Phase 8 bats |
| AC5.6 | **MIXED** | Phase 4 automated + Phase 8 UAT |
| AC6.1 | AUTOMATED | Phase 3 + Phase 4 |
| AC6.2 | AUTOMATED | Phase 4 |
| AC6.3 | AUTOMATED | Phase 3 + Phase 4 |
| AC6.4 | **HUMAN_JUDGEMENT** | Phase 8 UAT only |
| AC7.1 | AUTOMATED | Phase 5 |
| AC7.2 | AUTOMATED | Phase 6 |
| AC7.3 | AUTOMATED | Phase 6 + Phase 7 bats smoke |
| AC7.4 | AUTOMATED | Phase 6 |
| AC7.5 | AUTOMATED | Phase 6 |
| AC7.6 | AUTOMATED | Phase 6 |
| AC7.7 | AUTOMATED | Phase 6 |
| AC8.1 | AUTOMATED | Phase 7 (grep-based; informal) |
| AC8.2 | AUTOMATED | Phase 8 inline |
| AC8.3 | AUTOMATED | Phase 8 inline |

### Gaps (UNCOVERED)

No ACs are uncovered. Every AC appears in either `test-requirements.md` (this file)
or `uat-requirements.md` (collated separately).

Items to flag for human review during finalisation:

- **AC8.1** is covered by informal `grep` checks inside Phase 7 Task 2 and Phase 8 Task 4 verification steps rather than a dedicated pytest assertion. Test-analyst should confirm these inline checks survive into the executed plan as actual verification gates. Consider promoting to a `test_readme_documents_dependency.py` if a stronger gate is desired.
- **AC1.1 / AC1.2 / AC1.4** are proxies — true install/listing behaviour is owned by Claude Code itself and cannot be exercised in CI without a live Claude Code instance. The marketplace.json listing assertion and json.load validity gate are the strongest automated approximations available.

### MIXED ACs (flagged for human review)

- **AC5.6 — Boot_id mismatch after reboot.** Automated portion (`test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive`) verifies the deterministic rule wiring with a synthetic boot_id. UAT portion verifies the real reboot scenario — a recycled PID on a fresh kernel must not produce false-positive `live` classification. Both portions are needed; do not collapse to one.

### Cross-phase ACs (named here for the test-analyst's incremental verification)

- **AC2.1 / AC2.2** — incrementally complete across Phases 1, 4, 5, 6. Test-analyst should re-run `test_help_exits_zero` and the `EXPECTED_SUBCOMMANDS` parametrisation at the end of each contributing phase.
- **AC3.2** — Phase 5 covers byte-identical render via snapshots; Phase 7 adds bats sha256 smoke as a regression guard.
- **AC5.1 / AC5.4** — Phase 3 covers parser-side enumeration; Phase 8 covers writer-side end-to-end.
- **AC5.6** — Phase 3 boot_id read, Phase 4 scan wiring, Phase 8 post-reboot UAT (UAT portion in `uat-requirements.md`).
- **AC6.1** — Phase 3 correlation primitives, Phase 4 scan integration.
- **AC6.3** — Phase 3 ambiguous-detection, Phase 4 scan override + state_summary.
- **AC7.3** — Phase 6 full coverage, Phase 7 bats smoke regression guard.
- **AC8.1** — Phase 7 README structure, Phase 8 placeholder fill.
