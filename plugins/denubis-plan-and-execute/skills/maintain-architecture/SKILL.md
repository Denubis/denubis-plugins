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

Map:

- system boundary, actors, external systems, and responsibilities;
- components, data flows, state transitions, and public contracts;
- implemented constraints and their observable checks;
- decisions with continuing consequences;
- downstream consumers and failure behavior;
- claims present only in docs or only in implementation; and
- missing, stale, ambiguous, or wrong-role source references.

Direct code and test evidence settles technical facts. A human question is appropriate
only when current sources expose a genuine ownership, scope, or architecture decision that
cannot be recovered. In that case ask one pointed question with the exact consequences and
sources.

## Update and verify

Invoke `denubis-plan-and-execute:architecture-update` with the working root, mapped
implemented state, relevant document paths, source pointers, and confirmed defects.

After it returns, inspect the edits directly. Verify links and source pointers, rerun any
structural documentation checks, and compare each changed claim with its implementation
evidence. Confirm that proposed but unimplemented design remains in its design plan and
that living documents contain no correction narrative.

Report changed documents, resolved defects, exact verification evidence, and any genuine
unresolved decision. Do not commit, publish, or update remote systems without separate
authority.
