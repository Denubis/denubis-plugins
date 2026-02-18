# Architecture Documentation System — Phase 4: Migration and Integration

**Goal:** Migrate `docs/database.md` path references to `docs/architecture/database.md` in two existing skill/agent files. Replace the "Before Commit: Database Documentation" section in `writing-design-plans` with the new "Before Commit: Architecture Documentation" section. Add version bump and changelog entry.

**Architecture:** Edit existing files to update path references. Add new "Before Commit: Architecture Documentation" section to `writing-design-plans` after proleptic challenge, removing the old "Before Commit: Database Documentation" section (superseded by the architecture docs step). Path migration for `writing-design-plans` is handled entirely by section replacement (Tasks 4-5), not by individual line edits — all `docs/database.md` references in that file are inside the section being deleted. Historical/documentation files (design plans, implementation plans) are NOT updated — they document the migration itself. The plugin's own CHANGELOG.md gets a release entry.

**Tech Stack:** Markdown edits

**Scope:** Phase 4 of 4

**Codebase verified:** 2026-02-18

---

## Acceptance Criteria Coverage

This phase implements and tests:

### maintain-arch-docs.AC5: Database documentation path migration
- **maintain-arch-docs.AC5.1 Success:** `writing-design-plans` references `docs/architecture/database.md` instead of `docs/database.md`
- **maintain-arch-docs.AC5.2 Success:** `dba-reviewer` references `docs/architecture/database.md` in Step 7
- **maintain-arch-docs.AC5.3 Success:** `howto-develop-with-postgres` references `docs/architecture/database.md` in template and lifecycle sections
- **maintain-arch-docs.AC5.4 Success:** No remaining references to `docs/database.md` exist in the plugin (verified by grep)

### maintain-arch-docs.AC6: Design workflow integration
- **maintain-arch-docs.AC6.1 Success:** `writing-design-plans` calls `update-architecture-docs` after proleptic challenge, before commit (sequence: Dependency Rationale → Proleptic Challenge → Architecture Documentation → Commit)
- **maintain-arch-docs.AC6.2 Success:** Architecture doc changes are included in the design plan commit
- **maintain-arch-docs.AC6.3 Edge:** When `update-architecture-docs` is called but the target project has no `docs/architecture/`, bootstrap mode triggers automatically

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->
<!-- START_TASK_1 -->
### Task 1: Update `dba-reviewer` — migrate database.md path references

**Verifies:** maintain-arch-docs.AC5.2

**Files:**
- Modify: `plugins/denubis-plan-and-execute/agents/dba-reviewer.md`

**Implementation:**

Update all `docs/database.md` references to `docs/architecture/database.md` at these locations:

- **Line 3:** YAML description `Validates and updates docs/database.md` → `Validates and updates docs/architecture/database.md`
- **Line 111:** section heading `### Step 7: Database Documentation (\`docs/database.md\`)` → `### Step 7: Database Documentation (\`docs/architecture/database.md\`)`
- **Line 113:** `Check if \`docs/database.md\` exists` → `Check if \`docs/architecture/database.md\` exists`
- **Line 140:** template `docs/database.md` → `docs/architecture/database.md`
- **Line 141:** template `docs/database.md` → `docs/architecture/database.md`
- **Line 142:** template `docs/database.md` → `docs/architecture/database.md`
- **Line 179:** output template `docs/database.md` → `docs/architecture/database.md`
- **Line 194:** checklist `Validate \`docs/database.md\`` → `Validate \`docs/architecture/database.md\``
- **Line 208:** rule `\`docs/database.md\`` → `\`docs/architecture/database.md\``

**Verification:**
```bash
grep -n "docs/database.md" plugins/denubis-plan-and-execute/agents/dba-reviewer.md
```
Expected: No output (zero matches).

No commit yet.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Update `howto-develop-with-postgres` — migrate database.md path references

**Verifies:** maintain-arch-docs.AC5.3

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/howto-develop-with-postgres/SKILL.md`

**Implementation:**

Update all `docs/database.md` references to `docs/architecture/database.md` at these locations:

- **Line 476:** section heading `## Database Documentation (\`docs/database.md\`)` → `## Database Documentation (\`docs/architecture/database.md\`)`
- **Line 478:** prose `\`docs/database.md\`` → `\`docs/architecture/database.md\``
- **Line 580:** table header `Action on \`docs/database.md\`` → `Action on \`docs/architecture/database.md\``
- **Line 582:** table row `Create \`docs/database.md\`` → `Create \`docs/architecture/database.md\``
- **Lines 591-596:** table rows — update each `\`docs/database.md\`` to `\`docs/architecture/database.md\``

**Verification:**
```bash
grep -n "docs/database.md" plugins/denubis-plan-and-execute/skills/howto-develop-with-postgres/SKILL.md
```
Expected: No output (zero matches).
<!-- END_TASK_2 -->
<!-- END_SUBCOMPONENT_A -->

<!-- START_TASK_3 -->
### Task 3: Commit path migration

**Files:**
- `plugins/denubis-plan-and-execute/agents/dba-reviewer.md`
- `plugins/denubis-plan-and-execute/skills/howto-develop-with-postgres/SKILL.md`

**Step 1: Stage and commit**

```bash
git add plugins/denubis-plan-and-execute/agents/dba-reviewer.md
git add plugins/denubis-plan-and-execute/skills/howto-develop-with-postgres/SKILL.md
git commit -m "refactor(plan-and-execute): migrate docs/database.md references to docs/architecture/database.md"
```

Note: `writing-design-plans` is NOT included here — all its `docs/database.md` references are inside the "Before Commit: Database Documentation" section, which is deleted entirely in Task 5. Path migration for that file is handled by section replacement (Tasks 4-5).
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Add "Before Commit: Architecture Documentation" section to `writing-design-plans`

**Verifies:** maintain-arch-docs.AC6.1, maintain-arch-docs.AC6.2, maintain-arch-docs.AC6.3

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`

**Implementation:**

Add a new section **after** the "Before Commit: Proleptic Challenge" section and **before** the "After Proleptic Challenge: Commit" section.

New section content:

```markdown
## Before Commit: Architecture Documentation

**After proleptic challenge is resolved,** invoke the architecture documentation skill.

**REQUIRED SUB-SKILL:** Use denubis-plan-and-execute:update-architecture-docs

Announce: "I'm using the update-architecture-docs skill to assess architecture documentation."

Pass the design plan file path as the artifact:

The inner skill will:
1. Read current `docs/architecture/` (or detect its absence for bootstrap)
2. Parse the design plan for architecture-relevant content
3. Detect contradictions with existing docs (may HALT)
4. Propose changes grouped by doc type
5. Write approved changes

**Include architecture doc changes in the design plan commit:**

```bash
git add docs/design-plans/YYYY-MM-DD-<topic>.md docs/architecture/ docs/dependency-rationale.md
```

**If no architecture changes detected:** The inner skill reports this and exits. Continue to commit.

**If bootstrap triggered:** The inner skill scaffolds `docs/architecture/` and proposes initial files. All created files are included in the commit.
```

Also update the "After Proleptic Challenge: Commit" section's git add command to include `docs/architecture/`:

```bash
git add docs/design-plans/YYYY-MM-DD-<topic>.md docs/architecture/ docs/dependency-rationale.md
```

**Verification:** Section exists between proleptic challenge and commit sections. Git add command includes `docs/architecture/`.

No commit yet — commit with Task 5.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Remove "Before Commit: Database Documentation" section from `writing-design-plans`

**Verifies:** maintain-arch-docs.AC5.1, maintain-arch-docs.AC6.1

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`

**Implementation:**

Remove the entire "Before Commit: Database Documentation" section (lines ~635-677). This section is replaced by the "Before Commit: Architecture Documentation" step added in Task 4.

The `update-architecture-docs` inner skill handles database.md as part of its broader scope — it reads the design plan's content for database-related signals and proposes updates to `docs/architecture/database.md` when needed.

This deletion also completes AC5.1: all `docs/database.md` references in `writing-design-plans` were inside this section. Removing it eliminates stale path references, and the new Architecture Documentation section (Task 4) uses the correct `docs/architecture/` path.

Also update any references to this removed section elsewhere in the skill file (e.g., the "Common Rationalizations" table or "Integration with Workflow" section).

After both Tasks 4 and 5, the final before-commit sequence in `writing-design-plans` is:

1. Before Commit: Dependency Rationale (existing)
2. Before Commit: Proleptic Challenge (existing)
3. Before Commit: Architecture Documentation (new, from Task 4)
4. After Proleptic Challenge: Commit (existing)

**Verification:**
```bash
grep -n "Before Commit: Database Documentation" plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md
```
Expected: No output (section removed).
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Commit integration changes

**Files:**
- `plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md`

**Step 1: Verify no remaining references across plugin**

```bash
grep -rn "docs/database\.md" plugins/denubis-plan-and-execute/
```

Expected: No output. All references migrated or removed.

**Step 2: Stage and commit**

```bash
git add plugins/denubis-plan-and-execute/skills/writing-design-plans/SKILL.md
git commit -m "feat(plan-and-execute): integrate update-architecture-docs into design workflow"
```
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Version bump and changelog

**Files:**
- Modify: `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` (bump version)
- Modify: `.claude-plugin/marketplace.json` (sync version)
- Modify: `CHANGELOG.md` (add release entry)

**Step 1: Bump plugin version**

Read `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json` and increment the minor version (this is a feature addition). Update the version field.

**Step 2: Sync marketplace version**

Read `.claude-plugin/marketplace.json` and update the `denubis-plan-and-execute` entry to match the new version.

**Step 3: Add changelog entry**

Add entry at the top of `CHANGELOG.md` (after the `# Changelog` heading):

```markdown
## [denubis-plan-and-execute] [NEW_VERSION]

Architecture documentation maintenance system.

**New:**
- `update-architecture-docs` inner skill for detecting contradictions and proposing architecture doc changes
- `maintain-architecture` wrapper skill and `/maintain-architecture` command for standalone maintenance sessions
- Architecture doc templates (DFD context, DFD process, database, personae, glossary, constraints, state)
- `docs/architecture/` directory convention with hierarchical DFD numbering

**Changed:**
- `writing-design-plans` now invokes `update-architecture-docs` after proleptic challenge
- `dba-reviewer` and `howto-develop-with-postgres` reference `docs/architecture/database.md` instead of `docs/database.md`
- Removed "Before Commit: Database Documentation" section from `writing-design-plans` (superseded by architecture docs step)
```

**Step 4: Stage and commit**

```bash
git add plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
git add .claude-plugin/marketplace.json
git add CHANGELOG.md
git commit -m "chore: bump denubis-plan-and-execute version for architecture docs feature"
```

**Step 5: Final verification**

```bash
ls plugins/denubis-plan-and-execute/skills/update-architecture-docs/
ls plugins/denubis-plan-and-execute/skills/maintain-architecture/
ls plugins/denubis-plan-and-execute/commands/maintain-architecture.md
grep -rn "docs/database\.md" plugins/denubis-plan-and-execute/
```

Expected: Template files and SKILL.md in update-architecture-docs, SKILL.md in maintain-architecture, command file exists, no stale database.md references.
<!-- END_TASK_7 -->
