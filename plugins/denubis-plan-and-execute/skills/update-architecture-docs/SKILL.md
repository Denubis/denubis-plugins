---
name: update-architecture-docs
description: Use when design or implementation work may affect architecture documentation - reads current docs, detects contradictions, and proposes changes for human approval before writing
user-invocable: false
---

# Update Architecture Docs

## Overview

Read current state, detect contradictions, propose changes, write approved changes.

This skill operates on concrete artifacts only: a design plan file path (sub-skill mode) or git diff output (wrapper mode). It never operates on conversation context alone.

**Announce at start:** "I'm using the update-architecture-docs skill to assess architecture documentation."

## Input Modes

| Mode | Input | Called by |
|------|-------|----------|
| Sub-skill | Design plan file path | `writing-design-plans` after proleptic challenge |
| Wrapper | Git diff output (from baseline) | `maintain-architecture` during maintenance |

**Sub-skill mode:** Read the design plan at the given file path and extract architecture-relevant content — entities, processes, data flows, constraints, terms, actors, and state transitions.

**Wrapper mode:** Receive pre-computed git diff output and extract what changed — new files, modified code, renamed components, changed schemas.

Both modes proceed to the same flow: read current state, detect contradictions, propose changes, write approved changes.

## Directory Convention

Architecture documentation lives in `docs/architecture/` with this structure:

```
docs/architecture/
  dfd/
    0-context-diagram.md          # Level 0: system boundary
    1-subsystem-name.md           # Level 1: major subsystems
    1.1-sub-process.md            # Level 2: decomposition
    1.1.1-detail.md               # Level 3: further decomposition
    2-another-subsystem.md
  states/
    order-lifecycle.md            # Entity state diagrams
    user-account-lifecycle.md
  database.md                     # ERD, data dictionary, design decisions
  personae.md                     # User types and access patterns
  glossary.md                     # Ubiquitous language
  constraints.md                  # Measurable quality attributes
```

### DFD Numbering Scheme

DFD files use hierarchical numbering: `0`, `1`, `1.1`, `1.1.1`. Each level decomposes a process from the level above.

| Level | Scope | Example File |
|-------|-------|-------------|
| 0 | System boundary (context diagram) | `0-context-diagram.md` |
| 1 | Major subsystem | `1-authentication.md` |
| 2 | Subsystem decomposition | `1.1-token-service.md` |
| 3 | Further detail | `1.1.1-jwt-generation.md` |

**Numbering stability:** Numbers are stable identifiers. Once a process is assigned a number, it keeps that number even if adjacent processes are removed. Gaps are acceptable. Periodic cleanup is handled by the wrapper skill during maintenance sessions.

### Cross-Reference Format

DFD files cross-reference each other:
- **Parent:** `0-context-diagram.md` (the diagram this decomposes from)
- **Children:** `1.1-sub-process.md`, `1.2-other.md` (diagrams that decompose this)
- **Related issues:** GitHub issue references
- **Related commits:** Commit SHAs where this was established or modified

### Template Files

See `template-dfd-context.md`, `template-dfd-process.md`, `template-database.md`, `template-personae.md`, `template-glossary.md`, `template-constraints.md`, and `template-state.md` in this skill directory for document templates.

## Assessment Framework

For each doc type, scan the input artifact for context signals. If a signal is found, check the corresponding atomic units against existing docs. If a contradiction pattern matches, HALT before proceeding.

| Doc Type | Atomic Unit | Context Signal | Contradiction Pattern |
|----------|-------------|----------------|----------------------|
| DFD | Process (numbered) | New data transformation, renamed component, changed data flow | Process duplicates existing responsibility; data flow contradicts existing diagram |
| Database | Table/relationship | New entity, changed schema, new FK | Entity in design doesn't match existing ERD; relationship contradicts existing constraints |
| Personae | User type | New actor, changed access pattern | New persona overlaps existing one; access pattern contradicts constraints |
| Glossary | Term | New domain concept, renamed entity | Term defined differently than existing entry; synonym collision |
| Constraints | Quality attribute | New SLA, performance target, capacity requirement | New constraint contradicts existing one |
| States | Entity lifecycle | New status, state transition, terminal state | State transition contradicts existing lifecycle; new state unreachable from existing graph |

### How to Use This Table

1. For each doc type, scan the input artifact (design plan or diff) for context signals
2. If a signal is found, read the existing architecture doc for that type and check the corresponding atomic units
3. If a contradiction pattern matches, HALT immediately — do not continue to the proposal step

## Contradiction Detection

Finding contradictions is more important than updating. If in doubt about whether something is a contradiction, HALT. False positives are cheap; missed contradictions are expensive.

When a contradiction is detected, present it using this format:

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

After HALT resolution, continue from step 4 (identify affected docs) with the resolution incorporated. If the human chose option 1, treat the new content as authoritative. If option 2, adjust the proposal to match existing docs. If option 3, document the divergence in both the architecture doc and the design plan.

## Proposing Changes

After the contradiction check passes (no contradictions found, or all contradictions resolved), group proposed changes by doc type.

### When No Changes Are Detected

If the artifact contains no architecture-relevant content (e.g., a pure refactor, a test-only change, or a dependency update), report:

"No architecture changes detected. The design plan does not introduce new processes, entities, terms, constraints, actors, or state transitions."

Exit without proposing.

### Presenting Proposals

Before asking for approval, output the complete proposal:

```
**Proposed architecture documentation changes:**

### DFD
- Create: `docs/architecture/dfd/1.3-new-process.md` (new process from design)
- Modify: `docs/architecture/dfd/1-subsystem.md` (add reference to new child)

### Database
- Modify: `docs/architecture/database.md` (add new_table to ERD and data dictionary)

### Glossary
- Add term: "Widget" — [definition from design context]

### Personae
- Add persona: "Auditor" — [role description from design]

[Continue for each affected doc type...]
```

Then ask for approval using AskUserQuestion:

```
Question: "Review proposed architecture documentation changes:"
Options:
  - "Approve all" (write all proposed changes)
  - "Approve with modifications" (I'll describe what to change)
  - "Reject" (no architecture doc changes)
```

### Writing Approved Changes

Write only approved changes. Use the templates from this skill directory (`template-dfd-context.md`, `template-dfd-process.md`, etc.) as the starting structure for new files. For modifications to existing files, preserve existing content and add or update the affected sections.

## Bootstrap and Greenfield

### Bootstrap Mode

Triggered when `docs/architecture/` does not exist AND a design plan is provided.

Bootstrap requires a design document. If there is no design plan, there is nothing to bootstrap from — the project needs brainstorming first.

**Bootstrap steps:**

1. Scaffold directory structure: create `docs/architecture/dfd/` and `docs/architecture/states/`
2. Create `docs/architecture/dfd/0-context-diagram.md` from the design plan's Architecture section (system boundary, external entities, top-level data flows) using `template-dfd-context.md`
3. Populate `docs/architecture/glossary.md` from the design plan's Glossary section using `template-glossary.md`
4. Populate `docs/architecture/personae.md` from the design plan's actors and user types using `template-personae.md`
5. Create `docs/architecture/constraints.md` from the design plan's quality constraints (if any) using `template-constraints.md`
6. If `docs/database.md` exists, move it to `docs/architecture/database.md`
7. Present all created files to human for approval before writing

### Greenfield Mode

Triggered when `docs/architecture/` does not exist AND the design plan is the first for a new project.

Same as bootstrap, but also creates `docs/architecture/database.md` from `template-database.md` if the design plan includes database schema.

## Skill Flow

The complete flow tying all sections together:

1. **Read current state** — load all files under `docs/architecture/`. If the directory does not exist, enter bootstrap mode.
2. **Parse artifact** — extract entities, processes, data flows, constraints, terms, actors, and state transitions from the design plan or diff.
3. **Detect contradictions** — for each doc type where context signals are found, check for contradiction patterns against existing docs. HALT if a contradiction is found.
4. **Identify affected docs** — determine which files need creation or modification, organised by doc type.
5. **Propose changes** — present grouped proposals to the human for approval.
6. **Write approved changes** — apply using templates from this skill directory.

## Common Rationalizations - STOP

| Excuse | Reality |
|--------|---------|
| "No contradictions possible, it's a new feature" | New features can duplicate existing responsibilities. Check the DFD. |
| "Glossary update is obvious, don't need approval" | Never write blind updates. Always present proposals. |
| "Bootstrap is simple, skip the approval" | Bootstrap creates many files. Human must approve the initial structure. |
| "Design plan doesn't mention architecture" | Check anyway. Context signals may be implicit. |
| "I'll update docs after the code is written" | Architecture docs are updated from the design plan, before implementation. |

**All of these mean: STOP. Follow the requirements exactly.**

## Integration

Where this skill sits in the broader workflow:

```
writing-design-plans (after proleptic challenge)
  -> calls update-architecture-docs with design plan path
  -> proposals presented to human
  -> approved changes written
  -> changes included in design plan commit

maintain-architecture (standalone sessions)
  -> calls update-architecture-docs with git diff output
  -> proposals presented to human
  -> approved changes committed separately
```
