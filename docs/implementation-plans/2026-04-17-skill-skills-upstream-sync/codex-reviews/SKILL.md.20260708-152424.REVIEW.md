# Critical Peer Review: SKILL.md

Reviewer: Codex critical peer reviewer  
Date: 2026-07-08  
Document reviewed: context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md

## Hidden Assumptions

1. The plan writer can maintain a consistent UAT lifecycle across per-phase planning, collation, stamping, finalization, and execution routing. Evidence status: weakened by internal contradiction between per-phase append and later stamped collation write.

2. The triplicated per-mode workflow is acceptable because each mode must be self-contained. Evidence status: partially unsupported. The branch’s own refactor-pipeline record says the triplication already drifted once and is deferred structural work.

3. The anti-smuggling gate is evidence-backed and honestly bounded. Evidence status: supported for disclosed-oracle categories. The adversarial record says “Round 5 matched expectations 12/12,” but also states “all verdicts come from a single model at a single temperature” and every fixture disclosed its oracle.

4. A 1475-line single-file skill remains usable and compliant with skill-authoring protocols. Evidence status: weakened. The authoring skill says “Separate files for: Heavy reference (100+ lines), reusable tools/scripts, worked examples,” while the target directory contains only `SKILL.md`.

## ACH Matrix

| Evidence | H1: target is ready | H2: UAT lifecycle inconsistency remains | H3: structural maintainability issue remains | H4: authoring-protocol issue remains |
|---|---:|---:|---:|---:|
| Target says “Append all human-judgment falsification entries from this phase's decisions to `uat-requirements.md`” | − | + | ? | ? |
| Target later says “Before writing `uat-requirements.md` to disk” run collation audit and first-line stamp | − | + | ? | ? |
| Target repeats Task NB/NC in three branches at lines 521/630/789 and 543/652/811 | − | ? | + | ? |
| Refactor record says “per-phase steps 1–3 triplicated ×3” and “batch copy already drifted” | − | ? | + | ? |
| Adversarial record says “Round 5 matched expectations 12/12” | + | ? | ? | + |
| `wc -l` says target has 1475 lines and `find` says only `SKILL.md` exists | − | ? | + | + |
| Writing-skills says “Separate files for: Heavy reference (100+ lines), reusable tools/scripts, worked examples.” | − | ? | ? | + |

Decision rule: H2 has the strongest direct contradiction; H3 is independently corroborated by both target repetition and the branch’s own deferred finding; H4 is supported but less immediately execution-breaking because some inline duplication is intentionally test-locked.

## Findings

### High (count: 1)

- **Issue**: UAT entries have two incompatible write paths: per-phase append versus post-phase collation write with a first-line audit stamp.
  **Evidence**: The design-decisions mode tells Task ND to write UAT material during each phase: “**Persist Popper UAT entries:** Append all human-judgment falsification entries from this phase's decisions to `uat-requirements.md` (see UAT Requirements Collation below).” It later defines the tracked collation task as the point where the file is audited and written: “Before writing `uat-requirements.md` to disk, dispatch a subagent” and “Write to `[PLAN_DIR]/uat-requirements.md`. The **first line** must be the collation-audit provenance stamp”. The finalization gate depends on that stamped file: “Finalization cannot complete until `uat-requirements.md` exists at `[PLAN_DIR]/uat-requirements.md` **and carries the collation-audit provenance stamp**”.
  **GRADE factors**: Demonstrated internal inconsistency. No production-path run needed; the contradictory instructions are in the target itself.
  **Ripple**: A planner following line 939 literally may create or append an unstamped `uat-requirements.md` before the collation audit. A later collation write may overwrite, duplicate, or trust stale entries. The execution skill routes phases by reading `uat-requirements.md`: “Read `uat-requirements.md` in the implementation plan directory. Check whether this phase has any entries under its `## Phase [N]` section.”
  **Corrected language**: Replace per-phase “Append” with “Record approved human-judgment entries in memory or the task tracker for the UAT Requirements Collation task; do not write `uat-requirements.md` until the collation audit writes the stamped file.”
  **Location**: context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md:935, :939, :1322, :1439, :1462; context/plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md:599.

### Medium (count: 2)

- **Issue**: The section-3d refactor-pipeline handoff improved correctness but left the known triplication hazard in the main per-phase workflow.
  **Evidence**: The target repeats the same workflow block in all three modes: “2. **Task NB: Verify codebase state**” appears at lines 521, 630, and 789; “3. **Task NC: Research external dependencies** (if phase involves them)” appears at lines 543, 652, and 811. The branch’s own refactor-pipeline record identifies this as still deferred: “**M1 (Major) — per-phase steps 1–3 triplicated ×3.** Interactive (516–549), batch (625–657), design-decisions (783–816) repeat steps 1–3 (~35 lines) near-verbatim” and notes “the batch copy already drifted”.
  **GRADE factors**: Demonstrated duplication and demonstrated prior drift. The risk is maintainability, not immediate wrong execution.
  **Ripple**: Future edits to structural readiness, external-dependency research, or preparatory-refactor insertion must be synchronized across three blocks. The branch fixed one drift instance, but the mechanism remains.
  **Corrected language**: Hoist common steps NA/ NB/ NC into a single “All modes” subsection before the branch split, or add explicit “MIRRORED x3 — edit all three copies” markers at each copy.
  **Location**: context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md:521, :543, :630, :652, :789, :811; context/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/refactor-pipeline-findings-phase-6-3d.md:28.

- **Issue**: The target only partially follows the project’s skill-authoring protocol for large skills.
  **Evidence**: The authoring protocol says “**Separate files for:** Heavy reference (100+ lines), reusable tools/scripts, worked examples.” The target is 1475 lines (`wc -l`) and includes long worked examples under “### Worked Examples — smuggled entry, genuine entry, zero-UAT phase”. The skill directory contains only `context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`.
  **GRADE factors**: Moderate. The line count and single-file layout are demonstrated, but the best split boundary is a design judgment. Some inline repetition is intentionally test-locked, so this should not be fixed mechanically.
  **Ripple**: This worsens the target’s own usability for plan authors, especially after compaction. It also compounds the branch’s deferred “no roadmap for a 1474-line doc” note: “add a 6–8 line spine to the Overview”.
  **Corrected language**: Keep the mandatory execution-critical spine inline; move long worked examples and non-immediate reference material into supporting files, with routing instructions from `SKILL.md`. At minimum, add a short roadmap near the Overview.
  **Location**: context/plugins/denubis-extending-claude/skills/writing-skills/SKILL.md:67; context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md:946; context/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/refactor-pipeline-findings-phase-6-3d.md:36.

### Low (count: 0)

No low-severity findings.

## Verification

Commands actually run and relevant real output:

- `ls -R context`  
  Output included the target path: `context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`.

- `nl -ba context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md | sed -n '1,260p'`, then continuing ranges through line 1475.  
  Output confirmed the full target content and line numbers cited above.

- `sed -n '1,260p' REVIEW-METHOD.md` and `sed -n '261,520p' REVIEW-METHOD.md`  
  Output confirmed required review format and severity rubric.

- `rg -n 'Append all human-judgment|Collate them into a single file|Before writing `uat-requirements.md`|first line|already generated per-phase|Write to `\[PLAN_DIR\]/uat-requirements.md`|stamp' context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`  
  Output included lines 939, 1322, 1402, 1439, 1462, and 1468.

- `rg -n "Task NB: Verify codebase state|Structural readiness check|If the investigator reports impediments|Task NC: Research external dependencies|Document findings for inclusion" context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`  
  Output included repeated blocks at 521/529/536/543/547, 630/638/645/652/656, and 789/797/804/811/815.

- `wc -l context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`  
  Output: `1475 context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`.

- `find context/plugins/denubis-plan-and-execute/skills/impl-plan-write -maxdepth 2 -type f -print`  
  Output: `context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`.

- `rg -n "Task 28|UAT Requirements Generation|After UAT Requirements collation completes" context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`  
  Output: no matches, exit code 1.

- `git -C context diff -- context/plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md | sed -n '1,260p'`  
  Output began: `warning: Not a git repository. Use --no-index to compare two paths outside a working tree`.

## Strongest Hypothesis

The strongest hypothesis is that the UAT lifecycle still contains a real internal inconsistency. The target simultaneously instructs per-phase append and later audited first-line-stamped write; execution routing depends on the resulting file.

## Weakest Hypothesis

The weakest finding is the authoring-protocol split issue. The single-file size conflicts with the authoring guidance, but the exact split must respect deliberately repeated, test-locked instructions.

## Pre-Mortem

If this review is wrong, likely failure scenarios are:

1. “Append” at line 939 was intended conceptually, not as a disk write. The problem is then wording, not workflow.
2. The triplicated workflow is intentionally optimized for post-compaction local completeness, and maintainers accept the synchronization cost.
3. Splitting supporting files may make the skill less reliable because critical instructions become easier for agents to skip.

## Fastest Next Test

Run a fresh planning-session pressure test in design-decisions mode with two phases that each produce one UAT entry. Observe whether the planner writes/appends `uat-requirements.md` during Task ND or waits for the tracked UAT Requirements Collation task to write the stamped file.

## Overall Assessment

Needs revision. The branch materially improved the anti-smuggling gate and fixed dead references, but the UAT write lifecycle contradiction should be fixed before presenting this skill as ready. The triplication and large-single-file issues can be handled as follow-up structural work, but they are real residuals.