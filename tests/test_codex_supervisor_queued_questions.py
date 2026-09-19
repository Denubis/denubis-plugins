"""Codex's queued-question widget is a question, not a sandbox approval.

Codex 0.154.0 registers `request_user_input_async` whenever the model advertises it
in `experimental_supported_tools` (`codex-rs/core/src/tools/spec_plan.rs` on `main`,
read 2026-09-19 through context7; not verified against the 0.154.0 tag). When the
model uses it the TUI draws a collapsed widget above the composer and puts
`[ ! ] Action Required` in the pane title, where it stays while the footer still
reads `Working` and Codex keeps going.

Observed on pane %161 on 2026-09-19, supervising a live session:

- the monitor announced `NEEDS APPROVAL` about nineteen times in thirty minutes,
  several within seconds of each other, because the widget's `· 15s` countdown
  redraws and the approval branch keys on the whole screen when it can find no
  command;
- `--approve` cannot answer the widget at all (`approval_choice` refuses, correctly,
  because no dialog is pending), so every one of those lines named an action the
  driver had no way to take;
- `--message` and `--send` refused with `is not Ready: '[ ! ] Action Required | …'`,
  which reads like a sandbox dialog and is not one, so the supervisor could not
  deliver the human's ruling and fell back to writing it into a ticket file.

The expectations below come from what the monitor promises — four kinds, each
meaning what it says, each waiting thing announced once — rather than from the
branch order that produced the failure. The last two cases keep the repair honest:
a real dialog drawn while a question is queued is still an approval, and a pane
that is merely not Ready must still say so plainly.

Fixture text is the pane and title recorded by the dispatcher on %161.
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

# The title stays this while Codex works underneath it. The thread name deliberately
# contains no question wording, so a refusal that merely echoes the title cannot pass
# a test asking whether the refusal named the queued question.
_QUEUED_TITLE = (
    "[ ! ] Action Required | breeze-narrate | main | Follow authoring "
    "specification | gpt-5.6-sol xhigh"
)
_FOOTER = (
    "  Follow authoring specification · Context 57% left · breeze-narrate · "
    "main · Working"
)


def _queued_pane(*, countdown: str | None = "15s", questions: int = 1) -> str:
    """The collapsed widget above the composer, as Codex draws it.

    The countdown is a hard-coded thirty-second expiry that ticks once a second and
    disappears once the widget is expanded or snoozed, leaving `? 1 question`.
    """
    tick = f" · {countdown}" if countdown else ""
    return "\n".join(
        [
            "• Ran rg -n 'authoring' docs/",
            "",
            "• Queued follow-up inputs",
            f"  ? {questions} question{'' if questions == 1 else 's'}{tick}",
            "    alt + , to answer",
            f"{_CURSOR} Ask Codex to do anything",
            _FOOTER,
        ]
    )


# A real sandbox dialog drawn while a question happens to be queued. The driver can
# and must answer this one.
_APPROVAL_WHILE_QUEUED = "\n".join(
    [
        "• Queued follow-up inputs",
        "  ? 1 question · 15s",
        "    alt + , to answer",
        "",
        "  $ uv run pytest tests/unit",
        "",
        "  Would you like to run this command?",
        f"{_CURSOR} 1. Yes, proceed (y)",
        "  2. No, and tell Codex what to do differently (esc)",
        "",
        _FOOTER,
    ]
)


# What the composer looked like after Brian answered one of these by hand on
# 2026-09-19: alt+, put the question into the composer as a quoted line and he typed
# the answer beneath it. That is ONE observation of the after-state, not of the
# expanded widget, and it is the only rendering these verbs were built against.
_EXPANDED_PANE = "\n".join(
    [
        "• Queued follow-up inputs",
        "  ? 1 question",
        "    alt + , to answer",
        f"{_CURSOR} > Question for Brian: which schema governs, the old or the new?",
        "",
        _FOOTER,
    ]
)


def _answered_pane(answer: str) -> str:
    return "\n".join(
        [
            "• Queued follow-up inputs",
            "  ? 1 question",
            f"{_CURSOR} > Question for Brian: which schema governs?",
            f"  {answer}",
            "",
            _FOOTER,
        ]
    )


_SETTLED_PANE = "\n".join(
    [
        "• Continued after the answer.",
        f"{_CURSOR} Ask Codex to do anything",
        _FOOTER,
    ]
)
_READY_TITLE = "Ready | breeze-narrate | main | Follow authoring specification"


class _ScriptedPane:
    """A scripted tmux pane, replacing the one external boundary these verbs have.

    Titles and bodies advance independently and hold their last value, so a verb
    that polls sees a pane that settles rather than one that runs off a list.
    """

    def __init__(self, titles: list[str], bodies: list[str]) -> None:
        self.titles = list(titles)
        self.bodies = list(bodies)
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: tuple[str, ...]) -> str:
        self.calls.append(argv)
        if argv[-1] == "#{pane_title}":
            return (self.titles.pop(0) if len(self.titles) > 1 else self.titles[0]) + (
                "\n"
            )
        if "capture-pane" in argv:
            return self.bodies.pop(0) if len(self.bodies) > 1 else self.bodies[0]
        return ""

    @property
    def keys(self) -> list[tuple[str, ...]]:
        return [argv for argv in self.calls if "send-keys" in argv]


def _install(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    pane: _ScriptedPane,
) -> _ScriptedPane:
    monkeypatch.setattr(watch, "joined_pane", lambda: "%161")
    monkeypatch.setattr(watch, "run_command", pane.run)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)
    return pane


@pytest.fixture(scope="module")
def watch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_supervisor", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so dataclasses resolve __module__ during class creation.
    sys.modules["codex_supervisor"] = module
    spec.loader.exec_module(module)
    return module


def test_a_queued_question_is_reported_as_a_question(watch: ModuleType) -> None:
    """`--approve` cannot answer this, so announcing it as an approval is a lie."""
    observation = watch.classify_snapshot(_QUEUED_TITLE, _queued_pane())

    assert observation.kind is watch.ObservationKind.QUESTION, (
        f"a queued follow-up question was announced as {observation.kind}; the "
        f"driver has no verb that answers it, and --approve refuses it outright"
    )


def test_the_expiry_countdown_is_not_a_new_waiting_thing(watch: ModuleType) -> None:
    """One question queued once is one event, however many times its clock redraws."""
    state = watch.MonitorState(seen_activity=True)
    emitted = []
    for countdown in ("15s", "14s", "13s", None):
        transition = watch.advance(
            state,
            watch.classify_snapshot(_QUEUED_TITLE, _queued_pane(countdown=countdown)),
        )
        state = transition.state
        if transition.action is not None:
            emitted.append(transition.action.kind)

    assert emitted == [watch.ObservationKind.QUESTION], (
        f"the ticking countdown produced {len(emitted)} events: {emitted}"
    )


def test_a_second_queued_question_is_a_new_waiting_thing(watch: ModuleType) -> None:
    """Deduplication must not silence a question Codex added to the queue."""
    state = watch.MonitorState(seen_activity=True)
    emitted = []
    for questions in (1, 1, 2):
        transition = watch.advance(
            state,
            watch.classify_snapshot(_QUEUED_TITLE, _queued_pane(questions=questions)),
        )
        state = transition.state
        if transition.action is not None:
            emitted.append(transition.action.kind)

    assert emitted == [
        watch.ObservationKind.QUESTION,
        watch.ObservationKind.QUESTION,
    ]


def test_a_real_dialog_under_a_queued_question_is_still_an_approval(
    watch: ModuleType,
) -> None:
    """The repair must not buy silence by calling every Action Required a question."""
    observation = watch.classify_snapshot(_QUEUED_TITLE, _APPROVAL_WHILE_QUEUED)

    assert observation.kind is watch.ObservationKind.APPROVAL


def test_send_refusal_names_the_queued_question_rather_than_the_title(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A supervisor carrying a human ruling must learn why it cannot deliver it.

    `is not Ready: '[ ! ] Action Required | …'` reads like a sandbox dialog, sends
    the reader to `--approve`, and `--approve` then refuses too. The refusal has to
    name the widget, because nothing this tool types can answer it.
    """
    typed: list[tuple[str, ...]] = []

    def fake_run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "#{pane_title}":
            return f"{_QUEUED_TITLE}\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return _queued_pane()
        typed.append(argv)
        return ""

    def fake_load(*_args: object, **_kwargs: object) -> None:
        typed.append(("tmux", "load-buffer"))

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", fake_load)
    monkeypatch.setattr(watch.time, "sleep", lambda _seconds: None)

    with pytest.raises(watch.MonitorError) as caught:
        watch.send_message("%161", "Brian ruled: keep the existing schema.")

    message = str(caught.value)
    assert "question" in message.casefold(), (
        f"the refusal does not say a question is blocking it: {message}"
    )
    assert "--question" in message and "--answer" in message, (
        f"the refusal names no way through; the supervisor has two: {message}"
    )
    assert not typed, f"a refused send still touched the pane: {typed}"


# ------------------------------------------------- opening and answering the widget
#
# Brian, 2026-09-19: "fuckit, for now, make it be able to alt , and just type in
# answers", after "worst case, multiple fucking calls to open it and answer if we
# cannot stop it from running in you=made sessions". Two verbs, separate calls, built
# against the one after-the-fact observation recorded above and UNPROVEN against a
# live pane. Every guard that does not need the expanded layout still applies.


def test_question_refuses_a_pane_with_no_queued_question(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No widget, no keystroke. The verbs exist for one state and only that one."""
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_READY_TITLE], [_SETTLED_PANE]),
    )

    with pytest.raises(watch.MonitorError, match="no queued question"):
        watch.open_queued_question()

    assert pane.keys == [], f"a refused --question still typed: {pane.keys}"


def test_question_refuses_a_pending_approval_dialog(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any keystroke answers a dialog on screen, including the expansion key."""
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_QUEUED_TITLE], [_APPROVAL_WHILE_QUEUED]),
    )

    with pytest.raises(watch.MonitorError, match="pending approval"):
        watch.open_queued_question()

    assert pane.keys == []


def test_question_sends_only_the_expansion_key_and_reports_the_pane(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One keystroke, then read. Nothing is typed into the composer by this verb."""
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_QUEUED_TITLE], [_queued_pane(), _EXPANDED_PANE]),
    )

    result = watch.open_queued_question()

    assert pane.keys == [("tmux", "send-keys", "-t", "%161", "M-,")], (
        f"--question must send alt+comma and nothing else; sent {pane.keys}"
    )
    assert "which schema governs" in result, (
        f"--question did not carry the question back: {result!r}"
    )


def test_answer_refuses_a_pane_with_no_queued_question(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_READY_TITLE], [_SETTLED_PANE]),
    )

    with pytest.raises(watch.MonitorError, match="no queued question"):
        watch.answer_queued_question("the new schema")

    assert pane.keys == []


def test_answer_refuses_a_pending_approval_dialog(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_QUEUED_TITLE], [_APPROVAL_WHILE_QUEUED]),
    )

    with pytest.raises(watch.MonitorError, match="pending approval"):
        watch.answer_queued_question("the new schema")

    assert pane.keys == []


def test_answer_types_literally_then_submits_as_a_separate_call(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Typed, seen on screen, and only then submitted — the send_message discipline.

    Success is evidence rather than silence: the queued question has to be gone
    from the pane before this reports that it answered.
    """
    answer = "the new schema governs"
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane(
            [_QUEUED_TITLE, _QUEUED_TITLE, _READY_TITLE],
            [_EXPANDED_PANE, _answered_pane(answer), _SETTLED_PANE],
        ),
    )

    result = watch.answer_queued_question(answer)

    assert pane.keys == [
        ("tmux", "send-keys", "-t", "%161", "-l", answer),
        ("tmux", "send-keys", "-t", "%161", "Enter"),
    ], f"the answer must be typed literally and submitted separately; got {pane.keys}"
    assert "%161" in result


def test_answer_raises_when_the_question_is_still_queued_after_enter(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Silence is not success: an unmoved widget means the answer did not land."""
    answer = "the new schema governs"
    _install(
        watch,
        monkeypatch,
        _ScriptedPane([_QUEUED_TITLE], [_answered_pane(answer)]),
    )

    with pytest.raises(watch.MonitorError) as caught:
        watch.answer_queued_question(answer)

    message = str(caught.value)
    assert "still" in message.casefold(), message
    assert "Question for Brian" in message, (
        f"the refusal carries no pane tail: {message}"
    )


def test_answer_refuses_when_it_cannot_see_what_it_typed(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never press Enter on a composer whose contents could not be confirmed."""
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_QUEUED_TITLE], [_EXPANDED_PANE]),
    )

    with pytest.raises(watch.MonitorError, match="not on screen"):
        watch.answer_queued_question("the new schema governs")

    assert ("tmux", "send-keys", "-t", "%161", "Enter") not in pane.keys


def test_answer_refuses_a_multi_line_answer(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keystrokes carry newlines as Enter, which would submit half an answer."""
    pane = _install(
        watch,
        monkeypatch,
        _ScriptedPane([_QUEUED_TITLE], [_EXPANDED_PANE]),
    )

    with pytest.raises(watch.MonitorError, match="multi-line"):
        watch.answer_queued_question("first line\nsecond line")

    assert pane.keys == []


def test_the_widget_verbs_are_one_shot_and_mutually_exclusive(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both reach their function through the parser, and neither shares a call."""
    seen: list[str] = []
    monkeypatch.setattr(
        watch, "open_queued_question", lambda: seen.append("question") or "opened"
    )
    monkeypatch.setattr(
        watch, "answer_queued_question", lambda text: seen.append(text) or "answered"
    )

    assert watch.run_verb(watch.parse_args(["--question"])) == 0
    assert watch.run_verb(watch.parse_args(["--answer", "option B"])) == 0
    assert seen == ["question", "option B"]

    with pytest.raises(SystemExit):
        watch.parse_args(["--question", "--answer", "option B"])
