---
name: absencejudgement-citations
source: Ballsun-Stanton, B. & Ross, S. A. (2025). "Absence of Judgement: Autoethnographic Investigation of LLM Research Tools." Working paper at `/home/brian/people/Shawn/LLM-History-Paper/AbsenceJudgement.tex`.
audit_date: 2026-04-17
---

This file is the evidence base for the `epistemic-humility` rubric. Every claim in `SKILL.md` traces to a quotation here with line numbers against `AbsenceJudgement.tex`. Latour citations appear in the Observability section of `SKILL.md` because the paper does not discuss Latour; they are named secondary sources, captured in the `## Named secondary sources (not in AbsenceJudgement.tex)` section below rather than mixed in with paper quotations.

## Technoscholasticism

From the paper's theoretical framing in §1 Introduction (AbsenceJudgement.tex:203):

> We propose 'technoscholasticism' as a conceptual framework for understanding these fundamental limitations. By this framework, we mean a digital scholasticism that privileges textual authority over critical assessment of knowledge claims.

Corroborating definition from the Abstract (AbsenceJudgement.tex:177):

> This paper introduces the concept of "technoscholasticism" to analyse fundamental limitations in AI research tools. [...] Like medieval scholastics, these tools privilege textual authority over critical assessment of knowledge claims, explaining their inability to generate novel insights despite vast information access.

Framing note: the rubric's `## Why this skill exists` section in `SKILL.md` treats technoscholasticism as the failure mode the rubric guards against — textual-authority substitution masquerading as evidence. Both quotations above bind the term to the paper's own language; paraphrase drift risks losing the "textual authority over critical assessment" contrast that the rubric leans on.

## Schön's four reflective-practitioner questions

From §2 Theoretical Framework, "Three Dimensions of AI Judgement" (AbsenceJudgement.tex:252-259):

> Schön's conceptualisation of reflective practice provides a framework for understanding what genuine judgement entails. Reflective practitioners continually evaluate their actions and adjust their approaches based on evolving understandings, asking themselves:
>
> > Can I solve the problem I have set?
> > Do I like what I get when I solve this problem?
> > Have I made the situation coherent?
> > Have I kept inquiry moving?
>
> (Schön 1994 p.132, cited at AbsenceJudgement.tex:259.)

Framing note: the paper cites Schön twice at p.132 (lines 259 and 259's continuation describing reflection as `'spiral[ling] through stages of appreciation, action, and reappreciation'`). The rubric's `## Process` section uses the four questions verbatim; they are irreducibly reflective and the rubric treats mechanical yes/no answers to them as a failure mode.

**Full bibliographic entry:**
Schön, Donald A. *The Reflective Practitioner: How Professionals Think in Action*. Taylor & Francis Group (Oxford), 1994. ISBN 978-1-351-88315-3. The four questions appear at p.132, which is also the page the paper cites.

## Jones's scope lever — three conditions

From §5.2.2 Scope/Confabulation Relationship (AbsenceJudgement.tex:794-798), quoting Jones at his source line 163:

> \textcite{jones_i_2025} advises:
>
> > Scope is the only lever you wholly control. When an executive asks for an agent, shrink the mandate until you can prove three things in a sandbox: first, the agent finishes the task 90%+ of the time without rescue; second, the remaining share of failures is bounded, auditable, and reversible; third, every miss surfaces fast enough that a human—not a cron job—decides whether to roll back or roll forward. (line 163)

Framing note: the three conditions are the spine of the rubric's `## Scope` section. The second condition's three adjectives — `bounded, auditable, and reversible` — are load-bearing; the rubric explicitly refuses to compress them to two. The third condition names a human (not a cron job) as the decider; passive-voice or cron-automated escalation breaks Jones's criterion.

**Full bibliographic entry:**
Jones, Nate. "I Summarized Mary Meeker's Incredible 340 Page 2025 AI Trends Deck—Here's Mary's Take, My Response, and What You Can Learn." *Nate's Substack*, June 2025. URL: `https://natesnewsletter.substack.com/p/i-summarized-mary-meekers-incredible`. The three-condition quote appears at line 163 of Jones's own source.

**Source type:** Substack newsletter, not peer-reviewed. The rubric cites Jones because the paper cites Jones; readers evaluating the rubric's evidence grade should weight this entry accordingly.

## Four failure patterns

One quotation per pattern, drawn from §5.2 Cross-Cutting Empirical Patterns.

### Temporality blindness (AbsenceJudgement.tex:785)

> Every system we tested exhibited a fundamental inability to reason about time while working on normal research problems. This temporality blindness manifested not merely as missing dates or failing to check timestamps, but as a complete absence of temporal reasoning capability. [...] They operate in an eternal present where all textual claims exist simultaneously without temporal hierarchy or decay.

Framing note: the paper's term is `temporality blindness` (two words, no hyphen). The rubric's `## Failure-pattern screen` uses it verbatim.

### Scope/confabulation (AbsenceJudgement.tex:789, 792)

§5.2.2 header (AbsenceJudgement.tex:789):

> % ### 5.2.2 Scope/Confabulation Relationship (1 paragraph)

Paragraph content (AbsenceJudgement.tex:792):

> Our testing revealed a consistent relationship between task scope and output quality across all models. Each system performed roughly the same amount of work regardless of the task's actual requirements. When given narrow, bounded tasks, this effort produced high-quality outputs (still requiring validation) with minimal confabulation. When given broader tasks, the same effort became diluted across a wider scope, dramatically increasing confabulation rates. Claude Research demonstrated unusual self-awareness about this limitation, stating it could handle "1 to 3" tools thoroughly but warning that "with 10 tools, you're going to get a shallow summary." Yet even Claude's actual performance failed to match this self-assessment, as quality degraded well before reaching stated limits.

Framing note: the paper uses `scope/confabulation` with a slash, not a hyphen. The rubric respects the punctuation verbatim. The Claude-Research "1 to 3 tools" vs "10 tools" passage is retained here for specificity — it names the concrete behaviour the screen catches.

### Stamp-collecting without evaluation / evidence-accumulating approach (AbsenceJudgement.tex:801, 810)

§5.2.3 header (AbsenceJudgement.tex:801):

> % ### 5.2.3 Stamp-Collecting Without Evaluation (1-2 paragraphs)

Paragraph content (AbsenceJudgement.tex:810):

> This evidence-accumulating approach contrasted with Elicit, which by design separates source discovery from evaluation. Even Elicit's superior architecture failed in execution, however, suggesting that its limitation stems from judgement deficiency rather than architectural constraints. [...] The result across all platforms was what we liken to an undergraduate 'source soup': uncritical aggregation lacking sufficient historiographical awareness to evaluate when claims were made, by whom, for what purpose, and whether such claims are valid and relevant.

Framing note: the paper uses two phrases for this pattern — `stamp-collecting without evaluation` (section header at line 801) and `evidence-accumulating approach` (body text at line 810). The rubric uses the paper's own two phrases; do not paraphrase them (e.g. as "evidence accumulation without evaluation").

### Vibes-based operation / 'vibes' or opaque heuristics (AbsenceJudgement.tex:816, 819)

§5.2.4 header (AbsenceJudgement.tex:816):

> % ### 5.2.4 The "Vibes" Problem (1 paragraph)

Paragraph content (AbsenceJudgement.tex:819):

> A recurring pattern across all systems was their reliance on what can only be described as 'vibes' or opaque heuristics rather than systematic evaluation criteria. This tendencey manifested in multiple ways: Carnapian confirmation proceeded until some internal threshold, quality assessments (if they exist) seemed to rely on heuristics like 'appearing in a journal' rather than on merit-based assessment, while decision thresholds appeared arbitrary rather than principled. The absence of discernable evaluation criteria meant that systems would terminate searches, select sources, and generate conclusions based on opaque internal states rather than observable quality metrics. This vibes-based operation fundamentally distinguishes these tools from genuine agents, which would require explicit success criteria and systematic evaluation methods.

Framing note: the paper uses both `'vibes' or opaque heuristics` (opening of line 819) and `vibes-based operation` (later in the same paragraph). The rubric uses the paper's two phrases verbatim.

## Three success conditions

From §5.4.2 Mundane Utility Patterns (AbsenceJudgement.tex:868), a single paragraph containing all three conditions:

> Despite fundamental limitations, clear patterns of mundane utility emerged from our testing. We observed an inverse relationship: the more judgement a task required, the less utility the tools provided. Utility peaked on mechanical, bounded, low-judgement tasks such as data extraction with heavy scaffolding or initial literature discovery (not literature review composition) for well-defined topics. [...] These patterns suggest that researchers should deploy AI tools for initial aggregation and formatting tasks while reserving all evaluative and synthetic work for human judgement.

Framing note: the paper lists three adjectives — `mechanical, bounded, low-judgement` — not two; the rubric uses all three and does not compress them to "mechanical and bounded". The paper's third noun phrase is `heavy scaffolding`, and the final clause is `reserving all evaluative and synthetic work for human judgement` — the rubric uses the paper's phrase verbatim, not a compression such as "human-reserved synthesis".

## Paper's own §Epistemic Humility subsection

AbsenceJudgement.tex:261 contains the LaTeX `\subsubsection{Epistemic Humility}` that gives the skill its name. Opening sentence of that subsection (AbsenceJudgement.tex:263):

> Epistemic humility, the capacity to recognise and acknowledge the boundaries of one's knowledge, represents a fundamental dimension of judgement.

Load-bearing passage for the rubric's opening memento (AbsenceJudgement.tex:267):

> Even the most advanced LLMs struggle with authentic epistemic humility, regardless of their ability to mimic its linguistic patterns. While these systems can generate qualifiers and hedging language that superficially resembles uncertainty acknowledgement, they lack the metacognitive awareness that grounds genuine epistemic humility.

Framing note: the rubric's opening memento ("Remember thou art AI") cites lines 261 and 267 directly. The paper's argument that LLMs cannot genuinely hold this virtue is the reason the rubric is framed as a *mechanical surrogate* rather than an achievement.

## Named secondary sources (not in AbsenceJudgement.tex)

AbsenceJudgement.tex does not discuss Latour. The following entries support the `## Observability` section's black-box / immutable-mobile framing only; they are not cited from the paper.

**Latour, Bruno.** *Science in Action: How to Follow Scientists and Engineers Through Society*. Harvard University Press, 1987. ISBN 978-0-674-79291-3. Key concepts for the rubric: "black box" (a claim, tool, or finding that readers treat as settled and do not re-open) and "immutable mobile" (an inscription that travels between contexts while preserving its form). *Not in AbsenceJudgement.tex; named secondary source.*

**Latour, Bruno.** *Pandora's Hope: Essays on the Reality of Science Studies*. Harvard University Press, 1999. ISBN 978-0-674-65336-8. Key concept for the rubric: the construction-of-facts argument — facts survive because they can be traced back through a chain of inscriptions any reader can re-walk. *Not in AbsenceJudgement.tex; named secondary source.*

The rubric's Observability section cites Latour to name what the three screens exclude: a claim readers cannot re-walk is a closed box that rests on authority-by-form alone. This framing is ours, not the paper's.

## Verified absences

These absences bound what the rubric may and may not claim to draw from the paper.

- **Haraway** — zero hits in AbsenceJudgement.tex (exhaustive word-boundary grep, 2026-04-17). The rubric does not cite Haraway.
- **Popper** — one parenthetical mention at AbsenceJudgement.tex:829 ("falsifable statements (Popper)"), NOT a substantive discussion. The rubric does not draw from Popper via the paper.
- **Lakatos** — the same parenthetical mention at AbsenceJudgement.tex:829 ("context-increasing research programmes (Lakatos)"), NOT a substantive discussion. The rubric does not draw from Lakatos via the paper.
- **Prolepsis** — zero hits in AbsenceJudgement.tex. The Kudina/Ballsun-Stanton/Alfano 2025 paper is cited once at AbsenceJudgement.tex:905 but not for its prolepsis content; the rubric does not cite prolepsis as a paper concept.

Why this list matters: the rubric's credibility depends on its citations being verifiable. An absent-but-asserted source is the same failure mode as technoscholasticism — substituting the form of a citation for the fact of one.
