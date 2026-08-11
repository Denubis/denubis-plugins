---
name: brainstorming
family: starting-a-design-plan
description: Use after design intent is clear - investigates current constraints, tests genuine alternatives, and returns one recommended design with explicit tradeoffs
user-invocable: false
---

# Exploring a Design

## Purpose

Find a design that satisfies the settled context and fits the system that exists. The
result is one recommended design, the evidence that supports it, its costs, and any genuine
decision the human still owns.

## Investigate

Direct inspection is the default. Read the current implementation, tests, architecture,
interfaces, dependency configuration, and external contracts relevant to the design.
Search the full named universe before concluding that a component or pattern is absent.

Delegation is optional for a bounded independent investigation. A delegated result is a
lead: open its cited files, docs, logs, or tests before using it. Do not make agent
availability a prerequisite for design work.

For current libraries, services, or APIs, use authoritative current documentation and pin
the version or contract the design assumes. Separate observed facts from inferences.

## Form candidates

Start with the simplest design that satisfies the goals and constraints while using
current project boundaries. Identify its components, data flow, state transitions,
failure behavior, security and operational boundaries, migration or compatibility needs,
and named downstream consumers.

Do not invent alternatives to create a comparison table. Compare another approach only
when it is technically viable under the accepted constraints and changes a material
quality such as correctness, reversibility, operational risk, compatibility, or cost.

For each genuine candidate, state:

- the boundary and responsibility of each component;
- the evidence that it fits current state;
- the observable consequence for users and downstream systems;
- failure and recovery behavior;
- what becomes harder to change later; and
- the acceptance criteria or tests capable of falsifying it.

Reject candidates whose necessary dependency, authority, consumer, or failure recovery
cannot be established. Do not preserve rejected approaches in the current design unless
their rejection is itself a durable decision with continuing consequences.

## Recommend and resolve

Recommend one design. Explain why its evidence and tradeoffs fit the settled goals. Name
uncertainties honestly; do not use fluent prose to make an untested assumption sound
settled.

If evidence determines the choice, proceed without asking. If materially different viable
designs remain, ask one pointed question at a time with what each answer implies. Capture
the exact human source locator and resolver for the selected direction.

Return the recommended design, current evidence, real tradeoffs, rejected candidates that
must become durable decision records, remaining blockers, and authority sources to
`denubis-plan-and-execute:design-write`.
