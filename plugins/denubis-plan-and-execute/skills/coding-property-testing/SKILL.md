---
name: coding-property-testing
description: Use when a serialization, normalization, validation, ordering, or pure function has a meaningful generative invariant stronger than selected examples
---

# Property-Based Testing

## Choose a property before a generator

Use property-based testing when many inputs share an independently stated invariant:
round-trip, idempotence, preservation, inverse, ordering law, algebraic law, or agreement
with a simpler trusted implementation. Do not use it for CRUD with no transformation,
behavior whose oracle merely reimplements the function, or a “does not crash” claim when a
stronger contract exists.

State the valid input domain, property, and failure interpretation first. A property may
need several assertions to establish one behavior.

## Build strategies from the domain

- Encode constraints in the strategy rather than discarding most examples with `assume`.
- Generate representation boundaries, empty and minimal values, duplicates, Unicode,
  numeric extremes, and invalid inputs only when they belong to the real contract.
- Bound collection or text size when runtime is part of the test budget.
- Add explicit examples only for known regressions or boundaries that generation and
  shrinking do not reliably communicate. `@example` is not a universal requirement.
- Preserve shrunk failures and seeds through the project's normal Hypothesis database and
  CI configuration; do not invent a cache location.

Prefer the project's current Hypothesis profile and settings. Increase examples or remove
deadlines only for a measured reason; a large count cannot repair a weak property.

## Keep lifecycle honest

Pytest function-scoped fixtures are set up once for the whole Hypothesis test function,
not once per generated example. Generated examples therefore share mutations made through
that fixture. Use pure functions, generate independent values, reset state inside the
example, or place context setup and teardown inside the test when per-example isolation is
required. Health-check suppression does not create isolation.

Avoid external I/O inside a generative loop unless the integration boundary itself is the
claim and the cost and cleanup are controlled. A small deterministic model can serve as an
oracle, but it must be simpler and independently justified.

## Red-green evidence

Run the new property against the uncorrected implementation and observe a counterexample
for the intended defect. Confirm the fixture reached the behavior. Implement minimally,
rerun, and preserve the property while refactoring. Do not narrow the strategy, add an
`assume`, suppress a health check, or raise the example limit merely to hide a failure.

Review failures by their smallest counterexample and contract. A nondeterministic external
dependency, invalid generated state, or fixture leak is a test defect; a valid minimal
counterexample is implementation or design evidence.
