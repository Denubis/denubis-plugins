## Phase 6: Guidance File Support

**Goal:** Load project-specific guidance from `.ed3d/` directory

**Dependencies:** None (can be developed in parallel)

**Done when:** Guidance files are loaded at appropriate points and `/how-to-customize` command documents the feature

---

<!-- START_SUBCOMPONENT_A (tasks 1-4) -->

<!-- START_TASK_1 -->
### Task 1: Add Guidance Loading to starting-a-design-plan

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/starting-a-design-plan/SKILL.md`

**Location:** Between "### Phase 1: Context Gathering" (ends at line 77 with "Mark Phase 1 as completed when you have initial context.") and "### Phase 2: Clarification" (starts at line 79).

**Step 1: Add guidance check section**

Insert after line 77 ("Mark Phase 1 as completed when you have initial context."), before "### Phase 2: Clarification":

```markdown
### Between Phase 1 and Phase 2: Check for Project Guidance

Before clarification, check for project-specific design guidance.

**Check if `.ed3d/design-plan-guidance.md` exists:**

Use the Read tool to check if `.ed3d/design-plan-guidance.md` exists in the session's working directory.

**If the file exists:**

1. Use TaskCreate to add: "Read project design guidance from [absolute path to .ed3d/design-plan-guidance.md]"
   - Set this task as blocked by Phase 1 (Context Gathering)
   - Update Phase 2 (Clarification) to be blocked by this new task
2. Mark the task in_progress
3. Read the file and incorporate the guidance into your understanding
4. Mark the task completed
5. Proceed to Phase 2

**If the file does not exist:**

Proceed directly to Phase 2. Do not create a task or mention the missing file.

**What project guidance provides:**
- Domain-specific terminology to use in clarification
- Architectural constraints or preferences
- Technologies that are required, preferred, or forbidden
- Stakeholders and their priorities
- Project conventions that designs must follow

The guidance informs what questions you ask during clarification.
```

**Step 2: Verify the modification**

```bash
grep -n "design-plan-guidance" plugins/denubis-plan-and-execute/skills/starting-a-design-plan/SKILL.md
```

Expected: Shows references to guidance file loading

**Step 3: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/starting-a-design-plan/SKILL.md
git commit -m "feat(plan-and-execute): add design guidance loading to starting-a-design-plan

Load .ed3d/design-plan-guidance.md before clarification phase
when it exists. Graceful degradation if file missing.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add Guidance Loading to starting-an-implementation-plan

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/starting-an-implementation-plan/SKILL.md`

**Location:** After Branch Setup, before Planning

**Step 1: Add guidance check section**

Insert after "Mark 'Branch setup' task as completed":

```markdown
### Check for Implementation Guidance

After branch setup, check for project-specific implementation guidance.

**Check if `.ed3d/implementation-plan-guidance.md` exists:**

Use the Read tool to check if `.ed3d/implementation-plan-guidance.md` exists in the session's working directory.

**If the file exists:**

1. Use TaskCreate to add: "Read project implementation guidance from [absolute path to .ed3d/implementation-plan-guidance.md]"
   - Set this task as blocked by "Branch setup"
   - Update "Create implementation plan" to be blocked by this new task
2. Mark the task in_progress
3. Read the file and incorporate the guidance into your understanding
4. Mark the task completed
5. Proceed to Planning

**If the file does not exist:**

Proceed directly to Planning. Do not create a task or mention the missing file.

**What implementation guidance provides:**
- Coding standards and conventions
- Testing requirements and patterns
- Review criteria beyond defaults
- Project-specific quality gates
```

**Step 2: Update task creation section**

Update the orchestration task tracker to show conditional guidance task:

```markdown
TaskCreate: "Branch setup"
(conditional) TaskCreate: "Read project implementation guidance from [absolute path]"
  → TaskUpdate: addBlockedBy: [Branch setup]
  → (only if .ed3d/implementation-plan-guidance.md exists)
TaskCreate: "Create implementation plan"
  → TaskUpdate: addBlockedBy: [Branch setup] (or [Read guidance] if it exists)
```

**Step 3: Verify the modification**

```bash
grep -n "implementation-plan-guidance" plugins/denubis-plan-and-execute/skills/starting-an-implementation-plan/SKILL.md
```

Expected: Shows references to guidance file loading (multiple lines)

**Step 4: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/starting-an-implementation-plan/SKILL.md
git commit -m "feat(plan-and-execute): add implementation guidance loading

Load .ed3d/implementation-plan-guidance.md after branch setup
when it exists. Graceful degradation if file missing.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Pass Guidance to Code Reviewers in executing-an-implementation-plan

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md`

**Location:**
- Phase discovery: "### 1. Discover Phases" section (around lines 56-86)
- Code review invocation: "#### 3c. Code Review for Phase" section (around lines 199-261)

**Step 1: Add guidance discovery at plan start**

In the "### 1. Discover Phases" section (after the grep command example around line 68), add:

```markdown
**Check for implementation guidance:**

After discovering phases, check if `.ed3d/implementation-plan-guidance.md` exists in the project root:

```bash
# Check for implementation guidance (note the absolute path for later use)
ls [project-root]/.ed3d/implementation-plan-guidance.md
```

If the file exists, note its **absolute path** for use during code reviews. If it doesn't exist, proceed without it—do not pass a nonexistent path to reviewers.
```

**Step 2: Update code review invocation**

In the phase code review section, add IMPLEMENTATION_GUIDANCE parameter:

```markdown
When dispatching code-reviewer for phase review:

- WHAT_WAS_IMPLEMENTED: All tasks from this phase
- PLAN_OR_REQUIREMENTS: All tasks from this phase
- BASE_SHA: commit before phase started
- HEAD_SHA: current commit
- IMPLEMENTATION_GUIDANCE: absolute path to `.ed3d/implementation-plan-guidance.md` (**only if it exists**—omit entirely if the file doesn't exist)

The implementation guidance file contains project-specific coding standards, testing requirements, and review criteria. When provided, the code reviewer should read it and apply those standards during review.
```

**Step 3: Verify the modification**

```bash
grep -n "IMPLEMENTATION_GUIDANCE" plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
```

Expected: Shows references to IMPLEMENTATION_GUIDANCE parameter (at least 2 occurrences)

**Step 4: Commit the change**

```bash
git add plugins/denubis-plan-and-execute/skills/executing-an-implementation-plan/SKILL.md
git commit -m "feat(plan-and-execute): pass implementation guidance to code reviewers

Discover .ed3d/implementation-plan-guidance.md at plan start.
Pass absolute path to code reviewers during phase reviews.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Create /how-to-customize Command

**Files:**
- Create: `plugins/denubis-plan-and-execute/commands/how-to-customize.md`

**Step 1: Create command file**

```markdown
---
description: Explains how to customize design and implementation plans with project-specific guidance
---

# Customizing Plan-and-Execute

You can provide project-specific guidance that shapes how design and implementation plans are created for your project.

## Guidance Files

Create a `.ed3d/` directory in your project root with these optional files:

### `.ed3d/design-plan-guidance.md`

Loaded before the clarification phase of `/start-design-plan`.

**What to include:**
- **Domain terminology**: Define terms specific to your project
- **Architectural constraints**: Required patterns, forbidden approaches
- **Technology preferences**: What to use, what to avoid
- **Stakeholder context**: Who cares about what
- **Scope boundaries**: What's typically in/out of scope

### `.ed3d/implementation-plan-guidance.md`

Loaded when starting an implementation plan and again during code reviews.

**What to include:**
- **Coding standards**: Naming conventions, file organization
- **Testing requirements**: Coverage expectations, testing patterns
- **Review criteria**: Quality gates beyond the defaults
- **Commit conventions**: Message format, granularity
- **Project-specific patterns**: How things are done here

## Example Files

### `.ed3d/design-plan-guidance.md`

```markdown
# Design Guidance for MyProject

## Domain Terms
- **Widget**: User-configurable dashboard component (not a generic UI element)
- **Pipeline**: BullMQ-based async job system

## Architectural Constraints
- All services use FCIS pattern (functional core, imperative shell)
- Database access only through repository pattern in `src/repositories/`
- No direct HTTP calls from business logic

## Technology Stack
- **Required**: TypeScript strict mode, PostgreSQL, Redis
- **Avoid**: ORMs (we use raw SQL with type generation)
- **Decided**: Auth0 for authentication (don't propose alternatives)

## Scope Defaults
- Admin UI is always out of scope unless explicitly requested
- Migrations are in scope for any schema changes
```

### `.ed3d/implementation-plan-guidance.md`

```markdown
# Implementation Guidance for MyProject

## Coding Standards
- All files must have FCIS pattern comment at top
- Prefer `type` over `interface` unless extending
- No default exports

## Testing Requirements
- Unit tests for all pure functions
- Integration tests for repository methods
- E2E tests only for critical user flows
- Test files colocated as `*.test.ts`

## Review Criteria
- No `any` types without justification comment
- All database queries must use parameterized statements
- Error messages must not leak internal details

## Commit Conventions
- Conventional commits: feat:, fix:, chore:, docs:
- One logical change per commit
- Tests and implementation in same commit
```

## Notes

- If the guidance files don't exist, the standard workflow proceeds without them
- Guidance is incorporated into context, not shown to you directly
- Update guidance files as your project evolves
- The `/how-to-customize` command shows this help at any time
```

**Step 2: Verify the command was created**

```bash
head -5 plugins/denubis-plan-and-execute/commands/how-to-customize.md
```

Expected: YAML frontmatter with description

**Step 3: Commit the command**

```bash
git add plugins/denubis-plan-and-execute/commands/how-to-customize.md
git commit -m "feat(plan-and-execute): add /how-to-customize command

Documents .ed3d/ guidance files with examples for design
and implementation customization.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```
<!-- END_TASK_4 -->

<!-- END_SUBCOMPONENT_A -->
