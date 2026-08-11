"""Behaviour contract for the branch-colour SessionStart hook."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-hook-branch-bg"
    / "hooks"
    / "branch-bg.py"
)


@pytest.fixture
def hook_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("branch_bg", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_sets_repo_branch_colour_without_model_context(
    hook_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    colours: list[str] = []
    monkeypatch.setattr(hook_module, "get_git_info", lambda: ("/repo/.git", "topic"))
    monkeypatch.setattr(
        hook_module,
        "git_info_to_colour",
        lambda repo_id, branch: "#123456",
    )
    monkeypatch.setattr(hook_module, "set_terminal_bg", colours.append)

    hook_module.main()

    assert colours == ["#123456"]
    assert capsys.readouterr().out == ""


def test_main_is_silent_outside_git(
    hook_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    colours: list[str] = []
    monkeypatch.setattr(hook_module, "get_git_info", lambda: (None, None))
    monkeypatch.setattr(hook_module, "set_terminal_bg", colours.append)

    hook_module.main()

    assert colours == []
    assert capsys.readouterr().out == ""
