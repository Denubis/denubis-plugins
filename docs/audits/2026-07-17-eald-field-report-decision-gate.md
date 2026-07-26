# Field report: the strengthened decision gate and paste-supervision in the wild

Date: 2026-07-17. Author: Claude (Fable), from the eald-prototype planning
sessions of 2026-07-16/17 (design and implementation planning for
persistence-cluster-53), written for the decision-discipline thread as
promised in that session. Evidence grade per claim: **observed** = I did or
verified it in-session; **reported** = the human or another agent stated it.

## Setting

The eald-prototype repo ran a full design → implementation-plan cycle with
Claude (Fable) supervising and codex (GPT-5.5 then, GPT-5.6 Sol now)
drafting, the human pasting prompts and ruling on decisions. The gate under
test was e138cc0's three-filter decision discipline (restatement / invented
alternative / obvious default), applied batched rather than per-phase. The
installed impl-plan-write (2.36.x) supplied the artefact contracts
(phase files, test-requirements, uat-requirements).

## What held

- **The three-filter gate, batched, worked as designed** (observed). Run
  once after the full seven-phase draft: six candidate decisions, all killed
  by the filters, zero survivors presented, kill list reported in one table.
  The human vetoed nothing. Zero-survivors-as-normal is livable in practice
  and the human read the table rather than skipping it.
- **The proposer/verifier premise confirmed with a different-model doer**
  (observed). Codex self-reported "zero findings" on both major drafts. The
  supervision pass found an approach-selection smuggled past the human in
  the design draft and a real collection-breaking defect in the plan draft
  (two same-basename test files under pytest's prepend import mode). The
  load-bearing gate was mechanical verification — resolve every line pin,
  grep every quote, fetch the library source, re-run the claimed checks —
  not any prose discipline on the doer.
- **Test/UAT requirements ownership survived the port** (observed). The
  planner kept both files; the collation audit caught a UAT entry whose
  conditions were mechanically checkable and forced the split.

## What fought the work

- **Per-phase task ceremony collides with batched drafting** (observed). The
  A/B/C/D-per-phase task lattice had to be re-mapped by hand onto a
  one-prompt-per-artefact workflow. Supports the rebalance's lean-planner
  and batched-review direction.
- **The TaskCreate dependency lattice assumed a tool the session lacked**
  (observed). Directives that name harness tools need fallbacks stated
  inline; this is now also in writing-claude-directives, and the field
  confirms it matters.
- **Widget compression of decisions was rejected by the human** (reported,
  verbatim: "howabout we don't just compress huge decisions into a question
  prompt"). One decision at a time, in plain sentences, survived; an
  AskUserQuestion box carrying an audit verdict plus three resolutions did
  not.
- **An auditor proposed manufacturing an artefact to make a human gate
  mechanical** (observed): a consumer-track list that nobody had written,
  invented so a script could diff against it. The human killed it. Evidence
  for reserving evaluative work to the human over automating the gate by
  inventing its inputs.

## Downstream

The process is distilled into five self-contained repo-local skills
(eald-prototype PR #128, ~450 lines total): loop map, codex supervision
mechanism, design stage, implementation-planning stage with the three-filter
gate, bounded QA/UAT/refactor. Two pressure tests passed on first run
(observed): the decision gate produced a zero-survivors kill table under
"show the client due diligence" pressure and escalated a planted false
premise as a blocking defect; the verification-pass rule refused to land
unverified codex output under end-of-day human pressure. Critical review of
the skills themselves found real defects (a gitignore that only covered the
codex workspace's markdown; exemplar references dangling on the merge
target), both adjudicated by the human. Skill failures in that repo are to
be reported back here as issues.

The parked impl-plan-write cut can treat this as one datapoint that the
gate's wording ports cleanly out of the plugin and holds under pressure
without the surrounding apparatus.
