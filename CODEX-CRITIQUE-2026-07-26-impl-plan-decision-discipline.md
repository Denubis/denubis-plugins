# Codex critique: `impl-plan-decision-discipline`

Reviewer: Codex / GPT-5
Date: 2026-07-26
Artifact type: technical reasoning and generated-source design
Disposition: findings for Claude and Brian; no implementation performed

## Artifact identity

Repository:
`/home/brian/people/Brian/brian-ed3d-plugins`

Worktree:
`/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/impl-plan-decision-discipline`

Reviewed worktree key:

```text
repository: /home/brian/people/Brian/brian-ed3d-plugins
commit: 4c34ab2cf565b8ac5acb55b1af027eb7559868e9
path: plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
bytes: 72210
digest: sha256:f44fe0332c713010c22538b1e5588ff0face493828dda7e62e779add23079c4e
```

Comparison key:

```text
repository: /home/brian/people/Brian/brian-ed3d-plugins
commit: c25c1ad5371fc80e6d0e3bf9ff8432f94a908e76
ref at observation: main
path: plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md
bytes: 94932
digest: sha256:fd45aba97b774ad414b1b4b03f64d13873a60c1c0884b33eca74e3f809abbb9f
```

The worktree was 185 commits behind and 6 ahead of `main` when measured. Its tracked tree was
clean; existing untracked files were left untouched. These measurements are dated observations.
Recompute before acting. Mtime carries no version authority.

## Bottom line

The branch is a valid record of the rejected decision-theatre and its first cut. It is not a safe
base for further direct edits to `impl-plan-write`. Reconcile the six-commit branch against current
upstream first, then implement the settled target across the interlocking planner, executor, and
reviewer contracts.

## High findings

### H1. The worktree copy is a superseded implementation base

The worktree's skill is 72,210 bytes and 1,329 lines. Current `main` is 94,932 bytes and 1,475
lines. The branch's `e138cc0` cut therefore applies to a substantially older artifact.

Editing the worktree copy further before reconciliation risks either discarding upstream
hardening or reconstructing it by hand. The 2026-07-25 resume already records this, but the
content discrepancy is still present.

Recommendation: treat `e138cc0` as a semantic patch to replay deliberately against current
upstream. Do not merge by accepting either whole file.

### H2. The committed cut contradicts the branch's own target architecture

The authoritative responsibility matrix says:

- replace the three review modes;
- surface genuine forks as one batched set;
- use `run it / read it / ask it`;
- emit a lightweight plan index.

The worktree skill still:

- asks the human to choose among three review modes;
- keeps a per-phase “design decisions” mode;
- discovers and approves decisions phase by phase;
- conditions test/UAT handling on that old mode;
- emits no plan index.

`e138cc0` improves the old per-phase gate but does not implement the target. This is not a minor
follow-up: the old orchestration shape remains the controlling workflow.

Recommendation: after reconciliation, remove the mode split as one coherent edit and update every
downstream reference in the skill, checklist, examples, and test/UAT collation sections.

### H3. The strengthened gate still permits unsourced model judgement

The cut says a decision is something the model “cannot settle on plain technical grounds” and
disqualifies choices settled by an “obvious best practice.” Those phrases allow the planner to
declare its own training prior obvious.

The branch design already has the stronger control: run it, read it, or ask the human for a
world-state fact. A surviving tradeoff needs observable results or citations for both sides and a
named human-held pivot.

Recommendation: make the evidence channel part of the candidate-decision record. “Obvious” is not
an evidence class.

### H4. Removing the old mode without rewriting test/UAT ownership will orphan contracts

The current skill says UAT entries are generated per phase in design-decisions mode and otherwise
constructed from acceptance criteria. The responsibility matrix correctly rules that
`impl-plan-write` retains ownership of both `test-requirements.md` and `uat-requirements.md`.

Once the mode split disappears, those conditional branches no longer describe reality. The
executor, test analyst, and UAT gate consume these files, so a planner-only prose cut can create
dangling contracts even when the skill still reads coherently.

Recommendation: define one unconditional generation route for each artifact, including valid
zero-entry output, and verify every consumer against it.

### H5. The design declares the change interlocking; finishing only this file would violate that

The responsibility matrix says the planner emits an index consumed by executor pre-flight, while
reviewers gain a plan-conflict verdict and no-pre-judging discipline. Those changes cannot be
landed independently without dead output or missing consumers.

Recommendation: “finish `impl-plan-write`” should mean reconcile its source first, then execute the
five-item queue on one branch. If Brian instead wants only the planner cut, explicitly drop the
new index and other unimplemented cross-skill promises from the target.

## Medium findings

### M1. No regression test was found for the new behavioural contract

The repository search found prose references but no test enforcing:

- removal of the three modes;
- one batched decision gate;
- zero decisions as valid;
- evidence-channel classification;
- preservation of test/UAT ownership;
- index producer/consumer agreement.

Token and phrase tests alone will not catch a coherent-sounding but unusable workflow. The Codex
mirror demonstrated this: its forbidden-token regression passes while several translated
orchestration contracts remain false.

Recommendation: add structural assertions over the source skills and a small fixture-based
workflow test covering zero decisions, one human-held fork, and a fully test-settled candidate.

### M2. “Where I lean” needs an evidence constraint or removal

A recommendation can help the human, but an unsourced lean restores the same model-vibe channel
the redesign rejects. If retained, it should follow the sourced costs/buys and name the pivot; it
must not resolve the fork or downgrade the human's ruling.

### M3. The plan index remains underspecified

The matrix acknowledges that the index needs a size bound. It also needs an exact canonical
location, schema, producer, and consumer. Without those, it risks becoming another duplicated
summary whose interpretation drifts from the phase files.

Recommendation: either specify the smallest index contract and test it end to end, or omit the
index from this cut.

## Provider-boundary note

The named Claude agents in the upstream skill are not defects: that repository actually ships
them. Do not damage the Claude source to accommodate Codex.

The Codex mirror must translate those roles into complete dispatch briefs and adapt transport,
monitoring, tool names, and completion evidence. Current Codex-specific defects belong in
`brian-ed3d-plugins-codex/scripts/bootstrap_plan_and_execute.py`, after the upstream semantics
settle.

## Recommended sequence

1. Recompute artifact identities and reconcile `e138cc0` against current `main`.
2. Confirm with Brian whether the five-item interlocking queue still governs.
3. Replace the three modes with one evidence-channel workflow.
4. Repair test/UAT generation and all consumers.
5. Implement or drop the plan index as an explicit decision.
6. Add behavioral regression tests.
7. Run the full editing pass across planner, executor, reviewers, examples, and README.
8. Only then regenerate and audit the Codex mirror.

No changes in this critique should be treated as human rulings. The artifact keys identify the
copies reviewed; they do not make the critique true.
