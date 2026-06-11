# Resume Prompt — Skill-Skills Upstream Sync — Phase 3 DONE, Phase 4 Next

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in this worktree on branch `skill-skills-upstream-sync`.

**State (2026-06-11, Phases 1, 2, 2.5, 2.6, 3 complete; Phase 4 next):**

- **Phases 1, 2, 2.5, 2.6: COMPLETE.** Unchanged since the previous handoff; see `phase_02_green_verification.md`, `phase_02_5_smell_checkpoint.md`, `phase_02_6_green_verification.md` (all historical; dated append only).
- **Phase 3 (restructure testing-skills-with-subagents): COMPLETE** — 17 commits (`0adc63e` → `f04995f`). Drift survey clean; RED evidence sourced through the independent-session gate (`phase_03_red_evidence.md`); SKILL.md restructured with byte-identical preserved blocks; code review APPROVED zero issues (`code-review-findings-phase-3.md`); rubric self-application surfaced 8 vulnerabilities, all dispositioned and operator-acknowledged (`phase_03_rubric_self_application.md`); UAT entries DR-P3-DR7 + AM2-P3 armed; refactor pipeline ran (smell report + falsification review committed; sole surviving finding P2 fixed at `fbda343`).
- **2026-04-22/23 and 2026-06-10 amendment passes: still in force.** Do not reverse.

**New standing facts since the last handoff (2026-06-11, Phase 3 gate):**

- **Citation house style (operator-directed):** name-drops must point at readable sources — no "name-drops and walks away". Jones/Schön/AbsenceJudgement mentions point to `epistemic-humility`'s `absencejudgement-citations.md`; `exec-refactoring-rubric` gained a References section citing the **webpages actually consulted** (Mäntylä's taxonomy page, Fowler's online catalogue — NOT "Fowler (1999)", the book was never the source); Popper/Carnap/Fowler-ADR cited at first use across denubis-plan-and-execute. Brian's Zotero is the resolution path for citations (skill: `denubis-bibliography:using-bibliography`); chat-history search recovers what was actually consulted when provenance is unclear.
- **Qualifying-criteria checklist** is now part of the Conversation-Precedent Protocol (`41138e0`): observed-not-described, recorded independence argument, in-scope, externally confirmed, not self-licensing. Phase 4's RED evidence sourcing (H2 discipline) MUST apply it and record the answers.
- **ISSUE-10 operator direction:** improve cc-search-chats upstream (FTS5 quoting + worktree path round-trip) rather than re-documenting workarounds per consumer. Until then the constraints stand: single literal term per query, no hyphens/apostrophes, union in Python.
- **CA3 rule (now in phase_05.md):** audits recompute line/commit counts from files and git at audit time — never from phase-summary prose. Do not transcribe counts forward.
- **P2 template fix (`fbda343`):** phase_05's CHANGELOG template no longer claims the Haiku passage was "removed" (it was retained + reframed per the 2026-04-22 amendment). Do not reintroduce.
- Suite is **879 passed**.

**Execution order:** `phase_04 → phase_06 → phase_05` (Phase 6 before Phase 5, per phase_05.md DoD).

## Phase 4 carry-forwards

1. **Beta-surface caution:** the advisor/task-budget claims in `model-tier-notes.md` are beta APIs outside the header-date tripwire — Phase 4's true-up sweep must re-verify them independently, not bless them because the header reads current.
2. **V5 deferral (from Phase 3 walk-through):** inline model anchors (Haiku 4.5 / Sonnet 4.6 / Opus 4.8) in `testing-skills-with-subagents/SKILL.md` violate rubric R6 (model claims live in dated supporting files) — reconcile at Phase 4/5 via rubric-draft pending item 4. Recorded in `phase_03_rubric_self_application.md` V5.
3. **Rule-of-Three watch (smell C2/D1, reviewed-verified):** the rubric-callback summary sentence is byte-identical in `testing-skills-with-subagents` and `writing-claude-directives`; the qualifying-criteria idea appears in two places. If Phase 4's cornerstone adds a third instance of either, extract a shared reference instead of duplicating. See `phase_03_smell_report.md` + `phase_03_smell_review.md`.
4. **Dispatch-time staleness check:** before executing Phase 4 tasks, read `model-tier-notes.md`'s `last-verified` header; if a model has shipped since, HALT and re-verify.

## Post-resume verification (run before any work)

```bash
pwd                         # must end with .worktrees/skill-skills-upstream-sync
git branch --show-current   # skill-skills-upstream-sync
git log --oneline -3        # tip: RESUME-PROMPT rewrite, then f04995f, f12d8b2
uv sync --all-packages && uv run pytest -q | tail -2  # 879 passed before proceeding
```

(`uv sync --all-packages` is required — plain `uv sync` skips workspace members and pytest fails on `workflow_statusline`. uv.lock self-modifying its exclude-newer stanza is expected, not drift.)

## Then

**Invoke** `denubis-plan-and-execute:executing-an-implementation-plan` targeting Phase 4 (`phase_04.md` — rewrite `writing-skills` as cornerstone orchestrator, ≤250 lines, sequencing epistemic-humility → writing-claude-directives → testing-skills-with-subagents, with obra supporting-file imports). Read its `## 2026-06-10 Amendment (operator-approved)` block first; it overrides matching base instructions.

If any phase returns surprising results — tests failing, reviewer flagging structural issues, subagent empty response, upstream drift beyond what the amendment anticipated — HALT per the repo CLAUDE.md "HALT When Things Feel Sideways" discipline.

## Read first

1. `phase_04.md` including its amendment block.
2. `phase_03_rubric_self_application.md` — the 8 dispositions, especially V5 (binds Phase 4/5) and V2's now-in-skill checklist.
3. `plugins/denubis-extending-claude/skills/testing-skills-with-subagents/SKILL.md` — Phase 4 invokes this skill in practice; the Conversation-Precedent Protocol (with qualifying criteria) governs Phase 4's RED sourcing.
4. `docs/audits/2026-06-10-rubric-for-rubrics-draft.md` (pending item 4 = V5's reconciliation point) and `docs/audits/2026-06-10-skill-audit-campaign.md`.
5. `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` — current tier doctrine, advisor pairing, cost-gate scope.
6. `docs/issues.md` — ISSUE-06 (this plan), ISSUE-10 (cc-search-chats constraints + 2026-06-11 operator direction).
7. `phase_03_smell_review.md` — what the falsification review rejected and why (precedent for gating smell reports against closed decisions).

## Standing rules (unchanged + carried forward)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, the Phase 2/2.5/2.6 GREEN/checkpoint artefacts, or the Phase 3 records (`phase_03_red_evidence.md`, `phase_03_rubric_self_application.md`, smell report/review, code-review findings) except by dated append — audit trail.
- Do not reverse the 2026-04-22/23 or 2026-06-10 amendment passes without explicit operator direction.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Operator rule (2026-06-10, extended 2026-06-11): never auto-dispatch Fable-tier subagents, schedule unattended Fable runs, or set a Fable advisor on automated runs — Fable invocations are human-triggered only (real-money cost).** Automated phase work runs on Haiku/Sonnet/Opus; pin `model` explicitly on every Agent dispatch (default inheritance would dispatch Fable).
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
