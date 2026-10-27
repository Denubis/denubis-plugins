"""Claude Code transcripts: discovery, assistant usage, deduplication, user text.

Claude Code writes one transcript per session at ``<projects>/<project>/<id>.jsonl``
and each subagent's transcript under ``<project>/<id>/subagents/``, sometimes nested
further. It writes several assistant records per message as the response streams,
with growing output counts, and a subagent transcript replays the parent's
assistant records under the parent's message ids. Counting records therefore
overcounts; :func:`deduplicate` applies the token-estimator's audited rule, the only
deduplication rule this library offers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from denubis_agent_logs.records import iter_records
from denubis_agent_logs.roots import claude_projects_root
from denubis_agent_logs.timestamps import parse_timestamp

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable, Iterator, Mapping
    from datetime import datetime
    from pathlib import Path

    from denubis_agent_logs.records import JsonRecord, ReadReport

SUBAGENT_DIRECTORY = "subagents"
# Every assistant record carries `"type":"assistant"`; other lines are not parsed.
_ASSISTANT_NEEDLES = (b'"assistant"',)


@dataclass(frozen=True, slots=True)
class TranscriptFile:
    """A transcript path and whether it sits under a ``subagents`` directory."""

    path: Path
    is_subagent: bool


@dataclass(frozen=True, slots=True)
class UsageRecord:
    """The usage one assistant record reports for one message.

    ``is_main`` is false for a record in a subagent transcript or marked
    ``isSidechain``. Token fields that are absent or not integers read as 0.
    """

    message_id: str
    model: str
    session_id: str | None
    cwd: str | None
    timestamp: datetime | None
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    is_main: bool
    path: Path


@dataclass(frozen=True, slots=True)
class ClaudeMessage:
    """One message after deduplication across every record that carries its id.

    ``is_main`` is true when any record of the message is a main-thread record.
    ``origin`` is the earliest timestamp among the main-thread records when the
    message is main, otherwise among its subagent records; ``None`` when none of
    those records has a parseable timestamp. ``peak`` is the record holding the
    maximum output, and supplies the working directory, model, session and all four
    token fields.
    """

    message_id: str
    origin: datetime | None
    is_main: bool
    peak: UsageRecord


def transcript_files(
    root: str | os.PathLike[str] | None = None, *, include_subagents: bool
) -> list[TranscriptFile]:
    """Return every transcript under ``root``, sorted by path.

    ``root`` defaults to :func:`~denubis_agent_logs.roots.claude_projects_root`.
    Every ``*.jsonl`` file below it is a transcript, as in the token-estimator's
    discovery. A file is a subagent's when a directory named ``subagents`` lies
    between ``root`` and the file; the root's own path does not count. A missing
    root yields no transcripts.
    """
    base = claude_projects_root(root)
    found = []
    for path in sorted(base.rglob("*.jsonl")):
        is_subagent = SUBAGENT_DIRECTORY in path.relative_to(base).parts[:-1]
        if include_subagents or not is_subagent:
            found.append(TranscriptFile(path, is_subagent))
    return found


def usage_record(record: JsonRecord, transcript: TranscriptFile) -> UsageRecord | None:
    """Return the usage of one countable assistant record, else ``None``.

    A record counts when it is an assistant record whose message has a non-empty
    id and a model that does not contain ``synthetic``.
    """
    identity = _message_identity(record.data)
    if identity is None:
        return None
    message, message_id, model = identity
    usage = message.get("usage")
    tokens: Mapping[str, Any] = usage if isinstance(usage, dict) else {}
    data = record.data
    return UsageRecord(
        message_id=message_id,
        model=model,
        session_id=_text(data.get("sessionId")),
        cwd=_text(data.get("cwd")),
        timestamp=parse_timestamp(data.get("timestamp")),
        input_tokens=_count(tokens, "input_tokens"),
        cache_creation_input_tokens=_count(tokens, "cache_creation_input_tokens"),
        cache_read_input_tokens=_count(tokens, "cache_read_input_tokens"),
        output_tokens=_count(tokens, "output_tokens"),
        is_main=not (transcript.is_subagent or data.get("isSidechain") is True),
        path=record.path,
    )


def iter_usage_records(
    transcripts: Iterable[TranscriptFile], report: ReadReport
) -> Iterator[UsageRecord]:
    """Yield the usage of every countable assistant record in ``transcripts``.

    Lines without ``"assistant"`` are skipped unparsed; what could not be read is
    counted in ``report``.
    """
    for transcript in transcripts:
        for record in iter_records(
            [transcript.path], report, needles=_ASSISTANT_NEEDLES
        ):
            usage = usage_record(record, transcript)
            if usage is not None:
                yield usage


def deduplicate(records: Iterable[UsageRecord]) -> list[ClaudeMessage]:
    """Collapse usage records to one message per message id, in first-seen order.

    This is the token-estimator's audited rule (``estimate.collect_claude``): the
    maximum output per message id; main when any record is main; the origin from
    the counted partition. The peak record is the first record seen, replaced by any
    record with a larger output, or with an equal output and a working directory
    whose string sorts first. A record without a working directory compares as the
    string ``"None"``, and a peak without one is never replaced on a tie, exactly as
    in that rule.
    """
    tallies: dict[str, _Tally] = {}
    for record in records:
        tally = tallies.get(record.message_id)
        if tally is None:
            tally = tallies[record.message_id] = _Tally(peak=record)
        tally.add(record)
    return [tally.message() for tally in tallies.values()]


def text_blocks(record: Mapping[str, Any]) -> list[str]:
    """Return the text blocks of a record's message content.

    String content is one block. List content yields the ``text`` of each block
    whose type is ``text``, in order; tool results, images and other blocks carry no
    text here. Anything else yields no blocks.
    """
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    texts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                texts.append(text)
    return texts


@dataclass(slots=True)
class _Tally:
    peak: UsageRecord
    is_main: bool = False
    first_main: datetime | None = None
    first_subagent: datetime | None = None

    def add(self, record: UsageRecord) -> None:
        if record.is_main:
            self.is_main = True
            self.first_main = _earlier(self.first_main, record.timestamp)
        else:
            self.first_subagent = _earlier(self.first_subagent, record.timestamp)
        if _replaces_peak(self.peak, record):
            self.peak = record

    def message(self) -> ClaudeMessage:
        return ClaudeMessage(
            message_id=self.peak.message_id,
            origin=self.first_main if self.is_main else self.first_subagent,
            is_main=self.is_main,
            peak=self.peak,
        )


def _replaces_peak(peak: UsageRecord, candidate: UsageRecord) -> bool:
    if candidate.output_tokens != peak.output_tokens:
        return candidate.output_tokens > peak.output_tokens
    return peak.cwd is not None and str(candidate.cwd) < peak.cwd


def _earlier(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None or candidate < current:
        return candidate
    return current


def _message_identity(
    data: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str, str] | None:
    message = data.get("message")
    if data.get("type") != "assistant" or not isinstance(message, dict):
        return None
    message_id = message.get("id")
    model = message.get("model")
    if not isinstance(message_id, str) or not message_id:
        return None
    if not isinstance(model, str) or not model or "synthetic" in model:
        return None
    return message, message_id, model


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _count(tokens: Mapping[str, Any], key: str) -> int:
    value = tokens.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0
