---
name: design-clarify
family: starting-a-design-plan
description: Use when a design request contains unresolved intent, scope, constraints, or contradictions that repository and external evidence cannot settle
user-invocable: false
---

# Clarifying a Design

## Purpose

Separate recoverable facts from human intent. Clarification ends when the design problem,
scope, constraints, success conditions, and real open decisions are precise enough to
explore—not when a questionnaire has been exhausted.

## Inspect before asking

Inspect before asking. Read the initiating request, project instructions, current
architecture, relevant notes and exact authority sources, design guidance, and nearby code
and tests. If a fact may have changed outside the repository, consult current authoritative
documentation.

Map:

- actors, systems, data, interfaces, and downstream consumers in the design's universe;
- current behavior and the observable problem;
- explicit goals and exclusions;
- technical, policy, compatibility, and operational constraints;
- acceptance judgments the human must make; and
- contradictions between the request and current evidence.

Resolve contradictions first because later questions may disappear once the governing
goal is clear. Distinguish a genuine conflict from different requirements applying at
different boundaries.

## Question filter

Do not ask the human for a fact that code, tests, logs, project records, or current
documentation can establish. Do not ask them to choose between an existing pattern and an
invented alternative when the accepted constraints select the pattern. Do not turn an
ordinary implementation detail into a design decision.

A question survives only when its answers lead to materially different scope, behavior,
risk, compatibility, or authority. For each survivor, state:

- the exact uncertainty;
- what current evidence establishes;
- the viable answers;
- what each answer changes; and
- the sources the human can open.

Ask one pointed question at a time. Resolve it before moving to another protected decision.
Use the human's answer as authority for the expressed choice; do not require them to defend
it against a model-generated alternative.

## Output

Return a settled context bundle containing:

- problem and desired outcome;
- universe of discourse and present behavior;
- goals, non-goals, and constraints;
- known consumers and failure modes;
- acceptance judgments;
- design decisions already made;
- unresolved blockers; and
- an authority source entry for every human instruction used, with exact locator and
  resolver invocation.

Do not write design solutions in this step. If a human answer changes an existing durable
decision, identify the document that must be brought to current truth during design
writing.
