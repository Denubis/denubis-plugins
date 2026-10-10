"""The default Codex model is read from the catalogue, not pinned to a release.

Brian, 2026-10-10: "how do we generalise this without needing to revise this each
release but also without having multi-discovery steps?", then "great" to the rule: the
default is the listed `-sol` slug with the lowest `priority` in the catalogue `--spawn`
already reads, falling back to the pinned constant when no such slug exists. Effort
stays xhigh, and an explicit `--model` still wins.

Observed on codex-cli 0.160.1 (2026-10-10): `codex debug models` lists `gpt-6.1-sol`
at priority 1, `gpt-6-astra` at 2, `gpt-6-sol` at 3, hidden models share priorities
with listed ones, and `visibility` is `list` or `hide`. The `priority` ordering is
observed, not documented.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
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
LIVE_CATALOGUE = ("codex", "debug", "models")

# Cut from `codex debug models` on codex-cli 0.160.1, 2026-10-10, to the fields the
# rule reads. The hidden model shares gpt-6-sol's priority to show hiding is honoured.
CATALOGUE = {
    "models": [
        {"slug": "gpt-6-astra", "priority": 0, "visibility": "list"},
        {"slug": "gpt-6.1-sol", "priority": 1, "visibility": "list"},
        {"slug": "gpt-6-sol", "priority": 3, "visibility": "list"},
        {"slug": "memory4-dream", "priority": 3, "visibility": "hide"},
        {"slug": "gpt-7-sol", "priority": 0, "visibility": "hide"},
        {"slug": "gpt-5.6-sol", "priority": 5, "visibility": "list"},
    ]
}


@pytest.fixture(scope="module")
def watch() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codex_supervisor", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["codex_supervisor"] = module
    spec.loader.exec_module(module)
    return module


def test_the_lowest_priority_listed_sol_slug_is_the_default(watch: ModuleType) -> None:
    assert watch.default_model(CATALOGUE) == "gpt-6.1-sol"


@pytest.mark.parametrize(
    "models",
    [
        pytest.param([], id="empty catalogue"),
        pytest.param(
            [{"slug": "gpt-6-astra", "priority": 0, "visibility": "list"}],
            id="no sol family",
        ),
        pytest.param(
            [{"slug": "gpt-7-sol", "priority": 0, "visibility": "hide"}],
            id="sol is hidden",
        ),
        pytest.param([{"slug": "gpt-6-sol"}], id="no priority or visibility"),
        pytest.param(
            [{"slug": "gpt-6-sol", "priority": "1", "visibility": "list"}],
            id="priority is not a number",
        ),
    ],
)
def test_no_candidate_means_no_default(
    watch: ModuleType, models: list[dict[str, object]]
) -> None:
    """The caller falls back to the pinned constant; the rule never guesses."""
    assert watch.default_model({"models": models}) is None


def test_the_fallback_is_still_a_sol_model(watch: ModuleType) -> None:
    """The constant the rule falls back to must itself satisfy the Astra/Fable gate."""
    assert "-sol" in watch.FALLBACK_MODEL
    assert watch.DEFAULT_REASONING_EFFORT == "xhigh"


def _spawn_calls(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    catalogue: dict[str, object],
) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[:3] == LIVE_CATALOGUE:
            return json.dumps(catalogue)
        if argv[:2] == ("tmux", "split-window"):
            return "%10\n"
        return ""

    def no_joined_pane() -> str:
        raise watch.NoCodexPaneError("no Codex pane")

    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setenv("TMUX_PANE", "%4")
    monkeypatch.setattr(watch, "joined_pane", no_joined_pane)
    monkeypatch.setattr(watch, "run_command", fake_run)
    status = watch.main(["--spawn", "--cwd", str(workdir)])
    assert status == 0
    return calls


def _spawned_model(calls: list[tuple[str, ...]]) -> str:
    command = next(argv[-1] for argv in calls if argv[:2] == ("tmux", "split-window"))
    words = shlex.split(command)
    return words[words.index("--model") + 1]


def test_spawn_without_a_model_uses_the_catalogue_default(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = _spawn_calls(watch, monkeypatch, tmp_path, CATALOGUE)
    out = capsys.readouterr().out
    assert _spawned_model(calls) == "gpt-6.1-sol"
    assert "gpt-6.1-sol" in out, f"--spawn did not say which model it chose: {out!r}"
    assert calls.count(LIVE_CATALOGUE) == 1, "the catalogue was read more than once"


def test_spawn_falls_back_and_says_so_when_no_sol_slug_is_listed(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    catalogue = {
        "models": [{"slug": "gpt-6-astra", "priority": 0, "visibility": "list"}]
    }
    calls = _spawn_calls(watch, monkeypatch, tmp_path, catalogue)
    out = capsys.readouterr().out
    assert _spawned_model(calls) == watch.FALLBACK_MODEL
    assert "fallback" in out, f"--spawn did not say the default was a fallback: {out!r}"


def test_default_model_verb_prints_the_slug_alone(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--default-model` is what the peer-review runner substitutes, so stdout is
    exactly the slug; the reason goes to stderr."""
    calls: list[tuple[str, ...]] = []

    def fake_run(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        if argv[:3] == LIVE_CATALOGUE:
            return json.dumps(CATALOGUE)
        raise AssertionError(f"unexpected command {argv!r}")

    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setattr(watch, "run_command", fake_run)
    status = watch.main(["--default-model"])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == "gpt-6.1-sol\n"
    assert "priority" in captured.err


def test_default_model_verb_falls_back_when_no_catalogue_can_be_read(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unlike `--spawn`, nothing here needs the catalogue to be safe, so the runner
    still gets a model when codex cannot list any."""

    def fake_run(argv: tuple[str, ...]) -> str:
        raise watch.MonitorError(f"{' '.join(argv)} broke for this test")

    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setattr(watch, "run_command", fake_run)
    status = watch.main(["--default-model"])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == f"{watch.FALLBACK_MODEL}\n"
    assert "fallback" in captured.err
