# Test Requirements: Architecture Documentation System

Maps each acceptance criterion to verification. All verification is file-existence, content-matching, or human review -- there is no executable code to unit test.

**Plugin root:** `plugins/denubis-plan-and-execute/`

**Shorthand:** all relative paths below are relative to the plugin root unless otherwise noted.

---

## Automated Verification

### maintain-arch-docs.AC1: Inner skill proposes architecture doc changes from design plans

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| maintain-arch-docs.AC1.1 | grep-match | `grep -c "DFD\|data flow\|data transformation\|dfd/" skills/update-architecture-docs/SKILL.md` | Count >= 3 (assessment framework references DFD context signals for data transformations) |
| maintain-arch-docs.AC1.2 | grep-match | `grep -c "database\.md\|Database\|new entity\|changed schema" skills/update-architecture-docs/SKILL.md` | Count >= 2 (assessment framework references database context signals) |
| maintain-arch-docs.AC1.3 | grep-match | `grep -c "personae\|persona\|user type\|new actor" skills/update-architecture-docs/SKILL.md` | Count >= 2 (assessment framework references personae context signals) |
| maintain-arch-docs.AC1.4 | grep-match | `grep -c "glossary\|domain concept\|renamed entity\|ubiquitous" skills/update-architecture-docs/SKILL.md` | Count >= 2 (assessment framework references glossary context signals) |
| maintain-arch-docs.AC1.5 | grep-match | `grep -c "group.*by doc type\|grouped by doc type\|Proposed architecture documentation changes" skills/update-architecture-docs/SKILL.md` | Count >= 1 (proposal section documents grouping by doc type) |
| maintain-arch-docs.AC1.6 | grep-match | `grep -c "no architecture changes detected" skills/update-architecture-docs/SKILL.md` | Count >= 1 (exit clause for pure refactors) |

### maintain-arch-docs.AC2: Inner skill detects contradictions and halts

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| maintain-arch-docs.AC2.1 | grep-match | `grep -c "duplicates.*responsibilit\|Process duplicates existing" skills/update-architecture-docs/SKILL.md` | Count >= 1 (DFD contradiction pattern documented) |
| maintain-arch-docs.AC2.2 | grep-match | `grep -c "defined differently\|synonym collision\|conflicts with.*glossary" skills/update-architecture-docs/SKILL.md` | Count >= 1 (glossary contradiction pattern documented) |
| maintain-arch-docs.AC2.3 | grep-match | `grep -c "contradicts existing.*constraint\|New constraint contradicts" skills/update-architecture-docs/SKILL.md` | Count >= 1 (constraint contradiction pattern documented) |
| maintain-arch-docs.AC2.4 | grep-match | `grep "HALT" skills/update-architecture-docs/SKILL.md \| grep -c "resolution\|resolve\|continues\|respond"` | Count >= 1 (HALT section documents that human resolves and skill continues) |
| maintain-arch-docs.AC2.4 (supplemental) | grep-match | `grep -c "I will not proceed past this point until you respond" skills/update-architecture-docs/SKILL.md` | Count >= 1 (HALT blocks until human response) |

### maintain-arch-docs.AC3: Inner skill handles greenfield and bootstrap

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| maintain-arch-docs.AC3.1 | grep-match | `grep -ic "bootstrap\|scaffold.*directory\|does not exist" skills/update-architecture-docs/SKILL.md` | Count >= 3 (bootstrap mode documented with scaffolding instructions) |
| maintain-arch-docs.AC3.2 | grep-match | `grep -c "0-context-diagram\|context.diagram\|system boundary" skills/update-architecture-docs/SKILL.md` | Count >= 1 (bootstrap creates context diagram) |
| maintain-arch-docs.AC3.2 (supplemental) | file-exists | `stat skills/update-architecture-docs/template-dfd-context.md` | File exists (template available for bootstrap to use) |
| maintain-arch-docs.AC3.3 | grep-match | `grep -c "initial glossary\|initial.*personae\|Populate initial" skills/update-architecture-docs/SKILL.md` | Count >= 1 (bootstrap populates glossary and personae) |
| maintain-arch-docs.AC3.4 | grep-match | `grep -c "docs/database\.md.*migrate\|move.*docs/database\.md\|migrate.*docs/architecture/database" skills/update-architecture-docs/SKILL.md` | Count >= 1 (bootstrap handles existing database.md migration) |

### maintain-arch-docs.AC4: Wrapper skill runs standalone maintenance sessions

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| maintain-arch-docs.AC4.1 | grep-match | `grep -c "merge-base\|git diff\|git log.*docs/architecture" skills/maintain-architecture/SKILL.md` | Count >= 2 (both branch and main baseline methods documented) |
| maintain-arch-docs.AC4.2 | grep-match | `grep -c "subagent\|sonnet.*general.*purpose\|Task.*description\|Dispatch" skills/maintain-architecture/SKILL.md` | Count >= 2 (subagent dispatch for investigation documented) |
| maintain-arch-docs.AC4.3 | grep-match | `grep -c "one.*question\|pointed.*question\|one.*at a time" skills/maintain-architecture/SKILL.md` | Count >= 1 (one-question-at-a-time pattern documented) |
| maintain-arch-docs.AC4.4 | grep-match | `grep -c "update-architecture-docs" skills/maintain-architecture/SKILL.md` | Count >= 1 (wrapper invokes inner skill) |
| maintain-arch-docs.AC4.5 | grep-match | `grep -c "architecture docs appear current\|no changes.*detected" skills/maintain-architecture/SKILL.md` | Count >= 1 (edge case: no changes exits cleanly) |

### maintain-arch-docs.AC5: Database documentation path migration

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| maintain-arch-docs.AC5.1 | grep-match | `grep -c "docs/architecture/database\.md" skills/writing-design-plans/SKILL.md` | Count >= 1 (new path referenced) |
| maintain-arch-docs.AC5.1 (supplemental) | grep-absent | `grep -c "docs/database\.md" skills/writing-design-plans/SKILL.md` | Count = 0 (old path absent) |
| maintain-arch-docs.AC5.2 | grep-match | `grep -c "docs/architecture/database\.md" agents/dba-reviewer.md` | Count >= 1 (new path in Step 7 and elsewhere) |
| maintain-arch-docs.AC5.2 (supplemental) | grep-absent | `grep -c "docs/database\.md" agents/dba-reviewer.md` | Count = 0 (old path absent) |
| maintain-arch-docs.AC5.3 | grep-match | `grep -c "docs/architecture/database\.md" skills/howto-develop-with-postgres/SKILL.md` | Count >= 1 (new path in template and lifecycle sections) |
| maintain-arch-docs.AC5.3 (supplemental) | grep-absent | `grep -c "docs/database\.md" skills/howto-develop-with-postgres/SKILL.md` | Count = 0 (old path absent) |
| maintain-arch-docs.AC5.4 | grep-absent | `grep -rn "docs/database\.md" plugins/denubis-plan-and-execute/` | No output (zero matches across entire plugin) |

### maintain-arch-docs.AC6: Design workflow integration

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| maintain-arch-docs.AC6.1 (sequence) | grep-match | `grep -n "Before Commit:" skills/writing-design-plans/SKILL.md` | Lines show sequence: Dependency Rationale, then Proleptic Challenge, then Architecture Documentation. Architecture Documentation appears after Proleptic Challenge and before the commit section. |
| maintain-arch-docs.AC6.1 (inner skill call) | grep-match | `grep -c "update-architecture-docs" skills/writing-design-plans/SKILL.md` | Count >= 1 (writing-design-plans calls inner skill) |
| maintain-arch-docs.AC6.2 | grep-match | `grep -c "git add.*docs/architecture" skills/writing-design-plans/SKILL.md` | Count >= 1 (architecture docs included in git add for commit) |
| maintain-arch-docs.AC6.3 | grep-match | `grep -c "bootstrap" skills/update-architecture-docs/SKILL.md` | Count >= 2 (bootstrap mode is documented and triggers when docs/architecture/ absent) |

### Phase 1 infrastructure (templates)

These are prerequisite checks, not AC-mapped, but required for the skill to function.

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| phase1.templates | file-exists | `ls skills/update-architecture-docs/template-*.md` | 7 files: template-dfd-context.md, template-dfd-process.md, template-database.md, template-personae.md, template-glossary.md, template-constraints.md, template-state.md |
| phase1.dfd-context-mermaid | grep-match | `grep -c "flowchart" skills/update-architecture-docs/template-dfd-context.md` | Count >= 1 (valid Mermaid flowchart syntax) |
| phase1.dfd-process-mermaid | grep-match | `grep -c "flowchart" skills/update-architecture-docs/template-dfd-process.md` | Count >= 1 (valid Mermaid flowchart syntax) |
| phase1.dfd-process-das | grep-match | `grep -c "@{ shape: das" skills/update-architecture-docs/template-dfd-process.md` | Count >= 1 (data store notation present) |
| phase1.database-mermaid | grep-match | `grep -c "erDiagram" skills/update-architecture-docs/template-database.md` | Count >= 1 (valid Mermaid ERD syntax) |
| phase1.state-mermaid | grep-match | `grep -c "stateDiagram-v2" skills/update-architecture-docs/template-state.md` | Count >= 1 (valid Mermaid state diagram syntax) |
| phase1.inner-skill-exists | file-exists | `stat skills/update-architecture-docs/SKILL.md` | File exists |
| phase1.inner-skill-frontmatter | grep-match | `grep -c "user-invocable: false" skills/update-architecture-docs/SKILL.md` | Count = 1 (inner skill is not user-invocable) |

### Phase 3 infrastructure (wrapper and command)

| ID | Verification Type | Command | Expected Result |
|----|------------------|---------|-----------------|
| phase3.wrapper-exists | file-exists | `stat skills/maintain-architecture/SKILL.md` | File exists |
| phase3.wrapper-frontmatter | grep-match | `grep -c "user-invocable: true" skills/maintain-architecture/SKILL.md` | Count = 1 (wrapper is user-invocable) |
| phase3.command-exists | file-exists | `stat commands/maintain-architecture.md` | File exists |
| phase3.command-content | grep-match | `grep -c "maintain-architecture" commands/maintain-architecture.md` | Count >= 1 (command references the skill) |

---

## Human Verification

### maintain-arch-docs.AC1.1 — Inner skill identifies affected DFD files and proposes additions

**What to check:** Read the assessment framework in `skills/update-architecture-docs/SKILL.md`. Verify that the DFD row defines context signals that would match "a design plan introducing a new data transformation" and that the skill flow instructions would lead to identifying the correct DFD files.

**How to verify:** Read the SKILL.md assessment framework table and the skill flow steps 2-5. Trace through a hypothetical design plan that introduces a data transformation (e.g., "new ETL pipeline"). Confirm the context signals ("new data transformation, renamed component, changed data flow") would trigger DFD assessment, and that the proposal step would propose adding/modifying DFD files.

**Why automation is insufficient:** Automated grep confirms the words exist but cannot verify the logical connection between context signals, the skill flow, and the proposal output. The assessment framework must be coherent as a decision procedure, not just contain the right keywords.

### maintain-arch-docs.AC1.2 — Inner skill proposes updates to database.md

**What to check:** Same as AC1.1 but for the Database row. Verify context signals ("new entity, changed schema, new FK") would trigger database assessment and proposals targeting `docs/architecture/database.md`.

**How to verify:** Trace a design plan introducing a new database table through the assessment framework. Confirm the flow leads to a proposal for `docs/architecture/database.md`.

**Why automation is insufficient:** Same as AC1.1 -- logical coherence of the decision procedure.

### maintain-arch-docs.AC1.3 — Inner skill proposes additions to personae.md

**What to check:** Same pattern. Verify context signals ("new actor, changed access pattern") connect to personae proposals.

**How to verify:** Trace a design plan introducing a new user type through the assessment framework.

**Why automation is insufficient:** Same as AC1.1.

### maintain-arch-docs.AC1.4 — Inner skill proposes additions to glossary.md

**What to check:** Same pattern. Verify context signals ("new domain concept, renamed entity") connect to glossary proposals.

**How to verify:** Trace a design plan with new domain terminology through the assessment framework.

**Why automation is insufficient:** Same as AC1.1.

### maintain-arch-docs.AC1.5 — Proposals are grouped by doc type and presented for approval

**What to check:** Read the "Proposing Changes" section. Verify that: (a) the proposal format groups changes under doc-type headings (DFD, Glossary, etc.), (b) AskUserQuestion is used with Approve/Modify/Reject options, (c) writing only happens after approval.

**How to verify:** Read the proposal section end-to-end. Confirm the example output shows grouped headings. Confirm the approval gate precedes any file writes.

**Why automation is insufficient:** Grep can confirm the presence of "group by doc type" text, but cannot verify the proposal format is coherent and the approval gate actually precedes writes in the flow.

### maintain-arch-docs.AC2.1 — HALT on DFD responsibility duplication

**What to check:** Read the contradiction detection section. Verify that the DFD contradiction pattern ("process duplicates existing responsibility") is documented with: (a) a clear HALT format showing both existing and new content, (b) explicit instruction to stop and wait for human resolution, (c) resolution options.

**How to verify:** Read the HALT template and the DFD contradiction pattern. Confirm a scenario where `PaymentService` duplicates `BillingService` responsibilities would trigger the HALT.

**Why automation is insufficient:** The HALT format must be clear enough for the model to actually stop. Grep confirms the text exists but cannot judge whether the instructions are unambiguous enough to produce correct model behaviour.

### maintain-arch-docs.AC2.2 — HALT on glossary term conflict

**What to check:** Same HALT format verification for the glossary contradiction pattern ("term defined differently than existing entry; synonym collision").

**How to verify:** Read the contradiction patterns table and HALT template. Confirm a conflicting term definition would trigger HALT with both definitions shown.

**Why automation is insufficient:** Same as AC2.1.

### maintain-arch-docs.AC2.3 — HALT on constraint contradiction

**What to check:** Same HALT format verification for the constraints contradiction pattern ("new constraint contradicts existing one").

**How to verify:** Read the contradiction patterns table and HALT template. Confirm a scenario like "sub-100ms" vs "batch processing acceptable" would trigger HALT with both constraints shown.

**Why automation is insufficient:** Same as AC2.1.

### maintain-arch-docs.AC2.4 — After HALT, human resolves and skill continues

**What to check:** Verify the HALT section provides three resolution options (update existing, revise design, acknowledge divergence) and documents that the skill continues from step 4 after resolution.

**How to verify:** Read the HALT section. Confirm the three options are present. Confirm there is an explicit instruction about what step to resume from after resolution.

**Why automation is insufficient:** The continuation instruction must be clear enough that the model actually resumes correctly. Grep confirms the words exist but cannot assess instructional clarity.

### maintain-arch-docs.AC3.1 — Bootstrap scaffolds directory structure

**What to check:** Read the bootstrap section. Verify it lists the complete directory structure to scaffold (`docs/architecture/dfd/`, `docs/architecture/states/`, plus the root-level files).

**How to verify:** Compare the bootstrap instructions against the directory convention section. Every directory and file type in the convention should be scaffolded.

**Why automation is insufficient:** Grep can confirm "scaffold" appears, but cannot verify the scaffolding instructions produce the complete directory structure from the convention.

### maintain-arch-docs.AC3.2 — Bootstrap creates 0-context-diagram.md from system boundary

**What to check:** Verify the bootstrap instructions specifically reference creating `0-context-diagram.md` from the design plan's Architecture section / system boundary.

**How to verify:** Read the bootstrap section and confirm it connects the design plan's system boundary content to the context diagram template.

**Why automation is insufficient:** The instruction must correctly map design plan content to the template. Grep confirms the file name appears but not the mapping logic.

### maintain-arch-docs.AC3.3 — Bootstrap populates initial glossary and personae

**What to check:** Verify bootstrap instructions map design plan glossary to `glossary.md` and design plan actors/user types to `personae.md`.

**How to verify:** Read the bootstrap section and confirm both mappings are documented.

**Why automation is insufficient:** Same as AC3.2 -- mapping logic, not just keyword presence.

### maintain-arch-docs.AC4.1 — Wrapper computes git diff baseline appropriate to context

**What to check:** Verify the baseline computation section has correct bash commands for both scenarios (branch: `git merge-base HEAD main`; main: `git log -1 --format=%H -- docs/architecture/`) and error handling for edge cases.

**How to verify:** Read the "Computing Baseline" section. Verify both commands are present. Verify error handling covers: merge-base failure, no architecture commits existing.

**Why automation is insufficient:** Grep confirms command strings exist but cannot verify the commands are correct for their stated purpose or that error handling is complete.

### maintain-arch-docs.AC4.2 — Wrapper dispatches subagents to read code and architecture files

**What to check:** Verify the investigation section dispatches at least two subagents: one for current architecture docs, one for the diff/changed code. Verify each subagent has a clear prompt specifying what to report.

**How to verify:** Read the "Investigation" section. Confirm subagent invocations use the XML Task format. Confirm each has a distinct purpose and clear reporting instructions.

**Why automation is insufficient:** The subagent prompts must be clear enough to produce useful reports. Grep confirms subagent references exist but cannot assess prompt quality.

### maintain-arch-docs.AC4.3 — Wrapper asks one pointed question at a time

**What to check:** Verify the question loop section instructs: one question at a time, use AskUserQuestion for choices, open-ended for understanding, and explicitly states not to ask questions when only one answer is sensible.

**How to verify:** Read the "Question Loop" section. Confirm all four instructions are present. Compare against the brainstorming skill's question pattern for consistency.

**Why automation is insufficient:** The question instructions must be clear enough to produce single, pointed questions in practice. Grep confirms keywords but not instructional coherence.

### maintain-arch-docs.AC4.4 — Wrapper invokes inner skill with diff baseline

**What to check:** Verify the wrapper documents a `REQUIRED SUB-SKILL` invocation of `update-architecture-docs` with the git diff output as the artifact.

**How to verify:** Read the "Updating Architecture Docs" section. Confirm the sub-skill call pattern matches the inner skill's "Wrapper mode" input specification.

**Why automation is insufficient:** The invocation must pass the correct artifact type. Grep confirms the skill name appears but not that the artifact is correctly specified.

### maintain-arch-docs.AC6.1 — writing-design-plans calls update-architecture-docs in correct sequence

**What to check:** Verify the before-commit section order is: (1) Dependency Rationale, (2) Proleptic Challenge, (3) Architecture Documentation, (4) Commit. Verify the Architecture Documentation section calls `update-architecture-docs` as a required sub-skill.

**How to verify:** Read `skills/writing-design-plans/SKILL.md`. Find all "Before Commit:" headings and verify their order. Verify the Architecture Documentation section contains the sub-skill invocation.

**Why automation is insufficient:** Automated grep can confirm the headings exist but verifying their relative order requires reading the file and confirming the sequence. The `grep -n` approach in the automated table provides line numbers, but a human should confirm the ordering is correct and there are no intervening sections that break the sequence.

### maintain-arch-docs.AC6.2 — Architecture doc changes included in design plan commit

**What to check:** Verify the `git add` command in the commit section includes `docs/architecture/`.

**How to verify:** Read the commit section. Confirm `docs/architecture/` appears in the git add command alongside the design plan and dependency rationale.

**Why automation is insufficient:** Grep confirms the path appears in a git add command but cannot verify it is the commit-step git add (not some other git add elsewhere in the file). Human must confirm context.

### maintain-arch-docs.AC6.3 — Bootstrap mode triggers when docs/architecture/ absent

**What to check:** Verify the inner skill's bootstrap section is triggered by the absence of `docs/architecture/` regardless of caller (both sub-skill and wrapper modes). The Architecture Documentation section in `writing-design-plans` should note that bootstrap may trigger.

**How to verify:** Read the inner skill's bootstrap section. Confirm it triggers on directory absence. Read the `writing-design-plans` Architecture Documentation section. Confirm it acknowledges bootstrap.

**Why automation is insufficient:** The bootstrap trigger condition must apply in both calling modes. Grep can confirm bootstrap is mentioned but not that the trigger logic is mode-independent.

---

## Verification Execution Plan

### Phase 1 gate (templates)

Run after Phase 1 implementation:

```bash
cd plugins/denubis-plan-and-execute
ls skills/update-architecture-docs/template-*.md | wc -l  # expect 7
grep -c "flowchart" skills/update-architecture-docs/template-dfd-context.md  # expect >= 1
grep -c "flowchart" skills/update-architecture-docs/template-dfd-process.md  # expect >= 1
grep -c "@{ shape: das" skills/update-architecture-docs/template-dfd-process.md  # expect >= 1
grep -c "erDiagram" skills/update-architecture-docs/template-database.md  # expect >= 1
grep -c "stateDiagram-v2" skills/update-architecture-docs/template-state.md  # expect >= 1
```

### Phase 2 gate (inner skill)

Run after Phase 2 implementation:

```bash
cd plugins/denubis-plan-and-execute
stat skills/update-architecture-docs/SKILL.md  # exists
grep -c "user-invocable: false" skills/update-architecture-docs/SKILL.md  # expect 1
grep -c "no architecture changes detected" skills/update-architecture-docs/SKILL.md  # expect >= 1
grep -c "HALT" skills/update-architecture-docs/SKILL.md  # expect >= 3
grep -c "bootstrap" skills/update-architecture-docs/SKILL.md  # expect >= 2
grep -c "0-context-diagram" skills/update-architecture-docs/SKILL.md  # expect >= 1
grep -c "group.*by doc type\|grouped by doc type" skills/update-architecture-docs/SKILL.md  # expect >= 1
```

Then: **human review** of AC1.1-AC1.5, AC2.1-AC2.4, AC3.1-AC3.3 per the Human Verification section above.

### Phase 3 gate (wrapper skill)

Run after Phase 3 implementation:

```bash
cd plugins/denubis-plan-and-execute
stat skills/maintain-architecture/SKILL.md  # exists
stat commands/maintain-architecture.md  # exists
grep -c "user-invocable: true" skills/maintain-architecture/SKILL.md  # expect 1
grep -c "merge-base" skills/maintain-architecture/SKILL.md  # expect >= 1
grep -c "update-architecture-docs" skills/maintain-architecture/SKILL.md  # expect >= 1
grep -c "architecture docs appear current" skills/maintain-architecture/SKILL.md  # expect >= 1
grep -c "maintain-architecture" commands/maintain-architecture.md  # expect >= 1
```

Then: **human review** of AC4.1-AC4.4 per the Human Verification section above.

### Phase 4 gate (migration and integration)

Run after Phase 4 implementation:

```bash
cd plugins/denubis-plan-and-execute

# AC5: No remaining old-path references
grep -rn "docs/database\.md" .  # expect NO output

# AC5.1: writing-design-plans uses new path
grep -c "docs/architecture/database\.md" skills/writing-design-plans/SKILL.md  # expect >= 1

# AC5.2: dba-reviewer uses new path
grep -c "docs/architecture/database\.md" agents/dba-reviewer.md  # expect >= 1

# AC5.3: howto-develop-with-postgres uses new path
grep -c "docs/architecture/database\.md" skills/howto-develop-with-postgres/SKILL.md  # expect >= 1

# AC5.4: Full plugin sweep
grep -rn "docs/database\.md" .  # expect NO output (same as above, belt and suspenders)

# AC6.1: Sequence check
grep -n "Before Commit:" skills/writing-design-plans/SKILL.md
# Expect: Dependency Rationale < Proleptic Challenge < Architecture Documentation (by line number)

# AC6.1: Inner skill invocation
grep -c "update-architecture-docs" skills/writing-design-plans/SKILL.md  # expect >= 1

# AC6.2: Architecture docs in commit
grep -c "git add.*docs/architecture" skills/writing-design-plans/SKILL.md  # expect >= 1

# AC6.1 (negative): Old section removed
grep -c "Before Commit: Database Documentation" skills/writing-design-plans/SKILL.md  # expect 0
```

Then: **human review** of AC6.1-AC6.3 per the Human Verification section above.

### Final cross-cutting check

After all phases:

```bash
cd plugins/denubis-plan-and-execute

# All new files exist
ls skills/update-architecture-docs/SKILL.md
ls skills/update-architecture-docs/template-*.md | wc -l  # expect 7
ls skills/maintain-architecture/SKILL.md
ls commands/maintain-architecture.md

# No stale references anywhere in plugin
grep -rn "docs/database\.md" .  # expect NO output

# Both skills have correct invocability
grep "user-invocable:" skills/update-architecture-docs/SKILL.md  # expect false
grep "user-invocable:" skills/maintain-architecture/SKILL.md  # expect true
```
