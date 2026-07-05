# Resume Prompt — Skill-Skills Upstream Sync — Phase 4 Tasks 1–6 DONE, Phase 4 Review Gate Next

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** Ensure your session is rooted in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is `main` or anything other than `skill-skills-upstream-sync`, STOP. Do not paste this prompt. Either `cd` into the worktree first or create a new session rooted there (`claude` from inside the worktree path).

---

I'm resuming work on the skill-skills upstream sync plan at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`. Execution takes place in this worktree on branch `skill-skills-upstream-sync`.

**State (2026-07-05, Phases 1–3 complete; Phase 4 Tasks 1–6 complete; Phase 4 review gate next):**

- **Phases 1, 2, 2.5, 2.6, 3: COMPLETE.** Unchanged; see the respective green-verification / rubric files (historical; dated append only).
- **Phase 4 Tasks 1–6: COMPLETE** through `6a53fc8` (`phase_04_green_verification.md`). GREEN 4/4 first run (Sonnet-tier, checks undisclosed, **non-causal reading binding** — static RED per amendment). Rubric walk-through surfaced V1–V7, all dispositioned with operator 2026-07-05: V1 edit-path serviced (`f88007c`), V2 human acceptance gate (`e25ce08`), V3 accepted, V4 restated + substance fixes (`16bac36`, `d3cc5c7`), V5 falsifiable exit (`aae5aef`), V6 watched-with-escalation, V7 dated labels (`a12e0c7`).
- **2026-04-22/23 and 2026-06-10 amendment passes: still in force.** Do not reverse.
- **Execution order:** `phase_04 (review gate remains) → phase_06 → phase_05`.

**New standing facts since the 2026-06-11 handoff:**

- **Sonnet 5 shipped 2026-06-30.** `model-tier-notes.md` re-verified 2026-07-02 (`65c847b`). Operator rules: **Sonnet 5 hallucination caution** (be super careful; operator-owned falsifier in the notes); **never configure Sonnet as advisor at any tier** (`4686fe4`); Fable-tier availability is intermittent.
- **Edit-path rule now live in the cornerstone** (`f88007c`): edits to tested skills re-enter the three-sub-skill sequence scoped to the change. The edit path itself has **no pressure scenario yet** — named limitation in `phase_04_green_verification.md`; the Phase 4 code review should weigh it.
- **Upstream drift recorded** (`a4b8403`, dated append in `phase_04_true_up_sweep.md`): obra added "Match the Form to the Failure" + "Micro-Test Wording" guidance (obra-observed, unpublished — import with attribution and evidence-grading). **Queued work item (do NOT start before Phase 4 closes):** import both into the sub-skills; then author a denubis-native worked example from real campaign evidence (phase_02/2.6/03 RED files + Phase 4 GREEN) and repoint the worked-example reference; decide the Rule-of-Three extraction of the rubric-callback duplication inside that same work item (both byte-identical instances share the "usually" nuance-clause defect — probe C2).
- **Probe findings committed:** `docs/audits/2026-07-05-form-taxonomy-probe.md` (10 findings / 5 files, 7 clean; epistemic-humility and model-tier-notes graded exemplary) — input to the import work item.
- **Process misses on record** (`phase_04_green_verification.md` §Process misses): duplicate CLAUDE_MD_TESTING copies consolidated (`d3cc5c7`, includes retraction of `16bac36`'s false 404 claim); CSO confabulation removed (`dd37aff`). Anthropic live best-practices doc verified unchanged 2026-07-05; obra's vendored copy has diverged from Anthropic (their agent-neutral rewording) — ours at pin `6fd4507` is closer to the Anthropic original.
- **UNCOMMITTED, awaiting operator read:** `docs/audits/2026-07-02-skill-engagement-audit.md` (51 skills: 37 keep / 12 revise / 2 investigate / 0 dead-weight; 262 quotes byte-verified) and `docs/audits/2026-07-02-model-anchor-sweep.md` (20 findings incl. stale "current models" lists in `writing-claude-directives/SKILL.md:69,96` and `using-generic-agents`' "(Sonnet 4.6 era)" — feeds the R6 reconciliation). Untracked `note20260621` still needs a home.

## Phase 4 review-gate carry-forwards

1. **V3 phrasing discipline:** any claim about the GREEN result stays non-causal ("routes correctly", never "the rewrite caused it").
2. **R6 reconciliation still open** (Phase 3 V5 → rubric-draft pending item 4): inline model anchors in `testing-skills-with-subagents/SKILL.md`; the 2026-07-02 anchor sweep (uncommitted) maps every instance repo-wide. Reconcile at Phase 5, or earlier if the reviewer flags it.
3. **Edit path untested** (see above) — surface to the reviewer explicitly; do not let the 4/4 creation-shaped GREEN stand in for it.
4. **Dispatch-time staleness check:** before dispatching review subagents, read `model-tier-notes.md`'s `last-verified` (2026-07-02); if a model shipped since, HALT and re-verify first.

## Post-resume verification (run before any work)

```bash
pwd                         # must end with .worktrees/skill-skills-upstream-sync
git branch --show-current   # skill-skills-upstream-sync
git log --oneline -3        # tip: RESUME-PROMPT update, then 64df493 (probe findings), 6a53fc8 (green verification)
uv sync --all-packages && uv run pytest -q | tail -2  # 879 passed before proceeding
```

(`uv sync --all-packages` is required — plain `uv sync` skips workspace members and pytest fails on `workflow_statusline`. uv.lock self-modifying its exclude-newer stanza is expected, not drift.)

## Then

**Invoke** `denubis-plan-and-execute:executing-an-implementation-plan` and run the **Phase 4 review gate**: code review via `requesting-code-review` (SCOPE: Phase 4 — commits `f04995f..HEAD` touching `plugins/denubis-extending-claude/skills/` + the plan-dir docs; pass `.ed3d/implementation-plan-guidance.md` if present), then proleptic challenge, then UAT gate (`uat-requirements.md` Phase 4 section carries back-referenced DR-P2-DR8 / DR-P3-DR7), then the refactor pipeline. Print every subagent response in full. On any reviewer findings: **halt and discuss every level with the operator one-by-one** (repo CLAUDE.md discipline) — the 2026-07-05 V-walk is the precedent; batch-fixing is a named trigger.

If anything feels sideways — tests failing, reviewer flagging structure, subagent empty response, upstream drift beyond the dated appends — HALT per repo CLAUDE.md.

## Read first

1. `phase_04_green_verification.md` — state of record for Task 6, V1–V7 dispositions, process misses, limitations.
2. `phase_04_true_up_sweep.md` — both dated appends (2026-07-02 Sonnet-5 pass; 2026-07-05 drift check + queued import).
3. `phase_04.md` including its amendment block — what the reviewer will be reviewing against.
4. `docs/audits/2026-07-05-form-taxonomy-probe.md` — corpus form-audit; context for reviewer findings that overlap it.
5. `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` — current tier doctrine (Sonnet 5 section, advisor rules, cost-gate scope).
6. `docs/issues.md` — ISSUE-06 (this plan), ISSUE-10 (cc-search-chats constraints + 2026-06-11 operator direction).

## Standing rules (unchanged + carried forward)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, the Phase 2/2.5/2.6 GREEN/checkpoint artefacts, the Phase 3 records, or `phase_04_green_verification.md` except by dated append — audit trail.
- Do not reverse the 2026-04-22/23 or 2026-06-10 amendment passes without explicit operator direction.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Operator rule (2026-06-10, extended 2026-06-11): never auto-dispatch Fable-tier subagents, schedule unattended Fable runs, or set a Fable advisor on automated runs — Fable invocations are human-triggered only (real-money cost).** Automated phase work runs on Haiku/Sonnet/Opus; pin `model` explicitly on every Agent dispatch (default inheritance would dispatch Fable).
- **Operator rule (2026-07-02): never configure Sonnet as advisor at any tier.** Operator rule (2026-07-02): treat Sonnet 5 outputs with heightened hallucination scrutiny — verify quotes and claims against files.
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
