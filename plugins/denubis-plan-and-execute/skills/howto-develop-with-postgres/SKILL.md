---
name: howto-develop-with-postgres
description: Use when changing PostgreSQL schemas, queries, or transactions - derives keys, constraints, indexes, and transaction behavior from the domain and observed workload
---

# Developing with PostgreSQL

## Ground the database boundary

Read the supported PostgreSQL version, migrations, schema, access layer, transaction
owner, representative queries, project naming rules, and relevant architecture. Use
current PostgreSQL and driver documentation for syntax and runtime behavior. Do not impose
an ORM, key family, naming prefix, isolation level, or documentation template across
projects.

State the domain invariant, concurrent actors, failure atomicity, and query workload
before choosing schema or transaction machinery.

## Put durable invariants in the database

- Normalize around actual functional dependencies. Denormalize only for a measured
  workload with a named source of truth and synchronization rule.
- Make nullability express the domain; `NULL`, empty text, zero, and missing relationships
  are different states.
- Use primary keys, foreign keys, `UNIQUE`, `CHECK`, and exclusion constraints for rules
  the database can enforce under concurrency.
- Choose types for semantics: `numeric` for exact decimal quantities, `timestamptz` for
  instants, bounded checks for domain limits, and JSON only when the shape genuinely varies
  or PostgreSQL operators are part of the requirement.

Conditional uniqueness is a partial unique index, not a partial `UNIQUE` constraint:

```sql
CREATE UNIQUE INDEX subscriptions_one_active_plan
    ON subscriptions (user_id, plan_id)
    WHERE cancelled_at IS NULL;
```

Review migration SQL rather than trusting autogeneration. Existing applied migrations are
history; correct them with a new migration unless the project proves the original has not
left a private environment.

## Choose keys from identity and consumers

Use a natural key when it is stable, compact, truly identifies the entity, and changes
under explicit migration. Use a surrogate key when identity is otherwise composite,
mutable, private, or inconvenient for consumers. Composite keys are often correct for
association identities. UUID, integer identity, and time-sortable identifiers have
different locality, size, disclosure, and generation trade-offs; none is a universal
default, and an opaque identifier is not an authorization control.

## Make transaction ownership visible

One layer owns begin, commit, rollback, and retry for a unit of work. Lower-level
operations accept or otherwise participate in that transaction without secretly opening
or committing another. Use the project's ordinary naming; a `TX_` prefix is not a
portable semantic contract.

Keep all effects that must succeed or fail together inside the unit. Place external
network calls outside a long database transaction unless an explicit idempotency, outbox,
or compensation design owns the split. Handle cancellation and exceptions so connections
return to the pool and partial work cannot be mistaken for success.

`READ COMMITTED` is often sufficient, but select isolation from the anomaly the operation
must prevent. PostgreSQL Serializable transactions may abort with a serialization failure;
the caller must be able to retry the whole transaction with bounded attempts and safe
external effects. Row locks solve specific contention, not every consistency problem.

## Query safely and index observed access

Pass values through the driver's parameter API. Parameters do not stand for identifiers;
allowlist or compose identifiers with the driver's dedicated SQL-object API. Neither
f-strings nor t-strings supply SQL safety by themselves.

Index for demonstrated filters, joins, ordering, uniqueness, and foreign-key maintenance.
PostgreSQL does not automatically index referencing foreign-key columns, so examine the
delete/update behavior and relevant queries. Do not index every column: each index costs
writes, storage, vacuum work, and migration time. Validate important choices with realistic
plans and data distribution, not an unqualified `EXPLAIN` screenshot.

## Verification

Test schema changes through the migration tool on a representative database. Exercise
upgrade, constraints, transaction rollback, concurrency or retry behavior where relevant,
and the important query plans. Confirm tests reach PostgreSQL rather than an incompatible
stand-in. Update living database architecture only when the repository maintains it and
the implemented relationship or invariant changed; do not create a mandatory encyclopedia
for every database project.
