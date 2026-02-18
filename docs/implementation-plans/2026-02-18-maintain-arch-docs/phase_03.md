# Architecture Documentation System — Phase 3: Wrapper Skill — `maintain-architecture`

**Goal:** Create the user-invocable wrapper skill that orchestrates standalone architecture documentation maintenance sessions, plus its command registration file.

**Architecture:** SKILL.md with `user-invocable: true` following the `starting-a-design-plan` orchestrator pattern. Dispatches subagents for investigation, asks one question at a time, calls `update-architecture-docs` inner skill for proposals. Command file registers the skill as a slash command.

**Tech Stack:** Markdown (SKILL.md, command .md)

**Scope:** Phase 3 of 4

**Codebase verified:** 2026-02-18

---

## Acceptance Criteria Coverage

This phase implements and tests:

### maintain-arch-docs.AC4: Wrapper skill runs standalone maintenance sessions
- **maintain-arch-docs.AC4.1 Success:** Wrapper computes git diff baseline appropriate to context (branch: merge-base; main: last architecture commit)
- **maintain-arch-docs.AC4.2 Success:** Wrapper dispatches subagents to read code and architecture files, reporting what exists, what changed, and what's missing
- **maintain-arch-docs.AC4.3 Success:** Wrapper asks one pointed question at a time to fill gaps or resolve conflicts
- **maintain-arch-docs.AC4.4 Success:** Wrapper invokes inner skill with diff baseline to propose and apply updates
- **maintain-arch-docs.AC4.5 Edge:** When no changes are detected in the diff, wrapper reports "architecture docs appear current" and exits

---

<!-- START_TASK_1 -->
### Task 1: Create wrapper SKILL.md with frontmatter and overview

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`

**Implementation:**

Create the SKILL.md with frontmatter following the user-invocable pattern:

```yaml
---
name: maintain-architecture
description: Use for standalone architecture documentation maintenance - computes git diff baselines, dispatches subagents to read code and docs, asks targeted questions, and invokes update-architecture-docs to propose changes
user-invocable: true
---
```

Overview section states:
- Core principle: Scope → Investigate → Question → Update. Understand what changed, ask targeted questions, propose updates.
- Announce at start: "I'm using the maintain-architecture skill to review and update architecture documentation."
- This skill orchestrates maintenance sessions by dispatching subagents and calling the `update-architecture-docs` inner skill.

Include workflow status line table:

| Transition | `--skill` | `--context` |
|------------|-----------|-------------|
| Entry | `maintain-architecture` | `scoping changes` |
| Computing diff baseline | | `computing baseline` |
| Dispatching investigators | | `investigating codebase` |
| Question to user | | `asking: <topic>` |
| Calling inner skill | | `updating docs` |
| Between steps (Claude working) | | `""` |

**Verification:** File exists with correct frontmatter.

No commit yet.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add scope determination section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`

**Implementation:**

Add "Scope Determination" section. On entry, ask the user what kind of session:

```
Use AskUserQuestion:
Question: "What kind of architecture documentation review?"
Options:
  - "Review changes on this branch" (diff from merge-base with main)
  - "Review recent changes on main" (diff since last architecture update)
  - "Full sweep" (review all architecture docs against current codebase)
  - "Specific area" (I'll describe what to review)
```

Document what each option means for baseline computation and investigation scope.

**Verification:** Section exists with scope options.

No commit yet.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add git diff baseline computation section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`

**Implementation:**

Add "Computing Baseline" section with the exact bash commands:

| Scope | Command | What it produces |
|-------|---------|-----------------|
| Branch changes | `git diff $(git merge-base HEAD main)` | All changes since branch diverged from main |
| Recent on main | `git diff $(git log -1 --format=%H -- docs/architecture/)..HEAD` | Changes since last architecture doc update |
| Full sweep | N/A — no diff, investigate everything | Complete review |
| Specific area | User provides files/features | Targeted investigation |

Include error handling:
- If `git merge-base` fails (no common ancestor): fall back to full sweep, warn user
- If no `docs/architecture/` commits exist: treat as bootstrap scenario

**Verification:** Section exists with baseline commands.

No commit yet.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Add investigation dispatch section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`

**Implementation:**

Add "Investigation" section documenting subagent dispatch:

1. Dispatch sonnet subagent to read current `docs/architecture/` files and report:
   - What architecture docs exist
   - Summary of each doc's content
   - Any obvious gaps or staleness

2. Dispatch sonnet subagent with the diff output to report:
   - What code changed
   - Which changes affect architecture (new processes, entities, actors, terms)
   - Which architecture doc types are affected

3. Compare investigation results:
   - What exists in docs vs what the diff introduces
   - Gaps between reality and documentation
   - Potential contradictions

Include instruction: "DON'T do this investigation yourself. Dispatch subagents. This keeps your context clean for the question loop."

Use the XML Task invocation format:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Reading current architecture docs</parameter>
<parameter name="prompt">
Read all files under docs/architecture/ in the current project.
Report: what exists, summary of each doc, any obvious gaps or staleness.
</parameter>
</invoke>
```

**Verification:** Section exists with subagent dispatch instructions.

No commit yet.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Add question loop section

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`

**Implementation:**

Add "Question Loop" section documenting the one-question-at-a-time pattern:

- After investigation, identify gaps and conflicts between docs and reality
- Ask one pointed, specific, and critical question at a time
- Use AskUserQuestion for choices with 2-4 options and trade-offs
- Use open-ended questions when understanding "why" or getting freeform feedback
- Do not ask questions when only one answer is useful, coherent, and effective — state the assumption and continue
- Do not ask questions just to ask them — if no useful questions remain, proceed to updates

Include the rule from brainstorming: "Ask only useful, coherent, and effective questions."

**Verification:** Section exists with question loop instructions.

No commit yet.
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Add inner skill invocation and completion sections

**Files:**
- Modify: `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`

**Implementation:**

Add "Updating Architecture Docs" section:

1. After question loop, invoke `update-architecture-docs`:
   - `REQUIRED SUB-SKILL: Use denubis-plan-and-execute:update-architecture-docs`
   - Announce: "I'm using the update-architecture-docs skill to assess and propose changes."
   - Pass the git diff output as the artifact

2. The inner skill will:
   - Read current docs
   - Detect contradictions (may HALT — wrapper waits)
   - Propose changes for human approval
   - Write approved changes

3. After inner skill completes:
   - If more doc types need attention (investigation revealed gaps the inner skill didn't cover), loop back to question step
   - Otherwise, summarise what was updated

Add "Completion" section:
- List all files created or modified
- Suggest committing changes if any were made
- Report "architecture docs appear current" if no changes were needed (AC4.5)

Add "Common Rationalizations - STOP" table.

Add "Integration" section showing this skill's place in the workflow.

**Verification:** Complete SKILL.md with all sections.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Create command registration file

**Files:**
- Create: `plugins/denubis-plan-and-execute/commands/maintain-architecture.md`

**Implementation:**

Following the established command registration pattern (single `description` field in frontmatter, one-line body directing to the Skill tool):

```markdown
---
description: Run architecture documentation maintenance session
---

Use your Skill tool to engage the `maintain-architecture` skill. Follow it exactly as written.
```

**Verification:** File exists with correct frontmatter and body.
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Commit wrapper skill and command

**Files:**
- `plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md`
- `plugins/denubis-plan-and-execute/commands/maintain-architecture.md`

**Step 1: Stage**

```bash
git add plugins/denubis-plan-and-execute/skills/maintain-architecture/SKILL.md
git add plugins/denubis-plan-and-execute/commands/maintain-architecture.md
```

**Step 2: Commit**

```bash
git commit -m "feat(plan-and-execute): add maintain-architecture wrapper skill and command"
```

**Step 3: Verify**

```bash
ls plugins/denubis-plan-and-execute/skills/maintain-architecture/
ls plugins/denubis-plan-and-execute/commands/maintain-architecture.md
```

Expected: SKILL.md exists, command file exists.
<!-- END_TASK_8 -->
