---
name: maintain-architecture
description: Use when implemented state and living architecture may differ - maps current evidence, updates the existing semantic owner, and verifies every changed relationship
user-invocable: true
argument-hint: "[artifact, change range, or architecture scope]"
---

# Maintain Architecture

## Boundary

Living architecture describes implemented state and continuing decisions. It does not
predict an unimplemented design, preserve correction history, or certify work because a
document was generated. This skill both maps and updates current architecture; do not
invoke a second writer skill for the same responsibility.

Use the scope or change range supplied by the human. Otherwise derive the narrowest
complete boundary from the merge base plus relevant staged, unstaged, and untracked work.
For a current-state audit, compare named documents with implementation sources without
requiring a diff. State what the baseline cannot see.

## Build the implemented-state map first

Read project instructions and inventory the relevant architecture universe. Inspect actual
modules, schemas, manifests, hooks, commands, tests, generated artifacts, and runtime
observations before a design prediction. An empty diff or search is not proof of currency;
use another route or positive control to establish the inspected universe.

Map only what the evidence supports:

- system boundary, actors, external systems, and responsibilities;
- components, public contracts, data or control flows, state transitions, and failure
  routes;
- durable constraints and how they are checked;
- decisions with continuing consequences;
- downstream consumers; and
- claims present only in documents or only in implementation.

When plan execution supplies a predicted boundary, derive the implemented map independently
from every changed code, schema, configuration, generated, and runtime surface, then
compare them. A different internal mechanism is not a design change when participants,
inputs, outputs, meaning, consumers, effects, ordering, persistence, control, and failure
behavior remain fixed. A difference in one of those properties is load-bearing: restore
the accepted design or obtain a real design decision before documenting it as accepted.

## Update the semantic owner

Follow the repository's existing architecture organization when it has a clear owner.
Update rather than duplicate:

- context or component architecture for boundaries, components, flows, and consumers;
- constraints for implemented invariants;
- database architecture for current schema and transaction boundaries;
- an ADR for an accepted decision with continuing consequences;
- personae for actor goals and access patterns; and
- glossary for project-specific terms.

Create only the sections and diagrams needed to make actual relationships inspectable.
There is no mandatory template set. A repository may keep all relevant truth in one
context document or split it by genuine semantic boundaries.

Write current truth directly. Do not retain “previously,” correction dialogue, phase
narration, historical commit identifiers, or comparison prose in living sections. Remove
a retired entity from indexes and affected edges with its source. Proposed components stay
in the accepted design until implementation evidence makes them current.

Technical claims cite resolvable current sources at the precision needed to check them.
Do not require an exact chat-message locator for facts established by code, tests, or
runtime evidence. A human source locator is required only when an architecture decision
depends on that human judgment and cannot be recovered from an accepted project artifact.

## Verify

Open every changed claim beside its source. Verify links and source pointers, run project
documentation or reference-integrity checks, and inspect every relationship affected by a
renamed, added, moved, or retired entity. A negative search for a stale name needs a known
search universe and positive control.

Report changed documents, exact evidence, removed stale claims, and any genuine unresolved
decision. Do not commit, publish, deploy, or mutate remote systems unless separately
authorised.
