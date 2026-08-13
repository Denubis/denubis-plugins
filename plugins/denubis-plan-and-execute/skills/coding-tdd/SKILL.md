---
name: coding-tdd
description: Use when implementing a feature, bug fix, or behavioral refactor - establishes the behavior with a failing test, makes it pass minimally, then cleans up under green tests
user-invocable: false
---

# Test-Driven Development

## Scope

Use the project test harness for features, bug fixes, and behavioral refactors. Generated
artifacts, declarative configuration, and exploratory spikes may need a different positive
check, but they do not justify shipping unverified behavior. Follow stricter project rules
when present.

## RED

RED: write the smallest behavioral test that expresses the missing or broken observable
result. Prefer the public boundary and real domain values. Name the condition and expected
outcome; avoid asserting incidental calls or private structure unless that structure is
itself the contract.

Run the focused test before implementation. Observe it fail for the intended reason. A
syntax error, missing fixture, wrong import, malformed command, or failure in unrelated
setup is not a valid red state. A test that passes on its first run provides no red-state
evidence; determine whether the behavior already exists or the test cannot observe it.

For a bug, reproduce the actual symptom or establish the closest bounded production path.
For existing untested behavior that must be refactored, first add characterization tests
whose expected behavior is supported by current requirements or observed consumers.

## GREEN

GREEN: make the smallest coherent implementation that satisfies the test. Keep the change
at the responsible boundary and include the first real consumer of any new interface. Do
not weaken the test, special-case only the fixture, or bundle unrelated refactoring.

Run the focused test and inspect its positive signal. Then run nearby tests capable of
detecting regressions in the affected contract.

## REFACTOR

REFACTOR: improve structure only while the behavior stays green. Remove duplication or
improve names within the tested scope. Do not use the passing test as authority to refactor
uncovered neighboring code.

Rerun the focused and affected checks after cleanup. Repeat the cycle for the next distinct
behavior; do not combine several failure conditions into one opaque test.

## Test quality

A useful test:

- fails when the required behavior is absent and passes when present;
- is deterministic and isolated from unrelated global state;
- verifies output, state transition, error, or externally visible interaction;
- uses mocks only at actual external boundaries;
- cleans up resources it creates; and
- provides a failure message that identifies the broken contract.

Property-based tests are appropriate when the behavior is better expressed as an
invariant, round trip, idempotence rule, or normalization property. Integration tests are
appropriate when the contract crosses a real service, process, filesystem, or database
boundary.

## Completion evidence

Report the red command and intended failure, the green command and result, affected-suite
results, and any boundary not exercised. Do not claim that a test guards the behavior if
its red state was never observed.
