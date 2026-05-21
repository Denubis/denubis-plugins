# Critical Peer Review: denubis-crash-recovery implementation plan

**Reviewer:** Critical Peer Reviewer (claude-opus-4-7[1m])
**Date:** 2026-05-14
**Documents reviewed:**
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/phase_01.md` … `phase_08.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/test-requirements.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/uat-requirements.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/design-plans/2026-05-08-crash-recovery.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/code-review-findings-plan-validation.md` (UNTRUSTED; not used as authority)

**Verification baseline (commands actually run):**
- `cat /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/plugins/denubis-plan-and-execute/scripts/claude-wrapper.sh` — read the on-disk wrapper at HEAD of `crash-recovery` branch.
- `cat /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` — confirmed version `2.32.1`.
- `cat /proc/sys/kernel/random/boot_id` — confirmed 36-char UUID + newline (37 bytes total).
- `python3 -c '…'` enumerated 14 plugins in `marketplace.json`.
- `grep -n "^### DR" docs/design-plans/2026-05-08-crash-recovery.md` — confirmed DR1–DR9 exist in design plan; DR3 = "Patch denubis-plan-and-execute's wrapper directly".
- `grep -n "DR" docs/implementation-plans/2026-05-08-crash-recovery/phase_*.md` — confirmed Phase 7 cites a "DR3 in Phase 6" that does not exist (Phase 6 has no Decision Records); Phase 8 bats tests are labelled "DR2" / "DR3" with semantics unrelated to design DR2/DR3.

---

## Source Inventory

| Artifact | Status |
|---|---|
| 8 phase files | Read in full |
| test-requirements.md | Read in full |
| uat-requirements.md | Read in full |
| design plan | Read in full |
| Prior reviewer findings | Read; **not trusted; not used as authority** |
| `claude-wrapper.sh` (on-disk) | Read in full |
| `pyproject.toml` (repo-root) | Read in full |
| `marketplace.json` (on-disk) | Read in full (14 plugin entries) |
| `/proc/sys/kernel/random/boot_id` (live) | Read; format verified |
| `tests/test_skill_descriptions.py` (on-disk) | Read in full |

**Missing evidence:** None blocking. The `denubis-crash-recovery` plugin directory does not yet exist on disk (work has not begun); this is expected — the plan precedes implementation. The Phase 1B and Phase 2B investigator reports cited by phase files are not co-located with the implementation plan; I cannot verify the claim "three real JSONLs sampled" in Phase 2's "Codebase verified" line. I treat that claim as unverified-research-output but not load-bearing.

**Provenance note:** the prior plan-validation reviewer's two cycles concluded APPROVED. That verdict is from a structural checklist agent, not a falsification pass; I do not adopt it. I will mark below where my findings overlap with prior I1–I4/M1–M3 and where they go further.

---

## Hidden Assumptions (ABP step 3)

Load-bearing assumptions extracted from across the eight phases + design plan. Each is marked **L** (load-bearing — conclusion fails if wrong) or **N** (non-critical).

| # | Assumption | Load? | Evidence in plan? | Signposts of breakdown |
|---|---|---|---|---|
| H1 | The classification rule table's `RULES` tuple in Phase 2 Task 4 *partitions* the input space (every realistic `(TailKind, liveness_present, pid_alive, boot_id_current)` quadruple matches exactly one row). | **L** | Asserted by the comment block above `RULES`; Task 5 asserts every row matches its fixture; defensive fallback is tested as supposedly-unreachable. Partition exhaustiveness is **not** proved against the full cartesian product of input states. | A real session lands in `borderline / unmatched` (the defensive fallback). |
| H2 | `boot_id_current` on every liveness-bearing `SessionFact` is computed by comparing `Liveness.boot_id` against `current_boot_id()` at scan time. | **L** | Comment on `SessionFact.boot_id_current` field (Phase 4 Task 1 line 88) names the rule. The walk-strategy bullet list (lines 92–97) **does not show the call site**. No code-level pseudocode wires it. | All live sessions silently classify as `hard_crash / liveness_boot_id_mismatch` (or worse: fail to classify as `live` per AC6.2 even when the rule table would). |
| H3 | The wrapper's `$*` records argv as a single space-joined string that matches Phase 3's `_extract_resume_uuid` parser. | **L** | Phase 8 Task 1 Block A line 61 hardcodes `printf 'argv=%s\n' "$*"`. The wrapper's current code uses `"$@"` (verified on disk, line 89). Phase 3 Task 4 uses `shlex.split(argv)` which handles either form. | Argv strings with embedded spaces or quotes parse to the wrong UUID and AC6.1's direct-match path silently degrades to mtime fallback. |
| H4 | The `~/.claude/run/<pid>.live` file write is atomic on the filesystems users will actually have. POSIX `rename(2)` semantics are claimed (Phase 8 Task 1, line 74). | **L** | Plan says "Linux-only by design" (Phase 8 Task 3 CHANGELOG; design plan DR7). The plan does **not** address whether NFS / FUSE / overlayfs / tmpfs / encrypted home directories provide atomic rename. `~/.claude/run/` is in `$HOME`, which can be remote-mounted. | Half-written `.live` files; `read_liveness` raises `ValueError` on missing keys and gets swallowed by `warnings.warn` in `list_liveness_files` — silently dropping a real casualty. |
| H5 | The wrapper's `EXIT_CODE=$?` (line 90, on disk) captures Claude's exit status before any subsequent command can clobber it. | **L** | Verified on disk. But the wrapper has *additional* code between line 90 and `exit $EXIT_CODE` (line 121): the post-session transcript-archival block (lines 92–119) including a `read -r` that waits for user input. Phase 8 Task 1 says "insert immediately AFTER `EXIT_CODE=$?` at line 90" — this places the rm-liveness logic **before** the long-running transcript-archive prompt. While the user is staring at "Press Enter to archive transcript", the liveness file has already been removed; if a clean session is `kill -9`'d during the archive prompt, the file is *already gone* and the wrapper-PID-was-killed signal is lost. | A `kill -9` of a wrapper waiting at the transcript prompt leaves no liveness file, AC5.3 false-negative. |
| H6 | The `_orphan_sweep` correctly re-classifies stale rows whose JSONLs vanish. | **L** | Phase 4 Task 3 specifies the algorithm. But the sweep does NOT distinguish "JSONL was once present and is now gone" from "JSONL was never on disk". An audit reader can't tell from the row alone whether prune's three-condition guard should fire. | A row that was classified `concluded` before its JSONL was deleted gets re-classified to `irrecoverable / missing_jsonl_on_disk` and then can never be pruned (it no longer matches `classification = 'concluded'`). The plan does not flag this as a deliberate choice. |
| H7 | Two concurrent scans cannot produce duplicate `classification_history` rows. | **L** | Phase 4 Task 2 says `_append_history` "primary key is `(uuid, scan_id)`, so re-running with the same scan_id raises". But two concurrent scans each get a distinct `scan_id` (autoincrement) — they would write disjoint history rows, not duplicates. The actual hazard is two scans assigning *the same `last_scanned`* to a row, plus one history row per scan; the concurrent test (`test_scan_two_concurrent_invocations_do_not_corrupt_db`) asserts `1 or 2` scan_runs rows — both are accepted. So if both scans complete, you have two history rows per session per run. Is that the desired audit behaviour? Plan never says. | Audit history doubles under concurrency. Probably harmless; unconfirmed. |
| H8 | The triage skill body invokes the CLI at a hardcoded absolute path that resolves on the user's machine. | **L** | Phase 7 Task 1 hardcodes `uv run --project ~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery triage`. The path embeds `marketplaces/denubis-plugins/` — this is the *marketplace's* fork path, not a generic "denubis-plugins marketplace alias". Whether this resolves depends on how the user added the marketplace. | Skill fails on first invocation; user reports "command not found" or "no such directory". Plan claims this "matches workflow_statusline" — I did not verify workflow_statusline's invocation path. |
| H9 | The Phase 1 widening of `testpaths` to `["tests", "plugins/*/scripts/*/tests"]` is safe because `workflow_statusline` tests "start running as a side-effect — acceptable". | **L** | Phase 1 Task 3 Step 2 calls this "acceptable" without verifying it. I verified the workflow_statusline tests exist (8 files including 18.8K test_main.py). The plan does not run them first to confirm they pass under the wider pytest collection. They depend on `uv sync` for the workflow_statusline package; the root `uv run pytest` may or may not find that package's deps. **This is one of the seeded probes (#5).** | First repo-root `pytest -q` post-Phase-1 fails because workflow_statusline tests can't import their dependencies. |
| H10 | The classifier version bump path is forward-compatible because `CLASSIFIER_VERSION = 1` and rows are stamped on every upsert. | N | Phase 2 sets `CLASSIFIER_VERSION = 1`; Phase 4 writes it on every upsert; orphan sweep also stamps it. AC3.6 test seeds a row at `CLASSIFIER_VERSION - 1` (i.e., 0). But there is no migration path documented for v0 → v1 if v0 used a different `RULES` shape. (For first release this is fine.) | A future v2 bump without rule-table archive means historical classifications can't be reproduced. |
| H11 | The `boot_id=unknown` fallback (Phase 8 Block A line 62) on non-Linux + Phase 3's `current_boot_id()` failing the same way → both endpoints return `"unknown"` and MATCH trivially. | **L** | Phase 8 says "On non-Linux hosts the `cat` would fail, and we'd write `boot_id=unknown`. Phase 3's `current_boot_id()` would never match, so the session would always classify as boot-mismatch — but this is the Linux-only path." This is **factually wrong** about Phase 3. Phase 3 Task 1's `current_boot_id()` does `Path("/proc/sys/kernel/random/boot_id").read_text().strip().lower()` with no try/except — on non-Linux this raises `FileNotFoundError`, not returns `"unknown"`. So **the Phase 8 comment is wrong about Phase 3 behaviour**, but the Phase 8 fallback path itself is correct-by-accident: `current_boot_id()` raising would crash `scan` before any classification happens. **This is one of the seeded probes (#6).** | On non-Linux, `crash-recovery scan` crashes with FileNotFoundError on the first call to `current_boot_id()`. Plan claims "the plugin runs on non-Linux but classifies all sessions as boot-mismatched" (Phase 8 Task 4 CHANGELOG, line 376) — this is **false**: scan crashes. |
| H12 | The `classification_history` table has no FK to `sessions`, so prune's row deletion leaves history rows orphaned by design. | **L** (decision-level) | Phase 1 schema has no FK constraint; Phase 6 `prune.delete_candidates` deletes from `sessions` only; history rows persist. The plan never states whether this is intentional (audit trail) or oversight. **This is one of the seeded probes (#7).** | `history <uuid>` returns rows for a UUID that no longer exists in `sessions`; downstream tooling (e.g., a future "show all history" report) sees ghosts. |

---

## ACH Matrix

Competing hypotheses about the most consequential single risk in the plan.

**H_A:** The plan's biggest risk is *citation drift* — DR labels and AC mappings have rotted; functional content is correct.
**H_B:** The plan's biggest risk is *unspecified mechanism* — load-bearing computations (`boot_id_current`, atomicity scope, the orphan-sweep semantics) are *named* in prose but never wired in pseudocode; an implementer following only the code blocks will silently misimplement.
**H_C:** The plan's biggest risk is *unverified empirical claims* — "atomic rename", "Linux-only", "concurrent scans safe under WAL" are stated without independent verification or signposts of breakdown.
**H_D:** The plan is essentially fine; remaining issues are cosmetic and the executor can fill in the gaps.

| Evidence | H_A | H_B | H_C | H_D |
|---|---|---|---|---|
| Phase 7 cites "DR3 in Phase 6" — DR does not exist in Phase 6 (verified) | + | ? | − | − |
| Phase 8 bats tests labelled "DR2/DR3" with semantics unrelated to design DR2/DR3 (verified) | + | ? | − | − |
| `SessionFact.boot_id_current` defaults False; walk strategy never shows compute site (verified by reading phase_04.md lines 88–97) | ? | **+** | ? | − |
| Phase 8 prose claim about non-Linux behaviour is factually wrong about Phase 3 code (verified by reading phase_03.md line 83 vs phase_08.md line 75) | ? | **+** | **+** | − |
| Phase 8 CHANGELOG claim "plugin runs on non-Linux" is false (current_boot_id crashes) | − | + | **+** | − |
| Atomic-rename claim made without addressing NFS/FUSE/overlayfs (Phase 8 Task 1 line 74) | − | − | **+** | − |
| Phase 1 testpaths widening "acceptable" without running workflow_statusline tests first | − | + | + | − |
| Wrapper patch insertion point (line 90) places rm-logic before transcript-archive prompt | − | **+** | + | − |
| Phase 4 walk strategy doesn't enumerate where `current_boot_id()` is called | − | **+** | − | − |
| Plan covers all 34 ACs with at least proxy tests | ? | ? | ? | + |
| Defensive fallback in `classify()` is tested but plan says it's "unreachable" — partition is asserted not proved | − | + | + | − |
| Phase 6 has no DRs but Phase 7 cites one | + | ? | − | − |
| Phase 4 imports `TailSummary, TailKind` only in test file (line 260), not in scan.py spec | ? | + | − | − |

**Score (count of `+`, treating `?` and `−` as zero):** H_A=3, H_B=8, H_C=7, H_D=1.

**Decision rule (the hypothesis requiring the fewest contradictions survives; a single strong `−` outweighs many weak `+`):** H_B wins. Several pieces of evidence fit H_C as well as H_B; both should be reported. H_A is real but lower-stakes (citations don't break code). H_D is contradicted by ≥3 strong negatives.

**Strongest hypothesis:** H_B — unspecified mechanism. An implementer who reads only the code-block pseudocode and skims the prose will write `scan.py` with `boot_id_current=False` for every live liveness fact, breaking AC5.6 and AC6.2 in production despite the synthetic test passing.

**Weakest hypothesis:** H_D. The "remaining issues are cosmetic" framing collapses on contact with H_B and H_C evidence.

---

## Findings

### High (count: 5)

#### High-1: `boot_id_current` is never wired in the walk-strategy code block; AC5.6 and AC6.2 are at risk

- **Location:** `phase_04.md` Task 1, lines 88–97 (SessionFact field + walk strategy bullets).
- **Issue:** The `SessionFact.boot_id_current` field has a default value of `False` and a prose comment "True iff liveness.boot_id == current_boot_id()". The bullet list describing the walk (`DIRECT_MATCH`/`MTIME_MATCH`/`AMBIGUOUS`/`NO_MATCH` cases at lines 93–96) never shows the `current_boot_id()` call site or the `boot_id == current_bid` comparison. The plan also does not specify caching `current_boot_id()` once per scan (the file is cheap to read but reading it N times under load is wasteful). An implementer who follows the code blocks will leave `boot_id_current=False` for every liveness-bearing fact.
- **Evidence:** `phase_04.md:88` ("`boot_id_current: bool = False`"); `phase_04.md:97` (the only place the walk explicitly sets it: `boot_id_current=False` for JSONL-only facts); no other explicit `boot_id_current=True` assignment in the file.
- **GRADE factors:** Indirectness — the wire-up logic is asserted but not demonstrated in the spec. Imprecision — single fail mode covers multiple ACs.
- **Ripple:** AC5.6 test (`test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive`) passes by *accident* — it uses a boot_id `00000000-…` that is never equal to current, so the `boot_id_current=False` default produces the right answer regardless of the missing computation. AC6.2 test (`test_scan_classifies_live_pid_as_live`) supplies a "fresh boot_id matching current" but would silently route through `boot_id_current=False` if the implementer follows the bullets — the test would then *fail* and surface the bug. This means the test catches it but only because the test predicates on the *missing* wiring being present. The plan does not name this dependency.
- **Corrected language:** Add a numbered step to the walk strategy at `phase_04.md:92`: "Read `current_boot_id()` once at scan start (cache as local variable). For each `Liveness` record where `correlate` returned `DIRECT_MATCH` or `MTIME_MATCH`, set `boot_id_current = (liveness.boot_id == cached_current_boot_id)` when constructing the `SessionFact`. For `AMBIGUOUS` candidates, set `boot_id_current` the same way (boot mismatch supersedes ambiguity)." Also add `pid_alive_value = pid_alive(liveness.pid)` to the same step — Phase 4 currently never shows where `pid_alive` is called either.
- **Severity:** High because two ACs depend on it; a checklist reviewer would not catch this because the synthetic test in AC5.6 happens to be a 00000000-shaped boot_id that satisfies the False default.

#### High-2: Phase 8's non-Linux claim is internally inconsistent and the CHANGELOG misrepresents behaviour

- **Location:** `phase_08.md:75` (prose: "Phase 3's `current_boot_id()` would never match, so the session would always classify as boot-mismatch"), `phase_08.md:310` (compatibility note: "On non-Linux hosts, the wrapper still works but writes `boot_id=unknown` — crash-recovery's classifier will treat all such sessions as boot-mismatched on the next scan"), `phase_08.md:376` ("The plugin runs on non-Linux but classifies all sessions as boot-mismatched").
- **Issue:** Phase 3 Task 1 (`phase_03.md:83`) defines `current_boot_id()` as `Path("/proc/sys/kernel/random/boot_id").read_text().strip().lower()` — no try/except, no fallback. On macOS/BSD/non-Linux the file does not exist and `read_text()` raises `FileNotFoundError`. The Phase 3 test at `phase_03.md:151` (`test_current_boot_id_returns_kernel_value`) asserts the file is readable. So on non-Linux:
  - The wrapper writes `boot_id=unknown` (Phase 8 Block A handles `cat` failure).
  - The scanner's first call to `current_boot_id()` **crashes** with `FileNotFoundError`.
- The plan's claim that the classifier "will treat all such sessions as boot-mismatched" is false. The classifier never gets to compare boot_ids because `current_boot_id()` raises.
- **Evidence:** Direct comparison of `phase_03.md:83` and `phase_08.md:75`/`310`/`376`.
- **GRADE factors:** Risk of bias (single source — Phase 8 prose describes Phase 3 behaviour from memory, not from reading Phase 3); Inconsistency (Phase 3 spec contradicts Phase 8 prose).
- **Ripple:** The CHANGELOG entry committed in Phase 8 Task 4 contains an untrue compatibility claim. Users running non-Linux will hit an unhandled exception on first `scan`. The Phase 7 README troubleshooting section (`phase_07.md:131`) does not list this failure mode.
- **Corrected language:** Either (a) make Phase 3's `current_boot_id()` defensive — wrap in try/except, return `"unknown"` on `OSError`, document the asymmetry that the wrapper writes `unknown` and the reader matches `unknown` (which means non-Linux sessions classify as `live_pid_present_boot_current` whenever PID is alive — a different failure mode worth surfacing); or (b) make `scan` fail-fast on non-Linux with a clear error; or (c) drop the non-Linux claim from the CHANGELOG entirely and gate `scan` on `sys.platform == "linux"`. The plan must pick one and the prose must match. Right now the plan endorses option (a) in three places and implements neither (a) nor (b) nor (c).
- **Severity:** High because (i) it lands an untrue claim in a public CHANGELOG, (ii) the symmetric `unknown == unknown` failure mode the user's seed probe #6 flagged is the *correct* alternative reading that the plan dismissed, (iii) prune's stale-version logic does not anticipate a scan that crashed before writing.

#### High-3: Wrapper patch insertion point puts rm-logic BEFORE the transcript-archive prompt — AC5.3 has a hole

- **Location:** `phase_08.md:79` ("Block B — Conditional cleanup (insert immediately AFTER `EXIT_CODE=$?` at line 90)"). Wrapper as currently on disk (verified, lines 89–121): line 89 invokes Claude; line 90 captures `EXIT_CODE`; lines 92–119 are the post-session transcript-archival block including `read -r` (line 106) that blocks waiting for user input; line 121 is `exit $EXIT_CODE`.
- **Issue:** Inserting `rm -f "$CR_LIVE_FILE"` immediately after line 90 means the liveness file is removed *before* the wrapper has finished. The wrapper then sits on `read -r` for an arbitrary amount of time (the user may walk away for minutes/hours). If the wrapper is `kill -9`'d during this prompt, AC5.3 ("`kill -9` of wrapper preserves liveness file") **fails** — the file was already removed.
- **Evidence:** Read of `claude-wrapper.sh` at HEAD. The `read -r` at line 106 is a clear blocking-IO point.
- **GRADE factors:** Risk of bias — Phase 8 was written without reading the full current wrapper. Indirectness — bats tests use a stub `claude` that exits immediately, never exercising the transcript-archive block, so the AC5.3 bats test passes despite the bug.
- **Ripple:** AC5.3 has bats coverage (`@test "AC5.3 — kill -9 of wrapper preserves the liveness file"`) but the bats test does not enable the transcript-archival prompt path (no `ai_transcripts` dir in the fixture; no `read -r` blocking). The AC6.4 UAT (`uat-requirements.md:42`) would surface this in real use — but only if the user's project is *not* a transcripting one (otherwise the rm happens before the kill). The UAT runbook doesn't specify which kind of project to run in.
- **Corrected language:** Move Block B to *immediately before* `exit $EXIT_CODE` (line 121). Re-derive `CR_LIVE_FILE` from `$$` if the variable scope is lost (it isn't — `set -euo pipefail` plus the bash variable model keeps it). Alternatively (better): keep Block B near `EXIT_CODE=$?` for locality but document explicitly that the transcript-archive prompt path means a `kill -9` during the prompt does not produce a casualty record — and add a bats test for this path or call it out as a known limitation.
- **Severity:** High because (i) it's a genuine AC5.3 false-negative under a normal user flow (transcripting projects are a stated feature), (ii) it would not be caught by any automated test in the plan, (iii) the prior reviewer did not flag this — they did not read the on-disk wrapper.

#### High-4: Phase 8 bats labels "DR2" / "DR3" do not match design plan DR2 / DR3

- **Location:** `phase_08.md:244` (`@test "DR3 — user-supplied argv is recorded verbatim"`), `phase_08.md:259` (`@test "DR2 — liveness file appears atomically (no .tmp file at target path)"`).
- **Issue:** Design plan DR2 (verified `design-plans/2026-05-08-crash-recovery.md:205`) is "PID-keyed liveness files, UUID resolved post-hoc" — not atomicity. Design plan DR3 (verified line 220) is "Patch denubis-plan-and-execute's wrapper directly" — not argv recording. The bats labels appear to be invented for the tests. Phase 7 also cites "DR3 in Phase 6" (`phase_07.md:132`) — Phase 6 contains zero `### DR` headings (verified by grep).
- **Evidence:** Direct comparison of `design-plans/2026-05-08-crash-recovery.md` (DR1 line 189 through DR9 line 311) versus Phase 7 and Phase 8 citations.
- **GRADE factors:** Indirectness — citations to DRs that don't exist; Reporting bias — every Phase-8 design choice has a DR-flavoured justification slapped on it, regardless of whether a corresponding DR exists.
- **Ripple:** Bats test failure messages refer to "DR2" / "DR3" — a developer debugging a failure will look in Phase 6 (Phase 7 says so) or the design plan and find no matching decision record. This is documentation rot baked into test output, which is worse than rot in prose.
- **Corrected language:** Either (a) rename the bats tests to drop the DR label and describe what they actually test (e.g. `@test "wrapper writes argv verbatim from user invocation"`); or (b) cite the actual DR — DR2 ("PID-keyed liveness files") doesn't say anything about atomicity, so option (a) is what's available. Same for the Phase 7 "DR3 in Phase 6" claim — there's no DR3 in Phase 6; that should be rewritten to describe the design choice directly.
- **Severity:** High because the rot is in test names (visible in CI output) and in user-facing README (Phase 7's troubleshooting section).

#### High-5: Partition exhaustiveness of `RULES` is asserted, not proven; the defensive fallback is described as both "unreachable" and "tested"

- **Location:** `phase_02.md:312–318` (defensive fallback + comment "The rule table is intended to be exhaustive; the fallback only fires if the table is misconfigured"); `phase_05.md:74` (`"unmatched"` is in `JSONL_ONLY_REASONS` set); `phase_05.md:506` (test_reason_prefix_partition_is_exhaustive); `phase_02.md:372` (`test_defensive_fallback_returns_borderline_unmatched` — "synthesise an input combination not covered by any rule").
- **Issue:** "Unreachable but tested" is incoherent unless the test deliberately constructs an *impossible* state. Phase 2 Task 5 says exactly that: "this requires temporarily constructing an impossible state, e.g., `LivenessState(present=False, boot_id_current=False)` paired with `pid_alive=True`". But the example given is *not* impossible — a session walk could absolutely produce `present=False, boot_id_current=False, pid_alive=True` if someone wired `pid_alive_value` wrong upstream. The test is checking that *if* the rule table misclassifies, the fallback fires. It does NOT prove the rule table partitions the realistic input space. **This is one of the seeded probes (#2).**
- **Evidence:** Direct read of `phase_02.md` Task 4 RULES enumeration. Counting cases by hand:
  - 14 rules. Inputs are `(TailKind ∈ 8 values, liveness_present ∈ {T,F}, pid_alive ∈ {T,F,None}, boot_id_current ∈ {T,F})` = 8 × 2 × 3 × 2 = 96 combinations.
  - Several rules use wildcards (`None` matchers). The first-match ordering means later rules are reached only for unmatched inputs.
  - The plan does NOT provide a proof or test that the 96-cell cartesian product is fully covered.
- **GRADE factors:** Imprecision — no enumeration test; Indirectness — coverage claim rests on hand-eye reading of the RULES table.
- **Ripple:** A realistic case that lands in `unmatched`: `liveness_present=False, pid_alive=None, boot_id_current=False, trailing_kind=CONCLUDED`. Walking the rule table: irrecoverable_missing_jsonl (no — CONCLUDED), borderline_malformed_tail (no), borderline_empty_file (no), hard_crash_boot_mismatch (no — liveness_present is False), live_pid_present (no — liveness_present is False), hard_crash_tool_use through hard_crash_dead_pid_unknown_tail (no — liveness_present is False)… **concluded_no_liveness_clean_tail matches.** OK, that case is fine.
  - Try: `liveness_present=True, pid_alive=None (irrelevant — liveness present means pid_alive should be set), boot_id_current=True, trailing_kind=CONCLUDED`. This is "liveness file exists, boot current, but `pid_alive` is None"… can this happen? Per Phase 4 Task 1: "`pid_alive_value: bool | None # result of pid_alive(liveness.pid); None when liveness is None`". So liveness present ⇒ pid_alive_value is bool, never None. OK partition holds here.
  - Try: `liveness_present=True, pid_alive=True, boot_id_current=False, trailing_kind=CONCLUDED`. Walk: hard_crash_boot_mismatch matches (boot_id_current=False). OK.
  - Try: `liveness_present=True, pid_alive=False, boot_id_current=True, trailing_kind=CONCLUDED`. Walk: no rule for `pid_alive=False + trailing=CONCLUDED` — only TOOL_USE_NO_RESULT, ASK_QUESTION_NO_REPLY, AGENT_DISPATCH_NO_RESULT, UNKNOWN have explicit rows. **`borderline_unknown_tail` catches it** because that rule has `trailing_kind=UNKNOWN`, and the actual trailing_kind is CONCLUDED, NOT UNKNOWN — so this rule doesn't match either. **This input lands in `unmatched` (the defensive fallback).** The session is a concluded session whose wrapper is somehow still recording-but-dead (PID dead, boot still current). Maybe rare but not impossible (race between kill and scan).
- **Corrected language:** Add a test `test_rules_table_partitions_cartesian_product` that enumerates the 96 (or however many *realistic*) combinations and asserts each matches exactly one rule before the defensive fallback. Where a combination is genuinely impossible (e.g. liveness_present=True + pid_alive=None), the test should assert that explicitly so the partition argument is documented. The existing `test_defensive_fallback_returns_borderline_unmatched` is fine for what it tests but the plan should not call the fallback "unreachable" — it's reachable for the (concluded + liveness_present + pid_dead + boot_current) case at minimum.
- **Severity:** High because the defensive fallback emits `borderline / unmatched` which lands in `JSONL_ONLY_REASONS`'s "session data is incomplete or corrupted" warning category — a real session that hit this case would be shown to the user with a misleading message.

### Medium (count: 6)

#### Medium-1: Atomicity claim made without scoping to filesystem

- **Location:** `phase_08.md:74` ("`mv` is atomic (POSIX `rename(2)` semantics) — Phase 3's parser never sees a half-written file (DR2)").
- **Issue:** POSIX `rename(2)` is atomic *on the same filesystem*. Across filesystems (e.g. `/tmp` to `$HOME` when `/tmp` is tmpfs and `$HOME` is encrypted ext4) it falls back to copy+unlink which is *not* atomic. The plan writes both `.tmp` and `.live` to the same dir (`$CR_RUN_DIR`), so within-FS atomicity *should* hold — but if `$HOME` is on NFS, FUSE, or overlayfs (common in containerised setups), the atomicity contract weakens or breaks. The plan says "Linux-only by design" but `Linux + arbitrary filesystem` is not the same as `Linux + ext4`. **This is one of the seeded probes (#4).**
- **Evidence:** Direct read; no filesystem-scoping mention in Phase 8 or design DR7.
- **GRADE factors:** Imprecision — empirical claim with implicit unstated scope.
- **Ripple:** Phase 3's `list_liveness_files` swallows `ValueError` from malformed files via `warnings.warn`. A half-written file (NFS write+rename race) silently disappears from the scan. AC5.3 false-negative under NFS home.
- **Corrected language:** Add to Phase 8 Block A invariants: "Atomicity assumes `$CR_RUN_DIR` is on a POSIX-compliant local filesystem (ext4, btrfs, xfs, zfs, tmpfs). Behaviour on NFS, FUSE, overlayfs, or other network/union filesystems is not specified; users with non-local homes should set `CRASH_RECOVERY_RUN_DIR` to a local path."
- **Severity:** Medium — affects a real but minority population; documented mitigation exists (env var override).

#### Medium-2: `$@` vs `$*` argv recording

- **Location:** `phase_08.md:61` (`printf 'argv=%s\n' "$*"`), `phase_08.md:73` ("`$*` (not `$@`) records the user's argv as a single space-joined string"). Wrapper on disk uses `$@` (line 89, verified).
- **Issue:** `$*` joins with IFS (default space). `$@` expands to separate words. For `printf '%s\n' "$*"` they're equivalent in output; the *meaningful* difference is in `for arg in "$@"` (line 57 of wrapper — verified) versus what is printed. The plan's choice of `$*` for `printf` is fine. But the rationale "matches Phase 3's `_extract_resume_uuid` expectation" is wrong — Phase 3 Task 4 uses `shlex.split(argv)` which handles either form. So the rationale is post-hoc justification.
- **Evidence:** Direct read of both files.
- **GRADE factors:** None — this is reasoning-quality not factual.
- **Ripple:** None functional. The rationale is just wrong.
- **Corrected language:** Drop the rationale or replace with "Either `$*` or `$@` works inside double-quoted `printf %s`; `$*` is chosen for explicit single-string semantics."
- **Severity:** Medium because the wrong rationale appears in test annotations too (the bats `DR3` test name).

#### Medium-3: Foreign-key cleanup in prune is undecided

- **Location:** Phase 1 schema (`phase_01.md:347` — `classification_history` has no FK declared); Phase 6 prune (`phase_06.md:339` — `DELETE FROM sessions WHERE uuid IN (…)` only). **This is one of the seeded probes (#7).**
- **Issue:** Prune deletes from `sessions` and leaves `classification_history` rows with `uuid` values that no longer exist in `sessions`. The plan never says whether this is intentional (audit trail across prune) or an oversight. The schema sets `PRAGMA foreign_keys = ON` in init but declares no FK — so there's no enforcement either way.
- **Evidence:** Direct read.
- **GRADE factors:** Reporting bias — the plan asserts forward-compatibility via classifier_version but does not address audit-trail-after-prune.
- **Ripple:** `crash-recovery history <uuid>` returns rows for a deleted session UUID. The `fetch_history` query joins `classification_history` to `scan_runs` — the join succeeds; the deleted session's history is shown without any context that the session no longer exists.
- **Corrected language:** Decide explicitly. Two coherent options: (a) intentional audit-trail preservation — say so in Phase 6 prune docs, add a test that asserts `classification_history` rows persist after `prune --confirm`, surface "(session no longer in DB)" in `history <uuid>` output; or (b) cascade delete — add FK constraint with `ON DELETE CASCADE` to Phase 1 schema, update orphan-sweep to also tolerate deleted history rows. Either is fine; silence is not.
- **Severity:** Medium because correctness is unclear without a decision, and the choice affects what `history` shows.

#### Medium-4: Phase 1 widening of testpaths is "acceptable" without verification

> **SUPERSEDED — see commit `56bd7cd` (2026-05-15).**
> The M4 → 4b decision (recorded in this session's RESUME.md) called for reversing the testpaths widening and documenting a per-plugin invocation: `uv run --project <plugin> pytest -q` run from the worktree root. Empirically, that invocation does NOT collect the plugin's tests — pytest walks up from `cwd` and finds the worktree's `pyproject.toml` first; `--project` only scopes uv's dependency resolution, not pytest's rootdir detection. The workflow_statusline precedent the decision rested on had the same behaviour. The current resolution is a uv workspace + the `collect_ignore_glob` removal, which lets a single `uv run pytest -q` from the worktree root collect 615 tests (457 root + 140 workflow_statusline + 18 crash_recovery). Per-plugin iteration still works via `cd <plugin-path> && uv run pytest`. The finding itself remains useful as a record of why the surface-level "widen testpaths" change was unsafe; the workspace addresses the underlying concern properly.

- **Location:** `phase_01.md:266` ("Side effect: `workflow_statusline` tests are now also collected by the root pytest invocation."). **This is one of the seeded probes (#5).**
- **Issue:** Phase 1 widens `testpaths` to `["tests", "plugins/*/scripts/*/tests"]` without first running the workflow_statusline test suite at the repo root to confirm it passes under the wider collection. workflow_statusline's `pyproject.toml` declares its own deps (`pytest>=8.0` in dev group); the root `uv run pytest -q` may not install those deps unless explicitly synced. The plan asserts the widening is "acceptable" — a load-bearing claim with no test.
- **Evidence:** `workflow_statusline/pyproject.toml` and `workflow_statusline/tests/` exist; the root `pyproject.toml` does not list workflow_statusline as a workspace member. `uv run pytest` at root may collect but fail to import.
- **GRADE factors:** Imprecision — empirical claim without verification.
- **Ripple:** First `uv run pytest -q` post-Phase-1 commit could fail, blocking the rest of Phase 1's done-when. Phase 1 Step 4 (line 503) asserts "Expected: the count increases by the number of tests added in this task; pre-existing tests still pass" — this would fail.
- **Corrected language:** Before adopting the widening, run `uv run pytest plugins/denubis-plan-and-execute/scripts/workflow_statusline/tests/ -q` and confirm green. If the workflow_statusline tests need a `uv sync --project` at the package level first, document this in Phase 1 Step 2.
- **Severity:** Medium — Phase 1 is foundational; a broken testpaths widening delays everything.

#### Medium-5: Phase 1 cites "DR2" in repo-root context that doesn't have a DR2

- **Location:** `phase_01.md:249` ("This is the change the design plan and DR2 authorised").
- **Issue:** Design plan DR2 is "PID-keyed liveness files". It does not authorise the testpaths widening. The widening is mentioned in design plan "Existing Patterns" section (line 336) but not labelled as a DR. The phase file's citation is mis-labelled.
- **Evidence:** `grep -n "^### DR" docs/design-plans/2026-05-08-crash-recovery.md` shows DR2 = "PID-keyed liveness files, UUID resolved post-hoc" (line 205). The testpaths widening is in the "Existing Patterns" prose section, line 336.
- **GRADE factors:** Reporting bias — DR citations are sprinkled to confer authority on routine decisions.
- **Ripple:** Same pattern as High-4 but lower-impact — Phase 1 only.
- **Corrected language:** "This is the change the design plan's Existing Patterns section authorises".
- **Severity:** Medium because it sets a tone that DR labels are decorative, which compounds High-4.

#### Medium-6: Concurrent-scan test is "1 or 2 scan_runs rows; both valid"

- **Location:** `phase_04.md:484` (`test_scan_two_concurrent_invocations_do_not_corrupt_db`). Specifically the assertion at line 487: "Either one `scan_runs` row (one scan won the race and ran the orphan sweep; the other saw nothing new) or two `scan_runs` rows (both scans completed in sequence) — both outcomes are valid; the assertion is that the count is `1` or `2`, never `0` or `>2`."
- **Issue:** The "1 row" branch is described as "one scan won the race and ran the orphan sweep; the other saw nothing new". But both scans are independent processes both holding their own `with conn:` transaction — they don't share orchestration state. Each scan writes its own `scan_runs` row at the start of its transaction. SQLite WAL serializes the writes; both transactions will commit eventually and produce *two* rows. The "1 row" outcome would only occur if one scan failed and rolled back, which is not described as a valid outcome. The plan accepts an outcome that the design's concurrency model does not actually produce. **This is one of the seeded probes (#8) related.**
- **Evidence:** Direct read. `_write_scan_run` in `phase_04.md:243` is called unconditionally from `run_scan` (line 164). There is no "skip if another scan is in progress" logic.
- **GRADE factors:** Inconsistency — the design's concurrency model does not match the test's accepted outcomes.
- **Ripple:** The test passes under both outcomes, but if only `1 row` ever appears in practice, that signals a bug (one scan crashed silently); the test will not flag it.
- **Corrected language:** Either (a) tighten the assertion to `== 2` and document that both scans produce a `scan_runs` row by design; or (b) explain when "1 row" is a valid outcome with a specific failure mode that the test would distinguish from the bug case.
- **Severity:** Medium — the test as specified is not falsifiable in the direction that matters.

### Low (count: 5)

- **Low-1:** `phase_07.md:132` "no audit trail in v0.1.0 by design (DR3 in Phase 6)" — Phase 6 has no Decision Records. Same citation rot as High-4. Lower severity because the prose still communicates intent. Fix: rewrite as "no audit trail in v0.1.0 by design (the prune flow does not log deletions)".
- **Low-2:** `phase_04.md:132–144` (the ambiguous-correlation pseudocode) uses `TailKind.UNKNOWN`, `TailSummary`, `CorrelationKind.AMBIGUOUS` but the spec's import block (lines 104–105) only imports `classify`, `Classification`, `ClassificationValue`, `LivenessState`. An implementer must derive the additional imports. Low because the imports are obvious; but the prior reviewer's I3 fix was *exactly* about avoiding implicit imports — same hazard partially returned. Fix: extend the import block to include `from crash_recovery.jsonl import TailSummary, TailKind` and `from crash_recovery.correlate import CorrelationKind`.
- **Low-3:** `phase_08.md:533–535` "Phase 8 Done When" lists "bats lifecycle tests pass for all 10 cases (AC5.1 four-key check, AC5.2 × 2 clean-exit paths, AC5.3 wrapper-SIGKILL, AC5.4 × concurrent, AC5.5 × 3 abnormal exits, DR3 argv recording, DR2 atomic write)". Counting: 1 (AC5.1) + 2 (AC5.2) + 1 (AC5.3) + 1 (AC5.4) + 3 (AC5.5) + 1 (DR3) + 1 (DR2) = **10**. The count is correct, but the DR-labelled tests (10 of 10) again reify the High-4 problem at the level of the done-when count. Fix paired with High-4.
- **Low-4:** `phase_07.md:11` "Phase 1B investigator report — crash-recovery design plan rename committed in 8c10b95". I did not verify commit `8c10b95` exists in the worktree. This is a citation that could be checked but is non-load-bearing — the rename has clearly been done (the directory is named `denubis-crash-recovery`).
- **Low-5:** The plan claims Python 3.12+; multiple phases use `StrEnum` (Python 3.11+, `enum.StrEnum`) and `from __future__ import annotations`. Plan is consistent. Low because it's correct; flagging here only because the prior reviewer's "Specific Consistency Check" (line 129) listed it without checking the 3.13 / 3.14-only features the plan would also need to avoid (e.g. `type X = int` PEP 695 syntax). I verified no such syntax appears in the plan. The prior check was incomplete but not wrong.

---

## Verification (what I checked independently)

| Check | Command | Result |
|---|---|---|
| Wrapper structure on disk | `Read /home/brian/.../claude-wrapper.sh` | Lines 89–121 as quoted in this review |
| Plan-and-execute version | `cat /home/brian/.../plan-and-execute/.claude-plugin/plugin.json` | `2.32.1` confirmed |
| Marketplace plugin count | `python3 -c 'json.load…'` | 14 plugins; plan-and-execute keys = `{author, description, license, name, source, version}` |
| boot_id format | `wc -c /proc/sys/kernel/random/boot_id; cat` | 37 bytes (UUID + newline); `len(strip) == 36` matches plan |
| Design plan DR1–DR9 | `grep -n "^### DR" design-plans/2026-05-08-crash-recovery.md` | 9 DRs confirmed |
| Phase 6 has no DRs | `grep -n "^### DR\|^## DR\|DR1\|DR2\|DR3" phase_06.md` | No matches (verified) |
| Phase 7 cites "DR3 in Phase 6" | `grep -n "DR3" phase_07.md` | `phase_07.md:132` (citation rot confirmed) |
| Phase 8 bats DR labels | `grep -n "DR" phase_08.md` | Lines 244, 259 use DR2/DR3 with unrelated semantics |
| Phase 4 `boot_id_current` wiring | Read `phase_04.md:88–146` | No call-site shown for the comparison; only the field declaration with default False |
| Phase 3 `current_boot_id()` | Read `phase_03.md:83` | No try/except; will raise FileNotFoundError on non-Linux |
| Phase 8 "non-Linux runs" claim | Cross-read `phase_03.md` vs `phase_08.md:75/310/376` | Phase 8 prose contradicts Phase 3 code |
| testpaths widening side-effect | Read `phase_01.md:264–266` | "Acceptable" assertion without test |
| Lakatosian/PROGRESSIVE/Haraway framing | `grep -n "PROGRESSIVE\|Lakatosian\|Haraway\|problem-shift" phase_*.md` | **0 matches** — the user's seed probe #3 was based on a misremembered or stale concern; no such framing exists in the current plan |

**The user's seed probe #3 (Lakatosian framing) is not a finding.** I checked and the framing isn't in the plan. Probe is closed.

**The user's seed probe #1 (UAT-vs-CI overclaim risk for AC5.6/AC6.4):** the AC mapping is internally consistent. `test-requirements.md` correctly marks AC5.6 as MIXED (automated rule wiring + human-judged reboot) and AC6.4 as HUMAN_JUDGEMENT. Phase 4's `test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive` is explicitly the rule-wiring test, not the reboot test. I find no overclaim that the CI test substitutes for the UAT. Probe is closed.

**The user's seed probe #2 (defensive fallback unreachable):** is a real finding — see High-5 above.

**The user's seed probe #4 (NFS/FUSE atomicity):** is a real finding — see Medium-1.

**The user's seed probe #5 (testpaths widening):** is a real finding — see Medium-4.

**The user's seed probe #6 (boot_id=unknown symmetry):** is a real finding, escalated — see High-2. The plan is *more* wrong than the probe suggests: it's not just that the asymmetry trivially matches; Phase 3's reader will *crash* on non-Linux before getting to compare.

**The user's seed probe #7 (FK cleanup in prune):** is a real finding — see Medium-3.

**The user's seed probe #8 (phase-boundary independence):** partially a finding. Phase 7's bats smoke does depend on Phases 4/5/6 CLI subcommands existing (the smoke test invokes `crash-recovery init`, `triage`, `regenerate`, `prune` — all from later phases). But Phase 7's own dependency declaration (`phase_07.md` "Dependencies: All prior phases") accurately states this. The plan does not claim phase-by-phase test independence; it claims phase-by-phase implementability with cumulative testing. Probe is partially closed; no separate finding.

---

## Strongest Hypothesis (most-supported finding)

**High-1: `boot_id_current` is never wired in the walk-strategy code block.**

Reasoning: this is the single finding most likely to produce a silent in-production failure that the plan's own test suite would catch only by accident. The synthetic AC5.6 test uses a boot_id of all-zeros that satisfies the `False` default, so it passes whether or not the wiring is present. The AC6.2 test would fail and surface the bug — but only after Phase 4 is implemented and run. The plan does not name this dependency; an executor's coherence-review pass on Phase 4 alone, reading the bullets, would miss it.

ACH support: 5 of the 13 evidence rows in the matrix specifically support H_B (unspecified mechanism), with this finding the cleanest exemplar.

---

## Weakest Hypothesis (least-supported claim, or speculation worth flagging)

**Speculation worth flagging:** the prior reviewer's APPROVED verdict implicitly assumes that the executor will perform a "full editing pass" on every change. The plan's revision-cycle evidence (the I1–I4 / M1–M3 list in `code-review-findings-plan-validation.md`) was a checklist of structural defects. None of those defects are about mechanism-as-specified-in-prose-but-not-in-code-blocks, which is the High-1 / High-3 pattern. The weakest hypothesis in this review is therefore "the prior reviewer's checks generalise to mechanism specification" — they don't. A different review modality (this one) was needed; the user's instinct to commission it was right.

---

## Pre-Mortem (Step 11)

Assume the plan ships as-is. What goes wrong?

1. **Phase 4 implementation passes all unit tests including AC5.6 and AC6.2 synthetic** because the implementer happens to wire `boot_id_current` correctly (most will — the prose is clear even if the code block isn't), OR because the synthetic tests' choice of boot_id values masks the bug. Real Phase 8 UAT after merge: a real reboot produces a session classified as `live` instead of `hard_crash`. User files a bug. Root cause: High-1 was not caught at plan time.

2. **A user with `$HOME` on NFS** reports that `crash-recovery scan` randomly misses sessions. Triage: half-written `.live` files swallowed by `list_liveness_files` via `warnings.warn`. Root cause: Medium-1 — atomicity assumption out of scope.

3. **A user on macOS** runs `crash-recovery scan` for the first time. Crash: `FileNotFoundError: /proc/sys/kernel/random/boot_id`. They consult the CHANGELOG: "On non-Linux hosts, the wrapper still works but writes `boot_id=unknown`". User confused. Root cause: High-2 — CHANGELOG misrepresents non-Linux behaviour.

4. **A user who runs Claude in a transcripting project** kills their session with `kill -9` during the "Press Enter to archive transcript" prompt. The session is then missed by `crash-recovery scan` (the wrapper had already removed the liveness file). Root cause: High-3 — rm-logic placed before the transcript prompt.

5. **A user reads the bats test failure** `AC5.5 — Claude exit 137 (SIGKILL) preserves the liveness file` and goes hunting for the design decision. They search the design plan for "DR3 — argv recording" (a separate bats label they saw earlier) and find DR3 = "Patch denubis-plan-and-execute's wrapper directly". They lose 20 minutes to confusion. Root cause: High-4 — DR labels recycled.

6. **A future v1.1.0 release** adds a new tail kind (e.g. `INTERRUPTED_DURING_AGENT_STREAMING`) to handle a newly-observed case. The new rule isn't added to RULES because nobody enumerated the cartesian product. A real session lands in `unmatched` and renders with the misleading "session data is incomplete or corrupted" warning. Root cause: High-5 — partition not proven.

The plan can ship without addressing every finding, but failures (3), (4), and (6) are user-visible and embarrassing.

---

## Fastest Next Test (Step 11)

**Single highest-yield test:** Run `uv run pytest plugins/denubis-plan-and-execute/scripts/workflow_statusline/tests/ -q` against the worktree *right now*, before any Phase 1 work begins. If those tests fail (or fail to collect under the wider testpaths discipline), Medium-4 is upgraded to High and Phase 1 needs revision. If they pass, Medium-4 is downgraded to Low. Cost: under 60 seconds; resolves the most foundational uncertainty in the plan.

**Second-highest-yield test:** Manually verify on macOS or a Linux container with `/proc` masked that `python3 -c "from pathlib import Path; print(Path('/proc/sys/kernel/random/boot_id').read_text())"` produces FileNotFoundError. Confirms High-2's mechanism is reproducible. Cost: ~3 minutes if a non-Linux box is at hand; skip if not.

---

## Overall Assessment

**Verdict: NEEDS_DISCUSSION.**

The plan is structurally complete — all 34 ACs have at least proxy coverage, the file paths are consistent, the schema is coherent, and the phase ordering is defensible. The prior reviewer's APPROVED verdict is reasonable as a structural check. **But the plan ships five High-severity issues that a structural checklist could not catch by construction:**

1. **High-1** (boot_id_current wiring) is a silent-failure landmine.
2. **High-2** (non-Linux behaviour claim) is a CHANGELOG falsehood that ships to users.
3. **High-3** (wrapper insertion point vs transcript prompt) is an AC5.3 hole under a normal user flow.
4. **High-4** (DR label rot) is documentation rot baked into test output and README.
5. **High-5** (partition not proven) leaves a real input combination landing in the defensive fallback that is described as "unreachable".

None of these is fatal individually. Together they suggest the plan was edited by composition rather than by re-reading — a known pattern after multi-cycle revision. The user's instruction to "halt and discuss" findings rather than batch-fix is appropriate here: each High has a different fix shape, and at least three of them require renegotiating the spec (non-Linux scope; wrapper-patch placement; partition proof) rather than just editing a code block.

**Recommended next step:** discuss High-1 through High-5 one at a time with the user. Do not have an executor begin Phase 1 until at least High-1 (boot_id_current wiring) and High-2 (non-Linux behaviour) are decided — these affect the spec of multiple later phases and back-editing them after implementation begins will require re-deriving tests.

The Medium and Low findings can be batched after High issues are resolved, *if* a final editing pass over all eight phases + test-requirements + uat-requirements + design plan is performed and confirmed in the revision notes. Otherwise the per-citation-fix cycle that produced the High-4 problem will reproduce.
