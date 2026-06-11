# Resume Prompt — Skill-Skills Upstream Sync — Phases 2.5 + 2.6 DONE, Phase 3 Next

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in this worktree on branch `skill-skills-upstream-sync`.

**State (2026-06-11, Phases 1, 2, 2.5, 2.6 complete; Phase 3 next):**

- **Phase 1 (epistemic-humility): COMPLETE** (10 commits, C1–C4 resolved). Unchanged since the 2026-04-23 handoff.
- **Phase 2 (writing-claude-directives): COMPLETE.** See `phase_02_green_verification.md` (historical; do not re-edit).
- **Phase 2.5 (preparatory refactor of testing-skills-with-subagents RED): COMPLETE.** Three-agent pipeline (smell-assessor → critical-peer-review → refactoring-executor) with one reviewer-required checkpoint revision. Result: two H3s inserted (`### Basic Baseline Checklist`, `### Synthetic Pressure-Scenario Example`), all verbatim blocks byte-identical. Commits `cdc9811` (split), `0f52233` (checkpoint). Phase-3 notes live in the checkpoint: line-339 edit-target note; M2 hazard (RED example near-duplicates GREEN great-scenario — Phase 3's demotion must decide merge vs cross-reference vs duplicate).
- **Phase 2.6 (model-tier refresh): COMPLETE.** Main refresh `c7659d9` + `47fca9d`; audits closeout `052bdca`; post-GREEN advisor addendum `93d572d`; code review to zero issues (`43778b9`, `5cb75fa`); 2026-06-11 advisor correction (`a97b0f3`, `6767b4f`); SKILL.md small refactor `eba4818` (281/300 lines); coherence review CONFIRMED with all findings fixed (`3c66720`, `ec544b9`, `a33bddb`, `7e4caea`, `0e4f22e`). See the GREEN artefact's two addenda + coherence closeout for the full audit trail.
- **2026-04-22/23 and 2026-06-10 amendment passes: still in force.** Do not reverse.

**New standing facts since the last handoff (2026-06-11):**

- **Advisor correction:** Claude Code docs (<https://code.claude.com/docs/en/advisor>) accept Fable as advisor for Haiku 4.5 / Sonnet 4.6 mains — conflicting with the platform API table. Both recorded in `model-tier-notes.md`, not resolved. **The Fable cost gate now covers advisor configuration** (advisor calls are model-triggered Fable spend; automated runs route advisors to Opus 4.8). Advisor is session main-loop only — no subagent attachment exists.
- **Doc-conflict house style:** repo `CLAUDE.md` → "Conflicting Authoritative Sources Are Recorded, Not Resolved". Phases 3/4 drift surveys follow it.
- **Operator-claim falsifiers:** the Fable cost gate and Haiku-no-judgement notes now carry operator-owned falsifiers (only dated operator notes/trials overturn them). Do not delete or weaken either position.
- **Standing test:** `tests/test_model_tier_freshness.py` enforces AC2.6.8's mechanisable subset on `model-tier-notes.md` (header date, per-URL verified markers, no bare `N.x`, anchored "current models"). Suite is now **879 passed**.

**Execution order:** `phase_03 → phase_04 → phase_06 → phase_05` (Phase 6 before Phase 5, per phase_05.md DoD).

## Phase 3 carry-forwards (from Phase 2.6 coherence closeout)

1. **Dispatch-time staleness check:** before executing Phase 3 tasks, read `model-tier-notes.md`'s `last-verified` header; if a model has shipped since, HALT and re-verify before building the executor-tier test matrix on it.
2. **Beta-surface caution (also binds Phase 4):** the advisor/task-budget claims are beta APIs outside the header-date tripwire — Phase 4's true-up sweep must re-verify them independently, not bless them because the header reads current.
3. The Real-World-Impact contradiction flagged in phase_03's amendment block was **resolved at `eb83f0f` (drop the section)** — do not re-litigate it.

## Post-resume verification (run before any work)

```bash
pwd                         # must end with .worktrees/skill-skills-upstream-sync
git branch --show-current   # skill-skills-upstream-sync
git log --oneline -3        # tip: RESUME-PROMPT rewrite, then 0e4f22e, 7e4caea
uv sync --all-packages && uv run pytest -q | tail -2  # 879 passed before proceeding
```

(`uv sync --all-packages` is required — plain `uv sync` skips workspace members and pytest fails on `workflow_statusline`. uv.lock self-modifying its exclude-newer stanza is expected, not drift.)

## Then

**Invoke** `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 3 (`phase_03.md` — restructure testing-skills-with-subagents). Read its `## 2026-06-10 Amendment` block first; it overrides matching base instructions (dual-upstream refetch + drift survey, executor-tier test matrix with Fable cost gate).

If any phase returns surprising results — tests failing, reviewer flagging structural issues, subagent empty response, upstream drift beyond what the amendment anticipated — HALT per the repo CLAUDE.md "HALT When Things Feel Sideways" discipline.

## Read first

1. `phase_03.md` including its amendment block.
2. `phase_02_5_smell_checkpoint.md` — Phase-3 notes section (line-339 edit target; M2 RED/GREEN near-duplicate hazard).
3. `phase_02_6_green_verification.md` — coherence closeout carry-forwards (historical record; append-only).
4. `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` (items 1–2 closed; R8 deferred — SKILL.md headroom now 19 lines) and `docs/audits/2026-06-10-skill-audit-campaign.md`.
5. `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` — current tier doctrine, advisor pairing, cost-gate scope.
6. Operator standing positions: Haiku-no-judgement — primary in-tree record is `model-tier-notes.md` (Haiku section, now with falsifier). The archived memory-file path in older docs is dead; do not "fix" it by deleting the position.
7. `docs/issues.md` — ISSUE-06 (this plan), ISSUE-10 (cc-search-chats FTS5 constraints: single literal term, no apostrophes/hyphens/regex).

## Standing rules (unchanged + carried forward)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, `phase_02_green_verification.md`, or the Phase 2.5/2.6 GREEN/checkpoint artefacts except by dated append — audit trail.
- Do not reverse the 2026-04-22/23 or 2026-06-10 amendment passes without explicit operator direction.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Operator rule (2026-06-10, extended 2026-06-11): never auto-dispatch Fable-tier subagents, schedule unattended Fable runs, or set a Fable advisor on automated runs — Fable invocations are human-triggered only (real-money cost).** Automated phase work runs on Haiku/Sonnet/Opus; pin `model` explicitly on every Agent dispatch (default inheritance would dispatch Fable).
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
