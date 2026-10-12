"""Behavioural tests for the supervisee-offers hook (ADR 0028).

The hook runs in a team lead's session. It finds the team whose
`leadSessionId` is its own session, takes the tmux-backed members, resolves
each member's session id from the transcript Claude Code wrote for it (the
first records carry `teamName` and `agentName`), reads the builtin "You should
know" plugin's store for those sessions, and hands any unforwarded offer to
the lead as additional context, attributed to the teammate. Forwarded offers
are remembered in a pane option on the lead's own pane so each arrives once.

Fixtures mirror the layouts observed on Claude Code 2.1.296 (2026-10-12):
`~/.claude/teams/<team>/config.json`, `~/.claude/projects/<cwd-slug>/*.jsonl`
and `~/.claude/plugins/store/cc-plugin-you-should-know_builtin-*.json`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = (
    REPO_ROOT / "plugins" / "denubis-external-agents" / "hooks" / "supervisee-offers.py"
)

LEAD = "e957317c-fbb3-4dca-a285-a15bbef6ea90"
TEAM = "session-e957317c"
CWD = "/media/brian/storage/people/Adela/melica/.worktrees/caller-spec"
SLUG = "-media-brian-storage-people-Adela-melica--worktrees-caller-spec"
SID = "b5f993dc-95d2-4062-805d-6b9131af6f70"
JOINED = 1791781638303

OFFER_VIEW = {
    "kind": "offer",
    "line": "The brief says uploads are remembered; the engine does not.",
    "explanation": "**Restarted jobs upload everything again**\n\n* detail",
    "shownAt": 1791766518447,
}


def _load():
    spec = importlib.util.spec_from_file_location("supervisee_offers", HOOK)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses resolves deferred annotations through sys.modules[__module__].
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


def _config(*members):
    return {
        "name": TEAM,
        "leadSessionId": LEAD,
        "members": [
            {
                "agentId": f"team-lead@{TEAM}",
                "name": "team-lead",
                "agentType": "team-lead",
                "tmuxPaneId": "leader",
                "cwd": CWD,
                "backendType": "in-process",
            },
            *members,
        ],
    }


def _member(name="gemini-files-2", pane="%35", model="opus", joined=JOINED):
    return {
        "agentId": f"{name}@{TEAM}",
        "name": name,
        "tmuxPaneId": pane,
        "model": model,
        "cwd": CWD,
        "joinedAt": joined,
        "backendType": "tmux",
        "isActive": True,
    }


def _transcript_line(agent_name, team=TEAM, sid=SID):
    return (
        json.dumps(
            {
                "isSidechain": False,
                "teamName": team,
                "agentName": agent_name,
                "type": "attachment",
                "cwd": CWD,
                "sessionId": sid,
                "version": "2.1.296",
            }
        )
        + "\n"
    )


def _store(*sessions):
    return {"sessions": list(sessions), "seen": [], "known": []}


# --- pure ---------------------------------------------------------------------


def test_lead_team_is_the_config_whose_lead_is_this_session(mod):
    other = {"name": "session-x", "leadSessionId": "x", "members": []}
    assert mod.lead_team([other, _config()], LEAD)["name"] == TEAM
    assert mod.lead_team([other], LEAD) is None
    assert mod.lead_team([], LEAD) is None


def test_only_tmux_backed_members_are_supervisees(mod):
    cfg = _config(_member(), {"name": "ghost", "backendType": "in-process"})
    members = mod.tmux_members(cfg)
    assert [m.name for m in members] == ["gemini-files-2"]
    m = members[0]
    assert (m.pane_id, m.model, m.cwd, m.joined_at_ms) == ("%35", "opus", CWD, JOINED)


def test_project_dir_name_matches_claude_code_slug(mod):
    assert mod.project_dir_name(CWD) == SLUG
    assert (
        mod.project_dir_name("/home/brian/people/Brian") == "-home-brian-people-Brian"
    )


def test_transcript_matches_on_team_and_agent_name(mod):
    me = mod.tmux_members(_config(_member()))[0]
    assert mod.transcript_matches(_transcript_line("gemini-files-2").encode(), TEAM, me)
    assert not mod.transcript_matches(
        _transcript_line("gemini-files").encode(), TEAM, me
    )
    assert not mod.transcript_matches(
        _transcript_line("gemini-files-2", team="session-other").encode(), TEAM, me
    )
    assert not mod.transcript_matches(b'{"type":"summary"}\n', TEAM, me)


def test_offer_is_attributed_to_the_teammate(mod):
    me = mod.tmux_members(_config(_member()))[0]
    store = _store(
        {"id": SID, "tag": "Heads up", "view": OFFER_VIEW},
        {"id": "someone-else", "tag": "Heads up", "view": OFFER_VIEW},
    )
    offers = mod.offers_in(store, [(me, SID)], forwarded=set())
    assert len(offers) == 1
    o = offers[0]
    assert o.member.name == "gemini-files-2"
    assert (o.tag, o.line, o.explanation) == (
        "Heads up",
        OFFER_VIEW["line"],
        OFFER_VIEW["explanation"],
    )
    assert o.key == f"{SID}:1791766518447"


def test_forwarded_offers_are_not_repeated(mod):
    me = mod.tmux_members(_config(_member()))[0]
    store = _store({"id": SID, "tag": "Heads up", "view": OFFER_VIEW})
    assert mod.offers_in(store, [(me, SID)], forwarded={f"{SID}:1791766518447"}) == []


def test_explained_view_is_forwarded_with_its_text(mod):
    me = mod.tmux_members(_config(_member()))[0]
    view = {
        "kind": "explained",
        "line": "A line.",
        "text": "**T**\n\nMore.",
        "shownAt": 5,
    }
    store = _store({"id": SID, "tag": "You should know", "view": view})
    assert [o.explanation for o in mod.offers_in(store, [(me, SID)], set())] == [
        "**T**\n\nMore."
    ]


def test_non_offer_views_are_ignored(mod):
    me = mod.tmux_members(_config(_member()))[0]
    for kind in ("asked", "explaining", "failed", "off", "making"):
        store = _store(
            {
                "id": SID,
                "tag": "Heads up",
                "view": {"kind": kind, "line": "x", "shownAt": 1},
            }
        )
        assert mod.offers_in(store, [(me, SID)], set()) == [], kind


def test_rendering_names_the_teammate_and_carries_the_body(mod):
    me = mod.tmux_members(_config(_member()))[0]
    store = _store({"id": SID, "tag": "Heads up", "view": OFFER_VIEW})
    text = mod.render(mod.offers_in(store, [(me, SID)], set()))
    for needle in ("gemini-files-2", "%35", SID, "opus", CWD, "Heads up"):
        assert needle in text
    assert OFFER_VIEW["line"] in text
    assert "Restarted jobs upload everything again" in text


def test_forwarded_set_round_trips_and_is_bounded(mod):
    keys = [f"s:{i}" for i in range(200)]
    back = mod.parse_forwarded(mod.format_forwarded(keys))
    assert back <= set(keys)
    assert len(back) == mod.FORWARDED_KEPT
    assert "s:199" in back
    assert mod.parse_forwarded("") == set()
    assert mod.parse_forwarded(None) == set()


# --- end-to-end through a fake HOME and a fake tmux --------------------------

FAKE_TMUX = """#!/usr/bin/env bash
# Fake tmux: keeps one pane option in a file; refuses anything else.
state="$FAKE_TMUX_STATE"
case "$1" in
  show-options) [ -f "$state" ] && cat "$state" ;;
  set-option) printf '%s' "${@: -1}" > "$state" ;;
  *) echo "fake tmux: unexpected $*" >&2; exit 1 ;;
esac
"""


@pytest.fixture
def home(tmp_path):
    """A HOME with one led team, its teammate's transcript, and a fake tmux."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tmux = bin_dir / "tmux"
    tmux.write_text(FAKE_TMUX)
    tmux.chmod(tmux.stat().st_mode | stat.S_IXUSR)

    team_dir = tmp_path / ".claude" / "teams" / TEAM
    team_dir.mkdir(parents=True)
    (team_dir / "config.json").write_text(json.dumps(_config(_member())))

    project = tmp_path / ".claude" / "projects" / SLUG
    project.mkdir(parents=True)
    (project / f"{SID}.jsonl").write_text(_transcript_line("gemini-files-2") * 3)
    # A sibling transcript from another teammate must not be confused with ours.
    (project / "11111111-aaaa-bbbb-cccc-222222222222.jsonl").write_text(
        _transcript_line("gemini-files", sid="1111")
    )

    (tmp_path / ".claude" / "plugins" / "store").mkdir(parents=True)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path),
        "TMUX_PANE": "%8",
        "FAKE_TMUX_STATE": str(tmp_path / "state.txt"),
    }
    return tmp_path, env


def _write_store(home_dir, *sessions):
    path = (
        home_dir
        / ".claude"
        / "plugins"
        / "store"
        / "cc-plugin-you-should-know_builtin-19776595df2c.json"
    )
    path.write_text(json.dumps(_store(*sessions)))
    return path


def _run(env, session_id=LEAD, event="PostToolUse"):
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"hook_event_name": event, "session_id": session_id}).encode(),
        env=env,
        capture_output=True,
        timeout=20,
    )
    out = result.stdout.decode()
    return (
        result.returncode,
        (json.loads(out) if out.strip() else None),
        result.stderr.decode(),
    )


def test_hook_is_silent_when_this_session_leads_no_team(home):
    home_dir, env = home
    _write_store(home_dir, {"id": SID, "tag": "Heads up", "view": OFFER_VIEW})
    code, parsed, err = _run(env, session_id="not-a-lead")
    assert (code, parsed, err) == (0, None, "")


def test_hook_is_silent_without_a_session_id(home):
    _, env = home
    code, parsed, err = _run(env, session_id="")
    assert (code, parsed, err) == (0, None, "")


def test_hook_forwards_a_teammates_offer_once(home):
    home_dir, env = home
    _write_store(home_dir, {"id": SID, "tag": "Heads up", "view": OFFER_VIEW})

    code, parsed, err = _run(env)
    assert code == 0, err
    assert parsed is not None
    out = parsed["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    assert OFFER_VIEW["line"] in out["additionalContext"]
    assert "gemini-files-2" in out["additionalContext"]
    assert "%35" in out["additionalContext"]

    code, parsed, err = _run(env)
    assert (code, parsed) == (0, None), err


def test_hook_event_name_follows_the_payload(home):
    home_dir, env = home
    _write_store(home_dir, {"id": SID, "tag": "Heads up", "view": OFFER_VIEW})
    _, parsed, _ = _run(env, event="Stop")
    assert parsed["hookSpecificOutput"]["hookEventName"] == "Stop"


def test_a_sibling_teammates_offer_is_not_attributed_to_ours(home):
    home_dir, env = home
    _write_store(home_dir, {"id": "1111", "tag": "Heads up", "view": OFFER_VIEW})
    code, parsed, err = _run(env)
    assert (code, parsed, err) == (0, None, "")


def test_missing_store_is_reported_when_there_are_teammates(home):
    _, env = home
    code, parsed, _ = _run(env)
    assert code == 0
    assert parsed is not None
    assert "store" in parsed["hookSpecificOutput"]["additionalContext"].lower()


def test_unreadable_store_is_reported_when_there_are_teammates(home):
    home_dir, env = home
    path = _write_store(home_dir)
    path.write_text("{not json")
    code, parsed, _ = _run(env)
    assert code == 0
    assert parsed is not None
    assert "store" in parsed["hookSpecificOutput"]["additionalContext"].lower()


def test_store_override_env_is_honoured(home, tmp_path):
    _, env = home
    alt = tmp_path / "alt.json"
    alt.write_text(
        json.dumps(_store({"id": SID, "tag": "Heads up", "view": OFFER_VIEW}))
    )
    code, parsed, err = _run(dict(env, SUPERVISEE_OFFERS_STORE=str(alt)))
    assert code == 0, err
    assert OFFER_VIEW["line"] in parsed["hookSpecificOutput"]["additionalContext"]
