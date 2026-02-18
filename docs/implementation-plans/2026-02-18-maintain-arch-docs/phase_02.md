# Architecture Documentation System — Phase 2: Inner Skill — `update-architecture-docs`

**Goal:** Create the inner skill SKILL.md that reads architecture docs, detects contradictions, and proposes changes for human approval.

**Architecture:** Single SKILL.md file with `user-invocable: false`. Follows the pattern of `writing-design-plans` and `brainstorming` — non-user-invocable skills called by orchestrating skills. Uses the DBA reviewer's HALT format for contradiction detection. Template files from Phase 1 are cross-referenced from SKILL.md.

**Tech Stack:** Markdown (SKILL.md)

**Scope:** Phase 2 of 4

**Codebase verified:** 2026-02-18

---

## Acceptance Criteria Coverage

This phase implements and tests:

### maintain-arch-docs.AC1: Inner skill proposes architecture doc changes from design plans
- **maintain-arch-docs.AC1.1 Success:** Given a design plan path introducing a new data transformation, the inner skill identifies affected DFD files and proposes additions
- **maintain-arch-docs.AC1.2 Success:** Given a design plan with new database entities, the inner skill proposes updates to `docs/architecture/database.md`
- **maintain-arch-docs.AC1.3 Success:** Given a design plan introducing a new user type, the inner skill proposes additions to `personae.md`
- **maintain-arch-docs.AC1.4 Success:** Given a design plan with new domain terms, the inner skill proposes additions to `glossary.md`
- **maintain-arch-docs.AC1.5 Success:** Proposals are grouped by doc type and presented to the human for approval before writing
- **maintain-arch-docs.AC1.6 Failure:** Given a design plan with no architecture-relevant content (e.g., pure refactor), the inner skill reports "no architecture changes detected" and exits

### maintain-arch-docs.AC2: Inner skill detects contradictions and halts
- **maintain-arch-docs.AC2.1 Success:** When a design plan introduces a process that duplicates responsibilities already assigned in the DFD, the skill HALTs and presents the contradiction
- **maintain-arch-docs.AC2.2 Success:** When a new term definition conflicts with an existing glossary entry, the skill HALTs and presents both definitions
- **maintain-arch-docs.AC2.3 Success:** When a new constraint contradicts an existing one (e.g., "sub-100ms" vs "batch processing acceptable"), the skill HALTs with both constraints
- **maintain-arch-docs.AC2.4 Success:** After HALT, the human can resolve the contradiction and the skill continues with the resolution

### maintain-arch-docs.AC3: Inner skill handles greenfield and bootstrap
- **maintain-arch-docs.AC3.1 Success:** When `docs/architecture/` does not exist, the skill scaffolds the directory structure and creates initial files from the design plan
- **maintain-arch-docs.AC3.2 Success:** Bootstrap creates `0-context-diagram.md` from the design plan's system boundary
- **maintain-arch-docs.AC3.3 Success:** Bootstrap populates initial glossary and personae from design context
- **maintain-arch-docs.AC3.4 Success:** If the project has an existing `docs/database.md`, bootstrap migrates it to `docs/architecture/database.md`

---

<!-- START_TASK_1 -->
### Task 1: Create SKILL.md with frontmatter and overview

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Create the SKILL.md file with YAML frontmatter following the established pattern (three fields: `name`, `description`, `user-invocable`), overview section, and workflow status line section.

Frontmatter:
```yaml
---
name: update-architecture-docs
description: Use when design or implementation work may affect architecture documentation - reads current docs, detects contradictions, and proposes changes for human approval before writing
user-invocable: false
---
```

Overview must state:
- Core principle: Read current state → detect contradictions → propose changes → write approved changes
- This skill operates on concrete artifacts only (design plan file path or git diff output), never conversation context
- Announce at start: "I'm using the update-architecture-docs skill to assess architecture documentation."

Include workflow status line table following the convention from other skills (prefixed with the wrapper script path).

**Verification:** File exists with correct frontmatter.

No commit yet — building the full SKILL.md across tasks.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add input modes section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the "Input Modes" section defining the two ways the skill receives context:

| Mode | Input | Called by |
|------|-------|----------|
| Sub-skill | Design plan file path | `writing-design-plans` after proleptic challenge |
| Wrapper | Git diff output (from baseline) | `maintain-architecture` during maintenance |

Document that:
- In sub-skill mode, the skill reads the design plan at the given file path and extracts architecture-relevant content
- In wrapper mode, the skill receives pre-computed git diff output and extracts what changed
- Both modes proceed to the same flow: read current state → detect → propose → write

**Verification:** Section exists with both modes documented.

No commit yet.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add directory convention section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the "Directory Convention" section defining the `docs/architecture/` structure. Include:
- The full directory tree (dfd/, states/, database.md, personae.md, glossary.md, constraints.md)
- DFD file numbering scheme (hierarchical: 0, 1, 1.1, 1.1.1)
- Numbering stability rule: numbers are stable identifiers, gaps acceptable, periodic cleanup via wrapper
- Cross-reference format for DFD files
- Reference to companion template files: "See `template-dfd-context.md`, `template-dfd-process.md`, etc. in this skill directory for document templates."

**Verification:** Section exists with complete directory convention.

No commit yet.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Add assessment framework section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the "Assessment Framework" section with the per-doc-type table defining:

| Doc Type | Atomic Unit | Context Signal | Contradiction Pattern |
|----------|-------------|----------------|----------------------|
| DFD | Process (numbered) | New data transformation, renamed component, changed data flow | Process duplicates existing responsibility; data flow contradicts existing diagram |
| Database | Table/relationship | New entity, changed schema, new FK | Entity in design doesn't match existing ERD; relationship contradicts existing constraints |
| Personae | User type | New actor, changed access pattern | New persona overlaps existing one; access pattern contradicts constraints |
| Glossary | Term | New domain concept, renamed entity | Term defined differently than existing entry; synonym collision |
| Constraints | Quality attribute | New SLA, performance target, capacity requirement | New constraint contradicts existing one |
| States | Entity lifecycle | New status, state transition, terminal state | State transition contradicts existing lifecycle; new state unreachable from existing graph |

Include instructions for how the skill uses this table:
1. For each doc type, scan the input artifact for context signals
2. If a signal is found, check the corresponding atomic units against existing docs
3. If a contradiction pattern matches, HALT before proceeding

**Verification:** Section exists with complete assessment table.

No commit yet.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Add contradiction detection and HALT section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the "Contradiction Detection" section using the HALT format from `dba-reviewer.md`:

```markdown
## Architecture Documentation HALT: [Brief description]

**What I see:** [Describe the contradiction — new content vs existing content]
**Existing doc:** [Quote the relevant section from the existing architecture doc]
**New content:** [Quote the relevant section from the design plan or diff]
**Why it matters:** [Impact if this contradiction goes unresolved]
**What I need from you:** Choose one:
1. Update the existing architecture doc (the new design supersedes)
2. Revise the design (the existing architecture is correct)
3. Acknowledge the divergence (both are valid in different contexts)

I will not proceed past this point until you respond.
```

Include the rule: "Finding contradictions is more important than updating. If in doubt about whether something is a contradiction, HALT. False positives are cheap; missed contradictions are expensive."

Include explicit instruction: after HALT resolution, the skill continues from step 4 (identify affected docs) with the resolution incorporated.

**Verification:** Section exists with HALT format matching dba-reviewer pattern.

No commit yet.
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Add proposal and approval flow section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the "Proposing Changes" section documenting:

1. After contradiction check passes, group proposed changes by doc type
2. Present proposals to human using AskUserQuestion with structured options:
   ```
   Question: "Review proposed architecture documentation changes:"
   Options:
     - "Approve all" (write all proposed changes)
     - "Approve with modifications" (I'll describe what to change)
     - "Reject" (no architecture doc changes)
   ```
3. Before the question, output the complete proposal in the message:
   ```
   **Proposed architecture documentation changes:**

   ### DFD
   - Create: `docs/architecture/dfd/1.3-new-process.md` (new process from design)
   - Modify: `docs/architecture/dfd/1-subsystem.md` (add reference to new child)

   ### Glossary
   - Add term: "Widget" — [definition from design context]

   [Continue for each affected doc type...]
   ```
4. Write only approved changes using the templates from Phase 1
5. If "no architecture changes detected" — report this and exit without proposing

**Verification:** Section exists with complete proposal flow.

No commit yet.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Add bootstrap and greenfield mode section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the "Bootstrap and Greenfield" section documenting:

**Bootstrap mode** (triggered when `docs/architecture/` does not exist AND a design plan is provided):
1. Scaffold directory: create `docs/architecture/dfd/`, `docs/architecture/states/`
2. Create `0-context-diagram.md` from design plan's system boundary (Architecture section)
3. Populate initial `glossary.md` from design plan's Glossary section
4. Populate initial `personae.md` from design plan's actors/user types
5. Create `constraints.md` from design plan's quality constraints (if any)
6. If `docs/database.md` exists, move it to `docs/architecture/database.md`
7. Present all created files to human for approval before writing

**Greenfield mode** (no `docs/architecture/` AND first design plan for new project):
- Same as bootstrap but also creates `database.md` if design plan includes database schema

**Key rule:** Bootstrap requires a design document. If there is no design plan, there is nothing to bootstrap from — the project needs brainstorming first.

**Verification:** Section exists with complete bootstrap flow.

No commit yet.
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Add complete skill flow and common mistakes

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Implementation:**

Add the complete "Skill Flow" section tying all sections together:

1. **Read current state** — load all files under `docs/architecture/`. If directory doesn't exist, enter bootstrap mode.
2. **Parse artifact** — extract entities, processes, data flows, constraints, and terms from the design plan or diff.
3. **Detect contradictions** — for each doc type where context signals are found, check for contradiction patterns. HALT if found.
4. **Identify affected docs** — determine which files need creation or modification, organised by doc type.
5. **Propose changes** — present grouped proposals to the human for approval.
6. **Write approved changes** — apply using templates from this skill directory.

Add "Common Rationalizations - STOP" table following the convention from other skills:

| Excuse | Reality |
|--------|---------|
| "No contradictions possible, it's a new feature" | New features can duplicate existing responsibilities. Check the DFD. |
| "Glossary update is obvious, don't need approval" | Never write blind updates. Always present proposals. |
| "Bootstrap is simple, skip the approval" | Bootstrap creates many files. Human must approve the initial structure. |
| "Design plan doesn't mention architecture" | Check anyway. Context signals may be implicit. |
| "I'll update docs after the code is written" | Architecture docs are updated from the design plan, before implementation. |

Add "Integration" section showing where this skill sits:
```
writing-design-plans (after proleptic challenge)
  → calls update-architecture-docs with design plan path
  → proposals presented to human
  → approved changes written
  → changes included in design plan commit

maintain-architecture (standalone sessions)
  → calls update-architecture-docs with git diff output
  → proposals presented to human
  → approved changes committed separately
```

**Verification:** Complete SKILL.md with all sections.
<!-- END_TASK_8 -->

<!-- START_TASK_9 -->
### Task 9: Commit inner skill

**Files:**
- `plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md`

**Step 1: Stage**

```bash
git add plugins/denubis-plan-and-execute/skills/update-architecture-docs/SKILL.md
```

**Step 2: Commit**

```bash
git commit -m "feat(plan-and-execute): add update-architecture-docs inner skill"
```

**Step 3: Verify**

```bash
ls plugins/denubis-plan-and-execute/skills/update-architecture-docs/
```

Expected: SKILL.md and 7 template files from Phase 1.
<!-- END_TASK_9 -->
