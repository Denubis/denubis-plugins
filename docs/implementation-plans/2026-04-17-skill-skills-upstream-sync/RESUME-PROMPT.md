# Resume Prompt — Skill-Skills Upstream Sync — Phase 6 CLOSED; §3d done; Phase 5 STARTED then HALTED on stale model anchors → next: R6 model-anchor reconciliation, then release/4.5/finalization

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** root the session in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is anything else, STOP — `cd` into the worktree or start a session rooted there.

---

I'm resuming the skill-skills upstream sync at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`, branch `skill-skills-upstream-sync`.

**State (2026-07-07 — Phases 1–4 + 6 COMPLETE; Phase 6 gate CLOSED; §3d done; Phase 5 STARTED, then HALTED for escalation on stale model anchors):**

- **Phases 1, 2, 2.5, 2.6, 3, 4: COMPLETE and CLOSED.** Unchanged.
- **Phase 6 (executes BEFORE Phase 5): COMPLETE, coherence gate CLOSED.** This session (2026-07-07):
  - ✅ **Coherence gate closed.** Code review APPROVED (0 Critical / 0 Important / 2 Minor, both dispositioned one-by-one), proleptic engaged, external **codex** pass converged 0 findings. Codex caught an ordering contradiction the internal reviews missed (Finalization existence gate verified `uat-requirements.md` but the task graph placed Finalization BEFORE the tasks that write it). Fixed by reordering to **Test Requirements → UAT Requirements Collation → Finalization** (Finalization runs last, so its gate verifies already-written work). Commits `5e3e72f` (reorder + stamp/collation calibrations), `b182123` (AC6.6 pass/fail/split + findings record).
  - ✅ **§3d refactor pipeline** done as a **Fable read-only prose-structure pass** (the code pipeline — complexipy/ast-grep — is N/A on a Markdown skill, and the refactoring-executor would be a hazard near test-locked wording). Provenance-gated (Fable is non-Opus; verified line-level claims verbatim; flagged one overstated quantifier). Caught 3 residuals the gate-close reorder left and codex missed — **fixed in `9cad6da`**: handoff trigger (1471/1472) still said "After UAT Requirements collation completes" (announced "validated" before Finalization ran) → "After Finalization completes (existence gate passed)"; dead ref "UAT Requirements Generation" → "Collation"; batch-mode Task-NC dropped a bullet present in the other two branches. Full finding set + dispositions in **`refactor-pipeline-findings-phase-6-3d.md`** (`073dd2e`). **Deferred M1/M2/m3 (structural refactors) → the separate impl-plan-write worktree** (see carry-forward A).
- **Phase 5 (terminal): STARTED, re-baselined, then HALTED.** This session:
  - ✅ **Task 1 cross-reference audit** created + **refined + PASSES.** First run reported 32 failures; all were false-positives (24 inside the obra-vendored `anthropic-best-practices.md`; 6 bare-sibling markdown links resolved against repo-root not the file dir; 2 path-form labels missing the `./` convention prefix). Refined honestly (a real broken ref still FAILs): `VENDORED_VERBATIM` skips verbatim external imports when walking; markdown link-refs resolve md-dir-relative; the 2 labels got `./` in content. Commits `ddaadcc` (content), `fb35c1a` (script + execution note). Run: `python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py --repo-root "$PWD"` → PASS (37 refs, 0 broken). **NOTE:** must pass `--repo-root "$PWD"` (script's `DEFAULT_REPO_ROOT` hardcodes the MAIN checkout, not this worktree).
  - ✅ **Version baselines RE-BASELINED (2026-06-10 amendment).** Plan Task 2/3 targets (extending-claude 1.8.0, plan-and-execute 2.31.0) are **TAKEN** — both shipped on `main` for unrelated work while this branch's sync content sat **branch-only and unversioned** (`behind main = 0, ahead = 130`; `plugin.json` never bumped; `git diff main HEAD` = all sync content). **Re-baselined to next minor: extending-claude 1.9.0, plan-and-execute 2.36.0.** Documented in `phase_05.md` execution notes.
  - ⏳ **CHANGELOG entries DRAFTED but NOT written / NOT committed** (held — see NEXT ACTION step 2). Both drafts are in the 2026-07-07 session transcript.
  - 🛑 **HALTED for escalation.** Two blockers surfaced (operator chose halt-and-escalate rather than cram them into the session tail):
    1. **Model anchors are stale + internally inconsistent** (the operator: "we're at Opus 4.8, that's wrong"). Blocks the release — a 1.9.0 changelog cannot ship stale anchors as a feature.
    2. **impl-plan-write is bloated** (1475 lines vs 108–528 for the other sync skills). This is being handled in a **separate worktree** (carry-forward A) — NOT this branch's scope.

## NEXT ACTION — R6 model-anchor reconciliation, then finish Phase 5, then Finalization

**Re-confirm Fable authorization before any Fable dispatch** (carry-forward B). Then:

1. **Model-anchor R6 reconciliation (THE blocker for the release).** The parked **`docs/audits/2026-07-02-model-anchor-sweep.md`** is the map (20 findings; still untracked — commit or consume it here). Current tier: **Opus 4.8 / Sonnet 5 / Haiku 4.5 / Fable 5**. The state is stale AND internally inconsistent:
   - `writing-claude-directives/SKILL.md` body already says "Opus 4.8, Fable 5" but still "Sonnet 4.6" (stale — Sonnet 5 shipped 2026-06-30).
   - `model-tier-notes.md` (the sweep's sanctioned dated home; 26 anchor sites) and `long-running-state-patterns.md` (8) still say "Opus 4.7 / Sonnet 4.6" — trailing the body and reality.
   - Do it properly: **VERIFY current model facts against docs** (context7 / platform.claude.com — do NOT blind-rename 4.7→4.8 / 4.6→5; pricing/effort-control/capability properties may have changed). Update `model-tier-notes.md` + `long-running-state-patterns.md` to current, and **de-inline the SKILL-body anchors per the sweep's R6 findings** (`writing-claude-directives/SKILL.md:69,96,98,127,217`; `testing-skills-with-subagents/SKILL.md:63`) so model claims live in the one dated file. Resolve the body-vs-supporting-file inconsistency. **⚠ `testing-skills-with-subagents/SKILL.md` is a tested skill** — inline-anchor edits there need its pressure-scenario re-check (V5 carry-forward). **Also honours carry-forward: R6/V5 reconciliation was slated for exactly this Phase 4/5 boundary.**
2. **Version bumps + CHANGELOG (Tasks 2–3, re-baselined).** extending-claude **1.8.0→1.9.0**, plan-and-execute **2.35.3→2.36.0**. For each: `plugin.json` + repo-root `.claude-plugin/marketplace.json` + prepend `CHANGELOG.md` entry; run the plan's triad-sync verifier (Task 2/3 Step 4), adjusting the asserted version strings to 1.9.0 / 2.36.0. **Atomic triad commit per plugin.** The 1.9.0 entry: plan Task 2 template + `long-running-state-patterns.md` model-anchor bullet + **corrected anchors from step 1** (NOT "Opus 4.7 / Sonnet 4.6"). The 2.36.0 entry: authored fresh to reflect the as-shipped Phase 6 state (disclosed-oracle check, mixed-signal SPLIT + "It's wrong if" anchor, two-layer self-audit+collation, provenance stamp, Test→UAT→Finalization order) + the **round-5 calibrated claim VERBATIM** (`phase_06_adversarial_test.md:121`, carry-forward: ship verbatim, "structurally prevents" stays retired) + the incidental plan-and-execute deltas on-branch (`proleptic-challenger` counterargument-naming `c3952f8`; citations pass `a783949`/`419e7d0`). Drafts are in the 2026-07-07 transcript.
3. **Task 4.5 frustration-signal audit (AC5.8).** Needs **joint human review** with the operator (cc-search-chats queries → categorise). See `phase_05.md` Task 4.5 for the CLI constraints + query set + fatigue-floor/calibration guardrails. Produces `phase_05_frustration_audit.md`.
4. **Task 4 final verification.** Re-run the cross-ref audit (with `--repo-root "$PWD"`); branch-discipline guard; commit-discipline + DoD checks; Phase 5 UAT entry appended to `uat-requirements.md`.
5. **Finalization (after Phase 5).** M2 ADRs (disclosed-oracle check; mixed-signal exception + "It's wrong if" anchor; M6 reframe; M4 stamp) + M6 `constraints.md` row/ADR for the E1–E12 re-validation protocol; Stage-2 ADR Proposed→Accepted.

## Post-resume verification (run before any work)

```bash
pwd; git branch --show-current            # skill-skills-upstream-sync
git log --oneline -8
uv sync --all-packages && uv run pytest -q | tail -2   # expect 1116 passed
git rev-list --count HEAD..main           # expect 0 (main has not advanced past this branch)
python3 docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/phase_05_cross_ref_audit.py --repo-root "$PWD"  # expect PASS
```

HEAD at handoff: `fb35c1a`. This session's commits (oldest→newest): `5e3e72f` `b182123` (gate-close), `9cad6da` (§3d residual fixes), `073dd2e` (§3d findings), `ddaadcc` `fb35c1a` (Phase 5 audit script). behind main 0 / ahead 130.

## Carry-forwards (act on these)

A. **impl-plan-write SIZE REDUCTION is a SEPARATE worktree, halted pending THIS sync landing (operator, 2026-07-07).** It is NOT this branch's Phase 5 scope — do NOT shrink impl-plan-write here. The §3d findings (`refactor-pipeline-findings-phase-6-3d.md`: M1 steps-1–3 triplicated ×3; M2 doctrine block lacks subheadings; m3 stamp-template dup; optional m4/m6/m7) are the INPUT for that worktree. **Coordination flag:** that worktree must rebase on this branch's heavy impl-plan-write edits once this sync lands; expect conflicts on `impl-plan-write/SKILL.md`.
B. **Fable authorization: operator re-opened it this session** ("any work we can do with fable is probably a good idea", 2026-07-07) — used for the §3d prose pass. This may lapse; the standing Fable cost gate is human-triggered-only. **Re-confirm before any Fable dispatch in a new session.** Pin `model` explicitly. Gate-under-test in any E1–E12 re-validation MUST stay Sonnet 5 (production fidelity); Fable supervises.
C. **Round-5 calibrated anti-smuggling claim (binding, ships in the 2.36.0 CHANGELOG).** Verbatim from `phase_06_adversarial_test.md:121`. States the gate rejects disclosed-oracle smuggles AND SPLITs genuine mixed-signal entries, verified over E1–E12 across 5 rounds (incl. the round-4 hole found+closed). "structurally prevents" stays retired.
D. **E1–E12 fixture + binding re-validation protocol.** Any edit to the three anti-smuggling tests / disclosed-oracle check / mixed-signal exception in `impl-plan-write/SKILL.md` MUST be blind-re-validated against E1–E12 (Sonnet-5 gate = production tier; Fable supervises) reproducing the expected column (E1,E3,E4,E6,E7,E8,E9,E12 FAIL; E2,E5,E10 PASS; E11 SPLIT). Inspection-equivalence is insufficient (rounds 2 AND 4 proved it). The reorder + §3d residual fixes this session touched none of the three test copies, so no re-validation triggered.
E. **Two parked untracked audits await operator read:** `docs/audits/2026-07-02-model-anchor-sweep.md` (the R6 map — consume at step 1), `docs/audits/2026-07-02-skill-engagement-audit.md`.
F. **M2/M6 finalization ADRs** — see NEXT ACTION step 5.
G. **`.ed3d/implementation-plan-guidance.md`** is a conditional path (in the audit's `CONDITIONAL_PATHS`); a consuming-project file absent here by design — not a broken ref.
H. **V3 non-causal phrasing** binding: any GREEN/verification claim stays "routes correctly / non-regressing n=1", never causal.
I. **Dispatch-time staleness check:** read `model-tier-notes.md` `last-verified` before dispatching subagents; if a model shipped since, HALT and re-verify (this is now overdue — Sonnet 5 shipped 2026-06-30; step 1 addresses it).
J. **Dispatch reliability:** a subagent non-response with **0 tool uses** → re-dispatch (foreground) once before treating as turn exhaustion. (proleptic-challenger + Fable supervisor legitimately return 0 tool uses for pure reasoning.)

## Standing rules (unchanged)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the Phase 1 C1–C4, Phase 2/2.5/2.6 GREEN/checkpoint, Phase 3, Phase 4, or Phase 6 audit-trail artefacts except by **dated append**. (`phase_05.md` is the un-executed Phase 5 plan — refining it at execution time is fine; it's not frozen.)
- Do not route judgement-requiring subagent tasks to Haiku.
- **Fable cost gate (2026-06-10):** never auto-dispatch Fable-tier subagents or set a Fable advisor on automated runs — human-triggered only. Pin `model` explicitly. Core pipeline agents = Opus. (Carry-forward B is this session's grant.)
- **Operator rule (2026-07-02):** never configure Sonnet as advisor at any tier; treat Sonnet outputs with heightened hallucination scrutiny — verify quotes/claims against files. (Applied this session to the codex + Fable passes.)
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it.
