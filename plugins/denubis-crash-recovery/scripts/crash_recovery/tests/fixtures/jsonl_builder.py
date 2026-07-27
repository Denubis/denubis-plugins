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
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from crash_recovery.jsonl import TailKind
from crash_recovery.liveness import current_boot_id

# Deterministic timestamp used across every fixture so ``last_ts`` is stable
# in assertions.
FIXED_TS = "2026-05-13T03:00:12.000Z"


def _snapshot_record() -> dict:
    """Return a snapshot/bookkeeping record carrying NO ``cwd`` and NO ``timestamp``.

    Mirrors the real shape modern Claude Code transcripts open with: top-level
    keys ``type, messageId, snapshot, isSnapshotUpdate`` with ``type`` value
    ``snapshot``. Because ``snapshot`` is not in ``_REAL_TYPES`` it is filtered
    out by :func:`crash_recovery.jsonl.parse_tail`, and because it carries no
    ``cwd``/``timestamp`` the line-1-only readers this phase replaces see an
    empty value here — the regression :func:`first_record_field` repairs.
    """
    return {
        "type": "snapshot",
        "messageId": "msg_snapshot_0001",
        "snapshot": {"messageIds": []},
        "isSnapshotUpdate": False,
    }


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
            {
                "type": "custom-title",
                "timestamp": FIXED_TS,
                "title": "Just bookkeeping",
            },
            {"type": "agent-name", "timestamp": FIXED_TS, "name": "Claude"},
            {"type": "permission-mode", "timestamp": FIXED_TS, "mode": "default"},
        ],
    )


def make_liveness_file(
    run_dir: Path,
    pid: int,
    cwd: str = "/tmp/test",
    started: int = 1715151234,
    argv: str | None = None,
    boot_id: str = "8b2f4a3d-6c0e-4f1a-9d2b-7e3c5a8b1c4d",
    session_id: str | None = None,
    start_time: int | None = None,
) -> Path:
    """Write a ``<pid>.live`` file under ``run_dir``; return the path.

    Mirrors the privacy-minimized format the wrapper writes: one ``key=value``
    line per field, UTF-8, newline-terminated. ``argv`` is emitted only when
    supplied to build a legacy marker; it may contain ``=`` signs.

    ``session_id`` and ``start_time`` are the optional Phase 2 additive keys.
    Each line is written ONLY when its value is provided, so callers that omit
    them get a current marker without legacy argv.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{pid}.live"
    lines = [
        f"cwd={cwd}\n",
        f"started={started}\n",
        f"boot_id={boot_id}\n",
    ]
    if argv is not None:
        lines.append(f"argv={argv}\n")
    if session_id is not None:
        lines.append(f"session_id={session_id}\n")
    if start_time is not None:
        lines.append(f"start_time={start_time}\n")
    path.write_text("".join(lines))
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


@dataclass
class FixtureSession:
    """High-level declarative spec for one session in a scan fixture.

    Combines a tail-shape choice (``tail_kind``) with optional liveness-file
    presence so :func:`make_full_fixture` can synthesise a complete
    ``(db, run_dir, projects_root)`` layout from a list of these.

    ``started_offset`` is added to ``time.time()`` at fixture-construction
    time; the default ``-3600`` makes the liveness ``started`` an hour in
    the past so correlate's mtime window (now > started - 60) admits the
    JSONL written immediately after.

    ``start_time`` is the optional Phase 2 ``start_time=`` marker key. Left
    ``None`` (the default) the marker omits the optional start time and
    ``pid_alive_checked`` falls back to bare ``kill -0``. Set it to a
    deliberately wrong value to drive the PID-reuse-rejection path (a marker
    whose stored start_time no longer matches ``/proc/<pid>/stat``).
    """

    uuid: str
    cwd: str
    tail_kind: TailKind
    has_liveness: bool
    pid_alive: bool | None
    boot_id_current: bool
    started_offset: int = -3600
    cwd_on_first_line: bool = True
    start_time: int | None = None


# Sentinel boot_id that will never match the kernel's value — used to
# drive the AC5.6 boot-mismatch-wins-over-pid-alive test path.
_NEVER_MATCH_BOOT_ID = "00000000-0000-0000-0000-000000000000"


def _pick_dead_pid() -> int:
    """Return a PID guaranteed not to be alive — now and for the whole run.

    Returns one greater than ``/proc/sys/kernel/pid_max``. The kernel never
    assigns a PID above that ceiling, so ``kill -0`` always raises
    ``ProcessLookupError`` → ``pid_alive`` returns ``False``.

    The previous implementation returned ``max(/proc PIDs) + 1`` — which is
    precisely the PID the kernel is about to hand to the next ``fork()``. On a
    busy test run (subprocess-spawning tests, concurrent ``uv`` invocations) a
    freshly-spawned process could claim that PID before the scan's liveness
    check ran, so a ``pid_alive=False`` session read as *live* — an
    order-dependent flake. A PID above ``pid_max`` can never collide.

    Fallback to ``2**22 + 1`` if ``pid_max`` isn't readable (non-Linux).
    """
    try:
        with Path("/proc/sys/kernel/pid_max").open() as f:
            return int(f.read().strip()) + 1
    except OSError, ValueError:
        return 2**22 + 1


def _iso_ts(epoch: int) -> str:
    """Return ``epoch`` as ISO-8601 UTC with millisecond precision."""
    return datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _tail_entries_for(kind: TailKind) -> list[dict]:
    """Return the JSONL entries that produce ``kind`` from ``parse_tail``.

    Used by :func:`_write_session_jsonl` to append tail-shape content
    after the leading cwd+timestamp header entry. Empty list means the
    file gets only the header (which by itself parses as UNKNOWN).
    """
    if kind is TailKind.CONCLUDED:
        return [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "done"}],
                },
            }
        ]
    if kind is TailKind.TOOL_USE_NO_RESULT:
        return [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_no_result_fixture",
                            "name": "Bash",
                            "input": {},
                        }
                    ],
                },
            }
        ]
    if kind is TailKind.ASK_QUESTION_NO_REPLY:
        return [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_ask_fixture",
                            "name": "AskUserQuestion",
                            "input": {"question": "?"},
                        }
                    ],
                },
            }
        ]
    if kind is TailKind.AGENT_DISPATCH_NO_RESULT:
        return [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_agent_fixture",
                            "name": "Task",
                            "input": {"prompt": "go"},
                        }
                    ],
                },
            }
        ]
    # UNKNOWN / EMPTY / MALFORMED_TAIL / MISSING_FILE: header alone yields
    # UNKNOWN from parse_tail. Tests that need EMPTY/MALFORMED would call
    # make_empty / make_malformed_tail directly rather than via FixtureSession.
    return []


def _write_session_jsonl(
    jsonl_path: Path,
    cwd: str,
    first_entry_epoch: int,
    tail_kind: TailKind,
    cwd_on_first_line: bool = True,
) -> None:
    """Write a session JSONL with a cwd+timestamp header plus tail-shape entries.

    The header satisfies correlate's first-entry-cwd lookup
    (:func:`_project_dir_for_cwd`) and mtime-window filter
    (:func:`_jsonl_first_entry_ts_in_tight_window`). The tail entries
    drive :func:`parse_tail`'s ``TailKind`` discrimination.

    When ``cwd_on_first_line`` is ``False`` a snapshot/bookkeeping record (no
    ``cwd``, no ``timestamp``) is prepended so the authoritative cwd+timestamp
    header lands on line 2 — the modern-transcript shape that the line-1-only
    readers mis-read and :func:`crash_recovery.jsonl.first_record_field`
    repairs.
    """
    iso = _iso_ts(first_entry_epoch)
    header = {
        "type": "user",
        "cwd": cwd,
        "timestamp": iso,
        "message": {"content": []},
    }
    prefix = [] if cwd_on_first_line else [_snapshot_record()]
    entries = [*prefix, header, *_tail_entries_for(tail_kind)]
    _write(jsonl_path, entries)


def make_snapshot_prefixed_jsonl(
    path: Path,
    cwd: str,
    first_ts: int,
    *,
    tail_kind: TailKind,
) -> None:
    """Write a snapshot-prefixed session JSONL (cwd+timestamp on line 2).

    Line order:

    1. a ``snapshot`` bookkeeping record with NO ``cwd`` and NO ``timestamp``
       (see :func:`_snapshot_record`);
    2. the first real record carrying ``cwd`` and ``timestamp``;
    3. the tail entries for ``tail_kind`` (see :func:`_tail_entries_for`).

    This is the fixture for the forward-scan ACs (AC2.1 / AC2.2): the line-1
    readers being replaced see the snapshot record and read no cwd/timestamp,
    while :func:`crash_recovery.jsonl.first_record_field` scans forward to the
    line-2 header.
    """
    _write_session_jsonl(
        path,
        cwd=cwd,
        first_entry_epoch=first_ts,
        tail_kind=tail_kind,
        cwd_on_first_line=False,
    )


def _encoded_dir_name_for(cwd: str) -> str:
    """Return a deterministic encoded directory name for ``cwd``.

    Claude Code's real encoding collapses ``/`` and ``.`` to ``-`` and is
    lossy. Tests only need a unique-per-cwd name that doesn't collide
    with other test fixtures; ``correlate`` never decodes the name (it
    reads the in-file ``cwd`` via :func:`_project_dir_for_cwd`).
    """
    # Strip leading slash so we don't produce a name starting with "-"
    # twice; map remaining "/" and "." to "-" to mimic the lossy encoding.
    stripped = cwd.lstrip("/")
    return "-" + stripped.replace("/", "-").replace(".", "-")


def make_full_fixture(
    tmp_path: Path,
    sessions: list[FixtureSession],
) -> tuple[Path, Path, Path]:
    """Build a ``(db_dir, run_dir, projects_root)`` layout from declared sessions.

    Returns absolute paths to three directories rooted at ``tmp_path``:

    * ``db_dir`` — empty parent dir; tests place their SQLite file here.
    * ``run_dir`` — populated with one ``<pid>.live`` file per session
      that requested ``has_liveness=True``.
    * ``projects_root`` — populated with one encoded-directory per
      distinct ``cwd``, each containing the session JSONLs that share
      that cwd.

    Sessions sharing a ``cwd`` land in the same encoded directory so
    AMBIGUOUS-correlation tests can drive multiple in-window candidates
    against one liveness file.

    Liveness semantics:

    * ``pid_alive=True`` → ``os.getpid()`` (the test process). ``kill -0``
      always succeeds against the test process.
    * ``pid_alive=False`` → :func:`_pick_dead_pid` (max-PID + 1). ``kill -0``
      yields ``ProcessLookupError`` → ``False``.
    * ``boot_id_current=True`` → :func:`current_boot_id` (real kernel value).
    * ``boot_id_current=False`` → :data:`_NEVER_MATCH_BOOT_ID` sentinel.

    Two sessions in the same fixture must use different ``pid_alive=False``
    PIDs to keep the resulting ``<pid>.live`` filenames distinct — we
    increment from ``_pick_dead_pid()`` for each dead PID allocated.

    Parameters
    ----------
    tmp_path
        pytest's ``tmp_path`` fixture (the per-test temp directory).
    sessions
        Declarative spec for each session. Order is not significant.

    Returns
    -------
    tuple[Path, Path, Path]
        ``(db_dir, run_dir, projects_root)`` as absolute paths.
    """
    db_dir = tmp_path / "db"
    run_dir = tmp_path / "run"
    projects_root = tmp_path / "projects"
    for d in (db_dir, run_dir, projects_root):
        d.mkdir(parents=True, exist_ok=True)

    # Group sessions by cwd so each unique cwd maps to one encoded dir.
    by_cwd: dict[str, list[FixtureSession]] = {}
    for session in sessions:
        by_cwd.setdefault(session.cwd, []).append(session)

    import time as _time

    now_epoch = int(_time.time())

    # Sequential dead PIDs so two has_liveness+pid_alive=False sessions
    # don't share a <pid>.live filename.
    dead_pid_base = _pick_dead_pid()
    dead_pid_counter = itertools.count(dead_pid_base)

    real_boot_id = current_boot_id()

    for cwd, cwd_sessions in by_cwd.items():
        project_dir = projects_root / _encoded_dir_name_for(cwd)
        project_dir.mkdir(parents=True, exist_ok=True)
        for session in cwd_sessions:
            # JSONL first-entry timestamp = now + started_offset so the
            # mtime-window filter (entry_ts >= started - 60) admits it.
            first_entry_epoch = now_epoch + session.started_offset + 1
            _write_session_jsonl(
                project_dir / f"{session.uuid}.jsonl",
                cwd=cwd,
                first_entry_epoch=first_entry_epoch,
                tail_kind=session.tail_kind,
                cwd_on_first_line=session.cwd_on_first_line,
            )

    # Now write liveness files (after JSONLs exist on disk, so the
    # mtime-window scan has everything to find).
    for session in sessions:
        if not session.has_liveness:
            continue
        pid = os.getpid() if session.pid_alive is True else next(dead_pid_counter)
        boot_id = real_boot_id if session.boot_id_current else _NEVER_MATCH_BOOT_ID
        started = now_epoch + session.started_offset
        # argv carries ``--resume <uuid>`` so correlate takes the DIRECT_MATCH
        # path — keeps fixtures unambiguous unless the test explicitly omits
        # this by constructing its own liveness file.
        make_liveness_file(
            run_dir=run_dir,
            pid=pid,
            cwd=session.cwd,
            started=started,
            argv=f"--resume {session.uuid}",
            boot_id=boot_id,
            start_time=session.start_time,
        )

    return db_dir, run_dir, projects_root


@dataclass
class DbFixtureRow:
    """Declarative spec for one ``sessions`` row inserted directly by tests.

    Used by :func:`make_db_with_sessions` to seed the DB without going through
    Phase 4's filesystem walk — render tests can then assert byte-level
    contracts against a known set of rows. All timestamp fields default to
    deterministic values so two test runs against the same fixture produce
    byte-identical render output.
    """

    uuid: str
    cwd: str
    classification: str
    classification_reason: str
    state_summary: str
    user_notes: str | None
    last_scanned: int
    first_seen: int
    classifier_version: int = 1
    project_path: str = "/decoded/project/path"
    jsonl_path: str = "/jsonl/path.jsonl"
    jsonl_mtime: int = 1_700_000_000
    jsonl_last_ts: int | None = 1_700_000_000
    pane_title: str | None = None
    last_substantive: str | None = None


def make_db_with_sessions(tmp_path: Path, sessions: list[DbFixtureRow]) -> Path:
    """Initialise a fresh DB under ``tmp_path`` and insert each ``DbFixtureRow``.

    Bypasses :mod:`crash_recovery.scan` so render-layer tests do not depend
    on Phase 4's filesystem walk. The DB is created via
    :func:`crash_recovery.db.init` (so WAL mode and CHECK constraints apply),
    then each row is inserted with an explicit ``INSERT INTO sessions``
    statement. Returns the path to the created DB so callers can pass it
    directly to :func:`crash_recovery.render.render`.
    """
    from crash_recovery import db as _db

    db_path = tmp_path / "render-fixture.db"
    _db.init(db_path)
    conn = _db.open_db(db_path)
    try:
        for session in sessions:
            conn.execute(
                """
                INSERT INTO sessions (
                    uuid, project_path, cwd, jsonl_path, jsonl_mtime, jsonl_last_ts,
                    classification, classification_reason, classifier_version,
                    state_summary, first_seen, last_scanned, user_notes,
                    pane_title, last_substantive
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.uuid,
                    session.project_path,
                    session.cwd,
                    session.jsonl_path,
                    session.jsonl_mtime,
                    session.jsonl_last_ts,
                    session.classification,
                    session.classification_reason,
                    session.classifier_version,
                    session.state_summary,
                    session.first_seen,
                    session.last_scanned,
                    session.user_notes,
                    session.pane_title,
                    session.last_substantive,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return db_path


def make_substantive_then_bookkeeping_tail(path: Path) -> None:
    """Real assistant text, then operator-leaked bookkeeping content turns.

    The last two *real* (assistant/user) turns carry content-level bookkeeping
    text — a ``<usage>`` block and a ``</task-notification>`` close — that the
    type-level ``_REAL_TYPES`` filter does NOT drop (they are genuine
    assistant/user turns whose *text* is operator noise). ``last_substantive_text``
    must walk past them to the prior real assistant turn and return its text.
    """
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "Here is the real answer."}],
                },
            },
            {
                "type": "user",
                "timestamp": FIXED_TS,
                "message": {
                    "content": "<usage>tokens: 1234</usage>",
                },
            },
            {
                "type": "user",
                "timestamp": FIXED_TS,
                "message": {
                    "content": "</task-notification>",
                },
            },
        ],
    )


def make_post_compaction_boilerplate_tail(path: Path) -> None:
    """Real assistant turn, then a post-compaction boilerplate user turn.

    The final real turn is the standard post-compaction notice whose text
    starts with ``If you need specific details from before compaction``.
    ``last_substantive_text`` must skip it and return the prior assistant text.
    """
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "Prior substantive turn."}],
                },
            },
            {
                "type": "user",
                "timestamp": FIXED_TS,
                "message": {
                    "content": (
                        "If you need specific details from before compaction, "
                        "ask me to recover them."
                    ),
                },
            },
        ],
    )


def make_only_bookkeeping_content_tail(path: Path) -> None:
    """Every real turn carries only bookkeeping content → no substantive text.

    Both turns are genuine assistant/user entries (so ``_REAL_TYPES`` keeps
    them) but their text is operator noise. ``last_substantive_text`` must
    return ``None`` because nothing in the window is substantive.
    """
    _write(
        path,
        [
            {
                "type": "assistant",
                "timestamp": FIXED_TS,
                "message": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "<summary>recap</summary>"}],
                },
            },
            {
                "type": "user",
                "timestamp": FIXED_TS,
                "message": {"content": "<task-notification>queued</task-notification>"},
            },
        ],
    )


def make_attachment_interleaved_then_concluded(path: Path) -> None:
    """Assistant tool_use → attachment (bookkeeping) → user tool_result
    → assistant end_turn.

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
