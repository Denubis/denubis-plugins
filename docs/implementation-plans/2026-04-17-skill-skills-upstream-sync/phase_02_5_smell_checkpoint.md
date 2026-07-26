# Smell Assessment Report

## Phase: Preparatory refactoring for Phase 3 — Restructure testing-skills-with-subagents
## Files Assessed: 1 file, 421 lines
## Date: 2026-06-10
## Framing: structural-readiness (impediments to upcoming Phase 3 goal only)

---

## Upcoming Phase Goal (context)

Phase 3 will:
- (a) Prepend a conversation-precedent protocol to the RED phase's process checklist (DR3)
- (b) Demote the synthetic pressure-scenario detail from RED to the REFACTOR completeness section

Phase 2.5's job (this assessment's context): split the currently monolithic RED section so those two edits become clean in-place operations.

---

## Complexity Measurements

### complexipy (cognitive complexity >15)
Markdown file — complexipy cannot parse. No functions found. Expected. No findings.

### Line Counts
| File | Lines | Flag |
|------|-------|------|
| testing-skills-with-subagents/SKILL.md | 421 | Over 400-line threshold (+21) |

### Structural Smells (ast-grep)
All four rules (fcis-violation, global-mutable-state, long-parameter-list, nesting-depth) return empty. Expected — rules target Python; target file is Markdown. No findings.

---

## RED Section Scope (verified against file)

The RED section is:
- H2 heading: `## RED Phase: Baseline Testing (Watch It Fail)` at line 71
- End: line 109 (last content line before the GREEN Phase H2 at line 110)
- Length: 38 content lines

Internal structure (flat — no H3 subsections):
- Lines 71-76: Goal statement + TDD-mapping rationale
- Lines 77-83: Process checklist (5 scenario-agnostic checklist items)
- Lines 85-108: Concrete synthetic pressure-scenario example with rationalizations ("**Example:**" block)

---

## Findings

### Couplers

**Finding 1: Feature Envy — example block embeds the synthetic-baseline method the checklist sets up**

- **Smell:** Feature Envy
- **Location:** SKILL.md lines 85-108 (the `**Example:**` block within the RED section)
- **Evidence Grade:** Plausible
- **Evidence:** The example block (lines 85-108) does not serve the generic process checklist (lines 77-83) — it instantiates a different concern. The checklist's first item at line 79 ("Create pressure scenarios (3+ combined pressures)") sets up the synthetic-baseline method; the `**Example:**` block then implements that method in 24 lines of scenario construction. DR3 displaces the synthetic-scenario method from RED's primary role (replacing it with conversation-precedent), which means the coupling between the checklist's method-assumption (line 79) and the example block's method-instantiation (lines 85-108) is exactly the entanglement Phase 3 must untangle. The two responsibilities — scenario-agnostic process steps and synthetic-baseline illustration — sit inside one flat section with no structural boundary between them.
- **Structural impediment:** Phase 3 cannot cleanly prepend the conversation-precedent protocol to the RED checklist (lines 77-83) without the example block immediately contradicting it: the example demonstrates the synthetic method DR3 is demoting from primary to secondary. Separating the two blocks into named subsections is the prerequisite for the prepend to be a clean in-place edit.
- **Suggested Refactoring:** Move Function (extract the `**Example:**` block into a new H3 subsection within RED; Phase 3 then relocates or demotes that subsection cleanly)

**Finding 1a (second lens, Possible): Divergent Change at RED-section granularity**

- **Smell:** Divergent Change (second lens on Finding 1's coupling)
- **Location:** SKILL.md lines 71-109 (entire RED section)
- **Evidence Grade:** Possible
- **Evidence:** Phase 3 applies two edits to the RED section — prepend conversation-precedent protocol (DR3 facet A) and demote synthetic scenario detail to REFACTOR (DR3 facet B). Both edits descend from a single design decision (DR3, design plan line 208); they land in one phase and plausibly one commit. This is not Divergent Change in the classical sense (changes from unrelated reasons at different times), but the two edits target structurally different content within the same flat section, making them harder to separate cleanly without the H3 split. The coupling identified in Finding 1 is the root cause; this is a second description of the same problem.
- **No separate refactoring action:** The two-H3 split that resolves Finding 1 also resolves this. No additional executor step.

---

### Bloaters

**Finding 2 (context only, out of scope for Phase 2.5): Large Skill Document**

- **Smell:** Large Class (file-level analogue)
- **Location:** SKILL.md (entire file, 421 lines)
- **Evidence Grade:** Demonstrated (wc -l = 421, threshold = 400)
- **Evidence:** File is 21 lines over the 400-line threshold. Phase 3's prepend will add approximately 15-30 lines. Post-Phase-3 the file will be approximately 436-450 lines. The design plan targets ≤550 lines post-Phase-3, so this is within planned budget.
- **Phase-2.5 action: NONE.** This is not a blocker for Phase 2.5 or Phase 3. The Phase-2.5 done-when criteria forbid adding or removing content lines; progressive-disclosure peer-file extraction (DR5) is out of scope here. This measurement informs Phase-3 budget: the pressure-scenario demotion should be a move (not a copy-and-add) to keep the net delta small.

---

**Candidate: Long Method at section level — NOT CONFIRMED**

- **Candidate:** Long Method applied to RED section (lines 71-109)
- **Verdict:** Below threshold. The RED section is 38 lines. The Long Method threshold is >40 lines. The section does not cross the threshold.
- **Evidence:** wc of lines 71-109 = 38 lines. Threshold not met.
- **Why it feels dense:** The section contains two responsibilities in 38 lines (process checklist + scenario example), creating cognitive density disproportionate to line count. The actual smell is Feature Envy (Finding 1). Not reported as a finding.

---

### Phase-3 Edit-Target Notes (not smell findings)

**Note A — Testing Checklist line 339 mirrors RED checklist line 79**

The synthetic-scenario assumption ("Create pressure scenarios (3+ combined pressures)") appears at both line 79 (RED process checklist) and line 339 (Testing Checklist). These are two instances of the same item — below the Rule of Three gate for Duplicate Code, and one item rather than a group (not a Data Clump). The note is structural: when Phase 3 updates the RED checklist (line 79) to reflect conversation-precedent as the primary method, line 339 must be updated in the same commit or the two locations will be inconsistent.

**Note B — RED example block near-duplicates the GREEN great-scenario (Phase-3 hazard)**

The RED example block (lines 88-100) and the VERIFY GREEN "Great scenario" (lines 141-151) share the same framing: dinner at 6:30pm, code review at 9am, A/B/C TDD choice, differing only in 4h-vs-3h and the 200-line detail. Phase 2.5's structural split does not create or resolve this near-duplication — it is a pre-existing condition. But when Phase 3 demotes the RED synthetic scenario toward REFACTOR, it will be positioned closer to or adjacent to the GREEN great-scenario. Phase 3 must decide: merge the two blocks into one canonical scenario, have one cross-reference the other, or leave the near-duplicate in place with a comment acknowledging the overlap. Not fixing this in Phase 2.5 is correct; it is a Phase-3 design question the executor should carry forward explicitly.

---

## No Action Needed

Categories assessed with no findings:

- **Object-Orientation Abusers:** Assessed for Switch Statements, Refused Bequest, Alternative Classes, Temporary Field. Markdown skill file has no class hierarchy; no analogues found. No smells detected.
- **Dispensables — Duplicate Code:** Assessed against Rule of Three gate. The Testing Checklist (lines 339-341) condenses but does not duplicate the RED checklist (lines 77-83); the two instances do not meet the 3+ threshold. No findings. The RED/GREEN scenario near-duplication (lines 88-100 vs 141-151) is also 2 instances, not 3 — no Duplicate Code finding; the near-duplication is flagged as Phase-3 Note B above.
- **Dispensables — Lazy Class:** Assessed. RED section content is substantive — it carries the baseline-testing goal, process, and example. Not under-responsible.
- **Dispensables — Dead Code:** Assessed. All RED section content is referenced by the Testing Checklist. No unreferenced content found within the section.
- **Dispensables — Speculative Generality:** Assessed against design plan. The RED section structure is called for by DR3 and Phase 3's explicit plan. No abstractions present without use cases.
- **Couplers — Message Chains:** No chains found; markdown has no chained method calls.
- **Couplers — Middle Man:** No delegation-only sections found within RED.
- **Couplers — Inappropriate Intimacy:** Assessed for RED section accessing implementation details of other sections. The example block's pressure-scenario content is a conceptual overlap, captured as Feature Envy (Finding 1), not Inappropriate Intimacy.

---

## Deferred (Tier 3)

Smells requiring cross-file or historical analysis (not assessed):

- **Shotgun Surgery** — would require git history showing RED section edits scattered across unrelated commits. Not assessed.
- **Divergent Change (full Tier 3)** — this assessment included a Possible-grade observation (Finding 1a) using design-plan evidence as a second lens on Finding 1. The full Tier 3 smell requires commit-history topic analysis showing unrelated change reasons at different times. That analysis was not performed; the design-plan evidence shows two facets of a single decision (DR3), not independent change histories.
- **Parallel Inheritance** — no inheritance hierarchy present. Not applicable.
- **Insider Trading** — cross-module dependency analysis. Not assessed.
- **Mysterious Name** — cross-file usage context required. Not assessed.
- **Cross-file Duplication** — the pressure-scenario example in RED (lines 85-108) has structural similarity to examples in VERIFY GREEN (lines 139-151) and the Common Mistakes section. A cross-file clone detection pass would be needed for a formal finding. Not assessed here; Rule of Three within-file check showed the patterns are contextually distinct (RED example = failing baseline, VERIFY GREEN examples = passing compliance test).
- **God Module** — full-module cohesion analysis required. Not assessed.

---

## Refactoring Prescription for Phase 2.5

The Phase 2.5 refactor is purely structural: insert two H3 headings within the RED H2 to create explicit subsections, with no text content lines added or removed except the two new headings themselves.

**Prescribed structure after Phase 2.5:**

```
## RED Phase: Baseline Testing (Watch It Fail)

[lines 71-76: goal + TDD rationale — unchanged]

### Basic Baseline Checklist
[lines 77-83: process checklist — unchanged text]

### Synthetic Pressure-Scenario Example
[lines 85-108: example block — unchanged text]
```

This split resolves Finding 1:
- Phase 3 can prepend the conversation-precedent protocol inside `### Basic Baseline Checklist` without touching the scenario example
- Phase 3 can relocate or demote `### Synthetic Pressure-Scenario Example` as a clean block operation
- The two changes become independent edits to distinct named subsections

**Phase-3 Note A (carry forward):** Testing Checklist at line 339 also needs updating when the RED process checklist changes. The line "Created pressure scenarios (3+ combined pressures)" will be inconsistent with a conversation-precedent-leading RED section. Phase 3's executor should update line 339 in the same commit.

**Phase-3 Note B (carry forward):** The RED example block (lines 88-100) near-duplicates the VERIFY GREEN "Great scenario" (lines 141-151) — same dinner/review/A-B-C-TDD framing, differing in 4h-vs-3h and the 200-line detail. Phase 2.5 does not create or resolve this; the near-duplicate predates this refactor. When Phase 3 demotes the RED synthetic scenario toward REFACTOR, the two blocks will be adjacent or in the same vicinity. Phase 3 must decide: merge into one canonical scenario, cross-reference, or leave in place with a comment. Leaving it silently creates a visible duplicate.

**Constraint respected:** Verbatim-preserved blocks (model-tier guidance lines 47-60, "No Blaming the Model" lines 61-69, flaky-result discipline lines 384-389, meta-testing pattern) are not within the RED section (lines 71-109) and are not touched by this prescription.

---

## Summary

- **Total actionable findings:** 1 (the structural split)
- **By grade:** Demonstrated: 1 (out-of-scope measurement), Plausible: 1 (Finding 1, Feature Envy), Possible: 1 (Finding 1a, Divergent Change — second lens on Finding 1, no separate action)
- **By category:** Couplers: 1 actionable (Finding 1); Bloaters: 1 out-of-scope measurement (Finding 2); Change Preventers: 1 Possible second lens (Finding 1a, no separate action)
- **Candidate smells verified:** Feature Envy (confirmed, Plausible — mechanism corrected), Divergent Change (regraded Possible, folded into Finding 1 as second lens, no separate action), Long Method (not confirmed — below threshold at 38 lines)
- **Phase-3 notes carried forward:** Note A (line 339 Testing Checklist mirrors line 79, update in same commit); Note B (RED example near-duplicates GREEN great-scenario, Phase 3 must decide merge/cross-reference/leave)
- **Net Phase-2.5 work:** ONE structural change — insert `### Basic Baseline Checklist` heading before line 77 and `### Synthetic Pressure-Scenario Example` heading before line 85, within the RED H2. No text moved. No content added or removed beyond the two headings.

---

## Peer Review (2026-06-10)

Reviewer: Opus 4.8 (critical-peer-review, falsification-first)
Scope: pipeline step B. Standard checks limited to evidence-grading, overclaiming, Speculative Generality, Rule of Three (per dispatch). ACH / pre-mortem / timeline checks not applied (not a debugging artifact).

**Verdict: PROCEED WITH REVISIONS.** No smell fails falsification outright — the core prescription (split RED into two H3 subsections) is sound, behaviour-preserving, and the minimal change that enables Phase 3. But the report overstates its findings in four specific ways that must be corrected before the refactoring-executor runs, because three of the four findings either misstate their mechanism, overlap, or are misclassified. The executor should act on the **single** structural split; Findings 2, 3, and 4 must not spawn additional edits beyond that split plus one Phase-3 note.

### Verification performed (independently reproduced)

- `wc -l SKILL.md` = 421. Confirmed. Large Class threshold (>400, rubric line 20) exceeded. Finding 3 grade "Demonstrated" is correct per rubric (T1 + tool output = always Demonstrated).
- H2 headings: RED at line 71, GREEN at line 110. Confirmed. RED content = lines 71-109 (sed 71-109 = 39 lines; report's "38 content lines" treats line 109 as the boundary blank before the GREEN H2 — internally consistent, off-by-one is cosmetic).
- Process checklist = lines 77-83. Example block = lines 85-108. Line 79 and line 339 both carry "pressure scenarios (3+ combined pressures)". All confirmed verbatim.
- Design plan DR3 (line 208) and Phase 3 (line 351): the demotion target is **synthetic pressure scenarios as the *primary RED baseline method***, replaced by conversation-precedent. Verified.
- The RED example block (lines 88-100) is a near-duplicate of the VERIFY-GREEN "Great scenario" (lines 141-151): same dinner-6:30 / review-9am / A-B-C-TDD framing, differing only in 4h-vs-3h and the 200-line detail. Reproduced by side-by-side diff.
- Rubric tiers: Feature Envy T2, Data Clumps T2, Divergent Change T3, Large Class T1. Rule of Three gate requires a repeated *group* appearing 3+ times.

### Findings against the report

**H1 — Finding 1 (Feature Envy): smell is real, but the confirmation mechanism is overstated.**
The coupling is genuinely present: the `**Example:**` block (85-108) is a synthetic pressure scenario serving as the RED baseline *method*, sitting under a checklist (77-83) whose first item ("Create pressure scenarios") sets it up. That is a real entanglement and a real Phase-3 impediment. But the evidence sentence "Phase 3 will demote exactly this content to REFACTOR, which confirms the misplacement" overclaims. DR3 demotes *synthetic-scenario-as-primary-baseline-method*; it does not say this specific worked block moves verbatim to REFACTOR. The pressure-scenario *machinery* the report points to ("developed in VERIFY GREEN, lines 119-187") already lives outside RED — so the block does not "envy" a framework located elsewhere; it instantiates the same method the framework documents. **Corrected language:** drop "Phase 3 will demote exactly this content" and "envies the pressure-scenario section"; state instead that the block embeds the synthetic-baseline method DR3 displaces from RED's primary role, which is why separating it from the checklist makes the DR3 prepend clean. Grade Plausible is correct; the reasoning, not the grade, is the problem.

**H2 — Finding 2 (Divergent Change): two "independent reasons" both descend from a single design decision (DR3); finding overlaps Finding 1 and is over-graded.**
The report's note (line 75) is transparent that it substitutes design-plan evidence for the git history a T3 smell normally needs. But the substituted evidence does not support "two independent axes." DR3 (design plan line 208) is *one* decision that simultaneously (a) introduces conversation-precedent and (b) demotes synthetic scenarios. Both Phase-3 edits land in one phase, from one decision, plausibly one commit. Divergent Change classically means a unit changes for *unrelated* reasons at *different times* — not two facets of one coordinated change. The "neither reason implies the other" claim is false: both are entailed by DR3's single rationale (real evidence over invented scenarios). **GRADE factor — indirectness + imprecision:** evidence is a single design decision, not two independent change histories; downgrade Plausible → Possible. The smell is also largely redundant with Finding 1 (both say "RED mixes checklist and scenario"). **Corrected language:** either fold Finding 2 into Finding 1 as a second lens on the same coupling, or re-grade to Possible and state that the two edits share one root decision. Do not let it justify a *separate* refactoring action — the prescription for Findings 1 and 2 is identically "the two-H3 split," so this is one action, not two.

**H3 — Finding 4 (Data Clump): misclassified to bypass a gate the report already conceded.**
The rubric defines Data Clumps as "same *group* of fields/params repeated" (line 22). Finding 4 is a *single* checklist line mirrored at 79 and 339 — one item, not a group. The report's own "No Action Needed" section (line 122) already assessed these two checklists against the Rule of Three, found "do not meet the 3+ threshold," and declined a Duplicate Code finding — then re-entered the identical two-location observation as a Data Clump. This is relabeling to escape the gate the assessor just applied. **Corrected language:** demote from a "Finding" to what it actually is — a Phase-3 edit-target note: "line 339 (Testing Checklist) mirrors line 79 and must be updated in the same Phase-3 commit when the RED checklist changes." The underlying note is valid and useful; the smell name is not. No Phase-2.5 refactoring action attaches to it.

**M1 — Finding 3 (Large Skill Document): correctly graded Demonstrated, but irrelevant to Phase 2.5's structural-readiness framing and prescribes out-of-scope work.**
The measurement is real (421 > 400). But the report's own structural-impediment text says "this is not a blocker for Phase 2.5 or 3" and "within planned budget" (design plan line 26 confirms ≤550). The framing of this assessment (line 6) is "impediments to the upcoming Phase 3 goal only." A non-blocking measurement does not meet that bar. Worse, the prescription ("Extract Class … delegate the dense block to a supporting peer file per DR5") is a Phase-4-shaped action that the report's own prescription section (line 171) excludes from Phase 2.5 scope, and that the Phase-2.5 done-when criteria forbid ("no content added or removed"). **Corrected language:** keep the measurement as context, but mark it explicitly Out-of-Scope-for-Phase-2.5 / Informs-Phase-3-budget, not a finding the executor acts on. The DR5 peer-file extraction is correctly deferred; saying so in the finding prevents the executor from attempting it.

**M2 — Missed within-RED concern Phase 3 will work around: the RED example near-duplicates the GREEN great-scenario.**
The report flags this in the Deferred section (line 141) and declines a formal finding, calling the two "contextually distinct." That call is defensible (RED = failing-baseline illustration; GREEN = scenario-writing exemplar) and correctly within the Rule-of-Three gate (2 instances, not 3) — I do **not** raise it as a missed smell. But it is under-emphasized as a Phase-3 hazard: when Phase 3 demotes the RED synthetic scenario toward REFACTOR, it will sit beside a near-identical block already in GREEN (141-151). Phase 3 risks creating a visible duplicate or an awkward cross-reference. The Phase-2.5 split does not fix this; it is a Phase-3 design question. **Action:** add one line to the prescription flagging that Phase 3 must decide whether the demoted RED scenario merges with, cross-references, or duplicates the existing GREEN great-scenario.

### Audit questions (per phase file step B)

1. **Are the named smells actually present, or pattern-matching?** Feature Envy: present (coupling is real), mechanism overstated (H1). Divergent Change: weakly present, over-graded, redundant with Feature Envy (H2). Data Clump: not present as classified; it is single-line mirroring, misclassified (H3). Large Class: present and Demonstrated, but not a Phase-3 impediment (M1).
2. **Is the prescription the right one, or would lighter-weight work suffice?** The core prescription (two H3 headings, no text moved) IS the minimal change and is correct. The report inflates this single action into four findings; three of them attach no additional Phase-2.5 work once corrected. Lighter-weight is not available below "one structural split"; the report is heavier than warranted only in *count*, not in prescribed edits.
3. **Smells the assessor missed that Phase 3 works around?** The RED/GREEN scenario near-duplication (M2) — acknowledged but under-weighted as a Phase-3 hazard.
4. **Does the prescription preserve behaviour (Two Hats)?** Yes. Inserting two H3 headings with no content added or removed is purely structural; the done-when criteria (phase_02_5.md lines 102-103) enforce byte-identical verbatim blocks and zero net content change. No semantic change smuggled. RED stays baseline, REFACTOR stays completeness. This is the strongest part of the report.

### Speculative Generality / Rule of Three checks (per dispatch)

- **Speculative Generality:** The report claims none, citing DR3/Phase 3 (line 125). Confirmed against design plan — the two-subsection structure is called for by DR3 + Phase 3. No SG to reject.
- **Rule of Three (Duplicate Code):** The report correctly declined a Duplicate Code finding at the 2-instance RED/Testing-Checklist pair (line 122) and at the RED/GREEN scenario pair (line 141). Both declines are correct. The only Rule-of-Three violation is *internal*: Finding 4 reintroduces a 2-instance duplication the gate already rejected, under a different smell name (see H3).

### Required revisions before the refactoring-executor runs

1. Finding 1: remove the "Phase 3 demotes exactly this block" / "envies VERIFY GREEN" overclaim; restate as the synthetic-baseline method DR3 displaces.
2. Finding 2: re-grade to Possible and fold into Finding 1, OR mark explicitly as a second lens on the same coupling with no separate action.
3. Finding 4: demote from Data Clump finding to a Phase-3 edit-target note (line 339 mirrors line 79).
4. Finding 3: mark Out-of-Scope-for-Phase-2.5; do not action the DR5 peer-file extraction here.
5. Add M2 note to the prescription: Phase 3 must reconcile the demoted RED scenario with the existing GREEN great-scenario (141-151).

After these revisions the executor's actual task is unchanged and minimal: **insert `### Basic Baseline Checklist` and `### Synthetic Pressure-Scenario Example` within the RED H2, move no text, and record the line-339 note for Phase 3.** A full editing pass (per the editing-pass rule) is required on the revised checkpoint, with confirmation, because Findings 1, 2, and 4 cross-reference each other and the summary counts.

### Summary count impact

Report claims 4 findings (1 Demonstrated, 3 Plausible). After review: 1 actionable Phase-2.5 structural finding (the split, supported by the Feature-Envy coupling), 1 Phase-3 note (line 339), 1 out-of-scope measurement (line count), 1 redundant/over-graded finding (Divergent Change). The summary's "by grade" and "by category" lines must be updated to reflect the regrade and the Data-Clump reclassification.
