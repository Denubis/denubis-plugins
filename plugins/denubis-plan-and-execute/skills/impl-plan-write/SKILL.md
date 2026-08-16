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

Default to one file:

```text
docs/implementation-plans/YYYY-MM-DD-<slug>.md
```

Use a directory with an `index.md` and one file per outcome only when independent loading
or interruption recovery materially helps. Create a boundary-flow appendix, verification
appendix, or UAT appendix only when its content is shared by several outcomes or has a
real consumer outside the outcome that owns it. Do not create empty or “not applicable”
paperwork.

The plan begins with the design path, working root, current repository evidence, scope,
and acceptance criteria. For each outcome include:

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

Tasks may be nested where dependency detail helps execution, but do not add parser markers
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

When the human invokes execution of the approved plan, that instruction authorises local
private checkpoint commits for the plan on an isolated feature branch unless project or
human instructions explicitly prohibit them. Checkpoints may be frequent and require no
routine prompt. They do not authorise pushing, publication, deployment, or rewriting
inherited or published history.

Fix rounds and superseded checkpoints fold into their owning outcome. Final history
normalization waits until the human has accepted finished-work UAT. It must preserve the
exact accepted tree, then rerun the relevant diff audit and verification. A plan should
state these lifecycle boundaries, not prescribe a commit-count quota.

## Integrity and handoff

Before handoff, verify directly that:

- every file, consumer, skill, command, dependency, and external source resolves;
- every criterion has one primary evidence owner and no outcome duplicates or drops it;
- every outcome leaves a runnable, testable state;
- dependencies precede their consumers without chronology-only splits;
- open decisions are resolved or named as blockers;
- UAT is complete-surface judgment after mechanical and sanity checks; and
- no publication, deployment, credential use, or final history rewrite exceeds granted
  authority.

Report the exact plan path and working root. When no blocker remains, provide:

```text
/denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-path> <absolute-working-directory>
```

Do not claim that planned behavior or tests already exist.
