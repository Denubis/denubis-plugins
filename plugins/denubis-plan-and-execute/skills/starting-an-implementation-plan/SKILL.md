---
name: starting-an-implementation-plan
description: Use when an accepted design is ready for implementation planning - resolves the design and workspace, invokes the plan writer, verifies its artifacts, and returns an exact execution invocation
user-invocable: true
---

# Starting an Implementation Plan

## Purpose

Resolve the design and workspace, write the implementation plan through
`denubis-plan-and-execute:impl-plan-write`, verify its artifacts, and return an exact
execution invocation. This procedure does not commit, publish, label an issue, or begin
implementation.

At the start, use `denubis-plan-and-execute:exec-session-naming` so concurrent terminal
sessions expose this work's repository and purpose to the human.

## Resolve inputs

Use the design-plan path supplied by the human. If none was supplied, inspect
`docs/design-plans/`. Proceed when one current accepted design is unambiguous. If several
could govern materially different work, ask one pointed question naming the candidates;
do not guess or bundle workspace questions into it.

Read the design completely. Resolve any project `CLAUDE.md` or `AGENTS.md`, test and tool
configuration, current architecture, and `.ed3d/implementation-plan-guidance.md` when it
exists. A missing optional guidance file is not an event to report.

## Workspace boundary

Use the current workspace unless the human requested isolation, project instructions
require it, or existing changes would overlap the planned files. If isolation is required
and the branch or base cannot be discovered safely, ask one pointed question. Then invoke
`denubis-plan-and-execute:using-git-worktrees` and report the absolute worktree path at the
first edit.

Do not create a branch or worktree merely because planning began. Do not mutate GitHub
issues as a side effect of writing local plan files.

## Write and verify the plan

Invoke `denubis-plan-and-execute:impl-plan-write` with the exact design path, working root,
and implementation-guidance path if present.

After it returns, inspect the artifacts rather than trusting its report:

1. Resolve the implementation-plan directory under the selected working root.
2. Confirm every `phase_##.md` has a phase type, scoped acceptance-criteria coverage, and
   balanced task/subcomponent markers.
3. Confirm `test-requirements.md` accounts for automated and operational criteria.
4. Confirm `uat-requirements.md` contains only human-judgment entries or explicitly states
   that there are none.
5. Open every source pointer on which the plan relies. Missing, ambiguous, stale, or
   wrong-role authority is an integrity defect and blocks the dependent task.
6. Run any repository structural checks that validate plan or reference shape. A model
   review may identify candidates; it is not evidence that these checks passed.

If verification finds a defect, repair that artifact and rerun the failed check. Ask the
human only when the repair requires a genuine design or authority decision.

## Handoff

Resolve and verify the absolute working root and plan directory. Return:

```text
/denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-directory> <absolute-working-directory>
```

Recommend a fresh session only when the current context is actually depleted or the human
asks for one. The handoff path, not a forced `/clear`, preserves execution continuity.
