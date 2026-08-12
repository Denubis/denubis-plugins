---
name: architecture-update
description: Use when updating living architecture from an implemented-state map - writes current truth, repairs reference defects, and verifies each changed claim against its source
user-invocable: false
---

# Update Architecture Documentation

## Purpose

Write current architecture from a bounded map of implemented state and evidence. Living
architecture describes implemented state. It does not approve a design, predict future
topology, preserve correction history, or certify work merely because documentation was
generated.

## Input boundary

Require the working root, implementation change boundary, implemented-state map, relevant
document paths, exact source pointers, confirmed defects, and any applicable predicted
boundary map and reconciliation result from the caller. Open the supplied evidence rather
than trusting its summary.

Before reading the prediction, independently enumerate every code, schema, configuration,
generated, and runtime surface in the supplied change boundary and derive its implemented
boundary consequence. Account for each surface, including one that preserves its boundary.
Then compare that implementation-first inventory with the caller's map and prediction. If
the change boundary is unavailable or the caller's map omits a changed surface, return an
input defect rather than writing architecture from an incomplete account.

Do not project a future design into living architecture. A design plan may reveal that a
current document is already false, but unimplemented components, flows, schemas, and
constraints remain in the design plan until source or runtime evidence makes them real.

The planner's boundary map says what should be made. The implemented-state map and its
sources say what was made. Use the former to detect divergence and the latter to write
living architecture; never copy the prediction into current topology without implemented
evidence.

Inventory the architecture directory before creating a document. Follow the repository's
current organization where it has a clear semantic owner; do not create a second taxonomy
or a new file merely to narrate the update.

## Document ownership

Place each claim with its owner:

| Claim | Living owner |
|---|---|
| System boundary, components, flows, consumers | Context or component architecture |
| Implemented invariant and how it is checked | Constraints |
| Current database shape and transaction boundary | Database architecture |
| Decision with continuing consequences | ADR or decision record |
| Actor goals and access patterns | Personae |
| Project-specific term | Glossary |
| Historical dispute, superseded wording, incident narrative | Git or explicit archive |

Update an existing owner instead of duplicating the claim. Remove a retired entity from
living indexes and relationships in the same coherent change that removes its source.

## Boundary divergence

Classify a predicted/implemented difference before writing:

- An internal change in **how** preserves the boundary participants, inputs, outputs,
  semantics, consumers, observable effects, ordering, persistence, control, and failure
  behavior. Write the implemented current truth without preserving the comparison.
- A load-bearing change in **what** changes at least one of those properties. If it is an
  accepted design change, update the accepted design and create or supersede an ADR that
  records what changed and why, with exact authority. If it lacks that decision, return an
  integrity blocker; implementation drift and model agreement cannot create an Accepted
  ADR.

Living architecture still states observable implemented truth. It does not disguise an
unresolved design mismatch as agreement, and the caller must not claim completion while a
load-bearing mismatch remains unresolved.

## Evidence and authority

Every technical claim points to the exact current implementation source: file and symbol,
test, generated manifest, schema, log, or operational observation capable of supporting
it. State the relevant boundary and do not generalize beyond what the source observed.

When a decision depends on a human instruction, human authority uses an exact source
locator and resolver selecting one human message. A quotation, paraphrase, model-authored
note, session UUID without a message locator, or review status does not create authority.
Repair an unresolved reference before writing a dependent current claim; if repair is not
possible, obtain a focused human invocation.

## Update

Apply factual corrections directly within the requested architecture-maintenance scope.
Ask the human only when the evidence leaves a genuine architecture or authority decision;
ask one pointed question at a time and record its exact source if the answer is memorialized.

No palimpsests: write what the system is now. Do not retain “previously,” “corrected,”
review dialogue, phase narration, or explanations aimed at a superseded version in living
sections. Git already preserves the older text.

Keep diagrams and tables only when they make relationships easier to inspect. Update every
edge affected by a renamed, moved, added, or retired entity. Do not preserve a marketplace
or directory grouping as the primary architecture axis unless it represents an actual
runtime boundary.

## Verify and return

Verify every link and source pointer. Re-read each changed paragraph against its source,
run repository documentation or reference-integrity checks, and search the bounded living
architecture for the retired or corrected claim. A negative search is useful only after
its scope and exclusions are known.

Return the changed paths, evidence checked, removed stale claims, and unresolved defects.
Do not commit, publish, or modify remote systems; the caller's maintenance authority does
not imply release authority.
