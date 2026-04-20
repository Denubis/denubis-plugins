# UAT Requirements — Skill-Skills Upstream Sync

Human-judgment falsification entries. Each requires a human to USE the built thing
and exercise judgment that automated tests cannot capture.

**Quality gate for every entry:** (1) what the human DOES (an action, not inspection),
(2) what they're JUDGING (subjective quality), (3) what FAILURE looks like (concrete experience).

---

## Phase 1: `epistemic-humility` reference skill

### DR-AC4.5 — Self-application walk-through and vulnerability acknowledgement (H4 revision: walk-through + surfacing, not pass/fail)

**Originating decision:** AC4.5 per Phase 1 / design plan's Additional Consideration "Rubric self-application is a walk-through with surfaced vulnerabilities, not a pass/fail gate." Earlier framing was "coherence check passes / fails"; H4 revision dropped pass/fail framing because the walk-through author is also the reviewer — passes were unfalsifiable.

**What's automatable:** `self-application.md` exists; contains the four rubric H2s; contains at least one `honesty` / `tautology` / `vulnerab` marker indicating a named reflective vulnerability. Covered in test-requirements.md AC4.5 automated portion.

**What's NOT automatable:** Whether the walk-through genuinely probes the rubric or rubber-stamps it; whether the surfaced vulnerabilities are substantive or token; whether the user's acknowledgement of vulnerabilities was informed.

**This decision assumes:** The walk-through in `plugins/denubis-extending-claude/skills/epistemic-humility/self-application.md` genuinely probes the rubric (surfaces named vulnerabilities the rubric itself is subject to) rather than rubber-stamping it. The user reviewing the walk-through is willing to acknowledge vulnerabilities or direct remediation — not just nod at a performed-coherence narrative.

**To shatter it:** Read `self-application.md` after the rubric sections in `SKILL.md`, and ask: "Do the four walk-through sections genuinely probe the rubric, or do they rubber-stamp it? Does the walk-through name reflective vulnerabilities the rubric itself is subject to, or does it perform competence it hasn't earned? Were surfaced vulnerabilities raised to the user for acknowledgement, or papered over?"

**It's wrong if:** The walk-through reads like a checklist mechanically ticked against itself — every section passes with no named tension, no acknowledged vulnerability, no honesty about where the rubric cannot fully solve what it addresses. That is Schön-screen failure (the artefact closed inquiry rather than kept it moving) *and* Observability-screen failure (tautological self-proof) simultaneously. Retrospective backstop: Phase 5 Task 4.5 frustration-signal audit (AC5.8) would catch rationalised walk-throughs where the user's later frustration at discovered incoherence appears in the transcript but the walk-through never named it at authoring time.

---

## Phase 4: `writing-skills` cornerstone (back-references from Phase 1 decisions)

These entries originate in Phase 1 decisions but cannot be shattered until the rubric is *used* by an orchestrator skill, which Phase 4 first makes concrete.

### DR-P1-DR1 (back-ref) — Self-application file helps evaluate a novel skill-authoring moment

**Originating decision:** Phase 1 DR1 (sibling `self-application.md` with cross-refs, not in-body demonstration).

**This decision assumes:** When a skill-author faces a new scope-assessment decision and loads `self-application.md`, the walk-through helps them evaluate the new case — not just the walk-through's own case.

**To shatter it:** Using Phase 4's `writing-skills` entry point, take a real skill-authoring moment (a new skill being considered for this repo or another) and load `self-application.md` via cross-reference. Work through the rubric with the author's help.

**It's wrong if:** The author ends up having to re-derive the coherence argument from scratch because `self-application.md` is too abstract to map onto the live decision. That would mean the walk-through is illustrative, not operative — the rubric inherits Schön but the self-application doesn't transmit Schön's reflective posture to new cases.

### DR-P1-DR2 (back-ref) — Companion citations file is load-bearing at decision time

**Originating decision:** Phase 1 DR2 (separate `absencejudgement-citations.md` rather than inlining quotations in SKILL.md).

**This decision assumes:** Keeping quotations in a companion file preserves skim-speed for orchestrators invoking the rubric while retaining verifiability for reviewers.

**To shatter it:** In a real scope-assessment cycle triggered by Phase 4's `writing-skills`, observe whether SKILL.md alone suffices or whether you reach for `absencejudgement-citations.md`. If you reach for it every time, the split was artificial — quotations *are* load-bearing at decision time and should have been inlined.

**It's wrong if:** Every rubric use requires loading both files, meaning the companion-file architecture cost overhead without the skim-speed benefit. Alternatively, it's wrong if the companion file is never loaded, meaning the quotations were overhead no one actually consulted — the skill would have been better grounding the claims inline with tighter paraphrase discipline.

### DR-P1-DR4 (back-ref) — Verbatim wording beats paraphrase in rubric use

**Originating decision:** Phase 1 DR4 (paper-verbatim wording for "bounded, auditable, and reversible"; "scope/confabulation"; "stamp-collecting without evaluation"; "mechanical, bounded, low-judgement tasks").

**This decision assumes:** Verbatim citations beat prettier paraphrases; the rubric is a guard against textual-authority drift, and drifting its own source text would be self-undermining.

**To shatter it:** In Phases 2, 3, and 4, when orchestrators cross-reference the rubric and authors apply it to scope decisions, observe whether the verbatim phrasing is cognitively workable or whether authors consistently mentally re-translate to paraphrase.

**It's wrong if:** Rubric users consistently need to mentally re-translate "stamp-collecting without evaluation" back to "evidence accumulation without evaluation" (or similar) to apply the screen — meaning the paraphrase was the real handle and the paper's wording is archival-only. If this happens, DR4 was correct about attribution discipline but wrong about the cognitive cost; a revision should note the paper's wording alongside a glossary translation.

---

## Phase 2: `writing-claude-directives` restructure

*Entries below use the Phase 6 gate-form template: every UAT entry names what's automatable AND what's not automatable before the falsification template. This models the behaviour Phase 6 codifies in impl-plan-write.*

### DR-P2-DR8 — Rubric-callback placement achieves pre-authoring timing

**Originating decision:** Phase 2 DR8 (rubric-callback H2 inserted between Compliance Techniques and Structure Patterns — highest visibility position during primary read-through).

**What's automatable:** The rubric-callback H2 exists at the specified position; grep SKILL.md for the H2 heading and verify its line index is less than the "Structure Patterns" H2's line index. Also verify the cross-reference `denubis-extending-claude:epistemic-humility` resolves. These checks land in test-requirements.md.

**What's NOT automatable:** Whether the placement actually achieves the intended timing — that a skill-author hits the rubric-callback *before* committing to directive phrasing, not as a post-hoc check after writing and regretting. Position on a page is automatable; cognitive timing during authoring is not.

**This decision assumes:** A reader authoring a new directive will encounter the rubric-callback early enough in their primary read-through to apply it before committing to phrasing choices.

**To shatter it:** After Phase 2 lands and the next time you (or another author) write a new directive using this skill, observe when the rubric-callback fires. Does it surface BEFORE you've drafted candidate wording, or AFTER — as a "now let me check whether what I wrote was scoped right"?

**It's wrong if:** You consistently discover the rubric-callback only after drafting directive text, and find yourself re-scoping or rewriting because the rubric screens surface concerns the early phases should have caught. That would mean the placement didn't achieve pre-authoring timing — either the section needs to move higher, or the rubric-callback needs to be wired into a different entry point (e.g., the skill's opening Core Principles).

### DR-P2-DR3 — "Dial back aggressive language" guidance changes actual authoring behaviour

**Originating decision:** Phase 2 DR3 (update aggressive-language guidance at SKILL.md lines 96, 237 to match current Anthropic docs with explicit before/after example and URL citation).

**What's automatable:** The updated guidance string is present with the current Anthropic source URL; grep SKILL.md for both. The before/after example ("CRITICAL: You MUST → Use this tool when...") is present. Added to test-requirements.md.

**What's NOT automatable:** Whether authors writing NEW directives actually dial back aggressive phrasing after reading this skill, or whether the guidance is absorbed intellectually but not operationally — "I know the recommendation, but this case genuinely needs CRITICAL."

**This decision assumes:** The updated guidance (with concrete example + current URL) will change authoring behaviour when applied, not just provide a rule authors can cite and override.

**To shatter it:** Audit the next 5-10 new directive additions across denubis skills after Phase 2 lands. Count all-caps imperatives and "CRITICAL:" / "YOU MUST" occurrences. Compare against the pre-Phase-2 baseline.

**It's wrong if:** Aggressive-language patterns persist at pre-Phase-2 rates or higher, suggesting the guidance is known but overridden in practice. That would mean either the guidance needs stronger framing (e.g., "before using aggressive language, document why the dial-back pattern fails for this case") or the directive genre genuinely needs aggressive phrasing and the guidance is wrong for denubis's use cases.

## Phase 3: `testing-skills-with-subagents` restructure

### DR-P3-DR7 — Rubric-callback placement fires before testing investment begins

**Originating decision:** Phase 3 DR7 (rubric-callback H2 between "When to Use" and "TDD Mapping for Skill Testing" — early placement to catch scope failures before the tester invests in synthetic-scenario authoring).

**What's automatable:** The rubric-callback H2 exists at the specified position; grep SKILL.md and compare H2 line indexes — must be between "When to Use" (< index) and "TDD Mapping" (> index). Cross-reference `denubis-extending-claude:epistemic-humility` present. These are in test-requirements.md.

**What's NOT automatable:** Whether the placement actually causes skill-testers to apply the rubric *before* investing in test scenarios — vs after a test cycle has already surfaced a scope problem and the tester consults the rubric retroactively. Position is automatable; cognitive timing during testing is not.

**This decision assumes:** A skill-tester reading this skill will encounter the rubric-callback early enough to apply it before committing to test-scenario authoring, not as a sunk-cost-amplifying retroactive check.

**To shatter it:** After Phase 3 lands and the next time you (or another tester) apply this skill to a new skill-under-test, observe when the rubric-callback fires. Does it surface BEFORE you've drafted test scenarios, or AFTER — as a "why isn't this test showing me what I expected?" check?

**It's wrong if:** Skill-testers consistently discover the rubric-callback only after investing in test-scenario authoring, and find themselves either (a) defending scope choices they'd reconsider if they'd caught them earlier, or (b) ignoring the rubric because they've sunk cost into testing as-is. That would mean the placement didn't achieve the pre-testing timing — either the H2 needs to move still earlier (before "When to Use", as the skill's opening check) or the rubric-callback needs a more intrusive trigger (e.g., wired into the subagent-dispatch prompt itself so the testing subagent raises the rubric as its first output).

## Phase 4: `writing-skills` cornerstone rewrite

Phase 4 itself produces no native UAT entries — all DRs routed to test-requirements. Back-referenced UAT entries from Phase 2 (DR8 rubric-callback timing in `writing-claude-directives`) and Phase 3 (DR7 rubric-callback timing in `testing-skills-with-subagents`) manifest here because Phase 4 is when orchestrator-to-rubric timing can first be exercised in practice with all three sub-skills wired together.

**DR-P4-INT-1 was DELETED during H3 revision (2026-04-18).** The original entry covered "Integration evidence: cornerstone production used the methodology it describes" — the meta-claim that Phase 4's production IS the integration evidence. The entry itself admitted the written evidence could be perfect while the lived process had skipped the methodology; the "To shatter it" procedure (compare commit history to GREEN narrative) offered no falsifiable test because the commits and the narrative share an author. Critical peer review flagged this as unauditable-by-design (H3 + H7). The replacement is Phase 5 Task 4.5 (frustration-signal audit, AC5.8): instead of auditing self-attested narrative against self-authored commits, the audit queries `cc-search-chats:search-chat` across all phase-authoring sessions within the plan's implementation window for user-expressed frustration signals. Frustration IS observable evidence that the methodology did NOT cohere at a given point — falsifiable, re-runnable by a later reviewer, and grounded in an independent record (the user's interaction transcript).

## Phase 5: Cross-reference audit, version bump, commit, frustration-signal audit

Phase 5 includes one UAT-bearing decision per H3 revision: the frustration-signal audit (AC5.8) produces a joint human-review output that requires human judgement for each match's categorisation.

### DR-P5-FRUST-1 — Frustration-signal audit categorisation (replaces DR-P4-INT-1)

**Originating decision:** Phase 5 Task 4.5 runs `cc-search-chats:search-chat` across all phase-authoring sessions within the plan's implementation window and collects matches on frustration-signal queries (safe query set, one term per invocation: `mate`, `FFS`, `deeply frustrating`, `deeply frustrated`, `no stop`, `stop no`, `this is wrong`, `yoloed`, `oh god`, `jesus`; plus manual uppercase-correction scanning). The query set was narrowed during M2 revision 2026-04-19 to work within the cc-search-chats CLI's FTS5 constraints — no regex, no OR, no apostrophes, no hyphens — see `docs/issues.md` ISSUE-10. Each match requires categorisation as GENUINE-FRUSTRATION / TECHNICAL-DISAGREEMENT / QUOTED-ILLUSTRATIVE before the audit produces a verdict. (M3 revision 2026-04-19 dropped the prior RESOLVED-IN-SESSION category — user-expressed frustration flags the audit regardless of whether the session self-corrected; "I got it to work in the end" is not a dismissal path.)

**What's automatable:** Running each safe query as a separate cc-search-chats invocation (`--days $DAYS_SINCE` for time-window, post-filter by match timestamp to bound the end of the window); unioning the per-query match lists by message UUID; collecting session ID + timestamp + ±5 surrounding messages per match; producing the match list in `phase_05_frustration_audit.md`. The automation is per-term: the executor invokes cc-search-chats N times (once per term), not once with an alternation. This is in test-requirements.md (AC5.8 automatable portion).

**What's NOT automatable:** The category assigned to each match. The difference between frustration and technical-disagreement lives in emotional register + discourse context (was the user frustrated, or just pivoting?); quoted-illustrative matches need human recognition that the context is quotation not direct expression. A regex pass cannot make these distinctions reliably — a human who was there (or reads the surrounding context) must. (M3 revision 2026-04-19: the former resolved-vs-unresolved distinction is removed — subsequent course-correction is noted as observational context but does not change the category, because methodology that requires user frustration to self-correct is still methodology that failed at that point.)

**This decision assumes:** The user reviewing the matches remembers (or can reconstruct from context) whether their frustration at time T was about methodology failure or something incidental (tool malfunction, external interruption). If the user cannot distinguish, default to GENUINE-FRUSTRATION — the audit is biased toward flagging rather than dismissing.

**Known limit (L1 revision 2026-04-19):** The "joint human review" nominally pairs executor + user, but in the single-operator case the two roles collapse into one person — the same person whose authoring sessions are being audited. Unlike RED evidence (which uses an independent session's transcript as the evidence base), the frustration-signal audit's evidence base (cc-search-chats transcripts) IS independent of the executor, but the categorisation step is not. This makes AC5.8's categorisation less independently verifiable than RED evidence. Mitigation already in the design: (a) the "default to GENUINE-FRUSTRATION" tiebreak biases toward flagging; (b) the transcripts are the ground truth — a later reviewer can re-run the queries and re-categorise independently; (c) the M3 revision 2026-04-19 removed the RESOLVED-IN-SESSION dismissal path, so "I fixed it in session" cannot be retro-spun into a pass. The limit is acknowledged, not eliminated; it is a bounded defect, not a rejection of the audit.

**Fatigue-floor and calibration check (Meta-M7 revision 2026-04-19):** The review session(s) that audited this plan's design explicitly quote the frustration queries by name (`mate`, `FFS`, `yoloed`, `this is wrong`) — so when cc-search-chats sweeps the implementation window, it will also return QUOTED-ILLUSTRATIVE matches from those review sessions. Fast-categorising a long list risks false-dismissing a genuine match as QUOTED-ILLUSTRATIVE because the context looks superficially like a quotation. Phase 5 Task 4.5 Step 3 therefore includes two procedural guardrails: (1) a 30-match fatigue-floor (halt and resume in a later sitting if the combined list exceeds 30), and (2) a blinded recategorisation of three random matches per assigned category (so up to 9 samples); if >1 sample disagrees with the original verdict, the categorisation pass is flagged as calibration-failed and Step 4's verdict logic treats calibration-failed equivalently to ≥1 unresolved GENUINE-FRUSTRATION match. Both are process discipline, not category-scheme changes.

**To shatter it:** Consider a match where the user said "mate" after Claude proposed the wrong three options. Is that frustration at the methodology, or technical disagreement about the options? The category assigned changes the verdict. If the user consistently categorises ambiguous matches as technical-disagreement, the audit systematically under-reports methodology failure; if consistently as genuine-frustration, it over-reports. The joint review is the mechanism for calibration, but the calibration is human-judgement-load-bearing.

**It's wrong if:** The audit produces zero genuine-frustration matches but the user, reading the full transcript later, recalls clear frustration that the keyword queries missed (e.g., tone-of-voice frustration without a flagged word). That would mean the query list is incomplete and the audit gave a false-pass. Mitigation: the query list is extensible; if the user adds signals during joint review, the audit can re-run with the expanded queries before producing its verdict.

## Phase 6: Harden `impl-plan-write` against UAT smuggling

Phase 6 produces no native UAT entries — all three DRs routed to test-requirements. This is itself evidence of the amended three-lens table at work: zero UAT entries is a first-class valid output for a skill-internal refactor phase whose decisions all decompose to automatable checks (per AC6.7).

---

*All six phases (plus Phase 2.5 preparatory-refactor) planned. Retroactive audit (Phase 6 Task 5) will rewrite any smuggled entries in place with provenance comments.*


