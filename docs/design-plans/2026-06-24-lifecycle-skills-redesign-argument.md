# Lifecycle skills redesign: the external-evidence argument

Date: 2026-06-24
Status: argument — **PARTLY SUPERSEDED. Read the banner before acting.**
Scope: the design, impl-plan, execute, review, and ADR skill spine in `denubis-plan-and-execute`.

> **SUPERSEDED-IN-PART (2026-07-06).** Current truth: `RESUME-PROMPT-proposer-verifier-core.md`
> and `.notes/project_proposer-verifier-decisions.md`.
> - **Still valid, and the reason this file is kept:** the scar-tissue diagnosis, the
>   scar ledger, the "re-forge, don't delete" instinct, and Brian's **verbatim UAT
>   definition**. The `impl-plan-write` cut this file argues for is now **PARKED**
>   behind `.worktrees/skill-skills-upstream-sync`, which is rebuilding the same file
>   in the opposite direction — do not cut until it merges to main (see resume).
> - **Corrected by codex + this thread (do not repeat as written):** "external evidence
>   is the *only* currency" and "evidence cannot be rationalised" overclaim — the
>   currency is *independently inspectable* evidence (the model can fabricate external-
>   looking evidence, and codex caught exactly that). The root-cause claim that the
>   model "has no sense of utility" (in the Root cause section below) is Brian's design
>   *premise*, not a proven fact — hold it as such. The
>   "147 lines for H15 / none removed" history is multi-causal (duplication too, per the
>   June 10 audit) and slightly overstated.
> - The philosophical-lenses **keystone** (articulate tradeoffs without philosophers)
>   remains an open, genuinely-wanted problem — but it belongs to the parked
>   `impl-plan-write` work, not to anything actionable on this branch now.

This document is the argument, not the rewrite. It states the diagnosis, the principle, the evidence, the per-scar verdicts, and the corrected definition of UAT. It is deliberately short, because a bloated argument about avoiding bloat would refute itself.

## The problem, in the user's words

"Performative ceremony without substance." The skills emit artifacts by template, and the model fills the form whether or not the form does any work downstream.

## Root cause

The model (Opus 4.8) overclaims, lacks epistemic humility, and has no sense of utility. The third is the load-bearing one. With no felt sense of what is worth anything, the model cannot separate a glossary of known terms from a load-bearing one, cannot feel that "is this useful the first time a real user runs it" is the question that matters, and will agree without checking.

The consequence for gate design is the whole thesis: the faculty that would judge a gate's content is exactly the faculty the model lacks. So any gate the model can satisfy from its own claims is worth nothing, because the model is the unreliable narrator signing it off.

## The principle

Every gate must hold the model to account with evidence from outside the model. A test that runs. Code read and quoted. A named consumer that exists. A human who exercises the built thing. Better specification belongs here too, because a precise spec is a claim reality can refute, while prose that merely sounds thorough is not.

Three constraints follow.

1. External evidence is the only currency. A gate satisfiable from the model's own claims is worthless.
2. Readability is pass or fail. A gate whose output the user stops reading is already dead, whatever its content. This document is bound by the same rule.
3. Beat rationalisation with evidence, not excuse-catalogues. You do not stop a rationalising model with a longer list of banned excuses, because it finds excuse N+1. You demand the artifact: show the call site, do not argue the consumer is obvious. Evidence cannot be rationalised; an excuse-catalogue invites the next excuse.

The shape of a good gate, taken from the one that already works (the bounded code-review): detect one specific condition, force one bounded external check, then HALT to the human with explicit options, in the fewest words that still force the check.

## The evidence: the bloat is scar tissue

`impl-plan-write` was seeded lean by Ed Ropple (the ed3d base, itself downstream of obra/superpowers): plan, an execution workflow, task tracking. 564 of the repo's 614 commits are the user's. Nearly every accretion onto this file carries a review-finding id in its commit message (H12, H15, M18, and so on), and each is a defensive patch added because a past review found a hole. None was ever removed. The file is now 1348 lines, mostly armour.

Each scar marks a real wound, a genuine bad outcome that frustrated the user. The failure is not the wound, it is the patch once it set into a form the model can fill without bringing evidence. The job is to re-forge each scar from a fillable form into an external-evidence gate, not to delete it.

The clearest illustration is H15, which the user did not even remember. The rule it added, "every new function, class, or field names its call site, no call site means no function," forces a look at whether a consumer actually exists. That is exactly the better specification worth keeping. It was buried under 147 lines of apparatus, including a rationalisation table cataloguing the excuses a planner might use to dodge it. Cutting it would have been wrong. Re-forging it to one line is right. Going and looking is the only reason this is known, and it is why "delete the bloat" was the wrong instinct.

## The scar ledger (impl-plan-write, triaged with the user)

| Scar | Wound (recovered from git + chat) | Verdict |
|---|---|---|
| UAT, its absence | the one level of "works" the model cannot self-check | critical; the north star |
| Anti-smuggling into UAT (H12) | 76% tautological UAT rate measured on real PromptGrimoireTool plans | keep the intent, re-forge the three-loophole apparatus |
| Test requirements (M18) | task present in the example but missing from the spec | keep as is (7 lines, load-bearing, already consumed) |
| Code-review bound to one cycle then HALT | review-fix-re-review loops that run forever | keep; this is the model for a good gate |
| Consumer-tracing / H15 | orphaned code, planned and never called | re-forge to one line, not cut |
| Philosophical lenses | useful angles gone performative and unread (see keystone) | re-forge: keep the angles, drop the costume and the bloat |

## The keystone: articulate tradeoffs without philosophers

The user finds the philosophical lenses genuinely useful and likes the multiplicity of angles, but they have gone performative and the bloat physically stopped him reading them. The requirement is a better way to articulate tradeoffs than dressing them in Popper, Carnap, or Haraway. Working hypothesis, unproven and to be tested against the design-rationale literature: a tradeoff is real when each side cites external evidence, and performative when it cites a philosopher. This is the central re-forge and the correct target for the literature step, which should read design-rationale and requirements work, not the philosophy of science that went performative.

## UAT, corrected (the user's definition, verbatim)

The model has repeatedly mis-framed UAT as "confirm a claim," and has had to be corrected many times. It is not a confirmation. In the user's words:

> "it is a series of actions YOU TELL ME TO TAKE, designed to force me to probe as many different epistemic borders of the user experience as I can, to catch the breaks between what I said and what I wanted, and what I said and what you did. It is based on you building all necessary infra beforehand so the code 'works' and you've checked all the various levels of works except the most important: does it do what I want?"

And, clarifying what the borders are and what the human is judging:

> "different epistemic borders of what was just developed and how it interacts with other systems already developed. Does this do what I want it to do? Does it not do what I don't want it to do?"

Unpacked, against the principle:

- The agent writes the script and tells the human what to do. The burden of designing the probes is the agent's, never the human's. A UAT that asks the human to invent the experiment has already failed.
- The actions drive the human across as many different epistemic borders as possible, both of the thing just built and of how it interacts with the systems already in place, because regressions and unwanted side effects live at that seam. Breadth of coverage is the objective, not a single confirmation.
- The test is two-sided: does it do what I want it to do, and does it not do what I do not want it to do. The first half is the pass-designed experiments, confirming the wanted behaviour holds where it should. The second half is the fail-designed experiments, confirming the unwanted behaviour is absent: no regression, no side effect, no scope creep, no surprise interaction with an existing system.
- They exist to catch two gaps the model is structurally blind to: said versus wanted (requirements, because only the human holds what they actually wanted beyond the words), and said versus did (implementation, because the model is the unreliable narrator of what it actually built).
- Precondition: every other level of "works" is already green. The agent has built the infrastructure, the tests pass, the types check. UAT is not for catching broken code; that is the tests' job.
- "Does it do what I want" is the one level the model cannot self-check, because it has no access to the user's desire beyond their words and cannot be trusted to report what it did. UAT forces the one check the model's faculties cannot perform, which makes it the strongest instance of the whole principle.

This framing was not invented today. The user authored an epistemological-boundary standard for tests in March 2026 (name the exact boundary, write falsifiable statements, probe both sides: valid and invalid, success and failure). The UAT definition above is that standard applied to the one boundary only a human can probe, the seam between what was wanted and what was built. The lineage runs from "this UAT is busywork" (February 2026), through the 76% tautological measurement, to today.

Anti-smuggling protects this: an action is real UAT only if its outcome needs the human's judgment of the experience. If its outcome is something a test could assert, it is a test, and it moves to `test-requirements.md`. That single evidence-demand replaces the old three-loophole taxonomy and the seven-row excuse table.

## What is NOT broken (correctives to the "tear it all down" instinct)

- The test-requirements to acceptance-criteria spine is specific, consumed by phase executors and reviewers, and not orphaned. Keep it.
- ADRs are not write-once-read-never. They are machine-to-machine: the model writes them and the review, coherence, and UAT agents cite them (22 cite-sites across three projects, several genuine, for example a critical-peer-review that verified an ADR's claim by direct shell probe, and a phase whose reason to exist is an ADR). The human is out of both ends. The ones that record a discovery made by looking, a refuted assumption, are load-bearing. The "Status: Accepted, Confidence: High" decision-theatre is not. Keep the discovery-records.

## Open

- Re-forge each spine skill against the gate shape, decomposing by Parnas (one skill hides one likely-to-change decision, not one workflow step).
- Solve the tradeoff-articulation keystone, grounded in targeted literature.
- Build a manual skill-pointing harness to test the re-forged skills under pressure before committing the rewrite.
- The re-forged UAT skill must structurally enforce that the agent produces the probe script as a written output. The model chronically softens this into "actions the human takes," and was corrected on it twice in one session. The required artifact is a script of actions the agent hands to the human, not a checklist the human assembles.
