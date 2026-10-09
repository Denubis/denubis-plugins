"""Behaviour contract for the branch-colour hook and its tmux pane strip."""

from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

HOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-hook-branch-bg"
    / "hooks"
    / "branch-bg.py"
)

HEX = re.compile(r"^#[0-9a-f]{6}$")
BLOCK = re.compile(r"#\[bg=(#[0-9a-f]{6}),fg=(#[0-9a-f]{6}),bold\] ([^#]+) ")


@pytest.fixture
def hook_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("BRANCH_BG_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.delenv("TMUX_PANE", raising=False)
    spec = importlib.util.spec_from_file_location("branch_bg", HOOK_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_git(mapping: dict[str, tuple[str | None, str | None]]):
    return lambda path: mapping.get(path, (None, None))


def _blocks(strip: str) -> list[tuple[str, str, str]]:
    return BLOCK.findall(strip)


def _strip_and_field(hook_module: ModuleType, path: str, title: str) -> tuple[str, str]:
    strip, field, _ = hook_module.strip_output(path, title).split("\n")
    return strip, field


def _rgb(colour: str) -> tuple[int, ...]:
    return tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))


def _wcag_luminance(colour: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in _rgb(colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_wcag_luminance(a), _wcag_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# --- the palette ------------------------------------------------------------


def test_every_block_colour_is_distinct_and_its_text_reads_on_it(
    hook_module: ModuleType,
) -> None:
    colours = [c for c, _ in hook_module.BLOCKS]
    assert all(HEX.match(c) for c in colours)
    assert len(set(colours)) == len(colours)
    for colour, text in hook_module.BLOCKS:
        assert text in ("#000000", "#ffffff")
        assert _contrast(colour, text) >= 4.5


# --- reading a pane -----------------------------------------------------------


def test_person_is_the_directory_under_people(hook_module: ModuleType) -> None:
    assert hook_module.person_of("/home/b/people/Jodie/proj/src") == "Jodie"
    assert hook_module.person_of("/media/x/people/Adela/melica") == "Adela"
    assert hook_module.person_of("/home/b/code/proj") == ""
    assert hook_module.person_of("/home/b/people") == ""


def test_session_label_comes_from_claude_or_codex_pane_titles(
    hook_module: ModuleType,
) -> None:
    assert (
        hook_module.session_of("✳ Approver Wave 1 handover")
        == "Approver Wave 1 handover"
    )
    codex = "Ready | approver | main | Execute phone recorder plan | GPT-6-Sol xhigh"
    assert hook_module.session_of(codex) == "Execute phone recorder plan"
    assert hook_module.session_of("~/p/J/2026-AILOC-Validation") == ""
    assert hook_module.session_of("") == ""


def test_repo_name_is_the_directory_holding_the_git_dir(
    hook_module: ModuleType,
) -> None:
    assert hook_module.repo_name("/home/b/people/Brian/plugins/.git") == "plugins"
    assert hook_module.repo_name("/srv/bare-repo.git") == "bare-repo.git"


# --- the strip ------------------------------------------------------------------


def test_strip_has_one_block_per_known_name_in_order(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = "/home/b/people/Jodie/proj"
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({repo: (repo + "/.git", "main")})
    )

    strip, field = _strip_and_field(hook_module, repo, "✳ Plan")

    labels = [label for _, _, label in _blocks(strip)]
    assert labels == ["Jodie", "proj", "main", "Plan"]
    assert strip.endswith("#[default]")
    pinned = {v for table in hook_module.PINNED.values() for v in table.values()}
    for colour, text, _ in _blocks(strip):
        assert (colour, text) in hook_module.BLOCKS or (colour, text) in pinned
    assert HEX.match(field)


def test_shell_pane_outside_git_has_only_the_person_block(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook_module, "git_identity", _fake_git({}))

    strip, field = _strip_and_field(
        hook_module, "/home/b/people/JP/notes", "~/p/JP/notes"
    )

    assert [label for _, _, label in _blocks(strip)] == ["JP"]
    assert field != "#000000", (
        "the field is derived from the person when there is no repo"
    )
    person_colour = _blocks(strip)[0][0]
    assert all(f <= c for f, c in zip(_rgb(field), _rgb(person_colour), strict=True))


def test_pane_with_nothing_known_prints_an_empty_strip(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook_module, "git_identity", _fake_git({}))

    strip, field = _strip_and_field(hook_module, "/tmp", "fish")

    assert strip == ""
    assert HEX.match(field)
    assert field != "#000000", "even a bare pane gets a tint derived from where it is"


def test_place_is_the_first_directory_under_home_or_a_short_prefix(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "Downloads" / "deep").mkdir(parents=True)
    assert hook_module.place_of(str(tmp_path / "Downloads" / "deep")) == "Downloads"
    assert hook_module.place_of(str(tmp_path)) == "~"
    assert hook_module.place_of("/media/brian/storage/x") == "//media/brian"


def test_field_is_a_near_black_shade_of_the_repo_block(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({"/r": ("/r/.git", "main")})
    )

    strip, field = _strip_and_field(hook_module, "/r", "")

    repo_colour = next(c for c, _, label in _blocks(strip) if label == "r")
    assert field != "#000000"
    assert all(f <= c for f, c in zip(_rgb(field), _rgb(repo_colour), strict=True))
    assert _contrast(field, "#d0d0d0") >= 7.0


def test_hash_characters_in_labels_are_escaped_for_tmux(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({"/r": ("/r/.git", "fix/#12")})
    )

    strip, _ = _strip_and_field(hook_module, "/r", "")

    assert " fix/##12 " in strip


# --- assignment ---------------------------------------------------------------


def test_names_keep_their_colours_and_distinct_names_get_distinct_colours(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    git = _fake_git({"/a": ("/a/.git", "dev"), "/b": ("/b/.git", "dev")})
    monkeypatch.setattr(hook_module, "git_identity", git)

    first = _blocks(_strip_and_field(hook_module, "/a", "")[0])
    second = _blocks(_strip_and_field(hook_module, "/b", "")[0])
    first_again = _blocks(_strip_and_field(hook_module, "/a", "")[0])

    assert first == first_again
    repo_a = next(c for c, _, label in first if label == "a")
    repo_b = next(c for c, _, label in second if label == "b")
    assert repo_a != repo_b
    dev_a = next(c for c, _, label in first if label == "dev")
    dev_b = next(c for c, _, label in second if label == "dev")
    assert dev_a == dev_b, "the same branch name is the same colour in every repo"


def test_main_and_master_are_always_bright_red_and_take_no_registry_slot(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    git = _fake_git({"/a": ("/a/.git", "main"), "/b": ("/b/.git", "master")})
    monkeypatch.setattr(hook_module, "git_identity", git)

    for path, branch in (("/a", "main"), ("/b", "master")):
        strip, _ = _strip_and_field(hook_module, path, "")
        colour, text, _ = next(b for b in _blocks(strip) if b[2] == branch)
        assert colour == "#ff0000"
        assert _contrast(colour, text) >= 4.5
    assert "#ff0000" not in {c for c, _ in hook_module.BLOCKS}
    data = json.loads(Path(os.environ["BRANCH_BG_REGISTRY"]).read_text())
    assert data["kinds"]["branch"] == {}


def test_kinds_start_at_different_points_of_the_table(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = "/home/b/people/Ann/r"
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({repo: (repo + "/.git", "main")})
    )

    strip, _ = _strip_and_field(hook_module, repo, "✳ S")

    colours = [c for c, _, _ in _blocks(strip)]
    assert len(set(colours)) == 4


def test_full_table_reuses_the_least_recently_seen_name(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = iter(range(1, 10_000))
    monkeypatch.setattr(hook_module, "now", lambda: float(next(clock)))
    count = len(hook_module.BLOCKS)
    paths = {f"/repo{i}": (f"/repo{i}/.git", "main") for i in range(count + 1)}
    monkeypatch.setattr(hook_module, "git_identity", _fake_git(paths))

    def repo_colour(path: str) -> str:
        strip = _strip_and_field(hook_module, path, "")[0]
        return next(c for c, _, label in _blocks(strip) if label == path[1:])

    colours = [repo_colour(f"/repo{i}") for i in range(count)]
    assert len(set(colours)) == count
    for i in range(1, count):
        repo_colour(f"/repo{i}")  # everything but repo0 is seen again

    newcomer = repo_colour(f"/repo{count}")

    assert newcomer == colours[0]


def test_unwritable_registry_still_colours_every_block(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setenv("BRANCH_BG_REGISTRY", str(blocker / "registry.json"))
    repo = "/home/b/people/Ann/r"
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({repo: (repo + "/.git", "dev")})
    )

    strip, field = _strip_and_field(hook_module, repo, "✳ S")

    assert [label for _, _, label in _blocks(strip)] == ["Ann", "r", "dev", "S"]
    assert HEX.match(field)


def test_registry_file_is_keyed_by_kind_and_name(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = "/home/b/people/Ann/r"
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({repo: (repo + "/.git", "dev")})
    )

    hook_module.strip_output(repo, "✳ S")
    data = json.loads(Path(os.environ["BRANCH_BG_REGISTRY"]).read_text())

    assert "Ann" in data["kinds"]["person"]
    assert repo + "/.git" in data["kinds"]["repo"]
    assert "dev" in data["kinds"]["branch"]
    assert "session" not in data["kinds"], "sessions are hashed, not registered"


# --- the SessionStart hook --------------------------------------------------------


def test_session_start_paints_terminal_and_pane_and_installs_the_strip_once(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMUX_PANE", "%42")
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({"/r": ("/r/.git", "main")})
    )
    monkeypatch.setattr(hook_module.Path, "cwd", lambda: Path("/r"))
    painted: list[str] = []
    monkeypatch.setattr(hook_module, "set_terminal_bg", painted.append)
    calls: list[list[str]] = []
    tmux_default = '#{?pane_active,#[reverse],}#{pane_index}#[default] "#{pane_title}"'
    options = {"pane-border-format": tmux_default}

    def fake_tmux(argv: list[str]) -> str:
        calls.append(list(argv))
        if argv[:2] == ["show-options", "-gv"]:
            return options.get(argv[2], "")
        if argv[:2] == ["set-option", "-g"]:
            options[argv[2]] = argv[3]
        return ""

    monkeypatch.setattr(hook_module, "run_tmux", fake_tmux)

    hook_module.main([])
    hook_module.main([])

    assert len(painted) == 2
    assert painted[0] == painted[1]
    assert painted[0] != "#000000"
    pane_paints = [c for c in calls if c[:2] == ["set-option", "-p"]]
    expected = ["set-option", "-p", "-t", "%42", "window-style", f"bg={painted[0]}"]
    assert pane_paints == [expected] * 2
    assert not [c for c in calls if c[0] == "select-pane"], (
        "painting must never move focus"
    )
    installs = [c for c in calls if c[:3] == ["set-option", "-g", "pane-border-format"]]
    assert len(installs) == 1, "the strip is installed once per server, not per session"
    assert "branch-strip.sh" in installs[0][3]
    assert " #{q:pane_current_path} #{q:pane_title} #{pane_id})" in installs[0][3], (
        "q: already shell-quotes, so the arguments must not be wrapped in quotes"
    )
    assert ["set-option", "-g", "pane-border-status", "top"] in calls


def test_session_start_outside_tmux_only_paints_the_terminal(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({"/r": ("/r/.git", "main")})
    )
    monkeypatch.setattr(hook_module.Path, "cwd", lambda: Path("/r"))
    painted: list[str] = []
    monkeypatch.setattr(hook_module, "set_terminal_bg", painted.append)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        hook_module, "run_tmux", lambda argv: calls.append(list(argv)) or ""
    )

    hook_module.main([])

    assert len(painted) == 1
    assert calls == []


def test_session_start_outside_git_paints_a_derived_tint_and_prints_nothing(
    hook_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(hook_module, "git_identity", _fake_git({}))
    monkeypatch.setattr(hook_module.Path, "cwd", lambda: Path("/nowhere"))
    painted: list[str] = []
    monkeypatch.setattr(hook_module, "set_terminal_bg", painted.append)

    hook_module.main([])

    assert len(painted) == 1
    assert painted[0] != "#000000"
    assert capsys.readouterr().out == ""


def test_a_hand_set_border_format_is_left_alone(
    hook_module: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TMUX_PANE", "%42")
    monkeypatch.setattr(
        hook_module, "git_identity", _fake_git({"/r": ("/r/.git", "main")})
    )
    monkeypatch.setattr(hook_module.Path, "cwd", lambda: Path("/r"))
    monkeypatch.setattr(hook_module, "set_terminal_bg", lambda colour: None)
    calls: list[list[str]] = []

    def fake_tmux(argv: list[str]) -> str:
        calls.append(list(argv))
        if argv[:2] == ["show-options", "-gv"]:
            return "#{pane_title} (mine)"
        return ""

    monkeypatch.setattr(hook_module, "run_tmux", fake_tmux)

    hook_module.main([])

    assert not [c for c in calls if c[:2] == ["set-option", "-g"]]
