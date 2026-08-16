---
name: using-plan-and-execute
description: Use when beginning non-trivial design, implementation, debugging, review, or acceptance work - selects the procedure that owns the next consequential decision
user-invocable: false
---

# Using Plan and Execute

Choose the procedure that owns the work before changing project state. The skill
catalogue is the index; this skill does not repeat each procedure.

## Task entry

1. State the goal and action boundary. Decompose non-trivial work around decisions that
   protect materially different consequences, not around chat turns or a fixed sequence
   of phases.
2. Read project instructions, relevant project-owned memory, accepted decisions, and the
   current implementation at that boundary. Say which findings change the work.
3. Classify the next consequential action as design, implementation planning, execution,
   debugging, review, acceptance, or branch lifecycle work.
4. Invoke the most specific applicable skill and follow its evidence and exit conditions.

If intent, scope, authority, target, or consequences remain materially unclear, stop
before mutation and ask one pointed question. Resolve it before opening another question
or dependent sub-goal.

Open-ended work needs design before implementation when the protected behavior or
trade-off is unsettled. The name of a UI mode or tool is not the gate: apply
`starting-a-design-plan` whether or not the runtime exposes a plan mode.

Routine answers and already-grounded lookups do not need workflow ceremony.

## State worth preserving

Use a task tracker or durable project file only when the work is long enough that losing
the current outcome, owned changes, last evidence, or next unresolved condition would
make recovery materially harder. A checklist in a skill is not by itself a reason to
create one task per sentence. Track outcomes and blockers, not narration.

## Evidence boundary

A skill supplies a procedure. Repository state, test output, tool results, and focused
human acceptance establish whether the procedure succeeded. A skill announcement,
progress marker, commit, or model verdict does not.
