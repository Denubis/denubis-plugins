"""JSONL fixture builders for parse_tail tests.

Each helper writes a minimal sequence of JSON-lines to ``path`` that mimics
the shape Phase 2B confirmed in real Claude Code session logs: top-level
``type`` discriminator, ``message.stop_reason`` on assistant entries,
``message.content[].type`` for tool dispatch, and ``tool_use_id`` matching
on user tool_results. Timestamps are deterministic UTC strings.

The helpers are deliberately tiny: each one writes the smallest entry set
that lets ``parse_tail`` discriminate the corresponding ``TailKind``. They
do not attempt to reproduce a complete real-world session — only the
load-bearing shape.
"""

from __future__ import annotations

import json
from pathlib import Path

# Deterministic timestamp used across every fixture so ``last_ts`` is stable
# in assertions.
FIXED_TS = "2026-05-13T03:00:12.000Z"


def _write(path: Path, entries: list[dict]) -> None:
    """Write each entry on its own line as JSON."""
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))


def make_concluded(path: Path) -> None:
    """Assistant entry with stop_reason=end_turn and text-only content."""
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "done"}],
                },
            }
        ],
    )


def make_tool_use_no_result(path: Path, tool_name: str = "Bash") -> None:
    """Assistant tool_use dispatch with no matching user tool_result."""
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_no_result_001",
                            "name": tool_name,
                            "input": {},
                        }
                    ],
                },
            }
        ],
    )


def make_ask_question_no_reply(path: Path) -> None:
    """Assistant AskUserQuestion dispatch with no answers follow-up."""
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_ask_001",
                            "name": "AskUserQuestion",
                            "input": {"question": "?"},
                        }
                    ],
                },
            }
        ],
    )


def make_agent_dispatch_no_result(path: Path) -> None:
    """Assistant Task dispatch with no follow-up tool_result."""
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_agent_001",
                            "name": "Task",
                            "input": {"prompt": "go"},
                        }
                    ],
                },
            }
        ],
    )


def make_empty(path: Path) -> None:
    """Create an empty file."""
    path.write_text("")


def make_malformed_tail(path: Path) -> None:
    """Three valid entries followed by a line that is not valid JSON."""
    valid = [
        {"type": "assistant", "timestamp": FIXED_TS, "message": {"content": []}},
        {"type": "user", "timestamp": FIXED_TS, "message": {"content": []}},
        {"type": "assistant", "timestamp": FIXED_TS, "message": {"content": []}},
    ]
    body = "".join(json.dumps(e) + "\n" for e in valid)
    body += "{this is not valid json\n"
    path.write_text(body)


def make_ask_question_answered_by_answers(path: Path) -> None:
    """Assistant AskUserQuestion dispatch followed by a user answers entry.

    Pins the ``_has_ask_question_answer`` satisfaction path in ``parse_tail``:
    when a user entry carries ``toolUseResult.answers``, the AskUserQuestion
    is considered answered and must NOT produce ASK_QUESTION_NO_REPLY.
    Added during Phase 2 review (Minor 1 finding).
    """
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_ask_answered_001",
                            "name": "AskUserQuestion",
                            "input": {"question": "Which option?"},
                        }
                    ],
                },
            },
            {
                "type": "user",
                "timestamp": FIXED_TS,
                "toolUseResult": {
                    "answers": [{"inputName": "answer", "inputValue": "option A"}]
                },
            },
        ],
    )


def make_bookkeeping_only_tail(path: Path) -> None:
    """Assistant end_turn entry followed by 4 bookkeeping entries.

    Types ``custom-title``, ``agent-name``, ``agent-color``, and
    ``permission-mode`` were observed at real session tails on 2026-05-16.
    The original allow-list filter did not record these types, so it would
    have walked back through them and mis-classified the session as UNKNOWN.
    The deny-list approach (_REAL_TYPES) correctly filters them out, leaving
    the ``assistant`` end_turn entry as the last real signal → CONCLUDED.
    """
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "done"}],
                },
            },
            {"type": "custom-title", "timestamp": FIXED_TS, "title": "My session"},
            {"type": "agent-name", "timestamp": FIXED_TS, "name": "Claude"},
            {"type": "agent-color", "timestamp": FIXED_TS, "color": "#abc"},
            {"type": "permission-mode", "timestamp": FIXED_TS, "mode": "default"},
        ],
    )


def make_attachment_interleaved_then_concluded(path: Path) -> None:
    """Assistant tool_use → attachment (bookkeeping) → user tool_result → assistant end_turn.

    The parser must not classify this as TOOL_USE_NO_RESULT just because an
    attachment sits between the dispatch and the result. The last meaningful
    assistant entry is a clean ``end_turn`` so the tail is CONCLUDED.
    """
    tool_id = "toolu_interleave_001"
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "Bash",
                            "input": {},
                        }
                    ],
                },
            },
            {
                "type": "attachment",
                "timestamp": FIXED_TS,
                "data": {"hook": "hook_success"},
            },
            {
                "type": "user",
                "timestamp": FIXED_TS,
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": "ok",
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "done"}],
                },
            },
        ],
    )
