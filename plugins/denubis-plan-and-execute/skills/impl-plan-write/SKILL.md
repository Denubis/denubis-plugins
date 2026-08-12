---
name: impl-plan-write
description: Use when an accepted design needs executable implementation phases with exact files, dependencies, verification ownership, and only genuine open decisions raised to the human
user-invocable: false
---

# Writing Implementation Plans

## Purpose

Convert one accepted design plan into phase files that another session can execute without
reconstructing the repository or inventing missing decisions. Planning does not implement,
commit, publish, or certify the work.

## Inputs and discovery

Start from the exact design-plan path. Read the current project instructions,
implementation guidance, architecture, test configuration, and the code each phase will
touch. List the relevant universe before asserting that a file, test, dependency, or
pattern is absent.

The main session may inspect the codebase directly. Delegation is optional and useful only
when a bounded investigation benefits from independent context. A delegated report is a
lead: open its file, symbol, test, log, or documentation pointer before using the finding.

For an external dependency, use current official documentation for the public contract and
upstream source for undocumented internals. Record the version and source the task depends
on. Do not turn model recollection into an API requirement.

Compare the design's assumptions with current state. Correct implementation detail in the
plan. If current evidence invalidates the accepted direction or reveals a choice with
materially different consequences, stop that branch of planning and use the decision
filter below.

## Open decisions

There is one route: inspect, filter apparent choices, ask only about survivors, then write
the settled phase. Do not offer review modes or make the human review routine defaults.

Apply these filters in order:

1. **Restatement.** If it restates the design or an acceptance criterion, it is not a
   decision.
2. **Invented alternative.** If an alternative exists only so the plan has options to
   present, discard it.
3. **Obvious default.** If current project evidence and the accepted design select one
   ordinary implementation, write it and cite that evidence.
4. **Recoverable fact.** If inspection or current documentation can answer it, investigate
   instead of asking.

Most phases surface none. Zero is the normal outcome. For a genuine survivor, ask one
pointed question at a time and include:

- the decision and why it blocks this phase;
- the viable alternatives supported by current evidence;
- **What it implies:** the concrete downstream difference for each alternative; and
- the exact sources a human can open.

Record the resolved choice in the design's decision record when it changes design. Do not
leave the conversation as its only durable owner.

## Plan artifacts

Write to `docs/implementation-plans/YYYY-MM-DD-<slug>/`:

- one `phase_##.md` per design phase;
- `flow-boundaries.md`, containing the predicted boundary flow or the bounded reason it
  does not apply;
- `test-requirements.md`, mapping automated and operational checks to acceptance criteria;
  and
- `uat-requirements.md`, containing only irreducible human-judgment checks. A zero-entry
  file is valid.

Do not create model-authored approval certificates, transition ledgers, or review receipts.
A review file may record findings when an actual review occurs, but it does not prove the
plan is correct.

## Boundary-flow contract

Decide applicability from the behavior being changed, not the file type or size. A
predicted DFD is required when the implementation changes what crosses a boundary between
an actor, external system, runtime component, process, or durable store. This includes
adding, removing, or rerouting a flow; changing its meaning, owner, ordering, persistence,
transformation, side effect, or failure route; or changing a control signal that permits,
blocks, retries, or terminates downstream work. Plan phases are delivery boundaries, not
DFD participants; a multi-phase plan does not become applicable for that reason alone.

It is not required for an internal change in how one component performs its responsibility
when the boundary participants, inputs, outputs, effects, ordering, and failure behavior
remain unchanged. A refactor, dependency substitution, test repair, or prose edit is not
automatically exempt: use its observable boundary effect.

Always create `flow-boundaries.md`. Start it with an applicability result and the current
design, architecture, or source evidence that supports that result. When it does not
apply, give one specific sentence naming the preserved boundary; do not add an empty
diagram or generic “no architecture change” claim.

When it applies, map breadth-first before elaborating phases:

- the system or feature boundary and external actors;
- processes, components, and durable stores that own a transformation or decision;
- each data or control flow's source, destination, payload or signal, contract or
  transformation, ordering or persistence when material, and failure behavior;
- separately, the delivery phase that creates each runtime producer and consumer, plus
  every inter-phase construction seam; and
- downstream consumers and exclusions needed to prevent an adjacent system from being
  silently pulled into scope.

Use stable flow identifiers that phase tasks can cite. Decompose only where another phase,
consumer, or failure boundary needs the detail. The artifact predicts what should be made;
it is not living architecture and must not describe planned state as implemented.

## Phase contract

Every phase starts with:

```markdown
# Phase N: [Outcome]

**Goal:** [observable state this phase creates]
**Architecture:** [how this phase fits the accepted design]
**Tech Stack:** [current tools and dependency versions]
**Depends on:** [prior phase or external prerequisite]

## Acceptance Criteria Coverage

- `<slug>.AC1.1` — [design text, copied exactly]
```

Use scoped acceptance-criterion identifiers from the design. A phase may cite an earlier
criterion, but one phase owns its completion.

Wrap each coherent task so the execution skill can extract it without loading every phase:

```markdown
<!-- START_TASK_1 -->
### Task 1: [Outcome]

**Files:**
- Create: `/absolute/path/to/new_file.py`
- Modify: `/absolute/path/to/existing_file.py`
- Test: `/absolute/path/to/test_file.py`

**Prerequisites:** [files, interfaces, or state already established]
**Verifies:** `<slug>.AC1.1`, or `None` for a non-behavioural task

1. [One coherent change, including the consumer of every new interface]
2. [Relevant failing check before a feature or bug fix]
3. [Minimal implementation and cleanup]

**Run:** `[exact project-native command]`
**Expected evidence:** [positive result and the condition that would fail]
<!-- END_TASK_1 -->
```

Use subcomponent markers only when several tasks share one reviewable outcome:

```markdown
<!-- START_SUBCOMPONENT_A (tasks 2-4) -->
<!-- START_TASK_2 -->
...
<!-- END_TASK_2 -->
<!-- END_SUBCOMPONENT_A -->
```

Task boundaries follow coherent outcomes, not a two-minute timer. Keep tests with the
behaviour they establish. Name a real consumer for every new function, class, field, file,
or service. Do not write `if present`, unresolved TODOs, speculative paths, or code that
only becomes valid in a later phase.

Use the project's own test runner and conventions. Functionality and bug-fix tasks use
red-green-refactor. Infrastructure tasks use a positive operational signal. A preparatory
refactor changes structure while existing behavioural tests remain green; it does not add
new behaviour to justify the refactor after the fact.

Never put a commit step in a task unless the human authorised commits for this plan. A
version bump is a release boundary, not a progress marker.

## Verification ownership

Map every acceptance criterion to one primary verification owner:

| Claim | Owner | Plan destination |
|---|---|---|
| Deterministic behaviour or invariant | Automated test or static check | `test-requirements.md` |
| Install, build, migration, or integration result | Operational command with positive signal | `test-requirements.md` |
| Usability, domain fit, clarity, or another irreducible judgment | Human use of the built surface | `uat-requirements.md` |
| Missing prerequisite or unavailable environment | Explicit blocker | Phase prerequisite; no success claim |

`test-requirements.md` names the criterion, test level, file or command, setup, positive
signal, and failure signal. Tests verify observable behaviour rather than a particular
internal call.

UAT collation consumes two inputs:

- **Input 1, the accumulated entries.** Keep only decisions whose prediction cannot be
  settled by an automated or operational check.
- **Input 2, the acceptance criteria no decision covered.** Inspect every unmapped
  criterion and add a human check only when judgment is irreducible.

Before retaining individual entries, map the human-visible boundaries of the built
surface breadth-first. Include the intended workflow, relevant failure paths, and seams
with existing systems. Design one or more actions that let the human encounter both the
wanted result and plausible unwanted behavior. The agent supplies the actions; the human
does not have to invent the experiment. Coverage is incomplete when it probes only literal
acceptance-criterion success while leaving said-versus-wanted, said-versus-built, adjacent
system, regression, or side-effect boundaries unexamined.

Each UAT entry states what the human does with the built surface, what they judge, and the
specific experience that would falsify the design. A phase that produced zero entries is normal,
and an entirely empty UAT plan is valid. Do not pad deterministic assertions with words such
as “feels” to make a manual gate.

Before retaining an entry, apply three distinctions:

- **Separation:** after every automated prerequisite passes, can the human judgment still
  fail? If not, route the claim to automated verification.
- **Reduction:** can the scenario be decomposed into checks whose outputs settle the
  verdict? If so, automate those checks instead of asking the human to perform them.
- **Disagreement:** could informed observers using the same built surface reasonably
  disagree about the result? If not, the entry describes a deterministic check.

When an entry combines a deterministic boundary with an irreducible judgment, split it:
route the boundary to `test-requirements.md` and keep only the independently falsifiable
human judgment in `uat-requirements.md`.

No model-authored stamp binds either file. Execution evidence comes from the tests,
operational results, and human interaction the entries name.

## Plan integrity

Before handoff, verify directly that:

- every phase, task, file, skill, agent, command, and external source pointer resolves;
- every acceptance criterion has one primary owner and no criterion silently disappears;
- every phase leaves the repository in a runnable, testable state;
- dependencies and consumers precede the tasks that require them;
- `flow-boundaries.md` has a supported applicability result; when applicable, every
  inter-phase producer/consumer seam has one owner on each side and every changed flow is
  covered by a task and either an existing acceptance criterion or an explicit design
  invariant. Do not invent an acceptance criterion solely to satisfy flow bookkeeping;
- each negative result states its search or check coverage and has a positive control;
- open decisions are resolved or marked as blockers; and
- the plan requests no commit, publication, deployment, credential, or human ceremony
  beyond the authority already granted.

A review finding is a lead, not a completion certificate. If a review is used, open each
cited artifact, repair confirmed defects, and leave unresolved findings visible. Do not
manufacture a green verdict, loop reviews until one appears, or treat a findings-file
header as external evidence.

## Handoff

Report the absolute plan directory and working directory. Name any blocker. When none
remain, provide the exact invocation:

```text
/denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-directory> <absolute-working-directory>
```

Do not claim that planned tests passed or that planned behaviour exists. Those are
execution results.
