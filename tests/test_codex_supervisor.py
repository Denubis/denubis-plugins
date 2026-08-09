"""Behaviour tests for the Codex supervision monitor.

Migrated from the eald-prototype repo (google-live), `postgres-schema-53` at commit
7981a6a, `tests/test_codex_watch.py`. The monitor supervises a Codex pane and has
nothing to do with any one project's domain, so its tests belong beside the tool
rather than in whichever repo happened to grow it.

Two upstream tests did not come across.

`test_legacy_pane_shells_stay_removed` asserted eald's `scripts/` no longer holds
`codex-send.sh`, `codex-status.sh` or `codex-tail.sh`. Those files never existed here,
so the assertion cannot fail in this repo and reports nothing. It guards eald's own
consolidation and stays there.

`test_project_hook_configuration_relays_supported_events` read `ROOT/.codex/hooks.json`
and pinned a real contract: five relayed events, a five-second timeout, and a command
ending `/scripts/codex-watch.sh" --hook`. That contract still matters, but it describes
how a *consuming project* wires itself to the tool, and this repo is the tool's home
rather than a consumer. Restoring it needs a shipped hooks template plus a decision on
how an installed plugin's script path is referenced, which is open. Recorded here so
the contract is not lost by omission.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "plugins" / "denubis-external-agents" / "scripts" / "codex_supervisor.py"
)

# A Ready pane always draws this footer, and the dispatch floor reads its meter to
# decide whether the pane can still hold an answer. The send fixtures below carried
# no footer, which made them panes no Codex has ever rendered; the floor refused them
# for that reason rather than for the one each test is about. Shape captured from pane
# %55 on 2026-08-01, with a percentage comfortably above the floor.
FOOTER = "  weekly 99% left · google-live · main · Context 96% left · R…"


@pytest.fixture(scope="module")
def watch() -> ModuleType:
    """Load the monitor only after proving its implementation exists."""
    assert MODULE_PATH.is_file(), f"{MODULE_PATH} has not been implemented"
    spec = importlib.util.spec_from_file_location("codex_supervisor", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so dataclasses resolve __module__ during class creation.
    sys.modules["codex_supervisor"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("title", "content"),
    [
        ("⠋ Working | google-live", ""),
        ("⠹ Waiting | google-live", ""),
        ("Waiting for background terminal (12m 04s)", ""),
        ("Context compacted", ""),
        ("Future transient vocabulary", "streaming a diff"),
    ],
)
def test_transient_and_unknown_snapshots_default_to_busy(
    watch: ModuleType,
    title: str,
    content: str,
) -> None:
    """Routine or unknown progress can never become an idle notification."""
    observation = watch.classify_snapshot(title, content)

    assert observation.kind is watch.ObservationKind.BUSY


def test_ready_snapshot_distinguishes_question_from_completion(
    watch: ModuleType,
) -> None:
    question = watch.classify_snapshot(
        "Ready | google-live",
        "• The implementation choice changes the contract.\n  Should I proceed?",
    )
    completion = watch.classify_snapshot(
        "Ready | google-live",
        "• Implemented the monitor and verified its focused tests.",
    )

    assert question.kind is watch.ObservationKind.QUESTION
    assert completion.kind is watch.ObservationKind.DONE
    assert question.key != completion.key


def test_distinct_approval_commands_have_distinct_stable_keys(
    watch: ModuleType,
) -> None:
    first = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git status\nPress enter to confirm",
    )
    repeated = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git status\nPress enter to confirm",
    )
    second = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git diff\nPress enter to confirm",
    )

    assert first.kind is watch.ObservationKind.APPROVAL
    assert first.key == repeated.key
    assert first.key != second.key


def test_approval_key_ignores_stale_commands_above_current_prompt(
    watch: ModuleType,
) -> None:
    clean = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git status\nPress enter to confirm",
    )
    with_history = watch.classify_snapshot(
        "Action Required",
        "old transcript\n$ git diff\nmore history\n"
        "Would you like to run this command?\n$ git status\nPress enter to confirm",
    )

    assert with_history.key == clean.key


def test_complete_stale_approval_does_not_shadow_current_approval(
    watch: ModuleType,
) -> None:
    current = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git diff\nPress enter to confirm",
    )
    with_history = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git status\nPress enter to confirm\n"
        "• Continued after approval.\n"
        "Would you like to run this command?\n$ git diff\nPress enter to confirm",
    )

    assert with_history.key == current.key


def test_ready_snapshot_ignores_stale_approval_history(
    watch: ModuleType,
) -> None:
    observation = watch.classify_snapshot(
        "Ready | google-live",
        "Would you like to run this command?\n$ git status\nPress enter to confirm\n"
        "• Finished cleanly.",
    )

    assert observation.kind is watch.ObservationKind.DONE


def test_recognized_fatal_snapshot_is_a_crash(watch: ModuleType) -> None:
    observation = watch.classify_snapshot(
        "Codex",
        "stream disconnected before completion",
    )

    assert observation.kind is watch.ObservationKind.CRASH


def test_running_tool_output_that_mentions_a_fatal_error_stays_busy(
    watch: ModuleType,
) -> None:
    observation = watch.classify_snapshot(
        "⠋ Working | google-live",
        "test fixture: fatal error\nstill running",
    )

    assert observation.kind is watch.ObservationKind.BUSY


def test_initial_ready_is_silent_then_actionable_events_emit_once(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState()
    ready = watch.classify_snapshot("Ready", "• Finished.")
    busy = watch.classify_snapshot("⠋ Working", "")
    approval = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ uv run pytest",
    )
    question = watch.classify_snapshot("Ready", "• Should I continue?")
    done = watch.classify_snapshot("Ready", "• Finished cleanly.")

    transition = watch.advance(state, ready)
    assert transition.action is None

    outputs = []
    for observation in (busy, approval, approval, busy, question, question, busy, done):
        transition = watch.advance(transition.state, observation)
        if transition.action is not None:
            outputs.append(transition.action.kind)

    assert outputs == [
        watch.ObservationKind.APPROVAL,
        watch.ObservationKind.QUESTION,
        watch.ObservationKind.DONE,
    ]


def test_busy_flicker_never_emits_or_rearms_completion(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState()
    observations = [
        watch.classify_snapshot("⠋ Working", ""),
        watch.classify_snapshot("⠙ Waiting", ""),
        watch.classify_snapshot("Waiting for background terminal", ""),
        watch.classify_snapshot("Ready", "• Finished."),
        watch.classify_snapshot("⠹ Waiting", ""),
        watch.classify_snapshot("Ready", "• Finished."),
    ]

    actions = []
    for observation in observations:
        transition = watch.advance(state, observation)
        state = transition.state
        if transition.action is not None:
            actions.append(transition.action.kind)

    assert actions == [watch.ObservationKind.DONE]


def test_select_codex_pane_requires_exactly_one_candidate(
    watch: ModuleType,
) -> None:
    assert watch.select_codex_pane(
        "%1\tbash\t101\n%2\tcodex\t202\n%3\tpython\t303\n"
    ) == watch.PaneCandidate("%2", 202)

    with pytest.raises(watch.MonitorError, match="no Codex pane"):
        watch.select_codex_pane("%1\tbash\t101\n")

    with pytest.raises(watch.MonitorError, match="multiple Codex panes"):
        watch.select_codex_pane("%2\tcodex\t202\n%3\tcodex\t303\n")


def test_select_codex_pane_accepts_zero_id(watch: ModuleType) -> None:
    """Tmux allocates pane ID zero in a fresh server."""
    assert watch.select_codex_pane("%0\tcodex\t202\n") == watch.PaneCandidate(
        "%0",
        202,
    )


@pytest.mark.parametrize(
    "rows",
    [
        "%2\tcodex\t202\textra\n%3\tcodex\t303\n",
        "%2\tcodex\tnot-a-pid\n",
        "not-a-pane\tcodex\t202\n",
    ],
)
def test_select_codex_pane_rejects_malformed_rows(
    watch: ModuleType,
    rows: str,
) -> None:
    with pytest.raises(watch.MonitorError, match="malformed tmux pane row"):
        watch.select_codex_pane(rows)


def test_discovery_lists_only_callers_exact_window(watch: ModuleType) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[:2] == ("tmux", "display-message"):
            return "@17\n"
        if argv[:2] == ("tmux", "list-panes"):
            return "%8\tcodex\t880\n"
        return "991\n"

    pane = watch.discover_codex_pane("%4", fake_run)

    assert pane == watch.PaneRef("%8", 991)
    assert calls == [
        ("tmux", "display-message", "-p", "-t", "%4", "#{window_id}"),
        (
            "tmux",
            "list-panes",
            "-t",
            "@17",
            "-F",
            "#{pane_id}\t#{pane_current_command}\t#{pane_pid}",
        ),
        ("ps", "-o", "tpgid=", "-p", "880"),
    ]
    assert all("-a" not in call for call in calls)


def test_discovery_rejects_unresolved_foreground_process_group(
    watch: ModuleType,
) -> None:
    def fake_run(argv: tuple[str, ...]) -> str:
        if argv[:2] == ("tmux", "display-message"):
            return "@17\n"
        if argv[:2] == ("tmux", "list-panes"):
            return "%8\tcodex\t880\n"
        return "not-a-process-group\n"

    with pytest.raises(watch.MonitorError, match="foreground process"):
        watch.discover_codex_pane("%4", fake_run)


def test_spawn_refuses_multiple_joined_codex_panes(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def reject_ambiguous_window() -> str:
        raise watch.MonitorError(
            "multiple Codex panes in Claude's current tmux window: %8, %9"
        )

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        return "%10\n"

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", reject_ambiguous_window)
    monkeypatch.setattr(watch, "run_command", fake_run)

    with pytest.raises(watch.MonitorError, match="multiple Codex panes"):
        watch.spawn_pane()

    assert all(call[:2] != ("tmux", "split-window") for call in calls)


def test_spawn_execs_codex_and_sets_default_pane_label(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[-1] == "#{pane_current_path}":
            return "/worktrees/postgres-schema-53\n"
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    pane_id = watch.spawn_pane()

    assert pane_id == "%10"
    assert calls == [
        ("tmux", "display-message", "-p", "-t", "%4", "#{pane_current_path}"),
        (
            "tmux",
            "split-window",
            "-h",
            "-t",
            "%4",
            "-c",
            "/worktrees/postgres-schema-53",
            "-P",
            "-F",
            "#{pane_id}",
            (
                "exec codex -c check_for_update_on_startup=false "
                "-s workspace-write -a on-request"
            ),
        ),
        (
            "tmux",
            "set-option",
            "-p",
            "-t",
            "%10",
            "@codex_label",
            "postgres-schema-53",
        ),
    ]


def test_spawn_contains_codex_rather_than_asking_per_command(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Containment is the sandbox, not a dialog for every command.

    A pane spawned with neither `-s` nor `-a` inherits whatever the config or the
    built-in default gives, and a verification pass of probes and pytest runs then
    raises one dialog per command. The sandbox is what actually bounds the damage,
    so it is set explicitly and codex is left to escalate only when it needs to
    leave the workspace.
    """
    calls: list[tuple[str, ...]] = []

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[-1] == "#{pane_current_path}":
            return "/worktrees/postgres-schema-53\n"
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    watch.spawn_pane()

    spawned = next(argv[-1] for argv in calls if argv[:2] == ("tmux", "split-window"))
    assert "-s workspace-write" in spawned, (
        f"spawn must bound writes to the workspace; got {spawned!r}"
    )
    assert "-a on-request" in spawned, (
        f"spawn must let codex escalate rather than ask per command; got {spawned!r}"
    )


def test_spawn_sets_explicit_pane_label(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[-1] == "#{pane_current_path}":
            return "/worktrees/postgres-schema-53\n"
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    watch.spawn_pane("lesson-schema")

    assert calls[-1] == (
        "tmux",
        "set-option",
        "-p",
        "-t",
        "%10",
        "@codex_label",
        "lesson-schema",
    )


def test_label_option_reaches_spawn(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels: list[str | None] = []

    def fake_spawn(label: str | None = None) -> str:
        labels.append(label)
        return "%10"

    monkeypatch.setattr(watch, "spawn_pane", fake_spawn)

    args = watch.parse_args(["--spawn", "--label", "lesson-schema"])
    assert watch.run_verb(args) == 0
    assert labels == ["lesson-schema"]


def test_send_refuses_non_ready_pane_before_loading_text(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = False

    def fake_run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "#{pane_title}":
            return "⠋ Working | google-live\n"
        return ""

    def fake_load(*_args: object, **_kwargs: object) -> None:
        nonlocal loaded
        loaded = True

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", fake_load)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    with pytest.raises(watch.MonitorError, match="not Ready"):
        watch.send_message("%8", "Do the next task.")

    assert not loaded


def test_send_refuses_nonempty_composer_before_loading_text(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = False

    def fake_run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "#{pane_title}":
            return "Ready | google-live\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return (
                f"• Earlier response\n{watch.PROMPT_MARKER} unfinished message\n"
                "? for shortcuts\n"
            )
        return ""

    def fake_load(*_args: object, **_kwargs: object) -> None:
        nonlocal loaded
        loaded = True

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", fake_load)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    with pytest.raises(watch.MonitorError, match="composer holds"):
        watch.send_message("%8", "Do the next task.")

    assert not loaded


def test_send_treats_dim_placeholder_as_an_empty_composer(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex renders its composer hint faint; hint text is not typed content.

    Captured verbatim from a live pane on 2026-07-23, where the guard read the
    hint as an unfinished message and refused every send.
    """
    status_reads = 0
    placeholder = (
        "\x1b[0m\x1b[48;2;65;69;76m\n"
        f"\x1b[1m{watch.PROMPT_MARKER}\x1b[0m\x1b[48;2;65;69;76m "
        "\x1b[2mImplement {feature}\x1b[0m\x1b[48;2;65;69;76m\n"
        f"{FOOTER}\n"
    )

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal status_reads
        if argv[-1] == "#{pane_title}":
            status_reads += 1
            return "Ready | google-live\n" if status_reads == 1 else "⠋ Working\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return placeholder
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    assert watch.send_message("%8", "Do the next task.") == "submitted to %8"


def test_send_still_refuses_typed_text_alongside_colour(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Colour codes must not become a way to smuggle a half-typed message past."""
    typed = (
        f"\x1b[1m{watch.PROMPT_MARKER}\x1b[0m\x1b[48;2;65;69;76m "
        "half a thought\x1b[0m\n"
    )

    def fake_run(argv: tuple[str, ...]) -> str:
        if argv[-1] == "#{pane_title}":
            return "Ready | google-live\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return typed
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    with pytest.raises(watch.MonitorError, match="composer holds"):
        watch.send_message("%8", "Do the next task.")


def test_guard_distinguishes_an_undrawn_composer_from_a_full_one(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pane too short to draw a composer must not be reported as holding text.

    Codex sizes its TUI to the pane, so a short pane renders no composer line at
    all and `_composer_text` returns None. The guard refused that correctly but
    announced it as "composer is not empty", which sends the reader looking for
    typed text that was never there. Observed 2026-08-09 on a live 127x5 codex
    pane whose whole capture was five lines of status bar, while a 182x41 pane of
    the same Codex build drew its composer normally and passed the guard.

    No capture flag recovers this: the composer was never drawn, so it is not in
    the scrollback either. The only honest move is to say the pane is too short.
    """
    height_reads = 0

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal height_reads
        if argv[-1] == "#{pane_title}":
            return "Ready | integration-review\n"
        if argv[-1] == "#{pane_height}":
            height_reads += 1
            return "5\n"
        if argv[:2] == ("tmux", "capture-pane"):
            # Five lines of status bar. No prompt marker anywhere.
            return f"\x1b[2m────\x1b[0m\n{FOOTER}\n"
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    with pytest.raises(watch.MonitorError) as caught:
        watch.send_message("%46", "Do the next task.")

    message = str(caught.value)
    assert "5 lines" in message, f"height not reported: {message}"
    assert "composer is not empty" not in message, (
        f"an undrawn composer is still being reported as a full one: {message}"
    )
    assert height_reads == 1


def test_send_preflights_ready_empty_composer_before_submitting(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    status_reads = 0

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal status_reads
        if argv[-1] == "#{pane_title}":
            events.append("status")
            status_reads += 1
            return "Ready | google-live\n" if status_reads == 1 else "⠋ Working\n"
        if argv[:2] == ("tmux", "capture-pane"):
            events.append("capture")
            return (
                f"• Earlier response\n{watch.PROMPT_MARKER} \n? for shortcuts\n"
                f"{FOOTER}\n"
            )
        if argv[:2] == ("tmux", "paste-buffer"):
            events.append("paste")
        if argv[:2] == ("tmux", "send-keys"):
            events.append("enter")
        return ""

    def fake_load(*_args: object, **_kwargs: object) -> None:
        events.append("load")

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", fake_load)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    result = watch.send_message("%8", "Do the next task.")

    assert result == "submitted to %8"
    assert events == [
        "status",
        "capture",
        "load",
        "paste",
        "capture",
        "enter",
        "status",
    ], "the capture between paste and Enter is the paste-landed check"


def test_send_does_not_call_a_collapsed_paste_submitted(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A long paste is drawn as a placeholder, so its own text is never on screen.

    Captured from a live pane on 2026-07-31, where a 1584-character paste rendered
    as a cyan `[Pasted Content N chars]`. Reading the absent text as a composer that
    had accepted and cleared reported a message still sitting there unsent.
    """
    message = "Investigate the failing import contract, and name the slice. " * 26
    empty = f"• Earlier response\n{watch.PROMPT_MARKER} \n? for shortcuts\n{FOOTER}\n"
    collapsed = (
        "• Earlier response\n"
        "\x1b[0m\x1b[48;2;65;69;76m\n"
        f"\x1b[1m{watch.PROMPT_MARKER}\x1b[0m\x1b[48;2;65;69;76m "
        f"\x1b[38;5;6m[Pasted Content {len(message)} chars]\x1b[39m\n"
        "? for shortcuts\n"
    )
    pasted = False

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal pasted
        if argv[-1] == "#{pane_title}":
            return "Ready | google-live\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return collapsed if pasted else empty
        if argv[:2] == ("tmux", "paste-buffer"):
            pasted = True
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    with pytest.raises(watch.MonitorError, match="not submitted"):
        watch.send_message("%8", message)


def test_send_refuses_a_paste_whose_char_count_is_not_the_message(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The placeholder reports a count, and the sender knows what it sent.

    Comparing the two is the one cheap check a partial paste cannot pass, so a
    disagreement stops the send before Enter rather than running whatever
    fraction of the message arrived.
    """
    message = "Investigate the failing import contract."
    empty = f"• Earlier response\n{watch.PROMPT_MARKER} \n? for shortcuts\n{FOOTER}\n"
    truncated = f"{watch.PROMPT_MARKER} \x1b[38;5;6m[Pasted Content 12 chars]\x1b[39m\n"
    pasted = False
    enters = 0

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal pasted, enters
        if argv[-1] == "#{pane_title}":
            return "Ready | google-live\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return truncated if pasted else empty
        if argv[:2] == ("tmux", "paste-buffer"):
            pasted = True
        if argv[:2] == ("tmux", "send-keys"):
            enters += 1
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    with pytest.raises(watch.MonitorError, match="12 chars"):
        watch.send_message("%8", message)

    assert enters == 0, "a partial paste must not be submitted"


def test_send_submits_a_paste_whose_char_count_matches(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A placeholder counting the whole message is the paste landing intact."""
    message = "Investigate the failing import contract."
    empty = f"• Earlier response\n{watch.PROMPT_MARKER} \n? for shortcuts\n{FOOTER}\n"
    landed = (
        f"{watch.PROMPT_MARKER} "
        f"\x1b[38;5;6m[Pasted Content {len(message)} chars]\x1b[39m\n"
    )
    pasted = False
    status_reads = 0

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal pasted, status_reads
        if argv[-1] == "#{pane_title}":
            status_reads += 1
            return "Ready | google-live\n" if status_reads == 1 else "⠋ Working\n"
        if argv[:2] == ("tmux", "capture-pane"):
            return landed if pasted else empty
        if argv[:2] == ("tmux", "paste-buffer"):
            pasted = True
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    assert watch.send_message("%8", message) == "submitted to %8"


def test_send_reads_a_cleared_composer_as_a_submission(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A composer that empties has submitted, whether or not the title is caught.

    Codex can finish a short turn between polls, so `Working` is a signal that
    can be missed. Guards the collapsed-paste fix against becoming a refusal of
    everything.
    """
    empty = f"• Earlier response\n{watch.PROMPT_MARKER} \n? for shortcuts\n{FOOTER}\n"
    captures = 0

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal captures
        if argv[-1] == "#{pane_title}":
            return "Ready | google-live\n"
        if argv[:2] == ("tmux", "capture-pane"):
            captures += 1
            if captures == 2:
                return f"• Earlier response\n{watch.PROMPT_MARKER} Do the next\n"
            return empty
        return ""

    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.setattr(watch.subprocess, "run", lambda *_a, **_k: None)
    monkeypatch.setattr(watch.time, "sleep", lambda _: None)

    assert watch.send_message("%8", "Do the next task.") == "submitted to %8"


def test_send_prompt_leaves_write_scope_to_prompt(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "04-implement.md"
    prompt.write_text("# Output contract\nWrite code in the worktree.\n")
    sent: list[tuple[str, str]] = []

    monkeypatch.setattr(watch, "joined_pane", lambda: "%8")
    monkeypatch.setattr(
        watch,
        "send_message",
        lambda pane, message, **_: (
            sent.append((pane, message)) or f"submitted to {pane}"
        ),
    )

    result = watch.send_prompt(str(prompt))

    assert sent == [
        (
            "%8",
            f"Read {prompt.as_posix()} and carry out that task exactly. "
            f"{watch.CODEX_PING_INSTRUCTION}",
        )
    ]
    assert result == "submitted to %8: 04-implement.md"


def test_one_shot_verbs_are_mutually_exclusive(watch: ModuleType) -> None:
    with pytest.raises(SystemExit):
        watch.parse_args(["--tail", "--status"])


def test_monitor_tool_has_no_stale_default_pane_id() -> None:
    assert "%133" not in MODULE_PATH.read_text()


def test_topology_tracker_tolerates_one_miss_but_reports_loss(
    watch: ModuleType,
) -> None:
    target = watch.PaneRef("%8", 880)
    tracker = watch.TopologyTracker(target=target, miss_limit=2)

    first_miss = tracker.observe(None)
    recovered = first_miss.tracker.observe(target)
    second_first_miss = recovered.tracker.observe(None)
    lost = second_first_miss.tracker.observe(None)

    assert first_miss.crash is None
    assert recovered.crash is None
    assert second_first_miss.crash is None
    assert lost.crash is not None
    assert lost.crash.kind is watch.ObservationKind.CRASH


def test_topology_tracker_rejects_replaced_codex_process(
    watch: ModuleType,
) -> None:
    tracker = watch.TopologyTracker(
        target=watch.PaneRef("%8", 880),
        miss_limit=2,
    )

    result = tracker.observe(watch.PaneRef("%8", 881))

    assert result.crash is not None
    assert result.crash.kind is watch.ObservationKind.CRASH


def test_permission_hook_uses_command_keyed_sanitized_event(
    watch: ModuleType,
) -> None:
    first = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )
    repeated = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )
    second = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git diff"},
        }
    )

    assert first is not None
    assert repeated is not None
    assert second is not None
    assert first.kind is watch.ObservationKind.APPROVAL
    assert first.key == repeated.key
    assert first.key != second.key
    assert json.loads(watch.serialize_observation(first)) == {
        "correlation_key": first.correlation_key,
        "kind": "approval",
        "key": first.key,
        "scoped": True,
    }


@given(st.text(min_size=1))
def test_hook_transport_never_contains_raw_private_fields(
    watch: ModuleType,
    private_text: str,
) -> None:
    payload: dict[str, Any] = {
        "hook_event_name": "PermissionRequest",
        "turn_id": "turn-1",
        "tool_name": "Bash",
        "tool_input": {"command": private_text},
        "prompt": private_text,
        "tool_response": private_text,
        "transcript_path": private_text,
    }

    observation = watch.normalize_hook(payload)

    assert observation is not None
    transported = json.loads(watch.serialize_observation(observation))
    assert set(transported) == {"correlation_key", "kind", "key", "scoped"}
    assert transported["kind"] == "approval"
    assert re.fullmatch(r"[0-9a-f]{64}", transported["key"])
    assert re.fullmatch(r"[0-9a-f]{64}", transported["correlation_key"])


def test_hook_and_snapshot_of_same_action_deduplicate(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState(seen_activity=True)
    hook_approval = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )
    hook_stop = watch.normalize_hook(
        {
            "hook_event_name": "Stop",
            "turn_id": "turn-2",
            "last_assistant_message": "Finished cleanly.",
        }
    )
    assert hook_approval is not None
    assert hook_stop is not None

    observations = [
        hook_approval,
        watch.classify_snapshot(
            "Action Required",
            "Would you like to run this command?\n$ git status\nPress enter to confirm",
        ),
        hook_stop,
        watch.classify_snapshot("Ready", "• Finished cleanly."),
    ]
    actions = []
    for observation in observations:
        transition = watch.advance(state, observation)
        state = transition.state
        if transition.action is not None:
            actions.append(transition.action.kind)

    assert actions == [
        watch.ObservationKind.APPROVAL,
        watch.ObservationKind.DONE,
    ]


def test_snapshot_then_hook_of_same_action_deduplicates(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState(seen_activity=True)
    snapshot = watch.classify_snapshot(
        "Action Required",
        "Would you like to run this command?\n$ git status\nPress enter to confirm",
    )
    hook = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )
    assert hook is not None

    first = watch.advance(state, snapshot)
    second = watch.advance(first.state, hook)

    assert first.action is not None
    assert second.action is None


def test_identical_hook_actions_in_different_turns_each_emit(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState(seen_activity=True)
    first = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )
    second = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-2",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )
    assert first is not None
    assert second is not None

    first_transition = watch.advance(state, first)
    second_transition = watch.advance(first_transition.state, second)

    assert first_transition.action is not None
    assert second_transition.action is not None


def test_identical_stop_messages_in_different_turns_each_emit(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState(seen_activity=True)
    observations = [
        watch.normalize_hook(
            {
                "hook_event_name": "Stop",
                "turn_id": turn_id,
                "last_assistant_message": "Finished cleanly.",
            }
        )
        for turn_id in ("turn-1", "turn-2")
    ]
    assert all(observation is not None for observation in observations)

    actions = []
    for observation in observations:
        assert observation is not None
        transition = watch.advance(state, observation)
        state = transition.state
        actions.append(transition.action)

    assert all(action is not None for action in actions)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("The contract is ambiguous. Should I proceed?", "question"),
        ("Implemented and verified the requested monitor.", "done"),
    ],
)
def test_stop_hook_distinguishes_question_and_done(
    watch: ModuleType,
    message: str,
    expected: str,
) -> None:
    observation = watch.normalize_hook(
        {
            "hook_event_name": "Stop",
            "turn_id": "turn-7",
            "last_assistant_message": message,
        }
    )

    assert observation is not None
    assert observation.kind.value == expected


@pytest.mark.parametrize(
    "event_name",
    ["SessionStart", "UserPromptSubmit", "PostToolUse"],
)
def test_activity_hooks_are_busy(
    watch: ModuleType,
    event_name: str,
) -> None:
    observation = watch.normalize_hook({"hook_event_name": event_name})

    assert observation is not None
    assert observation.kind is watch.ObservationKind.BUSY


def test_malformed_or_unknown_hooks_are_ignored(watch: ModuleType) -> None:
    assert watch.normalize_hook([]) is None
    assert watch.normalize_hook({"hook_event_name": "FutureEvent"}) is None


def test_hook_send_without_listener_is_silent_success(
    watch: ModuleType,
    tmp_path: Path,
) -> None:
    sent = watch.send_hook_observation(
        watch.Observation(watch.ObservationKind.BUSY),
        "%42",
        runtime_dir=tmp_path,
    )

    assert sent is False


def test_hook_sender_wakes_matching_pane_receiver(
    watch: ModuleType,
    tmp_path: Path,
) -> None:
    expected = watch.Observation(
        watch.ObservationKind.APPROVAL,
        "a" * 64,
    )

    with watch.HookReceiver("%42", runtime_dir=tmp_path) as receiver:
        assert watch.send_hook_observation(
            expected,
            "%42",
            runtime_dir=tmp_path,
        )
        assert receiver.receive(0.1) == expected
