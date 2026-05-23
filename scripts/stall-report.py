#!/usr/bin/env python3
"""Report Claude Code session stalls.

A turn is "stalled" when the model receives a tool_result and then produces
zero assistant content (no text, no tool_use, no thinking) before Stop fires.
The signature, verified in the 2026-05-22 investigation, is:

  user[tool_result] event  →  (no intervening assistant content)  →  system[stop_hook_summary]

This script walks every JSONL under ~/.claude/projects/, applies that signature,
and prints stall details. Use --since / --days to bound the window.

Examples
--------
  scripts/stall-report.py                          # last 7 days, all projects
  scripts/stall-report.py --days 1                 # last 24 hours
  scripts/stall-report.py --project sillytavern    # only matching projects
  scripts/stall-report.py --since 2026-05-22T04:57:00Z --json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class Stall:
    session_id: str
    project_dir: str
    timestamp: str
    tool_name: str
    tool_command: str
    result_excerpt: str
    is_error: bool


def _has_assistant_content(event: dict) -> bool:
    msg = event.get("message")
    if not isinstance(msg, dict):
        return False
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(
        isinstance(c, dict) and c.get("type") in ("text", "tool_use", "thinking")
        for c in content
    )


def _get_tool_result(event: dict) -> dict | None:
    msg = event.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if not isinstance(content, list):
        return None
    for c in content:
        if isinstance(c, dict) and c.get("type") == "tool_result":
            return c
    return None


def _index_tool_uses(events: list[dict]) -> dict[str, tuple[str, str]]:
    """Build {tool_use_id: (tool_name, command_str)} for command-excerpt lookup."""
    out: dict[str, tuple[str, str]] = {}
    for e in events:
        if e.get("type") != "assistant":
            continue
        msg = e.get("message")
        if not isinstance(msg, dict):
            continue
        for c in msg.get("content") or []:
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            tu_id = c.get("id", "")
            inp = c.get("input") or {}
            cmd = inp.get("command", "") if isinstance(inp, dict) else ""
            out[tu_id] = (c.get("name", ""), str(cmd))
    return out


def _result_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                t = c.get("type", "")
                if t == "text":
                    parts.append(c.get("text", ""))
                else:
                    parts.append(f"[{t}]")
            else:
                parts.append(str(c))
        return " | ".join(parts)
    return str(content)


def find_stalls_in_file(path: Path) -> list[Stall]:
    """Walk a single JSONL session file and return stalls per the verified signature."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    events: list[dict] = []
    for line in text.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    tool_uses = _index_tool_uses(events)
    stalls: list[Stall] = []
    pending_tool_result: tuple[dict, dict] | None = None

    for e in events:
        et = e.get("type")

        if et == "assistant" and _has_assistant_content(e):
            pending_tool_result = None
            continue

        if et == "user":
            tr = _get_tool_result(e)
            if tr is not None:
                pending_tool_result = (e, tr)
            else:
                pending_tool_result = None
            continue

        if et == "system" and e.get("subtype") == "stop_hook_summary":
            if pending_tool_result is not None:
                event, tr = pending_tool_result
                tu_id = tr.get("tool_use_id", "")
                tool_name, tool_cmd = tool_uses.get(tu_id, ("?", ""))
                stalls.append(Stall(
                    session_id=event.get("sessionId", ""),
                    project_dir=path.parent.name,
                    timestamp=event.get("timestamp", ""),
                    tool_name=tool_name,
                    tool_command=tool_cmd[:200],
                    result_excerpt=_result_to_text(tr.get("content", ""))[:200],
                    is_error=bool(tr.get("is_error", False)),
                ))
            pending_tool_result = None
            continue

    return stalls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--since",
        help="ISO timestamp (e.g. 2026-05-22T04:57:00Z). Overrides --days.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Only include sessions modified within N days (default: 7).",
    )
    parser.add_argument(
        "--project",
        help="Substring match on project directory name.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable table.",
    )
    args = parser.parse_args(argv)

    if args.since:
        since_dt = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)
    since_iso = since_dt.isoformat()
    since_epoch = since_dt.timestamp()

    if not PROJECTS_DIR.exists():
        print(f"No project directory at {PROJECTS_DIR}", file=sys.stderr)
        return 1

    all_stalls: list[Stall] = []
    sessions_scanned = 0

    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        if args.project and args.project not in project_dir.name:
            continue
        for jsonl_path in sorted(project_dir.glob("*.jsonl")):
            try:
                if jsonl_path.stat().st_mtime < since_epoch:
                    continue
            except OSError:
                continue
            sessions_scanned += 1
            all_stalls.extend(find_stalls_in_file(jsonl_path))

    all_stalls = [s for s in all_stalls if s.timestamp >= since_iso]
    all_stalls.sort(key=lambda s: s.timestamp)

    if args.json:
        out = {
            "since": since_iso,
            "sessions_scanned": sessions_scanned,
            "total_stalls": len(all_stalls),
            "stalls": [asdict(s) for s in all_stalls],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print(f"Stalls since {since_iso}")
    print(f"Sessions scanned: {sessions_scanned}")
    print(f"Total stalls:     {len(all_stalls)}")
    print()

    if not all_stalls:
        return 0

    by_session: dict[str, list[Stall]] = {}
    for s in all_stalls:
        by_session.setdefault(s.session_id, []).append(s)

    print("Per-session counts:")
    for sid, ss in sorted(by_session.items(), key=lambda x: -len(x[1])):
        proj = ss[0].project_dir
        print(f"  {len(ss):>3}  {sid[:8]}…  {proj}")
    print()

    print("Stall details:")
    print(f"  {'TIMESTAMP':<24} {'TOOL':<8} {'ERR':<4} COMMAND")
    print("  " + "-" * 96)
    for s in all_stalls:
        cmd = s.tool_command.replace("\n", "↵")[:60]
        err = "yes" if s.is_error else " no"
        print(f"  {s.timestamp[:23]:<24} {s.tool_name:<8} {err:<4} {cmd}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
