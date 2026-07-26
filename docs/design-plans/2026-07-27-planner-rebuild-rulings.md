# Planner rebuild: operator rulings, 2026-07-27

**Status:** Current truth for this thread's decisions. Supersedes the open forks in
`RESUME-PROMPT-proposer-verifier-core.md` and the target state in
`2026-06-24-responsibility-matrix-and-rebalance.md` where they disagree.

**Provenance:** every ruling below is Brian's, given in session on 2026-07-27. Quoted
strings are verbatim. Anything marked *inference* is mine and is not ratified.

## What this closes

Two forks recorded as open since 2026-07-06 are now settled.

**The build-versus-cut fork is settled toward the full rebuild.** The charter is not
cutting `impl-plan-write` alone. Ruling: *"let us treat the entire core of this as
in-scope."*

**The deferral is lifted.** `RESUME-2026-07-25.md` records a 2026-07-25 ruling,
*"codex council is stale, impl-plan comes much later."* That was worktree triage while
`skill-skills-upstream-sync` was mid-flight on the same file. It merged, and on
2026-07-26 Brian stated the purpose of that merge was *"to get this worktree to main such
that we can do the impl-plan-write refactor."* The 2026-07-25 banner is stale.

The Contested fork from that resume, pure-discipline versus a tiny mechanical home, is
not addressed here and remains open.

## The rulings

**R1. The quarantine on the five codex reviews is lifted.** One of the five,
`codex-reviews/SKILL.md.20260708-152424.REVIEW.md`, reviews `impl-plan-write`. The other
four cover extending-claude skills and belong to the Phase 5 synthesis.

**R2. The three review modes collapse to one route.** No mode selection. Only what
requires Brian's judgement reaches him. The three modes are to be *"reduced to simply
'the correct way' where only things I need to judge are surfaced to me."*

**R3. Planning is breadth-first, and attention goes to the seams.** *"We do breadth
first, and we focus on the seams and the contracts between them."* The current per-phase
ceremony is *"almost entirely performative."*

**R4. Question triage is delegated.** The cost Brian objects to is questions reaching
*him*, not questions existing. Small questions are answered by a supervisor or subagent,
and only genuine human-judgement questions escalate.

**R5. The anti-smuggling apparatus becomes universal.** It applies to every plan.
*"If I want something to skip it, I'll simply say so."* Opt-out is a human instruction,
not a mode.

**R6. That apparatus moves out of `SKILL.md`.** It *"should be a subskill or rubric or
method loaded as appropriate."* This also settles the codex Medium on the authoring
protocol, because the apparatus is roughly 270 lines of the file's 1478.

**R7. DFD creation becomes first-class in planning.** A DFD describes what the work
transforms, which makes it the natural home for seams and contracts, and fits the
functional-core split.

**R8. The two DFDs have distinct owners and a defined relationship.** *"The planner's
dfd says what should be made. The update says what was made. Usually with any
differences being registered with adrs."* So `impl-plan-write` owns the predicted DFD,
`architecture-update` owns the observed one, and the diff between them produces ADRs.

**R9. The ADR bar.** *"Load bearing changes that change what it does, which should be a
change in the dfd. Specifically a change in what, less so how, always a why."* A change
in *what* earns a record, a change in *how* generally does not, and every record carries
its *why*.

Corollary, agreed in session: if what-it-does changed and the DFD did not, the DFD was
underspecified. The bar therefore also falsifies the diagram.

## Why R8 and R9 matter beyond bookkeeping

The 2026-06-24 test for a legitimate ADR was that it records a discovery made by looking
or a refuted assumption, rather than `Status: Accepted` theatre. A should-versus-was
divergence is a refuted assumption discovered by looking, so the legitimacy test is now
satisfied by the structure rather than by instructing the model to be honest.

This also gives the "buried load-bearing decisions" row of the responsibility matrix a
mechanical spine. That row currently relies on the coherence reviewer's baked-in
assumptions pass and critical peer review, both prose judgement. A DFD diff catches a
store that gained an unplanned writer, or a flow whose source moved, without a model's
opinion.

*Inference, not ratified:* the reconciliation belongs in `exec-coherence-review`, which
already exists to verify implementation coheres with design intent. Branch-finish is the
alternative site and was not ruled on.

## Grounding: what was verified on 2026-07-27

Three agents read the files rather than grepping them. Findings were sampled and
confirmed against the sources by hand.

- The merge brought this branch current with `main` at `447d633`, 201 commits, one
  conflict, `uv run pytest -q` at 1131 passed.
- `impl-plan-write/SKILL.md` is 1478 lines with 25 mode-dependent locations across 428
  lines of mode blocks. Full inventory in the session transcript.
- Four instructions in that file cannot be followed as written today. Three dissolve when
  the modes go: batch mode carries a mandatory `AskUserQuestion` at `:645-647` while being
  told to write without asking at `:1200`; the Test Requirements subagent at `:1367` is
  told to cross-check a file that does not yet exist in two of three modes; the
  `uat-requirements.md` template mandates `DR[X]` identifiers at `:1422` that two modes
  never assign. The fourth is independent: the finalization gate at `:1340` uses
  `$PLAN_DIR` as a shell variable the skill never exports.
- The codex triplication finding needs correcting in our favour. The 34-line investigation
  preamble is byte-identical across all three copies, verified by `diff`. The drift sits
  in step 4, where the modes legitimately differ.
- `epistemic-humility` carries a verified citation defect. `SKILL.md:101` cites
  `AbsenceJudgement.tex:789, 792` for Scope/confabulation, but those lines now hold the
  Temporality Blindness header and paragraph. The paper moved about seven lines on
  2026-07-25 and several citations landed on neighbouring content rather than falling off
  the end. This belongs to the Phase 5 queue, not to this branch.

## Field evidence bearing on R3 and R4

Two field reports dated 2026-07-17, currently untracked in `docs/field-reports/` and
`docs/audits/`, record the only real-world runs of this process.

The planning report found batched drafting plus terminal review beat per-phase review on
defect yield, with three review passes producing almost perfectly disjoint defect classes
across roughly twenty findings. The terminal fresh-context review contributed
cross-task-seam defects, specifically five variables or functions consumed across a task
boundary with no producing task. In DFD terms that is a flow with a consumer and no
producer, which is mechanically checkable.

The execution report found the opposite at the inner scale, that interactive
pause-and-ask beat batch-draft-then-verify on decision quality, and that question triage
between human and supervisor worked once delegated.

Together they support R3 and R4 rather than conflicting: batch the drafting, keep the
inner loop interactive and delegated, and concentrate review on the seams.

## Task list

Every critique against this work is folded in below. Source tags: **CC** = the 2026-07-26
codex critique; **CR** = the quarantined codex review
`codex-reviews/SKILL.md.20260708-152424.REVIEW.md`; **3D** =
`refactor-pipeline-findings-phase-6-3d.md`; **RD** = the 2026-07-27 read-based audit.
A task carrying no tag comes from a ruling above.

### Group 0 — housekeeping

- **T0.1** Track the at-risk untracked files: the codex critique and the three 2026-07-17
  field reports. The record above cites them as evidence and they would die with the
  worktree.
- **T0.2** Commit the doc reconciliation.

### Group 1 — prerequisites, before `SKILL.md` is touched

- **T1.1** Read the E1–E12 fixture in
  `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_06_adversarial_test.md`
  and write down how to re-run it. **3D** records that the anti-smuggling wording is
  test-locked and that any edit mandates re-validation. This gates Group 2, so it comes
  first.
- **T1.2** Specify the predicted-DFD contract: schema, canonical path, producer, consumers,
  and how it relates to the existing `architecture-update` templates. **CC-M3** killed the
  plan index for being underspecified on exactly these points; the DFD inherits that
  objection and must answer it.

### Group 2 — extract the apparatus (R5, R6)

- **T2.1** Move the anti-smuggling apparatus, roughly 270 lines, into a loadable sub-skill
  or rubric. Resolves **CR-M2** and **CC** on the authoring protocol, and most of the
  1478-line problem.
- **T2.2** Re-run E1–E12 and record the result. Non-optional: **3D-M2** flags the hazard
  that edits adjacent to locked wording still need the fixture.
- **T2.3** Make the apparatus universal with human opt-out, and delete the mode-scoped
  framing it currently sits inside.

### Group 3 — one route (R2), and the contracts it must not orphan (**CC-H2**, **CC-H4**)

- **T3.1** Delete mode selection and collapse the three blocks to one route. 25 locations
  across 428 lines, inventory in the session transcript. Dissolves **CR-M1** and **3D-M1**
  triplication, plus **3D-m4** and **3D-m6**.
- **T3.2** Make `test-requirements.md` and `uat-requirements.md` generation unconditional.
  The keystone. Carry the unstamped-accumulate-then-restamp protocol across, because it
  currently lives inside the design-decisions branch and **CR** called the contradiction it
  fixes the strongest finding in the file.
- **T3.3** Verify the three defects that should dissolve are gone: the mandatory
  `AskUserQuestion` inside batch mode, the Test Requirements subagent told to cross-check a
  file that does not yet exist, and the `DR[X]` identifiers the template demands but two
  modes never assign. **RD**. If any survives, the collapse was incomplete.
- **T3.4** Restore the second defensive layer for all plans. **RD** found the
  pre-presentation self-audit lives only in the design-decisions branch, so the "two
  layers" claim holds for one mode of three.

### Group 4 — DFD first-class (R7, R8, R9)

- **T4.1** `impl-plan-write` emits the predicted DFD.
- **T4.2** Reconciliation of predicted against observed, producing ADRs at the R9 bar.
  Site not yet ruled; `exec-coherence-review` is the proposal.
- **T4.3** Implement the dangling-flow check: a consumed input with no producing process is
  a mechanical defect. This is the seam test, and the answer to **CC-M1**, which objected
  that no regression test enforces the new behavioural contract and that token tests will
  not catch a coherent-sounding but unusable workflow.

### Group 5 — defects that survive the refactor

These are independent of the mode collapse and must be fixed on their own.

- **T5.1** The finalization gate's shell snippet uses `$PLAN_DIR`, a variable the skill
  never exports; everywhere else uses `[PLAN_DIR]` substitution. Fails for the wrong
  reason. **RD-O3**.
- **T5.2** Stamp template duplicated across two sites, attestation-not-proof across three.
  **3D-m3**.
- **T5.3** Unresolvable identifiers and an unsourced statistic: `AC6.7`, `(M6 revision)`,
  "the 497-min parallel-session audit", and "76% of Popper entries in real plans were
  tautological". **RD-O10**.
- **T5.4** `test-requirements.md` has no existence gate while `uat-requirements.md` has one,
  though the skill insists both must exist before execution. **RD-O13**.
- **T5.5** The Requirements Checklist omits the collation audit entirely, which is the
  structural gate a compacted session would rely on. **RD-O14**.
- **T5.6** Small corrections: the design-plan path given as `docs/plans/` in one place,
  a rationalization row naming fewer tasks than the checklist requires, and fractional
  phase numbers with no filename convention. **RD-O4/O5/O6**.
- **T5.7** Navigability: document order inverts execution order, and a 1478-line file has
  no roadmap. **RD-O9**, **3D-m7**.

### Group 6 — the rest of the interlocking queue (**CC-H5**)

One branch, because these cannot land independently without dangling contracts.

- **T6.1** `executing-an-implementation-plan`: pre-flight over the DFD rather than phase
  bodies, preserving "never load all phases upfront", plus a durable progress ledger.
- **T6.2** `requesting-code-review` and `code-reviewer`: the no-pre-judging rule, and a
  plan-conflict verdict that halts for human adjudication before the bug-fixer runs.
- **T6.3** `coherence-reviewer` and `critical-peer-review`: the wider net, now with the DFD
  diff as its spine rather than prose judgement alone.
- **T6.4** The research path: `internet-researcher` identifies, `using-bibliography` reads,
  loading to Zotero stays behind confirmation.

### Group 7 — evidence channel (**CC-H3**)

- **T7.1** Make the evidence channel part of the candidate-decision record. **CC-H3**
  objected that "cannot settle on plain technical grounds" and "obvious best practice" let
  the planner declare its own training prior obvious, and that "obvious" is not an evidence
  class. A surviving fork needs run-it or read-it evidence on both sides and a named
  human-held pivot.

### Group 8 — separate queues, not this branch

- **T8.1** The Fable whole-file fitness pass, skill 5 of 5, is owed to `impl-plan-write`
  and routes here. Best run after Group 3, against the collapsed file.
- **T8.2** Phase 5 synthesis: the four other quarantined codex reviews, the verified
  `epistemic-humility` citation drift, the missing Task/Agent fallback in
  `testing-skills-with-subagents` for three of its four phases, and the Haiku-testing
  checklist item in the vendored `anthropic-best-practices.md`. These belong to
  `skill-skills-upstream-sync`, not here.

## Still open

- The Contested fork, pure-discipline versus a tiny mechanical home.
- Where the reconciliation step lives, per the inference above.
- Whether the predicted DFD replaces the plan index promised in the responsibility
  matrix, or the index is retired in its favour.
- Which plans a DFD does not suit. A rename across many files has no interesting data
  flow, and forcing a diagram there would be new ceremony of the kind R2 removes.
- The proposer/verifier boundary, deferred to its own worktree, though the planner's
  self-audit at `:903-924` is a live instance of a model grading its own output and the
  collation audit at `:1440` is the same concern handled by dispatch.
