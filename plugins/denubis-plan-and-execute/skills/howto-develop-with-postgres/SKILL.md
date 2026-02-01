---
name: howto-develop-with-postgres
description: Use when writing database access code, creating schemas, or managing transactions with PostgreSQL - enforces transaction safety, ACID compliance, type safety, and naming conventions
---

# PostgreSQL Development Patterns

## Overview

The database is the source of truth. Treat it with respect.

**Core principles:**
- Transactions prevent partial updates (data corruption)
- ACID compliance is non-negotiable
- Type safety catches errors early
- Naming conventions ensure consistency

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

**Exceptions:**
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

## Red Flags

**Transaction management:**
- Method calls `.begin()` but no `TX_` prefix
- Method has `TX_` prefix but accepts session
- Multi-step operation without transaction

**Type safety:**
- JSONB without validation
- UUID stored as string
- Float for monetary values

**Schema:**
- Missing indexes on foreign keys
- No timestamps
- camelCase in database identifiers

## Quick Reference

| Element | Convention |
|---------|------------|
| Table names | `snake_case`, plural |
| Column names | `snake_case` |
| Primary keys | ULID as UUID |
| Money | `Numeric(19, 4)` |
| Timestamps | `TIMESTAMP WITH TIME ZONE` |
| Indexes | `idx_table_columns` |
| Foreign keys | `fk_table_reftable` |
