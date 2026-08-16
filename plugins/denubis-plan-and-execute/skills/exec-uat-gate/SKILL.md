---
name: exec-uat-gate
description: Use after all mechanical and sanity checks pass when the finished behavior has an implication only human interaction and judgment can verify
user-invocable: false
---

# Human UAT Gate

## Boundary

UAT is the human touching an implication of the complete built surface. It owns only
irreducible judgment that remains after implementation, automated and operational checks,
independent sanity review, documentation reconciliation, and diff/status inspection.
It is not a phase transition, test-report review, permission ritual, or substitute for a
literal expected value.

Before presenting an entry, confirm that the surface exists now, every mechanical
prerequisite has fresh positive evidence, the human can perform the action, and informed
observers could reasonably disagree about the judgment. If the verdict reduces to a
command or deterministic output, return it to automated verification. If later
implementation could change the surface, wait for the finished surface.

## Present one falsifiable interaction

The plan owns coverage across intended use, relevant failure paths, and adjacent effects.
Present one entry at a time with:

1. the finished surface or workflow;
2. concrete setup and action;
3. the implication the human is judging; and
4. the experience that would falsify acceptance.

Ask one pointed question and wait. Do not make the human invent the experiment, rerun a
unit test, review the agent's checklist, or generically approve the project.

## Consume the observation

The response is authority only for the judgment actually expressed. Silence, ambiguity,
politeness, and comments about another surface are not acceptance. Ask one pointed
follow-up when the named falsifier remains unresolved.

- Accepted: record the observation in the existing plan or tracker and proceed to the
  next planned entry.
- Falsifier observed: leave acceptance open, return the exact observation to
  implementation, then require affected mechanical and sanity checks before another UAT
  attempt.
- Design changed: stop dependent work until the accepted design and plan agree.

After every required entry is explicitly accepted, return to execution for final history
normalization. UAT acceptance does not authorise pushing, publishing, deploying, or
rewriting inherited or published history.
