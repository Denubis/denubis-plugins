# External review: academic-writing skill and output style

**Reviewer:** Shawn Ross (with Claude Fable 5), 2026-07-18, at Brian's
request.
**Scope:** `plugins/denubis-plan-and-execute/skills/academic-writing/SKILL.md`
and `plugins/denubis-plan-and-execute/output-styles/academic-writing.md`.
**Method:** both files read in full and reviewed against the repo's own
instruments (`epistemic-humility::*`, the rubric-for-rubrics draft R1–R12,
the form-taxonomy probe C1–C6, and `writing-skills::*`), then compared
with the corpus-empirical apparatus behind Shawn's register
(corpus-style-analyser v2.3: 18 publications, 127,720 words of body
prose, per-claim attestation counts). No prior audit covers these files;
`docs/audits/*` and `docs/issues.md` contain no mention of either, so
this is the first review pass. Citations follow the `file::section`
convention. Licence: CC-BY-SA-4.0.

## Verdict

The architecture is right and worth keeping: a portable procedural floor,
per-project register authority in `.notes/`, a session gate that forces
the full rules into context, and paired skill/output-style delivery. The
subject test and the laundering test are the best parts, because both are
falsifiable at the sentence level. The findings below are mostly cases
where the floor claims to be register-neutral but is not, where a
prohibition generates the distortions it then has to patch, and where the
skill's exit criteria fall short of the observability standards this repo
applies elsewhere.

## Strengths worth keeping unchanged

- **The `.notes/` gate with its rationalisation table**
  (`SKILL.md::Gate`). Pre-empting "I skimmed them earlier" and "it's a
  tiny change" is exactly how discipline skills survive long sessions.
  We are adopting this pattern into our own write-like-me workflow.
- **The subject test** (`SKILL.md::Scar tissue`). Study-or-manuscript is
  a binary a weak executor can apply per sentence, and the reframing of
  reviewer requests as the main scar-tissue generator is an insight we
  have not seen written down elsewhere.
- **The laundering test** (`SKILL.md::Sentence construction`).
  Clause-for-clause mapping with only the mark changed is a named
  falsifier for a fake fix. This satisfies `epistemic-humility::Screen 3`
  better than most checklist items in the repo.
- **Naming the counter-failure.** The staccato guard prevents the
  em-dash rule from producing fragment stacks. Prohibitions rarely ship
  with their backfire mode documented; this one does.

## Findings

### F1. The "portable floor" ships a register (structural, highest priority)

`SKILL.md::Register` states "This skill does not ship one project's
register." The sentence-construction section then ships one: em-dash
never, semicolon exceptionally rare, long connected sentences with
sentence-initial discourse connectives (*Despite this*, *Therefore*,
*However*). These are register choices, not register-neutral floors, and
they conflict with empirically attested academic voices. In Shawn's
corpus, sentential semicolons run ≈ 3.4 per 1,000 words across 18/18
papers, "however" is mid-sentence and comma-set with sentence-initial
use the minority form, and sequential signposting is heavily attested.
The Paper B register note we produced for this skill
(`reference_register-shawn-ross.md`, shipped alongside this review) has
to override the floor in four places before it can describe one real
author.

The override mechanism exists and is stated ("project rules win"), but
the rhetoric fights it: the semicolon prohibition is restated four times
(hierarchy, laundering paragraph, red flags, closing checklist) while
the project-rules-win clause appears once. A session holding both a
project note that says "semicolons are on-voice, target 3.4/1k" and a
red flag that says "you used a semicolon where a full stop would carry
the meaning → Recast" receives contradictory instructions at a four-to-
one repetition ratio favouring the floor. By `rubric-for-rubrics::R4`,
"never" here is rhetorical emphasis presented as a true boundary; by the
form taxonomy this is **C1** (prohibition on the shaping problem), and
the skill exhibits the C1 signature in full: prohibition → distortion
(laundering, staccato) → patch (two paragraphs of counter-guidance).

**Recommendation.** Move the punctuation hierarchy and connective
preference into an explicitly labelled default register block ("this is
Brian's register, used when the project supplies none"), and state the
floor's actually-portable rules separately (laundering test, staccato
guard, one-idea-per-sentence, rebuild-from-the-idea). Honesty about
whose register the defaults encode costs nothing and removes the
contradiction pressure on overriding notes.

### F2. The subject test overreaches venue-attested signposting

The scar-tissue forms list cuts "this section sets out" and
foreshadowing unconditionally (`SKILL.md::Scar tissue`). In archaeology
and much of HASS, "This paper presents…" openers (attested 11/18 papers)
and "First / Second / Finally" sequencing (72 instances, 18/18 papers)
are venue conventions with real reader-orientation payoff, and some
venues require explicit contribution statements in the introduction. The
floor's red flags would fire on prose that is correct for the venue.
This is **C2** (nuance handled by implication rather than an observable
predicate): the carve-out currently exists only via the general
project-rules-win clause.

**Recommendation.** One added sentence scopes the cut: "Where the
project's register note attests a signposting convention, the
convention wins; the subject test governs sentences the note is silent
on." That converts the implicit nuance into a checkable conditional.

### F3. No epistemic-hedge guard (overclaim risk on weak executors)

The floor cuts "defensive hedging" and instructs "make the positive
claim and stop" (`SKILL.md::Scar tissue`,
`SKILL.md::Sentence construction`). Nothing distinguishes reviewer
pre-emption (cut, rightly) from epistemic calibration ("suggests",
"may", "indicates"), which in empirical venues carries the
claim-evidence fit. Failure scenario: a Haiku-tier executor, holding
"cut defensive hedging" and "make the positive claim and stop", edits a
results paragraph and strips "suggests" from a claim the data only
suggests. The edit passes every current checklist item and produces an
overclaim a reviewer will catch months later. By `rubric-for-rubrics::R2`
the floor is exactly where the guard belongs, because the weakest
executor is the one that needs the distinction spelled out.

**Recommendation.** Add one rule: "Epistemic hedges calibrate claim
strength to evidence and stay; match the attribution verb to the
evidence (demonstrates / indicates / suggests). Defensive hedging
anticipates a reviewer and goes. When unsure which you are looking at,
ask whether deleting it strengthens a claim the evidence does not
support."

### F4. Exit criteria are self-attested (the repo's own screens fail them)

Run `epistemic-humility::Observability` over the closing checklist:
"Ran the subject test on every new or revised sentence" and "Read the
passage aloud" have no named falsifier (Screen 3) and hold true in a
state where nothing was done (Screen 2). This is **C6** (vibes exit
criterion) in a skill whose subject matter is unusually countable.
Em-dash count, consecutive-short-sentence runs, booster vocabulary, and
sentence-length means are all measurable with a ten-line script, and
this plugin already ships Python tooling far heavier than that
(`workflow_statusline`, `crash_recovery`). The writing skill is the
outlier: zero tooling for the most machine-checkable rules in the repo.

**Recommendation.** Add an optional verification step: a small script
(or documented one-liners) that counts em-dashes, flags three-in-a-row
short sentences, and greps a booster deny-list over the changed prose.
Report counts; let the human judge. That converts three checklist items
from self-attestation to evidence, and satisfies the Jones conditions
(bounded, auditable, reversible; misses surface immediately). Shawn's
8-metric gate (see F6) is a working reference implementation.

### F5. The `.notes/` contract is defined outside the repo

The gate greps `.notes/` and reads `reference_*` notes by description
(`SKILL.md::Gate`), but no file in this repo specifies the naming or
frontmatter contract; the skill-audit campaign itself lists the ".notes
frontmatter spec" as living in the global CLAUDE.md
(`docs/audits/2026-06-10-skill-audit-campaign.md::Blocks to relocate`).
For marketplace adopters, the skill gates on a convention they cannot
read anywhere. This review's companion artefact,
`reference_register-shawn-ross.md`, was built by reverse-engineering the
contract from `SKILL.md::Gate` plus `feedback_*` usage in the audit
docs.

**Recommendation.** Ship a `reference_register-TEMPLATE.md` next to the
skill (or a ten-line spec section in SKILL.md): filename must match the
gate's grep, description must name register/citation/style so the
description-scan finds it, body sections the skill expects. The Paper B
note can serve as the worked example.

### F6. Single-exemplar register derivation confounds voice with venue

`SKILL.md::Register` derives the register from one target paper by
qualitative read. Two failure modes, both observed empirically when we
built Shawn's guide from an 18-paper corpus: (1) venue- and
co-author-imposed features masquerade as voice (citation-string
conventions looked like a voice tic until cross-paper comparison showed
them venue-determined and they were excluded); (2) drift is invisible at
n=1 (the corpus-aggregate em-dash rate of 0.57/1k conceals a deliberate
post-2023 decline to zero; only year-binning exposed it, and an emulator
matching the aggregate would write 2019-vintage prose). A single
exemplar cannot distinguish stable voice, venue imposition, or a
register the author has since abandoned.

**Recommendation (structure-preserving).** Keep lazy at-write-time
derivation as the floor behaviour. In the register-note template (F5),
add three slots the deriving session must fill: attestation basis (how
many papers or words the rule rests on), venue-versus-voice separation
(which rules are imposed by the target venue rather than the author),
and recency (is the exemplar current, and is any feature known to have
drifted). Where a team has its own publication corpus, derive the note
from the corpus once rather than from one paper repeatedly; the
corpus-style-analyser agent that produced Shawn's guide is available as
prior art, including its status vocabulary (attested /
attested-rarely / attested-concentrated / absent-when-searched /
derived-by-inference) and its finding that generation shows systematic
biases against measured targets (over-producing "we" at ≈ 1.3× corpus
rate, over-conceding at ≈ 2×, under-using semicolons at ≈ 0.4×). A
"known generation biases" slot in the note lets the skill warn the
executor which direction it will drift.

### F7. Skill and output style duplicate 43 of 60 lines with no sync test

43 of the output style's 60 non-blank lines are verbatim copies of
SKILL.md lines (measured with `comm` over sorted unique lines,
2026-07-18). The layering intent is sound (style = always-on floor,
skill = gate + workflow), but the shared core is copy-paste with no
guard, and `rubric-for-rubrics::R12` treats silent divergence of living
documents as scar tissue. The repo already has precedent for exactly
this class of guard (`tests/test_marketplace_sync.py`).

**Recommendation.** Either generate one file from the other, or add a
`test_academic_writing_sync.py` that asserts the shared sections remain
identical and names the intentionally-divergent ones.

### F8. Mechanical conformance: pass (verified)

`uv run pytest tests/test_skill_descriptions.py -q` passes 379/379 on
this checkout (2026-07-18), so the skill's description satisfies the
trigger-first, length, name-drop, and enumeration rules. The
description's claims match the body (announce line, gate, scar-tissue
focus). No action.

## Summary of recommendations

| # | Change | Size |
|---|--------|------|
| F1 | Label the default register as Brian's; separate truly portable rules | Medium |
| F2 | One-sentence venue-convention carve-out on the subject test | Small |
| F3 | One-rule epistemic-hedge guard with attribution-verb tiers | Small |
| F4 | Optional counting script for em-dash / staccato / boosters | Medium |
| F5 | Ship `.notes/` register-note template + worked example | Small |
| F6 | Attestation-basis, venue-separation, recency, and bias slots in the note template | Medium |
| F7 | Sync test or single-source generation for the skill/style pair | Small |
| F8 | None | — |

## What we are taking in return

The review cuts both ways. Our write-like-me workflow is adopting the
`.notes/` gate with the rationalisation table, the subject test as a
pre-filter before our quantitative gate, and the announce-at-start
convention. Our empirical guide gains a procedural delivery layer it
lacked; Brian's procedural skill gains an empirical register source it
lacked. The two systems compose rather than compete, and the Paper B
register note is the first artefact built to run on both.
