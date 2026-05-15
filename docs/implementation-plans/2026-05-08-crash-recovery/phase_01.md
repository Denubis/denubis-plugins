# denubis-crash-recovery Implementation Plan — Phase 1: Plugin scaffold and database schema

**Goal:** Stand up the `denubis-crash-recovery` plugin directory, the uv-managed Python package, the SQLite schema, and the `crash-recovery init` subcommand.

**Architecture:** New plugin under `plugins/denubis-crash-recovery/` follows the `workflow_statusline` precedent: a uv-managed Python package at `scripts/crash_recovery/` with `src/` layout, `tests/` sibling, `[project.scripts]` entry point. SQLite database at `~/.claude/crash-recovery.db` (overridable via `CRASH_RECOVERY_DB`); schema seeded by `crash-recovery init`; idempotent by SQLite's `CREATE … IF NOT EXISTS` semantics; WAL journal mode set persistently in init.

**Tech Stack:** Python 3.12+, uv, typer (>=0.12), sqlite3 (stdlib), pytest.

**Scope:** Phase 1 of 8 from `docs/design-plans/2026-05-08-crash-recovery.md`.

**Codebase verified:** 2026-05-12 (Phase 1B investigator report).

## Per-plugin test invocation convention

The root `pyproject.toml` keeps `testpaths = ["tests"]`. Each uv-managed plugin package owns its own test suite and is invoked at its own project root, matching the precedent set by `plugins/denubis-plan-and-execute/scripts/workflow_statusline/`. Run tests for this plugin with:

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest -q
```

Why not a uv workspace or wider `testpaths`: the plugin install model copies each plugin directory standalone — users invoke the CLI via `uv run --project <plugin-path>/scripts/<pkg>`, which requires a self-contained `pyproject.toml` per plugin. A wider repo-root `testpaths` would attempt to collect plugin tests under the root environment, which does not have the per-plugin dependencies synced. Empirical check: running the workflow_statusline tests from the repo root fails on import; the existing per-plugin convention is what works.

**Phase Type:** infrastructure

---

## Acceptance Criteria Coverage

This phase implements and tests:

### crash-recovery.AC1: Plugin installs and registers
- **crash-recovery.AC1.1 Success:** `claude plugin install denubis-crash-recovery@brian-ed3d-plugins` exits 0
- **crash-recovery.AC1.3 Success:** `plugin.json` and the `marketplace.json` entry both have all required fields (name, version, source, author, license) and identical version strings
- **crash-recovery.AC1.4 Failure:** Install with a malformed `plugin.json` exits non-zero with a parseable error message (no silent failure)

### crash-recovery.AC2: CLI exposes the documented surface
- **crash-recovery.AC2.3 Success:** `crash-recovery init` creates `~/.claude/crash-recovery.db` (or path from `CRASH_RECOVERY_DB`) with the schema documented in Architecture
- **crash-recovery.AC2.4 Success:** Re-running `init` against an existing DB is a no-op (idempotent — verified by row-count and schema-hash check)
- **crash-recovery.AC2.5 Failure:** Unknown subcommand exits non-zero with an error message pointing to `--help`

> AC1.2 (plugin appears in `/plugin` listing after install) is verified in Phase 7 alongside the triage skill registration. AC2.1 and AC2.2 (every documented subcommand listed in `--help`) are seeded by Phase 1's typer scaffold and completed incrementally as Phases 4–6 add subcommands.

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Plugin directory + LICENSE + README + plugin.json

**Files:**
- Create: `plugins/denubis-crash-recovery/LICENSE`
- Create: `plugins/denubis-crash-recovery/README.md`
- Create: `plugins/denubis-crash-recovery/.claude-plugin/plugin.json`

**Step 1: Create LICENSE**

Copy the CC-BY-SA-4.0 license text used by `plugins/denubis-plan-and-execute/LICENSE` byte-for-byte. The exact text is the canonical Creative Commons CC-BY-SA-4.0 deed; matching the sibling guarantees marketplace tooling parses both consistently.

**Step 2: Create README.md skeleton**

The README must document:
- One-paragraph overview matching the design plan's Summary (regenerable, deterministic triage of Claude Code sessions).
- Installation: `claude plugin install denubis-crash-recovery@brian-ed3d-plugins`.
- Dependency note: requires `denubis-plan-and-execute ≥ <wrapper-patch-version>` (the version will be filled in by Phase 8; leave a `TBD-PHASE-8` placeholder for now and add a short note that Phase 8 wires the wrapper patch).
- Usage: a single example invocation of `crash-recovery triage` (the user-facing entry point), with a one-line description.
- A "this is a v0.1.0 release; the wrapper patch lands in Phase 8" caveat.

Keep the README under 80 lines. No emojis.

**Step 3: Create plugin.json**

```json
{
    "name": "denubis-crash-recovery",
    "description": "Identify and resume Claude Code sessions that ended abnormally; classifies live/crashed/concluded sessions deterministically and renders ~/llm-resume.md.",
    "version": "0.1.0",
    "author": {
        "name": "Brian Ballsun-Stanton",
        "github": "denubis"
    },
    "license": "CC-BY-SA-4.0",
    "keywords": [
        "claude-code",
        "session-recovery",
        "triage",
        "sqlite",
        "resume"
    ]
}
```

**Step 4: Verify operationally**

```bash
test -f plugins/denubis-crash-recovery/LICENSE
test -f plugins/denubis-crash-recovery/README.md
python -c "import json; json.load(open('plugins/denubis-crash-recovery/.claude-plugin/plugin.json'))"
```
All three must succeed.

**Step 5: Commit**

```bash
git add plugins/denubis-crash-recovery/LICENSE plugins/denubis-crash-recovery/README.md plugins/denubis-crash-recovery/.claude-plugin/plugin.json
git commit -m "feat(crash-recovery): scaffold plugin directory with LICENSE, README, plugin.json"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Python package skeleton

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/pyproject.toml`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__init__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/__init__.py`
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/conftest.py`

**Step 1: pyproject.toml (complete contents)**

```toml
[project]
name = "crash-recovery"
version = "0.1.0"
description = "Deterministic triage of Claude Code sessions"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.12",
]

[project.scripts]
crash-recovery = "crash_recovery.__main__:main"

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/crash_recovery"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: `src/crash_recovery/__init__.py` (complete contents)**

```python
"""denubis-crash-recovery: deterministic triage of Claude Code sessions."""

__version__ = "0.1.0"
```

**Step 3: `src/crash_recovery/__main__.py` (typer App skeleton, no subcommands yet)**

The `__main__` module exposes `main()` as the entry point declared in `[project.scripts]`. It must:
- Construct a `typer.Typer()` app with `no_args_is_help=True` so `crash-recovery` (no args) prints help and exits 0.
- Export `main = app` (or wrap with `def main(): app()`).
- NOT define any subcommands yet — Task 5 wires `init`, later phases wire the remaining eight.
- Be importable from tests without invoking the CLI (i.e., `app` is module-level).

Verification: `uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery --help` exits 0 and prints typer's default help (no subcommands listed yet — that's expected at this task's boundary).

**Step 4: `tests/__init__.py`** — empty file, exists so pytest treats `tests/` as a package.

**Step 5: `tests/conftest.py`**

Minimal conftest:

```python
"""Shared pytest fixtures for crash_recovery tests."""

from __future__ import annotations

import sqlite3
import typing as _t
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """A throw-away DB path inside pytest's tmp_path."""
    return tmp_path / "crash-recovery.db"
```

**Step 6: Verify operationally**

```bash
uv sync --project plugins/denubis-crash-recovery/scripts/crash_recovery
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery --help
```
Both must succeed; `--help` exits 0.

**Step 7: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/
git commit -m "feat(crash-recovery): add Python package skeleton with typer entry point"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Marketplace registration + CHANGELOG

**Files:**
- Modify: `.claude-plugin/marketplace.json` (add new entry)
- Modify: `CHANGELOG.md` (repo root — add denubis-crash-recovery 0.1.0 section)

**Step 1: Add marketplace.json entry**

Locate the `plugins` array in `.claude-plugin/marketplace.json` and add a new entry. Match the existing schema (use `denubis-bibliography`'s entry as the structural template — it is the most recent and contains all standard fields). The new entry:

```json
{
    "name": "denubis-crash-recovery",
    "description": "Identify and resume Claude Code sessions that ended abnormally; classifies live/crashed/concluded sessions deterministically and renders ~/llm-resume.md.",
    "version": "0.1.0",
    "source": "./plugins/denubis-crash-recovery",
    "author": {
        "name": "Brian Ballsun-Stanton",
        "github": "denubis"
    },
    "license": "CC-BY-SA-4.0",
    "keywords": [
        "claude-code",
        "session-recovery",
        "triage",
        "sqlite",
        "resume"
    ]
}
```

Insertion point: alphabetically after `denubis-bibliography`. Preserve existing JSON formatting (4-space indent, trailing newline).

**Verifies AC1.3:** `name`, `version`, `source`, `author`, `license` present and version string matches `plugin.json` exactly (`0.1.0`).

**Step 2: Add CHANGELOG entry**

Insert at the top of `CHANGELOG.md` (after the `# Changelog` heading, before the existing `## [denubis-bibliography] 0.1.0` entry):

```markdown
## [denubis-crash-recovery] 0.1.0

New plugin. Identify and resume Claude Code sessions that ended abnormally; classifies live/crashed/concluded sessions deterministically and renders `~/llm-resume.md`. This release ships the plugin scaffold, SQLite schema, and `crash-recovery init` subcommand. Subsequent phases land the classification rule table, scan/render/note/prune subcommands, the triage skill, and the wrapper patch in `denubis-plan-and-execute`.

**New:**
- `plugins/denubis-crash-recovery/` plugin scaffold (plugin.json, LICENSE, README).
- `crash-recovery` CLI (typer-based) with `init` subcommand creating `~/.claude/crash-recovery.db` (overridable via `CRASH_RECOVERY_DB`).
- SQLite schema for `sessions`, `scan_runs`, `classification_history` tables; WAL journal mode set persistently in init.
```

**Step 3: Verify operationally**

```bash
python -c "import json; m = json.load(open('.claude-plugin/marketplace.json')); names = [p['name'] for p in m['plugins']]; assert 'denubis-crash-recovery' in names, names"
grep -q '^## \[denubis-crash-recovery\] 0.1.0' CHANGELOG.md
```

**Step 4: Verify version-sync invariant (AC1.3)**

```bash
python -c "
import json
plugin_version = json.load(open('plugins/denubis-crash-recovery/.claude-plugin/plugin.json'))['version']
marketplace = json.load(open('.claude-plugin/marketplace.json'))
entry = next(p for p in marketplace['plugins'] if p['name'] == 'denubis-crash-recovery')
assert plugin_version == entry['version'], (plugin_version, entry['version'])
print(f'OK: version {plugin_version} matches across plugin.json and marketplace.json')
"
```

**Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "feat(crash-recovery): register denubis-crash-recovery 0.1.0 in marketplace"
```
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

---

<!-- START_SUBCOMPONENT_B (tasks 4-6) -->

<!-- START_TASK_4 -->
### Task 4: Database schema constants and connection helper

**Verifies:** none directly (consumed by Tasks 5 and 6; tested transitively via AC2.3, AC2.4).

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/db.py`

**Implementation:**

`db.py` exposes:

1. **Module-level constants** for the schema (DDL strings) — one per table, plus an `ALL_DDL` tuple for the init code to iterate. Match the design's Data Model verbatim:

   ```python
   SESSIONS_DDL = """
   CREATE TABLE IF NOT EXISTS sessions (
       uuid                  TEXT PRIMARY KEY,
       project_path          TEXT NOT NULL,
       cwd                   TEXT NOT NULL,
       jsonl_path            TEXT,
       jsonl_mtime           INTEGER,
       jsonl_last_ts         INTEGER,
       classification        TEXT NOT NULL,
       classification_reason TEXT,
       classifier_version    INTEGER NOT NULL,
       state_summary         TEXT,
       first_seen            INTEGER NOT NULL,
       last_scanned          INTEGER NOT NULL,
       user_notes            TEXT
   )
   """

   SCAN_RUNS_DDL = """
   CREATE TABLE IF NOT EXISTS scan_runs (
       id                    INTEGER PRIMARY KEY,
       ts                    INTEGER NOT NULL,
       live_pids             TEXT,
       sessions_scanned      INTEGER,
       classifier_version    INTEGER NOT NULL
   )
   """

   CLASSIFICATION_HISTORY_DDL = """
   CREATE TABLE IF NOT EXISTS classification_history (
       uuid                  TEXT NOT NULL,
       scan_id               INTEGER NOT NULL,
       classification        TEXT NOT NULL,
       reason                TEXT,
       classifier_version    INTEGER NOT NULL,
       PRIMARY KEY (uuid, scan_id),
       FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE CASCADE
   )
   """

   ALL_DDL = (SESSIONS_DDL, SCAN_RUNS_DDL, CLASSIFICATION_HISTORY_DDL)
   ```

   Match column names and types exactly — Phases 4 and 5 will query these columns by name.

2. **`default_db_path() -> Path`** — returns `Path(os.environ.get("CRASH_RECOVERY_DB", "~/.claude/crash-recovery.db")).expanduser()`.

3. **`init(path: Path) -> None`** — creates the parent directory if missing, opens a sqlite3 connection at `path`, applies each DDL in `ALL_DDL`, executes `PRAGMA journal_mode = WAL` (do NOT wrap in a transaction — WAL mode-change must run outside of a transaction), executes `PRAGMA foreign_keys = ON`, commits, closes. Idempotent: re-running on an existing DB is a no-op because every CREATE is guarded by IF NOT EXISTS.

4. **`open_db(path: Path) -> sqlite3.Connection`** — opens a connection, asserts `PRAGMA journal_mode` returns `'wal'`, raises `RuntimeError("crash-recovery DB at {path} is not in WAL mode; re-run `crash-recovery init`")` on mismatch, enables `PRAGMA foreign_keys = ON`, returns the connection. Used by all subsequent phases that read or write the DB.

5. **`schema_hash(conn: sqlite3.Connection) -> str`** — returns SHA-256 (hex) of the concatenated `(name, sql)` rows of `sqlite_master` ordered by name. Used by tests for AC2.4 idempotency verification. Pure read-only helper.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery python -c "
from crash_recovery import db
import tempfile, pathlib
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / 'test.db'
    db.init(p)
    conn = db.open_db(p)
    rows = conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name').fetchall()
    assert [r[0] for r in rows] == ['classification_history', 'scan_runs', 'sessions'], rows
    print('OK')
"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/db.py
git commit -m "feat(crash-recovery): add db module with schema DDL, init, open_db, schema_hash"
```
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `crash-recovery init` subcommand

**Verifies:** crash-recovery.AC2.3 (init creates the documented schema), crash-recovery.AC2.4 (idempotency — verified by tests in Task 6).

**Files:**
- Modify: `plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py`

**Implementation:**

Add an `init` subcommand to the typer app already created in Task 2.

The subcommand must:
- Accept an optional `--db PATH` option that overrides the default DB path (which itself comes from `CRASH_RECOVERY_DB` env var, falling back to `~/.claude/crash-recovery.db`).
- Call `db.init(resolved_path)`.
- Print a one-line confirmation: `Initialised crash-recovery DB at {resolved_path}` to stdout.
- Exit 0 on success.
- On any exception, print `init failed: {exception}` to stderr and exit non-zero (let typer's default exception handling do this — i.e., raise; don't catch).

Wire-up pattern:

```python
import typer
from pathlib import Path
from crash_recovery import db

app = typer.Typer(no_args_is_help=True)


@app.command()
def init(
    db_path: Path = typer.Option(
        None,
        "--db",
        help="Path to crash-recovery SQLite DB (default: $CRASH_RECOVERY_DB or ~/.claude/crash-recovery.db).",
    ),
) -> None:
    """Initialise the crash-recovery SQLite database."""
    resolved = db_path if db_path is not None else db.default_db_path()
    db.init(resolved)
    typer.echo(f"Initialised crash-recovery DB at {resolved}")


def main() -> None:
    app()
```

**Unknown-subcommand behaviour (AC2.5):** typer's default behaviour is to exit non-zero and print a "No such command" message that references `--help`. No custom code needed; Task 6's test asserts this.

**Step: Verify operationally**

```bash
TMPDIR=$(mktemp -d)
CRASH_RECOVERY_DB="$TMPDIR/test.db" uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery init
test -f "$TMPDIR/test.db" && echo "OK: DB created"
rm -rf "$TMPDIR"
```

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/src/crash_recovery/__main__.py
git commit -m "feat(crash-recovery): add init subcommand to crash-recovery CLI"
```
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Tests for init, idempotency, and CLI surface

**Verifies:** crash-recovery.AC2.3, crash-recovery.AC2.4, crash-recovery.AC2.5, crash-recovery.AC1.4.

**Files:**
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_init.py` (unit + integration)
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_cli_help.py` (integration)
- Create: `plugins/denubis-crash-recovery/scripts/crash_recovery/tests/test_plugin_manifest.py` (unit — runs against the on-disk plugin.json / marketplace.json)

**Tests must verify each AC listed above:**

- **crash-recovery.AC2.3 (init creates schema):** `test_init_creates_documented_schema` — call `db.init(tmp_db_path)`, open the DB, query `sqlite_master` for tables named `sessions`, `scan_runs`, `classification_history`, assert all three present. Then for the `sessions` table specifically, query `PRAGMA table_info(sessions)` and assert every column from the design's Data Model is present with the documented type/NOT-NULL flag. Test type: unit (touches sqlite directly, no subprocess).

- **crash-recovery.AC2.4 (idempotency via row-count and schema-hash):** `test_init_is_idempotent` — call `db.init(tmp_db_path)`, capture `schema_hash(conn)` and row counts for all three tables (expected: 0 each); call `db.init(tmp_db_path)` a second time on the same path; capture hash and counts again; assert both unchanged. Test type: unit.

- **crash-recovery.AC2.5 (unknown subcommand exits non-zero with `--help` hint):** `test_unknown_subcommand_exits_nonzero` — invoke the CLI as a subprocess with `crash-recovery wibble`; assert exit code is non-zero and stderr contains the substring `--help` (typer's default error message includes this). Test type: integration (uses subprocess).

- **crash-recovery.AC1.4 (malformed plugin.json surfaces a parseable error):** `test_plugin_json_is_valid` — `json.load` the on-disk plugin.json; assert it has the required fields (`name`, `description`, `version`, `author`, `license`). This proves the plugin's manifest is well-formed; the failure case (malformed plugin.json caused by `claude plugin install` to exit non-zero) is owned by Claude Code itself and is asserted by the test that `json.load` would raise on our manifest if it were malformed — i.e., the well-formed-ness gate.

- **AC2.3 also verified at CLI layer:** `test_cli_init_writes_db_at_env_var_path` — invoke `crash-recovery init` as a subprocess with `CRASH_RECOVERY_DB=$TMPDIR/test.db`, assert the DB file exists at that path, open it, assert the documented tables exist. Test type: integration (subprocess + env var).

- **CLI help surface:** `test_help_exits_zero` — invoke `crash-recovery --help` as a subprocess; assert exit code 0. (AC2.1 / AC2.2's full subcommand listing assertion is parameterised over an `EXPECTED_SUBCOMMANDS` constant; Phase 1 seeds the constant with `["init"]` and later phases append.) Test type: integration.

**Test patterns to follow:**
- Use `pytest`'s `tmp_path` for filesystem-touching tests.
- Use `subprocess.run([sys.executable, "-m", "crash_recovery", ...])` for CLI-as-subprocess tests so the test uses the same interpreter and the package is importable.
- Do NOT mock `sqlite3` — touch the real SQLite engine. The tests are fast and correctness depends on actual SQLite behaviour.

**Step: Verify operationally**

```bash
uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest -q
```

Expected: all tests pass. (This is the per-plugin invocation convention documented at the top of this phase; the repo-root `uv run pytest -q` still runs only `tests/` and is unaffected.)

**Step: Confirm repo-root pytest is unaffected**

```bash
uv run pytest -q
```

Expected: pre-existing 457 tests still pass; count does NOT increase (per-plugin tests live under their own project and are not collected by the repo-root invocation).

**Step: Commit**

```bash
git add plugins/denubis-crash-recovery/scripts/crash_recovery/tests/
git commit -m "test(crash-recovery): cover init schema, idempotency, CLI surface, manifest"
```
<!-- END_TASK_6 -->

<!-- END_SUBCOMPONENT_B -->

---

## Phase 1 Done When

- `uv sync --project plugins/denubis-crash-recovery/scripts/crash_recovery` succeeds.
- `uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery crash-recovery --help` exits 0 and lists `init`.
- `CRASH_RECOVERY_DB=/tmp/cr.db crash-recovery init` creates the DB with the three documented tables; re-running is a no-op.
- `uv run --project plugins/denubis-crash-recovery/scripts/crash_recovery pytest -q` passes for the new package's tests.
- `uv run pytest -q` at the repo root still passes (pre-existing 457 tests; root invocation is unaffected by this phase).
- `plugin.json` and `marketplace.json` agree on version `0.1.0`; CHANGELOG carries the `[denubis-crash-recovery] 0.1.0` entry.

## Outstanding for later phases

- AC1.2 (`/plugin` listing) — Phase 7 (skill registration + post-install verification).
- AC2.1 / AC2.2 (full subcommand surface) — Phases 4–6 add remaining subcommands; the test's `EXPECTED_SUBCOMMANDS` list grows phase-by-phase.
- Wrapper patch + version coordination — Phase 8.
