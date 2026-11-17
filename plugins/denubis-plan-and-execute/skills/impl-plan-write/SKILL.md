---
name: impl-plan-write
description: Use when an accepted design needs an executable plan organized around coherent completed outcomes, their consumers, and falsifiable evidence
user-invocable: false
---

# Writing Implementation Plans

## Purpose

Turn an accepted design into work another session can execute without reconstructing the
repository or inventing missing decisions. Plan around coherent completed outcomes, not
the order in which files happen to be edited. Planning does not implement, publish, or
certify the behavior.

## Ground the plan

Read the exact design, project instructions, implementation guidance, architecture, test
configuration, affected code, and two or three relevant consumers or local examples.
List the relevant search universe before asserting that a file, test, dependency, or
pattern is absent. A delegated report is a lead; open its cited source before relying on
it.

Use current official documentation for external public contracts and upstream source for
undocumented internals. Record the version and source when they affect the implementation.

Compare design assumptions with current state. Correct implementation detail in the
plan. If evidence invalidates the accepted direction or exposes materially different
consequences, stop that branch and ask one pointed question. Do not manufacture options:
discard restatements, invented alternatives, ordinary defaults selected by project
evidence, and facts recoverable by inspection.

## Choose outcome boundaries

An outcome is a state that is independently understandable, usable or verifiable, and
reversible without depending on an unfinished later edit. It normally includes a new
interface with its first real consumer, behavioral tests, failure handling, and user or
operator documentation. Separate outcomes when they protect different decisions, have
different rollback or deployment boundaries, or can be accepted independently. Do not
split setup, implementation, tests, fixes, review responses, and documentation merely
because they occur at different times.

There is no target count. A substantial design often yields two or three outcomes; a
small design may yield one and a large design may yield more.

## Artifact shape

Create one plan directory with distinct semantic owners:

```text
docs/implementation-plans/YYYY-MM-DD-<slug>/
  plan.md
  todo.md
  worklog.md
```

`plan.md` owns the stable outcomes, dependencies, acceptance criteria, and evidence design.
`todo.md` owns only pending, in-progress, or blocked work. `worklog.md` owns completed work,
changed surfaces, decisions reached during execution, and exact evidence. When work
completes, remove it from `todo.md` and append it to `worklog.md`; do not keep a checked-off
copy in the task list.

Split `plan.md` into an `index.md` and one file per outcome only when independent loading
or interruption recovery materially helps. Keep `todo.md` and `worklog.md` separate either
way. Create a boundary-flow appendix, verification
appendix, or UAT appendix only when its content is shared by several outcomes or has a
real consumer outside the outcome that owns it. Do not create empty or “not applicable”
paperwork.

The plan begins with the design path, working root, current repository evidence, scope,
acceptance criteria, and the execution layout described under “Execution by several
agents”. For each outcome include:

```markdown
## Outcome: <completed state>

**Goal:** <observable state>
**Depends on:** <prior outcome or external prerequisite, if any>
**Owns:** <acceptance criteria or design invariant>

### Files and consumers
- Modify/Create/Test: `<resolved path>` — <role>
- First real consumer: `<resolved path or runtime surface>`

### Work
1. <failing behavioral check or other positive operational probe>
2. <smallest implementation with its consumer and failure path>
3. <documentation and bounded cleanup owned by this behavior>

### Verification
- Run: `<project-native command>`
- Positive signal: <evidence that the intended boundary ran and worked>
- Failure signal: <evidence that the behavior or probe is defective>

### Finished-work implication
<human UAT action, judgment, and falsifier, or “None: automated evidence settles it.”>
```

Initialize `todo.md` from the executable work and leave `worklog.md` with its heading and
any already-established evidence. Do not copy the plan narrative into either file. Tasks
may be nested where dependency detail helps execution, but do not add parser markers
or phase types unless a real consumer requires them. Never leave `if present`, unresolved
TODOs, speculative paths, or an interface that becomes valid only in a later outcome.

## Verification ownership

Assign every criterion one primary owner:

- deterministic behavior or invariant: automated test or static check;
- install, build, migration, or integration state: operational command with a positive
  signal;
- usability, domain fit, clarity, or another irreducible judgment: human interaction with
  the complete built surface; or
- unavailable prerequisite: explicit blocker, with no success claim.

Tests observe public behavior rather than a particular call or phrase. Features and bug
fixes use red-green-refactor. A refactor first needs behavioral coverage and must keep it
green. Infrastructure and generated metadata need a real consumer or operational probe.
For documentation, execute examples or render through the real documentation consumer
when that machinery exists; otherwise require a bounded agent inspection against the
implemented interface. Do not invent an exact-phrase search as a documentation test. An
empty search is not success until scope and a positive control establish what it could
have found.

For methodological evaluations, keep the acting instructions and the evaluator's oracle
in different artifacts. The actor receives its task, applicable skill, and realistic
workspace, but not expected answers or scoring criteria. The evaluator inspects observable
actions or consequences and includes a permitted or positive-control path so “nothing
happened” cannot pass by default.

## Execution by several agents

Plan how agents will execute the outcomes, so independent work runs at the same time and
every piece is checked by an agent that did not write it. Parallelism is not a target:
when the design is one coupled outcome, the layout says that one implementer works in the
task checkout and nothing more.

- **Concurrency.** Work runs at the same time only when it edits no common file, counting
  tests, generated files, lockfiles, migrations, and release or changelog metadata, and
  each piece has its own check that can fail. Give every shared file one owner, normally
  the coordinating session when it joins the work. Work that depends on another piece, or
  changes an interface another piece consumes, waits until that piece has joined. Keep
  coupled work with one implementer.
- **Isolation.** Each concurrent implementer works in its own worktree on its own branch,
  which the coordinating session creates from the task branch's current tip through
  `denubis-plan-and-execute:using-git-worktrees`. It runs the documented setup's install
  steps and only the narrowest check that shows its environment works, relying on the
  task branch's recorded baseline for that same tree rather than rerunning the expensive
  suite. Do not use a runtime's own agent worktrees, such as Claude Code's
  `isolation: "worktree"`, unless the plan records a compelling reason the skill's
  worktree cannot serve; that one starts from the remote default branch unless
  `worktree.baseRef` is `"head"`, not from the task branch. An agent-team teammate shares
  the lead's checkout, so it never writes alongside another implementer.
- **Checking.** Each implemented piece has a named checker that did not write it and does
  not share its context. The checker reads the piece's diff and the implementer's recorded
  check results, runs only the narrowest check that could falsify a claim it doubts, and
  judges the piece against its acceptance criteria; it does not edit. Its findings go back
  to the implementer.
- **Joining.** The coordinating session joins verified branches into the task branch one
  at a time, in dependency order. Before a branch joins, it squashes the branch's
  checkpoints into the few coherent commits of the outcome it serves, so the join keeps
  those commits and `git branch -d` still finds the branch merged. After each join it
  reruns, on the combined tree, the checks the join could affect, and tells implementers
  still working what has landed. A
  conflict goes back to the implementer whose branch conflicts, to rebase onto the new
  tip.
- **Test runs.** Say which agent runs which tests, when, and what each run proves. An
  expensive suite runs once for a given state of the code; other agents rely on that
  recorded result and run only the narrowest check that could falsify a doubt.
- **Cleanup.** List every worktree and branch the plan creates. Once a piece has joined
  and its combined checks pass, the coordinating session removes its worktree from
  outside it with `git worktree remove`, after confirming the worktree's status is clean
  and its branch has no commit the task branch lacks. It then deletes that branch with
  `git branch -d`, which refuses a branch not fully merged. It confirms each removal with
  `git worktree list` and `git branch --list`, and records it in the worklog. The task
  worktree and task branch stay until the human, authorising the final merge, names their
  removal (below).

Name each agent by role, with the model and effort the instruction files set for that
role. Lay the plan out as one table of the work and a few lines of rules:

```markdown
## Execution

| Work | Implementer and worktree | Starts after | Checker |
|---|---|---|---|
| <outcome or piece> | <role>; `<worktree path>` on `<branch>` from the task branch | <piece, or start> | <role, not the implementer> |

- Shared files and their owner: <file> — <owner>
- Join order and combined checks: <order>; <command and what it proves>
- Test runs: <agent> runs <scope> <when>, proving <claim>
- Cleanup: <each worktree and branch>, removed after its join passes; `git worktree list`
```

## Boundary changes

Add a boundary-flow section only when the work changes what crosses a boundary between an
actor, external system, runtime component, process, or durable store. Trace participants,
payload or signal, transformation, ordering or persistence where material, side effects,
failure routes, and downstream consumers. Name which outcome owns each changed producer
and consumer. An internal change that preserves participants, inputs, outputs, effects,
ordering, and failures needs no ceremonial diagram.

## UAT and Git lifecycle

Collate UAT over the finished design, after every implementation outcome. Retain a human
probe only when automation and operational evidence cannot settle the judgment and
informed observers could reasonably disagree. Give the human a concrete action on the
built surface and a falsifying experience. Do not ask for per-outcome UAT when later work
changes the surface, and do not disguise deterministic checks with words such as “feels.”

Before choosing a checkout, record the intended integration branch. Concurrent agents,
overlapping files, or unrelated dirty state require a task-owned worktree. An existing
task-owned branch or worktree is suitable. If execution would begin on the default branch,
warn and obtain human assent before the first edit there.

The human's approval of a plan, and their instruction to execute it, authorise without
further prompts (ruled 2026-11-15):

- local private checkpoint commits on the isolated task branch and in the agent
  worktrees, on the agent branches the plan names;
- the joins of those branches into the task branch, and the commits and squashes there
  that keep it to a few coherent commits, before integration testing, because the
  combined tree cannot be tested without merging, nor merged without committing; and
- the removal of the agent worktrees, and the safe deletion (`git branch -d`) of each
  agent branch the plan's cleanup step names, once it has joined.

Checkpoints may be frequent and require no routine prompt. None of this authorises the
final merge of the task branch into the intended integration branch: it is never
automatic, and happens only when the human authorises it at that point, after discussing
the finished work and accepting its UAT. Unless the human types a delivery request such
as `ship` or `commit, marketplace, push`, which orders the session to run the whole
delivery, merge included (ruled 2026-11-17), the human starts the merge by running
`/denubis-plan-and-execute:merge-to-main`; the session hands the human that command and
does not run the merge itself (ruled 2026-11-15). That authorisation also permits the
merge's commit; the task worktree and task branch are removed only as the human names
then. Nor
does plan approval authorise pushing, publication, deployment, or rewriting inherited or
published history.

Fix rounds and superseded checkpoints fold into their owning outcome on the task branch
as they land, and any fix round after UAT folds the same way. Each rewrite must preserve
the exact tree it starts from, then rerun the relevant diff audit and verification before
the final merge. A subsequent direct-delivery request integrates the accepted tree into
the intended branch, pushes it, verifies the remote ref, and cleans the task branch. A
plan should state these lifecycle boundaries and aim for a few coherent commits on the
task branch, not prescribe a commit-count quota.

## Integrity and handoff

Before handoff, a second fresh worker, never the plan's author, verifies the plan. Give
that worker a full checklist that names what to check and never an expected defect or
outcome, covering that:

- every file, consumer, skill, command, dependency, and external source resolves;
- every criterion has one primary evidence owner and no outcome duplicates or drops it;
- every outcome leaves a runnable, testable state;
- dependencies precede their consumers without chronology-only splits;
- work scheduled at the same time shares no file, every shared file has one owner, and
  each implemented piece has a checker other than its implementer;
- every worktree and branch the plan creates has a removal step after its join;
- open decisions are resolved or named as blockers;
- UAT is complete-surface judgment after mechanical and sanity checks; and
- no final merge, publication, deployment, credential use, or final history rewrite
  exceeds granted authority.

Report the exact plan, todo, and worklog paths plus the working root. When no blocker
remains, provide:

```text
/denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-directory> <absolute-working-directory>
```

This invocation is also the resume form. Point to the durable owners; do not paste their
current tasks, completed work, or evidence into a second resume narrative.

Do not claim that planned behavior or tests already exist.
