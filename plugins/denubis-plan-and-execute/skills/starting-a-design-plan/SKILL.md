---
name: starting-a-design-plan
description: Use when beginning a non-trivial feature or change - resolves intent and evidence, explores the design, writes the accepted design, and hands off to implementation planning
user-invocable: true
argument-hint: "[request or design topic]"
---

# Starting a Design Plan

## Purpose

Turn a non-trivial request into one current, evidence-grounded design before implementation
planning begins. Clarification discovers intent; brainstorming selects a design; the design
document owns the resulting boundaries and acceptance criteria.

This workflow does not implement the design or certify that it is correct.

At the start, use `denubis-plan-and-execute:exec-session-naming` so concurrent terminal
sessions expose this work's repository and purpose to the human.

## Resolve the boundary

Use the current workspace unless the human requested isolation, project instructions
require it, or existing changes overlap the design documents. Do not create a worktree or
branch merely because design work began. If isolation is needed and its base cannot be
resolved safely, ask one pointed question.

Read project `AGENTS.md` or `CLAUDE.md`, the named request, relevant `.notes/` through the
project's retrieval procedure, current architecture, design guidance, and two or three
nearby implementations. Inventory the relevant entities, consumers, external systems, and
known exclusions before asserting that something is absent.

Resolve the initiating human request to an exact human source locator and resolver. A
session identifier without a message locator, model summary, quotation, or paraphrase is
not authority evidence. If no exact source can be resolved, repair the reference or obtain
a focused human invocation before the design becomes current.

## Workflow

1. Invoke `denubis-plan-and-execute:design-clarify` with the request, inspected project
   context, and authority source. It asks only about intent or consequential tradeoffs that
   inspection cannot answer.
2. Invoke `denubis-plan-and-execute:brainstorming` with the settled context. It inspects
   current patterns, compares only genuine alternatives, and recommends one design.
3. Invoke `denubis-plan-and-execute:design-write` with the chosen design, exact evidence
   pointers, and working root. It writes and verifies the design document, runs any
   targeted proleptic challenge warranted by a named risk, and obtains the human judgment
   needed to make the design current.

At every step, resolve technical facts from code, tests, logs, or current external
documentation. When a materially different design choice remains, ask one pointed question
at a time and state what each viable answer changes. Do not invent choices to demonstrate
that consultation occurred.

## Handoff

Return the absolute design path and working directory, plus any unresolved blocker. When
the design is current and its authority sources resolve, provide:

```text
/denubis-plan-and-execute:starting-an-implementation-plan <absolute-design-path>
```

Do not commit, publish, label an issue, or begin implementation unless separately
authorised. The existence of the design document grants none of those permissions.
