# Resume Prompt — Skill-Skills Upstream Sync — Phase 2 Complete, 2026-06-10 Amendments Applied, Step-0 Merge Then Phase 2.5

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in this worktree on branch `skill-skills-upstream-sync`.

**State (2026-06-10, Phase 2 complete, amendment pass applied, step-0 merge next):**

- **Phase 1 (epistemic-humility): COMPLETE** (10 commits, C1–C4 resolved). Unchanged since the 2026-04-23 handoff; see git history and `phase-01-*` artefacts.
- **Phase 2 (writing-claude-directives): COMPLETE.** Task commits `9ed5658` (RED static code-smell evidence), `6a29760` (SKILL.md restructure), `cc4176d` (model-tier-notes.md), `76faf34` (long-running-state-patterns anchors), `bb2f87f` (graphviz attribution); remediations `1fbd8c8` (V4), `3af9968` (V6 Gap 2); GREEN verification `089ab70`; post-GREEN touch-ups `8230047`, `0a2d607`, `acacdff`. See `phase_02_green_verification.md`.
- **2026-04-22/23 amendment pass:** still in force (static-RED reframe for preventive phases; FTS5-safe queries; operator-empirical Haiku-no-judgement retention). Do not reverse.
- **2026-06-10 amendment pass (operator-approved, this update):** the 2026-04 model tier went stale (Opus 4.8 and Fable 5 shipped; `model-tier-notes.md` tripped its own staleness wire), `/tmp` source materials vanished, and main drifted ~164 commits. Amendments: new `phase_02_6.md` (model-tier refresh + rubric-for-rubrics reconciliation); `phase_03.md` amendment block (dual-upstream refetch + drift survey, executor-tier test matrix with Fable cost gate, flagged Real-World-Impact contradiction for operator decision); `phase_04.md` amendment block (pin imports to up-most upstream at recorded hash, dated-import discipline for `anthropic-best-practices.md`, true-up sweep, Discipline skill-type fix, Fable-gated GREEN tiers); `phase_05.md`/`phase_06.md` post-merge re-verification annotations. Companion docs (on main; in-tree after step 0): `docs/audits/2026-06-10-rubric-for-rubrics-draft.md`, `docs/audits/2026-06-10-skill-audit-campaign.md`.

**Execution order:** `phase_02_5 → phase_02_6 → phase_03 → phase_04 → phase_06 → phase_05` (Phase 6 before Phase 5, per phase_05.md DoD).

## Step 0 — integrate main by MERGE, not rebase

Main is ~164 commits ahead of the 2026-04-22 merge-base `4d5c952`. **Merge `main` into this branch; do not rebase.** Reason: `phase_02_green_verification.md` and this file cite branch commit SHAs as the Phase 2 audit trail — a rebase rewrites them and orphans every citation; a merge preserves them. (The 2026-04-22 rebase predates any SHA-citing artefacts; that precedent no longer applies.)

```bash
git status --short            # expect: modified uv.lock, untracked .codex/
git diff uv.lock | head       # inspect; if incidental (no pyproject change), restore: git checkout -- uv.lock
# .codex/ is untracked tooling residue — inspect, then remove or leave (it is not part of the plan)
git merge main
```

Expected conflicts: `pyproject.toml` / `uv.lock` (branch added pyyaml at `98e4cf4`; main has moved both). Resolve pyproject by union of dependencies, then regenerate the lock: `uv lock`, and verify `uv run pytest` still passes (113+ root tests). Skill-file conflicts are not expected — main has not touched `writing-claude-directives` since the branch's edits (audit-campaign rule, 2026-06-10). HALT on any conflict outside pyproject/uv.lock/CHANGELOG/marketplace.

After the merge: confirm `docs/audits/2026-06-10-*.md` are present in-tree, then run the post-resume verification:

```bash
pwd                         # must end with .worktrees/skill-skills-upstream-sync
git branch --show-current   # skill-skills-upstream-sync
git log --oneline -3        # merge commit on top of acacdff
uv run pytest -q | tail -2  # all green before proceeding
```

## Then

**Invoke** `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 2.5 (preparatory refactor of testing-skills-with-subagents RED section), then Phase 2.6 (model-tier refresh) under the amended framing.

If any phase returns surprising results — tests failing, reviewer flagging structural issues, subagent empty response, upstream drift beyond what the amendment anticipated — HALT per the repo CLAUDE.md "HALT When Things Feel Sideways" discipline.

## Read first

1. `phase_02_6.md` — the new model-tier refresh phase (this is the first content phase after 2.5).
2. `phase_03.md` and `phase_04.md` — including their `## 2026-06-10 Amendment` blocks, which override matching instructions in the rest of each file.
3. `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` — R1–R11; Phases 2.6/3/4 cite specific R-items.
4. `docs/audits/2026-06-10-skill-audit-campaign.md` — the wider audit campaign this plan now interlocks with (esp. the rule that Phase 6 lands before the campaign's impl-plan-write restructure).
5. `phase_02_green_verification.md` — Phase 2 closure record (historical; do not re-edit).
6. Operator standing positions: Haiku-no-judgement — primary in-tree record is `model-tier-notes.md` (Haiku section). The original memory file `feedback_haiku-no-judgement.md` lived under `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/`, which was archived to `memory.archive-2026-05-22/` — the live path in older docs is dead; do not "fix" it by deleting the position.
7. `docs/issues.md` — ISSUE-06 (this plan), ISSUE-10 (cc-search-chats FTS5 constraints: single literal term, no apostrophes/hyphens/regex).

## Standing rules (unchanged + new)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, or `phase_02_green_verification.md` — audit trail.
- Do not reverse the 2026-04-22/23 or 2026-06-10 amendment passes without explicit operator direction.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **NEW (2026-06-10, operator rule): never auto-dispatch Fable-tier subagents or schedule unattended Fable runs — Fable invocations are human-triggered only (real-money cost).** Automated phase work runs on Haiku/Sonnet/Opus.
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
