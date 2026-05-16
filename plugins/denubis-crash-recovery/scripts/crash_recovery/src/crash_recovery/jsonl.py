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
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Deny-list filter: keep only top-level ``type`` values that carry real
# signal; everything else is treated as bookkeeping and dropped before the
# tail-shape walk.
#
# Deny-list approach (Phase 2 review, 2026-05-16): earlier allow-list held
# ``{"assistant", "user", "system", "attachment", ...}`` but empirical
# verification found ``custom-title``, ``agent-name``, ``agent-color``, and
# ``pr-link`` at the tails of main-session JSONLs — types the Phase 2B
# investigator's allow-list did not record. A smoking-gun session ended with
# 5 bookkeeping entries; the allow-list would have walked back through 3
# unfiltered ones and mis-classified a cleanly-concluded session as
# ``borderline_unknown_tail``. The deny-list is robust to new bookkeeping
# types Claude Code adds in future: any unknown ``type`` is conservatively
# filtered so it can never silently mask a concluded-tail signal. The failure
# mode runs the other direction (a future *real* type would be misclassified
# as bookkeeping) but that failure is visible (session falls to UNKNOWN /
# borderline) rather than silent — load-bearing on Phase 5 surfacing
# ``classification_reason`` row-level (anchored in phase_05.md).
#
# Full rationale and the empirical verification details live in
# ``docs/implementation-plans/2026-05-08-crash-recovery/phase_02.md`` Task 1.
# Do NOT revert to an allow-list without re-running that verification.
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
    except (ValueError, OSError):
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
    """Scan forward through ``entries`` from ``start_idx + 1`` for a matching tool_result.

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


def _has_ask_question_answer(
    entries: list[dict[str, Any]], start_idx: int
) -> bool:
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
    return all(
        isinstance(item, dict) and item.get("type") == "text" for item in items
    )


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

        if isinstance(tool_id, str) and _has_matching_tool_result(
            filtered, i, tool_id
        ):
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
            state_summary=_summarise(TailKind.UNKNOWN, None, "only bookkeeping entries"),
        )

    last_entry = filtered[-1]
    last_ts, last_ts_str = _parse_ts_pair(last_entry.get("timestamp"))

    # --- Classify the tail ----------------------------------------------
    # CONCLUDED: last entry is assistant end_turn with text-only content.
    if _is_concluded(last_entry):
        return _make_tail(
            TailKind.CONCLUDED, last_ts, last_ts_str, total_entries
        )

    # Tool dispatch: walk backward through ``filtered`` for the most recent
    # unmatched assistant tool_use. ``None`` means every dispatch in the
    # window was satisfied — fall through to UNKNOWN.
    dispatch_summary = _classify_dispatch(
        filtered, last_ts, last_ts_str, total_entries
    )
    if dispatch_summary is not None:
        return dispatch_summary

    # Nothing matched — clean parse, no end_turn, no dangling dispatch.
    return _make_tail(TailKind.UNKNOWN, last_ts, last_ts_str, total_entries)
