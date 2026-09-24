"""Runtime-structure checks for the human-triggered Fable cost boundary."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS = REPO_ROOT / "plugins"
ADVISOR_SKILL = (
    PLUGINS
    / "denubis-external-agents"
    / "skills"
    / "consulting-a-fable-advisor"
    / "SKILL.md"
)
ADVISOR_LAUNCHER = ADVISOR_SKILL.with_name("fable-advisor-spawn.sh")


def _frontmatter(path: Path) -> dict[str, Any]:
    _opening, raw, _body = path.read_text(encoding="utf-8").split("---", 2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict)
    return parsed


def _is_fable_model(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalised = value.casefold().removeprefix("claude-")
    return normalised == "fable" or normalised.startswith("fable-")


def _agent_model(path: Path) -> str | None:
    match = re.search(
        r"^model:\s*([^\s#]+)", path.read_text(encoding="utf-8"), re.MULTILINE
    )
    return match.group(1) if match else None


def test_fable_model_classifier_has_positive_and_negative_controls() -> None:
    assert _is_fable_model("fable")
    assert _is_fable_model("claude-fable-5")
    assert not _is_fable_model("opus")


def test_advisor_skill_requires_human_selection() -> None:
    metadata = _frontmatter(ADVISOR_SKILL)

    assert metadata["user-invocable"] is True
    assert metadata["disable-model-invocation"] is True


def test_shipped_agent_definitions_do_not_dispatch_fable() -> None:
    agents = sorted(PLUGINS.glob("*/agents/*.md"))
    assert agents, "agent-definition corpus was not discovered"

    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in agents
        if _is_fable_model(_agent_model(path))
    ]

    message = "Fable agent definitions bypass human selection: " + ", ".join(offenders)
    assert not offenders, message


@pytest.mark.parametrize("alive", [False, True])
def test_advisor_preserves_selection_and_never_falls_back(
    tmp_path: Path,
    alive: bool,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tmux = bin_dir / "tmux"
    tmux.write_text(
        """#!/usr/bin/env bash
if [ \"$1\" = split-window ]; then
  printf '%s\\n' \"$@\" > \"$ARGS_FILE\"
  printf '%%99\\n'
elif [ \"$1\" = list-panes ] && [ \"$ALIVE\" = yes ]; then
  printf '%%99\\n'
fi
""",
        encoding="utf-8",
    )
    claude = bin_dir / "claude"
    claude.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    sleep = bin_dir / "sleep"
    sleep.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    for executable in (tmux, claude, sleep):
        executable.chmod(0o755)

    result = subprocess.run(
        ["bash", str(ADVISOR_LAUNCHER), str(tmp_path), "requested-model", "medium"],
        capture_output=True,
        check=False,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "TMUX": "fixture",
            "TMUX_PANE": "%1",
            "ARGS_FILE": str(tmp_path / "args"),
            "ALIVE": "yes" if alive else "no",
        },
        text=True,
    )

    args = (tmp_path / "args").read_text().splitlines()
    assert args[args.index("--model") + 1] == "requested-model"
    assert args[args.index("--effort") + 1] == "medium"
    if alive:
        assert result.returncode == 0
        assert "effort:   medium" in result.stdout
        return
    assert result.returncode == 2
    assert "'requested-model'" in result.stderr
    assert "no fallback model was selected" in result.stderr.casefold()
    assert "opus" not in result.stderr.casefold()


@pytest.mark.parametrize("arguments", [[], ["."], [".", "claude-fable-5"]])
def test_advisor_requires_explicit_model_and_effort(arguments: list[str]) -> None:
    result = subprocess.run(
        ["bash", str(ADVISOR_LAUNCHER), *arguments],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 1
    assert "model and effort" in result.stderr
