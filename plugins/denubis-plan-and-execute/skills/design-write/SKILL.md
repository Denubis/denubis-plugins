---
name: design-write
family: starting-a-design-plan
description: Use after a design direction is selected - writes one current design with resolvable authority, explicit boundaries, acceptance criteria, and coherent implementation phases
user-invocable: false
---

# Writing a Design Plan

## Purpose

Write the selected design so another session can understand the relevant universe, why the
boundaries exist, how failure appears, and what observable results would make the design
accepted. The document is a current design, not a transcript, review certificate, or
step-by-step implementation script.

## Location and status

Write `docs/design-plans/YYYY-MM-DD-<topic>.md` in the selected working root. Use `Draft`
until the human has accepted the design and every authority source on which it depends
resolves exactly. Change the status to `Current design` only after those conditions hold.

If an existing current design owns the same decision, update it rather than layering a
second source of truth. Superseded argument belongs in Git or an explicit archive; do not
append correction history to living sections.

## Document contract

Use the sections the design actually needs, drawn from this shape:

```markdown
# [Design title]

**Status:** Draft | Current design

## Purpose
[Problem, desired outcome, and why this design exists]

## Authority Sources

| Decision or instruction | Exact source | Resolver | Resolution condition |
|---|---|---|---|
| [human-owned boundary] | [provider-qualified locator] | `[exact invocation]` | [unique expected result] |

## Universe of discourse
[Actors, systems, data, consumers, external boundaries, and explicit exclusions]

## Current state
[Observed behavior with code, test, log, or architecture pointers]

## Goals and non-goals
[Current scope]

## Design
[Components, responsibilities, data flow, state transitions, and contracts]

## Failure and recovery
[Observable failures, invalidation conditions, and safe recovery]

## Decisions
[Only decisions with continuing consequences: choice, alternatives that were genuinely
viable, evidence, consequences, and invalidation condition]

## Acceptance criteria
[Scoped identifiers with positive and failure observations]

## Implementation phases
[Coherent outcomes, dependencies, criteria owned, and resulting usable state]

## Verification and human judgment
[What automation or operations can prove, and the irreducible judgments reserved for UAT]
```

Add a glossary only for terms whose local meaning is not obvious from the document. Add
dependency or migration sections when the design actually introduces them.

## Authority and evidence

Every human-derived decision includes an exact locator and resolver invocation. The
resolver must select exactly one human message. A quotation, paraphrase, session UUID
without a message locator, model note, or review summary does not satisfy the reference.

Code and operational claims cite the current file, symbol, test, log, or generated
artifact. External contracts cite authoritative current documentation and the applicable
version. State inference as inference.

If a pointer is missing, ambiguous, stale, wrong-role, or unavailable, repair it. When it
cannot be repaired from the current evidence, keep the design draft and obtain a focused
human invocation rather than inventing authority.

## Content boundaries

Specify architecture and public contracts at enough detail to protect decisions:
component responsibilities, schemas or message shapes consumed elsewhere, state
transitions, validation boundaries, and failure behavior. Leave function bodies, exact
task sequences, and incidental file edits to implementation planning.

Living architecture describes implemented state. A future design remains in the design
plan until implementation changes the system; do not rewrite living architecture as if
proposed components already exist. If current architecture is already false, record and
repair that integrity defect separately.

Decision entries state what is currently chosen and its consequences. Do not include the
conversation, apology, earlier mistaken version, or a model's argument with an offscreen
claim. No model-authored approval, review status, or provenance-shaped record proves the
design was accepted.

## Acceptance and phases

Every acceptance criterion names an observable success and relevant failure condition.
Cover every goal, contract, compatibility boundary, and failure behavior. Distinguish
deterministic checks from human judgment; do not disguise a command with expected output
as UAT.

Implementation phases are coherent usable outcomes, not arbitrary time slices. Each phase
names its dependencies, the criteria it owns, and the state it leaves working. Put a new
interface with its first real consumer. Avoid phases consisting only of speculative
abstractions or cleanup of untested code.

## Challenge and acceptance

Before asking for acceptance, resolve technical inconsistencies directly. Invoke
`denubis-plan-and-execute:proleptic-challenge` only for a named consequential uncertainty
that survives the evidence already in the document. Apply evidence-determined corrections
without burdening the human; present genuine design choices one at a time.

Ask the human one final pointed question: whether the written design matches the intended
outcome and boundaries. Resolve their exact response and add it to `## Authority Sources`.
If they change the design, update the relevant sections to current truth and recheck
criteria and phases before asking again.

## Verify and return

Before handoff, verify that every source resolves, every goal has acceptance coverage,
every phase has a usable outcome and dependency order, every public interface has a named
consumer, and no section claims unimplemented state as current architecture.

Return the absolute design path, status, unresolved blockers, and working directory. Do
not commit, publish, deploy, or mutate GitHub. Those actions require separate authority and
their own observable evidence.
