"""Tests for ``crash_recovery.note`` and the ``crash-recovery note`` CLI.

Covers Phase 6 acceptance criteria for annotation CRUD:

* AC4.1 — ``note <uuid> "x"`` followed by ``regenerate`` surfaces "x" under
  the matching UUID.
* AC4.2 — ``note <uuid> "y"`` on a row with an existing note overwrites the
  prior note.
* AC4.3 — ``note <uuid> --clear`` removes the note; subsequent renders omit
  the Notes line for that UUID.
* AC4.5 — ``note`` against an unknown UUID exits non-zero with a clear error
  and does NOT silently insert a row.

The module-level tests exercise :mod:`crash_recovery.note` directly; the CLI
tests shell out via :func:`subprocess.run` so they cover argv parsing, the
``--clear`` mutual-exclusion guard, and the AC4.5 stderr text on a real
process boundary.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from crash_recovery import db as db_mod
from crash_recovery import note as note_mod
from crash_recovery import render as render_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_db(tmp_path: Path) -> Path:
    """Create a fresh crash-recovery DB at ``tmp_path/note-test.db``."""
    db_path = tmp_path / "note-test.db"
    db_mod.init(db_path)
    return db_path


def _seed_concluded_session(db_path: Path, uuid: str, *, user_notes: str | None = None) -> None:
    """Insert one ``concluded`` sessions row.

    Mirrors the column set documented in :class:`crash_recovery.db.SESSIONS_DDL`
    so the inserted row passes the CLASSIFICATION CHECK constraint and is
    visible to :func:`crash_recovery.render.render`.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO sessions (
                uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                classification, classification_reason, classifier_version,
                state_summary, first_seen, last_scanned, user_notes
            ) VALUES (?, '/p', '/c', '/no/such.jsonl', NULL, NULL,
                      'concluded', 'no_liveness_clean_end_turn', 1,
                      'end_turn observed', 1, 1, ?)
            """,
            (uuid, user_notes),
        )
        conn.commit()
    finally:
        conn.close()


def _read_note(db_path: Path, uuid: str) -> str | None:
    """Return the ``user_notes`` cell for ``uuid`` (or None if absent)."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT user_notes FROM sessions WHERE uuid = ?", (uuid,)
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else row[0]


def _session_count(db_path: Path) -> int:
    """Return the count of rows in ``sessions``."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# AC4.1 — set, then regenerate surfaces the note
# ---------------------------------------------------------------------------


def test_note_set_then_regenerate_surfaces_text(tmp_path: Path) -> None:
    """AC4.1: setting a note and rendering surfaces the text under the UUID.

    Skips the wrapping CLI to exercise the contract at the module boundary
    (``set_note`` → DB → ``render``). The CLI is exercised separately by the
    subprocess tests below.
    """
    db_path = _init_db(tmp_path)
    uuid = "11111111-1111-1111-1111-111111111111"
    _seed_concluded_session(db_path, uuid)

    note_mod.set_note(db_path, uuid, "remember to re-run after lunch")

    rendered = render_mod.render(db_path)
    assert "remember to re-run after lunch" in rendered
    # Section header for concluded rows surrounds the entry.
    assert uuid[:8] in rendered


# ---------------------------------------------------------------------------
# AC4.2 — overwrite
# ---------------------------------------------------------------------------


def test_note_overwrites_existing(tmp_path: Path) -> None:
    """AC4.2: a second ``set_note`` replaces the first note's text in render."""
    db_path = _init_db(tmp_path)
    uuid = "22222222-2222-2222-2222-222222222222"
    _seed_concluded_session(db_path, uuid)

    note_mod.set_note(db_path, uuid, "first note")
    note_mod.set_note(db_path, uuid, "second note overrides")

    rendered = render_mod.render(db_path)
    assert "first note" not in rendered
    assert "second note overrides" in rendered


# ---------------------------------------------------------------------------
# AC4.3 — clear removes the Notes line
# ---------------------------------------------------------------------------


def test_note_clear_removes_note(tmp_path: Path) -> None:
    """AC4.3: ``clear_note`` removes the user_notes cell; render omits the line.

    The render template emits ``- Notes: <text>`` only when ``user_notes`` is
    not NULL, so the absence of "Notes:" anywhere in the rendered file is the
    structural guarantee here.
    """
    db_path = _init_db(tmp_path)
    uuid = "33333333-3333-3333-3333-333333333333"
    _seed_concluded_session(db_path, uuid)

    note_mod.set_note(db_path, uuid, "scratch this")
    note_mod.clear_note(db_path, uuid)

    rendered = render_mod.render(db_path)
    assert "scratch this" not in rendered
    # The fixture has exactly one row; if "Notes:" appears anywhere, it must
    # be for that row.
    assert "Notes:" not in rendered
    # The DB column itself is NULL.
    assert _read_note(db_path, uuid) is None


# ---------------------------------------------------------------------------
# AC4.5 — unknown UUID is a fail-loud guard, never a silent insert
# ---------------------------------------------------------------------------


def test_note_unknown_uuid_raises_and_does_not_insert(tmp_path: Path) -> None:
    """AC4.5 (module-level): ``set_note`` on a missing UUID raises and inserts nothing.

    This is the structural guarantee that the implementation uses
    ``UPDATE ... WHERE uuid = ?`` + ``rowcount == 0`` rather than an
    ``INSERT OR REPLACE``/``UPSERT`` pattern. The DB starts and stays empty.
    """
    db_path = _init_db(tmp_path)
    assert _session_count(db_path) == 0

    with pytest.raises(note_mod.UnknownSessionError, match="no-such-uuid"):
        note_mod.set_note(db_path, "no-such-uuid", "should not land")

    assert _session_count(db_path) == 0


def test_clear_note_unknown_uuid_raises(tmp_path: Path) -> None:
    """``clear_note`` on a missing UUID raises the same fail-loud error.

    Pins symmetry between ``set_note`` and ``clear_note`` so a future
    refactor cannot silently drop the rowcount guard on the clear path.
    """
    db_path = _init_db(tmp_path)
    with pytest.raises(note_mod.UnknownSessionError, match="no-such-uuid"):
        note_mod.clear_note(db_path, "no-such-uuid")


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------


def _run_cli(*args: str, db_path: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python -m crash_recovery note <args>`` with the test DB injected."""
    env = {**os.environ, "CRASH_RECOVERY_DB": str(db_path)}
    return subprocess.run(
        [sys.executable, "-m", "crash_recovery", "note", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_note_cli_unknown_uuid_exits_nonzero_with_error_text(tmp_path: Path) -> None:
    """AC4.5 (CLI): unknown UUID → exit code != 0 and "no session with uuid" in stderr."""
    db_path = _init_db(tmp_path)
    result = _run_cli("no-such-uuid", "hello", db_path=db_path)
    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "no session with uuid" in result.stderr
    # Defence-in-depth: no row landed.
    assert _session_count(db_path) == 0


def test_note_cli_clear_without_text(tmp_path: Path) -> None:
    """``note <uuid> --clear`` exits 0 and NULLs the row's user_notes column."""
    db_path = _init_db(tmp_path)
    uuid = "55555555-5555-5555-5555-555555555555"
    _seed_concluded_session(db_path, uuid, user_notes="will be cleared")

    result = _run_cli(uuid, "--clear", db_path=db_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert _read_note(db_path, uuid) is None


def test_note_cli_clear_with_text_is_rejected(tmp_path: Path) -> None:
    """``note <uuid> "text" --clear`` exits non-zero (typer.BadParameter).

    Pins the mutual-exclusion guard so callers cannot ambiguously request
    "set this text" and "clear" in one invocation.
    """
    db_path = _init_db(tmp_path)
    uuid = "66666666-6666-6666-6666-666666666666"
    _seed_concluded_session(db_path, uuid, user_notes="untouched")

    result = _run_cli(uuid, "some text", "--clear", db_path=db_path)
    assert result.returncode != 0, (result.stdout, result.stderr)
    # And the row's note must not have been disturbed.
    assert _read_note(db_path, uuid) == "untouched"


def test_note_cli_set_writes_text(tmp_path: Path) -> None:
    """``note <uuid> "text"`` exits 0 and writes the text into the DB row.

    Round-trips the happy-path CLI invocation so the subcommand wiring is
    pinned independently of the module-level :func:`set_note` tests above.
    """
    db_path = _init_db(tmp_path)
    uuid = "77777777-7777-7777-7777-777777777777"
    _seed_concluded_session(db_path, uuid)

    result = _run_cli(uuid, "from cli", db_path=db_path)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert _read_note(db_path, uuid) == "from cli"
