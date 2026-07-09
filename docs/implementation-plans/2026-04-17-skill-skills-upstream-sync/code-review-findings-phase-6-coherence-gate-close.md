# Code Review Findings — phase-6-coherence-gate-close

# Code Review: Phase 6 coherence-gate-close (M1, M3-skill, M4, M5 + Fable follow-up)

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 2**

Re-run confirmation pass over already-directed coherence fixes. Diff surface: two Markdown files (a skill + a design-plan doc). No source code or tests changed.

## Verification
```
Tests: N/A — Markdown-only diff, no runtime surface. Not run (nothing to run).
Build: N/A — no build for prose changes.
Lint:  N/A — no markdown linter in scope; not reported as a failure.
```
Verification appropriate to directive prose was performed instead: cross-file consistency greps (writer-vs-reader stamp string, residual "blocks ND" language, reintroduced "proves"/"structurally prevents" overclaims) and an end-to-end trace of the SPLIT verdict chain.

## Plan Alignment
- AC6.6 (M1, non-blocking self-audit reframe): ✓ corrected. Design plan line 90 + 428 now describe a non-blocking pre-presentation self-audit (step 6.5) with the collation audit as the structural gate; explicit "It does NOT block ND". Matches skill step 6.5 (line 904) and the M6-revision rationale (line 921).
- AC6.8 (M4, audit-provenance stamp): ✓ strengthened. Design plan line 92 + 429 now require file existence AND the first-line stamp; matches the skill's Existence gate (lines 1322–1340) and the honest bound "attests the step ran, not that it scored every current entry".
- M3 (efficacy calibration): ✓ implemented. Skill lines 904 and 1458 replace guarantee-language with calibrated, evidence-bounded phrasing.
- M5 (mixed-signal SPLIT exception + "It's wrong if" anchor): ✓ implemented at lines 742, 911/918, 1444 with the anti-laundering anchor present in all three copies.

## Targeted verification of the five requested checks

1. **M4 overclaim gone.** Confirmed. The stamp prose claims only what a grep can back. Line 1333: "attestation that the collation step ran, not proof it scored every current entry … nothing compares the stamp's count/date to the file's actual entries." Line 1462: "it attests the collation step ran; it is not proof a subagent scored every entry." The residual risk ("a stamp older than entries appended beneath it") is explicitly disclosed as NOT closed. No "proves the audit ran over these entries" language survives.

2. **Grep anchor matches the writer's stamp.** Confirmed byte-consistent. Writers emit `<!-- collation-audit: PASS | …` (lines 1327, 1435, 1465). Reader greps `^<!-- collation-audit:` (line 1338). All writer forms satisfy the anchor. The reader is deliberately loose (prefix only, not PASS/count/date) — consistent with the stated honest bound, not a defect. First-line anchoring (`head -1 | grep -q '^…'`) correctly prevents a body entry that merely mentions the audit from self-stamping (line 1340).

3. **SPLIT cannot launder a FAIL.** Confirmed. The exception makes the operative test textual and located in "It's wrong if" (line 742, bolded). SPLIT requires a nonempty wrongness condition that (a) survives in "It's wrong if", (b) a human could trigger *while every routed check passes*, and (c) is drawn from the entry's own "It's wrong if" rather than newly invented. The closing sentence forecloses the round-4 laundering hole: "an entry whose 'It's wrong if' enumerates only automatable conditions FAILs even if it invokes a coherence or gestalt judgment elsewhere." This anchor is present in all three copies (self-audit rubric 742, step-6.5 sub-check 911/918, collation subagent prompt 1444). E7/E9/E12 (fail side) and E10/E11 (exception guards) are named in the rubric-maintenance note.

4. **No residual "blocks ND"/ND-gate language.** Confirmed. Zero hits in the skill. The two design-plan hits (lines 90, 428) are deliberate historical corrections ("originally … a rejection gate that blocks ND", "It does NOT block ND") — they negate the old framing, they do not assert it.

5. **Efficacy claims calibrated.** Confirmed. No live "structurally prevents"/"proves" overclaim. The two "structurally prevent" hits (lines 904, 921) are negations/limitations ("not a guarantee that 'structurally prevents' all smuggling"; "the planner-side self-audit does not structurally prevent reaching the user"). "close the gap" is qualified at line 1458 ("'close' in the architectural sense that an independent enforcing layer now exists; the gate's catch rate is a calibrated, wording-sensitive property, not a structural guarantee").

## Internal-consistency trace: SPLIT verdict chain
Coherent end to end — rubric definition (742) → subagent prompt carries the exception (1444) → output format `PASS / FAIL / SPLIT` (1446) → "For any FAIL or SPLIT, block the collation write and surface" (1448) → human decision includes `accept-split` (1452) → write gate "pass, split with human acknowledgement, OR … overrides" (1454) → stamp "(any FAIL/SPLIT resolved with human acknowledgement)" (1465). No dangling verdict.

## Issues

### Minor (count: 2)
- **Issue**: Design-plan AC6.6 (line 90) summarises the self-audit as surfacing "pass/fail with suggested re-routing" and does not name the SPLIT verdict the skill now emits. Defensible as design-altitude abstraction (a SPLIT is a re-routing recommendation: route the boundary + keep the residual), so not a contradiction — but a slight granularity gap between the design doc and the operational rubric introduced by M5 landing before the M1 AC6.6 rewrite.
  - **Location**: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md:90
  - **Fix**: Optional. If desired, add "/split" to "pass/fail with suggested re-routing" so the AC enumerates all three verdicts. Not blocking.
- **Issue**: The mixed-signal exception is maintained in three near-identical copies (skill lines 742, 911/918, 1444). Future wording edits must stay in sync across all three or the LLM-judged catch rate diverges by location. Pre-existing structural property (the three anti-smuggling tests already lived in all three sites before this diff); this diff updated all three in lockstep, so no drift is present now. The rubric-maintenance note (line 744) already mandates E1–E12 re-validation on any edit, which mitigates.
  - **Location**: plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md:742, 911, 1444
  - **Fix**: None required for this change. Noted as a standing maintenance hazard, not a regression.

## Consolidation Opportunities
None visible in the diff. The three exception copies are synchronized updates to pre-existing parallel sites, not new duplication superseding old code.

## Decision: APPROVED FOR MERGE

All four directed fixes are present, internally consistent, and honestly bounded. The M4 overclaim is genuinely removed; the stamp writer and grep reader agree byte-for-byte; the mixed-signal SPLIT exception is anchored to a human-triggerable residual inside "It's wrong if" and explicitly forecloses gestalt-elsewhere laundering across all three copies; no "blocks ND" live language and no reintroduced guarantee-style overclaims survive. The two Minor items are documentation-granularity and standing-maintenance notes, neither a regression nor a blocker.

## Disposition (2026-07-07, operator-directed)

Both Minors surfaced at every level and dispositioned one-by-one with the operator (no auto-batch-fix, no silent drop):

- **Minor 1 — RESOLVED.** Verified against source: the step-6.5 self-audit does emit SPLIT (SKILL.md:918, inside "Self-audit behaviour"), so AC6.6's two-verdict enumeration was a genuine design-plan-lags-skill drift (same class as M1; M5's SPLIT landed before the M1 AC6.6 rewrite and the verdict list was never updated). Fixed by dated append to `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md:90`: `pass/fail` → `pass/fail/split` in both the correction parenthetical and the body, plus a `split-and-keep-the-residual` re-routing option. Doc-only; touches none of the three-tests / disclosed-oracle / mixed-signal wording in SKILL.md, so no E1–E12 re-validation triggered.
- **Minor 2 — ACCEPTED (no action).** The triple-maintenance (742 rubric / 911+918 self-audit / 1444 collation subagent) is intentional multi-site guidance — three distinct read contexts, each must carry the rule standalone; Markdown has no include mechanism, and any edit to those sites triggers the mandatory E1–E12 re-validation at :744. Pre-existing, lockstep-updated, no drift present. Recorded as a documented standing hazard (already covered by the :744 maintenance mandate and carry-forward L2), not a bug-fix.
