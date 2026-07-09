# Smell Assessment Report

## Phase: Phase 4 — Rewrite `writing-skills` as Cornerstone Orchestrator
## Files Assessed: 3 files, 379 lines
## Date: 2026-07-06
## Framing: post-phase (holistic Mantyla taxonomy)

## Preamble — File-Type Caveat

All three files are Markdown skill-authoring documents, not executable code:

- `writing-skills/SKILL.md` (152 lines) — cornerstone orchestrator
- `writing-skills/README.md` (29 lines) — supporting-files note
- `writing-skills/examples/CLAUDE_MD_TESTING.md` (198 lines) — worked example (obra-authored body preserved verbatim; only denubis frontmatter + top note are denubis-owned)

The mechanical toolchain therefore returned nothing usable: complexipy found no functions to parse (it reported a parse error per file, which is expected for Markdown), and all four ast-grep structural rules matched zero nodes. Tier 2 was assessed by LLM reasoning against genuine documentation smells (duplication under Rule of Three, tangled/oversized sections, dead cross-references, accretion). Per the orchestrator's instruction, code-only refactoring patterns were not translated onto prose where they do not apply, and a near-empty result is the expected outcome.

## Complexity Measurements

### complexipy (cognitive complexity >15)
All functions below threshold — N/A. complexipy reported "No files were found with functions" and a parse error for each Markdown file. No Long Method signal is derivable from Markdown.

### Line Counts
| File | Lines | >400? | Design target |
|------|-------|-------|---------------|
| SKILL.md | 152 | No | ≤250 (AC1.2); ~150–200 (Phase 4 goal) — within target |
| README.md | 29 | No | n/a |
| examples/CLAUDE_MD_TESTING.md | 198 | No | n/a |

No file exceeds the 400-line Large Class threshold. SKILL.md sits comfortably inside the design's thin-orchestrator envelope.

### Structural Smells (ast-grep)
| Rule | Result |
|------|--------|
| fcis-violation | `[]` — no matches |
| global-mutable-state | `[]` — no matches |
| long-parameter-list | `[]` — no matches |
| nesting-depth | `[]` — no matches |

No structural smells detected. (All four rules target code constructs absent from Markdown; empty is expected, not evidence of cleanliness in the code sense.)

## Findings

### Bloaters
No findings in this category. No section is oversized or tangled; the longest SKILL.md section (the Skill Creation Checklist, ~30 lines) is a flat bulleted list. Primitive Obsession / Data Clumps are code-only and do not apply to prose.

### Object-Orientation Abusers
No findings in this category. Switch Statements, Refused Bequest, Alternative Classes, and Temporary Field are object-orientation constructs with no analogue in these documents.

### Change Preventers
Tier 3, deferred — not assessed in a single-phase run (see Deferred section).

### Dispensables
No findings in this category. Details of what was checked and why nothing rose to a reportable finding are in "No Action Needed" and "Below Threshold" below. The most material check — dead cross-references (a Dead Code analogue for documentation) — was run against disk and came back clean.

### Couplers
No findings in this category. Feature Envy, Inappropriate Intimacy, Message Chains, and Middle Man are code-coupling smells with no analogue here. The one documentation analogue worth noting — SKILL.md's "Supporting Files" section (lines 107–113) overlapping README.md — is intentional progressive disclosure: SKILL.md gives one-line pointers and explicitly delegates detail to README.md ("See `README.md` for dependencies and invocation", line 109). This is the designed delegation, not Inappropriate Intimacy.

## No Action Needed

Categories assessed with no findings:

- **Bloaters (size/complexity):** Assessed SKILL.md (152 lines, within the ≤250 design target), README.md (29), and CLAUDE_MD_TESTING.md (198) for oversized files and tangled sections. All within target; no section runs long or interleaves unrelated concerns.
- **Dispensables — Dead Code / dead cross-references:** Verified on disk that every skill cross-reference and every supporting-file reference resolves. Sibling skills `epistemic-humility`, `writing-claude-directives`, and `testing-skills-with-subagents` all exist with a `SKILL.md`. Supporting files `anthropic-best-practices.md`, `render-graphs.js`, `examples/CLAUDE_MD_TESTING.md`, and `README.md` all exist. No dangling reference. Design AC1.3 / AC1.4 hold as observed at assessment time.
- **Dispensables — Speculative Generality:** Cross-checked SKILL.md's sections and references against design-plan Phase 4 (component list, line 373). Every section (Core Principle, TDD Mapping, When to Create, Skill Types, Directory Structure, Template, Workflow, Supporting Files, Anti-Patterns, Checklist) and every sub-skill reference is called for by the design. No abstraction exists ahead of a caller.
- **Dispensables — Accretion (Layercake):** The design's explicit thrust is consolidation. CLAUDE_MD_TESTING.md's frontmatter records that an earlier duplicate copy was merged and deleted (2026-07-05 consolidation) — the opposite of accretion. No coexisting old/new solutions to the same problem were found.
- **Object-Orientation Abusers & Couplers (code smells):** Assessed for applicability; these are class/method-level constructs with no analogue in skill-authoring Markdown.

## Below Threshold

Logged per the Rule-of-Three gate (Part 4 of the rubric) and the Speculative-Generality design-exemption — observed, but not rising to a reportable finding:

- **Near-verbatim restatement of the Core Principle (2 instances — below Rule of Three).** "Writing skills IS Test-Driven Development applied to process documentation" appears at line 9 (overview paragraph) and again at line 13 (Core Principle heading body); "Iron Law: no skill without a failing test first" likewise appears at line 9 and line 17. Two instances each, within ~8 lines. Below the 3-instance gate, so not reported. The overview-then-anchor repetition is also a legitimate skill-authoring affordance: line 9 is the description-adjacent skim surface, the Core Principle section is the in-body anchor. Noted only for the author's awareness; no action prescribed.
- **epistemic-humility rubric callback repeated across three sections (3 instances — gate condition 3 not met, and design-exempt).** The instruction "run the artefact through `denubis-extending-claude:epistemic-humility`; if it fails Scope / Observability / Process / Failure-pattern, re-scope rather than author" appears at line 42 (When to Create a Skill), lines 101–102 (Workflow step 1), and lines 129–130 (Checklist, Scope). This meets the 3-instance count but fails Rule-of-Three condition 3 (extraction would yield no meaningful abstraction beyond what the document structure already provides) and is affirmatively called for by the design plan, which specifies the rubric callback in the When-to-Create, Workflow, and Checklist sections separately (Phase 4 component list). A checklist that restates its workflow's actions as checkable items is the intended affordance, not accidental duplication. Not reported as Duplicate Code.

## Scope Note — obra-authored content excluded from prescription

Per the assessment constraint, `examples/CLAUDE_MD_TESTING.md`'s scenario/variant body is obra-authored and deliberately preserved verbatim; only its denubis frontmatter and top note are denubis-owned. That file's body was read for context (dead-reference and consolidation checks) but was not assessed for prose smells or offered any prescription. Its denubis-owned frontmatter/top-note carry the consolidation provenance and the doctrinal caveat cleanly and produced no finding.

## Deferred (Tier 3)

Smells requiring cross-file, cross-module, or historical analysis (not assessed in this single-phase run):

- Shotgun Surgery — requires git history
- Divergent Change — requires change-frequency analysis
- Parallel Inheritance — requires cross-hierarchy analysis
- Insider Trading — requires cross-module dependency analysis
- Mysterious Name — requires cross-file usage context
- Cross-file Duplication — requires cross-file structural comparison
- God Module — requires full-module cohesion analysis

Note: a cross-file duplication pass (Tier 3) between `writing-skills/SKILL.md` and the three sibling SKILL.md files it orchestrates, and between SKILL.md's "Supporting Files" section and README.md, would be the natural next check if orchestrator/sub-skill redundancy is a concern. Within-file assessment found the SKILL.md↔README.md overlap to be intended delegation, not duplication.

## Summary

- **Total findings:** 0
- **By grade:** Demonstrated: 0, Plausible: 0, Possible: 0
- **By category:** Bloaters: 0, Object-Orientation Abusers: 0, Dispensables: 0, Couplers: 0
- **Below threshold (logged, not reported):** 2
- **Assessment outcome:** Clean. The Phase 4 rewrite meets its thin-orchestrator size target, all cross-references resolve on disk, no section is oversized or tangled, and the only repetition present is either below the Rule-of-Three gate or a design-called-for checklist/workflow affordance. This near-empty result is the expected and correct outcome for well-formed skill-authoring Markdown; no findings were manufactured to fill the report.
