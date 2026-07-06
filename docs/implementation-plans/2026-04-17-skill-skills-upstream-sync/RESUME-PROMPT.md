# Resume Prompt — Skill-Skills Upstream Sync — Phase 4 COMPLETE; next Phase 6 → Phase 5

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** root the session in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is anything else, STOP — `cd` into the worktree or start a session rooted there.

---

I'm resuming the skill-skills upstream sync at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`, branch `skill-skills-upstream-sync`.

**State (2026-07-06 — Phases 1–4 COMPLETE; next execution target is Phase 6, then Phase 5):**

- **Phases 1, 2, 2.5, 2.6, 3: COMPLETE.** Unchanged.
- **Phase 4: COMPLETE and CLOSED.** All tasks (1–6) and the full review gate done: code review (Sonnet), proleptic (Opus), codex external (GPT-5.5), UAT provisional-confirm, and — the final gate step — the §3d refactor pipeline (2026-07-06). Refactor pipeline ran clean: smell-assessor (Opus) **0 findings**; gate skipped critical-peer-review + refactoring-executor; no code changed; 879 green. Closure recorded by dated append in `phase_04_green_verification.md`; full smell-report at `refactor-pipeline-smell-report-phase-4.md`. Closure commit `b0c8fb0`.
- **Remaining phases execute OUT OF NUMERIC ORDER: phase_06 → phase_05.** Phase 6 is cross-plugin hardening of `impl-plan-write`; Phase 5 is the terminal coherent-set commit (version bumps + marketplace + CHANGELOG) that must capture Phase 6's deltas, so Phase 6 lands first.

## Step-0 main merge — DONE (2026-07-06, merge commit `c702205`)

The branch was 58 commits behind `main`; merged clean via `git merge --no-ff main`. Branch is now **0 behind main**, full suite **1116 green** (was 879 pre-merge — main added net test suites). Three conflicts resolved: `pyproject.toml` (took main's `requires-python >=3.14`, kept this branch's `pyyaml>=6.0.3`; `uv.lock` regenerated via `uv add`), `CLAUDE.md` (both sides added a distinct convention section under Schema Constants — kept both). **Tooling gotcha for future merges:** conflict markers in the root `pyproject.toml` deadlock the `uv run`-based PreToolUse hooks (Edit/Write/Bash all blocked), because `uv` can't parse a TOML with `<<<<<<<` markers. Resolve any future root-`pyproject.toml`/`uv.lock` conflict from a plain terminal (outside Claude's tool hooks) first, then Claude's tools unblock.

**Phase 6 anchors have shifted — re-verify before editing.** With main merged, `impl-plan-write/SKILL.md` is **1350 lines** and the anchors phase_06 names against an assumed 1337 are now:
- three anti-smuggling tests (Decomposition / Reduction / Disagreement): lines **732 / 734 / 736** (phase_06 says 728–734).
- `## UAT Requirements Collation`: line **1298** (phase_06 says 1285).
Treat these as the current baseline but re-grep at execution — "exact boundaries determined at execution time."

**Phase 5 version baselines moved too:** denubis-extending-claude **1.8.0** (was 1.7.0), denubis-plan-and-execute **2.35.3** (was 2.30.0). Re-verify `.claude-plugin/marketplace.json` + `CHANGELOG.md` against these at Phase 5. Do not execute the plan on `main`.

## NEXT ACTION — Phase 6 (main merge done; re-verify anchors, then execute)

Invoke `denubis-plan-and-execute:executing-an-implementation-plan`, create a fresh task list for Phase 6 from `phase_06.md`, and execute it: convert the three anti-smuggling tests (Decomposition / Reduction / Disagreement) from rubric-as-text into a forcing gate in `impl-plan-write/SKILL.md` — template mandating `**What's automatable:**` / `**What's NOT automatable:**` before every UAT falsification template, three-lens-table amendment making "no UAT entry" first-class, per-phase ND rejection gate firing before user approval, Finalization existence gate on `uat-requirements.md`, one-time collation audit via a dedicated Sonnet subagent, and a retroactive audit of this plan's own accumulated UAT entries (`uat-audit-2026-04-17.md`). Phase Type: functionality. Full phase gate applies (code review → proleptic → UAT/coherence → refactor). Then Phase 5.

## Post-resume verification (run before any work)

```bash
pwd; git branch --show-current            # skill-skills-upstream-sync
git log --oneline -6
uv sync --all-packages && uv run pytest -q | tail -2   # 1116 passed (post-merge baseline)
git rev-list --count HEAD..main           # should be 0 (main merged 2026-07-06, c702205)
```

(`uv sync --all-packages` is required; uv.lock self-modifying its exclude-newer stanza is expected, not drift.)

## Carry-forwards

1. **V3 non-causal phrasing** binding: any GREEN claim stays "routes correctly / non-regressing n=1", never causal.
2. **R6 reconciliation still open** (Phase 3 V5): inline model anchors in `testing-skills-with-subagents/SKILL.md`; the uncommitted `docs/audits/2026-07-02-model-anchor-sweep.md` maps them. Reconcile at Phase 5.
3. **Edit path is ACCEPTED-and-bound, not tested:** task #7 (queued obra-import) must exercise the edit-re-entry rule against a boundary-condition scenario — see `phase_04_true_up_sweep.md` §"Boundary-condition specification (2026-07-05 proleptic CA1)" — not an incidental edit.
4. **Dispatch-time staleness check:** read `model-tier-notes.md` `last-verified` (2026-07-02) before dispatching subagents; if a model shipped since, HALT and re-verify.
5. **Dispatch reliability note (2026-07-06):** during the Phase 4 refactor pipeline, the first Opus smell-assessor dispatch (background) degenerated — 0 tool uses, echoed system/agent-registry boilerplate, no output file; recovered by one foreground re-dispatch (13 tool uses). If a subagent returns a non-response with **0 tool uses**, re-dispatch (foreground) once before treating it as turn exhaustion — this is a distinct failure mode from budget exhaustion.
6. **Model policy for this work (operator, 2026-07-05):** core pipeline agents = Opus (pinned explicitly). Fable and Codex call-outs are pre-authorised without cost-gate hesitation as a **session-scoped human trigger** — NOT a standing revocation of the Fable cost gate. Re-confirm per session; the standing cost-gate doctrine in `model-tier-notes.md` is unchanged.

## Queued / parked (do NOT start before Phase 6)

- **task #7 — obra-import work item** (`phase_04_true_up_sweep.md`, 2026-07-05 append): import obra's "Match the Form to the Failure" + "Micro-Test Wording" into the sub-skills; author a denubis-native worked example (repoint the worked-example reference); decide Rule-of-Three extraction of the V6 rubric-callback pair (`writing-claude-directives/SKILL.md:135` + `testing-skills-with-subagents/SKILL.md:36`); exercise the edit path per carry-forward 3.
- **Two uncommitted audit docs await operator read:** `docs/audits/2026-07-02-skill-engagement-audit.md`, `docs/audits/2026-07-02-model-anchor-sweep.md`. (Also untracked and parked: `.review/`.)
- **ISSUE-12** (`docs/issues.md`): "can it do it by default?" skill-authoring pre-check — candidate fold into task #7.
- **Minor tooling note:** `denubis-external-agents:codex-peer-review` v0.3.0 fails on a directory target (`cp: -r not specified`); file-only in practice — worth a fix/issue.

## Read first

1. `phase_06.md` incl. the L3 execution-order note and 2026-06-10 amendment — the next phase; re-verify every SKILL.md anchor after the step-0 main merge.
2. `phase_05.md` incl. the L3 note and 2026-06-10 amendment — terminal phase; re-verify version/marketplace/CHANGELOG baselines.
3. `phase_04_green_verification.md` — Phase 4 record incl. the 2026-07-06 refactor-pipeline closure append.
4. `phase_04_true_up_sweep.md` — task #7 + the edit-path/boundary-condition obligation.
5. `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` — tier doctrine (Sonnet 5 caution, advisor rules, Fable cost gate; last-verified 2026-07-02).

## Standing rules (unchanged)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, the Phase 2/2.5/2.6 GREEN/checkpoint artefacts, the Phase 3 records, or the Phase 4 GREEN/red/findings artefacts except by **dated append** — audit trail.
- Do not reverse the 2026-04-22/23 or 2026-06-10 amendment passes without explicit operator direction.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Fable cost gate (2026-06-10, extended):** never auto-dispatch Fable-tier subagents or set a Fable advisor on automated runs — human-triggered only. Pin `model` explicitly on every Agent dispatch. (See carry-forward 6 for the current session-scoped human authorisation.)
- **Operator rule (2026-07-02):** never configure Sonnet as advisor at any tier; treat Sonnet 5 outputs with heightened hallucination scrutiny — verify quotes/claims against files.
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
