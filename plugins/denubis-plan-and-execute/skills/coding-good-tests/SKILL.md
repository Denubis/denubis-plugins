---
name: coding-good-tests
description: Use when writing or reviewing tests - chooses the smallest observable boundary that can fail for the intended reason and keeps test development under the same red-green discipline
---

# Writing Good Tests

## Start with the claim and consumer

Read project instructions, test configuration, custom runners, and nearby tests. State the
behavior, consumer, setup, positive signal, and defect that should make the check fail.
Use the repository's documented command and installed plugins; do not paste a universal
pytest invocation whose optional flags the project may not support.

Prefer the narrowest stable public boundary that establishes the claim. Unit tests suit
pure decisions and failure classification. Integration tests suit adapters, persistence,
configuration, and component seams. End-to-end tests suit a small number of critical user
journeys. “Mostly integration” and “one assertion per test” are heuristics, not rules.

## Develop the test red-green-refactor

1. Write the smallest check for the missing or defective behavior.
2. Run it against the uncorrected implementation and observe failure for the intended
   reason. A malformed command, broken fixture, uncollected test, or unreachable branch is
   not useful red evidence.
3. Make the smallest implementation pass without weakening the expectation.
4. Rerun the focused check and inspect its positive signal.
5. Refactor only covered behavior, then rerun focused and affected broader checks.

Do not delete, skip, loosen, invert, or over-mock a failing test to make the run green. If
the expectation is wrong, demonstrate the contract error and correct it explicitly.

## Test behavior, not the edit

Do not read source or prose, assert that a chosen phrase is present or absent, then write
that phrase. This observes the change itself. An independent gate exercises public
behavior, parses a declared format through its consumer, recomputes an invariant, or uses
syntax analysis whose classification does not share the implementation's wording.

An empty result needs scope and a positive control. Demonstrate that the query or probe can
find a known match or reject a deliberately defective fixture; otherwise “nothing found”
cannot distinguish success from a check that exercised nothing.

For prose methods, give an acting agent a realistic task in one artifact and keep expected
behavior and failure evidence in a separate evaluator-only oracle. Observe consequential
output such as a diff, tool trace, filesystem state, or public fixture behavior. Include a
permitted or non-match control. Apply `testing-skills-with-subagents`.

## Control state and time

Each test owns or uniquely identifies mutable state. Clean up processes, connections,
locks, temporary non-test directories, and other resources that outlive the assertion.
Use fresh fixtures when isolation matters; do not rely on test order or a previous failure.

Wait for an observable condition with a bounded deadline rather than sleeping for guessed
completion time. A deliberate sleep is appropriate only when elapsed time is itself the
behavior under test, and the assertion must distinguish early, on-time, and late results.

## Use doubles at the consequential boundary

Choose real collaborators when they are fast, deterministic, and part of the claim. Use a
fake, stub, or mock when an external effect is slow, unavailable, destructive, or needs a
controlled failure. “Never mock internals” and “always mock externals” are too absolute:
the boundary follows the behavior being established.

Assert the observable result or outgoing contract, not merely that a mock was called. If
setup recreates most of the collaborator's logic, use a higher-level fixture or contract
test. Do not add production methods used only by tests when a fixture, factory, or public
boundary can establish state honestly.

## Review evidence

Run the focused test, affected suite, and project gates appropriate to the change. Confirm
collection, environment, fixture lifetime, parallel-safety assumptions, and failure-path
coverage. A test count, coverage percentage, snapshot update, or green model review is a
lead, not proof that the intended behavior ran.

Use `coding-property-testing` when a generative invariant is stronger than a list of
examples.
