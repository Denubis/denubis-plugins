# Post-mortem crash detection — Phase 4: render overhaul + schema migration

**Goal:** Add `pane_title`/`last_substantive` columns via an idempotent additive migration; populate them at scan time; render an all-means-all report with a `## Probable system-crash victims` top section, full UUIDs, and the new fields — degrading gracefully on a not-yet-migrated DB.

**Architecture:** `db.py` gains the columns in DDL plus a `PRAGMA table_info`-guarded `ALTER TABLE ADD COLUMN` migration fired from `init()` only. `open_db()` asserts the columns are present and refuses with a RuntimeError if they are absent (directing the operator to run `crash-recovery init`); it does not run DDL. `jsonl.py` gains `last_substantive_text`. `scan_db`/`scan` populate the columns. `render.py` reroutes `hard_crash` to a new top section, shows the new fields + full UUID, and builds its read-only SELECT defensively.

**Tech Stack:** Python 3.14+ stdlib (sqlite3, datetime), pytest.

**Scope:** Phase 4 of 5 from `docs/design-plans/2026-06-12-crash-detection.md`. Depends on Phases 1-3.

**Codebase verified:** 2026-06-12 (commit 03b97f2; db/render/jsonl read this session).

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

### crash-detection.AC1: Crash victims surface as hard_crash (render side)
- **crash-detection.AC1.2 Success:** A `hard_crash` row renders in `## Probable system-crash victims` with its full UUID and a `claudew --resume <full-uuid>` line.

### crash-detection.AC5: All-means-all render
- **crash-detection.AC5.1 Success:** Every in-scope session renders; the crash highlight adds a section, never drops a roster row.
- **crash-detection.AC5.2 Success:** Row header uses the full UUID (not `uuid[:8]`); pane-title, last-substantive, and `jsonl_last_ts` appear when available.
- **crash-detection.AC5.3 Success:** Render is byte-identical for identical DB state.

### crash-detection.AC7: Schema migration
- **crash-detection.AC7.1 Success:** `init()` on a pre-existing DB lacking the new columns adds `pane_title`/`last_substantive` without data loss; re-running `init` is a no-op. `open_db()` does NOT mutate schema; against an un-migrated DB it refuses cleanly (RuntimeError → run `crash-recovery init`).
- **crash-detection.AC7.2 Success:** A fresh `init()` creates the columns from DDL.
- **crash-detection.AC7.3 Edge:** `render()` on a not-yet-migrated DB does not raise `no such column`; it renders with the new fields treated as absent.

---

## Context for the implementer

- **db.py:** `SESSIONS_DDL`, `init()`, `open_db()`. `open_db` opens read-write, asserts WAL, sets `PRAGMA foreign_keys`. `render()` (in `render.py`) opens its OWN `file:{db}?mode=ro` connection — it bypasses `open_db`, hence AC7.3.
- **render.py:** `SectionKey` StrEnum + `SECTIONS` tuple (currently 6); `_section_for_row` routes `hard_crash → IDLE_LIVE_KILLED` (the only thing routing there). `_render_entry` uses `_COL_*` index constants; header is `**{uuid[:8]}**`. The reason partition (`LIVENESS_REASONS`/`NO_LIVENESS_REASONS`/`JSONL_ONLY_REASONS`) is pinned by `test_render.py::test_reason_prefix_partition_is_exhaustive` — rerouting sections does NOT change reasons, so the partition is unaffected.
- **jsonl.py:** `parse_tail` filters to `_REAL_TYPES={assistant,user}` (type-level bookkeeping already dropped). The operator's leakage (`<usage>`, `<summary>`, `</task-notification>`, post-compaction boilerplate) is *content within* user turns — a content-level skip.
- **Determinism:** render is byte-identical per DB state. New fields are stored values; render `jsonl_last_ts` as a UTC ISO derived from the stored int (host-tz-independent).

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Additive schema migration in db.py

**Verifies:** crash-detection.AC7.1, crash-detection.AC7.2

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/db.py`
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_init.py` (unit)

**Implementation:**
- Add `pane_title TEXT` and `last_substantive TEXT` (both nullable, no constraint) to `SESSIONS_DDL` after `user_notes`.
- Add:
  ```python
  _ADDITIVE_SESSION_COLUMNS = (("pane_title", "TEXT"), ("last_substantive", "TEXT"))

  def _migrate_additive_columns(conn) -> None:
      existing = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
      for name, decl in _ADDITIVE_SESSION_COLUMNS:
          if name not in existing:
              conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} {decl}")
  ```
  (Column names are module constants, not user input — safe to interpolate.)
- Call `_migrate_additive_columns(conn)` in `init()` after the DDL loop — the sole DDL site. Do NOT call it from `open_db()`; instead, after `PRAGMA foreign_keys = ON`, assert schema-current via `PRAGMA table_info(sessions)` and raise `RuntimeError` if any `_ADDITIVE_SESSION_COLUMNS` entry is absent. This keeps DDL off the per-command hot path and avoids the concurrency race where concurrent openers each attempt the same `ADD COLUMN`.
- `_schema_hash` will change once (expected; it is a test helper, not a runtime invariant — see database.md migration strategy).

**Testing (test_init.py):**
- AC7.2: fresh `init()` → `PRAGMA table_info(sessions)` includes `pane_title`, `last_substantive`.
- AC7.1: build an "old-shape" DB (create a `sessions` table without the two columns, set WAL), insert a row, then call `init(path)` → both columns now present; pre-existing row's data retained; re-run `init(path)` → no error, schema unchanged (idempotent). Durability verified via a fresh raw `sqlite3.connect` after the connection closes. Also: call `open_db()` on the old-shape DB before running `init()` → raises `RuntimeError` matching `crash-recovery init`; fresh raw connection confirms columns were NOT added.

**Verification:** `uv run pytest .../tests/test_init.py -q` green.

**Commit:** `feat(crash-recovery): additive pane_title/last_substantive columns + open_db migration`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: last-substantive extraction in jsonl.py

**Verifies:** crash-detection.AC5.2 (extraction half)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/jsonl.py`
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_jsonl_tail.py` (unit)

**Implementation:**
Add `last_substantive_text(path, n=...) -> str | None`: read the last `n` lines (reuse the `deque`/parse approach), filter to `_REAL_TYPES`, walk backward, extract each entry's text, and return the first that is non-empty AND not content-level bookkeeping.
- Text extraction: assistant → join `text`-type content items; user → the string content, or joined `text` items if content is a list.
- Bookkeeping skip (`_BOOKKEEPING_MARKERS`): skip a turn whose extracted text (stripped) starts with any of `"<usage>"`, `"<summary>"`, `"</task-notification>"`, `"<task-notification>"`, or `"If you need specific details from before compaction"`. Also skip empty text.
- Return `None` if nothing substantive in the window. Keep it short (the column mirrors `state_summary`'s ~120-char spirit — truncate to a sane cap, e.g. 200 chars).

**Testing (test_jsonl_tail.py):** build JSONLs (extend the fixture builders) whose final real turns are bookkeeping:
- AC5.2: tail ending in `<usage>…</usage>` then `</task-notification>` preceded by a real assistant text → returns the real assistant text, not the bookkeeping.
- post-compaction boilerplate as the last user turn → skipped; returns the prior real turn.
- a tail with only bookkeeping → `None`.

**Verification:** `uv run pytest .../tests/test_jsonl_tail.py -q` green.

**Commit:** `feat(crash-recovery): last-substantive text extraction skipping bookkeeping`
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (task 3) -->

<!-- START_TASK_3 -->
### Task 3: scan populates pane_title + last_substantive

**Verifies:** crash-detection.AC5.2 (population half)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py` (`SessionFact`, the fact builders, `_walk_jsonl_only`)
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan_db.py` (`_upsert_session`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py` (integration)

**Implementation:**
- `SessionFact`: add `pane_title: str | None = None`, `last_substantive: str | None = None`.
- Liveness fact builders: `last_substantive = last_substantive_text(Path(jsonl_path))` when `jsonl_path` is not None; `pane_title = resurrect.label_for_cwd(snapshot, session_cwd)` where `snapshot = resurrect.snapshot_near(snapshots, liveness.started)` (thread `snapshots` from `_walk_sessions`, already loaded in Phase 3). `label_for_cwd` tolerates a `None` snapshot (hardened in Phase 3 — empty/old resurrect dir → `snapshot_near` is `None` → `pane_title` NULL, no crash), so no guard is needed at the call site.
  - **`session_cwd` is the cwd of the JSONL this row represents**, read from that session's OWN first-entry `cwd` (`first_record_field(jsonl, "cwd")`) — NOT `liveness.cwd`. Under a lossy encoded-dir collision two candidates share one directory but declare distinct cwds; labelling by `liveness.cwd` would attach the wrong pane's title to the candidate whose cwd differs. This is the same per-candidate-cwd discipline `correlate.py`'s corroboration uses (Phase 3). For ambiguous candidates, populate `pane_title` per candidate using each candidate's own cwd.
- `_walk_jsonl_only`: `last_substantive = last_substantive_text(jsonl_path)`; `pane_title = None` (no marker/started → no snapshot anchor).
- `scan_db._upsert_session`: add `pane_title`, `last_substantive` to the INSERT column list and the `ON CONFLICT DO UPDATE SET` clause (refresh on each scan, like the other derived fields).

**Testing (test_scan.py):**
- AC5.2: a fixture marker with a matching resurrect snapshot → the row's `pane_title` equals the snapshot label; `last_substantive` equals the JSONL's last real text. A jsonl-only session → `pane_title` NULL, `last_substantive` populated.
- AC5.2 (per-candidate cwd, CA2): an AMBIGUOUS marker whose two candidates have distinct cwds in one lossy-collided encoded dir, with a snapshot whose panes label each cwd differently → each candidate row's `pane_title` matches ITS OWN cwd's pane label, not the other's and not `liveness.cwd`'s. (Guards against regressing to `liveness.cwd` for the label lookup.)
- No-snapshot safety: a marker with an empty/non-existent resurrect dir → `snapshot_near` is `None` → `pane_title` NULL and scan does not crash (the `label_for_cwd(None, ...)` path hardened in Phase 3).

**Verification:** `uv run pytest .../tests/test_scan.py -q` green.

**Commit:** `feat(crash-recovery): scan populates pane_title + last_substantive`
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_SUBCOMPONENT_C (task 4) -->

<!-- START_TASK_4 -->
### Task 4: Render overhaul — top crash section, full UUID, new fields, graceful degradation

**Verifies:** crash-detection.AC1.2, crash-detection.AC5.1, crash-detection.AC5.2, crash-detection.AC5.3, crash-detection.AC7.3

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/render.py`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py` (extend `DbFixtureRow`/`make_db_with_sessions` for the new columns + `jsonl_last_ts`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py` (unit)

**Implementation:**
- `SectionKey`: rename `IDLE_LIVE_KILLED` → `PROBABLE_CRASH_VICTIMS` (value `"probable_crash_victims"`); make it the FIRST entry in `SECTIONS` with header `## Probable system-crash victims` and an appropriate empty message. `_section_for_row`: `hard_crash → SectionKey.PROBABLE_CRASH_VICTIMS`. (This is a rename+reorder; section count stays 6, the full roster is preserved — all-means-all.)
- **Update the dependent test + fixtures for the rename** (these reference the old name and WILL break otherwise): in `tests/test_render.py`, the `_EXPECTED_SECTIONS` mapping (every `("hard_crash", ...) : SectionKey.IDLE_LIVE_KILLED` entry → `SectionKey.PROBABLE_CRASH_VICTIMS`) and the section-comment docstrings (~lines 76, 412); and the snapshot fixtures under `tests/fixtures/snapshots/` (`expected_empty.md`, `expected_all_concluded.md`, `expected_mixed.md`) whose `## Idle-live killed` heading and ordering change to `## Probable system-crash victims` at the top. Regenerate the snapshot fixtures to match the new output.
- SELECT: build the column list defensively. Read `cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}` first; select `pane_title`/`last_substantive` if present else `NULL AS pane_title`/`NULL AS last_substantive`. Also select `jsonl_last_ts`. Add `_COL_*` constants for the new columns. This satisfies AC7.3 (render-only on un-migrated DB does not crash).
- `_render_entry`: 
  - Header (non-irrecoverable): lead with `**{pane_title or last_substantive-snippet or "(session " + uuid_full[:8] + ")"}**` then `` `claudew --resume {uuid_full}` `` (FULL uuid). AC5.2's "row header uses full UUID" is satisfied by the full UUID appearing in the resume-command line (the bold label is the human-meaningful pane-title/snippet, not a truncated hash). The 8-char form may appear ONLY as a last-resort parenthetical when no pane_title/last_substantive exists — never as the primary identifier and never replacing the full UUID in the resume line.
  - Add lines when present: `- Last activity: {utc_iso(jsonl_last_ts)}`, `- Last substantive: {last_substantive}`.
  - Keep `Working dir`, `Classification`, `State`, reduced-confidence, Notes lines. Irrecoverable rows keep the strikethrough no-resume opener but may still show pane_title/last activity.
  - `utc_iso(ts)`: `datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()` when `ts` is not None; omit the line otherwise (deterministic).
- Keep ordering `last_scanned DESC, uuid ASC` for byte-identical output.

**Testing (test_render.py):**
- AC1.2: a `hard_crash` row → appears under `## Probable system-crash victims`, header contains the FULL uuid, body has `claudew --resume <full-uuid>`.
- AC5.1: seed one row per classification (live, hard_crash, borderline/ambiguous_match, borderline/unknown_tail_kind, concluded, irrecoverable) → every uuid appears exactly once in the output; crash section present AND the other sections still populated.
- AC5.2: a row with pane_title + last_substantive + jsonl_last_ts → all three rendered; header is the full uuid, never the 8-char form.
- AC5.3: `render(db)` twice → byte-identical.
- AC7.3: seed an old-shape DB (no new columns) via direct SQL, then `render(db)` → no `OperationalError`; output renders (new fields absent).
- Existing `test_reason_prefix_partition_is_exhaustive` stays green (reasons unchanged).

**Verification:** `uv run pytest .../tests/test_render.py -q` green; full `uv run pytest` green (AC9.1); bats green (AC9.2).

**Commit:** `feat(crash-recovery): render crash-victims top section, full UUID, pane/last-substantive`
<!-- END_TASK_4 -->

<!-- END_SUBCOMPONENT_C -->

## Phase 4 done when

- New columns exist on fresh and migrated DBs; migration idempotent (AC7.1, AC7.2).
- `hard_crash` rows render in `## Probable system-crash victims` with full UUID + resume line (AC1.2); full roster preserved (AC5.1); pane-title/last-substantive/last-activity shown (AC5.2); byte-identical (AC5.3).
- render-only on an un-migrated DB does not crash (AC7.3).
- Full pytest + bats green (AC9).
