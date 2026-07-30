"""Answering a pending approval is one keypress, chosen by reading the options.

The supervisor had no sanctioned way to answer a Codex approval dialog. `--send` and
`--message` both refuse unless the pane title is `Ready` and the composer is empty, so
the only path to a dialog was a raw `tmux send-keys`, which the skill otherwise treats
as the thing you do not do. Doctrine therefore said the human answers every dialog,
which put a human on a keypress treadmill for a pass that was nothing but probes.

`approval_choice` is the decision half, kept pure so it can be tested without tmux. It
answers one question: which key selects the affirmative option on the screen in front
of me? Two properties make it safe to automate.

It refuses unless an approval is actually pending, so the verb cannot press a key into
a composer or into scrollback holding an answered dialog.

It selects by reading the option's own number rather than assuming a position, and it
refuses when no plain `Yes` is on offer. A `Yes, and don't ask again` grants standing
permission for everything matching, which changes the security posture of the session
and belongs to the human, so a dialog offering only that must stop rather than be
guessed at.

The dialog body below is the shape Codex draws, taken from the attested fixture in
`test_codex_supervisor_classify.py`, which was captured from a live pane.
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

_PENDING_APPROVAL = "\n".join(
    [
        "  $ podman run --rm -v /tmp/evidence:/out:Z eald-test pytest -q",
        "",
        "  Would you like to run this command?",
        "  > 1. Yes   2. No, and tell Codex what to do differently",
    ]
)

_ANSWERED_APPROVAL = "\n".join(
    [
        "  $ podman run --rm -v /tmp/evidence:/out:Z eald-test pytest -q",
        "",
        "  Would you like to run this command?",
        "  > 1. Yes   2. No, and tell Codex what to do differently",
        "",
        "• Ran the suite; 40 passed.",
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


def test_affirmative_option_is_selected_by_number(watch: ModuleType) -> None:
    """The plain `Yes` on a pending dialog answers with its own list number."""
    assert watch.approval_choice(_PENDING_APPROVAL) == "1"


def test_yes_is_found_wherever_it_sits_in_the_list(watch: ModuleType) -> None:
    """Selection reads the number beside `Yes` rather than assuming first position."""
    body = "\n".join(
        [
            "  $ git push --force-with-lease origin gates",
            "",
            "  Would you like to run this command?",
            "  > 1. No, and tell Codex what to do differently   2. Yes",
        ]
    )
    assert watch.approval_choice(body) == "2"


def test_refuses_when_no_approval_is_pending(watch: ModuleType) -> None:
    """An answered dialog stays in scrollback, and must not be answered twice."""
    with pytest.raises(watch.MonitorError, match="no pending approval"):
        watch.approval_choice(_ANSWERED_APPROVAL)


def test_refuses_a_standing_grant_and_reports_what_it_saw(watch: ModuleType) -> None:
    """`don't ask again` changes the session's posture, so it goes to the human."""
    body = "\n".join(
        [
            "  $ rm -rf build/",
            "",
            "  Would you like to run this command?",
            "  > 1. Yes, and don't ask again for rm   2. No, and tell Codex why",
        ]
    )
    with pytest.raises(watch.MonitorError) as excinfo:
        watch.approval_choice(body)
    assert "don't ask again for rm" in str(excinfo.value), (
        "refusing without showing the options leaves the supervisor unable to act"
    )


def _fake_tmux(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    captures: list[str],
) -> list[tuple[str, ...]]:
    """Drive the verb against scripted pane captures, recording every tmux call.

    tmux is the external boundary, so it is the thing that gets replaced. Each
    `capture-pane` consumes the next scripted body, which is how a dialog that
    clears and a dialog that does not are told apart.
    """
    calls: list[tuple[str, ...]] = []
    pending = list(captures)

    def fake_run_command(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if "capture-pane" in argv:
            return pending.pop(0) if pending else captures[-1]
        return ""

    monkeypatch.setattr(watch, "joined_pane", lambda: "%237")
    monkeypatch.setattr(watch, "run_command", fake_run_command)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    return calls


def test_approving_sends_one_key_and_reports_the_command(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One keypress answers the dialog, and the answer names what it approved."""
    calls = _fake_tmux(watch, monkeypatch, [_PENDING_APPROVAL, _ANSWERED_APPROVAL])

    result = watch.approve_pending()

    keypresses = [argv for argv in calls if "send-keys" in argv]
    assert keypresses == [("tmux", "send-keys", "-t", "%237", "1")], (
        f"a dialog answer is a single key into a select list; sent {keypresses}"
    )
    assert "eald-test pytest -q" in result


def test_a_dialog_that_did_not_clear_is_not_reported_as_approved(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keypresses race the dialogs, so a cleared screen is checked, not assumed."""
    _fake_tmux(watch, monkeypatch, [_PENDING_APPROVAL])

    with pytest.raises(watch.MonitorError, match="did not clear"):
        watch.approve_pending()
