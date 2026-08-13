---
name: using-plan-and-execute
description: Use when beginning non-trivial design, implementation, debugging, or review work - select the applicable workflow, route planning through design, and materialize checklists
user-invocable: false
---

# Using Plan and Execute

Choose the procedure that owns the work before changing project state. The skill
catalogue is the index; this skill does not repeat each procedure.

## Task entry

1. State the requested goal and action boundary. For an open-ended request, recursively
   separate components that protect materially different decisions. Resolve the current
   component's goal and mechanism before opening the next one.
2. Inspect project instructions, relevant project memory and feedback through the
   project's retrieval procedure, and accepted decisions and constraints that govern the
   boundary. Say which findings change the work; do not silently consume or ignore them.
3. Identify whether the request is design, implementation planning, execution, debugging,
   review, acceptance, or branch lifecycle work.
4. Invoke the most specific applicable skill and follow its evidence and exit conditions.

If intent, scope, authority, target, or consequences remain materially unclear, stop before
mutation and ask one pointed question. Resolve it before opening another question or
dependent sub-goal.

Routine answers and already-grounded lookups do not need workflow ceremony.

## Two gates worth stopping for

**EnterPlanMode without brainstorming.** If you are about to call EnterPlanMode and have
not brainstormed this session, stop and invoke `starting-a-design-plan` instead. It
gathers context, clarifies the goal, develops the design, and records the result. Where
EnterPlanMode is unavailable, run the same sequence and present the plan inline.

**A skill with a checklist.** Create one task per item with `TaskCreate` before starting.
Where TaskCreate is unavailable, keep the checklist in a project file that survives an
interruption. The checklist is state, not a reminder.

## Evidence boundary

A skill supplies a procedure. Repository state, test output, tool results, and focused
human acceptance establish whether the procedure succeeded. Do not use a skill
announcement or self-assessment as completion evidence.
