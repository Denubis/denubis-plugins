# Project Context Inventory Implementation Plan

**Goal:** Create a project context inventory system that helps Claude Code subagents discover project-specific conventions

**Architecture:** Python discovery script scans project for CLAUDE.md files, MCP configs, and installed plugins, then outputs structured markdown. Command invokes script, wrapper skill filters and injects context into subagent prompts.

**Tech Stack:** Python 3.13+, shell scripts, Claude Code skills/commands

**Scope:** 6 phases from original design (phases 1-6)

**Codebase verified:** 2026-01-30

---

## Phase 4: Skill Integration

**Goal:** Key skills call wrapper before spawning subagents

**Codebase verification findings:**
- `executing-an-implementation-plan` has 5 Task invocations (lines 147, 176, 236, 282, 390)
- `brainstorming` does NOT use Task tool - it references agents by name in documentation
- `writing-implementation-plans` has 1 Task invocation (line 752) for code-reviewer
- `requesting-code-review` has 4 Task invocations (lines 60, 88, 120, 151)
- All Task invocations pass context via `<parameter name="prompt">` with key-value pairs
- Existing pattern: include file paths as absolute paths in prompt parameters

**Design adjustment:** Since brainstorming doesn't use Task tool, we'll add project context guidance to its research protocol section instead.

**Filter strategy:** Per design, skills pass `PROJECT_INVENTORY` path to subagents. The subagent reads the full file and applies filtering based on its role:
- Implementation agents (task-implementor, bug-fixer): Read full inventory
- Code reviewers: Read full inventory for context
- Brainstorming: Documented to consult inventory during research (pattern-based, not Task invocation)

The inject-project-context skill documents filter definitions. Subagents follow these when reading the inventory.

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Update executing-an-implementation-plan to inject project context

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md`

**Step 1: Add project context injection section**

After the "Before Starting" section (around line 50), add a new section:

```markdown
## Project Context Injection

Before dispatching subagents, check for project context:

1. Check if `.ed3d/project-inventory.md` exists in the project root
2. If it exists, include its path in subagent prompts:

```
PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md]

Read this file first to understand project conventions:
- Command patterns (how to run tests, linting, etc.)
- MCP servers and plugins available
- CLAUDE.md/AGENTS.md file locations
```

If the inventory file does not exist, proceed without it. Do not error.
```

**Step 2: Update task-implementor dispatch template (line 147)**

Find the block starting at line 147 and update the prompt parameter to include PROJECT_INVENTORY:

Before:
```
<parameter name="prompt">
  Implement Task N from the phase file.

  Phase file: [absolute path to phase file]
  Task number: N
```

After:
```
<parameter name="prompt">
  Implement Task N from the phase file.

  PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md, or "None" if file does not exist]

  Phase file: [absolute path to phase file]
  Task number: N
```

**Step 3: Update subcomponent dispatch template (line 176)**

Same change - add PROJECT_INVENTORY line after opening of prompt:

```
<parameter name="prompt">
  Implement Subcomponent A (Tasks 3, 4, 5) from the phase file.

  PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md, or "None" if file does not exist]

  Phase file: [absolute path to phase file]
  Tasks: 3, 4, 5 (look for `<!-- START_SUBCOMPONENT_A -->`)
```

**Step 4: Update bug-fixer dispatch template (line 236)**

Add PROJECT_INVENTORY to the bug-fixer prompt:

```
<parameter name="prompt">
  Fix the issues found by code review.

  PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md, or "None" if file does not exist]

  Code reviewer found these issues:
  [list issues by category]
```

**Step 5: Verify changes**

```bash
grep -n "PROJECT_INVENTORY" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
```

Expected: Multiple lines showing PROJECT_INVENTORY in different dispatch templates.

**Step 6: Commit**

```bash
git add plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
git commit -m "feat(plan-and-execute): add project context injection to executing-an-implementation-plan"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Update requesting-code-review to inject project context

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md`

**Step 1: Add project context section**

After the overview section, add:

```markdown
## Project Context

Before dispatching code-reviewer, check for project context:

1. Check if `.ed3d/project-inventory.md` exists in the project root
2. If it exists, include its path in the code-reviewer prompt

If the inventory file does not exist, proceed without it.
```

**Step 2: Update code-reviewer dispatch template (line 60)**

Add PROJECT_INVENTORY to the prompt:

Before:
```
<parameter name="prompt">
  Use template at requesting-code-review/code-reviewer.md

  WHAT_WAS_IMPLEMENTED: [summary of implementation]
```

After:
```
<parameter name="prompt">
  Use template at requesting-code-review/code-reviewer.md

  PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md, or "None" if file does not exist]

  WHAT_WAS_IMPLEMENTED: [summary of implementation]
```

**Step 3: Update bug-fixer dispatch template (line 120)**

Add PROJECT_INVENTORY to the prompt:

```
<parameter name="prompt">
  Fix issues from code review.

  PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md, or "None" if file does not exist]

  Code reviewer found these issues:
  [list all issues - Critical, Important, and Minor]
```

**Step 4: Verify changes**

```bash
grep -n "PROJECT_INVENTORY" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md
```

Expected: Lines showing PROJECT_INVENTORY in code-reviewer and bug-fixer dispatch templates.

**Step 5: Commit**

```bash
git add plugins/denubis-plan-and-execute/skills/requesting-code-review/SKILL.md
git commit -m "feat(plan-and-execute): add project context injection to requesting-code-review"
```
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-4) -->

<!-- START_TASK_3 -->
### Task 3: Update writing-implementation-plans to inject project context

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/writing-implementation-plans/SKILL.md`

**Step 1: Update code-reviewer dispatch template (line 752)**

Add PROJECT_INVENTORY alongside the existing parameters:

Before:
```
<parameter name="prompt">
  Review the implementation plan for completeness and alignment with the design.

  DESIGN_PLAN: [path to design plan, e.g., docs/design-plans/YYYY-MM-DD-feature.md]

  IMPLEMENTATION_GUIDANCE: [absolute path to .ed3d/implementation-plan-guidance.md, or "None" if file does not exist]
```

After:
```
<parameter name="prompt">
  Review the implementation plan for completeness and alignment with the design.

  DESIGN_PLAN: [path to design plan, e.g., docs/design-plans/YYYY-MM-DD-feature.md]

  PROJECT_INVENTORY: [absolute path to .ed3d/project-inventory.md, or "None" if file does not exist]

  IMPLEMENTATION_GUIDANCE: [absolute path to .ed3d/implementation-plan-guidance.md, or "None" if file does not exist]
```

**Step 2: Verify changes**

```bash
grep -n "PROJECT_INVENTORY" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/skills/writing-implementation-plans/SKILL.md
```

Expected: Line showing PROJECT_INVENTORY in the code-reviewer dispatch.

**Step 3: Commit**

```bash
git add plugins/denubis-plan-and-execute/skills/writing-implementation-plans/SKILL.md
git commit -m "feat(plan-and-execute): add project context injection to writing-implementation-plans"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Update brainstorming to reference project context

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/brainstorming/SKILL.md`

**Note:** Brainstorming does not use the Task tool directly. It references agents by name in documentation. We add guidance for consulting project inventory during research.

**Step 1: Add project context section in Research Protocol**

After the "Research Protocol" section header (around line 95), add a new subsection:

```markdown
### Project Context Awareness

Before starting research, check for project context inventory:

1. Check if `.ed3d/project-inventory.md` exists
2. If it exists, read it to understand:
   - Available command patterns (how this project runs tests, linting, etc.)
   - MCP servers and plugins available
   - Location of CLAUDE.md/AGENTS.md files

This context helps:
- Ensure design aligns with existing project conventions
- Know what tools are available for the design
- Understand project structure before investigating codebase

If no inventory exists, proceed with codebase investigation as usual.
```

**Step 2: Verify changes**

```bash
grep -n "project-inventory" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/skills/brainstorming/SKILL.md
```

Expected: Line showing reference to `.ed3d/project-inventory.md`.

**Step 3: Commit**

```bash
git add plugins/denubis-plan-and-execute/skills/brainstorming/SKILL.md
git commit -m "feat(plan-and-execute): add project context awareness to brainstorming"
```
<!-- END_TASK_4 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_TASK_5 -->
### Task 5: Verify Phase 4 complete

**Files:**
- Read: All four modified skill files

**Step 1: Verify all skills have project context integration**

```bash
for skill in executing-an-implementation-plan requesting-code-review writing-implementation-plans brainstorming; do
  echo "=== $skill ==="
  grep -c "project-inventory\|PROJECT_INVENTORY" /home/brian/people/Brian/brian-ed3d-plugins/plugins/denubis-plan-and-execute/skills/$skill/SKILL.md
done
```

Expected:
```
=== executing-an-implementation-plan ===
4 (or more - section + 3 dispatch templates)
=== requesting-code-review ===
3 (or more - section + 2 dispatch templates)
=== writing-implementation-plans ===
1 (or more - 1 dispatch template)
=== brainstorming ===
1 (or more - research protocol section)
```

**Step 2: Verify Phase 4 complete**

Check:
- [x] executing-an-implementation-plan includes PROJECT_INVENTORY in task-implementor and bug-fixer dispatches
- [x] requesting-code-review includes PROJECT_INVENTORY in code-reviewer and bug-fixer dispatches
- [x] writing-implementation-plans includes PROJECT_INVENTORY in code-reviewer dispatch
- [x] brainstorming references project-inventory in research protocol

Phase 4 is complete when all four skills integrate with the project context system.
<!-- END_TASK_5 -->
