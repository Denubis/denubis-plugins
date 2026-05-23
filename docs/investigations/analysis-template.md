# Causal Analysis: [brief description]

**Date:** YYYY-MM-DD
**Investigator:** Claude ([model id, e.g. claude-opus-4-7])
**Project:** [path / branch / worktree]
**Status:** In progress / Awaiting peer review / Reviewed

> **Peer-review contract:** This file must be readable by a fresh LLM (any vendor) or human reviewer with NO context from the conversation that produced it. Every claim is defended in the Toulmin table below. Every citation resolves to a file path + line number or a timestamp + JSONL line in this repo. No "as we discussed", no "per the prior session". If a statement cannot be defended in the Claim Verification table, it does not appear in the Summary or Causal Chain. Use graded language only: never "confirmed", never "root cause found".

## Summary

[2-3 sentences. Graded language only. State the leading hypothesis with its evidence grade. Name the next experiment that would upgrade or falsify.]

## Differential Baseline

- **Reference branch / state:** [e.g. `main` at commit abc123, or `pre-2026-05-21` for behavioural baselines]
- **Current branch / state:** [e.g. `approver-rtk` at HEAD]
- **What changed:** [files / config / behaviour]
- **Evidence universe:** [the diff or specification contradiction that grounds every claim below]

If the bug exists on the reference branch too, state this and cite the specification or test that defines expected behaviour instead.

## Causal Chain

[Narrative. Multiple contributing factors, not a single "root cause". Every factual claim references the Claim Verification table by `[Cn]` and includes a file:line or timestamp citation inline.]

Example shape:
> 1. `[C1]` Event X happened at `path/to/file.jsonl:N` at timestamp Y.
> 2. `[C2]` This triggered behaviour Z because of mechanism M (see `module.py:line`).
> 3. `[C3]` The model then produced N instead of expected M.
> 4. ...

## Evidence Grading

| # | Finding | Grade | Positive border | Negative border | Upgrade path |
|---|---------|-------|----------------|-----------------|--------------|
| 1 | [finding text] | Demonstrated / Plausible / Possible / Speculative | [test that showed it triggers] | [test that showed removing it prevents it; "not yet tested" if missing] | [specific next test to upgrade grade] |
| 2 | … | … | … | … | … |

**Grade definitions:**
- **Demonstrated:** Mechanism triggers failure AND removing it prevents failure, both tested on actual production code path. BOTH borders required.
- **Plausible:** One border shown, OR shown in production-like conditions but not production.
- **Possible:** Mechanism triggers failure in synthetic test only. Production path unconfirmed.
- **Speculative:** Hypothesis among several; untested.

## Claim Verification (Toulmin)

| # | Claim | Data | Warrant | Qualifier | Rebuttal |
|---|-------|------|---------|-----------|----------|
| C1 | [the assertion] | [diff line, JSONL line, log entry — narrow & specific] | [why the data supports the claim] | [evidence grade] | [what would make this claim false] |
| C2 | … | … | … | … | … |

**Rules for this table:**
- One row per atomic assertion. If a sentence contains two facts, split into two rows.
- Data must cite a specific file path + line, JSONL line in a specific session file, log entry, or quoted spec passage. Never "see somewhere".
- For "demonstrated" grade, both borders must be in the table — typically as adjacent rows.
- Falsified claims stay in the table with the qualifier "FALSIFIED — see rebuttal" so the audit trail is preserved.

## Epistemic Boundary

- **Demonstrated:** [findings with both borders on production path]
- **Plausible:** [findings with partial evidence — state what's missing]
- **Possible:** [findings from synthetic tests only — state what would lift to plausible]
- **Speculative:** [hypotheses generated but not tested]
- **Not tested:** [borders we did not exercise; alternative hypotheses we did not rule out]
- **Corrected:** [what was previously believed and was found to be wrong; preserves the audit trail]

## Primary Data References

Cite all primary data so a reviewer can verify independently without re-running anything:

- **Session JSONLs:** `~/.claude/projects/<project-dir>/<session-uuid>.jsonl:<lineno>` for each turn cited
- **Approver logs:** `~/.claude/approver/projects/<slug>/log/<YYYY-MM-DD>.jsonl:<lineno>` for hook decisions
- **Tool excerpts:** drop large outputs into `data/<name>.txt` (relative to this file) and cite by path

The `data/` subdirectory in this folder is for raw evidence excerpts — anything that would clutter the analysis but a reviewer might want to read.

## Peer Review

[Empty until reviewed. External reviewer (different model, or human) writes findings here.]

### Reviewer 1 — [model / name] — [date]

**Findings:**
- [severity: High / Medium / Low] [finding] → [resolution / acknowledgement]

**Verification performed:**
- [what the reviewer checked independently]

**Assessment:** Ready to ship / Needs revision / Reject

### Reviewer 2 — …

## Status & Hand-off

- **Open questions:** [what's still unresolved]
- **Next experiment:** [the specific falsifiable test that would advance the leading hypothesis]
- **Hand-off to next investigator:** [exact first action if this analysis is paused]
