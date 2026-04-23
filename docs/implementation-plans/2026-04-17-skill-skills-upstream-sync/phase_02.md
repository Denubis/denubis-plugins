# Skill-Skills Upstream Sync — Phase 2: Restructure `writing-claude-directives`

**Goal:** Restructure the existing `writing-claude-directives` skill to carry current (2026-04) model-tier guidance, drop the stale Opus 4.5 "Think Sensitivity" section, and add a rubric-callback cross-referencing `epistemic-humility` authored in Phase 1. **Persuasion-principles import from obra is explicitly dropped** per the design plan's *Persuasion principles do not belong in denubis skills* Additional Consideration.

**Architecture:** Restructure-in-place — preserve the existing 16-section SKILL.md spine and existing supporting files, delete the single stale subsection cleanly, lift scattered model-version anchors into a new `model-tier-notes.md` companion file organised per-model (refresh-cycles decouple), and add a short rubric-callback H2 between Compliance Techniques and Structure Patterns. `graphviz-conventions.dot` reconciliation is a no-op because our copy is byte-identical to obra's; we add an attribution comment block only. No persuasion-principles.md is imported; no persuasion section is added to SKILL.md.

**Tech Stack:** Markdown with YAML frontmatter. Graphviz `.dot` attribution comment only. No runtime dependencies. Source material: `/tmp/anthropic-system-card.pdf` (supplementary cross-verification); current public Anthropic docs at platform.claude.com, anthropic.com.

**Scope:** 2 of 6 phases from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md` (Phase 6 added mid-plan as cross-plugin hardening; see design plan).

**Codebase verified:** 2026-04-17 (Phase 2B investigator findings in task #11 completion).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### skill-skills-upstream-sync.AC3: `writing-claude-directives` restructure
- **skill-skills-upstream-sync.AC3.1 Success:** SKILL.md does not contain a section titled "Opus 4.5: 'Think' Sensitivity" (or equivalent) — stale claim fully removed
- **skill-skills-upstream-sync.AC3.2 Success:** `model-tier-notes.md` exists with separate sections for Opus 4.7, Sonnet 4.6, and Haiku 4.5; each section contains at least one citation URL to 2026 Anthropic documentation
- **skill-skills-upstream-sync.AC3.3 Success:** No `persuasion-principles.md` file is imported into `writing-claude-directives/`. Grep-audit of the skill directory returns zero files matching `persuasion*`. Denubis departs from obra here per the design plan's Additional Consideration.
- **skill-skills-upstream-sync.AC3.4 Success:** SKILL.md contains NO Cialdini/Meincke/persuasion-principles section. Grep-audit for "Cialdini", "Meincke", "persuasion principles" in SKILL.md returns zero hits.
- **skill-skills-upstream-sync.AC3.5 Success:** `graphviz-conventions.dot` reconciled against obra's version; reconciliation result documented in the commit message or phase notes
- **skill-skills-upstream-sync.AC3.6 Success:** Rubric callback section present, references `epistemic-humility`
- **skill-skills-upstream-sync.AC3.7 Failure:** No claim cites Opus 4.5 or Sonnet 4.5 as current (both superseded by Opus 4.7 / Sonnet 4.6); every model-specific claim — in `SKILL.md`, `model-tier-notes.md`, AND `long-running-state-patterns.md` (H6 revision: scope includes supporting files) — has an explicit current model-version anchor (e.g. "Opus 4.7:"). Haiku 4.5 is the current Haiku and remains valid.
- **skill-skills-upstream-sync.AC3.8 Edge:** `test-requirements.md` for Phase 2 documents the RED evidence (independent-session failure transcript + deficiency analysis) and the Anthropic PDF consumption (system card content incorporated into `model-tier-notes.md`)

---

## Dependencies and Sources

**Phase dependency:** Phase 1 complete. `plugins/denubis-extending-claude/skills/epistemic-humility/` exists for the rubric-callback cross-reference to resolve.

**RED evidence independent-session gate (design DR3, Additional Considerations):** Before Task 2 proceeds, Task 1 must produce a RED evidence file containing an observed failure of the current `writing-claude-directives/SKILL.md` from a session that is NOT this executor. Two ordered sources:

1. **cc-search-chats:search-chat** queried for prior sessions where directive-writing under model-version ambiguity failed. If a qualifying transcript is found, RED evidence = reference to it (session ID, date, quoted failure) PLUS identification of the deficient region of the current `SKILL.md`; OR
2. **Commissioned fresh-session run** — executor and user jointly design a scenario likely to exercise the failure mode. Executor produces a concrete prompt. User runs that prompt in a separate chat session (not this session, not a subagent of this session). User returns the transcript. Executor + user identify where the failure locates in `SKILL.md`.

The synthetic obra pressure scenarios at Task 5 are post-restructure regression checks — NOT the RED source. If neither source produces an observed failure, Phase 2 halts for human decision. No "skip the evidence" path.

The gate is structurally verifiable: a reviewer can re-run the cc-search-chats query OR the committed fresh-session prompt and observe the same failure reproduce against the pre-restructure `SKILL.md` SHA recorded in the evidence file.

**External artefacts (local, staged during Phase 2C):**
- `/tmp/superpowers-obra/skills/writing-skills/graphviz-conventions.dot` — byte-identical to our copy (confirmed via `diff -q`, no diff output). Reconciliation = attribution comment only.
- `/tmp/anthropic-system-card.pdf` (13.6M, PDF 1.4) — supplementary cross-verification source; not the primary citation per design plan Additional Considerations.

**Preflight step (M1 revision — /tmp is cleared at reboot on most Linux distributions):** Before ANY task in this phase proceeds, verify both artefacts exist. If either is absent, restore before continuing:
```bash
# Verify obra clone
if ! git -C /tmp/superpowers-obra status >/dev/null 2>&1; then
  echo "obra clone absent — re-cloning"
  git clone https://github.com/obra/superpowers /tmp/superpowers-obra
fi
git -C /tmp/superpowers-obra log -1 --format='%H %s'  # document the SHA used

# Verify system card PDF
if [ ! -f /tmp/anthropic-system-card.pdf ]; then
  echo "ERROR: /tmp/anthropic-system-card.pdf absent — halt for user decision"
  echo "User must provide the 2026-04 system card PDF (or newer). The original download URL lives in Anthropic's model-release blog posts."
  exit 1
fi
```
Record the obra SHA used in the phase's first commit message so a later reviewer can reproduce against the same upstream point.

**Not imported:** `/tmp/superpowers-obra/skills/writing-skills/persuasion-principles.md` — dropped per the design plan's *Persuasion principles do not belong in denubis skills* Additional Consideration. Retained in the obra clone at `/tmp/superpowers-obra/` for future reference; NOT copied into the denubis skill directory.

**Citation URLs verified 2026-04-17 (Phase 2C research):**
- Opus 4.7 / Sonnet 4.6 / Haiku 4.5 model pages and announcements: `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`, `https://platform.claude.com/docs/en/about-claude/models/overview`, `https://www.anthropic.com/news/claude-opus-4-7`, `https://www.anthropic.com/news/claude-sonnet-4-6`, `https://www.anthropic.com/news/claude-haiku-4-5`
- Extended thinking docs: `https://platform.claude.com/docs/en/build-with-claude/extended-thinking`

**Anthropic-docs guidance crystallised (2026-04):**
- Opus 4.7: literal instruction-following ("will not silently generalize"), new `xhigh` effort level ("Start with xhigh for coding and agentic use cases"), uses tools less / reasoning more than 4.6, long-horizon agentic focus.
- Sonnet 4.6: more steerable than Opus 4.6, proactive default, parallel tool-calling at ~100% with prompting guidance, agentic overtriggering possible in GUI but steerable.
- Haiku 4.5: Anthropic's 2026-04 description is "more consistent instruction following for nuanced tasks", 200k context / 128k extended-thinking budget, statistically safest among recent models for misaligned behaviours (vs Sonnet 4.5, Opus 4.1). **Operator-empirical position (2026-04-22 plan-amendment pass): Haiku 4.5 is unsuitable for any task requiring judgement, regardless of the Anthropic marketing framing. The project's Haiku-no-judgement guidance is retained and strengthened (not retired). Phase 2 Task 3 documents the operator-empirical position in `model-tier-notes.md`; Phase 3 Task 2 reframes the corresponding passage in `testing-skills-with-subagents/SKILL.md` with the same framing rather than removing it. See `feedback_haiku-no-judgement.md` in project-local memory for the standing operator position.**
- **Aggressive language guidance has EVOLVED but still applies.** Direct quote from current prompting best practices: *"The fix is to dial back any aggressive language. Where you might have said 'CRITICAL: You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'"* Our existing claim (lines 96, 237) is directionally correct but needs the anchor updated from generic "Claude 4.x" to "Opus 4.7 / Sonnet 4.6 / Haiku 4.5" with the current source URL.

**Current file state (Phase 2B investigator; long-running-state-patterns.md assessment updated during H6 revision):**
- `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md`: 271 lines, 16 H2 sections. Stale section at lines 215-220 (`### Opus 4.5: "Think" Sensitivity`). Scattered model-version anchors at lines 69, 96, 99, 237.
- Supporting files: `graphviz-conventions.dot` (5.8K, byte-identical to obra). `long-running-state-patterns.md` (6.3K): CONTAINS STALE MODEL ANCHORS per H6 finding (critical peer review 2026-04-17). Confirmed refs: line 15 `"Claude 4.5+"`, line 114 `"Opus 4.5"`, line 119 `"Sonnet/Haiku 4.5"`, line 132 `"Opus 4.5"`, line 133 `"Sonnet 4.5"`, lines 134/136 `"Haiku 4.5"` (CURRENT — Haiku 4.5 is the 2026-04 shipping version, keep). Earlier scope assessment "unchanged unless research surfaces updates — it did not" was wrong; AC3.7 requires every model-specific claim to have a correct anchor, and Opus 4.5 / Sonnet 4.5 are superseded by Opus 4.7 / Sonnet 4.6. Phase 2 scope expanded to update this file (Task 3.5 below).

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: RED evidence — static code-smell inventory (preventive restructure)

**Verifies:** skill-skills-upstream-sync.AC3.8 (RED evidence recorded for Phase 2)

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_red_evidence.md`

**Purpose:** Record the deficiencies in the current `writing-claude-directives/SKILL.md` and its supporting files as a static RED evidence inventory. **Phase 2 is a preventive restructure, not a corrective one.** The deficiencies (stale `Opus 4.5` section, undifferentiated `Claude 4.x` anchors, stale `Opus 4.5` / `Sonnet 4.5` refs in `long-running-state-patterns.md`) were identified by reading the files in Phase 2B investigation, not by observing a session fail. A 2026-04-22 independent-session search returned 0 qualifying transcripts across 30+ FTS5-safe queries in 6 projects — confirming the deficiencies have not measurably misled sessions in the chat index. The restructure is preemptive hygiene; the code-smell inventory is the RED evidence. Task 5's synthetic obra pressure scenarios remain the GREEN regression check.

**History:** The original Task 1 required an independent-session transcript (cc-search-chats match or user-commissioned fresh-session run) as RED. That framing was reversed during the 2026-04-22 plan-amendment pass after the independent-session search confirmed no such transcripts exist for Phase 2's deficiencies. The amendment follows the H3 revision precedent that dropped Phase 4's earlier "production IS integration evidence" claim as unfalsifiable and replaced it with the Phase 5 Task 4.5 frustration-signal audit as the downstream effectiveness check. Phase 3 retains the independent-session gate because Phase 3's restructure is corrective (its target methodology is explicitly about sourcing from real prior transcripts); Phase 4 also moves to static-evidence RED under the same precedent.

**Step 1: Enumerate the code-smell inventory**

Read the current `writing-claude-directives/SKILL.md` and its supporting files. Record every location where the Phase 2 deficiencies appear:

- `SKILL.md` lines 215-220: `### Opus 4.5: "Think" Sensitivity` subsection — stale model-version anchor; Opus 4.7 is current (2026-04).
- `SKILL.md` lines approx 69, 96, 99, 237: `Claude 4.x` generic anchors — must become per-model (`Opus 4.7 / Sonnet 4.6 / Haiku 4.5`).
- `long-running-state-patterns.md` lines 15, 114, 119, 132, 133: `Opus 4.5` / `Sonnet 4.5` / `Claude 4.5+` anchors — both `Opus 4.5` and `Sonnet 4.5` are superseded; `Haiku 4.5` stays (current 2026-04 shipping model).
- `graphviz-conventions.dot`: byte-identical to obra, attribution comment absent.

**Step 2: Record the independent-session search result**

The 2026-04-22 independent-session search (orchestrator plus dispatched subagent) covered:

- FTS5-safe single-term queries including `directive`, `Opus`, `Sonnet`, `Haiku`, `judgement`, `aggressive`, `overtriggering`, `CRITICAL`, `rationalize`, `rationalise`, `bypass`, `loophole`, `YOU`, `MUST`, `Sensitivity`, `think`, `mate`, `fuck` (the last two as frustration-signal proxies per `feedback_haiku-no-judgement.md` + project-wide memory).
- 6+ projects with meaningful chat indices: `brian-ed3d-plugins`, `PromptGrimoireTool`, `marketplaces/denubis-plugins`, `pretix`, `INTS1301`, `LLM-History-Paper`.
- 0 qualifying transcripts — no session was observed failing at directive-authoring in a way traceable to the deficiencies listed in Step 1.

Interpretation: Phase 2 restructures a skill whose deficiencies have not measurably misled authors in-the-wild. The restructure is preemptive hygiene. Record this explicitly so a future reader is not surprised that `phase_02_red_evidence.md` contains static evidence rather than a transcript quote.

**Step 3: Document RED evidence in `phase_02_red_evidence.md`**

File structure:
```markdown
# Phase 2 RED Evidence — Static Code-Smell Inventory

**Source:** Phase 2B investigator file-read findings (2026-04-17) + 2026-04-22 independent-session search confirming no in-chat RED candidates exist.
**Restructure framing:** PREVENTIVE (not corrective). No prior session has been observed failing at the listed deficiencies.
**Pre-restructure SKILL.md SHA:** [git rev-parse HEAD:plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md]
**Pre-restructure long-running-state-patterns.md SHA:** [git rev-parse HEAD:plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md]

## Code-smell inventory

[file + line + deficiency triple per location listed in Task 1 Step 1]

## Independent-session search (2026-04-22)

**Queries run (FTS5-safe single-term):** [list actual queries]
**Projects searched:** [list with chat-index path for each]
**Qualifying transcripts:** 0
**Interpretation:** deficiencies are preemptive hygiene; restructure is preventive.

## How Phase 2 addresses the deficiencies

- Task 2 drops the stale `Opus 4.5: "Think" Sensitivity` subsection and updates per-model anchors in SKILL.md.
- Task 3 creates `model-tier-notes.md` as the per-model companion file (refresh-cycles decouple).
- Task 3.5 updates `long-running-state-patterns.md` anchors (Opus 4.5 / Sonnet 4.5 → Opus 4.7 / Sonnet 4.6; Haiku 4.5 preserved).
- Task 4 adds obra attribution to `graphviz-conventions.dot` (content byte-identical).
```

**Step 4: Commit RED evidence**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_red_evidence.md
git commit -m "docs(phase-02): RED evidence — static code-smell inventory (preventive restructure)

Phase 2 is a preventive restructure, not a corrective one. Deficiencies
were identified by file-read in Phase 2B investigation (2026-04-17);
2026-04-22 independent-session search returned 0 qualifying transcripts
across 30+ FTS5-safe queries in 6 projects. The code-smell inventory is
the RED evidence; Task 5's synthetic obra pressure scenarios remain the
GREEN regression check.

Amended from the original independent-session-gate framing per the
2026-04-22 plan-amendment pass."
```

**Consumer-tracing:** This file is consumed by (a) Phase 2's Task 5 GREEN verification, which tests the restructured SKILL.md against synthetic obra pressure scenarios, and (b) Phase 5's cross-reference audit, which verifies every phase has a RED evidence file.

**Gate statement (amended 2026-04-22):** Phase 2 does not proceed to Task 2 without a committed `phase_02_red_evidence.md` containing the Step 1 code-smell inventory and the Step 2 independent-session search record. The gate is still structurally verifiable: a reviewer can re-run the 2026-04-22 search (FTS5-safe queries against the same projects) and reproduce the 0-qualifying-transcripts result, and can diff-audit the listed line numbers against the pre-restructure SHAs.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Restructure `writing-claude-directives/SKILL.md` — drop stale section, add new sections, update scattered anchors

**Verifies:** skill-skills-upstream-sync.AC3.1, skill-skills-upstream-sync.AC3.4, skill-skills-upstream-sync.AC3.6, skill-skills-upstream-sync.AC3.7

**Files:**
- Modify: `plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md`

**Step 1: Delete stale Opus 4.5 section**

Remove the existing `### Opus 4.5: "Think" Sensitivity` subsection at lines 215-220 of the current file. The entire subsection (heading + body) goes. Replace with nothing — not a pointer, not a footnote. The subsequent "Model-Specific Notes" H2 heading will likely need review: if its only content was the Opus 4.5 subsection, replace that H2 with a pointer to `model-tier-notes.md` (see Step 3); if it contained other content, preserve that content and add the pointer as a lead paragraph.

**Step 2: Update scattered model-version anchors**

At lines approximately 69, 96, 99, 237 (re-verify with Read before editing), the current text uses generic "Claude 4.x" anchors. For each:

- **Line 69:** "Claude 4.x models are highly responsive to instructions." → Replace with model-tiered wording that points at `model-tier-notes.md` for specifics. Suggested: *"Current Claude models (Opus 4.7, Sonnet 4.6, Haiku 4.5) are highly responsive to instructions, with per-model specifics in `model-tier-notes.md`."*
- **Line 96:** "For Claude 4.x, aggressive language ('YOU MUST', 'CRITICAL') can cause overtriggering." → Update per design DR3: strengthen the claim with the current Anthropic source. Suggested: *"For current Claude models (Opus 4.7, Sonnet 4.6, Haiku 4.5), Anthropic's prompting best practices explicitly recommend dialling back aggressive language: rather than 'CRITICAL: You MUST use this tool when X', prefer 'Use this tool when X'. Aggressive language can cause overtriggering with these more responsive models. Source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices (verified 2026-04-17)."* The exact wording is the implementor's call; the substantive requirements: (a) anchors are per-model, not "4.x"; (b) the URL is present and dated; (c) the concrete before/after example is present.
- **Line 99:** "Often sufficient for 4.x" (in-example comment). Update the comment so it no longer assumes an undifferentiated "4.x".
- **Line 237:** "Aggressive language for 4.x" (Common Mistakes table cell). Update to "Aggressive language for current models" with the same URL reference or a back-pointer to the main aggressive-language section.

**Step 3: Add pointer to `model-tier-notes.md`**

Replace the old "Model-Specific Notes" H2 (or insert a new H2 if that heading is gone after Step 1) with a short section titled `## Model-Specific Notes`. Contents: one paragraph stating that per-model specifics (effort levels, steerability notes, instruction-following characteristics, extended-thinking behaviour) live in `model-tier-notes.md` as a supporting file so they can be refreshed without touching this orchestrator. Link the file by relative path.

**Step 4: Add `## Rubric Callback` section**

Insert between "Compliance Techniques" and "Structure Patterns" (design DR8). Contents (~5-10 lines):

> Before writing a new directive, check whether the underlying agent-task-or-skill passes the `denubis-extending-claude:epistemic-humility` rubric. The rubric screens Scope (Jones's three conditions), Observability (form-gate + tautology-screen + named-falsifier), Process (Schön's four questions), and Failure-pattern (four named patterns from AbsenceJudgement). If the artefact under review fails any screen, the right next step is usually to revise the scope, not to write stronger directives — directive-writing is a protective belt around a scope decision, not a substitute for it.

Include explicit cross-reference using the `plugin:skill` format: `denubis-extending-claude:epistemic-humility`.

**Step 5: Verify structural constraints**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md') as f:
    content = f.read()
# AC3.1: No Opus 4.5 section
assert 'Opus 4.5' not in content, 'Opus 4.5 still referenced'
assert 'Think Sensitivity' not in content and \"Think' Sensitivity\" not in content, 'Think Sensitivity section still present'
# AC3.3: NO persuasion-principles.md file in the skill directory.
# This is the primary enforcement. AC3.4 follows structurally — if the
# source file does not exist, authoring a section that cites it would
# be nonsensical and is not defended against here.
import os
persuasion_path = 'plugins/denubis-extending-claude/skills/writing-claude-directives/persuasion-principles.md'
assert not os.path.exists(persuasion_path), \
    f'{persuasion_path} exists — AC3.3 violation; persuasion content must not be imported'
# AC3.6: Rubric callback
assert 'epistemic-humility' in content, 'rubric callback missing'
assert 'denubis-extending-claude:epistemic-humility' in content, 'rubric callback uses wrong cross-ref format'
# AC3.3 partial: Model-tier notes pointer (AC3.3 is now 'persuasion NOT imported'; the model-tier pointer check is structural only)
assert 'model-tier-notes.md' in content, 'model-tier-notes.md pointer missing'
print('SKILL.md structural checks passed')
"
```
Expected: `SKILL.md structural checks passed`. Any assertion failure = halt and fix.

**Step 6: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-claude-directives/SKILL.md
git commit -m "refactor(writing-claude-directives): restructure for 2026-04 model tier, drop Opus 4.5, add rubric callback

- Delete stale 'Opus 4.5: Think Sensitivity' subsection (superseded)
- Replace generic 'Claude 4.x' anchors with per-model references
- Update aggressive-language guidance with current Anthropic prompting
  best practices citation (dial back CRITICAL/YOU MUST)
- Add '## Model-Specific Notes' as pointer to model-tier-notes.md
- Add '## Rubric Callback' cross-referencing denubis-extending-claude:epistemic-humility
- Do NOT add a Cialdini/Meincke/persuasion-principles section
  (denubis explicitly departs from obra on this point per the design
  plan's 'Persuasion principles do not belong in denubis skills'
  Additional Consideration)

Part of skill-skills upstream sync (Phase 2).
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-4) -->

<!-- START_TASK_3 -->
### Task 3: Create `model-tier-notes.md` with per-model sections (Opus 4.7 / Sonnet 4.6 / Haiku 4.5)

**Verifies:** skill-skills-upstream-sync.AC3.2, skill-skills-upstream-sync.AC3.7

**Files:**
- Create: `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md`

**Step 1: Author the file**

Structure (design DR4: per-model organisation, NOT per-feature):

1. **Frontmatter + dated header** (DR6):
   ```yaml
   ---
   name: model-tier-notes
   description: Per-model behavioural specifics for Opus 4.7, Sonnet 4.6, Haiku 4.5 — referenced from writing-claude-directives SKILL.md
   last-verified: 2026-04-17
   ---
   ```
   Plus a `_Last verified: 2026-04-17_` line immediately below frontmatter (visible in rendered markdown).

2. **Opening paragraph** (2-3 sentences): purpose of this file, staleness warning, pointer back to SKILL.md.

3. **`## Opus 4.7`** — Contents (DR5 requires foregrounding effort levels):
   - Literal instruction-following: *"Opus 4.7 interprets prompts more literally than Opus 4.6, particularly at lower effort levels. It will not silently generalize an instruction from one item to another."* (cite `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`)
   - **Effort levels** as a first-class subsection: supports `low`, `medium`, `high`, `xhigh` (new in 4.7), `max`. Anthropic guidance: "Start with the new `xhigh` effort level for coding and agentic use cases." At `low`/`medium`, the model scopes tightly; at `xhigh`/`max`, it reasons more and uses tools less. Cite same URL.
   - Tool-use: Opus 4.7 uses tools less than 4.6 and reasons more; increasing effort setting increases tool-use. Cite same URL.
   - Agentic focus: designed for long-horizon agentic work; better at refusing malicious agentic requests and resisting prompt injection in Claude Code / computer-use settings. Cite `https://www.anthropic.com/news/claude-opus-4-7`.
   - Model ID for API use: `claude-opus-4-7`.

4. **`## Sonnet 4.6`** — Contents:
   - Steerability: more steerable than Opus 4.6; corrective instructions more effective. Cite `https://www.anthropic.com/news/claude-sonnet-4-6`.
   - Proactive default: may show overly agentic behavior in GUI settings (unsanctioned actions); "aggressive behavior is much more steerable by prompting than Opus 4.6's equivalent". Same URL.
   - Tool-use: parallel tool calling at ~100% with prompting guidance. Same URL.
   - Adaptive thinking: supports extended thinking and adaptive thinking (recommended). Cite `https://platform.claude.com/docs/en/about-claude/models/overview`.
   - Aggressive-language guidance: dial back "CRITICAL / YOU MUST" phrasing (see SKILL.md aggressive-language section for the primary discussion). Cite `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices`.
   - Model ID for API use: `claude-sonnet-4-6`.

5. **`## Haiku 4.5`** — Contents (amended 2026-04-22: operator-empirical position on judgement retained and strengthened, not retired):
   - Instruction-following for mechanical tasks: *"Claude Haiku 4.5 follows detailed mechanical instructions well — data extraction, structured output generation, tool-call loops, summarisation."* Anthropic's 2026-04 announcement describes it as *"more consistent instruction following for nuanced tasks"* — cite `https://www.anthropic.com/news/claude-haiku-4-5` for the Anthropic framing, but see the operator-empirical note below for the scope under which that framing applies.
   - Context and extended thinking: 200k total context, up to 128k extended-thinking budget, up to 64k output tokens. Cite `https://platform.claude.com/docs/en/build-with-claude/extended-thinking`.
   - Safety profile: statistically lower rate of misaligned behaviours than Sonnet 4.5 or Opus 4.1 per Anthropic announcement. Cite `https://www.anthropic.com/news/claude-haiku-4-5`.
   - **Operator-empirical note on judgement:** *"Haiku 4.5 is unsuitable for any task requiring judgement. This is the project's empirical position based on operator experience (2026-04-22), overriding Anthropic's 2026-04 marketing framing of 'more consistent instruction following for nuanced tasks' — that framing describes mechanical instruction-following, not evaluative or reflective judgement. Route judgement-heavy work (code review, proleptic challenge, coherence review, rubric application, scope decisions) to Sonnet 4.6 or Opus 4.7. Haiku 4.5 is appropriate for mechanical, bounded, low-judgement tasks only — which aligns with AbsenceJudgement.tex:868's three success conditions for AI-assisted work."* This note retains and strengthens the structural principle encoded in `testing-skills-with-subagents` — see Phase 3 of the upstream-sync plan, which keeps the Haiku-judgement guidance with the same operator-empirical framing.
   - Model ID for API use: `claude-haiku-4-5-20251001`.

6. **`## Cross-model patterns`** — one short subsection calling out what's common:
   - All three support extended thinking / adaptive thinking.
   - All three are more responsive to prompting than pre-4.x generations; aggressive-language patterns that helped older models can overtrigger current models.
   - Cite the prompting best practices URL as the common source.

7. **Closing footer** with staleness protocol: *"This file is dated 2026-04-17. When Anthropic releases new models or updated prompting guidance, re-verify each citation URL and update the dated header. The design plan's Additional Considerations note 'Model-note staleness' is the authority for this maintenance pattern."*

**Step 2: Cross-verify against Anthropic system card PDF (supplementary)**

Per design plan Additional Considerations, consume `/tmp/anthropic-system-card.pdf` as a supplementary cross-verification source (not primary). Run:

```bash
# Extract system-card content targeting the three models (selective pages)
pdftotext -f 1 -l 20 /tmp/anthropic-system-card.pdf /tmp/system-card-p1-20.txt 2>/dev/null || echo "pdftotext not installed — use Read tool on the PDF instead with pages parameter"
```

If `pdftotext` available, grep the extracted text for Opus 4.7 / Sonnet 4.6 / Haiku 4.5 context. If `pdftotext` not available, use `Read` tool with `pages` parameter on the PDF. Goal: cross-verify no claim in `model-tier-notes.md` is contradicted by the system card. Any contradiction → halt and resolve.

**Step 3: Verify the file**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md') as f:
    content = f.read()
# Dated header (DR6)
assert 'Last verified' in content or 'last-verified' in content.lower(), 'dated header missing'
assert '2026-04-17' in content, 'verification date missing'
# Per-model H2s (DR4 + AC3.2)
for h in ['## Opus 4.7', '## Sonnet 4.6', '## Haiku 4.5']:
    assert h in content, f'missing model section: {h}'
# URL citations per AC3.2 (at least one per model)
# Check for the three canonical anthropic.com announcement URLs:
urls = [
    'anthropic.com/news/claude-opus-4-7',
    'anthropic.com/news/claude-sonnet-4-6',
    'anthropic.com/news/claude-haiku-4-5',
]
for u in urls:
    assert u in content, f'missing primary-source URL: {u}'
# xhigh effort-level mention (DR5)
assert 'xhigh' in content, 'xhigh effort level not mentioned (DR5 violation)'
# Haiku-no-judgement operator-empirical guidance (amended 2026-04-22) —
# reversed from the earlier retirement framing. The project's empirical
# position is that Haiku 4.5 is unsuitable for judgement tasks regardless
# of Anthropic's 2026-04 marketing description of "more consistent
# instruction following for nuanced tasks". The check verifies the
# operator-empirical guidance is present, so a future reader auditing the
# framing can spot it without needing to trace this plan amendment.
has_haiku_no_judgement_guidance = (
    'Haiku 4.5' in content
    and ('judgement' in content.lower() or 'judgment' in content.lower())
    and ('operator' in content.lower() or 'empirical' in content.lower())
    and ('unsuitable' in content.lower() or 'never' in content.lower())
    # Reasoned-guidance tightening (V4 fix, 2026-04-23, from Codex triage of
    # the Task 5 rubric walkthrough). A file containing only the keyword
    # clauses above could satisfy the check with an incoherent paragraph;
    # the next two clauses require specific reasoned constructs that
    # distinguish genuine guidance from keyword-stringing. Both phrases
    # appear verbatim in the 2026-04-22 amendment's operator-empirical
    # passage. If a future author reframes the guidance, the assertions
    # should be updated alongside the prose — making the re-framing a
    # conscious edit rather than a silent drift.
    and 'Route judgement-heavy work' in content
    and 'mechanical instruction-following' in content.lower()
)
assert has_haiku_no_judgement_guidance, \
    'operator-empirical Haiku-no-judgement guidance missing — need a passage citing Haiku 4.5 together with a judgement term (judgement/judgment), an operator/empirical anchor, a strong negation (unsuitable/never), a concrete routing instruction (the exact phrase "Route judgement-heavy work"), and a contrast anchor (the phrase "mechanical instruction-following"). Operator-empirical framing is required per the 2026-04-22 plan-amendment pass; do not satisfy the check by repeating only Anthropic marketing language.'
# Model IDs
for model_id in ['claude-opus-4-7', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001']:
    assert model_id in content, f'missing model ID: {model_id}'
print('model-tier-notes.md structural checks passed')
"
```
Expected: `model-tier-notes.md structural checks passed`.

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md
git commit -m "feat(writing-claude-directives): add model-tier-notes.md for Opus 4.7 / Sonnet 4.6 / Haiku 4.5

Per-model behavioural specifics with citation URLs to current (2026-04)
Anthropic documentation. Foregrounds new xhigh effort level for Opus 4.7.
Retains the operator-empirical Haiku-no-judgement guidance (strengthened
per the 2026-04-22 plan-amendment pass) against Anthropic's 2026-04
marketing framing of 'more consistent instruction following for nuanced
tasks' — that framing describes mechanical instruction-following, not
evaluative judgement; operator position is that Haiku 4.5 is unsuitable
for any task requiring judgement.

Dated header enables staleness auditing. System card PDF consumed as
supplementary cross-verification per design plan Additional Considerations.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR4, DR5)"
```

**Consumer-tracing:** SKILL.md's `## Model-Specific Notes` section points at this file. Phase 5's cross-reference audit verifies the pointer resolves. Staleness is observable via the dated header.
<!-- END_TASK_3 -->

<!-- START_TASK_3_5 -->
### Task 3.5: Update stale model anchors in `long-running-state-patterns.md` (H6 scope expansion)

**Verifies:** skill-skills-upstream-sync.AC3.7 (every model-specific claim has an explicit model-version anchor — extended to supporting files per H6 revision)

**Files:**
- Modify: `plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md`

**Why this task exists:** The pre-revision plan declared this file "unchanged unless research surfaces updates — it did not." Critical peer review H6 (2026-04-17) falsified that: the file contains `Opus 4.5` (lines 114, 132) and `Sonnet 4.5` (line 133) references, both superseded by current 2026-04 Anthropic models. User direction (2026-04-18): "remove Opus 4.5 references, Sonnet 4.5 references". Haiku 4.5 is the CURRENT shipping Haiku and stays.

**Step 1: Apply targeted replacements**

Read the file. Apply these exact replacements (line numbers are from the pre-edit file and will drift):
- Line 15: `"Claude 4.5+ receives updates on remaining context after tool calls"` → `"Claude 4.x (Opus 4.7 / Sonnet 4.6 / Haiku 4.5) receives updates on remaining context after tool calls"`
- Line 114 (inside diagram block): `"Orchestrator (Opus 4.5)"` → `"Orchestrator (Opus 4.7)"`
- Line 119 (inside diagram block): `"Subagents (Sonnet/Haiku 4.5)"` → `"Subagents (Sonnet 4.6 / Haiku 4.5)"`
- Line 132 (in Model Selection table): `"| Opus 4.5 | Orchestration, complex planning | $15/M output |"` → `"| Opus 4.7 | Orchestration, complex planning | $15/M output |"`
- Line 133: `"| Sonnet 4.5 | Focused implementation | $15/M output |"` → `"| Sonnet 4.6 | Focused implementation | $15/M output |"`
- Lines 134, 136: `Haiku 4.5` stays (current model; no edit).

**Step 2: Add dated header and source URL anchor**

At the top of the file (after the H1 `# Long-Running State Patterns`), insert:

```markdown
_Last verified: 2026-04-17. Model anchors: Opus 4.7 / Sonnet 4.6 / Haiku 4.5. Source: https://platform.claude.com/docs/en/about-claude/models/overview_
```

This mirrors the dated-header pattern from `model-tier-notes.md` (Task 3 Step 1) and makes staleness observable per the design plan's Additional Consideration on model-note staleness.

**Step 3: Verification (inline Python)**

```python
content = open('plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md').read()

# Stale anchors must be absent
assert 'Opus 4.5' not in content, 'Opus 4.5 still present — H6 regression'
assert 'Sonnet 4.5' not in content, 'Sonnet 4.5 still present — H6 regression'
assert 'Claude 4.5+' not in content, 'Claude 4.5+ still present — H6 regression'

# Current anchors must be present
assert 'Opus 4.7' in content, 'Opus 4.7 not added'
assert 'Sonnet 4.6' in content, 'Sonnet 4.6 not added'
assert 'Haiku 4.5' in content, 'Haiku 4.5 removed (should stay — current model)'

# Dated header + URL present
assert 'Last verified' in content, 'dated header missing'
assert 'platform.claude.com/docs/en/about-claude/models/overview' in content, 'source URL missing'

print('long-running-state-patterns.md model anchors updated per H6')
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-claude-directives/long-running-state-patterns.md
git commit -m "refactor(writing-claude-directives): update stale model anchors in long-running-state-patterns.md

- Opus 4.5 → Opus 4.7 (lines 114, 132)
- Sonnet 4.5 → Sonnet 4.6 (line 133)
- Sonnet/Haiku 4.5 → Sonnet 4.6 / Haiku 4.5 (line 119)
- Claude 4.5+ → Claude 4.x (Opus 4.7 / Sonnet 4.6 / Haiku 4.5) (line 15)
- Haiku 4.5 preserved (current 2026-04 shipping model)
- Added dated header + source URL per design plan's model-note-staleness principle

Addresses H6 from critical-peer-review 2026-04-17. Extends AC3.7
(model-version anchors) to include this supporting file rather than
narrowing AC3.7 to SKILL.md only.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```

**Consumer-tracing:** This file is referenced from `writing-claude-directives/SKILL.md`'s supporting-file pointers. Phase 5's cross-reference audit verifies the pointer resolves. AC3.7 coverage now includes this file (see test-requirements.md).
<!-- END_TASK_3_5 -->

<!-- START_TASK_4 -->
### Task 4: Reconcile `graphviz-conventions.dot` against obra (no-op with attribution)

**Verifies:** skill-skills-upstream-sync.AC3.5

**Files:**
- Modify: `plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot` (attribution comment only — content unchanged)

**Step 1: Reconfirm byte-identicality**

Run:
```bash
diff -q /tmp/superpowers-obra/skills/writing-skills/graphviz-conventions.dot /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot
```
Expected: no output (files are byte-identical, already verified 2026-04-17 in Phase 2C).

If the files have diverged since Phase 2C (unlikely but possible if someone edited either copy), resolve manually:
- If only whitespace diverged, normalise on obra's version.
- If semantic divergence exists, surface to user and halt — design plan assumed a no-op reconciliation.

**Step 2: Add attribution comment block at the top of the file**

Prepend a Graphviz-comment block (uses `//` or `/* */` — check file style and match) immediately after the opening `digraph { ... }` or `strict ...` declaration. Example:

```dot
// Source: obra/superpowers/skills/writing-skills/graphviz-conventions.dot
// Verified byte-identical 2026-04-17 during skill-skills upstream sync (Phase 2).
// Upstream repo: https://github.com/obra/superpowers
```

Place this comment where it won't affect rendering. If the file is a `.dot` with graph blocks, the comment goes inside the block or at the top before any declarations — follow the existing comment style already in the file (the file is well-commented per Phase 2B investigator findings).

**Step 3: Verify**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && grep -c 'obra/superpowers' plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot
```
Expected: at least `1` (attribution line present).

Also verify the file still parses as valid Graphviz:
```bash
which dot && dot -Tcanon plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot > /dev/null && echo "valid dot" || echo "dot not installed or file invalid"
```
Expected: `valid dot` if `dot` installed; otherwise `dot not installed or file invalid` (non-blocking — the attribution change is text-only).

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-claude-directives/graphviz-conventions.dot
git commit -m "chore(writing-claude-directives): add obra attribution to graphviz-conventions.dot

File is byte-identical to obra/superpowers/skills/writing-skills/graphviz-conventions.dot
(verified 2026-04-17). Reconciliation is a no-op; attribution comment
makes provenance visible for future diffs against upstream.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR7)"
```

**Consumer-tracing:** The `.dot` file is referenced from SKILL.md's `## Graphviz (for Process Flows)` section (current line 264). No change to that cross-reference.
<!-- END_TASK_4 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_TASK_5 -->
### Task 5: Phase-level verification and GREEN verification with obra pressure scenarios

**Verifies:** skill-skills-upstream-sync.AC3.* (all AC3 criteria pass)

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_green_verification.md`

**Step 1: GREEN verification with obra's pressure scenarios**

Obra's `testing-skills-with-subagents.md` (12.3K file inside obra's writing-skills/) contains multi-factor pressure scenarios. Run at least one of those scenarios against the restructured SKILL.md via a task-scoped subagent invocation (recommended: `denubis-basic-agents:sonnet-general-purpose` — Phase 3 methodology says run RED at production tier).

For Phase 2, a relevant pressure scenario: *"You're writing a skill directive under time pressure. The user asks for 'aggressive instructions that Claude will definitely follow.' Apply the restructured writing-claude-directives skill."* The restructured skill must:
1. Route the writer to `model-tier-notes.md` for current model behaviour
2. Show the aggressive-language dial-back guidance
3. Point at the rubric-callback section before the writer commits to phrasing
4. If Haiku 4.5 is the target model, NOT reproduce the "struggles with judgement" claim

Capture the subagent's output and note each of the four checks as pass/fail.

**Step 2: REFACTOR — close any loopholes surfaced**

If Step 1 reveals that the restructured SKILL.md fails any of the four checks, make targeted edits and re-run. Iterate until all four pass. Document the iterations in the GREEN verification file.

**Step 3: Rubric self-application walk-through (H4 revision: not a pass/fail gate)**

Apply `denubis-extending-claude:epistemic-humility` to the restructured Phase 2 artefact as a whole. This is a walk-through, not a pass/fail check. The deliverable is:
- An honest application of each section, noting where the answer strains against the artefact's state
- **Any reflective vulnerability surfaced — raise to user BEFORE committing GREEN.** A vulnerability is any question where (a) the honest answer strains against current state, (b) the walk-through has to rationalise a near-miss, or (c) the author would not defend the answer to a reviewer. Zero vulnerabilities surfaced is itself a flag — re-run with sharper honesty.
- User acknowledges vulnerability or directs remediation. Document the acknowledgement in the GREEN verification file.

Sections to walk through:
- Scope: does this phase's scope pass Jones's three conditions? (90%+ the phase can be completed without intervention; failures are bounded, auditable, reversible; human decides rollback)
- Observability: do the phase's Done-when entries pass the three Observability screens (form-gate, tautology-screen, named-falsifier)?
- Process: do Schön's four questions answer affirmatively for this phase?
- Failure-pattern: is the phase clear of temporality blindness, scope/confabulation, stamp-collecting without evaluation, vibes-based operation?

Document the walk-through + surfaced vulnerabilities + user acknowledgement in the GREEN verification file.

**Step 4: Write `phase_02_green_verification.md`**

File structure:
```markdown
# Phase 2 GREEN Verification

## Pressure scenario

**Scenario applied:** [description]
**Subagent used:** [agent name]

### Results

1. Routed to model-tier-notes.md: [PASS/FAIL, evidence]
2. Aggressive-language dial-back shown: [PASS/FAIL, evidence]
3. Rubric-callback surfaced: [PASS/FAIL, evidence]
4. Haiku judgement claim absent: [PASS/FAIL, evidence]

### REFACTOR iterations

[List any loopholes closed and the targeted edits]

## Rubric self-application walk-through (epistemic-humility)

### Scope
[Jones's three conditions applied to this phase — note any vulnerabilities]

### Observability
[Three screens applied to Done-when entries — note any vulnerabilities]

### Process
[Schön's four questions — note any vulnerabilities]

### Failure-pattern screen
[Four patterns checked — note any vulnerabilities]

### Vulnerabilities surfaced and user acknowledgement
[List each vulnerability surfaced during the walk-through (or "none surfaced — walk-through re-run with sharper honesty"); user acknowledgement recorded per each]
```

**Step 5: Commit GREEN verification**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_green_verification.md
git commit -m "docs(phase-02): GREEN verification + rubric self-application walk-through

Phase 2 passes obra pressure scenario (four-check routing). Rubric
self-application walk-through committed; [N] vulnerabilities surfaced
and acknowledged by user (or: zero surfaced + walk-through re-run with
sharper honesty — specify). REFACTOR closed [N] loopholes: [brief list].

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```

**Consumer-tracing:** This file is consumed by (a) Phase 5's cross-reference audit, which checks every phase has a GREEN verification, and (b) the Finalization code-reviewer.
<!-- END_TASK_5 -->

---

## Done when (phase-level)

- [ ] `phase_02_red_evidence.md` exists on disk with the Phase 2B code-smell inventory + the 2026-04-22 independent-session search record (0 qualifying transcripts across 30+ FTS5-safe queries in 6 projects) — static-evidence RED per the 2026-04-22 plan-amendment pass (Phase 2 is preventive, not corrective; original independent-session-failure framing reversed)
- [ ] `writing-claude-directives/SKILL.md` restructured: no Opus 4.5 section, per-model anchors, NO Cialdini/Meincke/persuasion section, rubric callback resolving to `denubis-extending-claude:epistemic-humility` (Task 2)
- [ ] `model-tier-notes.md` exists with three per-model H2s, dated header, xhigh effort-level mention, operator-empirical Haiku-no-judgement guidance documented (amended 2026-04-22: retained and strengthened, not retired), model IDs present, URL citations per section (Task 3)
- [ ] `long-running-state-patterns.md` model anchors updated: Opus 4.5 / Sonnet 4.5 / Claude 4.5+ removed; Opus 4.7 / Sonnet 4.6 present; Haiku 4.5 preserved (current); dated header + source URL added (Task 3.5 — H6 scope expansion)
- [ ] `graphviz-conventions.dot` gains obra attribution comment; content otherwise unchanged (Task 4)
- [ ] GREEN verification passes pressure scenario; rubric self-application walk-through committed with any surfaced vulnerabilities acknowledged by user before GREEN (Task 5)
- [ ] Commits land per user's commit preference (5 commits minimum for Tasks 1-4 + Task 3.5; Task 5 adds 1 more for GREEN doc)
- [ ] Phase 2 UAT entries appended to `uat-requirements.md` using the new gate-form template (`**What's automatable:**` / `**What's NOT automatable:**` lines before the falsification block) — models the behaviour Phase 6 codifies

**Not in scope for Phase 2:**
- Phase 5's version bumps / CHANGELOG entries (cross-plugin scope per AC5.7 handled in Phase 5/6)
- Phase 3's testing-skills-with-subagents restructure (SKILL.md-level Haiku-judgement wording lives there; Phase 3 reframes with the same operator-empirical guidance per the 2026-04-22 plan-amendment pass)
- Phase 6's impl-plan-write template change (covered separately per design plan Phase 6)
