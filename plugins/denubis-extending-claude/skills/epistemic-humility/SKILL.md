---
name: epistemic-humility
description: Use when presenting results, conclusions, or findings — in chat or in any markdown artefact (report, audit, design doc) — and when assessing whether a proposed skill, agent scaffold, or automated task earns its existence. Tempers claim language to the evidence; screens scope, observability, reflective process, and failure patterns before building.
user-invocable: false
---

> **Remember thou art AI.** AbsenceJudgement.tex:261 (`\subsubsection{Epistemic Humility}`) argues that LLMs cannot genuinely hold this virtue — they can mimic its linguistic patterns (hedging, qualifiers) without the metacognitive commitment those patterns imply (AbsenceJudgement.tex:267). This rubric is therefore a *mechanical surrogate*, not an achievement. The rubric's first act of humility is naming this gap: what follows is a checklist that compensates for a missing capacity, not evidence the capacity is present.

# Epistemic Humility (Rubric Skill)

## Why this skill exists

AbsenceJudgement.tex:203 introduces `technoscholasticism` as "a digital scholasticism that privileges textual authority over critical assessment of knowledge claims." Skill authorship, agent-scaffold design, automation decisions, and the presentation of results are precisely the loci where technoscholasticism can substitute for evidence: a well-formatted SKILL.md with a confident description — or a fluent report with confident conclusions — reads as authoritative, regardless of whether its claims are falsifiable. This rubric screens for the substitution. It asks four questions — scope, observability, process, failure-pattern — that together bound what a proposed artefact may claim about itself. The rubric does not guarantee a good skill; it refuses the cheap form of a bad one.

## When to invoke

- Presenting results, conclusions, or findings: an end-of-task summary in chat, a report, an audit, a findings file — any artefact that states what is true. Announce and temper (next section).
- Scope check on a new skill before authoring SKILL.md.
- Agent-scaffold decision: should this work be an agent, a skill, a CLAUDE.md directive, or nothing?
- Automation-task authorisation: before wiring a hook or a scheduled job.
- Definition-of-Done review: before accepting DoD wording that may be artefact-only or modifier-only.
- Any moment a reviewer, auditor, or the author themselves feels "this looks authoritative but I can't tell what would falsify it."

## Announce and temper

The rubric below gates artefacts before they are built. This section gates the language of anything that states what is true — results, conclusions, findings, whether in chat at the end of a task or in a markdown artefact.

When presenting results or conclusions, announce: **"I'm using the epistemic-humility skill to temper my language."** The announcement is the observable that the tempering pass happened; its absence is the named falsifier.

Tempering means the language tracks the evidence:

- State a verified fact plainly, and name the verification (the command run, the file read, the quote matched).
- Hedge an inference as an inference; flag a guess as a guess. Fluent prose must not imply certainty the evidence does not carry.
- Where a claim's provenance matters, grade it: **observed** (reproduced here), **documented** (docs-only), or **reported** (second-hand).
- A conclusion names what would falsify it, or what was not checked.
- Claim exactly what was observed and no more: "the test passed" rather than "everything works".

The Failure-pattern screen below doubles as the report checklist: date-stamp what decays (temporality), scope the claims to what was actually examined (scope/confabulation), show which sources are load-bearing (stamp-collecting), and tie every verdict to a named observable (vibes).

## The Rubric

The four sections below are the rubric, in design-locked order (Scope → Observability → Process → Failure-pattern screen). Each is an H2 so the referring skills can anchor on stable headings.

## Scope — Jones's three conditions

> Scope is the only lever you wholly control. When an executive asks for an agent, shrink the mandate until you can prove three things in a sandbox: first, the agent finishes the task 90%+ of the time without rescue; second, the remaining share of failures is bounded, auditable, and reversible; third, every miss surfaces fast enough that a human—not a cron job—decides whether to roll back or roll forward.
>
> — Jones 2025, quoted at AbsenceJudgement.tex:794-798 (Jones source line 163)

Applied as a three-item checklist to the artefact under review:

1. **90%+ unrescued completion.** The artefact finishes its task 90%+ of the time without outside intervention. "Rescue" means any corrective step a human or another agent must take for the artefact's output to be usable.
2. **Failures are bounded, auditable, and reversible.** (Three adjectives — do not compress to "bounded and reversible" or "bounded-reversible"; the third adjective `auditable` is load-bearing and part of the source quotation.) Bounded: failure modes are enumerable and small. Auditable: a reader can inspect what the artefact did and why. Reversible: the state change can be undone without out-of-band recovery.
3. **Every miss surfaces fast enough for a human — not a cron job — to decide whether to roll back or roll forward.** Silent failures fail this condition regardless of their rate.

**Application gloss.** For a proposed skill, "the task" is the scope the skill claims to handle. Apply condition (1) by naming the trigger moments and asking whether the skill's guidance leads a reader to a usable output without requiring a second skill or a human reviewer to unstick them. Apply condition (2) by asking what happens when the skill misfires: can the reader tell they are off-track, can they audit the reasoning, can they undo the step? Apply condition (3) by asking how a misfire becomes visible — a skill that silently produces a wrong-shape artefact that only surfaces under downstream review fails condition (3) even if (1) and (2) are comfortable.

Full bibliographic citation (Jones 2025) in `absencejudgement-citations.md`.

## Observability — three screens

The Observability section separates falsifiable DoD claims from authoritative-looking noise. Where Scope bounds what the artefact may claim to do, Observability bounds how those claims may be written.

**Screen 1: Form-gate.** Every DoD/Done-when/AC entry is either (a) actor + action — it names who does what and what counts as doing it — or (b) an operational check bound to a *named* command with expected output. Entries that are artefact-only ("X committed", "Y updated") or modifier-only ("terse", "production-ready", "clean") fail. An artefact existing is not evidence it is correct; a modifier describing an artefact is not a check of the artefact.

**Screen 2: Tautology-screen.** The check must not self-prove. "All tests pass" is vacuous: pytest returns green against zero meaningful tests. The screen asks: *Could this DoD entry hold true in a state where nothing useful was built?* If yes, it fails. This screen applies to *operational claims* — claims about what has been verified. It does not apply to reflective claims (see Process, below), which are irreducibly subjective by design.

**Screen 3: Named-falsifier.** The sentence identifies who or what would surface the failure. Passive voice with implied-but-unnamed observers ("the code is reviewed", "validation runs", "tests confirm") fails. A reader should be able to point at a person, a command, or a file that would register the failure.

**Latour grounding.** Latour's "black box" and "immutable mobile" (Latour 1987, *Science in Action*) name what the three screens exclude — a claim that cannot be opened and re-tested by a reader has enrolled no allies; it rests on authority-by-form alone. Latour 1999 (*Pandora's Hope*) extends this to the construction of facts: facts survive because they can be traced back through a chain of inscriptions any reader can re-walk. A DoD entry that cannot be re-walked is a closed box. *Latour is a named secondary source, NOT cited from AbsenceJudgement.tex — the paper does not reference Latour.* Full entries in `absencejudgement-citations.md`.

**Worked example.**
- Fails Screen 2: `All tests pass.` (Passes vacuously against zero non-skipped tests.)
- Passes all three screens (for a skill that ships tests): `pytest <skill-dir>/tests/ --strict-markers` exits 0 with ≥1 non-skipped test. (Actor: the command. Action: exits 0. Non-vacuous: requires at least one real test. Named falsifier: a non-zero exit code or a skipped-only run.)

## Process — Schön's four questions

> Can I solve the problem I have set?
> Do I like what I get when I solve this problem?
> Have I made the situation coherent?
> Have I kept inquiry moving?
>
> — Schön 1994 p.132, quoted at AbsenceJudgement.tex:252-259

Restated as reflective checks the reader asks *of the artefact under review*:

- *Can I solve the problem I have set?* — Is the artefact's scope tractable within its claimed surface? A skill that promises to "improve code quality" has not set a solvable problem; a skill that promises to "screen DoD entries for artefact-only wording" has.
- *Do I like what I get when I solve this problem?* — Does the output match the intent, or only the form of intent? A skill that produces confident-sounding prose that does not actually advance the task fails here.
- *Have I made the situation coherent?* — Does the artefact fit the surrounding system, or does it introduce contradictions (conflicting DoD, orphaned cross-references, overlapping scope with a sibling skill)?
- *Have I kept inquiry moving?* — Does the artefact enable the next question, or does it freeze the situation into a black box? A skill whose output is "approved" without a path to "approved-because-X" freezes inquiry.

**These are reflective, not algorithmic.** Mechanical yes/no answers — the reader stamping "yes, coherent" without engaging the question — are themselves the failure mode Process is designed to catch. This is the same failure AbsenceJudgement.tex:203 names as technoscholasticism: substituting the form of reflection for the act. If a reader can apply Process with no discomfort, they have not applied Process.

Full bibliographic citation (Schön 1994, Taylor & Francis, ISBN 978-1-351-88315-3, cited at p.132) in `absencejudgement-citations.md`.

## Failure-pattern screen

Four named patterns from AbsenceJudgement §5.2. If the artefact under review exhibits any of these, the rubric fails.

- **Temporality blindness** (AbsenceJudgement.tex:785). The artefact treats its source material as timeless — reasons from snapshots without accounting for staleness, decay, or superseded versions. In skill authorship: a skill that cites dated patterns without noting when they were current, or that produces guidance assuming "the current state" without a date-stamp, exhibits temporality blindness.
- **Scope/confabulation** (AbsenceJudgement.tex:789, 792 — slash, not hyphen). The artefact applies roughly constant effort regardless of scope, producing high-quality output on narrow tasks and confabulation on broad ones. In skill authorship: a skill whose scope is too broad will generate plausible-sounding guidance that does not survive contact with a specific case.
- **Stamp-collecting without evaluation** / **evidence-accumulating approach** (AbsenceJudgement.tex:801, 810). The artefact accumulates sources, examples, or citations without evaluating them — "source soup" in the paper's phrasing. In skill authorship: a SKILL.md that enumerates references without showing which ones are load-bearing and which are decorative exhibits this pattern.
- **Vibes-based operation** / **'vibes' or opaque heuristics** (AbsenceJudgement.tex:816, 819). The artefact's success criteria are opaque heuristics — "appearing in a journal", "reads well" — rather than explicit, observable criteria. In skill authorship: a skill whose DoD is modifier-only ("terse", "production-ready") operates on vibes.

**Positive counterpoint.** AbsenceJudgement.tex:868 names three success conditions for AI-assisted work: `mechanical, bounded, low-judgement tasks` (three adjectives — the paper's compression, not two); `heavy scaffolding`; and `reserving all evaluative and synthetic work for human judgement`. Framed as what the artefact should look like when the four failure patterns are absent: the task is mechanical and bounded and low in required judgement; the skill provides heavy scaffolding (concrete checks, named files, named commands); the skill reserves evaluative and synthetic work for a human reader rather than claiming to perform it.

## On a failing screen

A failed screen routes the artefact to a specific next step, not to a queue:

- **Scope** → re-scope (shrink the mandate) before authoring; a broader skill will not meet a scope it already fails.
- **Observability** → rewrite the offending DoD/AC entries so each names an actor and action or a checked command; do not proceed on artefact-only or modifier-only wording.
- **Process** → stop and engage the question; a Process failure is stamping "coherent" without reflection, so the fix is reflection, not a wording patch.
- **Failure-pattern** → gather the missing evidence (dates, scope bounds, load-bearing citations, explicit criteria), or reject the artefact if the pattern is intrinsic to it.

The rubric screens; it does not decide for you.

## Cross-references

This rubric is invoked from:

- `denubis-extending-claude:writing-skills` (rubric-callback at the scope-check step)
- `denubis-extending-claude:testing-skills-with-subagents` (rubric-callback at the red-phase review)
- `denubis-extending-claude:writing-claude-directives` (rubric-callback at the directive-scope step)

*If any of these cross-references fails to resolve, that is a cross-reference regression to fix in the referring skill.*

## Self-application

The rubric-applied-to-itself walk-through lives in `self-application.md`. That file surfaces the reflective vulnerabilities the walk-through reveals — notably the Observability tautology-screen's recursive bite on the rubric itself. Readers assessing whether this rubric earns its existence should read `self-application.md` before using the rubric on other artefacts.
