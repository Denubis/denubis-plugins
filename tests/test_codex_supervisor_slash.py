"""Slash commands are typed into the composer, never handed to codex as work.

The supervisor exposes dedicated verbs for slash commands. A message containing a
slash command is still a message, so it cannot establish that the TUI ran the command.

Most fixtures below were captured from pane %55 on 2026-08-01, codex v0.144.5, at 90
columns. Current named-title fixtures were captured from v0.152.0. Three properties of
the real TUI drive the design:

The composer opens a completion list on `/`, and a *partial* command leaves the wrong
entry selected: typing `/c` lists `/compact`, `/copy`, `/clear` in that order with
`/compact` highlighted, so Enter would compact a pane you meant to clear. Typing the
command in full narrows the list to exactly one entry.

Current pane titles carry a mutable thread name rather than a session id. A fresh
`/status` panel still exposes the immutable id: `/clear` rotates it and `/compact`
leaves it alone, which is what tells the two apart afterwards rather than an absence
check over the transcript.

The footer carries `Context N% left`, which is the meter the operator ruling says to
read in place of codex's own claim. It is truncated at the pane width, so a narrower
pane showed `Context 50% …` with the word `left` cut off.
"""

from __future__ import annotations

import calendar
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-external-agents"
    / "scripts"
    / "codex_supervisor.py"
)

_CURSOR = "\N{SINGLE RIGHT-POINTING ANGLE QUOTATION MARK}"

# The pane title before and after a `/clear`, verbatim. The second lost its `weekly`
# segment while codex restarted, which is why the id is found by its shape rather than
# by counting separators.
_TITLE_BEFORE_CLEAR = (
    "Ready | brian-ed3d-plugins | extract-denubis-academic | weekly 99% left | "
    "019fbc55-f624-7b50-a0ae-6f3cc5ffce64 | gpt-5.6-sol xhigh"
)
_TITLE_AFTER_CLEAR = (
    "⠋ Starting | brian-ed3d-plugins | extract-denubis-academic | "
    "019fbc57-05eb-7d33-b188-4e3740a4f53d | gpt-5.6-sol xhigh"
)
_TITLE_AFTER_CLEAR_READY = (
    "Ready | brian-ed3d-plugins | extract-denubis-academic | weekly 99% left | "
    "019fbc57-05eb-7d33-b188-4e3740a4f53d | gpt-5.6-sol xhigh"
)
_TITLE_WORKING = (
    "⠋ Working | brian-ed3d-plugins | extract-denubis-academic | weekly 99% left | "
    "019fbc55-f624-7b50-a0ae-6f3cc5ffce64 | gpt-5.6-sol xhigh"
)
_NAMED_TITLE_READY = (
    "Ready | brian-ed3d-plugins | main | Verify supervising plugin session | "
    "gpt-5.6-sol xhigh"
)
_ID_BEFORE = "019fbc55-f624-7b50-a0ae-6f3cc5ffce64"
_ID_AFTER = "019fbc57-05eb-7d33-b188-4e3740a4f53d"

# The composer's faint placeholder and the footer, with their real escape sequences.
# The footer's truecolor runs matter: `38;2;242;181;144` carries a literal 2 that means
# colour space, not faint, and reading it as faint would drop the meter entirely.
_EMPTY_COMPOSER = (
    f"\x1b[1m{_CURSOR}\x1b[0m\x1b[48;5;238m "
    "\x1b[2mImprove documentation in @filename\x1b[0m\x1b[48;5;238m"
)


def _footer(percent: int) -> str:
    return (
        "\x1b[49m  \x1b[38;2;233;144;169mweekly 99% left\x1b[2m\x1b[39m · "
        "\x1b[0m\x1b[38;2;171;223;167mbrian-ed3d-plugins\x1b[2m\x1b[39m · "
        "\x1b[0m\x1b[38;2;143;179;239mextract-denubis-academic\x1b[2m\x1b[39m · "
        f"\x1b[0m\x1b[38;2;242;181;144mContext {percent}% left\x1b[2m\x1b[39m · "
        "\x1b[0m\x1b[38;2;200;169;238mR…"
    )


def _pane(*, percent: int = 96, body: list[str] | None = None) -> str:
    """A Ready pane with an empty composer, a transcript, and the footer meter."""
    lines = [
        "╭─────╮",
        "│ >_ OpenAI Codex (v0.144.5) │",
        "╰─────╯",
        "",
        *(body if body is not None else ["• acknowledged"]),
        "",
        _EMPTY_COMPOSER,
        "",
        _footer(percent),
    ]
    return "\n".join(lines)


# Captured after `tmux send-keys -l '/clear'`: the list has narrowed to one entry and
# the composer holds the whole command. The footer is replaced by the list while it is
# open, which is why the meter is read before typing rather than after.
_TYPED_CLEAR = "\n".join(
    [
        "• acknowledged",
        "",
        f"\x1b[1m{_CURSOR}\x1b[0m\x1b[48;5;238m /clear",
        "",
        "\x1b[49m  \x1b[1m\x1b[38;5;6m/clear  clear the terminal and start a new "
        "chat\x1b[0m",
    ]
)

# Captured after typing only `/c`. `/compact` is highlighted, so Enter here compacts a
# pane the supervisor meant to clear.
_TYPED_AMBIGUOUS = "\n".join(
    [
        "• acknowledged",
        "",
        f"\x1b[1m{_CURSOR}\x1b[0m\x1b[48;5;238m /c",
        "",
        "\x1b[49m  \x1b[1m\x1b[38;5;6m/compact  summarize conversation to prevent "
        "hitting the context limit\x1b[0m",
        "  /\x1b[1mc\x1b[0mopy     \x1b[2mcopy last response as markdown\x1b[0m",
        "  /\x1b[1mc\x1b[0mlear    \x1b[2mclear the terminal and start a new "
        "chat\x1b[0m",
    ]
)

_TYPED_COMPACT = "\n".join(
    [
        "• acknowledged",
        "",
        f"\x1b[1m{_CURSOR}\x1b[0m\x1b[48;5;238m /compact",
        "",
        "\x1b[49m  \x1b[1m\x1b[38;5;6m/compact  summarize conversation to prevent "
        "hitting the context limit\x1b[0m",
    ]
)

# Typing `/status` in full does NOT narrow the list, because `/statusline` shares the
# prefix. The selected entry is drawn bold and coloured with its description intact,
# while the rest keep theirs faint, which is what tells the highlight from its
# neighbours
# when narrowing cannot. Captured from pane %58 on 2026-08-01.
_TYPED_STATUS = "\n".join(
    [
        "• acknowledged",
        "",
        f"\x1b[1m{_CURSOR}\x1b[0m\x1b[48;5;238m /status",
        "",
        "\x1b[49m  \x1b[1m\x1b[38;5;6m/status      show current session configuration "
        "and token usage\x1b[0m",
        "  /\x1b[1mstatus\x1b[0mline  \x1b[2mconfigure which items appear in "
        "the status line\x1b[0m",
    ]
)

# Codex v0.157.0 draws the selected entry in reverse video behind the prompt marker,
# with no leading indent, and sits the composer below the list. Lines verbatim from
# `tmux capture-pane -p -e` at 180x45 on 2026-09-28 (/tmp/diag-status-0157/).
_V157_COMPOSER = f"\x1b[1m{_CURSOR}\x1b[0m /status"
_V157_TYPED_STATUS = "\n".join(
    [
        f"\x1b[1;7m{_CURSOR} /status      \x1b[0;7mshow current session configuration "
        "and token usage\x1b[1m",
        "\x1b[0m  /\x1b[1mstatus\x1b[0mline  \x1b[2mconfigure which items appear in "
        "the status line\x1b[0m",
        "",
        _V157_COMPOSER,
    ]
)
_V157_TYPED_CLEAR = "\n".join(
    [
        f"\x1b[1;7m{_CURSOR} /clear  \x1b[0;7mclear the terminal and start a new "
        "chat\x1b[1m",
        "",
        f"\x1b[0;1m{_CURSOR}\x1b[0m /clear",
    ]
)
# Typing only `/c` on v0.157.0 highlights `/compact`, as it did on v0.144.5.
_V157_TYPED_AMBIGUOUS = "\n".join(
    [
        f"\x1b[1;7m{_CURSOR} /compact  \x1b[0;7msummarize conversation to prevent "
        "hitting the context limit\x1b[1m",
        "\x1b[0m  /\x1b[1mc\x1b[0mopy     \x1b[2mcopy the last response or part of "
        "it\x1b[0m",
        "  /\x1b[1mc\x1b[0md       \x1b[2mchange the current working directory\x1b[0m",
        "  /\x1b[1mc\x1b[0mlear    \x1b[2mclear the terminal and start a new "
        "chat\x1b[0m",
        "",
        f"\x1b[1m{_CURSOR}\x1b[0m /c",
    ]
)

# The panel `/status` draws, verbatim from pane %58 apart from the account address.
# Two weekly limits are reported and only the first is the one the quota check is about.
_STATUS_PANEL = [
    "╭──────────────────────────────────────────────────────────────────╮",
    "│  >_ OpenAI Codex (v0.144.5)                                      │",
    "│                                                                  │",
    "│ Visit https://chatgpt.com/codex/settings/usage for up-to-date    │",
    "│ information on rate limits and credits                           │",
    "│                                                                  │",
    "│  Model:                    gpt-5.6-sol (reasoning xhigh)         │",
    "│  Account:                  someone@example.edu.au (Pro)          │",
    "│  Session:                  019fbcac-3c93-7250-b008-0e3236f2809a  │",
    "│                                                                  │",
    "│  Weekly limit:             [██████████] 99% left                 │",
    "│                            (resets 14:41 on 8 Aug)               │",
    "│  GPT-5.3-Codex-Spark Weekly limit: [██████████] 100% left        │",
    "│                            (resets 19:33 on 8 Aug)               │",
    "╰──────────────────────────────────────────────────────────────────╯",
]

# Codex echoes the submitted command on its own line and draws the panel beneath it.
# That ordering is what marks a panel as belonging to this invocation, because the
# screen scrolls: on a second check the earlier panel slides off while the new one
# draws, so counting panels never rises and a count-based check fails a good reading.
_STATUS_ECHOED = ["/status", "", *_STATUS_PANEL]
# The same panel with the echo beneath it, which is a stale reading and not this one.
_STATUS_STALE = [*_STATUS_PANEL, "", "/status"]

# Current Codex (v0.152.0) shows a mutable thread name in configured terminal titles,
# while `/status` still exposes the immutable session UUID. The extra Thread name row
# is material: the parser must select the labelled Session row, not whichever identity-
# looking presentation field happens to precede it.
_NAMED_STATUS_PANEL = [
    "╭──────────────────────────────────────────────────────────────────╮",
    "│  >_ OpenAI Codex (v0.152.0)                                      │",
    "│                                                                  │",
    "│  Thread name:              Verify supervising plugin session    │",
    f"│  Session:                  {_ID_BEFORE}  │",
    "╰──────────────────────────────────────────────────────────────────╯",
]

_PENDING_APPROVAL_PANE = "\n".join(
    [
        "  Would you like to run the following command?",
        "",
        "  $ git rebase origin/main",
        "",
        f"{_CURSOR} 1. Yes, proceed (y)",
        "  2. No, and tell Codex what to do differently (esc)",
        "",
        _EMPTY_COMPOSER,
        "",
        _footer(96),
    ]
)


@pytest.fixture(scope="module")
def watch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_supervisor", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so dataclasses resolve __module__ during class creation.
    sys.modules["codex_supervisor"] = module
    spec.loader.exec_module(module)
    return module


class _Pane:
    """A scripted tmux pane, replacing the one external boundary this code has.

    Titles and bodies advance independently, each holding its last value once the
    script runs out, so a verb that polls sees a pane that settles rather than one
    that runs off the end of a list.
    """

    def __init__(self, titles: list[str], bodies: list[str]) -> None:
        self.titles = list(titles)
        self.bodies = list(bodies)
        self.calls: list[tuple[str, ...]] = []
        self.pasted = False

    def run(self, argv: tuple[str, ...]) -> str:
        self.calls.append(argv)
        if argv[-1] == "#{pane_title}":
            return self.titles.pop(0) if len(self.titles) > 1 else self.titles[0]
        if "capture-pane" in argv:
            return self.bodies.pop(0) if len(self.bodies) > 1 else self.bodies[0]
        return ""

    @property
    def keys(self) -> list[tuple[str, ...]]:
        return [argv for argv in self.calls if "send-keys" in argv]


def _install(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    pane: _Pane,
    *,
    session_ids: list[str] | None = None,
) -> _Pane:
    target = watch.PaneRef("%55", 5055)
    identities = list(session_ids or [_ID_BEFORE, _ID_BEFORE])

    def session_identity(_target: object) -> str:
        return identities.pop(0) if len(identities) > 1 else identities[0]

    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "joined_pane", lambda: target.pane_id)
    # No process table to read, so these verbs take the `/status` screen route.
    monkeypatch.setattr(watch, "PROC_ROOT", Path("/nonexistent-proc"))
    monkeypatch.setattr(
        watch,
        "_probe_session_identity",
        session_identity,
        raising=False,
    )
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)

    def refuse_paste(*_args: object, **_kwargs: object) -> None:
        pane.pasted = True

    monkeypatch.setattr(watch.subprocess, "run", refuse_paste)
    return pane


# ---------------------------------------------------------------- reading the meter


def test_the_context_meter_is_read_from_the_footer(watch: ModuleType) -> None:
    """The percentage is what the operator ruling says to trust over codex's claim."""
    assert watch.context_left(_pane(percent=96)) == 96


def test_a_meter_truncated_at_the_pane_width_still_reads(watch: ModuleType) -> None:
    """A narrower pane cut `left` off the end; the number arrives before the cut.

    Captured from pane %12 at its own width, where the footer ended `Context 50% …`.
    """
    assert watch.context_left("  google-live · main · Context 50% …") == 50


def test_a_pane_with_no_footer_reports_no_reading(watch: ModuleType) -> None:
    """Unreadable is its own answer, distinct from a reading that cleared the floor."""
    assert watch.context_left("• acknowledged\n") is None


# ------------------------------------------------------------ reading the session id


def test_the_session_id_is_read_from_a_fresh_status_panel(
    watch: ModuleType,
) -> None:
    content = _pane(body=["/status", "", *_NAMED_STATUS_PANEL])

    assert watch.status_session_identity(content, below="/status") == _ID_BEFORE


def test_a_status_panel_above_the_current_echo_is_stale(watch: ModuleType) -> None:
    content = _pane(body=[*_NAMED_STATUS_PANEL, "", "/status"])

    assert watch.status_session_identity(content, below="/status") is None


def test_the_session_probe_runs_status_and_reads_its_fresh_panel(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    named_title = (
        "Ready | brian-ed3d-plugins | main | Verify supervising plugin session | "
        "gpt-5.6-sol xhigh"
    )
    pane = _Pane(
        [named_title],
        [
            _pane(),
            _TYPED_STATUS,
            _pane(body=["/status", "", *_NAMED_STATUS_PANEL]),
        ],
    )
    target = watch.PaneRef("%55", 5055)
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(watch, "joined_target", lambda: target, raising=False)

    assert watch._probe_session_identity(target) == _ID_BEFORE
    assert pane.keys == [
        ("tmux", "send-keys", "-t", "%55", "-l", "/status"),
        ("tmux", "send-keys", "-t", "%55", "Enter"),
    ]


def test_the_session_probe_does_not_reuse_a_panel_while_status_is_still_typed(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_while_typed = "\n".join([*_STATUS_ECHOED, "", _TYPED_STATUS])
    pane = _Pane(
        [_NAMED_TITLE_READY],
        [_pane(), _TYPED_STATUS, stale_while_typed],
    )
    target = watch.PaneRef("%55", 5055)
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "RESPONSE_POLLS", 2)

    with pytest.raises(watch.MonitorError, match="no fresh session identity"):
        watch._probe_session_identity(target)


# --------------------------------------------------------------- the completion list


def test_a_fully_typed_command_narrows_the_list_to_itself(watch: ModuleType) -> None:
    assert watch.slash_completions(_TYPED_CLEAR) == ["/clear"]


def test_a_partial_command_leaves_the_wrong_entry_first(watch: ModuleType) -> None:
    """This is the hazard the two-call split exists for, observed rather than feared."""
    assert watch.slash_completions(_TYPED_AMBIGUOUS) == ["/compact", "/copy", "/clear"]


def test_a_full_command_does_not_always_narrow_the_list(watch: ModuleType) -> None:
    """`/statusline` shares the prefix, so narrowing cannot be Enter's gate."""
    assert watch.slash_completions(_TYPED_STATUS) == ["/status", "/statusline"]


def test_the_selected_entry_is_the_one_enter_would_take(watch: ModuleType) -> None:
    """Codex leaves the highlighted entry's description bright and the rest faint."""
    assert watch.selected_completion(_TYPED_STATUS) == "/status"
    assert watch.selected_completion(_TYPED_CLEAR) == "/clear"


def test_the_selection_is_read_rather_than_assumed_from_position(
    watch: ModuleType,
) -> None:
    """`/c` highlights `/compact`, which sits above both `/copy` and `/clear`."""
    assert watch.selected_completion(_TYPED_AMBIGUOUS) == "/compact"


def test_the_v0157_marked_entry_is_the_one_enter_would_take(watch: ModuleType) -> None:
    """v0.157.0 marks the selection with the prompt marker instead of an indent."""
    assert watch.selected_completion(_V157_TYPED_STATUS) == "/status"
    assert watch.selected_completion(_V157_TYPED_CLEAR) == "/clear"
    assert watch.slash_completions(_V157_TYPED_STATUS) == ["/status", "/statusline"]


def test_the_v0157_status_probe_submits_status(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pane = _Pane(
        [_NAMED_TITLE_READY],
        [
            _pane(),
            _V157_TYPED_STATUS,
            _pane(body=["/status", "", *_NAMED_STATUS_PANEL]),
        ],
    )
    target = watch.PaneRef("%55", 5055)
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(watch, "joined_target", lambda: target, raising=False)

    assert watch._probe_session_identity(target) == _ID_BEFORE
    assert ("tmux", "send-keys", "-t", "%55", "Enter") in pane.keys


def test_a_v0157_half_typed_command_is_never_submitted(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/c` highlights `/compact` on v0.157.0 too, so a `/clear` there must refuse."""
    pane = _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(), _V157_TYPED_AMBIGUOUS]),
    )

    with pytest.raises(watch.MonitorError, match="Enter would take /compact "):
        watch.run_slash_command("/clear")

    assert ("tmux", "send-keys", "-t", "%55", "Enter") not in pane.keys


def test_a_v0157_highlight_on_another_entry_still_refuses(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enter takes `/status` here, so a request for `/statusline` must not submit."""
    pane = _Pane([_NAMED_TITLE_READY], [_V157_TYPED_STATUS])
    monkeypatch.setattr(watch, "run_command", pane.run)

    with pytest.raises(watch.MonitorError, match="Enter would take /status "):
        watch._confirm_selection("%55", _V157_TYPED_STATUS, "/statusline")

    assert ("tmux", "send-keys", "-t", "%55", "Enter") not in pane.keys


# ------------------------------------------------------------------------- the verbs


def test_clearing_types_the_command_and_never_pastes_it(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A slash command goes in as keystrokes on its own line, not through a buffer.

    `--message` would route this through `load-buffer`/`paste-buffer`, which is how
    the supervisor kept handing codex the text as work instead of running it.
    """
    pane = _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR, _TITLE_AFTER_CLEAR_READY],
            [_pane(), _TYPED_CLEAR],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    watch.run_slash_command("/clear")

    assert pane.keys == [
        ("tmux", "send-keys", "-t", "%55", "-l", "/clear"),
        ("tmux", "send-keys", "-t", "%55", "Enter"),
    ], pane.keys
    assert not pane.pasted, "a slash command must never go through the paste buffer"


def test_clearing_a_named_thread_is_confirmed_by_status_session_rotation(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_NAMED_TITLE_READY],
            [_pane(), _TYPED_CLEAR, _pane(percent=100)],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    result = watch.run_slash_command("/clear")

    assert _ID_BEFORE in result and _ID_AFTER in result, result


def test_clearing_is_confirmed_by_the_session_id_rotating(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The new id is positive evidence; an emptied screen would only be an absence."""
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR, _TITLE_AFTER_CLEAR_READY],
            [_pane(), _TYPED_CLEAR],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    result = watch.run_slash_command("/clear")

    assert _ID_BEFORE in result and _ID_AFTER in result, result


def test_a_clear_that_did_not_rotate_the_session_is_not_reported_as_done(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enter can be swallowed, so the same id afterwards means nothing ran."""
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(), _TYPED_CLEAR]),
    )

    with pytest.raises(watch.MonitorError, match="session"):
        watch.run_slash_command("/clear")


def test_a_half_typed_command_is_never_submitted(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/c` highlights `/compact`, so Enter here compacts a pane meant to be cleared."""
    pane = _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(), _TYPED_AMBIGUOUS]),
    )

    with pytest.raises(watch.MonitorError, match="/compact"):
        watch.run_slash_command("/clear")

    assert ("tmux", "send-keys", "-t", "%55", "Enter") not in pane.keys, (
        "the guard is worthless if Enter goes anyway"
    )


def test_a_refused_command_leaves_the_composer_usable(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Text left in the composer makes the next send refuse for the wrong reason."""
    pane = _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(), _TYPED_AMBIGUOUS]),
    )

    with pytest.raises(watch.MonitorError):
        watch.run_slash_command("/clear")

    assert ("tmux", "send-keys", "-t", "%55", "C-a") in pane.keys, pane.keys
    assert ("tmux", "send-keys", "-t", "%55", "C-k") in pane.keys, pane.keys


def test_compacting_is_confirmed_by_the_meter_rather_than_the_claim(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """96% to 100% left with a fresh `Context compacted` bullet, as observed."""
    compacted = _pane(
        percent=100,
        body=["• acknowledged", "", "• Context compacted"],
    )
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(percent=96), _TYPED_COMPACT, compacted]),
    )

    result = watch.run_slash_command("/compact")

    assert "96" in result and "100" in result, result


def test_a_compaction_that_cost_context_is_reported_as_a_failure(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A falling meter disproves compaction even when Codex acknowledges it."""
    worse = _pane(
        percent=18,
        body=["• acknowledged", "", "• Context compacted"],
    )
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(percent=21), _TYPED_COMPACT, worse]),
    )

    with pytest.raises(watch.MonitorError, match=r"21.*18|18.*21"):
        watch.run_slash_command("/compact")


def test_a_compaction_codex_never_acknowledged_is_not_reported_as_done(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A flat meter alone cannot tell a compaction from nothing having happened."""
    unchanged = _pane(percent=96, body=["• acknowledged"])
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(percent=96), _TYPED_COMPACT, unchanged]),
    )

    with pytest.raises(watch.MonitorError, match="compacted"):
        watch.run_slash_command("/compact")


def test_a_compaction_refuses_if_the_status_session_changes(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compacted = _pane(
        percent=100,
        body=["• acknowledged", "", "• Context compacted"],
    )
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_NAMED_TITLE_READY],
            [_pane(percent=96), _TYPED_COMPACT, compacted],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    with pytest.raises(watch.MonitorError, match="session changed"):
        watch.run_slash_command("/compact")


def test_a_context_command_refuses_if_the_foreground_codex_changes(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compacted = _pane(
        percent=100,
        body=["• acknowledged", "", "• Context compacted"],
    )
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_NAMED_TITLE_READY],
            [_pane(percent=96), _TYPED_COMPACT, compacted],
        ),
    )
    targets = iter(
        [
            watch.PaneRef("%55", 5055),
            watch.PaneRef("%55", 6066),
        ]
    )
    monkeypatch.setattr(watch, "joined_target", lambda: next(targets))

    with pytest.raises(watch.MonitorError, match="target changed"):
        watch.run_slash_command("/compact")


def test_no_slash_command_is_typed_into_a_pending_approval(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any keystroke answers the dialog on screen, so `/clear` would approve it."""
    pane = _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_PENDING_APPROVAL_PANE]),
    )

    with pytest.raises(watch.MonitorError, match="approval"):
        watch.run_slash_command("/clear")

    assert pane.keys == [], "a pane holding a dialog must receive nothing at all"


# ------------------------------------------------------------------ the context floor


def test_a_dispatch_below_the_floor_refuses_and_names_the_remedy(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under 30% left, the next prompt is dispatched into a pane that cannot hold it."""
    _install(watch, monkeypatch, _Pane([_TITLE_BEFORE_CLEAR], [_pane(percent=22)]))

    with pytest.raises(watch.MonitorError) as excinfo:
        watch.send_message("%55", "Do the next task.")

    message = str(excinfo.value)
    assert "22" in message, message
    assert "--compact" in message or "--clear" in message, message


def test_a_dispatch_at_the_floor_proceeds(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The floor is a threshold to cross, not one to sit exactly on and fail."""
    pane = _install(
        watch,
        monkeypatch,
        _Pane(["Ready | x", "⠋ Working | x"], [_pane(percent=30)]),
    )

    assert watch.send_message("%55", "Do the next task.") == "submitted to %55"
    assert pane.pasted


def test_the_floor_yields_to_an_explicit_human_ruling(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a way to say yes, the supervisor falls back to raw send-keys."""
    _install(
        watch,
        monkeypatch,
        _Pane(["Ready | x", "⠋ Working | x"], [_pane(percent=12)]),
    )

    assert (
        watch.send_message("%55", "Do the next task.", under_floor=True)
        == "submitted to %55"
    )


def test_a_dispatch_refuses_when_the_meter_cannot_be_read(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failing open on an unreadable meter is the absence-read-as-a-pass again."""
    bare = f"• acknowledged\n\n{_EMPTY_COMPOSER}\n"
    _install(watch, monkeypatch, _Pane(["Ready | x"], [bare]))

    with pytest.raises(watch.MonitorError, match="meter"):
        watch.send_message("%55", "Do the next task.")


def test_a_clear_hands_back_a_pane_that_is_ready_to_take_the_next_prompt(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A clear restarts Codex, and returning on the rotation alone hands back a pane
    that is still booting, so the next dispatch refuses and the round is wasted.
    """
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR, _TITLE_AFTER_CLEAR_READY],
            [_pane(), _TYPED_CLEAR, _pane(percent=100)],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    result = watch.run_slash_command("/clear")

    assert "Ready" in result, result
    assert "100" in result, result


def test_clear_survives_old_ready_title_before_new_session_starts(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The old Ready title can linger after Enter, then change to Starting."""
    target = watch.PaneRef("%55", 5055)

    class RestartingPane:
        def __init__(self) -> None:
            self.typed = ""
            self.cleared = False
            self.title_reads_after_clear = 0
            self.status_pending = False
            self.keys: list[tuple[str, ...]] = []

        def title(self) -> str:
            if not self.cleared:
                return _TITLE_BEFORE_CLEAR
            self.title_reads_after_clear += 1
            if self.title_reads_after_clear == 1:
                return _TITLE_BEFORE_CLEAR
            if self.title_reads_after_clear == 2:
                return _TITLE_AFTER_CLEAR
            return _TITLE_AFTER_CLEAR_READY

        def capture(self) -> str:
            if self.typed == "/status":
                return _TYPED_STATUS
            if self.typed == "/clear":
                return _TYPED_CLEAR
            if self.status_pending:
                self.status_pending = False
                panel = _NAMED_STATUS_PANEL
                if self.cleared:
                    panel = [line.replace(_ID_BEFORE, _ID_AFTER) for line in panel]
                return _pane(body=["/status", "", *panel])
            return _pane(percent=100 if self.cleared else 96)

        def run(self, argv: tuple[str, ...]) -> str:
            if argv[-1] == "#{pane_title}":
                return self.title()
            if "send-keys" in argv:
                self.keys.append(argv)
                if "-l" in argv:
                    self.typed = argv[-1]
                elif argv[-1] == "Enter":
                    self.status_pending = self.typed == "/status"
                    self.cleared |= self.typed == "/clear"
                    self.typed = ""
                return ""
            if "capture-pane" in argv:
                return self.capture()
            return ""

    pane = RestartingPane()
    monkeypatch.setattr(watch, "PROC_ROOT", Path("/nonexistent-proc"))
    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)

    result = watch.run_slash_command("/clear")

    assert f"{_ID_BEFORE} -> {_ID_AFTER}" in result
    assert "Ready, context 100% left" in result
    assert pane.title_reads_after_clear >= 2
    assert pane.keys.count(("tmux", "send-keys", "-t", "%55", "Enter")) == 3


def test_clear_waits_for_a_transient_missing_composer_before_status_probe(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ready can appear before the restarted TUI has redrawn its composer."""
    target = watch.PaneRef("%55", 5055)
    bare = "• Codex is starting\n"
    pane = _Pane(
        [_TITLE_AFTER_CLEAR_READY],
        [bare, _pane(percent=100)],
    )
    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)

    def probe(_target: object) -> str:
        watch._preflight_pane(target.pane_id)
        return _ID_AFTER

    monkeypatch.setattr(watch, "_probe_session_identity", probe)

    result = watch._confirm_clear(target, _ID_BEFORE)

    assert f"{_ID_BEFORE} -> {_ID_AFTER}" in result
    assert "Ready, context 100% left" in result
    assert pane.keys == []


def test_initial_clear_preflight_still_refuses_a_missing_composer(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pane = _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], ["• Codex is starting\n"]),
    )

    with pytest.raises(watch.MonitorError, match="no composer drawn"):
        watch.run_slash_command("/clear")

    assert pane.keys == []


def test_clear_does_not_confirm_a_pane_whose_composer_never_redraws(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = watch.PaneRef("%55", 5055)
    pane = _Pane([_TITLE_AFTER_CLEAR_READY], ["• Codex is starting\n"])
    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(watch, "SETTLE_POLLS", 3)

    def probe(_target: object) -> str:
        watch._preflight_pane(target.pane_id)
        return _ID_AFTER

    monkeypatch.setattr(watch, "_probe_session_identity", probe)

    with pytest.raises(watch.MonitorError, match="no composer drawn"):
        watch._confirm_clear(target, _ID_BEFORE)

    assert pane.keys == []


def test_a_clear_that_never_returns_ready_cannot_be_confirmed(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without Ready the post-command status identity cannot safely be requested."""
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR], [_pane(), _TYPED_CLEAR]),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    with pytest.raises(watch.MonitorError, match="did not return Ready"):
        watch.run_slash_command("/clear")


def test_stale_ready_before_permanent_starting_reports_not_ready(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An old Ready reading cannot establish that the new session settled."""
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR],
            [_pane(), _TYPED_CLEAR],
        ),
    )

    with pytest.raises(watch.MonitorError, match="did not return Ready"):
        watch.run_slash_command("/clear")


def test_a_compaction_hands_back_a_pane_that_is_ready(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compacted = _pane(percent=100, body=["• acknowledged", "", "• Context compacted"])
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_WORKING, _TITLE_AFTER_CLEAR_READY],
            [_pane(percent=96), _TYPED_COMPACT, compacted],
        ),
    )

    result = watch.run_slash_command("/compact")

    assert "Ready" in result, result


def test_the_meter_is_read_once_the_pane_has_settled(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex draws its marker before the footer catches up, so a meter read at the
    marker reports a figure that is about to change, and a compaction that worked
    can be reported as one that cost context.
    """
    mid = _pane(percent=41, body=["• acknowledged", "", "• Context compacted"])
    settled = _pane(percent=100, body=["• acknowledged", "", "• Context compacted"])
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_WORKING, _TITLE_AFTER_CLEAR_READY],
            [_pane(percent=96), _TYPED_COMPACT, mid, settled],
        ),
    )

    result = watch.run_slash_command("/compact")

    assert "100" in result, result
    assert "41" not in result, f"the mid-compaction meter is not the answer: {result}"


def test_a_clear_waits_for_the_footer_to_be_redrawn_before_reading_the_meter(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The footer is absent for a moment after the title says Ready.

    Observed live on pane %57, 2026-08-01: a cleared pane prints its token-usage
    summary and its resume line, and only then redraws the footer, so the one read
    taken on the title going Ready fell in the gap and the verb reported the meter
    unreadable on a clear that had worked.
    """
    bare = f"• acknowledged\n\n{_EMPTY_COMPOSER}\n"
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR, _TITLE_AFTER_CLEAR_READY],
            [_pane(), _TYPED_CLEAR, bare, _pane(percent=100)],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    result = watch.run_slash_command("/clear")

    assert "100" in result, result
    assert "unreadable" not in result, result


def test_a_compaction_survives_the_same_redraw_gap(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unreadable meter raises here, so the gap would fail a good compaction."""
    marked = _pane(percent=100, body=["• acknowledged", "", "• Context compacted"])
    bare = f"• Context compacted\n\n{_EMPTY_COMPOSER}\n"
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_WORKING, _TITLE_AFTER_CLEAR_READY],
            [_pane(percent=96), _TYPED_COMPACT, marked, bare, marked],
        ),
    )

    result = watch.run_slash_command("/compact")

    assert "100" in result, result


# ------------------------------------------------------------------------- the quota


def test_the_quota_verb_reports_the_figure_and_the_date_it_resets(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A percentage alone cannot say whether the burn is on track.

    Half the allowance left on day two is a problem and the same figure on day six is
    fine, so the reset is the half of the answer the pane title cannot give.
    """
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR],
            [_pane(), _TYPED_STATUS, _pane(body=_STATUS_ECHOED)],
        ),
    )

    result = watch.run_slash_command("/status")

    assert "99" in result, result
    assert "14:41 on 8 Aug" in result, result
    assert "Ready" in result, (
        f"a verb that leaves the caller asking whether the pane is usable has "
        f"cost the round it was meant to save: {result}"
    )


def test_the_quota_verb_reads_the_first_weekly_limit_not_the_second(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second model's allowance is reported alongside and is not the one asked for."""
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR],
            [_pane(), _TYPED_STATUS, _pane(body=_STATUS_ECHOED)],
        ),
    )

    result = watch.run_slash_command("/status")

    assert "19:33" not in result, f"that is the Spark limit's reset: {result}"


def test_the_quota_verb_does_not_carry_the_account_back(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The panel names the signed-in address, which the quota question never needs."""
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR],
            [_pane(), _TYPED_STATUS, _pane(body=_STATUS_ECHOED)],
        ),
    )

    result = watch.run_slash_command("/status")

    assert "example.edu.au" not in result, result


def test_a_quota_check_that_drew_no_panel_is_not_reported_as_a_reading(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enter can be swallowed, and a stale panel is not this reading."""
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [_pane(), _TYPED_STATUS, _pane()]),
    )

    with pytest.raises(watch.MonitorError, match="drew no status panel"):
        watch.run_slash_command("/status")


def test_a_quota_check_needs_a_panel_newer_than_the_one_already_there(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running it twice must read the second panel rather than re-reading the first.

    The screen scrolls, so the earlier panel is still partly visible while the new
    one draws. What separates them is the echo: a panel above this invocation's
    echoed command belongs to the previous one.
    """
    stale = _pane(body=_STATUS_STALE)
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [stale, _TYPED_STATUS, stale]),
    )

    with pytest.raises(watch.MonitorError, match="drew no status panel"):
        watch.run_slash_command("/status")


def test_a_second_quota_check_reads_the_new_panel_as_the_screen_scrolls(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observed live on pane %58, 2026-08-01: the second check reported no panel.

    Drawing the new panel scrolls the earlier one off the visible capture, so the
    number of panels on screen goes from one to one and never rises. A check counting
    them therefore fails the second reading of a pane that answered perfectly well,
    which is why the echo rather than the count is what marks a panel as this one's.
    """
    before = _pane(body=_STATUS_PANEL)
    after = _pane(body=_STATUS_ECHOED)
    _install(
        watch,
        monkeypatch,
        _Pane([_TITLE_BEFORE_CLEAR], [before, _TYPED_STATUS, after]),
    )

    result = watch.run_slash_command("/status")

    assert "99" in result, result


def test_the_floor_does_not_block_the_verbs_that_relieve_it(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gating `/clear` on context would leave an exhausted pane with no way out."""
    _install(
        watch,
        monkeypatch,
        _Pane(
            [_TITLE_BEFORE_CLEAR, _TITLE_AFTER_CLEAR, _TITLE_AFTER_CLEAR_READY],
            [_pane(percent=4), _TYPED_CLEAR, _pane(percent=100)],
        ),
        session_ids=[_ID_BEFORE, _ID_AFTER],
    )

    assert _ID_AFTER in watch.run_slash_command("/clear")


# ------------------------------------------------------- reading Codex's own files
#
# Codex keeps a lock per session under `thread-writer-locks/` and appends every model
# call's token and rate-limit figures to that session's rollout file, and its process
# holds both open (observed on codex-cli 0.157.0, 2026-09-28). The tests below build a
# process table and those files under a temporary directory; the record shape is the
# one observed then, with every value synthetic.

_ID_OTHER = "01a0e6e0-07a1-7320-9111-6f33ec1c3f24"
_CODEX_PGID = 5055


class _Proc:
    """A process table in the shape `/proc` presents, holding synthetic Codex files."""

    def __init__(self, root: Path) -> None:
        self.root = root / "proc"
        self.codex_home = root / "codex-home"
        self.root.mkdir()
        self._fds: dict[int, int] = {}

    def process(self, pid: int, pgid: int, command: str = "codex") -> None:
        (self.root / str(pid) / "fd").mkdir(parents=True)
        # pid (comm) state ppid pgrp session tty_nr tpgid ...
        stat = f"{pid} ({command}) S 1 {pgid} {pgid} 34816 {pgid} 4194560 0 0\n"
        (self.root / str(pid) / "stat").write_text(stat)
        self._fds[pid] = 30

    def _open(self, pid: int, target: Path) -> None:
        self._fds[pid] += 1
        (self.root / str(pid) / "fd" / str(self._fds[pid])).symlink_to(target)

    def hold_lock(self, pid: int, session_id: str) -> None:
        lock = self.codex_home / "thread-writer-locks" / f"{session_id}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.touch()
        self._open(pid, lock)

    def hold_rollout(self, pid: int, session_id: str, lines: list[str]) -> Path:
        rollout = (
            self.codex_home
            / "sessions"
            / "2026"
            / "09"
            / "28"
            / f"rollout-2026-09-28T15-55-49-{session_id}.jsonl"
        )
        rollout.parent.mkdir(parents=True, exist_ok=True)
        rollout.write_text("".join(f"{line}\n" for line in lines))
        self._open(pid, rollout)
        return rollout


def _session_meta(session_id: str, parent: str | None = None) -> str:
    """A rollout's first record: a main thread names itself, a sub-agent its parent.

    Observed across eight panes on 2026-09-28 (codex-cli 0.157.0): each held exactly
    one rollout whose `id` equalled its `session_id`, with `source` "cli", and every
    other held rollout was a sub-agent whose `session_id` was that main thread's id.
    """
    source: object = {"subagent": {"depth": 1}} if parent else "cli"
    return json.dumps(
        {
            "timestamp": "2026-09-28T05:55:49.001Z",
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "session_id": parent or session_id,
                "cwd": "/x",
                "source": source,
                "thread_source": "subagent" if parent else "user",
            },
        }
    )


def _token_count(
    timestamp: str,
    used: float,
    resets_at: int,
    *,
    limit_id: str = "codex",
    limit_name: str | None = None,
    window_minutes: int = 10080,
) -> str:
    """One `token_count` record, in the skeleton observed on 2026-09-28.

    One session file mixes allowances: pane %6's main thread held records for
    `codex` (unnamed, one week), `base_model_inference` ("gpt-reserve", one week) and
    `codex_bengalfox` ("GPT-5.3-Codex-Spark", five hours), interleaved.
    """
    return json.dumps(
        {
            "timestamp": timestamp,
            "ordinal": 7,
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {"total_token_usage": {"total_tokens": 1}},
                "rate_limits": {
                    "limit_id": limit_id,
                    "limit_name": limit_name,
                    "primary": {
                        "used_percent": used,
                        "window_minutes": window_minutes,
                        "resets_at": resets_at,
                    },
                    "secondary": None,
                    "credits": {"has_credits": False},
                    "individual_limit": None,
                    "spend_control_reached": None,
                    "plan_type": "pro",
                    "rate_limit_reached_type": None,
                },
            },
        }
    )


# 1791046701 is 16:58 UTC on 3 Oct 2026 (`date -u -d @1791046701`).
_RESETS_AT = 1791046701
_READ_AT = "2026-09-28T05:55:49.123Z"
_READ_EPOCH = calendar.timegm((2026, 9, 28, 5, 55, 49)) + 0.123
# The previous week's reset, already past at _READ_EPOCH.
_RESET_LAST_WEEK = _RESETS_AT - 7 * 86400


@pytest.fixture
def utc() -> Iterator[None]:
    """Pin local time to UTC, so a reset time renders the same on every machine."""
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    yield
    if previous is None:
        del os.environ["TZ"]
    else:
        os.environ["TZ"] = previous
    time.tzset()


@pytest.fixture
def proc(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> _Proc:
    table = _Proc(tmp_path)
    table.process(_CODEX_PGID, _CODEX_PGID, "node-MainThread")
    table.process(_CODEX_PGID + 7, _CODEX_PGID)
    monkeypatch.setattr(watch, "PROC_ROOT", table.root)
    return table


def _join(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    runner: object,
) -> None:
    target = watch.PaneRef("%55", _CODEX_PGID)
    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "joined_pane", lambda: target.pane_id)
    monkeypatch.setattr(watch, "run_command", runner)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(watch.time, "time", lambda: _READ_EPOCH + 180)


def test_the_sessions_a_pane_holds_are_read_from_its_process_group(
    watch: ModuleType,
    proc: _Proc,
) -> None:
    """Only the pane's own foreground group counts; another Codex's locks do not."""
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    proc.process(9999, 9999)
    proc.hold_lock(9999, _ID_OTHER)

    held = watch.held_sessions(_CODEX_PGID)

    assert held is not None
    assert held.ids == frozenset({_ID_BEFORE})


def test_no_process_table_is_no_answer_rather_than_no_sessions(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(watch, "PROC_ROOT", tmp_path / "absent")

    assert watch.held_sessions(_CODEX_PGID) is None


def test_the_quota_is_read_from_the_session_file_without_typing(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    utc: None,
) -> None:
    """The figures come from Codex's last model call, so the reading carries its age."""
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    proc.hold_rollout(
        pid,
        _ID_BEFORE,
        [_session_meta(_ID_BEFORE), _token_count(_READ_AT, 48.0, _RESETS_AT)],
    )
    pane = _Pane([_NAMED_TITLE_READY], [_pane()])
    _join(watch, monkeypatch, pane.run)

    result = watch.report_quota()

    assert "weekly 52% left" in result, result
    assert "resets 16:58 on 3 Oct" in result, result
    assert "3m old" in result, result
    assert pane.keys == [], "a file reading must not type into the pane"


def test_the_newest_rate_limit_record_is_the_reading(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    utc: None,
) -> None:
    """Later records follow later model calls; a half-written last line is skipped."""
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    proc.hold_rollout(
        pid,
        _ID_BEFORE,
        [
            _session_meta(_ID_BEFORE),
            _token_count("2026-09-28T05:40:00.000Z", 10.0, _RESETS_AT),
            _token_count(_READ_AT, 48.0, _RESETS_AT),
            json.dumps({"timestamp": _READ_AT, "type": "response_item", "payload": {}}),
            '{"timestamp":"2026-09-28T05:58:00.000Z","type":"event_msg","payl',
        ],
    )
    pane = _Pane([_NAMED_TITLE_READY], [_pane()])
    _join(watch, monkeypatch, pane.run)

    result = watch.report_quota()

    assert "weekly 52% left" in result, result
    assert "90%" not in result, result


def test_the_main_thread_is_read_when_sub_agents_hold_sessions_too(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    utc: None,
) -> None:
    """Long-running panes held four sessions each: one main thread, three sub-agents.

    The main thread is told apart by its own first record, not by id order, and its
    file is the one read even when a sub-agent has recorded a later model call.
    """
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_OTHER)
    proc.hold_rollout(
        pid,
        _ID_OTHER,
        [
            _session_meta(_ID_OTHER, parent=_ID_BEFORE),
            _token_count("2026-09-28T05:57:00.000Z", 60.0, _RESETS_AT),
        ],
    )
    proc.hold_lock(pid, _ID_BEFORE)
    proc.hold_rollout(
        pid,
        _ID_BEFORE,
        [_session_meta(_ID_BEFORE), _token_count(_READ_AT, 48.0, _RESETS_AT)],
    )
    proc.hold_lock(pid, _ID_AFTER)
    proc.hold_rollout(pid, _ID_AFTER, [_session_meta(_ID_AFTER, parent=_ID_BEFORE)])
    pane = _Pane([_NAMED_TITLE_READY], [_pane()])
    _join(watch, monkeypatch, pane.run)

    result = watch.report_quota()

    assert "weekly 52% left" in result, result
    assert pane.keys == [], "a file reading must not type into the pane"


def test_a_sub_agent_of_another_thread_is_ignored_rather_than_refused(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    utc: None,
) -> None:
    """Brian, 2026-09-28: "we don't care about codex's own subagents"."""
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    proc.hold_rollout(
        pid,
        _ID_BEFORE,
        [_session_meta(_ID_BEFORE), _token_count(_READ_AT, 48.0, _RESETS_AT)],
    )
    proc.hold_lock(pid, _ID_AFTER)
    proc.hold_rollout(pid, _ID_AFTER, [_session_meta(_ID_AFTER, parent=_ID_OTHER)])
    pane = _Pane([_NAMED_TITLE_READY], [_pane()])
    _join(watch, monkeypatch, pane.run)

    assert "weekly 52% left" in watch.report_quota()
    assert pane.keys == []


def test_a_newer_record_of_another_allowance_is_not_the_weekly_figure(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    utc: None,
) -> None:
    """Pane %6, 2026-09-28: the newest record was a reserve allowance at 0% used,
    which would have reported an untouched week while the plain weekly limit stood at
    roughly half. The plain `Weekly limit:` row is the unnamed `codex` limit.
    """
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    proc.hold_rollout(
        pid,
        _ID_BEFORE,
        [
            _session_meta(_ID_BEFORE),
            _token_count(_READ_AT, 48.0, _RESETS_AT),
            _token_count(
                "2026-09-28T05:57:00.000Z",
                3.0,
                _RESETS_AT,
                limit_id="codex_bengalfox",
                limit_name="GPT-5.3-Codex-Spark",
                window_minutes=300,
            ),
            _token_count(
                "2026-09-28T05:58:00.000Z",
                0.0,
                _RESETS_AT + 86400,
                limit_id="base_model_inference",
                limit_name="gpt-reserve",
            ),
        ],
    )
    pane = _Pane([_NAMED_TITLE_READY], [_pane()])
    _join(watch, monkeypatch, pane.run)

    result = watch.report_quota()

    assert "weekly 52% left" in result, result
    assert "resets 16:58 on 3 Oct" in result, result


def test_a_reading_from_a_window_that_has_reset_gives_way_to_a_current_one(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    utc: None,
) -> None:
    """A record whose reset has passed describes a week that is over."""
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    proc.hold_rollout(
        pid,
        _ID_BEFORE,
        [
            _session_meta(_ID_BEFORE),
            _token_count("2026-09-21T05:55:49.000Z", 5.0, _RESET_LAST_WEEK),
            _token_count(_READ_AT, 48.0, _RESETS_AT),
        ],
    )
    pane = _Pane([_NAMED_TITLE_READY], [_pane()])
    _join(watch, monkeypatch, pane.run)

    result = watch.report_quota()

    assert "weekly 52% left" in result, result
    assert pane.keys == []


def _no_rollout(proc: _Proc) -> None:
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)


def _no_record(proc: _Proc) -> None:
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    proc.hold_rollout(_CODEX_PGID + 7, _ID_BEFORE, [_session_meta(_ID_BEFORE)])


def _no_lock(proc: _Proc) -> None:
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_BEFORE,
        [_token_count(_READ_AT, 48.0, _RESETS_AT)],
    )


def _two_main_sessions(proc: _Proc) -> None:
    """Two rollouts that each name themselves: which is current is not known."""
    for session in (_ID_BEFORE, _ID_AFTER):
        proc.hold_lock(_CODEX_PGID + 7, session)
        proc.hold_rollout(
            _CODEX_PGID + 7,
            session,
            [_session_meta(session), _token_count(_READ_AT, 48.0, _RESETS_AT)],
        )


def _just_cleared(proc: _Proc) -> None:
    """The new session's lock has no rollout yet, so it cannot be classified."""
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_BEFORE,
        [_session_meta(_ID_BEFORE), _token_count(_READ_AT, 48.0, _RESETS_AT)],
    )
    proc.hold_lock(_CODEX_PGID + 7, _ID_AFTER)


def _other_limits_only(proc: _Proc) -> None:
    """A named or shorter-window allowance is not the weekly figure."""
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_BEFORE,
        [
            _session_meta(_ID_BEFORE),
            _token_count(
                _READ_AT,
                0.0,
                _RESETS_AT,
                limit_id="base_model_inference",
                limit_name="gpt-reserve",
            ),
            _token_count(
                _READ_AT,
                3.0,
                _RESETS_AT,
                limit_id="codex_bengalfox",
                limit_name="GPT-5.3-Codex-Spark",
                window_minutes=300,
            ),
        ],
    )


def _five_hour_codex_limit(proc: _Proc) -> None:
    """Codex's panel code names an unnamed `codex` five-hour window "5h limit"."""
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_BEFORE,
        [
            _session_meta(_ID_BEFORE),
            _token_count(_READ_AT, 20.0, _RESETS_AT, window_minutes=300),
        ],
    )


def _expired_weekly_only(proc: _Proc) -> None:
    """Pane %6, 2026-09-28: the only weekly record was from a week already ended."""
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_BEFORE,
        [
            _session_meta(_ID_BEFORE),
            _token_count("2026-09-21T05:55:49.000Z", 5.0, _RESET_LAST_WEEK),
        ],
    )


def _sub_agents_only(proc: _Proc) -> None:
    """Sub-agents naming a main thread whose own file is not held here."""
    proc.hold_lock(_CODEX_PGID + 7, _ID_AFTER)
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_AFTER,
        [
            _session_meta(_ID_AFTER, parent=_ID_BEFORE),
            _token_count(_READ_AT, 48.0, _RESETS_AT),
        ],
    )


def _main_lock_released(proc: _Proc) -> None:
    """The main thread's file is still open but it no longer holds that lock."""
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_BEFORE,
        [_session_meta(_ID_BEFORE), _token_count(_READ_AT, 48.0, _RESETS_AT)],
    )
    proc.hold_lock(_CODEX_PGID + 7, _ID_AFTER)
    proc.hold_rollout(
        _CODEX_PGID + 7,
        _ID_AFTER,
        [_session_meta(_ID_AFTER, parent=_ID_BEFORE)],
    )


@pytest.mark.parametrize(
    "arrange",
    [
        _no_rollout,
        _no_record,
        _no_lock,
        _two_main_sessions,
        _just_cleared,
        _sub_agents_only,
        _main_lock_released,
        _other_limits_only,
        _five_hour_codex_limit,
        _expired_weekly_only,
    ],
    ids=[
        "no-rollout-yet",
        "no-record",
        "no-lock",
        "two-main-sessions",
        "just-cleared",
        "sub-agents-only",
        "main-lock-released",
        "other-limits-only",
        "five-hour-codex-limit",
        "expired-weekly-only",
    ],
)
def test_the_quota_falls_back_to_the_status_panel_when_the_file_cannot_answer(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
    arrange: Callable[[_Proc], None],
) -> None:
    arrange(proc)
    pane = _Pane(
        [_NAMED_TITLE_READY],
        [_pane(), _TYPED_STATUS, _pane(body=_STATUS_ECHOED)],
    )
    _join(watch, monkeypatch, pane.run)

    result = watch.report_quota()

    assert "weekly 99% left" in result, result
    assert "14:41 on 8 Aug" in result, result
    assert ("tmux", "send-keys", "-t", "%55", "-l", "/status") in pane.keys


def test_the_quota_falls_back_when_there_is_no_process_table(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(watch, "PROC_ROOT", tmp_path / "absent")
    pane = _Pane(
        [_NAMED_TITLE_READY],
        [_pane(), _TYPED_STATUS, _pane(body=_STATUS_ECHOED)],
    )
    _join(watch, monkeypatch, pane.run)

    assert "weekly 99% left" in watch.report_quota()


# The v0.157.0 panel is about nineteen rows, so a 25-row pane clips its top, echo line
# included. Panel rows as observed on 2026-09-28, directory and thread name replaced.
_CLIPPED_PANEL = [
    "│                                                                     │",
    "│ Visit https://chatgpt.com/codex/settings/usage for up-to-date       │",
    "│ information on rate limits and credits                              │",
    "│                                                                     │",
    "│  Model:                       GPT-6-Sol (reasoning xhigh)           │",
    "│  Directory:                   ~/projects/example                    │",
    "│  Thread name:                 Example task                          │",
    f"│  Session:                     {_ID_BEFORE}  │",
    "│                                                                     │",
    "│  Weekly limit:                [██████████░░░░░░░░░░] 51% left "
    "(resets 3:58 AM on 4 Oct)",
    "│  Luna Reserve Weekly limit:   [████████████████████] 100% left "
    "(resets 6:11 PM on 5 Oct)",
    "╰─────────────────────────────────────────────────────────────────────╯",
]
_CLIPPED_SCREEN = "\n".join(
    [
        *_CLIPPED_PANEL,
        "",
        f"\x1b[1m{_CURSOR}\x1b[0m Ask Codex to do anything",
        "",
        "  GPT-6-Sol xhigh · Example task · Context 58% left · Ready",
    ]
)


def test_a_panel_clipped_by_a_short_pane_is_reported_as_too_short(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Observed on pane %104, 2026-09-28: a 25-row pane hid the `/status` echo line.

    The figures were on screen, but without the echo a fresh panel cannot be told from
    a stale one, so this still refuses; what changes is that the refusal says why.
    """
    monkeypatch.setattr(watch, "PROC_ROOT", tmp_path / "absent")
    monkeypatch.setattr(watch, "RESPONSE_POLLS", 2)

    def run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "#{pane_height}":
            return "25\n"
        return pane.run(argv)

    pane = _Pane([_NAMED_TITLE_READY], [_pane(), _TYPED_STATUS, _CLIPPED_SCREEN])
    _join(watch, monkeypatch, run)

    with pytest.raises(watch.MonitorError, match=r"25 lines tall.*too short"):
        watch.report_quota()


def test_a_panel_whose_echo_alone_is_cut_off_is_reported_as_too_short(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Observed on a scratch 25-row pane, 2026-09-28: the border fit, its echo not."""
    monkeypatch.setattr(watch, "PROC_ROOT", tmp_path / "absent")
    monkeypatch.setattr(watch, "RESPONSE_POLLS", 2)
    screen = "\n".join(
        [
            "",
            "╭─────────────────────────────────────────────────────────────────────╮",
            "│  >_ OpenAI Codex (v0.157.0)                                         │",
            _CLIPPED_SCREEN,
        ]
    )

    def run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "#{pane_height}":
            return "25\n"
        return pane.run(argv)

    pane = _Pane([_NAMED_TITLE_READY], [_pane(), _TYPED_STATUS, screen])
    _join(watch, monkeypatch, run)

    with pytest.raises(watch.MonitorError, match=r"25 lines tall.*too short"):
        watch.report_quota()


def test_a_status_panel_that_never_drew_is_still_not_called_too_short(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A stale panel beneath its own echo is not a clipped one."""
    monkeypatch.setattr(watch, "PROC_ROOT", tmp_path / "absent")
    monkeypatch.setattr(watch, "RESPONSE_POLLS", 2)
    stale = _pane(body=_STATUS_STALE)
    pane = _Pane([_NAMED_TITLE_READY], [stale, _TYPED_STATUS, stale])
    _join(watch, monkeypatch, pane.run)

    with pytest.raises(watch.MonitorError, match="drew no status panel"):
        watch.report_quota()


class _ClearingPane(_Pane):
    """A pane whose Codex takes a new session lock when `/clear` is submitted."""

    def __init__(
        self,
        titles: list[str],
        bodies: list[str],
        on_clear: Callable[[], None],
    ) -> None:
        super().__init__(titles, bodies)
        self.on_clear = on_clear
        self.typed = ""

    def run(self, argv: tuple[str, ...]) -> str:
        if "send-keys" in argv and "-l" in argv:
            self.typed = argv[-1]
        elif "send-keys" in argv and argv[-1] == "Enter" and self.typed == "/clear":
            self.on_clear()
        return super().run(argv)


def test_a_clear_is_confirmed_by_a_new_session_lock_without_typing_status(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
) -> None:
    """The old lock is still held just after a clear (2026-09-28); one is added."""
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    pane = _ClearingPane(
        [_NAMED_TITLE_READY, _TITLE_AFTER_CLEAR, _TITLE_AFTER_CLEAR_READY],
        [_pane(), _TYPED_CLEAR, _pane(percent=100)],
        lambda: proc.hold_lock(pid, _ID_AFTER),
    )
    _join(watch, monkeypatch, pane.run)

    result = watch.run_slash_command("/clear")

    assert f"{_ID_BEFORE} -> {_ID_AFTER}" in result, result
    assert "Ready, context 100% left" in result, result
    assert pane.keys == [
        ("tmux", "send-keys", "-t", "%55", "-l", "/clear"),
        ("tmux", "send-keys", "-t", "%55", "Enter"),
    ]


def test_a_new_lock_under_a_stale_ready_title_waits_for_the_restart(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
) -> None:
    """Observed 2026-09-28: 0.22s after Enter the new lock was held and the title still
    read Ready; it went to Starting for about a second and then back to Ready. A pane
    handed back in that window is refused by the next dispatch as not Ready.
    """
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    pane = _ClearingPane(
        [
            _NAMED_TITLE_READY,
            _NAMED_TITLE_READY,
            _TITLE_AFTER_CLEAR,
            _TITLE_AFTER_CLEAR_READY,
        ],
        [_pane(), _TYPED_CLEAR, _pane(percent=100)],
        lambda: proc.hold_lock(pid, _ID_AFTER),
    )
    _join(watch, monkeypatch, pane.run)

    result = watch.run_slash_command("/clear")

    assert _ID_AFTER in result, result
    assert "Ready" in watch.pane_status("%55"), "handed back while still starting"


def test_a_clear_that_took_no_new_session_is_not_reported_as_done(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
) -> None:
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    monkeypatch.setattr(watch, "SETTLE_POLLS", 3)
    pane = _ClearingPane(
        [_NAMED_TITLE_READY],
        [_pane(), _TYPED_CLEAR, _pane()],
        lambda: None,
    )
    _join(watch, monkeypatch, pane.run)

    with pytest.raises(watch.MonitorError, match=r"no new session.*did not run"):
        watch.run_slash_command("/clear")


def test_a_compaction_is_checked_against_the_held_sessions_without_typing_status(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
) -> None:
    proc.hold_lock(_CODEX_PGID + 7, _ID_BEFORE)
    compacted = _pane(percent=100, body=["• acknowledged", "", "• Context compacted"])
    pane = _Pane(
        [_NAMED_TITLE_READY],
        [_pane(percent=96), _TYPED_COMPACT, compacted],
    )
    _join(watch, monkeypatch, pane.run)

    result = watch.run_slash_command("/compact")

    assert "96% -> 100%" in result, result
    assert f"session {_ID_BEFORE} unchanged" in result, result
    assert pane.keys == [
        ("tmux", "send-keys", "-t", "%55", "-l", "/compact"),
        ("tmux", "send-keys", "-t", "%55", "Enter"),
    ]


def test_a_compaction_that_took_a_new_session_refuses(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    proc: _Proc,
) -> None:
    pid = _CODEX_PGID + 7
    proc.hold_lock(pid, _ID_BEFORE)
    compacted = _pane(percent=100, body=["• acknowledged", "", "• Context compacted"])
    pane = _Pane(
        [_NAMED_TITLE_READY],
        [_pane(percent=96), _TYPED_COMPACT, compacted],
    )

    def run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "Enter":
            proc.hold_lock(pid, _ID_AFTER)
        return pane.run(argv)

    _join(watch, monkeypatch, run)

    with pytest.raises(watch.MonitorError, match=_ID_AFTER):
        watch.run_slash_command("/compact")
