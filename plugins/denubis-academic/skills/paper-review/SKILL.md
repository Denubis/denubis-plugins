---
name: paper-review
description: Use when conducting critical-friend or adversarial peer review of academic manuscripts across argument, validity, transparency, source fidelity, coherence, register, and concision.
---

# Paper Review

Review the paper diagnostically through independent lanes, then synthesise the
findings. Do not let fluent prose, significant results, checklist totals, or one
lane's framing substitute for judgment in another lane.

## Preserve the review contract

- Review and discuss; do not silently edit the manuscript.
- Treat every reviewer claim as untrusted until tied to a current source anchor.
- Separate confirmed defects, plausible concerns, competing readings, and
  unresolved uncertainty.
- Preserve lane disagreement until synthesis. Agreement raises priority but is
  not proof.
- Record `CLEAR`, a finding ID, or an explicit uncertainty for every unit in
  every assigned lane. A blank means unreviewed.
- Never calculate an aggregate checklist score or derive a verdict from item
  counts.
- Do not add, remove, or restyle citations during the diagnostic pass.
- Ask one pointed question at a time when authorial intent or authority is
  genuinely required.

## Load local authority

1. Read repository instructions and identify the canonical manuscript source.
2. Load the local scholarly workflow sources before review:
   - load the sibling `academic-writing` skill;
   - before any Zotero, citation, rendered-paper, quote-verification, or
     literature-note operation, load the sibling `using-bibliography` skill;
   - load any project or workspace register skill exposed by the runtime.
   Resolve skills through runtime discovery, never a developer-checkout path.
   If a required source is unavailable, record `BLOCKED-SKILL` and continue
   only with review work that does not depend on it.
3. Read the full repository `.notes/` writing/register rules. Apply precedence:
   repository register, then workspace register, then portable writing floor.
4. Determine the actual venue from current project evidence; do not infer it
   from a stale template or LaTeX preamble. Verify current requirements against
   the venue's official instructions when project evidence does not contain a
   dated, current copy. Record the authority and access date.
5. Identify the study or argument design before selecting a reporting guideline
   or critical-appraisal tool. Keep reporting compliance distinct from
   methodological appraisal and record each tool's limits.
6. If no register exists, derive a provisional register from an author-approved
   corpus or target paper. State the evidence and uncertainty, present the
   wording for approval, and write the `.notes/` file only after the author
   agrees. Do not infer a durable voice from one unverified draft.

The register governs the `REG` lane. It does not override methodological,
ethical, evidential, or transparency defects. Missing venue rules block only
venue-specific checks unless they also leave the canonical submission source
uncertain; mark the affected cells `BLOCKED-SOURCE` or `UNCERTAIN` and continue
independent lanes whose evidence is complete.

## Set scope and mode

Record:

- canonical files, supplements, tables, and excluded material;
- the project-approved review work directory and its required
  `source-claims.md` ledger;
- a source-lock manifest for every candidate artifact: canonical path, role,
  `INCLUDED`/`EXCLUDED`/`BLOCKED-SOURCE` status, repository and commit where
  applicable, byte size, and SHA-256 digest for every included file;
- baseline commit, submodule commits, index state, and relevant working-tree
  changes;
- review unit: section, full paper, revision, or response-to-reviewers;
- mode:
  - `CRITICAL-FRIEND` — section-first default, explanatory and diagnostic;
  - `ADVERSARIAL` — whole-paper Reviewer 2 pass near submission;
- depth and any explicitly excluded lanes;
- unavailable front or end matter as `BLOCKED-SOURCE`, never borrowed from a
  stale copy.

Recompute the manifest before dispatch and after every wave. If an included
source changes after mapping begins, stop dependent synthesis, mark affected
records `STALE`, and re-anchor them before relying on the review.

## Build the shared evidence map serially

Before lane work:

1. Assign stable paragraph or paragraph-equivalent IDs in reading order.
2. Give every unit a durable opening-text anchor; line numbers are secondary.
3. Inventory tables, figures, captions, footnotes, supplements, and end matter.
4. Create the initial canonical inventory of assertoric propositions and assign
   stable claim IDs. Label reconstructed claims as explicit, implicit,
   presupposed, or uncertain.
5. Inventory every citation and map each source-dependent claim to every cited
   work presented as supporting it. Split grouped citations into separate
   claim-source pairs.
6. Record the question/objective → design/variables → analysis → results →
   conclusion traceability spine.

`ARG` audits, completes, and Toulmin-analyses this inventory; it does not
renumber it. A lane reader returns any omission as a proposed claim with an
exact anchor. The orchestrator assigns the next unused canonical ID before the
Stage 2 gate and records any effect on sibling-lane coverage.

Read [toulmin-analysis.md](references/toulmin-analysis.md) for claim inclusion,
Toulmin relations, implication statuses, and falsification tests. Read
[review-records.md](references/review-records.md) for IDs and templates.

## Run the hybrid lane schedule

Parallelise only independent work. Keep dependency gates serial.

| Stage | Execution | Lanes or action |
|---|---|---|
| 0 | Serial | Source lock, register/venue gate, paragraph and claim map |
| 1 | Parallel wave | `ARG`, `APP`, `TRN` |
| 2 | Serial | Substantive synthesis and validity-blocker assessment |
| 3 | Parallel wave | `SRC`, `COH`, `SCAR` |
| 4 | Serial | Source-fidelity/argument/coherence/cold-reader synthesis |
| 5 | Parallel wave | `REG`, `CUT` |
| 6 | Serial | Final synthesis, promotion triage, hostile recheck, coverage audit |

With four available agent slots, the orchestrator may dispatch at most three
lane readers at once. Give every lane reader a read-only packet containing:

- the source-lock manifest, baseline, scope, exclusions, and blocked sources;
- the identical locked manuscript and artifact inventory;
- the paragraph and claim maps and traceability spine;
- only that reader's lane contract and output schema;
- applicable register, venue, reporting-guideline, and appraisal-tool
  decisions, with their authority and limits;
- settled author rulings that affect the current text.

Lane readers:

- work independently before seeing sibling or earlier lane findings;
- remain read-only;
- use exact anchors and stable IDs;
- report `CLEAR`, `CONCERN`, `UNCERTAIN`, or `N/A` with evidence;
- return raw findings to the orchestrator, which alone writes canonical
  scratchpads.

Later waves receive the refreshed lock and canonical maps, but not earlier raw
findings or synthesis. `SRC` additionally receives the claim-source inventory
and the resolved rendered-source packets prepared at the Stage 2 gate. Record
any necessary exception as lane contamination. The orchestrator adds
cross-links during the appropriate serial gate and never rewrites a raw lane
verdict to manufacture agreement.

When independent agents are unavailable, run the same lanes serially in the
listed order and keep their records separate until synthesis.

Read [review-lanes.md](references/review-lanes.md) before dispatching or running
any lane. Read [source-fidelity.md](references/source-fidelity.md) before
preparing or running `SRC`.

## Enforce the serial gates

Use the gate template in [review-records.md](references/review-records.md).
Do not advance merely because all agents returned.

- **Stage 0 → 1:** verify the manifest, scope, maps, inventory, traceability
  spine, authority decisions, and explicit partial blocks.
- **Stage 2 → 3:** verify a result for every assigned `ARG`, `APP`, and `TRN`
  unit; complete the claim-level Toulmin audit; incorporate newly discovered
  claims without renumbering; freeze the claim-source inventory; use
  `using-bibliography` to resolve and prepare each available cited source;
  recheck the manifest; and record the preserved validity decision.
- **Stage 4 → 5:** verify a result for every assigned `SRC`, `COH`, and `SCAR`
  unit; verify that `source-claims.md` has a pinpointed verdict or explicit
  `UNVERIFIED` result for every claim-source pair; recheck the manifest; and
  record unresolved disagreements.
- **Stage 5 → 6:** verify a result for every assigned `REG` and `CUT` unit and
  recheck the manifest.

Assign `ARG`–`APP` and `ARG`–`TRN` cross-checks to Stage 2;
`ARG`–`SRC`, `ARG`–`COH`, and `ARG`–`SCAR` to Stage 4; and `ARG`–`CUT`,
editorial interactions, final prioritisation, and the complete coverage audit
to Stage 6.
If the owner deliberately stops, write a gate record and mark every remaining
cell explicitly `UNREVIEWED`; do not present partial coverage as completion.

## Apply the validity gate without losing coverage

After `ARG`, `APP`, and `TRN`:

1. Identify defects that make downstream interpretation unreliable.
2. Preserve the methods verdict before interpreting the direction,
   significance, novelty, or desirability of the results.
3. Treat a validity blocker as a priority and dependency judgment, not automatic
   permission to leave the rest of a commissioned full review blank.
4. If stopping would be proportionate, state exactly what remains unreviewed and
   ask the review owner whether to stop or complete diagnostic coverage.

## Synthesise without flattening

For every candidate issue:

1. Verify the quoted anchor against the current canonical source.
2. Link paragraph, claim, lane-finding, and source-evidence IDs.
3. State the reader consequence, not just the surface symptom.
4. Give the strongest reasonable competing interpretation.
5. State confidence and what evidence would change the assessment.
6. Reconcile overlaps while preserving genuine lane disagreement.
7. Assign priority by consequence:
   - `P1` — central validity, claim, or interpretation fails;
   - `P2` — material coherence, transparency, or self-sufficiency failure;
   - `P3` — local clarity, consistency, mechanics, or concision issue;
   - `P4` — optional polish, retained as evidence unless the owner requested it.
8. Present small, coherent decision groups. Proposed wording is rare and clearly
   marked as a proposal.

A lane concern does not automatically become an author-facing issue. Read
[promotion-triage.md](references/promotion-triage.md), consolidate candidates by
the same author decision or root defect, and run its one hostile recheck before
assigning `PR-nnn` IDs. Preserve rejected, merged, batched, and deferred records
as evidence-only dispositions. Do not optimise toward a target number of
findings.

Before reporting no concern, audit both the unit × lane matrix and the
claim-level Toulmin ledger. Silence is not a pass.

## Verify cited-source claims as a lane

Run `SRC` for every source-dependent manuscript claim in scope, not only for
claims that another lane has already challenged. The required canonical output
is `source-claims.md` in the recorded review work directory.

1. Load `using-bibliography`, resolve the real citekey, and never construct one.
2. Render each source once on the orchestrator side and prove that its
   `full.md` exists and is non-empty before dispatch.
3. Give each paper reader all and only the claim-source pairs assigned to that
   paper plus the rendered markdown path and OCR note.
4. Record a physical-page pinpoint and source passage for every support verdict,
   even when the manuscript's paraphrase does not conventionally take a page
   locator.
5. Mark inaccessible sources and unresolved mappings `UNVERIFIED`; never turn
   lack of access into a claim that the source fails to support the manuscript.
6. Distinguish source fidelity from citation placement or venue style.

The ledger pinpoints are an internal evidential audit trail. They do not create
a blanket requirement to add page numbers to paraphrases in the manuscript.

Read [evidence-base.md](references/evidence-base.md) when auditing why a lane
criterion exists or adapting it to a discipline.

## Finish the diagnostic pass

Deliver:

- scope, mode, baseline, exclusions, and blocked sources;
- coverage matrix by unit and lane;
- the completed `source-claims.md` ledger and a list of sources that could not
  be verified;
- prioritised author-facing findings that survived promotion triage, with exact
  anchors, competing readings, confidence, and falsifiers;
- cross-lane synthesis and unresolved disagreements;
- reviewer-bias and expertise-limit statement;
- explicit list of unreviewed or unverified material;
- no manuscript edits unless the author separately authorises an application
  phase.
