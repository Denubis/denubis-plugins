# Human Test Plan: Architecture Documentation System

**Implementation plan:** `docs/implementation-plans/2026-02-18-maintain-arch-docs/`
**Branch:** `feat/maintain-arch-docs`
**Date:** 2026-02-18

## Automated Verification Results

All automated checks from `test-requirements.md` pass with two known casing deviations and one design deviation:

| Check | Result | Notes |
|-------|--------|-------|
| Phase 1 templates (7 files) | PASS | All Mermaid syntax correct |
| Phase 2 inner skill content | PASS | AC1.6 case mismatch (sentence case vs lowercase in grep pattern) |
| Phase 3 wrapper + command | PASS | AC4.5 case mismatch (same pattern) |
| Phase 4 path migration | PASS | AC5.1 design deviation: broader architecture section replaces database-specific section |
| Phase 4 sequence verification | PASS | Lines 604/635/675 in correct order |
| Phase 4 no stale refs | PASS | Only intentional bootstrap migration reference remains |

## Human Verification Items

### AC1: Inner skill proposes architecture doc changes

**AC1.1-AC1.4 (assessment framework coherence):**
Read `skills/update-architecture-docs/SKILL.md` assessment framework table. For each doc type (DFD, Database, Personae, Glossary, Constraints, States), trace a hypothetical design plan through the context signals and verify they would lead to correct identification of affected docs.

**AC1.5 (proposals grouped by doc type):**
Read the "Proposing Changes" section. Verify the proposal format groups changes under doc-type headings and the AskUserQuestion approval gate precedes any file writes.

### AC2: Contradiction detection and HALT

**AC2.1-AC2.3 (HALT format):**
Read the "Contradiction Detection" section. Verify the HALT format includes: "What I see", "Existing doc", "New content", "Why it matters", 3 resolution options, and "I will not proceed past this point until you respond."

**AC2.4 (post-HALT continuation):**
Verify the HALT section documents that the skill continues from step 4 (identify affected docs) after resolution.

### AC3: Bootstrap and greenfield

**AC3.1 (scaffolding completeness):**
Compare the bootstrap instructions against the directory convention section. Verify every directory and file type is scaffolded.

**AC3.2-AC3.3 (context diagram + glossary/personae from design):**
Verify bootstrap instructions map design plan content to the correct templates.

### AC4: Wrapper skill standalone sessions

**AC4.1 (baseline computation):**
Read the "Computing Baseline" section. Verify both git commands are correct and error handling covers merge-base failure and missing architecture commits.

**AC4.2 (subagent dispatch):**
Verify subagent invocations use XML Task format and each has distinct purpose with clear reporting instructions.

**AC4.3 (question loop):**
Verify the question loop section instructs one question at a time with quality criteria.

### AC6: Design workflow integration

**AC6.1 (sequence):**
Verify `writing-design-plans/SKILL.md` "Before Commit" sections appear in order: Dependency Rationale, Proleptic Challenge, Architecture Documentation.

**AC6.2 (architecture docs in commit):**
Verify the commit section's `git add` command includes `docs/architecture/`.

**AC6.3 (bootstrap triggers):**
Verify the inner skill's bootstrap logic is mode-independent (triggers for both sub-skill and wrapper callers).
