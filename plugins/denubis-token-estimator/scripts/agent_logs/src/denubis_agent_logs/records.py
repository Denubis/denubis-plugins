"""Tolerant JSONL iteration that reports what it could not read.

Session logs are appended while they are read, so the last line of a live file may
be torn, and a file may vanish between discovery and reading. Neither stops a pass:
the line or file is skipped and counted in a :class:`ReadReport`, so a consumer can
say how much it could not read instead of reporting a silently smaller total.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class UnreadableFile:
    """A file that could not be opened or read to its end, with the reason."""

    path: Path
    error: str


@dataclass(slots=True)
class ReadReport:
    """What a pass over JSONL files read, and what it had to skip.

    ``files_read`` counts files read to their end. ``torn_lines`` counts lines that
    were parsed and were not valid JSON; ``non_object_lines`` counts valid JSON
    lines whose value is not an object. Blank lines are neither.
    """

    files_read: int = 0
    torn_lines: int = 0
    non_object_lines: int = 0
    unreadable: list[UnreadableFile] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class JsonRecord:
    """One JSON object from one line of a JSONL file; lines are numbered from 1."""

    path: Path
    line_number: int
    data: dict[str, Any]


def iter_records(
    paths: Iterable[Path],
    report: ReadReport,
    *,
    needles: Sequence[bytes] = (),
) -> Iterator[JsonRecord]:
    """Yield every JSON object line in ``paths``, counting what is skipped.

    When ``needles`` is given, a line containing none of them is skipped before it
    is parsed, as the token-estimator's passes do. Such a line is never counted, even
    when it is torn: the prefilter trades that visibility for not parsing every line
    of a multi-gigabyte store. Bytes that are not UTF-8 are replaced, not rejected,
    matching a text-mode read with ``errors="replace"``.
    """
    for path in paths:
        yield from _file_records(path, report, needles)


def summarise(source: str, report: ReadReport) -> str:
    """Return text for stderr saying how much of ``source``'s logs a pass read.

    One line gives the files read and the torn lines, non-object lines and
    unreadable files skipped; one further line names each unreadable file and its
    error.
    """
    lines = [
        f"{source} logs: {report.files_read:,} files read; skipped "
        f"{report.torn_lines:,} torn lines, {report.non_object_lines:,} non-object "
        f"lines and {len(report.unreadable):,} unreadable files\n"
    ]
    lines.extend(
        f"  unreadable: {entry.path}: {entry.error}\n" for entry in report.unreadable
    )
    return "".join(lines)


def _file_records(
    path: Path, report: ReadReport, needles: Sequence[bytes]
) -> Iterator[JsonRecord]:
    try:
        with path.open("rb") as handle:
            for line_number, raw in enumerate(handle, start=1):
                data = _parse_line(raw, report, needles)
                if data is not None:
                    yield JsonRecord(path, line_number, data)
    except OSError as error:
        report.unreadable.append(UnreadableFile(path, str(error)))
        return
    report.files_read += 1


def _parse_line(
    raw: bytes, report: ReadReport, needles: Sequence[bytes]
) -> dict[str, Any] | None:
    if needles and not any(needle in raw for needle in needles):
        return None
    if not raw.strip():
        return None
    try:
        value = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError:
        report.torn_lines += 1
        return None
    if not isinstance(value, dict):
        report.non_object_lines += 1
        return None
    return value
