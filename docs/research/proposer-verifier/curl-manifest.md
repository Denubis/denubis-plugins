# Proposer-Verifier Bibliography — curl manifest

Generated 2026-04-23 from Haiku internet-researcher output, with arXiv IDs spot-verified by Opus, augmented by harness-engineering grey literature surfaced via Fowler.

**Status of underlying data:** arXiv IDs are real and resolve. Author lists from the Haiku pass were fabricated for almost every 2025-2026 paper checked (5/5 spot-checks had wrong authors). **Treat this manifest as a leads list of arXiv URLs only** — rebuild the bibliography from the PDFs themselves once fetched.

**Scope decision (2026-04-23):** Hop-1 only for now. Read first-generation papers, identify which cites recur across roots and which contradict each other, then make an informed decision about hop-2 with real signal. No depth-3 BFS up front.

Run from the worktree root. Files land in `docs/papers/` (gitignored).

---

## Tier A — Foundational (well-known IDs, high confidence)

```bash
mkdir -p docs/papers
cd docs/papers

# Chain-of-Thought (Wei et al. 2022)
curl -L -o wei-2022-cot.pdf "https://arxiv.org/pdf/2201.11903"

# Self-Consistency (Wang et al. 2023)
curl -L -o wang-2023-self-consistency.pdf "https://arxiv.org/pdf/2203.11171"

# Self-Refine (Madaan et al. 2023)
curl -L -o madaan-2023-self-refine.pdf "https://arxiv.org/pdf/2303.17651"

# Reflexion (Shinn et al. 2023)
curl -L -o shinn-2023-reflexion.pdf "https://arxiv.org/pdf/2303.11366"

# Self-Verification (Weng et al. 2023)
curl -L -o weng-2023-self-verification.pdf "https://arxiv.org/pdf/2212.09561"

# Chain-of-Verification / CoVe (Dhuliawala et al. 2023 — Haiku cited as "Jie et al."; real authors per Meta AI)
curl -L -o dhuliawala-2023-cove.pdf "https://arxiv.org/pdf/2309.11495"

# CRITIC (Gou et al. 2023)
curl -L -o gou-2023-critic.pdf "https://arxiv.org/pdf/2305.11738"

# Tree of Thoughts (Yao et al. 2023)
curl -L -o yao-2023-tot.pdf "https://arxiv.org/pdf/2305.10601"

# LLM-as-a-Judge / MT-Bench (Zheng et al. 2023)
curl -L -o zheng-2023-llm-as-judge.pdf "https://arxiv.org/pdf/2306.05685"

# AI Safety via Debate (Irving et al. 2018)
curl -L -o irving-2018-debate.pdf "https://arxiv.org/pdf/1805.00899"

# Multi-Agent Debate (Liang et al. 2023, EMNLP 2024)
curl -L -o liang-2023-mad.pdf "https://arxiv.org/pdf/2305.19118"

# Multi-agent debate for factuality (Du et al. 2023, ICLR 2024 — Haiku had wrong co-authors)
curl -L -o du-2023-multiagent-debate.pdf "https://arxiv.org/pdf/2305.14325"

# Constitutional AI (Bai et al. 2022)
curl -L -o bai-2022-constitutional-ai.pdf "https://arxiv.org/pdf/2212.08073"

# Theory of Mind for Multi-Agent Collaboration (Sap et al. 2023)
curl -L -o sap-2023-theory-of-mind.pdf "https://arxiv.org/pdf/2310.10701"

# Let's Verify Step by Step (Lightman et al. 2023 — Haiku cited as "Hao et al." with wrong link)
curl -L -o lightman-2023-verify-step-by-step.pdf "https://arxiv.org/pdf/2305.20050"
```

---

## Tier B — Counter-evidence / verifier-limitations (high relevance, real IDs)

These are the load-bearing critique papers. **Authors below were spot-verified against arXiv where noted; otherwise assume Haiku's authorship is suspect and confirm from the PDF metadata.**

```bash
# LLMs Cannot Self-Correct Reasoning Yet (Huang et al. 2023, ICLR 2024)
curl -L -o huang-2023-cannot-self-correct.pdf "https://arxiv.org/pdf/2310.01798"

# Self-Verification Limitations on Reasoning and Planning (Stechly, Marquez, Kambhampati 2024
# — Haiku attributed to "Du et al."; real authors are Kambhampati's group at ASU. CONFIRM from PDF.)
curl -L -o stechly-2024-self-verification-limits.pdf "https://arxiv.org/pdf/2402.08115"

# Variation in Verification (Zhou, Xu, Zhou, Singh, Gui, Joty 2025, ICLR 2026 — VERIFIED)
curl -L -o zhou-2025-variation-in-verification.pdf "https://arxiv.org/pdf/2509.17995"

# Why Your Deep Research Agent Fails (Zhan, Fan, Huang, Guo, Huang 2026 — VERIFIED)
curl -L -o zhan-2026-deep-research-fails.pdf "https://arxiv.org/pdf/2601.22984"

# Tool Receipts, Not ZK Proofs (Basu 2026 — VERIFIED single author; uses Nyaya Shastra epistemics)
curl -L -o basu-2026-tool-receipts.pdf "https://arxiv.org/pdf/2603.10060"
```

---

## Tier C — Test-time scaling, generative verifiers, PRMs (real IDs, authors unverified)

```bash
# Scaling LLM Test-Time Compute Optimally (Snell, Lee, Xu, Kumar 2024
# — Haiku cited as "Huang et al."; real authors are Snell et al., Google DeepMind)
curl -L -o snell-2024-test-time-scaling.pdf "https://arxiv.org/pdf/2408.03314"

# Generative Verifiers (Zhang et al. 2024 — verify from PDF)
curl -L -o zhang-2024-generative-verifiers.pdf "https://arxiv.org/pdf/2408.15240"

# Self-Certainty Best-of-N (verify authors from PDF)
curl -L -o snell-2025-self-certainty.pdf "https://arxiv.org/pdf/2502.18581"

# Learning to Self-Verify (Chen et al. 2026, Y. Chen first author — VERIFIED)
curl -L -o chen-2026-learning-to-self-verify.pdf "https://arxiv.org/pdf/2602.07594"
```

---

## Tier D — Calibration / overconfidence (real IDs, authors unverified)

```bash
# Mind the Confidence Gap (verify from PDF)
curl -L -o tian-2025-confidence-gap.pdf "https://arxiv.org/pdf/2502.11028"

# Overconfidence in LLM-as-a-Judge (verify from PDF)
curl -L -o ghai-2025-overconfidence-judge.pdf "https://arxiv.org/pdf/2508.06225"
```

---

## Tier E — Surveys & directly-relevant-to-this-repo (added by verifier)

```bash
# Agent Skills for LLMs: Architecture, Acquisition, Security (Xu, Yan 2026 — VERIFIED)
# DIRECTLY about the SKILL.md spec this repo uses. Haiku surfaced it but missed its centrality.
curl -L -o xu-2026-agent-skills-survey.pdf "https://arxiv.org/pdf/2602.12430"

# Mitigating Hallucinations: RAG, Reasoning, Agentic Systems (Prabhumoye et al. 2025? — verify)
curl -L -o prabhumoye-2025-hallucination-survey.pdf "https://arxiv.org/pdf/2510.24476"

# LLM-based Agents Suffer from Hallucinations: A Survey (Zhang et al. 2025 — verify)
curl -L -o zhang-2025-agent-hallucination-survey.pdf "https://arxiv.org/pdf/2509.18970"
```

---

## Tier F — Harness engineering grey literature (HTML, not PDF)

Cited by Fowler/Birgitta in [Harness Engineering](https://martinfowler.com/articles/harness-engineering.html). Not academic, but directly on our question — and the Anthropic piece explicitly describes the long-running-agent failure mode the user is investigating.

```bash
mkdir -p docs/papers
cd docs/papers

# Anthropic — Effective Harnesses for Long-Running Agents
# Notes Opus 4.5 in a loop "will fall short" without harness — directly cognate to user's 4.7 issue
curl -sL -A "Mozilla/5.0" -o anthropic-2025-effective-harnesses.html \
  "https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents"

# LangChain — Anatomy of an Agent Harness (Mar 2026)
# Explicitly names "self-verification" as harness feature; Top 30 → Top 5 on Terminal Bench 2.0 by harness change alone
curl -sL -A "Mozilla/5.0" -o langchain-2026-agent-harness.html \
  "https://blog.langchain.com/the-anatomy-of-an-agent-harness/"

# Fowler / Birgitta — Harness Engineering (2026)
# Cybernetic framing: guides vs sensors, computational vs inferential controls
curl -sL -A "Mozilla/5.0" -o fowler-2026-harness-engineering.html \
  "https://martinfowler.com/articles/harness-engineering.html"

# Fowler fragment 2026-04-21 — Tech Radar 34, "permission hungry" agents
curl -sL -A "Mozilla/5.0" -o fowler-2026-04-21-fragment.html \
  "https://martinfowler.com/fragments/2026-04-21.html"

# Mason — AI Slop Code April 2026 (ALREADY SAVED to docs/papers/mason-2026-ai-slop-code.html)
# Quote: "You don't get to know which is which without reading the code."

# Bonus arXiv: Natural-Language Agent Harnesses (surfaced incidentally — verify before reading)
curl -L -o natural-language-agent-harnesses-2026.pdf "https://arxiv.org/pdf/2603.25723"
```

---

## Skipped from Haiku output

- **Jason Wei blog post on verifier asymmetry** — useful framing but not academic; cite with caution.
- **Sebastian Raschka's "State of RL for LLM Reasoning" magazine post** — survey blog, not primary.
- **Math-Shepherd (cited as "Ong et al.")** — real paper is Wang et al. 2024; not core to our question.
- **Hao 2024 "Let's Verify Step by Step"** — fabricated author attribution (real: Lightman et al. 2023, included in Tier A).
- **Brown-Cohen 2023 "Scalable Debate"** — real paper but adjacent; can add later if relevant.
- **Kumar 2025 "Scaling Laws for Precision"** — real paper but tangential to verification asymmetry.
- **Ji 2024 "Rewarding Progress" (PRMs)** — covered by Tier C generative-verifier work.
- **Gao 2024 "RL from Verifiable Rewards"** — RL training, not architectural verifier-agent design.

---

## After fetch (hop-1 plan)

Once PDFs and HTML are in place:

1. **Read full primary sources** (not abstracts) starting with the load-bearing few:
   - **Counter-evidence first** — Huang 2023 (Cannot Self-Correct), Stechly 2024 (Self-Verification Limits), Zhou 2025 (Variation in Verification). If the asymmetry is contested, that's the most important finding.
   - **Anthropic Effective Harnesses + LangChain Anatomy** — current practitioner consensus on what works.
   - **Zhan 2026 (DeepHalluBench)** — closest match to user's "agent returns BS findings" symptom.
   - **Xu 2026 (Agent Skills survey)** — directly about SKILL.md, the spec this repo uses.
   - **Wei blog + Self-Refine + Reflexion** — the proposer-verifier thesis on its own terms.
   - **Fowler harness pieces + Mason** — practitioner-grade context.
2. **Per-paper notes** in `docs/papers/<author-year-slug>.md` per the academic protocol — DOI/arXiv URL, summary, key claims, relevance, limitations, page-numbered quotes.
3. **Cross-citation map** — note which references recur across multiple hop-1 papers, which papers cite each other, which directly contradict each other. This is the input to the hop-2 decision.
4. **`critical-peer-review`** skill on the proposer-verifier asymmetry thesis itself, treating Wei as the primary claim to falsify against the counter-evidence corpus.
5. **Hop-2 decision point** — informed by the cross-citation map, decide whether to follow another generation of cites and which.
6. **Only then** circle back to the codebase: which skills/agents in this repo make verification asymmetry assumptions, and which don't.
