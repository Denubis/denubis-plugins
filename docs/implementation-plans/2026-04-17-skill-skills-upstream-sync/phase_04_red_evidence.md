# Phase 4 RED Evidence — Static File-Shape Diff (Preventive Cornerstone Rewrite)

**Source:** File-read of current `plugins/denubis-extending-claude/skills/writing-skills/SKILL.md` (observed 2026-06-11).
**Restructure framing:** PREVENTIVE (not corrective), per the 2026-04-22 plan-amendment pass. No prior session has been observed failing at "being too wordy" or "missing sub-skill orchestration" in a cc-search-chats-addressable way — file shape is a structural observation, not a session-observable failure.
**Pre-rewrite commit SHA:** `76f437265c60ec271fecb69ed28c2182e6224719` (`git rev-parse HEAD` at observation time).
**Pre-rewrite SKILL.md blob SHA:** `cee2f068c111c6996f815a60b8a9037ea2d3b4da` (`git rev-parse HEAD:plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`).
**Pre-rewrite line count:** 163 (`wc -l plugins/denubis-extending-claude/skills/writing-skills/SKILL.md`).

A reviewer can reproduce the deficiency assessment two ways: by the blob SHA directly (`git cat-file -p cee2f068c111c6996f815a60b8a9037ea2d3b4da`), or by checking out the commit SHA and reading the file at that path.

## File-shape diff

### Current shape (pre-rewrite)

- **Line count:** 163.
- **H2 sections (document-level), 11 total:**
  1. `## Core Principle`
  2. `## TDD Mapping`
  3. `## When to Create a Skill`
  4. `## Skill Types`
  5. `## Directory Structure`
  6. `## SKILL.md Template`
  7. `## RED-GREEN-REFACTOR Cycle`
  8. `## Testing by Skill Type`
  9. `## Common Rationalizations to Block`
  10. `## Anti-Patterns`
  11. `## Skill Creation Checklist`
- **Enumeration note (reproducibility):** `grep -n '^## '` over the file returns 16 lines, not 11. Five of those matches (`## Overview`, `## When to Use`, `## Core Pattern`, `## Quick Reference`, `## Common Mistakes`) sit *inside* the fenced ```` ```markdown ```` block of `## SKILL.md Template` (lines 73-86); they are exemplar headings for the template, not sections of this file. The document-level count is 11, which matches the phase file's "Current file state (Phase 4B direct inspection)" note. (That note's prose says "14 H2 sections" but then lists 11; the 11-name list is correct. The "14" was a counting slip in the note, neither the 11 document-level H2s nor the 16 raw grep hits.)
- **Absent structural elements:**
  - Rubric callback to `epistemic-humility` (no reference to it anywhere; the "When to Create a Skill" section makes a scope decision with no rubric handoff).
  - `## Workflow` H2 sequencing the three sub-skills (the sub-skill references that exist — `writing-claude-directives` at line 9, `testing-skills-with-subagents` at line 110 — are inline prose pointers, not a first-class sequencing section).
  - `## Supporting Files` section for obra imports (no `anthropic-best-practices.md`, `render-graphs.js`, or `examples/CLAUDE_MD_TESTING.md` exist or are named).
  - Attribution scaffolding for imported content (none, because no imports exist yet).
  - Opening paragraph naming the three-sub-skill sequencing pattern (current opening is a single "REQUIRED BACKGROUND" line pointing only at `writing-claude-directives`).

### Target shape (post-rewrite)

- **Line count:** ≤250 (thin-orchestrator target; AC1.2). Small margin over the 200-line target in design DR5.
- **H2 sections (document-level), per Task 2 Step 1 ordering:**
  1. `## Core Principle` (keep Iron Law; consolidate)
  2. `## TDD Mapping` (keep table)
  3. `## When to Create a Skill` (**add rubric callback to `epistemic-humility`** per DR3)
  4. `## Skill Types` (Technique / Pattern / Reference; **Discipline added** per 2026-06-10 amendment item 4)
  5. `## Directory Structure` (update to show supporting-files + `examples/` pattern)
  6. `## SKILL.md Template` (keep inline per DR4)
  7. `## Workflow` (**NEW** per DR7 — sequences epistemic-humility -> writing-claude-directives -> testing-skills-with-subagents)
  8. `## Supporting Files` (**NEW** — documents the three obra imports)
  9. `## Anti-Patterns` (keep four)
  10. `## Skill Creation Checklist` (keep)
- **Present structural elements (the additions that close the diff):**
  - Rubric callback to `epistemic-humility` inside "When to Create a Skill".
  - `## Workflow` H2 sequencing all three sub-skills as first-class steps.
  - `## Supporting Files` H2 naming `anthropic-best-practices.md`, `render-graphs.js`, and `examples/CLAUDE_MD_TESTING.md`.
  - Attribution preserved for each obra import (source line in frontmatter or top-of-file).
- **Sections removed in the reshape:**
  - `## RED-GREEN-REFACTOR Cycle` (content now owned by `testing-skills-with-subagents`).
  - `## Testing by Skill Type` (subsumed by `testing-skills-with-subagents`'s model-tier + pressure-type coverage).
  - `## Common Rationalizations to Block` (removed per DR9 — duplicated in sub-skills).

**The diff between current-shape and target-shape IS the RED evidence.** The current file is 163 lines carrying the full TDD-for-skills spine inline (RED/GREEN/REFACTOR mechanics, rationalization tables, testing-by-type matrix); the target is a thin (≤250-line) cornerstone that sequences three sub-skills and pushes the heavy content down into them. The drift is from "self-contained TDD-for-skills doc" toward "sequencer," and the structural absences (no rubric callback, no Workflow H2, no Supporting Files section) are the measurable gap.

## How Phase 4 addresses the deficiency

- **Task 2** rewrites `SKILL.md` as a thin cornerstone orchestrator (adds Workflow H2, Supporting Files H2, rubric callback; removes the three subsumed sections).
- **Tasks 3-5** import the obra supporting files verbatim (or light-touch) with attribution, populating the Supporting Files section's targets.
- **Task 6** verifies via a synthetic GREEN pressure scenario (four-check sequencing) and an `epistemic-humility` rubric self-application walk-through.

## Why this is NOT session-transcript RED

The deficiency is architectural, not behavioural. Sessions have used the current `writing-skills/SKILL.md` to author skills without failing in a transcript-quotable way — but the output shape has drifted from what a thin cornerstone should be. The rewrite is preventive hygiene. The fact that no prior session has failed at "being too wordy" is itself evidence the deficiency is structural/architectural, not behavioural.

This mirrors the H3-revision precedent that dropped Phase 4's earlier "production IS integration evidence" claim as unfalsifiable, and it mirrors Phase 2's amendment (static evidence accepted as RED). Phase 3's RED-gate stays corrective because its target methodology is transcript-sourcing; Phase 2 and Phase 4 accept static evidence as RED. The observable downstream effectiveness check for Phase 4 is the GREEN pressure scenario at Task 6, with the retrospective coherence audit at Phase 5 Task 4.5 (frustration-signal audit, AC5.8).

## Qualifying-criteria checklist (recorded per 2026-06-11 resume-prompt requirement)

The Conversation-Precedent Protocol's qualifying-criteria checklist (see the RED phase of `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`) governs RED evidence that *claims a conversation precedent*. This RED evidence claims **no** conversation precedent: it is a static file-shape observation produced under the 2026-04-22 plan-amendment pass. Therefore each of the five checklist items is **N/A**, recorded individually below with the reason grounded in the static framing. This is not a claim that the checklist passed — it is a record that it does not apply, and why.

1. **Observed-not-described** — N/A. There is no observed conversation failure to qualify; the evidence is a static read of file shape (line count, H2 enumeration, structural absences) against the design target, not a transcript of behaviour.
2. **Recorded independence argument** (the failing session is not this executor) — N/A. No session is cited at all, so there is no session whose independence from this executor could be argued or recorded.
3. **In-scope** (the failure exercises the skill under test) — N/A. No failure episode is invoked; the deficiency is the gap between current and target file shape, which is a design-conformance measurement rather than a scoped behavioural failure.
4. **Externally confirmed** (reproducible by a reviewer re-running the source) — N/A *as a conversation re-run*. Reproducibility here is structural, not transcript-based: a reviewer reproduces by diffing current-vs-target line count and H2 shape against the recorded blob SHA `cee2f068c111c6996f815a60b8a9037ea2d3b4da`. That path is documented above; the checklist's "re-run the conversation source" sense does not apply.
5. **Not self-licensing** (the evidence is not the author asserting the skill already works) — N/A. The checklist item guards against a conversation precedent that merely rationalises the skill; no conversation precedent is asserted, so there is nothing self-licensing to guard against. The preventive-not-corrective framing is recorded openly rather than used to license skipping a corrective gate.
