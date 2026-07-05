# Resume Prompt — Skill-Skills Upstream Sync — Phase 4 Review Gate DONE except the Refactor Pipeline

**Copy this prompt verbatim into a fresh Claude Code session after `/clear`.**

**BEFORE PASTING:** root the session in the worktree:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/skill-skills-upstream-sync
git branch --show-current   # must print: skill-skills-upstream-sync
```

If the branch is anything else, STOP — `cd` into the worktree or start a session rooted there.

---

I'm resuming the skill-skills upstream sync at `docs/implementation-plans/2026-04-17-skill-skills-upstream-sync/`, branch `skill-skills-upstream-sync`.

**State (2026-07-05 — Phases 1–3 complete; Phase 4 Tasks 1–6 complete; Phase 4 review gate all done EXCEPT the refactor pipeline):**

- **Phases 1, 2, 2.5, 2.6, 3: COMPLETE.** Unchanged.
- **Phase 4 Tasks 1–6: COMPLETE** (`phase_04_green_verification.md`). GREEN 4/4 first run (Sonnet-tier, **non-causal reading binding**). V1–V7 dispositioned earlier.
- **Phase 4 review gate — completed steps (all committed, 2026-07-05):**
  - **Code review DONE** (Sonnet, scope `f04995f..87946b4`): APPROVED, 0C / 2I / 1M, worked one-by-one under halt-and-discuss. Imp#1 CSO preface confabulation FIXED (`68843a8`); Imp#2 edit-path-untested ACCEPTED non-blocking (obligation bound to task #7); Minor V6 — reviewer named the wrong pair, corrected in record. See `code-review-findings-phase-4.md` (`a38f3fc`).
  - **Proleptic challenge DONE** (Opus): 4 CAs. CA3 directory-wide claim-about-content sweep RUN — clean beyond the already-fixed CSO; CA1 edit-path obligation strengthened with boundary conditions; CA2 GREEN claim disambiguated ("non-regressing n=1, Sonnet-tier", not "validated"); CA4 V6-correction method recorded (`aa483e8`).
  - **Codex external peer review DONE** (GPT-5.5; provenance gate passed 6/6 quotes): 0 High / 1 Medium. Medium = the sweep record overclaimed "every/only"; reworded to a bounded claim + enumeration method + byte-identity caveat (`aa483e8`).
  - **UAT gate DONE** — provisional confirm, definitive deferred: five back-referenced deferred-observation entries (DR-P1-DR1/DR2/DR4, DR-P2-DR8, DR-P3-DR7) provisionally confirmed by operator; recorded in `uat-requirements.md` §"UAT gate outcome — 2026-07-05". ISSUE-12 flagged as the live novel case to shatter DR-P1-DR1/DR2/DR4 later.
- **Commits since previous handoff (`87946b4`):** `d1162ef` (ISSUE-12 filed) → `68843a8` (CSO fix) → `a38f3fc` (findings + dispositions) → `aa483e8` (proleptic + codex hardening) → UAT-record commit (tip).

## NEXT ACTION — the last Phase 4 gate step: the REFACTOR PIPELINE

Invoke `denubis-plan-and-execute:executing-an-implementation-plan` and run its §3d phase refactor over the Phase 4 files (`plugins/denubis-extending-claude/skills/writing-skills/`: `SKILL.md`, `README.md`, `anthropic-best-practices.md`, `render-graphs.js`, `examples/CLAUDE_MD_TESTING.md`):

1. Measurement (`wc -l`, `complexipy`, ast-grep rubric rules) → SCRATCHPAD.
2. `smell-assessor` (**pin model** — Sonnet or Opus; never Haiku/Fable).
3. Gate: empty findings → announce and skip to verify. Else `critical-peer-review` (scoped: evidence-grading only).
4. `refactoring-executor` on "proceed"-verdict findings only, one transformation at a time; revert on red.
5. Verify **879 tests green**; commit the refactor separately.

Most Phase 4 files are markdown/JS docs — smell yield is likely low; a near-empty assessment is expected and fine. Do NOT force refactors on prose. `anthropic-best-practices.md` and `render-graphs.js` are byte-identical obra imports — **out of scope for refactoring** (touching them breaks the verbatim/byte-identity claim).

**After the refactor pipeline, Phase 4 CLOSES.** Then execution order is **phase_06 → phase_05**.

## Post-resume verification (run before any work)

```bash
pwd; git branch --show-current            # skill-skills-upstream-sync
git log --oneline -6
uv sync --all-packages && uv run pytest -q | tail -2   # 879 passed
```

(`uv sync --all-packages` is required; uv.lock self-modifying its exclude-newer stanza is expected, not drift.)

## Carry-forwards

1. **V3 non-causal phrasing** binding: any GREEN claim stays "routes correctly / non-regressing n=1", never causal.
2. **R6 reconciliation still open** (Phase 3 V5): inline model anchors in `testing-skills-with-subagents/SKILL.md`; the uncommitted `docs/audits/2026-07-02-model-anchor-sweep.md` maps them. Reconcile at Phase 5.
3. **Edit path is ACCEPTED-and-bound, not tested:** task #7 (queued obra-import) must exercise the edit-re-entry rule against a boundary-condition scenario — see `phase_04_true_up_sweep.md` §"Boundary-condition specification (2026-07-05 proleptic CA1)" — not an incidental edit.
4. **Dispatch-time staleness check:** read `model-tier-notes.md` `last-verified` (2026-07-02) before dispatching subagents; if a model shipped since, HALT and re-verify.

## Queued / parked (do NOT start before Phase 4 closes)

- **task #7 — obra-import work item** (`phase_04_true_up_sweep.md`, 2026-07-05 append): import obra's "Match the Form to the Failure" + "Micro-Test Wording" into the sub-skills; author a denubis-native worked example (repoint the worked-example reference); decide Rule-of-Three extraction of the V6 rubric-callback pair (`writing-claude-directives/SKILL.md:135` + `testing-skills-with-subagents/SKILL.md:36`); exercise the edit path per carry-forward 3.
- **Two uncommitted audit docs await operator read:** `docs/audits/2026-07-02-skill-engagement-audit.md`, `docs/audits/2026-07-02-model-anchor-sweep.md`.
- **ISSUE-12** (`docs/issues.md`): "can it do it by default?" skill-authoring pre-check — candidate fold into task #7; MS "stop overloading your skills" post recorded unread/unverified.
- **Minor tooling note:** `denubis-external-agents:codex-peer-review` v0.3.0 fails on a directory target (`cp: -r not specified`); file-only in practice — worth a fix/issue.

## Read first

1. `phase_04_green_verification.md` — Task 6 record, V1–V7, and the three 2026-07-05 dated appends (CSO fix; proleptic sweep + CA2; codex rewording).
2. `code-review-findings-phase-4.md` — reviewer output + orchestrator corrections.
3. `phase_04.md` incl. the 2026-06-10 amendment — what the phase built and against what.
4. `phase_04_true_up_sweep.md` — task #7 + the edit-path/boundary-condition obligation.
5. `uat-requirements.md` §"UAT gate outcome — 2026-07-05".
6. `plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md` — tier doctrine (Sonnet 5 caution, advisor rules, Fable cost gate).

## Standing rules (unchanged)

- Do not execute the plan on `main`; all execution commits belong on this branch.
- Do not re-edit the H/M/L revision-history markers, the Phase 1 C1–C4 artefacts, the Phase 2/2.5/2.6 GREEN/checkpoint artefacts, the Phase 3 records, or the Phase 4 GREEN/red/findings artefacts except by **dated append** — audit trail.
- Do not reverse the 2026-04-22/23 or 2026-06-10 amendment passes without explicit operator direction.
- Do not route judgement-requiring subagent tasks to Haiku 4.5.
- **Fable cost gate (2026-06-10, extended):** never auto-dispatch Fable-tier subagents or set a Fable advisor on automated runs — human-triggered only. Pin `model` explicitly on every Agent dispatch.
- **Operator rule (2026-07-02):** never configure Sonnet as advisor at any tier; treat Sonnet 5 outputs with heightened hallucination scrutiny — verify quotes/claims against files.
- Do not push without checking with the user. The remote (`origin/skill-skills-upstream-sync` at `c394d63`) predates the 2026-04-22 rebase; any push needs `--force-with-lease` and explicit approval.
- Do not `git worktree remove` this worktree from inside it; `finishing-a-development-branch` handles cleanup.
