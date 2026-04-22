# Resume Prompt — Skill-Skills Upstream Sync — Phase 1 Complete, Phase 2 Entry Point

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in the feature-branch worktree at `.worktrees/skill-skills-upstream-sync/` on branch `skill-skills-upstream-sync`. The branch was **rebased onto `main` at commit `4d5c952` on 2026-04-22** (previous base was `9e11497`; the rebase was a clean fast-forward replay with zero conflicts).

**State (2026-04-22, Phase 1 complete, Phase 2 next):** Phase 1 (epistemic-humility rubric) is complete with all four C-checks (C1–C4) resolved. Branch holds 10 commits of execution work past the new merge-base. Working tree clean. 113/113 root tests pass. Invoke `denubis-plan-and-execute:executing-an-implementation-plan` to begin Phase 2 (writing-claude-directives).

## What Phase 1 produced (branch commits past `4d5c952`)

In chronological order (oldest first):

1. **`aa0f2c8`** `feat(epistemic-humility): author rubric SKILL.md with four-section structure` — core Phase 1 deliverable.
2. **`972cbc4`** `feat(epistemic-humility): add paragraph-level source citations` — Schön, Jones, technoscholasticism pointers anchored at the paragraph level.
3. **`e4e4e32`** `feat(epistemic-humility): add rubric self-application walk-through` — worked example applying the rubric to itself.
4. **`98e4cf4`** `build: add pyyaml dependency for phase-verification scripts` — `pyproject.toml` + `uv.lock` updated for script infra used by later phases.
5. **`628632c`** `fix(epistemic-humility): correct archaic form in memento ("thou art", not "you art")` — Shakespeare-fidelity nit.
6. **`c3952f8`** `feat(proleptic-challenger): require counterarguments to name the claim they argue against` — agent-prompt tightening discovered during Phase 1 independence work.
7. **`e890355`** `docs(phase-01): commit the Phase 1 code-review verdict + plan-deviation record (C1+C3)` — completeness checks C1 (code-reviewer verdict) and C3 (plan-deviation record).
8. **`554a1ac`** `docs(phase-01): mark Done-when checkboxes complete (C2)` — phase_01.md Done-when criteria ticked.
9. **`518487c`** `docs(phase-01): add independent self-application + C4 independence check` — separate-session independence verification.
10. **`c878a3b`** `docs(epistemic-humility): append three subsidiary vulnerabilities from C4 independence check` — subsidiary gaps surfaced during C4 independence work.

## Commits landed on `main` since this branch was first cut

- **`2a52ffe`** `chore: bump plan-and-execute to 2.31.0 for exec-session-naming revision`
- **`0bf0779`** `feat(skill): revise exec-session-naming with structured slug and anti-drift targeting`
- **`b12fd12`** `docs(plan): update RESUME-PROMPT for worktree-ready execution handoff` (superseded by this version)
- **`1e85703`** `fix(brainstorming): drop legacy @agent- prefix in internet-researcher reference` (2026-04-22 audit)
- **`119ff69`** `feat(writing-claude-md-files): add last-reviewed stamp and quarterly cadence` (2026-04-22 audit)
- **`4d5c952`** `docs(issues): migrate GH #1 as ISSUE-11 (reflective session-history pass)` (2026-04-22 audit; new merge-base)

All five of the above are now in this branch's ancestry via the 2026-04-22 rebase.

## Force-push required

The remote branch `origin/skill-skills-upstream-sync` is at **`c394d63`** — that SHA is pre-rebase and no longer exists in this branch's history. Any push will need `--force-with-lease` to rewrite the remote. Do not push silently; confirm with the user first.

## Read first

1. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02.md` — Phase 2 (writing-claude-directives) specification.
2. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase-01-code-review-2026-04-20.md` — Phase 1 code-review verdict (historical; for context on how the review cycle runs).
3. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase-01-independent-self-application.md` and `phase-01-self-application-independence-check.md` — the C4 artefacts.
4. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` — the 15 findings that drove the two pre-execution revision sessions (historical; do NOT re-edit).
5. `/home/brian/people/Brian/brian-ed3d-plugins/docs/issues.md` — ISSUE-06 (this plan, currently in-progress); ISSUE-01 (xref-audit tool promotion, separate design cycle); ISSUE-11 (reflective session-history pass, new as of 2026-04-22).
6. `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/MEMORY.md` — feedback memories active during Phase 1.

## First concrete action for this session

1. **Run post-resume verification** per `denubis-plan-and-execute:executing-an-implementation-plan`'s "Post-Resume Verification" section:

   ```bash
   pwd                         # must end with .worktrees/skill-skills-upstream-sync
   git worktree list           # confirm this worktree appears
   git branch --show-current   # must print: skill-skills-upstream-sync (NOT main/master)
   git log --oneline -1        # should show c878a3b as the current branch tip
   git merge-base main HEAD    # should show 4d5c952 (post-rebase merge-base)
   ```

   If any check fails, STOP and report. Do not proceed.

2. **Invoke** `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 2 (writing-claude-directives). Execution order from here: Phase 2 → Phase 2.5 (prep refactor) → Phase 3 (testing-skills-with-subagents) → Phase 4 (writing-skills cornerstone) → Phase 6 (impl-plan-write hardening) → Phase 5 (cross-reference audit + version bumps + frustration audit). Phase 6 lands before Phase 5 per execution-order in phase_05.md DoD.

3. **If any phase returns surprising results** — tests failing, reviewer flagging structural issues, subagent empty response — HALT per the repo CLAUDE.md "HALT When Things Feel Sideways" discipline. Don't work around the anomaly; report and ask.

## Alternate paths (if the user changes direction)

- **Third `critical-peer-review` before continuing.** The second pre-execution review cycle's 15 findings are all addressed, but a Phase-1-aware review would catch any regressions introduced during Phase 1 execution itself. Focus on the phase_01.md edits, the epistemic-humility skill files, and the proleptic-challenger agent change. If requested, invoke `denubis-plan-and-execute:critical-peer-review` against the plan directory and the branch's Phase 1 artefacts before launching Phase 2.

- **Push the branch to origin** with `git push --force-with-lease` so the remote reflects the rebased tip. Requires explicit user approval (see Force-push required section).

- **Work a deferred thread first.** If ISSUE-01 (xref-audit tool promotion), ISSUE-11 (reflective session-history pass), or another ISSUE has become more pressing, return to `main` (`cd` back to the main checkout), invoke `denubis-plan-and-execute:starting-a-design-plan` for that thread, and come back to this worktree later.

## What NOT to do without explicit direction

- Do not execute the plan on `main`. You must be in the worktree on branch `skill-skills-upstream-sync`. The executing-an-implementation-plan skill's precondition enforces this, and phase_05.md Task 4 Step 2's M5 branch-discipline guard hard-fails if run on `main` (by design).
- Do not re-edit the revision-history notes inside the plan files (H1-H7 + M1-M7 + L1-L3 + Meta-M7 markers are the audit trail — preserve them).
- Do not re-edit the Phase 1 C1-C4 artefacts (`phase-01-code-review-2026-04-20.md`, `phase-01-independent-self-application.md`, `phase-01-self-application-independence-check.md`) — they are the Phase 1 audit trail.
- Do not commit additional work to `main` during this execution; all execution commits belong on the feature branch.
- Do not push `main` or the feature branch to `origin` without checking with the user. The feature branch in particular requires `--force-with-lease` (see Force-push required section).
- Do not delete `docs/issues.md` or any ISSUE-NN entries.
- Do not try to re-run `cc-search-chats` with apostrophes, hyphens, or regex — ISSUE-10 remains unfixed upstream; stick to the safe query set.
- Do not `git worktree remove` this worktree while the current working directory is inside it. The `finishing-a-development-branch` skill handles safe cleanup.

## Task-list state at handoff

- Phases 1–6 planning: committed on main (`1a77fa8`).
- Both pre-execution critical-peer-review cycles: addressed + committed on main.
- **Phase 1 execution: COMPLETE.** 10 branch commits; C1-C4 all resolved; working tree clean; 113/113 tests pass.
- **Phase 2 execution: NOT started.** Entry point is `denubis-plan-and-execute:executing-an-implementation-plan` invoked from this worktree.
- Feature branch + worktree: rebased 2026-04-22 onto `main@4d5c952`; tip `c878a3b`; remote (`origin/skill-skills-upstream-sync` at `c394d63`) is stale and requires `--force-with-lease` on next push.
- test-requirements.md: 43 ACs; AC5.8 covered by cc-search-chats + joint review; AC6.4 cut during M2 revision.
- uat-requirements.md: 8 DR entries; DR-P4-INT-1 deleted during H3 revision; DR-P5-FRUST-1 added as replacement; M3-Meta-M7 revisions landed.

When resuming, run the post-resume verification block above, confirm branch + tip + merge-base match, then invoke `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 2.

## Key conventions established pre-execution and during Phase 1

- **Path-form cross-reference convention** (H1): backticked path with `/` → audited; bare backticked filename → prose vocabulary (not audited); angle-bracket prefix → teaching placeholder (opts out); `CONDITIONAL_PATHS` frozenset → deliberately-optional refs (silently skipped).
- **Functional-decomposition + Ripple Rule discipline**: work findings one-by-one; after each fix, grep the plan directory for all references to the changed claim, update every downstream reference, confirm "I have done a full editing pass" before moving to the next finding.
- **Frustration is always the signal** (M3): if a user expressed frustration, the methodology failed at that point, regardless of whether the session subsequently course-corrected. No "resolved-in-session" dismissal path.
- **Repo-local issue tracking** (`docs/issues.md`) in preference to GitHub issues. As of 2026-04-22, all 7 open GitHub issues have been closed; local tracker now holds ISSUE-01 through ISSUE-11.
- **cc-search-chats CLI constraints** (ISSUE-10): single literal query, no regex, no OR, no apostrophes, no hyphens, `--days N` for time-window. Any skill or plan invoking it needs defensive query construction.
- **Epistemic-humility rubric** (Phase 1 output): four-section structure (methodology → scope-lever → technoscholasticism → absence-judgement) with paragraph-level source citations; `thou art` fidelity; proleptic-challenger required to name the claim it argues against.
