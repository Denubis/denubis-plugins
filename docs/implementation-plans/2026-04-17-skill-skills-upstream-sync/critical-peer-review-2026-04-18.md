# Critical Peer Review: Skill-Skills Upstream Sync Implementation Plan (Re-Review)

Reviewer: denubis-plan-and-execute:critical-peer-review (Opus 4.7, 1M context)
Date: 2026-04-18
Artifact type: implementation-plan
Artifact reviewed: `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/` (7 phase files + test-requirements.md + uat-requirements.md, uncommitted revision on main)

## Source Inventory

- `phase_01.md` (read in full)
- `phase_02.md` (read in full — includes Task 3.5 H6 scope expansion)
- `phase_02_5.md` (read in full — preparatory-refactor)
- `phase_03.md` (read in full)
- `phase_04.md` (read in full — includes H3 integration-evidence dropping)
- `phase_05.md` (read in full — includes Task 4.5 frustration-signal audit and L3 execution-order warning)
- `phase_06.md` (read in full — includes M6 self-audit reframe and AC6.4 cut)
- `test-requirements.md` (read in full)
- `uat-requirements.md` (read in full)
- `critical-peer-review-2026-04-17.md` (read for prior-finding context; NOT applied as current findings)
- `../design-plans/2026-04-17-skill-skills-upstream-sync.md` (spot-checked for terminology propagation and line-count claim)
- `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (spot-checked at lines 675-720, 830-885, 1285 — line references verified)
- `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md` (spot-checked for pre-restructure state)
- `plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md` (verified stale Opus 4.5 anchors at lines 15, 114, 132, 133)
- `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md` (163 lines, current pre-rewrite)
- `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` (version 2.30.0 confirmed)
- `plugins/denubis-extending-claude/.claude-plugin/plugin.json` (version 1.7.0 confirmed)
- `/tmp/superpowers-obra/skills/writing-skills/anthropic-best-practices.md` (checked for backticked filename references)
- `cc-search-chats search --help` output (capability check for time-windowed search)
- Current git branch: `main` (status dirty with uncommitted revisions)

## Frustration-signal search (step 0)

No conversation history available for frustration search — this is a fresh subagent dispatch. See Meta-Finding M7 below for analysis of AC5.8's own falsifiability under simulated adversarial application.

## Hidden Assumptions (ABP)

Load-bearing assumptions the revised plan does NOT fully evidence:

| Assumption | Load-bearing? | Status |
|---|---|---|
| cc-search-chats supports arbitrary `(start_ts, end_ts)` time-window queries | Load-bearing for AC5.8 Task 4.5 Step 1-2 | **UNEVIDENCED.** CLI supports `--days N` only; arbitrary windows require post-filter. Not addressed in plan. |
| cc-search-chats indexes this session's transcripts in near-real-time | Load-bearing for AC5.8 capturing revision-session frustration | **UNEVIDENCED.** Index build timing unstated; if only closed sessions are indexed, Phase 5 authoring is invisible to its own audit. |
| cc-search-chats search query string supports alternation / regex | Load-bearing for queries like `"no,? stop"`, `"that['\u2019]s wrong"`, `"yoloed" OR "yolo'd"` | **UNEVIDENCED.** CLI takes a single query string; semantics of AND/OR not documented in plan. |
| Plan executes on a feature branch with empty `main..HEAD` baseline | Load-bearing for AC5.5/AC5.6 `git log main..HEAD` counts | **UNSTATED.** Plan does not specify branching. If run on main, `main..HEAD` returns zero commits — the ≥27/28-commit check fails vacuously (passes trivially or fails wrongly). No `using-git-worktrees` reference. |
| User's frustration categorisation categories are mutually exclusive | Load-bearing for AC5.8 verdict production | **UNEVIDENCED.** RESOLVED-IN-SESSION can overlap with GENUINE-FRUSTRATION (user expressed genuine frustration, then the session self-corrected). Plan gives no disambiguation rule. |
| A user presented with a smuggled UAT entry at step 7 will NOT approve it | NOT load-bearing post-M6 (collation audit backstops user approval) | **Acknowledged by M6.** Task 4 collation audit is the stated structural gate — good. |
| The Phase 5 cross-reference audit script's OBRA_SKIP list is complete | Load-bearing for AC5.4 passing cleanly | **FALSIFIED.** See H1 below — obra's anthropic-best-practices.md contains 4 uncovered illustrative filenames; impl-plan-write SKILL.md contains 5 more. |
| Phase 6 edits land with the assertion strings the plan expects | Load-bearing for Step 3 verifications passing | **FALSIFIED.** See H2 below — Task 4 Step 3 asserts `"Second defensive layer" in content` but the inserted Step 2 content doesn't contain that phrase. |

## ACH Matrix

Hypotheses:
- **H_RFS (Revisions Fully Sound):** All 17 prior findings were addressed and no regressions were introduced.
- **H_RFPR (Regressions from Partial Revisions):** Fixes addressed surface claims but introduced new inconsistencies.
- **H_DEEP (Deeper structural issue revisions skirted):** Revisions closed visible loopholes but a structural weakness survives.
- **H_META (Falsifiability still not earned):** The plan's own gates remain self-reported at key junctures despite rename.

| Evidence | H_RFS | H_RFPR | H_DEEP | H_META |
|---|---|---|---|---|
| H1 version bump (1.7.0→1.8.0, 2.30.0→2.31.0) fixed across phase_05.md + test-requirements.md | + | ? | ? | ? |
| H2 rename `binary gate`→`independent-session gate` propagated to phase files + design plan | + | − (stale in test-reqs.md AC6.6) | ? | + (rename doesn't add independent verification mechanism) |
| H3/H7 DR-P4-INT-1 deleted; replaced by AC5.8/DR-P5-FRUST-1 | + | ? | + (frustration audit is real, but MECE concerns remain) | − (AC5.8 is more falsifiable than H3; H_META weakened here) |
| H4 rubric self-application reframed as walk-through + vulnerability surfacing | + | ? | + (zero-vulnerabilities flag is new but still self-reported) | + (author still authors the walk-through) |
| H5 Task 28 → UAT Requirements Collation (line 1285) | + | ? | + (grounded in actual section name) | ? |
| H6 long-running-state-patterns.md scope expansion (Task 3.5 added) | + | ? | ? | ? |
| M1 /tmp preflight checks added to Phases 2/3/4 | + | ? | ? | ? |
| M2 AC6.4 cut entirely | + | − (test-reqs.md AC6.6 still references pre-M6 language) | − (cutting rather than filling leaves "future plans bypassing impl-plan-write" unguarded, but plan acknowledges this as out-of-scope) | + (cut avoids false-comfort) |
| M3 OBRA_SKIP narrowed to tuples | + | − (tuple list still incomplete; 9+ illustrative filenames uncovered) | + (narrowing was right direction; execution missed several cases) | ? |
| M6 step 6.5 reframed to self-audit | + | − (CHANGELOG entry + commit message + test-reqs.md AC6.6 all retain "rejection gate" language) | + (acknowledging Task 4 as structural gate is more honest) | ? |
| Verification assertions land matching inserted content | + | − (H2 — "Second defensive layer" assertion won't find that string) | ? | ? |
| Commit count claim `≥27` in test-reqs vs `≥28` in phase_05.md DoD | + | − (Task 4.5 added 1 commit but test-reqs not updated) | ? | ? |

Decision rule: H_RFS requires zero `−`. It has 6 strong `−`. H_RFPR is the best-supported hypothesis. H_DEEP has partial support (some structural issues survived revision). H_META is neutral-to-weakened (H3 revision genuinely strengthened falsifiability; other gates still self-reported by author).

**Favoured hypothesis: H_RFPR with partial H_DEEP.** The revisions addressed the 17 prior findings, but the editing pass was not complete — multiple downstream references to changed claims were missed.

## Findings

### High (count: 6)

#### H1. FALSE-WORLD-MODEL / CITATION FAILURE — `phase_05_cross_ref_audit.py` will FAIL at execution on spurious illustrative-filename hits

**Issue:** The audit script in `phase_05.md` Task 1 (lines 74-190) adds `impl-plan-write` to the `TARGETS` list but the `OBRA_SKIP` list was narrowed (M3 revision) around `writing-skills` obra imports and never re-swept for `impl-plan-write` content. When executed, the audit will flag:

- Inside `impl-plan-write/SKILL.md`: backticked illustrative filenames `\`config.py\``, `\`main.py\``, `\`types.py\``, `\`test-requirements.md\``, `\`uat-requirements.md\`` — ALL will fail `FILE_RE.finditer` same-dir resolution
- Inside obra-imported `anthropic-best-practices.md`: backticked illustrative filenames `\`analyze_form.py\``, `\`doc2.md\``, `\`pdf_to_images.py\``, `\`validate_form.py\`` — all uncovered by the 4-tuple `OBRA_SKIP` entries

**Evidence grade:** Demonstrated. Ran `grep -oE '\`[a-zA-Z0-9_.-]+\.(md|js|dot|py|sh|txt)\`'` against both files:
- `anthropic-best-practices.md` → `analyze_form.py`, `doc2.md`, `form_validation_rules.md`, `pdf_to_images.py`, `validate_form.py` (only `form_validation_rules.md` is in `OBRA_SKIP`)
- `impl-plan-write/SKILL.md` → `config.py`, `main.py`, `test-requirements.md`, `types.py`, `uat-requirements.md`

**Type:** citation failure / scope error
**Pattern level:** pattern-level — the audit script's regex design treats *every* backticked filename as a cross-reference; M3's narrowing fixed the immediate false-positive flagged by L4 but never swept the now-broader `TARGETS` list.
**Ripple:**
- Phase 5 Task 1 Step 2 (`Expected: PASS: all cross-references...`) will NOT pass on first run
- Phase 5 Task 4 Step 1 re-run will also fail
- AC5.4 "covered" status in test-requirements.md line 457 is overclaimed
- AC1.3, AC1.6, AC2.5, AC3.6 all depend on this audit script (per test-requirements.md lines 429-431, 438, 446) — their "covered" status is fragile
**Corrected language:** Either pre-emptively expand `OBRA_SKIP` with the illustrative tuples, OR change `FILE_RE` logic to only flag references that look like skill-local supporting files (e.g., require path-like context), OR remove `impl-plan-write` from `TARGETS` and audit it with a different mechanism that doesn't flag illustrative code examples.
**Location:** `phase_05.md` lines 74-190 (script body); `phase_05.md` line 199 (expected output claim); test-requirements.md line 270.
**Next proof step:** Copy the audit script to disk now (pre-execution) and run it against the current-state repo. Any FAIL output before Phase 1 runs is a script bug, not a sync defect.

#### H2. OVERCLAIM / INTERNAL INCONSISTENCY — Phase 6 Task 4 Step 3 assertion checks for string NOT present in inserted content

**Issue:** `phase_06.md` Task 4 Step 3 verification (line 437) asserts:
```python
assert 'Second defensive layer' in content, 'two-layer framing missing'
```
Reading `content` = contents of `impl-plan-write/SKILL.md` after Task 4 Step 2 inserts the Collation audit block. But the Step 2 content block (phase_06.md lines 398-420) does NOT contain the phrase "Second defensive layer" anywhere. The phrase appears only in the commit message (line 458) and in phase_05.md's CHANGELOG entry (line 347) — neither of which writes to `impl-plan-write/SKILL.md`.

**Evidence grade:** Demonstrated. `grep -c "Second defensive layer" phase_06.md` → 2 matches, both OUTSIDE the inserted content block. The inserted block uses instead "The two layers together close the rubric-vs-gate gap" (line 420).

**Type:** internal inconsistency / overclaim
**Pattern level:** local-only (one verification mismatch)
**Ripple:** Phase 6 Task 4's Python verification will halt with `AssertionError: two-layer framing missing` even if Step 2 executed correctly. An executor may then "fix" this by adding the "Second defensive layer" phrase to `impl-plan-write/SKILL.md` (creating documentation-drift), OR by removing the assertion (weakening verification), OR by halting and escalating. Any of the three introduces drift from the plan's intent.
**Corrected language:** Either change the assertion to `assert 'close the rubric-vs-gate gap' in content, ...` matching the inserted text, OR add "Second defensive layer" to the Step 2 content block so the assertion passes. Second option is cleaner because the phrase is useful in-file documentation.
**Location:** `phase_06.md` line 437 (assertion) vs lines 398-420 (inserted content).
**Next proof step:** Dry-run Task 4 Step 2 against a throwaway copy of impl-plan-write/SKILL.md and run Step 3's assertion block. Confirm the assertion fails before revising it.

#### H3. INTERNAL INCONSISTENCY — `test-requirements.md` AC6.6 not updated for M6 revision

**Issue:** The M6 revision (2026-04-18) reframed Task 3's step 6.5 from "authoring-time rejection gate" to "pre-presentation self-audit" and explicitly REMOVED the "Do NOT proceed to step 7" blocking language. `phase_06.md` Task 3 Step 3 (lines 322-331) now asserts:
```python
assert 'Pre-presentation self-audit' in content
# No "Do NOT proceed to step 7" assertion
```
But `test-requirements.md` line 357 still reads:
> **What it verifies:** Strings `Authoring-time rejection gate`, `Decomposition test`, `Reduction test`, `Disagreement test` all present in `impl-plan-write/SKILL.md`; positional check that `gate_pos < step7_pos`; explicit `Do NOT proceed to step 7` blocking language present.

After Phase 6 Task 3 executes, `impl-plan-write/SKILL.md` will contain "Pre-presentation self-audit" but NOT "Authoring-time rejection gate" and NOT "Do NOT proceed to step 7". An executor re-checking AC6.6 coverage against test-requirements.md will see the test-requirements description mismatching the actual file contents.

**Evidence grade:** Demonstrated. `grep -n "Authoring-time rejection gate"` across plan → only test-requirements.md line 357. `grep -n "Do NOT proceed to step 7"` → only test-requirements.md line 357 and historical critical-peer-review-2026-04-17.md.

**Type:** internal inconsistency
**Pattern level:** pattern-level — same M6-revision-incomplete pattern as H4 (CHANGELOG) and H5 (commit message).
**Ripple:**
- test-requirements.md description of AC6.6 coverage is stale
- A code-reviewer checking "plan says X, skill contains X" for AC6.6 will see X="Authoring-time rejection gate" but the skill contains X="Pre-presentation self-audit" — the reviewer will file a false-positive contradiction
- Coverage summary (line 467) still says "AC6.6 | structural-check | phase_06.md T3 S3 | covered" — the coverage claim stands but the description underneath it is stale
**Corrected language:** Update test-requirements.md line 357 to match M6 revision: `Strings \`Pre-presentation self-audit\`, \`Decomposition test\`, \`Reduction test\`, \`Disagreement test\` all present; positional check \`audit_pos < step7_pos\`; collation-audit-as-structural-gate reference present.`
**Location:** `test-requirements.md` line 357 (stale).
**Next proof step:** After test-requirements.md is updated, re-grep plan for all occurrences of "authoring-time rejection gate" (case-insensitive) — should be zero except historical-review references.

#### H4. INTERNAL INCONSISTENCY — Phase 6 CHANGELOG entry (Task 3 of phase_05.md) still describes the M6-reframed self-audit as a blocking "rejection gate"

**Issue:** `phase_05.md` line 345 (the Task 3 prepended CHANGELOG entry for denubis-plan-and-execute 2.31.0):
> **New:** Per-phase Task-ND authoring-time rejection gate: every proposed UAT entry runs through the three anti-smuggling tests (Decomposition / Reduction / Disagreement) before phase_##.md is written. **Failures block ND until the entry is rewritten**, downgraded (...), or overridden with explicit human acknowledgment.

The M6 revision (phase_06.md lines 288-308) explicitly says:
> This is a pre-presentation self-audit, NOT the structural anti-smuggling gate. The structural gate is the collation audit in Task 4 ... **The user CAN still approve a smuggled entry**; the collation audit at Task 4 is what actually prevents smuggled entries...

The CHANGELOG language "Failures block ND" contradicts the M6 self-audit framing. A user reading the release notes will believe the planner blocks smuggled entries at ND-write time. The plan internally says they don't.

Also phase_05.md line 355 **Fixed:** "Now enforced at Task ND generation, collation..., and Finalization existence" — same contradiction: Task ND generation is NOT "enforcement" per M6; only the collation audit is.

**Evidence grade:** Demonstrated via verbatim quotation comparison.
**Type:** internal inconsistency / overclaim
**Pattern level:** pattern-level (see H3).
**Ripple:**
- Users reading 2.31.0 CHANGELOG get a misleading impression of what the hardening does
- Future reviewers auditing "does impl-plan-write actually block smuggled entries at ND time?" will find NO — and will flag the skill-vs-CHANGELOG mismatch
**Corrected language:** Rewrite the New/Fixed blocks to match M6 framing:
> **New:** Per-phase Task-ND pre-presentation self-audit: every proposed UAT entry is scored against the three anti-smuggling tests (Decomposition / Reduction / Disagreement) at planner-side before step 7 (AskUserQuestion). Self-audit does NOT block user approval — it surfaces concerns to the user before approval. Structural anti-smuggling enforcement lives in the Task 4 Collation audit (dedicated subagent before uat-requirements.md is written) and the Finalization existence gate.
> **Fixed:** Rubric-vs-gate drift: three anti-smuggling tests previously lived only in `exec-uat-gate` (execution time). Now structurally enforced at the collation-audit step (dedicated subagent runs each entry through the three tests before uat-requirements.md is written) and at Finalization (existence gate on uat-requirements.md). Planner-side self-audit at step 6.5 is hygienic, not structural.
**Location:** phase_05.md lines 345, 355.
**Next proof step:** Do a single-pass `grep -n "authoring-time rejection gate"` across the plan after fixing H3 and H4 — expect zero hits outside historical-review.

#### H5. INTERNAL INCONSISTENCY — Phase 6 commit message (Task 3 of phase_06.md) retains pre-M6 "rejection gate" framing

**Issue:** `phase_06.md` line 342-353 commit message:
```
feat(impl-plan-write): per-phase ND authoring-time rejection gate

- Insert step 6.5 between 'Present to user' and AskUserQuestion
  approval that runs the three anti-smuggling tests... on each proposed UAT entry.
- Gate placement BEFORE user approval (not within Task ND writing)
  so users don't approve smuggled entries and then have them rejected
  downstream — pre-approval placement is the stronger gate.
```

This commit message describes the gate as BLOCKING user approval ("users don't approve smuggled entries ... pre-approval placement is the stronger gate"). The M6 revision explicitly says the user CAN approve smuggled entries at step 7 and the planner-side audit is hygienic only. Commit message lies about the mechanism.

**Evidence grade:** Demonstrated via side-by-side comparison (phase_06.md line 288-308 vs 342-353).
**Type:** internal inconsistency
**Pattern level:** pattern-level (H3, H4, H5 are all manifestations of incomplete M6 editing pass).
**Ripple:**
- `git log` reader gets misleading impression
- If AC6.6 is later re-audited via commit-message grep, the grep will match the commit message and mislead the auditor
**Corrected language:** Update commit message to:
```
feat(impl-plan-write): per-phase ND pre-presentation self-audit (step 6.5)

- Insert step 6.5 between 'Present to user' and AskUserQuestion
  approval that runs the three anti-smuggling tests (Decomposition /
  Reduction / Disagreement) on each proposed UAT entry as planner-side
  hygiene before step 7.
- Explicitly NOT a structural gate — user can still approve a surfaced
  smuggled entry at step 7. Structural gate is the Task 4 Collation
  audit (independent subagent before uat-requirements.md is written).
- Four routing outcomes per entry: pass all three (retain), fail
  Decomposition (route to test-requirements), fail Reduction (decompose),
  fail Disagreement (rewrite or route); all fail → zero-UAT output
  per AC6.7 first-class valid outcome.
```
**Location:** phase_06.md lines 342-353.
**Next proof step:** same as H4.

#### H6. INTERNAL INCONSISTENCY — Commit count claim divergence (`≥27` in test-requirements.md vs `≥28` in phase_05.md DoD)

**Issue:** test-requirements.md lines 276 and 283 both claim `≥ 27 commits`. phase_05.md line 554 claims `≥ 28 commits` (breakdown: 3+5+1+5+6+3+5 = 28; the +1 comes from the H3-revision Task 4.5 frustration-signal-audit commit). Additionally, phase_05.md Task 4 Step 2 (line 438-444) still lists "Phase 5: 4 commits" — which would produce 27, not 28 — inconsistent with the DoD's "Phase 5 (5)" on line 554.

**Evidence grade:** Demonstrated via `grep -n "≥ 2[0-9]"`.

**Type:** internal inconsistency
**Pattern level:** pattern-level (same incomplete-editing-pass pattern).
**Ripple:**
- AC5.5/AC5.6 verification will use whichever number the auditor remembers; 27 vs 28 is minor but "commit discipline" gates shouldn't have off-by-one slop
- Phase 5 Task 4 Step 2's own text predicts 4 commits for itself while the DoD says 5 — self-contradicting
**Corrected language:**
- test-requirements.md lines 276, 283: `≥ 28 commits`
- phase_05.md Task 4 Step 2 line 444: "Phase 5: 5 commits (audit script, extending-claude 1.8.0, plan-and-execute 2.31.0, frustration-signal audit, this final audit)"
**Location:** test-requirements.md lines 276, 283; phase_05.md lines 444, 554.
**Next proof step:** same as H3-H5.

### Medium (count: 5)

#### M1. CITATION INCONSISTENCY — phase_06.md AC6.7 line 30 points at the wrong line number for the three-lens table

**Issue:** phase_06.md line 30:
> **skill-skills-upstream-sync.AC6.7 Success:** The three-lens table in `impl-plan-write/SKILL.md` at approximately **line 664** is amended...

But phase_06.md line 44 (the file outline):
> Three-lens table: **line 681-686** (Popper row at line 683)

And phase_06.md Task 1 Files line 72:
> Modify: ... (three-lens table only, approximately **line 681-686**)

I verified by reading impl-plan-write/SKILL.md directly: the three-lens table is at lines 681-685, Popper row at line 683. AC6.7 says "line 664" — that's off by 17-19 lines.

**Evidence grade:** Demonstrated.
**Type:** citation failure
**Pattern level:** local-only.
**Ripple:** An executor reading AC6.7 and opening SKILL.md at line 664 will not find the three-lens table; they will have to scan. Minor productivity hit; no functional impact.
**Corrected language:** Update AC6.7 in phase_06.md line 30 to `approximately line 683` (or `line 681-686` to match Task 1's phrasing).
**Location:** phase_06.md line 30.
**Next proof step:** Verify current line number is stable (it was at review time); commit the correction.

#### M2. OVERCLAIM — AC5.8 frustration audit depends on cc-search-chats capabilities the plan does not verify

**Issue:** phase_05.md Task 4.5 Step 2 proposes queries like `"no,? stop"`, `"that['\u2019]s wrong"`, `"yoloed" OR "yolo'd"`, `"FFS" OR "for fuck's sake"`. These are regex-style alternations and character classes. Actual cc-search-chats CLI signature (verified via `cc-search-chats search --help`):
```
search [-h] [--json] [--project PROJECT] [--epoch EPOCH] [--days DAYS] query
```
`query` is a single string argument. The CLI supports `--days N` but NOT arbitrary time windows, NOT regex, NOT AND/OR operator syntax. The plan's queries will be passed literally.

Additionally, Step 1 wants to derive the search window from git log timestamps — but cc-search-chats has no `--after TIMESTAMP` / `--before TIMESTAMP` flags. The only temporal filter is `--days N` (integer days back from today). Post-filtering on match timestamps requires the executor to do manual comparison per match.

**Evidence grade:** Demonstrated (CLI help output inspected).
**Type:** overclaim / unverifiable claim
**Pattern level:** local-only.
**Ripple:**
- Task 4.5 Step 2 is not executable as written
- AC5.8 "covered" status is fragile — the automation portion needs meaningful re-work
- DR-P5-FRUST-1's automatable-vs-non-automatable split (uat-requirements.md lines 127-129) says "Running the queries; collecting matches" is automatable — but it's automatable ONLY by a non-trivial executor who translates the plan's regex-ish queries into per-keyword runs and aggregates the results manually
**Corrected language:** Either (a) list each term as a separate query (one `cc-search-chats search "mate"` run, one `cc-search-chats search "FFS"` run, etc. — matches unioned by the executor) and drop the regex/OR notation; or (b) if cc-search-chats gains regex support later, cite that capability with a version requirement. For the time window: document that the executor will post-filter matches by timestamp using the git-log-derived window. Update DR-P5-FRUST-1's "automatable" claim to acknowledge this.
**Location:** phase_05.md lines 488-498, 507; uat-requirements.md lines 127-129.
**Next proof step:** Dry-run one of the more complex queries (`"no,? stop"`) against cc-search-chats; confirm the literal string treatment, then split into separate runs.

#### M3. WEAK FALSIFIER — AC5.8 categorisation scheme is not MECE (RESOLVED-IN-SESSION can overlap GENUINE-FRUSTRATION)

**Issue:** phase_05.md Task 4.5 Step 3 defines four categories:
- GENUINE-FRUSTRATION (user expressed frustration; methodology failed)
- TECHNICAL-DISAGREEMENT (no emotional register)
- QUOTED-ILLUSTRATIVE (false positive)
- RESOLVED-IN-SESSION (frustration appeared AND the session course-corrected)

RESOLVED-IN-SESSION is clearly a sub-case of GENUINE-FRUSTRATION — you can't "resolve" frustration that didn't exist. phase_05.md line 509 treats it as mutually exclusive with GENUINE-FRUSTRATION ("GENUINE" vs "RESOLVED"), and the verdict logic (line 517) says "Resolved-in-session matches are catalogued but do not fail the audit" — i.e., they're COUNTED AS NOT-GENUINE even though they're semantically GENUINE-THEN-FIXED.

This matters because DR-P5-FRUST-1 (uat-requirements.md line 131) says "If the user cannot distinguish, default to GENUINE-FRUSTRATION — the audit is biased toward flagging rather than dismissing." But the scheme's RESOLVED-IN-SESSION is a dismissal path — if a user categorises an ambiguous post-correction match as RESOLVED-IN-SESSION, the audit under-reports. The "default to GENUINE-FRUSTRATION" rule protects the GENUINE/TECHNICAL-DISAGREEMENT boundary but not the GENUINE/RESOLVED-IN-SESSION boundary.

**Evidence grade:** Plausible (both borders of the overlap are discussed in the plan; the overlap itself is not).
**Type:** weak falsifier / scope error
**Pattern level:** local-only.
**Ripple:**
- AC5.8 verdict can under-report methodology failure if the scheme is applied literally
- The joint-review calibration DR-P5-FRUST-1 flags is load-bearing but the calibration rule is incomplete
**Corrected language:** Either:
- Make RESOLVED-IN-SESSION a subtype flag applied AFTER categorisation (so `GENUINE-FRUSTRATION + resolved-in-session` is a valid joint label), with the verdict logic treating "all genuine matches were resolved-in-session" as a softer audit-passes, OR
- Keep four categories mutually exclusive and add a tiebreak rule: "if the user initially expressed frustration and the session self-corrected before moving on, classify as RESOLVED-IN-SESSION regardless of initial intensity; the audit's verdict then separates count(GENUINE-FRUSTRATION unresolved) vs count(RESOLVED-IN-SESSION), reporting both."
**Location:** phase_05.md lines 507-510, 514-520; uat-requirements.md lines 125, 131.
**Next proof step:** Walk through a concrete hypothetical (e.g., "user said 'no mate' and Claude then changed course successfully") and categorise under current scheme vs proposed scheme; note which verdict each produces.

#### M4. INTERNAL INCONSISTENCY — Phase 6 Task 2 instructs amending DR2/DR3/DR4 templates but acknowledges some don't take UAT format; the instruction is ambiguous

**Issue:** phase_06.md Task 2 Step 1 line 182:
> Apply the SAME amendment to DR2, DR3, DR4 templates in the same section (each currently has its own falsification block variant). The two new lines are required in EVERY UAT entry format; they can be omitted for DRs that route entirely to test-requirement with no UAT entry.

Reading the actual DR templates in impl-plan-write/SKILL.md lines 858-884:
- DR2: routes to `**Popper:** -> **test-requirement**` (NOT a UAT entry; no falsification block)
- DR3: has `**This decision assumes / To shatter it / It's wrong if`** (IS a UAT entry, deferred to future phase)
- DR4: routes to test-requirement (no falsification block)

So DR2 and DR4 should NOT get the `What's automatable` lines; DR3 SHOULD. The plan's instruction "Apply the SAME amendment to DR2, DR3, DR4" plus "they can be omitted for DRs that route entirely to test-requirement" is internally consistent but leaves the executor to judge which DR templates get the amendment. An executor reading it mechanically may amend all four templates, introducing `What's automatable` lines into DR2/DR4 where they don't apply.

**Evidence grade:** Plausible.
**Type:** step too abstract to execute (per implementation-plan checklist)
**Pattern level:** local-only.
**Ripple:** Inconsistent DR templates between plans; future planners looking at DR2/DR4 may include the lines on every UAT entry, defeating the "zero-UAT is valid" spirit.
**Corrected language:** Name specifically which DR templates get the amendment: "Apply the amendment to DR1 and DR3 templates (the two that take the falsification `**This decision assumes / To shatter it / It's wrong if**` block). Do NOT amend DR2 and DR4 templates (they route to test-requirements without a falsification block; adding `What's automatable` lines there would be nonsensical)."
**Location:** phase_06.md line 182.
**Next proof step:** Walk the executor instructions literally on a copy of impl-plan-write/SKILL.md; see whether DR2/DR4 mistakenly receive the amendment.

#### M5. HIDDEN ASSUMPTION — Plan assumes execution on a feature branch; AC5.5/AC5.6 use `main..HEAD` which breaks if executed on main

**Issue:** phase_05.md Task 4 Step 2 uses `git log --oneline main..HEAD` to verify commit discipline (AC5.5, AC5.6). If the plan is executed with HEAD == main (as the repo currently is — I verified `git branch --show-current` == `main`), this query returns zero commits. The ≥27/28-commit check is vacuously-false then vacuously-true depending on interpretation — either way, the check is broken.

The plan never instructs the executor to create a feature branch. It doesn't reference `denubis-plan-and-execute:using-git-worktrees` either. The hidden assumption is that the executor starts this plan from a fresh branch with empty `main..HEAD`.

**Evidence grade:** Demonstrated. `git branch --show-current` → `main` at review time; all plan revisions are uncommitted on main.

**Type:** hidden blocking assumption
**Pattern level:** local-only.
**Ripple:**
- If an executor runs Phase 5 Task 4 Step 2 after executing all Phases on main, `main..HEAD` yields empty — AC5.5/5.6 pass or fail vacuously
- Related: the `using-git-worktrees` skill lives in the denubis-plan-and-execute plugin; plan is modifying that plugin mid-execution (Phase 6), so worktree discipline is locally meaningful but unstated
**Corrected language:** Either (a) add a preflight step in Phase 1 (or plan-level preamble): "This plan assumes execution on a feature branch diverged from main. If HEAD == main, halt and create a branch per `denubis-plan-and-execute:using-git-worktrees` before proceeding." OR (b) change AC5.5/5.6 to track commits differently (e.g., by plan-authored-file filter: `git log --oneline -- docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/ plugins/denubis-extending-claude/skills/epistemic-humility/ ...`).
**Location:** phase_05.md lines 430-434, 554.
**Next proof step:** Document branch expectation explicitly; re-read AC5.5/5.6 assertions against the explicit branch assumption.

### Low (count: 3)

#### L1. Phase 5 Task 4.5 depends on the session's own audit to categorise — can produce bias if the user reviewing is also the executor

**Issue:** AC5.8 / DR-P5-FRUST-1 asks "user" to categorise each match. Who is the user? In this plan's context it's the repo owner, who is also the author of the commits being audited. The "joint human review" (phase_05.md line 507) conflates executor-with-judgement and user-with-judgement in the single person. That's an acknowledged limit of the design, but it does mean AC5.8 is less independently verifiable than RED evidence (which at least used independent-session transcripts).
**Severity:** Low — the plan acknowledges this structurally via the categorisation scheme's "default to GENUINE-FRUSTRATION" tiebreak.
**Location:** phase_05.md line 507; uat-requirements.md line 131.

#### L2. `has_haiku_retirement` check still overly permissive despite L2 revision

**Issue:** phase_02.md Task 3 Step 3 check:
```python
has_haiku_retirement = any([
    'retired' in content.lower() and 'Haiku' in content,
    'not supported' in content.lower() and ('judgement' in content.lower() or 'judgment' in content.lower()) and 'Haiku' in content,
])
```
The file has a `## Haiku 4.5` H2 — so `'Haiku' in content` is always True. If the word "retired" appears ANYWHERE in the file (including unrelated notes like "retired Anthropic engineer"), the check passes. The check is weaker than the L2-revision narrative claims. Same for the second arm — `'not supported' in content.lower()` can match unrelated prose.
**Severity:** Low — the belt-and-braces check (lines 354-355) on the ABSENCE of "struggles with judgement" is the real guard and is solid.
**Location:** phase_02.md lines 347-352.
**Corrected language:** Require the retirement note to appear in a specific context: e.g., look for the specific phrase "struggles with judgement" in a retirement-note sentence pattern. Or require `'retired' in content.lower() and 'Haiku 4.5' in content and 'judgement' in content.lower()` (all three co-locating, not just all three existing).

#### L3. phase_05.md Task 2 CHANGELOG ordering check is weak

**Issue:** phase_05.md line 378 checks `p29 < e18` (2.31.0 appears before 1.8.0 in CHANGELOG). This is the correct newest-first property, but the comparison `p29 < e18` uses mere `str.find` — which finds the FIRST occurrence. If 2.31.0 or 1.8.0 entries get edited or duplicated, the check produces false signals. More meaningfully, the test doesn't verify that 2.31.0 comes BEFORE 2.30.0 (the pre-existing newest entry); it only checks 2.31.0 vs 1.8.0.
**Severity:** Low.
**Corrected language:** Add `p30 = changelog.find('## [denubis-plan-and-execute] 2.30.0'); assert p29 < p30, 'new 2.31.0 entry must precede existing 2.30.0 entry (newest-first)'`.

## Meta-findings

### M7 (Meta). If AC5.8's frustration audit were run on THIS review session's transcript, it would generate substantial QUOTED-ILLUSTRATIVE false positives

This review explicitly discusses "mate" (global MEMORY.md signal), "FFS" (phase_05.md query), "yoloed" (phase_05.md query), "that's wrong" (phase_05.md query), and quotes frustration signals as part of auditing AC5.8's design. When cc-search-chats runs the AC5.8 queries over this review session's transcript, it will return:
- N matches on "mate" (from MEMORY.md note and this review)
- Several matches on "FFS", "yoloed", "that's wrong" (from quoted query lists and worked examples)

All categorisable as QUOTED-ILLUSTRATIVE — but the categoriser must read each match's surrounding context to be confident. For a 20-30-query × 6-phase × N-authoring-session corpus, this is meaningful joint-review work. The plan estimates no time cost for Task 4.5's Step 3.

That's a feature-not-a-bug acknowledgement: the plan's scheme handles the case (via QUOTED-ILLUSTRATIVE category). But it will fire frequently. An executor should expect Step 3 to be the longest step in Task 4.5.

The more concerning failure mode: if the joint reviewer tires and starts fast-categorising, the risk of false-dismissing a genuine-frustration match as QUOTED-ILLUSTRATIVE (because it APPEARS to be in a document-quoting context) goes up. Mitigation: Task 4.5 Step 3 should document an explicit fatigue-floor ("if review takes >X matches in one sitting, halt and resume") and a calibration check ("pick 3 random matches per category and have a reviewer verify the categorisation without seeing the prior verdict").

**Severity:** Medium (bordering High if applied to a 100+-match corpus).

## Verification

- Files read: All 7 phase files, test-requirements.md, uat-requirements.md, prior critical-peer-review (historical), design plan (targeted sections), impl-plan-write SKILL.md (targeted lines), writing-claude-directives SKILL.md, long-running-state-patterns.md
- Commands or queries checked:
  - `grep -n "^## UAT Requirements Collation"` in impl-plan-write/SKILL.md → line 1285 (confirmed H5 fix landed correctly)
  - `grep -c "Second defensive layer" phase_06.md` → 2 matches, neither in the inserted content block (H2 proof)
  - `grep -n "Authoring-time rejection gate"` across plan → single hit in test-requirements.md (H3 proof)
  - `grep -oE '\`[a-zA-Z0-9_.-]+\.(md|js|dot|py|sh|txt)\`'` on obra anthropic-best-practices.md → 4 uncovered filenames (H1 proof)
  - `grep -oE '\`[a-zA-Z0-9_.-]+\.(md|js|dot|py|sh|txt)\`'` on impl-plan-write/SKILL.md → 5 uncovered filenames (H1 proof)
  - `cc-search-chats search --help` → confirmed no regex, no arbitrary time window, single-string query (M2 proof)
  - `git branch --show-current` → `main` (M5 proof)
  - `grep -c '^### DR' uat-requirements.md` → 8 entries (matches phase_06.md claim)
  - `cat plugin.json` for both plugins → confirmed 1.7.0 and 2.30.0 (H1 prior fix verified)
  - `wc -l impl-plan-write/SKILL.md` → 1337 (matches phase_06.md line 43)
  - `wc -l long-running-state-patterns.md` → 203 (consistent with H6 scope)
  - `sed -n '683p' impl-plan-write/SKILL.md` → Popper row (M1 proof for correct current line)
- Citations verified:
  - phase_06.md line 1285 → verified (matches actual file)
  - phase_06.md three-lens table at "line 664" → FALSIFIED (actual line 681-686)
  - phase_06.md DR template at "line 838-884" → verified (actual line 838-883)
  - Design plan line 123 ("≤250 lines") → verified (M5 fix landed)
  - phase_02.md Opus 4.5 at lines 114, 132 in long-running-state-patterns.md → verified
- Provenance concerns: None. Plan revisions are uncommitted on main; revision session context is fresh; no artefact contamination.

## Strongest Hypothesis

**H_RFPR (Regressions from Partial Revisions)** with most support.

Evidence:
- H1 (version bump) fix landed completely — H_RFS-consistent for that finding
- H2/H5/H6/H7 fixes all landed structurally — H_RFS-consistent
- But H2 (rename), M2 (AC6.4 cut), M6 (step 6.5 reframe) each left downstream references stale in other files → H_RFPR-consistent
- M3 (OBRA_SKIP narrowing) fixed one false-positive but didn't sweep the expanded `TARGETS` list → H_RFPR-consistent

The pattern is: **each revision correctly addressed the finding's primary claim but stopped short of the Ripple-Rule sweep that critical-peer-review.md explicitly names.** The full-editing-pass confirmation was not performed (or was performed only at the phase-file level, not plan-wide).

## Weakest Hypothesis

**H_RFS (Revisions Fully Sound)** has the least support — six High findings disprove it directly.

## Pre-Mortem

Assume the revised plan is committed as-is. What does the next incident reveal?

Scenario 1 — Audit script fails on first run: Executor runs Phase 5 Task 1 Step 2, audit script exits 1 with spurious broken-reference errors from illustrative filenames in impl-plan-write and anthropic-best-practices. Executor either (a) expands OBRA_SKIP ad-hoc until the script passes (erodes the audit's falsifiability), or (b) halts and escalates. Best-case outcome is the halt — but scripts that "just need a config tweak" often get tweaked rather than halted.

Scenario 2 — Assertion failure cascades into self-edits: Phase 6 Task 4 Step 3 fails with `AssertionError: two-layer framing missing`. Executor adds "Second defensive layer" to impl-plan-write/SKILL.md to pass the assertion. The edit is cosmetic; the underlying inconsistency is papered over; no one notices.

Scenario 3 — M6 reframe contradiction ships to users: CHANGELOG 2.31.0 is published saying "authoring-time rejection gate" / "Failures block ND". Users authoring plans believe the planner blocks smuggled entries. Users reading impl-plan-write/SKILL.md discover the planner doesn't. Credibility hit on the docs-match-behaviour contract. Fix requires a follow-on patch release.

Scenario 4 — AC5.8 audit runs but returns zero matches because queries were passed literally: Executor runs `cc-search-chats search "no,? stop"` and gets zero hits (no session literally contains the string with the comma). The audit "passes" vacuously. Frustration-signal audit provides false comfort.

Scenario 5 — AC5.5/5.6 pass on main without any commits: Executor runs Phases on main (no branch). `git log main..HEAD` returns empty. The ≥27-commit check either fails (halt) or is silently interpreted as "no commits have been made yet, so no violations" (pass). Either interpretation is wrong.

All five scenarios are reachable from the current plan state. Three are blocked by High findings; two are Medium.

## Fastest Next Test

**Pre-execute the Phase 5 audit script against the current (pre-Phase-1) repo state.**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
# Copy the script body from phase_05.md Task 1 Step 1 into a temp file
# Then run it
python3 /tmp/phase_05_cross_ref_audit.py
```

Predictions:
- If H1 is correct: script exits 1 with FAIL lines flagging `config.py`, `main.py`, `types.py`, `test-requirements.md`, `uat-requirements.md` (inside impl-plan-write/SKILL.md) and `analyze_form.py`, `doc2.md`, `pdf_to_images.py`, `validate_form.py` (inside any obra-imported anthropic-best-practices.md that's present).
- If H1 is wrong: script exits 0 or reports only reference failures caused by current-state (not the false-positives the `OBRA_SKIP` should prevent).

Execution time: <60 seconds. Grade-changing: turns H1 from Demonstrated to Demonstrated-and-reproduced.

## Overall Assessment

**NEEDS_REVISION.**

Specific blockers before commit:
1. **H1** must be fixed — the Phase 5 cross-reference audit script will fail with false positives; expand `OBRA_SKIP` to cover impl-plan-write illustrative filenames and anthropic-best-practices illustrative filenames, OR narrow the `FILE_RE` scope so illustrative code examples aren't flagged.
2. **H2** must be fixed — Phase 6 Task 4 Step 3 assertion `'Second defensive layer' in content` will fail; either add the phrase to Task 4 Step 2's content block or update the assertion to match the actual inserted phrasing.
3. **H3 + H4 + H5 must be fixed as a batch** — the M6 revision editing pass missed three downstream references (test-requirements.md AC6.6 description, phase_05.md CHANGELOG 2.31.0 entry, phase_06.md Task 3 commit message). All three still describe the step 6.5 as a blocking rejection gate when the actual mechanism is a non-blocking self-audit. The CHANGELOG contradiction is user-visible and is the most urgent of the three.
4. **H6** must be fixed — commit count divergence between test-requirements.md (27) and phase_05.md DoD (28); also internal contradiction within phase_05.md (Task 4 Step 2 text says 4, DoD says 5).
5. **M1** should be fixed — wrong line number in AC6.7 (`664` vs actual `683`).
6. **M2** should be fixed — AC5.8 query syntax assumes regex/OR support cc-search-chats does not provide.

**Recommended revision approach:** Do a plan-wide Ripple Rule sweep this time. After fixing each finding, grep the whole plan directory for the affected phrase and confirm all occurrences are updated. Then confirm "I have done a full editing pass" per the critical-peer-review skill's Editing Pass Rule.

Do not commit the revision until H1-H6 are addressed. M1-M5 are fixable in the same editing pass.

The ACH matrix strongly supports H_RFPR over H_RFS: revision addressed the 17 prior findings' primary claims but the full-editing-pass discipline was not applied plan-wide. Fix that, commit, and the plan is ready.
