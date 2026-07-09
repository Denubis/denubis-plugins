# Critical Peer Review: phase_03_smell_report.md

Reviewer: Opus 4.8 (critical-peer-review, falsification-first)
Date: 2026-06-11
Document reviewed: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_smell_report.md`
Changeset: BASE `52578e1` → HEAD `0005296` (14 commits)

## Verdict summary

| Finding | Report grade | Audit verdict | One-line reason |
|---|---|---|---|
| B1 | Plausible | **Verified (but out-of-scope as actionable)** | Forward-pointer + retained example real; but it is V7, operator-acknowledged as cosmetic — re-merge churns reviewed text |
| B2 | Plausible | **Refuted (fabricated quotation)** | The two checklist items are NOT verbatim-identical; report pasted L386 text into both slots |
| D1 | Possible | **Verified** | Two-instance criteria spread real; correctly held below Rule-of-Three; no action proposed |
| D2 | Plausible | **Overclaimed** | Clause exists and is late-placed, but "Dead Code" mislabel; move reopens the deliberate V6 minimal edit |
| D3 | Possible | **Verified** | Inline anchor real; but duplicates the V5 disposition already deferred to Phase 4/5 |
| C1 | Possible | **Verified (mislabelled, cross-plugin)** | Text/line correct; "Message Chains / Inappropriate Intimacy" is the wrong smell; lives in a different plugin |
| C2 | Plausible | **Verified** | Shared clause byte-identical at tss L36 / wcd L135; Rule-of-Three calibration correct |
| P1 | Plausible | **Verified** | Count floor at L741 + recompute note at L745 coexist; confusing-message reading is fair |
| P2 | Demonstrated | **Verified conclusion, Overclaimed evidence** | Fixed bullet (L386) is false vs committed artefact — correct; but two supporting evidentiary claims are wrong |

**Hand to refactoring-executor:** P2 only (and it is a plan-document prose edit, not a code refactor). Every other finding either touches operator-acknowledged/deferred decisions (B1→V7, D2→V6, D3→V5), is below threshold with no action (D1, C2), is a misclassified-but-true note (C1), is refuted (B2), or is a judgement-call prose edit a human should weigh (P1). None of the six skill-file findings should be auto-applied.

---

## Hidden Assumptions (extracted before evaluating evidence)

| # | Assumption in the report | Load-bearing? | Status |
|---|---|---|---|
| A1 | The two RED-baseline checklist bullets are word-for-word identical (B2) | Yes — B2's entire "adds volume without information" claim rests on it | **FALSE.** Byte comparison refutes it. |
| A2 | The phase_05 2026-06-10 Amendment block documents the Haiku amendment (P2 evidence) | No — P2's conclusion survives without it | **FALSE.** That block is about version baselines + Phase 2.6, not Haiku. |
| A3 | The smell-assessor's own brief that "preserved blocks were byte-audited; findings scoped to what the phase changed" | Yes — bounds the whole report | Holds; but the report does not check whether its *fixes* reopen acknowledged dispositions (V5/V6/V7). It treats the rubric self-application as corroboration, not as a record of closed decisions. |
| A4 | Reading-order / placement smells in prose are equivalent to Fowler structural smells (B1, D2) | Partial — drives the "actionable refactoring" framing | Weak. Fowler's "Dead Code" and "Introduce Guard Clause" are being applied by analogy to prose; the analogy is not load-bearing wrong but it inflates Possible/Plausible findings toward an actionability they don't have. |

The report never asks: *does my suggested fix reopen a decision the phase already closed?* That unasked question is the single biggest gap. Three of nine findings (B1, D2, D3) propose edits to text the rubric self-application explicitly dispositioned as acknowledge/defer with operator sign-off (2026-06-11). A refactoring-executor acting on them would churn reviewed, signed-off text.

---

## ACH Matrix — competing readings of the changeset's prose seams

Hypotheses about what the report's nine findings collectively represent:

- **H1:** The changeset has genuine, actionable structural smells the executor should fix now.
- **H2:** The changeset's "seams" are mostly the residue of deliberate, operator-acknowledged design decisions (split material, late-but-minimal V6 clause, deferred V5 anchor) that are out of refactor scope.
- **H3:** The report is padding count (9 findings) by re-classifying already-dispositioned items and one fabricated duplicate.

| Evidence | H1 | H2 | H3 |
|---|---|---|---|
| B2 checklist items are NOT verbatim (L106 vs L386 differ) | − | ? | **+** |
| V7 = B1, operator-acknowledged "cosmetic" (`phase_03_rubric_self_application.md` L133, L155) | − | **+** | + |
| V6 = D2, fixed at gate as minimal clause on operator direction (L132, L163) | − | **+** | + |
| V5 = D3, deferred to Phase 4/5 with pointer (L131, L161) | − | **+** | + |
| P2 Fixed bullet (L386) genuinely contradicts committed SKILL.md L63 | **+** | ? | − |
| C2 shared clause byte-identical, only 2 instances (grep: tss+wcd only) | + | + | ? |
| D1 correctly held below threshold, no action proposed | ? | **+** | + |
| C1 text correct but smell mislabelled + cross-plugin, no functional break | ? | + | + |

**Decision rule (fewest strong contradictions):** H2 survives best. H1 is contradicted by the four strong `−` marks (B2 fabrication, and B1/D2/D3 each re-litigating a closed disposition). The one genuinely actionable item (P2) is a plan-document contradiction, which is real but is *not* a smell in the changed skills — it sits orthogonal to H1's "the changeset has smells" framing. H3 (padding) is partly supported but uncharitable: most findings are honestly graded low and several explicitly say "below threshold / no action," which is not what padding looks like.

**Conclusion:** The report is a competent, mostly honestly-graded scan whose central defect is that it does not cross-check its suggested fixes against the phase's own acknowledgement/amendment record, and it contains one fabricated-quotation finding (B2).

---

## Findings

### High (count: 2)

**H-1 — B2 is built on a fabricated quotation. Refuted.**
- **Issue:** B2's load-bearing claim is that the RED-phase "Basic Baseline Checklist" bullet and the terminal "Testing Checklist" bullet are "word-for-word identical." They are not.
- **Evidence (actual bytes):**
  - L106: `- [ ] **Source the RED baseline from an independent session** (Conversation-Precedent Protocol above) — a \`cc-search-chats\` transcript of a real failure, or a user-run fresh-session scenario; not invented by this executor`
  - L386: `- [ ] Sourced the RED baseline from an independent session (Conversation-Precedent Protocol — cc-search-chats transcript or user-run fresh session, not invented by the executor)`
  - Differences: verb ("Source" vs "Sourced"), parenthetical ("Protocol **above**" vs "Protocol —"), body phrasing (full "a transcript of a real failure, or a user-run fresh-session scenario" vs compressed "cc-search-chats transcript or user-run fresh session"), article ("**this** executor" vs "**the** executor"), and bold/plain markup. They are summary-vs-detail, which is exactly the pattern B2 claims they are *not*.
  - The report's Evidence block quotes the *same string twice* (the L386 text) and attributes it to both locations. That string does not appear at L106 at all.
- **GRADE factors:** Risk of bias (the quotation was not read from the file — it was pasted), Indirectness (the "verbatim" claim is the evidence, and it is false). Downgrade from Plausible to **Refuted**.
- **Ripple:** B2 feeds the Summary ("Bloaters: 2") and the priority-order tail ("B2" at item 5). Both must drop B2. The "Below Threshold" section does not cite B2, so no ripple there.
- **Corrected language:** Either delete B2, or re-state it honestly: "The terminal checklist summarises the RED-phase gate; the two phrasings are summary-vs-detail, which is the intended pattern for a discipline-skill terminal checklist. No finding." A summary-vs-detail relationship is the *correct* form, not a Bloater.
- **Location:** report Finding B2; SKILL.md L106 vs L386.

**H-2 — P2 conclusion is correct and Demonstrated, but two supporting evidentiary claims are false, and it misses the strongest evidence (an in-document contradiction).**
- **Issue:** P2 correctly identifies that the CHANGELOG Fixed bullet at `phase_05.md` L386 ("...claim... removed") contradicts the committed `testing-skills-with-subagents/SKILL.md` L63 ("operator experience (2026-04-22) is that Haiku 4.5 is unsuitable for any task requiring judgement" — retained and strengthened). That conclusion is verified three ways: SKILL.md L63; phase_03.md 2026-06-10 Amendment + Task 2 Step 2 (L176–186) + Done-when L529 + commit `7d727b8`/`6b2dc70`; and the rubric self-application V5 framing. A verbatim executor of phase_05 Task 2 Step 3 would indeed write a false "removed" CHANGELOG entry. **Direction confirmed — fix the template, do not "fix" it back to "removed."**
- **But the evidence is overclaimed in two places:**
  1. P2 says: "The `phase_05.md` 2026-06-10 Amendment block documents the amendment but does not update the CHANGELOG template text at Step 3." **False.** The phase_05.md 2026-06-10 Amendment block (L5) is about version baselines and Phase 2.6 in-scope; it never mentions the Haiku reversal. The Haiku amendment is documented in *phase_03.md*, not phase_05.md. (`grep "2026-04-22" phase_05.md` returns only L381 and L597 — neither is an amendment block.)
  2. P2 misses the decisive nearby evidence: phase_05.md **L381** (the Changed section, four lines above the Fixed bullet) *already states the correct outcome*: "Haiku-judgement passage retained and reframed with operator-empirical anchor (amended 2026-04-22 plan-amendment pass — not removed)." The true defect is therefore an **internal self-contradiction within phase_05.md** (L381 correct, L386 stale), not a CHANGELOG-vs-implementation mismatch with no internal warning. The L381 text is also the ready-made template for the corrected Fixed bullet.
- **GRADE factors:** Imprecision (P2 cites one location when the contradiction is visible inside the same document); Reporting bias (it cites the confirming half and overlooks the half that already self-corrects). The *conclusion* stays Demonstrated; the *evidence chain* is downgraded.
- **Ripple:** P2 is item 1 in the priority order and the sole "Demonstrated" in the Summary. Both stand. The suggested edit is sound and should additionally note the L381↔L386 inconsistency so a fixer reconciles both, not just L386.
- **Corrected language:** Keep the suggested edit. Replace the false amendment-block sentence with: "phase_05.md is internally inconsistent: the Changed bullet (L381) correctly says the Haiku passage was *retained and reframed, not removed*, while the Fixed bullet (L386) says it was *removed*. Reconcile L386 to match L381 and the committed SKILL.md L63."
- **Location:** report Finding P2; phase_05.md L381 (correct), L386 (stale), L5 (misattributed amendment block); SKILL.md L63.

### Medium (count: 4)

**M-1 — D2 mislabels the smell and its fix reopens the deliberate V6 minimal edit.**
- **Issue:** D2 calls the if-unavailable clause "Dead Code" and proposes hoisting it to a protocol preflight. The clause is live, correct guidance, not dead. More important: it was added *today* (`7cbc9cc`) as the deliberate, minimal V6 fix on operator direction (`phase_03_rubric_self_application.md` L132, L163). The operator chose the minimal in-path clause and additionally directed that the real remedy is ISSUE-10 path 1 (improve cc-search-chats upstream), not re-documenting workarounds.
- **Evidence:** SKILL.md L85 carries the clause at the end of Path 1; V6 disposition: "**Fixed at gate (2026-06-11) on operator direction** — if-unavailable clause added to protocol path 1." The "Dead Code" label is wrong by the report's own definition (the clause executes for every reader who lacks the tool).
- **GRADE factors:** Indirectness (Fowler "Dead Code" applied by analogy to a live prose clause). Downgrade Plausible → Possible at most.
- **Ripple:** D2 is priority item 2. Demoting it changes the priority order.
- **Corrected language:** "The clause is correctly placed for a minimal targeted edit. A preflight hoist is a legitimate readability preference but reopens an operator-signed V6 decision and is superseded by the directed ISSUE-10 upstream fix. Leave as-is unless the operator reopens it." Do not hand to executor.
- **Location:** report Finding D2; SKILL.md L85; rubric self-application V6.

**M-2 — D3 re-raises the V5 disposition without acknowledging it is already deferred-with-operator-signoff.**
- **Issue:** D3 (inline Haiku-4.5 anchor will go stale) is real and correctly graded Possible. But it is verbatim V5 from the rubric self-application, whose disposition is "Defer to Phase 4/5 reconciliation (rubric-draft pending item 4); record pointer" — acknowledged by the operator 2026-06-11 (L131, L161). D3's own text concedes this ("The rubric self-application already recorded this and deferred to Phase 4/5... The assessment agrees with that disposition"), so the finding is honest, but recording an already-deferred item as a fresh finding inflates the count and its suggested fix (replace inline claim with a reference) directly contradicts the deferral.
- **Evidence:** SKILL.md L63 (anchor present); rubric self-application V5.
- **Corrected language:** Keep as a pointer to V5, drop the suggested edit (it pre-empts the Phase 4/5 reconciliation the operator chose). Do not hand to executor.
- **Location:** report Finding D3; SKILL.md L63; rubric self-application V5.

**M-3 — C1 is true but mislabelled and lives in a different plugin than the header implies.**
- **Issue:** C1's text is accurate (exec-refactoring-rubric L254 reads exactly as quoted; the Parallel Inheritance attribution did change to "Fowler's refactoring catalogue (References)"; per-URL entries carry no individual access dates). But the smell label "Message Chains / Inappropriate Intimacy / inappropriate cross-document dependency" is wrong — a References section citing external URLs is neither a message chain (A→B→C→D resolution) nor inappropriate intimacy (reaching into another unit's internals). It is, at most, a citation-form nit. Also, the location header omits the plugin: the file is `plugins/denubis-plan-and-execute/skills/exec-refactoring-rubric/SKILL.md`, a *different plugin* from the B1/B2/C2 findings (denubis-extending-claude). The report never flags this cross-plugin jump.
- **Evidence:** `git diff` confirms the References section and attribution change landed this phase (commit `419e7d0`), so C1 is in-scope. L254 verbatim-confirmed.
- **Corrected language:** Re-file as a Low citation-form note: "per-URL access dates would decouple each citation's verifiability from the blanket re-verification statement." Drop the Coupler/Message-Chains framing.
- **Location:** report Finding C1; exec-refactoring-rubric/SKILL.md L254 (denubis-plan-and-execute).

**M-4 — B1 is verified as a real seam but is operator-acknowledged-cosmetic (V7); the suggested re-merge churns reviewed text and may collide with the embedded verify script.**
- **Issue:** The forward-pointer (SKILL.md L155–159) and the retained "Great scenario" (L141–153) plus the REFACTOR Pressure-Scenario Completeness Coverage (L261–311) do co-occupy the "what a good scenario looks like" niche — the seam is real. But: (a) this is V7, operator-acknowledged as "navigable via pointers; cosmetic" with "no change required" (rubric self-application L133, L155); (b) the split was a *deliberate, script-enforced* Phase 3 design decision — phase_03.md Task 3 moves the pressure material into REFACTOR as "completeness coverage," and the bidirectional pointers (L155–159 forward, L265 back) are the intended navigation. B1's suggested fix ("keep the full progression inline... and remove Pressure Types from REFACTOR" OR "move the whole progression to REFACTOR") would *undo* the AC2.2 demotion the phase was built to achieve. The report is, in effect, flagging the design, which is out of refactor scope.
- **Evidence:** phase_03.md AC2.2 ("Synthetic multi-stressor pressure scenarios are positioned as REFACTOR-phase completeness checks, not primary RED baseline"); Task 3 Step 1; rubric self-application V7 disposition.
- **GRADE factors:** the report itself downgrades V7 from cosmetic to "structural accretion seam" — that re-grading is the overreach. The underlying observation is fine; the escalation to actionable is not.
- **Corrected language:** "Recorded as V7 (operator-acknowledged cosmetic). Re-merging reopens the AC2.2 RED→REFACTOR demotion and the script-enforced no-duplication design. No action." Do not hand to executor.
- **Location:** report Finding B1; SKILL.md L141–159, L261–311.

### Low (count: 1)

**L-1 — Minor line-count and locator drift.**
- SKILL.md is **460** lines (the file's own last line is 461 due to a trailing newline; report's 460 is correct by `wc -l` semantics — no issue).
- D1 cites `phase_03.md` "lines 119–124" for the qualifying-hit criteria; the actual block is L120 ("Qualifying-hit criteria:") — close enough, no material error.
- P1 cites "near line 741" for the ≥31 floor and "line 745" for the recompute note; verified exactly (L741 floor, L745 note). A second ≥31 floor exists at L582 (Task 4 manual checklist) that P1 does not mention — if the floor is replaced per P1's suggested edit, L582 must be updated too. **Ripple P1 missed:** the suggested edit changes only the Done-when floor (L741); the L582 manual-checklist floor would then disagree with it. Flag both or neither.

---

## Verification (independently checked)

- Read in full: the report; `testing-skills-with-subagents/SKILL.md` (460 lines); `phase_05.md` (749 lines); `phase_03.md` (540 lines); `phase_03_rubric_self_application.md` (173 lines); relevant slices of `writing-claude-directives/SKILL.md` and `exec-refactoring-rubric/SKILL.md`.
- `git diff 52578e1 0005296 --stat` and per-file diffs to confirm scope (exec-refactoring-rubric touched via `419e7d0`; SKILL.md restructure via 4 refactor commits).
- Positive-control byte comparison (script `/tmp/exec-2026-04-17-skill-skills-upstream-sync-564e1be7/verify.py`):
  - B2: L106 ≠ L386 (refuted verbatim claim).
  - C2: shared clause `identical shared clause: True` at tss L36 / wcd L135.
  - Shared clause appears in exactly two files (`grep -rl` → tss + wcd only; absent from writing-skills) → C2 Rule-of-Three calibration correct.
  - P2: L381 (correct) and L386 (stale) both present; phase_05 amendment block (L5) does not mention Haiku.
  - D3: SKILL.md L63 anchor present. D2: L85 clause present.
- Confirmed `epistemic-humility/SKILL.md` exists (C2's suggested fix targets a real file).

## Strongest Hypothesis (best-supported finding)

**P2's conclusion** — the phase_05 Fixed bullet (L386) is false against the committed artefact (SKILL.md L63) and against its own Changed bullet (L381). Verified by direct text comparison and triangulated through phase_03's amendment, the commit messages, and the rubric self-application. This is the one finding that should reach a fixer. (Its evidence chain needs the corrections in H-2, but the verdict holds.)

## Weakest Hypothesis (least-supported finding)

**B2** — refuted outright. The "word-for-word identical" claim is a fabricated quotation; the actual lines are summary-vs-detail, which is the correct form for a terminal discipline checklist.

## Pre-Mortem (assume my own verdicts are wrong)

1. *What if B2's items really were meant to be identical and the difference is an unintended drift?* Then B2 should be re-framed as "two phrasings of the same gate drifted — pick one as canonical," which is a *different* (and milder) finding than "adds volume without information," and still not verbatim. Either way the report's stated evidence is false. My refutation of the *quotation* stands; a charitable re-file as "minor phrasing drift, below threshold" is the most B2 can become.
2. *What if the operator wants the V5/V6/V7 dispositions reopened?* Then D2/D3/B1 become live — but that is an operator decision, not a refactoring-executor action. My "do not auto-apply" verdict is about provenance/scope, not about whether the ideas have merit. I have flagged them as operator-reopenable rather than wrong.
3. *What if P2's misattributed amendment block is actually load-bearing for the fix?* It is not — the fix (reconcile L386) is driven by the committed SKILL.md and L381, neither of which I dispute. The misattribution is an evidence-quality defect inside a correct conclusion.

## Diagnostic Timeout (honest self-check)

- *Am I anchored to the report's framing?* I started from its order but verified each quotation against bytes; B2's refutation came from reading the file, not the report.
- *What did I not look for?* I did not re-run the phase_05 embedded audit script or the embedded verify scripts (out of read-only scope and not load-bearing for the nine findings). I did not audit the byte-identicality of the preserved "No Blaming the Model" / flaky-result blocks — the brief states they were byte-audited and no finding touches them.
- *What would change my mind?* For B2: a git-blame showing L106 once carried the L386 text verbatim and the report read a stale revision. I checked the current HEAD bytes; if the report was written against an earlier commit, its quotation might have been true then — but the report's own header dates it 2026-06-11 against HEAD, and B2's suggested fix presupposes the current divergent text. The fabrication reading is the most consistent with the report's own framing.

## Overall Assessment

**NEEDS REVISION before any fix is applied.**

Specific requirements:
1. **Delete or re-file B2** (refuted; fabricated verbatim quotation).
2. **Keep P2's verdict, correct its evidence** (drop the false amendment-block claim; cite the L381↔L386 internal contradiction; have the fix reconcile both L386 and the L582 floor if P1 is also actioned).
3. **Demote D2, D3, B1 to "operator-reopenable, not executor-actionable"** — each reopens a V6/V5/V7 disposition signed off 2026-06-11. Strip their suggested edits from the actionable set.
4. **Re-file C1 as a Low citation-form note** and add the missing plugin path + cross-plugin flag.
5. **Recount the Summary** after B2 drops (Bloaters: 1, not 2; total honest findings: 8, of which exactly 1 — P2 — is executor-actionable, and it is a plan-document prose edit).

**Subset to hand to a refactoring-executor:** P2's template edit to `phase_05.md` (reconcile the Fixed bullet at L386 to the Changed bullet at L381 and committed SKILL.md L63). Nothing else. No suggested fix touches a byte-audited preserved block, but B1/D2/D3 each reopen an operator-acknowledged decision and must not be auto-applied.
