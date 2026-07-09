# Model-Tier Notes — Supersession Log

Dated record of claims in [`model-tier-notes.md`](model-tier-notes.md) that were later dissolved, corrected, or re-sourced. The main file carries current facts only; an entry lands here so a stale claim resurfacing from memory or an old note can be checked against when and why it died. Newest first.

## 2026-07-02 — Advisor-pairing doc conflict dissolved

The 2026-06-11 conflict between the platform API compatibility table and the Claude Code advisor docs, over whether Fable 5 may advise lesser mains, dissolved by upstream convergence: the platform table now lists Fable 5 and Mythos 5 as accepted advisors for Haiku 4.5, Sonnet 4.6, Sonnet 5, and all Opus 4.6+ executors, matching the Claude Code docs it previously contradicted. A new discrepancy (the Sonnet 5 advisor rows) replaced it and is recorded live in the main file.

## 2026-07-02 — Advisor scope correction: subagents inherit the advisor

Supersedes the 2026-06-11/12 "main-loop only" claim. Claude Code's advisor docs state that subagents inherit the configured advisor and apply the same pairing check against their own model; the earlier claim that a subagent runs with no advisor no longer holds.

## 2026-07-02 — Task-budgets citation re-sourced

The task-budgets bullet now cites the dedicated task-budgets page. The earlier citation pointed to the Opus 4.8 prompting page, which does not cover task budgets.
