"""Tests for crash_recovery.jsonl.parse_tail and first_record_field.

Each test exercises one TailKind classification or one first_record_field
behaviour. Filesystem is real (``tmp_path``) — both are pure functions
relative to the bytes on disk.

Covers AC3.4 (malformed_tail) and AC3.5 (empty_file) directly; AC3.1 is
covered when Task 5's parametrised rule-table tests run against the
TailKind values produced here.

AC2.1/AC2.3 (forward-scan helper) are covered by the
``test_first_record_field_*`` tests below.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from crash_recovery.jsonl import (
    TailKind,
    TailSummary,
    first_record_field,
    last_substantive_text,
    parse_tail,
)

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
    make_only_bookkeeping_content_tail,
    make_only_bookkeeping_no_signal,
    make_post_compaction_boilerplate_tail,
    make_snapshot_prefixed_jsonl,
    make_substantive_then_bookkeeping_tail,
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
    """AskUserQuestion satisfied by toolUseResult.answers must NOT produce
    ASK_QUESTION_NO_REPLY.

    Exercises the ``_has_ask_question_answer`` satisfaction path in parse_tail
    which had no coverage in the initial Task 2 set (Phase 2 review Minor 1).
    The answered AskUserQuestion is the last signal, so the tail resolves to
    UNKNOWN (no end_turn, no dangling dispatch) rather than ASK_QUESTION_NO_REPLY.
    """
    p = tmp_path / "ask_answered.jsonl"
    make_ask_question_answered_by_answers(p)
    summary = parse_tail(p)
    assert summary.kind is not TailKind.ASK_QUESTION_NO_REPLY, (
        "answered AskUserQuestion should not produce ASK_QUESTION_NO_REPLY;"
        f" got {summary.kind}"
    )


def test_parse_tail_classifies_agent_dispatch_no_result(tmp_path: Path) -> None:
    p = tmp_path / "agent.jsonl"
    make_agent_dispatch_no_result(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.AGENT_DISPATCH_NO_RESULT


def test_parse_tail_handles_attachment_interleave(tmp_path: Path) -> None:
    """Attachment between tool_use and tool_result must NOT trigger TOOL_USE_NO_RESULT.
    """
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
    """last_ts is unix epoch seconds parsed from the final filtered entry's timestamp.
    """
    p = tmp_path / "ts.jsonl"
    make_concluded(p)
    summary = parse_tail(p)
    expected = int(datetime(2026, 5, 13, 3, 0, 12, tzinfo=UTC).timestamp())
    assert summary.last_ts == expected


def test_parse_tail_returns_tail_summary_instance(tmp_path: Path) -> None:
    """parse_tail always returns a TailSummary, even for the missing-file branch."""
    missing = tmp_path / "nope.jsonl"
    assert isinstance(parse_tail(missing), TailSummary)
    p = tmp_path / "ok.jsonl"
    make_concluded(p)
    assert isinstance(parse_tail(p), TailSummary)


def test_parse_tail_handles_only_bookkeeping_no_signal(tmp_path: Path) -> None:
    """Deny-list edge case: every entry is bookkeeping; no real signal.

    The filter strips every entry, leaving an empty filtered window. The
    parser must walk that empty window without crashing and return UNKNOWN
    (there is no signal to interpret). Coherence-review L2 (2026-05-16).
    """
    p = tmp_path / "only_bookkeeping.jsonl"
    make_only_bookkeeping_no_signal(p)
    summary = parse_tail(p)
    assert summary.kind is TailKind.UNKNOWN, (
        f"expected UNKNOWN when filter strips every entry, got {summary.kind}"
    )


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
        "expected CONCLUDED after deny-list strips bookkeeping tail,"
        f" got {summary.kind}"
    )


# ---------------------------------------------------------------------------
# last_substantive_text — AC5.2 (extraction half)
# ---------------------------------------------------------------------------


def test_last_substantive_skips_usage_and_task_notification(tmp_path: Path) -> None:
    """AC5.2: a tail ending in <usage>/</task-notification> returns the real prior text.

    The two trailing turns are genuine user entries (kept by ``_REAL_TYPES``)
    whose *content* is operator noise. The backward walk must skip both and
    return the earlier assistant's substantive text.
    """
    p = tmp_path / "usage_tail.jsonl"
    make_substantive_then_bookkeeping_tail(p)
    result = last_substantive_text(p)
    assert result == "Here is the real answer."


def test_last_substantive_skips_post_compaction_boilerplate(tmp_path: Path) -> None:
    """AC5.2: post-compaction boilerplate as the last user turn is skipped."""
    p = tmp_path / "compaction_tail.jsonl"
    make_post_compaction_boilerplate_tail(p)
    result = last_substantive_text(p)
    assert result == "Prior substantive turn."


def test_last_substantive_returns_none_when_only_bookkeeping(tmp_path: Path) -> None:
    """AC5.2: a window with only bookkeeping content yields ``None``."""
    p = tmp_path / "only_bookkeeping_content.jsonl"
    make_only_bookkeeping_content_tail(p)
    result = last_substantive_text(p)
    assert result is None


def test_last_substantive_returns_last_real_assistant_text(tmp_path: Path) -> None:
    """A clean concluded tail returns the final assistant text."""
    p = tmp_path / "concluded.jsonl"
    make_concluded(p)
    result = last_substantive_text(p)
    assert result == "done"


def test_last_substantive_missing_file_returns_none(tmp_path: Path) -> None:
    """Missing file → ``None`` without raising."""
    p = tmp_path / "nope.jsonl"
    assert not p.exists()
    assert last_substantive_text(p) is None


def test_last_substantive_truncates_to_cap(tmp_path: Path) -> None:
    """A very long substantive turn is truncated to the ~200-char cap."""
    p = tmp_path / "long_text.jsonl"
    long_text = "x" * 500
    p.write_text(
        json.dumps(
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": long_text}],
                },
            }
        )
        + "\n"
    )
    result = last_substantive_text(p)
    assert result is not None
    assert len(result) <= 200


def test_last_substantive_collapses_multiline_markdown_to_single_line(
    tmp_path: Path,
) -> None:
    """A multi-line markdown assistant turn collapses to one rendered line.

    Real assistant messages carry their own markdown — ``##`` headings,
    ``**bold**``, fenced code. Stored verbatim with newlines intact, the value
    spills across multiple rendered lines: an embedded ``## heading`` lands at
    column 0 and is parsed as a new report section, shredding the structure and
    bleeding one session's entry into the next (the real-DB failure that made
    triage output unreadable). The extracted snippet must be a single line so it
    sits on one ``- Last substantive:`` row.
    """
    p = tmp_path / "multiline_markdown.jsonl"
    multiline = (
        "## What changed\n\n"
        "**Phase 1** — main CV data:\n"
        "- pulled new bib\n\n"
        "```python\nrun()\n```\n"
    )
    p.write_text(
        json.dumps(
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": multiline}],
                },
            }
        )
        + "\n"
    )
    result = last_substantive_text(p)
    assert result is not None
    assert "\n" not in result, "embedded newline would shatter the report row"
    assert "\r" not in result
    # Whitespace runs (including the blank lines) collapse to single spaces;
    # the text content is preserved.
    assert result.startswith("## What changed")
    assert "  " not in result, "whitespace runs must collapse to single spaces"


# ---------------------------------------------------------------------------
# first_record_field — AC2.1 and AC2.3 (helper level)
# ---------------------------------------------------------------------------


def test_first_record_field_cwd_on_line2_snapshot_prefixed(tmp_path: Path) -> None:
    """AC2.1: snapshot-prefixed JSONL (cwd on line 2) → returns the real cwd.

    Before this fix, readers that only examined line 1 saw the snapshot record
    which carries no ``cwd``, and returned ``""`` or ``None``. The forward scan
    must skip the snapshot record and return the line-2 value.
    """
    p = tmp_path / "snapshot_prefixed.jsonl"
    expected_cwd = "/home/user/my-project"
    make_snapshot_prefixed_jsonl(
        p, cwd=expected_cwd, first_ts=1_715_151_234, tail_kind=TailKind.CONCLUDED
    )
    result = first_record_field(p, "cwd")
    assert result == expected_cwd


def test_first_record_field_returns_none_when_no_cwd_anywhere(tmp_path: Path) -> None:
    """AC2.3: JSONL whose records never carry ``cwd`` → returns ``None``.

    Genuine no-cwd case: every record is a snapshot/bookkeeping entry with no
    ``cwd`` field. The forward scan exhausts its budget and returns ``None``,
    preserving the conservative contract.
    """
    p = tmp_path / "no_cwd.jsonl"
    # Write records that carry no ``cwd`` at all.
    entries = [
        {
            "type": "snapshot",
            "messageId": "msg_001",
            "snapshot": {},
            "isSnapshotUpdate": False,
        },
        {
            "type": "snapshot",
            "messageId": "msg_002",
            "snapshot": {},
            "isSnapshotUpdate": False,
        },
        {
            "type": "snapshot",
            "messageId": "msg_003",
            "snapshot": {},
            "isSnapshotUpdate": False,
        },
    ]
    p.write_text("".join(json.dumps(e) + "\n" for e in entries))
    result = first_record_field(p, "cwd")
    assert result is None


def test_first_record_field_timestamp_on_snapshot_prefixed(tmp_path: Path) -> None:
    """Timestamp variant: snapshot-prefixed JSONL → returns first real timestamp string.

    The snapshot record on line 1 carries no ``timestamp``; the real record on
    line 2 does. The forward scan must return that line-2 timestamp.
    """
    import time as _time

    now_epoch = int(_time.time()) - 3600
    p = tmp_path / "ts_prefixed.jsonl"
    make_snapshot_prefixed_jsonl(
        p, cwd="/tmp/ts-test", first_ts=now_epoch, tail_kind=TailKind.CONCLUDED
    )
    result = first_record_field(p, "timestamp")
    assert result is not None
    assert result.startswith("20")  # ISO-8601 year prefix sanity check


def test_first_record_field_returns_none_when_cwd_beyond_limit(tmp_path: Path) -> None:
    """Bound test: cwd only appears beyond the scan limit → returns ``None``.

    Writes ``limit + 2`` snapshot-only records before the real cwd record.
    The helper must stop at the limit and return ``None``, capping its cost
    on pathological files.
    """
    limit = 5  # Use a small explicit limit for the test.
    p = tmp_path / "beyond_limit.jsonl"
    entries = [
        {
            "type": "snapshot",
            "messageId": f"msg_{i:03d}",
            "snapshot": {},
            "isSnapshotUpdate": False,
        }
        for i in range(limit + 2)  # more parseable records than the limit
    ]
    # Real cwd record sits past the limit window.
    entries.append(
        {
            "type": "user",
            "cwd": "/should/not/be/found",
            "timestamp": FIXED_TS,
            "message": {"content": []},
        }
    )
    p.write_text("".join(json.dumps(e) + "\n" for e in entries))
    result = first_record_field(p, "cwd", limit=limit)
    assert result is None


def test_first_record_field_returns_none_for_missing_file(tmp_path: Path) -> None:
    """Missing file → returns ``None`` without raising."""
    p = tmp_path / "does_not_exist.jsonl"
    assert not p.exists()
    result = first_record_field(p, "cwd")
    assert result is None


def test_first_record_field_cwd_on_line1_standard_format(tmp_path: Path) -> None:
    """Standard format (cwd on line 1) still works after the refactor.

    Regression guard: existing sessions without a snapshot prefix must not
    be broken by the forward-scan change.
    """
    p = tmp_path / "standard.jsonl"
    expected_cwd = "/tmp/standard-project"
    entry = {
        "type": "user",
        "cwd": expected_cwd,
        "timestamp": FIXED_TS,
        "message": {"content": []},
    }
    p.write_text(json.dumps(entry) + "\n")
    result = first_record_field(p, "cwd")
    assert result == expected_cwd
