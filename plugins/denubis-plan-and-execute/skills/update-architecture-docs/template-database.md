# Database Documentation

## Universe of Discourse

[What this database models. Domain boundaries. Core entities with business definitions. Key business rules that constrain the data.]

## Entity-Relationship Model

```mermaid
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
```

## Data Flow Diagrams

```mermaid
flowchart LR
    Actor([External Actor]) -->|"request"| P1((Process))
    P1 -->|"read/write"| DB@{ shape: das, label: "Database" }
    P1 -->|"response"| Actor
```

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
**Status:** Proposed | Accepted | Superseded by [link] | Deprecated
**Confidence:** High | Medium | Low
**Reevaluation triggers:** [Conditions under which to revisit]

**Context:** [Why this decision was needed]
**Decision:** [What was decided]
**Consequences:**
- **Enables:** [What this unlocks]
- **Prevents:** [What this forecloses]
**Alternatives rejected:** [What else was considered and why it was rejected]

## Denormalisation Register

[If no denormalisation exists, state: "No denormalisation. All tables are in 3NF or higher."]

| Table | Column | Denormalised from | Justification | Sync mechanism |
|-------|--------|-------------------|---------------|----------------|
| [table] | [column] | [source table.column] | [Why denormalised] | [How kept in sync] |
