---
name: maintain-architecture
description: Use for standalone architecture maintenance - maps implemented state against living architecture, resolves factual drift, and updates current documentation with exact evidence
user-invocable: true
argument-hint: "[artifact, change range, or architecture scope]"
---

# Maintain Architecture

## Purpose

Bring living architecture into agreement with implemented state. This workflow discovers
what exists, identifies factual drift and unresolved decisions, invokes the document
updater, and verifies the result. It does not redesign the system or turn a future plan
into current topology.

## Resolve scope and baseline

Use the artifact, change range, or scope supplied by the human. If none is supplied and
the working tree has relevant changes, use the repository merge base plus staged,
unstaged, and relevant untracked files. If the request is an audit of current docs, compare
the named architecture surface with its implementation sources rather than requiring a
Git diff.

When called from plan execution, also require the plan's `flow-boundaries.md` and the
caller's implementation change boundary, implemented-state map, and exact supporting
sources. The prediction is comparison input, not evidence of implemented state. Invoke
this workflow only when reconciliation identified an architecture-owned claim,
relationship, source pointer, or decision record that needs creation, change, or removal.

If several scopes would lead to materially different work and evidence cannot identify
the intended one, ask one pointed question. Otherwise proceed with the narrowest scope
that fully contains the changed responsibilities and their consumers.

Record what the chosen baseline cannot see. An empty diff or search result does not prove
that architecture is current until the implementation and document universes have both
been inspected.

## Map current state

Inspect the implementation and architecture directly. Read project instructions, list all
files under `docs/architecture/`, and open the documents relevant to the scope. Inspect
the actual modules, schemas, manifests, hooks, commands, tests, and runtime evidence on
which those documents rely.

For plan reconciliation, reconstruct the implemented boundary from the supplied change
range before reading the predicted map: enumerate every changed code, schema,
configuration, generated, and runtime surface and account for its boundary consequence.
Then compare that implementation-first inventory with the caller's map and prediction.
Treat an omitted changed surface as an incomplete input, not evidence that no flow changed.

Map:

- system boundary, actors, external systems, and responsibilities;
- components, data flows, state transitions, and public contracts;
- implemented constraints and their observable checks;
- decisions with continuing consequences;
- downstream consumers and failure behavior;
- claims present only in docs or only in implementation; and
- missing, stale, ambiguous, or wrong-role source references.

When a predicted boundary map applies, compare it with the implemented map. Distinguish an
internal change in how from a load-bearing change in what crosses the boundary. A changed
participant, flow, meaning, consumer, observable effect, ordering, persistence, control
signal, or failure route is a change in what. A non-applicable prediction contradicted by
implemented flow is a plan defect, not a documentation shortcut.

Direct code and test evidence settles technical facts. A human question is appropriate
only when current sources expose a genuine ownership, scope, or architecture decision that
cannot be recovered. In that case ask one pointed question with the exact consequences and
sources.

## Update and verify

Invoke `denubis-plan-and-execute:architecture-update` with the working root, mapped
implemented state, relevant document paths, source pointers, confirmed defects, and any
applicable predicted boundary map and reconciliation result.

After it returns, inspect the edits directly. Verify links and source pointers, rerun any
structural documentation checks, and compare each changed claim with its implementation
evidence. Confirm that proposed but unimplemented design remains in its design plan and
that living documents contain no correction narrative.

Report changed documents, resolved defects, exact verification evidence, and any genuine
unresolved decision. Do not commit, publish, or update remote systems without separate
authority.
