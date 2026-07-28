"""An unanswered prompt must be raised again, on a lengthening interval.

The monitor announced each actionable event once and never repeated itself, so a
notification missed was a notification gone. On 2026-07-27 a Codex pane sat blocked on
an approval for 57 minutes while its supervisor waited on a line that had already
scrolled past, and an earlier stall the same day ran 1h51m.

Announcing once was a deliberate property, not an oversight: a stationary screen is
re-observed every poll, so an ungated repeat would emit every few seconds and train the
reader to ignore it. The repair is therefore a clock rather than a removed guard. A
pending action re-announces on a backoff, and anything that changes on screen is a fresh
event on the existing path.

Expectations here come from the operator's ruling of 2026-07-28: approvals, questions
and completions all re-announce, a crash does not because it is terminal and repeating
it is noise, and a completion asks what should happen to the pane's context rather than
reporting an all-clear. The intervals are the ruling's, not the code's; a test that
imported the schedule it checks would pass against any schedule at all.
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

# The ruling's schedule: two minutes, then five, then ten, then ten forever.
_FIRST = 120.0
_SECOND = 300.0
_STEADY = 600.0


@pytest.fixture(scope="module")
def watch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_supervisor", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so dataclasses resolve __module__ during class creation.
    sys.modules["codex_supervisor"] = module
    spec.loader.exec_module(module)
    return module


def _approval(watch: ModuleType) -> object:
    return watch.Observation(
        kind=watch.ObservationKind.APPROVAL,
        key="k-approval",
        detail="run the migration?",
        correlation_key="c-approval",
    )


def test_a_pending_approval_stays_quiet_until_the_first_interval(
    watch: ModuleType,
) -> None:
    """Silence before the interval is the anti-spam property, and must survive."""
    state = watch.arm_reminder(watch.MonitorState(), _approval(watch), 1000.0)

    _, early = watch.due_reminder(state, 1000.0 + _FIRST - 1.0)

    assert early is None, (
        "reminded before the first interval elapsed; a stationary screen is "
        "re-observed every poll, so this emits continuously"
    )


def test_a_pending_approval_is_raised_again_once_the_interval_passes(
    watch: ModuleType,
) -> None:
    """The 57-minute silence is the defect this closes."""
    state = watch.arm_reminder(watch.MonitorState(), _approval(watch), 1000.0)

    _, due = watch.due_reminder(state, 1000.0 + _FIRST)

    assert due is not None, "an approval pending past the interval was never re-raised"
    assert due.kind is watch.ObservationKind.APPROVAL


def test_the_interval_lengthens_rather_than_repeating_flatly(
    watch: ModuleType,
) -> None:
    """Backoff, so a genuinely abandoned pane nags without drumming."""
    now = 1000.0
    state = watch.arm_reminder(watch.MonitorState(), _approval(watch), now)

    gaps = []
    for _ in range(4):
        previous = now
        # Advance to whenever this reminder actually comes due.
        for _tick in range(10_000):
            state_after, due = watch.due_reminder(state, now)
            if due is not None:
                state = state_after
                break
            now += 1.0
        else:  # pragma: no cover - only reached if a reminder never comes due
            pytest.fail("reminder never came due within 10000 seconds")
        gaps.append(round(now - previous))

    assert gaps == [_FIRST, _SECOND, _STEADY, _STEADY], (
        f"backoff schedule was {gaps}, expected two minutes, five, ten, then ten"
    )


def test_a_crash_is_never_raised_again(watch: ModuleType) -> None:
    """Terminal, so repeating it is noise rather than a prompt to act."""
    crash = watch.Observation(
        kind=watch.ObservationKind.CRASH,
        detail="joined Codex pane disappeared",
    )
    state = watch.arm_reminder(watch.MonitorState(), crash, 1000.0)

    _, due = watch.due_reminder(state, 1000.0 + _STEADY * 10)

    assert due is None, "a crash was re-announced, and it cannot be acted on"


def test_a_completion_is_raised_again_like_any_other_pending_decision(
    watch: ModuleType,
) -> None:
    """DONE waits on a human choosing what happens to the pane's context."""
    done = watch.Observation(
        kind=watch.ObservationKind.DONE,
        key="k-done",
        detail="Finished.",
        correlation_key="c-done",
    )
    state = watch.arm_reminder(watch.MonitorState(), done, 1000.0)

    _, due = watch.due_reminder(state, 1000.0 + _FIRST)

    assert due is not None, "a finished pane was never raised again"
    assert due.kind is watch.ObservationKind.DONE


def test_a_completion_asks_what_to_do_with_the_context(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Finishing a task is the moment to clear or compact, so the line says so."""
    done = watch.Observation(
        kind=watch.ObservationKind.DONE,
        detail="Finished.",
    )

    watch._emit("%10", done)

    line = capsys.readouterr().out
    assert "compact" in line and "clear" in line and "quit" in line, (
        f"completion line {line!r} reports an all-clear; it should ask what happens "
        "to the pane's context, which is the decision actually waiting"
    )


def test_a_reminder_says_how_long_the_pane_has_been_waiting(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A repeat that reads identically to the first notice cannot be triaged."""
    state = watch.arm_reminder(watch.MonitorState(), _approval(watch), 1000.0)
    _, due = watch.due_reminder(state, 1000.0 + _FIRST)
    assert due is not None

    watch._emit("%10", due)

    line = capsys.readouterr().out
    assert "2m" in line, (
        f"reminder line {line!r} does not say how long the pane has been waiting, so "
        "it cannot be told apart from the original notice"
    )


def test_an_answered_approval_stops_nagging(watch: ModuleType) -> None:
    """Codex working means nothing waits on the human, so the reminder must lapse.

    Without this, answering an approval and letting Codex run for twenty minutes
    produces three reminders about a prompt that was dealt with in the first thirty
    seconds, which is the failure that teaches people to ignore the monitor.

    Dropping the reminder on busy cannot lose a live approval, because
    `classify_snapshot` matches pending approval text before falling through to busy:
    a pane genuinely waiting classifies as APPROVAL on every poll and re-arms.
    """
    state = watch.arm_reminder(watch.MonitorState(), _approval(watch), 1000.0)

    transition = watch.advance(state, watch.classify_snapshot("⠋ Working", ""))

    _, due = watch.due_reminder(transition.state, 1000.0 + _STEADY * 5)
    assert due is None, (
        "kept reminding about an approval while Codex was working; the human answered "
        "it and the monitor is now crying wolf"
    )


def test_a_changed_screen_restarts_the_schedule(watch: ModuleType) -> None:
    """A new event is not a continuation of the old wait."""
    state = watch.arm_reminder(watch.MonitorState(), _approval(watch), 1000.0)
    state, due = watch.due_reminder(state, 1000.0 + _FIRST)
    assert due is not None

    question = watch.Observation(
        kind=watch.ObservationKind.QUESTION,
        key="k-question",
        detail="which branch?",
        correlation_key="c-question",
    )
    state = watch.arm_reminder(state, question, 5000.0)

    _, early = watch.due_reminder(state, 5000.0 + _FIRST - 1.0)
    assert early is None, "the new wait inherited the old schedule's elapsed time"

    _, fresh = watch.due_reminder(state, 5000.0 + _FIRST)
    assert fresh is not None and fresh.kind is watch.ObservationKind.QUESTION
