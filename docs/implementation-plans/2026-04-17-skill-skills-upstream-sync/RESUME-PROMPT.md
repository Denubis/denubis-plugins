# Resume Prompt — Skill-Skills Upstream Sync — Post-Second-Revision Partial Checkpoint

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

---

I'm resuming work on the skill-skills upstream sync implementation plan at `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`.

**State (2026-04-19, post-second-revision partial):** The plan's second critical-peer-review (2026-04-18, in `critical-peer-review-2026-04-18.md`) returned NEEDS_REVISION with **15 findings (6 HIGH + 5 MEDIUM + 3 LOW + 1 META).** A revision session on 2026-04-19 worked **8 of 15 findings** (all 6 HIGH + M1 + M2) one-by-one using functional-decomposition discipline, with full Ripple Rule sweeps for the M6-reframe findings (H3/H4/H5). **All revision edits are uncommitted on main** — no commits made since 24a7848.

**7 findings remain outstanding:** M3, M4, M5, L1, L2, L3, Meta M7. This session halted here because (a) the user directed it, and (b) substantial revision scope over ~8 findings is the boundary where rushed additional work risks reproducing the same ripple-pattern the reviewer flagged.

## Read first

1. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/critical-peer-review-2026-04-18.md` — the 15 findings with correction directions (historical record; do NOT re-edit; addressed ones listed below).
2. `/home/brian/people/Brian/brian-ed3d-plugins/docs/issues.md` — **new this session** — local issue tracker covering deferred work. ISSUE-01 captures the xref-audit tool promotion + architecture-update template fix + skill-gates (this session's H1 scope grew into a tool-design thread that was correctly deferred). ISSUE-02 through ISSUE-10 cover unrelated deferred threads surfaced via chat-history audit.
3. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05.md` — Task 1 (cross-ref audit script, rewritten), Task 4.5 (frustration audit, CLI-safe rewrite)
4. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_06.md` — Task 4 Step 3 (H2 fix), Task 3 (H3+H4+H5 ripple), new Task 6 (illustrative-path rewrite for H1 support)
5. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/test-requirements.md` — AC5.4 (H1), AC5.5/5.6 (H6), AC6.6 (H3)
6. `/home/brian/people/Brian/brian-ed3d-plugins/docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/uat-requirements.md` — DR-P5-FRUST-1 (M2)
7. `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/MEMORY.md` — feedback memories active during this revision

## Session summary (what changed, by finding)

**HIGH — all 6 addressed:**

- **H1** — Cross-reference audit refactored. Old `FILE_RE` (bare-backticked filenames + `OBRA_SKIP` skip-list) replaced with:
  - `PATH_REF_RE` — requires `/` in the backticked string; optional `:N` or `:N-M` line-range suffix
  - `LINK_REF_RE` — markdown-link form `[text](path.md)`
  - `CONDITIONAL_PATHS` frozenset for deliberately-optional refs (currently: `.ed3d/implementation-plan-guidance.md`)
  - `resolve_xref` tries `skills/<name>/SKILL.md`, then `agents/<name>.md`, then `commands/<name>.md` — first hit wins. This fixes the pre-existing gap where agent refs like `denubis-basic-agents:sonnet-general-purpose` failed the old skill-only resolver.
  - New `--dump-matches` pre-audit spot-check mode (Task 1 Step 2, inserted between author and run)
  - **Convention**: path-form required for audit coverage; bare backticked filenames are prose vocabulary (not audited); teaching-material placeholders use angle-bracket prefix (`` `<your-service>/auth.py` ``) to opt out; conditional refs enumerated in `CONDITIONAL_PATHS`.
  - **Scope creep spun out to ISSUE-01**: the full-tool promotion (Typer CLI, architecture-update skill coverage, architecture-presence check, skill-gates hooks, template rewrites in architecture-update) is a separate design cycle. The H1 fix is compatible with it — regex semantics carry forward.
  - New **Phase 6 Task 6** added for illustrative-path rewrite in `impl-plan-write/SKILL.md` (11 inline `` `src/...` `` / `` `tests/...` `` teaching paths → angle-bracket form).
  - Verified by dry-run: new regex catches only real references; 4 XREF now resolve OK (agents); conditional `.ed3d/` path skipped; 11 impl-plan-write illustratives remain BROKEN pending Task 6 execution.

- **H2** — Phase 6 Task 4 Step 3 assertion `'Second defensive layer' in content` previously had no matching content in the inserted block. Added "the **Second defensive layer**" noun-phrase in the Step 2 inserted content so the assertion passes.

- **H3 + H4 + H5** — M6 reframe ("authoring-time rejection gate" → "pre-presentation self-audit") ripple swept across three locations the first revision missed:
  - test-requirements.md AC6.6 description (H3)
  - phase_05.md CHANGELOG 2.31.0 entry: New block, Fixed block, summary intro, and commit-message bullet — four downstream references in one file (H4 + adjacent)
  - phase_06.md Task 3 commit message + Step 1 header + AC6.6 Success criterion at phase head (H5 + adjacent)
  - Post-fix grep confirms only historical-record files retain old language (critical-peer-review-2026-04-17.md, critical-peer-review-2026-04-18.md). This is the Ripple Rule discipline the first revision skipped.

- **H6** — Commit count reconciled. Old ≥27/≥28 claims were inconsistent across test-requirements.md (≥27) and phase_05.md DoD (≥28). Task 4 Step 2 checklist had "Phase 5: 4" contradicting DoD's "Phase 5 (5)". Reconciled to **≥ 31 commits** after accounting for H3's Phase 5 Task 4.5 frustration audit (+1) and H1's Phase 6 Task 6 illustrative-path rewrite (+1). Updated:
  - test-requirements.md AC5.5 description
  - test-requirements.md AC5.6 per-phase breakdown + total
  - phase_05.md Task 4 Step 2 checklist (Phase 5: 5; Phase 6: 6+ explicit)
  - phase_05.md DoD breakdown

**MEDIUM — 2 of 5 addressed:**

- **M1** — AC6.7 line number at phase_06.md line 30 was "line 664" but actual three-lens table is at lines 681-686 (Popper row 683). Fixed.

- **M2** — AC5.8 frustration-audit queries used regex/OR/apostrophes/hyphens that cc-search-chats CLI cannot handle. Empirically verified this session: `cc-search-chats search "resume-aware"` crashes with `no such column: aware`; `search "we don't"` crashes with `fts5: syntax error`. Rewrote Task 4.5 Step 1 (time-window scoping via `--days N` plus post-filter) and Step 2 (safe one-term-per-query list: `mate`, `FFS`, `deeply frustrating`, `deeply frustrated`, `no stop`, `stop no`, `this is wrong`, `yoloed`, `oh god`, `jesus`; dropped apostrophe-crash queries with rationale; ISSUE-10 filed for upstream CLI fix). Updated DR-P5-FRUST-1 in uat-requirements.md to match.

**MEDIUM — 3 of 5 NOT addressed (outstanding):**

- **M3** — AC5.8 categorisation scheme (`GENUINE-FRUSTRATION` / `TECHNICAL-DISAGREEMENT` / `QUOTED-ILLUSTRATIVE` / `RESOLVED-IN-SESSION`) is not mutually exclusive. `RESOLVED-IN-SESSION` is a sub-case of `GENUINE-FRUSTRATION` (you can't resolve frustration that didn't exist). The verdict logic treats them as mutually exclusive, which means ambiguous "genuine-then-fixed" cases collapse to "RESOLVED-IN-SESSION" and under-report methodology failure. Reviewer suggested either making RESOLVED-IN-SESSION a subtype flag (joint label `GENUINE-FRUSTRATION + resolved-in-session`) or adding an explicit tiebreak rule. Needs a design decision before edit.

- **M4** — phase_06.md Task 2 Step 1 instructs "Apply the SAME amendment to DR2, DR3, DR4 templates" but acknowledges "they can be omitted for DRs that route entirely to test-requirement with no UAT entry." Actual template structure (impl-plan-write/SKILL.md ~lines 858-884): DR1 and DR3 take the falsification block and need amendment; DR2 and DR4 route to test-requirement and should NOT receive the `What's automatable` lines. Fix: name specifically which DR templates to amend. Small edit, no design decision required.

- **M5** — Plan assumes execution on a feature branch; AC5.5/5.6 use `git log main..HEAD` which returns zero if run on main itself. Currently the entire plan is uncommitted on main (confirmed: this session did not branch). Reviewer's fix (a): preflight step instructing executor to create a feature branch via `/using-git-worktrees` if HEAD == main. Reviewer's fix (b): change AC5.5/5.6 to track commits differently (e.g., path-filter). Option (a) is cleaner but requires a Phase 1 preamble or plan-level preflight. Needs decision: where does the preamble live? Options: new `phase_00.md`, top of `phase_01.md`, or a note in the main plan file's Done-when.

**LOW — 0 of 3 addressed (outstanding):**

- **L1** — Phase 5 Task 4.5 depends on the session's user being both executor and reviewer. Acknowledged limit; reviewer said it's Low. Decision: accept the note as-is, or add an acknowledgement in DR-P5-FRUST-1 that RED-evidence-style independent-session audit isn't available here.

- **L2** — `has_haiku_retirement` check in phase_02.md Task 3 Step 3 is overly permissive (`'retired' in content.lower() and 'Haiku' in content` matches unrelated prose). Belt-and-braces absence check is solid per reviewer. Fix: require specific context (e.g., `'retired' in content.lower() and 'Haiku 4.5' in content and 'judgement' in content.lower()`).

- **L3** — phase_05.md Task 2 CHANGELOG ordering check compares 2.31.0 vs 1.8.0 (new denubis-plan-and-execute vs older denubis-extending-claude) but doesn't verify 2.31.0 precedes the existing 2.30.0 entry for the same plugin. Fix: add `p30 = changelog.find('## [denubis-plan-and-execute] 2.30.0'); assert p29 < p30`.

**META — 0 of 1 addressed (outstanding):**

- **Meta M7** — If AC5.8's frustration audit were run on this review session's transcript, it would generate substantial `QUOTED-ILLUSTRATIVE` false positives (the review quotes `"mate"`, `"FFS"`, `"yoloed"`, `"that's wrong"` as query examples). Plan's scheme handles the case (via QUOTED-ILLUSTRATIVE category), but fatigue risk in joint review: if the reviewer fast-categorises, they may miss genuine matches. Reviewer suggested explicit fatigue-floor + calibration check. Medium-bordering-High severity.

## What changed in `docs/issues.md` (new file this session)

Created repo-local issues tracker (preferred over GitHub issues). Current entries:

- **ISSUE-01** — Promote `phase_05_cross_ref_audit.py` to common Typer-based tool with architecture coverage + skill-gates. Captures the full scope that H1 discussion uncovered: Typer CLI, architecture-update template updates, `docs/architecture/` presence check (WARN-only), and Claude Code hooks integration (PostToolUse / Stop / pre-commit-style) to run the audit automatically. Skill-gates = hooks that invoke a wrapper skill around the tool to fail cleanly.
- **ISSUE-02** — Agent teams integration design paused at Phase 2; Zendo experiment invalidated the inter-agent-messaging assumption. Needs halt-or-pivot decision record (not a design plan).
- **ISSUE-03** — Parts 2-4 of the upstream sync programme (umbrella: upstream innovations, critique skills, MELICA tuning) — sequenced behind ISSUE-06 + ISSUE-02.
- **ISSUE-04** — "Eyeball N%" → stratified-sampling skill (flagged in design plan's Additional Considerations).
- **ISSUE-05** — AbsenceJudgement fabricated-codes repo-wide audit — the codes (`TEMP/RAND/SCOP/VIBE/FABR` / `MECH/MTCH/SCAF/BOUN`) are not in the paper; current plan audits only the four touched skills. Could fold into ISSUE-01's tool as a "forbidden tokens" check.
- **ISSUE-06** — Plan never executed; uncommitted on main; no feature branch. (Relevant to M5 — they share root cause.)
- **ISSUE-07** — `/maintaining-project-context` never invoked post-plan. Systemic gap.
- **ISSUE-08** — "Fast test" sideline for `/commit` skill (user direction 2026-03-13, not landed).
- **ISSUE-09** — Resume-aware transcript archiving TODO (external plugin).
- **ISSUE-10** — `cc-search-chats` FTS5 fragility (hyphens + apostrophes crash). Upstream tool defect; workaround documented in M2 revision.

## User direction for the halting session

"resume prompt please" — halt-and-escalate after 8 findings worked. The user is aware the remaining 7 findings (M3-M5 + L1-L3 + Meta M7) exist and chose to break here rather than continue in this session.

## First concrete action for the next session

Ask the user which path:

1. **Continue the revision** — work M3-M5, L1-L3, Meta M7 one-by-one with the same functional-decomposition discipline this session used. Expected scope: 7 findings, probably 2-3 hours given the first batch took ~6-8 hours across 8 findings.

2. **Re-run `critical-peer-review` before committing** — this session's revisions were substantial enough that a third review would probably catch new ripple issues. Same rationale as the 2026-04-18 re-review that triggered this work. If the re-review finds regressions, those get worked before commit.

3. **Commit the current batch and handoff to execution** — addresses 8 of 15 review findings; leaves 7 open as documented here. Risks shipping a plan with known (but low-severity) outstanding findings. The user's global CLAUDE.md: "Never commit unless explicitly requested" — so this path requires explicit direction.

4. **Something else** — e.g., the user might want to work ISSUE-01 (tool promotion) as its own design cycle now rather than continue on the current plan's remaining review findings; or focus on M5 (branch discipline) alone because it's the only outstanding finding that blocks execution.

Do NOT default to committing. Global CLAUDE.md: "Never commit unless explicitly requested."

## What NOT to do without explicit direction

- Do not commit any changes. User's global rule: commits require explicit request.
- Do not re-execute critical-peer-review without asking first.
- Do not proceed to Execution Handoff without explicit direction.
- Do not batch-fix the remaining 7 findings without one-by-one decomposition (batch-fixing is the pattern the reviewer's first NEEDS_REVISION flagged; this session's ripple-sweep discipline is what improved the quality bar — keep it).
- Do not rewrite the revision-history notes inside the plan files (the `H1`/`H2`/`H3+H4+H5`/`H6`/`M1`/`M2` revision annotations + `M6 revision 2026-04-18` + `H1 revision 2026-04-19` + `M2 revision 2026-04-19` + `H6 revision 2026-04-19` markers are the audit trail — preserve them).
- Do not delete `docs/issues.md` or any ISSUE-NN entries — they are the deferred-work commitment.
- Do not try to re-run `cc-search-chats` from a background subagent — even with `bypassPermissions` mode, Bash is denied at a layer the mode doesn't reach. Main-session invocation works; subagents cannot reach the CLI.

## Task-list state at handoff

- Phases 1-6 planning complete + twice-revised (tasks completed + re-revised against the first review's 17 findings + this session's 8-of-15 findings from the second review)
- Finalization code-reviewer: ran once pre-first-revision; would need to re-run after the remaining 7 findings land if user picks path 1
- Test Requirements: AC5.4 (H1), AC5.5/5.6 (H6), AC6.6 (H3), AC5.8 unchanged (M3 still outstanding)
- UAT Requirements: DR-P5-FRUST-1 updated (M2); MECE issue (M3) still outstanding
- Critical peer review 2026-04-17 fully addressed (first-revision session)
- Critical peer review 2026-04-18 returned NEEDS_REVISION; 8 of 15 findings addressed (this session); 7 outstanding
- Execution Handoff — NOT started; depends on user decision
- **No commits made since 24a7848**; all revision work is uncommitted file edits on main

When resuming, start with `TaskList` (likely empty — task IDs #1-6 were marked completed and are only visible to the session that created them), then read this `RESUME-PROMPT.md` in full, then **read `docs/issues.md` too** (new this session), then ask the user the four-path question above before touching any file.

## Key conventions established this session

- **Path-form cross-reference convention** (H1): backticked path with `/` → audited; bare backticked filename → prose vocabulary; angle-bracket prefix → teaching placeholder (opts out); `CONDITIONAL_PATHS` frozenset → deliberately-optional refs (silently skipped).
- **Functional-decomposition discipline with Ripple Rule**: after any fix, grep the whole plan directory for all references to the changed claim/number/finding, update every downstream reference, confirm "I have done a full editing pass" before moving to the next finding. This session applied this discipline for H3+H4+H5 (four downstream references to the M6 reframe, all updated in one pass) and H6 (five downstream references to commit counts, all updated).
- **Repo-local issue tracking** (`docs/issues.md`) in preference to GitHub issues.
- **cc-search-chats CLI constraints** (ISSUE-10): single literal query, no regex, no OR, no apostrophes, no hyphens, `--days N` for time-window. Any skill or plan invoking it needs defensive query construction.
