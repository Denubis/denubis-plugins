# Skill-Skills Upstream Sync — Phase 1: Author `epistemic-humility` Reference Skill

**Goal:** Create the `epistemic-humility` reference skill as the cornerstone dependency for Phases 2–4, grounded in verifiable content from `AbsenceJudgement.tex`, Schön 1994, Jones 2025, and Latour 1987/1999.

**Architecture:** A reference-type skill (not discipline-enforcing at invocation) loaded on demand by orchestrator skills. A terse `SKILL.md` carries the four-section rubric (Scope → Observability → Process → Failure-pattern screen). Two sibling supporting files carry dense material: `absencejudgement-citations.md` holds paragraph-level verbatim quotations and `self-application.md` holds the rubric-applied-to-itself coherence demonstration required by AC4.5. Cross-references from Phases 2/3/4 are deferred — this phase does not wire them up.

**Tech Stack:** Markdown with YAML frontmatter. No runtime dependencies. Source material: `/home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex` (read-only, outside repo), plus named secondary sources for the Observability section (Latour 1987 *Science in Action*; Latour 1999 *Pandora's Hope*).

**Scope:** 1 of 5 phases from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md`.

**Codebase verified:** 2026-04-17 (Phase 1B investigator findings recorded in task #7 completion).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### skill-skills-upstream-sync.AC4: `epistemic-humility` reference skill
- **skill-skills-upstream-sync.AC4.1 Success:** `plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md` exists with reference-type frontmatter (description keyed to scope-assessment triggers)
- **skill-skills-upstream-sync.AC4.2 Success:** Rubric has four sections: Scope (Jones's three conditions), Observability, Process (Schön's four questions), Failure-pattern screen
- **skill-skills-upstream-sync.AC4.3 Success:** Every cited claim is attributable to `AbsenceJudgement.tex` with a page or section ref, or to a named secondary source (Schön 1994 p.132, Jones — citation located and verified)
- **skill-skills-upstream-sync.AC4.4 Failure:** No mention of TEMP, RAND, SCOP, VIBE, FABR, MECH, MTCH, SCAF, or BOUN as defined codes (grep-audit); if any of these strings appear, it must be in a rejection context explicitly citing DR4
- **skill-skills-upstream-sync.AC4.5 Edge:** Rubric self-application is a **walk-through with surfaced vulnerabilities, not a pass/fail gate** (H4 revision). Deliverable: (a) a committed walk-through applying each rubric section to the rubric itself, living in the skill's body or a supporting file, AND (b) any reflective vulnerability surfaced by the walk-through raised to the user for acknowledgement before GREEN. Zero vulnerabilities surfaced is itself a flag — re-run with sharper honesty. Retrospective backstop: Phase 5 Task 4.5 frustration-signal audit (AC5.8).

---

## Dependencies and Sources

**External artefact (outside repo):** `/home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex` must be readable during implementation. Task 1's Step 0 verifies this.

**Verbatim source content captured in Phase 1C (use these exactly — paraphrasing re-introduces DR4 risk):**

- **Technoscholasticism (AbsenceJudgement.tex:203):** `"'technoscholasticism' [...] a digital scholasticism that privileges textual authority over critical assessment of knowledge claims."`
- **Schön's four questions (AbsenceJudgement.tex:252-259, citing `schon_reflective_1994` p.132):**
  > Can I solve the problem I have set?
  > Do I like what I get when I solve this problem?
  > Have I made the situation coherent?
  > Have I kept inquiry moving?
- **Jones's three conditions (AbsenceJudgement.tex:794-798, quoting `jones_i_2025` line 163):**
  > Scope is the only lever you wholly control. When an executive asks for an agent, shrink the mandate until you can prove three things in a sandbox: first, the agent finishes the task 90%+ of the time without rescue; second, the remaining share of failures is bounded, auditable, and reversible; third, every miss surfaces fast enough that a human—not a cron job—decides whether to roll back or roll forward.
- **Four failure patterns (paper's verbatim terminology — use these, not the design plan's paraphrases):**
  - `temporality blindness` (AbsenceJudgement.tex:785) — verbatim
  - `scope/confabulation` (AbsenceJudgement.tex:789, 792) — slash, not hyphen
  - `stamp-collecting without evaluation` / `evidence-accumulating approach` (AbsenceJudgement.tex:801, 810) — NOT "evidence accumulation without evaluation"
  - `vibes-based operation` / `'vibes' or opaque heuristics` (AbsenceJudgement.tex:816, 819) — verbatim
- **Three success conditions (AbsenceJudgement.tex:868, all in one paragraph):**
  - `mechanical, bounded, low-judgement tasks` — verbatim (note: paper lists three adjectives, not two)
  - `heavy scaffolding` — verbatim
  - `reserving all evaluative and synthetic work for human judgement` — the design's "human-reserved synthesis" is a paraphrase; use the paper's phrase or mark explicitly as our compression
- **Paper section for the skill's own name:** `\subsubsection{Epistemic Humility}` at AbsenceJudgement.tex:261 — cite this as grounding for why the skill carries this name.
- **Jones bibliographic details:** Nate Jones, "I Summarized Mary Meeker's Incredible 340 Page 2025 AI Trends Deck—Here's Mary's Take, My Response, and What You Can Learn", Nate's Substack, June 2025, URL `https://natesnewsletter.substack.com/p/i-summarized-mary-meekers-incredible`, the three-condition quote at Jones's own line 163. Type-tag: newsletter (not peer-reviewed).
- **Schön bibliographic details:** Donald A. Schön, *The Reflective Practitioner: How Professionals Think in Action*, Taylor & Francis Group (Oxford), 1994, ISBN 978-1-351-88315-3, cited at p.132.
- **Latour (named secondary source for Observability black-boxing framing — NOT in AbsenceJudgement.tex):** Bruno Latour, *Science in Action: How to Follow Scientists and Engineers Through Society*, Harvard University Press, 1987; and Bruno Latour, *Pandora's Hope: Essays on the Reality of Science Studies*, Harvard University Press, 1999. Task-implementor should verify ISBNs at implementation time; the key concepts are "black box" and "immutable mobile" (1987) and the construction-of-facts argument (1999).

**Verified absences (load-bearing for DR4 compliance):**
- `TEMP`, `RAND`, `SCOP`, `VIBE`, `FABR`, `MECH`, `MTCH`, `SCAF`, `BOUN` — zero hits in `AbsenceJudgement.tex` (exhaustive word-boundary grep audit in Phase 1C).
- Haraway — zero hits; Popper/Lakatos — one parenthetical mention only; prolepsis — zero hits. These must not be cited as if they were paper content.

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Create `epistemic-humility/SKILL.md` with frontmatter, memento, and rubric sections

**Verifies:** skill-skills-upstream-sync.AC4.1, skill-skills-upstream-sync.AC4.2, skill-skills-upstream-sync.AC4.3 (partial — closed by Task 2), skill-skills-upstream-sync.AC4.4

**Files:**
- Create: `plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md`
- Create: `plugins/denubis-extending-claude/skills/epistemic-humility/` (directory must be created first)

**Step 0: Verify source file accessibility**

Run:
```bash
test -r /home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex && echo "source readable" || echo "MISSING SOURCE — HALT"
```
Expected: `source readable`. If missing, halt and surface to user — DR4 compliance cannot be verified without the source.

**Step 1: Create the skill directory**

```bash
# L1 revision: verify the parent skills/ directory exists before mkdir.
# If absent, the plugin was renamed mid-flight — halt rather than silently
# recreate a directory that shouldn't exist.
test -d /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills || {
  echo "ERROR: parent skills/ directory missing — plugin may have been renamed"
  echo "Halt and check plugin state before continuing"
  exit 1
}
mkdir -p /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/epistemic-humility
```

**Step 2: Author SKILL.md**

Follow this structure exactly. Section ordering is design-locked (DR6). Frontmatter field set matches the denubis-extending-claude convention (confirmed in Phase 1B: `name`, `description`, `user-invocable` only — no `family` field).

The file must contain these sections, in order:

1. **YAML frontmatter**
   - `name: epistemic-humility`
   - `description:` — one sentence that keys the skill to scope-assessment triggers. Phrasing target: "Use when assessing whether a proposed skill, agent scaffold, or automated task earns its existence — provides a rubric for scope, observability, reflective process, and failure-pattern screening, sourced from AbsenceJudgement.tex, Schön 1994 p.132, Jones 2025, and Latour 1987/1999."
   - `user-invocable: false` — Phase 1 DR3 (this planning session, 2026-04-17): sidecar, loaded by cross-reference from orchestrator skills. User approved with the "remember thou art AI" memento framing: AbsenceJudgement §Epistemic Humility argues LLMs cannot genuinely hold this virtue, so the rubric is a mechanical surrogate invoked by other skills at scope-check points, not a human-triggerable action. If a future need arises for direct human `/epistemic-humility` invocation (ad-hoc scope checks on proposed skills outside an orchestrator flow), revisit this decision — it is reversible without breaking cross-references.

2. **Opening memento (DR3 reflexive framing)** — a short note immediately after frontmatter, before the H1 heading, explicitly stating that AbsenceJudgement's §Epistemic Humility (line 261) argues LLMs cannot genuinely hold this virtue. The rubric is therefore a *mechanical surrogate*, not an achievement. Frame honesty about this gap as the rubric's first act.

3. **H1 title:** `# Epistemic Humility (Rubric Skill)`

4. **Why this skill exists** — 3-5 sentences. Technoscholasticism (AbsenceJudgement.tex:203) as the failure the rubric guards against; textual-authority substitution masquerading as evidence. Cite AbsenceJudgement.tex by line numbers inline.

5. **When to invoke** — bullet list of trigger moments (scope check on a new skill, agent-scaffold decision, automation-task authorisation, DoD review). Terse.

6. **The Rubric** — H2. Four subsections, in design order:

   a. **`## Scope — Jones's three conditions`**
      - Open with the verbatim block quote of Jones's three conditions (AbsenceJudgement.tex:794-798 quoting `jones_i_2025` line 163). Format as a block quote.
      - Restate the three as a numbered checklist the reader applies to the artefact under review: (1) 90%+ of runs complete without rescue; (2) failures are *bounded, auditable, and reversible* (three adjectives — DR4, do not compress to "bounded-reversible"); (3) every miss surfaces fast enough that a human — not a cron job — decides whether to roll back or roll forward.
      - One-paragraph application gloss: how to apply each condition to a proposed skill or agent scaffold. Keep under 150 words.
      - Closing pointer: full bibliographic citation in `absencejudgement-citations.md` (Task 2).

   b. **`## Observability — three screens`**
      - Introduce as the screen that separates falsifiable DoD claims from authoritative-looking noise.
      - **Screen 1: Form-gate.** Every DoD/Done-when/AC entry is either (a) actor + action — names who does what and what counts as doing it — or (b) an operational check bound to a *named* command with expected output. Entries that are artefact-only ("X committed", "Y updated") or modifier-only ("terse", "production-ready") fail.
      - **Screen 2: Tautology-screen.** The check must not self-prove. "All tests pass" is vacuous: pytest returns green against zero meaningful tests. The screen asks: *Could this DoD entry hold true in a state where nothing useful was built?* If yes, it fails.
      - **Screen 3: Named-falsifier.** The sentence identifies who or what would surface the failure. Passive voice with implied-but-unnamed observers ("the code is reviewed", "validation runs") fails.
      - **Latour grounding (one paragraph):** Latour's "black box" / "immutable mobile" (Latour 1987, *Science in Action*) names what the three screens exclude — a claim that cannot be opened and re-tested by a reader has enrolled no allies; it rests on authority-by-form alone. Cite Latour 1987 and Latour 1999 (*Pandora's Hope*) for the construction-of-facts argument. Flag explicitly: Latour is a named secondary source, NOT cited from AbsenceJudgement (the paper does not reference Latour).
      - Worked example (3-5 lines): take the "All tests pass" anti-pattern and show it failing Screen 2, then show the corrected form passing all three (e.g., "`pytest plugins/denubis-extending-claude/skills/epistemic-humility/tests/ --strict-markers` exits 0 with ≥1 non-skipped test").

   c. **`## Process — Schön's four questions`**
      - Open with the verbatim block quote of Schön's four questions (AbsenceJudgement.tex:252-259). Format as a block quote.
      - Restate each as a reflective check the reader asks *of the artefact under review*:
        - *Can I solve the problem I have set?* — Is the artefact's scope tractable?
        - *Do I like what I get when I solve this problem?* — Does the output match the intent, or only the form of intent?
        - *Have I made the situation coherent?* — Does the artefact fit the surrounding system, or does it introduce contradictions?
        - *Have I kept inquiry moving?* — Does the artefact enable the next question, or does it freeze the situation into a black box?
      - Emphasise: **these are reflective, not algorithmic.** Mechanical yes/no answers are themselves a failure mode of the screen (echoes AbsenceJudgement's technoscholasticism critique at line 203).
      - Bibliographic pointer: Schön 1994 p.132, full details in `absencejudgement-citations.md`.

   d. **`## Failure-pattern screen`**
      - Short introduction: four named patterns from AbsenceJudgement §5.2. If the artefact under review exhibits any of these, the rubric fails.
      - Four named patterns (use paper-verbatim wording — DR4):
        - **Temporality blindness** (AbsenceJudgement.tex:785) — 1-2 sentence gloss as it applies to skill authorship.
        - **Scope/confabulation** (AbsenceJudgement.tex:789, 792) — slash, not hyphen; 1-2 sentence gloss.
        - **Stamp-collecting without evaluation** / **evidence-accumulating approach** (AbsenceJudgement.tex:801, 810) — explicitly use the paper's two phrases, not the design plan's paraphrase "evidence accumulation without evaluation"; 1-2 sentence gloss.
        - **Vibes-based operation** / **'vibes' or opaque heuristics** (AbsenceJudgement.tex:816, 819) — 1-2 sentence gloss.
      - Positive counterpoint (one paragraph): three success conditions from AbsenceJudgement.tex:868 — `mechanical, bounded, low-judgement tasks`; `heavy scaffolding`; `reserving all evaluative and synthetic work for human judgement`. Frame as "what the artefact should look like if the four failure patterns are absent".

7. **Cross-reference stanza** — H2. State that this rubric is invoked from: `denubis-extending-claude:writing-skills`, `denubis-extending-claude:testing-skills-with-subagents`, `denubis-extending-claude:writing-claude-directives`. Add explicit note: *these cross-references point forward; the referring skills are updated in Phases 2-4 of the upstream-sync plan. If any reference fails to resolve, that is a Phase 5 cross-reference-audit issue.*

8. **Self-application pointer** — H2. One paragraph pointing to `self-application.md` (Task 3) as the AC4.5 coherence demonstration. Do NOT inline the walk-through here.

9. **Fabricated-codes rejection note** — H2 titled "Note on fabricated taxonomy". One short paragraph explicitly noting that prior-session handoffs contained fabricated codes (TEMP/RAND/SCOP/VIBE/FABR/MECH/MTCH/SCAF/BOUN). None of these appear in AbsenceJudgement.tex (verified by word-boundary grep-audit, 2026-04-17). This skill does not use them. Cite DR4 of the upstream-sync design plan. This section is the only place in the whole skill directory those strings may appear, and they appear in an explicit rejection context (AC4.4).

**Consumer-tracing:** Every section in this SKILL.md names its consumer — Sections 6a-6d are the rubric invoked from orchestrator rubric-callback sections (authored in Phases 2-4); the Cross-reference stanza's forward references resolve when Phases 2-4 land; the self-application pointer consumes Task 3's output; the fabricated-codes rejection note is read by Phase 5's cross-reference audit when it runs the fabricated-codes grep.

**Step 3: Verify frontmatter is valid YAML**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
import yaml, sys
with open('plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md') as f:
    content = f.read()
assert content.startswith('---\n'), 'no frontmatter opener'
_, fm, _ = content.split('---', 2)
data = yaml.safe_load(fm)
assert data.get('name') == 'epistemic-humility', f'name wrong: {data.get(\"name\")}'
assert isinstance(data.get('description'), str) and len(data['description']) > 60, 'description missing or too short'
assert data.get('user-invocable') is False, f'user-invocable must be false, got {data.get(\"user-invocable\")}'
print('frontmatter OK')
"
```
Expected output: `frontmatter OK`. Any assertion failure = halt and fix before proceeding.

**Step 4: Verify four rubric H2 sections present in required order**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
import re
with open('plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md') as f:
    lines = f.read().splitlines()
h2s = [l.strip() for l in lines if l.startswith('## ')]
expected_order = ['## Scope', '## Observability', '## Process', '## Failure-pattern screen']
present = [h for h in h2s if any(h.startswith(e) for e in expected_order)]
indices = [next(i for i, h in enumerate(present) if h.startswith(e)) for e in expected_order]
assert indices == sorted(indices), f'rubric sections out of order: {present}'
print('rubric sections present and in order')
"
```
Expected output: `rubric sections present and in order`.

**Step 5: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md
git commit -m "feat(epistemic-humility): author rubric SKILL.md with four-section structure

Cornerstone reference skill for skill-skills upstream sync (Phase 1).
Sources: AbsenceJudgement.tex (technoscholasticism, failure patterns,
success conditions), Schon 1994 p.132 (four reflective questions),
Jones 2025 Substack (three scope conditions), Latour 1987/1999
(black-box / immutable-mobile framing for Observability).

Refs: docs/design-plans/2026-04-17-skill-skills-upstream-sync.md"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Create `absencejudgement-citations.md` supporting file with paragraph-level quotations

**Verifies:** skill-skills-upstream-sync.AC4.3 (completed)

**Files:**
- Create: `plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md`

**Step 1: Author the citations file**

Structure:

1. **Frontmatter:** Single `---` block with `source:` line naming AbsenceJudgement.tex, author/title, and the audit date (2026-04-17). Optionally a `name:` field matching the file stem. No `description` or `user-invocable` needed — this is a supporting file, not a skill.

2. **Opening note** (2-3 sentences): This file is the evidence base for the `epistemic-humility` rubric. Every claim in `SKILL.md` traces to a quotation here with line numbers. Latour citations appear in the Observability section of SKILL.md because the paper does not discuss Latour; they are named secondary sources, not AbsenceJudgement content.

3. **H2 sections, one per source area** — each section contains the verbatim quotation(s) in a blockquote, then a 1-2 sentence framing note, with line references:

   - `## Technoscholasticism` — quote from AbsenceJudgement.tex:203 (the "digital scholasticism" definition). Include the abstract definition at AbsenceJudgement.tex:177 as corroborating quotation.
   - `## Schön's four reflective-practitioner questions` — quote the four-question enumeration from AbsenceJudgement.tex:252-259. Include Schön's full bibliographic entry (Taylor & Francis, 1994, ISBN 978-1-351-88315-3, p.132).
   - `## Jones's scope lever — three conditions` — quote the verbatim block from AbsenceJudgement.tex:794-798. Include Jones's full citation (Nate Jones, "I Summarized Mary Meeker's Incredible 340 Page 2025 AI Trends Deck", Nate's Substack, June 2025, URL, line 163 of source). Include an explicit note: **source is a Substack newsletter, not peer-reviewed**.
   - `## Four failure patterns` — one quotation per pattern:
     - Temporality blindness (AbsenceJudgement.tex:785)
     - Scope/confabulation (AbsenceJudgement.tex:792 — include the Claude-Research tool-count passage for specificity)
     - Stamp-collecting without evaluation (AbsenceJudgement.tex:801, 810)
     - Vibes-based operation (AbsenceJudgement.tex:819)
   - `## Three success conditions` — the single paragraph from AbsenceJudgement.tex:868 containing all three.
   - `## Paper's own §Epistemic Humility subsection` — note that AbsenceJudgement.tex:261 is `\subsubsection{Epistemic Humility}`. Quote one or two sentences from that subsection so the reader can verify the skill inherits its name from the paper's own usage.

4. **H2 section: `## Named secondary sources (not in AbsenceJudgement.tex)`**
   - Full bibliographic entry for Latour 1987 (*Science in Action*, Harvard UP, ISBN to be verified by implementor).
   - Full bibliographic entry for Latour 1999 (*Pandora's Hope*, Harvard UP, ISBN to be verified by implementor).
   - Explicit note: AbsenceJudgement does not discuss Latour. These citations support the Observability section's black-box / immutable-mobile framing.

5. **H2 section: `## Verified absences`** — explicit list: Haraway (zero hits in AbsenceJudgement.tex), Popper (one parenthetical mention at line 829, NOT substantive discussion), Lakatos (same parenthetical mention at line 829, NOT substantive), prolepsis (zero hits; the Kudina/Ballsun-Stanton/Alfano 2025 paper is cited once at AbsenceJudgement.tex:905 but not for its prolepsis content), and the nine fabricated taxonomy codes (TEMP/RAND/SCOP/VIBE/FABR/MECH/MTCH/SCAF/BOUN, all zero hits, exhaustive word-boundary grep). Include a brief explanation for why this list matters (DR4): these absences bound what the rubric may and may not claim from the paper.

**Consumer-tracing:** SKILL.md's Scope, Observability, Process, and Failure-pattern sections all cross-reference this file. Phase 5's fabricated-codes audit reads the Verified absences section to confirm the baseline it asserts.

**Step 2: Verify the file contains every required line-number reference**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md') as f:
    content = f.read()
required_line_refs = ['203', '252', '794', '785', '789', '801', '810', '819', '868', '261']
missing = [r for r in required_line_refs if f'AbsenceJudgement.tex:{r}' not in content and f'line {r}' not in content and f':{r}' not in content]
assert not missing, f'missing line refs: {missing}'
print('all required line references present')
"
```
Expected: `all required line references present`.

**Step 3: Verify verbatim phrases appear as quoted in the paper**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md') as f:
    citations = f.read()
required_verbatim = [
    'bounded, auditable, and reversible',
    'scope/confabulation',
    'stamp-collecting without evaluation',
    'vibes-based operation',
    'mechanical, bounded, low-judgement',
    'heavy scaffolding',
    'technoscholasticism',
    'Can I solve the problem I have set',
]
missing = [p for p in required_verbatim if p not in citations]
assert not missing, f'missing verbatim phrases (design paraphrased?): {missing}'
print('all required verbatim phrases present')
"
```
Expected: `all required verbatim phrases present`. Any missing phrase indicates the implementor slipped into a paraphrase — DR4 violation, must be corrected before commit.

**Step 4: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/epistemic-humility/absencejudgement-citations.md
git commit -m "feat(epistemic-humility): add paragraph-level source citations

Evidence base for the rubric. Every SKILL.md claim traces to a
quotation here with line numbers. Includes explicit 'verified absences'
section for DR4 compliance (Haraway, Popper, Lakatos, prolepsis, and
the nine fabricated taxonomy codes all confirmed absent from
AbsenceJudgement.tex)."
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Author `self-application.md` coherence demonstration

**Verifies:** skill-skills-upstream-sync.AC4.5

**Files:**
- Create: `plugins/denubis-extending-claude/skills/epistemic-humility/self-application.md`

**Step 1: Author the self-application walk-through**

The design plan's Additional Considerations section (quoted verbatim, design-plan lines 367-369) defines what this file must demonstrate: *"The rubric is a judgment aid — Schön's questions are reflective by design, not algorithmic. Self-application passes when the rubric demonstrably probes the same question categories it asks of other skills (i.e. the rubric's sections map back onto itself without contradiction), not when every checkbox is mechanically satisfied."*

Structure the walk-through as four H2 sections mirroring the rubric:

1. **`## Scope — applied to this rubric`** — Walk through Jones's three conditions as they apply to the rubric itself as an artefact:
   - 90%+ unrescued: a reader applying the rubric to a proposed skill reaches a judgement without requiring outside intervention the majority of the time. The judgement may be "needs more reflection" — that is a valid, unrescued outcome, not a failure.
   - Bounded, auditable, and reversible: the rubric's claims are all attributable to source quotations in `absencejudgement-citations.md`; auditability is direct. The rubric is markdown, reversible via git revert.
   - Human decides rollback: no automation surfaces the rubric's outputs; a human reads it and applies it. No cron can trigger a "roll forward" on a rubric verdict.
   State the judgement: the rubric passes Scope — by construction.

2. **`## Observability — applied to this rubric`** — Walk through the three screens on the rubric:
   - Form-gate: the rubric is a checklist (actor = reader, action = apply each screen). Passes.
   - Tautology-screen: could the rubric claim to be applied correctly without any useful judgement? **This is the reflective pinch-point — acknowledge it.** A reader could rubber-stamp each section without genuine engagement. The rubric is vulnerable to its own Screen 2. Document this explicitly. Mitigation: the Process section (Schön) is irreducibly reflective and resists rubber-stamping; the tautology-screen applies to *operational claims*, and Process is not operational. This is the coherence-check Brian named in AC4.5 — the rubric's Observability and Process sections are intentionally non-identical in form.
   - Named-falsifier: the rubric names its falsifier as "the human applying it"; there is no unnamed "system" or passive construction.
   State the judgement: the rubric passes Observability *with an explicit honesty-note about the tautology vulnerability in Screen 2*. That honesty-note IS the rubric's opening memento made concrete.

3. **`## Process — applied to this rubric`** — Walk through Schön's four questions asked OF the rubric:
   - *Can I solve the problem I have set?* — The rubric's problem is "prevent skill-authoring from substituting textual authority for evidence." The rubric can demonstrably screen out artefact-only DoD ("X committed") and modifier-only DoD ("terse, production-ready"). It can't demonstrably screen out subtle technoscholasticism. Answer: partially — the rubric is a partial solution, and that is the correct scope (AbsenceJudgement argues no rubric can fully solve this for LLMs).
   - *Do I like what I get when I solve this problem?* — Apply rubric to a toy DoD, judge output. The expected answer for the walk-through: yes, the output is a named failure mode or a named pass, not a vibe.
   - *Have I made the situation coherent?* — The rubric's four sections cohere: Scope bounds what's under review; Observability screens its falsifiability; Process asks whether the reflection is real; Failure-pattern catches residual drift. Each section has a distinct job.
   - *Have I kept inquiry moving?* — Applying the rubric should produce the next question (e.g., "should this scope be narrower?") not close the inquiry. If a reader ever experiences the rubric closing inquiry, that IS the rubric failing its own Schön screen. Document this as the rubric's primary failure mode.

4. **`## Failure-pattern screen — applied to this rubric`** — Walk through the four failure patterns as applied to the rubric:
   - Temporality blindness: the rubric cites 2025 sources and 1994/1987/1999 sources. The rubric does not assume its sources are eternal. A future revision must re-verify citations against the then-current AbsenceJudgement version. Pass, with documented staleness risk.
   - Scope/confabulation: the rubric's scope is narrow (four screens for one kind of artefact). Claims stay within that scope. Pass.
   - Stamp-collecting without evaluation: the rubric explicitly separates Observability (the screen) from Process (the evaluation). If a reader stamp-collects (ticks each screen without judgement), the rubric fails — but the failure is diagnosable via the Process section. Pass, with a named vulnerability.
   - Vibes-based operation: the rubric names its sources, line numbers, and secondary sources. A rubric verdict tied to a named screen is not a vibe. Pass.

5. **`## Closing coherence note`** — Two or three sentences: the rubric passes its own screens, with two explicitly-named honesty-notes (the Observability tautology vulnerability and the Process "primary failure mode"). Those honesty-notes are the rubric's first act of epistemic humility — acknowledging that the rubric, like the AI applying it, cannot fully solve what it addresses.

**Consumer-tracing:** SKILL.md's "Self-application pointer" section consumes this file. Phase 1's Task 4 (verification) and Phase 5's cross-reference audit confirm the pointer resolves.

**Step 2: Verify the four rubric sections appear in the walk-through**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/epistemic-humility/self-application.md') as f:
    content = f.read()
required_headings = ['## Scope', '## Observability', '## Process', '## Failure-pattern']
missing = [h for h in required_headings if h not in content]
assert not missing, f'missing H2 sections: {missing}'
# All four rubric sections should appear in the walk-through so coherence is inspectable
honesty_markers = ['honesty', 'tautology', 'vulnerab']
found_honesty = any(m in content.lower() for m in honesty_markers)
assert found_honesty, 'walk-through must surface at least one reflective vulnerability (AC4.5 H4 revision: walk-through + vulnerability-surfacing, not pass/fail)'
print('self-application walk-through structurally valid')
"
```
Expected: `self-application walk-through structurally valid`.

**Step 3: Commit**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git add plugins/denubis-extending-claude/skills/epistemic-humility/self-application.md
git commit -m "feat(epistemic-humility): add rubric self-application walk-through

Demonstrates rubric coherence by applying each section to the rubric
itself. Explicitly names two reflective vulnerabilities (Observability
tautology screen, Process 'primary failure mode') per AC4.5 — coherence
check, not mechanical pass."
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_TASK_4 -->
### Task 4: Phase-level verification and audit

**Verifies:** skill-skills-upstream-sync.AC4.4 (final grep-audit), cross-checks of skill-skills-upstream-sync.AC4.1-AC4.3 against the three files produced by Tasks 1-3

**Files:**
- No new files. This task runs audit commands against the three files written in Tasks 1-3 and commits only if audits pass.

**Step 1: Fabricated-codes grep-audit (AC4.4)**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
# Word-boundary search for all nine fabricated codes across the skill directory.
# Expected: zero hits OUTSIDE the explicit rejection context in SKILL.md.
for code in TEMP RAND SCOP VIBE FABR MECH MTCH SCAF BOUN; do
    echo "=== $code ==="
    grep -Hn -w "$code" plugins/denubis-extending-claude/skills/epistemic-humility/ -r || echo "  (zero hits)"
done
```

Expected: each code reports either `(zero hits)` OR a small number of hits *all* within SKILL.md's "Note on fabricated taxonomy" section (the explicit rejection context permitted by AC4.4). Any hit in `absencejudgement-citations.md` or `self-application.md` is a DR4 violation — halt and rewrite.

**Step 2: Cross-reference presence check**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins && python3 -c "
with open('plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md') as f:
    skill = f.read()
# These three cross-refs are deferred-resolve; their TARGETS are authored in Phases 2-4.
# This task only checks that SKILL.md *names* them.
expected_refs = [
    'denubis-extending-claude:writing-skills',
    'denubis-extending-claude:testing-skills-with-subagents',
    'denubis-extending-claude:writing-claude-directives',
]
missing = [r for r in expected_refs if r not in skill]
assert not missing, f'SKILL.md missing forward cross-references: {missing}'
# Self-application pointer and citations pointer must be present
assert 'self-application.md' in skill, 'SKILL.md missing self-application.md pointer'
assert 'absencejudgement-citations.md' in skill, 'SKILL.md missing absencejudgement-citations.md pointer'
print('cross-references named (forward-targets resolved by Phases 2-4; supporting-file pointers intra-phase)')
"
```
Expected: `cross-references named (forward-targets resolved by Phases 2-4; supporting-file pointers intra-phase)`.

**Step 3: File-set completeness check**

Run:
```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
ls -1 plugins/denubis-extending-claude/skills/epistemic-humility/
```

Expected (exactly three files):
```
SKILL.md
absencejudgement-citations.md
self-application.md
```

If any file is missing, the corresponding task is not complete.

**Step 4: Final commit (audit log)**

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
# Record audit pass in a one-line commit so CI/reviewers can see the checkpoint.
# If nothing to commit (no changes), skip — this is a dry commit for audit only.
git log -1 --pretty=format:"%h %s" -- plugins/denubis-extending-claude/skills/epistemic-humility/
```

If the last three commits from Tasks 1-3 already capture the skill, Task 4 does not produce a new commit. Record the audit results in the phase-completion notes instead (no file changes to commit).

**Consumer-tracing for Task 4:** This task's verification output is consumed by Phase 5's cross-reference audit (Task 5B's investigator will re-run the fabricated-codes grep across the full plugin) and by the Finalization code-reviewer.
<!-- END_TASK_4 -->

---

## Done when (phase-level)

- [ ] `plugins/denubis-extending-claude/skills/epistemic-humility/SKILL.md` exists, frontmatter validates, four rubric H2 sections present in design order (Task 1 Steps 3-4)
- [ ] `absencejudgement-citations.md` present with all required line-number references and all required verbatim phrases (Task 2 Steps 2-3)
- [ ] `self-application.md` present with four H2 walk-through sections and at least one explicit honesty-note (Task 3 Step 2)
- [ ] Fabricated-codes grep-audit (TEMP/RAND/SCOP/VIBE/FABR/MECH/MTCH/SCAF/BOUN) returns zero hits outside SKILL.md's explicit rejection context (Task 4 Step 1)
- [ ] Forward cross-references to Phases 2-4's orchestrators are named in SKILL.md (Task 4 Step 2)
- [ ] File-set is exactly three files (Task 4 Step 3)
- [ ] Three commits land on branch (one per Task 1-3; Task 4 is audit-only, produces no new commit)

**Not in scope for Phase 1:**
- Resolving the forward cross-references (Phases 2-4 author the targets)
- Wiring the rubric-callback sections into orchestrators (Phases 2-4)
- Version-bumping the plugin manifest (Phase 5)
