---
name: exec-coherence-review
description: Use when a specific design-conformance risk warrants an independent audit of implemented behavior against an accepted design and its current evidence
user-invocable: false
---

# Design-Conformance Review

## Purpose

Test a specific concern that implemented behavior may diverge from an accepted design.
Use only when a design-conformance question remains after ordinary implementation and
verification, or when the human or governing plan explicitly requests the audit.

It is not a substitute for an empty UAT plan, a routine phase transition, or missing
automated evidence. The executor already owns acceptance-criterion coverage. This review
adds an independent reading only where that reading could expose a named risk.

## Establish scope

Resolve:

- the accepted design and relevant phase;
- the exact acceptance criteria or assumptions at risk;
- the implementation files and current diff;
- the predicted boundary-flow artifact and implemented-state map when the plan says the
  change affects meaningful data or control flow;
- the tests, operational results, architecture, and decision records that claim to bind
  the behavior; and
- the repository state those sources describe.

Open every cited source. A phase summary, review report, task label, or commit message is
not a substitute for the implementation or observed check. If the design's authority
pointer is missing, ambiguous, stale, or wrong-role, report the integrity defect and do
not infer the decision.

## Audit

For each scoped question, compare:

| Element | Required observation |
|---|---|
| Design intent | Exact current design or decision source |
| Implemented behavior | File and line, runtime observation, or generated artifact |
| Verification | Test or operational command with its positive and failure signals |
| Assumption | Condition on which the comparison depends and what would invalidate it |
| Downstream fit | Named consumer and whether the implemented interface satisfies it |
| Boundary flow | Predicted versus implemented participants, data or control, transformation, effect, ordering, persistence, failure route, and consumer |

Inspection may be direct or optionally delegated with this exact bounded surface. The
main session opens every returned pointer and recomputes relevant checks.

## Return

Report confirmed mismatches, unsupported claims, unresolved source defects, and the
evidence that establishes each. When the inspected surface reveals no mismatch, state the
surface and limitations; do not generalize beyond them.

The review does not certify conformance. Its findings are leads until the caller verifies
them against source and observed behavior. It does not require human approval unless a
confirmed mismatch exposes a genuine design choice.
