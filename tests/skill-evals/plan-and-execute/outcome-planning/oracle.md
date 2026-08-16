# Evaluator oracle: outcome planning

Read this only after the actor has finished.

## Protected decision

The accepted design contains one independently usable and reversible outcome: the public
greeting interface supports uppercase output, its tests establish both modes, and the user
documentation describes the option. There is no cross-component runtime flow, migration,
external service, or irreducible human judgment.

## Evidence to inspect

- Every plan artifact the actor created.
- Whether the plan's tasks keep interface, first consumer, tests, and documentation in the
  same coherent outcome.
- Whether any extra artifact has a real consumer in this plan.
- Whether the plan invents a human decision or UAT judgment for deterministic output.
- Whether commands name a positive signal and a relevant failure.

## Failure evidence

The method fails this case if the observed plan:

- decomposes the single outcome into chronology-only phases that are not independently
  usable;
- creates mandatory empty/non-applicable flow or UAT paperwork with no consumer;
- separates the interface from its tests or first real consumer;
- asks the human to choose an ordinary implementation detail fixed by the design and
  fixture; or
- relies on an empty search or expected phrase as verification.

Different filenames or prose are not failures when the plan preserves the outcome and
evidence boundaries.

