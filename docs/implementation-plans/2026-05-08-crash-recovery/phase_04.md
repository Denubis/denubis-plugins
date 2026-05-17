# denubis-crash-recovery Implementation Plan — Phase 4: `scan` subcommand

**Goal:** End-to-end pipeline that walks the filesystem, classifies each session, upserts SQLite rows in a single transaction, and re-classifies any DB rows whose stored `classifier_version` is below the current constant.

**Architecture:** `crash_recovery.scan.run_scan(ctx)` performs all read-only work first (filesystem walk, tail parse, liveness parse, correlate, classify) into an in-memory list of `(uuid, project_path, cwd, jsonl_path, classification, ...)` tuples. It then opens one SQLite transaction and writes every sessions upsert, classification_history append, and the closing scan_runs row in that single transaction. A second pass queries the DB for any UUID not seen in the filesystem walk whose stored `classifier_version` is stale, re-classifies it (typically as `irrecoverable` if the JSONL is gone), and updates the row inside the same transaction. WAL mode (set in Phase 1) lets concurrent readers proceed unblocked; concurrent scans serialize at the write lock.

**Tech Stack:** Python 3.12+ stdlib (`sqlite3`, `pathlib`, `time`, `os`); typer for the CLI wiring.

**Scope:** Phase 4 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-13. Phase 1 db.py (init, open_db, _schema_hash) is consumable; Phase 2 (TailSummary, classify) and Phase 3 (Liveness, correlate) provide the read-side primitives. SQLite ≥3.43 (bundled with Python 3.12) supports `INSERT … ON CONFLICT(uuid) DO UPDATE` upserts.

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### crash-recovery.AC3: Classification is deterministic
- **crash-recovery.AC3.6 Success:** When `scan` runs against a DB containing rows whose `classifier_version` is below the current `CLASSIFIER_VERSION` constant, those rows are re-classified using the current rule table before render or prune sees them. After scan completes, no `sessions` row has a stale `classifier_version`.

### crash-recovery.AC5: Wrapper liveness lifecycle
- **crash-recovery.AC5.6 Success (end-to-end):** A liveness file whose `boot_id` does not match the current `/proc/sys/kernel/random/boot_id` is classified as a casualty by `scan` regardless of whether its PID is alive (PID may have been recycled by the new boot).

  *Phase 3 surfaced `current_boot_id()` and `Liveness.boot_id`; Phase 4 wires the comparison into `classify()`'s `LivenessState(boot_id_current=...)` input.*

### crash-recovery.AC6: Idle-live-session detection end-to-end
- **crash-recovery.AC6.2 Success:** A liveness file whose PID is still alive (verified via `kill -0`) classifies its session as `live`, never `hard_crash`.
- **crash-recovery.AC6.3 Borderline:** When mtime-window correlation finds multiple candidate UUIDs, classification is `borderline` with reason `ambiguous_match` and the candidate UUID list is recorded in `state_summary`.

> **AC mapping correction:** the design plan's "Covers ACs" line for Phase 4 lists `crash-recovery.AC4.1`, `crash-recovery.AC4.2`, `crash-recovery.AC4.3`. Those ACs cover the `note` subcommand (annotation persistence) and properly belong to Phase 6, not Phase 4. This implementation file maps Phase 4 to the ACs Phase 4 actually exercises (AC3.6, AC5.6 end-to-end, AC6.2, AC6.3). Phase 6's plan file will own AC4.*.

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: `crash_recovery.scan` — orchestration + filesystem walk

**Verifies:** none directly; foundation for Tasks 2–5.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py`

**Implementation:**

The module exposes:

1. **`ScanContext`** — frozen dataclass capturing all I/O configuration:

   ```python
   from dataclasses import dataclass
   from pathlib import Path

   @dataclass(frozen=True)
   class ScanContext:
       db_path: Path
       run_dir: Path           # ~/.claude/run/ (or override)
       projects_root: Path     # ~/.claude/projects/ (or override)
       now: int                # unix epoch at scan start; injected for test determinism
   ```

2. **`ScanRunResult`** — frozen dataclass returned from `run_scan`:

   ```python
   @dataclass(frozen=True)
   class ScanRunResult:
       scan_run_id: int        # rowid of the scan_runs row written
       sessions_scanned: int   # count of sessions touched on filesystem
       sessions_reclassified: int  # count of orphan-sweep rows updated
   ```

3. **`_walk_sessions(ctx) -> list[SessionFact]`** — read-only filesystem walk. Returns one `SessionFact` per session UUID found via either liveness-file correlation OR direct JSONL enumeration. `SessionFact` is a frozen dataclass with these fields (in declaration order):

   ```python
   @dataclass(frozen=True)
   class SessionFact:
       uuid: str
       project_path: str          # encoded project dir as a string for storage
       cwd: str                   # real cwd (resolved via Phase 3's _project_dir_for_cwd)
       jsonl_path: str | None     # absolute path to the JSONL on disk; None if no JSONL ever written
       jsonl_mtime: int | None    # unix epoch; for cache invalidation
       tail_summary: "TailSummary"            # from Phase 2's parse_tail
       liveness: "Liveness | None"            # the correlated Liveness record, if any
       pid_alive_value: bool | None           # result of pid_alive(liveness.pid); None when liveness is None
       boot_id_current: bool = False          # True iff liveness.boot_id == current_boot_id(); defaults False when no liveness
       ambiguity_candidates: tuple[str, ...] = ()  # full candidate list when correlate returned AMBIGUOUS; () otherwise
   ```

   Walk strategy:
   - **Cache the current kernel boot_id once at the start of the walk:** `current_bid = current_boot_id()` (from Phase 3). The read is cheap but reading it N times under load is wasteful and would also create a race window if the kernel value somehow changed mid-walk (it cannot — boot_id is stable per kernel uptime — but caching once also makes the test fixture-mocking story simpler).
   - Iterate `list_liveness_files(ctx.run_dir)`. For each `Liveness`, call `correlate(liveness, ctx.projects_root)`:
     - `DIRECT_MATCH` or `MTIME_MATCH`: produce one `SessionFact` for that UUID. Compute the per-fact liveness-dependent fields explicitly at construction:
       ```python
       facts.append(SessionFact(
           uuid=resolved_uuid,
           ...,
           tail_summary=parse_tail(jsonl_path),
           liveness=liveness,
           pid_alive_value=pid_alive(liveness.pid),
           boot_id_current=(liveness.boot_id == current_bid),
           ambiguity_candidates=(),
           ...,
       ))
       ```
     - `AMBIGUOUS`: produce one `SessionFact` per candidate UUID, marked with `ambiguity_candidates: tuple[str, ...]` (the full candidate list). These facts also compute `pid_alive_value=pid_alive(liveness.pid)` and `boot_id_current=(liveness.boot_id == current_bid)` so an ambiguous candidate whose liveness file is on a stale boot still routes correctly even though the classification override fires. They bypass Phase 2's `classify()` and emit `Classification(BORDERLINE, "ambiguous_match")` directly per AC6.3 (the classification override is in `_classify_fact` below).
     - `NO_MATCH`: skip (the liveness file describes a wrapper whose session we cannot identify; no DB row to write).
   - Iterate `ctx.projects_root.glob("*/*.jsonl")` and collect any UUIDs NOT already produced by the liveness walk. For each, produce a `SessionFact` with `liveness=None`, `pid_alive_value=None`, `boot_id_current=False`, `ambiguity_candidates=()`. (`boot_id_current=False` for JSONL-only facts is correct by definition: with no liveness file there is no recorded boot_id to compare, and the field is consulted by `classify()` only when `LivenessState.present=True`.)

   The walk does NOT touch the DB.

4. **`_classify_fact(fact) -> Classification`** — pure function wrapping Phase 2's `classify()`, with one special case for AC6.3:

   ```python
   from crash_recovery.classify import classify, Classification, ClassificationValue
   from crash_recovery.liveness import LivenessState, current_boot_id, pid_alive
   from crash_recovery.jsonl import TailSummary, TailKind, parse_tail
   from crash_recovery.correlate import CorrelationKind, correlate

   def _classify_fact(fact: SessionFact) -> Classification:
       # AC6.3: ambiguous correlation gets a hardcoded BORDERLINE/ambiguous_match.
       # Phase 2's RULES catalogues tail-shape-driven outcomes; correlation
       # ambiguity is a different category entirely.
       if fact.ambiguity_candidates:
           return Classification(
               value=ClassificationValue.BORDERLINE,
               reason="ambiguous_match",
           )
       ls = LivenessState(
           present=fact.liveness is not None,
           boot_id_current=fact.boot_id_current,
       )
       return classify(fact.tail_summary, ls, fact.pid_alive_value)
   ```

   **Boundary-contract invariant** (recorded after Phase 2 proleptic challenge CA2, 2026-05-16): `classify()` raises `ValueError` if `LivenessState.present=True` is paired with `pid_alive=None`. The two construction sites in `_walk_sessions` already honour this — the liveness-walk path sets `pid_alive_value=pid_alive(liveness.pid)` (which Phase 3 guarantees returns `bool`, never `None`), and the JSONL-only path sets `liveness=None` together with `pid_alive_value=None` (so `LivenessState.present=False` and the ValueError doesn't fire). Phase 3's `pid_alive()` contract MUST guarantee bool-return; Phase 4 does not catch the `ValueError` deliberately — if it fires, the scan crashes loudly rather than silently producing wrong classifications, surfacing a Phase 3 contract violation immediately.

   When `_walk_sessions` builds a `SessionFact` for an ambiguous-correlation candidate, it constructs the `TailSummary` with `state_summary=f"ambiguous match: {', '.join(candidates)}"` at construction time (TailSummary is frozen — no mutation possible; the field is set via the constructor). The override path then propagates that pre-set `state_summary` through into the `sessions.state_summary` column per AC6.3.

   Pseudocode for the walk's ambiguous-correlation branch:
   ```python
   if correlation.kind is CorrelationKind.AMBIGUOUS:
       candidates_str = ", ".join(correlation.candidates)
       for candidate_uuid in correlation.candidates:
           # Build a fresh TailSummary at this point; do not attempt to mutate
           # any parsed-from-disk TailSummary.
           synthetic_tail = TailSummary(
               kind=TailKind.UNKNOWN,
               last_ts=None,
               total_entries=0,
               state_summary=f"ambiguous match: {candidates_str}",
           )
           facts.append(SessionFact(
               uuid=candidate_uuid,
               ...,
               tail_summary=synthetic_tail,
               liveness=liveness,
               ambiguity_candidates=correlation.candidates,
               ...
           ))
   ```

5. **`run_scan(ctx) -> ScanRunResult`** — top-level orchestrator. Skeleton:

   ```python
   def run_scan(ctx: ScanContext) -> ScanRunResult:
       facts = _walk_sessions(ctx)
       classifications = [(fact, _classify_fact(fact)) for fact in facts]
       seen_uuids = {fact.uuid for fact in facts}
       # Collect live PIDs for the scan_runs.live_pids column.
       # Sorted for determinism so identical inputs produce identical DB content.
       live_pids: list[int] = sorted({
           fact.liveness.pid
           for fact in facts
           if fact.liveness is not None and fact.pid_alive_value is True
       })
       with closing(db.open_db(ctx.db_path)) as conn:
           with conn:                            # context manager = transaction
               run_id = _write_scan_run(
                   conn, ctx,
                   sessions_scanned=len(facts),
                   live_pids=live_pids,
               )
               for fact, classification in classifications:
                   _upsert_session(conn, fact, classification, ctx, run_id)
                   _append_history(conn, fact.uuid, run_id, classification)
               reclassified = _orphan_sweep(conn, ctx, run_id, seen_uuids)
       return ScanRunResult(scan_run_id=run_id, sessions_scanned=len(facts), sessions_reclassified=reclassified)
   ```

   Note: the `with conn:` context manager wraps the entire write block in a single transaction; sqlite3 commits on `__exit__` if no exception, rolls back otherwise. This honours DR1's transactional invariant.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.scan import ScanContext, ScanRunResult
from pathlib import Path
ctx = ScanContext(db_path=Path('/tmp/x.db'), run_dir=Path('/tmp/r'), projects_root=Path('/tmp/p'), now=1)
assert ctx.db_path == Path('/tmp/x.db')
print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py
git commit -m "feat(crash-recovery): add scan module with ScanContext, _walk_sessions, run_scan skeleton"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: DB writers — upsert, history append, scan_runs row

**Verifies:** AC3.6 indirectly (the upsert writes current `CLASSIFIER_VERSION` on every touched row; full test in Task 5).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py`

**Implementation:**

Add to `scan.py`:

1. **`_upsert_session(conn, fact, classification, ctx, scan_run_id)`** — single SQLite upsert. Uses `INSERT … ON CONFLICT(uuid) DO UPDATE SET …`. Preserves `first_seen` on conflict; refreshes `last_scanned`, `classification`, `classification_reason`, `classifier_version`, `state_summary`, `jsonl_mtime`, `jsonl_last_ts`, `jsonl_path`. Does NOT touch `user_notes` (annotations persist across scans per Phase 6's contract).

   ```sql
   INSERT INTO sessions (
       uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
       classification, classification_reason, classifier_version, state_summary,
       first_seen, last_scanned, user_notes
   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
   ON CONFLICT(uuid) DO UPDATE SET
       project_path = excluded.project_path,
       cwd = excluded.cwd,
       jsonl_path = excluded.jsonl_path,
       jsonl_mtime = excluded.jsonl_mtime,
       jsonl_last_ts = excluded.jsonl_last_ts,
       classification = excluded.classification,
       classification_reason = excluded.classification_reason,
       classifier_version = excluded.classifier_version,
       state_summary = excluded.state_summary,
       last_scanned = excluded.last_scanned
       -- first_seen and user_notes NOT updated on conflict
   ```

   Parameter binding order matches the column order above; `classifier_version` is always the current `CLASSIFIER_VERSION` constant from `crash_recovery.classify`.

2. **`_append_history(conn, uuid, scan_run_id, classification)`** — INSERT one row into `classification_history`:

   ```sql
   INSERT INTO classification_history (uuid, scan_id, classification, reason, classifier_version)
   VALUES (?, ?, ?, ?, ?)
   ```

   Primary key is `(uuid, scan_id)`, so re-running with the same scan_id raises — that's a programmer error guard (each scan_run should produce at most one history row per UUID).

3. **`_write_scan_run(conn, ctx, sessions_scanned, live_pids)`** — INSERT one row into `scan_runs` and return its rowid via `cursor.lastrowid`:

   ```sql
   INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version)
   VALUES (?, ?, ?, ?)
   ```

   The `live_pids` parameter is the sorted list of PIDs assembled by `run_scan` (Task 1). It is serialised with `json.dumps(live_pids)` before binding to the `?` placeholder. Empty list serialises as `"[]"` (not NULL — matches the design's TEXT column non-null pattern by convention).

   Call this BEFORE the per-session upserts so the returned `run_id` is available for `_append_history`.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery import db, scan
from crash_recovery.classify import Classification, ClassificationValue
from crash_recovery.jsonl import TailSummary, TailKind
import tempfile, pathlib, time
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'x.db'
    db.init(p)
    # Smoke: open conn, write a scan_run, assert one row.
    conn = db.open_db(p)
    with conn:
        cur = conn.execute(
            'INSERT INTO scan_runs (ts, live_pids, sessions_scanned, classifier_version) VALUES (?, ?, ?, ?)',
            (int(time.time()), '[]', 0, 1)
        )
        rid = cur.lastrowid
    assert rid == 1
    print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py
git commit -m "feat(crash-recovery): add _upsert_session, _append_history, _write_scan_run with ON CONFLICT upsert"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Orphan sweep — classifier-version re-classification

**Verifies:** AC3.6 (re-classify rows with stale classifier_version).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py`

**Implementation:**

Add to `scan.py`:

**`_orphan_sweep(conn, ctx, scan_run_id, seen_uuids) -> int`** — finds DB rows NOT seen in the filesystem walk this scan, re-classifies each, returns the count of rows updated.

Algorithm:
1. Query the DB for all `(uuid, jsonl_path, classifier_version)` rows.
2. Filter to rows whose `uuid` is NOT in `seen_uuids`.
3. For each such row:
   - If `jsonl_path` is NULL or `Path(jsonl_path).exists() is False`: classify as `IRRECOVERABLE` with reason `missing_jsonl_on_disk`. The session has no liveness file (or we'd have seen it on the filesystem walk) and no JSONL — irrecoverable.
   - Otherwise: re-read the JSONL tail via `parse_tail(jsonl_path)`, build a `LivenessState(present=False, boot_id_current=False)` (no liveness file means no boot_id to compare), call `classify(tail, ls, pid_alive=None)`. This handles the case where a previous scan saw a liveness file that has since been cleaned up — the session itself may still have a JSONL on disk.
4. UPDATE the row with new `classification`, `classification_reason`, `classifier_version = CLASSIFIER_VERSION`, `last_scanned = ctx.now`. Append a `classification_history` row.
5. Return the count of rows actually updated.

The classifier-version filter is intentional: even rows whose `classifier_version` is current still get re-considered if they're orphans (no longer on disk), because the JSONL might have been deleted since last scan. But we DON'T downgrade their `classifier_version`; we just write the current value (which matches what they already had, in the no-change case).

```python
def _orphan_sweep(conn, ctx, scan_run_id, seen_uuids) -> int:
    rows = conn.execute(
        "SELECT uuid, jsonl_path, classifier_version FROM sessions"
    ).fetchall()
    updated = 0
    for uuid, jsonl_path_str, stored_version in rows:
        if uuid in seen_uuids:
            continue
        if not jsonl_path_str or not Path(jsonl_path_str).exists():
            new_classification = Classification(
                value=ClassificationValue.IRRECOVERABLE,
                reason="missing_jsonl_on_disk",
            )
            tail_summary = TailSummary(kind=TailKind.MISSING_FILE, last_ts=None, total_entries=0, state_summary="jsonl missing on disk")
        else:
            tail_summary = parse_tail(Path(jsonl_path_str))
            ls = LivenessState(present=False, boot_id_current=False)
            new_classification = classify(tail_summary, ls, pid_alive=None)
        conn.execute(
            "UPDATE sessions SET classification = ?, classification_reason = ?, "
            "classifier_version = ?, state_summary = ?, last_scanned = ? WHERE uuid = ?",
            (new_classification.value, new_classification.reason, CLASSIFIER_VERSION,
             tail_summary.state_summary, ctx.now, uuid),
        )
        _append_history(conn, uuid, scan_run_id, new_classification)
        updated += 1
    return updated
```

**Step: Verify operationally**

```bash
# Hand-test: seed a DB row at classifier_version=0, run orphan_sweep, verify it's now at CLASSIFIER_VERSION.
# Full verification lands in Task 5 via fixtures.
echo "Verification deferred to Task 5 fixtures."
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py
git commit -m "feat(crash-recovery): add _orphan_sweep for classifier-version re-classification (AC3.6)"
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (tasks 4-5) -->

<!-- START_TASK_4 -->
### Task 4: `crash-recovery scan` CLI subcommand

**Verifies:** plumbing only; full behaviour verified by Task 5 integration tests.

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`

**Implementation:**

Add a `scan` typer subcommand. It must:
- Accept optional `--db PATH` (defaults to `CRASH_RECOVERY_DB` env var → `~/.claude/crash-recovery.db`).
- Accept optional `--run-dir PATH` (defaults to `CRASH_RECOVERY_RUN_DIR` env var → `~/.claude/run/`).
- Accept optional `--projects-root PATH` (defaults to `CRASH_RECOVERY_PROJECTS_ROOT` env var → `~/.claude/projects/`).
- Build a `ScanContext(db_path, run_dir, projects_root, now=int(time.time()))`.
- Call `run_scan(ctx)`.
- Print a one-line summary: `Scanned N sessions; M re-classified (orphans/version-stale); scan_run_id=K`.
- Exit 0 on success; let exceptions propagate to typer (non-zero exit).

```python
import os
import sys
import time
from pathlib import Path

from crash_recovery import scan as _scan
from crash_recovery import db
from crash_recovery import liveness as _liveness


def _resolve(option_value: Path | None, env_var: str, default: str) -> Path:
    if option_value is not None:
        return option_value
    return Path(os.environ.get(env_var, default)).expanduser()


@app.command()
def scan(
    db_path: Path = typer.Option(None, "--db"),
    run_dir: Path = typer.Option(None, "--run-dir"),
    projects_root: Path = typer.Option(None, "--projects-root"),
) -> None:
    """Walk the filesystem, classify each session, upsert to the DB."""
    if sys.platform != "linux":
        typer.echo(
            "crash-recovery scan requires Linux: reboot detection reads "
            "/proc/sys/kernel/random/boot_id, which only exists on Linux. "
            f"Detected platform: {sys.platform}.",
            err=True,
        )
        raise typer.Exit(code=2)
    ctx = _scan.ScanContext(
        db_path=_resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db"),
        run_dir=_resolve(run_dir, "CRASH_RECOVERY_RUN_DIR", "~/.claude/run"),
        projects_root=_resolve(projects_root, "CRASH_RECOVERY_PROJECTS_ROOT", "~/.claude/projects"),
        now=int(time.time()),
    )
    try:
        _liveness.assert_local_filesystem(ctx.run_dir)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    result = _scan.run_scan(ctx)
    typer.echo(
        f"Scanned {result.sessions_scanned} sessions; "
        f"{result.sessions_reclassified} re-classified; "
        f"scan_run_id={result.scan_run_id}"
    )
```

The `sys.platform == "linux"` guard at the top of `scan` is what makes the plugin Linux-only as a design choice: every other subcommand (`init`, `render`, `triage`, `note`, `history`, `prune`, `list-live`) is filesystem/DB-only and runs on any platform, but `scan` is the only command that reads `/proc/sys/kernel/random/boot_id` (via Phase 3's `current_boot_id()`). Exiting with code 2 and a clear error to stderr means non-Linux users get a useful diagnostic instead of a `FileNotFoundError` traceback. `triage` invokes `scan` internally so it inherits the guard.

Also update the `EXPECTED_SUBCOMMANDS` constant in tests (introduced in Phase 1 Task 6) to include `"scan"`.

**Step: Verify operationally**

```bash
TMPDIR=$(mktemp -d)
CRASH_RECOVERY_DB="$TMPDIR/test.db" uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery init
CRASH_RECOVERY_DB="$TMPDIR/test.db" CRASH_RECOVERY_RUN_DIR="$TMPDIR/run" CRASH_RECOVERY_PROJECTS_ROOT="$TMPDIR/projects" \
  uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery scan
# Expected: "Scanned 0 sessions; 0 re-classified; scan_run_id=1" (empty filesystem)
rm -rf "$TMPDIR"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_cli_help.py
git commit -m "feat(crash-recovery): add scan subcommand with --db/--run-dir/--projects-root options"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Fixture-driven integration tests for scan

**Verifies:** crash-recovery.AC3.6 (re-classification of stale classifier_version), crash-recovery.AC5.6 (boot_id mismatch → casualty regardless of PID), crash-recovery.AC6.2 (live PID → `live` classification).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py` — add `make_full_fixture(tmp_path, sessions: list[FixtureSession]) -> tuple[Path, Path, Path]` helper that constructs a complete (db_dir, run_dir, projects_root) triple from a high-level declaration.

**`FixtureSession` declaration shape:**

```python
@dataclass
class FixtureSession:
    uuid: str
    cwd: str
    tail_kind: TailKind          # what the synthetic JSONL should look like
    has_liveness: bool
    pid_alive: bool | None       # if has_liveness, what kill -0 should return; None otherwise
    boot_id_current: bool        # if has_liveness, whether the recorded boot_id matches current
    started_offset: int = -3600  # liveness.started = now + offset (seconds; defaults to 1 hour ago)
```

**Required tests:**

- **`test_scan_writes_expected_rows`** — fixture with one CONCLUDED session, one HARD_CRASH (liveness, dead pid, tool_use_no_result), one LIVE (liveness, alive pid). Run scan. Assert 3 rows in `sessions` table with the expected classifications. Assert one `scan_runs` row. Assert 3 `classification_history` rows.

- **`test_scan_is_idempotent`** — same fixture as above; run scan twice. Assert row count unchanged in `sessions` (3 rows). Assert `first_seen` preserved (unchanged between runs). Assert `last_scanned` updated (newer than first run). Assert two `scan_runs` rows. Assert six `classification_history` rows (3 sessions × 2 scan runs).

- **`test_scan_reclassifies_stale_classifier_version_rows`** (AC3.6) — seed DB with 3 rows at `classifier_version = CLASSIFIER_VERSION - 1` (no corresponding files on disk). Run scan against empty filesystem. Assert all 3 rows now have `classifier_version == CLASSIFIER_VERSION`. Assert their classification is `irrecoverable` with reason `missing_jsonl_on_disk` (their JSONLs are gone).

- **`test_scan_reclassifies_stale_row_whose_jsonl_still_exists`** — seed DB with 1 row at `classifier_version - 1` AND keep its JSONL on disk in the fixture's projects_root. Run scan. Assert the row's `classifier_version` is now current AND its classification was recomputed (the actual value depends on the synthetic JSONL's tail kind; assert it matches what `classify()` would produce for that input).

- **`test_scan_classifies_live_pid_as_live`** (AC6.2) — fixture with one session that has a liveness file pointing to `os.getpid()` (the test process — guaranteed alive) and a fresh boot_id matching current. Run scan. Assert the row's `classification == "live"` AND `classification_reason == "live_pid_present_boot_current"`.

- **`test_scan_classifies_boot_mismatch_as_hard_crash_even_if_pid_alive`** (AC5.6 end-to-end) — fixture with one session whose liveness file has `boot_id="00000000-0000-0000-0000-000000000000"` (guaranteed to not match the real boot_id) AND points to `os.getpid()` (alive). Run scan. Assert the row's `classification == "hard_crash"` AND `classification_reason == "liveness_boot_id_mismatch"`. This is the key assertion of AC5.6: boot mismatch wins over PID-alive.

- **`test_scan_marks_vanished_jsonl_as_irrecoverable`** — seed DB with a row whose `jsonl_path` points to a non-existent file. Run scan (no liveness, no JSONLs on disk). Assert the row updated to `IRRECOVERABLE` with reason `missing_jsonl_on_disk`.

- **`test_scan_writes_scan_runs_with_live_pids`** — fixture with two live sessions and one crashed. Run scan. Assert the `scan_runs.live_pids` column parses as a JSON array containing exactly the two live PIDs, sorted.

- **`test_scan_atomic_on_simulated_failure`** — monkey-patch `_upsert_session` to raise after the second of three calls. Run scan, catch the exception. Assert NO rows were written to `sessions` (transaction rolled back) AND no `scan_runs` row was created.

- **`test_scan_cli_refuses_to_run_on_non_linux`** — invoke `crash-recovery scan` as a subprocess with `sys.platform` monkey-patched (or run a pytest-conditional skip on non-Linux that still asserts the import path doesn't raise). On non-Linux: assert exit code 2 and stderr contains `requires Linux`. On Linux: parametrise with `monkeypatch.setattr(sys, "platform", "darwin")` invoking the CLI function directly (subprocess won't propagate the monkeypatch), assert `typer.Exit` raised with code 2.

- **`test_scan_cli_refuses_when_run_dir_is_on_network_fs`** — monkey-patch `crash_recovery.liveness._detect_fstype` to return `"nfs4"`. Invoke the scan CLI function directly with a valid temp `run_dir`; assert `typer.Exit` raised with code 2 and stderr mentions `CRASH_RECOVERY_RUN_DIR` and `nfs4`. Mirror test with `"fuse.sshfs"` to confirm prefix matching.

- **`test_scan_classifies_ambiguous_correlation_as_borderline_ambiguous_match`** (AC6.3) — fixture with one liveness file whose argv lacks `--resume`, pointing to a cwd whose project directory contains TWO JSONLs both within the mtime window. Run scan. Assert TWO sessions rows produced (one per candidate UUID), both with `classification == "borderline"` and `classification_reason == "ambiguous_match"`, both with `state_summary` containing the other candidate's UUID.

- **`test_scan_two_concurrent_invocations_do_not_corrupt_db`** (design Additional Considerations — concurrency requirement) — fixture with three synthetic sessions on disk. Spawn two `subprocess.Popen([sys.executable, "-m", "crash_recovery", "scan", "--db", path, "--run-dir", run_dir, "--projects-root", projects_root])` invocations against the same DB simultaneously; `wait()` both. Assert:
  - Both subprocesses exit 0 (no SQLite locked errors leaked out — the default 5s busy timeout under WAL absorbs the contention).
  - `sessions` row count is exactly 3 (no duplicates, no missing rows).
  - **`scan_runs` row count is exactly 2.** Both scans hold their own `with conn:` transaction; SQLite WAL serialises the writes; each transaction writes its own `scan_runs` row via `_write_scan_run`. There is no "skip if another scan is running" path, so the count is `== 2` by design (anything else signals a regression: 0 means both crashed, 1 means one rolled back silently, > 2 means duplicate scan_run rows).
  - Every `sessions` row's `classifier_version` equals `CLASSIFIER_VERSION`.
  - Every `sessions` row's `last_scanned` equals one of the two scan_runs timestamps.

  This test exercises the design's "Concurrency" claim in Additional Considerations: WAL mode + per-row upserts + scan_runs row as transaction boundary handles concurrent writes without corruption.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py -q
```

Expected: all tests pass.

**Step: Confirm Phase 4 done-when criteria**

```bash
uv run pytest -q
```

Expected: all Phase 1–4 tests pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py
git commit -m "test(crash-recovery): cover scan idempotency, AC3.6, AC5.6 end-to-end, AC6.2"
```
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 4 Done When

- `crash_recovery.scan` exposes `ScanContext`, `ScanRunResult`, `run_scan(ctx)`. The orchestrator walks filesystem (read-only), classifies, then writes in a single transaction.
- `crash-recovery scan` CLI subcommand works end-to-end (env-var or flag-driven).
- Idempotency tests pass: scan twice → identical `sessions` state (excluding `last_scanned`); `first_seen` preserved.
- AC3.6 test passes: pre-seeded rows at `CLASSIFIER_VERSION - 1` re-classified to current version.
- AC5.6 end-to-end test passes: boot_id mismatch wins over PID-alive.
- AC6.2 test passes: live PID classified as `live`.
- Repo-root `uv run pytest -q` passes (Phases 1–4 cumulative).

## Outstanding for later phases

- **(Documented design choice, accepted at Phase 4 closure 2026-05-17 via proleptic review.)** Single-transaction write model: `run_scan` holds the SQLite write lock for the entire walk + classify + upsert + sweep loop. WAL mode lets concurrent readers proceed; concurrent writers (other `scan` invocations) serialize at the write lock. Acceptable for expected scale (hundreds to low thousands of sessions per `~/.claude/`). Real-world starvation of a `render` waiting on a long `scan` would indicate the design needs revisiting (batched transactions, which would complicate rollback semantics). Phase 8's reboot/idle-kill UAT will surface any practical issue.
- **(Deferred to Phase 6 as design constraint, 2026-05-17 via proleptic review.)** Orphan-sweep + `user_notes` interaction: when Phase 6 adds the `note` subcommand, `_orphan_sweep` in `scan.py` must be modified to skip rows where `user_notes IS NOT NULL`. The constraint is recorded under **Design Constraints** in `phase_06.md`. The motivating concern: a user who annotates a session, then has its JSONL transiently unavailable (unmounted volume), then runs `scan`, would silently see classification flipped to `irrecoverable` — contradicting the annotation's "I care about this" intent. Phase 4 surfaced this via proleptic review but defers the resolution to where annotation semantics live.
- Phase 5: render markdown from DB; covers AC3.2 (byte-identical scan+render), AC2.1/AC2.2 partially (scan+render are listed subcommands).
- Phase 6: `note`, `history`, `prune`, `list-live` subcommands; covers AC4.* (annotations) and AC7.* (no-auto-prune).
- Phase 7: triage skill; covers AC1.2, AC8.1.
- Phase 8: wrapper patch; covers AC5.1/AC5.2/AC5.3/AC5.5 writer side, AC5.6 reboot UAT, AC6.4 idle-kill UAT, AC8.2/AC8.3.
