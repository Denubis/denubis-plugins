"""Tests for crash_recovery.jsonl.parse_tail.

Each test exercises one TailKind classification. Filesystem is real
(``tmp_path``) — parse_tail is a pure function relative to the bytes on
disk and the read window size.

Covers AC3.4 (malformed_tail) and AC3.5 (empty_file) directly; AC3.1 is
covered when Task 5's parametrised rule-table tests run against the
TailKind values produced here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from crash_recovery.jsonl import TailKind, TailSummary, parse_tail
# pytest injects tests/ onto sys.path when tests/__init__.py is absent (a
# deliberate Phase 1 decision for workspace-wide collection), so the
# fixtures package is addressable as top-level "fixtures", not "tests.fixtures".
from fixtures.jsonl_builder import (
    FIXED_TS,
    make_agent_dispatch_no_result,
    make_ask_question_answered_by_answers,
    make_ask_question_no_reply,
    make_attachment_interleaved_then_concluded,
    make_bookkeeping_only_tail,
    make_concluded,
    make_empty,
    make_malformed_tail,
    make_tool_use_no_result,
)


def test_parse_tail_classifies_concluded(tmp_path: Path) -> None:
    p = tmp_path / "concluded.jsonl"
    make_concluded(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.CONCLUDED
    assert summary.state_summary  # AC3.3 surrogate: non-empty


def test_parse_tail_classifies_tool_use_no_result(tmp_path: Path) -> None:
    p = tmp_path / "tool_use.jsonl"
    make_tool_use_no_result(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.TOOL_USE_NO_RESULT


def test_parse_tail_classifies_ask_question_no_reply(tmp_path: Path) -> None:
    p = tmp_path / "ask.jsonl"
    make_ask_question_no_reply(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.ASK_QUESTION_NO_REPLY


def test_parse_tail_handles_ask_question_answered_by_answers(tmp_path: Path) -> None:
    """AskUserQuestion satisfied by toolUseResult.answers must NOT produce ASK_QUESTION_NO_REPLY.

    Exercises the ``_has_ask_question_answer`` satisfaction path in parse_tail
    which had no coverage in the initial Task 2 set (Phase 2 review Minor 1).
    The answered AskUserQuestion is the last signal, so the tail resolves to
    UNKNOWN (no end_turn, no dangling dispatch) rather than ASK_QUESTION_NO_REPLY.
    """
    p = tmp_path / "ask_answered.jsonl"
    make_ask_question_answered_by_answers(p)
    summary = parse_tail(p)
    assert summary.kind is not TailKind.ASK_QUESTION_NO_REPLY, (
        f"answered AskUserQuestion should not produce ASK_QUESTION_NO_REPLY; got {summary.kind}"
    )


def test_parse_tail_classifies_agent_dispatch_no_result(tmp_path: Path) -> None:
    p = tmp_path / "agent.jsonl"
    make_agent_dispatch_no_result(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.AGENT_DISPATCH_NO_RESULT


def test_parse_tail_handles_attachment_interleave(tmp_path: Path) -> None:
    """Attachment between tool_use and tool_result must NOT trigger TOOL_USE_NO_RESULT."""
    p = tmp_path / "interleave.jsonl"
    make_attachment_interleaved_then_concluded(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.CONCLUDED


def test_parse_tail_classifies_empty_file_as_empty(tmp_path: Path) -> None:
    """AC3.5: empty JSONL yields EMPTY with state_summary mentioning 'empty'."""
    p = tmp_path / "empty.jsonl"
    make_empty(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.EMPTY
    assert "empty" in summary.state_summary.lower()


def test_parse_tail_classifies_malformed_tail(tmp_path: Path) -> None:
    """AC3.4: malformed JSON in read window yields MALFORMED_TAIL."""
    p = tmp_path / "malformed.jsonl"
    make_malformed_tail(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.MALFORMED_TAIL
    # state_summary should mention the malformation so downstream render
    # can cite it; "malformed" appearing in the reason text is the
    # documented contract per Phase 2 design.
    assert "malformed" in summary.state_summary.lower()


def test_parse_tail_handles_missing_file(tmp_path: Path) -> None:
    """No exception; MISSING_FILE kind returned for a path that does not exist."""
    p = tmp_path / "does_not_exist.jsonl"
    assert not p.exists()
    summary = parse_tail(p)
    assert summary.kind is TailKind.MISSING_FILE
    assert summary.total_entries == 0
    assert summary.last_ts is None


def test_parse_tail_respects_n_window(tmp_path: Path) -> None:
    """A long file with n=10 reports total_entries == 10."""
    p = tmp_path / "long.jsonl"
    lines = []
    for i in range(1000):
        kind = "assistant" if i % 2 == 0 else "user"
        lines.append(
            json.dumps(
                {"type": kind, "timestamp": FIXED_TS, "message": {"content": []}}
            )
            + "\n"
        )
    p.write_text("".join(lines))
    summary = parse_tail(p, n=10)
    assert summary.total_entries == 10


def test_parse_tail_extracts_last_ts(tmp_path: Path) -> None:
    """last_ts is unix epoch seconds parsed from the final filtered entry's timestamp."""
    p = tmp_path / "ts.jsonl"
    make_concluded(p)
    summary = parse_tail(p)
    expected = int(
        datetime(2026, 5, 13, 3, 0, 12, tzinfo=timezone.utc).timestamp()
    )
    assert summary.last_ts == expected


def test_parse_tail_returns_tail_summary_instance(tmp_path: Path) -> None:
    """parse_tail always returns a TailSummary, even for the missing-file branch."""
    missing = tmp_path / "nope.jsonl"
    assert isinstance(parse_tail(missing), TailSummary)
    p = tmp_path / "ok.jsonl"
    make_concluded(p)
    assert isinstance(parse_tail(p), TailSummary)


def test_bookkeeping_only_tail_walks_past_to_real_signal(tmp_path: Path) -> None:
    """Deny-list filter regression: bookkeeping entries after end_turn are dropped.

    The smoking-gun case: an assistant ``end_turn`` entry followed by
    ``custom-title``, ``agent-name``, ``agent-color``, and ``permission-mode``
    entries (types observed at real session tails on 2026-05-16). The
    allow-list filter would have walked back through those unfiltered entries
    and mis-classified the session as UNKNOWN → borderline_unknown_tail. The
    deny-list (_REAL_TYPES) correctly filters them out, leaving the
    ``assistant`` end_turn as the last real signal → CONCLUDED.
    """
    p = tmp_path / "bookkeeping_tail.jsonl"
    make_bookkeeping_only_tail(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.CONCLUDED, (
        f"expected CONCLUDED after deny-list strips bookkeeping tail, got {summary.kind}"
    )
