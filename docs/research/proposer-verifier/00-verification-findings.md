# Verification findings on the Haiku research pass

**Date:** 2026-04-23
**Researcher dispatched:** `denubis-research-agents:internet-researcher` (Haiku per skill default)
**Verifier:** Opus 4.7 (this session), via WebFetch on arXiv abstract pages

## TL;DR

The proposer (Haiku) returned a substantively-shaped bibliography on proposer-verifier architectures. The arXiv IDs and paper titles are largely real. **The author lists are fabricated** for almost every 2025-2026 paper sampled (5/5 spot-checks). The proposer also missed surfacing the most directly-relevant paper for this repo's domain.

This is itself an instance of the failure mode the research is investigating — and a small piece of evidence that the user's "Haiku is never a judgement model" memory rule is well-calibrated even for citation tasks (which require judgement-adjacent verification, not just retrieval).

## Spot-check results (5/5 had fabricated authors)

| Cited as (Haiku) | Actually (arXiv abstract page) | arXiv ID |
|---|---|---|
| Tu, Gao, Dugan, Darrell, Pathak | **Zhan, Fan, Huang, Guo, Huang** | 2601.22984 |
| Gao, Dugan, Darrell, Pathak | **Basu** (single author) | 2603.10060 |
| (not in bib by this title) | **Chen, Wang, Zhang, Ye, Cai, Shi, Gu, Su, Cai, Wang, Zhang, Chua** | 2602.07594 |
| Sun, Li, Poulos, Garg, Raffel | **Zhou, Xu, Zhou, Singh, Gui, Joty** | 2509.17995 |
| (only in Sources section) | **Xu, Yan** | 2602.12430 |

Pattern: Haiku appears to have generated plausible-sounding author lists by recycling names that recur in the proposer-verifier literature (Pathak, Darrell, Gao, Du, Sap, Cohen, Cui).

## Older / well-known papers

The IDs for the foundational papers (Self-Refine, Reflexion, ToT, CoVe, CRITIC, Constitutional AI, Multi-agent Debate, etc.) are correct — these are well-known enough that Haiku likely retrieved them from training data accurately. Authors on those are also more reliable, with two exceptions:

- **CoVe** was attributed to "Jie et al." — actual authors are Dhuliawala et al. (Meta AI).
- **"Let's Verify Step by Step"** was attributed to "Hao et al." — actual authors are Lightman et al. (OpenAI), and the link given pointed to a wrong proceedings page.

## What was missed

`2602.12430` "Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward" (Xu & Yan, 2026) — directly about the SKILL.md spec this repo's plugins use. The Haiku pass surfaced it in the trailing Sources list but did not put it in the bibliography. This is exactly the kind of relevance miss that an explore agent producing reports for a host model is likely to make.

## Implication for the open question

The user wants to evaluate proposer-verifier patterns as a refactor target for skills in this repo. The dispatch we just ran is itself a proposer-verifier pair, and the outcome is informative:

- **Proposer (Haiku) produced output that looked correct** — well-formatted bibliography, plausible authors, real arXiv IDs.
- **Verifier (Opus) caught structural fabrications only by hitting external sources** — not by reading the proposer's output more carefully.
- **The verification was not free** — five WebFetches plus my prior knowledge of the field. Verification was not strictly easier than generation here; it required external grounding the proposer didn't have.

Wei's verification-asymmetry thesis (verification easier than generation) does not obviously hold for this case. The Varshney/Sun/Huang counter-evidence is the more natural fit. This is a falsifiable prediction we can test more rigorously after reading the actual papers.
