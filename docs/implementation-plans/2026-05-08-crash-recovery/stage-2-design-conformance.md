# Stage 2 Design Conformance Review — denubis-crash-recovery

**Reviewer:** Coherence Reviewer (Opus 4.7)
**Date:** 2026-05-20
**Branch:** crash-recovery
**Diff range:** deaf92a..8147046 (full branch from merge-base with main)
**Design plan:** `docs/design-plans/2026-05-08-crash-recovery.md` (DR1-DR10, AC1.1-AC8.3)
**Architecture docs:** `docs/architecture/` (Stage 1 just landed: constraints.md Phase 8 update, new `plugins/denubis-crash-recovery/0-context.md`, ADRs 0001 and 0002)
**Scope:** Full-implementation conformance — not per-phase. Anchor is the design plan, not the phase files.

---

## Executive Summary

The implementation **coheres** with the design plan's intent. All 10 Decision Records (DR1-DR10) are honoured in code. All 40 ACs (AC1.1-AC8.3) are either pinned by a test, deferred to live operation with explicit constraint documentation, or covered by manual procedures whose absence from automated testing is by design.

Three classes of finding warrant the orchestrator's attention:

1. **Two unrecorded architectural divergences** from the design plan: the `scan.py` → `scan.py` + `scan_db.py` module split, and the abandonment of the design plan's "boolean liveness flag column" in favour of a render-side reason-prefix partition. Neither is a defect — both are reasoned engineering choices made during implementation — but neither has an ADR.
2. **Two architecture-doc-vs-code drifts** from the just-landed Stage 1 docs: `0-context.md` and `constraints.md` reference `bookkeeping.py` / `crash_recovery.bookkeeping` as if it were a separate module; in code the deny-list lives in `jsonl.py:_REAL_TYPES`.
3. **One latent plan-vs-code drift** in `phase_06.md` that was caught and corrected inline (the `scan.py` vs `scan_db.py` reference) — flagged for completeness against the Phase 8 plan-defect class.

No High-severity findings. Five Medium findings, five Low.

---

## 1. Conformance

### 1.1 Components in design plan → code

The design plan enumerates eight phases of components and a "three components produce data" architecture summary. Mapping is exhaustive:

| Designed component (design plan) | Implementation location | Status |
|---|---|---|
| `denubis-crash-recovery` plugin scaffold | `plugins/denubis-crash-recovery/` | Built |
| `.claude-plugin/plugin.json` (1.0.0) | exists; version 1.0.0; marketplace.json matches | Built |
| `scripts/crash_recovery/` uv-managed Python package | exists with `pyproject.toml`, `src/`, `tests/` | Built |
| `crash_recovery.db` (schema constants + connection) | `src/crash_recovery/db.py` | Built |
| `crash_recovery.jsonl` (tail parser) | `src/crash_recovery/jsonl.py` | Built |
| `crash_recovery.classify` (rule table + `classify()`) | `src/crash_recovery/classify.py` | Built |
| `crash_recovery.liveness` (read/boot/pid/local-fs) | `src/crash_recovery/liveness.py` | Built |
| `crash_recovery.correlate` (DIRECT/MTIME/AMBIGUOUS/NO_MATCH) | `src/crash_recovery/correlate.py` | Built |
| `crash_recovery.scan` (orchestrator) | `src/crash_recovery/scan.py` + `scan_db.py` | **Split** (see §4.1) |
| `crash_recovery.render` (DB→markdown) | `src/crash_recovery/render.py` | Built |
| `crash_recovery.note` (set/clear `user_notes`) | `src/crash_recovery/note.py` | Built |
| `crash_recovery.history` (read `classification_history`) | `src/crash_recovery/history.py` | Built |
| `crash_recovery.prune` (gated delete) | `src/crash_recovery/prune.py` | Built |
| `crash_recovery.list_live` (live PIDs) | `src/crash_recovery/list_live.py` | Built |
| `crash-recovery` CLI (typer-based) | `src/crash_recovery/__main__.py` | Built |
| Skill `denubis-crash-recovery:triage` | `plugins/denubis-crash-recovery/skills/triage/SKILL.md` | Built |
| Patched `denubis-plan-and-execute/scripts/claude-wrapper.sh` | `plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` (Block A + Block B) | Built |
| Marketplace entry for `denubis-crash-recovery` 1.0.0 | `.claude-plugin/marketplace.json` | Built |
| `~/.claude/run/$$.live` files (writer side) | wrapper writes via `mkdir -p` + tempfile + `mv` | Built |

**No designed component is missing.** Phases 1-8 all delivered the artifacts the design enumerated.

### 1.2 CLI subcommand surface (AC2.1)

Design plan AC2.1 lists nine subcommands: `scan`, `render`, `triage`, `regenerate`, `list-live`, `note`, `history`, `prune`, `init`.

`__main__.py` declares: `init`, `scan`, `render`, `triage`, `regenerate`, `note`, `history`, `prune`, `list-live`. **All nine present.** `test_cli_help.py` pins this against the design (AC2.1 + AC2.2).

### 1.3 Schema vs Data Model

Design plan's Data Model (lines 142-174) specifies three tables. Comparison against `db.py::SESSIONS_DDL`, `SCAN_RUNS_DDL`, `CLASSIFICATION_HISTORY_DDL`:

- **`sessions`:** all 13 columns present (uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts, classification, classification_reason, classifier_version, state_summary, first_seen, last_scanned, user_notes). CHECK constraint on `classification` references `CLASSIFICATION_VALUES` (the StrEnum-derived authoritative source). Conforms.
- **`scan_runs`:** all 5 columns present (id, ts, live_pids, sessions_scanned, classifier_version). `live_pids` is `json.dumps(sorted set)` → TEXT, matching the design's "JSON-encoded array of integers" intent. Conforms.
- **`classification_history`:** all 5 columns present + composite PK (uuid, scan_id) + both FKs (CASCADE on sessions, RESTRICT on scan_runs) + CHECK constraint. Conforms.

### 1.4 Liveness file format (writer side)

Design plan (lines 178-183) specifies four key=value lines: `cwd`, `started`, `argv`, `boot_id`. Wrapper writes (lines 88-99 of `claude-wrapper.sh`) all four. Atomic via tempfile (`$$.live.tmp`) + `mv`. AC5.1 pinned by `test_claude_wrapper_liveness.bats::AC5.1`. Conforms.

### 1.5 Wrapper exit-status discipline (DR8 — the load-bearing one)

DR8 specifies: "remove the file when exit status is 0 (clean) or 130 (Ctrl-C); any other status leaves it." Wrapper implements exactly that at the `# --- crash-recovery liveness file cleanup ---` block. **AC5.5 (×3 codes 1/137/139) and AC5.2 (codes 0 and 130) all pass.** ADR 0001 captures the implementation-time discovery that this required `|| EXIT_CODE=$?` to defeat `set -e`.

### 1.6 No erosion, one drift (rated below)

No structural pattern in the implementation violates the design's intent. The single architecturally interesting drift is the `scan.py` → `scan.py + scan_db.py` split (functional core / imperative shell separation made explicit at module boundary). The design plan was silent on this. Rated **notable** in §4.

---

## 2. Plan-vs-Code Drift Sweep (extended per Phase 8 ADRs)

Per the orchestrator's brief, sample the 8 phase files for the class of error that produced Phase 8's two known defects (`set -e` interaction at wrapper line 89, `REAL_CLAUDE` vs `CLAUDE_REAL_BINARY` env-var name). Findings reported as latent risk; do NOT retroactively edit phase files.

### 2.1 Known defects (already ADR-captured)

| Defect | Location | Status |
|---|---|---|
| `phase_08.md` "Codebase verified: no `exec` to replace, EXIT_CODE=$? capture at line 89-90" missed `set -e` interaction | `phase_08.md` § Subcomponent A "Codebase verified" | Captured as ADR 0001; constraint row added; fitness test `test_claude_wrapper_liveness.bats::AC5.5` (×3) locks the contract. **No action.** |
| `phase_08.md` bats template used `REAL_CLAUDE` not `CLAUDE_REAL_BINARY` | `phase_08.md` § Subcomponent A Task 2 (lines 112, 137, 154, 169, 216, 234, 236, 254, 264) | Captured as ADR 0002; constraint row added; `tests/test_claude_wrapper_liveness.bats` uses `CLAUDE_REAL_BINARY` end-to-end. **No action.** |

### 2.2 Latent drift caught and corrected inline (no production defect)

| Drift | Location | Status |
|---|---|---|
| `phase_06.md` Design Constraint section (line 47) originally said `_orphan_sweep` lives in `scan.py`; the Phase 4 module split moved it to `scan_db.py` | `phase_06.md:47` carries the inline correction *"the function moved here in the Phase 4 module split; an earlier draft of this constraint referenced `scan.py`"*; line 65 has the parallel correction | Detected and corrected inline during Phase 6 implementation; no test relied on the wrong module. **No action — Low.** |

### 2.3 Sweep results across other phases

Spot-check of phase_01.md through phase_07.md for the "specified an identifier from memory rather than reading the code" class:

- **phase_01.md:** schema DDL columns specified verbatim against design Data Model. Cross-checked: every column in design `sessions` / `scan_runs` / `classification_history` matches `db.py`. No drift.
- **phase_02.md:** TailKind enum members specified. Cross-checked against `jsonl.py::TailKind` — all members (MISSING_FILE, MALFORMED_TAIL, EMPTY, TOOL_USE_NO_RESULT, ASK_QUESTION_NO_REPLY, AGENT_DISPATCH_NO_RESULT, UNKNOWN, CONCLUDED) match the rule table. No drift.
- **phase_03.md:** `read_liveness`, `pid_alive`, `current_boot_id`, `list_liveness_files`, `assert_local_filesystem` symbols all present in `liveness.py` with matching signatures. No drift.
- **phase_04.md:** `_walk_sessions`, `_classify_fact`, `_upsert_session`, `_append_history`, `_orphan_sweep`, `_write_scan_run`, `ScanContext`, `ScanRunResult`, `SessionFact` all present (across `scan.py` + `scan_db.py`). The module split was a Phase 4 implementation decision discovered during build; phase_04.md does not document the split but the file inventory is correct. **Latent risk: future plan edits referencing "scan.py::_orphan_sweep" by symbol path will not match grep.**
- **phase_05.md:** `LIVENESS_REASONS`, `NO_LIVENESS_REASONS`, `JSONL_ONLY_REASONS`, `SectionKey`, `Section`, `SECTIONS`, `_section_for_row`, `_reduced_confidence_text`, `_render_entry`, `render` all present in `render.py`. **Phase 5 plan declared `render() -> str`; implementation is `render() -> tuple[str, int]`.** This was a Phase 6 fix (commit ac50812) to resolve a TOCTOU window; phase_05.md was not retroactively edited. Documented Medium risk for future plan re-edits.
- **phase_06.md:** All four subcommand functions (`set_note`/`clear_note`, `fetch_history`, `survey`/`delete_candidates`, `survey_live`) present at the documented paths. Apart from the inline-corrected `scan.py`→`scan_db.py` drift (§2.2), no further drift.
- **phase_07.md:** SKILL.md frontmatter shape and triage flow match. No symbol-level drift.

### 2.4 Drift sweep summary

**One latent risk** (M1): phase_05.md still documents `render() -> str` (current code is `tuple[str, int]`). If a future plan author re-reads phase_05.md as the source of truth for `render`'s contract, they will write the wrong type signature. Either retroactively note "amended Phase 6" in phase_05.md, or accept that constraints.md + the actual code are the binding sources.

**One latent risk** (M2): phase_04.md does not document the `scan.py` → `scan_db.py` module split. The `phase_06.md` Design Constraint section caught this inline; future phase authors editing in this area should know the split exists.

---

## 3. Traceability — DR1-DR10 and AC1.1-AC8.3

### 3.1 Decision Records → code + test

| DR | Decision | Code | Test | Doc |
|---|---|---|---|---|
| DR1 | SQLite as truth, markdown as render | `db.py`, `render.py`, `__main__.py::regenerate` | `test_render.py::test_render_overwrites_user_edits`, AC4.4 in `test_render.py` | constraints.md "Deterministic render", design-plan |
| DR2 | PID-keyed liveness, post-hoc UUID resolve | `liveness.py` (filename = `$$.live`), `correlate.py` (DIRECT/MTIME/AMBIGUOUS/NO_MATCH) | `test_correlate.py::test_project_dir_for_cwd_handles_encoding_collision` + AC6.1 fixtures | constraints.md "Liveness file four-key format", "Lossy-encoding collision safety" |
| DR3 | Patch `denubis-plan-and-execute` wrapper directly | `claude-wrapper.sh` Blocks A+B | `test_claude_wrapper_liveness.bats` (11 tests) | CHANGELOG.md `[denubis-plan-and-execute] 2.32.2`, constraints.md "Writer-side liveness lifecycle" |
| DR4 | Triage-only scope (no byobu/OOM) | Plugin scope: no byobu/OOM in `plugins/denubis-crash-recovery/` | n/a (negative space) | design-plan "Explicitly OUT of scope", README "Out of scope" |
| DR5 | Deterministic Python rules, no LLM | `classify.py::RULES` + `classify()` (pure) | `test_classify.py::test_every_rule_classifies_its_fixture` (parametrised, one per rule); `test_render.py` snapshots | constraints.md "Deterministic classification" |
| DR6 | No automatic pruning | `prune.py::survey` + `delete_candidates`; CLI requires `--confirm` | `test_prune.py::test_prune_without_confirm_refuses`, `..._dry_run_is_read_only` | constraints.md "No auto-prune" |
| DR7 | Boot-aware liveness via `boot_id` | `liveness.py::current_boot_id`, `scan.py::_build_liveness_fact_direct_or_mtime` computes `boot_id_current`, `classify.py` Rule(`liveness_present=True, boot_id_current=False` → HARD_CRASH/`liveness_boot_id_mismatch`) | `test_scan.py::test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive`; AC5.6 deferred to live operation per constraint | constraints.md "Boot-aware liveness" |
| DR8 | Exit-status-conditional cleanup, NOT `trap EXIT` | `claude-wrapper.sh` Block B `if [ "$EXIT_CODE" -eq 0 ] || [ "$EXIT_CODE" -eq 130 ]` | `test_claude_wrapper_liveness.bats::AC5.2`, `AC5.3`, `AC5.5` (×3) | ADR 0001 (the `set -e` correction), constraints.md "Writer-side liveness lifecycle", "Wrapper exit-code capture + transcript-archive gate" |
| DR9 | `classifier_version` column on every row | `db.py` (column on `sessions`, `scan_runs`, `classification_history`); `scan_db.py::_orphan_sweep` re-classifies | `test_scan.py::test_scan_reclassifies_stale_classifier_version_rows`; `test_prune.py::test_prune_*_does_not_delete_stale_rows` (AC7.7) | constraints.md "Classifier version forward-compat", "No auto-prune" (four-condition guard) |
| DR10 | Orphan sweep re-classifies ALL unseen rows (not just version-stale) | `scan_db.py::_orphan_sweep` walks every `sessions.uuid NOT IN seen_uuids` | `test_scan.py::test_scan_reclassifies_stale_row_whose_jsonl_still_exists` (the vanished-JSONL path) | design-plan DR10, constraints.md "Classifier version forward-compat" |

**All 10 DRs are traceable to code + test + doc.** No gaps.

### 3.2 Acceptance Criteria → tests

Cross-check between the 40 ACs in the design plan and AC-tagged test code:

**Pinned by automated tests (36):** AC1.2, AC1.3, AC1.4, AC2.1, AC2.2, AC2.3, AC2.4, AC2.5, AC3.1, AC3.2, AC3.3, AC3.4, AC3.5, AC3.6, AC4.1, AC4.2, AC4.3, AC4.4, AC4.5, AC5.1, AC5.2, AC5.3, AC5.4, AC5.5, AC6.1, AC6.2, AC6.3, AC7.1, AC7.2, AC7.3, AC7.4, AC7.5, AC7.6, AC7.7, AC8.1, **plus AC5.6 (read-side pinned in `test_liveness.py::test_current_boot_id`; reboot UAT deferred)**.

**Deferred to live operation by explicit constraint (1):** AC6.4 (idle-kill UAT). Documented in constraints.md "AC5.6 / AC6.4 UAT deferral to live operation". Empirically observed twice (2026-05-18, 2026-05-20 real crashes).

**Deferred to manual install verification (1):** AC1.1 (`claude plugin install` exit 0). Cannot be tested without a Claude Code plugin host. **No constraint row captures this deferral explicitly.** Rated **Low** (M3).

**Verified by manual one-time release script, not locked as a regression test (2):** AC8.2, AC8.3.
- AC8.2 (version-sync invariant across both plugins): `test_plugin_manifest.py::TestMarketplaceEntry::test_versions_match` covers `denubis-crash-recovery`. **No equivalent test for `denubis-plan-and-execute`.** Phase 8 Task 4 step 5 ran a one-time `python -c "for plugin_name, expected_version in ..."` check at release commit time. The version-sync invariant for `denubis-plan-and-execute@2.32.2` is not pinned; if it drifts at the next bump, no test will catch it. Rated **Medium** (M3 candidate fitness function). The repo CLAUDE.md "Version Updates Require Marketplace and Changelog Sync" rule is enforced by reviewer eye, not by test, for this plugin.
- AC8.3 (two CHANGELOG entries): satisfied in CHANGELOG.md (head shows `[denubis-crash-recovery] 1.0.0` and `[denubis-plan-and-execute] 2.32.2`). Not locked by a test. Rated **Low**.

### 3.3 Candidate fitness functions (Ford et al.)

Per the brief — flag automatable concerns as test requirements rather than recurring review items:

- **AC8.2 fitness function:** add a root-level `test_marketplace_sync.py` that walks every `plugins/*/.claude-plugin/plugin.json` and asserts the marketplace entry's version string matches. Would cover both `denubis-crash-recovery` AND `denubis-plan-and-execute` (and every future plugin) without per-plugin retooling. **Recommended as M3 fitness function.**
- **AC1.1 fitness function:** not automatable without a Claude Code plugin host. Document the deferral in constraints.md (paired with AC5.6/AC6.4 deferral). **Recommended as L3 documentation fix.**

---

## 4. Baked-In Assumptions (Built but Not Designed)

These are decisions the implementation made where the design plan was silent. Rated benign / notable / concerning per the brief.

### 4.1 `scan.py` → `scan.py` + `scan_db.py` module split (notable)

- **Design said:** "crash_recovery.scan module — orchestrates: enumerate JSONLs … etc."
- **Implementation chose:** Split into `scan.py` (orchestrator + read-only walk + `SessionFact`/`ScanContext`/`ScanRunResult`/`_classify_fact`) and `scan_db.py` (the four DB-writer helpers `_write_scan_run`, `_upsert_session`, `_append_history`, `_orphan_sweep`, plus `WriteContext`).
- **Rating:** **notable.**
- **Why notable:** This is an explicit Functional-Core / Imperative-Shell separation at the module boundary. The rationale (write-block isolation, FCIS) is recorded in `scan_db.py` docstring and `scan.py` docstring. **It is not recorded as an ADR.** Phase 6 plan caught the impact inline (the `_orphan_sweep` moved); future architecture diagrams should reflect the split.
- **Forward impact:** any future "where does `_orphan_sweep` live" question will resolve correctly via grep, but plan re-edits referencing "scan.py::_orphan_sweep" by symbol path will fail. Recommended: lift to ADR 0003 OR add a Module Inventory section to `0-context.md` that names both files.

### 4.2 Liveness-presence-via-reason-prefix instead of dedicated boolean column (notable)

- **Design said (line 508):** "Liveness presence/absence is recorded in `sessions` as a boolean flag, so renders can flag pre-installation entries with reduced confidence."
- **Implementation chose:** No boolean column on `sessions`. Instead, render-side derivation: `render.py::LIVENESS_REASONS` (six reason strings), `NO_LIVENESS_REASONS` (four reason strings), `JSONL_ONLY_REASONS` (six reason strings) form a disjoint partition over every reason `classify.py::RULES` can emit + `ambiguous_match` + `unmatched`. `_reduced_confidence_text` reads the reason and returns the appropriate inline warning.
- **Rating:** **notable.**
- **Why notable:** The schema is simpler (one fewer column to migrate when adding rules); the trade-off is that any new reason must be assigned to exactly one of the three sets, otherwise `test_reason_prefix_partition_is_exhaustive` fails. The partition test pins this contract. The design's "boolean flag" framing is structurally dead but linguistically alive in the design plan.
- **Forward impact:** if a future maintainer reads the design plan looking for `sessions.liveness_present`, they will not find it and may add the column thinking it was forgotten. Recommended: lift to ADR 0003 (paired with §4.1) OR add a "Schema vs Design Plan" note in `0-context.md`.

### 4.3 `bookkeeping.py` referenced in architecture docs but lives in `jsonl.py` (notable, doc-side defect)

- **Stage 1 docs said (0-context.md:96 and constraints.md:72):** `bookkeeping.py` is a separate module owning the `_REAL_TYPES` deny-list.
- **Implementation reality:** `_REAL_TYPES` lives in `jsonl.py:58` (a frozenset constant). There is no `bookkeeping.py` file on disk.
- **Rating:** **notable** — architecture-doc-vs-code drift introduced in Stage 1.
- **Why it matters:** Stage 1 was the orchestrator's commitment to documenting the implementation faithfully. A reference to a non-existent module file undermines the document's reliability for future readers (who will grep, fail, and wonder if the file was removed or never existed). Constraints.md:72 also says `crash_recovery.bookkeeping._REAL_TYPES` — the actual import path is `crash_recovery.jsonl._REAL_TYPES`.
- **Forward impact:** every future reader of `0-context.md` § "Key modules" will see a row that doesn't exist on disk. Recommended Stage 1 follow-up: either rename `_REAL_TYPES` into a real `bookkeeping.py` module (small refactor) OR fix the docs to say `jsonl.py:_REAL_TYPES`. **The docs were just written and not yet circulated — easier to fix the docs than the code.**

### 4.4 CLI exit code 1 vs 2 contract (benign — but worth verifying)

- **Design said:** Nothing about exit codes.
- **Implementation chose:** A 0/1/2 contract — 0 = success, 1 = "no data" (history with no rows, prune refusal without --confirm), 2 = "invalid input or operation refused" (note against unknown UUID, --dry-run+--confirm mutex, platform refusal, network-FS refusal).
- **Rating:** **benign.** Documented in constraints.md "CLI exit-code contract (Phase 6)" with rationale.
- **Forward impact:** skill authors (the triage SKILL.md already relies on this) and shell scripts can count on stable semantics. Lifting to an ADR is optional; the constraints.md row is sufficient.

### 4.5 `state_summary` format for AMBIGUOUS rows (benign)

- **Design said:** "`state_summary` TEXT — 1-line render of the last few entries."
- **Implementation chose:** For ambiguous-correlation rows, `state_summary` carries a stable prefix `"ambiguous match: "` followed by comma-joined candidate UUIDs (`scan.py::AMBIGUOUS_STATE_SUMMARY_PREFIX`). Phase 5's render checks this prefix to route the row to the AMBIGUOUS_CORRELATION section.
- **Rating:** **benign.** The format is part of the module's public surface (named constant) and pinned by Phase 4 coherence M5.

### 4.6 Console-script name kept bare while plugin name carries `denubis-` prefix (benign — already explained)

- **Design said:** "the plugin directory is `denubis-crash-recovery` (matching the repo's universal `denubis-` prefix convention) while the Python package, CLI binary, AC slug, env-var prefix, and DB filename keep the bare `crash-recovery` / `crash_recovery` form for ergonomic command-line use."
- **Implementation:** matches verbatim. Plugin = `denubis-crash-recovery`, package = `crash_recovery`, binary = `crash-recovery`.
- **Rating:** **benign.** Design explicitly addressed.

### 4.7 `list-live` does NOT filter on `boot_id_current` (benign)

- **Design said (DR7 implies):** "Files whose `boot_id` does not match the current boot are treated as guaranteed casualties."
- **Implementation chose:** `list_live.py::survey_live` deliberately includes rows where `boot_id_current=False`, surfacing them with a `boot_ok=NO` column rather than filtering. Rationale documented inline in `__main__.py::list_live` and in `list_live.py` docstring: a recycled PID showing `boot_ok=NO` is diagnostic signal, not a row to hide.
- **Rating:** **benign.** This is the "list-live is a diagnostic, not a classifier" boundary. DR7 governs `scan`-time classification, not `list-live` reporting. Code comment makes this explicit.

### 4.8 Triage skill description was rewritten to match Phase 7 description-shape rules (benign)

- **Phase 7 plan template description:** *"Use when inspecting Claude Code session state after a suspected crash and want to produce ~/llm-resume.md (classification, annotation, gated prune)."* — three-term parenthetical enumeration; would fail constraints.md "Skill description QA" regex.
- **Implementation chose:** *"Use when inspecting Claude Code session state after a suspected crash or idle-kill and producing ~/llm-resume.md with deterministic classification and gated prune."* — passes all six skill description QA rules.
- **Rating:** **benign.** Caught during Phase 7 implementation; documented in constraints.md "Skill description QA" row.

---

## 5. Forward Fitness

**N/A — this is the final phase.** The brief specifies forward fitness reduces to "live operation" + "post-mortem detection seed".

### 5.1 Live operation readiness

Foundations support live operation:

- The wrapper has shipped (commit d22b49d, 2026-05-19) and been version-bumped (`denubis-plan-and-execute@2.32.2` in commit bd16dc0). Any new Claude Code session via `claudew` will now write a liveness file.
- The CLI (`crash-recovery init` + `scan` + `triage`) is installable and runnable. README documents the install path and dependency.
- Two empirical real-world crash events (2026-05-18, 2026-05-20) have already validated the pipeline end-to-end. The constraint row "AC5.6 / AC6.4 UAT deferral" captures this.
- Real-world crash data was used to refine the design seed for post-mortem detection at `docs/design-plans/2026-05-19-post-mortem-crash-detection.md`.

### 5.2 Post-mortem detection seed (out of scope for this implementation)

The README and constraints.md "Post-mortem crash detection limitations" row both call out the limitation honestly — `hard_crash` cannot fire without a pre-existing liveness file. Sessions that crashed before the wrapper was installed appear under "Needs investigation" as `unknown_tail_kind` or `no_liveness_dangling_*`, NOT under "Idle-live killed". The future-work design seed enumerates the algorithm and open questions.

**No overclaim.** The implementation does not advertise capability it lacks.

### 5.3 What a hostile reviewer would flag (forward)

If a deeply hostile reviewer examined this foundation against the future post-mortem detection extension's needs, they would flag:

- **The `last -F` parsing dependency** for post-mortem detection is not yet present anywhere in the codebase. The design seed addresses this but is not implemented. **Not a defect for this scope.**
- **`_orphan_sweep`'s annotation-exemption** (Phase 6 Task 0) creates a category of "row that scan no longer touches once annotated." A future post-mortem detector that wants to re-classify annotated rows under a new algorithm will have to override or branch around this guard. The constraint "Annotation-preserves-classification" pins this contract. **Not a defect — known design trade-off.**
- **The 4-condition prune guard** means a future maintainer cannot widen prune to delete `hard_crash` rows without explicitly changing `prune.py::survey`. **Not a defect — intentional gating.**

No High-severity forward-fitness gaps.

---

## 6. Situated Accountability

The implementation encodes assumptions about how people use Claude Code. Applying the Haraway question:

### 6.1 Whose perspective shaped the design?

- **A Linux-using, single-user-machine, command-line-fluent power user** is the implicit reader of `~/llm-resume.md`. The skill's "Step 2: Annotate borderline entries" prompts the user to `crash-recovery note <uuid>` — assumes the user is comfortable invoking the CLI mid-skill. A user who prefers GUI workflows or who has not encountered the wrapper installation step will find the report harder to engage with.
- **A user who values determinism over nuance.** DR5 chose deterministic rules over LLM judgement; this means borderline cases require the user to interpret the reason string and decide. A user who would prefer an LLM-summarised narrative explanation of "what happened to this session" is being underserved by design — and that under-serving is the *point* of DR5.
- **A user on a single boot.** DR7's boot-id check assumes `/proc/sys/kernel/random/boot_id` is read-once-per-scan and stable. The constraints.md "Crash-Recovery bookkeeping deny-list re-sampling cadence" row acknowledges the wrapper writes `boot_id=unknown` on non-Linux hosts (so the wrapper itself is cross-platform but the reader is Linux-only). **Users on macOS/BSD are explicitly out of scope for `scan`** — the README and constraints.md both call this out.

### 6.2 Who bears costs that aren't visible in code?

- **The wrapper plugin user who is NOT a crash-recovery plugin user.** Every wrapper invocation now writes a liveness file under `~/.claude/run/`. If the user never installs `denubis-crash-recovery`, these files accumulate as cruft. The wrapper has no garbage-collection logic; the reader does (orphan sweep) but only runs if the reader is installed. **Asymmetric externality on the wrapper-only user.** Not flagged by the design plan. Rated **Low** finding (L1).
- **A user whose `$HOME` is on a network filesystem.** The reader-side `assert_local_filesystem` refuses to operate, exiting code 2. The wrapper does NOT check — it writes whatever `CRASH_RECOVERY_RUN_DIR` resolves to. This means the wrapper "looks fine" but `scan` refuses; the user must read the CHANGELOG.md Compatibility note OR the constraints.md "Local-filesystem refusal" row to understand. Documented, but the discovery path is not obvious.
- **A user who runs concurrent wrappers from different worktrees with the same Claude Code installation.** Phase 8 AC5.4 tests concurrent wrappers; the per-PID filename keeps them isolated. No cost here. **Good.**

### 6.3 What's absent?

- **Non-Linux post-mortem support.** macOS users cannot use `crash-recovery scan` at all; they get the wrapper-side liveness file but cannot read it. Documented but accepts the absence.
- **The user who would prefer to edit `~/llm-resume.md` directly.** DR1 ruled this out (markdown is regenerated). The skill's "Common rationalisations" table addresses one variant ("`--confirm` is enough") but not the user who would prefer GUI editing. Out of scope per design.
- **Telemetry on classification outcomes.** No instrumentation records which classifications fire most often, which would inform DR9 `CLASSIFIER_VERSION` bump decisions. Out of scope, but worth noting as a future-extension candidate.

The implementation reflects a particular user — a Linux-using, terminal-fluent, single-machine power user who values determinism — and is honest about this in the README and the design plan's "Out of scope" section. **No High-severity situated-accountability concerns.**

---

## 7. Architecture Doc Updates

Per the brief — verify Stage 1's architecture docs are consistent with the implementation as it currently exists.

### 7.1 `constraints.md` Phase 8 update

Reviewed: the 8 new constraint rows + 4 updated rows. Cross-check each against code:

- **Writer-side liveness lifecycle:** matches `claude-wrapper.sh` Blocks A+B; pinned by `test_claude_wrapper_liveness.bats` (11 tests). Consistent.
- **Wrapper exit-code capture + transcript-archive gate:** matches `|| EXIT_CODE=$?` line + `if [[ "$EXIT_CODE" -eq 0 ]]` gate. Consistent. ADR 0001 paired.
- **Bats env-var contract:** matches `CLAUDE_REAL_BINARY` usage in tests. Consistent. ADR 0002 paired.
- **AC5.6 / AC6.4 UAT deferral:** documented; matches README runbook structure. Consistent.
- **Crash-Recovery bookkeeping deny-list re-sampling cadence:** **inconsistent.** Refers to `crash_recovery.bookkeeping._REAL_TYPES` — actual location is `crash_recovery.jsonl._REAL_TYPES`. See M4 below.

### 7.2 New `0-context.md` for `denubis-crash-recovery`

Reviewed: comprehensive system-boundary diagram, external entities table, in/out-of-scope list, module inventory, env vars, dependencies. Cross-check against implementation:

- Module inventory at lines 85-96: lists `db.py`, `classify.py`, `liveness.py`, `scan.py`, `correlate.py`, `render.py`, `note.py`/`history.py`/`prune.py`/`list_live.py`, **`bookkeeping.py`**. **`scan_db.py` is missing from this list** (see §4.1 — the module split is undocumented). **`bookkeeping.py` is listed but does not exist as a file** (see §4.3).
- CLI subcommand table at lines 65-77: nine subcommands listed, matches `__main__.py`.
- Diagram: accurate — wrapper writes files, plugin reads them, DB is source of truth, render produces resume.md atomically.

### 7.3 Cross-references between the two plugin contexts

Reviewed: `0-context.md` (denubis-crash-recovery) names `denubis-plan-and-execute` as the wrapper-side sibling and pins `>= 2.32.2`. The wrapper-side plugin's `0-context.md` (`plugins/denubis-plan-and-execute/0-context.md`) — let me check if it's been updated.

<verify-not-needed: out of scope for this review — Stage 1 may or may not have touched denubis-plan-and-execute's context doc; the brief's focus is on the just-landed crash-recovery work>

The crash-recovery 0-context.md correctly identifies the wrapper as the writer-side, the version pin (2.32.2), and the cross-plugin contract. **Consistent.**

### 7.4 Recommended doc updates

**M4 (Medium):** Fix the two `bookkeeping.py` references in the just-landed docs:

- `docs/architecture/plugins/denubis-crash-recovery/0-context.md:96` — replace `bookkeeping.py` row with `jsonl.py` (or add `_REAL_TYPES` as a sub-bullet of jsonl.py; currently jsonl.py is not in the module table at all — the row says "`bookkeeping.py` | `_REAL_TYPES` deny-list filtering..." but jsonl.py owns parse_tail, TailKind, TailSummary as well, also unlisted).
- `docs/architecture/constraints.md:72` — replace `crash_recovery.bookkeeping._REAL_TYPES` with `crash_recovery.jsonl._REAL_TYPES`.

**M5 (Medium):** Add `scan_db.py` to the `0-context.md` module inventory. Either as a separate row OR merge with `scan.py` ("`scan.py` + `scan_db.py` | `run_scan()` orchestrator (scan.py) + DB-writer helpers + `_orphan_sweep` (scan_db.py)").

**L1 (Low):** Consider documenting the wrapper-side liveness-file cruft externality (§6.2) — for users who install the wrapper but not the crash-recovery reader. Either as a constraint row (e.g. "Wrapper-side liveness cruft accumulation") or as a Troubleshooting subsection in `plugins/denubis-plan-and-execute/README.md`. **Optional.**

**L2 (Low):** Consider documenting the AC1.1 deferral (not automatable without a Claude Code host) by appending to the existing constraints.md "AC5.6 / AC6.4 UAT deferral" row or adding an "AC1.1 install verification deferral" row. **Optional.**

**L3 (Low):** Consider lifting either §4.1 (scan_db.py module split) or §4.2 (no `liveness_present` column) — or both — to ADR 0003 / 0004. These are reasoned engineering decisions; ADRs make the rationale findable. Alternatively, expand the `0-context.md` "Key modules" section with a "Schema vs design plan" subsection explaining the divergence. **Optional but recommended for Phase 8 closure.**

---

## Findings Summary

### High (count: 0)

(None — all design-plan intent is honoured in code; all DRs are traceable; all ACs are pinned-or-deferred with documented rationale.)

### Medium (count: 5)

- **M1: phase_05.md still documents `render() -> str` (current signature is `tuple[str, int]`).** Latent plan-vs-code drift. Phase 6 fix (commit ac50812) corrected the implementation but not the phase file. Rated Medium because a future plan re-edit using phase_05.md as the source of truth would reintroduce the bug. **Recommended action:** add a footnote to phase_05.md noting the Phase 6 amendment, OR accept that constraints.md + actual code are the binding sources and treat phase files as historical artifacts.

- **M2: phase_04.md does not document the `scan.py` → `scan.py` + `scan_db.py` module split.** Latent plan-vs-code drift caught inline by phase_06.md but not retroactively noted in phase_04.md. **Recommended action:** add a brief "Module split note" to phase_04.md (one sentence) OR lift to an ADR (§4.1, L3 below).

- **M3: AC8.2 (version-sync invariant) has no regression test for `denubis-plan-and-execute@2.32.2`.** Only `denubis-crash-recovery` is locked by `test_plugin_manifest.py`. A future version bump to `denubis-plan-and-execute` without a corresponding marketplace.json update will not be caught by CI. **Recommended action:** add a root-level `tests/test_marketplace_sync.py` that walks every `plugins/*/.claude-plugin/plugin.json` and asserts marketplace entry agreement. Candidate fitness function per Ford et al.

- **M4: Stage 1 docs (0-context.md:96 and constraints.md:72) reference `bookkeeping.py` / `crash_recovery.bookkeeping`, which does not exist. The actual location is `jsonl.py:_REAL_TYPES`.** Documentation defect introduced by Stage 1. **Recommended action:** rewrite both references to point at `jsonl.py:_REAL_TYPES`. Easier to fix the docs than to create the file. The 0-context.md "Key modules" table is also missing `jsonl.py` entirely.

- **M5: `0-context.md` module inventory does not list `scan_db.py`.** The module exists, owns four DB-writer helpers + `WriteContext`, and is imported by `scan.py`. **Recommended action:** add to the module table (either as its own row or merged with `scan.py`).

### Low (count: 5)

- **L1: Wrapper-side liveness-file cruft externality for wrapper-only users.** A user who installs `denubis-plan-and-execute` but NOT `denubis-crash-recovery` accumulates `.live` files with no garbage collection. **Recommended action:** add a Troubleshooting note to `denubis-plan-and-execute`'s README or constraints.md.

- **L2: AC1.1 deferral (`claude plugin install` not automatable) is not documented as a deferral.** AC5.6 and AC6.4 have a constraint row; AC1.1 silently lives in the "not automated" bucket. **Recommended action:** extend constraints.md "AC5.6 / AC6.4 UAT deferral" row to include AC1.1, OR add a new row.

- **L3: §4.1 (`scan_db.py` module split) and §4.2 (no `liveness_present` column on `sessions`) are reasoned engineering choices made during implementation; neither has an ADR.** Future maintainers reading the design plan will find the "boolean flag" claim and the single-module assumption and may try to "fix" them. **Recommended action:** lift to ADR 0003 (module split) and ADR 0004 (reason-prefix partition instead of column), OR document in `0-context.md` as a "Departures from design plan" subsection.

- **L4: Design plan's Phase 4 and Phase 6 "Covers ACs" lists are mis-mapped.** Phase 4 says it covers AC4.1/AC4.2/AC4.3 (annotation CRUD), but annotations are Phase 6. Phase 6 says it covers AC2.3 (`init` schema), but `init` is Phase 1. The implementation plan correctly maps ACs to phases; the design plan's internal labeling is wrong. **Recommended action:** none. Design plan is a historical artifact; phase files and tests are the binding sources. Note for future design-plan-to-impl-plan validation: cross-check Phase → AC mappings against AC owners.

- **L5: The triage SKILL.md says "The dry-run gate is for the *user*, not the CLI."** This is a deliberate design statement (the CLI permits `prune --confirm` without first running `--dry-run`), but is not documented as a Decision Record. **Recommended action:** consider whether the user-must-see-the-list workflow deserves a Decision Record alongside DR6 (No automatic pruning). The skill body and constraint enforce it; an ADR would make the *why* findable.

---

## Overall Assessment

**COHERES — with five Medium findings and five Low findings.**

The implementation honours the design plan's intent across all 10 Decision Records and all 40 Acceptance Criteria. Two ADRs (0001 set-e exit-code capture, 0002 CLAUDE_REAL_BINARY env-var) capture the two known plan defects discovered during Phase 8 implementation. The plan-vs-code drift sweep (per the orchestrator's brief) surfaced one additional latent drift class (M1, M2) — phase files that document an older module shape or function signature than what the implementation eventually stabilised on. These are not implementation defects; they are historical-artefact defects that could trip a future plan re-edit.

The architecture docs landed in Stage 1 are mostly consistent with the implementation, with two specific corrections needed (M4, M5) — `bookkeeping.py` references should point at `jsonl.py`, and `scan_db.py` should appear in the module inventory.

The single fitness-function recommendation (M3) — a root-level marketplace-version-sync test — would prevent a future regression in the version-sync invariant that currently relies on reviewer eye for `denubis-plan-and-execute`. This is the only finding that affects ongoing CI guarantees; the others are documentation hygiene.

No High-severity findings. No DR is unhonoured. No AC is unaccounted-for. The implementation can proceed to merge once the human orchestrator decides which Medium findings to act on now vs defer.

---

## Recommended Next Steps (for the orchestrator's decision)

1. **Act on M3 now** if the version-sync invariant should be CI-enforced — this is the only finding with ongoing regression-prevention value.
2. **Act on M4 now** because Stage 1 docs were just written and not yet circulated; trivial to fix `bookkeeping.py` → `jsonl.py:_REAL_TYPES` references before they cement as "the docs say".
3. **Act on M5 now** for the same reason as M4 — add `scan_db.py` to the module inventory.
4. **Defer M1 and M2** unless the workflow re-reads phase files as the source of truth for future plan edits. If phase files are archived as historical artefacts, these are Low.
5. **Defer all Low findings** to a separate doc-hygiene pass, or close them as out-of-scope acknowledged.
