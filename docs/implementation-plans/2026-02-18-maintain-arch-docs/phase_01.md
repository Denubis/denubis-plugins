# Architecture Documentation System — Phase 1: Directory Convention and Document Templates

**Goal:** Create template files for each architecture doc type as companion files alongside the inner skill's SKILL.md.

**Architecture:** Templates are companion markdown files in the `update-architecture-docs/` skill directory, cross-referenced from SKILL.md. This follows the established pattern from `requesting-code-review/code-reviewer.md` — companion files alongside SKILL.md, not a subdirectory.

**Tech Stack:** Markdown, Mermaid diagrams

**Scope:** Phase 1 of 4

**Codebase verified:** 2026-02-18

---

## Acceptance Criteria Coverage

This phase is infrastructure — it creates template files. No ACs are directly verified here; templates are consumed by Phase 2 (inner skill).

**Verifies:** None (infrastructure phase)

---

<!-- START_TASK_1 -->
### Task 1: Create skill directory structure

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/` (directory)

**Step 1: Create the directory**

```bash
mkdir -p plugins/denubis-plan-and-execute/skills/update-architecture-docs
```

**Step 2: Verify**

```bash
ls -d plugins/denubis-plan-and-execute/skills/update-architecture-docs
```

Expected: Directory exists.

No commit yet — commit with template files.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Create DFD context diagram template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-dfd-context.md`

**Implementation:**

Create the level-0 context diagram template. This is the system boundary view — the single process representing the entire system, with all external entities and data flows.

Template content:

```markdown
# Context Diagram (Level 0)

> System boundary: [System Name]

## Diagram

\`\`\`mermaid
flowchart LR
    %% External entities (rectangles)
    E1[External Entity 1]
    E2[External Entity 2]

    %% The system (double circle = process)
    P0((0.0\nSystem Name))

    %% Data flows
    E1 -->|"input data"| P0
    P0 -->|"output data"| E2
\`\`\`

## External Entities

| Entity | Description | Inputs to System | Outputs from System |
|--------|-------------|-----------------|---------------------|
| [Name] | [What it is] | [Data it sends] | [Data it receives] |

## System Boundary

**In scope:** [What the system does]

**Out of scope:** [What external entities handle]

## Cross-References

- **Parent:** None (this is the top-level diagram)
- **Children:** [List level-1 DFD files, e.g., `1-subsystem.md`]
- **Related issues:** [GitHub issue references]
- **Related commits:** [Commit SHAs where this was established/modified]
```

**Verification:** File exists with valid Mermaid flowchart syntax.

No commit yet — batch with other templates.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Create DFD process template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-dfd-process.md`

**Implementation:**

Template for any DFD process at level 1 or deeper. Includes the process's decomposition diagram and cross-references up/down the hierarchy.

Template content:

```markdown
# [N.M] [Process Name]

> Decomposes process [N] from [parent file]

## Diagram

\`\`\`mermaid
flowchart LR
    %% Inputs from parent diagram
    IN1([Input Flow 1])
    IN2([Input Flow 2])

    %% Processes at this level
    P1((N.1\nSub-Process 1))
    P2((N.2\nSub-Process 2))

    %% Data stores
    D1@{ shape: das, label: "Data Store 1" }

    %% Internal flows
    IN1 -->|"data"| P1
    P1 -->|"processed data"| D1
    D1 -->|"stored data"| P2
    P2 -->|"output"| OUT1

    %% Outputs to parent diagram
    OUT1([Output Flow 1])
\`\`\`

> **Note:** `@{ shape: das }` requires Mermaid v11.3.0+. If your renderer is older, use `[(Data Store 1)]` as a fallback.

## Processes

| Process | Number | Description | Decomposed in |
|---------|--------|-------------|---------------|
| [Name] | N.1 | [What it does] | [File path or "leaf process"] |
| [Name] | N.2 | [What it does] | [File path or "leaf process"] |

## Data Stores

| Store | Description | Read by | Written by |
|-------|-------------|---------|------------|
| [Name] | [What it holds] | [Process numbers] | [Process numbers] |

## Inputs and Outputs

| Flow | Direction | Source/Destination | Description |
|------|-----------|--------------------|-------------|
| [Name] | In | [Parent process or external entity] | [What data flows] |
| [Name] | Out | [Parent process or external entity] | [What data flows] |

## Cross-References

- **Parent:** [Parent DFD file, e.g., `0-context-diagram.md`]
- **Children:** [Child DFD files, e.g., `N.1-sub-process.md`]
- **Related issues:** [GitHub issue references]
- **Related commits:** [Commit SHAs]

## Numbering

DFD numbers are stable identifiers. Once assigned, a process keeps its number. New processes get the next available number at this level. Gaps are acceptable.
```

**Verification:** File exists with valid Mermaid flowchart syntax including `@{ shape: das }`.

No commit yet.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Create database documentation template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-database.md`

**Implementation:**

Template for `docs/architecture/database.md`. This mirrors the existing template from `howto-develop-with-postgres` but is the canonical reference for the new path. The six sections are preserved exactly.

Template content:

```markdown
# Database Documentation

## Universe of Discourse

[What this database models. Domain boundaries. Core entities with business definitions. Key business rules that constrain the data.]

## Entity-Relationship Model

\`\`\`mermaid
erDiagram
    ENTITY_A ||--o{ ENTITY_B : "relationship"
    ENTITY_A {
        uuid id PK
        string name
        timestamp created_at
    }
    ENTITY_B {
        uuid id PK
        uuid entity_a_id FK
        string status
    }
\`\`\`

## Data Flow Diagrams

\`\`\`mermaid
flowchart LR
    Actor([External Actor]) -->|"request"| P1((Process))
    P1 -->|"read/write"| DB@{ shape: das, label: "Database" }
    P1 -->|"response"| Actor
\`\`\`

[Describe how data moves between system components, external actors, and data stores.]

## Data Dictionary

### [table_name]

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, NOT NULL | [Business meaning] |
| name | VARCHAR(255) | NOT NULL | [Business meaning] |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | [Business meaning] |

[Repeat for each table.]

## Design Decisions

### [Decision Title]
**Date:** YYYY-MM-DD
**Context:** [Why this decision was needed]
**Decision:** [What was decided]
**Alternatives rejected:** [What else was considered and why it was rejected]

## Denormalisation Register

[If no denormalisation exists, state: "No denormalisation. All tables are in 3NF or higher."]

| Table | Column | Denormalised from | Justification | Sync mechanism |
|-------|--------|-------------------|---------------|----------------|
| [table] | [column] | [source table.column] | [Why denormalised] | [How kept in sync] |
```

**Verification:** File exists with valid erDiagram and flowchart Mermaid syntax.

No commit yet.
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Create personae template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-personae.md`

**Implementation:**

Template content:

```markdown
# Personae

User types, their goals, access patterns, and constraints.

## [Persona Name]

**Role:** [What they do in the system]

**Goals:**
- [Primary goal]
- [Secondary goal]

**Access patterns:**
- [How they interact with the system]
- [Frequency, volume, typical workflows]

**Constraints:**
- [What limits their access]
- [Security level, permissions, quotas]

**Key scenarios:**
1. [Scenario description — what they do, what they expect]
2. [Another scenario]

---

[Repeat for each persona.]

## Persona Relationships

[How personae interact with each other. Which personae share resources, compete for resources, or have authority over others.]
```

**Verification:** File exists.

No commit yet.
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Create glossary template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-glossary.md`

**Implementation:**

Template content:

```markdown
# Project Glossary

Ubiquitous language for this project. Every term here means the same thing in code, docs, and conversation.

## Domain Terms

- **[Term]**: [Definition in the context of this project. Not the general definition — the project-specific meaning.]

## Technical Terms

- **[Term]**: [Definition. Include version/specification references where relevant.]

## Abbreviations

| Abbreviation | Full Form | Context |
|-------------|-----------|---------|
| [ABBR] | [Full form] | [Where/when this abbreviation is used] |

## Deprecated Terms

| Old Term | Replaced By | Since | Reason |
|----------|-------------|-------|--------|
| [Old] | [New] | [Date] | [Why renamed/replaced] |
```

**Verification:** File exists.

No commit yet.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Create constraints template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-constraints.md`

**Implementation:**

Template content:

```markdown
# Quality Constraints

Measurable limits on system behaviour. Each constraint has a metric, a target, and a verification method.

## Performance

| Constraint | Metric | Target | Verification |
|-----------|--------|--------|-------------|
| [Name] | [What's measured] | [Threshold] | [How to test] |

## Availability

| Constraint | Metric | Target | Verification |
|-----------|--------|--------|-------------|
| [Name] | [What's measured] | [Threshold] | [How to test] |

## Security

| Constraint | Requirement | Verification |
|-----------|-------------|-------------|
| [Name] | [What must hold] | [How to verify] |

## Capacity

| Constraint | Metric | Current | Limit | Verification |
|-----------|--------|---------|-------|-------------|
| [Name] | [What's measured] | [Current value] | [Maximum] | [How to test] |

## Constraint History

| Date | Constraint | Change | Reason |
|------|-----------|--------|--------|
| [Date] | [Which constraint] | [What changed] | [Why] |
```

**Verification:** File exists.

No commit yet.
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Create entity state template

**Files:**
- Create: `plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-state.md`

**Implementation:**

Template content:

```markdown
# [Entity Name] Lifecycle

## State Diagram

\`\`\`mermaid
stateDiagram-v2
    [*] --> Initial
    Initial --> Active : activate
    Active --> Suspended : suspend
    Suspended --> Active : reactivate
    Active --> [*] : close
\`\`\`

## States

| State | Description | Entry Conditions | Exit Conditions |
|-------|-------------|-----------------|-----------------|
| Initial | [What this state means] | [How entities enter] | [What triggers transition out] |
| Active | [What this state means] | [How entities enter] | [What triggers transition out] |
| Suspended | [What this state means] | [How entities enter] | [What triggers transition out] |

## Transitions

| From | To | Trigger | Side Effects | Reversible? |
|------|----|---------|-------------|-------------|
| Initial | Active | [What causes this] | [What happens as a result] | [Yes/No] |
| Active | Suspended | [What causes this] | [What happens as a result] | [Yes] |

## Invariants

- [Rules that must hold across all states, e.g., "An entity cannot transition directly from Initial to Suspended"]
- [Business rules about state combinations]

## Cross-References

- **Database:** [Which table/column stores state, e.g., `orders.status`]
- **Related DFD:** [Which DFD process manages transitions]
- **Related issues:** [GitHub issue references]
```

**Verification:** File exists with valid stateDiagram-v2 Mermaid syntax.
<!-- END_TASK_8 -->

<!-- START_TASK_9 -->
### Task 9: Commit all templates

**Files:**
- All 7 template files from Tasks 2-8

**Step 1: Stage all template files**

```bash
git add plugins/denubis-plan-and-execute/skills/update-architecture-docs/template-*.md
```

**Step 2: Commit**

```bash
git commit -m "feat(plan-and-execute): add architecture doc templates for update-architecture-docs skill"
```

**Step 3: Verify**

```bash
ls plugins/denubis-plan-and-execute/skills/update-architecture-docs/
```

Expected: 7 template files listed.
<!-- END_TASK_9 -->
