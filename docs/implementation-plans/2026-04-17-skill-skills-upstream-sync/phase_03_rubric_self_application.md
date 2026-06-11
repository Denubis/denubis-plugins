# Phase 3 — Rubric Self-Application Walk-Through

**Task:** phase_03.md Task 5 Step 3 (H4 revision: walk-through with surfaced
vulnerabilities, not a pass/fail gate).
**Artefact under review:** Phase 3 as a whole — the restructured
`testing-skills-with-subagents/SKILL.md` (at `6b2dc70`) plus the phase's own
process (RED evidence sourcing, restructure, audits).
**Rubric:** `denubis-extending-claude:epistemic-humility` (Scope → Observability
→ Process → Failure-pattern), read in full before application. The named sources
(Jones 2025; Schön 1994) are fully cited in that skill's
`absencejudgement-citations.md`, alongside an evidence-grade note for each.
**Author:** Phase 3 orchestrator (Fable 5 main loop), 2026-06-11.
**Ground rule:** zero vulnerabilities surfaced is itself a flag. Seven are named
below, plus two proleptic-challenge carry-ins.

---

## Scope — Jones's three conditions

**1. 90%+ unrescued completion.** The restructured skill's RED phase now hard-gates
on independent-session evidence. Source 1 (cc-search-chats) completed unrescued in
this phase's own Task 1 — but that is N=1, and the gate's second path (user-run
fresh session) requires human participation *by design*. The skill deliberately
trades unrescued completion for grounded evidence: when the index has no qualifying
transcript, the cycle halts for a human. This is a chosen violation of condition
(1)'s letter, defensible because the halt is the feature — but it means every
future skill-testing cycle carries a contingent human cost that this phase did not
have to pay. **V1.**

**2. Failures bounded, auditable, and reversible.** Reversible: all edits are
git-tracked; the preservation audit pins baseline `cdc9811` and byte counts.
Auditable: the evidence chain names session IDs, message UUIDs, and re-run
commands — degraded one step by the cc-search-chats project-path lossiness for
worktree directories (documented; UUID-keyed `context` is the workaround).
Bounded: the gate's failure modes are enumerable (false halt when no transcript
exists though the failure is real; false pass when a marginal transcript is
accepted). The second mode is live: **the gate screens the evidence source but
not the screener** — "qualifying" is an executor judgement call, and this phase's
own evidence needed a one-hop indirection argument to qualify. A less careful
future executor could accept weaker hits and cite this phase as precedent. **V2.**

**3. Misses surface fast, to a human.** A wrong RED baseline surfaces at
GREEN/REFACTOR only if something forces it — the V6 precedent shows the prescribed
cycle alone did not; the out-of-band rubric did. The restructure's answer is the
early Rubric Callback, whose cognitive timing is exactly the open UAT question
(DR-P3-DR7): position is verified, timing is observable only in future use.

## Observability — three screens

**Form-gate.** The phase's ACs bind to named commands (embedded Python scripts,
pytest, grep audits) with expected outputs. Pass at the form level.

**Tautology-screen.** The embedded scripts verify *structure* (headings present,
positions ordered, keyword constellations on the file). A semantically garbled
file with the right shape would pass every script; content is guarded only by the
byte-identicality audit (for preserved blocks) and human review (for new prose).
This is the same form-not-content limitation Phase 2 named as its V4; Phase 3's
scripts inherit it. The phase-02 tightening (require reasoned phrases, not bare
keywords) is partially present — the Haiku check requires the operator/unsuitable/
judgement constellation but on the whole file, not the same passage. **V4.**

**Named-falsifier.** The RED evidence names its falsifier (re-run the queries
against the recorded SHA; the failure should reproduce). The preservation audit
names baseline SHA and byte counts. One claim lacks a falsifier: **the
independence of the qualifying session.** It is this plan's own Phase 2 execution;
"independent enough" is argued (distinct session, predates this executor, failure
confirmed by codex rather than self-attested) but no observation is named that
would show it was *not* independent enough. The honest statement: the gate's
authoring phase passed the gate via an indirection argument the gate's own text
does not anticipate. Proleptic counterargument 2 raised the same recursion. **V3.**

## Process — Schön's four questions

**Can I solve the problem I have set?** Yes — "ground RED baselines in observed
failures" was tractable and was executed with a real, externally-confirmed failure.
The unsolved remainder is deliberate: whether the gate is *workable* at scale
(fresh-session fallback cost) is deferred to use, not claimed.

**Do I like what I get?** Mostly. One aesthetic regression: relocating the
pressure-type reference material into REFACTOR means VERIFY GREEN now points
*forward* to material used *after* its first mention — a reader meets the "Great
scenario" before the criteria that explain it. The pointer sentences make this
navigable, but the reading order inverted. Cosmetic; recorded, not fixed. **V7.**

**Have I made the situation coherent?** Cross-references resolve (Rubric Callback
↔ epistemic-humility; bidirectional Note-B pointers). One R7 (tool-availability)
gap: the protocol names `cc-search-chats:search-chat` without an explicit
"if the tool is unavailable" clause. Functionally self-healing — path 2 (user-run
fresh session) is the no-tool path — but it is framed as the no-*hits* fallback,
not the no-*tool* fallback. One clause would close it. **V6.**

**Have I kept inquiry moving?** Yes. The gate halts to a human rather than
freezing; the unknowables are filed as UAT entries (DR-P3-DR7, AM2-P3) with
shatter conditions; the evidence file's near-miss log keeps the rejected
candidates inspectable.

## Failure-pattern screen

**Temporality blindness.** The phase *removed* the worst instance (the dated
Real-World Impact narrative) and dated its operator claims. But the restructured
SKILL.md now carries inline model anchors (Haiku 4.5, Sonnet 4.6, Opus 4.8) with
no dated header and no staleness tripwire of its own — rubric R6 says
model-specific claims live only in a dated supporting file. The text was
plan-specified and the operator position is governed by `model-tier-notes.md`'s
falsifier, but the *anchors in this skill* will age silently. The rubric-draft's
pending item 4 (per-tier testing requirements for this skill) is the natural
reconciliation point. **V5.**

**Scope/confabulation.** The phase stayed narrow (one skill, surgical edits,
explicit not-in-scope list). No finding.

**Stamp-collecting without evaluation.** The evidence file weighs sources — the
near-miss log rejects three tempting-but-circular candidates and two
frustration-only hits with reasons. No finding.

**Vibes-based operation.** The gate replaces "invent a plausible scenario" with
named sources and named qualifying criteria. The criteria themselves require
judgement (see V2), but they are explicit and inspectable. Partial pass — the
residue is V2, not a separate finding.

---

## Surfaced vulnerabilities (summary)

| # | Vulnerability | Rubric section | Lean |
|---|---|---|---|
| V1 | Gate's unrescued-completion rate is N=1; fresh-session fallback cost untested and lands on future cycles (first: Phase 4) | Scope 1 | Acknowledge — captured by AM2-P3 + DR-P3-DR7 observation windows |
| V2 | The gate screens the source, not the screener: "qualifying" is unguarded executor judgement; this phase's own one-hop evidence becomes citable precedent | Scope 2 / Obs 3 | **Fixed at gate (2026-06-11) on operator direction** — qualifying-criteria checklist promoted into the Conversation-Precedent Protocol (observed-not-described, independence argument, in-scope, externally confirmed, not self-licensing) |
| V3 | No named falsifier for the qualifying session's independence (it is this plan's own Phase 2 session) | Obs 3 | **Partially fixed with V2** — the checklist now requires a recorded independence argument per source; this phase's own evidence remains argued-not-falsifiable, superseded by stronger direct evidence when it appears |
| V4 | Verification scripts enforce form, not content (whole-file keyword constellations) | Obs 1/2 | Acknowledge — standing Phase 2 V4 limitation; byte-identicality + human review are the content guards |
| V5 | Inline model anchors in SKILL.md violate R6 (no dated supporting file / staleness tripwire for this skill) | Failure: temporality | Defer to Phase 4/5 reconciliation (rubric-draft pending item 4); record pointer |
| V6 | R7 gap: cc-search-chats named without explicit if-unavailable clause (path 2 covers it functionally) | Process: coherence | **Fixed at gate (2026-06-11) on operator direction** — if-unavailable clause added to protocol path 1; operator additionally directed ISSUE-10 path 1 (improve the tool rather than re-document workarounds per consumer) |
| V7 | Reading-order inversion: VERIFY GREEN forward-references REFACTOR's criteria material | Process: output | Acknowledge — navigable via pointers; cosmetic |
| V8 | Derived artefacts name-dropped Jones/Schön/AbsenceJudgement with no path to the bibliography (`absencejudgement-citations.md`); the self-application's own coherence check verified cross-references but not source resolvability | Obs 3 / Failure: stamp-collecting | **Operator-surfaced at gate (2026-06-11), not self-surfaced.** Fixed same day: pointer clauses added to this file's header and SKILL.md Rubric Callback (`32e3bb0`) |

**Proleptic carry-ins:** CA2 (gate recursion) folded into V2/V3. CA3
(line-count provenance: 421-plan vs 425-baseline vs 452-actual circulating in
prose) — disposition: Phase 5 audits must recompute counts from files at audit
time, never from phase-summary prose; proposed as a dated note for phase_05.md
pending operator approval.

**Lean stated for the record (operator decides):** V1, V4, V7
acknowledge-and-document; V5 defer-with-pointer to Phase 4/5. V2, V6, and V8
were fixed at the gate on operator direction; V3 partially fixed with V2 (no
decisions pending on any of these).
Per the Phase 2 precedent, the self-serving move would be marking cheap fixes as
acknowledge-only — V6 is the only sub-five-minute fix here, and it is flagged as
such rather than buried.

## User acknowledgement

**Acknowledged by the operator, 2026-06-11.** Eight vulnerabilities surfaced
(seven self-surfaced, V8 operator-surfaced at the gate). Dispositions:

- **V1, V4, V7** — acknowledged and documented; no change required.
- **V2** — fixed at gate on operator direction: qualifying-criteria checklist
  promoted into the Conversation-Precedent Protocol (`41138e0`).
- **V3** — partially fixed via V2's recorded-independence-argument requirement;
  this phase's own evidence remains argued-not-falsifiable, superseded when
  stronger direct evidence appears.
- **V5** — deferred to Phase 4/5 reconciliation (rubric-draft pending item 4),
  pointer recorded.
- **V6** — fixed at gate on operator direction: if-unavailable clause
  (`7cbc9cc`); operator additionally directed ISSUE-10 path 1 (improve
  cc-search-chats upstream rather than re-document workarounds per consumer).
- **V8** — operator-surfaced citation finding; fixed same day in this plugin
  (`32e3bb0`, `c6b8829`) and generalised across denubis-plan-and-execute
  (`419e7d0`, `a783949`).

UAT entries DR-P3-DR7 and AM2-P3 confirmed armed by the operator (2026-06-11).
Proleptic CA3 disposition approved: dated recompute-counts-from-files note
appended to `phase_05.md`.
