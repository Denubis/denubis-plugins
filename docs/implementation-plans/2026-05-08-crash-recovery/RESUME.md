# Resume — denubis-crash-recovery planning session

**Last updated:** 2026-05-15
**Branch:** `crash-recovery` (in `.worktrees/crash-recovery/`)
**HEAD:** will be the commit that lands this file plus `critical-peer-review-findings.md`
**Upstream gap:** 6 commits ahead of `origin/main` (design plan, arch pin, bibliography fix, design rename, implementation plan, first RESUME bridge).

---

## Start the next session inside the worktree

Tasks are keyed by working directory, so the next session must open the worktree to inherit the 14 queued fix tasks:

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery
claudew --resume <session-uuid-if-resuming>   # or just: claudew
```

Verify state on the first turn:

```bash
pwd                        # should print .../.worktrees/crash-recovery
git branch --show-current  # should print crash-recovery
git log --oneline -3       # most recent should be the resume commit
```

Then `TaskList` should show tasks #1, #2, and #3–#14 in pending state.

---

## What happened in this session (2026-05-15)

The previous session left task #4 (critical peer review) pending. This session:

1. ✅ Dispatched `denubis-plan-and-execute:critical-peer-review` against the whole plan directory. Treated prior code-reviewer's APPROVED verdict as untrusted. Subagent wrote `critical-peer-review-findings.md` alongside the existing `code-review-findings-plan-validation.md`.
2. ✅ Review came back **NEEDS_DISCUSSION** with **5 High / 6 Medium / 5 Low** findings.
3. ✅ Triaged every High and every Medium one-by-one with the human (no batch-fixing — per HALT-when-sideways and the user's `feedback_functional-decomposition-readbacks` memory). Lows bundled.
4. ✅ One escalation mid-triage: Medium-4 was promoted to needing-a-decision when running `uv run pytest plugins/.../workflow_statusline/tests/ -q` confirmed the proposed testpaths widening would break the test suite on first commit. Resolved by reversing the widening rather than working around it.
5. ✅ 12 explicit fix decisions captured as tasks (#3–#14). All 16 findings are dispositioned; none silently dropped.

Critical peer review verdict and decisions are below. Subagent reply summary:

> "Verdict is NEEDS_DISCUSSION, not APPROVED. The plan is structurally complete — every AC maps to a test, file paths agree, phase ordering is defensible — and on those terms the prior reviewer's APPROVED is reasonable. But the falsification pass surfaces five High-severity issues that a structural checklist cannot catch by construction."

Full findings file: `docs/implementation-plans/2026-05-08-crash-recovery/critical-peer-review-findings.md`.

---

## The 14 queued fixes — what each decision was and where to apply it

These are user-approved decisions made in this session. The next session executes them; it must NOT re-litigate them.

### High findings (all approved)

| Task | Finding | Decision | Files affected |
|---|---|---|---|
| #3 | H1 — `boot_id_current` not wired in walk strategy | Add explicit pseudocode in walk strategy showing `current_bid = current_boot_id()` cached once, and `boot_id_current=(liveness.boot_id == current_bid)` + `pid_alive_value=pid_alive(liveness.pid)` at each `SessionFact` construction site. Pure document edit. | phase_04.md |
| #4 | H2 — non-Linux CHANGELOG lies | **Fail-fast on non-Linux** at top of `scan` / CLI entry. Drop the "still works on non-Linux" claim from CHANGELOG. Wrapper itself unchanged (its `boot_id=unknown` fallback is harmless). | phase_04.md, phase_07.md, phase_08.md |
| #5 | H3 — wrapper rm-logic placed before transcript-archive prompt | **Move Block B to immediately BEFORE `exit $EXIT_CODE`** (line 121 of on-disk wrapper) rather than after `EXIT_CODE=$?` (line 90). Option 3a — no extra bats test for the transcript-prompt path; accept the test gap. | phase_08.md |
| #6 | H4 — DR-label rot in test names + README | **Drop DR prefixes** from bats test names; use plain descriptions of what each test verifies. Also fix Phase 7 README citation `"DR3 in Phase 6"` → describe the choice directly. Sweep all phase files for `"DRn — ..."` labels that don't match design plan DR1–DR9. | phase_07.md, phase_08.md, possibly others |
| #7 | H5 — "unreachable" fallback is reachable | **Reframe `unmatched` as deliberate review-queue route**, not defensive fallback. Drop "unreachable" language. Rename test, use a realistic input. Add a new `test_rules_table_partition_documents_unmatched_cases` enumerating realistic combinations. Render message for `unmatched`: literally `"Something fucky — let's go look"` (user's phrasing). Triage skill surfaces `borderline / unmatched` with a "manual review" tag. | phase_02.md, phase_05.md, phase_07.md |

### Medium findings (all approved)

| Task | Finding | Decision | Files affected |
|---|---|---|---|
| #8 | M1 — NFS/FUSE atomicity scoping | **Refuse to run on network filesystems** (strict option, not "document and let users opt in"). Detect via `findmnt` / `/proc/mounts` whether `CR_RUN_DIR` is on `{nfs, nfs4, cifs, smb3, smbfs, sshfs, davfs, glusterfs, ceph, beegfs, lustre, afs, fuse.*}` and raise a clear error pointing at `CRASH_RECOVERY_RUN_DIR` for the override. | phase_01.md or phase_03.md, phase_07.md, phase_08.md |
| #9 | M3 — FK cleanup in prune undecided | **Cascade delete**. Add `FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE` to `classification_history`. `PRAGMA foreign_keys = ON` already set. Add `test_prune_cascades_classification_history_deletion`. `history <uuid>` for pruned UUIDs naturally returns no rows — no change needed. | phase_01.md, phase_06.md |
| #10 | M6 — concurrent-scan test accepts `1 OR 2` rows | **Tighten to `== 2`**. Update docstring to drop the "one scan won the race" narrative; document that both scans hold their own transaction, SQLite WAL serialises, both write a `scan_runs` row by design. | phase_04.md |
| #11 | M4 — testpaths widening "acceptable" without verification (test FAILED) | **Reverse the widening entirely** (option 4b). Root `pyproject.toml` keeps `testpaths = ["tests"]`. Document the per-plugin invocation convention: `uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest -q`. Same convention workflow_statusline already follows. **Why not workspaces:** workflow_statusline's pyproject is structurally required because users invoke it via `uv run --project <plugin-path>/scripts/workflow_statusline` — the install model copies plugin dirs standalone. Crash-recovery has the same shape. The wider testpaths was an aspirational unification; per-plugin invocation is the existing convention and matches the install model. | phase_01.md (remove widening + add convention doc), test-requirements.md (incantation column) |
| #12 | M2 — `$*` vs `$@` rationale wrong | Drop the rationale `"matches Phase 3's _extract_resume_uuid expectation"` (Phase 3 uses `shlex.split` which handles either). Replace with `"Either $* or $@ works inside double-quoted printf %s; $* is chosen for explicit single-string semantics."` | phase_08.md |
| #13 | M5 — Phase 1 "DR2 authorised widening" citation | **Mooted by M4 → 4b**. There's no widening to authorise. Delete the citation and its surrounding paragraph if they only existed to justify the widening. | phase_01.md |

### Low findings (bundled)

| Task | Findings | Decision |
|---|---|---|
| #14 | L1–L5 | L1 (Phase 7 "DR3 in Phase 6") and L3 (Phase 8 Done-When DR labels) caught by H4's DR-rot sweep; verify. L2 (Phase 4 import block) — extend imports for ambiguous-correlation pseudocode. L4 (commit hash `8c10b95`) — `git cat-file -t 8c10b95`, confirm or strip. L5 — reviewer confirmed clean, no-op. |

---

## What the next session does

### Step 1: Editing pass

Read each phase file fresh (don't assume prior framing). Apply tasks #3–#14. Use the **Editing Pass Rule** from the critical-peer-review skill:

> *After any High-severity fix, search the entire document for every reference to the changed claim/number/finding. Update all references. Re-read the document from top to bottom for narrative coherence. Confirm "I have done a full editing pass" in the revision notes.*

The reviewer explicitly flagged that the plan was "edited by composition rather than re-reading" — that's the failure mode to avoid. Each edit needs a full sweep for ripples, not just a local fix.

Order suggestion (largest-blast-radius first):
1. Task #11 (Med-4, no testpaths widening) — affects Phase 1, test-requirements, multiple phase test-run incantations
2. Task #7 (High-5 reframe) — touches Phase 2, 5, 7
3. Task #4 (High-2 non-Linux) — Phase 4, 7, 8
4. Task #6 (High-4 DR-rot sweep) — across phases, plus rolls up L1, L3
5. Task #5 (High-3 wrapper insertion point) — Phase 8 single line
6. Task #3 (High-1 walk-strategy pseudocode) — Phase 4 single section
7. Task #8 (Med-1 network-FS refuse) — Phase 1 or 3 + Phase 7, 8
8. Task #9 (Med-3 cascade delete) — Phase 1 schema, Phase 6 test
9. Task #10 (Med-6 concurrent-scan test) — Phase 4 single line
10. Tasks #12, #13, #14 — text cleanup last

### Step 2: Light structural re-review

After editing pass, dispatch `denubis-plan-and-execute:code-reviewer` (NOT critical-peer-review again — that one has done its job) for a structural sweep. Goal: catch any inconsistencies introduced by the edits (stale cross-refs, drifted test names, etc.). Should be APPROVED with at most cosmetic findings.

### Step 3: Execution handoff (task #2)

Per `denubis-plan-and-execute:starting-an-implementation-plan` skill, lines 261-323. Output:

```
/denubis-plan-and-execute:executing-an-implementation-plan /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/docs/implementation-plans/2026-05-08-crash-recovery/ /home/brian/people/Brian/brian-ed3d-plugins/.worktrees/crash-recovery/
```

Pass the **directory**, not `phase_01.md`.

---

## State pointers

### Findings file (committed at the resume commit)

`critical-peer-review-findings.md` — falsification-first audit. 5H / 6M / 5L with full ACH matrix, hidden-assumptions table, pre-mortem, GRADE annotations. Has more detail than this RESUME captures; treat it as the source of truth for "what the reviewer actually said" if any decision in this RESUME seems wrong.

### Prior reviewer's file (kept)

`code-review-findings-plan-validation.md` — the structural code-reviewer's two-cycle APPROVED verdict. Useful as a foil: it shows what *structural* review catches, which is exactly NOT what the falsification pass surfaced. Don't delete it; it's the audit trail.

### Things to NOT re-litigate

The next session must NOT:
- Re-run the critical peer review (already done; findings are authoritative until the editing pass changes the substrate).
- Re-debate the per-finding decisions captured above (the user already chose).
- Add a uv workspace (deliberately rejected — Med-4 → 4b).
- Re-introduce the testpaths widening (deliberately rejected).
- Restore "unreachable" language in Phase 2's classify() (deliberately reframed).
- Restore "the plugin runs on non-Linux" claim (deliberately retired).

### Things to watch for during the editing pass

These are falsification anchors. If any of these stops being true after edits, halt and discuss:

- `unmatched` reason has a render message and a triage-skill entry that mention manual review.
- Every reference to `boot_id_current` shows the comparison site, not just the field declaration.
- No bats test name or README sentence starts with `"DR<n> —"` except where it correctly cites an actual design plan DR.
- Root `pyproject.toml`'s `testpaths` is still `["tests"]` after Phase 1's edits.
- `classification_history` has the FK on `uuid` with `ON DELETE CASCADE`.
- Phase 4's concurrent-scan test asserts `== 2` rows, not `1 or 2`.
- No reference to `current_boot_id()` returning `"unknown"` survives anywhere (we picked fail-fast, not defensive fallback).
- `crash-recovery scan` has a `sys.platform == "linux"` guard early.
- `CR_RUN_DIR` / `$HOME` has a network-FS check that refuses to run on `nfs/cifs/sshfs/fuse.*/etc.`.

---

## Task tracker state (at handoff)

14 fix tasks queued. The original RESUME's task list (#4 critical peer review, #5 execution handoff) was lost to task-list reset between sessions; in this session's tracker they are numbered #1 (critical peer review, still `in_progress` until editing pass + re-review + handoff complete) and #2 (execution handoff, blocked by #1).

- **#1** Critical peer review — `in_progress`. Keep in progress until editing pass + re-review pass + handoff complete. Counts the whole "review + apply + re-verify" envelope.
- **#2** Execution handoff — `pending`, blocked by #1.
- **#3 – #14** Fix tasks from the 14 decisions above.

The next session can `TaskList` and pick up from this state.
