#!/usr/bin/env python3
"""SessionStart hook (denubis-plan-and-execute) — keep the crash-recovery .live
marker's session_id= line pointed at the LIVE transcript across /clear rotation,
so correlate()'s exact match names the live work (ADR 0003).

Stdlib only (json, os, re, sys, pathlib, tempfile). Invoked as a SessionStart
command via plain `python3` (NOT `uv run`): the hook runs with arbitrary cwd and
must not depend on a uv project. Stdlib-only keeps that safe.

Contract (Phase 2b Task 1, revised 2026-06-17):
  - No-op + exit 0 unless CR_LIVE_FILE is set/non-empty AND names an existing
    file (never create a marker; never touch an unowned one). Checked BEFORE
    stdin is read, so the silent no-op paths stay silent.
  - Read stdin; json.loads. Parse failure -> ONE diagnostic line on stderr,
    exit 0 (never block session start).
  - Key off transcript_path, NOT the stdin session_id (the two are different
    namespaces; transcript_path is the live file by construction). No-op exit 0
    if it is not a non-empty str ending in .jsonl.
  - uuid = basename(transcript_path) without .jsonl. Validate against a UUID
    regex; a non-match -> stderr diagnostic + no-op exit 0 (clean replacement for
    the old sed shape-guard; also makes the `a&b` case a no-op).
  - Rewrite ONLY the session_id= line to session_id=<uuid>, preserving every
    other line, its order, and the file's trailing-newline convention
    byte-for-byte (notably start_time=, which drives PID-reuse rejection). If no
    session_id= line exists (legacy 4-key marker), append one. Exactly one
    session_id= line afterward.
  - Write atomically: temp file in the SAME directory, then os.replace. Clean up
    the temp file on any error. The marker is mutated ONLY by a successful
    os.replace.
  - ALWAYS exit 0. Any internal error -> stderr diagnostic + exit 0; never a
    partial write. Emit nothing on stdout.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

_SESSION_ID_LINE = re.compile(r"^session_id=.*$", re.MULTILINE)
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _diag(message: str) -> None:
    """Write one diagnostic line to stderr. Never raises."""
    with contextlib.suppress(Exception):
        print(f"update-live-marker: {message}", file=sys.stderr)


def rewritten_marker(text: str, uuid: str) -> str:
    """Return the marker text with its session_id= line set to ``uuid``.

    Pure function. Rewrites ONLY the session_id= line, preserving every other
    line, its order, and the trailing-newline convention byte-for-byte. If no
    session_id= line exists, appends ``session_id=<uuid>\\n`` (ensuring the file
    ends in a newline first). Exactly one session_id= line afterward.
    """
    if _SESSION_ID_LINE.search(text):
        return _SESSION_ID_LINE.sub(f"session_id={uuid}", text, count=1)
    suffix = "" if text == "" or text.endswith("\n") else "\n"
    return f"{text}{suffix}session_id={uuid}\n"


def _atomic_write(marker: Path, content: str) -> None:
    """Write ``content`` to ``marker`` atomically via a same-dir temp + replace.

    The marker is mutated solely by os.replace. The temp file is cleaned up on
    any error so no partial write can survive. The marker's existing permission
    bits are carried onto the temp file before the replace, so the inode swap
    does not silently narrow the mode from the wrapper's value to mkstemp's 0600.
    """
    original_mode = marker.stat().st_mode
    fd, tmp_name = tempfile.mkstemp(
        dir=marker.parent, prefix=f"{marker.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
        tmp_path.chmod(original_mode)
        tmp_path.replace(marker)
    except Exception:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise


def main() -> int:  # noqa: PLR0911  # guard clauses; each early return is a documented no-op contract
    # 1. No-op unless CR_LIVE_FILE is set/non-empty and names an existing file.
    #    Checked before stdin is read, so silent no-op paths stay silent.
    live = os.environ.get("CR_LIVE_FILE") or ""
    if not live:
        return 0
    marker = Path(live)
    if not marker.is_file():
        return 0

    # 2. Read stdin and parse JSON. Parse failure -> diagnostic + exit 0.
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError) as err:
        _diag(f"JSON parse failed: {err}")
        return 0
    if not isinstance(payload, dict):
        _diag("payload is not a JSON object")
        return 0

    # 3. Key off transcript_path. No-op if not a non-empty .jsonl str.
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path.endswith(".jsonl"):
        return 0

    # 4. uuid = basename without .jsonl. Validate the shape; reject otherwise.
    uuid = Path(transcript_path).name[: -len(".jsonl")]
    if not _UUID.match(uuid):
        _diag(f"transcript_path basename is not a UUID: {uuid!r}")
        return 0

    # 5. Rewrite ONLY the session_id= line, atomically.
    try:
        text = marker.read_text()
        _atomic_write(marker, rewritten_marker(text, uuid))
    except OSError as err:
        _diag(f"marker rewrite failed: {err}")
        return 0

    return 0


if __name__ == "__main__":
    # Always exit 0: never block session start. Any unexpected error is a
    # diagnostic, not a non-zero exit.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as err:
        _diag(f"unexpected error: {err}")
        raise SystemExit(0) from err
