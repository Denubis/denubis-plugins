---
name: using-plan-and-execute
description: Use when starting any conversation - the skill-first workflow. Check for a skill before acting, announce the one you pick, brainstorm before coding, TaskCreate for checklists
user-invocable: false
---

# Getting Started with Skills

Skills encode workflows already debugged against this codebase. Working without
one usually means re-deriving a solved problem and getting it subtly wrong, so
checking costs seconds and skipping costs a rewrite.

## Before you act

1. Scan the skills listed in your system context.
2. Ask whether any of them covers this request.
3. Where one does, invoke it with the `Skill` tool and follow it.

A question is a task, and so is a quick look at a file: both are worth the scan.
Skills also change, so read the current version rather than working from your
memory of it.

## Announce the skill you are using

Say "I'm using [skill] to [what you're doing]" before you start. It lets your
human partner catch a wrong choice early, and it shows you read the skill rather
than recalling it.

## Two gates worth stopping for

**EnterPlanMode without brainstorming.** If you are about to call EnterPlanMode
and have not brainstormed this session, stop and invoke `starting-a-design-plan`
instead. It gathers context, clarifies, brainstorms, and documents the design.
EnterPlanMode comes after that rather than instead of it. Where EnterPlanMode is
unavailable, run the same sequence and present the plan inline.

**A skill with a checklist.** Create one task per item with `TaskCreate` before
starting. A checklist held in your head loses items, and the tracking overhead is
small against the cost of a missed step. Where TaskCreate is unavailable, keep
the checklist in a file on disk so it survives an interruption.

## Following a skill

Some skills carry rigid rules — TDD, debugging, verification. Follow those
exactly, because the discipline is the point. Others are flexible patterns, such
as architecture and naming, where the principles adapt to context. Each skill
says which kind it is.

A specific instruction says what to build, not which process to build it with.
"Add X" is the goal, and the workflow still applies. Clear requirements are
exactly when it pays, because a step skipped there is easy to take and slow to
find.

## In short

Scan for a skill, announce the one you pick, follow it. Checklists get tasks.
Design comes before plan mode.
