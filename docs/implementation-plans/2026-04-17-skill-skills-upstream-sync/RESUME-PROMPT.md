# Resume Prompt — Skill-Skills Upstream Sync — Phase 6 IMPL+HARDENING complete; next: coherence review → refactor → Phase 5

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** root the session in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is anything else, STOP — `cd` into the worktree or start a session rooted there.

---

I'm resuming the skill-skills upstream sync at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`, branch `skill-skills-upstream-sync`.

**State (2026-07-06 — Phases 1–4 COMPLETE; Phase 6 implementation + adversarial hardening COMPLETE; Phase 6 gate PARTLY done):**

- **Phases 1, 2, 2.5, 2.6, 3, 4: COMPLETE and CLOSED.** Unchanged.
- **Phase 6 (executes BEFORE Phase 5): implementation + hardening COMPLETE, committed.** All six tasks landed; the full phase gate is PARTLY complete:
  - ✅ Code review → APPROVED after one bounded fix cycle (findings in `code-review-findings-phase-6.md`, commit `64ddb79`). Fixes: `ce5f82c` (skill) + `435be93` + `f061dfa` (plan alignment).
  - ✅ Proleptic challenge → surfaced CA3 (the anti-smuggling gate was never adversarially tested).
  - ✅ **Adversarial test (operator-authorised, Fable-supervised, 3 rounds) → COMPLETE.** Found a real hole (E3: a threshold disclosed in `This decision assumes` laundered into experiential register cleared the gate). Hardened the skill with a **disclosed-oracle check** at all three rubric sites (commit `fe13d35`), covering numeric AND relational/parity-to-baseline boundaries. Re-verified blind against the *verbatim shipped* rubric: 6/6 smuggle categories caught, 2/2 genuine-judgment controls held, zero regressions. Full record + E1–E8 regression fixture + Fable-authored calibrated claim + residual risk in `phase_06_adversarial_test.md` (commit `a39d25d`).
  - ⏳ **Coherence review** — NOT YET RUN. Phase 6 is `functionality` with ZERO native UAT entries (its `uat-requirements.md` section says so), so the routing rubric sends it to **coherence review** (`exec-coherence-review`), NOT the UAT gate.
  - ⏳ **Refactor pipeline** — NOT YET RUN (§3d of executing-an-implementation-plan: measure → smell-assessor → gate → critical-peer-review → refactoring-executor → verify green).
- **After Phase 6 closes: Phase 5** (terminal coherent-set commit: version bumps + `marketplace.json` + `CHANGELOG.md`). Phase 5 MUST capture Phase 6's deltas AND ship the calibrated anti-smuggling claim (see carry-forward 1 below).

## NEXT ACTION — resume the Phase 6 gate at the coherence review

Invoke `denubis-plan-and-execute:executing-an-implementation-plan`, create a fresh task list, and resume the Phase 6 gate:
1. **Coherence review** — announce `exec-coherence-review`, dispatch the coherence-reviewer (Opus, pinned) over Phase 6's changes vs the design intent. BASE for the phase = `4a243ef` (session-start HEAD before Phase 6). Note for the reviewer: the disclosed-oracle check is an implementation-time design ADDITION discovered by the adversarial test (not in the original phase_06 plan) — it's a candidate implementation-time ADR at finalization (Stage 1 §4c).
2. **Refactor pipeline** (§3d). Target file: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (Markdown; likely minimal smell surface).
3. Then **Phase 5** — re-verify version baselines (`denubis-extending-claude`, `denubis-plan-and-execute`) + `marketplace.json` + `CHANGELOG.md`; ship the calibrated claim.

## Post-resume verification (run before any work)

```bash
pwd; git branch --show-current            # skill-skills-upstream-sync
git log --oneline -14
uv sync --all-packages && uv run pytest -q | tail -2   # expect 1116 passed
git rev-list --count HEAD..main           # re-check behind-main; if >0, main advanced during the long 2026-07-06 session — assess before merging
```

Current HEAD at handoff: `64ddb79`. Key Phase-6 commits (this session): `2cd7e83` (cd-path retarget), `d2dd4aa` `817a55e`/`5eb2da3` `433671a` `3e8a181`/`178937c` `532d26c`/`bd36446` `c0417ea` (Tasks 1–6), `ce5f82c` `435be93` `f061dfa` (code-review + plan alignment), `ab534d6` (crash-recovery test fix), `fe13d35` `a39d25d` `64ddb79` (adversarial hardening + records).

## Carry-forwards (NEW this session — act on these)

1. **Calibrated anti-smuggling claim for Phase 5 CHANGELOG (binding).** Phase 5 must ship the Fable-authored claim VERBATIM from `phase_06_adversarial_test.md` — NOT "structurally prevents". It is: *"The UAT anti-smuggling gate rejects disclosed-oracle smuggling — entries whose 'This decision assumes' clause discloses a numeric or relational boundary that would settle the verdict in 'It's wrong if', regardless of how that verdict is phrased. Verified against 6 smuggle categories and 2 genuine-judgment controls across 3 adversarial rounds..."* plus the residual-risk footnote. "structurally prevents" is RETIRED for this gate.
2. **E1–E8 regression fixture + binding re-validation protocol.** Any future edit to the three anti-smuggling tests or the disclosed-oracle check in `impl-plan-write/SKILL.md` MUST be re-validated blind against the E1–E8 fixture (in `phase_06_adversarial_test.md`) before shipping — inspection-equivalence is insufficient (Round 2 proved it). A `Rubric maintenance` note in SKILL.md points here.
3. **Hardening `fe13d35` post-dates the phase code review.** The pre-merge code review (final-review Stage 5a) covers it; no separate per-phase re-review needed, but don't forget it exists.
4. **Fable authorization was session-scoped (operator, 2026-07-06):** the "Fable supervises round and round" trigger was for the adversarial test only. Do NOT auto-dispatch Fable in a new session — re-confirm per the standing cost gate. Fable was available 2026-07-06 (dispatches succeeded).
5. **Sibling crash_recovery test latent brittleness (optional):** `test_help_lists_expected_subcommands` shares the `FORCE_COLOR` ANSI-splitting brittleness that `ab534d6` fixed in its sibling; route it through the same `_strip_ansi` helper if convenient. Not blocking.
6. **`.ed3d/implementation-plan-guidance.md` reference (SKILL.md ~line 444)** is a real path-form reference to a *consuming-project* file that does not exist in this repo — Phase 5's cross-reference audit must whitelist/skip it (it is NOT an illustrative `src/`/`tests/` placeholder).

## Carry-forwards (from prior resume prompt — still open)

7. **V3 non-causal phrasing** binding: any GREEN/verification claim stays "routes correctly / non-regressing n=1", never causal.
8. **R6 reconciliation still open** (Phase 3 V5): inline model anchors in `testing-skills-with-subagents/SKILL.md`; the uncommitted `docs/audits/2026-07-02-model-anchor-sweep.md` maps them. Reconcile at Phase 5.
9. **task #7 — obra-import work item** (`phase_04_true_up_sweep.md`, 2026-07-05): import obra's "Match the Form to the Failure" + "Micro-Test Wording"; author a denubis-native worked example; decide Rule-of-Three extraction of the V6 rubric-callback pair; exercise the edit path per the boundary-condition spec. Do NOT start before Phase 6 closes.
10. **Dispatch-time staleness check:** read `model-tier-notes.md` `last-verified` (2026-07-02, re-read and current as of 2026-07-06) before dispatching subagents; if a model shipped since, HALT and re-verify.
11. **Dispatch reliability:** a subagent returning a non-response with **0 tool uses** → re-dispatch (foreground) once before treating as turn exhaustion. (Note: proleptic-challenger and Fable supervisor legitimately return 0 tool uses for pure-reasoning tasks — that is NOT the failure mode; judge by whether the response is substantive.)
12. **Two uncommitted audit docs await operator read** (still untracked, parked): `docs/audits/2026-07-02-skill-engagement-audit.md`, `docs/audits/2026-07-02-model-anchor-sweep.md`.
13. **ISSUE-12** ("can it do it by default?" skill-authoring pre-check) — candidate fold into task #7.
14. **`denubis-external-agents:codex-peer-review` v0.3.0** fails on a directory target — file-only in practice.

## Standing rules (unchanged)

- Do not execute the plan on `main`; all execution commits belong on this branch. (The phase_06.md `cd`-paths were retargeted to the worktree in `2cd7e83`.)
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, the Phase 2/2.5/2.6 GREEN/checkpoint artefacts, the Phase 3 records, or the Phase 4 GREEN/red/findings artefacts except by **dated append** — audit trail. (Phase 6 artefacts `phase_06_adversarial_test.md`, `code-review-findings-phase-6.md`, `uat-audit-2026-04-17.md` are now part of that trail.)
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Fable cost gate (2026-06-10):** never auto-dispatch Fable-tier subagents or set a Fable advisor on automated runs — human-triggered only. Pin `model` explicitly on every Agent dispatch. Core pipeline agents = Opus (pinned).
- **Operator rule (2026-07-02):** never configure Sonnet as advisor at any tier; treat Sonnet 5 outputs with heightened hallucination scrutiny — verify quotes/claims against files. (Applied this session: the Sonnet retroactive-audit + gate verdicts were orchestrator-verified against the entry text.)
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
