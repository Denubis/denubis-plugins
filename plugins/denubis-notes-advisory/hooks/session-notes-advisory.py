#!/usr/bin/env python3
"""SessionStart hook (denubis-notes-advisory) — point the session at `.notes/`.

A reminder to read `.notes/` already exists in the global CLAUDE.md, and it is
ignored in practice. This hook does not repeat it louder. It supplies the three
facts a session cannot cheaply derive for itself, then names the skill that
does the work:

  - `.notes/` exists here, resolved at the **main repo root** — the parent of
    ``git rev-parse --git-common-dir``, never the worktree. A resolver keyed on
    the process cwd reports "no notes" from every worktree.
  - how many notes are in it, so "I found nothing" can be told apart from "I
    looked somewhere there was nothing to find".
  - where this session's transcript lives, so the advisor can read the purpose
    rather than be told it second-hand.

Silent by design where it cannot help: a project with no `.notes/` gets no
output at all.

**Fire log.** Each emitted advisory appends one row to
``~/.claude/notes-advisory/log/YYYY-MM-DD.jsonl``; set
``DENUBIS_NOTES_ADVISORY_LOG_DIR`` to override the directory. The log exists to
test whether a firing correlates with the session later invoking
``scanning-project-notes``, using that session's transcript as evidence.

**Portability.** Hooks run under whatever interpreter the user's machine
resolves, which may be stock 3.9 (repo CLAUDE.md, hooks carve-out). So:
``from __future__ import annotations`` keeps PEP 604 annotations off the
runtime path, and every ``except`` is a single class — never a tuple, which
ruff's pyupgrade would rewrite into the 3.14-only PEP 758 form.

**Stdin is read inside main().** ``test_hook_portability.py`` imports every
hook to execute its module body under a 3.9 canary. A module-level
``sys.stdin.read()`` would block that test until timeout instead of passing.

Contract: always exit 0. Any internal error is a stderr diagnostic, never a
non-zero exit, and never a partial line on stdout.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "scanning-project-notes"

# Sources where the session already has a purpose on record: the transcript
# holds the work so far, so the scan can run immediately. `fork` belongs here
# for the same reason `resume` does — a session started with --fork-session
# inherits the parent's transcript.
#
# Anything else defers to the first substantive request: a cold `startup`, and
# any source added upstream that we have not seen. Defaulting an unknown source
# to "dispatch now" would fire an advisor against a purpose nobody has stated,
# which returns generic noise; defaulting it to "defer" costs one turn.
_IMMEDIATE_SOURCES = frozenset({"compact", "resume", "clear", "fork"})

_GIT_TIMEOUT_S = 5
_LOG_DIR_ENV = "DENUBIS_NOTES_ADVISORY_LOG_DIR"
_LOG_LINE_MAX_BYTES = 4096
_TRUNCATION_MARKER = "[truncated]"
_TRUNCATION_ORDER = ("notes_dir", "source", "transcript_path", "session_id")


def _diag(message: str) -> None:
    """Write one diagnostic line to stderr. Never raises."""
    with contextlib.suppress(Exception):
        print("notes-advisory: " + message, file=sys.stderr)


def main_repo_root(start: Path) -> Path:
    """Return the main repository root for ``start``, or ``start`` itself.

    Keyed on ``--git-common-dir`` rather than ``--show-toplevel`` so that every
    worktree of a repo resolves to the same root. In the main checkout git
    answers with a relative ``.git``; in a worktree it answers with an absolute
    path into the main repo's ``.git``. Both cases resolve to the same parent.

    A directory outside any repository returns unchanged, so non-git projects
    still get their own `.notes/` found.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except OSError:
        return start
    except subprocess.SubprocessError:
        return start

    if result.returncode != 0:
        return start
    common = result.stdout.strip()
    if not common:
        return start

    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = start / common_path
    try:
        return common_path.resolve().parent
    except OSError:
        return start


def notes_dir_for(start: Path) -> Path | None:
    """Return the `.notes/` directory serving ``start``, or None if absent."""
    candidate = main_repo_root(start) / ".notes"
    try:
        return candidate if candidate.is_dir() else None
    except OSError:
        return None


def count_notes(notes_dir: Path) -> int:
    """Number of markdown notes directly in ``notes_dir``.

    Non-markdown strays do not count. A session told "43 notes" and shown 43
    frontmatter blocks can tell a complete read from a truncated one; an
    inflated count breaks that check.
    """
    try:
        return sum(1 for path in notes_dir.glob("*.md") if path.is_file())
    except OSError:
        return 0


def _attr(value: str) -> str:
    """Escape a value for use inside a double-quoted attribute."""
    return value.replace('"', "&quot;")


def build_context(
    notes_dir: Path,
    note_count: int,
    dispatch: str,
    transcript_path: str | None,
) -> str:
    """Render the injected context. Pure — the whole testable core lives here.

    The ``<notes-advisory …>`` header is the stable half of the contract; the
    prose below it is expected to be reworded without breaking anything.
    """
    attrs = [
        'dispatch="' + _attr(dispatch) + '"',
        'notes="' + str(note_count) + '"',
        'dir="' + _attr(str(notes_dir)) + '"',
    ]
    if transcript_path:
        attrs.append('transcript="' + _attr(transcript_path) + '"')

    if dispatch == "now":
        when = (
            "This session already has a purpose on record in the transcript "
            "above. Invoke the `" + SKILL_NAME + "` skill now."
        )
    else:
        when = (
            "Once it is clear what this session is for, invoke the `"
            + SKILL_NAME
            + "` skill. Not before — an advisor dispatched against an unknown "
            "purpose returns generic noise."
        )

    body = (
        "This project keeps durable notes in the directory above: prior "
        "failures, standing decisions, and facts the code does not reveal.\n\n"
        + when
        + " It dispatches an advisor that reads every note's frontmatter and "
        "searches this project's chat logs, then reports which notes bear on "
        "the work, what prior sessions already established, and whether any of "
        "it has gone stale.\n\n"
        "Consider whether any note covers what you are about to do, and "
        "whether it is still correct. If you have questions, pause and ask one "
        "pointed, critical, and specific question at a time.\n\n"
        "Read the notes themselves. `.notes/` is both hidden and gitignored, so "
        "rg skips it under --hidden alone and under --no-ignore alone, and a "
        "search here comes back clean whether or not the note exists."
    )

    return "<notes-advisory " + " ".join(attrs) + ">\n" + body + "\n</notes-advisory>"


def _payload_from_stdin() -> dict:
    """Parse the hook payload, degrading to {} on anything unexpected."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        loaded = json.loads(raw)
    except ValueError as err:
        _diag("JSON parse failed: " + str(err))
        return {}
    if not isinstance(loaded, dict):
        _diag("payload is not a JSON object")
        return {}
    return loaded


def _start_dir(payload: dict) -> Path:
    """The directory to resolve `.notes/` from: payload cwd, else process cwd."""
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        candidate = Path(cwd)
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            pass
    return Path.cwd()


def _log_dir() -> Path:
    """Return the daily fire-log directory, honoring the test override."""
    override = os.environ.get(_LOG_DIR_ENV)
    if override:
        return Path(override)
    return Path.home() / ".claude" / "notes-advisory" / "log"


def _encoded_log_line(row: dict) -> bytes:
    """Return one compact JSON line, truncating low-priority fields to fit."""
    bounded_row = row.copy()

    def encoded() -> bytes:
        return (
            json.dumps(bounded_row, sort_keys=True, separators=(",", ":")).encode()
            + b"\n"
        )

    line = encoded()
    for field in _TRUNCATION_ORDER:
        if len(line) <= _LOG_LINE_MAX_BYTES:
            return line
        value = bounded_row.get(field)
        if not isinstance(value, str) or not value:
            continue

        bounded_row[field] = _TRUNCATION_MARKER
        line = encoded()
        if len(line) > _LOG_LINE_MAX_BYTES:
            continue

        low = 0
        high = len(value)
        best = _TRUNCATION_MARKER
        while low <= high:
            kept = (low + high) // 2
            candidate = _TRUNCATION_MARKER + value[-kept:] if kept else best
            bounded_row[field] = candidate
            candidate_line = encoded()
            if len(candidate_line) <= _LOG_LINE_MAX_BYTES:
                best = candidate
                line = candidate_line
                low = kept + 1
            else:
                high = kept - 1
        bounded_row[field] = best

    if len(line) > _LOG_LINE_MAX_BYTES:
        raise ValueError("log row exceeds the 4096-byte write budget")
    return line


def _append_log_row(row: dict, timestamp: dt.datetime) -> None:
    """Append ``row`` to its UTC daily JSONL file with one ``O_APPEND`` write."""
    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / (timestamp.strftime("%Y-%m-%d") + ".jsonl")
    line = _encoded_log_line(row)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        written = os.write(descriptor, line)
    finally:
        os.close(descriptor)
    if written != len(line):
        raise OSError(f"short log write: {written} of {len(line)} bytes")


def main() -> int:
    payload = _payload_from_stdin()

    notes_dir = notes_dir_for(_start_dir(payload))
    if notes_dir is None:
        return 0

    payload_source = payload.get("source")
    source = payload_source if isinstance(payload_source, str) else None
    dispatch = "now" if source in _IMMEDIATE_SOURCES else "first-request"

    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        transcript_path = None

    payload_session_id = payload.get("session_id")
    session_id = payload_session_id if isinstance(payload_session_id, str) else None

    note_count = count_notes(notes_dir)
    context = build_context(
        notes_dir=notes_dir,
        note_count=note_count,
        dispatch=dispatch,
        transcript_path=transcript_path,
    )

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
        )
    )

    timestamp = dt.datetime.now(
        dt.timezone.utc  # noqa: UP017 - datetime.UTC is unavailable on Python 3.9
    )
    row = {
        "timestamp": timestamp.isoformat(),
        "session_id": session_id,
        "transcript_path": transcript_path,
        "source": source,
        "dispatch": dispatch,
        "note_count": note_count,
        "notes_dir": str(notes_dir),
    }
    try:
        _append_log_row(row, timestamp)
    except Exception as err:
        _diag("log write failed: " + str(err))
    return 0


if __name__ == "__main__":
    # Always exit 0: never block session start.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as err:
        _diag("unexpected error: " + str(err))
        raise SystemExit(0) from err
