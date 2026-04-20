# Skill-Skills Upstream Sync — Phase 2.5: Preparatory Refactor of `testing-skills-with-subagents` RED Phase

**Goal:** Restructure `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` RED-phase internal subsections to separate **basic baseline checklist** from **synthetic pressure-scenario detail**. Enables Phase 3: *Restructure testing-skills-with-subagents* by making the conversation-precedent-protocol prepend (DR3) and the synthetic-scenario demotion to REFACTOR a clean in-place edit rather than a rewrite of a monolithic section.

**Architecture:** Single-file internal restructure. Behaviour preserved per Kent Beck's Two Hats discipline — refactoring hat only. No semantic change (RED still = baseline, REFACTOR still = completeness); only structural split within RED so the two *kinds* of content currently intermixed become addressable separately.

**Tech Stack:** Markdown. No runtime dependencies.

**Scope:** Preparatory phase inserted between Phase 2 and Phase 3 of 6 from `docs/design-plans/2026-04-17-skill-skills-upstream-sync.md`. Surfaced by Phase 3B codebase investigation (structural-readiness check) and approved by human at design-decisions-mode step 2.

**Codebase verified:** 2026-04-17 (Phase 3B investigator findings in task #15).

**Phase Type:** preparatory-refactor

**Target Files:**
- `/home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` — RED phase section only, approximately lines 71-108 pre-Phase-2.5. Exact boundaries determined by smell-assessor at execution time.

---

## Acceptance Criteria Coverage

This phase is preparatory refactoring. It restructures existing code to enable the upcoming implementation phase.

**Verifies: None** — success = structural split achieved with content and behaviour preserved.

**Enables:** Phase 3: `testing-skills-with-subagents` restructure — provides two clean subsections within RED (basic baseline checklist + synthetic pressure-scenario detail) so Phase 3 can (a) prepend the conversation-precedent protocol to the checklist subsection and (b) move the pressure-scenario subsection into REFACTOR without tangling with paragraph-level surgery inside a monolithic section.

---

## Structural Smell Assessment (input for the refactoring pipeline)

Phase 3B's codebase investigator identified the following impediment (quoted): *"Synthetic scenarios (lines 79-107) are NOT in a separate subsection; they're integrated as THE RED method within the larger RED phase. Demoting to REFACTOR will require extracting the 'Great scenario (multiple pressures)' example (lines 139-154) and pressure-type guidance, keeping 'Process checklist' (lines 77-83) in RED for baseline establishment, moving only the pressure-scenario detail and complexity to REFACTOR completeness section. This is a rewrite/restructure, not a simple cut-and-move."*

Named smells (Mantyla taxonomy):
- **Feature envy / inappropriate intimacy:** The pressure-scenario example is deeply entangled with the process checklist — Phase 3 cannot address one without re-rendering the other. The checklist reads like it exists to set up the scenario example, not as a standalone baseline guide.
- **Divergent change at a section granularity:** The RED section currently has to change both when the conversation-precedent protocol is added (checklist-flavoured work) AND when synthetic scenarios move to REFACTOR (pressure-scenario-flavoured work). Two reasons to change = two things.
- **Long method at the section level:** The RED H2 carries ~37 lines mixing process guidance, worked examples, and rationalisation captures. Separation improves scanability for future readers.

Named refactoring prescription (Fowler):
- **Extract subsection / extract method** (markdown analogue): Pull the pressure-scenario content into its own H3 subsection within the RED H2. Pull the process checklist into its own H3 subsection within the RED H2. Keep both in RED until Phase 3 decides where the pressure-scenario subsection ultimately belongs.

---

## Execution Instructions (for the three-agent refactoring pipeline)

Per `impl-plan-write`'s preparatory-refactor convention, this phase's "tasks" are a single dispatch to the refactoring pipeline with framing tailored to this specific impediment. Tasks below are the pipeline's choreography, not hand-written edit scripts.

### Pipeline step A: Smell assessor

**Agent:** `denubis-plan-and-execute:smell-assessor`

**Prompt framing (execution composes exact prompt):**
> Read `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` with focus on the RED phase section (H2 heading at approximately line 71, extending to the start of the GREEN phase H2 at approximately line 110). Produce a structured smell report identifying:
> 1. Feature envy between the process checklist and the pressure-scenario example
> 2. Divergent change at the RED section granularity (cite Phase 3's planned changes: prepend conversation-precedent protocol; demote synthetic scenarios to REFACTOR)
> 3. Long method smell at the section level
> 4. Any additional smells within the RED section worth surfacing before Phase 3
>
> Produce a refactoring checkpoint file at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_5_smell_checkpoint.md` with evidence-graded findings and Fowler-named refactoring prescriptions. Do not edit SKILL.md.

**Consumer-tracing:** Checkpoint file feeds the critical-peer-review agent (step B) and the refactoring-executor (step C). Failure to produce the checkpoint = halt before any edit.

### Pipeline step B: Critical peer review

**Agent:** `denubis-plan-and-execute:critical-peer-review`

**Prompt framing:**
> Review the smell-assessor's checkpoint file at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_5_smell_checkpoint.md`. Your job is a falsification-first audit treating the smell report as untrusted. Specifically test:
> 1. Are the named smells actually present in the file, or is the assessor pattern-matching? Quote the file text for each claimed smell.
> 2. Is the refactoring prescription the right one, or would a lighter-weight change achieve the same enablement for Phase 3?
> 3. Are there smells the assessor missed within the RED section that Phase 3 will have to work around?
> 4. Does the prescription preserve behaviour (Two Hats discipline), or does it smuggle a semantic change?
>
> Append your review to the checkpoint file as a peer-review section. If any smell fails the falsification test, the prescription must be revised before the refactoring-executor runs.

**Consumer-tracing:** Reviewed checkpoint feeds the refactoring-executor. Failed falsifications block the pipeline.

### Pipeline step C: Refactoring executor

**Agent:** `denubis-plan-and-execute:refactoring-executor`

**Prompt framing:**
> Apply the reviewed refactoring prescription at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_5_smell_checkpoint.md` to `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md`. Two Hats discipline — refactoring hat only, no behaviour changes.
>
> Apply one finding at a time. After each edit:
> 1. Re-read the modified section to confirm structure changed but semantic meaning did not
> 2. Grep for the preserved verbatim content (model-tier guidance, "No Blaming the Model", flaky-result discipline, meta-testing pattern) — each block must still be byte-identical to pre-edit
> 3. Report complexity delta
>
> If any step finds behavioural drift, revert the edit immediately and report.
>
> Commit after each finding is applied and verified. Commit message format: `refactor(testing-skills-with-subagents): [smell name] — extract [subsection name]`.

---

## Done when (phase-level)

- [ ] `phase_02_5_smell_checkpoint.md` exists in the plan directory with smell-assessor findings + critical-peer-review audit
- [ ] RED phase section of `testing-skills-with-subagents/SKILL.md` has TWO distinct H3 (or equivalent) subsections:
  - Basic baseline checklist (scenario-agnostic process steps)
  - Synthetic pressure-scenario detail (multi-stressor examples + pressure-type guidance)
- [ ] All denubis-specific verbatim blocks (model-tier guidance at pre-prep lines 47-60; No Blaming the Model at 61-69; flaky-result discipline at 384-389; meta-testing pattern) remain byte-identical — grep audit confirms
- [ ] No content added or removed — diff between pre-prep and post-prep files is purely structural (re-flow, headings added, no text content lines lost or added except the new H3 headings themselves)
- [ ] Commit(s) land with `refactor(...)` conventional-commit prefix
- [ ] Enables check: Phase 3's conversation-precedent-protocol prepend can target the basic-baseline-checklist H3 cleanly; Phase 3's synthetic-scenario demotion can move the pressure-scenario H3 block as a unit

**Not in scope for Phase 2.5:**
- Phase 3's conversation-precedent-protocol prepend (happens in Phase 3 proper)
- Phase 3's synthetic-scenario demotion to REFACTOR (happens in Phase 3 proper)
- Any change to the Haiku-judgement claim (Phase 3 soften)
- Any change outside the RED phase section of SKILL.md

**Verifies: None** — success = tests green after restructuring. This skill has no runtime tests, so "green" means: Phase 3's GREEN verification (which follows this phase) can execute its pressure-scenario without the restructure tripping it up.
