# Resume Prompt — Skill-Skills Upstream Sync — Phase 1 Complete, Plan Amended, Phase 2 Entry Point

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in the feature-branch worktree at `.worktrees/skill-skills-upstream-sync/` on branch `skill-skills-upstream-sync`. The branch was **rebased onto `main` at commit `4d5c952` on 2026-04-22** (previous base was `9e11497`; the rebase was a clean fast-forward replay with zero conflicts).

**State (2026-04-23, Phase 1 complete, plan amendments committed, Phase 2 next):** Phase 1 (epistemic-humility rubric) is complete with all four C-checks (C1–C4) resolved. A 2026-04-22/23 plan-amendment pass reframed Phase 2 and Phase 4 RED-gates from independent-session-transcript to static code-smell evidence (preventive restructures), retained FTS5-safe cc-search-chats queries with Phase 3 staying corrective, and retained the operator-empirical Haiku-no-judgement guidance against Anthropic's 2026-04 marketing framing. Branch holds **14 commits of work past the new merge-base** (10 Phase 1 + 4 plan amendments). Working tree clean. 113/113 root tests pass. Invoke `denubis-plan-and-execute:executing-an-implementation-plan` to resume Phase 2 (writing-claude-directives) under the amended RED-gate framing.

## What Phase 1 produced (branch commits past `4d5c952`, oldest first)

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

## Plan-amendment pass (2026-04-22/23) — four commits, applied BEFORE Phase 2 execution resumes

The plan-amendment pass reframed the RED-gate structure across Phases 2–5 after the 2026-04-22 independent-session search (dispatched during C4 closure) returned 0 qualifying transcripts for Phase 2's deficiencies — exposing that the independent-session gate was architecturally mis-specified for preventive restructures. Same-session operator input then surfaced a Haiku-judgement framing conflict: the pre-amendment plan retired the "Haiku struggles with judgement" claim on the basis of 2026-04 Anthropic marketing; operator-empirical position (stated 2026-04-22, saved to `feedback_haiku-no-judgement.md`) contradicts that marketing. The amendment reverses both mis-specifications.

11. **`43e3b16`** `docs(phase-02): reframe RED-gate to static code-smell + retain Haiku-no-judgement` — Phase 2 accepts the Phase 2B investigator code-smell inventory + the 2026-04-22 search record as static RED; Task 3 Step 1 item 5 reframes Haiku with operator-empirical framing; verification script flipped from `has_haiku_retirement` to `has_haiku_no_judgement_guidance`; test-requirements.md AC3.8 rewritten.
12. **`6c0a07f`** `docs(phase-03): FTS5-safe RED queries + retain Haiku-no-judgement with operator framing` — Phase 3 stays corrective (target methodology is transcript-sourcing) but queries translated to FTS5-safe single-term form per ISSUE-10; Task 2 Step 2 reframes Haiku passage instead of removing it; Task 2 Step 3 verification flipped from absence-check to presence-check; test-requirements.md AC2.6 + AC2.7 rewritten.
13. **`749945c`** `docs(phase-04): reframe RED-gate to static file-shape diff (preventive cornerstone)` — Phase 4 accepts file-shape diff (current 163 lines of TDD-spine, target ≤250 lines of orchestrator, rubric callback + Workflow H2 + Supporting Files absent) as static RED; applies the H3-revision precedent that dropped the earlier "production IS integration evidence" claim as unfalsifiable; test-requirements.md AC1.7 rewritten.
14. **`a78484c`** `docs(phase-05): meta-gate reword for mixed RED types + Phase 3 Haiku reframe cross-ref` — Task 4 Step 3 meta-gate checkbox accepts the mix (Phase 2 + Phase 4 static-evidence; Phase 3 session-transcript); Phase 3 cross-reference summary in Phase 5 updated to match the Haiku reframe.

## Commits landed on `main` since this branch was first cut

- **`2a52ffe`** `chore: bump plan-and-execute to 2.31.0 for exec-session-naming revision`
- **`0bf0779`** `feat(skill): revise exec-session-naming with structured slug and anti-drift targeting`
- **`b12fd12`** `docs(plan): update RESUME-PROMPT for worktree-ready execution handoff` (superseded by this version)
- **`1e85703`** `fix(brainstorming): drop legacy @agent- prefix in internet-researcher reference` (2026-04-22 audit)
- **`119ff69`** `feat(writing-claude-md-files): add last-reviewed stamp and quarterly cadence` (2026-04-22 audit)
- **`4d5c952`** `docs(issues): migrate GH #1 as ISSUE-11 (reflective session-history pass)` (2026-04-22 audit; new merge-base)

All six are in this branch's ancestry via the 2026-04-22 rebase.

## Force-push required

The remote branch `origin/skill-skills-upstream-sync` is at **`c394d63`** — pre-rebase and no longer in this branch's history. Divergence as of 2026-04-23 is **20 ahead / 8 behind origin** (the 20 includes the 10 Phase 1 commits + 4 plan-amendment commits + older intermediate commits that survived the rebase). Any push will need `--force-with-lease` to rewrite the remote. Do not push silently; confirm with the user first.

## Read first

1. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02.md` — Phase 2 (writing-claude-directives) specification, **amended 2026-04-22 plan-amendment pass**. Task 1 is now static code-smell RED; Task 3 Step 1 item 5 carries the operator-empirical Haiku framing.
2. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_03.md` — Phase 3 (testing-skills-with-subagents), FTS5-safe queries + Haiku retention.
3. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_04.md` — Phase 4 (writing-skills cornerstone), static file-shape-diff RED.
4. `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/feedback_haiku-no-judgement.md` — operator-empirical standing position on Haiku, active 2026-04-22 onward.
5. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase-01-code-review-2026-04-20.md` — Phase 1 code-review verdict (historical; for context on how the review cycle runs).
6. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase-01-independent-self-application.md` and `phase-01-self-application-independence-check.md` — the C4 artefacts; read these before Phase 2's own Task 5 self-application to understand the independence-check concern (a single session authoring both the rubric and its self-application cannot distinguish genuine reflection from spec-compliant rubber-stamp).
7. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` — the 15 findings that drove the two pre-execution revision sessions (historical; do NOT re-edit).
8. `/home/brian/people/Brian/brian-ed3d-plugins/docs/issues.md` — ISSUE-06 (this plan, currently in-progress), ISSUE-01 (xref-audit tool promotion), ISSUE-10 (cc-search-chats FTS5 constraints — enforced throughout; queries must be single-term), ISSUE-11 (reflective session-history pass).
9. `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/MEMORY.md` — feedback memories active across this work.

## First concrete action for this session

1. **Run post-resume verification** per `denubis-plan-and-execute:executing-an-implementation-plan`'s "Post-Resume Verification" section:

   ```bash
   pwd                         # must end with .worktrees/skill-skills-upstream-sync
   git worktree list           # confirm this worktree appears
   git branch --show-current   # must print: skill-skills-upstream-sync (NOT main/master)
   git log --oneline -1        # should show a78484c as the current branch tip
   git merge-base main HEAD    # should show 4d5c952 (post-rebase merge-base)
   ```

   If any check fails, STOP and report. Do not proceed.

2. **Invoke** `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 2 (writing-claude-directives).

   **Phase 2 Task 1 note (2026-04-22 plan-amendment pass):** Task 1 is now a **static code-smell write-up**, not an independent-session search. The dispatched task-implementor should:
   - Enumerate the Phase 2B code-smell inventory (SKILL.md line 215-220 stale Opus 4.5 section, lines 69/96/99/237 generic 4.x anchors, long-running-state-patterns.md lines 15/114/119/132/133 stale anchors, graphviz-conventions.dot attribution absent).
   - Record the 2026-04-22 independent-session search result: 30+ FTS5-safe queries across 6 projects, 0 qualifying transcripts. Full query list + per-project hit counts are in this session's logs / the amended phase_02.md Task 1 Step 2.
   - Write `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_02_red_evidence.md` per the amended Task 1 Step 3 template.
   - Commit per the amended Task 1 Step 4 commit message (describes static code-smell inventory + preventive framing).
   - No HALT expected — the gate is structurally verifiable by static inspection.

   Execution order from here: Phase 2 → Phase 2.5 (prep refactor) → Phase 3 (testing-skills-with-subagents) → Phase 4 (writing-skills cornerstone) → Phase 6 (impl-plan-write hardening) → Phase 5 (cross-reference audit + version bumps + frustration audit). Phase 6 lands before Phase 5 per execution-order in phase_05.md DoD.

3. **If any phase returns surprising results** — tests failing, reviewer flagging structural issues, subagent empty response — HALT per the repo CLAUDE.md "HALT When Things Feel Sideways" discipline. Don't work around the anomaly; report and ask.

## Alternate paths (if the user changes direction)

- **Third `critical-peer-review` before continuing.** The second pre-execution review cycle's 15 findings are all addressed, and the 2026-04-22 plan-amendment pass revisited the RED-gate architecture after a 0-transcripts-found signal. A fresh Phase-1-and-amendment-aware review would catch any regressions introduced during Phase 1 execution or the amendment pass itself. Focus on: phase_01.md edits, the epistemic-humility skill files, the proleptic-challenger agent change, and the four plan-amendment commits (43e3b16, 6c0a07f, 749945c, a78484c). If requested, invoke `denubis-plan-and-execute:critical-peer-review` against the plan directory and the branch's Phase 1 + amendment artefacts before launching Phase 2.

- **Push the branch to origin** with `git push --force-with-lease` so the remote reflects the rebased + amended tip. Requires explicit user approval (see Force-push required section).

- **Work a deferred thread first.** If ISSUE-01 (xref-audit tool promotion), ISSUE-11 (reflective session-history pass), or another ISSUE has become more pressing, return to `main` (`cd` back to the main checkout), invoke `denubis-plan-and-execute:starting-a-design-plan` for that thread, and come back to this worktree later.

## What NOT to do without explicit direction

- Do not execute the plan on `main`. You must be in the worktree on branch `skill-skills-upstream-sync`. The executing-an-implementation-plan skill's precondition enforces this, and phase_05.md Task 4 Step 2's M5 branch-discipline guard hard-fails if run on `main` (by design).
- Do not re-edit the revision-history notes inside the plan files (H1-H7 + M1-M7 + L1-L3 + Meta-M7 markers are the audit trail — preserve them).
- Do not re-edit the Phase 1 C1-C4 artefacts (`phase-01-code-review-2026-04-20.md`, `phase-01-independent-self-application.md`, `phase-01-self-application-independence-check.md`) — they are the Phase 1 audit trail.
- Do not reverse the 2026-04-22 plan-amendment pass without explicit user direction. The Phase 2 / Phase 4 static-RED reframe and the Haiku-no-judgement retention were both operator-driven decisions; future sessions encountering the `feedback_haiku-no-judgement.md` memory or the amended plan files should respect them.
- Do not commit additional work to `main` during this execution; all execution commits belong on the feature branch.
- Do not push `main` or the feature branch to `origin` without checking with the user. The feature branch in particular requires `--force-with-lease` (see Force-push required section).
- Do not delete `docs/issues.md` or any ISSUE-NN entries.
- Do not try to re-run `cc-search-chats` with apostrophes, hyphens, or regex — ISSUE-10 remains unfixed upstream; stick to the safe query set (single literal term per query).
- Do not `git worktree remove` this worktree while the current working directory is inside it. The `finishing-a-development-branch` skill handles safe cleanup.
- Do not route judgement-requiring subagent tasks to Haiku 4.5 — see `feedback_haiku-no-judgement.md`. Mechanical / structured-extraction / tool-call-loop tasks are fine for Haiku.

## Task-list state at handoff

- Phases 1–6 planning: committed on main (`1a77fa8`).
- Both pre-execution critical-peer-review cycles: addressed + committed on main.
- **Phase 1 execution: COMPLETE.** 10 branch commits; C1-C4 all resolved; working tree clean; 113/113 tests pass.
- **Plan-amendment pass 2026-04-22/23: COMPLETE.** 4 branch commits (43e3b16, 6c0a07f, 749945c, a78484c); reframed Phase 2/4 RED-gates to static evidence, retained FTS5-safe cc-search-chats for Phase 3, retained operator-empirical Haiku-no-judgement guidance across Phase 2 + Phase 3.
- **Phase 2 execution: NOT started.** Entry point is `denubis-plan-and-execute:executing-an-implementation-plan` invoked from this worktree.
- Feature branch + worktree: rebased 2026-04-22 onto `main@4d5c952`; tip `a78484c`; remote (`origin/skill-skills-upstream-sync` at `c394d63`) is stale and requires `--force-with-lease` on next push.
- test-requirements.md: 43 ACs; AC5.8 covered by cc-search-chats + joint review; AC6.4 cut during M2 revision; AC3.8 + AC2.6 + AC2.7 + AC1.7 amended 2026-04-22/23 per the amendment pass.
- uat-requirements.md: 8 DR entries; DR-P4-INT-1 deleted during H3 revision; DR-P5-FRUST-1 added as replacement; M3-Meta-M7 revisions landed.

When resuming, run the post-resume verification block above, confirm branch + tip + merge-base match, then invoke `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 2.

## Key conventions established pre-execution, during Phase 1, and during the 2026-04-22 amendment pass

- **Path-form cross-reference convention** (H1): backticked path with `/` → audited; bare backticked filename → prose vocabulary (not audited); angle-bracket prefix → teaching placeholder (opts out); `CONDITIONAL_PATHS` frozenset → deliberately-optional refs (silently skipped).
- **Functional-decomposition + Ripple Rule discipline**: work findings one-by-one; after each fix, grep the plan directory for all references to the changed claim, update every downstream reference, confirm "I have done a full editing pass" before moving to the next finding.
- **Frustration is always the signal** (M3): if a user expressed frustration, the methodology failed at that point, regardless of whether the session subsequently course-corrected. No "resolved-in-session" dismissal path.
- **Repo-local issue tracking** (`docs/issues.md`) in preference to GitHub issues. As of 2026-04-22, all 7 open GitHub issues have been closed; local tracker now holds ISSUE-01 through ISSUE-11.
- **cc-search-chats CLI constraints** (ISSUE-10): single literal query, no regex, no OR, no apostrophes, no hyphens, `--days N` for time-window. Any skill or plan invoking it needs defensive query construction.
- **Epistemic-humility rubric** (Phase 1 output): four-section structure (methodology → scope-lever → technoscholasticism → absence-judgement) with paragraph-level source citations; `thou art` fidelity; proleptic-challenger required to name the claim it argues against.
- **Preventive vs corrective RED-gate distinction** (2026-04-22 amendment pass): preventive restructures (Phase 2, Phase 4) accept static code-smell / file-shape evidence as RED — the Phase 2B investigator inventory + the 2026-04-22 independent-session search record (0 qualifying transcripts) together satisfy the gate structurally. Corrective restructures (Phase 3) retain the cc-search-chats + fresh-session independent-session gate because their target methodology is transcript-sourcing. Meta-gates in Phase 5 accept the mix.
- **Operator-empirical Haiku-no-judgement position** (2026-04-22, `feedback_haiku-no-judgement.md`): Haiku 4.5 is unsuitable for any task requiring judgement, regardless of Anthropic's 2026-04 marketing framing. The Haiku-judgement guidance is retained and strengthened across `model-tier-notes.md` (Phase 2 Task 3) and `testing-skills-with-subagents/SKILL.md` (Phase 3 Task 2) — not retired. Never route judgement-heavy subagent tasks to Haiku.
