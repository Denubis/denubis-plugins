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

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
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
    identities = iter(session_ids or [_ID_BEFORE, _ID_BEFORE])
    monkeypatch.setattr(watch, "joined_target", lambda: target)
    monkeypatch.setattr(watch, "joined_pane", lambda: target.pane_id)
    monkeypatch.setattr(
        watch,
        "_probe_session_identity",
        lambda _target: next(identities),
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
