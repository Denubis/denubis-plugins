"""Executable packaging contracts for the repository Codex marketplace."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _marketplace_plugins() -> list[tuple[dict[str, object], Path, dict[str, object]]]:
    marketplace = _json(MARKETPLACE_PATH)
    plugins = marketplace.get("plugins")
    assert isinstance(plugins, list) and plugins

    resolved: list[tuple[dict[str, object], Path, dict[str, object]]] = []
    for entry in plugins:
        assert isinstance(entry, dict)
        source = entry.get("source")
        assert isinstance(source, dict) and source.get("source") == "local"
        relative_path = source.get("path")
        assert isinstance(relative_path, str)
        plugin_root = (REPO_ROOT / relative_path).resolve()
        manifest = _json(plugin_root / ".codex-plugin" / "plugin.json")
        resolved.append((entry, plugin_root, manifest))
    return resolved


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    frontmatter, _body = text.removeprefix("---\n").split("\n---\n", 1)
    value = yaml.safe_load(frontmatter)
    assert isinstance(value, dict)
    return value


def _metadata(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_marketplace_entries_resolve_to_matching_manifests() -> None:
    for entry, plugin_root, manifest in _marketplace_plugins():
        assert plugin_root.is_dir()
        assert entry["name"] == manifest["name"] == plugin_root.name
        assert entry["policy"] == {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        }
        interface = manifest.get("interface")
        assert isinstance(interface, dict)
        assert interface.get("displayName")
        assert interface.get("shortDescription")


def test_every_exposed_skill_has_valid_codex_metadata() -> None:
    discovered = 0
    for _entry, plugin_root, manifest in _marketplace_plugins():
        skills_path = manifest.get("skills")
        if skills_path is None:
            continue
        assert isinstance(skills_path, str)
        skill_root = plugin_root / skills_path
        for skill_file in sorted(skill_root.glob("*/SKILL.md")):
            discovered += 1
            frontmatter = _frontmatter(skill_file)
            skill_name = frontmatter.get("name")
            assert isinstance(skill_name, str)

            metadata = _metadata(skill_file.parent / "agents" / "openai.yaml")
            interface = metadata.get("interface")
            policy = metadata.get("policy")
            assert isinstance(interface, dict)
            assert isinstance(policy, dict)

            display_name = interface.get("display_name")
            short_description = interface.get("short_description")
            default_prompt = interface.get("default_prompt")
            assert isinstance(display_name, str) and display_name.strip()
            assert isinstance(short_description, str)
            assert 25 <= len(short_description) <= 64
            assert isinstance(default_prompt, str) and f"${skill_name}" in default_prompt
            assert isinstance(policy.get("allow_implicit_invocation"), bool)

    assert discovered > 0


def test_consequential_side_effect_skills_require_explicit_invocation() -> None:
    explicit_only = (
        "plugins/denubis-git-commit/skills/commit",
        "plugins/denubis-plan-and-execute/skills/exec-session-naming",
        "plugins/denubis-plan-and-execute/skills/make-pr",
        "plugins/denubis-plan-and-execute/skills/merge-to-main",
    )
    observed = {
        relative: _metadata(REPO_ROOT / relative / "agents" / "openai.yaml")["policy"]
        for relative in explicit_only
    }

    assert all(policy == {"allow_implicit_invocation": False} for policy in observed.values())


def test_expensive_project_memory_retrieval_requires_explicit_invocation() -> None:
    metadata = _metadata(
        REPO_ROOT
        / "plugins"
        / "denubis-project-notes"
        / "skills"
        / "scanning-project-notes"
        / "agents"
        / "openai.yaml"
    )

    assert metadata["policy"] == {"allow_implicit_invocation": False}


def test_dual_provider_hooks_resolve_without_ambiguous_default_discovery() -> None:
    for plugin_name in ("denubis-plan-and-execute", "denubis-hook-branch-bg"):
        plugin_root = REPO_ROOT / "plugins" / plugin_name
        claude_manifest = _json(plugin_root / ".claude-plugin" / "plugin.json")
        codex_manifest = _json(plugin_root / ".codex-plugin" / "plugin.json")

        claude_path = plugin_root / str(claude_manifest["hooks"])
        codex_path = plugin_root / str(codex_manifest["hooks"])
        claude_hooks = _json(claude_path)
        codex_hooks = _json(codex_path)

        assert claude_path.is_file() and codex_path.is_file()
        assert claude_path != codex_path
        assert not (plugin_root / "hooks" / "hooks.json").exists()

        claude_commands = json.dumps(claude_hooks)
        codex_commands = json.dumps(codex_hooks)
        assert "${PLUGIN_ROOT}" not in claude_commands
        assert "${CLAUDE_PLUGIN_ROOT}" not in codex_commands


def test_plan_plugin_does_not_register_the_claude_live_marker_in_codex() -> None:
    plugin_root = REPO_ROOT / "plugins" / "denubis-plan-and-execute"
    codex_manifest = _json(plugin_root / ".codex-plugin" / "plugin.json")
    codex_hooks = _json(plugin_root / str(codex_manifest["hooks"]))

    assert codex_hooks == {"hooks": {}}
