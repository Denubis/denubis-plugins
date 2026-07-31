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

It selects by reading the option's own label rather than assuming a position, and it
answers only the affirmative that grants nothing beyond the command on screen. A
`Yes, and don't ask again` grants standing permission for everything matching, which
changes the security posture of the session and belongs to the human. Where two
affirmatives survive that reading, the ambiguity is itself the refusal, so a wording
that slips the standing-grant vocabulary stops rather than being guessed at.

Codex draws two dialog shapes. The older one offers `Yes` and `No` on a single line.
The commoner one puts each option on its own line, sits a standing grant between the
two, and prints in each label the key that selects it. Both fixtures below were
captured from live panes, the first by way of the attested fixture in
`test_codex_supervisor_classify.py` and the second from pane %12 on 2026-07-31, where
sending `y` was observed to answer the dialog and clear it.
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

_CURSOR = "\N{SINGLE RIGHT-POINTING ANGLE QUOTATION MARK}"

_STANDING_GRANT_OFFERED = [
    "  Would you like to run the following command?",
    "",
    "  Environment: local",
    "",
    "  Reason: Allow Git to write rebase metadata and update the local",
    "  pr/scaffold-stacked-base branch in this dedicated worktree?",
    "",
    "  $ git rebase origin/main",
    "",
    f"{_CURSOR} 1. Yes, proceed (y)",
    "  2. Yes, and don't ask again for commands that start with `git rebase` (p)",
    "  3. No, and tell Codex what to do differently (esc)",
    "",
    "  Press enter to confirm or esc to cancel",
]

_PENDING_THREE_OPTION = "\n".join(_STANDING_GRANT_OFFERED)

_ANSWERED_THREE_OPTION = "\n".join(
    [*_STANDING_GRANT_OFFERED, "", "• Working (1m 34s • esc to interrupt)"]
)

_REPLIED_THREE_OPTION = "\n".join(
    [
        *_STANDING_GRANT_OFFERED,
        "",
        "• Working (2m 04s • esc to interrupt)",
        "",
        "• Ran git rebase origin/main",
        "  └ Successfully rebased and updated refs/heads/pr/scaffold-stacked-base.",
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


def test_the_commoner_dialog_answers_with_the_key_printed_in_its_label(
    watch: ModuleType,
) -> None:
    """A three-option dialog is answered by the key its proceed-once option advertises.

    The expectation is the key observed to work against pane %12, not a value read
    back out of the parser: sending `y` there answered the dialog and cleared it.
    """
    assert watch.approval_choice(_PENDING_THREE_OPTION) == "y"


def test_the_standing_grant_is_passed_over_wherever_it_sits(watch: ModuleType) -> None:
    """Reordering the list must not walk the choice onto the blanket grant."""
    body = "\n".join(
        [
            "  Would you like to run the following command?",
            "",
            "  $ git rebase origin/main",
            "",
            f"{_CURSOR} 1. Yes, and don't ask again for commands that start with"
            " `git rebase` (p)",
            "  2. Yes, proceed (y)",
            "  3. No, and tell Codex what to do differently (esc)",
            "",
            "  Press enter to confirm or esc to cancel",
        ]
    )
    assert watch.approval_choice(body) == "y"


def test_two_narrow_affirmatives_are_refused_rather_than_guessed_between(
    watch: ModuleType,
) -> None:
    """Ambiguity is the backstop for a standing grant worded in some new way.

    This dialog is constructed rather than captured. Its job is to pin the property
    that survives a vocabulary miss: where the reading cannot single out one
    affirmative, the verb stops instead of picking the likelier one.
    """
    body = "\n".join(
        [
            "  Would you like to run the following command?",
            "",
            "  $ git rebase origin/main",
            "",
            f"{_CURSOR} 1. Yes, proceed (y)",
            "  2. Yes, and approve anything like it from here on (a)",
            "  3. No, and tell Codex what to do differently (esc)",
            "",
            "  Press enter to confirm or esc to cancel",
        ]
    )
    with pytest.raises(watch.MonitorError) as excinfo:
        watch.approval_choice(body)
    assert "approve anything like it" in str(excinfo.value), (
        "refusing without showing the options leaves the supervisor unable to act"
    )


def test_the_taller_dialog_names_its_command_and_nothing_else(
    watch: ModuleType,
) -> None:
    """What was approved is the command, not the slab of text drawn around it."""
    assert watch._approval_material(_PENDING_THREE_OPTION) == "git rebase origin/main"


def test_the_older_dialog_still_names_its_command(watch: ModuleType) -> None:
    """The command sits above the question here and below it on the taller dialog."""
    assert watch._approval_material(_PENDING_APPROVAL) == (
        "podman run --rm -v /tmp/evidence:/out:Z eald-test pytest -q"
    )


def test_a_command_from_the_turn_before_is_not_the_one_named(watch: ModuleType) -> None:
    """A bullet closes the previous turn, so its command cannot be read as this one."""
    body = "\n".join(
        [
            "  $ git status --porcelain",
            "• Ran git status --porcelain",
            "",
            "  Would you like to run the following command?",
            "",
            "  $ git rebase origin/main",
            "",
            f"{_CURSOR} 1. Yes, proceed (y)",
            "  2. No, and tell Codex what to do differently (esc)",
        ]
    )
    assert watch._approval_material(body) == "git rebase origin/main"


def test_an_approval_carrying_no_command_names_its_question(watch: ModuleType) -> None:
    """Not every dialog is about a shell command, so the question is the fallback."""
    body = "\n".join(
        [
            "  Would you like to apply the patch to src/main.py?",
            "",
            f"{_CURSOR} 1. Yes, proceed (y)",
            "  2. No, and tell Codex what to do differently (esc)",
        ]
    )
    assert watch._approval_material(body) == (
        "Would you like to apply the patch to src/main.py?"
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


def test_approving_the_commoner_dialog_sends_the_key_it_advertises(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole path, parser through keypress, lands on proceed-once and nothing else.

    What the result names is deliberately not asserted here. `_approval_material`
    reads a fixed window around the last marker and misses the `$` line on a dialog
    this tall, which is a defect of its own rather than one this test should pin.
    """
    calls = _fake_tmux(
        watch, monkeypatch, [_PENDING_THREE_OPTION, _ANSWERED_THREE_OPTION]
    )

    watch.approve_pending()

    keypresses = [argv for argv in calls if "send-keys" in argv]
    assert keypresses == [("tmux", "send-keys", "-t", "%237", "y")], (
        f"`p` would grant every future `git rebase`; sent {keypresses}"
    )


def test_the_answer_carries_the_first_thing_codex_did_next(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approving reports back what Codex went on to do, not just that a key landed.

    A keypress that clears a dialog says nothing about the outcome, and the outcome
    is the whole reason for approving, so the verb waits for Codex to say something
    and carries the first thing it says.
    """
    _fake_tmux(watch, monkeypatch, [_PENDING_THREE_OPTION, _REPLIED_THREE_OPTION])

    result = watch.approve_pending()

    assert result.startswith("approved on %237: git rebase origin/main"), result
    assert "Successfully rebased" in result, (
        f"the outcome is what the supervisor needs; got {result!r}"
    )
    assert "esc to interrupt" not in result, (
        "the working spinner is a status line, not a thing Codex did"
    )


def test_a_codex_that_has_not_spoken_yet_is_reported_as_working(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Waiting is bounded, and a silent pane is said to be silent, not guessed at."""
    _fake_tmux(watch, monkeypatch, [_PENDING_THREE_OPTION, _ANSWERED_THREE_OPTION])

    result = watch.approve_pending()

    assert result.startswith("approved on %237: git rebase origin/main"), result
    assert "still working" in result, result


def test_a_dialog_that_did_not_clear_is_not_reported_as_approved(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keypresses race the dialogs, so a cleared screen is checked, not assumed."""
    _fake_tmux(watch, monkeypatch, [_PENDING_APPROVAL])

    with pytest.raises(watch.MonitorError, match="did not clear"):
        watch.approve_pending()
