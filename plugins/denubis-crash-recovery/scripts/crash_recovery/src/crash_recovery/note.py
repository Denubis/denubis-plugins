"""User-note CRUD on the sessions table.

Phase 6, Task 1. The ``user_notes`` column becomes load-bearing in Phase 6
— it signals "I care about this row, don't lose it" and is honoured by
:func:`crash_recovery.scan_db._orphan_sweep` (Task 0) and Phase 6's
``prune`` (Task 4). This module exposes the two write paths the CLI calls.

Both helpers use ``UPDATE … WHERE uuid = ?`` and raise
:class:`UnknownSessionError` when ``rowcount == 0``. This is the AC4.5
fail-loud guard: a typo'd UUID never silently inserts a row, and it never
silently succeeds with no row touched. Treating zero-row UPDATEs as
success would mask data-entry mistakes that only surface later when the
user wonders why their note never appeared in the rendered file.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from crash_recovery import db


class UnknownSessionError(LookupError):
    """Raised when a note operation targets a UUID not in the sessions table.

    Subclasses :class:`LookupError` so callers that already catch the
    standard lookup hierarchy degrade gracefully, but the dedicated type
    keeps CLI error messages unambiguous.
    """


def set_note(db_path: Path, uuid: str, text: str) -> None:
    """Set or overwrite the ``user_notes`` column for ``uuid``.

    Existing notes are replaced (AC4.2). The ``with conn:`` context wraps
    the UPDATE in a transaction so a mid-call interrupt cannot leave the
    row half-written.
    """
    with closing(db.open_db(db_path)) as conn:
        with conn:
            cur = conn.execute(
                "UPDATE sessions SET user_notes = ? WHERE uuid = ?",
                (text, uuid),
            )
            if cur.rowcount == 0:
                raise UnknownSessionError(f"no session with uuid {uuid}")


def clear_note(db_path: Path, uuid: str) -> None:
    """Set ``user_notes = NULL`` for ``uuid`` (AC4.3).

    Symmetric with :func:`set_note`: both honour the rowcount guard so a
    typo'd UUID raises rather than silently no-ops.
    """
    with closing(db.open_db(db_path)) as conn:
        with conn:
            cur = conn.execute(
                "UPDATE sessions SET user_notes = NULL WHERE uuid = ?",
                (uuid,),
            )
            if cur.rowcount == 0:
                raise UnknownSessionError(f"no session with uuid {uuid}")
