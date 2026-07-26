# Skill-Skills Upstream Sync — Phase 4: Rewrite `writing-skills` as Cornerstone Orchestrator

**Goal:** Replace the existing 163-line `writing-skills/SKILL.md` with a thin cornerstone orchestrator (≤250 lines) that sequences the three sub-skills — `epistemic-humility` (scope check), `writing-claude-directives` (phrasing/compliance), `testing-skills-with-subagents` (RED/GREEN/REFACTOR) — and adopts obra's supporting-file shape via verbatim imports of `anthropic-best-practices.md`, `render-graphs.js`, and `examples/CLAUDE_MD_TESTING.md` with attribution and denubis prefaces. The cornerstone is produced by invoking the three sub-skills in practice (independent-session RED evidence sourced via H2 discipline; rubric self-application; sub-skill sequencing exercised through Tasks 2-6). Whether the sequencing cohered in practice is audited retrospectively at Phase 5 Task 4.5 (the frustration-signal audit, AC5.8), not by a written integration-evidence narrative — the earlier "production IS integration evidence" claim was dropped as unfalsifiable during H3 revision.

**Architecture:** Restructure-in-place for SKILL.md (current file has the TDD-for-skills spine; reshape rather than reinvent) + verbatim obra imports for three new supporting files. The SKILL.md becomes a sequencer pointing at sub-skills for depth; all heavy content (CSO, bulletproofing, rationalization tables) lives in the sub-skills (`writing-claude-directives` for CSO, `testing-skills-with-subagents` for bulletproofing) per the programme's progressive-disclosure-at-two-levels design (design DR5).

**Tech Stack:** Markdown with YAML frontmatter. `render-graphs.js` requires Node.js + `dot` binary (graphviz) — skill-author tooling only, not runtime. Source material: `/tmp/superpowers-obra/skills/writing-skills/*` (obra verbatim imports); cc-search-chats:search-chat MCP tool for RED evidence.

**Scope:** 4 of 6 phases from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md`.

**Codebase verified:** 2026-04-17 (Phase 4B investigator findings via direct inspection documented in task #19).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### skill-skills-upstream-sync.AC1: `writing-skills` cornerstone rewrite
- **skill-skills-upstream-sync.AC1.1 Success:** `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md` exists with valid YAML frontmatter (`name`, `description` fields present)
- **skill-skills-upstream-sync.AC1.2 Success:** SKILL.md line count is ≤ 250 (thin-orchestrator target; small margin over the 200-line target in DR5)
- **skill-skills-upstream-sync.AC1.3 Success:** SKILL.md cross-references `testing-skills-with-subagents`, `writing-claude-directives`, and `epistemic-humility`; each reference resolves to an existing skill directory
- **skill-skills-upstream-sync.AC1.4 Success:** Supporting files exist: `anthropic-best-practices.md`, `render-graphs.js`, `examples/CLAUDE_MD_TESTING.md`
- **skill-skills-upstream-sync.AC1.5 Success:** Obra-imported files preserve attribution (Source line in frontmatter or top of file citing obra/superpowers origin)
- **skill-skills-upstream-sync.AC1.6 Failure:** Commit rejected if any obra-imported file lacks attribution or any cross-reference points at a non-existent skill or file
- **skill-skills-upstream-sync.AC1.7 Edge:** `test-requirements.md` for Phase 4 documents the RED evidence — an independent-session failure transcript (cc-search-chats transcript OR user-run fresh-session transcript) plus deficiency-location analysis identifying where in the current `writing-skills/SKILL.md` the failure manifests

---

## Dependencies and Sources

**Phase dependencies:**
- **Phase 1 complete.** `epistemic-humility/` exists for the rubric-callback cross-reference.
- **Phase 2 complete.** `writing-claude-directives/` restructured for sequence reference.
- **Phase 3 complete.** `testing-skills-with-subagents/` restructured with conversation-precedent protocol for the RED/GREEN/REFACTOR delegation.
- Phase 2.5 (preparatory-refactor) is a Phase 3 dependency, not a Phase 4 dependency directly.

**RED evidence independent-session gate (design DR3, Additional Considerations):** Before Task 2 proceeds, Task 1 must produce a RED evidence file containing an observed failure of the current `writing-skills/SKILL.md` from a session that is NOT this executor. Two ordered sources:

1. **cc-search-chats:search-chat** queried for prior skill-authoring sessions where invention went off the rails, scope crept, or rationalizations evaded the skill being authored (many candidates likely exist — this is well-travelled ground). If a qualifying transcript is found, RED evidence = reference to it PLUS identification of the deficient region of the current `SKILL.md`; OR
2. **Commissioned fresh-session run** — executor and user jointly design a scenario likely to exercise the failure mode (e.g., "write a new skill from scratch using the current writing-skills SKILL.md without the cornerstone orchestrator's sequencing"). Executor produces a concrete prompt. User runs it in a separate chat session. User returns the transcript. Executor + user identify where the failure locates in `SKILL.md`.

No "skip the evidence" path. The gate is structurally verifiable: a reviewer can re-run the cc-search-chats query OR the committed fresh-session prompt and observe the same failure reproduce against the recorded pre-rewrite SKILL.md SHA.

**External artefacts (local):**
- `/tmp/superpowers-obra/skills/writing-skills/SKILL.md` (655 lines) — obra reference; we do NOT mirror its length, but adopt its sequencing pattern.
- `/tmp/superpowers-obra/skills/writing-skills/anthropic-best-practices.md` (1150 lines) — verbatim import per DR2.
- `/tmp/superpowers-obra/skills/writing-skills/render-graphs.js` (168 lines) — verbatim import per DR6.
- `/tmp/superpowers-obra/skills/writing-skills/examples/CLAUDE_MD_TESTING.md` (189 lines) — light-touch denubis-voice adaptation.

**Preflight step (M1 revision — /tmp is cleared at reboot; this phase has the most obra dependencies):** Before any task proceeds, verify the obra clone is present:
```bash
if ! git -C /tmp/superpowers-obra status >/dev/null 2>&1; then
  echo "obra clone absent — re-cloning"
  git clone https://github.com/obra/superpowers /tmp/superpowers-obra
fi
# Verify each specific file we import:
for f in skills/writing-skills/SKILL.md skills/writing-skills/anthropic-best-practices.md skills/writing-skills/render-graphs.js skills/writing-skills/examples/CLAUDE_MD_TESTING.md; do
  [ -f "/tmp/superpowers-obra/$f" ] || { echo "MISSING: /tmp/superpowers-obra/$f"; exit 1; }
done
git -C /tmp/superpowers-obra log -1 --format='%H %s'  # record in first commit message
```

## 2026-06-10 Amendment (operator-approved)

Overrides matching instructions elsewhere in this file:

1. **Pin to the up-most upstream.** All imports source from obra/superpowers (the origin of these files) at a recorded commit hash — never from ed3d's intermediate copies. Record the hash in the phase's first commit message AND in each imported file's denubis preface. (Task 0 of phase_03's amendment will already have cloned both upstreams; reuse those clones and hashes.)
2. **Dated-import discipline (rubric R6).** `anthropic-best-practices.md` is a third party's snapshot of Anthropic guidance, necessarily pre-June-2026; a verbatim import without dating violates the version-pinning discipline this plan establishes. Each imported file's preface gains: source repo, commit hash, import date, and a last-verified-against-live-docs date. For `anthropic-best-practices.md` specifically, add a verification step: spot-check its claims against live platform.claude.com docs (2026-06 tier — Fable 5 / Opus 4.8 pages exist). Record deltas in a short dated denubis appendix rather than editing obra's text (attribution preserved). If deltas are material, surface to the operator before importing.
3. **True-up sweep (new task).** Inventory the other denubis-extending-claude files descending from obra/ed3d — `graphviz-conventions.dot` (April byte-identity claim: re-verify), `examples/CLAUDE_MD_TESTING.md`, `long-running-state-patterns.md`, and anything else `syncing-with-upstream` knows about — and true them up against the same pinned obra hash. Record per file: identical / diverged-deliberately (cite the decision) / diverged-stale (true up).
4. **Skill-type table fix.** The rewritten `writing-skills` SKILL.md skill-type table includes **Discipline** alongside Technique/Pattern/Reference (2026-06-10 audit: the omission in the definitional skill propagates to every new skill, and is inconsistent with `writing-claude-directives`' By-Skill-Type table).
5. **GREEN tier note.** Task 5's "production-tier Opus" framing: cornerstone production tier now includes the Fable 5 main loop. GREEN subagent runs stay Sonnet. **Fable-tier verification is human-invoked only** (operator rule 2026-06-10) — manual checkpoint, never auto-dispatched.

Reference: `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` (R6, R9, R10), `docs/audits/2026-06-10-skill-audit-campaign.md`.

**Current file state (Phase 4B direct inspection):**
- `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`: 163 lines, 14 H2 sections (Core Principle, TDD Mapping, When to Create a Skill, Skill Types, Directory Structure, SKILL.md Template, RED-GREEN-REFACTOR Cycle, Testing by Skill Type, Common Rationalizations to Block, Anti-Patterns, Skill Creation Checklist).
- Cross-references `denubis-extending-claude:writing-claude-directives` and `denubis-extending-claude:testing-skills-with-subagents` already present.
- No references to `epistemic-humility` yet.
- No `examples/` subdirectory yet.

**Integration-evidence framing dropped (H3 revision).** Earlier drafts claimed "Phase 4's production IS the integration evidence" — extrapolating from the user's brainstorming-time direction that "today is a refactoring day, not integration-test day." The extrapolation was unfalsifiable: the written narrative could be perfect while the lived authoring skipped the methodology. That claim was dropped during H3 revision. Phase 4 still produces `writing-skills/SKILL.md` by invoking the three sub-skills in practice (epistemic-humility rubric applied to "When to Create a Skill", writing-claude-directives phrasing patterns, testing-skills-with-subagents RED evidence discipline). Whether the sequencing cohered in practice is audited retrospectively at Phase 5 Task 4.5 (the frustration-signal audit, AC5.8) — not by a written integration-evidence narrative.

---

<!-- START_TASK_1 -->
### Task 1: RED evidence — static file-shape diff (preventive cornerstone rewrite)

**Verifies:** skill-skills-upstream-sync.AC1.7 (RED evidence recorded for Phase 4)

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04_red_evidence.md`

**Purpose:** Record the deficiency in the current `writing-skills/SKILL.md` as a static file-shape diff. **Phase 4 is a preventive cornerstone rewrite, not a corrective one.** The target-state difference (current file is 163 lines of TDD-for-skills spine; rewrite target is ≤250 lines of thin cornerstone orchestrator sequencing three sub-skills) was identified by reading the file and the design plan, not by observing a session fail. No prior session has "failed at being too wordy" in a way cc-search-chats can surface; file shape and bloat are structural observations, not session-observable failures.

This amendment (2026-04-22 plan-amendment pass) mirrors Phase 2's amendment and applies the same precedent Phase 4 already set during H3 revision: the earlier "production IS integration evidence" claim was dropped as unfalsifiable, replaced by Phase 5 Task 4.5's frustration-signal audit as the downstream effectiveness check. Static code-shape evidence here, GREEN pressure scenario at Task 6 as the observable test.

Phase 3's RED-gate stays corrective (its target methodology is transcript-sourcing); Phase 2 and Phase 4 accept static evidence as RED.

**Step 1: Enumerate the file-shape deficiency**

Read the current `writing-skills/SKILL.md`. Record:
- Current line count (baseline measurement, pre-rewrite).
- Current section shape (H2 list — what's there and what's absent).
- Target line count: ≤250 lines.
- Target section shape (from Task 2 Step 1 — orchestrator shape + Workflow H2 sequencing three sub-skills).
- Absent structural elements: rubric callback (epistemic-humility), sub-skill Workflow H2, supporting-files section for obra imports, attribution for imported content.

The diff between current-shape and target-shape IS the RED evidence. The fact that no prior session has failed at "being too wordy" is itself evidence the deficiency is structural/architectural, not behavioural — the cornerstone reshape is architectural hygiene, not a corrective response.

**Step 2: Document RED evidence in `phase_04_red_evidence.md`**

File structure:
```markdown
# Phase 4 RED Evidence — Static File-Shape Diff (Preventive Cornerstone Rewrite)

**Source:** File-read of current `writing-skills/SKILL.md` (2026-04-22).
**Restructure framing:** PREVENTIVE (not corrective). No prior session has been observed failing at "being too wordy" or "missing sub-skill orchestration" in a cc-search-chats-addressable way — file shape is a structural observation, not a session-observable failure.
**Pre-rewrite SKILL.md SHA:** [git rev-parse HEAD:plugins/denubis-extending-claude/skills/writing-skills/SKILL.md]
**Pre-rewrite line count:** [wc -l result]

## File-shape diff

**Current shape (pre-rewrite):**
- [line count]
- [H2 list]
- Absent: rubric callback, Workflow H2 sequencing, Supporting Files section for obra imports

**Target shape (post-rewrite):**
- ≤250 lines
- H2 list per Task 2 Step 1
- Present: rubric callback to epistemic-humility, Workflow H2 sequencing three sub-skills, Supporting Files section naming anthropic-best-practices.md / render-graphs.js / examples/CLAUDE_MD_TESTING.md

## How Phase 4 addresses the deficiency

- Task 2 rewrites SKILL.md as thin cornerstone orchestrator.
- Tasks 3-5 import obra supporting files verbatim with attribution.
- Task 6 verifies via synthetic pressure scenarios (GREEN) and rubric self-application.

## Why this is NOT session-transcript RED

The deficiency is architectural, not behavioural. Sessions have used the current `writing-skills/SKILL.md` to author skills without failing in a transcript-quotable way — but the output shape has drifted from what a thin cornerstone should be. The rewrite is preventive hygiene. This mirrors the H3-revision precedent that dropped Phase 4's earlier "production IS integration evidence" claim as unfalsifiable.
```

**Step 3: Commit RED evidence**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04_red_evidence.md
git commit -m "docs(phase-04): RED evidence — static file-shape diff (preventive cornerstone rewrite)

Phase 4 is a preventive cornerstone rewrite, not a corrective one. File
shape is a structural observation (current 163 lines of TDD-spine,
target ≤250 lines of orchestrator); no prior session has failed at
'being too wordy' in a cc-search-chats-addressable way. Task 6's
synthetic obra pressure scenarios remain the GREEN regression check.

Amended from the original independent-session-gate framing per the
2026-04-22 plan-amendment pass, mirroring Phase 2's amendment and
applying the H3-revision precedent that dropped Phase 4's earlier
'production IS integration evidence' claim."
```

**Consumer-tracing:** This file is consumed by (a) Phase 4's Task 6 GREEN verification, (b) Phase 5's cross-reference audit.

**Gate statement (amended 2026-04-22):** Phase 4 does not proceed to Task 2 without a committed `phase_04_red_evidence.md` containing the Step 1 file-shape diff. The gate is structurally verifiable: a reviewer can diff current-vs-target line count and section shape against the recorded SHA to reproduce the deficiency assessment.
<!-- END_TASK_1 -->

<!-- START_SUBCOMPONENT_A (tasks 2-5) -->

<!-- START_TASK_2 -->
### Task 2: Rewrite `writing-skills/SKILL.md` as thin cornerstone orchestrator

**Verifies:** skill-skills-upstream-sync.AC1.1, skill-skills-upstream-sync.AC1.2, skill-skills-upstream-sync.AC1.3

**Files:**
- Modify (full rewrite): `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`

**Step 1: Plan the section order**

Target ≤250 lines with this structure:

1. Frontmatter (existing `name` + `description`, `user-invocable: false` — keep)
2. H1 title `# Writing Skills`
3. Opening paragraph (2-3 sentences): *"Writing skills IS Test-Driven Development applied to process documentation. This cornerstone orchestrator sequences three sub-skills: epistemic-humility (should this skill exist?), writing-claude-directives (how should it be phrased?), testing-skills-with-subagents (does it survive pressure?). Iron Law: No skill without a failing test first."*
4. `## Core Principle` (keep Iron Law statement; consolidate existing content)
5. `## TDD Mapping` (keep existing table, minor cleanup)
6. `## When to Create a Skill` — add rubric callback per DR3 at the end of this section: *"**Before committing to creation, apply the rubric:** run the artefact-under-consideration through `denubis-extending-claude:epistemic-humility`. If it fails Scope (Jones's three conditions), Observability (three screens), Process (Schön's four questions), or the Failure-pattern screen, the right next step is to re-scope, not to author. Directive-writing is a protective belt around a scope decision, not a substitute for it."*
7. `## Skill Types` (keep — Technique / Pattern / Reference)
8. `## Directory Structure` — update to show the supporting-files pattern Phase 4 establishes (skill directory can contain `SKILL.md` + peer supporting files + optional `examples/` subdirectory). Reference obra's pattern.
9. `## SKILL.md Template` (keep inline per DR4)
10. `## Workflow` (NEW per DR7): explicit sequencing —
    - **Scope check:** `denubis-extending-claude:epistemic-humility` — rubric applied before committing to a skill
    - **Phrasing and compliance:** `denubis-extending-claude:writing-claude-directives` — token efficiency, discovery optimisation, model-tier notes, aggressive-language dial-back
    - **RED/GREEN/REFACTOR:** `denubis-extending-claude:testing-skills-with-subagents` — pressure testing, conversation-precedent sourcing, bulletproofing
11. `## Supporting Files` — document the three newly-imported files with their purpose:
    - `anthropic-best-practices.md` (obra verbatim) — Anthropic-authored reference on skill structure, CSO, anti-patterns
    - `render-graphs.js` (obra verbatim) — Node + graphviz skill-author tool for visualising process flows (see `README.md` for invocation)
    - `examples/CLAUDE_MD_TESTING.md` (obra adapted) — worked example of pressure-testing CLAUDE.md documentation
12. `## Anti-Patterns` (keep existing four: narrative example, multi-language dilution, code in flowcharts, generic labels)
13. `## Skill Creation Checklist` (keep — TaskCreate-oriented checklist)

**Step 2: Write the new SKILL.md**

Edit the existing file replacing sections per Step 1's plan. Key deletions:
- **Remove `## Common Rationalizations to Block` section** (per DR9 — content duplicated in sub-skills)
- **Remove `## Testing by Skill Type` table** (its content is subsumed by `testing-skills-with-subagents`'s model-tier + pressure-type coverage; keeping it as a summary was fine, but the reshape toward pure sequencing makes it redundant)

Key additions:
- New `## Workflow` H2 with sub-skill sequencing
- New `## Supporting Files` H2 documenting the imported files
- Rubric callback within `## When to Create a Skill`
- Opening paragraph naming the sequencing pattern

Keep:
- Core Principle + Iron Law
- TDD Mapping table
- Skill Types (Technique / Pattern / Reference)
- Directory Structure (update to show supporting-files pattern)
- SKILL.md Template
- Anti-Patterns (four)
- Skill Creation Checklist

**Step 3: Verify line count and structural constraints**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/writing-skills/SKILL.md') as f:
    content = f.read()
    lines = content.splitlines()
# AC1.2: line count <=250
assert len(lines) <= 250, f'line count {len(lines)} exceeds 250 (AC1.2)'
# AC1.1: frontmatter
assert content.startswith('---\n'), 'frontmatter missing opener'
import yaml
_, fm, _ = content.split('---', 2)
data = yaml.safe_load(fm)
assert data.get('name') == 'writing-skills', f'name wrong: {data.get(\"name\")!r}'
assert isinstance(data.get('description'), str) and len(data['description']) > 40, 'description missing/too short'
# AC1.3: cross-references to all three sub-skills
for ref in [
    'denubis-extending-claude:epistemic-humility',
    'denubis-extending-claude:writing-claude-directives',
    'denubis-extending-claude:testing-skills-with-subagents',
]:
    assert ref in content, f'cross-reference missing: {ref}'
# DR7: Workflow H2 exists
assert '## Workflow' in content, 'Workflow H2 missing (DR7)'
# DR9: obsolete rationalizations table removed
assert 'Common Rationalizations to Block' not in content, \
    'Common Rationalizations to Block section still present (DR9 violation)'
# DR3: rubric callback inside 'When to Create a Skill'
wtcas_pos = content.find('## When to Create a Skill')
# find the end of this section (next H2)
next_h2_pos = content.find('\n## ', wtcas_pos + 1)
wtcas_section = content[wtcas_pos:next_h2_pos] if next_h2_pos != -1 else content[wtcas_pos:]
assert 'epistemic-humility' in wtcas_section, 'rubric callback not in When to Create a Skill section (DR3)'
# DR4: SKILL.md template inline
assert '```markdown' in content, 'SKILL.md template code block missing (DR4)'
assert 'name:' in content and 'description:' in content, 'template frontmatter exemplar missing'
print(f'SKILL.md cornerstone structural checks passed (line count: {len(lines)})')
"
```
Expected: `SKILL.md cornerstone structural checks passed (line count: N)` where N ≤ 250.

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-skills/SKILL.md
git commit -m "refactor(writing-skills): cornerstone rewrite as thin orchestrator sequencing three sub-skills

- Reshape from 163-line TDD-for-skills spine into explicit sequencer:
  scope check (epistemic-humility) -> phrasing (writing-claude-directives)
  -> RED/GREEN/REFACTOR (testing-skills-with-subagents)
- Add rubric callback inside 'When to Create a Skill' section (DR3)
- Add new '## Workflow' H2 making sub-skill sequence first-class (DR7)
- Add new '## Supporting Files' H2 documenting obra imports (Task 3/4/5)
- Remove obsolete 'Common Rationalizations to Block' section (DR9;
  content now lives in sub-skills)
- Remove 'Testing by Skill Type' table (subsumed by testing-skills-with-subagents)
- Keep: Iron Law, TDD Mapping, Skill Types, Directory Structure,
  SKILL.md Template, Anti-Patterns, Skill Creation Checklist
- Preserve existing cross-references; add denubis-extending-claude:epistemic-humility

Line count target: ≤250 (thin orchestrator).

Part of skill-skills upstream sync (Phase 4). Integration evidence
per design plan DoD — cornerstone authored using Phase 1-3 outputs.
Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Import `anthropic-best-practices.md` verbatim with denubis preface

**Verifies:** skill-skills-upstream-sync.AC1.4 (partial), skill-skills-upstream-sync.AC1.5

**Files:**
- Create: `plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md`

**Step 1: Copy obra file verbatim**

```bash
cp /tmp/superpowers-obra/skills/writing-skills/anthropic-best-practices.md \
   /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md
```

**Step 2: Prepend frontmatter + denubis preface**

Edit the file to insert at the very top (before existing obra H1 or H2):

```markdown
---
source: obra/superpowers/skills/writing-skills/anthropic-best-practices.md
imported: 2026-04-17
adaptation: verbatim (frontmatter + preface only; body obra-authored)
---

# Anthropic Best Practices (imported reference)

> **Denubis preface:** This file is obra-authored reference material, imported verbatim from the obra/superpowers repository on 2026-04-17. It covers Anthropic-authored skill-authoring best practices (core principles, skill structure, CSO, anti-patterns) and example workflows. It is a reference, not denubis-authored guidance — denubis-specific skill-authoring guidance lives in the `writing-skills/SKILL.md` orchestrator and in the sub-skills it references. Consult this file when you want Anthropic's own framing on a skill-authoring concern; consult the sub-skills when you want denubis's applied methodology.

---

[original obra content follows verbatim below]
```

Then below the `---` separator, keep the obra file's content byte-identical. No edits to the body.

**Step 3: Verify**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md') as f:
    content = f.read()
# AC1.5: source attribution in frontmatter
assert 'source: obra/superpowers' in content, 'obra source attribution missing'
# Denubis preface present
assert 'Denubis preface' in content, 'denubis preface missing'
# Body substantially obra-length (within 10% tolerance because we added frontmatter + preface lines)
with open('/tmp/superpowers-obra/skills/writing-skills/anthropic-best-practices.md') as f:
    obra_content = f.read()
ratio = len(content) / len(obra_content)
assert 0.95 < ratio < 1.10, f'length ratio {ratio:.3f} outside tolerance — body may not be verbatim'
print('anthropic-best-practices.md import structural checks passed')
"
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-skills/anthropic-best-practices.md
git commit -m "feat(writing-skills): import anthropic-best-practices.md from obra (verbatim)

Imported from obra/superpowers/skills/writing-skills/anthropic-best-practices.md
on 2026-04-17. Body byte-identical; frontmatter source line + denubis preface
added to distinguish obra-authored reference from denubis-authored guidance.

Supports Phase 4 cornerstone rewrite: denubis-specific skill-authoring
guidance lives in writing-skills/SKILL.md and its sub-skills; this file
is reference material for Anthropic's own framing.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR2 Phase 4)"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Import `render-graphs.js` verbatim with README

**Verifies:** skill-skills-upstream-sync.AC1.4 (partial), skill-skills-upstream-sync.AC1.5 (partial)

**Files:**
- Create: `plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js`
- Create: `plugins/denubis-extending-claude/skills/writing-skills/README.md`

**Step 1: Copy obra script verbatim**

```bash
cp /tmp/superpowers-obra/skills/writing-skills/render-graphs.js \
   /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js
chmod +x /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js
```

**Step 2: Verify byte-identicality**

```bash
diff -q /tmp/superpowers-obra/skills/writing-skills/render-graphs.js \
        /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js
```
Expected: no output (byte-identical).

**Step 3: Create README.md documenting the Node + graphviz dependencies**

Author `plugins/denubis-extending-claude/skills/writing-skills/README.md` with:

```markdown
# writing-skills — Supporting Files Note

This skill ships with three supporting files imported from obra/superpowers. Two are reference documents; one is a dev-only CLI tool.

## `render-graphs.js` — skill-author CLI (dev-only)

**Source:** obra/superpowers/skills/writing-skills/render-graphs.js (imported verbatim 2026-04-17).

**Dependencies:**
- Node.js runtime (tested with Node 18+)
- `dot` binary from graphviz — install via `apt install graphviz` / `brew install graphviz` / equivalent

**Usage:**
```
./render-graphs.js <skill-directory>           # Render each dot block to a separate SVG
./render-graphs.js <skill-directory> --combine # Combine all dot blocks into one diagram
```

Extracts all ` ```dot ` code blocks from the target `SKILL.md` and renders them to SVG files alongside. Useful when preparing diagram-heavy skills for human review.

**This is skill-author tooling, not runtime.** Claude Code does not invoke it; the script is for a human author or a subagent preparing visual documentation.

## `anthropic-best-practices.md` — obra reference (verbatim import)

Anthropic-authored skill-authoring best practices, imported from obra with attribution. See its frontmatter for provenance. Denubis-specific guidance lives in `SKILL.md` and the sub-skills it references.

## `examples/CLAUDE_MD_TESTING.md` — worked pressure-testing example (light-touch adapted)

Example pressure-scenario campaign for testing CLAUDE.md documentation. Imported from obra with light denubis-voice adaptation. Illustrative, not discipline-enforcing.
```

**Step 4: Verify**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && test -x plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js && echo "executable OK" || echo "not executable — chmod +x the file"
test -f plugins/denubis-extending-claude/skills/writing-skills/README.md && grep -q 'graphviz' plugins/denubis-extending-claude/skills/writing-skills/README.md && echo "README OK"
```

**Step 5: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-skills/render-graphs.js plugins/denubis-extending-claude/skills/writing-skills/README.md
git commit -m "feat(writing-skills): import render-graphs.js from obra + README for supporting files

- render-graphs.js imported verbatim from obra/superpowers. Node + dot
  (graphviz) dependencies. Skill-author tooling, not runtime.
- README.md documents all three supporting files (render-graphs.js,
  anthropic-best-practices.md, examples/CLAUDE_MD_TESTING.md) with
  dependencies, usage, and obra attribution.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR6 Phase 4)"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Import `examples/CLAUDE_MD_TESTING.md` with light-touch adaptation

**Verifies:** skill-skills-upstream-sync.AC1.4 (final), skill-skills-upstream-sync.AC1.5 (final)

**Files:**
- Create: `plugins/denubis-extending-claude/skills/writing-skills/examples/` (new subdirectory — establishes the examples/ convention per DR5)
- Create: `plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md`

**Step 1: Create the examples/ subdirectory**

```bash
mkdir -p /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-skills/examples
```

**Step 2: Copy obra file and apply light-touch adaptation**

Copy:
```bash
cp /tmp/superpowers-obra/skills/writing-skills/examples/CLAUDE_MD_TESTING.md \
   /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md
```

Adaptation (minimal per DR5):
- Prepend frontmatter:
  ```yaml
  ---
  source: obra/superpowers/skills/writing-skills/examples/CLAUDE_MD_TESTING.md
  imported: 2026-04-17
  adaptation: light-touch — denubis voice tweaks; scenario content obra-authored
  ---
  ```
- Scan body for obra-specific references ("superpowers:X", obra skill names that don't exist in denubis). Where found, either (a) update to denubis equivalent if one exists, or (b) annotate as `_(obra reference; denubis equivalent: [name if known; otherwise "none"])_`.

**Do NOT** rewrite the scenarios themselves. They're illustrative, not discipline-enforcing. Keep obra content unless the cross-reference would break.

**Step 3: Verify**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
import os
# AC1.4: file exists
path = 'plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md'
assert os.path.exists(path), f'{path} missing'
with open(path) as f:
    content = f.read()
# AC1.5: obra attribution in frontmatter
assert 'source: obra/superpowers' in content, 'obra attribution missing from frontmatter'
# Scenario content preserved (rough length check)
with open('/tmp/superpowers-obra/skills/writing-skills/examples/CLAUDE_MD_TESTING.md') as f:
    obra = f.read()
ratio = len(content) / len(obra)
assert 0.95 < ratio < 1.25, f'length ratio {ratio:.3f} — adaptation too heavy or file incomplete'
print('examples/CLAUDE_MD_TESTING.md import structural checks passed')
"
```

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/writing-skills/examples/CLAUDE_MD_TESTING.md
git commit -m "feat(writing-skills): establish examples/ subdirectory with CLAUDE_MD_TESTING worked example

Imported from obra/superpowers/skills/writing-skills/examples/CLAUDE_MD_TESTING.md
with light-touch adaptation: frontmatter source attribution, obra-specific
cross-references updated where denubis equivalents exist.

Establishes the examples/ subdirectory convention for denubis skills
(design DR5 Phase 4). Other denubis skills may follow this pattern
for worked examples going forward. Phase 1's self-application.md
remains a sibling file rather than in examples/ because it is an
integrity proof, not an example.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md (DR5 Phase 4)"
```

**Consumer-tracing:** SKILL.md's `## Supporting Files` section points at this file. Phase 5's cross-reference audit verifies the pointer resolves.
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_TASK_6 -->
### Task 6: GREEN verification + rubric self-application

**Verifies:** skill-skills-upstream-sync.AC1.1-AC1.6 (final)

**Files:**
- Create: `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04_green_verification.md`

**Step 1: GREEN verification via pressure-scenario invocation**

Dispatch a subagent (recommended: `denubis-basic-agents:sonnet-general-purpose` — Phase 3's methodology says run GREEN one tier down from production, and cornerstone work is production-tier Opus). Pressure scenario:

> *You need to write a new skill for the repo. You have 30 minutes before end of day. You know the pattern you want to capture; you've done it successfully twice. Your human partner asks if the skill is ready to ship.*
>
> *Apply `denubis-extending-claude:writing-skills`. What's the sequence?*

The restructured cornerstone should cause the subagent to:
1. Invoke the rubric-callback — apply `epistemic-humility` before committing to creation
2. Surface conversation-precedent requirement — require a RED transcript before GREEN
3. Sequence writing-claude-directives for phrasing + testing-skills-with-subagents for pressure testing
4. NOT produce a "ship it" conclusion when the conversation-precedent gate hasn't been passed

Capture the subagent's output; check each of the four as pass/fail.

**Step 2: REFACTOR — close loopholes**

If Step 1 reveals any of the four checks fail, make targeted edits and re-run. Document iterations.

**Step 3: Rubric self-application walk-through (H4 revision: not a pass/fail gate)**

Apply `denubis-extending-claude:epistemic-humility` to the restructured Phase 4 artefact. This is a walk-through, not a pass/fail check. The deliverable is:
- An honest walk-through of each rubric section
- **Any reflective vulnerability surfaced — raise to user BEFORE committing GREEN.** A vulnerability is any question where (a) the honest answer strains against current state, (b) the walk-through has to rationalise a near-miss, or (c) the author would not defend the answer to a reviewer. Zero vulnerabilities surfaced is itself a flag — re-run with sharper honesty.
- User acknowledges or directs remediation. Document the acknowledgement.

Sections to walk through:
- Scope: Jones's three conditions (the phase is bounded, auditable, reversible; failures surface to a human)
- Observability: three screens applied to Done-when entries
- Process: Schön's four questions on the cornerstone rewrite
- Failure-pattern: four patterns checked

Document findings + surfaced vulnerabilities + user acknowledgement.

**Step 4: Write `phase_04_green_verification.md`**

Same structure as Phase 2/3 GREEN verification files. Add a closing section titled "Sub-skill Invocations" naming which sub-skills (Phase 1-3 outputs) were exercised in Phase 4's production and how. This is a factual record of invocations, not a claim of integration-evidence coherence — the retrospective audit of whether the sequencing cohered in practice happens at Phase 5 Task 4.5 (frustration-signal audit).

**Step 5: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04_green_verification.md
git commit -m "docs(phase-04): GREEN verification + rubric self-application

Phase 4 passes GREEN pressure scenario (four-check sequencing) and
epistemic-humility rubric self-application.

The cornerstone was authored using Phase 1 (epistemic-humility rubric
applied to 'when to create'), Phase 2 (writing-claude-directives phrasing
patterns), and Phase 3 (testing-skills-with-subagents RED evidence
discipline). Whether the sub-skill sequencing cohered in practice is
audited retrospectively at Phase 5 Task 4.5 (frustration-signal audit,
AC5.8); no separate integration test is authored.

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_6 -->

---

## Done when (phase-level)

- [ ] `phase_04_red_evidence.md` exists on disk with the pre-rewrite SKILL.md SHA, current-line-count baseline, current H2-shape enumeration, target-shape diff (≤250 lines + Workflow H2 + Supporting Files + rubric callback), and the explicit "preventive, not corrective" framing (Task 1) — static file-shape diff RED per the 2026-04-22 plan-amendment pass (Phase 4 is preventive; original independent-session-failure framing reversed, mirroring Phase 2)
- [ ] `writing-skills/SKILL.md` rewritten as thin cornerstone; ≤250 lines; cross-references to all three sub-skills resolve; rubric callback inside "When to Create a Skill"; Workflow H2 sequences sub-skills (Task 2)
- [ ] `anthropic-best-practices.md` imported with obra attribution + denubis preface; body byte-identical to obra (Task 3)
- [ ] `render-graphs.js` imported verbatim + executable; `README.md` documents dependencies (Task 4)
- [ ] `examples/CLAUDE_MD_TESTING.md` imported with frontmatter attribution; `examples/` subdirectory convention established (Task 5)
- [ ] GREEN verification passes four-check pressure scenario; rubric self-application walk-through committed with any surfaced vulnerabilities acknowledged by user; sub-skill-invocations section written (Task 6)
- [ ] Commits land per user's commit preference (5 commits for Tasks 1-5; Task 6 adds 1 GREEN/audit commit)
- [ ] Back-referenced UAT entries from Phase 2 DR8 and Phase 3 DR7 (both rubric-callback placement-timing) present in `uat-requirements.md`'s Phase 4 section using the gate-form template. DR-P4-INT-1 was DELETED during H3 revision (unauditable-by-design; replaced by Phase 5 Task 4.5 frustration-signal audit under AC5.8)

**Not in scope for Phase 4:**
- Anything outside `writing-skills/` (Phase 5 covers cross-references and version bump)
- Adaptation of obra's `anthropic-best-practices.md` body beyond attribution + preface (DR2 decision)
- Wiring `render-graphs.js` into any automated pipeline (dev-only tool)
