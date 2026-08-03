# Review lane contracts

Use each lane independently against the same source lock. Record evidence for
every concern and an explicit `CLEAR`, `UNCERTAIN`, or `N/A` when no concern is
raised.

## Contents

1. `ARG` — argument and implications
2. `APP` — critical appraisal and validity
3. `TRN` — transparency and reproducibility
4. `SRC` — cited-source fidelity
5. `COH` — coherence and flow
6. `SCAR` — cold-reader self-sufficiency
7. `REG` — register, consistency, and mechanics
8. `CUT` — concision and repetition
9. Reviewer self-audit

## ARG — argument and implications

Audit the Stage 0 inventory for every explicit, implicit, presupposed, or
uncertain claim. Return omissions with exact anchors; do not renumber the
canonical map. Test each claim's grounds, warrant, backing, qualifier, rebuttal,
dependencies, and licensed implications. Use
[toulmin-analysis.md](toulmin-analysis.md). Argument is one lane, not the
organising purpose of the whole review.

## APP — critical appraisal and validity

### Question and contribution

- Identify the research question, objective, hypothesis, knowledge gap, and
  claimed contribution.
- Test whether the question is meaningful and the objective, design, variables,
  results, and conclusion answer one another.
- Use PICO only when appropriate; select a design- and discipline-appropriate
  question framework otherwise.

### Design, sampling, and measurement

- Test whether the design fits the question, objective, and data type.
- Apply randomisation, matching, comparators, blinding, or sample-size
  calculations only when the design makes them relevant.
- Check population/source corpus, inclusion and exclusion, recruitment or
  selection, participant/item flow, attrition, and stopping rules.
- Check whether variables and outcomes follow from the objectives and whether
  instruments, coding, measures, reliability, validity, and assessment timing
  are adequate.

### Analysis and internal validity

- Check whether analyses fit variable types, distributions, design, and stated
  estimands or questions.
- Require effect or parameter estimates with appropriate uncertainty; do not
  treat a threshold or p-value alone as a result.
- Check assumptions, diagnostics, missingness, multiplicity, sensitivity,
  confounding, alternative explanations, and design-specific bias where
  applicable.
- Record major validity defects before reading outcome direction as a reason to
  accept or reject the methods.

### Results, interpretation, ethics, and applicability

- Trace every reported result to an objective and analysis; flag new,
  selectively omitted, internally inconsistent, or unreconciled results.
- Test whether discussion and conclusions are supported, qualified, and
  consistent with the reported data.
- Distinguish statistical evidence from substantive, clinical, practical, or
  interpretive importance.
- Check limitations, adverse or contrary evidence, ethics review or exemption,
  consent, confidentiality, conflicts, and research-integrity disclosures as
  applicable.
- Assess external validity or transfer only after internal validity, using the
  target field's concept of applicability.

Do not total checklist scores. Criterion-level evidence and consequence govern
priority.

## TRN — transparency and reproducibility

- Require exact sample or corpus accounting for every subset and analysis.
- Ask whether the methods let a competent researcher reconstruct data
  collection, preprocessing, coding, and analysis.
- Check durable, versioned access to data, code, instruments, protocols, and
  analysis details where disclosure is lawful and ethical.
- Require justified nondisclosure or access restrictions to be stated.
- Check complete reporting of variables, models, preliminary and exploratory
  analyses, alternative specifications, exclusions, and deviations.
- Record how sample size and data-collection cessation were determined; flag
  outcome-dependent stopping.
- Check observation/annotation bias controls and report why blinding was absent
  when relevant.
- Distinguish planned, preregistered, exploratory, and post hoc decisions;
  preregistration is evidence of provenance, not a universal validity condition.
- Require parameter/effect estimates, variation, and uncertainty appropriate to
  the analysis.
- Assess methods independently of significance, effect direction, prediction
  conformity, author reputation, or reviewer agreement with the conclusion.
- Mark expertise gaps and ask for missing information or specialist review
  rather than assuming another reviewer will cover them.

Adapt these criteria to the field. Procedural reproducibility in empirical
science is not a universal model for qualitative, interpretive, theoretical, or
humanities scholarship.

## SRC — cited-source fidelity

Use `using-bibliography` and follow
[source-fidelity.md](source-fidelity.md). Audit every source-dependent claim ×
cited-source pair in the frozen inventory, not only quotations or citations
another lane disputes. Write the canonical results to `source-claims.md` with a
physical-page pinpoint. A grouped citation is several evidential claims, not one
collective pass.

Judge only what the cited source supports. Keep source fidelity separate from
citation placement, reference style, venue convention, and whether the
manuscript should include a page locator. Inaccessibility is `UNVERIFIED`, not
evidence against the cited work.

## COH — coherence and flow

For every paragraph or equivalent unit:

- Name the claims it serves and its function: establish, support, qualify,
  rebut, connect, apply, exemplify, define, orient, or delimit.
- Test whether the opening makes that function recoverable.
- Check whether every sentence contributes to the function.
- Check antecedents, definitions, transitions, logical connectives, and
  information order.
- Test whether the unit follows from its predecessor, motivates its successor,
  and belongs in its section.

Record both common `Status` and lane-specific `Classification`:

- `FOCUSED` maps to `CLEAR`;
- `MIXED`, `OVERLOADED`, `UNDERDEVELOPED`, `MISPLACED`, and `ORPHANED` map to
  `CONCERN`;
- `UNCERTAIN` maps to `UNCERTAIN`;
- material outside the lane's scope uses `N/A` for both.

## SCAR — cold-reader self-sufficiency

Inspect negative, contrastive, corrective, defensive, and concession-shaped
prose without using prompts, planning notes, reviewer exchanges, or draft
history to rescue it.

Ask:

1. What positive proposition does the paper affirm?
2. Where is it stated?
3. What alternative or counter-position is rejected?
4. Where is that alternative introduced?
5. Why does the distinction matter to the on-page argument?
6. Would removing the opposition leave a complete positive claim?

Record both common `Status` and lane-specific `Classification`:

- `TEXT-CONTAINED` maps to `CLEAR`;
- `MOTIVATION-THIN`, `OFF-SCREEN`, and `SCAR-CANDIDATE` map to `CONCERN`;
- `UNCERTAIN` maps to `UNCERTAIN`;
- material outside the lane's scope uses `N/A` for both.

A contrast marker is a trigger for inspection, not a defect by itself.

## REG — register, consistency, and mechanics

Run only after substantive synthesis.

- Treat the repository `.notes` register and current venue rules as authority.
  Use general editorial guidance to find categories of inconsistency, never to
  overwrite local voice.
- Sample representative prose, notes, tables, and references before detailed
  work so recurrent faults and the required intervention depth are visible.
- Check authorial voice, stance, terminology, definitions, labels,
  capitalisation, tense, person, attribution, syntax, agreement, antecedents,
  spelling, punctuation, typography, headings, captions, lists, tables, and
  cross-references.
- Check document and version completeness before detailed work.
- Maintain a style/terminology sheet for internal consistency.
- Distinguish a factual or substantive query from an editorial correction.
  Make author queries specific, courteous, and answerable.
- Record general decisions and approved exceptions; do not create a competing
  style sheet when `.notes` already owns those decisions.
- Check that tables, figures, notes, references, and cross-references are
  present, consistently labelled, and internally linked.
- Protect quotations, cited titles, references, code, and other literal material
  from blanket normalisation.
- Never add, remove, or restyle citations during the diagnostic pass.
- Preserve source files and review changes visibly; do not let bulk or
  search-and-replace operations create silent collateral edits.

Copy-editing depth follows the brief. It must not repair, conceal, or downgrade
a validity, evidence, ethics, or transparency concern.

## CUT — concision and repetition

Check duplicated claims, redundant examples, throat-clearing, metadiscourse,
stacked qualifications, repeated transitions, and residue from deleted argument
branches.

For every proposed cut:

- state what information, warrant, orientation, qualification, or voice would
  be lost;
- preserve epistemic calibration;
- distinguish defensive qualification from load-bearing hedging;
- test interactions with `ARG`, `COH`, `SCAR`, and `REG`.

A grammatical remainder is not proof that a cut is safe.

## Reviewer self-audit

Before synthesis, record:

- outcome, novelty, prestige, familiarity, and confirmation biases that may have
  influenced scrutiny;
- expertise gaps and evidence not inspected;
- criteria judged not applicable and why;
- any lane contaminated by seeing another lane's findings too early;
- whether a surprising, null, or low-powered result received a different
  methodological standard.
