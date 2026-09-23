# Shawn's academic workflows: relevance and adoption review

Reviewed 2026-09-22 against personal-assistant commit
`c1ad9052b6ce90d661ea7312265e099300b4ab7f`.
Clone: `/tmp/shawn-personal-assistant-20260922`.

Read all 14 `skills/*/SKILL.md` definitions (3,639 lines), screened the
34 commands and 9 agents, and inspected selected academic command/agent bodies
and implementation dependencies. This is a relevance and portability review,
not a runtime certification or an exhaustive audit of every supporting script.
Nothing was installed or dispatched; no Zotero writes or external messages were made.
The private `data` submodule was not fetched.

Comparison baseline: this repository's `denubis-academic` README,
`academic-writing`, `paper-review`, and `using-bibliography` skill definitions,
plus the renderer paths implicated by the user's fault report.

**Recommendation:** retain our three existing academic skills. Add verified
literature discovery first; borrow selected study-design and verification checks;
evaluate AB+ as a separate source-note workflow. Do not transplant Shawn's
personal-assistant infrastructure or make a large review panel the default.

All upstream links below are pinned to the reviewed commit.

## All 14 skills

| Skill | Relevance here | Recommendation and adaptation |
|---|---|---|
| [review-paper](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/review-paper/SKILL.md) | High; overlaps our `paper-review` | Borrow the mechanical pre-pass, checks against stale author rulings, and calibration using known-good hedged prose. Keep our evidence-led finding promotion and proportional delegation. Its deterministic severity verdict still depends on model-assigned severities. |
| [academic-prose](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/academic-prose/SKILL.md) | High overlap | Explicitly credits Brian's academic-writing architecture. The mechanism/example/boundary drafting check is useful when a paragraph lacks substance. Do not import Shawn's voice, fixed density rules, punctuation counts, or private canonical register. Our register discovery already avoids its filename-only search. |
| [review-implementation](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/review-implementation/SKILL.md) | High for methods and preregistration | Strongest new checklist: circular outcome definitions, criterion contamination, post-treatment filtering, claim/test mismatch, blinding, instrument validation, and amendment policy. Add a bounded study-design reference to our review workflow. Avoid turning every routine choice into a full optimisation survey. |
| [pre-run-review](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/pre-run-review/SKILL.md) | High for experiments and large bibliography batches | Borrow explicit outputs, completion/stop conditions, dependency ordering, partial-state semantics, and independent claim re-derivation with a coverage denominator. Use proportionately; do not impose the entire dialogue and operator teach-back on ordinary work. Its project-specific defect-rate claims are not universal calibration data. |
| [audit-config](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/audit-config/SKILL.md) | High for computational research | Useful protocol-to-config-to-actual-payload check, especially checking that the intended manipulated factor actually differs. Externalise map-reader paths, image flags, model assumptions, and tile rules. Observed filesystem state establishes what happened; it must not itself authorise departure from a preregistration. |
| [phase-gate](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/phase-gate/SKILL.md) | Medium-high before scaling experiments | Keep the load-bearing assumption ledger and cost-of-being-wrong question. Do not adopt the generic sample-size-100 rule or CI-overlap classification as a universal power test; require a design-specific analysis. Could be a short reference alongside the previous two, not another compulsory ritual. |
| [build-rubric](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/build-rubric/SKILL.md) | High for teaching; separate from bibliography | Valuable learning-outcome mapping, teaching-before-deadline check, observable parallel descriptors, and audit against the assessment brief. Bring its reference files if adapted. Remove the inference that uncorrected weaknesses establish students probably did not use a tool; assess submitted evidence under the actual course rules. |
| [moderate-mark](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/moderate-mark/SKILL.md) | Conditional teaching use | Promising evidence dossiers and separate upward/downward checks, but explicitly HUMN8031-specific. Course paths, weights, previous-assessment mappings, cohort norm, and default-to-lower rules need replacement. The skill requires discipline rules, dossier format, a worked example, and four stage briefs; copying SKILL.md is insufficient. |
| [improve-prompt](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/improve-prompt/SKILL.md) | Medium for research instruments | Borrow authority, scope, known-failure and completion checks when designing research prompts. Technique/profile references are bundled. Self-assigned before/after scores do not establish improvement; evaluate on representative cases. Avoid mandatory reconfirmation and scoring ceremony for small edits. |
| [reflect](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/reflect/SKILL.md) | Medium for research records | Useful separation of factual log, reflection, and surprising-fact/probe/belief-revision entries; explicit reconstructed-context labels are worth borrowing. Our project notes already cover continuity. Do not import automatic personal-observation registers, Shawn-specific collaboration rules, or infer session identity from the newest transcript. |
| [entity-classifier](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/entity-classifier/SKILL.md) | Conditional digital-humanities use | Historical building/organisation/metonymy classification with evidence and confidence. Keep project-local until needed. Replace Blue Mountains paths and calibrate defaults against a labelled corpus; ambiguous references should remain uncertain rather than silently becoming buildings. |
| [notebook-creator](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/notebook-creator/SKILL.md) | Conditional Fieldmark use | Relevant to field-data collection, not general academic writing. Depends on external Fieldmark reference documentation and examples under Shawn's home directory. Adopt only for an actual Fieldmark project and verify against its current schema. |
| [field-type-docs](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/field-type-docs/SKILL.md) | Conditional Fieldmark documentation | Useful bidirectional documentation/evidence checks. Otherwise tied to a particular documentation tree, UI, screenshot harness, and staging notebook. Leave out of the academic plugin. |
| [draft-email](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/skills/draft-email/SKILL.md) | Peripheral academic administration | Anchored specifics and draft-only handover are sensible, but private register, personal signature and email integration are Shawn-specific. No reason to add this to bibliography or manuscript review. |

## Useful workflows outside skills/

Several of Shawn's recommendations are commands backed by agents, not skills.

| Workflow | Useful addition | Boundary or dependency |
|---|---|---|
| [lit-scout and lit-scout-verify](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/lit-scout.md) | Highest priority: multi-source discovery, forward/backward chaining, DOI-first deduplication, separate verification and resumable drafts. | Bring both agent definitions and `scripts/lit-search.py` (`httpx`). Replace absolute venv/script paths and direct Zotero SQLite queries with our resolver. Scholar Gateway/Hugging Face tools need available equivalents or explicit unavailable-source reporting. |
| [lit-scout-iterate](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/lit-scout-iterate.md) | Optional correction loop after single-pass discovery is useful. | Imports into Zotero with `--live` on terminal outcomes other than the legacy-proposer case, including unverified outcomes. Retain our explicit write boundary. Fix structured-status parsing before adopting the loop. |
| [prior-art-scout](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/agents/prior-art-scout.md) and verifier | High for research software, datasets and method tooling; broader than literature search. | API evidence for repositories/packages/model hubs/papers. Keep build-versus-adopt advice separate from factual metadata verification. Do not import the iterator unchanged. |
| [data-profile proposer/verifier](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/agents/data-profile-proposer.md) | High for empirical work: machine-readable numerical claims and independent recomputation from the dataset. | Parameterised but substantial; scientific Python dependencies, optional extensive resampling and remote Git/SSH execution. Start with a bounded descriptive profile. This review inspected selected sections, not its complete statistical machinery. |
| [gaps](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/gaps.md) | Useful six-axis collection coverage map and distinction between absent-from-collection and absent-from-literature. | Abstracts and memory records are a screening basis, not proof of research absence. Adapt to our source cache and verified notes. |
| [synthesise](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/synthesise.md) | Theme-based integration across sources and explicit disagreement/gaps. | Re-ground claims in primary sources; its memory/abstract-driven collection workflow cannot establish full-text support. Avoid importing the private memory/PostgreSQL infrastructure. |
| [read](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/read.md), cite, cite-new | Reading question and source-linked insight capture are useful. | Mostly overlap with our bibliography skill. Keep resolver front door and BBT citekeys; do not adopt cite-new's locally invented AuthorYear keys for our bibliography. |
| [corpus-style-analyser-v2](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/agents/corpus-style-analyser-v2.md) | Useful optional way to derive a register from an author-approved corpus, separating attested, inferred and aspirational claims. | Bundled style-analyser scripts plus NLP environment, corpus/manifests, private outputs and external write-like-me environment. Strong overlap with our existing attested-register approach; metric similarity is not sufficient evidence of prose quality. Selected sections inspected. |
| [audit](https://github.com/saross/personal-assistant/blob/c1ad9052b6ce90d661ea7312265e099300b4ab7f/commands/audit.md) | Distinguishes implementation correctness from whether tests would detect wrong behaviour. Useful for research pipelines. | Borrow the different review questions and explicit unchecked scope. Existing engineering review skills already cover much of this. Its commit-first and personal test-environment rules are not portable requirements. |

## Verified caveats before reuse

1. **Metadata verification is narrower than source fidelity.**
   `agents/lit-scout-verifier.md` explicitly checks authors, year, title, DOI
   and citation counts; analysis sections pass through verbatim. A verified
   findings table does not verify the thematic narrative, relevance judgement,
   or what a paper supports. Our source-reading and quotation checks remain necessary.

2. **The iterative status examples can misclassify valid JSON.** Both scout
   drivers count literal compact strings such as `"status":"fail"`. Valid JSON
   containing `"status": "fail"` does not match. Their PASS conditions do not
   establish a positive, complete set of checked claims. The prior-art driver's
   PASS condition also omits its computed `UNVER_CT`. These are observed defects
   in the documented orchestration; no live agent run was attempted. Use parsed
   JSON, account for every expected claim, and preserve unknown states.

3. **The email-header correction is present.** Both `lit-search.py` and
   `lit-scout-zotero-import.py` resolve contact identity from `LIT_SCOUT_MAILTO`
   or `CROSSREF_MAILTO`, omitting it if unset. The command documents the fix
   dated 2026-09-21. This confirms the implementation change by source inspection,
   not a captured outgoing request.

4. **review-paper requires a runtime as well as three files.** The skill,
   design spec, workflow and pre-pass are tracked. The `.mjs` workflow expects
   injected `args`, `agent`, `parallel` and `log` globals; it is not a standalone
   Node program. Pre-pass Python is stdlib-based, with optional `aspell`,
   `texcount`, `.bib`, `.aux` and build inputs. It reports skipped checks and can
   exit zero with blockers, so consumers must inspect its JSON. The skill's
   0.3M / 0.4–0.5M / 2.5–3M token figures are upstream estimates, not measurements
   here or guarantees for another model/runtime.

5. **Some dependencies are deliberately private or project-local.** The README
   identifies `data/` as a private submodule. Academic/email canonical registers
   reside there; Fieldmark and Blue Mountains dependencies live in other repos.
   These must be replaced with our own project material, not presumed bundled.

6. **Licence documentation is incomplete in this checkout.** README says MIT
   and links to LICENSE, but `git ls-files '*LICENSE*' '*license*'` returns no
   licence file. Preserve provenance and resolve the missing licence text before
   redistributing copied implementation. This did not prevent inspection.

## AB+ cross-check in map-reader-llm

Also cloned `/tmp/shawn-map-reader-llm-20260922`, commit
`e10d50dd0fb50a99919b9b639b3b1de577088081`. Shawn's pointers check out:
25 tracked files under `scripts/ab_plus/`, five under `prompts/ab-plus/`
(README plus four briefs), and the dated run card. Read the README, run-card
pipeline and outcome sections, verifier brief, extractor adapter, configuration,
and schema declarations; this was not a full code audit.

The [AB+ briefs](https://github.com/saross/map-reader-llm/blob/e10d50dd0fb50a99919b9b639b3b1de577088081/prompts/ab-plus/README.md)
provide the most directly relevant bibliography addition: separate source-note
drafting, exact-span checking, interpretation verification and editing. The
verifier reads the whole source cache and tests hedges, conditions, denominators,
omitted caveats and inflated relevance. Provenance sidecars tell it when page
images must replace cache text as authority. The schema separates quotations
from advisory interpretation and permits NOT CHECKABLE.

**One more dependency than the conversation suggests:**
[`_extractor.py`](https://github.com/saross/map-reader-llm/blob/e10d50dd0fb50a99919b9b639b3b1de577088081/scripts/ab_plus/_extractor.py)
imports `extract_pdf_text` and `pdf_cleaner` from another checkout,
`llm-reproducibility/extraction-system/scripts/pdf_processing`, selected by
`AB_PLUS_EXTRACTOR_DIR`. The two cloned repositories alone therefore do not
supply its complete extraction runtime. Config also fixes a collection key,
paper bibliography path and output tree; briefs contain map-reader-specific
relevance criteria. Reuse our resolver/render cache and adapt the entry/verification
method instead of adding a competing extraction system.

The [run card](https://github.com/saross/map-reader-llm/blob/e10d50dd0fb50a99919b9b639b3b1de577088081/planning/ab-plus-run-card-2026-08-30.md)
reports 88 drafters, 88 verifiers and 88 editors for its tail batch, with all
88 entries requiring edits. Those are upstream observations, not validation
performed here. Pilot on a few sources after fixing our renderer; do not infer
that a whole-library run is cheap because the deterministic stages are local.

## Bibliography faults and adoption order

The user's reports of OCR mislabelling and page displacement remain open;
they were not reproduced against the Edwards or Marsh/Wen/Hau PDFs here.
Source inspection found that `renderer.py` labels the PyMuPDF cascade entry
`False` unconditionally, calls `to_markdown(..., page_chunks=True)`, and keeps
only each chunk's text. `_write_outputs` numbers those strings sequentially
and stores the supplied OCR boolean. Thus the wrapper does not establish
observed OCR provenance or preserve renderer page identity. This is a concrete
lead, not proof of the page-displacement cause.

Recommended order:

1. Reproduce and fix render provenance and physical-page attribution first.
   Check printed page labels separately from PDF physical page indices. Recheck
   affected cached renders and quotations; adding another verifier above incorrect
   metadata does not repair the evidence it receives.
2. Add a bounded literature-discovery workflow around our resolver, with an
   independent metadata check and explicit source-coverage limits. Keep new-item
   ingestion separate and previewed.
3. Adapt and pilot AB+'s source-note schema and interpretation check over our
   existing source cache. The pieces are verified present in map-reader-llm;
   no AB+ skill exists among personal-assistant's 14 skills. Resolve its external
   extractor dependency by integrating with our renderer, and retain visual PDF
   checks where provenance or page attribution is uncertain.
4. Enrich our paper review with selected preregistration, configuration and
   mechanical checks. Preserve evidence-based findings rather than adding a
   mandatory full panel or an aggregate validity certificate.
5. Keep teaching assessment and Fieldmark workflows separate, adopting them
   when the relevant course or fieldwork project needs them.

At the initial review stage, only this document was added. The subsequent
implementation and validation are recorded below.

## Follow-up: transfer shape after the renderer repair

The review above records the initial inspection. Subsequent renderer work is
separate; the table records the transfer plan before implementation.

| Destination | Transfer | Integration boundary |
|---|---|---|
| New `denubis-academic/skills/literature-scout/` | Single-pass discovery and independent metadata verification, with resume support | Its SKILL.md owns the research question, search coverage and handoff. Bundle portable search helpers and bounded proposer/verifier references. Use existing Zotero resolution; preview imports through the existing write procedure. Do not initially port the defective iterative driver. |
| New `denubis-academic/skills/annotated-bibliography/` | AB+ source-note schema, quote checking and interpretation review | SKILL.md routes resolution/rendering/quotation work through `using-bibliography`. Keep source text in the existing cache. Package the draft/verify/edit briefs with project-neutral relevance instructions; avoid the external extractor and a second Zotero client. Pilot on a few papers, including OCR and a paragraph crossing a page boundary. |
| Existing `paper-review/references/` | Study-design/preregistration checks from review-implementation; relevant mechanical checks from review-paper | Add only questions missing from the current facets. Keep author decisions and source-fidelity findings evidence-led. A LaTeX-specific pre-pass should be optional and expose skipped checks. Do not require Shawn's Workflow runtime. |
| Later, a separate experimental-methods skill | Config transmission, load-bearing assumptions, dependency and partial-state checks | Combine audit-config, phase-gate and pre-run-review around a concrete experiment rather than making three overlapping compulsory gates. Remove map-reader paths and universal statistical thresholds. |
| Later, a teaching-focused plugin | build-rubric; then a separately adapted moderation skill | Use local course outcomes, institutional rules and assessment evidence. Keep cohort norms and personal examples out of the portable method. |

Before copying code, resolve personal-assistant's missing licence text; retain
attribution and the source revision. Each new skill needs a clean-install path
check, a small representative workflow trial, and provider packaging consistent
with this repository. No personal memory hooks, private submodules, automatic
Zotero imports, or fixed worker/model counts are required by this transfer plan.

## Renderer repair validation (follow-up, 2026-09-22)

Implemented in the current worktree:

- PyMuPDF's non-OCR tier explicitly passes `use_ocr=False` and checks physical
  page count/order. OCR remains available through the explicit Docling OCR tier.
- Docling converts one physical page at a time, preventing its reading-order
  stage from joining paragraphs across pages. Markdown includes furniture and
  page-footer labels, preserving the printed page numbers in the Marsh case.
- New metadata carries `render_version: 2`. Both resolver and batch-ingest cache
  checks reject older PyMuPDF/Docling renders. Other renderer caches are retained.

Live checks using the actual Zotero attachments, with outputs confined to `/tmp`:

| Paper | Result | Output |
|---|---|---|
| Marsh, Wen and Hau 2004 | 26 pages. Printed 296/297 retained; a distinctive continuation previously present in physical-page file 022 now appears only in 023, matching PDF text on physical page 23. | `/tmp/marsh-renderer-fixed/` |
| Edwards 2001 | 23 pages, no near-empty pages, no replacement characters; PyMuPDF succeeds with OCR disabled and records false. | `/tmp/renderer-fixed/edwardsTenDifferenceScore2001/` |
| Edwards 1994 | Both non-OCR tiers reject all 50 near-empty pages; Docling OCR produces 50 readable pages, no replacement characters, and records true. | `/tmp/renderer-fixed/edwardsStudyCongruenceOrganizational1994/` |

These validate rendering and attribution, not every quotation in the papers.
Docling's per-page processing trades some throughput and cross-page layout
context for reliable physical-page boundaries.

Validation: all 315 bibliography tests pass; format and whitespace checks pass;
renderer/ingestion still parse as Python 3.11. Ruff reports three pre-existing
diagnostics (RUF012, ARG002, PLR0917), confirmed against HEAD; no additional
diagnostics remain. The dependency lockfile is unchanged. No release/install or
central-cache replacement was performed during that repair.


## Skill transfer implementation (2026-09-22)

Added two skills to the existing shared skills directory, discovered by both
provider manifests without provider-specific copies:

- `literature-scout`: bounded search, citation tracing, metadata checks and
  coverage reporting. A new standard-library client queries Crossref, DataCite
  and Semantic Scholar. Operator contact and credentials come from environment
  variables; neither Shawn's identity nor his runtime is bundled.
- `annotated-bibliography`: an evidence-entry contract and draft/check/review/
  revision procedure over the existing bibliography cache. Its checker rejects
  stale PDF metadata, mismatched source hashes, invalid physical-page locators
  and nonliteral quotations. OCR visual checks and interpretation review remain
  separate states; text presence never certifies a summary or paraphrase.
- `paper-review`: optional focused study-design questions for definitions,
  criteria, delivered interventions, selection, independence, equivalence and
  competing explanations. No mandatory panel or workflow runtime was added.

The instructions and helper implementations are newly written, with pinned
upstream method attribution in `references/workflow-provenance.md`; no upstream
code was copied. LaTeX pre-pass, experimental-methods and teaching transfers
remain deferred until a concrete project needs them. Academic skill descriptions
were shortened to fit the existing aggregate description budget.

Validation: 945 selected tests pass, including bibliography regressions,
portable CLI failure cases, skill links/frontmatter/descriptions and provider
packaging. Both new skills and the existing Codex plugin pass package validation.
New helper and test files pass Ruff lint and format checks. Live Crossref and
DataCite metadata calls and Semantic Scholar reference traversal returned HTTP
200. A first-page span from the repaired Edwards 2001 cache passes the annotation
checker and fails when assigned to page two. Mocked OCR cases retain the visual
verification requirement. This is helper validation, not a completed independent
review of an annotated bibliography; that workflow still needs human UAT with a
real research brief. No commit, release, live installation or cache replacement
was performed.

## Literature Scout trial follow-up (2026-09-22)

The Phaedra trial exposed an identity-handoff omission: the discovery table named
Conolly and Lake, but the verifier packet copied a registry null. The skill now
requires reconciliation against the candidate table and all inspected metadata,
with per-field provenance and separate preservation of missing/conflicting values.
A new reconciled packet preserves the original trial records.

Fresh offline before/after actors both retained the required fields and controls;
the isolated baseline did not reproduce the original failure, so this is not a
proven red-to-green result. The updated actor retained publisher evidence, registry
conflicts and genuinely unknown dates without including relevance arguments.
617 packaging/reference tests and the skill validator passed. Evidence and limits:
`/home/brian/people/Phaedra/Paper/codex-prompts/out/literature-scout-2026-09-22/handoff-fix/result.md`.
This follow-up changes the development skill; it does not install or release it.

## Scout acquisition boundary (2026-09-22)

The trial's standalone `verification-evidence/caraher.pdf` download bypassed
the managed bibliography workflow even though its URL was openly accessible.
The scout now promotes sources worth reading into a dedicated Zotero scout
subcollection, keeps speculative hits in the candidate log, and escalates the
whole missing-full-text shortlist before beginning reading. Existing items are
reused, acquisition uses existing scoped authorisation, and later exclusions are
cleanup nominations rather than automatic deletion. The shared bibliography
instructions prohibit standalone document downloads and duplicate extraction
corpora; reviewer handoffs must carry the same boundary.

The existing fetch helper supports collection targeting and `--no-render`; no
new acquisition code was added. All 617 skill packaging/reference checks and the
scout validator pass. These checks do not test agent compliance. No live Zotero
items or trial artifacts were changed, and the historical Caraher loose-file
reconciliation remains outstanding. The updated skill has not been installed.

## Live scout retest (2026-09-23)

A fresh actor resumed five actual Phaedra candidates without the prior failure
reports or evaluator oracle. It created scout subcollection TEX7GUUQ under
Phaedra-Paper1-data (XLNWQE9X), reused three existing items and imported GPS.gov
and Caraher metadata. Independent API read-back confirmed memberships and
preservation of the reused items' metadata. Stock local items POST works on the
running Zotero 10.0.3, superseding older helper comments calling it read-only.

The handoff retained publisher authors/dates alongside registry nulls and
conflicts. The actor held reading of two existing PDFs pending three missing
managed attachments, and passed that gate to the verifier. No PDF was downloaded.
A GPS.gov metadata request returned the page body; no substantive claim was
made from it. Successful new attachment acquisition, speculative-hit exclusion,
post-supply reading and cleanup were not exercised. The original loose Caraher
PDF still needs attachment reconciliation. All 617 packaging/reference checks
passed. This run does not establish universal compliance or a controlled
before/after comparison, and the changes remain uninstalled.

Evidence: `/home/brian/people/Phaedra/Paper/codex-prompts/out/literature-scout-retest-2026-09-23/result.md`.

## Release preparation (2026-09-23)

Brian accepted the current validation boundary and requested commit, marketplace
and push. Version 0.18.0 includes both provider manifests and the Claude catalogue
entry. Full release testing found missing Codex UI metadata for the two new skills
and an overbroad test-quality lint match on a generated Markdown assertion. Added
the UI metadata and checked the renderer's ordered return values directly instead.
All 1,296 repository tests, strict Claude marketplace validation and Codex plugin
validation pass. This acceptance does not certify the unexercised behaviors above.
