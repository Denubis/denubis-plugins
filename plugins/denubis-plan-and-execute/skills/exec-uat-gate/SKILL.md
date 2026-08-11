---
name: exec-uat-gate
family: executing-an-implementation-plan
description: Use when a built surface has a planned acceptance criterion that only human interaction and judgment can verify
user-invocable: false
---

# Human UAT Gate

## Purpose

Obtain the human observation required by an entry in `uat-requirements.md`. UAT owns only
irreducible judgment about a built surface. It does not replace tests, operational checks,
design review, or permission for a later external action.

Invoke this skill only after the implementation and all automatable checks for the entry
are complete. If no planned entry applies, return to execution without asking the human
for a ceremonial confirmation.

## Validate the entry

Resolve the entry to its acceptance criterion, phase, built surface, and current working
state. Confirm that:

- the human can interact with the named surface now;
- the requested observation requires judgment rather than a literal expected value;
- the falsifier describes an experience on which reasonable people could disagree; and
- automated prerequisites have fresh positive evidence.

Do not ask the human to rerun an automated or operational check. If the entry reduces to a
command and expected output, move it to `test-requirements.md`, run it, and do not invoke
UAT for that claim. If the surface does not exist or prerequisites are failing, return to
implementation rather than presenting a hypothetical exercise.

## Present and wait

Present one entry at a time. Include only:

1. the surface or workflow to use;
2. the concrete action to perform;
3. the judgment the human is being asked to make;
4. the result or experience that would falsify acceptance; and
5. any setup needed to reach the surface.

Ask one pointed question for that entry and wait. Do not bundle later UAT items, explain
the model's prior failures, or solicit a generic approval of the whole project.

## Consume the response

The human's response is the authority for the judgment actually expressed. Do not upgrade
silence, ambiguity, politeness, or a comment about a different surface into acceptance.
If the response is ambiguous about the named falsifier, ask one pointed follow-up.

- If the human observes the falsifier, return the exact observation to implementation and
  leave the criterion open.
- If the human accepts the criterion, record completion in the existing task or plan
  tracker and proceed to the next planned entry.
- If the human changes the design, stop dependent execution until the design and plan
  reflect the new decision.

When a note, ADR, plan, or other document will memorialize the judgment, it must contain
the exact source locator and resolver for the human response. No quotation or paraphrase
can stand in for that evidence. If the pointer cannot be resolved, that document has an
integrity defect; repair the reference or obtain a new focused human invocation before
depending on the memorial.

Acceptance does not grant authority to commit, publish, or deploy. Those actions retain
their own human and workflow boundaries.
