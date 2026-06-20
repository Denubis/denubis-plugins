# Post-mortem crash detection — Phase 5: reap ~/.claude/run

**Goal:** Give dead `.live` markers a lifecycle: `prune` can reap dead, start-time-checked markers whose correlated session is already `concluded`/`hard_crash`, under the existing `--dry-run`/`--confirm` gate. Alive and uncorrelated markers are never reaped.

**Architecture:** `prune.py` gains a read-only `survey_markers(db_path, run_dir)` (mirrors `survey`'s no-mutation discipline) and a `reap_markers(paths)` that unlinks files. `__main__.py::prune` surveys markers alongside the existing concluded-row prune and reaps on `--confirm`.

**Tech Stack:** Python 3.14+ stdlib (pathlib, sqlite3), pytest.

**Scope:** Phase 5 of 5 from `docs/design-plans/2026-06-12-crash-detection.md`. Depends on Phases 1-4 (uses `liveness.pid_alive_checked` + `Liveness.session_id` from Phase 2).

**Codebase verified:** 2026-06-12 (commit 03b97f2; prune/__main__ read this session).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

### crash-detection.AC8: Reaping ~/.claude/run
- **crash-detection.AC8.1 Success:** `prune --dry-run` lists dead, start-time-checked markers whose session is `concluded`/`hard_crash`, without deleting.
- **crash-detection.AC8.2 Success:** `prune --confirm` removes them.
- **crash-detection.AC8.3 Failure:** Alive markers and uncorrelated markers are never reaped.

---

## Planned scope extension (2026-06-17): id-less / orphan marker reaping

**Status: recorded requirement — settle the design before implementing Phase 5.** Surfaced operationally when a real backlog sweep exposed that the Task 1 reaper, as specified, covers none of the markers that actually accumulate.

**The gap.** Task 1's `survey_markers` keys on `lv.session_id` and skips markers without it (the uncorrelated guard, line 62). But the real `~/.claude/run` backlog is dominated by **id-less** markers: pre-Phase-2 markers (no `session_id`/`start_time` stamp at all), plus an *ongoing* trickle from `--continue`-without-uuid / `--print` / bare sessions, for which the wrapper omits `session_id` by design. A 2026-06-17 read-only survey found 37 markers (6 live, 31 dead) — **all 31 dead were id-less**, so Phase 5 as specified would reap **0** of them. They were swept manually (read-only correlate → moved to a backup dir, keeping the 6 live), but the tooling should do this.

**Requirement.** `prune --confirm` must be able to reap dead markers that are **not** preserving a recoverable session, **including id-less ones** — not only `session_id`-bearing markers tied to a `concluded`/`hard_crash` row.

**Safety criterion (validated by the 2026-06-17 sweep).** Removing a marker never deletes a session — the JSONL persists and stays in the roster; it only drops the redundant liveness signal. So the *only* marker worth preserving is one that is the live `hard_crash` signal for an unrecovered **dangling** session (`TOOL_USE_NO_RESULT` / `ASK_QUESTION_NO_REPLY` / `AGENT_DISPATCH_NO_RESULT`). A dead marker is reapable iff it does NOT correlate to a dangling session — i.e. it correlates to `concluded`/`unknown`/`ambiguous`, or to nothing (`NO_MATCH`). For id-less markers, correlate via the Phase 3 mtime window rather than `lv.session_id`. (In the survey, the 31 dead split 12 concluded / 1 unknown / 18 ambiguous / 0 dangling — all safe.)

**Open design questions (settle in Phase 5 design, do not hard-code from this note):**
- A delete driven by *fuzzy* mtime correlation is riskier than the `session_id`-exact path. Does id-less reaping need a stricter gate — a separate `--confirm-orphans` flag, or a louder dry-run that shows the correlation basis per marker?
- Reconcile criteria: the original Task 1 reaps `concluded`/`hard_crash` (it assumes triage+recovery already happened, so reaping a `hard_crash` marker is fine); the backlog sweep *preserved* dangling/`hard_crash` (not yet recovered). For a routine `prune`, likely reap `concluded` + `ambiguous` + `no_match` + `unknown` and preserve dangling/`hard_crash` unless an explicit flag is given. Pick one consciously.
- Aging/TTL: should a sufficiently old dead id-less marker be reapable regardless of correlation, or always correlation-gated?

## Context for the implementer

- **prune.py** today: `survey(db_path) -> PruneSurvey` (read-only, four-condition guard for concluded *DB rows*); `delete_candidates(db_path, uuids)` (the only writer). Reaping markers is a NEW, orthogonal axis: it deletes *files* in `run_dir`, not DB rows. Keep the two concerns separate (a marker survey + a marker reaper) so the existing row-prune is untouched.
- **liveness.py** (Phase 2): `list_liveness_files(run_dir) -> Iterator[Liveness]`, `pid_alive_checked(pid, start_time)`, `Liveness.session_id`.
- **__main__.py::prune** today resolves `--db`, runs `survey`, prints/deletes under `--dry-run`/`--confirm`. It does NOT currently take `--run-dir`; add it (resolved via `_resolve(..., "CRASH_RECOVERY_RUN_DIR", "~/.claude/run")`).
- **NEVER** point tests at the real `~/.claude/run`; use a temp `run_dir` and the `make_liveness_file` fixture (extended in Phase 2 for `session_id`/`start_time`).

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Marker survey + reaper in prune.py

**Verifies:** crash-detection.AC8.1 (survey logic), crash-detection.AC8.3

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/prune.py`
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_prune.py` (unit)

**Implementation:**
```python
@dataclass(frozen=True)
class ReapableMarker:
    path: Path
    pid: int
    uuid: str
    classification: str

def survey_markers(db_path: Path, run_dir: Path) -> tuple[ReapableMarker, ...]:
    """Read-only: dead, start-time-checked markers whose correlated session is
    concluded/hard_crash. MUST NOT mutate the DB or the filesystem."""
```
Logic (no mutation):
- Enumerate `list_liveness_files(run_dir)`.
- Skip markers that are still alive: `pid_alive_checked(lv.pid, lv.start_time)` is `True` → skip (AC8.3 alive guard).
- Resolve the marker to a session UUID: use `lv.session_id` (Phase 2). If absent or not a UUID → skip (AC8.3 uncorrelated guard — conservative; do not reap markers we cannot tie to a row).
- Look up that UUID in `sessions`; reapable only if it exists AND `classification IN ('concluded','hard_crash')`. Otherwise skip.
- Return the reapable markers (sorted by path for determinism).
- DB access: `db.open_db` opens a read-write connection but `survey_markers` issues only `SELECT`s — same read-only discipline as `survey` (the connection is never used for writes). Do not mutate the DB or the filesystem in the survey.

```python
def reap_markers(paths: tuple[Path, ...]) -> int:
    """The only marker writer: unlink each path (missing_ok=True); return count."""
```
Keep `survey`/`delete_candidates` (DB-row prune) unchanged.

**Testing (test_prune.py):** temp `run_dir` + temp DB.
- AC8.1: write a dead marker (`pid=_pick_dead_pid()`, `session_id=UUID_A`, a `start_time` value) and seed a `sessions` row `uuid=UUID_A, classification='concluded'` → `survey_markers` returns it; the file is still on disk (survey is read-only).
- AC8.1 (hard_crash): same with `classification='hard_crash'` → returned.
- AC8.3 (alive): a marker with `pid=os.getpid()` and the correct `start_time` (`liveness._proc_start_time(os.getpid())`) → `pid_alive_checked` True → NOT returned.
- AC8.3 (uncorrelated): a dead marker with no `session_id` → NOT returned; a dead marker whose `session_id` UUID is not in `sessions` → NOT returned; a dead marker whose session is `borderline` → NOT returned.
- `reap_markers` unlinks the given paths and returns the count; missing path is tolerated.

**Verification:** `uv run pytest .../tests/test_prune.py -q` green.

**Commit:** `feat(crash-recovery): survey + reap dead ~/.claude/run markers`
<!-- END_TASK_1 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (task 2) -->

<!-- START_TASK_2 -->
### Task 2: prune CLI surfaces and reaps markers

**Verifies:** crash-detection.AC8.1, crash-detection.AC8.2, crash-detection.AC8.3

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py` (`prune`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_prune.py` (integration via the typer app)

**Implementation:**
- Add a `--run-dir` option to `prune`, resolved via `_resolve(run_dir, "CRASH_RECOVERY_RUN_DIR", "~/.claude/run")`.
- After the existing concluded-row handling:
  - Compute `markers = _prune.survey_markers(resolved_db, resolved_run_dir)`.
  - `--dry-run`: in addition to the row candidates, print the reapable markers (`path`, `uuid`, `classification`); if both lists empty, the existing "No prune candidates." may be extended to mention markers. Do not delete.
  - Default (no flag): the existing AC7.3 refuse-without-confirm message also covers markers (no deletion).
  - `--confirm`: after `delete_candidates(...)`, call `_prune.reap_markers(tuple(m.path for m in markers))` and report the reaped count alongside the deleted-rows count.
- Keep `--dry-run`/`--confirm` mutually exclusive (existing guard).

**Testing (test_prune.py):** drive `app` via typer's `CliRunner` (or invoke `prune(...)` directly) with `--db`/`--run-dir` pointed at temp dirs.
- AC8.1: `--dry-run` lists the reapable marker and leaves the file on disk.
- AC8.2: `--confirm` reaps the marker (file gone) and reports the count; the DB-row prune still works for concluded rows.
- AC8.3: an alive marker and an uncorrelated dead marker survive `--confirm`.

**Verification:** `uv run pytest .../tests/test_prune.py -q` green; full `uv run pytest` green (AC9.1); bats green (AC9.2).

**Commit:** `feat(crash-recovery): prune --confirm reaps dead run-dir markers`
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_B -->

## Phase 5 done when

- `survey_markers` returns only dead, start-time-checked markers whose session is `concluded`/`hard_crash` (AC8.1); alive and uncorrelated markers are excluded (AC8.3).
- `prune --dry-run` lists reapable markers without deleting (AC8.1); `--confirm` reaps them (AC8.2).
- Full `uv run pytest` green (AC9.1); `bats tests/test_claude_wrapper_liveness.bats` green (AC9.2).

## Final phase note

After Phase 5, the full acceptance set is covered: AC1 (Phases 1-4), AC2-AC3 (Phase 1), AC4 (Phase 2), AC5+AC7 (Phase 4), AC6 (Phase 3), AC8 (Phase 5), AC9 (every phase keeps baselines green). AC1.1 and AC1.3 are pure-classifier outcomes already covered by existing `test_classify.py` rules plus the Phase 1-2 correlation/liveness fixes that let those rules fire; the Phase 4 render tests cover AC1.2.
