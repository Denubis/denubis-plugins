"""Provider projection keeps shared plugin source intact."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTOR = REPO_ROOT / "scripts" / "project_antigravity_plugin.py"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _project(source: Path, target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECTOR), str(source), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )


def _frontmatter_and_body(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter, body = text[4:].split("\n---\n", 1)
    parsed = yaml.safe_load(frontmatter)
    assert isinstance(parsed, dict)
    return parsed, body


def _skill_plugin_roots() -> list[Path]:
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    return [
        REPO_ROOT / entry["source"]
        for entry in data["plugins"]
        if list((REPO_ROOT / entry["source"] / "skills").glob("*/SKILL.md"))
    ]


def test_all_skill_plugins_project_without_changing_shared_source(
    tmp_path: Path,
) -> None:
    roots = _skill_plugin_roots()
    assert roots
    source_agent_count = sum(len(list((root / "agents").glob("*.md"))) for root in roots)
    changed_models = 0
    preserved_commands = 0
    projected_agents = 0

    for source in roots:
        target = tmp_path / source.name
        original_agents = {
            path.name: path.read_bytes() for path in (source / "agents").glob("*.md")
        }
        result = _project(source, target)

        assert result.returncode == 0, result.stderr
        assert (target / "plugin.json").read_bytes() == (
            source / "plugin.json"
        ).read_bytes()
        for path in (source / "skills").rglob("*"):
            generated = {".venv", "__pycache__"}.intersection(path.parts)
            if path.is_file() and not generated and path.suffix != ".pyc":
                assert (target / path.relative_to(source)).read_bytes() == (
                    path.read_bytes()
                )
        for path in (source / "commands").rglob("*"):
            if path.is_file():
                preserved_commands += 1
                assert (target / path.relative_to(source)).read_bytes() == (
                    path.read_bytes()
                )
        for name, original in original_agents.items():
            path = source / "agents" / name
            projected = target / "agents" / name
            original_metadata, original_body = _frontmatter_and_body(path)
            projected_metadata, projected_body = _frontmatter_and_body(projected)
            projected_agents += 1
            assert path.read_bytes() == original
            assert projected_body == original_body
            assert projected_metadata["name"] == original_metadata["name"]
            if "model" in original_metadata:
                changed_models += 1
                assert projected_metadata["model"] == "inherit"
            if "tools" in original_metadata:
                assert projected_metadata["tools"] == [
                    "view_file", "grep_search", "find_by_name", "run_command"
                ]
        assert not (target / "scripts" / "workflow_statusline" / ".venv").exists()

    assert changed_models > 0
    assert projected_agents == source_agent_count
    assert preserved_commands > 0


@pytest.mark.parametrize(
    ("frontmatter", "reason"),
    [
        ("model: unknown-tier", "unknown model"),
        ("model: opus\ntools: Read, Unknown", "unknown tool"),
        ("model: opus\ntools: [", "frontmatter"),
        ("model: opus\ntools:\n  - Read", "tools"),
        ("model: 42", "model"),
    ],
)
def test_unknown_or_malformed_agent_metadata_fails_before_output(
    tmp_path: Path, frontmatter: str, reason: str
) -> None:
    source = tmp_path / "source"
    (source / "agents").mkdir(parents=True)
    (source / "plugin.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
    (source / "agents" / "worker.md").write_text(
        f"---\nname: worker\ndescription: worker\n{frontmatter}"
        "\n---\n\nKeep this body.\n",
        encoding="utf-8",
    )
    target = tmp_path / "target"

    result = _project(source, target)

    assert result.returncode != 0
    assert reason in result.stderr.lower()
    assert not target.exists()


@pytest.mark.parametrize("linked_part", ["agent", "agents-directory"])
def test_projection_rejects_agent_symlinks_without_writing_source(
    tmp_path: Path, linked_part: str
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "plugin.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
    actual_agents = tmp_path / "actual-agents"
    actual_agents.mkdir()
    original = (
        "---\nname: worker\ndescription: worker\nmodel: opus\n---\n\n"
        "Keep this body.\n"
    )
    actual = actual_agents / "worker.md"
    actual.write_text(original, encoding="utf-8")
    original_bytes = actual.read_bytes()
    if linked_part == "agent":
        (source / "agents").mkdir()
        (source / "agents" / "worker.md").symlink_to(actual)
    else:
        (source / "agents").symlink_to(actual_agents, target_is_directory=True)
    target = tmp_path / "target"

    result = _project(source, target)

    assert result.returncode != 0
    assert "symlink" in result.stderr.lower()
    assert actual.read_bytes() == original_bytes
    assert not target.exists()
