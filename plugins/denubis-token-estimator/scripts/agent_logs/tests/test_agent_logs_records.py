"""Tolerant JSONL reading skips what it cannot parse and says how much it skipped."""

from __future__ import annotations

import re

from denubis_agent_logs.records import ReadReport, iter_records, summarise


def test_torn_last_line_is_skipped_and_counted(tmp_path):
    path = tmp_path / "session.jsonl"
    # A blank line is not torn; the unterminated final object is.
    path.write_bytes(b'{"n": 1}\n\n{"n": 2}\n{"n": 3, "trunc')
    report = ReadReport()

    got = [(record.line_number, record.data) for record in iter_records([path], report)]

    assert got == [(1, {"n": 1}), (3, {"n": 2})]
    assert report.torn_lines == 1
    assert report.files_read == 1
    assert report.unreadable == []


def test_json_values_that_are_not_objects_are_counted_and_not_yielded(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_bytes(b'[1, 2]\n"text"\n{"n": 1}\n')
    report = ReadReport()

    got = [record.data for record in iter_records([path], report)]

    assert got == [{"n": 1}]
    assert report.non_object_lines == 2
    assert report.torn_lines == 0


def test_unreadable_files_are_reported_and_the_readable_ones_still_read(tmp_path):
    directory = tmp_path / "a-directory.jsonl"
    directory.mkdir()
    missing = tmp_path / "vanished.jsonl"
    good = tmp_path / "good.jsonl"
    good.write_bytes(b'{"n": 1}\n')
    report = ReadReport()

    got = [record.data for record in iter_records([directory, missing, good], report)]

    assert got == [{"n": 1}]
    assert [entry.path for entry in report.unreadable] == [directory, missing]
    assert all(entry.error for entry in report.unreadable)
    assert report.files_read == 1


def test_prefilter_skips_lines_without_a_needle_before_parsing_them(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_bytes(
        b'{"type": "assistant", "n": 1}\n'
        b'{"type": "user", "n": 2}\n'
        b'{"type": "user", "torn\n'
        b'{"type": "assistant", "torn\n'
    )
    report = ReadReport()

    got = [
        record.data
        for record in iter_records([path], report, needles=(b'"assistant"',))
    ]

    assert got == [{"type": "assistant", "n": 1}]
    # Only the torn line carrying the needle was parsed, so only it is counted.
    assert report.torn_lines == 1


def test_invalid_utf8_is_replaced_rather_than_counted_as_torn(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_bytes(b'{"text": "caf\xe9"}\n')
    report = ReadReport()

    got = [record.data for record in iter_records([path], report)]

    assert got == [{"text": "caf�"}]
    assert report.torn_lines == 0


def test_summary_names_every_skip_count_and_each_unreadable_file(tmp_path):
    good = tmp_path / "good.jsonl"
    good.write_bytes(b'{"n": 1}\n')
    torn = tmp_path / "torn.jsonl"
    # Every count differs (2 files read, 3 torn, 4 non-object, 1 unreadable), so a
    # count reported in place of another is caught.
    torn.write_bytes(b'{"n": 2}\n{"a\n{"b\n{"c\n[1]\n[2]\n"x"\n7\n')
    missing = tmp_path / "vanished-file.jsonl"
    report = ReadReport()
    list(iter_records([good, torn, missing], report))

    text = summarise("Claude", report)

    assert text.endswith("\n")
    first, *rest = text.splitlines()
    assert "Claude" in first
    assert sorted(int(n) for n in re.findall(r"\d+", first)) == [1, 2, 3, 4]
    assert len(rest) == 1
    assert str(missing) in rest[0]
    assert report.unreadable[0].error in rest[0]
