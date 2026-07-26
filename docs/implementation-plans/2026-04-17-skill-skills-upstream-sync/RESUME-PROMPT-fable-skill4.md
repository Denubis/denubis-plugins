# RESUME PROMPT — Fable pass, skill 4 of 5 (testing-skills-with-subagents)

**Branch:** `skill-skills-upstream-sync`
**Worktree:** `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync`
**Written:** 2026-07-10, end of the skill-3 session.

## Where things stand

Phase 5 (terminal). Three of five skills are reviewed, discussed
finding-by-finding with the operator, fixed, and committed. Skill 3
(writing-skills) closed this session: five findings fixed, one won't-fixed —
dispositions and commit hashes in `phase_05_fable_skill3_findings.md`.

Big state change this session: **the plugins were released and installed.**
denubis-extending-claude 1.9.0 and denubis-plan-and-execute 2.36.0 are on main
(merge commit `4fa47f1`, pushed) and in the installed cache. The trigger test
then ran validly: **round-2 RED recorded** in
`phase_05_announce_trigger_red_evidence.md` — description in the routing
position, skill text read as data, Skill tool never invoked, no announcement.

The skill-3 fix commits (`24b9d1b`..`32cf0fe`) are **branch-only and
unpushed**; main still holds the 1.9.0/2.36.0 content. They ride a later
1.9.1/2.36.1 bump-and-merge once the remaining reviews land.

Working tree clean except the parked untracked audits and resume prompts.

## Session decisions that now bind (operator-ruled)

Carried forward from skills 1–3:

- **Main-session review.** You run the reviews; subagents were for the trigger
  test only, which is now concluded.
- **One skill at a time; one finding at a time; halt-and-discuss; commit per
  skill** via the `denubis-git-commit:commit` skill.
- **Jones is settled.** Do not relitigate; the source-type grade lives in
  `absencejudgement-citations.md`.
- **Scar-tissue precedents:** plan-vocabulary in shipped skills is a defect;
  "prior session"/consolidation narration is scar; supersession history moves
  to a sibling log; promissory "queued to replace" intent moves to
  `docs/issues.md` **with its state** (ISSUE-13 is the worked precedent).

New this session (2026-07-10):

- **Announce cadence:** epistemic-humility's announce-and-temper should fire
  **once per session/load, not per presentation** — per-presentation degrades
  into a tic. This is a queued wording fix to epistemic-humility's
  "Announce and temper" section; not yet made.
- **Enforcement over prose** for the announcement observable: the valid RED
  showed the description lever is exhausted for unreinforced subagents. The
  follow-on is a separate design task (e.g. a hook checking report-shaped
  output), converging with `docs/audits/2026-07-02-skill-engagement-audit.md`.
- **TaskCreate pattern:** TaskCreate primary for in-session enforcement,
  mirrored to a checklist file on disk as a durable worklog; the file is the
  tracker when TaskCreate is absent. (Now in writing-skills' checklist
  preamble; reuse the pattern where the question recurs.)
- **Coordination inverted:** plan-and-execute 2.36.0 is on main, so the
  `impl-plan-decision-discipline` worktree now merges main and bumps above
  2.36.0 (plus this branch's unpushed 2.36.x deltas: `7103b88`
  exec-session-naming user-invocable).

## FIRST ACTION — skill 4 review, main session

Review `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/`
(worktree copy; `ls` the directory for supporting files first). Four axes:

1. Does the skill do its job in its plugin?
2. Did the branch's changes make it more effective?
   (`git diff main...HEAD -- <skill dir>` — note main now contains most of the
   branch, so also consider the full obra-descent delta via the phase records.)
3. Does it follow the project's own skill-authoring protocols (writing-skills
   orchestration, writing-claude-directives phrasing, epistemic-humility
   rubric)?
4. Scar tissue: does the skill argue with its own past selves? History lives
   in git (and in ISSUE entries with state, per the new precedent).

Verify every quote with `grep -nF '<quote>' <file>` before presenting; weigh
severities (lead with whether a finding is a REAL problem); discuss with the
operator one finding at a time.

Axis-2 caveat after the merge: `git diff main...HEAD` is now near-empty for
this skill. Use `git log --oneline main -- <skill dir>` and the phase-03
records to reconstruct the branch's delta, or diff against the pre-branch
baseline (`git merge-base` of the branch's first commit).

## After skill 4

- **Skill 5:** `impl-plan-write/SKILL.md` (denubis-plan-and-execute) — review
  it, but deliver any fixes as a note into the `impl-plan-decision-discipline`
  worktree; no impl-plan-write fixes on this branch.
- **Codex synthesis (still owed):** the codex reviews at
  `.review/SKILL.md.20260708-15*.REVIEW.md` have deliberately NOT been compared
  against the Fable findings (kept out of context to preserve independence).
  After all five reviews: weigh Fable findings (`phase_05_fable_skill3_findings.md`
  and the skills-1-2 commits) against codex's findings and won't-fixes.
- **Queued wording fix:** epistemic-humility announce-cadence (above).
- **Package:** 1.9.1 (extending-claude) + 2.36.1 (plan-and-execute, coordinate
  with the other worktree) + CHANGELOG + marketplace; read current versions
  from each `.claude-plugin/plugin.json`. Then merge to main and push (operator
  approval per push).
- **Frustration audit (AC5.8)** — joint pass with the operator; note the
  fabricated-taxonomy deletion deviation (operator ruling 2026-07-09 supersedes
  test-requirements.md).
- **Finalization ADRs (M2/M6).**

## Codex won't-fixes — do NOT re-open without genuinely new evidence

- model-tier behavioural "current models" claims (freshness test is
  version-strings-only by design)
- "usually" softeners (testing:36, WCD rubric-callback tail)
- writing-skills checklist vs Anthropic's 3-evals/model-matrix (deliberate
  denubis method)
- epistemic-humility scope-vs-examples (the four screens are general; the
  example is illustrative — the 2026-07-09 rescope changed "When to invoke",
  so new evidence comes from the new scope, not the old argument)

Fable-pass won't-fix (2026-07-10): writing-skills description does not
advertise the scope gate — triggers unchanged, gate is workflow step 1.

## Also open

- Parked untracked: `docs/audits/2026-07-02-*.md` (skill-engagement audit
  awaits the operator's read; now directly evidenced by the round-2 RED).
- `systematic-debugging` hyperbole — operator to decide whether to hedge.
- The two by-product drift findings from the round-2 audit are already fixed
  (`561f069`).

## Guardrails

- Commits on this branch only, never on main directly (releases merge via the
  primary checkout with operator approval).
- Don't push without explicit approval. The skill-3 fix commits are unpushed.
- Don't `git worktree remove` this worktree from inside it.
