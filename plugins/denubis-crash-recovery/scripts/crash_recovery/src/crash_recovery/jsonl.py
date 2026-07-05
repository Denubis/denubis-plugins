"""Memory-bounded JSONL tail reader for Claude Code session logs.

The classifier in :mod:`crash_recovery.classify` consumes a :class:`TailSummary`
that describes the shape of the trailing entries in a session JSONL. This
module is the only place that reads session logs from disk; it is a pure
function relative to the bytes it reads (no globals, no caches), and it is
memory-bounded by using :class:`collections.deque` with ``maxlen=n``.

The classification logic is deliberately conservative: it only resolves a
:class:`TailKind` that the classifier rule table speaks to, and falls back to
:attr:`TailKind.UNKNOWN` for tails that parse cleanly but do not match any
documented signature.

Phase 2B investigator note (2026-05-13) confirms three load-bearing JSONL
properties from real session logs:

- Top-level ``type`` discriminates entry shape.
- Assistant ``message.stop_reason`` and ``message.content[].type`` carry the
  dispatch/text signal.
- ``tool_use_id`` matches across assistant ``tool_use`` and user
  ``tool_result``; **attachments and other bookkeeping entries can interleave
  between dispatch and result**, so matching must scan forward through the
  whole read window, not just adjacent entries.
"""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# Allow-list filter: keep only top-level ``type`` values in ``_REAL_TYPES``
# that carry real signal; everything else is treated as bookkeeping and
# dropped before the tail-shape walk.
#
# Allow-list approach (Phase 2 review, 2026-05-16): an earlier broader set
# held ``{"assistant", "user", "system", "attachment", ...}`` but empirical
# verification found ``custom-title``, ``agent-name``, ``agent-color``, and
# ``pr-link`` at the tails of main-session JSONLs — types the Phase 2B
# investigator's broader set did not exclude. A smoking-gun session ended
# with 5 bookkeeping entries; the broader set would have walked back through
# 3 unfiltered ones and mis-classified a cleanly-concluded session as
# ``borderline_unknown_tail``. The allow-list approach (keep only types in
# ``_REAL_TYPES``; everything else is filtered as bookkeeping) is robust to
# new bookkeeping types Claude Code adds in future: any unknown ``type`` is
# conservatively filtered so it can never silently mask a concluded-tail
# signal. The failure mode runs the other direction (a future *real* type
# would be misclassified as bookkeeping) but that failure is visible (session
# falls to UNKNOWN / borderline) rather than silent — load-bearing on Phase
# 5 surfacing ``classification_reason`` row-level (anchored in phase_05.md).
#
# Full rationale and the empirical verification details live in
# ``docs/implementation-plans/2026-05-08-crash-recovery/phase_02.md`` Task 1.
# Do NOT revert to a deny-list approach without re-running that verification.
_REAL_TYPES: frozenset[str] = frozenset({"assistant", "user"})


class TailKind(Enum):
    """Shapes the tail of a session JSONL can take.

    Values are documented in Phase 2 of the crash-recovery design plan and
    mapped to a :class:`crash_recovery.classify.ClassificationValue` by the
    rule table in :mod:`crash_recovery.classify`.
    """

    CONCLUDED = "concluded"
    TOOL_USE_NO_RESULT = "tool_use_no_result"
    ASK_QUESTION_NO_REPLY = "ask_question_no_reply"
    AGENT_DISPATCH_NO_RESULT = "agent_dispatch_no_result"
    EMPTY = "empty"
    MALFORMED_TAIL = "malformed_tail"
    MISSING_FILE = "missing_file"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TailSummary:
    """Immutable summary of the trailing entries in a JSONL.

    ``last_ts`` is unix epoch seconds (int) parsed from the final filtered
    entry's ``timestamp`` field, or ``None`` when no timestamp could be
    extracted (e.g., missing file, empty file, or every tail entry was
    bookkeeping).

    ``total_entries`` is the count of JSON-parseable lines observed within
    the read window (``deque(maxlen=n)``). It is NOT the total line count
    of the file — by design, only the last ``n`` lines are read.

    ``state_summary`` is a one-line human-readable description (kept under
    ~120 chars) for the ``sessions.state_summary`` column.
    """

    kind: TailKind
    last_ts: int | None
    total_entries: int
    state_summary: str


def _parse_ts(value: Any) -> int | None:
    """Parse an ISO-8601 timestamp string to unix epoch seconds.

    Returns ``None`` on any failure. Handles the trailing ``Z`` UTC suffix
    that ``datetime.fromisoformat`` accepts on 3.11+.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        # Python 3.11+ accepts the trailing ``Z`` directly.
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int(ts.timestamp())
    except ValueError, OSError:
        return None


def _content_items(entry: dict[str, Any]) -> list[Any]:
    """Return the ``message.content`` list of an entry, or empty list."""
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return content


def _stop_reason(entry: dict[str, Any]) -> Any:
    message = entry.get("message")
    if not isinstance(message, dict):
        return None
    return message.get("stop_reason")


def _last_assistant_tool_use(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Return the last ``tool_use`` content item of an assistant entry, if any."""
    if entry.get("type") != "assistant":
        return None
    for item in reversed(_content_items(entry)):
        if isinstance(item, dict) and item.get("type") == "tool_use":
            return item
    return None


def _has_matching_tool_result(
    entries: list[dict[str, Any]],
    start_idx: int,
    tool_use_id: str,
) -> bool:
    """Scan forward through ``entries`` from ``start_idx + 1`` for a matching
    tool_result.

    Per Phase 2B: attachments and other bookkeeping entries can interleave
    between an assistant tool_use dispatch and the user tool_result. We
    must NOT assume immediate adjacency.
    """
    for j in range(start_idx + 1, len(entries)):
        nxt = entries[j]
        if nxt.get("type") != "user":
            continue
        for item in _content_items(nxt):
            if (
                isinstance(item, dict)
                and item.get("type") == "tool_result"
                and item.get("tool_use_id") == tool_use_id
            ):
                return True
    return False


def _has_ask_question_answer(entries: list[dict[str, Any]], start_idx: int) -> bool:
    """Scan forward for a user entry carrying ``toolUseResult.answers``."""
    for j in range(start_idx + 1, len(entries)):
        nxt = entries[j]
        if nxt.get("type") != "user":
            continue
        tur = nxt.get("toolUseResult")
        if isinstance(tur, dict) and tur.get("answers"):
            return True
    return False


def _is_concluded(entry: dict[str, Any]) -> bool:
    """Assistant entry with stop_reason=end_turn and text-only content."""
    if entry.get("type") != "assistant":
        return False
    if _stop_reason(entry) != "end_turn":
        return False
    items = _content_items(entry)
    if not items:
        return False
    return all(isinstance(item, dict) and item.get("type") == "text" for item in items)


def _parse_ts_pair(value: Any) -> tuple[int | None, str | None]:
    """Parse ``value`` into both epoch-seconds and ISO-string representations.

    Returns ``(epoch, iso_str)`` where ``epoch`` is the unix-epoch-seconds int
    parsed via :func:`_parse_ts`, and ``iso_str`` is the original string form
    (only when ``value`` itself was a string). Either or both may be ``None``.

    Consolidates the otherwise-duplicated pattern of deriving the int and the
    raw-string form of a ``timestamp`` field together — they are always used
    together as a pair within :func:`parse_tail`.
    """
    epoch = _parse_ts(value)
    iso_str = value if isinstance(value, str) else None
    return epoch, iso_str


def _extract_best_ts(
    parsed: list[dict[str, Any]],
) -> tuple[int | None, str | None]:
    """Best-effort scan for the latest parseable ``timestamp`` in ``parsed``.

    Used by the malformed-tail branch of :func:`parse_tail`: when one or more
    lines in the read window failed to JSON-decode, this walks the
    successfully-parsed entries in reverse to surface whatever timestamp
    information remains. Returns ``(None, None)`` when no entry carries a
    parseable ISO-8601 ``timestamp``.
    """
    for entry in reversed(parsed):
        epoch, iso_str = _parse_ts_pair(entry.get("timestamp"))
        if epoch is not None:
            return epoch, iso_str
    return None, None


def _summarise(
    kind: TailKind,
    last_ts_str: str | None,
    detail: str = "",
) -> str:
    """Build a short human-readable state_summary string (<120 chars)."""
    ts_part = f" at {last_ts_str}" if last_ts_str else ""
    prefix = {
        TailKind.CONCLUDED: "concluded - end_turn",
        TailKind.TOOL_USE_NO_RESULT: "tool_use no result",
        TailKind.ASK_QUESTION_NO_REPLY: "ask_question no reply",
        TailKind.AGENT_DISPATCH_NO_RESULT: "agent dispatch no result",
        TailKind.EMPTY: "empty jsonl",
        TailKind.MALFORMED_TAIL: "malformed json at tail",
        TailKind.MISSING_FILE: "jsonl missing on disk",
        TailKind.UNKNOWN: "unknown tail shape",
    }[kind]
    detail_part = f": {detail}" if detail else ""
    summary = f"{prefix}{detail_part}{ts_part}"
    return summary[:120]


def _make_tail(
    kind: TailKind,
    last_ts: int | None,
    last_ts_str: str | None,
    total_entries: int,
    detail: str = "",
) -> TailSummary:
    """Construct a :class:`TailSummary` for a late-phase dispatch-walk result.

    Consolidates the five structurally-identical ``TailSummary`` construction
    sites in :func:`parse_tail` and :func:`_classify_dispatch` that share the
    shape ``TailSummary(kind=K, last_ts=last_ts, total_entries=total_entries,
    state_summary=_summarise(K, last_ts_str, detail))``. The ``kind`` is
    passed explicitly at each call site (TailKind discrimination is *not*
    abstracted here — only the construction boilerplate is).

    Not used by the early-return branches (MISSING_FILE, EMPTY, bookkeeping-
    only UNKNOWN) which carry ``last_ts=None`` and ``total_entries=0`` and
    are structurally distinct.
    """
    return TailSummary(
        kind=kind,
        last_ts=last_ts,
        total_entries=total_entries,
        state_summary=_summarise(kind, last_ts_str, detail),
    )


def _classify_dispatch(
    filtered: list[dict[str, Any]],
    last_ts: int | None,
    last_ts_str: str | None,
    total_entries: int,
) -> TailSummary | None:
    """Walk ``filtered`` backward to find the most recent unmatched tool dispatch.

    Returns the appropriate :class:`TailSummary` for the unmatched dispatch
    (one of ASK_QUESTION_NO_REPLY, AGENT_DISPATCH_NO_RESULT, or
    TOOL_USE_NO_RESULT), or ``None`` if every assistant ``tool_use`` in the
    window is satisfied by a downstream ``tool_result`` (or
    ``toolUseResult.answers`` for AskUserQuestion). The caller decides what
    "no dangling dispatch" means in context — :func:`parse_tail` treats it
    as ``TailKind.UNKNOWN``.

    Extracted from :func:`parse_tail` to reduce its cognitive complexity; see
    Phase 2 refactoring assessment (2026-05-16).
    """
    for i in range(len(filtered) - 1, -1, -1):
        entry = filtered[i]
        tu = _last_assistant_tool_use(entry)
        if tu is None:
            continue
        tool_name = tu.get("name")
        tool_id = tu.get("id")

        if tool_name == "AskUserQuestion":
            if isinstance(tool_id, str) and _has_matching_tool_result(
                filtered, i, tool_id
            ):
                # tool_result satisfied — keep scanning earlier dispatches.
                continue
            if _has_ask_question_answer(filtered, i):
                continue
            return _make_tail(
                TailKind.ASK_QUESTION_NO_REPLY,
                last_ts,
                last_ts_str,
                total_entries,
            )

        if isinstance(tool_id, str) and _has_matching_tool_result(filtered, i, tool_id):
            # This dispatch was resolved — look further back for an earlier
            # unmatched dispatch.
            continue

        if tool_name == "Task":
            return _make_tail(
                TailKind.AGENT_DISPATCH_NO_RESULT,
                last_ts,
                last_ts_str,
                total_entries,
            )
        return _make_tail(
            TailKind.TOOL_USE_NO_RESULT,
            last_ts,
            last_ts_str,
            total_entries,
            f"{tool_name} dispatched" if tool_name else "tool dispatched",
        )

    return None


# Bound the forward scan: a real session's first cwd/timestamp record sits within
# the first few parseable records (after the snapshot prefix). Measured across
# 7683 real ~/.claude/projects transcripts, the first non-empty cwd appears by
# record 9 at the deepest (p99 = 4), so 50 is ~5x headroom. The limit counts
# parseable records, not raw lines (blank and unparseable lines are skipped
# without consuming it), so it bounds cost on the well-formed transcripts this
# reads; the line-by-line read keeps memory bounded regardless of file size.
_FIRST_FIELD_SCAN_LIMIT = 50


def first_record_field(
    path: Path, field: str, limit: int = _FIRST_FIELD_SCAN_LIMIT
) -> str | None:
    """Return the value of ``field`` from the first JSONL record that carries it
    as a non-empty value, scanning forward up to ``limit`` parseable records.

    Best-effort: returns ``None`` on missing file, unreadable file, or no record
    carrying the field within the window. Never raises. Blank lines and lines that
    fail to JSON-decode are skipped and do not consume the record budget — only
    parseable dict records count toward ``limit``.
    """
    try:
        f = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return None
    with f:
        count = 0
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                d = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(d, dict):
                continue
            count += 1
            value = d.get(field)
            if isinstance(value, str) and value:
                return value
            if count >= limit:
                return None
    return None


def parse_tail(path: Path, n: int = 20) -> TailSummary:
    """Read up to the last ``n`` lines of ``path`` and classify the tail.

    Memory-bounded via ``collections.deque(maxlen=n)``: even on a 1 GB
    JSONL only the last ``n`` lines are retained in memory.

    Never raises on malformed JSON or missing files. The :class:`TailSummary`
    return value's ``kind`` distinguishes the failure modes.
    """
    # --- Missing-file branch ---------------------------------------------
    if not path.exists():
        return TailSummary(
            kind=TailKind.MISSING_FILE,
            last_ts=None,
            total_entries=0,
            state_summary=_summarise(TailKind.MISSING_FILE, None),
        )

    # --- Read the last n lines into a bounded deque ----------------------
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            tail: deque[str] = deque(f, maxlen=n)
    except OSError:
        # Treat unreadable files the same as missing for classifier purposes;
        # an audit-level error path could differentiate, but for Phase 2 the
        # rule table only needs the binary present/absent signal.
        return TailSummary(
            kind=TailKind.MISSING_FILE,
            last_ts=None,
            total_entries=0,
            state_summary=_summarise(TailKind.MISSING_FILE, None),
        )

    if not tail:
        return TailSummary(
            kind=TailKind.EMPTY,
            last_ts=None,
            total_entries=0,
            state_summary=_summarise(TailKind.EMPTY, None),
        )

    # --- JSON-parse each line; a single decode failure flips kind --------
    parsed: list[dict[str, Any]] = []
    saw_malformed = False
    for line in tail:
        stripped = line.strip()
        if not stripped:
            # Skip blank lines silently — they aren't malformed JSON, just
            # noise (e.g., trailing newline at EOF).
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            saw_malformed = True
            continue
        if isinstance(obj, dict):
            parsed.append(obj)

    if saw_malformed:
        # Best-effort last_ts from whatever parsed cleanly.
        last_ts, last_ts_str = _extract_best_ts(parsed)
        return TailSummary(
            kind=TailKind.MALFORMED_TAIL,
            last_ts=last_ts,
            total_entries=len(parsed),
            state_summary=_summarise(
                TailKind.MALFORMED_TAIL, last_ts_str, "in read window"
            ),
        )

    total_entries = len(parsed)

    # --- Drop bookkeeping entries before walking the tail ----------------
    filtered = [e for e in parsed if e.get("type") in _REAL_TYPES]

    if not filtered:
        # All entries in the window were bookkeeping; we have no signal.
        return TailSummary(
            kind=TailKind.UNKNOWN,
            last_ts=None,
            total_entries=total_entries,
            state_summary=_summarise(
                TailKind.UNKNOWN, None, "only bookkeeping entries"
            ),
        )

    last_entry = filtered[-1]
    last_ts, last_ts_str = _parse_ts_pair(last_entry.get("timestamp"))

    # --- Classify the tail ----------------------------------------------
    # CONCLUDED: last entry is assistant end_turn with text-only content.
    if _is_concluded(last_entry):
        return _make_tail(TailKind.CONCLUDED, last_ts, last_ts_str, total_entries)

    # Tool dispatch: walk backward through ``filtered`` for the most recent
    # unmatched assistant tool_use. ``None`` means every dispatch in the
    # window was satisfied — fall through to UNKNOWN.
    dispatch_summary = _classify_dispatch(filtered, last_ts, last_ts_str, total_entries)
    if dispatch_summary is not None:
        return dispatch_summary

    # Nothing matched — clean parse, no end_turn, no dangling dispatch.
    return _make_tail(TailKind.UNKNOWN, last_ts, last_ts_str, total_entries)


# Content-level bookkeeping markers: a real (assistant/user) turn whose
# extracted text *starts with* any of these is operator leakage, not a
# substantive turn. This is distinct from the type-level ``_REAL_TYPES``
# filter — these turns ARE assistant/user entries, but their text is noise
# (``<usage>`` accounting, ``<summary>`` recaps, task-notification envelopes,
# and the standard post-compaction recovery notice).
_BOOKKEEPING_MARKERS: tuple[str, ...] = (
    "<usage>",
    "<summary>",
    "</task-notification>",
    "<task-notification>",
    "If you need specific details from before compaction",
)

# Cap on the returned snippet. Mirrors ``state_summary``'s short-string spirit
# (kept well under a sentence) so the ``sessions.last_substantive`` column and
# the render line it feeds stay compact.
_LAST_SUBSTANTIVE_CAP = 200

# A real assistant/user turn is multi-line markdown (``##`` headings,
# ``**bold**``, fenced code). The render places the snippet on a single
# ``- Last substantive:`` row, so any embedded newline would push the rest of
# the message to column 0 of a new line — an embedded ``## heading`` then reads
# as a new report section and shreds the structure. Collapse every whitespace
# run (newlines, tabs, repeated spaces) to one space so the snippet is always a
# single line. Markdown *inline* styling (``**``/`` ` ``) is left intact: it no
# longer breaks structure once the value is single-line and not column-0.
_WHITESPACE_RUN = re.compile(r"\s+")


def _entry_text(entry: dict[str, Any]) -> str:
    """Extract the human-readable text of one assistant/user entry.

    Assistant entries carry ``message.content`` as a list of items; we join
    the ``text`` of every ``type == "text"`` item. User entries carry
    ``message.content`` as either a plain string (the common shape) or a list
    of items (join the ``text`` items, mirroring the assistant path). Anything
    else yields the empty string.
    """
    message = entry.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            item["text"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        ]
        return "".join(parts)
    return ""


def _is_bookkeeping_text(text: str) -> bool:
    """True when ``text`` is empty or starts with a content-level bookkeeping marker."""
    stripped = text.strip()
    if not stripped:
        return True
    return stripped.startswith(_BOOKKEEPING_MARKERS)


def last_substantive_text(path: Path, n: int = 20) -> str | None:
    """Return the most recent substantive assistant/user text in the last ``n`` lines.

    Reads the last ``n`` lines via a bounded ``deque`` (same memory-bounded
    approach as :func:`parse_tail`), keeps only ``_REAL_TYPES`` entries, then
    walks them newest-first and returns the first whose extracted text is
    non-empty and not content-level bookkeeping. The result is stripped and
    truncated to :data:`_LAST_SUBSTANTIVE_CAP` characters.

    Returns ``None`` when the file is missing/unreadable or every real turn in
    the window is empty or bookkeeping. Never raises.
    """
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            tail: deque[str] = deque(f, maxlen=n)
    except OSError:
        return None

    real: list[dict[str, Any]] = []
    for line in tail:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("type") in _REAL_TYPES:
            real.append(obj)

    for entry in reversed(real):
        text = _entry_text(entry)
        if _is_bookkeeping_text(text):
            continue
        single_line = _WHITESPACE_RUN.sub(" ", text).strip()
        return single_line[:_LAST_SUBSTANTIVE_CAP]
    return None
