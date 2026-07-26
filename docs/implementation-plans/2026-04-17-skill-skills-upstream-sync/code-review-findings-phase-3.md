# Code Review Findings — phase-3

## Status: APPROVED

**Critical: 0 | Important: 1 | Minor: 2**

## Verification

```
Tests:  uv run pytest -q → 879 passed in 3.35s
Lint:   (no lint config for markdown; skill-lint tests included in pytest suite)

Embedded Task 2 script → PASS
Embedded Task 3 script → PASS
Embedded Task 4 script → PASS
Embedded Task 5 script → PASS
```

## Plan Alignment

- AC2.1 Conversation-Precedent Protocol H3 prepended into RED phase: ✓
- AC2.2 Synthetic scenarios repositioned as REFACTOR completeness tool: ✓
- AC2.3 Model-tier guidance, No Blaming the Model, flaky-result discipline retained: ✓
- AC2.4 Obra 7-pressure table + Key Elements + 3+ guidance absorbed into REFACTOR: ✓
- AC2.5 Rubric Callback H2 present, cross-references epistemic-humility: ✓
- AC2.6 Haiku passage reframed with operator-empirical anchor (unsuitable/judgement/empirical all present): ✓
- AC2.7 RED evidence file (phase_03_red_evidence.md) documents independent-session failure: ✓
- Task 5 Steps 3-4 (rubric self-application + user acknowledgement): ~ not in changeset — correctly excluded per prompt; flagged as intentional human-gated remainder
- UAT gate-form entry AM2-P3 appended to uat-requirements.md: ✓
- 2026-06-10 Amendment item 1 (dual-upstream drift survey): ✓ incorporated as appendix in red_evidence
- 2026-06-10 Amendment item 2 (Fable-tier manual checkpoint): ✓ AM2-P3 UAT entry
- 2026-06-10 Amendment item 3 (drop Real-World Impact): ✓ section deleted; load-bearing sentence folded into Core Principle
- Phase 2.5 Note A (Testing Checklist consistency): ✓ RED block updated to conversation-precedent; REFACTOR block gains synthetic-scenario item
- Phase 2.5 Note B (near-duplicate scenario decision): ✓ resolved by cross-reference; decision documented in commit body
- Task 3 consolidation judgement call (tables moved from VERIFY-GREEN rather than duplicated): ~ deviation from plan's "absorb verbatim from obra" framing, but justified — tables already existed in SKILL.md at the Phase 2.5 baseline; moving vs. duplicating is correct; verify script satisfied; documented in commit message

## Issues

### Important (count: 1)

- **Issue**: SKILL.md uses "Opus 4.8" (line 63) where the Task 2 plan spec explicitly says "update model anchors (Sonnet → Sonnet 4.6, Opus → Opus 4.7) consistent with Phase 2's model-tier-notes.md" and the commit message for 7d727b8 repeats "Sonnet 4.6, Opus 4.7". The plan spec is stale: model-tier-notes.md (the project-authoritative source, verified 2026-06-10) lists Opus 4.8 as current-generation and Opus 4.7 as "previous-generation Opus". So the SKILL.md value is correct relative to the authoritative source; the plan text and commit message are wrong.
- **Location**: SKILL.md line 63 (diff hunk `+The weakest model tier…Sonnet 4.6 and Opus 4.8 will follow them easily`); phase_03.md lines 183-185 and 239; commit 7d727b8 message.
- **Fix**: No change needed in SKILL.md — Opus 4.8 is correct per model-tier-notes.md. Update the plan spec text at phase_03.md lines 183-185 and 239 to read "Opus 4.8" so the spec matches both the authoritative source and the committed artefact, and so a future reader does not have to resolve the discrepancy themselves. This is a documentation consistency issue, not a code error, but it will confuse the next phase executor who reads the plan spec expecting Opus 4.7 and finds 4.8 in the file.

### Minor (count: 2)

- **Issue**: Note-B cross-reference sentence in the REFACTOR Pressure-Scenario Completeness Coverage subsection (SKILL.md line 257 in the diff) says "see that scenario for the side-by-side bad/good/great progression and the scenario-quality criteria it illustrates." The referenced "Great scenario" heading is under `## VERIFY GREEN: Pressure Testing` (line 133) which is *above* the REFACTOR phase in the document — the word "above" is absent from the pointer, so a reader scanning the REFACTOR section would have to search upward. The pointer is functional but directionally ambiguous.
- **Location**: SKILL.md diff hunk in commit 598ef7a, the lead paragraph of `### Pressure-Scenario Completeness Coverage`.
- **Fix**: Add "above" — "see the 'Great scenario' above under VERIFY GREEN for the bad/good/great progression…" — one word, eliminates the navigational ambiguity.

- **Issue**: The Rubric Callback H2 is placed at lines 34-37, between `## When to Use` (line 21) and `## TDD Mapping for Skill Testing` (line 38). The plan's Task 4 Step 3 says "Insert an H2 … between 'When to Use' and 'TDD Mapping for Skill Testing'." This is satisfied. However the body text of the Rubric Callback (single paragraph) makes no structural distinction between "the skill passes the rubric" and "the skill fails the rubric" — it describes what to do on failure ("revise the skill's scope") but not what to do on pass ("proceed to testing"). A reader invoking this skill for the first time may read the rubric-callback paragraph as a gating stop, not a gating check-and-proceed.
- **Location**: SKILL.md diff hunk in commit 2412bba, `## Rubric Callback` paragraph.
- **Fix**: Add a single sentence after the sunk-cost-amplifier clause: "If the skill passes all screens, proceed to the RED phase below." Keeps the gate explicit in both directions.

## Consolidation Opportunities (none visible in the diff)

No accretion detected in the diff context.

## Decision: APPROVED FOR MERGE

All four embedded verification scripts pass. 879 tests pass. All AC2.1-AC2.7 acceptance criteria satisfied. The Important finding (Opus 4.7 vs 4.8 in plan spec) does not affect the committed artefact — the SKILL.md value is correct. Both Minor findings are navigational; neither affects correctness or behaviour. Task 5 Steps 3-4 are correctly excluded from this changeset as human-gated remainder.
