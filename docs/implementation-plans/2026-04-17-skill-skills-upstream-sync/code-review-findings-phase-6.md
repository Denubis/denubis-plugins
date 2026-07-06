# Code Review Findings — phase-6

# Code Review: Phase 6 — impl-plan-write anti-smuggling hardening (RE-REVIEW after fixes)

## Status: APPROVED

**Critical: 0 | Important: 0 | Minor: 1 (pre-existing, outside diff)**

Re-review of BASE `c0417ea` → HEAD `435be93`. All three Important findings from
the prior cycle are resolved with verifiable evidence in the current diff. The
prior Minor is recorded as an accepted operator disposition. The fixes introduced
no new internal-coherence defects: the folded existence gate reads coherently
with a single point of completion, the "Task 4" leak is gone from the deliverable
skill, and the moved Worked Examples section broke no cross-reference. One
low-priority staleness remains in the plan's own checklist (outside the diff).

## Verification
```
Tests/Lint: N/A — Markdown-only change (skill docs + plan artefacts).
Re-review structural greps (SKILL.md), ALL PASS:
  grep "Task 4"        → 1 hit: line 387 (unrelated ### Task 4: TokenService). ✓
  grep "Step 4"        → 1 hit: line 593 (unrelated "Run test to verify"). ✓
  existence gate       → 1312 "must pass BEFORE marking complete";
                         1332 "Only after the existence gate passes: Mark ... completed". ✓
  step contiguity      → 6.5(896) → 7(917) → 8(928) → 9(935), then
                         ### Worked Examples(939), then ## Task Structure(978). ✓
  moved-block survival → 3x anti-smuggling tests, 3x Worked Examples, AskUserQuestion,
                         Task ND write step all present post-move. ✓
phase_06.md content blocks: grep "Task 4" shows only plan-internal task numbering
  and commit-message body; the SKILL-destined fenced blocks (318/333/452) are clean. ✓
```

## Prior Findings Verification

- **Important #1 (existence gate mis-sequenced) — RESOLVED.**
  The `### Step 4: Existence gate` heading is gone. The gate body now lives inside
  `### Step 3: Complete finalization` under `**Existence gate (must pass BEFORE
  marking complete):**` (SKILL.md:1312), and the completion line moved to *after*
  the gate: `**Only after the existence gate passes:** Mark the Finalization task
  as completed, then proceed to Test Requirements generation.` (SKILL.md:1332). The
  prior Step 3/Step 4 contradiction ("mark completed" vs "cannot complete until")
  is reconciled to a single point of completion. The anti-silent-skip gate can no
  longer be bypassed by reading in order. Verified coherent by reading 1304–1338.

- **Important #2 ("Task 4" leak into the deliverable skill) — RESOLVED.**
  `grep -n "Task 4" SKILL.md` returns exactly one hit: line 387, the unrelated
  `### Task 4: TokenService implementation` illustrative heading. The three prior
  leak sites now use skill-internal anchors: SKILL.md:898 and :913 (the moved 6.5
  block) say "the collation audit in the UAT Requirements Collation section";
  SKILL.md:1448 says "This UAT Requirements Collation audit IS the structural gate".
  The plan's SKILL-destined content blocks (phase_06.md:318/333/452) were cleaned in
  the same commit range. Remaining "Task 4" strings in phase_06.md are the plan's own
  task numbering (its Task 4 work item, commit-message body, checklist) — legitimate
  plan-internal references, not skill leaks.

- **Important #3 (Worked Examples orphans steps 7–9) — RESOLVED.**
  The numbered procedure block (6.5 → 7 → 8 → 9) was moved to immediately follow the
  DR templates, and `### Worked Examples` now trails at line 939, before
  `## Task Structure` (978). The numbered steps are contiguous (896/917/928/935) and
  nest under the real procedure heading at 677 — the DR1–DR4 `###` lines between 677
  and 896 are inside a fenced code block (fence closes at 894), so they are template
  text, not outline headings. Heading-based navigation now attributes the approval
  (step 7) and file-writing (step 8, Task ND) steps to the procedure, not to an
  illustrative section. No cross-reference to Worked Examples exists elsewhere, so the
  move broke nothing (the only other "worked example" mention, line 758, is an
  unrelated decision-sorting example).

- **Minor (bare `src/`/`tests/` paths in fenced blocks) — ACCEPTED (operator
  disposition).** Recorded as a principled mixed convention: inline paths are
  angle-bracketed to satisfy the AC5.4 cross-reference audit; fenced-block illustrative
  paths are left bare because they are not audited and read better in code context.
  This is a closed disposition, not an unresolved issue.

## Issues

### Minor (count: 1)

- **Issue**: The plan's acceptance checklist still reads "Finalization **Step 4**
  existence gate on uat-requirements.md present" while the shipped skill folded the
  gate into Step 3 (no Step 4 exists in Finalization anymore). The aligning commit
  (435be93, "align plan content with code-review fixes to the shipped skill") swept
  the prose and content blocks but not this checklist line, so a reader who greps the
  plan for "Step 4" gets a label the deliverable no longer matches.
- **Location**: phase_06.md:706 (also the related checklist line 705 references
  "Task 4 collation audit" as the backstop, which is correct plan-internal numbering).
- **Note on scope**: This line is *unchanged by the diff* (outside the modified hunks)
  and pre-existing. It is offered only because the commit's stated intent was
  plan/skill alignment; it does not affect the deliverable skill, which is correct.
- **Fix (optional)**: reword to "Finalization existence gate (inside Step 3) present"
  to match the shipped form, or leave as historical task-tracking.

## Plan Alignment
- AC6.8 (Finalization existence gate): ✓ now correctly sequenced — gate precedes completion.
- AC6.2 (collation audit, section-name cross-refs): ✓ "Task 4" leak removed; anchors are skill-internal.
- AC6.6 (step 6.5 pre-presentation self-audit): ✓ step 6.5 now contiguous within the procedure (6.5→7→8→9).
- AC6.7 / AC6.1 / AC6.3 / AC6.5 / AC5.4: unaffected by these positional/naming fixes; content preserved through the move (verified present).
- phase_06.md Step 1 carries an explicit "Placement correction (code review, 2026-07-06)" note documenting that the illustrative `### Step 4` block ships inside Step 3 — transparent reconciliation, plan matches deliverable.

## Decision: APPROVED FOR MERGE

All three prior Important findings are resolved with in-diff evidence; the prior
Minor is an accepted disposition. The sole remaining item is a pre-existing,
outside-the-diff checklist staleness in the plan (Minor, optional). No Critical or
Important issues, and the fixes introduced no new coherence defects.
