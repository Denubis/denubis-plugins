"""The global hook installer must merge, not overwrite, and must repair itself.

The Codex relay belongs in `~/.codex/hooks.json` rather than in each project, because
a project-local hook only wakes the monitor in directories somebody set up in advance,
which leaves a Codex started in a fresh directory unsupervised exactly when nobody was
thinking about supervision.

That makes the installer's failure modes machine-wide rather than project-wide. It
edits a file it does not own, holding hooks it did not write, and the relay it installs
names an absolute path that outlives no reinstall. So three properties are checked
here: a foreign hook survives, a second run adds nothing, and a relay left pointing at
a path that no longer exists is corrected rather than skipped.

The last one is the reason `reconcile` does not simply ask whether a relay is present.
Presence and correctness are different questions, and answering the easy one leaves
every hook on the machine invoking a script that has moved.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_INSTALLER = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "denubis-external-agents"
    / "skills"
    / "supervising-codex"
    / "hooks"
    / "install-codex-hooks.py"
)

_FOREIGN = "/opt/somebody-elses/notify.sh Codex"


@pytest.fixture(scope="module")
def installer() -> ModuleType:
    assert _INSTALLER.is_file(), f"{_INSTALLER} has not been implemented"
    spec = importlib.util.spec_from_file_location("install_codex_hooks", _INSTALLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["install_codex_hooks"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway HOME already carrying somebody else's Stop hook."""
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "hooks.json").write_text(
        json.dumps(
            {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": _FOREIGN}]}]}}
        )
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _commands(home: Path) -> list[str]:
    document = json.loads((home / ".codex" / "hooks.json").read_text())
    return [
        hook["command"]
        for entries in document["hooks"].values()
        for group in entries
        for hook in group["hooks"]
    ]


def test_a_hook_it_did_not_write_survives(
    installer: ModuleType,
    home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """It edits a file it does not own, so destroying a stranger's hook is the risk."""
    installer.main()
    capsys.readouterr()

    assert _FOREIGN in _commands(home), (
        "the installer dropped a pre-existing hook it did not write; it merges into "
        "a machine-level file that other tools also configure"
    )


def test_every_relayed_event_is_wired(
    installer: ModuleType,
    home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer.main()
    capsys.readouterr()

    document = json.loads((home / ".codex" / "hooks.json").read_text())
    for event in installer.RELAYED_EVENTS:
        wired = [
            hook
            for group in document["hooks"][event]
            for hook in group["hooks"]
            if installer.MARKER in hook["command"]
        ]
        assert len(wired) == 1, (
            f"{event} carries {len(wired)} relays, expected exactly 1"
        )


def test_running_it_twice_changes_nothing(
    installer: ModuleType,
    home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Re-running after an upgrade must not stack duplicate relays."""
    installer.main()
    once = sorted(_commands(home))
    installer.main()
    capsys.readouterr()

    assert sorted(_commands(home)) == once, "a second run altered the hook set"


def test_a_relay_left_pointing_at_a_moved_script_is_repaired(
    installer: ModuleType,
    home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Presence is not correctness, and this is the difference between them."""
    installer.main()
    path = home / ".codex" / "hooks.json"
    document = json.loads(path.read_text())
    for entries in document["hooks"].values():
        for group in entries:
            for hook in group["hooks"]:
                if installer.MARKER in hook["command"]:
                    hook["command"] = f'uv run python "/gone/{installer.MARKER}" --hook'
    path.write_text(json.dumps(document))

    installer.main()
    capsys.readouterr()

    assert not [c for c in _commands(home) if "/gone/" in c], (
        "a relay pointing at a script that no longer exists was left in place; "
        "the installer checked whether a relay was present rather than correct"
    )
