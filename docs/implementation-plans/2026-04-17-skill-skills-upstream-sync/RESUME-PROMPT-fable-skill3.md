# RESUME PROMPT — Fable pass, skill 3 of 5 (writing-skills) + epistemic-humility trigger test

**Branch:** `skill-skills-upstream-sync`
**Worktree:** `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync`
**Written:** 2026-07-09, end of the skills-1-and-2 session.

## Where things stand

Phase 5 (terminal). The codex review-and-fix cycle was already done at session start.
The Fable pass is now running **in the main session, not via review subagents** —
operator override of the earlier plan. Two of five skills are reviewed, discussed
finding-by-finding with the operator, fixed, and committed:

- `333ccb8` fix(writing-claude-directives): scrub plan-vocab, move supersession history to log, cite overengineering template
- `bca222e` feat(epistemic-humility): add announce-and-temper gate for results presentation, delete fabricated-taxonomy scar

Working tree clean except the parked untracked audits and resume prompts.

## Session decisions that now bind (operator-ruled, 2026-07-09)

- **Main-session review.** The operator wants *you* to run the reviews. Subagents are
  for the trigger test below, not for the review judgement.
- **One skill at a time; one finding at a time; halt-and-discuss; commit per skill**
  via the `denubis-git-commit:commit` skill.
- **epistemic-humility is rescoped.** It now gates anything that presents results or
  conclusions (chat summaries, reports, audits, any markdown artefact) and requires
  the announcement "I'm using the epistemic-humility skill to temper my language."
  Apply it yourself when presenting findings.
- **Jones is settled.** The project cites Jones because the paper does. Do not
  relitigate, do not re-add hedging parentheticals in SKILL.md (the source-type grade
  lives in `absencejudgement-citations.md`).
- **Scar-tissue precedents:** plan-vocabulary (Phase/AC/DR/H-codes, `docs/` plan
  paths) in shipped skill files is a defect — scrub on sight. "Prior session" /
  "prior design drafts" narrative framing is scar; keep the guard, drop the history.
  Supersession narratives move to a sibling log file
  (`writing-claude-directives/model-tier-notes-log.md` is the precedent).
- **Worktree copies are authoritative.** The installed plugin cache
  (`~/.claude/plugins/cache/denubis-plugins/...`) is stale relative to this branch.
  Read skills from the worktree; inject worktree SKILL.md content into any subagent
  that needs an edited skill.

## FIRST ACTION — subagent report on skill 3, doubling as the trigger pressure-test

`bca222e` changed epistemic-humility's description and added the announce-and-temper
rule, but should-fire behaviour is **untested**. The operator authorised (2026-07-09)
a subagent run that does real work and tests the trigger at once:

Dispatch one subagent to produce the skill-3 review report on
`plugins/denubis-extending-claude/skills/writing-skills/` (files: SKILL.md,
anthropic-best-practices.md (obra-vendored), render-graphs.js, README.md,
examples/CLAUDE_MD_TESTING.md). Confirm the model tier with the operator at dispatch
(cost gate: Fable subagents are human-triggered only; the trigger test itself does
not require Fable). In the prompt:

- Inject the **worktree** `epistemic-humility/SKILL.md` verbatim as an available
  skill, alongside whatever skills the subagent normally sees. Do not tell it to
  temper; the test is whether it announces and tempers unprompted when presenting
  its report conclusions.
- Ask for the review on the four axes (below), structured findings: severity +
  `file:line` + verbatim quote + why + suggested fix.
- Have it read the branch diff (`git diff main...HEAD -- <skill dir>`) for axis 2.

Record the trigger outcome either way — announcement present/absent, language
tempered or not — as the RED/GREEN evidence for the rescope. If it does not fire,
that is a finding about the description, not a reason to prompt harder (trigger
explicitness, not emphasis, is the lever — see writing-claude-directives).

Then review the subagent's report yourself: verify quotes
(`grep -nF '<quote>' <file>`), weigh severities (lead with whether a finding is a
REAL problem), and discuss with the operator one finding at a time.

## The four review axes

1. Does the skill do its job in its plugin?
2. Did the branch's changes make it more effective?
3. Does it follow the project's own skill-authoring protocols (writing-skills
   orchestration, writing-claude-directives phrasing, testing-skills
   pressure-testing, epistemic-humility rubric)?
4. Scar tissue: does the skill argue with its own past selves — change-log residue,
   relitigated decisions, hedges against superseded versions? A skill presents the
   world we care about; history lives in git.

## After skill 3

- **Skill 4:** `testing-skills-with-subagents/SKILL.md` — same axes, main-session review.
- **Skill 5:** `impl-plan-write/SKILL.md` (denubis-plan-and-execute) — review it, but
  deliver any fixes as a note into the `impl-plan-decision-discipline` worktree; no
  impl-plan-write fixes on this branch.
- **Codex synthesis (still owed):** the codex reviews at
  `.review/SKILL.md.20260708-15*.REVIEW.md` have deliberately NOT been compared
  against the Fable findings yet (kept out of context to preserve independence).
  After all five reviews, do the synthesis pass: weigh Fable findings against codex's
  findings and won't-fixes; check nothing codex caught was lost.

## Codex won't-fixes — do NOT re-open without genuinely new evidence

- model-tier behavioural "current models" claims (freshness test is version-strings-only by design)
- "usually" softeners (testing:36, WCD rubric-callback tail)
- writing-skills checklist vs Anthropic's 3-evals/model-matrix (deliberate denubis method)
- epistemic-humility scope-vs-examples (the four screens are general; the example is
  illustrative — note: the 2026-07-09 rescope changed "When to invoke", so if new
  evidence appears it comes from the new scope, not the old argument)

## Remaining Phase 5 after the reviews

1. **Package:** bump versions (denubis-extending-claude, denubis-plan-and-execute) +
   CHANGELOG.md + marketplace.json. **Read current versions from each
   `.claude-plugin/plugin.json`** — prior notes carried stale numbers. The
   epistemic-humility description change in `bca222e` is user-facing — it needs a
   CHANGELOG entry. Coordinate the denubis-plan-and-execute bump with the
   `impl-plan-decision-discipline` worktree.
2. **Frustration audit (AC5.8)** — joint pass with the operator. Note: deleting the
   fabricated-taxonomy section may deviate from a literal test-requirements.md
   expectation; operator ruling (2026-07-09) supersedes — flag it in the audit.
3. **Finalization ADRs (M2/M6).**

## Also open

- Parked untracked: `docs/audits/2026-07-02-*.md` (skill-engagement-audit awaits the
  operator's read — its verdict, that enforcement not prose moves compliance, is
  directly relevant to making the new announce-and-temper rule enforceable, e.g. a
  hook that greps for the announcement; that is a separate design task).
- `systematic-debugging` hyperbole — operator to decide whether to hedge.
- Small plan-and-execute deltas ride along in context — no dedicated review runs.

## Guardrails

- Commits on this branch only, never on main. Don't push without explicit approval.
- Don't `git worktree remove` this worktree from inside it.
