"""A pending prompt is announced once and never repeated.

The monitor used to raise anything still pending again on a backoff (two minutes, five,
then ten, stopping after an hour). Brian ruled on 2026-10-08 that supervising Codex
does not need repeated reminders: every repeat he saw was caused by a permission prompt
on his own side, where a repeat cannot help, and a screen of repeats is what he came
back to.
The property under test is the one that replaced the ladder: one line per new thing,
however long the pane waits, and the same line is not re-raised after a busy flicker.

The tests drive the monitor's poll step with a fixed pane and a scripted clock, and read
what reached stdout, because stdout is the contract the host's Monitor tool consumes.
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
_PANE = "%10"
_HOUR = 3600.0


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


def _busy(watch: ModuleType) -> object:
    return watch.classify_snapshot("⠋ Working", "")


def _lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line]


def test_a_prompt_pending_for_an_hour_is_announced_exactly_once(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The same screen re-observed every poll for an hour produces one line."""
    state = watch.MonitorState(seen_activity=True)
    now = 1000.0
    while now < 1000.0 + _HOUR:
        state, crashed = watch.poll_step(state, _approval(watch), None, _PANE, now)
        assert not crashed
        now += 5.0

    lines = _lines(capsys)
    assert len(lines) == 1, (
        f"{len(lines)} lines for one pending approval; Brian (2026-10-08): supervising "
        "Codex does not need repeated reminders"
    )
    assert "NEEDS APPROVAL" in lines[0]


def test_a_busy_flicker_does_not_re_announce_the_same_prompt(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One spinner frame between two identical screens is not a new event."""
    state = watch.MonitorState(seen_activity=True)
    state, _ = watch.poll_step(state, _approval(watch), None, _PANE, 1000.0)
    state, _ = watch.poll_step(state, _busy(watch), None, _PANE, 1010.0)
    state, _ = watch.poll_step(state, _approval(watch), None, _PANE, 1020.0)

    assert len(_lines(capsys)) == 1, "the returning approval was announced again"


def test_a_different_prompt_after_the_first_is_announced(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Announce-once is per thing, not per monitor lifetime."""
    state = watch.MonitorState(seen_activity=True)
    state, _ = watch.poll_step(state, _approval(watch), None, _PANE, 1000.0)
    question = watch.Observation(
        kind=watch.ObservationKind.QUESTION,
        key="k-question",
        detail="which branch?",
        correlation_key="c-question",
    )
    state, _ = watch.poll_step(state, question, None, _PANE, 1000.0 + _HOUR)

    lines = _lines(capsys)
    assert len(lines) == 2
    assert "QUESTION" in lines[1]


def test_a_hook_event_that_matches_the_snapshot_is_not_a_second_line(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The same approval reaches the monitor as pane text and as a hook event."""
    state = watch.MonitorState(seen_activity=True)
    hook = watch.Observation(
        kind=watch.ObservationKind.APPROVAL,
        key="k-hook",
        detail="run the migration?",
        correlation_key="c-approval",
        scoped=True,
    )
    state, _ = watch.poll_step(state, _approval(watch), hook, _PANE, 1000.0)

    assert len(_lines(capsys)) == 1


def test_a_completion_still_asks_what_to_do_with_the_context(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """DONE is a decision point, and the one line it gets must say so."""
    done = watch.Observation(
        kind=watch.ObservationKind.DONE,
        key="k-done",
        detail="Finished.",
        correlation_key="c-done",
    )
    state = watch.MonitorState(seen_activity=True)
    watch.poll_step(state, done, None, _PANE, 1000.0)

    line = _lines(capsys)[0]
    assert "compact" in line and "clear" in line and "quit" in line


def test_a_crash_reports_and_ends_the_watch(
    watch: ModuleType,
    capsys: pytest.CaptureFixture[str],
) -> None:
    crash = watch.Observation(
        kind=watch.ObservationKind.CRASH,
        detail="joined Codex pane disappeared",
    )
    _, crashed = watch.poll_step(
        watch.MonitorState(seen_activity=True), crash, None, _PANE, 1000.0
    )

    assert crashed
    assert "CRASH" in _lines(capsys)[0]
