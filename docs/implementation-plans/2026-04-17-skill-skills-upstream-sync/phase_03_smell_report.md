# Smell Assessment Report — Phase 3

## Phase: skill-skills-upstream-sync Phase 3 (restructure `testing-skills-with-subagents`)
## Files Assessed: 11 files across skills and plan artefacts
## Date: 2026-06-11

---

## Scope Note

All changed files in this phase are Markdown (skills and plan documents). There is
no new executable code except embedded Python verification scripts inside `phase_03.md`
and `phase_05.md` — those scripts are assessed for structural smells where relevant
but are not subject to Tier 1 code metrics (complexipy, line-count thresholds for
code files). The assessment is primarily Tier 2 / LLM-reasoned, applied to document
structure, prose coherence, internal cross-references, and duplication.

Per the assessment brief: preserved blocks in `testing-skills-with-subagents/SKILL.md`
were byte-audited this phase; findings are scoped to what the phase changed or added.

---

## Complexity Measurements

### complexipy (cognitive complexity >15)
No executable source files in this changeset. The embedded Python verification scripts
inside plan documents are short procedural scripts (10-30 lines each); none have
branching complexity that would approach the threshold. Not applicable.

### Line Counts

| File | Lines | Flag |
|------|-------|------|
| `testing-skills-with-subagents/SKILL.md` | 460 | Within normal range for a skill |
| `writing-claude-directives/SKILL.md` | 281 | Clean |
| `exec-refactoring-rubric/SKILL.md` | 262 | Clean |
| `phase_03_red_evidence.md` | 227 | Clean |
| `phase_03_rubric_self_application.md` | 172 | Clean |
| `phase_03.md` | ~540 | Plan document; bloater threshold does not apply |
| `phase_05.md` | ~750 | Plan document; bloater threshold does not apply |
| `uat-requirements.md` | 162 | Clean |
| `issues.md` (ISSUE-10 note) | ~368 | Issues register; not a skill |

No files breach the 400-line code smell threshold for a single unit of guidance. The
primary skill artefact is 460 lines but functions as a structured reference manual
with multiple H2 sections, which is appropriate for the document type.

### Structural Smells (ast-grep)
Markdown documents. Structural rules for code (deep nesting, FCIS, global mutable
state, long parameter lists) do not apply. Not executed.

---

## Findings

### Bloaters

**Finding B1**

- **Smell:** Accretion (Layercake) — partial
- **Location:** `testing-skills-with-subagents/SKILL.md` lines 124-170 (VERIFY GREEN section) and lines 261-312 (Pressure-Scenario Completeness Coverage in REFACTOR)
- **Evidence Grade:** Plausible
- **Evidence:** The VERIFY GREEN section retains an inline "Great scenario" example with a multi-pressure sunk-cost vignette (the "6pm, dinner at 6:30pm, code review tomorrow" scenario, around line 145-157), then points forward to the REFACTOR section with: "The catalogue of pressure types and the criteria for a good scenario now live in the REFACTOR phase's **Pressure-Scenario Completeness Coverage** subsection — pressure scenarios are a completeness tool, so their reference material sits with the REFACTOR work that uses it." The REFACTOR section then provides the Pressure Types table plus Key Elements list. The forward-pointer sentence and the retained inline example both occupy the same functional niche: showing the reader what a good pressure scenario looks like. The inline example is not vestigial (it provides a before/bad/good progression readers need at VERIFY GREEN time), but the forward-pointer clause reads as a disclaimer for content that was moved without fully committing to the move. This is the accretion pattern in mild form: the body of the section was moved, but the old location still carries the example plus an explanatory clause about the move, creating two locations that partially address the same reader need.
- **Suggested Refactoring (Fowler):** Remove Dead Code (for the explanatory pointer clause) combined with Extract Method analogue — consolidate: either keep the full bad/good/great progression inline at VERIFY GREEN where it is first needed (and remove the Pressure Types from REFACTOR as redundant), or move the whole progression to REFACTOR and replace the inline example with a one-line cross-reference. The current hybrid serves both locations weakly. The rubric self-application walk-through named this as V7 ("reading-order inversion") but classified it as cosmetic. The present assessment agrees it is minor but locates it more precisely as a structural accretion seam, not just a cosmetic ordering issue.

---

**Finding B2**

- **Smell:** Accretion (Layercake) — Testing Checklist and Basic Baseline Checklist duplicate the gate
- **Location:** `testing-skills-with-subagents/SKILL.md` — "Basic Baseline Checklist" (RED phase, around line 104-111) and "Testing Checklist (TDD for Skills)" (end of document, around lines 382-404)
- **Evidence Grade:** Plausible
- **Evidence:** The "Basic Baseline Checklist" in the RED phase section contains: "Sourced the RED baseline from an independent session (Conversation-Precedent Protocol — cc-search-chats transcript or user-run fresh session, not invented by the executor)". The terminal "Testing Checklist (TDD for Skills)" repeats the same requirement verbatim as its first RED Phase bullet: "Sourced the RED baseline from an independent session (Conversation-Precedent Protocol — cc-search-chats transcript or user-run fresh session, not invented by the executor)". The duplicate is intentional (a terminal checklist is a standard pattern in discipline-enforcement skills), but the two items are word-for-word identical rather than summary vs. detail. The Rule of Three gate for Duplicate Code requires three instances — only two exist here, so this does not meet the threshold for a Duplicate Code finding. It is recorded here as a Bloater-variant because the section adds volume without adding information.
- **Suggested Refactoring:** The terminal checklist entry is the correct location for the gate. The inline checklist in the RED phase section could be tightened: replace the verbatim repeat with a briefer "Independent-session gate satisfied (see Conversation-Precedent Protocol above)" to avoid two identical instruction blocks in the same document. This is a prose-level edit, not a Fowler structural refactoring.

---

### Object-Orientation Abusers

No findings in this category. The documents do not use conditional branching patterns,
inheritance, or type-dispatch structures. Assessed: presence of repeated conditional
logic in prose (e.g., "if X do Y, if Z do W" patterns that could be unified) — none
found that meets the evidence threshold.

---

### Change Preventers

Tier 3 — deferred. See Deferred section.

---

### Dispensables

**Finding D1**

- **Smell:** Duplicate Code — qualifying-criteria checklist appears in two locations
- **Location:** `testing-skills-with-subagents/SKILL.md` Conversation-Precedent Protocol (around lines 88-95, the five-item qualifying checklist) and the Testing Checklist at the end of the document (the RED Phase checklist item, around line 386) plus `phase_03.md` Task 1 Step 1 (the qualifying-hit criteria block, around lines 119-124 of that document)
- **Evidence Grade:** Possible
- **Evidence:** The qualifying-criteria checklist (observed-not-described, independent-of-this-session, in-scope, externally-confirmed, not-self-licensing) appears fully in the SKILL.md Conversation-Precedent Protocol section. A shorter paraphrase of the same criteria appears in `phase_03.md` as "Qualifying-hit criteria" — but `phase_03.md` is a historical plan document, not a living skill, so drift between it and the SKILL.md is expected and acceptable. The Rule of Three gate is not met (two skill-file instances at most). Below threshold for a Duplicate Code finding. Recorded as Possible because if Phase 4 or Phase 6 adds a third skill that cross-references these criteria, the pattern would cross the threshold and warrant extraction.

---

**Finding D2**

- **Smell:** Dead Code — if-unavailable clause placement creates an instruction seam
- **Location:** `testing-skills-with-subagents/SKILL.md` Conversation-Precedent Protocol, path 1, around line 85: "If `cc-search-chats` is unavailable in this session, skip directly to path 2 — do not reconstruct transcripts from memory."
- **Evidence Grade:** Plausible
- **Evidence:** The clause is correct guidance (V6 fix from the rubric self-application). However, it is placed as a parenthetical at the end of the first bullet of the two-path list, rather than as a gate at the top of the protocol. A reader following the protocol in order encounters "1. Prior conversation transcript retrieved via cc-search-chats:search-chat" and must read to the end of that bullet before learning that cc-search-chats availability should have been checked before starting path 1. The gate fires too late relative to when the reader needs it. This is a Dispensable (dead from the reader's perspective because it arrives after the decision point it guards) in the prose-structure sense.
- **Suggested Refactoring:** Move the if-unavailable clause to the top of the protocol as a preflight: "Check whether `cc-search-chats:search-chat` is available in this session. If it is, follow Path 1. If it is not, skip to Path 2." This removes the parenthetical from inside Path 1's description and makes the branching logic explicit before either path is described. Equivalent to Introduce Guard Clause (Fowler) applied to prose structure.

---

**Finding D3**

- **Smell:** Dead Code — stale Haiku-4.5 model anchor without dating mechanism
- **Location:** `testing-skills-with-subagents/SKILL.md` GREEN Phase Model section, around lines 62-63: "operator experience (2026-04-22) is that Haiku 4.5 is unsuitable for any task requiring judgement"
- **Evidence Grade:** Possible
- **Evidence:** The rubric self-application walk-through named this as V5 ("inline model anchors in SKILL.md violate R6 — no dated supporting file / staleness tripwire for this skill"). The operator-empirical claim is dated inline (2026-04-22), which provides better temporal grounding than an undated assertion. However, the same claim also references `model-tier-notes.md` as the authoritative per-model file for writing-claude-directives, creating a two-source situation: the claim lives in both this SKILL.md and (by reference) in `model-tier-notes.md`. When `model-tier-notes.md` is updated for a new Haiku generation, this SKILL.md's inline claim will silently diverge. The rubric self-application already recorded this and deferred to Phase 4/5 reconciliation. The assessment agrees with that disposition but records it here as a Possible Dead Code finding (the anchor will become stale code at the next model refresh).
- **Suggested Refactoring:** Replace the inline claim with a reference: "per current model-tier notes (`writing-claude-directives/model-tier-notes.md`), Haiku 4.5 is unsuitable for judgement tasks — the operator-empirical position is documented there with its evidence anchor." This makes `model-tier-notes.md` the single authoritative source and removes the staleness risk from this file.

---

### Couplers

**Finding C1**

- **Smell:** Message Chains / inappropriate cross-document dependency — `exec-refactoring-rubric/SKILL.md` References section uses hedge language that partially conflicts with the body's confident citation practice
- **Location:** `exec-refactoring-rubric/SKILL.md` References section, line 254: "Webpages are the sources actually consulted when this rubric was designed (2026-04-08 design sessions); URLs re-verified live 2026-06-11."
- **Evidence Grade:** Possible
- **Evidence:** The References section is a new addition this phase (from the phase brief: "new References section, corrected attributions"). The section introduces a framing sentence that positions the URLs as "sources actually consulted" — a stronger claim about provenance than bibliography entries typically carry. This is not a structural smell in the code-smell sense, but it creates a coupler between this skill's authority and the live availability of four external URLs. If any URL breaks, the "re-verified live" claim becomes a false citation. More concretely: the Parallel Inheritance entry in Part 6 was updated from "Fowler (1999)" to "Fowler's refactoring catalogue (References)" — a correct improvement — but the References section lists the catalogue URL without an access date on the catalogue entry itself (only the design-session date and the re-verification date are given). This is a minor citation-form inconsistency.
- **Suggested Refactoring (prose-level):** Add access dates to each individual URL entry in the References section, not just a blanket re-verification statement. This decouples each citation's verifiability from the blanket statement and follows the convention the Anthropic docs citations in `writing-claude-directives` use ("verified 2026-06-10" per citation).

---

**Finding C2**

- **Smell:** Inappropriate Intimacy — `writing-claude-directives/SKILL.md` Rubric Callback section contains a full rubric summary that is also in `testing-skills-with-subagents/SKILL.md`
- **Location:** `writing-claude-directives/SKILL.md` line 135 (Rubric Callback section) and `testing-skills-with-subagents/SKILL.md` lines 35-36 (Rubric Callback section)
- **Evidence Grade:** Plausible
- **Evidence:** Both sections describe the epistemic-humility rubric's four screens using nearly identical language: "The rubric screens Scope (Jones's three conditions), Observability (form-gate + tautology-screen + named-falsifier), Process (Schön's four questions), and Failure-pattern (four named patterns from AbsenceJudgement); full citations for Jones, Schön, and AbsenceJudgement are in that skill's `absencejudgement-citations.md`." The `writing-claude-directives` version adds one sentence specific to its context (about directive-writing being a "protective belt around a scope decision, not a substitute for it"). The `testing-skills-with-subagents` version adds two sentences specific to its context (about the sunk-cost amplifier and the right next step being to revise scope). The shared rubric-summary sentence is word-for-word identical across both files. This is a two-instance duplicate; it does not cross the Rule of Three gate. However, it establishes the pattern: if `writing-skills/SKILL.md` and a fourth skill each also carry this summary, the pattern will cross the threshold. The Rubric Callback sections are currently tight cross-references, not pure duplicates, which mitigates the smell — but the shared sentence creates a synchronisation burden if the rubric screen names change.
- **Suggested Refactoring:** Extract the shared summary sentence into `epistemic-humility/SKILL.md` itself as an "Overview" or "Screening Summary" that the callback sections point to, rather than repeating it. Each callback section retains its context-specific sentence and cross-references the rubric for the screen names. This is equivalent to Move Function (into the class that owns the data).

---

### Below Threshold (Duplicate Code, Rule of Three not met)

- The qualifying-criteria checklist in `testing-skills-with-subagents/SKILL.md` and `phase_03.md`: two instances, not three. See Finding D1.
- The rubric screen summary in `writing-claude-directives/SKILL.md` and `testing-skills-with-subagents/SKILL.md`: two instances, not three. See Finding C2 — recorded as a Coupler rather than Duplicate Code because the primary concern is synchronisation burden, not extraction opportunity.

---

## Plan Document Structural Assessment

The following findings apply to plan artefacts (`phase_03.md`, `phase_03_red_evidence.md`,
`phase_03_rubric_self_application.md`, `phase_05.md`, `uat-requirements.md`,
`issues.md`). Plan documents are historical records and are not refactored; findings
here are limited to structural problems that would mislead a future reader.

**Finding P1**

- **Smell:** Stale count in prose — `phase_05.md` Done-when section references "≥ 31 commits" as a floor
- **Location:** `phase_05.md`, Done-when section near line 741: "≥ 31 commits (count reconciled during H6 revision 2026-04-19)"
- **Evidence Grade:** Plausible
- **Evidence:** The Phase 3 rubric self-application walk-through explicitly named CA3 as a carry-forward proleptic concern: "three different line counts for the same artefact circulated in prose within days, each stale by the time it was read." The phase_05.md Done-when section documents the fix as a Note: "Phase 5 audits recompute line counts and commit counts from the files and git history at audit time — never from phase-summary prose." That Note appears at line 745 of phase_05.md, immediately after the ≥ 31 figure at line 741 — which means the plan simultaneously gives a count floor AND instructs readers to recompute from git. The count floor is therefore not stale-broken (it will be verified at execution time), but the two consecutive statements create a confusing message: "expect 31 commits" followed by "don't rely on that number." A future reader executing Phase 5 may reasonably ask which instruction governs.
- **Suggested edit:** Replace the numeric floor with a structural description: "Commit history shows the full sync cleanly: Phase 1 (3+ commits), Phase 2 (5+), Phase 2.5 (1+ per smell), Phase 3 (5+), Phase 4 (6+), Phase 6 (6+), Phase 5 (5) — recompute total from `git log` at audit time, not from this prose (CA3 from Phase 3 rubric self-application)." This removes the count floor while preserving the structural breakdown that a reviewer can validate.

**Finding P2**

- **Smell:** Contradictory status — `phase_05.md` CHANGELOG entry says "Haiku struggles with judgement calls" was "removed" in the Fixed section; the actual committed SKILL.md retains and strengthens the claim
- **Location:** `phase_05.md` Task 2 Step 3, CHANGELOG Fixed section, line ~385: "Unsupported 'Haiku struggles with judgement calls' claim in `testing-skills-with-subagents/SKILL.md` removed (not in current 2026-04 Anthropic docs)."
- **Evidence Grade:** Demonstrated
- **Evidence:** The CHANGELOG text was authored before the 2026-04-22 plan-amendment pass that reversed the removal decision. The `phase_05.md` 2026-06-10 Amendment block documents the amendment but does not update the CHANGELOG template text at Step 3. The committed `testing-skills-with-subagents/SKILL.md` line ~63 reads: "operator experience (2026-04-22) is that Haiku 4.5 is unsuitable for any task requiring judgement" — the claim was retained and strengthened, not removed. A future executor following `phase_05.md` Task 2 Step 3 verbatim will write a CHANGELOG entry that says the claim was "removed" when it was retained. This is a direct contradiction between the plan template and the implemented artefact.
- **Suggested edit:** Update the CHANGELOG Fixed bullet in `phase_05.md` Task 2 Step 3 to reflect the actual outcome: change "Unsupported 'Haiku struggles with judgement calls' claim in `testing-skills-with-subagents/SKILL.md` removed (not in current 2026-04 Anthropic docs)." to "Haiku-judgement claim in `testing-skills-with-subagents/SKILL.md` retained and reframed with operator-empirical anchor (2026-04-22 plan-amendment pass: claim strengthened, not removed; operator position overrides 2026-04 Anthropic marketing framing)." This is the only plan-document finding that reaches "Demonstrated" because the contradiction is verifiable by comparing the CHANGELOG template text to the committed SKILL.md content.

---

## No Action Needed

Categories assessed with no findings:

- **Bloaters — Long Method / Large Class:** No skill file is an unstructured monolith. `testing-skills-with-subagents/SKILL.md` at 460 lines is within reasonable range for a multi-section reference skill; it has clear H2 section boundaries. Not a Large Class analogue.
- **Object-Orientation Abusers — Switch Statements:** No repeated type-dispatch conditionals found in skill prose. Where conditional branching appears ("if cc-search-chats is unavailable... else...") it is a single well-bounded decision, not a repeated pattern.
- **Object-Orientation Abusers — Temporary Field / Refused Bequest / Alternative Classes:** These code-smell categories do not have document-level analogues that apply here.
- **Dispensables — Lazy Class:** All sections in the changed skills carry substantive guidance. No section is a thin wrapper over another section's content.
- **Dispensables — Speculative Generality:** The Rubric Callback sections cross-reference `denubis-extending-claude:epistemic-humility`, which exists on disk (Phase 1 produced it). The Conversation-Precedent Protocol references `cc-search-chats:search-chat` and `denubis-plan-and-execute:systematic-debugging`, both documented as installed. No phantom abstractions detected.
- **Couplers — Feature Envy:** The skills stay on their own subject matter. No section borrows heavily from a sibling skill's content rather than staying in its own domain.
- **Couplers — Middle Man:** No skill section is a pure relay to another skill with no added content.
- **Couplers — Message Chains:** No chained cross-reference chains (A → B → C → D) detected that require resolving through multiple documents to reach actionable guidance.

---

## Deferred (Tier 3)

Smells requiring cross-file or historical analysis (not assessed):

- **Shotgun Surgery** — whether changes to the Conversation-Precedent Protocol require simultaneous edits to `writing-claude-directives`, `phase_03.md`, and `uat-requirements.md` — requires git history analysis across the full plan lifecycle.
- **Divergent Change** — whether `testing-skills-with-subagents/SKILL.md` is accumulating unrelated responsibilities across phases (RED evidence gate + model-tier guidance + letter-vs-spirit + meta-testing + rubric callback) — requires commit frequency classification across all six phases.
- **Parallel Inheritance** — not applicable to this document set.
- **Insider Trading** — cross-plugin dependency structure between `denubis-extending-claude` skills and `denubis-plan-and-execute` skills — requires import/invocation graph analysis across the full plugin ecosystem.
- **Cross-file Duplication** — whether the rubric-callback boilerplate and the qualifying-criteria language appear in more than two skills across the full `denubis-extending-claude` plugin — not assessed here; requires full-plugin scan.
- **God Module** — whether `testing-skills-with-subagents/SKILL.md` is becoming a catch-all for skill-testing methodology, model-tier guidance, and anti-rationalization discipline — requires cohesion analysis across all six phases' additions.

---

## Summary

- **Total findings:** 9 (6 skill-file findings + 2 plan-document findings + 1 below-threshold recorded)
- **By grade:** Demonstrated: 1 (P2 — CHANGELOG contradiction); Plausible: 5 (B1, B2, C1, C2, P1); Possible: 3 (D1, D2, D3)
- **By category:** Bloaters (Accretion/Layercake): 2 (B1, B2); Dispensables: 3 (D1, D2, D3); Couplers: 2 (C1, C2); Plan-structural: 2 (P1, P2)

### Priority order for action

1. **P2 (Demonstrated)** — The `phase_05.md` CHANGELOG template says the Haiku claim was "removed" when it was retained and strengthened. A future executor will write a false CHANGELOG entry. Fix the template text before Phase 5 executes.
2. **D2 (Plausible)** — The if-unavailable guard in the Conversation-Precedent Protocol fires after the decision point it guards. One-sentence move to top of protocol.
3. **B1 (Plausible)** — The VERIFY GREEN forward-pointer plus retained inline example creates a split-location reader experience for pressure-scenario material. Commit to one location.
4. **C2 (Plausible)** — Two-instance shared rubric-summary sentence across `writing-claude-directives` and `testing-skills-with-subagents`. Below Rule of Three threshold now; flag for Phase 4 so a third instance does not silently cross it.
5. **D3, P1, B2, C1** — Lower priority; each has a self-contained edit path documented above.
