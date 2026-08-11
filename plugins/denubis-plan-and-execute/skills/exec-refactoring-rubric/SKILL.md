---
name: exec-refactoring-rubric
family: executing-an-implementation-plan
description: Use when evaluating or applying a behavior-preserving refactor - requires a concrete maintenance cost, current consumers, behavioral coverage, and one bounded transformation
user-invocable: false
---

# Refactoring Rubric

## Qualification

A smell name is a lead, not a defect. Refactoring is warranted when current source exhibits
a concrete maintenance cost such as:

- one responsibility changes in several unrelated places;
- one module changes for several unrelated reasons;
- duplicated behavior can diverge and already has multiple real consumers;
- business decisions cannot be tested without extensive I/O mocking;
- a public name or boundary misleads current callers;
- dead or superseded code increases the live decision surface; or
- dependency direction creates an observable cycle or unsafe state transition.

Metrics and thresholds cannot authorise a refactor. Size, complexity, churn, fan-in, and
clone matches identify where to inspect. Confirm the actual cohesion, coupling, duplication,
testability, or ownership problem in source and consumers.

## Safety boundary

Require behavioral coverage capable of detecting a changed contract. For untested code,
add characterization coverage supported by current requirements before structural change.
Do not refactor code merely because it is old, large, unfamiliar, or unlike a preferred
pattern.

Keep the two activities distinct:

- **Refactoring:** change structure while current behavior remains green.
- **Behavior change:** establish a new failing test and use the implementation workflow.

If a structural change requires altered behavior, split the work at that decision boundary.
A commit boundary is not required; verification is.

## Choose the smallest transformation

Map the observed problem to a specific transformation such as rename, extract function,
move responsibility, replace duplication with one owner, introduce a value object, or
separate deterministic decisions from I/O. Name all current consumers and the files that
must move together.

Prefer one coherent transformation whose benefit can be observed. Do not create a new
abstraction without current consumers or preserve the old path as an alias unless
compatibility is an explicit requirement.

For each prescription, state:

- exact source and concrete maintenance cost;
- proposed transformation and affected consumers;
- behavioral coverage and command;
- expected structural improvement;
- rollback boundary if the check fails; and
- exclusions not assessed.

## Evidence

Run the focused behavioral checks before and after the transformation and relevant project
gates afterward. Inspect the diff for accidental behavior, scope growth, unused interfaces,
and leftover superseded paths.

This rubric does not edit code or write a report. The caller or refactoring executor owns
the authorised transformation and its evidence.
