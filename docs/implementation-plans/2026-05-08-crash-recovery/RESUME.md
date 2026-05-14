# Resume — denubis-crash-recovery planning session

**Last updated:** 2026-05-14
**Branch:** `crash-recovery` (in `.worktrees/crash-recovery/`)
**HEAD:** `28ebf21 docs(crash-recovery): add implementation plan with test + UAT requirements`
**Upstream gap:** 5 commits ahead of `origin/main` (design plan, arch pin, bibliography fix, design rename, implementation plan).

---

## Start the next session inside the worktree

The previous session ran from the main checkout (`/home/brian/people/Brian/brian-ed3d-plugins`) instead of the worktree, writing to the worktree via absolute paths only. That worked but added friction. Open the next session inside the worktree directly:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery
claudew --resume <session-uuid-if-resuming>   # or just: claudew
```

Then verify state on the first turn:

```bash
pwd                        # should print .../.worktrees/crash-recovery
git branch --show-current  # should print crash-recovery
git log --oneline -3       # most recent should be 28ebf21
```

If any of those are wrong, halt and re-set CWD before doing anything else.

---

## What's done

- ✅ Worktree created at `.worktrees/crash-recovery` on branch `crash-recovery`.
- ✅ Bibliography description fix committed (`93a0f64`) — pre-existing baseline test failure resolved.
- ✅ Design plan patched in place: renamed `crash-recovery` → `denubis-crash-recovery` for repo's `denubis-*` prefix convention; widened repo-root `testpaths` directive documented. Committed at `1abee13`.
- ✅ 8 implementation phase files written: `phase_01.md` through `phase_08.md`. Each has frontmatter (Goal/Architecture/Tech Stack/Scope/Phase Type), AC coverage section, task markers (`<!-- START_TASK_N -->`), subcomponent markers where applicable.
- ✅ `test-requirements.md`: 34 ACs → 31 AUTOMATED + 2 HUMAN_JUDGEMENT + 1 MIXED. No UNCOVERED.
- ✅ `uat-requirements.md`: 3 entries (Phase 7 DR2 prune-prompt clarity, Phase 8 AC5.6 post-reboot, Phase 8 AC6.4 idle-kill).
- ✅ Code-reviewer (plan-validation, `denubis-plan-and-execute:code-reviewer`) ran TWO cycles:
  - Cycle 1: APPROVED — CHANGES REQUIRED. 4 Important + 3 Minor findings (I1-I4 + M1-M3), all clustered in Phase 4 spec gaps + cross-phase reference issues. Findings file: `code-review-findings-plan-validation.md` in this directory.
  - Cycle 2 (re-review against `PRIOR_FINDINGS_FILE`): APPROVED. All 7 findings VERIFIED resolved; no new issues introduced.
- ✅ Everything committed at `28ebf21`.

## What's next (in order)

### 1. Critical peer review (task #4, in_progress at session halt)

Dispatch `denubis-plan-and-execute:critical-peer-review` (NOT the code-reviewer — this is the falsification-first audit, a different agent). The full prompt for the dispatch was drafted in the previous session and should be re-built fresh.

**Key falsification suspects to put in the prompt** (these came out of designing the dispatch in the prior session, worth preserving):

1. **Overclaiming around UAT automation.** AC5.6 and AC6.4 require real-machine reboot/SIGKILL — does the plan ever implicitly claim CI coverage? The `test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive` in Phase 4 Task 5 covers the *rule wiring*; only the post-reboot UAT covers the actual reboot-safety story.
2. **The "unreachable" defensive fallback.** Phase 2's `classify()` ends with `return Classification(BORDERLINE, "unmatched")`. Phase 5's partition test now explicitly includes `"unmatched"` (per the M3 fix). If `RULES` truly partitions the input space, the fallback is unreachable. Is "unreachable but covered by tests" coherent, or is the fallback masking a partition gap?
3. **Two-phase re-classification labelled PROGRESSIVE.** Phase 4 DR2 claims Lakatos PROGRESSIVE. Is this warranted, or routine?
4. **POSIX `rename(2)` atomicity on non-local filesystems.** Phase 8 DR2 promises atomic liveness file creation via temp+mv. Holds on ext4/btrfs. Does it hold on NFS, FUSE, tmpfs? Plan is Linux-only by design — but worth surfacing whether "Linux" means "all Linux filesystems".
5. **Phase 1's testpaths widening side-effect.** Widening to `["tests", "plugins/*/scripts/*/tests"]` starts collecting `workflow_statusline` tests. Plan calls this "acceptable" without verifying those tests pass under the wider invocation.
6. **`boot_id=unknown` on non-Linux hosts.** Wrapper falls back to `boot_id=unknown` if `/proc/sys/kernel/random/boot_id` is unreadable. Phase 3's `current_boot_id()` would also fail. If BOTH return `unknown`, they MATCH trivially. Does the plan address this case?
7. **`sessions` ↔ `classification_history` foreign key.** Phase 6's prune deletes from `sessions` but NOT from `classification_history`. Schema has no FK. Intentional, or missed cleanup?
8. **Phase-boundary independence.** Phase 2's tests synthesise inputs directly (no caller chain to Phase 4). Phase 3 same. Phase 7's bats smoke test depends on Phases 4/5/6's CLI subcommands. Do all phases pass tests independently as the plan promises, or do some require later phases to compile?

The full first-cycle prompt template (slightly trimmed) was:

> Conduct a falsification-first peer review… treat the prior code-reviewer's verdict (APPROVED, all findings resolved) as untrusted — do your own audit… for each finding state: severity (Critical/Important/Minor/Flagged), evidence (specific quote or file:line), what this means, recommended remediation. End with verdict: APPROVED / NEEDS_DISCUSSION / NEEDS_REVISION.

Output should go to a new findings file alongside `code-review-findings-plan-validation.md` — suggested name: `critical-peer-review-findings.md`.

**Decision rule after the review:**
- If APPROVED → mark #4 done, proceed to #5 execution handoff.
- If NEEDS_DISCUSSION or NEEDS_REVISION → HALT and discuss findings one at a time with the human (per project CLAUDE.md HALT-when-sideways trigger: "Multiple findings at the Important level"). Do NOT batch-fix.

### 2. Execution handoff (task #5)

Per `denubis-plan-and-execute:starting-an-implementation-plan` skill, lines 261-323:

1. `git rev-parse --show-toplevel` from inside the worktree → captures absolute path (will be `.worktrees/crash-recovery`).
2. `ls -d "${WORKING_ROOT}/docs/implementation-plans/2026-05-08-crash-recovery"` → verify plan dir exists.
3. Output copy-paste instructions in the form:

   ```
   Implementation plan complete!

   **IMPORTANT: Copy the command below BEFORE running /clear (it will erase this conversation).**

   (1) Copy this command:
   /denubis-plan-and-execute:executing-an-implementation-plan /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/ /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/

   (2) /clear
   (3) Paste and run.
   ```

   Both paths absolute, both verified by Step 1-2. Pass the **directory**, not `phase_01.md`.

---

## State pointers

### Implementation plan files (committed at `28ebf21`)

All under `docs/implementation-plans/2026-05-08-crash-recovery/`:

| File | Purpose |
|---|---|
| `phase_01.md` | Plugin scaffold + DB schema + `crash-recovery init` (6 tasks, infrastructure phase, AC1.1/AC1.3/AC1.4/AC2.3/AC2.4/AC2.5) |
| `phase_02.md` | JSONL tail parser + classify rule table (5 tasks, functionality, AC3.1/AC3.3/AC3.4/AC3.5) |
| `phase_03.md` | Liveness primitives + correlate (5 tasks, functionality, parser side of AC5.1/AC5.4/AC5.6 + AC6.1) |
| `phase_04.md` | `scan` subcommand (5 tasks, functionality, AC3.6 + AC5.6 end-to-end + AC6.2 + AC6.3) |
| `phase_05.md` | `render` subcommand + markdown contract (6 tasks, functionality, AC2.1 advance + AC2.2 + AC3.2 + AC4.4 + AC7.1) |
| `phase_06.md` | `note`/`history`/`prune`/`list-live` (6 tasks, functionality, AC4.1/4.2/4.3/4.5 + AC7.2-AC7.7) |
| `phase_07.md` | Triage skill + bats smoke (3 tasks, infrastructure, AC1.2 + AC8.1) |
| `phase_08.md` | Wrapper patch + version bumps + bats lifecycle tests (5 tasks, functionality, AC5.1-5.6 writer + AC6.4 UAT + AC8.2 + AC8.3) |
| `test-requirements.md` | 34 ACs → automated test mapping; 31 AUTOMATED + 2 HUMAN_JUDGEMENT + 1 MIXED |
| `uat-requirements.md` | 3 human-judgement entries with falsification-template format |
| `code-review-findings-plan-validation.md` | Both review cycles' verdicts; useful audit trail |

### Design plan (committed earlier)

`docs/design-plans/2026-05-08-crash-recovery.md` — single source of truth. Patched in this session to rename plugin to `denubis-crash-recovery` and document testpaths widening.

### Key user decisions made in the planning session

- **Plugin naming:** `denubis-crash-recovery` (matches repo's universal `denubis-*` prefix). CLI binary, Python package, AC slug, env vars, DB filename remain unprefixed.
- **Test discovery:** widen repo-root `testpaths` to `["tests", "plugins/*/scripts/*/tests"]`. Side effect: workflow_statusline tests start being discovered.
- **Bibliography description fix:** committed inline (was a pre-existing baseline test failure unrelated to crash-recovery).
- **Liveness-presence storage:** derive from `classification_reason` prefix in Phase 5; no schema column added. The design plan's Additional Considerations text was NOT patched (lives as a known inconsistency — option A on the AskUserQuestion).
- **CLI framework:** typer (Phase 1 DR1).
- **Python floor:** `>=3.12` (Phase 1 DR2, Haraway-flagged).
- **Schema idempotency:** `CREATE TABLE IF NOT EXISTS` (Phase 1 DR3, PROGRESSIVE).
- **Rule-table representation:** structured Rule dataclass with optional field matchers (Phase 2 DR2, PROGRESSIVE).
- **Project-dir resolution:** read `cwd` from JSONL contents rather than reverse-engineer Claude Code's lossy encoding (Phase 3 DR1, PROGRESSIVE).
- **Scan transaction shape:** single transaction per scan run (Phase 4 DR1).
- **Stale-version prune:** hard-filter with explicit warning (Phase 6 DR1).
- **Conservative exit-status policy:** 0/130 remove, all else leaves (Phase 8 DR1).

---

## Task tracker state (at halt)

41 of 49 created tasks completed. Remaining:

- **#4** Critical peer review of implementation plan — `pending` (was `in_progress`; reset due to halt; redo in fresh session)
- **#5** Execution handoff — `pending` (blocked by #4)
- **#50** Commit planning artifacts — `completed` (commit `28ebf21`)
- **#51** Write RESUME.md — `in_progress` (this file)

The fresh session can `TaskList` and pick up from where the chain left off.
