## Phase 7: Version and Documentation Updates

**Goal:** Update plugin version, marketplace, changelog, and README

**Dependencies:** Phases 1-6 complete

**Done when:** Version updated, changelog entry added, README documents proleptic reasoning and UAT gates

---

<!-- START_SUBCOMPONENT_A (tasks 1-5) -->

<!-- START_TASK_1 -->
### Task 1: Bump Plugin Version

**Files:**
- Modify: `plugins/denubis-plan-and-execute/.claude-plugin/plugin.json`

**Step 1: Update version**

Change version from `2.0.0` to `2.1.0`:

```json
{
    "name": "denubis-plan-and-execute",
    "description": "Planning and execution workflows for Claude Code. Slow and steady. Based on obra/superpowers.",
    "version": "2.1.0",
    ...
}
```

**Step 2: Verify the change**

```bash
grep '"version"' plugins/denubis-plan-and-execute/.claude-plugin/plugin.json
```

Expected: `"version": "2.1.0"`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Sync Marketplace Version

**Files:**
- Modify: `.claude-plugin/marketplace.json`

**Step 1: Update denubis-plan-and-execute version**

Find the denubis-plan-and-execute entry (around line 23-32) and update version:

```json
{
    "name": "denubis-plan-and-execute",
    "description": "Planning and execution workflows for Claude Code. Slow and steady.",
    "version": "2.1.0",
    ...
}
```

**Step 2: Verify the change**

```bash
grep -A 3 '"denubis-plan-and-execute"' .claude-plugin/marketplace.json | grep version
```

Expected: Shows `"version": "2.1.0"`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add Changelog Entry

**Files:**
- Modify: `CHANGELOG.md`

**Step 1: Add changelog entry at top (after `# Changelog` heading)**

Insert after line 1:

```markdown
## denubis-plan-and-execute 2.1.0

Proleptic reasoning and human UAT gates.

**New:**
- `proleptic-challenger` agent - Generates counterarguments at phase transitions based on Kudina, Ballsun-Stanton & Alfano (2025) proleptic reasoning framework (DOI: 10.1007/s44204-025-00247-1)
- `proleptic-challenge` skill - Documents when and how to invoke the challenger (design finalisation, between phases, during UAT)
- `human-uat-gate` skill - Presents acceptance criteria and waits for explicit human verification after code review
- `/how-to-customize` command - Documents `.ed3d/` guidance files for project-specific customisation

**Changed:**
- `writing-design-plans` now invokes proleptic challenge before committing design
- `executing-an-implementation-plan` now includes proleptic challenge between phases and UAT gate after code review
- `requesting-code-review` now leads to proleptic challenge → UAT gate flow
- `starting-a-design-plan` loads `.ed3d/design-plan-guidance.md` before clarification (if exists)
- `starting-an-implementation-plan` loads `.ed3d/implementation-plan-guidance.md` at start (if exists)
- Code reviewers now receive implementation guidance for project-specific standards (if exists)

**Philosophy:**
- Proleptic reasoning forces deliberate evaluation before phase transitions
- "Drunk tutor" framing: both proposals AND counterarguments may be flawed
- Human UAT ensures implementations meet actual needs, not just automated checks
- Guidance files enable project-specific customisation without modifying plugin code

```

**Step 2: Verify the entry**

```bash
head -30 CHANGELOG.md
```

Expected: Shows the new 2.1.0 entry
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Update README with New Features

**Files:**
- Modify: `plugins/denubis-plan-and-execute/README.md`

**Step 1: Add Proleptic Reasoning section**

Insert after "## Phase 3: Execution" section (ends around line 111 with "**Output:** Working, reviewed code on your feature branch with clean commits."), before "## Why This Structure?" (starts at line 114):

```markdown
---

## Proleptic Reasoning and UAT Gates

This plugin implements proleptic reasoning as a workflow discipline, based on [Kudina, Ballsun-Stanton & Alfano (2025)](https://doi.org/10.1007/s44204-025-00247-1).

**What is proleptic reasoning?** Anticipating objections to a position, articulating them charitably, and responding preemptively. The value is not in the counterarguments being correct - it's in forcing deliberate evaluation before committing.

**When it fires:**
- Before design is committed (design → implementation transition)
- Between implementation phases
- During UAT (before declaring complete)

**The "drunk tutor" framing:** Both proposals AND counterarguments may be flawed. The human must evaluate both critically. This prevents premature consensus and forces thinking.

**Human UAT gates:** After code review passes, the workflow stops and presents acceptance criteria from the Definition of Done. The human must explicitly verify the implementation meets requirements before proceeding. Rejection loops back to fix and re-verify.

---

## Project Customisation

Create optional guidance files in `.ed3d/` at your project root:

- **`.ed3d/design-plan-guidance.md`** - Domain terminology, architectural constraints, technology preferences. Loaded before clarification.
- **`.ed3d/implementation-plan-guidance.md`** - Coding standards, testing requirements, review criteria. Loaded at plan start and during code reviews.

Run `/how-to-customize` for examples and details.

```

**Step 2: Update subagent table**

Add proleptic-challenger to the subagent table. The "## Subagents" section starts at line 156 and the table runs from lines 159-168. Insert a new row in the table:

```markdown
| **proleptic-challenger** | denubis-plan-and-execute | Generates counterarguments at phase transitions |
```

**Step 3: Verify the changes**

```bash
grep -n "proleptic" plugins/denubis-plan-and-execute/README.md
```

Expected: Shows multiple references to proleptic reasoning section
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Commit All Version and Documentation Updates

**Files:**
- All files modified in Tasks 1-4

**Step 1: Stage all changes**

```bash
git add plugins/denubis-plan-and-execute/.claude-plugin/plugin.json \
        .claude-plugin/marketplace.json \
        CHANGELOG.md \
        plugins/denubis-plan-and-execute/README.md
```

**Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
chore(plan-and-execute): bump version to 2.1.0

Adds proleptic reasoning and human UAT gates:
- proleptic-challenger agent at phase transitions
- human-uat-gate skill for explicit verification
- Project guidance via .ed3d/ files
- /how-to-customize command

Based on Kudina, Ballsun-Stanton & Alfano (2025)
DOI: 10.1007/s44204-025-00247-1

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_A -->
