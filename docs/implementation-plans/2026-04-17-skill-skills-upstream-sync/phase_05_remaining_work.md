# Phase 5 — remaining work

Written 2026-07-26, when the `skill-skills-upstream-sync` worktree folded. It carries forward
the live parts of that worktree's `RESUME-2026-07-25.md`, which was untracked and would have
been destroyed with the worktree. Everything that file recorded as pending is reproduced here;
the parts it recorded as next actions are done and are dropped.

Phases 1 to 4 and 6 are closed. Releases 1.9.1 and 2.36.1 shipped and merged. The branch merged
to main at `58e4dd5` on 2026-07-26, so Phase 5 no longer has a worktree of its own and resumes
from wherever is convenient.

## Where the Fable pass stopped

The whole-file fitness pass reached **skill 4 of 5**. Skill 5, `impl-plan-write`, is not started,
and its fixes route to the `impl-plan-decision-discipline` branch rather than to this plan.
That branch carries its own reconciliation problem, recorded in its `RESUME-2026-07-25.md` and
in `CODEX-CRITIQUE-2026-07-26-impl-plan-decision-discipline.md`, so read those before touching
`impl-plan-write`.

## Open items

| item | state |
|---|---|
| **Four open skill-4 findings** | #2 is the substantive one, a RED-run coherence question against the independence gate. #3 is the TaskCreate preamble on three checklists. #6 differentiates a near-duplicate example. #7 is the "the skill is always the problem" hyperbole, to be decided together with the parked `systematic-debugging` one. Dispositions in `phase_05_fable_skill4_findings.md`. |
| **Codex synthesis** | Five reviews were deliberately quarantined out of context to preserve independence from the Fable pass, and they are still unread. They now live in `codex-reviews/` beside this file, having been rescued from the folding worktree's gitignored `.review/`. Weigh them against the Fable findings once all five reviews land. Their filenames say only `SKILL.md`, so which skill each covers is unknown until someone opens them, which nobody has done by design. |
| **AC5.8 frustration audit** | `phase_05_frustration_audit.md` does not exist. It wants a joint pass with the operator, and it should record the fabricated-taxonomy deletion as a deviation. |
| **Finalization ADRs** | M2 and M6 are unwritten, the `constraints.md` row for the E1 to E12 protocol is missing, and the Stage-2 ADR is still Proposed rather than Accepted. Only ADRs 0001 to 0003 exist. |
| **Enforcement over prose** | The round-2 RED showed the description lever exhausted for unreinforced subagents. This is a separate design task, and it converges with `docs/audits/2026-07-02-skill-engagement-audit.md`. |

## Settled, do not relitigate

- **The Haiku judgement claim is strengthened, not retired.** The original plan proposed retiring
  it in Phase 2 (`model-tier-notes.md`) and Phase 3 (`testing-skills-with-subagents`). Operator
  rulings on 2026-07-25 and 2026-07-26 settled it in the opposite direction, and Sonnet is now
  the floor across the suite. The current contract and authority records live in
  `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md`.
- **Jones is settled.** The source-type grade lives in `absencejudgement-citations.md`.
- **Codex won't-fixes** are recorded in `RESUME-PROMPT-fable-skill4.md`. Do not reopen one
  without genuinely new evidence.

## Recovering context

The 2026-07-25 session is `28ff5c79-c20e-4039-bd82-c4ed1478bce3`. Earlier sessions for this
plan, newest first: `20d4ed87` (07-08 to 07-21), `e7c507e7` (07-11), `ddbd0c01` (07-10),
`06fcb04f`, `a73d7f7e`, `e333a58e` (07-09), `f5cb34f0` (07-08), `7be009f1` (07-07), `93611223`
(07-06). The worktree-folding session is 2026-07-26.

```bash
cc-search-chats extract 28ff5c79-c20e-4039-bd82-c4ed1478bce3 --json
cc-search-chats search "<phrase>" --all --json
```
