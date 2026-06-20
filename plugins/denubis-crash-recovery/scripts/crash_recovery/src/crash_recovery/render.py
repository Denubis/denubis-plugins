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

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Reason-prefix constants (partition of every reason the classifier emits).
# ---------------------------------------------------------------------------
#
# These three frozensets are a PARTITION: every reason belongs to exactly one,
# they are pairwise disjoint, and together they cover every reason (asserted by
# ``test_reason_prefix_partition_is_exhaustive``). Membership encodes "did a
# liveness file exist for this reason?", which feeds the backward-compatibility
# boolean — NOT whether a reduced-confidence note is shown. The note is decided
# independently by :func:`_reduced_confidence_text`. Most ``LIVENESS_REASONS``
# get no note, but ``liveness_dead_pid_concluded_tail`` is the one exception that
# does (its calm "concluded, then killed" message). Do not read membership here
# as "silent": consult :func:`_reduced_confidence_text` for that.

LIVENESS_REASONS: Final[frozenset[str]] = frozenset(
    {
        "live_pid_present_boot_current",
        "liveness_boot_id_mismatch",
        "liveness_dead_pid_tool_use_no_result",
        "liveness_dead_pid_ask_question_no_reply",
        "liveness_dead_pid_agent_dispatch_no_result",
        "liveness_dead_pid_unknown_tail",
        "liveness_dead_pid_concluded_tail",
    }
)
NO_LIVENESS_REASONS: Final[frozenset[str]] = frozenset(
    {
        "no_liveness_clean_end_turn",
        "no_liveness_dangling_tool_use",
        "no_liveness_dangling_ask_question",
        "no_liveness_dangling_agent_dispatch",
    }
)
JSONL_ONLY_REASONS: Final[frozenset[str]] = frozenset(
    {
        "malformed_tail",
        "empty_file",
        "missing_jsonl_on_disk",
        "unknown_tail_kind",
        "ambiguous_match",
        "unmatched",
    }
)


# ---------------------------------------------------------------------------
# Section model.
# ---------------------------------------------------------------------------


class SectionKey(StrEnum):
    """Six fixed section identifiers; order is defined by :data:`SECTIONS`."""

    CURRENTLY_UNFINISHED = "currently_unfinished"
    PROBABLE_CRASH_VICTIMS = "probable_crash_victims"
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
        key=SectionKey.PROBABLE_CRASH_VICTIMS,
        header="## Probable system-crash victims",
        empty_message="_No sessions classified as probable crash victims._",
    ),
    Section(
        key=SectionKey.CURRENTLY_UNFINISHED,
        header="## Currently unfinished",
        empty_message="_No sessions classified as currently unfinished._",
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
# Lean-mode (triage terminal) collapse policy.
# ---------------------------------------------------------------------------
#
# ``render(show_all=True)`` — the default, and what writes ``~/llm-resume.md`` —
# is the full all-means-all roster. The triage *terminal read* uses
# ``show_all=False`` to collapse the non-actionable bulk to counts so "what
# crashed" is a glance, not a 9k-line ledger dump. Bulk = the two terminal
# sections (concluded, irrecoverable) plus "unrecognised endings" (a borderline
# row whose tail shape carried no crash signal). Everything else stays full:
# crash victims, currently-unfinished, ambiguous, the dangling-tail /
# concluded-then-killed investigation rows, and uncorrelated markers.

_LEAN_COLLAPSED_SECTIONS: Final[frozenset[SectionKey]] = frozenset(
    {
        SectionKey.RECENTLY_CONCLUDED,
        SectionKey.IRRECOVERABLE,
    }
)
_LEAN_BULK_REASONS: Final[frozenset[str]] = frozenset({"unknown_tail_kind"})
_LEAN_SECTION_LABEL: Final[dict[SectionKey, str]] = {
    SectionKey.RECENTLY_CONCLUDED: "Recently concluded",
    SectionKey.IRRECOVERABLE: "Irrecoverable",
}
_LEAN_BULK_REASON_LABEL: Final = "Unrecognised endings"
# Fixed display order for the collapsed summary (byte-stable output).
_LEAN_SUMMARY_ORDER: Final[tuple[str, ...]] = (
    "Recently concluded",
    "Irrecoverable",
    _LEAN_BULK_REASON_LABEL,
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
        return SectionKey.PROBABLE_CRASH_VICTIMS
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

    ``liveness_dead_pid_concluded_tail`` is a liveness reason (so it is otherwise
    silent) that DOES carry a note: the marker surviving proves an abnormal exit,
    but the concluded tail means there is likely nothing to resume. Naming it
    calmly is the whole point of the rule — it replaces the alarming ``unmatched``
    prompt for the "finished a turn, then the process was killed" case.
    """
    if reason == "liveness_dead_pid_concluded_tail":
        return (
            "session concluded, then its process was killed (idle-kill, or a "
            "terminal closed at the archive prompt before the wrapper fix) — "
            "likely nothing to resume"
        )
    if reason == "unmatched":
        return "Something fucky — let's go look"
    if reason in NO_LIVENESS_REASONS:
        return "no liveness file recorded (pre-installation session or wrapper bypass)"
    if reason in JSONL_ONLY_REASONS and reason != "ambiguous_match":
        return "session data is incomplete or corrupted"
    return None


# ---------------------------------------------------------------------------
# Per-entry rendering (branches on irrecoverable vs everything else).
# ---------------------------------------------------------------------------


# Index aliases for the SELECT columns below. Defined as constants so the
# row-tuple indexing in :func:`_render_entry` and :func:`render` doesn't
# rely on positional magic numbers spread across two functions.
_COL_UUID = 0
_COL_CWD = 1
_COL_CLASSIFICATION = 2
_COL_REASON = 3
_COL_STATE_SUMMARY = 4
_COL_USER_NOTES = 5
_COL_JSONL_LAST_TS = 6
_COL_PANE_TITLE = 7
_COL_LAST_SUBSTANTIVE = 8
# Column 9 (last_scanned) is used only for ORDER BY; never rendered.


# Rows written before the ``jsonl.last_substantive_text`` newline-collapse fix
# stored ``last_substantive`` with its original markdown newlines. The render
# places the value on a single ``- Last substantive:`` row (and may use it as
# the bold header label), so a surviving newline would push the remainder to
# column 0 — an embedded ``## heading`` then reads as a new report section and
# shreds the structure. Collapse whitespace runs defensively at render time so
# those already-stored rows read clean without needing a full re-scan.
_WHITESPACE_RUN: Final = re.compile(r"\s+")


def _single_line(value: str | None) -> str | None:
    """Collapse whitespace runs in ``value`` to single spaces; preserve ``None``.

    Idempotent on already-clean values (a freshly extracted snippet is already
    single-line). Returns ``None`` for ``None`` and for a value that is empty
    after collapsing, so the caller's ``is not None`` branch drops a blank line
    rather than rendering an empty field.
    """
    if value is None:
        return None
    collapsed = _WHITESPACE_RUN.sub(" ", value).strip()
    return collapsed or None


def _utc_iso(ts: int | None) -> str | None:
    """Return ``ts`` as a UTC ISO-8601 string, or ``None`` when ``ts`` is ``None``.

    Derived from the stored int via an explicit ``tz=timezone.utc`` so the
    output is host-timezone-independent — render against the same DB state is
    byte-identical regardless of the machine's local TZ (AC5.3).
    """
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _header_label(
    pane_title: str | None, last_substantive: str | None, uuid_full: str
) -> str:
    """Return the bold header label for a row.

    Prefers the human-meaningful ``pane_title``; failing that, the
    ``last_substantive`` snippet; failing both, a last-resort
    ``(session <uuid[:8]>)`` parenthetical. The 8-char form is *only* this
    last-resort fallback — never the primary identifier and never a
    replacement for the full uuid in the resume line. Shared by the
    recoverable and irrecoverable branches so the two cannot drift.
    """
    if pane_title:
        return pane_title
    if last_substantive:
        return last_substantive
    return f"(session {uuid_full[:8]})"


def _render_entry(row: tuple) -> list[str]:
    """Render one ``sessions`` row to its per-entry markdown lines.

    Branches on ``classification``:

    * ``irrecoverable`` rows emit a strikethrough opener
      (``~~no resume — <reason>~~``) and skip the reduced-confidence line
      entirely. Resume is structurally impossible (no JSONL on disk, or no
      cwd recorded), so advertising ``claudew --resume`` would be misleading.
      See Phase 4 coherence-review falsification anchor (2026-05-17).
    * Every other classification emits the standard
      ``claudew --resume <full-uuid>`` opener and may include a reduced-confidence
      warning when :func:`_reduced_confidence_text` fires.

    The bold header label is the human-meaningful ``pane_title`` or
    ``last_substantive`` snippet (:func:`_header_label`); the full uuid lives in
    the resume command. The 8-char ``uuid[:8]`` form appears only as a
    last-resort ``(session …)`` parenthetical when neither field is set.

    Conditional lines (Last activity, Last substantive, Reduced confidence,
    Notes) are emitted in fixed order so two rows with the same column values
    render byte-identically.
    """
    uuid_full = row[_COL_UUID]
    cwd = row[_COL_CWD]
    classification = row[_COL_CLASSIFICATION]
    reason = row[_COL_REASON]
    state_summary = row[_COL_STATE_SUMMARY]
    user_notes = row[_COL_USER_NOTES]
    pane_title = _single_line(row[_COL_PANE_TITLE])
    last_substantive = _single_line(row[_COL_LAST_SUBSTANTIVE])
    last_activity = _utc_iso(row[_COL_JSONL_LAST_TS])
    label = _header_label(pane_title, last_substantive, uuid_full)

    lines: list[str] = []
    if classification == "irrecoverable":
        lines.append(f"- **{label}**: ~~no resume — {reason}~~")
    else:
        lines.append(f"- **{label}**: `claudew --resume {uuid_full}`")
    lines.append(f"  - Working dir: `{cwd}`")
    lines.append(f"  - Classification: `{classification}` (`{reason}`)")
    lines.append(f"  - State: {state_summary}")
    if last_activity is not None:
        lines.append(f"  - Last activity: {last_activity}")
    if last_substantive is not None:
        lines.append(f"  - Last substantive: {last_substantive}")
    # Irrecoverable rows skip the reduced-confidence line: resume is
    # structurally impossible, so the confidence framing does not apply.
    if classification != "irrecoverable":
        warning = _reduced_confidence_text(reason)
        if warning is not None:
            lines.append(f"  - ⚠ Reduced confidence: {warning}")
    if user_notes is not None:
        lines.append(f"  - Notes: {user_notes}")
    return lines


# ---------------------------------------------------------------------------
# Uncorrelated abnormal-exit markers (Gap A): crash evidence with no session.
# ---------------------------------------------------------------------------

_UNCORRELATED_HEADER: Final = "## Uncorrelated crash markers"

# Per-reason human explanation for an uncorrelated marker. The stored ``reason``
# is one of the scan's enum strings ("dead_pid" | "boot_mismatch"); unknown
# values fall back to the raw string so a future reason is still surfaced.
_MARKER_REASON_TEXT: Final[dict[str, str]] = {
    "dead_pid": (
        "process exited abnormally and the marker was not cleaned up; no "
        "transcript could be correlated (likely an early crash, or a marker "
        "left by a pre-fix archive-prompt close)"
    ),
    "boot_mismatch": (
        "marker is from a previous boot (its process is gone); no transcript "
        "could be correlated"
    ),
}


def _render_marker(row: tuple) -> list[str]:
    """Render one ``uncorrelated_markers`` row to its markdown lines.

    Columns: ``(cwd, started, reason, pid)``. There is no UUID and no transcript,
    so no ``claudew --resume`` line is emitted — there is nothing to resume.
    """
    cwd, started, reason, pid = row
    started_iso = _utc_iso(started)
    lines = [f"- **abnormal-exit marker (pid {pid})**: no resumable session found"]
    lines.append(f"  - Working dir: `{_single_line(cwd)}`")
    if started_iso is not None:
        lines.append(f"  - Started: {started_iso}")
    lines.append(f"  - Reason: {_MARKER_REASON_TEXT.get(reason, reason)}")
    return lines


def _read_uncorrelated_markers(conn: sqlite3.Connection) -> list[tuple]:
    """Return ``(cwd, started, reason, pid)`` rows ordered for byte-stable render.

    Defensive: an old read-only DB (render bypasses ``open_db``) may predate the
    ``uncorrelated_markers`` table, so its absence yields an empty list rather
    than raising ``no such table`` (mirrors the AC7.3 column degradation).
    """
    present = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='uncorrelated_markers'"
    ).fetchone()
    if present is None:
        return []
    return conn.execute(
        "SELECT cwd, started, reason, pid FROM uncorrelated_markers "
        "ORDER BY started DESC, pid ASC"
    ).fetchall()


# ---------------------------------------------------------------------------
# Top-level render entry point.
# ---------------------------------------------------------------------------


def render(db_path: Path, *, show_all: bool = True) -> tuple[str, int]:  # noqa: PLR0912  # one branch per render section
    """Read ``sessions`` from ``db_path`` and return ``(markdown, row_count)``.

    ``show_all`` (default ``True``) renders the full all-means-all roster — every
    session in its section — and is what writes ``~/llm-resume.md``. ``show_all=
    False`` is the lean triage *terminal* view: the non-actionable bulk (concluded,
    irrecoverable, and unrecognised-ending borderline rows) collapses to a count
    summary so "what crashed" is a glance. ``row_count`` is always the total
    session count regardless of mode.

    The connection is opened read-only via the ``file:...?mode=ro`` URI
    so render cannot accidentally mutate the DB. Rows are sorted
    ``last_scanned DESC, uuid ASC`` — the secondary ``uuid`` key keeps
    output stable when two rows share an epoch second (required for AC3.2
    byte-identical rendering).

    No timestamps appear in the output. ``last_scanned`` drives ordering
    only; rendering at different times against the same DB state produces
    byte-identical output.

    The row count is derived from ``len(rows)`` on the same ``fetchall``
    result used for rendering — no second ``COUNT(*)`` query is issued.
    This eliminates the TOCTOU window where a concurrent ``scan`` between
    ``os.replace`` and a second DB read could cause an off-by-one in the
    user-visible "Rendered N sessions" echo. Resolved in Phase 6 review
    2026-05-18 (Option i).
    """
    with closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)) as conn:
        # Defensive column list: a DB opened only by render() never runs the
        # additive migration (open_db is bypassed), so the Phase-4 columns may
        # be absent on an old-shape DB. Select each present column by name,
        # else a NULL literal under the same alias, so the row tuple keeps a
        # fixed shape and `no such column` cannot be raised (AC7.3).
        # `jsonl_last_ts` is pre-Phase-4 (always present) — selected directly.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
        pane_title_col = "pane_title" if "pane_title" in cols else "NULL AS pane_title"
        last_substantive_col = (
            "last_substantive"
            if "last_substantive" in cols
            else "NULL AS last_substantive"
        )
        rows = conn.execute(
            "SELECT uuid, cwd, classification, classification_reason, "  # noqa: S608  # column names from a fixed internal allowlist, not user input
            "state_summary, user_notes, jsonl_last_ts, "
            f"{pane_title_col}, {last_substantive_col}, last_scanned "
            "FROM sessions ORDER BY last_scanned DESC, uuid ASC"
        ).fetchall()
        marker_rows = _read_uncorrelated_markers(conn)

    grouped: dict[SectionKey, list[tuple]] = {s.key: [] for s in SECTIONS}
    for row in rows:
        key = _section_for_row(row[_COL_CLASSIFICATION], row[_COL_REASON])
        grouped[key].append(row)

    parts: list[str] = [
        "# Claude Code session resume",
        "",
        "_Generated by crash-recovery. Direct edits to this file are overwritten"
        " on `crash-recovery regenerate`._",
        "",
    ]
    # Collapsed-bulk counts accumulated in lean mode (empty when show_all).
    collapsed_counts: dict[str, int] = {}

    for section in SECTIONS:
        section_rows = grouped[section.key]
        if not show_all and section.key in _LEAN_COLLAPSED_SECTIONS:
            # Whole section is bulk: count it, emit no header or entries.
            if section_rows:
                label = _LEAN_SECTION_LABEL[section.key]
                collapsed_counts[label] = collapsed_counts.get(label, 0) + len(
                    section_rows
                )
            continue
        if not show_all:
            # Within an actionable section, drop unrecognised-ending rows to the
            # collapsed count; keep the genuine crash-signal rows.
            kept = [r for r in section_rows if r[_COL_REASON] not in _LEAN_BULK_REASONS]
            dropped = len(section_rows) - len(kept)
            if dropped:
                collapsed_counts[_LEAN_BULK_REASON_LABEL] = (
                    collapsed_counts.get(_LEAN_BULK_REASON_LABEL, 0) + dropped
                )
            section_rows = kept
        parts.append(section.header)
        parts.append("")
        if not section_rows:
            parts.append(section.empty_message)
        else:
            for row in section_rows:
                parts.extend(_render_entry(row))
        parts.append("")

    # Uncorrelated markers are supplementary crash evidence, not sessions: the
    # section is appended ONLY when non-empty (so an empty report is unchanged
    # and the row count below stays the count of session rows). Always full —
    # crash evidence is never collapsed.
    if marker_rows:
        parts.append(_UNCORRELATED_HEADER)
        parts.append("")
        for marker in marker_rows:
            parts.extend(_render_marker(marker))
        parts.append("")

    # Lean-mode collapsed summary: one count line per bulk category, plus the
    # total, and the pointer to the full roster. Omitted entirely when nothing
    # was collapsed (e.g. an empty filesystem) so the lean view stays minimal.
    if not show_all and collapsed_counts:
        parts.append("## Collapsed")
        parts.append("")
        parts.append(
            "_Hidden from this view. Run `crash-recovery triage --all` for the "
            "full roster, or search `~/llm-resume.md`._"
        )
        parts.append("")
        for label in _LEAN_SUMMARY_ORDER:
            if label in collapsed_counts:
                parts.append(f"- {label}: {collapsed_counts[label]}")
        parts.append(f"- Total tracked sessions: {len(rows)}")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n", len(rows)
