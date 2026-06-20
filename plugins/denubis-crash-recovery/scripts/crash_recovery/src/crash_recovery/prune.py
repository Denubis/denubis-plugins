"""Safely-gated removal of concluded sessions.

Phase 6, Task 4. ``prune`` is the only DB writer in Phase 6 that can lose user
state, so the design splits the operation in two: :func:`survey` is a pure
SELECT (AC7.2 — read-only) that applies the four-condition guard and returns
the list of UUIDs that would be deleted, plus a count of "would-be candidates
excluded because they are at a stale ``classifier_version``" so the CLI can
surface the AC7.7 warning. :func:`delete_candidates` is the only function that
mutates rows; it takes the survey's UUIDs verbatim and runs a single
``DELETE FROM sessions WHERE uuid IN (...)``.

Four-condition guard (all must hold for a row to be a candidate):

1. ``classification = 'concluded'`` — only concluded sessions are eligible.
2. ``user_notes IS NULL`` — AC7.5: an annotated row is preserved.
3. ``jsonl_path`` does not exist on disk — AC7.6: filesystem-presence guard.
4. ``classifier_version = CLASSIFIER_VERSION`` — AC7.7: the row's
   classification must reflect the current rule table; rows at an older
   version are excluded until ``scan`` refreshes them.

The ``DELETE FROM sessions`` cascades to the matching ``classification_history``
rows via Phase 1's ``FOREIGN KEY (uuid) REFERENCES sessions(uuid) ON DELETE
CASCADE``; :func:`crash_recovery.db.open_db` sets ``PRAGMA foreign_keys = ON``
so the cascade fires inside the same transaction. There is no separate
``DELETE FROM classification_history``; ``history <uuid>`` for a pruned UUID
naturally returns zero rows.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from crash_recovery import db
from crash_recovery.classify import CLASSIFIER_VERSION


@dataclass(frozen=True)
class Candidate:
    """One sessions row eligible for prune.

    Carries the minimum identifying fields the CLI needs to print a
    candidate line. ``last_scanned`` is included so the dry-run output gives
    the user a sense of "how stale is this row" without a second query.
    """

    uuid: str
    cwd: str
    last_scanned: int


@dataclass(frozen=True)
class PruneSurvey:
    """Result of a read-only :func:`survey`.

    ``candidates`` is the tuple of rows the four-condition guard cleared;
    ``stale_version_concluded_rows`` is the count of would-be candidates
    (concluded, no note, JSONL gone) that were excluded only because their
    ``classifier_version`` is below :data:`CLASSIFIER_VERSION`. The CLI uses
    the latter to print the AC7.7 warning telling the user to re-run ``scan``.
    """

    candidates: tuple[Candidate, ...]
    stale_version_concluded_rows: int


def survey(db_path: Path) -> PruneSurvey:
    """Read-only assessment of which sessions are prune candidates.

    AC7.2 invariant: this function MUST NOT mutate the DB. Only
    ``conn.execute("SELECT ...").fetchall()`` is permitted here. The opened
    connection is closed via :class:`contextlib.closing`; no transaction is
    opened and no UPDATE/DELETE/INSERT is issued.

    Applies the four-condition guard described in the module docstring. Rows
    that fail AC7.7 (stale ``classifier_version``) are NOT candidates, but
    if they would otherwise qualify (concluded + no note + JSONL gone) they
    are counted into ``stale_version_concluded_rows`` so the CLI can warn
    the user that ``scan`` would unlock them.
    """
    with closing(db.open_db(db_path)) as conn:
        all_concluded = conn.execute(
            "SELECT uuid, cwd, last_scanned, jsonl_path, user_notes,"
            " classifier_version "
            "FROM sessions WHERE classification = 'concluded'"
        ).fetchall()
    candidates: list[Candidate] = []
    stale_count = 0
    for uuid, cwd, last_scanned, jsonl_path, user_notes, cv in all_concluded:
        if cv != CLASSIFIER_VERSION:
            # AC7.7: prune does not touch rows whose classification was
            # computed under an older rule table. Count rows that would
            # otherwise qualify (no note, JSONL gone) so the CLI can warn.
            if user_notes is None and (
                jsonl_path is None or not Path(jsonl_path).exists()
            ):
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
    """Delete the supplied UUIDs from ``sessions``; return the rowcount.

    This is the ONLY function in :mod:`crash_recovery.prune` that writes.
    Callers must pass the UUIDs returned by :func:`survey` verbatim — the
    survey already applied the four-condition guard; re-applying it here
    would be redundant and (worse) would tempt callers into passing
    arbitrary UUIDs.

    The ``DELETE`` cascades to ``classification_history`` rows for the same
    UUIDs via Phase 1's ON DELETE CASCADE; ``PRAGMA foreign_keys = ON`` is
    set by :func:`crash_recovery.db.open_db` so the cascade fires inside the
    same transaction. An empty ``uuids`` argument returns 0 without opening
    the DB.
    """
    if not uuids:
        return 0
    with closing(db.open_db(db_path)) as conn, conn:
        placeholders = ",".join("?" * len(uuids))
        cur = conn.execute(
            f"DELETE FROM sessions WHERE uuid IN ({placeholders})",  # noqa: S608
            uuids,
        )
        return cur.rowcount
