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

import itertools
import json
from collections.abc import Sequence
from datetime import UTC, datetime
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


def make_only_bookkeeping_no_signal(path: Path) -> None:
    """File whose every entry is bookkeeping — no ``assistant`` or ``user`` entries.

    Edge case: the deny-list filter (Task 1) removes every entry, leaving an
    empty filtered window. The parser must walk that empty window without
    crashing and return ``UNKNOWN`` (it has no signal to interpret).
    Coherence-review L2 (2026-05-16) — no prior direct fixture for this case.
    """
    _write(
        path,
        [
            {"type": "system", "timestamp": FIXED_TS, "content": "boot"},
            {"type": "custom-title", "timestamp": FIXED_TS, "title": "Just bookkeeping"},
            {"type": "agent-name", "timestamp": FIXED_TS, "name": "Claude"},
            {"type": "permission-mode", "timestamp": FIXED_TS, "mode": "default"},
        ],
    )


def make_liveness_file(
    run_dir: Path,
    pid: int,
    cwd: str = "/tmp/test",
    started: int = 1715151234,
    argv: str = "",
    boot_id: str = "8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d",
) -> Path:
    """Write a four-key ``<pid>.live`` file under ``run_dir``; return the path.

    Mirrors the format Phase 8's wrapper patch will write: one ``key=value``
    line per required field, UTF-8, newline-terminated. ``argv`` may be empty
    (no resume flag in the parent invocation) and may contain ``=`` signs.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{pid}.live"
    path.write_text(
        f"cwd={cwd}\n"
        f"started={started}\n"
        f"argv={argv}\n"
        f"boot_id={boot_id}\n"
    )
    return path


# Counter used to keep encoded-dir names unique across calls within one test.
# Each call returns a different directory so callers can layer multiple
# projects under one projects_root without collisions.
_project_dir_counter = itertools.count(1)


def make_project_dir(
    projects_root: Path,
    cwd: str,
    uuids: Sequence[str],
    first_entry_ts: int = 1_715_151_234,
) -> Path:
    """Create a ``~/.claude/projects/<encoded>/`` directory with N session JSONLs.

    Each JSONL is named ``<uuid>.jsonl`` and starts with a single entry whose
    ``cwd`` and ``timestamp`` carry the supplied values — enough for both
    :func:`_project_dir_for_cwd` (which reads the first entry's ``cwd``) and
    :func:`correlate`'s mtime-window filter (which reads the first entry's
    ``timestamp``). The encoded directory name is opaque; correlate never
    decodes it (the codebase-verified note at the top of the phase file:
    Claude Code's encoding is lossy, so the canonical lookup is by reading
    the in-file ``cwd``).

    Parameters
    ----------
    projects_root
        The ``~/.claude/projects/`` analogue (callers pass ``tmp_path``).
    cwd
        Value written to every JSONL's first-entry ``cwd``.
    uuids
        One session UUID per JSONL to create.
    first_entry_ts
        Unix epoch (seconds) written into every JSONL's first-entry
        ``timestamp`` as an ISO-8601 UTC string. Default mirrors the
        liveness fixture's default ``started`` so happy-path tests don't
        need to pass anything.

    Returns
    -------
    Path
        The created project directory.
    """
    encoded = f"-encoded-project-{next(_project_dir_counter)}"
    project_dir = projects_root / encoded
    project_dir.mkdir(parents=True, exist_ok=True)
    iso_ts = datetime.fromtimestamp(first_entry_ts, tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    for uuid in uuids:
        jsonl = project_dir / f"{uuid}.jsonl"
        entry = {
            "type": "user",
            "cwd": cwd,
            "timestamp": iso_ts,
            "message": {"content": []},
        }
        jsonl.write_text(json.dumps(entry) + "\n")
    return project_dir


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
