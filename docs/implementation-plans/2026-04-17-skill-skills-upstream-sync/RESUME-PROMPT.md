# Resume Prompt — Skill-Skills Upstream Sync — Plan Fully Revised, Ready for Execution

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

---

I'm resuming work on the skill-skills upstream sync plan at `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`.

**State (2026-04-19, post-full-revision-commit):** All 15 findings from `critical-peer-review-2026-04-18.md` are now addressed across two revision sessions (8 in 2026-04-19a, 7 in 2026-04-19b). The plan is committed on `main` and the working tree is clean. The plan has not yet been executed.

## Commits landed since 24a7848

- **5cad1df** `docs: add local issue tracker for deferred threads` — `docs/issues.md` with ten deferred threads (ISSUE-01 through ISSUE-10).
- **1a77fa8** `docs: add skill-skills upstream sync implementation plan (twice-revised)` — the full `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/` directory (phases 01-06, test-requirements, uat-requirements, both critical-peer-review records, and this RESUME-PROMPT).
- **b9bed28** `refactor: complete M25 skill-rename ripple + HALT philosophy + design-plan H/M revisions` — backlog that was co-resident on main since 2026-04-17: frontmatter `name:`/`family:` fixes for the M25 rename, CLAUDE.md ed3d→denubis + HALT working-philosophy, design plan H1-H7 + M1-M7 revision text.

Working tree is clean as of commit 5cad1df.

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

## First concrete action for the next session

The plan is ready to execute. The next step requires a decision:

1. **Proceed to execution.** Create a feature branch via `denubis-plan-and-execute:using-git-worktrees`, then invoke `denubis-plan-and-execute:executing-an-implementation-plan`. Execution dispatches task-implementor subagents per phase; the plan's AC5.5/5.6 branch-discipline guard (M5) asserts `HEAD != main/master` before the commit-count runs — the branch must exist before Phase 5 is executed.

2. **Request a third `critical-peer-review`** before executing. The second review cycle's 15 findings are all addressed (verified by the revision summary above), but a third review would catch any regressions introduced by the revision text itself. Reviewer guidance: focus on the M3 / M4 / M5 / Meta-M7 revision blocks specifically, since those introduced the most new text.

3. **Work a deferred thread first.** If ISSUE-01 (xref-audit tool promotion) or ISSUE-06 (execution blocking items) has become more pressing, invoke `denubis-plan-and-execute:starting-a-design-plan` for it before returning to this plan's execution.

Do NOT default to executing. The user may want path 2 (third review) before committing to execution, given the substantial revision text. Ask before proceeding.

## What NOT to do without explicit direction

- Do not execute the plan without first creating a feature branch. The plan is on `main` but execution cannot happen on `main` — see `denubis-plan-and-execute:executing-an-implementation-plan`'s "Precondition: Worktree Required" and phase_05.md Task 4 Step 2's M5 guard.
- Do not re-edit the revision-history notes inside the plan files (H1-H7 + M1-M7 + L1-L3 + Meta-M7 markers are the audit trail — preserve them).
- Do not commit additional work to `main` without a feature branch; all further execution work belongs on the execution branch.
- Do not push `main` to `origin` without checking with the user; the three landed commits are local-only at the time this RESUME-PROMPT was written.
- Do not delete `docs/issues.md` or any ISSUE-NN entries.
- Do not try to re-run `cc-search-chats` with apostrophes, hyphens, or regex — ISSUE-10 remains unfixed upstream; stick to the safe query set.

## Task-list state at handoff

- Phases 1-6 planning: committed (1a77fa8).
- Both critical-peer-review cycles: addressed + committed (1a77fa8).
- Finalization code-reviewer: not yet run post-second-revision. Path 2 above would dispatch this.
- test-requirements.md: 43 ACs; AC5.8 covered by cc-search-chats + joint review; AC6.4 cut during M2 revision.
- uat-requirements.md: 8 DR entries; DR-P4-INT-1 deleted during H3 revision; DR-P5-FRUST-1 added as replacement; M3-Meta-M7 revisions landed.
- Execution handoff: NOT started; path 1 above is the entry point.
- Feature branch: does NOT exist yet. First action on path 1 is `denubis-plan-and-execute:using-git-worktrees`.

When resuming, start with `git status` and `git log --oneline -5` to verify the three commits are still present, read this RESUME-PROMPT.md in full, then ask the user which path.

## Key conventions established this revision cycle

- **Path-form cross-reference convention** (H1): backticked path with `/` → audited; bare backticked filename → prose vocabulary (not audited); angle-bracket prefix → teaching placeholder (opts out); `CONDITIONAL_PATHS` frozenset → deliberately-optional refs (silently skipped).
- **Functional-decomposition + Ripple Rule discipline**: work findings one-by-one; after each fix, grep the plan directory for all references to the changed claim, update every downstream reference, confirm "I have done a full editing pass" before moving to the next finding. The second revision session applied this for M3 (5 downstream references swept), M4 (per-DR-block assertion), M5 (inline guard + AC description updates), L3 (same-plugin ordering check), and Meta-M7 (Step 3 + Step 4 + DR entry + DoD).
- **Frustration is always the signal** (M3): if a user expressed frustration, the methodology failed at that point, regardless of whether the session subsequently course-corrected. No "resolved-in-session" dismissal path.
- **Repo-local issue tracking** (`docs/issues.md`) in preference to GitHub issues.
- **cc-search-chats CLI constraints** (ISSUE-10): single literal query, no regex, no OR, no apostrophes, no hyphens, `--days N` for time-window. Any skill or plan invoking it needs defensive query construction.
