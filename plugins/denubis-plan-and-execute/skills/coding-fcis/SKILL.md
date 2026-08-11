---
name: coding-fcis
family: coding-effectively
description: Use when business decisions are entangled with I/O or nondeterminism - separates pure transformations from a thin imperative boundary where that improves testability
---

# Functional Core, Imperative Shell

## Purpose

Use this separation when it improves testability, reuse, or failure clarity. It is a design
tool, not a requirement that every file be labelled or every I/O call live in a different
module.

## Boundaries

The **Functional core** receives all data and decision inputs explicitly and returns a
value or domain error. It contains deterministic validation, calculation, normalization,
selection, and state-transition logic. Tests use ordinary values without filesystem,
network, database, clock, or random-number fixtures.

The **Imperative shell** acquires data and nondeterministic inputs, calls the core, and
applies the result through files, processes, databases, networks, clocks, randomness, or
other external state. Keep coordination and boundary-specific error handling here.

Typical shape:

```python
def decide_order(order: Order, rules: Rules, now: datetime) -> OrderDecision:
    ...  # deterministic domain decision


def process_order(order_id: str, repository: OrderRepository, clock: Clock) -> None:
    order = repository.load(order_id)
    decision = decide_order(order, repository.rules(), clock.now())
    repository.apply(decision)
```

Passing a database session into a function does not make its queries pure. Passing a time,
random value, or loaded record into the decision function does.

## Apply proportionately

Separate code when:

- business branches cannot be tested without extensive mocks;
- several I/O paths need the same decision logic;
- nondeterminism obscures expected behavior; or
- the transaction boundary and domain decision have different failure semantics.

Keep a small cohesive boundary function together when splitting it would add indirection
without isolating a meaningful decision. Logging and metrics belong where their event is
owned; do not call a function pure if its observable behavior includes emitting them.

Refactor by characterizing current behavior, extracting a value-in/value-out decision,
and leaving acquisition and persistence in the shell. Do not refactor untested code merely
to fit the pattern.

## Verify

Test core decisions with values and shell behavior at the real or faithfully isolated
external boundary. Confirm transaction, retry, ordering, and partial-failure behavior in
the shell; pure tests alone cannot establish them.
