"""Classification-history audit readback.

Phase 6, Task 3. The ``classification_history`` table is appended to on every
``scan`` (Phase 4) whenever a session's classification or reason changes
(Phase 4 M4 dedup). ``fetch_history`` is the read side: given a UUID it
returns every recorded transition for that session in chronological order,
joined with ``scan_runs`` so the caller sees the wall-clock ``ts`` of each
scan alongside the recorded ``classifier_version``.

The function is a pure SELECT (no writes, no mutating PRAGMAs); concurrent
scans cannot disturb the result because Phase 4 writes through the
``with conn:`` transaction context. The CLI subcommand in
:mod:`crash_recovery.__main__` formats the result as a plain-text table.

``classifier_version`` lives on both ``scan_runs`` and ``classification_history``
(denormalised at write time so the re-classify-stale-rows query in Phase 4
avoids a join). This module surfaces the per-history-row version, not the
``scan_runs`` one, so each entry records "the rule table I was classified
under at the time", not "the rule table the scan ran under".
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from crash_recovery import db


@dataclass(frozen=True)
class HistoryEntry:
    """One row from ``classification_history`` joined with ``scan_runs.ts``.

    ``scan_id`` orders entries chronologically (autoincrement PK on
    ``scan_runs``); ``scan_ts`` is the wall-clock seconds-since-epoch the scan
    began. ``reason`` is nullable because not every classification carries
    one (the original Phase 1 schema permits NULL).
    """

    scan_id: int
    scan_ts: int
    classification: str
    reason: str | None
    classifier_version: int


def fetch_history(db_path: Path, uuid: str) -> tuple[HistoryEntry, ...]:
    """Return every ``classification_history`` row for ``uuid``, oldest first.

    JOIN ``scan_runs`` so each entry carries the originating scan's ``ts``.
    ``ORDER BY ch.scan_id ASC`` makes chronology load-bearing: callers (the
    CLI's table renderer, downstream audits) rely on the leftmost row being
    the oldest. An unknown UUID is not an error here — it surfaces as an
    empty tuple. The CLI layer is responsible for translating "empty
    history" into a non-zero exit so scripts can distinguish "you asked
    about a phantom UUID" from "history was fetched and was empty".
    """
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
