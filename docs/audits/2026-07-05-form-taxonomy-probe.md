<!-- Provenance: operator-commissioned 2026-07-05 during the Phase 4 V1–V7 disposition
     ("go launch a subagent to see where our advice fails"). Produced by a single
     denubis-basic-agents:opus-general-purpose dispatch, read-only, against the
     denubis-extending-claude skills corpus at commit dd37aff; taxonomy lens is
     obra/superpowers' "Match the Form to the Failure" (obra-observed, unpublished —
     hypothesis lens, not established fact; see phase_04_true_up_sweep.md 2026-07-05
     dated append). Findings are INPUT to the queued obra-import work item, not yet
     dispositioned — except: the writing-skills C6 finding ("Re-test until bulletproof")
     was already remediated same-day in aae5aef, and line numbers throughout reference
     the pre-remediation state. This probe also caught the CLAUDE_MD_TESTING duplicate
     (consolidated d3cc5c7) — see its closing note. -->

# Form-Taxonomy Probe — denubis-extending-claude skills vs obra "Match the Form to the Failure"

**Date:** 2026-07-05
**Corpus root:** `plugins/denubis-extending-claude/skills/`
**Taxonomy:** obra/superpowers "Match the Form to the Failure" (2026-05/06), plus the supporting rules (no-nuance-clauses, exemption-clauses-don't-scope, prohibitions-aimed-at-shaping-backfire *as a hypothesis lens*).

Categories flagged:
1. **Prohibition-on-shaping-problem** — "don't/never X" aimed at output *shape* or *omission* rather than a discipline violation (highest interest; backfire risk).
2. **Nuance clause** — a rule softened inline ("usually", "unless", "where appropriate") instead of a separate observable-predicate conditional.
3. **Exemption clause** — a carve-out that can't actually scope.
4. **Prose-reminder-where-slot-belongs** — a required element enforced by nearby prose/checklist instead of a REQUIRED slot in the template it fills.
5. **Soft-guidance-on-discipline-rule** — "prefer/consider" phrasing on something that is actually a rule the agent will be pressured to break.
6. **Vibes exit criterion** — a completion condition with no falsifier.

---

## Summary table (counts per category per file; only files with ≥1 finding shown)

| File | C1 | C2 | C3 | C4 | C5 | C6 | Total |
|---|---|---|---|---|---|---|---|
| `writing-claude-directives/SKILL.md` | 1 | 2 | 0 | 0 | 0 | 0 | 3 |
| `writing-skills/SKILL.md` | 1 | 0 | 0 | 1 | 0 | 1 | 3 |
| `testing-skills-with-subagents/SKILL.md` | 0 | 2 | 0 | 0 | 0 | 0 | 2 |
| `creating-an-agent/SKILL.md` | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| `maintaining-a-marketplace/SKILL.md` | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| **Totals** | **3** | **4** | **0** | **2** | **0** | **1** | **10** |

Grading is inside each finding (HIGH / MODERATE / LOW). Several C2 and one C4 are LOW/borderline; they are counted for honesty, not padded into severity.

**Wholly clean under the six categories:** `epistemic-humility/SKILL.md`, `creating-a-plugin/SKILL.md`, `maintaining-project-context/SKILL.md`, `syncing-with-upstream/SKILL.md`, `writing-claude-md-files/SKILL.md` (one non-category cross-consistency note), `writing-claude-directives/long-running-state-patterns.md`, `writing-claude-directives/model-tier-notes.md`.

**No directive content (not scored):** `epistemic-humility/self-application.md` (reflective walk-through), `epistemic-humility/absencejudgement-citations.md` (citation base), `writing-skills/README.md` (provenance note).

**Excluded — obra provenance (per lead + file self-labels):** `writing-skills/anthropic-best-practices.md`, `writing-claude-directives/graphviz-conventions.dot`, `writing-skills/render-graphs.js` (named skip-list); plus `writing-skills/examples/CLAUDE_MD_TESTING.md` and `testing-skills-with-subagents/examples/CLAUDE_MD_TESTING.md` (obra-authored worked examples, self-labelled "illustrative, not discipline-enforcing"; see note at end).

---

## Top 5 by backfire risk

1. **`writing-claude-directives/SKILL.md` lines 219–227 — Overengineering Prevention block (C1, HIGH).** A prohibition list against output bloat, in the very skill that authored the "Positive > Negative framing" principle. Classic backfire shape; self-contradiction.
2. **`writing-skills/SKILL.md` lines 117–120 — Anti-Patterns list (C1, MODERATE).** A four-item "don't do these to your skill" list about output shape (examples, flowcharts, labels) where a positive "what a good example/flowchart is" recipe belongs.
3. **`maintaining-a-marketplace/SKILL.md` line 83 — "Fields that DO NOT exist (do not invent these)" (C1, LOW, mitigated).** Names the exact confabulated tokens; per the hypothesis, naming forbidden fields can seed them. Mitigated by the adjacent positive schema.
4. **`testing-skills-with-subagents/SKILL.md` line 94 — self-licensing escape (C2, MODERATE).** A nuance clause ("state explicitly why it still counts") inside the anti-self-licensing RED-baseline gate — it reopens the one gate whose whole job is to refuse author-sourced evidence. Different mechanism from C1 backfire, but high integrity impact.
5. **`writing-skills/SKILL.md` line 147 — "Re-test until bulletproof" (C6, LOW–MODERATE).** A checklist exit whose falsifier lives only in a sibling skill; read locally it is a vibes exit. Mitigated because `testing-skills` does define "bulletproof" operationally.

---

## Per-file findings

### `writing-claude-directives/SKILL.md`

This is the meta-skill on directive phrasing. It states the correct principle at lines 13–14 — **"Positive > Negative framing.** 'Don't do X' triggers thinking about X (pink elephant problem). Say what TO do, not what to avoid."** — and its Anti-Rationalization template (lines 254–262, a Red-Flags/rationalization block explicitly "For discipline-enforcing directives") is a CORRECT instance of the taxonomy's discipline form. The findings below are where the skill departs from its own principle.

**C1 — Prohibition-on-shaping-problem (HIGH).** Lines 219–227, the "Overengineering Prevention" template block that authors are told to insert. Verbatim (the prohibition sentences):
> line 222: `Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up. A simple feature doesn't need extra configurability.`
> line 224: `Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs). Don't use backwards-compatibility shims when you can just change the code.`
> line 226: `Don't create helpers, utilities, or abstractions for one-time operations. Don't design for hypothetical future requirements. The right amount of complexity is the minimum needed for the current task. Reuse existing abstractions where possible and follow DRY.`

Overengineering is a *wrong-shape output* problem (the taxonomy lists "bloated" under that row), and `model-tier-notes.md` frames it as an unbidden model *tendency* at high effort (Opus 4.8 / Fable "may add extra files, abstractions, or defensive error handling"), not a known-rule-violated-under-pressure discipline lapse. So the taxonomy prescribes a positive recipe; the block is prohibition-led ("Don't add… / Don't create… / Don't design…"), which also contradicts this skill's own line 13 principle and is the exact shape the backfire hypothesis warns about.
*Charitable reading:* one could frame overengineering as a discipline lapse (agent knows better, over-reaches under effort-pressure), which would license a prohibition; and the block already embeds the positive core ("The right amount of complexity is the minimum needed for the current task. Keep solutions simple and focused."). *Replacement sketch:* lead with the positive contract — "Make exactly the change the task requires and stop. Complexity ceiling = the minimum for the current task; reuse existing abstractions; validate only at system boundaries." — and demote the "Don't…" items to at most a short red-flag tail.

**C2 — Nuance clause (LOW, ×2).**
- Line 135 (Rubric Callback): `If the artefact under review fails any screen, the right next step is usually to revise the scope, not to write stronger directives`. The inline **"usually"** softens a should-rule without an observable predicate for the exception. *Replacement sketch:* make the exception a named conditional — "revise scope, unless the failing screen is Process and the author records a specific reflective reason; then re-test."
- Line 244 (Common Mistakes): `| Multiple valid approaches | Pick one default, escape hatch for edge cases |`. Endorses an "escape hatch" without requiring it be a conditional keyed to an observable predicate — i.e. it green-lights the nuance-clause pattern the taxonomy warns against. *Replacement sketch:* "Pick one default; add exceptions only as conditionals on an observable predicate."

**Deliberately NOT flagged (correct under taxonomy):** the "Escalation: Imperatives (Use Sparingly)" section (lines 94–108) correctly distinguishes rhetorical emphasis (dial back) from true boundaries (keep `Never commit secrets…`) — a conditional on an observable predicate; the "By Skill Type" table (lines 119–123) is a conditional on skill type; the Anti-Rationalization Red-Flags template is the correct discipline form.

---

### `writing-skills/SKILL.md`

**C1 — Prohibition-on-shaping-problem (MODERATE).** Lines 117–120, the Anti-Patterns list. Verbatim:
> line 117: `- **Narrative example:** "In session 2025-10-03, we found..." (too specific, not reusable)`
> line 118: `- **Multi-language dilution:** example-js.js, example-py.py (mediocre quality, maintenance burden)`
> line 119: `- **Code in flowcharts:** Can't copy-paste, hard to read`
> line 120: `- **Generic labels:** helper1, step3 (labels need semantic meaning)`

These target the *shape* of the skill the author produces (examples, flowcharts, labels) — the wrong-shape-output row, whose right form is a positive recipe. Presented as a standalone prohibition list rather than folded into "what a good example / flowchart / label IS." Backfire risk is moderate (terse labels + rationale, not bare "never X"), and the positive counterpart is partly present elsewhere ("One excellent example (not multi-language)", line 141). *Replacement sketch:* a positive "Examples & diagrams" recipe — "One reusable example: a general technique, not a dated session, in a fenced code block, with semantically-named labels; flowcharts carry decision labels, not code."

**C4 — Prose-reminder-where-slot-belongs (LOW/weak).** The checklist requires `One excellent example (not multi-language)` (line 141), but the "SKILL.md Template" (lines 73–95) has no example slot, and the Directory Structure calls `examples/` "Optional" (line 61-ish). The required-by-checklist element is enforced by prose/checklist, not by a slot in the template — and the template's silence conflicts with the checklist's requirement. Weak because examples are declared optional. *Replacement sketch:* if an example is required, add a `## Example` slot (or an explicit "example optional for reference skills; required for technique/discipline skills") to the template so the requirement lives where the author fills it.

**C6 — Vibes exit criterion (LOW–MODERATE).** Line 147 (REFACTOR checklist): `- [ ] Re-test until bulletproof`. Read within this file, "bulletproof" has no local falsifier. It IS defined operationally in `testing-skills-with-subagents` ("When Skill is Bulletproof" / "Not bulletproof if"), so this is mitigated, but the checklist item does not point there. *Replacement sketch:* key the exit to the observable signs — "Re-test until the agent chooses the correct option under maximum pressure and surfaces no new rationalisation (see testing-skills-with-subagents → 'When Skill is Bulletproof')."

**Deliberately NOT flagged (correct):** line 17 "Iron Law: No skill without a failing test first" and line 105 "'I'm only editing, not creating' is not an exit …" are discipline rules in correct (positive/anti-rationalisation) form; the rubric-gated "re-scope, not author" (lines 42, 101) is a conditional on an observable predicate (rubric screen failure) and is stated hard here (no "usually").

---

### `testing-skills-with-subagents/SKILL.md`

A discipline skill, prohibition-dense by design — and mostly CORRECT: "Delete means delete. No exceptions" (lines 214–221), the rationalization table + Red-Flags scaffolding (lines 224–238), "Never conclude 'the model is the problem.'" (line 73), "Never silently move on from inconsistent results." (line 437) all target known-rule-violated-under-pressure and are the taxonomy's right form. Only the following depart.

**C2 — Nuance clause (MODERATE).** Line 94, inside the RED-baseline qualifying checklist:
> `- [ ] **Not self-licensing.** The evidence does not originate from the skill's own authoring or testing process. If only process-adjacent evidence exists, state explicitly why it still counts, grade it as weaker, or prefer path 2.`

The clause **"state explicitly why it still counts"** is a judgment-based escape on the one gate whose purpose is to refuse author-sourced (self-licensing) evidence. It reopens exactly the negotiation the gate exists to close — an author who wants to proceed will "explain why it still counts." *Replacement sketch:* make it a hard conditional on an observable predicate — "Process-adjacent evidence never satisfies this gate on its own; if it is all you have, go to path 2 (user-run fresh session) or halt." Keep "grade it as weaker" only for evidence that already clears an *external* corroborator.

**C2 — Nuance clause (LOW).** Line 36 (Rubric Callback): `If the skill-under-test fails any screen, the right next step is usually to revise the skill's scope, not to invest in testing it`. Same inline **"usually"** softener as the writing-claude-directives callback. *Replacement sketch:* as above — name the exception as a conditional rather than hedging with "usually."

**Noted, NOT counted (C6 defended):** "bulletproof" recurs as an exit term but is defined operationally in this file (lines 340–353: observable "Signs" and "Not bulletproof if" falsifiers), so it is not a vibes exit here. The gap is only that the *writing-skills* checklist (line 147) reuses the term without pointing to this definition — captured under writing-skills C6.

**Additional (out-of-taxonomy) note:** lines 55 and 71 name `AskUserQuestion` with no stated fallback, which this repo's own `writing-claude-directives` rule (lines 129–131: "A directive that names a harness tool … must state the fallback when the tool is absent") requires. A self-consistency gap, not one of the six categories.

---

### `creating-an-agent/SKILL.md`

**C4 — Prose-reminder-where-slot-belongs (MODERATE–LOW).** The base agent template (lines 41–60) contains only `name / description / tools / model` frontmatter plus `## Responsibilities` and `## Workflow`. But the checklist treats two further sections as required:
> line 325: `- [ ] Output format defined`
> line 326: `- [ ] Constraints/limitations stated`

`## Output Format` (a positive recipe — "state what the output IS, its parts, in order") and `## Constraints` are taught only in prose (lines 148–170) and enforced by the checklist, not present as slots in the template the author copies; the worked examples are themselves inconsistent (Code Reviewer has Output Format, no Constraints; Implementor has Constraints, no Output Format). *Replacement sketch:* add `## Output Format` and `## Constraints` slots (with placeholder guidance) to the base template at lines 41–60 so the required elements are filled in, not remembered.

**Deliberately NOT flagged (correct):** the Implementor example's `## Constraints — Never write implementation before test …` (lines 299–303) is a discipline/permission boundary in correct form; the recommended `## Output Format` section is itself the taxonomy's positive-recipe form for wrong-shape output.

---

### `maintaining-a-marketplace/SKILL.md`

**C1 — Prohibition-on-shaping-problem (LOW, mitigated).** Line 83:
> `**Fields that DO NOT exist** (do not invent these): `displayName`, `installUrl`, `path`, `marketplace` (as wrapper object)`

A "do not invent these" prohibition that names the specific confabulated tokens — per the backfire hypothesis, enumerating forbidden field names can seed them. Strongly mitigated: the authoritative positive schema (the valid required/optional field lists) sits directly above at lines 72–81, and the Common Mistakes row ("Inventing schema fields → Only use fields from the schema above", line 221) redirects positively. It reads as a targeted anti-confabulation correction of a known failure, backed by a positive contract. *Replacement sketch (optional):* drop the enumerated non-existent names, or move them to a collapsed "if validation complains about an unknown field, it is not in the schema above" note, so the positive schema stays the only field list the author sees.

**Deliberately NOT flagged (correct):** the Release Checklist (lines 103–110) and "All three MUST show the same version string." (line 137) are structural/operational checks bound to named files — the correct form for an omission/consistency failure.

---

## Clean files (verified, one line each)

- **`epistemic-humility/SKILL.md` — CLEAN and exemplary.** Its screens are the taxonomy's target forms: Screen 1 Form-gate (line 47) is a positive contract ("either actor + action … or an operational check bound to a *named* command"), Screen 3 Named-falsifier (line 51) is an observable-predicate conditional. The Process section's "If a reader can apply Process with no discomfort, they have not applied Process" (line 75) is *designed*-subjective and self-acknowledged (see `self-application.md`), not an accidental vibes exit. Line 36's "do not compress to 'bounded and reversible'" is an anti-drift fidelity guard on a quotation, not a shaping prohibition.
- **`creating-a-plugin/SKILL.md` — CLEAN.** Reference skill; "Don't create a plugin for" (lines 13–16) and Common Mistakes (lines 487–497) are scoping decisions and troubleshooting with positive fixes.
- **`maintaining-project-context/SKILL.md` — CLEAN.** "Always update when / Never update for" (lines 167–178) are conditionals on observable change-types; "Present findings to human — do not remove permissions without approval" (line 219) is a correct permission boundary.
- **`syncing-with-upstream/SKILL.md` — CLEAN.** The resolution table is explicitly framed "as starting points, not rules" (line 64); "Read every conflict." (line 62) and "Always run with `--dry-run` first" (line 121) are positive/true-boundary cautions.
- **`writing-claude-md-files/SKILL.md` — CLEAN under the six categories.** Freshness date is properly structural (template slot at lines 60/115 + checklist), and "Do NOT use @ syntax … Just name the files" (line 212) pairs the prohibition with a positive alternative. *Non-category note:* "**CRITICAL:** Use Bash to get the actual date." (line 189) is rhetorical emphasis on an ordinary (non-true-boundary) instruction — the exact pattern the sibling `writing-claude-directives` (line 96) says to dial back. Cross-skill consistency, not a taxonomy finding.
- **`writing-claude-directives/model-tier-notes.md` — CLEAN and exemplary.** The Fable cost gate (line 25) is a true-boundary prohibition ("burn real money") with an explicit named falsifier ("only a dated operator note … overturns this rule") — the correct form for both a prohibition and a conditional.
- **`writing-claude-directives/long-running-state-patterns.md` — CLEAN.** Reference patterns; "Common Pitfalls" (lines 189–197) and "Failure Mode Prevention" (lines 88–92) pair each pitfall with a positive prevention.

---

## Note on the excluded obra examples

`writing-skills/examples/CLAUDE_MD_TESTING.md` and `testing-skills-with-subagents/examples/CLAUDE_MD_TESTING.md` are obra-authored (source commit `6fd4507`, imported 2026-06-11), self-labelled "illustrative, not discipline-enforcing." They contain strings that *look* like C1/C6 violations — e.g. Variant C's `THIS IS EXTREMELY IMPORTANT. BEFORE ANY TASK, CHECK FOR SKILLS!` and `If a skill existed for your task and you didn't use it, you failed.` — but these are **documentation variants under test** (a NULL/A/B/C/D comparison harness), i.e. test *stimuli*, not denubis guidance. The testing-skills copy diverges from the writing-skills copy only by (a) dropping the obra frontmatter/denubis-note header and (b) replacing the `<available_skills>` XML example with a denubis correction comment ("that tag does not exist … refer to 'your available skills'"). Both correctly excluded from findings; flagged here only so the provenance and the divergence are on record.
