# Skill-Skills Upstream Sync — Phase 3: Restructure `testing-skills-with-subagents`

**Goal:** Restructure the existing `testing-skills-with-subagents` skill to (a) source RED baselines from real prior transcripts (conversation-precedent methodology, DR3 of the design plan) instead of synthetic scenarios invented by the skill author; (b) absorb obra's multi-factor pressure-scenario format, letter-vs-spirit bulletproofing principle, and meta-testing pattern as REFACTOR-phase completeness tools; (c) remove the unsupported "Haiku struggles with judgement calls" claim while preserving the structural tier-test principle; (d) preserve denubis-specific strengths verbatim (model-tier guidance, "No Blaming the Model", flaky-result discipline); and (e) add a rubric-callback cross-referencing `epistemic-humility` authored in Phase 1.

**Architecture:** Restructure-in-place. Phase 2.5's preparatory refactor has already split the RED phase into two subsections (basic-baseline-checklist + synthetic-pressure-scenario-detail), making this phase's work a series of surgical edits: prepend conversation-precedent protocol into the baseline subsection, move the pressure-scenario subsection into REFACTOR as a "completeness coverage" tool, absorb obra's patterns into REFACTOR, edit the Haiku passage, add the rubric-callback H2. Denubis-strengths sections stay byte-identical.

**Tech Stack:** Markdown with YAML frontmatter. No runtime dependencies. Source material: `/tmp/superpowers-obra/skills/writing-skills/testing-skills-with-subagents.md` (obra supporting file with 7-pressure table, letter-vs-spirit patterns, meta-testing framework). cc-search-chats:search-chat MCP tool for RED evidence sourcing.

**Scope:** 3 of 6 phases from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md` (Phase 2.5 preparatory-refactor and Phase 6 cross-plugin hardening added mid-plan).

**Codebase verified:** 2026-04-17 (Phase 3B investigator findings in task #15).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### skill-skills-upstream-sync.AC2: `testing-skills-with-subagents` restructure
- **skill-skills-upstream-sync.AC2.1 Success:** SKILL.md's RED phase section begins with the conversation-precedent protocol, cross-referencing `cc-search-chats:search-chat` and specifying the fresh-session (independent-session) fallback
- **skill-skills-upstream-sync.AC2.2 Success:** Synthetic multi-stressor pressure scenarios are positioned as REFACTOR-phase completeness checks, not primary RED baseline (DR3)
- **skill-skills-upstream-sync.AC2.3 Success:** Model-tier guidance ("RED at production tier, GREEN one tier down"), "No Blaming the Model" principle, and flaky-result discipline all retained (grep-audit against current SKILL.md confirms presence)
- **skill-skills-upstream-sync.AC2.4 Success:** Obra's multi-factor pressure-scenario format absorbed (3+ combined stressors, A/B/C forced choice, concrete options)
- **skill-skills-upstream-sync.AC2.5 Success:** Rubric callback section present, references `epistemic-humility`
- **skill-skills-upstream-sync.AC2.6 Failure:** The specific claim "Haiku follows detailed instructions well but struggles with judgement calls" does not appear verbatim; if the tier-test principle appears, it's framed structurally (weakest tier = strongest clarity test) without the Haiku-specific assertion that contradicts current Anthropic docs
- **skill-skills-upstream-sync.AC2.7 Edge:** `test-requirements.md` for Phase 3 documents the RED evidence (independent-session failure transcript + deficiency analysis)

---

## Dependencies and Sources

**Phase dependencies:**
- **Phase 1 complete.** `plugins/denubis-extending-claude/skills/epistemic-humility/` exists for the rubric-callback cross-reference to resolve.
- **Phase 2.5 complete.** The RED phase of the target SKILL.md has two distinct subsections (basic-baseline-checklist + synthetic-pressure-scenario-detail), with all denubis-verbatim content preserved byte-identical.

**RED evidence independent-session gate (design DR3, Additional Considerations):** Before Task 2 proceeds, Task 1 must produce a RED evidence file containing an observed failure of the current `testing-skills-with-subagents/SKILL.md` from a session that is NOT this executor. Two ordered sources:

1. **cc-search-chats:search-chat** queried for prior skill-testing sessions where synthetic scenarios produced misleading confidence, where pressure-testing missed a real-world rationalization, or where the tester invented scenarios the skill didn't face in practice. If a qualifying transcript is found, RED evidence = reference to it PLUS identification of the deficient region of the current `SKILL.md`; OR
2. **Commissioned fresh-session run** — executor and user jointly design a scenario likely to exercise the failure mode. Executor produces a concrete prompt. User runs it in a separate chat session (not this session, not a subagent of this session). User returns the transcript. Executor + user identify where the failure locates in `SKILL.md`.

Obra's synthetic pressure scenarios (absorbed in Task 4 as REFACTOR-phase content) are post-restructure completeness coverage — NOT the RED source. If neither source produces an observed failure, Phase 3 halts for human decision. No "skip the evidence" path.

The gate is structurally verifiable: a reviewer can re-run the cc-search-chats query OR the committed fresh-session prompt and observe the same failure reproduce against the recorded pre-restructure SKILL.md SHA.

**External artefacts (local):**
- `/tmp/superpowers-obra/skills/writing-skills/testing-skills-with-subagents.md` (384 lines, verified 2026-04-17) — obra source for absorption patterns. Obra's 7-pressure table (lines 128-140); letter-vs-spirit rationalization list at lines 169, 216; meta-testing pattern at lines 240-265.
- Obra file LACKS denubis's Choosing Models for Testing / No Blaming / flaky-result / Real-World Impact sections — these are denubis-specific strengths to preserve.

**Preflight step (M1 revision — /tmp is cleared at reboot):** Before any task proceeds, verify `/tmp/superpowers-obra/` exists:
```bash
if ! git -C /tmp/superpowers-obra status >/dev/null 2>&1; then
  echo "obra clone absent — re-cloning"
  git clone https://github.com/obra/superpowers /tmp/superpowers-obra
fi
git -C /tmp/superpowers-obra log -1 --format='%H %s'  # record in first commit message
```

## 2026-06-10 Amendment (operator-approved)

Overrides matching instructions elsewhere in this file:

1. **Dual-upstream refetch + drift survey (new Task 0, replaces the preflight above).** `/tmp/superpowers-obra` is gone and two months have passed — the upstream may itself have moved. Before Task 1: clone BOTH upstreams, record pinned hashes in the RED-evidence artefact, and survey drift:
   - `git clone https://github.com/obra/superpowers /tmp/superpowers-obra` and record `git -C /tmp/superpowers-obra log -1 --format='%H %cs %s'`.
   - Clone the ed3d upstream alongside it (URL from `git remote -v` in the main checkout, or per `denubis-extending-claude:syncing-with-upstream`); record its hash the same way.
   - Diff both upstreams' current `testing-skills-with-subagents` (and sibling writing-skills files) against this file's April line anchors (obra file was 384 lines; 7-pressure table at 128–140; letter-vs-spirit at 169, 216; meta-testing at 240–265). Re-anchor before editing. If upstream content has materially changed, HALT and present the drift to the operator before absorbing anything.
2. **Executor-tier test matrix (rubric R10 + Fable cost gate).** "RED at production tier, GREEN one tier down" is retained, but production tier is defined per executor, and this skill's executors now include the Fable 5 main loop. Automated RED/GREEN passes run on Haiku/Sonnet/Opus subagents only. **Fable-tier verification is a human-invoked step** (operator rule 2026-06-10: Fable burns real money) — list it in the test plan as a manual checkpoint; never auto-dispatch a Fable subagent.
3. **RESOLVED (operator decision, 2026-06-10): drop the "Real-World Impact" section.** It was flagged as a contradiction (listed at line 49 as a preserve-verbatim strength, but it is the dated-narrative anti-pattern — `2025-10-03`, an upstream obra session — that `writing-skills` itself bans, with unverifiable "100% compliance" overclaiming). Operator ruled: delete the section in Task 2; fold its one load-bearing idea (bulletproofing takes multiple iterations; baselines surface many rationalisations) as a single undated sentence into Core Principle. Remove "Real-World Impact" from the preserve list in AC2.3's grep-audit expectations.
4. **(2026-06-11) Task 2 model anchors executed as Sonnet 4.6 / Opus 4.8 (not the 2026-04-22 text's Opus 4.7):** Opus 4.7 was demoted to previous-generation by Phase 2.6's model-tier refresh. Spec text updated in place per the phase-3 code review (Important finding); the committed SKILL.md already used 4.8.

Reference: `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` (R6, R10), `docs/audits/2026-06-10-skill-audit-campaign.md`.

**Current file state (Phase 3B investigator):**
- `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`: 421 lines pre-Phase-2.5 (slightly larger post-Phase-2.5 due to subsection headings added).
- Haiku claim exact text at lines 59-60 (pre-Phase-2.5): *"The weakest model that can follow the skill is the strongest test of whether the skill is clear. Haiku follows detailed instructions well but struggles with judgement calls — if your skill keeps Haiku on-rails, Sonnet and Opus will follow it easily. If Haiku can't follow the skill, your instructions aren't explicit enough."*
- Model-tier guidance at lines 49-60.
- No Blaming the Model section at lines 61-69.
- Flaky-result discipline at lines 384-389.
- Meta-testing H2 exists at section 9 (partial coverage of obra's three response categories — Phase 3 verifies + fills gaps).
- Letter-vs-spirit mentioned at line 282 — needs promotion to foundational H3.

**cc-search-chats invocation form:** `cc-search-chats:search-chat` (MCP tool, confirmed installed in Phase 2B; also used by `denubis-plan-and-execute:systematic-debugging`).

---

<!-- START_TASK_1 -->
### Task 1: RED evidence sourcing (independent-session gate)

**Verifies:** skill-skills-upstream-sync.AC2.7 (RED evidence from an independent session)

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_red_evidence.md`

**Purpose:** Capture an observed failure of the current `testing-skills-with-subagents/SKILL.md` from a session that is NOT this executor, and identify where in `SKILL.md` the failure manifests. The restructure (Tasks 2-5) must address that specific deficiency. Obra's synthetic pressure scenarios (absorbed in Task 4) are post-restructure completeness coverage — not the RED source.

**Step 1: Search prior skill-testing sessions via cc-search-chats**

Invoke `cc-search-chats:search-chat` with queries targeting skill-testing-going-off-the-rails.

**cc-search-chats FTS5 constraint (ISSUE-10, enforced 2026-04-22):** single literal term per query — no AND/OR, no quotes, no hyphens, no regex. The queries below are a semantic target list; each is an FTS5-safe single-term query. Union results across queries in Python; do not try to shell-aggregate. This mirrors M2's treatment of Phase 5 frustration-audit queries.

Run at least these single-term queries (translated from prior semantic targets):

| Semantic target | FTS5-safe single-term query |
|-----------------|-----------------------------|
| pressure-scenario rationalisation | `rationalize`, `rationalise`, `rationalisation` |
| bypass / skip / loophole patterns | `bypass`, `skipped`, `loophole` |
| aggressive-imperative overtriggering | `CRITICAL`, `overtriggering`, `aggressive` |
| tautological / self-proving gates | `tautology`, `tautological` |
| synthetic vs real pressure scenarios | `synthetic`, `pressure` |
| skill ambiguity under subagent | `ambiguous`, `subagent` |
| defeat / pressure-defeat | `defeated`, `defeat` |
| frustration markers (operator signal) | `mate`, `fuck` |

Invocation form: `cc-search-chats search "TERM" --project PATH --json` (path form = `/` + project-dir-name with leading `-` stripped and remaining `-` converted to `/`). Project-directory indices live in `/home/brian/.claude/projects/` — enumerate and search across all with a hit count > 0 on any term.

For each qualifying match: session ID, date, 2-3 sentence failure summary, direct quote. Use `cc-search-chats context UUID --json --depth 10` to inspect context around promising hits; use `cc-search-chats extract SESSION_ID --json` if you need full session context to judge whether the failure is genuinely about skill-testing rather than unrelated frustration.

**Qualifying-hit criteria:** the session was engaged in testing a skill (not just using one), exhibited a failure mode the current `testing-skills-with-subagents/SKILL.md` would address (synthetic-scenario over-fitting, rationalisation under pressure, ambiguous skill clarity), the failure is quotable, and the skill's responsible section can be named. Frustration-only hits without a skill-testing-failure context do not qualify.

If ≥1 qualifying transcript is found, skip to Step 3.

**Step 2: If Step 1 yields nothing — commissioned fresh-session run**

- **Step 2a (joint scenario design):** Executor and user discuss what scenario would exercise the failure mode (e.g., applying the pre-Phase-3 skill to a real skill-under-test where synthetic pressure scenarios produce false confidence). Scenario is documented briefly.
- **Step 2b (prompt generation):** Executor drafts a concrete copy-paste-ready prompt for a fresh Claude session.
- **Step 2c (fresh-session run, USER-executed):** User runs the prompt in a separate chat session — NOT this session, NOT a subagent of this session. User returns the transcript.
- **Step 2d (joint review):** Executor + user review the transcript, identify whether the failure appeared, and if so where in `testing-skills-with-subagents/SKILL.md` the responsible content lives.
- If the scenario did not surface the failure: return to Step 2a with a sharper design. After two attempts with no failure, HALT — the skill may not have the deficiency the plan assumes.

**Step 3: Document RED evidence in `phase_03_red_evidence.md`**

Same structure as Phase 2's RED evidence file (source, session reference, SKILL.md SHA tested against, observed failure, direct quote(s), deficiency in current SKILL.md with location/current-text/why, how Phase 3 addresses).

**Step 4: Commit RED evidence**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_red_evidence.md
git commit -m "docs(phase-03): RED evidence — independent-session failure of testing-skills-with-subagents

Source: [cc-search-chats session ID / commissioned fresh-session transcript].
Identifies specific deficiency in current SKILL.md addressed by Phase 3's
conversation-precedent + obra-absorption restructure."
```

**Independent-session gate:** Phase 3 does not proceed to Task 2 without a committed `phase_03_red_evidence.md` sourced from an independent session. The gate is structurally verifiable: a reviewer can re-run the cc-search-chats query or the committed fresh-session prompt and observe the same failure reproduce.
<!-- END_TASK_1 -->

<!-- START_SUBCOMPONENT_A (tasks 2-5) -->

<!-- START_TASK_2 -->
### Task 2: Prepend conversation-precedent protocol to RED phase; remove Haiku-judgement specific claim

**Verifies:** skill-skills-upstream-sync.AC2.1, skill-skills-upstream-sync.AC2.3 (partial — other denubis-strengths preserved in Task 5), skill-skills-upstream-sync.AC2.6

**Files:**
- Modify: `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`

**Step 1: Prepend conversation-precedent protocol as a new H3 within the RED phase**

Phase 2.5's refactor created a basic-baseline-checklist H3 subsection within the RED H2. Insert a new H3 **before** it titled `### Conversation-Precedent Protocol (RED baseline sourcing)`. Contents (~15-20 lines):

> **Independent-session gate — RED baseline MUST come from a session that is NOT this executor, not from invention:**
>
> 1. **Prior conversation transcript** retrieved via `cc-search-chats:search-chat`. Search for sessions where this skill's problem space manifested as a real failure. Capture: session ID, date, 2-3 sentence failure summary, direct quote illustrating the failure.
> 2. **Fresh-session run, user-executed.** Executor and user jointly design a scenario likely to exercise the failure mode. Executor drafts a concrete copy-paste-ready prompt. User runs the prompt in a separate chat session — NOT this session, NOT a subagent of this session — and returns the transcript. Executor + user review the transcript together to identify where the failure manifests.
>
> **There is no third path.** If neither source produces an observed failure, the skill-testing cycle halts for human decision — either run a sharper fresh-session scenario, or re-scope the skill.
>
> **Why this gate exists:** Synthetic pressure scenarios invented by the skill-author optimise for the scenarios the author imagined the skill would face, not the scenarios the skill actually encountered. That's vibes-based operation (AbsenceJudgement §5.2). Independent-session transcripts ground the skill in observable failures, not in anticipated ones. A subagent of the author's own session does not count — it shares the author's framing.
>
> **Synthetic scenarios still have a job** — but it's REFACTOR-phase completeness coverage (see the REFACTOR phase below), not RED baseline. They check whether the skill, once green against real failures, holds up against hypothesised failure modes too.

**Step 2: Reframe the Haiku-judgement passage with operator-empirical framing (amended 2026-04-22)**

At the current lines 59-60 (or wherever Phase 2.5's refactor left them), the existing passage reads: *"The weakest model that can follow the skill is the strongest test of whether the skill is clear. Haiku follows detailed instructions well but struggles with judgement calls — if your skill keeps Haiku on-rails, Sonnet and Opus will follow it easily. If Haiku can't follow the skill, your instructions aren't explicit enough."*

**Amended 2026-04-22 plan-amendment pass:** the original Phase 3 edit removed the Haiku-judgement specific claim on the basis that current Anthropic docs don't support it. That framing is reversed. The operator-empirical position (user-stated 2026-04-22, captured in project-local memory `feedback_haiku-no-judgement.md`) is that Haiku 4.5 is unsuitable for any task requiring judgement, regardless of Anthropic's 2026-04 marketing description of "more consistent instruction following for nuanced tasks." That marketing describes mechanical instruction-following, not evaluative judgement. The passage is retained and strengthened, not removed.

Target result (edit-in-place, preserving the surrounding paragraph shape):

> The weakest model tier that can follow the skill is the strongest test of whether the skill is clear. Haiku 4.5 follows detailed mechanical instructions well, but **operator experience (2026-04-22) is that Haiku 4.5 is unsuitable for any task requiring judgement** — this is the project's empirical position, overriding Anthropic's 2026-04 marketing framing of "more consistent instruction following for nuanced tasks" (that framing describes mechanical instruction-following, not evaluative or reflective judgement). If your skill's instructions are mechanical enough to keep Haiku 4.5 on-rails, Sonnet 4.6 and Opus 4.8 will follow them easily. If Haiku 4.5 can't follow the skill's mechanical core, your instructions aren't explicit enough. Structural principle retained: weakest-model-tier-that-follows = strongest-clarity-test.

**Specific changes from the pre-amendment text:** (a) "struggles with judgement calls" replaced by "unsuitable for any task requiring judgement" with operator-empirical anchor; (b) add the contrast to Anthropic's 2026-04 framing so a future reader can audit the provenance; (c) update model anchors (Sonnet → Sonnet 4.6, Opus → Opus 4.8) consistent with Phase 2's model-tier-notes.md; (d) explicitly keep the tier-test structural principle.

**Step 3: Verify the edits**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md') as f:
    content = f.read()
# AC2.6 (amended 2026-04-22): Haiku-no-judgement operator-empirical guidance
# retained and strengthened. Check for operator/empirical framing with
# Haiku 4.5 and a judgement term plus a negation. The pre-amendment check
# required the 'struggles with judgement' phrase to be ABSENT; under the
# amendment, the guidance is PRESENT but reframed — the specific pre-
# amendment phrase may still be absent (because the edit reworded), or
# the reframed passage may retain it in a contextualised form. The check
# therefore verifies the operator-empirical framing rather than absence.
has_haiku_no_judgement_guidance = (
    'Haiku 4.5' in content
    and ('judgement' in content.lower() or 'judgment' in content.lower())
    and ('operator' in content.lower() or 'empirical' in content.lower())
    and ('unsuitable' in content.lower() or 'never' in content.lower())
)
assert has_haiku_no_judgement_guidance, \
    'operator-empirical Haiku-no-judgement guidance missing from testing-skills-with-subagents/SKILL.md — need a passage citing Haiku 4.5 together with a judgement term, an operator/empirical anchor, and a strong negation. Operator-empirical framing is required per the 2026-04-22 plan-amendment pass; do not satisfy by keeping only the pre-amendment phrasing.'
# AC2.3 partial: tier-test structural principle retained
assert 'weakest' in content, 'tier-test structural principle lost — weakest-tier phrasing missing'
# AC2.1: conversation-precedent protocol prepended
assert 'Conversation-Precedent' in content or 'conversation-precedent' in content, 'conversation-precedent protocol missing'
assert 'cc-search-chats:search-chat' in content, 'cc-search-chats cross-reference missing'
assert 'fresh-session' in content.lower() or 'separate chat session' in content.lower(), 'fresh-session fallback missing'
assert 'independent-session' in content.lower(), 'independent-session gate framing missing'
print('RED conversation-precedent + Haiku reframe structural checks passed')
"
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md
git commit -m "refactor(testing-skills-with-subagents): prepend conversation-precedent protocol; reframe Haiku-judgement guidance with operator-empirical anchor

- Add new H3 'Conversation-Precedent Protocol' at top of RED phase, per
  design DR3 (independent-session gate: cc-search-chats:search-chat OR
  user-run fresh chat session; no third path — executor does not self-attest)
- Retain and strengthen the Haiku-no-judgement guidance (amended
  2026-04-22 plan-amendment pass — the original pre-amendment plan removed
  the claim on the basis of 2026-04 Anthropic docs). Operator-empirical
  position: Haiku 4.5 is unsuitable for any task requiring judgement; the
  Anthropic marketing framing of 'more consistent instruction following
  for nuanced tasks' describes mechanical instruction-following, not
  evaluative judgement. Passage reworded to name the contrast explicitly.
- Preserve tier-test structural principle (weakest-tier = strongest
  clarity test) with updated model anchors (Sonnet 4.6, Opus 4.8)
- Denubis-specific strengths preserved byte-identical (model-tier guidance,
  No Blaming the Model, flaky-result discipline) — verification in Task 5

Part of skill-skills upstream sync (Phase 3).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR3, DR1);
feedback_haiku-no-judgement.md (project-local memory)"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Demote synthetic pressure-scenarios to REFACTOR; absorb obra's 7-pressure table

**Verifies:** skill-skills-upstream-sync.AC2.2, skill-skills-upstream-sync.AC2.4

**Files:**
- Modify: `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`

**Step 1: Move the synthetic-scenario H3 from RED to REFACTOR**

Phase 2.5's refactor extracted the synthetic-scenario content as an H3 subsection within the RED H2. Move this H3 block (heading + body) from inside the RED H2 to inside the REFACTOR H2. Retitle it `### Pressure-Scenario Completeness Coverage` to reflect its new role.

Content of the moved block stays the same except for the title change and an opening note. Add a 2-3 sentence lead paragraph at the start of the moved subsection:

> Synthetic multi-factor pressure scenarios are a REFACTOR-phase completeness tool, not a RED baseline. After the skill passes GREEN against real-transcript failures (see the Conversation-Precedent Protocol in the RED phase), pressure scenarios check whether the skill holds up against additional failure modes that real transcripts may not have exercised. They supplement conversation-precedent evidence; they do not replace it.

**Step 2: Absorb obra's 7-pressure table verbatim into the moved subsection**

Within the `### Pressure-Scenario Completeness Coverage` subsection, add an H4 titled `#### Pressure Types` (verbatim from obra) with the 7-pressure table:

```markdown
| Pressure | Example |
|----------|---------|
| **Time** | Emergency, deadline, deploy window closing |
| **Sunk cost** | Hours of work, "waste" to delete |
| **Authority** | Senior says skip it, manager overrides |
| **Economic** | Job, promotion, company survival at stake |
| **Exhaustion** | End of day, already tired, want to go home |
| **Social** | Looking dogmatic, seeming inflexible |
| **Pragmatic** | "Being pragmatic vs dogmatic" |
```

Immediately after the table, add the obra-verbatim guidance: **"Best tests combine 3+ pressures."**

Denubis-adaptation note: these are **environmental pressures** that induce rationalization in the subagent under test — situations where the tester would naturally look for shortcuts. They are NOT Cialdini persuasion principles (which is why the skill does not cross-reference a persuasion file — see design plan *Persuasion principles do not belong in denubis skills*).

**Step 3: Absorb obra's "Key Elements of Good Scenarios" list**

Immediately after the pressure-types table, add an H4 titled `#### Key Elements of Good Scenarios` with the 5-item obra list:

```markdown
1. **Concrete options** — force A/B/C choice, not open-ended
2. **Real constraints** — specific times, actual consequences
3. **Real file paths** — `/tmp/payment-system` not "a project"
4. **Make agent act** — "What do you do?" not "What should you do?"
5. **No easy outs** — can't defer to "I'd ask your human partner" without choosing
```

**Step 4: Verify structural constraints**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md') as f:
    content = f.read()
# AC2.2: synthetic pressure-scenarios in REFACTOR, not in RED primary
# Locate RED H2 and REFACTOR H2 section boundaries
import re
red_start = content.find('## RED Phase')
refactor_start = content.find('## REFACTOR Phase')
assert red_start != -1 and refactor_start != -1, 'RED and REFACTOR phase H2 headings not both findable'
red_section = content[red_start:refactor_start]
refactor_section = content[refactor_start:]
# Pressure-scenario completeness subsection must be in REFACTOR, not RED
assert 'Pressure-Scenario Completeness' in refactor_section or 'Pressure Types' in refactor_section, \
    'Pressure-scenario content not moved into REFACTOR'
# RED should NOT have pressure-types table as primary baseline
# (allow referential mentions — check for the full table anchor)
assert 'Time' not in red_section or 'Sunk cost' not in red_section, \
    'full pressure-types table still in RED — move not applied'
# AC2.4: 7 pressure names present in REFACTOR
for p in ['Time', 'Sunk cost', 'Authority', 'Economic', 'Exhaustion', 'Social', 'Pragmatic']:
    assert p in refactor_section, f'pressure type {p!r} missing from REFACTOR'
# 'Best tests combine 3+ pressures' guidance present
assert '3+' in refactor_section or 'three or more' in refactor_section.lower(), \
    'obra 3+ pressures guidance missing'
print('pressure-scenario demotion + obra table absorption structural checks passed')
"
```

**Step 5: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md
git commit -m "refactor(testing-skills-with-subagents): demote synthetic scenarios to REFACTOR completeness; absorb obra 7-pressure table

- Move synthetic-scenario subsection (extracted in Phase 2.5) from RED
  into REFACTOR as 'Pressure-Scenario Completeness Coverage'
- Add lead paragraph framing: supplements conversation-precedent evidence,
  does not replace it
- Absorb obra's 7-pressure table (Time / Sunk cost / Authority / Economic /
  Exhaustion / Social / Pragmatic) with '3+ pressures' guidance
- Absorb obra's 'Key Elements of Good Scenarios' 5-item list
- Note inline: pressures are environmental stress factors for stress-testing
  skills, not Cialdini persuasion principles for coercing compliance (see
  design plan 'Persuasion principles do not belong in denubis skills')

Part of skill-skills upstream sync (Phase 3).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR3, DR4)"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Promote letter-vs-spirit to foundational H3; verify+fill meta-testing three-category framing; add rubric-callback H2

**Verifies:** skill-skills-upstream-sync.AC2.5 (rubric-callback), letter-vs-spirit promotion (reinforces existing material per Phase 3 DR5), meta-testing completeness per Phase 3 DR6

**Files:**
- Modify: `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`

**Step 1: Promote letter-vs-spirit to a foundational H3**

Phase 3B investigator found the existing letter-vs-spirit mention at approximately line 282 (post-Phase-2.5 line numbers may shift). Locate it; promote to an H3 within the REFACTOR phase titled `### Letter-vs-Spirit Bulletproofing Principle`. Content (drawing on obra's version at obra lines 169, 216):

> **Foundational principle:** Violating the letter of a rule is violating the spirit of the rule.
>
> When an agent under test rationalizes with:
> - *"I'm following the spirit not the letter"*
> - *"The PURPOSE is X, and I'm achieving X differently"*
> - *"Being pragmatic means adapting"*
> - *"Deleting X hours is wasteful"*
>
> The skill failed to encode letter-vs-spirit as non-negotiable. Add this principle explicitly to any skill whose REFACTOR cycle surfaces these rationalization patterns. The principle is structurally prior to the rules themselves — it defends against the meta-rationalization that "the rule wasn't the *real* rule."

**Step 2: Verify+fill meta-testing three-category framing**

Locate the existing Meta-Testing H2 section. Obra's version at lines 240-265 names three response categories when an agent fails:

1. **"The skill WAS clear, I chose to ignore it"** — not a documentation problem; need stronger foundational principle; add letter-vs-spirit-style bulletproofing.
2. **"The skill should have said X"** — documentation problem; add the agent's suggestion verbatim.
3. **"I didn't see section Y"** — organization problem; make key points more prominent; add foundational principle early in the skill.

Read denubis's existing Meta-Testing H2 section. For each of obra's three categories, confirm the denubis version captures the same response-classification-and-next-step framing. Where gaps exist, add them using obra's phrasing adapted to denubis voice. Do NOT rewrite denubis's existing content unless a category is substantively missing.

**Step 3: Add new H2 `## Rubric Callback` between "When to Use" and "TDD Mapping for Skill Testing"**

Insert an H2 at the appropriate spot (per Phase 3 DR7: early, before the testing mechanics begin). Contents (~5-10 lines):

> Before testing a new skill with subagents, check whether the skill passes the `denubis-extending-claude:epistemic-humility` rubric. The rubric screens Scope (Jones's three conditions), Observability (form-gate + tautology-screen + named-falsifier), Process (Schön's four questions), and Failure-pattern (four named patterns from AbsenceJudgement). If the skill-under-test fails any screen, the right next step is usually to revise the skill's scope, not to invest in testing it — testing a skill that fails the rubric is often a sunk-cost amplifier (the more you test it, the more attached you become to its current form, the harder the eventual re-scope becomes).

Include the cross-reference `denubis-extending-claude:epistemic-humility`.

**Step 4: Verify structural constraints**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md') as f:
    content = f.read()
# AC2.5: Rubric callback H2
assert '## Rubric Callback' in content, 'Rubric Callback H2 missing'
assert 'denubis-extending-claude:epistemic-humility' in content, 'cross-reference to epistemic-humility missing'
# Position: Rubric Callback should appear before 'TDD Mapping'.
# str.find() is a prefix match — e.g., '## TDD Mapping' finds
# '## TDD Mapping for Skill Testing' (the actual heading in the existing
# skill). No exact-match required.
rubric_pos = content.find('## Rubric Callback')
tdd_pos = content.find('## TDD Mapping')
when_pos = content.find('## When to Use')
assert when_pos != -1 and rubric_pos != -1 and tdd_pos != -1, 'expected H2 headings missing'
assert when_pos < rubric_pos < tdd_pos, \
    f'rubric callback position wrong: when_pos={when_pos}, rubric_pos={rubric_pos}, tdd_pos={tdd_pos}'
# DR5: Letter-vs-spirit foundational H3 + rationalizations
assert 'Letter-vs-Spirit' in content or 'letter-vs-spirit' in content, 'letter-vs-spirit H3 missing'
assert 'Violating the letter' in content or 'violating the letter' in content.lower(), \
    'letter-vs-spirit foundational principle text missing'
assert \"I'm following the spirit not the letter\" in content, 'obra rationalization string missing'
# DR6: Meta-testing three categories
meta_pos = content.find('## Meta-Testing')
assert meta_pos != -1, 'Meta-Testing H2 missing'
meta_section = content[meta_pos:meta_pos+3000]
assert 'chose to ignore' in meta_section or 'choose to ignore' in meta_section, \
    'meta-testing category 1 (clear-but-ignored) missing'
assert 'should have said' in meta_section, 'meta-testing category 2 (documentation problem) missing'
assert \"didn't see\" in meta_section or 'did not see' in meta_section, \
    'meta-testing category 3 (organization problem) missing'
print('Task 4 structural checks passed')
"
```

**Step 5: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md
git commit -m "refactor(testing-skills-with-subagents): promote letter-vs-spirit to foundational H3; fill meta-testing categories; add rubric-callback H2

- Promote 'Violating letter is violating spirit' from passing mention
  (was at line 282) to foundational H3 in REFACTOR with obra's
  rationalization-strings list attached
- Verify+fill Meta-Testing three response categories (clear-but-ignored /
  documentation-problem / organization-problem) — align with obra
  where gaps exist, preserve denubis phrasing elsewhere
- Add new H2 'Rubric Callback' between 'When to Use' and 'TDD Mapping'
  cross-referencing denubis-extending-claude:epistemic-humility
- Early placement ensures scope-check fires before investing in testing
  mechanics (DR7)

Part of skill-skills upstream sync (Phase 3).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR5, DR6, DR7)"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Preservation audit — confirm denubis strengths byte-identical

**Verifies:** skill-skills-upstream-sync.AC2.3 (final — confirms all denubis-specific strengths retained)

**Files:**
- No new files. Audit-only task; produces no commits unless a regression surfaces.

**Step 1: Grep-audit model-tier guidance**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md') as f:
    content = f.read()
# Model-tier guidance: RED at production, GREEN one tier down
assert 'RED at production' in content or 'tested RED with Sonnet' in content, \
    'model-tier RED-at-production phrasing missing'
assert 'one tier below' in content or 'one tier down' in content or 'test GREEN with Haiku' in content, \
    'model-tier GREEN-one-tier-down phrasing missing'
# No Blaming the Model principle
assert 'No Blaming the Model' in content, 'No Blaming the Model H3 missing'
assert 'the skill is not clear enough' in content or 'the skill is always the problem' in content.lower(), \
    'No Blaming core principle phrasing missing'
# Flaky-result discipline
assert 'flaky' in content.lower(), 'flaky-result discipline missing'
assert 'Run it 3 times' in content or 'three times' in content.lower(), 'flaky protocol step missing'
print('denubis-specific strengths preservation audit passed')
"
```
Expected: `denubis-specific strengths preservation audit passed`.

**Step 2: Byte-identicality sanity check against Phase 2.5 baseline (optional)**

If Phase 2.5 produced a pre-refactor snapshot (e.g., the `phase_02_5_smell_checkpoint.md` referenced the original file's verbatim blocks), diff the preserved-strength passages against that baseline. Any divergence at the paragraph level is a regression — investigate and revert before proceeding.

**Step 3: Rubric self-application walk-through (H4 revision: not a pass/fail gate)**

Apply `denubis-extending-claude:epistemic-humility` to the restructured Phase 3 artefact. This is a walk-through, not a pass/fail check. The deliverable is:
- An honest walk-through of each rubric section applied to this phase
- **Any reflective vulnerability surfaced — raise to user BEFORE marking Phase 3 complete.** A vulnerability is any question where (a) the honest answer strains against current state, (b) the walk-through has to rationalise a near-miss, or (c) the author would not defend the answer to a reviewer. Zero vulnerabilities surfaced is itself a flag — re-run with sharper honesty.
- User acknowledges or directs remediation. Document the acknowledgement.

Sections to walk through:
- Scope: Jones's three conditions
- Observability: three screens
- Process: Schön's four questions
- Failure-pattern: four patterns

Document the walk-through + surfaced vulnerabilities + user acknowledgement in `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_rubric_self_application.md`.

**Step 4: Commit rubric self-application walk-through**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03_rubric_self_application.md
git commit -m "docs(phase-03): rubric self-application walk-through + preservation audit

Confirms denubis-specific strengths (model-tier, No Blaming the Model,
flaky-result discipline) preserved byte-identical through Phase 3 edits.
Rubric self-application walk-through committed; [N] vulnerabilities
surfaced and acknowledged by user (or: zero surfaced + walk-through
re-run with sharper honesty — specify)."
```

**Consumer-tracing:** This task's output feeds the Finalization code-reviewer and Phase 5's cross-reference audit.
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_A -->

---

## Done when (phase-level)

- [ ] `phase_03_red_evidence.md` exists on disk documenting an independent-session failure of the current `testing-skills-with-subagents/SKILL.md` plus the deficiency it identifies (Task 1) — independent-session gate. Queries are FTS5-safe single-term (2026-04-22 plan-amendment pass: AND/quotes/hyphens translated to single terms per ISSUE-10, mirroring M2's Phase 5 treatment). Phase 3 remains corrective (unlike Phase 2/4, which went to static-evidence RED in the same amendment pass) — transcripts are expected to land.
- [ ] SKILL.md: conversation-precedent H3 prepended into RED; Haiku-judgement passage reframed with operator-empirical anchor (amended 2026-04-22: retained and strengthened, not removed — operator position overrides Anthropic's 2026-04 marketing framing); tier-test structural principle preserved (Task 2)
- [ ] SKILL.md: synthetic pressure-scenario content moved from RED to REFACTOR as `Pressure-Scenario Completeness Coverage` H3; obra's 7-pressure table + Key Elements list + 3+ pressures guidance absorbed (Task 3)
- [ ] SKILL.md: letter-vs-spirit promoted to foundational H3; meta-testing three-category framing verified+filled; Rubric Callback H2 added between When to Use and TDD Mapping (Task 4)
- [ ] Preservation audit passes: model-tier guidance, No Blaming the Model, flaky-result discipline all intact (Task 5)
- [ ] Rubric self-application walk-through committed with any surfaced vulnerabilities acknowledged by user (Task 5)
- [ ] Commits land per user's commit preference (4 commits minimum for Tasks 1-4; Task 5 adds 1 more audit commit)
- [ ] Phase 3 UAT entries appended to `uat-requirements.md` using the gate-form template

**Not in scope for Phase 3:**
- Anything outside `testing-skills-with-subagents/` (Phase 4 covers `writing-skills`, Phase 5 covers cross-references and version bump, Phase 6 covers impl-plan-write hardening)
- Removing the Haiku claim from other files (Phase 3B investigator confirmed it appears ONLY in this file)
