# denubis-crash-recovery Implementation Plan — Phase 5: `render` subcommand and markdown contract

**Goal:** Pure DB-to-markdown render of `~/llm-resume.md`. Same DB state ⇒ byte-identical markdown. Concluded sessions remain present; direct edits to the file are overwritten on regenerate.

**Architecture:** `crash_recovery.render.render(db_path)` opens the SQLite DB read-only, queries `sessions` rows sorted by `last_scanned DESC`, groups them into six fixed sections, and emits a single markdown string. Section assignment is a pure function of `(classification, classification_reason)`. The reason prefix (`liveness_*` / `no_liveness_*` / JSONL-only outcomes) drives a "reduced confidence" inline tag — resolves the design's backward-compatibility wording ("Liveness presence/absence is recorded in `sessions` as a boolean flag") by deriving the boolean from the reason prefix rather than adding a column. See `LIVENESS_REASONS` / `NO_LIVENESS_REASONS` / `JSONL_ONLY_REASONS` in Task 1. The CLI subcommand writes via `tempfile + os.replace` for atomicity.

**Tech Stack:** Python 3.12+ stdlib (`sqlite3`, `pathlib`, `tempfile`, `os`); typer for the CLI wiring.

**Scope:** Phase 5 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-13. Phase 4's `sessions` schema is final; render reads `uuid`, `project_path`, `cwd`, `classification`, `classification_reason`, `classifier_version`, `state_summary`, `last_scanned`, `user_notes`.

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

This phase implements and tests:

### crash-recovery.AC2: CLI exposes the documented surface
- **crash-recovery.AC2.1 Success (advance):** `crash-recovery --help` now lists `render`, `triage`, `regenerate` alongside `init` and `scan`. Full surface completes in Phase 6.
- **crash-recovery.AC2.2 Success:** Every new subcommand here (`render`, `triage`, `regenerate`) accepts `--help` and prints a usage-with-flags message.

### crash-recovery.AC3: Classification is deterministic
- **crash-recovery.AC3.2 Success:** Same fixture filesystem state passed through `scan` + `render` twice produces byte-identical markdown.

### crash-recovery.AC4: Annotations persist via SQLite
- **crash-recovery.AC4.4 Edge:** Direct edits to `~/llm-resume.md` do NOT persist across `regenerate` (the markdown is overwritten from DB state).

### crash-recovery.AC7: No automatic pruning
- **crash-recovery.AC7.1 Success:** After `regenerate`, previously-classified-concluded sessions remain present in both the DB and the rendered markdown.

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: `crash_recovery.render` — types, constants, section-assignment helpers

**Verifies:** none directly (foundation).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/render.py`

**Implementation:**

The module exposes:

1. **Reason-prefix constants** — resolve the design's backward-compatibility wording (a `liveness_present` BOOLEAN column was not added to the schema; instead, liveness presence is derived from the reason prefix):

   ```python
   from typing import Final

   LIVENESS_REASONS: Final[frozenset[str]] = frozenset({
       "live_pid_present_boot_current",
       "liveness_boot_id_mismatch",
       "liveness_dead_pid_tool_use_no_result",
       "liveness_dead_pid_ask_question_no_reply",
       "liveness_dead_pid_agent_dispatch_no_result",
       "liveness_dead_pid_unknown_tail",
   })
   NO_LIVENESS_REASONS: Final[frozenset[str]] = frozenset({
       "no_liveness_clean_end_turn",
       "no_liveness_dangling_tool_use",
       "no_liveness_dangling_ask_question",
       "no_liveness_dangling_agent_dispatch",
   })
   JSONL_ONLY_REASONS: Final[frozenset[str]] = frozenset({
       "malformed_tail",
       "empty_file",
       "missing_jsonl_on_disk",
       "unknown_tail_kind",
       "ambiguous_match",
       "unmatched",
   })
   ```

   These three sets MUST be disjoint and MUST exhaustively cover every reason emitted by Phase 2's `RULES` plus Phase 4's `ambiguous_match` override. A separate test (Task 6) asserts this partition.

2. **`Section`** — frozen dataclass with section metadata:

   ```python
   from dataclasses import dataclass
   from enum import StrEnum

   class SectionKey(StrEnum):
       CURRENTLY_UNFINISHED = "currently_unfinished"
       IDLE_LIVE_KILLED = "idle_live_killed"
       AMBIGUOUS_CORRELATION = "ambiguous_correlation"
       NEEDS_INVESTIGATION = "needs_investigation"
       RECENTLY_CONCLUDED = "recently_concluded"
       IRRECOVERABLE = "irrecoverable"

   @dataclass(frozen=True)
   class Section:
       key: SectionKey
       header: str            # "## Currently unfinished"
       empty_message: str     # rendered when section has zero rows
   ```

3. **`SECTIONS: tuple[Section, ...]`** — ordered tuple (this order is the document order). Six entries matching the six SectionKey values.

4. **`_section_for_row(classification, reason) -> SectionKey`** — pure function:

   ```python
   def _section_for_row(classification: str, reason: str) -> SectionKey:
       if classification == "live":
           return SectionKey.CURRENTLY_UNFINISHED
       if classification == "hard_crash":
           return SectionKey.IDLE_LIVE_KILLED
       if classification == "concluded":
           return SectionKey.RECENTLY_CONCLUDED
       if classification == "irrecoverable":
           return SectionKey.IRRECOVERABLE
       if classification == "borderline":
           if reason == "ambiguous_match":
               return SectionKey.AMBIGUOUS_CORRELATION
           return SectionKey.NEEDS_INVESTIGATION
       # Defensive default
       return SectionKey.NEEDS_INVESTIGATION
   ```

5. **`_reduced_confidence_text(reason) -> str | None`** — pure function returning the warning string or None:

   ```python
   def _reduced_confidence_text(reason: str) -> str | None:
       if reason in NO_LIVENESS_REASONS:
           return "no liveness file recorded (pre-installation session or wrapper bypass)"
       if reason in JSONL_ONLY_REASONS and reason != "ambiguous_match":
           return "session data is incomplete or corrupted"
       return None
   ```

   `ambiguous_match` does not get a reduced-confidence warning — the ambiguity itself is the warning, surfaced in its own section.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery.render import _section_for_row, _reduced_confidence_text, SectionKey
assert _section_for_row('live', 'live_pid_present_boot_current') is SectionKey.CURRENTLY_UNFINISHED
assert _section_for_row('borderline', 'ambiguous_match') is SectionKey.AMBIGUOUS_CORRELATION
assert _section_for_row('borderline', 'malformed_tail') is SectionKey.NEEDS_INVESTIGATION
assert _reduced_confidence_text('no_liveness_clean_end_turn') is not None
assert _reduced_confidence_text('live_pid_present_boot_current') is None
assert _reduced_confidence_text('ambiguous_match') is None
print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/render.py
git commit -m "feat(crash-recovery): add render module helpers (section assignment, reduced confidence)"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `render(db_path) -> str` — full markdown rendering

**Verifies:** AC3.2, AC7.1 indirectly (concluded rows appear when present in DB); full verification via Task 6.

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/render.py`

**Implementation:**

`render(db_path: Path) -> str` returns a single markdown string. Structure:

```
# Claude Code session resume

_Generated by crash-recovery. Direct edits to this file are overwritten on `crash-recovery regenerate`._

## Currently unfinished

<entries OR empty_message>

## Idle-live killed

<entries OR empty_message>

## Ambiguous correlation

<entries OR empty_message>

## Needs investigation

<entries OR empty_message>

## Recently concluded

<entries OR empty_message>

## Irrecoverable

<entries OR empty_message>
```

Each entry within a section follows this exact template (line by line — no variation; this is what the snapshot tests assert):

```
- **<uuid-short>**: `claudew --resume <full-uuid>`
  - Working dir: `<cwd>`
  - Classification: `<classification>` (`<reason>`)
  - State: <state_summary>
  - ⚠ Reduced confidence: <warning text>            ← only when _reduced_confidence_text(reason) is not None
  - Notes: <user_notes>                              ← only when user_notes is not NULL
```

`<uuid-short>` is the first 8 characters of the UUID (e.g., `db0cc58f`). Entries within a section are sorted `last_scanned DESC`.

Implementation:

```python
import sqlite3
from contextlib import closing
from pathlib import Path

def render(db_path: Path) -> str:
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        rows = conn.execute(
            "SELECT uuid, cwd, classification, classification_reason, "
            "state_summary, user_notes, last_scanned "
            "FROM sessions ORDER BY last_scanned DESC"
        ).fetchall()
    # Group into sections by key (sorted by SECTIONS order, with DESC-by-last_scanned within).
    grouped: dict[SectionKey, list[tuple]] = {s.key: [] for s in SECTIONS}
    for row in rows:
        key = _section_for_row(row[2], row[3])
        grouped[key].append(row)

    parts: list[str] = [
        "# Claude Code session resume",
        "",
        "_Generated by crash-recovery. Direct edits to this file are overwritten on `crash-recovery regenerate`._",
        "",
    ]
    for section in SECTIONS:
        parts.append(section.header)
        parts.append("")
        section_rows = grouped[section.key]
        if not section_rows:
            parts.append(section.empty_message)
        else:
            for row in section_rows:
                parts.extend(_render_entry(row))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"  # exactly one trailing newline
```

`_render_entry(row) -> list[str]` produces the per-entry lines exactly as the template specifies.

**Determinism notes** (critical for AC3.2):

- All ordering uses `ORDER BY last_scanned DESC`. Ties in `last_scanned` (same epoch second across two rows) must produce stable order — append `, uuid ASC` as the secondary sort key.
- All conditional lines (Reduced confidence, Notes) are emitted in a fixed order whenever they appear.
- Section headers always appear in the same order even when empty.
- Trailing newline: exactly one `\n` at end of file (the `rstrip() + "\n"` pattern ensures this regardless of how many blank lines accumulated during rendering).
- No timestamps in the rendered output — `last_scanned` is used for sorting but NOT printed (it would make the rendering time-dependent and break byte-identical comparison across scan runs).

**Read-only connection:** opening with `mode=ro` URI guarantees render cannot accidentally write to the DB.

**Step: Verify operationally**

```bash
# Build a minimal DB, render it, check it has the six section headers.
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery import db, render
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'x.db'
    db.init(p)
    out = render.render(p)
    headers = ['Currently unfinished', 'Idle-live killed', 'Ambiguous correlation',
               'Needs investigation', 'Recently concluded', 'Irrecoverable']
    for h in headers:
        assert h in out, h
    assert out.endswith('\\n'), repr(out[-50:])
    assert not out.endswith('\\n\\n'), 'multiple trailing newlines'
    print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/render.py
git commit -m "feat(crash-recovery): render(db_path) emits stable markdown with 6 sections"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Empty DB renders the minimal six-section document

**Verifies:** rendering invariance to DB content; preliminary AC3.2 (empty fixture).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/render.py`

**Implementation:**

This is a property assertion rather than additional code — Task 2's `render()` already produces all six section headers regardless of DB content. Task 3 specifies the exact `empty_message` strings used in `SECTIONS`:

- Currently unfinished: `_No sessions classified as currently unfinished._`
- Idle-live killed: `_No sessions classified as idle-live killed._`
- Ambiguous correlation: `_No sessions with ambiguous correlation._`
- Needs investigation: `_No sessions needing investigation._`
- Recently concluded: `_No sessions classified as concluded._`
- Irrecoverable: `_No irrecoverable sessions._`

These strings are constants in `SECTIONS` (Task 1). Verification is part of Task 6's empty-fixture snapshot test.

**Step: Verify operationally** (no separate code change in this task; consolidated check):

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py::test_render_matches_snapshot -k empty -q
# Will pass once Task 6 lands the snapshot fixtures.
```

**Step: Commit** (consolidated with Task 2 if separate commit feels redundant; the skill allows bundling related infrastructure)

```bash
# If empty_message values are already set in Task 1's SECTIONS:
echo "No commit required for Task 3 — empty_message strings already in Task 1."
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (tasks 4-6) -->

<!-- START_TASK_4 -->
### Task 4: `crash-recovery render` typer subcommand

**Verifies:** AC2.1 advance (`render` listed), AC2.2 (render --help works).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`

**Implementation:**

Add a `render` typer subcommand. It must:
- Accept optional `--db PATH` (defaults to `CRASH_RECOVERY_DB` env var → `~/.claude/crash-recovery.db`).
- Accept optional `--output PATH` (defaults to `CRASH_RECOVERY_RESUME_PATH` env var → `~/llm-resume.md`).
- Call `render.render(db_path)` to get the markdown string.
- Write the string to `output` **atomically** via `tempfile.NamedTemporaryFile(dir=output.parent, delete=False)` + `os.replace`. This prevents a partial file appearing at `output` if the write is interrupted.
- Print a one-line confirmation: `Rendered <N> sessions to <output>` where N is the count of rows in `sessions`.

```python
import os
import tempfile
from pathlib import Path

from crash_recovery import render as _render


@app.command()
def render(
    db_path: Path = typer.Option(None, "--db"),
    output: Path = typer.Option(None, "--output"),
) -> None:
    """Render the crash-recovery DB to a markdown file."""
    resolved_db = _resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")
    resolved_out = _resolve(output, "CRASH_RECOVERY_RESUME_PATH", "~/llm-resume.md")
    content = _render.render(resolved_db)
    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=resolved_out.parent, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, resolved_out)
    # Count rows for the user-visible confirmation
    import sqlite3
    with sqlite3.connect(f"file:{resolved_db}?mode=ro", uri=True) as conn:
        (n,) = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
    typer.echo(f"Rendered {n} sessions to {resolved_out}")
```

Update `EXPECTED_SUBCOMMANDS` (from Phase 1 Task 6 / Phase 4 Task 4) to include `"render"`.

**Step: Verify operationally**

```bash
TMPDIR=$(mktemp -d)
CRASH_RECOVERY_DB="$TMPDIR/x.db" uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery init
CRASH_RECOVERY_DB="$TMPDIR/x.db" CRASH_RECOVERY_RESUME_PATH="$TMPDIR/out.md" uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery render
test -f "$TMPDIR/out.md" && grep -q "# Claude Code session resume" "$TMPDIR/out.md" && echo OK
rm -rf "$TMPDIR"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py
git commit -m "feat(crash-recovery): add render subcommand with atomic-write to ~/llm-resume.md"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `triage` and `regenerate` composite subcommands

**Verifies:** AC2.1 advance (`triage`, `regenerate` listed), AC2.2 (each accepts --help).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`

**Implementation:**

Add two composite subcommands that orchestrate scan + render:

```python
@app.command()
def triage(
    db_path: Path = typer.Option(None, "--db"),
    run_dir: Path = typer.Option(None, "--run-dir"),
    projects_root: Path = typer.Option(None, "--projects-root"),
) -> None:
    """Scan filesystem, then print the rendered report to stdout."""
    # Invoke scan (same option resolution as scan subcommand)
    ctx = _scan.ScanContext(
        db_path=_resolve(db_path, "CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db"),
        run_dir=_resolve(run_dir, "CRASH_RECOVERY_RUN_DIR", "~/.claude/run"),
        projects_root=_resolve(projects_root, "CRASH_RECOVERY_PROJECTS_ROOT", "~/.claude/projects"),
        now=int(time.time()),
    )
    _scan.run_scan(ctx)
    # Then render to stdout
    typer.echo(_render.render(ctx.db_path))


@app.command()
def regenerate(
    db_path: Path = typer.Option(None, "--db"),
    run_dir: Path = typer.Option(None, "--run-dir"),
    projects_root: Path = typer.Option(None, "--projects-root"),
    output: Path = typer.Option(None, "--output"),
) -> None:
    """Scan filesystem, then write the rendered report to the output file."""
    # ... same as triage's scan, then call the render-to-file path from Task 4 ...
```

Update `EXPECTED_SUBCOMMANDS` to include `"triage"` and `"regenerate"`.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery triage --help
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery regenerate --help
```

Both must exit 0.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py
git commit -m "feat(crash-recovery): add triage (scan+render-stdout) and regenerate (scan+render-file)"
```
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Snapshot tests + AC3.2/AC4.4/AC7.1 verification

**Verifies:** crash-recovery.AC3.2 (byte-identical render), crash-recovery.AC4.4 (direct edits don't persist), crash-recovery.AC7.1 (concluded sessions remain in render after regenerate), reduced-confidence rendering, reason-partition exhaustiveness.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/snapshots/expected_empty.md`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/snapshots/expected_mixed.md`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/snapshots/expected_all_concluded.md`
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/jsonl_builder.py` — add `make_db_with_sessions(tmp_path, sessions: list[DbFixtureRow]) -> Path` helper.

**`DbFixtureRow`** shape:

```python
@dataclass
class DbFixtureRow:
    uuid: str
    cwd: str
    classification: str
    classification_reason: str
    state_summary: str
    user_notes: str | None
    last_scanned: int       # fixed epoch for determinism (e.g., 1700000000 + index*60)
    first_seen: int         # same fixed scheme
    classifier_version: int = 1
    project_path: str = "/decoded/project/path"
    jsonl_path: str = "/jsonl/path.jsonl"
    jsonl_mtime: int = 1700000000
    jsonl_last_ts: int = 1700000000
```

The helper inserts the rows directly into a freshly-initialised DB (bypassing scan) so the snapshot tests don't depend on Phase 4's filesystem walk.

**Required tests:**

- **`test_render_matches_snapshot[empty]`** (AC3.2 empty case) — empty DB → assert `render(db_path)` equals `expected_empty.md` byte-for-byte.

- **`test_render_matches_snapshot[mixed]`** (AC3.2 mixed case) — DB with one row per section (`live`, `hard_crash`, `concluded`, `irrecoverable`, `borderline+ambiguous_match`, `borderline+malformed_tail`). One row carries a `user_notes` value to exercise the Notes line. Assert byte-equality with `expected_mixed.md`.

- **`test_render_matches_snapshot[all_concluded]`** (AC3.2 all-concluded case) — DB with three concluded rows, one with no-liveness reason and one with liveness reason. Assert byte-equality with `expected_all_concluded.md` (verifies the reduced-confidence inline tag fires for the no-liveness row).

- **`test_render_is_byte_identical_across_calls`** (AC3.2 idempotency) — call `render(db_path)` twice on the same fixture DB; assert outputs are `==`.

- **`test_render_overwrites_user_edits`** (AC4.4) — write a known fixture to the render output path; then call `regenerate` (or just `render` writing to the same path); read the file back; assert the user's text is gone and the rendered content is present.

- **`test_regenerate_preserves_concluded_rows`** (AC7.1) — fixture DB with two concluded rows. Call `regenerate`. Assert the rendered file still contains both concluded entries (no auto-pruning side-effect).

- **`test_reason_prefix_partition_is_exhaustive`** — collect every `reason` string from Phase 2's `RULES` plus `"ambiguous_match"` (Phase 4's override reason) plus `"unmatched"` (Phase 2's defensive fallback emitted when no row matches). Assert each is in exactly one of (LIVENESS_REASONS, NO_LIVENESS_REASONS, JSONL_ONLY_REASONS) sets. Without including `"unmatched"` explicitly, removing it from `JSONL_ONLY_REASONS` would not fail any test — defeats the partition guarantee. Catches drift if a new rule is added without updating the partition constants.

- **`test_reduced_confidence_emitted_for_no_liveness_only`** — render a fixture with a `no_liveness_clean_end_turn` row; assert the warning line is present. Render a fixture with a `live_pid_present_boot_current` row; assert the warning line is absent.

- **`test_section_assignment_for_every_phase_2_reason`** — parametrise over Phase 2's RULES; for each rule, assert `_section_for_row(rule.classification, rule.reason)` returns the expected SectionKey.

**Step: Verify operationally**

```bash
uv run pytest plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py -q
```

Expected: all tests pass; snapshots match byte-for-byte.

**Step: Confirm Phase 5 done-when criteria**

```bash
uv run pytest -q
```

Expected: all Phase 1–5 tests pass.

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_render.py plugins/denubis-crash-recovery/scripts/crash_recovery/tests/fixtures/
git commit -m "test(crash-recovery): snapshot tests for render, AC3.2/AC4.4/AC7.1 coverage"
```
<!-- END_TASK_6 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 5 Done When

- `crash_recovery.render.render(db_path)` returns a byte-stable markdown string with six sections in the documented order.
- `crash-recovery render`, `crash-recovery triage`, `crash-recovery regenerate` subcommands work end-to-end.
- Snapshot tests pass for three fixture DBs (empty, mixed, all_concluded).
- Render is idempotent: same DB → byte-identical output across calls.
- AC4.4 test passes (direct edits to the resume file don't persist).
- AC7.1 test passes (concluded rows remain visible after regenerate).
- Reason-prefix partition is exhaustive (test asserts all Phase 2 reasons map to exactly one of the three sets).
- Repo-root `uv run pytest -q` passes (Phases 1–5 cumulative).

## Outstanding for later phases

- Phase 6: `note`, `history`, `prune`, `list-live` subcommands; covers AC4.1/4.2/4.3/4.5 (annotation persistence) and AC7.2-AC7.7 (prune guards).
- Phase 7: triage skill registration; covers AC1.2, AC8.1.
- Phase 8: wrapper patch; covers AC5.1/5.2/5.3/5.5/5.6 writer side, AC6.4 idle-kill UAT, AC8.2/8.3.
