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
import io
import itertools
import json
import shlex
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
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


def _spawn_workdir(tmp_path: Path) -> Path:
    """A working directory that exists, because a live pane's cwd normally does.

    `spawn_pane` refuses a `#{pane_current_path}` that does not resolve, since tmux
    answers a deleted directory with a ` (deleted)` suffix and `split-window -c`
    then falls back to `$HOME`. The fixtures below therefore need a real path; the
    name is kept so the default-label assertion still reads as it did.
    """
    workdir = tmp_path / "postgres-schema-53"
    workdir.mkdir()
    return workdir


LIVE_CATALOGUE = ("codex", "debug", "models")
BUNDLED_CATALOGUE = ("codex", "debug", "models", "--bundled")

# The shape `codex debug models` printed on codex-cli 0.159.2 on 2026-09-30, cut to
# one model and the field `--spawn` rewrites. Spawn reads the catalogue before it opens
# the pane, so every fixture that reaches `split-window` has to answer that command.
SPAWN_CATALOGUE = json.dumps(
    {
        "models": [
            {
                "slug": "gpt-6-sol",
                "experimental_supported_tools": ["send_user_message_async", "clock"],
            }
        ]
    }
)


@pytest.fixture
def spawn_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Keep the catalogue `--spawn` writes out of the operator's runtime directory."""
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    return runtime


def _config_overrides(command: str) -> dict[str, object]:
    """Read a spawn command's `-c key=value` words the way Codex says it reads them.

    `codex --help` on codex-cli 0.159.2: "The `value` portion is parsed as TOML. If it
    fails to parse as TOML, the raw string is used as a literal."
    """
    overrides: dict[str, object] = {}
    for flag, word in itertools.pairwise(shlex.split(command)):
        if flag != "-c":
            continue
        key, _, raw = word.partition("=")
        try:
            overrides[key] = tomllib.loads(f"value = {raw}")["value"]
        except tomllib.TOMLDecodeError:
            overrides[key] = raw
    return overrides


def _spawn_command(calls: list[tuple[str, ...]]) -> str:
    return next(argv[-1] for argv in calls if argv[:2] == ("tmux", "split-window"))


def _pinned_catalogue(calls: list[tuple[str, ...]]) -> Path:
    """The model catalogue file the spawned Codex was told to load."""
    command = _spawn_command(calls)
    pinned = _config_overrides(command).get("model_catalog_json")
    assert isinstance(pinned, str), f"spawn pinned no model catalogue: {command!r}"
    return Path(pinned)


def _spawn_runner(
    watch: ModuleType,
    calls: list[tuple[str, ...]],
    catalogues: Mapping[tuple[str, ...], str | None],
) -> Callable[[tuple[str, ...]], str]:
    """Answer the commands `--spawn --cwd` runs; a `None` catalogue fails its command.

    A failing catalogue command raises what `run_command` raises for a non-zero exit,
    with the command's own words as the reason, so a test can tell which one failed.
    """

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[:3] == LIVE_CATALOGUE:
            reply = catalogues.get(argv)
            if reply is None:
                raise watch.MonitorError(f"{' '.join(argv)} broke for this test")
            return reply
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    return fake_run


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


def test_oversized_hook_payload_is_drained_before_return(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"x" * (watch.MAX_HOOK_BYTES + 4096)
    stdin = io.TextIOWrapper(io.BytesIO(payload))
    monkeypatch.setattr(watch.sys, "stdin", stdin)
    monkeypatch.setenv("TMUX_PANE", "%1")

    assert watch.run_hook() == 0
    assert stdin.buffer.tell() == len(payload)


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


def test_spawn_refuses_a_working_directory_that_no_longer_exists(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A deleted cwd must stop the spawn, not relocate the sandbox to $HOME.

    tmux reads the pane's working directory from `/proc/<pid>/cwd`, so a directory
    deleted under a live shell comes back as `<path> (deleted)`. `split-window -c`
    silently falls back to `$HOME` when its argument does not resolve, and the pane
    then starts codex with `-s workspace-write` rooted at the home directory — a
    sandbox over everything the operator owns, announced by nothing. Observed
    2026-09-19 on a pane whose worktree had been removed under it.
    """
    calls: list[tuple[str, ...]] = []
    removed = tmp_path / "worktrees" / "breeze-simplify"

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[-1] == "#{pane_current_path}":
            return f"{removed} (deleted)\n"
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    with pytest.raises(watch.MonitorError) as caught:
        watch.spawn_pane()

    assert str(removed) in str(caught.value), (
        f"the refusal does not name the directory it could not use: {caught.value}"
    )
    assert all(call[:2] != ("tmux", "split-window") for call in calls), (
        "codex was spawned anyway, and tmux put its sandbox in $HOME"
    )


def test_spawn_starts_codex_in_an_explicit_cwd(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
) -> None:
    """`--cwd` is what lets a supervisor whose own pane is unusable still spawn.

    Ruled by Brian, 2026-09-19: "being able to set cwd would be nice". The pane's
    own working directory is then not consulted at all, which is the point — the
    case that produced the ruling was a supervisor pane sitting in a deleted
    worktree, where reading that path is exactly what must not happen.
    """
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv == LIVE_CATALOGUE:
            return SPAWN_CATALOGUE
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    assert watch.spawn_pane(cwd=str(workdir)).splitlines()[0] == "%10"

    assert all(call[-1] != "#{pane_current_path}" for call in calls), (
        f"an explicit --cwd still read the pane's own path: {calls}"
    )
    split = next(argv for argv in calls if argv[:2] == ("tmux", "split-window"))
    assert str(workdir) in split, f"split-window did not get the given cwd: {split}"
    assert calls[-1][-1] == workdir.name, (
        f"the default label should be the given directory's name: {calls[-1]}"
    )


def test_spawn_refuses_an_explicit_cwd_that_does_not_exist(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A typo in `--cwd` must refuse for the same reason a deleted pane path does."""
    calls: list[tuple[str, ...]] = []
    missing = tmp_path / "no-such-worktree"

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        return "%10\n"

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    with pytest.raises(watch.MonitorError) as caught:
        watch.spawn_pane(cwd=str(missing))

    assert str(missing) in str(caught.value)
    assert all(call[:2] != ("tmux", "split-window") for call in calls)


def test_spawn_hands_tmux_an_absolute_cwd(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
) -> None:
    """A relative `--cwd` means this process's cwd, not the tmux server's.

    `split-window -c` resolves a relative path against whatever the server's
    directory happens to be, so a path that passed the existence check here could
    still start codex somewhere else entirely — the same silent relocation the
    deleted-directory guard exists to stop.
    """
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv == LIVE_CATALOGUE:
            return SPAWN_CATALOGUE
        return "%10\n"

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)
    monkeypatch.chdir(tmp_path)

    watch.spawn_pane(cwd=workdir.name)

    split = next(argv for argv in calls if argv[:2] == ("tmux", "split-window"))
    handed = split[split.index("-c") + 1]
    assert Path(handed).is_absolute(), f"tmux was handed a relative path: {handed!r}"
    assert Path(handed).samefile(workdir)


def test_spawn_execs_codex_and_sets_default_pane_label(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
) -> None:
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv == LIVE_CATALOGUE:
            return SPAWN_CATALOGUE
        if argv[-1] == "#{pane_current_path}":
            return f"{workdir}\n"
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)

    report = watch.spawn_pane()

    (pinned,) = spawn_runtime.rglob("*.json")
    assert report.splitlines()[0] == "%10"
    assert calls == [
        ("tmux", "display-message", "-p", "-t", "%4", "#{pane_current_path}"),
        LIVE_CATALOGUE,
        (
            "tmux",
            "split-window",
            "-h",
            "-t",
            "%4",
            "-c",
            str(workdir),
            "-P",
            "-F",
            "#{pane_id}",
            (
                "exec codex -c check_for_update_on_startup=false "
                "-s workspace-write -a on-request "
                f"-c 'model_catalog_json=\"{pinned}\"' --model gpt-6-sol "
                "-c 'model_reasoning_effort=\"xhigh\"'"
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
    tmp_path: Path,
    spawn_runtime: Path,
) -> None:
    """Containment is the sandbox, not a dialog for every command.

    A pane spawned with neither `-s` nor `-a` inherits whatever the config or the
    built-in default gives, and a verification pass of probes and pytest runs then
    raises one dialog per command. The sandbox is what actually bounds the damage,
    so it is set explicitly and codex is left to escalate only when it needs to
    leave the workspace.
    """
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv == LIVE_CATALOGUE:
            return SPAWN_CATALOGUE
        if argv[-1] == "#{pane_current_path}":
            return f"{workdir}\n"
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
    tmp_path: Path,
    spawn_runtime: Path,
) -> None:
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv == LIVE_CATALOGUE:
            return SPAWN_CATALOGUE
        if argv[-1] == "#{pane_current_path}":
            return f"{workdir}\n"
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


def test_spawn_model_arguments_are_literal_shell_words(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
) -> None:
    calls: list[tuple[str, ...]] = []

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv == LIVE_CATALOGUE:
            return SPAWN_CATALOGUE
        return "%10" if argv[:2] == ("tmux", "split-window") else ""

    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)
    model = "custom; $(touch unwanted)"
    watch.spawn_pane(cwd=str(tmp_path), model=model, reasoning_effort="high")
    command = next(call[-1] for call in calls if call[:2] == ("tmux", "split-window"))
    words = shlex.split(command)
    assert words[words.index("--model") + 1] == model
    assert words[-2:] == ["-c", 'model_reasoning_effort="high"']


def test_label_cwd_and_model_options_reach_spawn(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[tuple[str | None, str | None, str | None, str]] = []

    def fake_spawn(
        label: str | None = None,
        cwd: str | None = None,
        *,
        model: str | None,
        reasoning_effort: str,
    ) -> str:
        received.append((label, cwd, model, reasoning_effort))
        return "%10"

    monkeypatch.setattr(watch, "spawn_pane", fake_spawn)

    args = watch.parse_args(
        [
            "--spawn",
            "--label",
            "lesson-schema",
            "--cwd",
            "/srv/lesson-schema",
            "--model",
            "gpt-6-astra",
            "--reasoning-effort",
            "high",
        ]
    )
    assert watch.run_verb(args) == 0
    assert received == [("lesson-schema", "/srv/lesson-schema", "gpt-6-astra", "high")]

    # A bare --spawn passes no model: spawn_pane reads the default from the catalogue
    # it pins (tests/test_codex_supervisor_default_model.py owns that rule).
    bare = watch.parse_args(["--spawn"])
    assert watch.run_verb(bare) == 0
    assert received[-1] == (None, None, None, "xhigh")


@pytest.mark.parametrize("option", ["--model", "--reasoning-effort"])
def test_model_options_require_spawn(
    watch: ModuleType, option: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        watch.parse_args(["--clear", option, "high"])
    assert error.value.code == 2
    assert "require --spawn" in capsys.readouterr().err


def _no_joined_pane_for(watch: ModuleType) -> Callable[[], str]:
    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    return no_joined_pane


def test_spawn_pins_a_catalogue_without_the_question_tools(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A spawned Codex is never offered the async question tool at all.

    Brian, 2026-09-30: "if we can force the question widget off, that would be
    amazing", then "uh, fix it if it's fixed?". Codex registers the handler behind the
    queued-question widget only when the model's catalogue entry lists
    `request_user_input_async` or `send_user_message_async` in
    `experimental_supported_tools` (`codex-rs/core/src/tools/spec_plan.rs` on `main`),
    and `model_catalog_json` replaces the catalogue Codex loads. So the pane gets a
    copy with exactly those two names gone. Everything else is carried through as it
    was: `clock`, the different `send_message_to_user_async`, instruction text that
    merely mentions a tool, an empty list, an entry with no list, and the model and
    effort the operator asked for.
    """
    live = {
        "models": [
            {
                "slug": "gpt-6-sol",
                "context_window": 272000,
                "base_instructions": "Ask in plain text, not send_user_message_async.",
                "experimental_supported_tools": ["send_user_message_async", "clock"],
            },
            {
                "slug": "gpt-6-luna",
                "experimental_supported_tools": [
                    "request_user_input_async",
                    "send_message_to_user_async",
                    "clock",
                ],
            },
            {"slug": "gpt-5.5", "experimental_supported_tools": []},
            {"slug": "codex-auto-review"},
        ]
    }
    expected = {
        "models": [
            {
                "slug": "gpt-6-sol",
                "context_window": 272000,
                "base_instructions": "Ask in plain text, not send_user_message_async.",
                "experimental_supported_tools": ["clock"],
            },
            {
                "slug": "gpt-6-luna",
                "experimental_supported_tools": ["send_message_to_user_async", "clock"],
            },
            {"slug": "gpt-5.5", "experimental_supported_tools": []},
            {"slug": "codex-auto-review"},
        ]
    }
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)
    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", _no_joined_pane_for(watch))
    monkeypatch.setattr(
        watch,
        "run_command",
        _spawn_runner(watch, calls, {LIVE_CATALOGUE: json.dumps(live)}),
    )

    status = watch.main(
        [
            "--spawn",
            "--cwd",
            str(workdir),
            "--model",
            "gpt-6-luna",
            "--reasoning-effort",
            "low",
        ]
    )

    out = capsys.readouterr().out
    assert status == 0
    pinned = _pinned_catalogue(calls)
    assert json.loads(pinned.read_text(encoding="utf-8")) == expected
    assert pinned.is_relative_to(spawn_runtime), (
        f"the catalogue belongs in the runtime directory, not {pinned}"
    )
    assert out.splitlines()[0] == "%10", f"the pane id is no longer first: {out!r}"
    assert str(pinned) in out, f"--spawn did not say where the catalogue is: {out!r}"
    assert "codex debug models" in out, f"--spawn did not name its source: {out!r}"
    assert "--bundled" not in out, f"the live catalogue was read: {out!r}"
    command = _spawn_command(calls)
    words = shlex.split(command)
    assert words[words.index("--model") + 1] == "gpt-6-luna"
    assert _config_overrides(command)["model_reasoning_effort"] == "low"
    assert BUNDLED_CATALOGUE not in calls, "the bundled catalogue was read needlessly"


@pytest.mark.usefixtures("spawn_runtime")
@pytest.mark.parametrize(
    "live_reply",
    [
        pytest.param(None, id="command fails"),
        pytest.param("Error: could not read models cache\n", id="not JSON"),
        pytest.param(json.dumps([{"slug": "gpt-6-sol"}]), id="no models list"),
        pytest.param(
            json.dumps(
                {
                    "models": [
                        {
                            "slug": "gpt-6-sol",
                            "experimental_supported_tools": "send_user_message_async",
                        }
                    ]
                }
            ),
            id="tool list of an unknown shape",
        ),
    ],
)
def test_spawn_falls_back_to_the_bundled_catalogue_and_says_so(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    live_reply: str | None,
) -> None:
    """A live catalogue that cannot be read, or cannot be trusted to be stripped,
    gives way to the one the binary ships, still stripped, and the output says so.

    A tool list in a shape the supervisor does not recognise could still advertise the
    question tool after a strip that found nothing to remove, so it counts as a
    failure of that source rather than a catalogue to pin.
    """
    bundled = {
        "models": [
            {
                "slug": "gpt-6-sol",
                "base_instructions": "bundled",
                "experimental_supported_tools": ["send_user_message_async", "clock"],
            }
        ]
    }
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)
    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", _no_joined_pane_for(watch))
    monkeypatch.setattr(
        watch,
        "run_command",
        _spawn_runner(
            watch,
            calls,
            {LIVE_CATALOGUE: live_reply, BUNDLED_CATALOGUE: json.dumps(bundled)},
        ),
    )

    status = watch.main(["--spawn", "--cwd", str(workdir)])

    out = capsys.readouterr().out
    assert status == 0
    assert json.loads(_pinned_catalogue(calls).read_text(encoding="utf-8")) == {
        "models": [
            {
                "slug": "gpt-6-sol",
                "base_instructions": "bundled",
                "experimental_supported_tools": ["clock"],
            }
        ]
    }
    assert "--bundled" in out, f"--spawn did not say it used the bundled one: {out!r}"
    if live_reply is None:
        assert "codex debug models broke" in out, (
            f"--spawn did not say why the live one failed: {out!r}"
        )


def test_spawn_refuses_when_no_catalogue_can_be_stripped(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without a catalogue to strip, Codex would start with the widget; so no Codex."""
    calls: list[tuple[str, ...]] = []
    workdir = _spawn_workdir(tmp_path)
    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", _no_joined_pane_for(watch))
    monkeypatch.setattr(watch, "run_command", _spawn_runner(watch, calls, {}))

    status = watch.main(["--spawn", "--cwd", str(workdir)])

    captured = capsys.readouterr()
    assert status == 2
    assert all(call[:2] != ("tmux", "split-window") for call in calls), (
        "codex was spawned without prevention"
    )
    assert "codex debug models broke" in captured.err, captured.err
    assert "codex debug models --bundled broke" in captured.err, captured.err
    assert captured.out == ""
    assert list(spawn_runtime.rglob("*.json")) == []


@pytest.mark.parametrize("same_catalogue", [True, False], ids=["same", "refreshed"])
def test_a_second_spawn_leaves_the_first_panes_catalogue_alone(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    spawn_runtime: Path,
    same_catalogue: bool,
) -> None:
    """The first pane is still running on its file when the second pane is spawned."""
    first = {"models": [{"slug": "gpt-6-sol", "experimental_supported_tools": []}]}
    second = (
        first
        if same_catalogue
        else {"models": [{"slug": "gpt-6.1-sol", "experimental_supported_tools": []}]}
    )
    workdir = _spawn_workdir(tmp_path)
    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", _no_joined_pane_for(watch))

    first_calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        watch,
        "run_command",
        _spawn_runner(watch, first_calls, {LIVE_CATALOGUE: json.dumps(first)}),
    )
    assert watch.main(["--spawn", "--cwd", str(workdir)]) == 0
    first_pinned = _pinned_catalogue(first_calls)
    first_inode = first_pinned.stat().st_ino
    first_bytes = first_pinned.read_bytes()

    second_calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        watch,
        "run_command",
        _spawn_runner(watch, second_calls, {LIVE_CATALOGUE: json.dumps(second)}),
    )
    assert watch.main(["--spawn", "--cwd", str(workdir)]) == 0

    assert first_pinned.stat().st_ino == first_inode, "the first file was replaced"
    assert first_pinned.read_bytes() == first_bytes, "the first file was rewritten"
    assert json.loads(first_pinned.read_text(encoding="utf-8")) == first
    second_pinned = _pinned_catalogue(second_calls)
    assert json.loads(second_pinned.read_text(encoding="utf-8")) == second


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
    the scrollback either. The only honest move is to say the pane is too short,
    and to name the usual cause — a window that has accumulated agent panes
    until tmux squeezed this one — so the message states an action rather than
    only a diagnosis.
    """
    height_reads = 0

    def fake_run(argv: tuple[str, ...]) -> str:
        nonlocal height_reads
        if argv[-1] == "#{pane_title}":
            return "Ready | integration-review\n"
        if argv[-1] == "#{pane_height} #{window_panes}":
            height_reads += 1
            return "5 7\n"
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
    assert "7 panes" in message, f"window pane count not reported: {message}"
    assert "composer is not empty" not in message, (
        f"an undrawn composer is still being reported as a full one: {message}"
    )
    # Both facts come from a single tmux call, not one round trip each.
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


def test_the_standard_ping_sends_questions_through_the_transcript(
    watch: ModuleType,
) -> None:
    """A question asked through Codex's own tool cannot reach the supervisor.

    `request_user_input_async` queues the question in a TUI widget, locks the pane
    title to `[ ! ] Action Required`, and expires after thirty seconds; Codex's own
    default-mode template then tells it to "continue with best judgment", which is
    the silent assumption the standing rules exist to prevent. A plain-text question
    leaves the pane `Ready`, so `--message` can carry the human's ruling back.
    """
    assert "request_user_input_async" in watch.CODEX_PING_INSTRUCTION, (
        "the ping tells codex to ask questions but not which channel to avoid, so "
        "the question it asks may be one no supervisor can answer"
    )


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


def test_permission_hook_is_an_unscoped_activity_wakeup(
    watch: ModuleType,
) -> None:
    observation = watch.normalize_hook(
        {
            "hook_event_name": "PermissionRequest",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
    )

    assert observation == watch.Observation(watch.ObservationKind.BUSY)


def test_an_auto_resolved_permission_request_emits_no_approval(
    watch: ModuleType,
) -> None:
    """Another PermissionRequest hook may allow or deny before a dialog exists."""
    state = watch.MonitorState(seen_activity=True)
    observations = [
        watch.normalize_hook(
            {
                "hook_event_name": "PermissionRequest",
                "turn_id": "turn-1",
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
            }
        ),
        watch.classify_snapshot("Working | repo", "• Ran git status"),
    ]

    actions = []
    for observation in observations:
        assert observation is not None
        transition = watch.advance(state, observation)
        state = transition.state
        if transition.action is not None:
            actions.append(transition.action.kind)

    assert actions == []


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
    assert transported == {
        "correlation_key": None,
        "kind": "busy",
        "key": None,
        "scoped": False,
    }


def test_permission_wakeup_then_live_snapshot_emits_one_approval(
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
    assert hook_approval is not None

    observations = [
        hook_approval,
        watch.classify_snapshot(
            "Action Required",
            "Would you like to run this command?\n$ git status\nPress enter to confirm",
        ),
    ]
    actions = []
    for observation in observations:
        transition = watch.advance(state, observation)
        state = transition.state
        if transition.action is not None:
            actions.append(transition.action.kind)

    assert actions == [watch.ObservationKind.APPROVAL]


def test_live_approval_then_permission_wakeup_does_not_emit_again(
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


def test_stop_hook_and_snapshot_of_same_action_deduplicate(
    watch: ModuleType,
) -> None:
    state = watch.MonitorState(seen_activity=True)
    hook = watch.normalize_hook(
        {
            "hook_event_name": "Stop",
            "turn_id": "turn-2",
            "last_assistant_message": "Finished cleanly.",
        }
    )
    assert hook is not None
    snapshot = watch.classify_snapshot("Ready", "• Finished cleanly.")

    first = watch.advance(state, hook)
    second = watch.advance(first.state, snapshot)

    assert first.action is not None
    assert second.action is None


def test_permission_hooks_in_different_turns_remain_silent(
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

    assert first_transition.action is None
    assert second_transition.action is None


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


@pytest.mark.parametrize(
    "model", ["gpt-6-astra", "gpt-6-astra-2026-09-24", "astra", "claude-fable-5"]
)
def test_restricted_model_needs_explicit_effort(watch: ModuleType, model: str) -> None:
    with pytest.raises(SystemExit) as error:
        watch.parse_args(["--spawn", "--model", model])
    assert error.value.code == 2
