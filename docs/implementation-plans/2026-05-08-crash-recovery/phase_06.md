# denubis-crash-recovery Implementation Plan — Phase 6: `note`, `history`, `prune`, `list-live` subcommands

**Goal:** Add the DB-side management surface — user annotations on sessions, classification history readback, safely-gated prune, and a live-session listing.

**Architecture:** Four independent modules (`note`, `history`, `prune`, `list_live`) each exposing a small read or read/write function on the DB plus a typer subcommand. Prune applies a four-condition guard (concluded + no note + jsonl gone + classifier_version current); `--dry-run` prints candidates, `--confirm` deletes. List-live reads liveness files and filters by `pid_alive()`.

**Tech Stack:** Python 3.12+ stdlib; typer.

**Scope:** Phase 6 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-13. Phase 1 sessions schema includes `user_notes TEXT`; Phase 4 writes `classification_history` rows on every scan. Phase 5's render reads `user_notes` and surfaces it.

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

### crash-recovery.AC4: Annotations persist via SQLite
- **crash-recovery.AC4.1 Success:** `crash-recovery note <uuid> "x"` followed by `regenerate` causes "x" to appear under that UUID in `~/llm-resume.md`
- **crash-recovery.AC4.2 Success:** `note <uuid> "y"` against a UUID with an existing note overwrites the note; the prior text is no longer in the rendered output
- **crash-recovery.AC4.3 Success:** `note <uuid> --clear` removes the note; the subsequent render omits the user-notes line for that UUID
- **crash-recovery.AC4.5 Failure:** `note` against a UUID not in the DB exits non-zero with a clear error and does not insert a row

### crash-recovery.AC7: No automatic pruning
- **crash-recovery.AC7.2 Success:** `crash-recovery prune --dry-run` lists candidate rows but the DB row count is unchanged after the command exits
- **crash-recovery.AC7.3 Success:** `crash-recovery prune` invoked without `--confirm` refuses to delete and prints instructions on how to confirm
- **crash-recovery.AC7.4 Success:** `crash-recovery prune --confirm` deletes only rows where `classification = 'concluded' AND user_notes IS NULL AND jsonl_path` no longer exists on disk
- **crash-recovery.AC7.5 Failure:** A concluded session with a user note is NOT deleted by `prune --confirm` (note acts as preservation marker)
- **crash-recovery.AC7.6 Failure:** A concluded session whose JSONL is still on disk is NOT deleted by `prune --confirm` (filesystem-presence guard)
- **crash-recovery.AC7.7 Failure:** A session whose `classifier_version` is older than current is NOT deleted by `prune --confirm` until `scan` has re-classified it under the current rule table (prune operates only on rows reflecting current rules)

> **AC mapping correction:** the design plan's "Covers ACs" line for Phase 6 lists `crash-recovery.AC2.3` (the `init` AC, which belongs to Phase 1). Phase 6's actual coverage is AC4.* and AC7.* as listed above.

---

## Design Constraints

### Annotation-preserves-classification (deferred from Phase 4 proleptic review, 2026-05-17)

When Phase 6 implements `note`, the `user_notes` column becomes load-bearing for the user's intent — it signals "I care about this session; don't lose it". Phase 4's `_orphan_sweep` in `scan.py` re-classifies any row not seen in the filesystem walk: if `jsonl_path` is gone or NULL, the row's classification flips to `IRRECOVERABLE/missing_jsonl_on_disk`. This means a user who annotates a session, then has its JSONL transiently unavailable (unmounted volume, network filesystem hiccup, etc.), then runs `scan`, will silently see the classification flip to irrecoverable — even though their annotation said they wanted to keep it.

AC7.5 already exempts annotated rows from `prune --confirm`. The same logical exemption should apply to classification reset, since reset to `irrecoverable` can mislead the user about the session's actual recoverability (and the user's `user_notes` survives the reset, creating a contradictory record: "user said keep, classification says give up").

**Phase 6 must include a task** — placed in Subcomponent A alongside `note.py` so the constraint lands when `user_notes` becomes a load-bearing column — that:

1. Modifies `_orphan_sweep` in `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py` to skip rows where `user_notes IS NOT NULL`. The skip preserves both `classification` and `classifier_version` on annotated orphans. (`last_scanned` may still be refreshed since it's a bookkeeping field, not a user-intent field; the decision is documented in the new test's docstring.)
2. Adds `test_orphan_sweep_preserves_annotated_session_classification` in `tests/test_scan.py`: seed an annotated row with a vanished `jsonl_path`, run `scan`, assert `classification` and `classifier_version` unchanged and a `classification_history` row is NOT appended for it (no reclassification means no history entry).
3. Adds a paired test `test_orphan_sweep_reclassifies_unannotated_session` that re-verifies the existing AC3.6 behaviour on rows where `user_notes IS NULL` — to pin the exemption is scoped to annotated rows only.

This is a Phase 4 code change driven by Phase 6's semantics: the constraint surfaced in Phase 4's proleptic review, but the fix belongs with the annotation feature that motivates it. Phase 4's plan-level Outstanding section cross-references this constraint.

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: `crash_recovery.note` module

**Verifies:** AC4.1, AC4.2, AC4.3, AC4.5 (full verification via Task 2 CLI tests).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/note.py`

**Implementation:**

```python
"""User-note CRUD on the sessions table."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from crash_recovery import db


class UnknownSessionError(LookupError):
    """Raised when a note operation targets a UUID not in the sessions table."""


def set_note(db_path: Path, uuid: str, text: str) -> None:
    """Set or overwrite the user_notes column for a session."""
    with closing(db.open_db(db_path)) as conn:
        with conn:
            cur = conn.execute(
                "UPDATE sessions SET user_notes = ? WHERE uuid = ?",
                (text, uuid),
            )
            if cur.rowcount == 0:
                raise UnknownSessionError(f"no session with uuid {uuid}")


def clear_note(db_path: Path, uuid: str) -> None:
    """Set user_notes = NULL for a session."""
    with closing(db.open_db(db_path)) as conn:
        with conn:
            cur = conn.execute(
                "UPDATE sessions SET user_notes = NULL WHERE uuid = ?",
                (uuid,),
            )
            if cur.rowcount == 0:
                raise UnknownSessionError(f"no session with uuid {uuid}")
```

Key invariants:
- `UPDATE … WHERE uuid = ?` with `rowcount == 0` is the AC4.5 fail-loud guard: no INSERT-OR-CREATE behaviour, no silent acceptance of a typo'd UUID.
- Connection is opened via Phase 1's `db.open_db()` which asserts WAL mode.
- The `with conn:` context manager wraps the UPDATE in a transaction.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery import db, note
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'x.db'
    db.init(p)
    try:
        note.set_note(p, 'no-such-uuid', 'hi')
    except note.UnknownSessionError as e:
        print('OK:', e)
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/note.py
git commit -m "feat(crash-recovery): add note module with set_note, clear_note, UnknownSessionError"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `crash-recovery note` CLI subcommand + tests

**Verifies:** AC4.1, AC4.2, AC4.3, AC4.5.

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_note.py`

**CLI implementation:**

```python
@app.command()
def note(
    uuid: str = typer.Argument(..., help="Session UUID."),
    text: str = typer.Argument(None, help="Note text. Omit and pass --clear to remove."),
    clear: bool = typer.Option(False, "--clear", help="Remove the existing note for this UUID."),
    db_path: Path = typer.Option(None, "--db"),
) -> None:
    """Set, overwrite, or clear the user note for a session."""
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    try:
        if clear:
            if text is not None:
                raise typer.BadParameter("--clear cannot be combined with a text argument")
            _note.clear_note(resolved_db, uuid)
            typer.echo(f"Cleared note for {uuid}")
        else:
            if text is None:
                raise typer.BadParameter("missing note text (or pass --clear)")
            _note.set_note(resolved_db, uuid, text)
            typer.echo(f"Set note for {uuid}")
    except _note.UnknownSessionError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2)
```

Update `EXPECTED_SUBCOMMANDS` to include `"note"`.

**Required tests in `test_note.py`:**

- **`test_note_set_then_regenerate_surfaces_text`** (AC4.1) — seed DB with a known UUID + concluded row + last_scanned. Call `set_note(db, uuid, "abc")`. Render via Phase 5's `render(db_path)`. Assert "abc" appears under that UUID.
- **`test_note_overwrites_existing`** (AC4.2) — set "first", then set "second"; render; assert "first" is NOT present and "second" IS.
- **`test_note_clear_removes_note`** (AC4.3) — set, then clear, then render; assert no Notes line for that UUID.
- **`test_note_unknown_uuid_raises_and_does_not_insert`** (AC4.5) — DB has no rows. Attempt `set_note(db, "no-such-uuid", "x")`. Assert `UnknownSessionError` raised. Assert sessions row count is still 0 (no silent insert).
- **`test_note_cli_unknown_uuid_exits_nonzero_with_error_text`** — invoke `crash-recovery note no-such "text"` via subprocess; assert exit code != 0 AND stderr contains "no session with uuid".
- **`test_note_cli_clear_without_text`** — invoke `crash-recovery note <real-uuid> --clear`; assert exit 0; assert DB row's user_notes is NULL.
- **`test_note_cli_clear_with_text_is_rejected`** — invoke `crash-recovery note <uuid> "text" --clear`; assert exit code != 0 (typer.BadParameter).

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_note.py -q
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_note.py
git commit -m "feat(crash-recovery): add note CLI subcommand; cover AC4.1, AC4.2, AC4.3, AC4.5"
```
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (task 3) -->

<!-- START_TASK_3 -->
### Task 3: `crash-recovery history <uuid>` subcommand

**Verifies:** indirect — history readback supports debugging classifier_version drift; no direct AC mapping.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/history.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_history.py`

**Implementation:**

`history.py` exposes:

```python
@dataclass(frozen=True)
class HistoryEntry:
    scan_id: int
    scan_ts: int
    classification: str
    reason: str | None
    classifier_version: int


def fetch_history(db_path: Path, uuid: str) -> tuple[HistoryEntry, ...]:
    """Return all classification_history rows for a UUID, scan_id ASC (chronological)."""
    with closing(db.open_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT ch.scan_id, sr.ts, ch.classification, ch.reason, ch.classifier_version "
            "FROM classification_history ch "
            "JOIN scan_runs sr ON sr.id = ch.scan_id "
            "WHERE ch.uuid = ? "
            "ORDER BY ch.scan_id ASC",
            (uuid,),
        ).fetchall()
    return tuple(HistoryEntry(*row) for row in rows)
```

CLI subcommand prints a plain-text table:

```python
@app.command()
def history(
    uuid: str = typer.Argument(...),
    db_path: Path = typer.Option(None, "--db"),
) -> None:
    """Show all recorded classifications for a session, chronologically."""
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    entries = _history.fetch_history(resolved_db, uuid)
    if not entries:
        typer.echo(f"No history for {uuid}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{'scan_id':>8} {'ts':>11} {'classification':<16} {'reason':<40} {'cv':>3}")
    for e in entries:
        reason = e.reason or ""
        typer.echo(f"{e.scan_id:>8} {e.scan_ts:>11} {e.classification:<16} {reason:<40} {e.classifier_version:>3}")
```

Update `EXPECTED_SUBCOMMANDS` to include `"history"`.

**Required tests:**
- `test_history_returns_chronological_entries` — fixture with two scan_runs and two history rows for same UUID; assert `fetch_history(db, uuid)` returns both in scan_id ASC order.
- `test_history_for_unknown_uuid_returns_empty` — assert empty tuple.
- `test_history_cli_for_unknown_uuid_exits_nonzero` — assert exit code 1, stderr message.
- `test_history_includes_classifier_version` — fixture has rows at versions 1 and 2; assert both surface in the table.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/history.py plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_history.py
git commit -m "feat(crash-recovery): add history subcommand for classification audit"
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_B -->

---

<!-- START_SUBCOMPONENT_C (tasks 4-5) -->

<!-- START_TASK_4 -->
### Task 4: `crash_recovery.prune` module — candidate query + delete

**Verifies:** AC7.2 (candidates list read-only), AC7.4 (--confirm deletes only matching rows), AC7.5, AC7.6, AC7.7 (guards).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/prune.py`

**Implementation:**

```python
"""Safely-gated removal of concluded sessions."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from crash_recovery import db
from crash_recovery.classify import CLASSIFIER_VERSION


@dataclass(frozen=True)
class Candidate:
    uuid: str
    cwd: str
    last_scanned: int


@dataclass(frozen=True)
class PruneSurvey:
    candidates: tuple[Candidate, ...]
    stale_version_concluded_rows: int  # count of would-be candidates excluded by AC7.7


def survey(db_path: Path) -> PruneSurvey:
    """Read-only assessment. AC7.2: does not modify the DB."""
    with closing(db.open_db(db_path)) as conn:
        # AC7.7 filter: only consider rows at current classifier_version.
        all_concluded = conn.execute(
            "SELECT uuid, cwd, last_scanned, jsonl_path, user_notes, classifier_version "
            "FROM sessions WHERE classification = 'concluded'"
        ).fetchall()
    candidates: list[Candidate] = []
    stale_count = 0
    for uuid, cwd, last_scanned, jsonl_path, user_notes, cv in all_concluded:
        if cv != CLASSIFIER_VERSION:
            # AC7.7: prune does not touch rows whose classification was computed
            # under an older rule table. Count them for the warning.
            if user_notes is None and (jsonl_path is None or not Path(jsonl_path).exists()):
                stale_count += 1
            continue
        # AC7.5: skip rows with a user note.
        if user_notes is not None:
            continue
        # AC7.6: skip rows whose JSONL is still on disk.
        if jsonl_path and Path(jsonl_path).exists():
            continue
        candidates.append(Candidate(uuid=uuid, cwd=cwd, last_scanned=last_scanned))
    return PruneSurvey(
        candidates=tuple(candidates),
        stale_version_concluded_rows=stale_count,
    )


def delete_candidates(db_path: Path, uuids: tuple[str, ...]) -> int:
    """Delete the supplied UUIDs from sessions. Returns count of rows deleted."""
    if not uuids:
        return 0
    with closing(db.open_db(db_path)) as conn:
        with conn:
            placeholders = ",".join("?" * len(uuids))
            cur = conn.execute(
                f"DELETE FROM sessions WHERE uuid IN ({placeholders})",
                uuids,
            )
            return cur.rowcount
```

Critical invariants:
- `survey()` opens a read-only-style connection (Phase 1's `open_db` is read/write, but `survey` never writes — code review enforces no writes here).
- `delete_candidates` is the ONLY function that mutates rows. The caller must pass the survey's UUIDs verbatim; the survey already applied the four-condition guard.
- `survey().stale_version_concluded_rows` lets the CLI surface the AC7.7 warning text.
- The `DELETE FROM sessions` triggers a cascade to `classification_history` rows for the same UUID via Phase 1's `FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE` constraint. `PRAGMA foreign_keys = ON` is set by `db.open_db` so the cascade fires inside the same transaction; there is no separate `DELETE FROM classification_history` to write. `history <uuid>` for a pruned UUID consequently returns zero rows.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery import db, prune
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'x.db'
    db.init(p)
    s = prune.survey(p)
    assert s.candidates == ()
    assert s.stale_version_concluded_rows == 0
    print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/prune.py
git commit -m "feat(crash-recovery): add prune module with four-condition guard and survey/delete split"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `crash-recovery prune` CLI + tests

**Verifies:** AC7.2, AC7.3, AC7.4, AC7.5, AC7.6, AC7.7.

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_prune.py`

**CLI implementation:**

```python
@app.command()
def prune(
    dry_run: bool = typer.Option(False, "--dry-run", help="List candidate rows; do not delete."),
    confirm: bool = typer.Option(False, "--confirm", help="Execute deletion."),
    db_path: Path = typer.Option(None, "--db"),
) -> None:
    """Delete concluded sessions whose JSONLs are gone (gated)."""
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    survey = _prune.survey(resolved_db)
    if survey.stale_version_concluded_rows > 0:
        typer.echo(
            f"warning: {survey.stale_version_concluded_rows} concluded session(s) are at a stale "
            f"classifier_version and were excluded from this prune. Run `crash-recovery scan` to "
            f"refresh them, then re-run prune.",
            err=True,
        )
    if dry_run and confirm:
        raise typer.BadParameter("--dry-run and --confirm are mutually exclusive")
    if dry_run:
        # AC7.2: list candidates, do not delete.
        if not survey.candidates:
            typer.echo("No prune candidates.")
            return
        typer.echo(f"{len(survey.candidates)} session(s) would be deleted:")
        for c in survey.candidates:
            typer.echo(f"  {c.uuid}  cwd={c.cwd}  last_scanned={c.last_scanned}")
        return
    if not confirm:
        # AC7.3: refuse without --confirm.
        typer.echo(
            "Refusing to delete without --confirm.\n"
            "Run `crash-recovery prune --dry-run` to see what would be deleted, then re-run with --confirm.",
            err=True,
        )
        raise typer.Exit(code=1)
    # AC7.4: --confirm executes.
    n = _prune.delete_candidates(resolved_db, tuple(c.uuid for c in survey.candidates))
    typer.echo(f"Deleted {n} session(s).")
```

Update `EXPECTED_SUBCOMMANDS` to include `"prune"`.

**Required tests in `test_prune.py`:**

- **`test_prune_dry_run_is_read_only`** (AC7.2) — seed DB with one prune-eligible row (concluded, no note, no JSONL on disk, current classifier_version). Capture sessions row count. Invoke `crash-recovery prune --dry-run` via subprocess. Assert the dry-run output names the candidate UUID. Assert sessions row count is unchanged.
- **`test_prune_without_confirm_refuses`** (AC7.3) — same setup. Invoke `crash-recovery prune` (no flags). Assert exit code != 0. Assert stderr contains "--confirm" instruction. Assert sessions row count unchanged.
- **`test_prune_confirm_deletes_matching_rows`** (AC7.4) — same setup. Invoke `crash-recovery prune --confirm`. Assert exit 0. Assert sessions row count decreased by 1.
- **`test_prune_preserves_concluded_with_user_note`** (AC7.5) — seed DB with a concluded row that has `user_notes = "important"`, no JSONL on disk, current version. Invoke `prune --confirm`. Assert the row remains.
- **`test_prune_preserves_concluded_with_extant_jsonl`** (AC7.6) — seed DB with a concluded row whose `jsonl_path` points to an existing fixture file. Invoke `prune --confirm`. Assert the row remains.
- **`test_prune_excludes_stale_classifier_version_rows`** (AC7.7) — seed DB with one row at `CLASSIFIER_VERSION` (eligible) and one at `CLASSIFIER_VERSION - 1` (also otherwise eligible). Invoke `prune --dry-run`. Assert dry-run lists ONLY the current-version row. Assert stderr contains the "stale classifier_version" warning text.
- **`test_prune_confirm_does_not_delete_stale_rows`** (AC7.7) — same as above; invoke `--confirm`. Assert the current-version row deleted, stale row remains.
- **`test_prune_dry_run_and_confirm_mutually_exclusive`** — invoke `crash-recovery prune --dry-run --confirm`. Assert exit code != 0 (typer.BadParameter).
- **`test_prune_empty_db`** — empty DB. Invoke `--dry-run`. Assert "No prune candidates." printed. Invoke `--confirm`. Assert "Deleted 0 session(s).".
- **`test_prune_cascades_classification_history_deletion`** — seed DB with one prune-eligible row (concluded, no note, no JSONL, current version) AND seed `classification_history` with two history rows for the same `uuid` (e.g. from two prior scans). Assert pre-prune: `classification_history` row count = 2. Invoke `prune --confirm`. Assert post-prune: the `sessions` row is gone AND the two `classification_history` rows are gone (cascade fired via the `FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE` on the `classification_history` table; `PRAGMA foreign_keys = ON` is set by `db.open_db`). This locks Phase 1's schema decision against silent regression and confirms `history <uuid>` on a pruned UUID naturally returns no rows.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_prune.py -q
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_prune.py
git commit -m "feat(crash-recovery): add prune CLI; cover AC7.2-AC7.7"
```
<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_C -->

---

<!-- START_SUBCOMPONENT_D (task 6) -->

<!-- START_TASK_6 -->
### Task 6: `crash-recovery list-live` subcommand

**Verifies:** indirect (no direct AC mapping; supports user diagnostics).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/list_live.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_list_live.py`

**Implementation:**

`list_live.py` exposes:

```python
@dataclass(frozen=True)
class LiveEntry:
    pid: int
    cwd: str
    started: int
    argv: str
    boot_id_current: bool


def survey_live(run_dir: Path) -> tuple[LiveEntry, ...]:
    """Return liveness records whose PID is alive AND whose boot_id matches current."""
    from crash_recovery.liveness import list_liveness_files, pid_alive, current_boot_id
    current_bid = current_boot_id()
    entries: list[LiveEntry] = []
    for live in list_liveness_files(run_dir):
        if not pid_alive(live.pid):
            continue
        entries.append(LiveEntry(
            pid=live.pid,
            cwd=live.cwd,
            started=live.started,
            argv=live.argv,
            boot_id_current=(live.boot_id == current_bid),
        ))
    return tuple(entries)
```

CLI subcommand:

```python
import json

@app.command(name="list-live")
def list_live(
    run_dir: Path = typer.Option(None, "--run-dir"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON array instead of plain table."),
) -> None:
    """List currently-running Claude wrappers per liveness data."""
    resolved_run_dir = _resolve(run_dir, "CRASH_RECOVERY_RUN_DIR", "~/.claude/run")
    entries = _list_live.survey_live(resolved_run_dir)
    if json_out:
        payload = [
            {"pid": e.pid, "cwd": e.cwd, "started": e.started, "argv": e.argv, "boot_id_current": e.boot_id_current}
            for e in entries
        ]
        typer.echo(json.dumps(payload, indent=2))
        return
    if not entries:
        typer.echo("No live sessions.")
        return
    typer.echo(f"{'pid':>8} {'started':>11} {'boot_ok':>7} {'cwd':<40} argv")
    for e in entries:
        typer.echo(f"{e.pid:>8} {e.started:>11} {'yes' if e.boot_id_current else 'NO':>7} {e.cwd:<40} {e.argv}")
```

Update `EXPECTED_SUBCOMMANDS` to include `"list-live"`.

**Required tests:**
- `test_list_live_empty_run_dir_returns_empty_tuple` — pass a `Path` that doesn't exist; assert `survey_live` returns `()`.
- `test_list_live_filters_dead_pids` — create two liveness files, one with `os.getpid()` (alive) and one with `2**30` (dead); assert `survey_live` yields only the live one.
- `test_list_live_marks_boot_id_mismatch` — create a liveness file with `boot_id="00000000-…"` and `pid=os.getpid()`; assert the resulting LiveEntry has `boot_id_current=False`.
- `test_list_live_cli_plain_text` — same fixture; invoke subprocess; assert output contains expected columns.
- `test_list_live_cli_json` — same fixture; invoke with `--json`; assert output parses as a JSON array with the expected fields.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_list_live.py -q
```

**Step: Confirm Phase 6 done-when criteria**

```bash
uv run pytest -q
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery --help
# Help output must now list: init, scan, render, triage, regenerate, note, history, prune, list-live
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/list_live.py plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_list_live.py
git commit -m "feat(crash-recovery): add list-live subcommand (plain + --json output)"
```
<!-- END_TASK_6 -->

<!-- END_SUBCOMPONENT_D -->

---

## Phase 6 Done When

- `note`, `history`, `prune`, `list-live` subcommands all present in `crash-recovery --help`.
- AC4.1, AC4.2, AC4.3, AC4.5 tests pass (annotation CRUD).
- AC7.2, AC7.3, AC7.4, AC7.5, AC7.6, AC7.7 tests pass (prune guards).
- `crash-recovery --help` now lists all 9 documented subcommands (`init`, `scan`, `render`, `triage`, `regenerate`, `note`, `history`, `prune`, `list-live`) — completes AC2.1.
- Repo-root `uv run pytest -q` passes (Phases 1–6 cumulative).

## Deferred from phase-5 review

- **`_render_to_file` opens a second SQLite connection for `COUNT(*)`** (`plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py:180-182`). Phase 5 code review (2026-05-17) surfaced a narrow TOCTOU window where a concurrent `scan` between the `os.replace` and the `COUNT(*)` query can produce a stale "Rendered N sessions" line (cosmetic, off-by-one or off-by-two on the user-visible echo only — the rendered file itself is always consistent). Reviewer marked Minor with "No action required before merge". Phase 6 owns the resolution because (a) Phase 6 adds more typer subcommands (`note`, `history`, `prune`, `list-live`) that share the same `__main__.py` module and CLI patterns, so consolidating the count-handling can ride alongside, and (b) the natural fix lands in render itself or the CLI wrapper, both of which Phase 6 touches. Suggested fix options, pick whichever Phase 6 finds least intrusive: (i) `render()` returns `tuple[str, int]` so the count comes from the same read transaction; (ii) drop the count from the user-visible line; (iii) accept the TOCTOU window with an explicit comment. No test owed unless the fix changes user-visible semantics.

  **If you pick option (i)**, the return-type change requires SIMULTANEOUS updates across four sites — do not commit partial coverage:
  1. `crash_recovery/render.py::render()` — change signature to `tuple[str, int]` and adjust the body to extract the count from the same `conn.execute(...).fetchall()` call (use `len(rows)` rather than a second `COUNT(*)` query).
  2. `crash_recovery/__main__.py::_render_to_file` — unpack `(content, n) = _render.render(db_path)`; drop the second `sqlite3.connect`.
  3. `crash_recovery/__main__.py::triage` — currently `typer.echo(_render.render(ctx.db_path), nl=False)`; must become `content, _ = _render.render(...); typer.echo(content, nl=False)` (or surface the count somewhere — current `triage` doesn't echo it).
  4. `crash_recovery/tests/test_render.py::test_render_matches_snapshot[empty|mixed|all_concluded]` AND `test_render_is_byte_identical_across_calls` — both call `render.render(db_path)` and compare against snapshot strings via `==`. With a tuple return, these fail with cryptic `TypeError: cannot compare tuple to str`. Unpack the tuple in the test body or update the helper. The expected_*.md snapshot fixtures themselves DO NOT change.

  Without all four updates landing together, the test suite reports an unhelpful failure rather than a useful diff. (Falsification anchor surfaced by Phase 5 proleptic challenge CA3, 2026-05-17.)

## Outstanding for later phases

- Phase 7: triage skill registration; verifies AC1.2 (plugin lists after install), AC8.1 (README documents dependency).
- Phase 8: wrapper patch + version bumps; verifies AC5.1/AC5.2/AC5.3/AC5.5 writer side, AC5.6 reboot UAT, AC6.4 idle-kill UAT, AC8.2 (version sync), AC8.3 (CHANGELOG entries).
