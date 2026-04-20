# Resume Prompt — Skill-Skills Upstream Sync — Worktree Ready, Execution Entry Point

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in the feature-branch worktree at `.worktrees/skill-skills-upstream-sync/` on branch `skill-skills-upstream-sync`. The branch was created from `main` at commit 9e11497.

**State (2026-04-19, worktree ready, not yet executed):** All 15 findings from `critical-peer-review-2026-04-18.md` are addressed; the plan is committed on `main`; the worktree is set up with clean baselines; execution has not started. Invoke `denubis-plan-and-execute:executing-an-implementation-plan` to begin.

## Commits landed on `main` since 24a7848

- **9e11497** `chore: patch bumps for M25 rename ripple (plan-and-execute 2.30.1, extending-claude 1.7.1)` — version + marketplace + CHANGELOG updates for the M25 ripple. Minor-bump targets (2.31.0 / 1.8.0) reserved for this plan's Phase 5.
- **f594ea5** `docs(plan): update RESUME-PROMPT to post-revision-complete state` — superseded by this version.
- **5cad1df** `docs: add local issue tracker for deferred threads` — `docs/issues.md` with ten deferred threads (ISSUE-01 through ISSUE-10).
- **1a77fa8** `docs: add skill-skills upstream sync implementation plan (twice-revised)` — the full `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/` directory (phases 01-06, test-requirements, uat-requirements, both critical-peer-review records, and this RESUME-PROMPT).
- **b9bed28** `refactor: complete M25 skill-rename ripple + HALT philosophy + design-plan H/M revisions` — backlog that was co-resident on main since 2026-04-17: frontmatter `name:`/`family:` fixes for the M25 rename, CLAUDE.md ed3d→denubis + HALT working-philosophy, design plan H1-H7 + M1-M7 revision text.

Worktree baseline (verified 2026-04-19): 113 root tests + 140 workflow_statusline tests = **253 passing, 0 failing**. `uv sync` resolved clean; no `.env`/`.worktreeinclude`/`.ed3d/worktree-setup.md` setup needed; LFS configured but no dirty files.

## Read first

1. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` — the 15 findings that drove the two revision sessions (historical record; do NOT re-edit).
2. `/home/brian/people/Brian/brian-ed3d-plugins/docs/issues.md` — ISSUE-06 in particular (plan never executed; execution requires a feature branch); ISSUE-01 (xref-audit tool promotion, separate design cycle).
3. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05.md` Task 4 Step 2 (M5 branch-discipline guard), Task 4.5 (M3 category change + Meta-M7 fatigue-floor + calibration).
4. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_06.md` Task 2 Step 1 (M4 DR scope) and Step 3 (M4 per-DR-block assertion).
5. `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/MEMORY.md` — feedback memories active during the revisions.

## Revision pass summary (second review cycle, complete)

### First revision session (2026-04-19a): 8 of 15 findings

- **H1** — Cross-reference audit refactored: `PATH_REF_RE` (requires `/` in backticked string) + `LINK_REF_RE` (markdown link form) + `CONDITIONAL_PATHS` frozenset + `resolve_xref` covering skills/agents/commands. Scope creep (full Typer tool promotion) spun out to ISSUE-01.
- **H2** — Phase 6 Task 4 Step 3 `'Second defensive layer' in content` assertion now has matching inserted content.
- **H3 + H4 + H5** — M6 reframe ("authoring-time rejection gate" → "pre-presentation self-audit") ripple swept across test-requirements.md AC6.6, phase_05.md CHANGELOG 2.31.0 entry, and phase_06.md Task 3 commit message + Step 1 header.
- **H6** — Commit count reconciled to ≥ 31 (Phase 5 gained Task 4.5 frustration-signal audit +1; Phase 6 gained Task 6 illustrative-path rewrite +1). Updated in test-requirements.md AC5.5/5.6 + phase_05.md Task 4 Step 2 checklist + DoD.
- **M1** — AC6.7 line number corrected (664 → 681-686 range; Popper row 683).
- **M2** — Frustration-audit queries rewritten to work with cc-search-chats FTS5 constraints (one term per query, no regex, no apostrophes, no hyphens); workaround pattern documented; ISSUE-10 filed for upstream fix.

### Second revision session (2026-04-19b): 7 of 15 findings

- **M3** — RESOLVED-IN-SESSION category dropped entirely. Frustration flags the audit regardless of whether the session self-corrected (user direction: "frustration is bad, even if I got it to work"). Three categories remain: GENUINE-FRUSTRATION / TECHNICAL-DISAGREEMENT / QUOTED-ILLUSTRATIVE. Five sites updated in phase_05.md, test-requirements.md, uat-requirements.md.
- **M4** — DR scope narrowed to DR1 and DR3 only. DR2 and DR4 route to test-requirement (no UAT entry, no falsification block, no `What's automatable` lines). Step 3 Python assertion strengthened to parse DR template blocks and verify DR1/DR3 have the lines + DR2/DR4 don't.
- **M5** — Inline branch-discipline guard in phase_05.md Task 4 Step 2: `assert subprocess.check_output(['git','branch','--show-current']).strip() not in (b'main', b'master', b'')` before the commit-count runs. Covers the case where `executing-an-implementation-plan`'s precondition is bypassed. AC5.5/5.6 descriptions updated.
- **L1** — Known-limit note in DR-P5-FRUST-1 acknowledging single-operator executor/reviewer collapse; mitigations referenced.
- **L2** — `has_haiku_retirement` check tightened to single conjunction: `'Haiku 4.5' in content AND (judgement term) AND (retired OR not supported)`.
- **L3** — Same-plugin CHANGELOG ordering assertion added (2.31.0 must precede existing 2.30.0). AC5.7 description updated.
- **Meta M7** — 30-match sitting cap (fatigue-floor) + blinded 9-sample recategorisation (calibration) added to Task 4.5 Step 3. Step 4 verdict handles `audit-flags (calibration failed)` outcome. DR-P5-FRUST-1 + test-requirements.md + phase-level DoD updated.

## First concrete action for this session

1. **Run post-resume verification** per `denubis-plan-and-execute:executing-an-implementation-plan`'s "Post-Resume Verification" section:

   ```bash
   pwd                         # must end with .worktrees/skill-skills-upstream-sync
   git worktree list           # confirm this worktree appears
   git branch --show-current   # must print: skill-skills-upstream-sync (NOT main/master)
   git log --oneline -1        # should show 9e11497 as the branch base
   ```

   If any check fails, STOP and report. Do not proceed.

2. **Invoke** `denubis-plan-and-execute:executing-an-implementation-plan`. The skill dispatches task-implementor subagents per phase. Phase order for this plan is pre-set by the design: Phase 1 (epistemic-humility) → Phase 2 (writing-claude-directives) → Phase 2.5 (prep refactor) → Phase 3 (testing-skills-with-subagents) → Phase 4 (writing-skills cornerstone) → Phase 6 (impl-plan-write hardening) → Phase 5 (cross-reference audit + version bumps + frustration audit). Phase 6 lands before Phase 5 per execution-order in phase_05.md DoD.

3. **If any phase returns surprising results** — tests failing, reviewer flagging structural issues, subagent empty response — HALT per the repo CLAUDE.md "HALT When Things Feel Sideways" discipline. Don't work around the anomaly; report and ask.

## Alternate paths (if the user changes direction)

- **Third `critical-peer-review` before executing.** The second review cycle's 15 findings are all addressed, but a third review would catch regressions introduced by the revision text itself. Focus on the M3 / M4 / M5 / Meta-M7 revision blocks since those introduced the most new text. If the user asks for this, invoke `denubis-plan-and-execute:critical-peer-review` against the plan directory before launching execution.

- **Work a deferred thread first.** If ISSUE-01 (xref-audit tool promotion) or another ISSUE has become more pressing, return to `main` (`cd` back to the main checkout), invoke `denubis-plan-and-execute:starting-a-design-plan` for that thread, and come back to this worktree later.

## What NOT to do without explicit direction

- Do not execute the plan on `main`. You must be in the worktree on branch `skill-skills-upstream-sync`. The executing-an-implementation-plan skill's precondition enforces this, and phase_05.md Task 4 Step 2's M5 branch-discipline guard hard-fails if run on `main` (by design).
- Do not re-edit the revision-history notes inside the plan files (H1-H7 + M1-M7 + L1-L3 + Meta-M7 markers are the audit trail — preserve them).
- Do not commit additional work to `main` during this execution; all execution commits belong on the feature branch.
- Do not push `main` or the feature branch to `origin` without checking with the user; commits are local-only at the time this RESUME-PROMPT was written.
- Do not delete `docs/issues.md` or any ISSUE-NN entries.
- Do not try to re-run `cc-search-chats` with apostrophes, hyphens, or regex — ISSUE-10 remains unfixed upstream; stick to the safe query set.
- Do not `git worktree remove` this worktree while the current working directory is inside it. The `finishing-a-development-branch` skill handles safe cleanup.

## Task-list state at handoff

- Phases 1-6 planning: committed (1a77fa8).
- Both critical-peer-review cycles: addressed + committed (1a77fa8).
- Finalization code-reviewer: not yet run post-second-revision. An alternate path (third review) would dispatch it.
- test-requirements.md: 43 ACs; AC5.8 covered by cc-search-chats + joint review; AC6.4 cut during M2 revision.
- uat-requirements.md: 8 DR entries; DR-P4-INT-1 deleted during H3 revision; DR-P5-FRUST-1 added as replacement; M3-Meta-M7 revisions landed.
- Execution: NOT started; entry point is `denubis-plan-and-execute:executing-an-implementation-plan` invoked from this worktree.
- Feature branch + worktree: CREATED — `.worktrees/skill-skills-upstream-sync/` on branch `skill-skills-upstream-sync`, branched from `main@9e11497`. Baseline 253/253 tests passing.

When resuming, run the post-resume verification block above, confirm branch + commits are in place, then invoke `denubis-plan-and-execute:executing-an-implementation-plan`.

## Key conventions established this revision cycle

- **Path-form cross-reference convention** (H1): backticked path with `/` → audited; bare backticked filename → prose vocabulary (not audited); angle-bracket prefix → teaching placeholder (opts out); `CONDITIONAL_PATHS` frozenset → deliberately-optional refs (silently skipped).
- **Functional-decomposition + Ripple Rule discipline**: work findings one-by-one; after each fix, grep the plan directory for all references to the changed claim, update every downstream reference, confirm "I have done a full editing pass" before moving to the next finding. The second revision session applied this for M3 (5 downstream references swept), M4 (per-DR-block assertion), M5 (inline guard + AC description updates), L3 (same-plugin ordering check), and Meta-M7 (Step 3 + Step 4 + DR entry + DoD).
- **Frustration is always the signal** (M3): if a user expressed frustration, the methodology failed at that point, regardless of whether the session subsequently course-corrected. No "resolved-in-session" dismissal path.
- **Repo-local issue tracking** (`docs/issues.md`) in preference to GitHub issues.
- **cc-search-chats CLI constraints** (ISSUE-10): single literal query, no regex, no OR, no apostrophes, no hyphens, `--days N` for time-window. Any skill or plan invoking it needs defensive query construction.
