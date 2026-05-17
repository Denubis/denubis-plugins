"""Pure DB-to-markdown render of the crash-recovery resume report.

The render is a pure function of the ``sessions`` table: same DB state
produces byte-identical markdown. Direct edits to ``~/llm-resume.md`` are
overwritten on every ``crash-recovery regenerate``.

Section assignment is a pure function of ``(classification, classification_reason)``
(see :func:`_section_for_row`). The "reduced confidence" inline tag is also
purely reason-derived (see :func:`_reduced_confidence_text`) — this resolves
the design's backward-compatibility wording ("Liveness presence/absence is
recorded in sessions as a boolean flag") by deriving the boolean from the
reason prefix rather than adding a column. The three frozensets
(:data:`LIVENESS_REASONS`, :data:`NO_LIVENESS_REASONS`,
:data:`JSONL_ONLY_REASONS`) MUST be disjoint and exhaustively cover every
reason emitted by Phase 2's ``RULES`` plus Phase 4's ``ambiguous_match``
and ``unmatched`` review-queue routes; Phase 5 Task 6 asserts the partition.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Reason-prefix constants (partition of every reason the classifier emits).
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Section model.
# ---------------------------------------------------------------------------


class SectionKey(StrEnum):
    """Six fixed section identifiers; order is defined by :data:`SECTIONS`."""

    CURRENTLY_UNFINISHED = "currently_unfinished"
    IDLE_LIVE_KILLED = "idle_live_killed"
    AMBIGUOUS_CORRELATION = "ambiguous_correlation"
    NEEDS_INVESTIGATION = "needs_investigation"
    RECENTLY_CONCLUDED = "recently_concluded"
    IRRECOVERABLE = "irrecoverable"


@dataclass(frozen=True)
class Section:
    """Metadata for one rendered section."""

    key: SectionKey
    header: str  # e.g., "## Currently unfinished"
    empty_message: str  # rendered as the section body when no rows match


SECTIONS: Final[tuple[Section, ...]] = (
    Section(
        key=SectionKey.CURRENTLY_UNFINISHED,
        header="## Currently unfinished",
        empty_message="_No sessions classified as currently unfinished._",
    ),
    Section(
        key=SectionKey.IDLE_LIVE_KILLED,
        header="## Idle-live killed",
        empty_message="_No sessions classified as idle-live killed._",
    ),
    Section(
        key=SectionKey.AMBIGUOUS_CORRELATION,
        header="## Ambiguous correlation",
        empty_message="_No sessions with ambiguous correlation._",
    ),
    Section(
        key=SectionKey.NEEDS_INVESTIGATION,
        header="## Needs investigation",
        empty_message="_No sessions needing investigation._",
    ),
    Section(
        key=SectionKey.RECENTLY_CONCLUDED,
        header="## Recently concluded",
        empty_message="_No sessions classified as concluded._",
    ),
    Section(
        key=SectionKey.IRRECOVERABLE,
        header="## Irrecoverable",
        empty_message="_No irrecoverable sessions._",
    ),
)


# ---------------------------------------------------------------------------
# Pure helpers (section assignment, reduced-confidence text).
# ---------------------------------------------------------------------------


def _section_for_row(classification: str, reason: str) -> SectionKey:
    """Map a ``(classification, reason)`` pair to its section.

    Pure function — no DB access, no side effects. Mirrors the routing
    documented in the Phase 5 plan.
    """
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
    # Defensive default for any future classification value.
    return SectionKey.NEEDS_INVESTIGATION


def _reduced_confidence_text(reason: str) -> str | None:
    """Return the reduced-confidence warning string for ``reason`` or ``None``.

    ``ambiguous_match`` is intentionally excluded — the ambiguity itself is
    surfaced via its dedicated section. ``unmatched`` gets its own distinct
    message because it routes through Phase 2's deliberate review-queue
    fallback (the rule table didn't speak to this combination).
    """
    if reason == "unmatched":
        return "Something fucky — let's go look"
    if reason in NO_LIVENESS_REASONS:
        return "no liveness file recorded (pre-installation session or wrapper bypass)"
    if reason in JSONL_ONLY_REASONS and reason != "ambiguous_match":
        return "session data is incomplete or corrupted"
    return None
