"""Claude transcript discovery, usage records, deduplication and user text.

Expected values are worked out by hand from the token-estimator's audited rule
(`estimate.collect_claude`, `verify.claude_pass`): one message per message id; its
maximum output; main when any record of it is a main-thread record; its origin is
the earliest timestamp among the records of the partition it is counted in; and the
record holding the maximum output supplies the working directory, ties going to the
smaller directory string.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from denubis_agent_logs.claude import (
    ClaudeMessage,
    TranscriptFile,
    UsageRecord,
    deduplicate,
    iter_usage_records,
    text_blocks,
    transcript_files,
)
from denubis_agent_logs.records import ReadReport

SESSION = "0c0ffee0-0000-4000-8000-000000000001"
PROJECT = "-work-main"


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    return path


def _main_file(root: Path) -> Path:
    return root / PROJECT / f"{SESSION}.jsonl"


def _subagent_file(root: Path, agent: str = "agent-a1") -> Path:
    return root / PROJECT / SESSION / "subagents" / f"{agent}.jsonl"


def _assistant(
    message_id: str,
    output: int,
    *,
    timestamp: str,
    cwd: str = "/work/main",
    sidechain: bool = False,
    model: str = "claude-opus-4-7",
    input_tokens: int = 3,
    cache_creation: int = 200,
    cache_read: int = 5000,
) -> dict:
    return {
        "type": "assistant",
        "sessionId": SESSION,
        "cwd": cwd,
        "isSidechain": sidechain,
        "timestamp": timestamp,
        "message": {
            "id": message_id,
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
                "output_tokens": output,
            },
        },
    }


def _deduplicated(root: Path) -> tuple[list[ClaudeMessage], ReadReport]:
    report = ReadReport()
    transcripts = transcript_files(root, include_subagents=True)
    return deduplicate(iter_usage_records(transcripts, report)), report


def _usage(message_id: str, output: int, *, cwd: str | None) -> UsageRecord:
    return UsageRecord(
        message_id=message_id,
        model="claude-opus-4-7",
        session_id=SESSION,
        cwd=cwd,
        timestamp=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        input_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        output_tokens=output,
        is_main=True,
        path=Path("/unused.jsonl"),
    )


def test_message_in_a_main_and_a_subagent_file_counts_once_with_the_larger_output(
    tmp_path,
):
    root = tmp_path / "projects"
    _write_jsonl(
        _main_file(root),
        [_assistant("msg_A", 10, timestamp="2026-10-01T10:00:05Z", cwd="/work/main")],
    )
    _write_jsonl(
        _subagent_file(root),
        [
            _assistant(
                "msg_A",
                50,
                timestamp="2026-10-01T10:00:01Z",
                cwd="/work/sub",
                sidechain=True,
            )
        ],
    )

    messages, _ = _deduplicated(root)

    assert len(messages) == 1
    (message,) = messages
    assert message.message_id == "msg_A"
    assert message.is_main is True
    assert message.peak.output_tokens == 50
    assert message.peak.cwd == "/work/sub"
    # Counted as main, so the origin is the earliest main-thread record, not the
    # earlier subagent replay.
    assert message.origin == datetime(2026, 10, 1, 10, 0, 5, tzinfo=UTC)


def test_partial_stream_records_keep_the_maximum_output_and_its_token_fields(
    tmp_path,
):
    root = tmp_path / "projects"
    _write_jsonl(
        _main_file(root),
        [
            _assistant("msg_B", 1, timestamp="2026-10-01T11:00:00Z"),
            _assistant(
                "msg_B",
                120,
                timestamp="2026-10-01T11:00:02Z",
                input_tokens=4,
                cache_creation=210,
                cache_read=9000,
            ),
            _assistant("msg_B", 37, timestamp="2026-10-01T11:00:03Z"),
        ],
    )

    messages, _ = _deduplicated(root)

    (message,) = messages
    peak = message.peak
    assert (
        peak.input_tokens,
        peak.cache_creation_input_tokens,
        peak.cache_read_input_tokens,
        peak.output_tokens,
    ) == (4, 210, 9000, 120)
    assert (peak.model, peak.session_id) == ("claude-opus-4-7", SESSION)
    assert message.origin == datetime(2026, 10, 1, 11, 0, 0, tzinfo=UTC)


def test_message_seen_only_in_subagent_records_is_a_subagent_message(tmp_path):
    root = tmp_path / "projects"
    # The older layout kept sidechain records in the main file.
    _write_jsonl(
        _main_file(root),
        [_assistant("msg_C", 7, timestamp="2026-10-01T12:00:09Z", sidechain=True)],
    )
    _write_jsonl(
        _subagent_file(root),
        [
            _assistant("msg_C", 9, timestamp="2026-10-01T12:00:04Z", sidechain=True),
            _assistant("msg_D", 5, timestamp="2026-10-01T12:00:06Z", sidechain=True),
        ],
    )

    messages, _ = _deduplicated(root)

    by_id = {message.message_id: message for message in messages}
    assert len(messages) == 2
    assert by_id["msg_C"].is_main is False
    assert by_id["msg_C"].peak.output_tokens == 9
    assert by_id["msg_C"].origin == datetime(2026, 10, 1, 12, 0, 4, tzinfo=UTC)
    assert by_id["msg_D"].is_main is False


def test_synthetic_and_unidentified_assistant_records_are_not_usage(tmp_path):
    root = tmp_path / "projects"
    _write_jsonl(
        _main_file(root),
        [
            _assistant(
                "msg_E", 30, timestamp="2026-10-01T13:00:00Z", model="<synthetic>"
            ),
            _assistant("", 30, timestamp="2026-10-01T13:00:01Z"),
            {"type": "user", "sessionId": SESSION, "message": {"content": "hello"}},
            _assistant("msg_F", 2, timestamp="2026-10-01T13:00:02Z"),
        ],
    )
    report = ReadReport()

    records = list(
        iter_usage_records(transcript_files(root, include_subagents=True), report)
    )

    assert [record.message_id for record in records] == ["msg_F"]


def test_torn_last_line_of_a_transcript_is_counted_and_earlier_usage_kept(tmp_path):
    root = tmp_path / "projects"
    path = _write_jsonl(
        _main_file(root),
        [_assistant("msg_G", 11, timestamp="2026-10-01T14:00:00Z")],
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"type": "assistant", "message": {"id": "msg_H", "usa')

    messages, report = _deduplicated(root)

    assert [message.message_id for message in messages] == ["msg_G"]
    assert report.torn_lines == 1
    assert report.files_read == 1


def test_equal_peak_outputs_bind_the_smaller_working_directory_in_either_order():
    first = _usage("msg_I", 40, cwd="/work/b")
    second = _usage("msg_I", 40, cwd="/work/a")

    for order in ([first, second], [second, first]):
        (message,) = deduplicate(order)
        assert message.peak.cwd == "/work/a"


def test_message_with_no_output_still_binds_a_record():
    (message,) = deduplicate(
        [_usage("msg_J", 0, cwd="/work/b"), _usage("msg_J", 0, cwd="/work/a")]
    )

    assert message.peak.output_tokens == 0
    assert message.peak.cwd == "/work/a"


def test_discovery_includes_subagent_transcripts_only_when_asked(tmp_path):
    # The root's own path contains a `subagents` directory; only directories
    # below the root decide whether a transcript is a subagent's.
    root = tmp_path / "subagents" / "projects"
    main = _write_jsonl(_main_file(root), [])
    subagent = _write_jsonl(_subagent_file(root), [])
    nested = _write_jsonl(
        root
        / PROJECT
        / SESSION
        / "subagents"
        / "workflows"
        / "wf_1"
        / "agent-b2.jsonl",
        [],
    )

    assert transcript_files(root, include_subagents=False) == [
        TranscriptFile(main, is_subagent=False)
    ]
    assert set(transcript_files(root, include_subagents=True)) == {
        TranscriptFile(main, is_subagent=False),
        TranscriptFile(subagent, is_subagent=True),
        TranscriptFile(nested, is_subagent=True),
    }


def test_discovery_without_a_root_reads_under_claude_config_dir(monkeypatch, tmp_path):
    home = tmp_path / "home"
    config = tmp_path / "alt-config"
    decoy = _write_jsonl(home / ".claude" / "projects" / PROJECT / "decoy.jsonl", [])
    wanted = _write_jsonl(config / "projects" / PROJECT / f"{SESSION}.jsonl", [])
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)

    # Positive control: without the variable, the home default is what is read.
    assert [t.path for t in transcript_files(include_subagents=True)] == [decoy]

    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))

    assert [t.path for t in transcript_files(include_subagents=True)] == [wanted]


def test_user_text_comes_from_string_content_and_from_text_blocks():
    string_form = {
        "type": "user",
        "message": {"role": "user", "content": "Plain prompt text"},
    }
    block_form = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {"type": "text", "text": "First block"},
                {"type": "tool_result", "tool_use_id": "t1", "content": "output"},
                {"type": "image", "source": {}},
                "not a block",
                {"type": "text", "text": "Second block"},
            ],
        },
    }

    assert text_blocks(string_form) == ["Plain prompt text"]
    assert text_blocks(block_form) == ["First block", "Second block"]


def test_records_without_message_content_have_no_text():
    assert text_blocks({"type": "user"}) == []
    assert text_blocks({"type": "user", "message": {"content": None}}) == []
