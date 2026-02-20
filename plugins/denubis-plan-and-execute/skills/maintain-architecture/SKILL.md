---
name: maintain-architecture
description: Use for standalone architecture documentation maintenance - computes git diff baselines, dispatches subagents to read code and docs, asks targeted questions, and invokes update-architecture-docs to propose changes
user-invocable: true
---

# Maintain Architecture

## Overview

Orchestrate standalone architecture documentation maintenance sessions through four phases: Scope, Investigate, Question, Update.

**Core principle:** Scope -> Investigate -> Question -> Update. Understand what changed, ask targeted questions, propose updates.

**Announce at start:** "I'm using the maintain-architecture skill to review and update architecture documentation."

This skill orchestrates maintenance sessions by dispatching subagents for investigation and calling the `update-architecture-docs` inner skill for proposals.

## Workflow Status Line

Update the breadcrumb status line at phase transitions. If the state script is not installed, skip silently.

All commands prefixed with: `~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-plan-and-execute/scripts/workflow-state-wrapper.sh`

| Transition | `--skill` | `--context` |
|------------|-----------|-------------|
| Entry | `maintain-architecture` | `scoping changes` |
| Computing diff baseline | | `computing baseline` |
| Dispatching investigators | | `investigating codebase` |
| Question to user | | `asking: <topic>` |
| Calling inner skill | | `updating docs` |
| Between steps (Claude working) | | `""` |

## Scope Determination

On entry, ask the user what kind of session they want. Use AskUserQuestion:

```
Question: "What kind of architecture documentation review?"
Options:
  - "Review changes on this branch" (diff from merge-base with main)
  - "Review recent changes on main" (diff since last architecture update)
  - "Full sweep" (review all architecture docs against current codebase)
  - "Specific area" (I'll describe what to review)
```

What each option means:

| Option | Baseline | Investigation Scope |
|--------|----------|-------------------|
| **Branch changes** | `rtk git diff $(git merge-base HEAD main)` — all changes since branch diverged | Only code and docs affected by the branch |
| **Recent on main** | `rtk git diff $(rtk git log -1 --format=%H -- docs/architecture/)..HEAD` — changes since last architecture doc update | All code changed since last architecture update |
| **Full sweep** | No diff — investigate everything | All architecture docs against current codebase state |
| **Specific area** | User provides files, features, or areas to review | Targeted investigation of the described area |

## Computing Baseline

After scope is chosen, compute the git diff baseline. Use Bash to run the appropriate command.

| Scope | Command | What it produces |
|-------|---------|-----------------|
| Branch changes | `rtk git diff $(git merge-base HEAD main)` | All changes since branch diverged from main |
| Recent on main | `rtk git diff $(rtk git log -1 --format=%H -- docs/architecture/)..HEAD` | Changes since last architecture doc update |
| Full sweep | N/A — no diff, investigate everything | Complete review |
| Specific area | User provides files/features | Targeted investigation |

**Save the diff output.** You will pass it to `update-architecture-docs` later.

### Error Handling

- If `git merge-base` fails (no common ancestor with main): fall back to full sweep. Warn the user: "No common ancestor with main found. Falling back to a full sweep."
- If no `docs/architecture/` commits exist (the `git log` command returns empty): treat as bootstrap scenario. Inform the user: "No architecture documentation commits found. This will be treated as a bootstrap — the inner skill will scaffold `docs/architecture/`."
- If the diff is empty (no changes detected): report "Architecture docs appear current — no code changes detected in the baseline." and exit. Do not proceed to investigation.

## Investigation

**DON'T do this investigation yourself. Dispatch subagents. This keeps your context clean for the question loop.**

Dispatch two subagents in parallel:

### Subagent 1: Read Current Architecture Docs

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Reading current architecture docs</parameter>
<parameter name="prompt">
Read all files under docs/architecture/ in the current project.

Report:
- What architecture docs exist (list each file with its path)
- Summary of each doc's content (2-3 sentences)
- Any obvious gaps or staleness (e.g., references to removed code, missing doc types)

If docs/architecture/ does not exist, report that.
</parameter>
</invoke>
```

### Subagent 2: Analyse the Diff

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Analysing code changes for architecture impact</parameter>
<parameter name="prompt">
Here is the git diff output:

[paste the saved diff output here]

Analyse these changes and report:
- What code changed (files, functions, modules)
- Which changes affect architecture (new processes, entities, actors, terms, data flows, state transitions, constraints)
- Which architecture doc types are affected (DFD, database, personae, glossary, constraints, states)
- Any renamed or removed components
</parameter>
</invoke>
```

For **full sweep** mode (no diff), replace Subagent 2 with a codebase structure investigator:

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:sonnet-general-purpose</parameter>
<parameter name="description">Surveying codebase structure for architecture review</parameter>
<parameter name="prompt">
Survey the codebase structure of the current project.

Report:
- Top-level directory layout
- Major modules and their responsibilities
- Entry points and data flows you can infer from the code
- Any patterns, frameworks, or conventions in use
</parameter>
</invoke>
```

### Compare Results

After both subagents return, compare their findings:

- What exists in docs vs what the diff (or codebase) introduces
- Gaps between reality and documentation
- Potential contradictions (new code conflicts with documented architecture)

This comparison drives the question loop.

## Question Loop

After investigation, identify gaps and conflicts between docs and reality. Ask one pointed, specific, and critical question at a time.

### When to Ask

- **Use AskUserQuestion** when there are 2-4 discrete options with different trade-offs. Present the options and their implications.
- **Use open-ended questions** when you need to understand "why" something was done, or need freeform context the code cannot provide.
- **Do not ask** when only one answer is useful, coherent, and effective. State the assumption and continue.
- **Do not ask questions just to ask them.** If the investigation produced clear answers and no useful questions remain, proceed directly to updates.

### Question Quality

Ask only useful, coherent, and effective questions:

- **Useful:** The answer changes what you do next. If every answer leads to the same action, don't ask.
- **Coherent:** The question makes sense given what you already know. Don't ask what the investigation already answered.
- **Effective:** The question is specific enough to get a specific answer. "Should I update the docs?" is not effective. "The DFD shows authentication going through a gateway, but the new code adds a direct auth path — should the DFD reflect the new path, or is the gateway still canonical?" is effective.

### Loop Termination

Stop asking questions when:

- All gaps identified by investigation have been addressed (by answers or by assumptions)
- Remaining unknowns can be resolved from the diff and existing docs alone
- The user indicates they want to proceed

## Updating Architecture Docs

After the question loop, invoke the inner skill to propose and apply documentation changes.

**REQUIRED SUB-SKILL:** Use denubis-plan-and-execute:update-architecture-docs

**Announce:** "I'm using the update-architecture-docs skill to assess and propose changes."

Pass the git diff output as the artifact. The inner skill operates in wrapper mode when given diff output.

The inner skill will:

1. Read current `docs/architecture/` files
2. Parse the diff for architecture-relevant content
3. Detect contradictions against existing docs (may HALT — wait for the user to resolve before continuing)
4. Propose grouped changes for human approval
5. Write approved changes

### After Inner Skill Completes

- If the investigation revealed gaps that the inner skill did not cover (e.g., additional doc types needing attention), loop back to the question step to address them, then invoke the inner skill again.
- Otherwise, proceed to completion.

## Completion

Summarise the session:

- List all files created or modified during this session
- If changes were made, suggest committing: "Architecture documentation updated. Ready to commit these changes?"
- If no changes were needed (diff was empty, or inner skill found no architecture-relevant content), report: "Architecture docs appear current. No changes needed."

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "Diff is small, skip investigation" | Small diffs can have large architecture impact. Always investigate. |
| "I can read the docs myself, no need for subagents" | Dispatch subagents. Keep your context clean for questions. |
| "No questions needed, I understand everything" | If investigation revealed gaps, ask. If not, proceed — but don't skip the check. |
| "I'll update docs directly without the inner skill" | Always use `update-architecture-docs`. It handles contradiction detection and approval. |
| "User didn't ask for full review, skip some doc types" | The inner skill checks all doc types against the diff. Don't pre-filter. |
| "Architecture docs appear current" without checking | Only say this after computing baseline AND confirming the diff is empty. |

**All of these mean: STOP. Follow the process exactly.**

## Integration

Where this skill sits in the broader workflow:

```
User invokes /maintain-architecture
  -> Scope determination (ask user)
  -> Compute git diff baseline
  -> Dispatch investigation subagents
  -> Question loop (one question at a time)
  -> Invoke update-architecture-docs with diff
     -> Inner skill reads docs, detects contradictions, proposes changes
     -> Human approves/modifies
     -> Inner skill writes changes
  -> Summarise and suggest commit

writing-design-plans (after proleptic challenge)
  -> calls update-architecture-docs with design plan path
  -> separate invocation path, not through this wrapper
```
