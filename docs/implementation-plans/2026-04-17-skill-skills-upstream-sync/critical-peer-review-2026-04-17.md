# Critical Peer Review — Skill-Skills Upstream Sync Implementation Plan

**Reviewer:** denubis-plan-and-execute:critical-peer-review (Opus 4.7, 1M context)
**Date:** 2026-04-17
**Verdict:** NEEDS REVISION
**Findings:** 7 HIGH + 6 MEDIUM + 4 LOW

Session halted per user direction after this review. Revision pass deferred to next session.

---

## Core structural finding

The plan applies Phase 6-style anti-smuggling standards (rubric-as-text must become gate-as-forcing-function) to impl-plan-write while the plan's own gates are themselves rubric-as-text. Self-refuting under adversarial reading. The pattern is:

| Plan's gate | Plan's enforcement | Honest reading |
|---|---|---|
| RED precedent "binary gate" (Phases 2/3/4) | Author commits a file claiming they have a transcript | Self-report, no independent verification |
| Rubric self-application "passes" | Author writes a coherence walk-through | Prose written by the same author |
| "Phase 4 IS integration evidence" | Commit history should "tell the same story" as narrative | No specified audit procedure; DR-P4-INT-1 itself admits this |
| AC6.4 forward-enforcement | Bash script documented inside impl-plan-write markdown | Never runs unless manually extracted |

This pattern is the structural through-line of findings H2, H3, H4, H7, M2, and M6.

---

## HIGH findings (7)

### H1. OVERCLAIM / INCONSISTENCY — `denubis-plan-and-execute` version in plan is wrong

Plan assumes current version is `2.28.1` and targets `2.29.0`. **Actual current version is `2.30.0`.** Correct target is likely `2.31.0`. Seven downstream pieces depend on the wrong number:
- `phase_05.md:43` (Codebase verified section)
- `phase_05.md:317` (Task 3 Step 1 edit instruction)
- `phase_05.md:328` (Task 3 Step 4 verification assertion)
- `phase_05.md:358` (commit message)
- `phase_05.md:366` (CHANGELOG template)
- `phase_05.md:378` (test summary)
- `test-requirements.md:290`
- `test-requirements.md:443`

Phase 5 Task 3 Step 4's assertion `assert plugin_version == mp_version == '2.29.0'` will FAIL at execution; worst case, an executor "fixes" by downgrading to `2.29.0` (regression).

### H2. RUBRIC-AS-TEXT — RED precedent "binary gate" is not structurally enforcing

Phases 2, 3, 4 claim a "binary gate — phase does not proceed without a transcript on file." Enforcement is that a file `phase_0N_red_precedent.md` must be committed. But:
- Same agent commits as decides what counts as a "transcript"
- No check that the file isn't empty, paraphrased, or filled with invented session IDs
- No verification that cited session IDs actually exist in cc-search-chats
- "Halt and surface to user" IS the gate — but the halting is self-reported

Locations: `phase_02.md:68-134`, `phase_03.md:63-107`, `phase_04.md:63-104`.

**Correction direction:** Either add a second agent that verifies cited session IDs resolve, OR require explicit user approval (AskUserQuestion) on the precedent file before Task 2 proceeds.

### H3. UNFALSIFIABLE — Phase 4 "integration evidence" claim

Phase 4 Task 6 Step 5 commits "This phase's production IS the integration evidence per design plan DoD" and the plan asserts this substitutes for an integration test. But:
- No concrete procedure for the commit-history-vs-narrative audit beyond "they should tell the same story"
- DR-P4-INT-1 itself admits "the written evidence can be perfect; the lived process can still have skipped"
- Phase 6 Task 5 assigns this entry to a Sonnet subagent, which has access to NEITHER the lived authoring process NOR the commit history by default

GRADE downgrade: Indirectness (proxy = narrative, not process) + Imprecision (no procedure) + Reporting bias.

**Correction direction:** Either (a) drop "Phase 4 IS integration evidence" and author a real integration test with behavioural predictions, OR (b) specify a concrete procedure (git log ordering checks, commit message content assertions, subagent transcript inclusion in GREEN verification).

### H4. RUBRIC-AS-TEXT — Rubric self-application "coherence check" is unfalsifiable pass-pass

Every Phase 2-4 requires "rubric self-application passes (coherence check)." AC4.5 codifies "passes when the rubric demonstrably probes the same question categories… NOT when every checkbox is mechanically satisfied." This means subsequent phases inherit unfalsifiability: a phase "passes" when the author writes a walk-through saying it coheres.

The plan's primary scope-check mechanism and its "integration verification" are both prose-self-reports.

**Correction direction:** Reframe "rubric self-application passes" as "walk-through written and committed; any named reflective vulnerabilities surfaced to the user for acknowledgement before GREEN." Remove pass/fail framing.

### H5. FALSE-WORLD-MODEL — "Task 28" doesn't exist in `impl-plan-write`

AC6.2 and Phase 6 throughout reference `"Task 28"` in impl-plan-write. **Grep for "Task 28" in impl-plan-write SKILL.md returns zero hits.** The actual section is `## UAT Requirements Collation` at line 1283; the tracked-task description is `"UAT Requirements: Collate uat-requirements.md from phase decisions"`.

Locations: `phase_06.md:23`, `phase_06.md:47`; design plan Phase 6 description.

**Correction direction:** Rename all "Task 28" references to `UAT Requirements Collation section` or cite by line number.

### H6. INCONSISTENCY — AC3.7 "every model-specific claim" but `long-running-state-patterns.md` exempted

AC3.7 says "**every** model-specific claim has an explicit model-version anchor." Phase 2 declares `long-running-state-patterns.md` "unchanged unless research surfaces updates — it did not." **Grep shows `Opus 4.5` at lines 114 and 132** of that file.

Strict reading: Phase 2 cannot complete AC3.7 without touching this file.

**Correction direction:** Expand Phase 2 scope to update `long-running-state-patterns.md` Opus 4.5 references, OR narrow AC3.7 to "SKILL.md" only.

### H7. INCONSISTENCY — DR-P4-INT-1 is subject of its own audit

Phase 6 Task 5 dispatches Sonnet to audit `uat-requirements.md`. DR-P4-INT-1 is in-scope. The entry asks whether the written record of Phase 4's authoring is faithful to lived process. The Sonnet subagent has access to NEITHER the lived process NOR the commit history by default.

The "Planner's pre-audit notes" at phase_06.md:647 literally predicts this: "If the audit FAILs, the remediation options are: rewrite to a cleaner surface judgment; delete and accept the DoD framing itself needs refinement." The planner acknowledges the entry may be structurally un-auditable.

**Correction direction:** Do not include DR-P4-INT-1 in the retroactive audit. Handle it as a design-level DoD concern: escalate at Phase 6 Task 5 kick-off whether "integration evidence" framing survives a good-faith audit. If not, delete the entry and drop the DoD clause.

---

## MEDIUM findings (6)

### M1. FALSE-WORLD-MODEL — `/tmp/superpowers-obra/` and `/tmp/anthropic-system-card.pdf` are transient

All obra imports and system-card references depend on `/tmp/superpowers-obra/...`. `/tmp` is cleared at reboot on most Linux distributions. No phase verifies clone presence as Step 0.

Locations: `phase_02.md:44-48`, `phase_03.md:45-47`, `phase_04.md:47-51`.

**Correction direction:** Add preflight step to verify `/tmp/superpowers-obra/` exists with `git -C /tmp/superpowers-obra status`; re-clone if absent. Document the upstream commit SHA used.

### M2. RUBRIC-AS-TEXT — `audit-uat-template-compliance.sh` is documented-but-never-run

AC6.4's enforcement is a bash script embedded inside `impl-plan-write/SKILL.md` as a fenced code block. Nothing runs it. Phase 6 Task 2 Step 4 verification is just `grep -q 'audit-uat-template-compliance'` — i.e., the script name is mentioned, not executed.

**Correction direction:** EITHER (a) move script to `scripts/audit-uat-template-compliance.sh` as a standalone file and wire into a hook/pre-commit, OR (b) accept AC6.4 is aspirational and downgrade "covered" status to "enforcement deferred."

### M3. OVERCLAIM — Phase 5 audit script `OBRA_SKIP` is a bet, not an inventory

Script skips `{testing-skills-with-subagents.md, persuasion-principles.md, writing-skills.md}` as presumed false-positives. No procedure verifies completeness. If obra references another sibling NOT on the list, audit FAILs on a non-issue. If a genuine bad reference happens to match a name on the list, audit PASSes a real broken reference.

**Correction direction:** Pre-scan to-be-imported obra files for all `filename.(md|js|dot)` references and derive `OBRA_SKIP` programmatically, OR narrow skip to exact `(md_path, filename)` tuples.

### M4. OVERCLAIM — Jones citation tier conflated with peer-reviewed sources

Design plan theoretical-spine statement lists "Popper / Lakatos / Haraway / Carnap … Schön 1994 p.132 … Jones's scope-lever" as "load-bearing, verified against sources." Jones is Nate Jones's Substack newsletter (not peer-reviewed). Plan flags this inside the citations file but not at top-level design-plan scope.

**Correction direction:** Add tier note to design plan: "Popper / Lakatos / Haraway / Carnap (peer-reviewed philosophy); Schön (peer-reviewed, Taylor & Francis); Jones (newsletter, treated as primary-source quotation inside AbsenceJudgement, not as independent authority)."

### M5. INCONSISTENCY — Phase 4 size target contradicts itself

Design plan line 26: "≤250 lines." Design plan line 122: "~150-200 lines target." AC1.2: "≤250." Phase 4 Task 2 Step 1: "Target ≤250 lines." Phase 4 Task 2 Step 3 asserts `len(lines) <= 250`.

**Correction direction:** Pick one number. Reconcile to ≤250 everywhere; amend design plan line 122.

### M6. RUBRIC-AS-TEXT — Phase 6 Step 6.5 gate blocks "step 7" but user can override at step 7

Step 6.5 says "Do NOT proceed to step 7 with smuggled entries." But step 7 is AskUserQuestion — the user approves. A user presented with a smuggled entry CAN approve it. The gate assumes the planner self-polices; it does not structurally prevent reaching the user.

**Correction direction:** Reframe step 6.5 as "pre-presentation self-audit" and make clear the structural gate is the collation-audit in Task 4, OR dispatch Sonnet subagent at 6.5 too.

---

## LOW findings (4)

### L1. `mkdir -p` doesn't verify parent skills/ directory exists

Phase 1 Step 1 creates the skill directory without verifying `plugins/denubis-extending-claude/skills/` exists first. If the plugin was renamed mid-flight, the skill lands in a directory that shouldn't exist but gets created.

### L2. `has_haiku_retirement = any([...])` logic accepts the retired phrase itself as "retirement documented"

Phase 2 Task 3 Step 3 verification has four alternative conditions. Three match the implementor's retirement-note authoring; one matches the old string the retirement is supposed to remove. A file containing `struggles with judgement` (the retired phrase) passes the check. Intent was to force the retirement note; implementation accepts either.

**Correction direction:** Require the retirement-note specifically (`'retired' in content.lower() and 'Haiku' in content`) — remove the arms that match the retired phrase.

### L3. Filename-ordering risk (phase_05.md runs before phase_06.md lexically)

Phase files sort as 01, 02, 02_5, 03, 04, 05, 06. Design says Phase 5 executes AFTER Phase 6 (coherent-set commit). Documentation states ordering; no structural enforcement.

### L4. Cross-reference audit treats backtick-quoted filenames as references

Obra-imported file `anthropic-best-practices.md` line 1027 contains `` `form_validation_rules.md` `` as illustrative filename. Audit script will flag this. `OBRA_SKIP` doesn't cover illustrative filenames in general.

---

## Verification performed by reviewer

- Read all 9 plan files + design plan in full
- Grepped for actual repo state:
  - `denubis-plan-and-execute/.claude-plugin/plugin.json` version = `2.30.0` (falsifies plan's 2.28.1)
  - `denubis-extending-claude/.claude-plugin/plugin.json` version = `1.7.0` (matches plan)
  - `"Task 28"` in `impl-plan-write/SKILL.md` = zero hits (falsifies H5)
  - `Opus 4.5` in `long-running-state-patterns.md` at lines 114, 132 (confirms H6)
  - `/tmp/superpowers-obra/` and `/tmp/anthropic-system-card.pdf` exist at review time
  - `AbsenceJudgement.tex` exists at cited path
  - `diff -q graphviz-conventions.dot` against obra: no output (byte-identical, as plan claims)
- Counted: `^### DR` in uat-requirements.md = 8 entries (matches plan)

---

## Reviewer's overall assessment (verbatim)

> The plan is 85% sound. The 15% that needs revision is load-bearing.

Specific blockers before execution:
1. H1 must be fixed — version number wrong. Full editing pass across phase_05.md + test-requirements.md + CHANGELOG template.
2. H5 must be fixed or AC re-grounded — "Task 28" references replaced with accurate section names.
3. H3 + H7 must be addressed together — either commit to "Phase 4 IS integration evidence" as a testable claim with procedure, OR drop it.
4. H2 + H4 should be acknowledged — reframe "binary gate" and "coherence check" language where enforcement is a promise.
5. H6 must be resolved — either scope AC3.7 narrowly or expand Phase 2.

The code-reviewer approval does not substitute for these findings. The code-reviewer's approval is surface-level; the plan's structural claims about its own falsifiability do not survive adversarial reading.

---

## Session state (2026-04-17)

Plan files on disk (seven phases + test-requirements + uat-requirements + this review):
- phase_01.md (35.3K)
- phase_02.md (33.1K, minus persuasion content)
- phase_02_5.md (9.3K, preparatory-refactor)
- phase_03.md (29.9K)
- phase_04.md (29.9K)
- phase_05.md (26.4K, **version numbers wrong per H1**)
- phase_06.md (33.3K, **Task 28 references wrong per H5**)
- test-requirements.md (with framing corrections for AC3.3/AC6.4)
- uat-requirements.md (8 entries; Phase 1's 4 are pre-gate-form, flagged for retroactive audit)
- critical-peer-review-2026-04-17.md (this file)

**Design plan amendments since original:**
- Phase 2.5 (preparatory-refactor) added
- Phase 6 (cross-plugin impl-plan-write hardening) added
- Persuasion-principles import dropped (denubis departs from obra)
- AC3.3/AC3.4 inverted to negative assertions
- AC5.7 cross-plugin version scope added
- AC6.1-AC6.8 added
- Additional Considerations: rubric-vs-gate discovery, persuasion-principles drop rationale, stratified-sampling follow-up, eyeball-N% out-of-scope flag

**Revision strategy (deferred to next session):**
User chose "Halt and escalate" over Path A (substantial revision), Path B (scope reduction), or Path C (hybrid). Next session should re-open this file, decide strategy, and apply fixes with fresh context.

**Applicable skills feedback memory updated:**
- `feedback_review-all-levels.md` saved to `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/` — all reviewer levels must be discussed; interrogate Minor/Flagged for false-world-model assumptions.
