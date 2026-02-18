---
name: howto-develop-with-postgres
description: Use when writing database access code, creating schemas, designing tables, or managing transactions with PostgreSQL - enforces schema design principles, normalisation, key selection, transaction safety, ACID compliance, type safety, and naming conventions
---

# PostgreSQL Development Patterns

## Overview

The database is the source of truth. Treat it with respect.

**Core principles:**
- Schema design comes first — get the structure right before writing access code
- Normalisation prevents data anomalies; denormalise only with measured evidence
- Transactions prevent partial updates (data corruption)
- ACID compliance is non-negotiable
- Type safety catches errors early
- Naming conventions ensure consistency

## Schema Design

### Normalisation

Apply normal forms in order. Stop at BCNF unless you have measured evidence that denormalisation improves performance.

| Form | Rule | Violation Example |
|------|------|-------------------|
| **1NF** | Every column holds one atomic value | `tags TEXT` storing comma-separated values |
| **2NF** | Non-key columns depend on the *whole* key | Composite PK `(order_id, product_id)` with `customer_name` depending only on `order_id` |
| **3NF** | No transitive dependencies | `user` table with `department_id` AND `department_name` |
| **BCNF** | Every determinant is a candidate key | Rare in practice — 3NF usually sufficient |

**When to denormalise:**
- After profiling shows a specific query is too slow
- The denormalised column is derived/cached, not the source of truth
- Document why and how the cached value stays in sync

**Never denormalise because:**
- "It's simpler" — normalised schemas are simpler to reason about
- "Joins are slow" — they aren't, with proper indexes
- "We might need it later" — premature optimisation

### Key Selection

**Decision rule:**

| Data Type | Key Strategy | Example |
|-----------|-------------|---------|
| **Reference data** (permissions, roles, statuses) | Natural string PK | `name TEXT PRIMARY KEY` |
| **Entity data** (users, orders, resources) | Surrogate ULID/UUID PK | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| **Join tables** | Composite FK PK | `PRIMARY KEY (user_id, role_name)` |

**Reference tables** are constrained vocabularies — small, fixed sets where the name IS the identity:

```python
# Reference table: natural string PK
class Permission(SQLModel, table=True):
    name: str = Field(primary_key=True, max_length=50)  # "owner", "editor", "viewer"
    level: int
    description: str = ""

# Self-documenting FK
class ACLEntry(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    resource_id: UUID = Field(foreign_key="resource.id")
    user_id: UUID = Field(foreign_key="user.id")
    permission_name: str = Field(foreign_key="permission.name")  # obvious what this means
```

**Entity tables** get surrogate keys — see [Primary Keys: ULID](#primary-keys-ulid) below.

**Hard rules:**
- Never hardcode specific UUID values in source code as constants
- Never add surrogate UUIDs to reference tables — it's pointless indirection
- `default_factory=uuid4` (dynamic generation) is NOT the same as hardcoded UUIDs (static values)

### Constraint Strategy

**NOT NULL by default.** Every column should be NOT NULL unless you have a specific reason for allowing NULL. NULL means "unknown" — if the value isn't unknown, it shouldn't be nullable.

```python
# Good: explicit about nullability
class User(SQLModel, table=True):
    email: str = Field(nullable=False)          # Required — always known
    deleted_at: datetime | None = Field(None)   # Nullable — absence is meaningful
```

**Use CHECK constraints for domain rules:**

```sql
-- Length constraints (not varchar(n))
ALTER TABLE users ADD CONSTRAINT ck_users_email_length CHECK (length(email) <= 254);

-- Value constraints
ALTER TABLE orders ADD CONSTRAINT ck_orders_positive_total CHECK (total > 0);

-- Enum-like constraints (when a reference table is overkill)
ALTER TABLE tasks ADD CONSTRAINT ck_tasks_priority CHECK (priority IN ('low', 'medium', 'high'));
```

**Use UNIQUE constraints for business rules:**

```sql
-- Single column
ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);

-- Composite (one active subscription per user per plan)
ALTER TABLE subscriptions ADD CONSTRAINT uq_subscriptions_active
    UNIQUE (user_id, plan_id) WHERE (cancelled_at IS NULL);
```

**Use EXCLUDE constraints for range/temporal rules:**

```sql
-- No overlapping bookings for the same room
ALTER TABLE bookings ADD CONSTRAINT excl_bookings_no_overlap
    EXCLUDE USING gist (room_id WITH =, tstzrange(start_at, end_at) WITH &&);
```

### Relationship Modelling

| Relationship | Implementation | Key Rule |
|-------------|----------------|----------|
| **One-to-many** | FK on the "many" side | `orders.user_id → users.id` |
| **Many-to-many** | Association table with composite PK | `user_roles(user_id, role_name)` |
| **One-to-one** | FK with UNIQUE constraint | `profile.user_id → users.id` + UNIQUE |

**Association tables for many-to-many:**

```python
# Pure join table — composite PK, no surrogate key
class UserRole(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role_name: str = Field(foreign_key="role.name", primary_key=True)
    granted_at: datetime = Field(default_factory=datetime.now)
```

**Association tables with extra data** get their own surrogate PK:

```python
class Enrollment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    student_id: UUID = Field(foreign_key="student.id")
    course_id: UUID = Field(foreign_key="course.id")
    grade: str | None = None
    enrolled_at: datetime = Field(default_factory=datetime.now)

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )
```

### PostgreSQL Type Anti-Patterns

From the [PostgreSQL "Don't Do This" wiki](https://wiki.postgresql.org/wiki/Don't_Do_This):

| Don't Use | Use Instead | Why |
|-----------|-------------|-----|
| `char(n)` | `text` with CHECK constraint | Space-padding wastes storage, breaks comparisons |
| `varchar(n)` with arbitrary limits | `text` or `varchar` (unlimited) | Arbitrary limits cause production errors |
| `serial` | `IDENTITY` column (PG 10+) | Cleaner schema dependencies |
| `money` | `numeric` + separate currency column | Assumes single currency, locale-dependent |
| `timestamp` (without tz) | `timestamptz` | Loses timezone information |
| `timetz` | `timestamptz` | SQL compliance artifact, not useful |
| `float`/`double` for money | `numeric(19, 4)` | Rounding errors compound |

## Transaction Management

### TX_ Prefix Rule

**Methods that START transactions:**
- Prefix with `TX_`
- Must NOT accept connection/session parameter
- Call transaction internally

**Methods that PARTICIPATE in transactions:**
- No `TX_` prefix
- MUST accept session parameter with default
- Use the provided session

```python
class OrderRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._session_factory = session_factory

    async def TX_create_order_with_items(
        self,
        order_data: OrderCreate,
        items: list[ItemCreate],
    ) -> Order:
        """Create order with items atomically.

        Starts transaction - TX_ prefix, no session parameter.
        """
        async with self._session_factory() as session:
            async with session.begin():
                order = await self.create_order(order_data, session)
                for item in items:
                    await self.create_item(order.id, item, session)
                return order

    async def create_order(
        self,
        data: OrderCreate,
        session: AsyncSession | None = None,
    ) -> Order:
        """Create single order.

        Participates in transaction - no TX_ prefix, takes session.
        """
        session = session or self._session_factory()
        order = Order(**data.model_dump())
        session.add(order)
        await session.flush()
        return order
```

### Context Managers for Scope

Make transaction scope visually obvious:

```python
# Good: scope is clear
async with session.begin():
    user = await create_user(data, session)
    await create_profile(user.id, profile_data, session)
    # Commits at end of block

# Bad: implicit transaction
await create_user(data)  # When does this commit?
await create_profile(user.id, profile_data)  # Are these atomic?
```

### What Doesn't Need TX_ Prefix

- Single INSERT/UPDATE/DELETE (already atomic)
- Single SELECT queries
- Operations with `ON CONFLICT DO UPDATE`

## SQL Injection Prevention

### Use T-Strings (Python 3.14+)

```python
from string.templatelib import Template

# Good: t-string (template literal)
query = t"SELECT * FROM users WHERE id = {user_id}"
# Returns Template object - driver handles safely

# Pre-3.14 fallback: parameterised queries
await conn.execute(
    "SELECT * FROM users WHERE id = $1",
    user_id,
)
```

### Never String Formatting for SQL

```python
# NEVER: SQL injection vulnerability
query = f"SELECT * FROM users WHERE name = '{name}'"

# NEVER: even with escaping attempts
query = f"SELECT * FROM users WHERE name = '{name.replace(\"'\", \"''\")}'"
```

## Type Safety

### Primary Keys: ULID

**Default to ULID stored as UUID** for user-visible IDs:

```python
from ulid import ULID
from sqlalchemy import Uuid
from sqlalchemy.orm import mapped_column

class User(Base):
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=lambda: ULID().to_uuid(),
    )
```

**Why ULID:**
- Prevents ID enumeration attacks
- Time-sortable for indexing efficiency
- "Most things can leak in some way"

**Exceptions — see [Schema Design](#schema-design) above:**
- Reference tables (natural string PK)
- Pure join tables (composite PK)
- Internal-only tables (serial acceptable)

### Financial Data: Decimal

**Never float for money:**

```python
from decimal import Decimal
from sqlalchemy import Numeric

class Order(Base):
    total: Mapped[Decimal] = mapped_column(
        Numeric(19, 4),  # Up to 10^15, 4 decimal places
        nullable=False,
    )
```

**Why:** Floating-point accumulates rounding errors.

### JSONB: Always Typed

```python
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

class Config(Base):
    # Good: typed with pydantic
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    @validates('settings')
    def validate_settings(self, key, value):
        # Validate structure
        SettingsSchema.model_validate(value)
        return value
```

## Naming Conventions

### Database Identifiers: snake_case

```sql
-- Tables
CREATE TABLE user_preferences (...);
CREATE TABLE order_items (...);

-- Columns
created_at TIMESTAMP NOT NULL,
user_id UUID REFERENCES users(id),
is_active BOOLEAN DEFAULT true

-- Indexes
CREATE INDEX idx_users_email ON users(email);

-- Foreign keys
CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id)
```

### Standard Columns

Every table should have:

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
```

For soft deletion:
```sql
deleted_at TIMESTAMP WITH TIME ZONE
```

## Indexing

### Proactive Indexing

Add indexes for:
- All foreign key columns
- Columns in WHERE clauses
- Columns in JOIN conditions
- Columns in ORDER BY

```sql
-- Foreign key index
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Query pattern index
CREATE INDEX idx_orders_status_created ON orders(status, created_at);
```

### Don't Wait for Performance Issues

Missing indexes on foreign keys cause slow queries from day one.

## Isolation Levels

**Default (Read Committed)** for most operations.

**Serializable** for:
- Financial operations
- Inventory/count operations
- Anything involving money or limited resources

```python
from sqlalchemy import text

async with session.begin():
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
    # Critical section
```

**Pessimistic locking** for contended resources:

```python
# SELECT ... FOR UPDATE
user = await session.execute(
    select(User).where(User.id == user_id).with_for_update()
)
```

## Migrations

### Always Review Generated Migrations

```bash
# Generate
alembic revision --autogenerate -m "add user preferences"

# Review the generated SQL
cat alembic/versions/abc123_add_user_preferences.py

# Apply
alembic upgrade head
```

**Never auto-apply in production** without human review.

## Common Mistakes

| Mistake | Reality | Fix |
|---------|---------|-----|
| "One operation, no transaction" | Multi-step = partial updates | TX_ prefix, begin() |
| "UUID is just a string" | Type confusion | Use proper UUID type |
| "Float is close enough for money" | Rounding errors compound | Use Decimal |
| "I'll add indexes later" | Slow queries from day one | Index FKs proactively |
| "This won't be user-visible" | Requirements change, IDs leak | ULID by default |
| "JSONB doesn't need schema" | Runtime errors | Validate structure |
| "Reference tables need UUIDs too" | Name IS the identity | Natural string PK |
| "Hardcoded UUIDs are fine for seeds" | Opaque, fragile, two sources of truth | Natural keys or name-based lookup |
| "Joins are slow" | Not with proper indexes | Normalise first, measure later |
| "NULL means empty string" | NULL means unknown | NOT NULL + default, or meaningful NULL |
| "varchar(255) is safe enough" | Arbitrary limits cause production errors | `text` with CHECK constraint |
| "char(n) for fixed-width codes" | Space-padding breaks comparisons | `text` with `CHECK(length(x)=n)` |

## Red Flags

**Transaction management:**
- Method calls `.begin()` but no `TX_` prefix
- Method has `TX_` prefix but accepts session
- Multi-step operation without transaction

**Type safety:**
- JSONB without validation
- UUID stored as string
- Float for monetary values

**Schema design:**
- Surrogate UUID on a reference table (should be natural string PK)
- Hardcoded UUID values in Python source code
- Column storing comma-separated values (1NF violation)
- Transitive dependency (column depends on non-key column, 3NF violation)
- NULL-able column without clear semantic reason
- `char(n)`, `serial`, `money`, or `timestamp without time zone`
- Missing indexes on foreign keys
- No timestamps
- camelCase in database identifiers

## Database Documentation (`docs/architecture/database.md`)

Every project with a database MUST have a `docs/architecture/database.md` — a first-class living document that is THE reference for understanding the database. Not buried in design plan subdirectories. Not scattered across model files. One document you can open and understand the entire database from.

### Required Sections

```markdown
# Database Documentation

## Universe of Discourse

### What This Database Models
[What the system represents. Domain boundaries. What's in scope, what's out.]

### Core Entities
[Business definitions — what is a "User"? What is an "Order"? Not column lists —
business meaning. What does each entity represent in the real world?]

### Key Business Rules
[Domain constraints the schema enforces. "A user can have at most one active
subscription per plan." "Orders cannot be modified after confirmation."]

## Entity-Relationship Model

` ` `mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_LINE : contains
    PRODUCT ||--o{ ORDER_LINE : "included in"

    USER {
        uuid id PK "ULID"
        text email UK "RFC 5322"
        timestamptz created_at
    }
` ` `

## Data Flow Diagrams

` ` `mermaid
flowchart LR
    User -->|submits| API
    API -->|validates| AuthService
    AuthService -->|checks| sessions[(sessions)]
    API -->|writes| orders[(orders)]
    API -->|publishes| EventBus
    EventBus -->|notifies| EmailService
` ` `

[Show how data moves through the system. External actors, processes, data stores,
data flows. Multiple DFDs for different subsystems if needed.]

## Data Dictionary

### users
**Purpose:** Registered accounts that can authenticate and own resources.
**Type:** Entity

| Column | Type | Nullable | Constraints | Business Definition |
|--------|------|----------|-------------|---------------------|
| id | UUID | NO | PK (ULID) | Unique user identity |
| email | text | NO | UNIQUE | Primary login identifier. RFC 5322 compliant. |
| created_at | timestamptz | NO | DEFAULT now() | Account creation time |
| deleted_at | timestamptz | YES | | Soft deletion. NULL = active. |

**Relationships:**
- Referenced by: `orders.user_id`, `workspace_members.user_id`

### permissions
**Purpose:** Constrained vocabulary of permission levels.
**Type:** Reference

| Column | Type | Nullable | Constraints | Business Definition |
|--------|------|----------|-------------|---------------------|
| name | text | NO | PK | Permission identity: "owner", "editor", "viewer" |
| level | integer | NO | | Numeric ordering for comparison |

[Continue for every table...]

## Design Decisions

### [Decision: Natural String PKs for Reference Tables]
**Date:** YYYY-MM-DD
**Design plan:** docs/design-plans/YYYY-MM-DD-feature.md
**Decision:** Reference tables use natural string PKs, entity tables use ULID/UUID.
**Rationale:** Reference data's name IS its identity. Surrogate keys add pointless
indirection and produce opaque FKs.
**Alternatives rejected:** UUID PKs with name-based lookups (extra SELECT per
operation), hardcoded UUID constants (fragile, two sources of truth).

[One entry per significant schema decision. Linked to design plan that made it.]

## Denormalisation Register

| Table.Column | Justification | Measured Evidence | Sync Strategy |
|-------------|---------------|-------------------|---------------|
| (none currently) | | | |

[If any denormalisation exists, document the measured query performance that
justified it and how the cached/derived value stays in sync with the source.]
```

### Lifecycle

| Event | Action on `docs/architecture/database.md` |
|-------|------------------------------|
| First design plan with DB work | Create `docs/architecture/database.md` with initial sections |
| Subsequent design plans with DB work | Update affected sections (new entities, new decisions) |
| DBA review during code review | Validate document is current; update if stale |
| Schema migration | Update data dictionary and ERD to match |

### What Goes Where

| Content | Location | Why |
|---------|----------|-----|
| "What does this entity mean?" | `docs/architecture/database.md` | First-class, findable |
| "Why did we choose this key strategy?" | `docs/architecture/database.md` Design Decisions | Accumulated rationale |
| "What schema changes does this feature need?" | Design plan | Per-feature context |
| Column types, constraints, FKs | `docs/architecture/database.md` Data Dictionary | Single source of truth |
| Denormalisation justifications | `docs/architecture/database.md` Denormalisation Register | Auditable |
| Data flows between components | `docs/architecture/database.md` DFDs | System-level view |

## Quick Reference

| Element | Convention |
|---------|------------|
| Table names | `snake_case`, plural |
| Column names | `snake_case` |
| Entity PKs | ULID as UUID |
| Reference PKs | Natural string (`name TEXT PRIMARY KEY`) |
| Join table PKs | Composite FK (`PRIMARY KEY (a_id, b_id)`) |
| Money | `Numeric(19, 4)` |
| Timestamps | `TIMESTAMP WITH TIME ZONE` (`timestamptz`) |
| Text | `text` (not `char(n)` or `varchar(n)`) |
| Nullability | NOT NULL by default |
| Constraints | `ck_table_description`, `uq_table_columns`, `excl_table_description` |
| Indexes | `idx_table_columns` |
| Foreign keys | `fk_table_reftable` |
