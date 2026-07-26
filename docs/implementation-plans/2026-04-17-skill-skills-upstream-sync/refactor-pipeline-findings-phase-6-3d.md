# §3d Refactor-Pipeline Findings — Phase 6 (impl-plan-write/SKILL.md)

**Date:** 2026-07-07
**Step:** `executing-an-implementation-plan` §3d (post-phase refactor pipeline), Phase 6 gate.
**Target:** `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (1474 lines, Markdown prose).
**Reviewer:** Fable-5, read-only (operator re-authorised Fable 2026-07-07: "any work we can do with fable is probably a good idea").

## Why a prose pass, not the code pipeline

§3d's measurement stage is code tooling: `complexipy` (Python cyclomatic complexity — not installed here, and `.py`-only) and `ast-grep` (needs a code language). Against a Markdown prose skill the measurement collapses to `wc -l` (1474 lines, ~60 headings), and the Måntylä smell taxonomy (long method, feature envy, …) does not map to prose. The refactoring-executor stage is an active hazard here: told to "reduce duplication" it would try to consolidate the three anti-smuggling rule copies (742/911/1444), which are **test-locked** (any edit triggers mandatory E1–E12 re-validation, carry-forward 2) and already dispositioned as intentional (Minor-2, `code-review-findings-phase-6-coherence-gate-close.md`).

Operator decision (2026-07-07): substitute a **read-only Fable prose-structure pass** for the code pipeline — editorial smells only (navigability, bloat, redundancy beyond the accepted triple, terminology drift, dead pointers), **no executor**, findings dispositioned one-by-one.

## Provenance gate (Fable is a non-Opus voice — verify before believing)

Verified against the file: **m1** trigger (1471), **m2** dead ref (938), and **M1**'s drift (the dropped bullet present at 547/814, absent from the batch copy) all confirmed verbatim. One overstatement flagged: **M2**'s literal "not one #-heading between 675–943" is false — 5 heading lines exist, but 4 are `### DR1–DR4` output-template examples, so the *substance* (the design-decisions doctrine block lacks structural subheadings) holds. Not a confabulation; the report is trustworthy.

## Findings and dispositions

### Fixed now — verified residuals/typos, no restructure, no locked wording — commit `9cad6da`

- **m1 (trigger half) — handoff trigger stale.** Line 1471 read "After UAT Requirements collation completes, announce: …complete and validated…". The gate-close reorder (`5e3e72f`) moved Finalization to last (1467 → 1341), so the trigger fired one step early, announcing "validated" before the validation task runs. → "After Finalization completes (existence gate passed), announce:". Codex's final pass grepped the `Proceed to…` pointers and missed the `After … completes` phrasing; the internal sweeps did too. A real residual the reorder shipped ~90% done.
- **m2 — dead section reference.** Line 938 "(see UAT Requirements Generation below)" named a nonexistent section → "(see UAT Requirements Collation below)".
- **n5 / M1-drift — batch branch dropped a bullet.** The batch-mode Task NC step (652) had lost "- Document findings for inclusion in phase output", present in the interactive (547) and design-decisions (814) copies. Restored. (The concrete instance of the M1 triplication-drift mechanism.)

### Deferred — impl-plan-write structural refactor (distinct work item; see "Deferral home" below)

- **M1 (Major) — per-phase steps 1–3 triplicated ×3.** Interactive (516–549), batch (625–657), design-decisions (783–816) repeat steps 1–3 (~35 lines) near-verbatim; the branches differ only from step 4 onward. A future edit to the structural-readiness query or preparatory-refactor protocol must touch three sites, and the batch copy already drifted (the n5 bullet, now fixed). Fix = hoist steps 1–3 into one "all modes" subsection opened before the branch split; or, if inline-per-branch completeness is wanted, add "MIRRORED ×3 — edit all three" maintenance markers. Real restructure; **no locked wording**. Distinct from the accepted anti-smuggling triple (that has three distinct read-contexts + a re-validation lock; this has identical read-context and no lock).
- **M2 (Major) — design-decisions doctrine block (675–816) lacks structural subheadings.** Navigated only by bold pseudo-headings; remote sections point in via soft anchors ("the rubric-maintenance note under the Disagreement test" at 902/1457, where "Disagreement test" is a numbered list item, not a heading). Fix = promote the bold pseudo-headings to `####`. **HAZARD:** sits immediately adjacent to test-locked wording (730–742); heading-only promotion *around* the locked text should still get a cheap E1–E12 re-validation, in case maintainers read the "any edit" mandate as covering adjacent structure.
- **m3 (Minor) — stamp template duplicated in two sites (~1326 gate, 1464 write); attestation-not-proof in three (1332/1461/1467).** If the two full stamp templates drift, the first-line grep (1337) still passes but the documented formats disagree. Fix = one canonical stamp-FORMAT site (the collation write step, 1461–1466), and have the Finalization gate reference it rather than restate. Load-bearing gate prose (not locked) — change with care.

### Deferred — optional polish (fold into the same structural pass, or drop)

- **m4** — mode nicknames ("batch mode" etc.) used from 1083 on but never bound to the option strings at 58–63. Cheap: tag each option with its nickname at declaration.
- **m6** — "### Worked Examples" (945) sits at the same heading level as the three mode branches, reading as a fourth mode; "worked example" also names two different blocks (762 vs 945). Rename/relocate to scope it to the design-decisions branch it illustrates.
- **m7** — no roadmap for a 1474-line doc; add a 6–8 line spine to the Overview (highest-leverage of the polish set for post-compaction re-entry).

### Accepted — no action

- **m1 (physical-order half)** — the Finalization section (1214) physically precedes Test Req (1343) / UAT (1393) despite running after them; the signposts at 1218 ("both below") and 1467 ("section above") make it navigable. Physically relocating a ~120-line section is a larger edit with its own risk; the signposts suffice.
- **m5** — maintenance breadcrumbs (M6, AC6.7, the 497-min figure, adversarial dates) interleaved with operator instructions. Partly intentional audit-trail; the annotations at 738/742 sit inside/adjacent to locked wording and must not be touched. Accept.
- **n1–n4** — cosmetic.
- **Terminology / dead-pointer / bloat sweeps beyond the above** — Fable found no further actionable items: all other internal references resolve with correct direction (251→355, 902→1393, 1321→1393, 1467→1214, 986→209), tracked-task names are verbatim-consistent, and the 43-row Common Rationalizations table is compliance armour, not bloat.

## Deferral home

The operator's disposition was "fold the substantive restructures into task #7." On inspection, task #7 (`phase_04_true_up_sweep.md`, the obra-import work item) targets *different* skills (`writing-claude-directives`, `testing-skills-with-subagents`) and is a content-import, not a structural refactor of impl-plan-write. To keep task #7's scope clean, the deferred **M1 / M2 / m3** (plus optional m4 / m6 / m7) are recorded here as a **distinct** deferred work item — "impl-plan-write structural refactor" — cross-linked from the task-#7 entry in `phase_04_true_up_sweep.md` rather than merged into it. If this pass and the obra-import passes are done together, the M2 heading work shares their E1–E12-adjacency discipline (edits near locked wording re-run the fixture before shipping).
