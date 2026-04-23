# Resume — proposer-verifier research

**Branch:** `research/proposer-verifier` (worktree at `.worktrees/research-proposer-verifier`)
**Paused:** 2026-04-23
**Phase:** corpus assembled, read phase not yet started

## State at pause

- 30 PDFs + 4 HTML pieces in `docs/papers/` (gitignored, 71MB, see `fetch-log.txt`).
- Bibliography rebuild required from primary sources — Haiku's author lists are not trustworthy (see `00-verification-findings.md`).
- Hop-1 only is the agreed snowball scope. Hop-2 decision deferred until cross-citation map exists.
- One open meta-question on the table: do we adopt **harness-engineering** vocabulary (Fowler/Anthropic/LangChain) instead of **proposer-verifier** vocabulary (LLM literature) for the eventual skill refactor? See manifest's "Tier F" note.

## First action on resume

Read the **four load-bearing counter-evidence papers first**, in this order, writing per-paper notes (`docs/papers/<author-year-slug>.md`) per the academic protocol:

1. `huang-2023-cannot-self-correct.pdf` — does the asymmetry thesis survive at all?
2. `stechly-2024-self-verification-limits.pdf` — Kambhampati group, planning-domain evidence
3. `zhou-2025-variation-in-verification.pdf` — most recent systematic study
4. `zhan-2026-deep-research-fails.pdf` — closest match to the user's symptom (agent-returned BS findings)

Only after those four, read the **proposer side of the argument** (Self-Refine, Reflexion, CoVe, Wei blog) so we read the critique cleanly before being primed by the optimistic frame.

Then the **practitioner pieces** (Anthropic Effective Harnesses, LangChain Anatomy, Fowler Harness Engineering, Mason AI Slop, Xu 2026 Agent Skills survey).

## Suggested resume prompt

> Resume the proposer-verifier research from `.worktrees/research-proposer-verifier`. Read `docs/research/proposer-verifier/RESUME.md` for context. Begin with the four counter-evidence papers in the order specified, writing per-paper notes per the academic-research-protocol format. Stop after each paper to discuss before moving to the next.

## Watch-outs for next session

- **Don't dispatch Haiku for any judgement task** — the current corpus exists because Haiku fabricated author lists. Use Opus or Sonnet for reading; reserve Haiku for pure retrieval.
- **Don't accept "the agent said the paper says X"** without checking — read the PDF, quote with page numbers.
- **Don't over-batch fixes if the read surfaces a problem** — work findings one by one (project HALT-when-sideways norm).
- **Don't bump any plugin versions** — no implementation work yet, no version bumps until a refactor is verified working.
