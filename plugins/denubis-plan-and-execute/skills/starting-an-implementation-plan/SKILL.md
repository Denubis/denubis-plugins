---
name: starting-an-implementation-plan
description: Use when an accepted design is ready for implementation planning - resolves the design and workspace, writes outcome-owned work, verifies its evidence, and returns an exact execution invocation
user-invocable: true
---

# Starting an Implementation Plan

## Purpose

Resolve the accepted design and workspace, invoke
`denubis-plan-and-execute:impl-plan-write`, inspect the result, and return an exact
execution invocation. Planning does not implement, publish, label an issue, or mutate an
external system.

Session naming is an optional convenience when concurrent terminals would otherwise be
ambiguous. It is not a planning prerequisite.

## Resolve inputs

Use the design path supplied by the human. If none was supplied, inspect
`docs/design-plans/` and proceed only when one current accepted design is unambiguous. If
several could govern materially different work, ask one pointed question naming the
conflict.

Read the design completely. Resolve project `CLAUDE.md` or `AGENTS.md`, tool and test
configuration, current architecture, relevant consumers, and
`.ed3d/implementation-plan-guidance.md` when it exists.

Use the current workspace unless isolation was requested, project instructions require
it, or existing changes overlap the planned files. If isolation is required, invoke
`denubis-plan-and-execute:using-git-worktrees` and report the absolute worktree path at the
first edit. Do not create a worktree merely because planning began.

## Write and inspect

Invoke `denubis-plan-and-execute:impl-plan-write` with the exact design and working root.
It may return one plan file or a directory of independently resumable outcome files.

Inspect the artifacts directly:

1. Each outcome creates an independently usable or verifiable state and owns its first
   real consumers, tests, documentation, and failure handling. Chronology alone is not an
   outcome boundary.
2. Every acceptance criterion has one primary evidence owner. Commands name a positive
   signal and a relevant failure signal.
3. Boundary-flow detail exists only when a changed boundary needs it, and every changed
   producer, consumer, effect, ordering rule, and failure route has an implementation
   owner.
4. Human UAT describes only judgment that remains after the complete implementation and
   all mechanical and independent sanity checks. It asks the human to touch the finished
   implication, not repeat an automated assertion.
5. Every source pointer and command resolves. Negative findings state their search scope
   and a positive control.
6. Commit handling matches project authority: the execution request may authorise private
   checkpoints, but publication and final history normalization retain their later
   boundaries.

Repair implementation-detail defects and rerun affected checks. Ask the human only when
repair requires a genuine design, scope, authority, or external-state decision.

## Handoff

Return the absolute working root and exact plan path:

```text
/denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-path> <absolute-working-directory>
```

Recommend a fresh session only when context is actually depleted.
