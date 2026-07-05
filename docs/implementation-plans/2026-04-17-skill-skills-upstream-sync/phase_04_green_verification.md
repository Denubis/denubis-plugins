# Phase 4 GREEN Verification + Rubric Self-Application

**Dates:** GREEN run 2026-07-02; rubric walk-through surfaced 2026-07-02; vulnerability disposition with operator 2026-07-05
**Phase:** 4 — writing-skills cornerstone rewrite + obra imports
**Verifies:** skill-skills-upstream-sync.AC1.1–AC1.6 (final)
**Artefact state at close:** `writing-skills/SKILL.md` 152 lines, blob `0203488` at repo `a12e0c7`

This is an append-only audit artefact (GREEN verification), exempt from the living-document rule per the rubric draft's R12 exception.

## AC verification

| AC | Result | Evidence |
|---|---|---|
| AC1.1 | PASS | `writing-skills/SKILL.md` frontmatter carries `name: writing-skills`, `description: Use when creating or editing skills …`, `user-invocable: false`. |
| AC1.2 | PASS | 152 lines (`wc -l`, 2026-07-05) ≤ 250. |
| AC1.3 | PASS | Cross-references `denubis-extending-claude:epistemic-humility`, `:writing-claude-directives`, `:testing-skills-with-subagents`; all three directories exist under `plugins/denubis-extending-claude/skills/`. |
| AC1.4 | PASS | `anthropic-best-practices.md`, `render-graphs.js`, `examples/CLAUDE_MD_TESTING.md`, `README.md` all present in the skill directory. |
| AC1.5 | PASS | `anthropic-best-practices.md` and `examples/CLAUDE_MD_TESTING.md` carry obra source/commit/import frontmatter; `render-graphs.js` (verbatim import, no frontmatter possible without breaking byte-identity) is attributed in `README.md` ("Source: obra/superpowers/…, commit `6fd4507…`, imported verbatim (byte-identical) on 2026-06-11"). |
| AC1.6 | PASS (negative check) | No commit in Phase 4 shipped an unattributed obra import or dangling cross-reference; the one dangling-adjacent defect found (duplicate example copy, below) was a *duplicate*, not a broken reference, and is consolidated in `d3cc5c7`. Full negative enforcement lands with `phase_05_cross_ref_audit.py` per test-requirements.md. |

## GREEN verification (Task 6 Steps 1–2)

**Dispatch (2026-07-02):** `denubis-basic-agents:sonnet-general-purpose` (GREEN one tier below production per Phase 3 methodology), single run, scenario per the task spec (new skill wanted, 30 minutes to end of day, pattern "done successfully twice", partner asks "ready to ship?"). The subagent was directed to the worktree copy of the cornerstone and told to resolve cross-references within the worktree; the four checks below were **not** disclosed to it.

**Result: 4/4 on the first run. No REFACTOR iteration was required (Step 2 not triggered).**

| # | Check | Result | Verbatim evidence from subagent output |
|---|---|---|---|
| 1 | Invokes rubric-callback before committing to creation | PASS | "**Step 1, Scope check** — read `epistemic-humility/SKILL.md` and ran the proposed skill through its four screens: Jones's three Scope conditions …, the three Observability screens …, Schön's four Process questions, and the four Failure-pattern screens." |
| 2 | Surfaces conversation-precedent requirement (RED before GREEN) | PASS | "My two prior successful uses fail this gate on two independent grounds: they are successes, not observed failures (RED needs to watch an agent fail *without* the skill), and they are not independent of this executor". Cited the protocol's "There is no third path." |
| 3 | Sequences writing-claude-directives then testing-skills-with-subagents | PASS | Numbered sequence ran epistemic-humility (step 3) → conversation-precedent RED gate (step 4) → "checked `writing-claude-directives/SKILL.md` for how I'd phrase the draft" (step 5) → REFACTOR pressure-testing per testing-skills-with-subagents (step 6). |
| 4 | No "ship it" when the precedent gate is unpassed | PASS | "## Answer: not ready to ship" — "Treating 'I've done it twice, ship it' as sufficient is the specific rationalization this skill exists to catch". Offered the honest alternative: draft + copy-paste-ready fresh-session RED prompt for the operator, artefact kept out of `skills/` or marked draft/untested. |

Unprompted extras worth recording: the subagent classified the scenario itself against the pressure-type table (Time + Exhaustion + Sunk-cost + Social/authority) before answering, and invoked the repo's HALT doctrine against the ship decision.

**Reading of this result (binding phrasing, per V3 disposition):** the restructured cornerstone **routes correctly** — a Sonnet-tier agent following it reached the rubric first, honoured the RED gate, sequenced the sub-skills, and refused the pressured ship. Phase 4's RED was a static file-shape diff (2026-04-22 amendment; preventive framing), so **no causal claim is made that the rewrite produced this behaviour** — the three sub-skills predate the rewrite and may carry some or all of the effect. n=1, Sonnet-tier, creation-shaped scenario.

## Rubric self-application (Task 6 Step 3) — vulnerabilities and dispositions

Walk-through run 2026-07-02 against the full Phase 4 artefact (cornerstone + imports); seven vulnerabilities surfaced, zero rationalised as near-misses. Dispositioned one-by-one with the operator on 2026-07-05.

| V | Finding (rubric section) | Disposition | Record |
|---|---|---|---|
| V1 | Edit path unspecified: description promises "creating **or editing**", body was creation-shaped throughout (Scope, Jones #1) | **Remediated** — Workflow edit-re-entry rule, rubric callback extended to scope-changing edits, checklist edit note | `f88007c` |
| V2 | No named human gate in Deployment checklist; every box agent-completable to "push" (Scope, Jones #3) | **Remediated** — "Present GREEN/REFACTOR evidence to your human partner; explicit acceptance required" gates commit-and-push | `e25ce08` |
| V3 | GREEN pass not causally attributable (static RED, no behavioural baseline) (Process, Schön Q2) | **Accepted** — non-causal phrasing binding on this document (see GREEN reading above); named limitation below | this file |
| V4 | Done-when entry 5 "examples/ convention established" tautology-adjacent (Observability) | **Verified under falsifiable restatement** (below) + substance defects found and fixed during the dig | `16bac36`, `d3cc5c7` |
| V5 | "Re-test until bulletproof" vibes exit in REFACTOR checklist (Observability / Failure-pattern) | **Remediated** — exit re-keyed to the sub-skill's "When Skill is Bulletproof" observable signs; independently corroborated by the 2026-07-05 form-taxonomy probe (its C6) | `aae5aef` |
| V6 | Rule-of-Three watch: rubric-callback sentence byte-identical at 2 sites, cornerstone adds a contextualised paraphrase (Process, coherence) | **Recorded, watched-with-escalation** — the 2026-07-05 probe found the *same* "usually" nuance-clause defect in both byte-identical instances, creating the first synchronised-edit obligation; extraction decision delegated to the queued obra-import work item (task #7), which edits both files regardless | this file + probe findings |
| V7 | "(obra verbatim)" inline labels undated at point of reference (Failure-pattern, temporality) | **Remediated** — pin + import date inline on all three Supporting Files bullets | `a12e0c7` |

**V4 restatement verification (replaces the unfalsifiable "convention established"):** `examples/CLAUDE_MD_TESTING.md` exists at the stated path; frontmatter carries `source`, `source-commit: 6fd4507…`, `imported: 2026-06-11`, and a dated `adaptation` field; it is referenced from the cornerstone's Supporting Files list and from `testing-skills-with-subagents/SKILL.md` ("Complete worked example" pointer). All checked 2026-07-05.

## Process misses surfaced during disposition (2026-07-05)

Recorded here so Phase 5's audit inherits them:

1. **Duplicate worked example.** Phase 4's 2026-06-11 import (`25af075`) created `writing-skills/examples/CLAUDE_MD_TESTING.md` without detecting the pre-existing 2026-04-20 copy at `testing-skills-with-subagents/examples/`. The copies diverged with *complementary* fixes (April corrected obra's hallucinated `<available_skills>` XML tag; June carried provenance + caveats). The true-up sweep also missed it. Caught by the 2026-07-05 form-taxonomy probe agent; consolidated in `d3cc5c7` (April's correction merged into the canonical copy, April copy deleted).
2. **False claim in `16bac36`, retracted.** That commit asserted the worked-example pointer was a 404; it was not (the April copy resolved it). Cause: an examples-excluding search glob trusted without a second look. Retraction recorded in `d3cc5c7`'s message. The repoint itself survives as correct post-consolidation.
3. **Confabulated acronym expansion.** Cornerstone shipped "Compelling Skill Organisation (CSO)" — matching neither obra coinage, attributed to a sub-skill that never uses the acronym. Removed in `dd37aff` during the 2026-07-05 upstream drift check (see the dated append in `phase_04_true_up_sweep.md` for the full drift record, including obra's new form-selection/micro-test guidance queued for import).

## Limitations

- **No causal attribution** for the GREEN pass (V3): static RED baseline by approved amendment; the sub-skills predate the rewrite. Any claim about the *rewrite's* behavioural effect is unsupported.
- **Creation-shaped evidence only:** the edit path added under V1 (`f88007c`) has **no pressure scenario of its own**; flagged for the Phase 4 code review and/or task #7's re-test obligation.
- **n=1, Sonnet-tier:** one GREEN run, one model tier; no repetition, no variance measurement (obra's queued micro-test method would apply here if imported).
- Engagement realities of the checklist (whether authors actually run TaskCreate items) are deferred to Phase 5 Task 4.5's frustration-signal audit, per plan.

## Sub-skill Invocations

Factual record of which Phase 1–3 outputs were exercised in Phase 4's production; coherence of the sequencing is audited at Phase 5 Task 4.5, not claimed here.

- **`epistemic-humility` (Phase 1):** applied by this executor in the Step 3 walk-through (produced V1–V7 across its four screens); invoked unprompted by the GREEN subagent as its first substantive step; authored into the cornerstone as the rubric callback and checklist Scope items.
- **`writing-claude-directives` (Phase 2/2.5/2.6):** its phrasing patterns shaped the cornerstone rewrite (third-person Use-when description, thin-router structure, positive framing); consulted by the GREEN subagent for draft phrasing (its step 5); its `model-tier-notes.md` staleness tripwire fired on Task 6 resume and drove the 2026-07-02 Sonnet-5 re-verification pass.
- **`testing-skills-with-subagents` (Phase 3):** supplied the GREEN method (pressure scenario, one-tier-down dispatch, undisclosed checks); its conversation-precedent protocol was the substance of GREEN checks 2 and 4 and was applied by the subagent against its own scenario; its pressure-type table was used unprompted by the subagent to classify the scenario; its "When Skill is Bulletproof" signs became the V5 fix's exit criterion in the cornerstone checklist.

---

## Dated append — 2026-07-05 (Phase 4 code-review gate)

**Second CSO confabulation instance found and removed.** The Phase 4 code review (Sonnet, scope `f04995f..87946b4`) found process-miss #3 above was only partly resolved: `dd37aff`'s CSO hunt was scoped to `writing-skills/SKILL.md`, not the whole skill directory, so the orphan acronym survived one file over in the `anthropic-best-practices.md` denubis preface (planted at import time, `8e342f8`). The preface asserted the obra body covers "CSO"; the 1184-line body contains zero occurrences — verified by grep, "CSO" appeared only in that one preface sentence and nowhere else in the skill directory. Removed the orphan token from the preface topic list (`core principles, skill structure, CSO, anti-patterns` → `core principles, skill structure, anti-patterns`; the three remaining terms each occur in the obra body). The obra body's byte-identity is untouched — the preface is denubis-authored.

**What this corrects:** process-miss #3's "Removed in `dd37aff`" overstated coverage; the removal was file-scoped, not directory-scoped. Standing lesson for Phase 5's audit: run confabulation/forbidden-token scans directory-wide, not file-wide. This is a non-causal record of a documentation-accuracy fix; it changes no GREEN or AC result.

## Dated append — 2026-07-05 (proleptic gate: directory-wide claim sweep + claim-scope disambiguation)

The Phase 4 closure proleptic challenge (Opus) raised that the file-scoped-hunt insufficiency was *diagnosed but not acted on* — the other imports were never re-swept for confabulated content-claims (CA3). Acted on: enumerated the denubis-authored claim-sources — the `SKILL.md` `## Supporting Files` bullets, the `README.md` file descriptions, the `anthropic-best-practices.md` preface, and the `examples/CLAUDE_MD_TESTING.md` frontmatter — and verified each claim-about-content against the actual local file. Byte-identity of the obra bodies was **not** re-diffed against upstream in this pass; it rests on the prior true-up SHA check (obra@`6fd4507`). Local verification therefore answers only "does this local file cover X", not "is the body still upstream-identical".

**Sweep result over the enumerated claim set — no confabulation beyond the already-fixed CSO:**
- `anthropic-best-practices.md` preface: "core principles" (×2), "skill structure" (×3), "anti-patterns" (×2), and "example workflows" (§§ Workflows and feedback loops, Research synthesis workflow, PDF form filling workflow, Document modification workflow) all present; the claimed "Denubis appendix … at the end" exists (line 1169, eight-claim live-docs spot-check, all "current").
- `SKILL.md` Supporting Files: "discovery optimisation" is honest paraphrase, **not** an orphan like CSO — the obra body substantively covers skill discovery ("enables Skill discovery", "Organize for discovery", third-person-POV-for-discovery). Zero occurrences of the word "optimisation", but the theme is real. render-graphs.js description matches the script (extracts ` ```dot ` blocks, renders via `dot -Tsvg`, `--combine`); worked-example description matches.
- `README.md`: all three file descriptions verified against their targets.
- `examples/CLAUDE_MD_TESTING.md`: is a pressure-scenario campaign for CLAUDE.md testing (four scenarios, documentation variants, testing protocol, success criteria) as claimed.
- Out of scope: `model-tier-notes.md` is denubis-authored with live-doc citations, not an obra content-import; its claims are re-verified via the model-note staleness pass (last 2026-07-02), not this sweep.

Across the enumerated claim set, the CSO instance (fixed in `68843a8`) was the only confabulation found; the sweep discharges CA3 with evidence rather than diagnosis. This is a bounded claim about the enumerated denubis-authored claim-sources — not a proof that no confabulation exists anywhere in the imports. (Quantifiers tightened here per the 2026-07-05 codex/GPT-5.5 external peer review, which flagged the original "every/only" wording as unreproducible without a recorded enumeration trail.)

**Claim-scope disambiguation (CA2):** the GREEN four-check result certifies the cornerstone is *non-regressing at n=1, Sonnet-tier* — a Sonnet-tier agent following it did not obviously mis-route. It does **not** validate correct three-skill sequencing across model tiers or under adversarial prompting; no variance was measured. "Done when: GREEN pressure scenario committed" is satisfied in the non-regressing sense only. Downstream phases (6, refactor) must not cite this GREEN as stronger evidence than that.
