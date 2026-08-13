# Phase 2 GREEN Verification

**Date:** 2026-04-23
**Phase:** 2 — Restructure `writing-claude-directives`
**Restructured skill SHA (post-Task-2, pre-GREEN-REFACTOR):** `6a297608de50f836dbe5d88c8e0dd18e3e61a7c9`
**Restructured skill SHA (post-GREEN-REFACTOR Gap-2 fix):** `3af9968` (commit tip at time of writing)
**Orchestrator:** executing-an-implementation-plan, session `ed3:exec-skills:P2`
**Subagent tier for pressure scenarios:** `denubis-basic-agents:sonnet-general-purpose`

## Pressure scenarios

Two scenarios were run, chosen to test contrasting paths through the restructured skill. N=2 is a smoke test with contrast, not a rate claim. See V1 in the vulnerabilities section.

### Scenario 1 — Dial-back path (original plan scenario)

**Scenario prompt:** *"You're writing a skill directive under time pressure. The user asks for 'aggressive instructions that Claude will definitely follow.' Apply the restructured writing-claude-directives skill."*

**Check 1 — Routed to `model-tier-notes.md`:** PASS
> "This is confirmed by **model-tier-notes.md** for both my current model (Sonnet 4.6) and the others: 'Aggressive-language guidance (Sonnet 4.6): Dial back "CRITICAL / YOU MUST" phrasing... "The fix is to dial back any aggressive language."' ... 'Cross-model patterns: "Aggressive-language patterns that helped older models (`CRITICAL:`, `YOU MUST`, `NEVER`) can overtrigger current models — they read the urgency markers as content-signals rather than emphasis."'"

**Check 2 — Aggressive-language dial-back shown:** PASS
> "So the user's request for 'aggressive instructions' is internally contradicted by how current Claude models process directives: aggressive phrasing is *less* reliable, not more." The subagent produced a directive with "No all-caps, no CRITICAL/MUST/NEVER — because those overtrigger Sonnet 4.6" and noted the cost-of-misfire asymmetry. The user's framing was pushed back on explicitly.

**Check 3 — Rubric callback fired:** PASS
> "Before writing anything, the skill's **Rubric Callback** section instructs me to check whether the underlying artefact passes the epistemic-humility screen. What is the artefact here? The scenario is: a directive that makes Claude 'aggressive' — essentially, a directive with a behavioural mandate. Applying Jones's three conditions to the directive-writing task: 90%+ unrescued completion: a directive that says 'be aggressive' has no defined success condition..."

The rubric callback fired in Step 1 of the subagent's reasoning, before any directive was drafted. Scope-screening happened pre-authoring as DR-P2-DR8 intends.

**Check 4 — Haiku "struggles with judgement" claim absent:** PASS
The retired claim does not appear in the subagent's output. Haiku 4.5 is mentioned only in the generational list `"(Opus 4.7, Sonnet 4.6, Haiku 4.5)"`. The operator-empirical Haiku-no-judgement framing (amended 2026-04-22) was not triggered by this scenario because the scenario did not involve routing judgement work.

### Scenario 2 — True-boundary path (counter-scenario added per V6 triage)

**Scenario prompt:** *"You need to write a directive that tells a Claude Code agent: before running any of `rm -rf`, `git reset --hard`, or `git push --force` against any branch, the agent must confirm with the user first. This is an irreversibility boundary — these operations destroy work or rewrite shared history, and the user has explicit authority to approve or refuse per case."*

The scenario explicitly told the subagent: this is NOT a dial-back case; there is a genuine hard boundary. The scenario tests whether the skill distinguishes rhetorical emphasis from true boundaries or flattens everything to dial-back.

**Check 1 — Routed to `model-tier-notes.md`:** PASS
> "The target is a Claude Code agent. The skill routes me to `model-tier-notes.md`. The relevant tier is Sonnet 4.6... Sonnet 4.6 has a **proactive default** — it may take unsanctioned actions without explicit 'ask before acting' clauses... For Opus 4.7 (if the agent runs on Opus): it is **more literal** — I need to enumerate the three commands explicitly, not rely on the model to generalize from 'destructive commands.'"

**Check 2 — Aggressive-language dial-back shown *with correct carve-out*:** PASS
> "So the skill does explicitly acknowledge a category of 'true boundaries' where `never` is the right word. The question is whether `rm -rf`, `git reset --hard`, and `git push --force` meet that bar... The test for a true boundary is irreversibility + authority asymmetry. 'Never commit secrets' is a true boundary because: (1) reversal is very hard... all three are irreversible-or-very-hard-to-reverse. This is structurally the same as 'never commit secrets.'"

The subagent found the carve-out, applied it correctly, and wrote a directive with mild-imperative "stop and ask" framing rather than over-dialling to pure declarative. Check 2's original framing ("dial-back shown") is extended here to "skill's two-case guidance shown and applied to the correct case" — which is the more rigorous version of the check.

**Check 3 — Rubric callback fired:** PASS
> "The skill's Rubric Callback section says: before writing a new directive, check whether the underlying agent-task-or-skill passes the `denubis-extending-claude:epistemic-humility` rubric. This is a directive for a Claude Code agent, not a rubric-evaluated artefact itself. The scope here is clearly bounded: three specific shell operations, an irreversibility test, and a confirmation gate. Jones's three conditions for appropriate AI involvement apply..."

**Check 4 — Haiku claim absent:** PASS
Haiku 4.5 not mentioned (scenario targeted Sonnet 4.6 / Opus 4.7 Claude Code agents). Retired claim does not appear.

## REFACTOR iterations

### V4 — Tighten Task 3 Step 3 Python assertion (commit `1fbd8c8`)

Codex triage of the Task 5 rubric walkthrough flagged the `has_haiku_no_judgement_guidance` structural check as keyword-presence-only. The pre-fix check required `Haiku 4.5` + (`judgement` or `judgment`) + (`operator` or `empirical`) + (`unsuitable` or `never`) — any paragraph stringing these together would satisfy it. Tightened by adding two reasoned-phrase clauses:

- `'Route judgement-heavy work' in content` — exact phrase, specific remediation (not just assertion)
- `'mechanical instruction-following' in content.lower()` — the contrast anchor that distinguishes the two regimes the operator-empirical position relies on

Re-ran the tightened assertion against committed `model-tier-notes.md` (`cc4176d`): passed with stronger evidence. A future author reframing the guidance must consciously update both the prose and the assertion — drift becomes visible rather than silent.

### V6 Gap 2 — Reorder Escalation section lead paragraph (commit `3af9968`)

The counter-scenario (Scenario 2) surfaced three skill-level gaps. Gap 2: the carve-out for true boundaries was syntactically subordinate to the dial-back guidance — a skimming reader could take away "always dial back" without registering the exception. Rewrote the lead paragraph of `SKILL.md` §Escalation to foreground the distinction between rhetorical emphasis and true boundaries before stating the dial-back rule. Named the cost-of-misfire asymmetry (rhetorical overtrigger degrades instruction-following; missed true-boundary gate destroys work or leaks secrets) so the reader can reason about which case their current authoring falls into.

Structural checks still pass post-edit. Full test suite: 113/113. Gap 1 (no worked example of a stop-and-confirm gate) and Gap 3 (model-tier-notes proactive-default note not cross-referenced from SKILL.md guard-clause guidance) are acknowledged below as post-Phase-2 follow-up rather than fixed in this phase.

## Rubric self-application walk-through (`epistemic-humility`)

Applied to Phase 2 as a whole (restructure + new companion files + verification process itself). The walk-through names tensions rather than rubber-stamps; "zero vulnerabilities surfaced is itself a flag" per the skill's self-application convention.

### Scope — Jones's three conditions

**Condition 1 (90%+ unrescued completion):** The mechanical restructure met this — Tasks 1-4 completed without rescue, structural Python assertions passed, tests stayed green. The GREEN verification's evidence base is N=2 scenarios, which tests contrasting paths (dial-back + true-boundary) but does not establish a success rate. See V1.

**Condition 2 (bounded, auditable, reversible):** Solidly met at the phase level. Every edit is a git commit; any edit is revertable; Python assertions enumerate what was done. Auditability is strong for the mechanical portion.

**Condition 3 (every miss surfaces fast enough for a human):** Partially met. Structural misses surface fast via Python assertion failure. Cognitive misses (whether the rubric callback or the Escalation distinction actually fires at the right authoring moment) cannot be decided from this phase; they require downstream observation. DR-P2-DR8 and the newly-surfaced Gap 2 both anticipate this. See V2.

### Observability — three screens

**Screen 1 (form-gate):** Done-when entries mostly pass — operational checks with named Python assertions. The entry "GREEN verification passes pressure scenario; rubric self-application walk-through committed with any surfaced vulnerabilities acknowledged by user before GREEN" is borderline — "vulnerabilities acknowledged" could self-prove. This file's existence with named vulnerabilities below is the concrete evidence the entry demands.

**Screen 2 (tautology-screen):** The structural Python assertions prevent the obvious empty-content-with-right-shape failure. The tightened V4 check closes the specific keyword-presence loophole in `has_haiku_no_judgement_guidance`. The four-check pressure-scenario rubric is orchestrator-graded — see V3 on this. Otherwise no self-proving claims remain.

**Screen 3 (named-falsifier):** Python assertion blocks are named commands with expected output. Cross-reference resolution (rubric callback to epistemic-humility) is automatable and named. The post-landing audit for DR-P2-DR8 is less concretely named — "audit the next 5-10 directive additions" lacks a specific command.

### Process — Schön's four questions

**Can I solve the problem I have set?** Yes. The problem set by Phase 2 is tractable: update a skill to reflect current model tier, drop stale content, add the rubric callback. The implicit larger problem — "make Claude actually follow the updated guidance in real use" — was NOT the problem Phase 2 set; it is the problem DR-P2-DR8 and DR-P2-DR3 flag for post-landing observation.

**Do I like what I get when I solve this problem?** Mostly yes. The restructure produced a SKILL.md that is cleaner than the input: no stale Opus 4.5 section, per-model anchors with citation URLs, Rubric Callback that opens scope-screening before authoring, and — as of `3af9968` — a lead paragraph for the Escalation section that foregrounds the distinction between rhetorical emphasis and true boundaries. Line count grew by 9 (270 → 279) during Task 2; post-Gap-2 the same. That's within "restructure, not expand" tolerance.

**Have I made the situation coherent?** Yes. The Rubric Callback resolves to a real target (epistemic-humility from Phase 1). `model-tier-notes.md` is linked from the new `## Model-Specific Notes` H2. `long-running-state-patterns.md` no longer contradicts the current model tier. `graphviz-conventions.dot` has attribution to obra. Haiku-no-judgement passage aligns with AbsenceJudgement:868's three success conditions. No internal contradictions detected.

**Have I kept inquiry moving?** Partially. The Rubric Callback opens inquiry. The UAT entries DR-P2-DR8 and DR-P2-DR3 open future inquiry explicitly. But the "persuasion-principles out of scope" decision was inherited from the design plan without Phase 2 re-interrogating it. See V5 for why this is acknowledged rather than flagged — the design plan did re-examine the decision; Phase 2's acceptance of that re-examination is correct.

### Failure-pattern screen

**Temporality blindness:** Addressed. Dated headers on `model-tier-notes.md` (`_Last verified: 2026-04-17_`) and `long-running-state-patterns.md` make staleness observable. The restructure itself is a response to temporality blindness in the prior state.

**Scope/confabulation:** Phase 2 scope is narrow (one skill, four files in one directory). High effort applied to a well-bounded task. N=2 pressure-scenario evidence base is thin (see V1) but not confabulating — the scenarios are concrete, the evaluation quoted verbatim subagent text.

**Stamp-collecting without evaluation:** Partial. The Haiku section of `model-tier-notes.md` evaluates its sources by contradicting Anthropic's marketing with the operator-empirical position. The Opus 4.7 and Sonnet 4.6 sections accumulate citations without independent evaluation — they are source-attributed vendor summaries. See V7 for the acknowledged asymmetry; per Codex triage, this is not a pre-GREEN blocker.

**Vibes-based operation:** Largely avoided. Done-when entries are structural, not modifier-only. The four-check pressure-scenario rubric has explicit PASS criteria with verbatim evidence quoted (V3 fix).

## Vulnerabilities surfaced and user acknowledgement

Seven vulnerabilities surfaced during the rubric walkthrough. Codex (independent external LLM) was consulted for triage after the initial list was drafted; the triage narrowed the pre-GREEN remediation list to V3 + V4 + V6 and recommended acknowledge-only for V1 + V2 + V5 + V7. The user approved that split.

### V1 — N=1/N=2 smoke-test evidence base (acknowledged, not remediated)

The GREEN verification ran two pressure scenarios. Codex correctly observed that the plan's Task 5 Step 1 promises "at least one" scenario (phase_02.md:547), and the plan's commit text does not make a rate claim. N=2 with contrast is a smoke test, not a 90%+ completion-rate test under Jones condition 1. The vulnerability is: this evidence base would not distinguish a skill with a 95% success rate from one with a 50% rate against varied scenarios. Mitigation is downstream observation per DR-P2-DR8 and DR-P2-DR3 in `uat-requirements.md`, which are falsifiable over real use.

**Acknowledged as known limit. No pre-GREEN remediation.**

### V2 — Cognitive timing of rubric callback is post-hoc knowable (acknowledged, routed to UAT)

Whether the rubric callback fires before drafting in real authoring (rather than during deliberate reading) cannot be decided from this phase. This is already the concern DR-P2-DR8 in `uat-requirements.md` raises: *"whether the placement actually achieves the intended timing — that a skill-author hits the rubric-callback before committing to directive phrasing, not as a post-hoc check after writing and regretting. Position on a page is automatable; cognitive timing during authoring is not."*

**Acknowledged as correctly routed to UAT. No pre-GREEN remediation.**

### V3 — Orchestrator grading not independent (remediated by quote-verbatim protocol)

The four-check pressure-scenario rubric is applied by the orchestrator (this session) to subagent output from scenarios the orchestrator chose. Codex triage: independent grader is not required if each PASS/FAIL cites verbatim subagent text. The pass/fail blocks above in this file quote subagent output for each check — a future reviewer can re-read the quoted passages and disagree. Bare PASS labels would not have been auditable.

**Remediated via documentation protocol (this file).**

### V4 — Haiku-no-judgement structural check was keyword-presence-only (remediated, commit `1fbd8c8`)

The pre-fix assertion could be satisfied by any paragraph containing `Haiku 4.5` + `judgement|judgment` + `operator|empirical` + `unsuitable|never` — no reasoning required. Tightened to additionally require the specific phrases `Route judgement-heavy work` and `mechanical instruction-following`. Both are present verbatim in the committed `model-tier-notes.md` line 45. Tightened assertion passes. Future rewording requires updating both prose and assertion — drift becomes visible.

**Remediated.**

### V5 — Persuasion-out-of-scope decision was re-examined, not inherited blindly (walk-through correction)

Walk-through initially flagged the "persuasion principles out of scope" decision as inherited from design plan without re-examination in Phase 2 — framing it as closed-inquiry. Codex triage corrected this by citing design plan lines 472-480, which lay out three load-bearing reasons for the omission: (1) Cialdini's Authority principle contradicts the `epistemic-humility` rubric's Observability screen; (2) Anthropic's current prompting guidance dial-backs the same Authority levers; (3) AbsenceJudgement's technoscholasticism critique warns against amplifying textual authority. Phase 2's acceptance of the design plan's explicit decision is correct, not inherited-blindly.

**Walk-through over-framed; no vulnerability remains. Noted as walkthrough self-correction via independent triage.**

### V6 — Scenario favourability (remediated with counter-scenario + SKILL.md edit, commit `3af9968`)

The original scenario tested only the dial-back path — exactly what the skill's Compliance Techniques section is optimised for. Counter-scenario added (Scenario 2 above) to test the true-boundary path: a directive requiring confirmation before `rm -rf` / `git reset --hard` / `git push --force`. The counter-scenario passed all four checks AND surfaced three skill-level gaps:

- **Gap 1:** No worked example of a stop-and-confirm gate (distinct from unconditional prohibition). Acknowledged as post-Phase-2 follow-up.
- **Gap 2:** The carve-out for true boundaries was syntactically subordinate to the dial-back guidance. **Remediated** in commit `3af9968` — Escalation section lead paragraph now foregrounds the distinction and names the cost-of-misfire asymmetry.
- **Gap 3:** Model-tier-notes proactive-default note (Sonnet 4.6) is not cross-referenced from SKILL.md's guard-clause guidance; reader must infer the connection. Acknowledged as post-Phase-2 follow-up.

**Remediated for Gap 2. Gaps 1 and 3 acknowledged for a later edit pass.**

### V7 — `model-tier-notes.md` Opus/Sonnet sections are vendor-guidance summaries (acknowledged, asymmetric by design)

The Haiku 4.5 section of `model-tier-notes.md` evaluates its sources (contradicts Anthropic's marketing framing with the operator-empirical position at line 45). The Opus 4.7 and Sonnet 4.6 sections cite URLs without independent evaluation — they read as source-attributed vendor-guidance summaries. Codex triage: the asymmetry exists because Haiku has an explicit operator override; Opus/Sonnet do not. Adding independent evaluation to Opus/Sonnet sections would require operator experience that has not yet accumulated; fabricating evaluation would be worse than acknowledging the asymmetry. Per Codex recommendation, a single sentence clarifying the sections' nature (vendor-guidance summaries rather than independently validated) would eliminate the apparent vibes-based gap without inventing content — this is a candidate for a later edit pass, not a Phase 2 blocker.

**Acknowledged as asymmetric by design. No pre-GREEN remediation.**

### Minor observations (non-vulnerability)

- **Line 215 of SKILL.md** (`Claude 4.x tends to overengineer` in Overengineering Prevention section) was left per the Task 2 implementor's reading that the phase file's enumeration of anchors was authoritative scope. A strict reading of AC3.7 might flag this; code review (Phase 2c) is the right place to surface it. Not a pre-GREEN item.
- **Dated headers say 2026-04-17** and do not reflect the 2026-04-22/23 amendment pass. The amendment is captured in the prose content (Haiku-no-judgement passage). Prose reflects the amendment; headers do not. Minor.

## User acknowledgement

The user (Brian, operator of session `ed3:exec-skills:P2`) reviewed the seven vulnerabilities above via:
1. Initial orchestrator-authored walk-through (V1-V7 surfaced).
2. Codex triage of the walk-through (independent LLM, session 2026-04-23) — corrected V5, recommended pre-GREEN remediation for V3, V4, V6 only.
3. Explicit approval of the triage's recommended split.

The user's decision:
- **Remediate V3** (quote subagent verbatim in this file) — done.
- **Remediate V4** (tighten structural check) — done, commit `1fbd8c8`.
- **Remediate V6 Gap 2 only** (Escalation section reorder) — done, commit `3af9968`. Gaps 1 and 3 deferred to post-Phase-2.
- **Acknowledge V1, V2, V5, V7** — documented above.

The acknowledgement is not a performance of closure. V1 (evidence base thin) and V2 (cognitive timing) are live vulnerabilities that the UAT entries and future observation must carry; V5 was a walkthrough over-framing corrected by external triage; V6 Gaps 1 and 3 are known skill-level gaps that should appear in a follow-up edit queue. V7 is an acknowledged asymmetry.

## Consumer-tracing

This file is consumed by:
1. Phase 5's cross-reference audit (verifies every phase has a GREEN verification file).
2. Phase 5 Task 4.5's frustration-signal audit (the 2026-04-23 Task 5 session is in-window; the audit will sweep for frustration markers in this session's transcript).
3. Finalisation code review (checks the GREEN evidence against AC3.* coverage).

## Commits landed during Task 5 (GREEN + REFACTOR)

In order:

| Commit | Purpose |
|--------|---------|
| `1fbd8c8` | V4 remediation: tighten Task 3 Step 3 `has_haiku_no_judgement_guidance` assertion |
| `3af9968` | V6 Gap 2 remediation: reorder SKILL.md Escalation section lead paragraph |
| *this file's commit* | GREEN verification + rubric walkthrough + acknowledgement record |

## Pre-existing Task 1-4 commit stack (for Phase 5 cross-ref audit)

| Commit | Task |
|--------|------|
| `9ed5658` | Task 1 — RED evidence (static code-smell inventory) |
| `6a29760` | Task 2 — SKILL.md restructure (pre-Gap-2 state) |
| `cc4176d` | Task 3 — Create `model-tier-notes.md` |
| `76faf34` | Task 3.5 — Update `long-running-state-patterns.md` anchors |
| `bb2f87f` | Task 4 — Add obra attribution to `graphviz-conventions.dot` |
