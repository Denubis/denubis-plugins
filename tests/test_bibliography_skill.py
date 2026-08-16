"""Packaging and installation contracts for the bibliography skill."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "denubis-academic"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "using-bibliography"
SKILL = SKILL_ROOT / "SKILL.md"
SETUP = SKILL_ROOT / "references" / "setup-and-migration.md"
GLOBAL_CODEX_CANDIDATE = (
    REPO_ROOT / "deployment" / "instruction-control" / "foa4008439" / "AGENTS.md"
)
REQUIRED_REFERENCES = (
    "references/setup-and-migration.md",
    "references/resolve-and-render.md",
    "references/reading-and-quoting.md",
    "references/zotero-writes.md",
    "references/notes-and-bibliographies.md",
    "references/troubleshooting.md",
)


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    frontmatter, _body = text.removeprefix("---\n").split("\n---\n", 1)
    parsed = yaml.safe_load(frontmatter)
    assert isinstance(parsed, dict)
    return parsed


def _markdown_files() -> list[Path]:
    return sorted(SKILL_ROOT.rglob("*.md"))


def _slash_commands(path: Path) -> set[tuple[str, ...]]:
    commands: set[tuple[str, ...]] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif in_fence and line.startswith("/"):
            commands.add(tuple(shlex.split(line)))
    return commands


def test_bibliography_skill_uses_progressive_disclosure() -> None:
    missing = [
        name for name in REQUIRED_REFERENCES if not (SKILL_ROOT / name).is_file()
    ]
    assert not missing, f"bibliography skill package is missing: {missing}"
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 500


def test_bibliography_commands_are_independent_of_callers_working_directory() -> None:
    markdown = {path: path.read_text(encoding="utf-8") for path in _markdown_files()}
    command_docs = {path: text for path, text in markdown.items() if ".py" in text}
    assert command_docs, "no bibliography command documentation discovered"

    repo_relative = "plugins/denubis-academic/skills/using-bibliography"
    bare_script = re.compile(
        r"(?:uv run(?: --[^\n]+)*|python)\s+"
        r"(?:resolve|ingest|render|blockquote|fetch|copy_item|update_item|annotate)\.py\b"
    )
    url = re.compile(r"https?://\S+")
    violations = {
        str(path.relative_to(SKILL_ROOT)): problem
        for path, text in command_docs.items()
        for local_text in (url.sub("", text),)
        for problem in (
            repo_relative if repo_relative in local_text else None,
            "bare script invocation" if bare_script.search(local_text) else None,
        )
        if problem is not None
    }
    assert not violations, (
        f"commands depend on a source checkout or caller cwd: {violations}"
    )

    assignment = re.compile(r"(?m)^PLUGIN_DIR=.*\nBIB=.*$")
    missing_root = {
        str(path.relative_to(SKILL_ROOT)): "no executable provider-root assignment"
        for path, text in command_docs.items()
        if assignment.search(text) is None
    }
    assert not missing_root, f"command docs lack installed-root setup: {missing_root}"

    base_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"}
    }
    cases = (
        ({"PLUGIN_ROOT": "/codex/plugin"}, "/codex/plugin/skills/using-bibliography"),
        (
            {"CLAUDE_PLUGIN_ROOT": "/claude/plugin"},
            "/claude/plugin/skills/using-bibliography",
        ),
        (
            {
                "PLUGIN_ROOT": "/codex/plugin",
                "CLAUDE_PLUGIN_ROOT": "/claude/plugin",
            },
            "/codex/plugin/skills/using-bibliography",
        ),
    )
    for path, text in command_docs.items():
        block = assignment.search(text)
        assert block is not None
        for provider_env, expected in cases:
            result = subprocess.run(
                ["bash", "-c", f"set -u\n{block.group()}\nprintf '%s' \"$BIB\""],
                check=True,
                capture_output=True,
                env=base_env | provider_env,
                text=True,
            )
            assert result.stdout == expected, path


def test_setup_names_are_derived_from_the_current_manifest() -> None:
    plugin = json.loads(
        (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    skill = _frontmatter(SKILL)
    current_id = f"{plugin['name']}@denubis-plugins"
    current_skill = f"/{plugin['name']}:{skill['name']}"
    setup_commands = _slash_commands(SETUP)
    root_commands = _slash_commands(REPO_ROOT / "README.md")

    assert ("/plugin", "install", current_id) in setup_commands
    assert ("/plugin", "install", current_id) in root_commands
    assert (current_skill,) in setup_commands
    assert (
        "/plugin",
        "uninstall",
        "denubis-bibliography@denubis-plugins",
    ) in setup_commands


def test_deployment_candidate_points_to_the_live_bibliography_skill() -> None:
    text = GLOBAL_CODEX_CANDIDATE.read_text(encoding="utf-8")
    matches = re.findall(r"`(/[^`]+/skills/using-bibliography/SKILL\.md)`", text)
    assert matches, "global Codex candidate has no bibliography skill path"

    missing = [path for path in matches if not Path(path).is_file()]
    assert not missing, f"global Codex candidate points to missing skills: {missing}"
    assert all("/plugins/denubis-academic/" in path for path in matches)


def test_relative_markdown_links_resolve() -> None:
    missing: list[tuple[str, str]] = []
    link_pattern = re.compile(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")
    for path in _markdown_files():
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if "://" not in target and not (path.parent / target).resolve().exists():
                missing.append((str(path.relative_to(SKILL_ROOT)), target))
    assert not missing, f"broken relative links: {missing}"
