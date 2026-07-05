# Post-mortem crash detection — Phase 3: Stage-2 backlog disambiguation + tmux-resurrect

**Goal:** Resolve id-less backlog markers more precisely with a tight first-entry-ts window, and corroborate/label them with the tmux-resurrect pane set; when still ambiguous, list all candidates.

**Architecture:** New pure `resurrect.py` parses `~/.byobu-sessions/tmux_resurrect_*.txt` into snapshots of panes. `correlate.py`'s mtime branch gains an upper time bound (tight window) and an optional corroboration filter driven by the snapshot nearest a marker's `started`. `scan.py` loads snapshots once and threads corroboration into `correlate`.

**Tech Stack:** Python 3.14+ stdlib (pathlib, datetime), pytest.

**Scope:** Phase 3 of 5 from `docs/design-plans/2026-06-12-crash-detection.md`. Depends on Phases 1-2.

**Codebase verified:** 2026-06-12 (commit 03b97f2). Resurrect format confirmed against real snapshots in `~/.byobu-sessions/`.

**Phase Type:** functionality

---

## Acceptance Criteria Coverage

### crash-detection.AC6: Backlog disambiguation with tmux-resurrect
- **crash-detection.AC6.1 Success:** A backlog marker with exactly one in-tight-window JSONL resolves to `MTIME_MATCH`.
- **crash-detection.AC6.2 Success:** A multi-candidate set corroborated by exactly one resurrect `claude` pane resolves to that candidate.
- **crash-detection.AC6.3 Edge:** An uncorroborated multi-candidate set stays `borderline/ambiguous_match`, listing all candidates (never silently picks).
- **crash-detection.AC6.4 Success:** `resurrect.py` parses `pane` lines by field order, collects all pane cwds for path-based corroboration (NOT by command or the volatile `✳`/spinner glyph — see the glyph-volatility note below), and selects the latest snapshot at/just before `started`. The `✳` prefix is used only to pick the best *label* among same-cwd panes, never as a corroboration gate.

---

## Context for the implementer (grounded against real snapshots)

- **Snapshot path:** `~/.byobu-sessions/tmux_resurrect_<YYYYMMDDTHHMMSS>.txt` (NOT `~/.tmux/`). Timestamp is in the filename. Env override: `CRASH_RECOVERY_RESURRECT_DIR` (default `~/.byobu-sessions`).
- **`pane` line format (TAB-separated), 0-indexed:** `[0]=pane [1]=session [2]=window [3]=pane-idx [4]=flags(:*) [5]=1 [6]=<window title> [7]=:<pane_current_path> [8]=1 [9]=<pane_current_command> [10]=:<shell>`. The path and shell fields carry a **leading `:`** to strip. Real example (tabs shown as `\t`):
  `pane\t1\t1\t1\t:*\t1\t✳ Implement post-mortem crash detection…\t:/home/brian/people/Brian/brian-ed3d-plugins\t1\tbash\t:/usr/bin/fish -l`
- **Glyph volatility — important:** `pane_current_command` is the **shell** (`bash`/`fish`), NOT `claude` (the wrapper runs claude under bash). And the window-title leading glyph is **not stable**: an idle claude pane shows `✳` (U+2733, the `exec-session-naming` prefix), but a *busy* pane shows a spinner glyph (braille-range, e.g. U+2810) that changes frame to frame. **Therefore: corroborate by `pane_current_path`, not by command or the volatile glyph.** Use the `✳` prefix only to pick the best *label* when several panes share a path; never as the sole gate.
- **Determinism:** `Date.now()`-style calls are banned in scan; the snapshot timestamp comes from the filename, and "near `started`" is computed from stored values only.

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: resurrect.py parser

**Verifies:** crash-detection.AC6.4

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/resurrect.py`
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_resurrect.py` (unit)

**Implementation:**
Pure module, no I/O beyond reading the snapshot files it is given a dir for.

```python
@dataclass(frozen=True)
class Pane:
    window_title: str          # field 6, verbatim (may start with ✳ or a spinner glyph)
    cwd: str                   # field 7 with the leading ':' stripped
    command: str               # field 9 (the shell, not claude)

@dataclass(frozen=True)
class Snapshot:
    ts: int                    # unix epoch parsed from the filename's YYYYMMDDTHHMMSS (local time)
    panes: tuple[Pane, ...]
```

Functions:
- `parse_snapshot_file(path) -> Snapshot`: parse `ts` from the filename (`tmux_resurrect_YYYYMMDDTHHMMSS.txt`); read lines, keep those whose first TAB field == `pane`; split on `\t`; build `Pane` from fields 6/7/9 (strip leading `:` on field 7). Tolerant: skip malformed `pane` lines (<11 fields) with a `UserWarning`. Non-`pane` lines (window/state/etc.) are ignored.
- `load_snapshots(resurrect_dir) -> list[Snapshot]`: glob `tmux_resurrect_*.txt`, parse each, sorted by `ts`. Missing/empty dir → `[]`.
- `snapshot_near(snapshots, started, grace=0) -> Snapshot | None`: the snapshot with the greatest `ts <= started + grace` (the pre-crash save; continuum saves ~every 15 min). `None` if none qualify.
- `corroborating_cwds(snapshot) -> set[str]`: `{pane.cwd for pane in snapshot.panes}` (all pane cwds — corroboration is path-based per the glyph note).
- `label_for_cwd(snapshot, cwd) -> str | None`: among panes with that cwd, return the window_title, preferring one whose title startswith `✳` (`_CLAUDE_TITLE_PREFIX = "✳"`); `None` if no pane at that cwd. Used by Phase 4 for the render label.

**Testing (test_resurrect.py):** write a temp snapshot file mirroring the real TAB format (including the leading `:` on path/shell and a `✳`-titled pane).
- AC6.4 parse: `parse_snapshot_file` yields the expected `Pane`s — title verbatim, cwd with `:` stripped, command = shell.
- AC6.4 selection: `snapshot_near` picks the latest snapshot ≤ `started`; returns `None` when all are later.
- `label_for_cwd` prefers the `✳`-titled pane; `corroborating_cwds` includes the path.
- malformed `pane` line (too few fields) → skipped with `UserWarning`, others still parsed.

**Verification:** `uv run pytest .../tests/test_resurrect.py -q` green.

**Commit:** `feat(crash-recovery): tmux-resurrect snapshot parser (resurrect.py)`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Tight window + resurrect corroboration in correlate

**Verifies:** crash-detection.AC6.1, crash-detection.AC6.2, crash-detection.AC6.3

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/correlate.py`
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_correlate.py` (unit)

**Implementation:**
1. **Tight window.** Add `_TIGHT_WINDOW_SECONDS = 120`. In the mtime branch, a JSONL is a candidate when its `mtime >= started` AND its forward-scan first-entry-ts ∈ `[started - _CLOCK_SKEW_GRACE_SECONDS, started + _TIGHT_WINDOW_SECONDS]` (was: lower bound only). This excludes same-cwd sessions that began well after the wrapper. (Resumed sessions, whose first-entry-ts predates `started`, are handled by Phase 2's `session_id`/`--resume` direct path, not here — so the lower bound is safe.)
2. **Corroboration param.** Add keyword `corroborated_cwds: frozenset[str] | None = None` to `correlate()`. When the tight window yields >1 candidate AND `corroborated_cwds` is provided: filter candidates to those whose own JSONL forward-scan `cwd` is in `corroborated_cwds`. If exactly one survives → `MTIME_MATCH` to it. Otherwise → `AMBIGUOUS` with the **full tight-window candidate tuple** (never the filtered subset — all-means-all). When `corroborated_cwds is None`, behaviour is tight-window-only (single → MTIME_MATCH; multiple → AMBIGUOUS).

Keep the `session_id`/`--resume` direct paths (Phase 2) ahead of all this.

**Testing (test_correlate.py):**
- AC6.1: two JSONLs in one encoded project dir, one with first-entry-ts within `_TIGHT_WINDOW_SECONDS` of `started` and one well after → only the in-window one is a candidate → `MTIME_MATCH`.
- AC6.2: two in-window candidates with **different** cwds (lossy-shared encoded dir), `corroborated_cwds={cwdA}` → resolves to candidate A (`MTIME_MATCH`).
- AC6.3: two in-window candidates, `corroborated_cwds` empty or matching both → `AMBIGUOUS` with both candidates listed; and with `corroborated_cwds=None` and two candidates → `AMBIGUOUS`.

**Verification:** `uv run pytest .../tests/test_correlate.py -q` green.

**Commit:** `feat(crash-recovery): tight-window + resurrect corroboration in correlate`
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (task 3) -->

<!-- START_TASK_3 -->
### Task 3: scan threads resurrect corroboration; CLI exposes the dir

**Verifies:** crash-detection.AC6.2 (scan integration)

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/scan.py` (`ScanContext`, `_walk_sessions`)
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py` (`scan`, `triage`, `regenerate`, `_build_scan_ctx_and_run`)
- Test: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_scan.py` (integration)

**Implementation:**
- `ScanContext`: add `resurrect_dir: Path` field. (Frozen dataclass — add the field.) Every `ScanContext(...)` construction must pass it: update the call sites in `__main__.py` (real default `~/.byobu-sessions`) and **every `ScanContext(...)` construction in `test_scan.py` directly** (`make_full_fixture` returns `(db_dir, run_dir, projects_root)` but does NOT build `ScanContext` — the tests do). Default the tests to a non-existent temp dir so corroboration is a no-op and existing tests are unaffected.
- `_walk_sessions`: once at entry, `snapshots = resurrect.load_snapshots(ctx.resurrect_dir)`. Per liveness in the mtime path, compute `corroborated = resurrect.corroborating_cwds(resurrect.snapshot_near(snapshots, liveness.started))` (empty frozenset when `snapshot_near` is `None`) and pass `corroborated_cwds=` into `correlate(...)`. Direct/session_id matches are unaffected.
- `__main__`: add `--resurrect-dir` option resolved via `_resolve(..., "CRASH_RECOVERY_RESURRECT_DIR", "~/.byobu-sessions")` to `scan`, `triage`, `regenerate`, and `_build_scan_ctx_and_run`; pass into `ScanContext`. No local-filesystem guard needed (read-only, optional).

**Testing (test_scan.py):**
- AC6.2 integration: a fixture with a marker, two same-window candidate JSONLs (different cwds via lossy dir), and a temp resurrect snapshot whose only star-pane path matches cwd A → after `run_scan`, the marker's session resolves to candidate A (not `borderline/ambiguous_match`). With no snapshot (empty resurrect dir) and two candidates → `borderline/ambiguous_match` (AC6.3 path), all candidates in `state_summary`.

**Verification:** `uv run pytest .../tests/test_scan.py -q` green; full `uv run pytest` green (AC9.1); bats green (AC9.2).

**Commit:** `feat(crash-recovery): scan corroborates backlog markers via tmux-resurrect`
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_B -->

## Phase 3 done when

- `resurrect.py` parses real-format snapshots, selects the snapshot near `started`, extracts pane paths/labels (AC6.4).
- Tight window resolves single in-window candidates to `MTIME_MATCH` (AC6.1).
- Resurrect corroboration resolves a multi-cwd candidate set to the single corroborated one (AC6.2); uncorroborated/ambiguous stays `borderline/ambiguous_match` with all candidates (AC6.3).
- Corroboration is a no-op when no snapshots exist (back-compat); full pytest + bats green (AC9).
