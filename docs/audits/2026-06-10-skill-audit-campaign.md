# Skill Audit Campaign — 2026-06-10

Durable tracker for the full-harness skill audit and its spin-off projects. Update this file as items complete; it is the source of truth across sessions.

## Status summary

- Survey pass complete: 7 parallel subagent audits over 50 skills + global and project CLAUDE.md.
- Hard-break batch: 1 of 4 fixed (see below). No commits yet — commit the batch together at the end.
- Diverted (by Brian's decision) into building a writing-prose skill before resuming the walk.
- BLOCKING DECISION: sequencing with the in-flight `skill-skills-upstream-sync` worktree (see Collisions).

## Hard breaks (verified, mechanical)

| # | Item | Status |
|---|---|---|
| 1 | `writing-plans` dead skill name ×7 (design-write ×4, starting-a-design-plan L90, brainstorming L406) | FIXED on main (uncommitted). Renamed to impl-plan-write / starting-an-implementation-plan. Verified: grep clean. |
| 2 | `house-style:writing-for-a-technical-audience` REQUIRED ref in design-write L334 — plugin removed | DEFERRED: resolution is the writing-prose skill project (below). Repoint L334 when the skill exists. |
| 3 | Repo CLAUDE.md L17 points at `…/memory/feedback_review-all-levels.md`; memory dir archived to `memory.archive-2026-05-22` | OPEN. Fix path or fold rule inline. |
| 4 | `denubis-git-commit:commit` writes `Co-Authored-By: Claude`; global convention is `Claude Fable 5` | OPEN. |

## Discarded findings (false positives — do not "fix")

- Subagents claimed `EnterPlanMode` and `AskUserQuestion` are removed harness features. Both are live tools (verified in-session 2026-06-10). The claims were artefacts of audit-prompt priming.
- Lesson (from Brian's `claudew` alias): the right check is not "does tool X exist" but "is tool X guaranteed present in every session this skill runs in". Skills naming harness tools should carry an inline fallback ("if unavailable, ask inline"). Carry this check through the walk.
- Task vs Agent tool naming: genuinely unsettled (harness says Agent; repo convention mandates XML `Task` blocks). Needs a deliberate decision, not find-and-replace.

## Triage map (from survey, audited against main @ 723a454)

Tiers for the one-by-one walk, leverage-first:

1. ~~Hard breaks~~ (in progress, above)
2. Global CLAUDE.md — ~195 discrete instructions vs the 150 ceiling its own standards set. Largest removable blocks: Settings Sync runbook (→ .notes reference), .notes frontmatter spec, Git Commits (duplicates commit skill), Writing Prose section (→ writing-prose skill, keep one-line pointer). Writing Prose section violates its own positive-claim rule at L143–145.
3. using-plan-and-execute (102 lines, hook-injected every session) — EXTREMELY-IMPORTANT all-caps block is the documented overtriggering pattern; Fable 5 guidance now says over-prescription degrades output. Discussion needed: Brian may want some aggression retained.
4. Rubric sources — writing-claude-directives (BLOCKED on skill-skills-upstream-sync, see Collisions), writing-skills (missing Discipline in skill-type table; trim template), testing-skills-with-subagents (contains the dated-narrative anti-pattern writing-skills bans, `2025-10-03` verbatim; duplicate tables; ~422 lines).
5. Restructures: impl-plan-write (1348 — 3× near-verbatim workflow copies, 40-row rationalisation table, extract three-lens framework), executing-an-implementation-plan (1220 — extract example workflow; dedup turn budgets vs requesting-code-review), design-write (882 — extract 6 reference sections), systematic-debugging (737 — extract phases 3b/3c/3d). Borderline: howto-develop-with-postgres (614 — extract db-doc template), using-bibliography (800 — delete 135-line Provenance changelog).
6. Consolidations: merge-to-main/make-pr shared ~65-line block → shared file; critical-peer-review skill/agent name collision; pytest command single-source (coding-good-tests vs coding-python-idioms); FCIS-testing copy-paste block; marketplace schema canonical home (maintaining-a-marketplace), creating-a-plugin cross-refs; research-agents bidirectional cross-refs + academic-protocol relocation + paper-fetch contradiction vs using-bibliography; syncing-with-upstream → project docs (non-portable).
7. Long tail of minor fixes (descriptions to "Use when…", user-invocable flags, soften STOP footers, using-generic-agents stale benchmarks + missing Fable 5, coding-verify "you'll be replaced" line, etc.)

Full per-skill findings: in session transcript of 2026-06-10 audit (7 subagent reports). Key per-skill verdicts: 22 sound, 20 trim, 4 restructure, rest relocate/canonicalise.

## Collisions with in-flight worktrees

- `skill-skills-upstream-sync` (branch): **owns writing-claude-directives**. RESOLVED 2026-06-10: Phase 2 was found already complete (GREEN `089ab70`); a from-the-top staleness review produced the 2026-06-10 amendment pass, committed on the branch (`f2ef6c2`..`4d101a3`): new phase_02_6 (model-tier refresh reconciling the rubric-for-rubrics draft), phase_03/04 amendment blocks (dual-upstream refetch + drift survey, up-most-upstream pinning, dated imports, true-up sweep, Discipline skill-type fix, executor-tier test matrix), phase_05/06 re-verification annotations, RESUME-PROMPT rewritten (step-0 MERGE of main, not rebase — preserves the SHA-citing Phase 2 audit trail). Operator rule recorded: Fable-tier invocations are human-triggered only (cost). Resume via the worktree's RESUME-PROMPT. Already on that branch: "4.x"/"Opus 4.5 think" staleness fixed, model notes split into dated `model-tier-notes.md`, rhetorical-emphasis vs true-boundary imperative distinction, new epistemic-humility skill + Rubric Callback section, proleptic-challenger tightening. Its model-tier-notes is pinned 2026-04-17 (Opus 4.7 era) and by its own staleness rule is now expired (Opus 4.8 + Fable 5 released since).
  - Rule for this campaign: do NOT edit writing-claude-directives or its supporting files on main while that branch lives.
  - Open decision (Brian): land Phase 2 first then layer June-2026 intel, or amend the Phase 2 plan to absorb `2026-06-10-rubric-for-rubrics-draft.md` directly.
- `approver-rtk`, `denubis-dream`, `research-proposer-verifier`: unrelated to this campaign; no fold-in.

## June 2026 guidance deltas (fetched 2026-06-10, sources live)

For reconciliation into model-tier-notes.md and the rubric sources:

- Dedicated per-model prompting pages now exist: Fable 5 and Opus 4.8 (platform.claude.com/docs/en/build-with-claude/prompt-engineering/…).
- Fable 5: "Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality." Brief instructions steer as well as enumerations. Instructions to echo/transcribe internal reasoning can trigger `reasoning_extraction` refusals — audit skills for show-your-thinking phrasing. Longer turns by default; parallel subagents encouraged; memory systems (one lesson per file) recommended.
- Opus 4.8: under-reaches for tools/subagents/memory; fix is prescriptive trigger conditions in descriptions ("call this when…"), measurable lift. More narration by default (remove forced-progress scaffolding). Follows severity filters literally (report-everything-filter-downstream for review harnesses — relevant to code-reviewer agent + requesting-code-review).
- Aggressive-language dial-back confirmed current for all models; "Opus 4.5 think sensitivity" still documented but pinned to Opus 4.5 with thinking disabled only.
- Skill-authoring page now specifies: name ≤64 chars lowercase/hyphens, description ≤1024 chars third person, no XML tags, no reserved words "claude"/"anthropic"; TOC for reference files >100 lines; "old patterns" details block for time-sensitive content; evaluation-first development; test with every model tier that will run the skill.

## Project: writing-prose skill (task #5, Brian approved 2026-06-10)

Goal: one canonical home for Brian's calibrated Writing style, replacing the scattered copies and the dead house-style reference.

- Corpus (calibration sources, in authority order):
  1. `/home/brian/people/Brian/INTS1301/CLAUDE.md` § Bullet Voice (hand-calibrated killed/working patterns)
  2. `/home/brian/people/Jodie/BJET-Phase1-Longi-MixedMethods-RegReport/.notes/feedback_writing-prose.md` (academic-formal register; cites INTS1301 as upstream)
  3. `/home/brian/people/Mark/2026-WinterSchool/.notes/feedback_voice-when-authoring-new-prose.md` (slide-bullet sibling)
  4. Global CLAUDE.md "Writing prose" section (generalised descendant)
  5. Recovered upstream `writing-for-a-technical-audience` (git 1f9f44b^) — AI-tell phrase blacklist worth mining, register differs (developer docs)
- RED phase: mine "despair about writing style" chats via cc-search-chats for baseline failure modes (Brian: "there are lots").
- Must work across Sonnet 4.6, Opus 4.8, Fable 5 (and state what Haiku may not do with it). Test matrix per rubric-for-rubrics.
- Build per writing-skills RED-GREEN-REFACTOR with testing-skills-with-subagents.
- Open design questions: home plugin (revive denubis-house-style vs denubis-extending-claude); register scoping (academic prose vs slide bullets vs technical docs — one skill with modes, or sibling skills); relationship to global CLAUDE.md section (skill becomes canonical, CLAUDE.md keeps one-line pointer?).
- Execution: new worktree (decision pending Brian's confirmation).
- When done: design-write L334 repoints here; global CLAUDE.md Writing Prose section shrinks.

## Companion document

- `2026-06-10-rubric-for-rubrics-draft.md` (same directory): meta-rubric for directive standards across Sonnet/Opus/Fable. Status: DRAFT, input to skill-skills-upstream-sync Phase 2 reconciliation. Not yet applied anywhere.
