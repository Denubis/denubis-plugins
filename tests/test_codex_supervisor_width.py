"""Phone-width behavior, with synthetic rollout/proc fixtures and no live sends."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import test_codex_supervisor_slash as slash

if TYPE_CHECKING:
    from types import ModuleType

watch = slash.watch
proc = slash.proc

_NEW = slash._ID_AFTER
_OLD = slash._ID_BEFORE
_OTHER = slash._ID_OTHER
_PID = slash._CODEX_PGID + 7
_CURSOR = slash._CURSOR
_EMPTY = f"{_CURSOR} \x1b[2mAsk Codex\x1b[0m\n  example · Working\n"


def _usage(used: object = 107995, window: object = 475000) -> str:
    # Numeric skeleton of our own 2026-11-02 live sample. Cumulative usage is
    # deliberately over the window; the wide meter for latest=107995 read 79.
    return json.dumps(
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {"total_tokens": 653667},
                    "last_token_usage": {"total_tokens": used},
                    "model_context_window": window,
                },
            },
        }
    )


@pytest.fixture
def phone(watch: ModuleType, monkeypatch: pytest.MonkeyPatch) -> slash._Pane:
    pane = slash._Pane(["Ready", "Working"], [_EMPTY])

    def run(argv: tuple[str, ...]) -> str:
        if "#{pane_width}" in argv[-1]:
            return "20 32 3\n"
        return pane.run(argv)

    slash._join(watch, monkeypatch, run)
    monkeypatch.setattr(
        watch.subprocess, "run", lambda *_a, **_k: setattr(pane, "pasted", True)
    )
    return pane


def _main(proc: slash._Proc, used: object = 107995, window: object = 475000) -> Path:
    proc.hold_lock(_PID, _OLD)
    return proc.hold_rollout(
        _PID, _OLD, [slash._session_meta(_OLD), _usage(used, window)]
    )


def test_phone_send_uses_latest_main_usage_not_cumulative_or_subagent(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    _main(proc)
    proc.hold_lock(_PID, _OTHER)
    proc.hold_rollout(
        _PID, _OTHER, [slash._session_meta(_OTHER, parent=_OLD), _usage(470000)]
    )
    assert "submitted" in watch.send_message("%55", "Continue.")
    assert phone.pasted


@pytest.mark.parametrize("verb", ["message", "send"])
@pytest.mark.parametrize("old_session_held", [False, True])
def test_first_dispatch_reports_no_model_call_even_while_old_session_is_held(
    watch: ModuleType,
    proc: slash._Proc,
    phone: slash._Pane,
    tmp_path: Path,
    *,
    verb: str,
    old_session_held: bool,
) -> None:
    if old_session_held:
        _main(proc, used=470000)
    proc.hold_lock(_PID, _NEW)
    if verb == "send":
        prompt = tmp_path / "01-task.md"
        prompt.write_text("Do the task.")
        result = watch.send_prompt(str(prompt))
    else:
        result = watch.send_message("%55", "Continue.")
    assert "submitted" in result
    assert "no model call yet" in result
    assert "100%" not in result
    assert phone.pasted


@pytest.mark.parametrize(
    "state",
    [
        "no_proc",
        "no_locks",
        "unreadable_rollout",
        "two_mains",
        "two_unwritten",
        "unwritten_with_unreadable_old",
        "unwritten_with_two_mains",
        "rollout_exists_but_not_open",
    ],
)
def test_every_other_unreadable_context_refuses_before_typing(
    watch: ModuleType,
    proc: slash._Proc,
    phone: slash._Pane,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    if state == "no_proc":
        monkeypatch.setattr(watch, "PROC_ROOT", proc.root / "absent")
    elif state == "no_locks":
        proc.hold_rollout(_PID, _OLD, [slash._session_meta(_OLD), _usage()])
    elif state == "unreadable_rollout":
        _main(proc).unlink()
    elif state in {"two_mains", "unwritten_with_two_mains"}:
        _main(proc)
        proc.hold_lock(_PID, _OTHER)
        proc.hold_rollout(_PID, _OTHER, [slash._session_meta(_OTHER), _usage()])
        if state == "unwritten_with_two_mains":
            proc.hold_lock(_PID, _NEW)
    elif state == "two_unwritten":
        proc.hold_lock(_PID, _OLD)
        proc.hold_lock(_PID, _NEW)
    elif state == "unwritten_with_unreadable_old":
        _main(proc).write_text("not JSON\n")
        proc.hold_lock(_PID, _NEW)
    elif state == "rollout_exists_but_not_open":
        proc.hold_lock(_PID, _OLD)
        proc.hold_rollout(_PID, _OLD, [slash._session_meta(_OLD), _usage(470000)])
        for fd in (proc.root / str(_PID) / "fd").iterdir():
            if "rollout-" in str(fd.readlink()):
                fd.unlink()
    with pytest.raises(watch.MonitorError):
        watch.send_message("%55", "Continue.")
    assert not phone.pasted
    assert not phone.keys


@pytest.mark.parametrize(
    "state",
    [
        "unreadable_descriptors",
        "unreadable_store",
        "deleted_rollout",
        "symlinked_store_branch",
    ],
)
def test_incomplete_discovery_never_qualifies_as_fresh(
    watch: ModuleType,
    proc: slash._Proc,
    phone: slash._Pane,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    if state == "unreadable_descriptors":
        proc.hold_lock(_PID, _NEW)
        proc.process(_PID + 1, slash._CODEX_PGID)
        original = Path.iterdir

        def unreadable(path: Path):
            if path == proc.root / str(_PID + 1) / "fd":
                raise PermissionError("unreadable process descriptors")
            return original(path)

        monkeypatch.setattr(Path, "iterdir", unreadable)
    elif state == "unreadable_store":
        proc.hold_lock(_PID, _NEW)
        original_stat = Path.stat

        def unreadable_stat(path: Path, **kwargs: object):
            if path == proc.codex_home / "sessions":
                raise PermissionError("unreadable session store")
            return original_stat(path, **kwargs)

        monkeypatch.setattr(Path, "stat", unreadable_stat)
    elif state == "deleted_rollout":
        rollout = _main(proc)
        for fd in (proc.root / str(_PID) / "fd").iterdir():
            if "rollout-" in str(fd.readlink()):
                fd.unlink()
                fd.symlink_to(str(rollout) + " (deleted)")
        rollout.unlink()
    elif state == "symlinked_store_branch":
        proc.hold_lock(_PID, _NEW)
        sessions = proc.codex_home / "sessions"
        sessions.mkdir()
        other = proc.codex_home / "stored-sessions"
        other.mkdir()
        (other / f"rollout-example-{_NEW}.jsonl").write_text(_usage(470000))
        (sessions / "2026").symlink_to(other, target_is_directory=True)
    with pytest.raises(watch.MonitorError):
        watch.send_message("%55", "Continue.")
    assert not phone.pasted
    assert not phone.keys


@pytest.mark.parametrize("used, allowed", [(336100, True), (340730, False)])
def test_rollout_context_respects_the_existing_thirty_percent_floor(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane, used: int, allowed: bool
) -> None:
    _main(proc, used=used)
    if allowed:
        assert "submitted" in watch.send_message("%55", "Continue.")
    else:
        with pytest.raises(watch.MonitorError, match="29%"):
            watch.send_message("%55", "Continue.")
        assert not phone.pasted


@pytest.mark.parametrize(
    "used, window", [(True, 475000), (-1, 475000), (1000, None), (1000, 0)]
)
def test_invalid_usage_is_not_a_context_reading(
    watch: ModuleType,
    proc: slash._Proc,
    phone: slash._Pane,
    used: object,
    window: object,
) -> None:
    _main(proc, used, window)
    with pytest.raises(watch.MonitorError):
        watch.send_message("%55", "Continue.")
    assert not phone.pasted


def test_on_screen_meter_has_priority_over_rollout(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    _main(proc, used=470000)
    phone.bodies[:] = [_EMPTY + "Context 80% left\n"]
    assert "submitted" in watch.send_message("%55", "Continue.")


def test_later_invalid_usage_does_not_reuse_an_older_passing_reading(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    rollout = _main(proc)
    with rollout.open("a") as handle:
        handle.write(_usage(1000, None) + "\n")
    with pytest.raises(watch.MonitorError):
        watch.send_message("%55", "Continue.")
    assert not phone.pasted


@pytest.mark.parametrize(
    "state", ["not_ready", "approval", "composer", "no_composer", "floor", "unknown"]
)
def test_phone_refusals_name_actual_width_and_height(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane, state: str
) -> None:
    if state == "not_ready":
        phone.titles[:] = ["Working"]
    elif state == "approval":
        phone.bodies[:] = [slash._PENDING_APPROVAL_PANE]
    elif state == "composer":
        phone.bodies[:] = [f"{_CURSOR} unfinished\n"]
    elif state == "no_composer":
        phone.bodies[:] = ["footer only\n"]
    elif state == "floor":
        _main(proc, used=470000)
    with pytest.raises(watch.MonitorError) as caught:
        watch.send_message("%55", "Continue.")
    assert "20 columns" in str(caught.value)
    assert "32 lines" in str(caught.value)
    assert not phone.pasted


def test_phone_compact_confirms_the_marker_with_rollout_context(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    _main(proc, used=300000)
    phone.titles[:] = ["Ready"]
    phone.bodies[:] = [_EMPTY, slash._TYPED_COMPACT, "• Context compacted\n" + _EMPTY]
    result = watch.run_slash_command("/compact")
    assert "compacted" in result
    assert "38% -> 38%" in result
    assert "unchanged" in result


def test_wrapped_quota_panel_reports_width_without_calling_it_missing(
    watch: ModuleType,
    proc: slash._Proc,
    phone: slash._Pane,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    phone.titles[:] = ["Ready"]
    phone.bodies[:] = [
        _EMPTY,
        slash._TYPED_STATUS,
        "/status\n╭────────────────╮\n│ Weekly\n│ limit:\n│ 99% left\n"
        "│ (resets 12:00\n│ on 3 Nov)\n╰────────────────╯\n" + _EMPTY,
    ]
    monkeypatch.setattr(watch, "RESPONSE_POLLS", 1)
    with pytest.raises(watch.MonitorError) as caught:
        watch.report_quota()
    message = str(caught.value)
    assert "too narrow" in message
    assert "20 columns" in message
    assert "32 lines" in message


def test_wrapped_approval_opener_still_blocks_a_send_and_reports_approval(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    _main(proc)
    phone.bodies[:] = [
        "Would you like to\nrun this command?\n$ true\n"
        f"{_CURSOR} 1. Yes, proceed (y)\n  2. No (esc)\n" + _EMPTY
    ]
    observation = watch.classify_snapshot("Ready", phone.bodies[0])
    assert observation.kind is watch.ObservationKind.APPROVAL
    with pytest.raises(watch.MonitorError, match="pending approval"):
        watch.send_message("%55", "Continue.")
    assert not phone.pasted


def test_wrapped_dialog_taller_than_twelve_rows_still_blocks_a_send(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    _main(proc)
    phone.bodies[:] = [
        "Would you like to\nrun this command?\n$ true\n"
        + "\n".join(["  reason continues"] * 12)
        + f"\n{_CURSOR} 1. Yes, proceed (y)\n  2. No (esc)\n"
        + _EMPTY
    ]
    assert (
        watch.classify_snapshot("Ready", phone.bodies[0]).kind
        is watch.ObservationKind.APPROVAL
    )
    with pytest.raises(watch.MonitorError, match="pending approval"):
        watch.send_message("%55", "Continue.")
    assert not phone.pasted


def test_wrapped_fatal_message_is_a_monitor_crash(watch: ModuleType) -> None:
    observation = watch.classify_snapshot(
        "Ready",
        f"• stream disconnected\n  before completion\n{_CURSOR}\n",
    )
    assert observation.kind is watch.ObservationKind.CRASH


def test_wrapped_compaction_marker_is_confirmed(
    watch: ModuleType, proc: slash._Proc, phone: slash._Pane
) -> None:
    _main(proc)
    phone.titles[:] = ["Ready"]
    phone.bodies[:] = [
        _EMPTY,
        slash._TYPED_COMPACT,
        "• Context\n  compacted\n" + _EMPTY,
    ]
    assert "compacted" in watch.run_slash_command("/compact")


def test_wrapped_question_count_is_already_readable(watch: ModuleType) -> None:
    observation = watch.classify_snapshot(
        "Action Required",
        f"• Queued follow-up inputs\n ? 1\n question · 15s\n{_CURSOR}\n",
    )
    assert observation.kind is watch.ObservationKind.QUESTION


def test_clipped_widget_count_does_not_confirm_an_answer(
    watch: ModuleType, phone: slash._Pane
) -> None:
    phone.titles[:] = ["Action Required"]
    phone.bodies[:] = [
        f"? 1 question\n{_CURSOR}\n",
        f"? 1 question\n{_CURSOR} Yes\n",
        f"{_CURSOR}\n",
    ]
    with pytest.raises(watch.MonitorError):
        watch.answer_queued_question("Yes")


def test_wrapped_answer_still_refuses_before_enter_with_geometry(
    watch: ModuleType, phone: slash._Pane
) -> None:
    phone.titles[:] = ["Action Required"]
    phone.bodies[:] = [
        f"? 1 question\n{_CURSOR}\n",
        f"? 1 question\n{_CURSOR} Use the\n  current schema\n",
    ]
    with pytest.raises(watch.MonitorError) as caught:
        watch.answer_queued_question("Use the current schema")
    assert "20 columns" in str(caught.value)
    assert "32 lines" in str(caught.value)
    assert all(call[-1] != "Enter" for call in phone.keys)
