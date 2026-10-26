#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = []
# [tool.ty.environment]
# python-version = "3.14"
# ///

"""Bubble a teammate pane's "You should know" offer up to its team lead.

ADR 0028: an offer that Claude Code's builtin `cc-plugin-you-should-know` shows
in a teammate's pane is mail from that teammate to the session that leads it.
Until the messaging record exists, this hook is the interim carrier. It keeps
no store of its own. Everything it reads, Claude Code already writes:

- `~/.claude/teams/<team>/config.json`: `leadSessionId` and, per member,
  `name`, `agentId`, `tmuxPaneId`, `model`, `cwd`, `joinedAt`, `backendType`.
- `~/.claude/projects/<cwd-slug>/<session>.jsonl`: a teammate's transcript,
  whose first records carry `"teamName"` and `"agentName"`. That is the only
  place the teammate's own session id is written down; the spawn passes none.
- `~/.claude/plugins/store/cc-plugin-you-should-know_builtin-<hash>.json`:
  `sessions[]` keyed by session id with `tag` and a `view` of kind `offer`
  (`line`, `explanation`, `shownAt`) while the band shows, or `explained`
  (`line`, `text`) after the person asked for more. Cleared two prompts later.

Runs on PostToolUse in every session (UserPromptSubmit is not an action boundary
for this marketplace; see tests/test_instruction_delivery.py). Exits silently
unless the session leads a team with tmux-backed members. Forwarded offers are
remembered in the `@ysk_forwarded` option on the lead's own tmux pane, so they
live and die with the pane. A missing or unreadable store is reported, not
swallowed, whenever there is a teammate to report it for.

Layouts observed on Claude Code 2.1.296, 2026-10-12. Launched through uv at
the repository Python floor (ADR 0038).
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

FORWARDED_OPTION = "@ysk_forwarded"
FORWARDED_KEPT = 50
CLAUDE_DIR = Path("~/.claude")
STORE_PATTERN = "cc-plugin-you-should-know_builtin-*.json"
BODY_KINDS = {"offer": "explanation", "explained": "text"}
TRANSCRIPT_HEAD_BYTES = 32_000
JOIN_SLACK_S = 120.0


@dataclass(frozen=True)
class Member:
    name: str
    agent_id: str
    pane_id: str
    model: str
    cwd: str
    joined_at_ms: int


@dataclass(frozen=True)
class Offer:
    member: Member
    session_id: str
    tag: str
    line: str
    explanation: str
    shown_at: int
    key: str


# --- pure ---------------------------------------------------------------------


def lead_team(configs: Iterable[dict], session_id: str) -> dict | None:
    for cfg in configs:
        if isinstance(cfg, dict) and cfg.get("leadSessionId") == session_id:
            return cfg
    return None


def tmux_members(config: dict) -> list[Member]:
    members = []
    for m in config.get("members") or []:
        if not isinstance(m, dict) or m.get("backendType") != "tmux":
            continue
        joined = m.get("joinedAt")
        members.append(
            Member(
                name=str(m.get("name") or ""),
                agent_id=str(m.get("agentId") or ""),
                pane_id=str(m.get("tmuxPaneId") or ""),
                model=str(m.get("model") or ""),
                cwd=str(m.get("cwd") or ""),
                joined_at_ms=int(joined) if isinstance(joined, (int, float)) else 0,
            )
        )
    return members


def project_dir_name(cwd: str) -> str:
    """Claude Code's transcript directory for a working directory."""
    return re.sub(r"[/.]", "-", cwd)


def transcript_matches(head: bytes, team: str, member: Member) -> bool:
    """True when a transcript's first records name this team and this teammate.

    Parses the complete JSON lines in `head`; a trailing partial line is skipped.
    The first record carrying `teamName` decides, so a transcript that merely
    quotes another teammate's name later on cannot match.
    """
    for raw in head.split(b"\n")[:-1]:
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(record, dict) or "teamName" not in record:
            continue
        return record.get("teamName") == team and record.get("agentName") == member.name
    return False


def offers_in(
    store: dict,
    sessions: Iterable[tuple[Member, str]],
    forwarded: set[str],
) -> list[Offer]:
    by_session = {sid: m for m, sid in sessions}
    offers = []
    for entry in store.get("sessions") or []:
        if not isinstance(entry, dict):
            continue
        sid = entry.get("id")
        member = by_session.get(sid)
        view = entry.get("view")
        if member is None or not isinstance(view, dict):
            continue
        body_field = BODY_KINDS.get(view.get("kind"))
        if body_field is None:
            continue
        shown_at = view.get("shownAt")
        key = f"{sid}:{shown_at}"
        if key in forwarded:
            continue
        offers.append(
            Offer(
                member=member,
                session_id=str(sid),
                tag=str(entry.get("tag") or "You should know"),
                line=str(view.get("line") or ""),
                explanation=str(view.get(body_field) or ""),
                shown_at=int(shown_at) if isinstance(shown_at, (int, float)) else 0,
                key=key,
            )
        )
    return offers


def render(offers: Iterable[Offer]) -> str:
    parts = []
    for o in offers:
        m = o.member
        who = f"teammate {m.name} (pane {m.pane_id}, session {o.session_id}"
        if m.model:
            who += f", model {m.model}"
        if m.cwd:
            who += f", cwd {m.cwd}"
        who += ")"
        parts.append(
            f'Mail from {who}. Its side agent raised a "{o.tag}" offer that nobody '
            f"in that pane will read:\n{o.line}\n\n{o.explanation}".rstrip()
        )
    return "\n\n---\n\n".join(parts)


def parse_forwarded(text: str | None) -> set[str]:
    if not text:
        return set()
    return {tok for tok in text.split() if tok}


def format_forwarded(keys: Iterable[str]) -> str:
    seen: list[str] = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    return " ".join(seen[-FORWARDED_KEPT:])


# --- shell --------------------------------------------------------------------


def _claude_dir() -> Path:
    return CLAUDE_DIR.expanduser()


def _read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    return value if isinstance(value, dict) else None


def _team_configs() -> list[dict]:
    configs = []
    for path in sorted((_claude_dir() / "teams").glob("*/config.json")):
        cfg = _read_json(path)
        if cfg is not None:
            configs.append(cfg)
    return configs


def _member_session(team: str, member: Member) -> str | None:
    project = _claude_dir() / "projects" / project_dir_name(member.cwd)
    if not project.is_dir():
        return None
    floor = member.joined_at_ms / 1000.0 - JOIN_SLACK_S
    best: tuple[float, str] | None = None
    for path in project.glob("*.jsonl"):
        try:
            mtime = path.stat().st_mtime
            if mtime < floor:
                continue
            with path.open("rb") as fh:
                head = fh.read(TRANSCRIPT_HEAD_BYTES)
        except OSError:
            continue
        if transcript_matches(head, team, member) and (best is None or mtime > best[0]):
            best = (mtime, path.stem)
    return best[1] if best else None


def _store_path() -> Path | None:
    override = os.environ.get("SUPERVISEE_OFFERS_STORE")
    if override:
        return Path(override)
    matches = sorted((_claude_dir() / "plugins" / "store").glob(STORE_PATTERN))
    return matches[-1] if matches else None


def _tmux(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["tmux", *args], capture_output=True, text=True, timeout=3, check=False
        )
    except OSError, subprocess.SubprocessError:
        return None
    return result.stdout if result.returncode == 0 else None


def _emit(event: str, context: str) -> None:
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": context,
                }
            }
        )
    )
    sys.stdout.write("\n")


def _led_members(session_id: str) -> tuple[str, list[Member]]:
    """The team this session leads, as (team name, tmux-backed members)."""
    team = lead_team(_team_configs(), session_id) if session_id else None
    if team is None:
        return "", []
    return str(team.get("name") or ""), tmux_members(team)


def _context_for(session_id: str) -> str | None:
    """What the lead should be told on this call, or None for nothing."""
    team_name, members = _led_members(session_id)
    if not members:
        return None

    path = _store_path()
    store = _read_json(path) if path is not None else None
    if store is None:
        where = path or _claude_dir() / "plugins" / "store" / STORE_PATTERN
        return (
            f"supervisee-offers hook: the You-should-know plugin store at {where} "
            f"is missing or unreadable, so offers from {len(members)} teammate "
            "pane(s) cannot be forwarded. Check the store layout against ADR 0028."
        )

    sessions = []
    for m in members:
        sid = _member_session(team_name, m)
        if sid:
            sessions.append((m, sid))

    own_pane = os.environ.get("TMUX_PANE") or ""
    forwarded = (
        parse_forwarded(_tmux("show-options", "-pqv", "-t", own_pane, FORWARDED_OPTION))
        if own_pane
        else set()
    )
    offers = offers_in(store, sessions, forwarded)
    if not offers:
        return None
    if own_pane:
        _tmux(
            "set-option",
            "-p",
            "-t",
            own_pane,
            FORWARDED_OPTION,
            format_forwarded([*sorted(forwarded), *(o.key for o in offers)]),
        )
    return render(offers)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError, OSError:
        payload = {}
    event = str(payload.get("hook_event_name") or "PostToolUse")
    context = _context_for(str(payload.get("session_id") or ""))
    if context is not None:
        _emit(event, context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
