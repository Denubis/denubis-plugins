# Resume Prompt — Skill-Skills Upstream Sync — Phase 6 coherence review DONE; next: close coherence gate (code review + proleptic) → refactor pipeline → Phase 5

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** root the session in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is anything else, STOP — `cd` into the worktree or start a session rooted there.

---

I'm resuming the skill-skills upstream sync at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`, branch `skill-skills-upstream-sync`.

**State (2026-07-07 — Phases 1–4 COMPLETE; Phase 6 implementation + hardening COMPLETE; Phase 6 coherence review DONE, findings resolved/dispositioned):**

- **Phases 1, 2, 2.5, 2.6, 3, 4: COMPLETE and CLOSED.** Unchanged.
- **Phase 6 (executes BEFORE Phase 5): implementation + hardening + coherence review COMPLETE.** Prior gate steps (code review APPROVED, proleptic, 3-round adversarial test) done in earlier sessions. This session (2026-07-07):
  - ✅ **Coherence review** (coherence-reviewer, Opus) → "Coheres, no High findings"; 6 Medium + 2 Low. All worked one-by-one with the operator.
  - ✅ **M5** (the sharp finding: the disclosed-oracle check *taxed disclosure* — over-rejected honest mixed-signal entries). Operator chose to refine. Added a **mixed-signal SPLIT exception** to the gate. Blind Sonnet-5 re-validation (Fable-supervised) caught a **laundering hole** in the first wording (E7 downgraded FAIL→SPLIT via a coherence gestalt asserted outside "It's wrong if"); closed it with a **textual anchor** (SPLIT only if a human-triggerable wrongness condition survives inside "It's wrong if" after routing the boundary). Round-5 re-run over the extended **E1–E12** fixture: **12/12 match expected**, Fable ship ruling SHIP. Commits `29bbef8` (skill) + `68a3700` (record).
  - ✅ **M1** design-plan drift (AC6.6 said "blocks ND"; M6 reframe made it a non-blocking self-audit + collation-audit-as-structural-gate). Dated correction, commit `b3cafcf`.
  - ✅ **M4** existence gate checked file presence, not audit execution. Added an **audit-provenance stamp** the collation audit writes and the Finalization gate greps for. Commit `33b9144`.
  - ✅ **M3 (skill half)** efficacy phrasings ("actually prevents" / "close the gap") calibrated. Commit `33b9144`. **M3 CHANGELOG half → Phase 5 (binding, see carry-forward 1).**
  - ✅ **Fable adversarial pass** (2026-07-07, day-scoped auth) over the M1/M3/M4 fixes caught a fresh overclaim in the M4 stamp prose ("proves the audit ran over these entries" — grep can't back it) + consistency gaps. Corrected to **honest attestation** (the stamp attests the collation step ran, not that it scored every current entry) + **first-line-anchored grep** (`head -1 | grep -q '^<!-- collation-audit:'`) + design-plan cleanups (residual ND-gate language, AC6.8 stamp-ratification, E1–E12 in the maintenance note). Follow-up fix commit.
  - ⏳ **M2** → finalization: ADRs for the implementation-time additions (disclosed-oracle check, mixed-signal exception + anchor, M6 reframe ratification, M4 stamp).
  - ⏳ **M6** → finalization: `constraints.md` row + ADR giving the E1–E12 re-validation protocol a discoverable home.
  - **L1** (brittle `assert "What's automatable" not in dr4_block` in `phase_06.md` Task 2 — false-positive-FAILs now): NOTED only; `phase_06.md` is append-only audit trail; historical guard, phase passed when it ran. **L2** (only collation-tier wording was blind-tested): documented in the adversarial record's residual risk; the canonical/step-6.5 sites are planner guidance, not the structural gate.

## NEXT ACTION — close the Phase 6 coherence gate, then refactor pipeline, then Phase 5

Invoke `denubis-plan-and-execute:executing-an-implementation-plan`, create a fresh task list, and resume:
1. **Close the coherence gate.** Per the coherence fix-loop (fix → re-run code review → proleptic → re-present), run a **code review** over the four coherence-fix commits (`5706331..HEAD` = `5706331..33b9144`) and a **proleptic challenge**, then the operator confirms the gate closed. (The operator directed each fix explicitly and M5 had 5 adversarial rounds, so this is a confirmation pass, not a re-litigation.) **Re-confirm Fable authorization first — see carry-forward 3; if it's a new day the day-scoped grant has lapsed and reviews route to Opus.**
2. **Refactor pipeline** (§3d): measure → smell-assessor → gate → critical-peer-review → refactoring-executor → verify green. Target file: `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md` (Markdown; likely minimal smell surface).
3. **Phase 5** — re-verify version baselines (`denubis-extending-claude`, `denubis-plan-and-execute`) + `marketplace.json` + `CHANGELOG.md`; ship the ROUND-5 calibrated claim (carry-forward 1).
4. **Finalization** (after Phase 5, per executing-an-implementation-plan Stage 1/2): M2 ADRs + M6 constraints-home; Stage-2 ADR Proposed→Accepted.

## Post-resume verification (run before any work)

```bash
pwd; git branch --show-current            # skill-skills-upstream-sync
git log --oneline -8
uv sync --all-packages && uv run pytest -q | tail -2   # expect 1116 passed
git rev-list --count HEAD..main           # re-check behind-main; if >0, main advanced — assess before merging
```

HEAD at handoff: the `fix(impl-plan-write): honest stamp attestation…` commit on top of `33b9144` (run `git log --oneline -1` for its sha). This session's commits: `29bbef8` `68a3700` (M5), `b3cafcf` (M1), `33b9144` (M4+M3), then the resume-prompt commit and the Fable-review fix commit.

## Carry-forwards (UPDATED this session — act on these)

1. **Calibrated anti-smuggling claim for Phase 5 CHANGELOG (binding) — now the ROUND-5 version.** Supersedes the round-3 claim. Ship VERBATIM from `phase_06_adversarial_test.md` ("Updated calibrated claim (Fable-authored…)"): it states the gate rejects disclosed-oracle smuggles AND now SPLITs genuine mixed-signal entries, verified over E1–E12 across 5 rounds incl. the round-4 hole found+closed, plus the residual-risk footnote. **"structurally prevents" stays retired.**
2. **E1–E12 fixture + binding re-validation protocol (updated from E1–E8/E1–E10).** The full verbatim E1–E12 entry text is now IN `phase_06_adversarial_test.md` (backfilled — the original record kept only the E1–E8 scoring key). Any edit to the three anti-smuggling tests, the disclosed-oracle check, OR the mixed-signal exception in `impl-plan-write/SKILL.md` MUST be blind-re-validated against E1–E12 (Sonnet-5 gate = production tier; Fable supervises) reproducing the expected column (E1,E3,E4,E6,E7,E8,E9,E12 FAIL; E2,E5,E10 PASS; E11 SPLIT) before shipping. Inspection-equivalence is insufficient (rounds 2 AND 4 proved it).
3. **Fable authorization is DAY-SCOPED (operator, 2026-07-07): "use fable for all the reviews today until I tell you otherwise."** This session used Fable as adversary (E9–E12) + supervisor/adjudicator (rounds 4–5). The coherence review itself was Opus (dispatched before the Fable instruction). In a NEW session/day, RE-CONFIRM before any Fable dispatch — the standing Fable cost gate is human-triggered-only and the "today" grant lapses. Pin `model` explicitly on every dispatch. Gate-under-test in any re-validation MUST stay Sonnet 5 (production fidelity), Fable takes the supervisor seat.
4. **M2 finalization ADRs (implementation-time additions the design was silent on):** (a) disclosed-oracle check, (b) mixed-signal exception + "It's wrong if" textual anchor, (c) M6 reframe (self-audit non-blocking; collation audit = structural gate), (d) M4 audit-provenance stamp. Create at finalization Stage 1 §4c (status Proposed).
5. **M6 finalization:** `constraints.md` row + ADR giving the E1–E12 re-validation protocol a discoverable home (the repo already treats the anti-smuggling test as load-bearing at `constraints.md:87`).

## Carry-forwards (from prior resume prompts — still open)

6. **`.ed3d/implementation-plan-guidance.md` reference (SKILL.md)** is a path-form reference to a *consuming-project* file that does not exist in this repo — Phase 5's cross-reference audit must whitelist/skip it (NOT an illustrative `<src>/`/`<tests>/` placeholder).
7. **V3 non-causal phrasing** binding: any GREEN/verification claim stays "routes correctly / non-regressing n=1", never causal.
8. **R6 reconciliation still open** (Phase 3 V5): inline model anchors in `testing-skills-with-subagents/SKILL.md`; the uncommitted `docs/audits/2026-07-02-model-anchor-sweep.md` maps them. Reconcile at Phase 5.
9. **task #7 — obra-import work item** (`phase_04_true_up_sweep.md`, 2026-07-05): import obra's "Match the Form to the Failure" + "Micro-Test Wording"; author a denubis-native worked example; decide Rule-of-Three extraction of the V6 rubric-callback pair; exercise the edit path per the boundary-condition spec. Do NOT start before Phase 6 closes (it is now essentially closed — this becomes actionable after the refactor pipeline).
10. **Dispatch-time staleness check:** read `model-tier-notes.md` `last-verified` (2026-07-02, current as of 2026-07-07) before dispatching subagents; if a model shipped since, HALT and re-verify.
11. **Dispatch reliability:** a subagent returning a non-response with **0 tool uses** → re-dispatch (foreground) once before treating as turn exhaustion. (proleptic-challenger and Fable supervisor legitimately return 0 tool uses for pure-reasoning tasks — judge by whether the response is substantive.)
12. **Two uncommitted audit docs await operator read** (still untracked, parked): `docs/audits/2026-07-02-skill-engagement-audit.md`, `docs/audits/2026-07-02-model-anchor-sweep.md`.
13. **ISSUE-12** ("can it do it by default?" skill-authoring pre-check) — candidate fold into task #7.
14. **`denubis-external-agents:codex-peer-review` v0.3.0** fails on a directory target — file-only in practice.

## Standing rules (unchanged)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, the Phase 2/2.5/2.6 GREEN/checkpoint artefacts, the Phase 3 records, or the Phase 4 GREEN/red/findings artefacts except by **dated append** — audit trail. Phase 6 artefacts (`phase_06_adversarial_test.md`, `code-review-findings-phase-6.md`, `uat-audit-2026-04-17.md`) are part of that trail; the rounds-4–5 append + E1–E12 backfill followed the dated-append rule.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Fable cost gate (2026-06-10):** never auto-dispatch Fable-tier subagents or set a Fable advisor on automated runs — human-triggered only. Pin `model` explicitly on every Agent dispatch. Core pipeline agents = Opus (pinned). (See carry-forward 3 for today's day-scoped grant.)
- **Operator rule (2026-07-02):** never configure Sonnet as advisor at any tier; treat Sonnet 5 outputs with heightened hallucination scrutiny — verify quotes/claims against files.
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
