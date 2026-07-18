---
name: academic-writing
description: Use when drafting or revising academic prose, especially revision passes and reviewer edits. Reads the project's .notes/ register rules first, then cuts scar tissue and rebuilds crammed sentences.
---

# Writing Academic Prose

**Announce at start:** "I'm using the academic-writing skill, and I'll read the project's register and writing rules in `.notes/` before I touch the prose."

## Overview

Academic prose fails in two compounding ways. The session works off the project's CLAUDE.md summary and never opens the full rules, so the calibrated discipline never loads. Then, expanding or revising, the writer reaches for sentences that manage the reader instead of carrying content. These are scar tissue, and they regrow on every revision pass.

This skill makes the project's own rules fire at draft time, then supplies the discipline that keeps the prose clean. The project's `.notes/` rules are authoritative and override anything here. This skill is the portable floor, and the thing that forces you to go read them.

The same register floor ships as the `Academic Writing` output style. Select it via `/config` when a whole session is writing, and it holds these rules in the system prompt on every response. This skill is the on-demand path that also runs the `.notes/` gate and the revision-pass workflow.

## Gate: read the project's writing rules first (once per session)

Before your first prose edit this session, open the project's `.notes/` and read the full writing and register rules. Not the CLAUDE.md one-liner. The summary in your context is a pointer, not the rule, and the calibration that matters lives in the full note.

Find them:

```bash
ls .notes/ 2>/dev/null | grep -Ei 'prose|plain|scar|register|citation|pinpoint|writing|voice'
```

Read every match. Read any `reference_*` whose own description mentions register, citation, or style. If the project has no such notes, the portable core below is the floor, and consider proposing one `.notes/feedback_*.md` once you learn the project's register.

This gate fires on every kind of prose edit, including a two-sentence reviewer tweak deep in a long session. The cost is one read. The failure it prevents is a whole session of drift that no one catches until review.

| Rationalisation | Reality |
|---|---|
| "I skimmed them earlier this session" | A skim hours and forty tool-calls ago is not the rule in front of you now. Re-open it. |
| "It's a tiny two-sentence change" | Reviewer-driven tweaks are where scar tissue regrows fastest. Small edits earn the same gate. |
| "Submission is in 40 minutes" | The read is thirty seconds. Shipping uncaught scar tissue costs a review round. |
| "I wrote this section, I know the rules" | You knew them and still produced the drift the rule exists to block. Reading is cheaper than re-deriving. |

## Scar tissue: the subject test

For each sentence, ask: is its subject the **study**, or the **manuscript**? If the subject is the paper, meaning its structure, its defensibility, the relationship between its citations, or what comes next, cut the sentence or rewrite it to state the substance directly. Describing the analysis itself (what a test is, how it works) is content and stays. Talking about the machinery as machinery is scar.

The recurring forms:

- **Foreshadowing.** Previewing a hypothesis, result, or contribution before its section. State hypotheses in the present-study section, and let the introduction end on the gap.
- **Defensive hedging.** Pre-empting a reviewer ("twelve students cannot generalise", "without a control group"). State the design, and let limitations live where limitations live.
- **Provenance housekeeping.** Sentences about the citations or the structure ("this section sets out", "building on the gap above", "reported through two lenses"). Make the substantive claim and let the relationship show itself.
- **Journal-requirement framing.** Justifying a choice by the venue ("per journal policy"). The choice stands on its own grounds.
- **Procedural narration.** "We computed", "we then ran", where the sentence adds nothing beyond the step.

Where the project's register note attests a signposting convention (sequential markers such as "First / Second / Finally", or a "this paper presents" opener), the convention wins, and the subject test governs the sentences the note is silent on. Some venues require explicit contribution statements in the introduction; the note is where that requirement lives.

### Reviewer requests are the main scar-tissue generator

A reviewer asking you to "signpost how this follows", "make the contribution explicit", or "address concern X" is asking for a clearer **claim**, not a sentence about the manuscript. Satisfy the request with substance:

- "Signpost how this follows" → open with the substantive link, not a structural announcement. Not *"That transfer question is the gap this study addresses."* Instead state what the study does about it, and the connection is visible.
- "Make the contribution explicit" → put the novel claim where contributions live, stated plainly, not foreshadowed in an opening that should carry the gap.
- "Address the small-N concern" → that belongs in limitations as a stated design fact, not as a defensive aside in the body.

## Plain language

Write to the audience the project names (often non-statisticians). Introduce a concept by what it does, then name it once: *"deciding how many groups to use, based on how well each candidate number predicts left-out respondents (cross-validation)."* Spell an acronym on first use, then prefer the plain phrase. Three acronyms in one sentence means stop and rewrite. A glossary at the end does not fix a jargon-stacked paragraph. Rewrite the paragraph.

## Register: derive it from a target paper

Match a concrete register target, usually a paper the team already published in the venue. Read it and derive the rules rather than guessing: sentence length and connective density, where first person is allowed, how hedging is calibrated, how every statistic gets a plain-words gloss, whether sections open on what they investigate, and the punctuation the register actually uses. The project's `.notes/` may already carry this rubric, and where it does, that rubric wins. This skill does not ship a universal register. The construction discipline in the next section (the laundering test, the staccato guard, one idea per sentence) is portable; the punctuation hierarchy and connective defaults are one author's register, supplied as the starting point when the project's `.notes/` names none. Where a project note attests different values, the note wins, and those defaults do not fire as red flags.

## Pinpoint citations (APA paraphrase rule)

For a journal-article **paraphrase**, the APA default is to omit the page. Keep a page only when it earns its place:

- **Direct quotation.** A page number is required, so keep it.
- **Book or book chapter.** APA's own worked example, so keep it.
- **Reproduces a specific numeric value** (an alpha, a threshold, an effect size). Keep it, because the locator aids verification.
- **Paraphrase of a finding or concept.** Remove the page and keep the cite.

Cite a source for what it actually supports. Do not stretch a finding past what the source shows. If a claim needs a stretch, name the stretch as extrapolation.

## Sentence construction and punctuation

Flow lives in how a sentence is built, not in the marks that hold it together. The register most academic venues reward, and the one this skill defaults to, is the long connected sentence carried by subordinate clauses, with the relation between sentences and paragraphs made explicit by discourse connectives (*Despite this*, *Therefore*, *However*, *Additionally*). A glue mark is a sign the construction failed, not a tool to reach for.

Punctuation hierarchy, one author's defaults, in force when the project's `.notes/` register names no values of its own (an attested project value wins):

- **Em-dash (—): never.** Hard stop. Where one would go, the sentence wants rebuilding.
- **Semicolon: exceptionally rare.** Reach for it only when there is genuinely no other way to say the phrase.
- **Colon: sparing, for a list or a definition.** Fine in its place. A colon on every page means the prose has come to lean on it.
- **Commas and full stops carry the prose.** Related clauses ride on commas, and a separate idea takes a new sentence.

When you reach for a banned or rare mark, rewrite the thought rather than re-mark the sentence. Reaching for an em-dash means the sentence is trying to carry a second idea or a crammed aside. Rebuild it in the connected register, subordinating the related material with a relative clause or a connective, or giving a separate idea its own sentence, and drop an aside that repeats something already said. Swapping the em-dash for a semicolon, a colon, or a comma pair while the clauses stay put is laundering. The test is plain. If the new version maps onto the old one clause-for-clause with only the mark changed, you laundered it, and the cadence has not moved.

Do not over-correct into staccato. Breaking a sentence into a stack of short declaratives to avoid a mark is the opposite failure, and three or more short sentences in a row reads as a machine gun. The cure for the crammed sentence and for the choppy stack is the same one, a single connected sentence that carries one idea, joined by connectives where the clauses relate.

- **One complete idea per sentence.** The subordinate clauses elaborate that idea. They do not smuggle in a second one.
- **Pairs, not triples.** Two parallel clauses read cleanly. A third wants to become a list.
- **Make the positive claim and stop.** A claim trailed by a "not the other thing" foil is a tic, and the positive half carries the meaning alone.
- **Read it aloud, and let the read be the judge.** A rebuilt passage flows, neither crammed with glue marks nor chopped into fragments. En-dashes in number ranges (*weeks 1–2*) are correct and stay.

## After an edit

- **Propagate the fix.** When you change a fact, name, threshold, or method, grep the project and fix every place it appears in the same pass. Canonical files first, and leave dated historical records alone.
- **Do not launder prior AI output.** A working note that looks authored may be a prior session's draft. Do not migrate it into a "verified" form. Read the primary source and write fresh.

## Red flags, stop here

If you catch yourself reasoning any of these, you are about to reproduce the failure:

- The project's register note attests the mark or pattern you are about to fix. → The note wins. Check its stated target instead of this floor, and leave the prose alone.
- "It's a small edit, I'll skip re-reading the notes." → Open them. The gate has no size threshold.
- The reviewer said "signpost" / "make explicit" / "clarify the connection", and you are about to write a sentence whose subject is the section. → That is scar tissue. State the claim instead.
- "I'll gloss the statistic later." → Gloss it now. Later never comes.
- You swapped an em-dash for a semicolon, colon, or comma pair and left the sentence otherwise intact. → Laundering. The crammed structure is the problem, not the mark. Rebuild from the idea.
- Your rebuilt sentence maps onto the original clause-for-clause with only the punctuation changed. → The cadence has not moved, so the fix failed. Rebuild from the idea.
- You used a semicolon where a full stop or a recast sentence would carry the meaning. → Semicolons are exceptionally rare in this register. Recast.
- Avoiding em-dashes pushed you into three or more short sentences in a row. → Staccato. The register wants connected sentences, so rejoin related clauses with connectives.
- "The content in this working file is basically ours." → Check the voice. It is probably unreviewed AI output.

## Before declaring the prose done

- [ ] Opened and read the project's full `.notes/` writing and register rules this session
- [ ] Ran the subject test on every new or revised sentence
- [ ] Read the passage aloud: each sentence carries one complete idea and the prose flows, neither crammed (glue marks) nor choppy (short-sentence stack)
- [ ] Every em-dash, glue colon, or glue semicolon rebuilt from the idea, not swapped for another mark
- [ ] Reviewer requests answered with substance, not signposting
- [ ] Pages kept only for quotes, books, or numeric values
- [ ] Propagated any changed fact, name, or threshold across the project
