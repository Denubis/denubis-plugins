"""Repo-wide marketplace version-sync fitness function.

Stage 2 design-conformance finding M3 (2026-05-20): the existing
`test_plugin_manifest.py` (in `denubis-crash-recovery`) only locks crash-
recovery's plugin.json against marketplace.json. A future version bump on any
other plugin that forgets to sync marketplace.json would not be caught by CI.

This test walks every `plugins/*/.claude-plugin/plugin.json` and asserts the
marketplace entry's version string matches. It also reverse-checks that every
marketplace entry has a corresponding on-disk plugin.json — orphan marketplace
entries (referring to plugins that no longer exist) are also caught.

Per Ford et al. (Building Evolutionary Architectures), this is a "fitness
function" — a recurring concern (the repo CLAUDE.md's "Version Updates
Require Marketplace and Changelog Sync" rule) lifted from reviewer-eye to
automated test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# tests/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_MARKETPLACE_JSON = _REPO_ROOT / ".claude-plugin" / "marketplace.json"
_PLUGINS_DIR = _REPO_ROOT / "plugins"


def _plugin_json_paths() -> list[Path]:
    """Every plugin.json under `plugins/`.

    Two layouts are accepted because the repo uses both:
    - Root-level: `plugins/<name>/.claude-plugin/plugin.json` (most plugins).
    - Hook-plugin: `plugins/<name>/hooks/.claude-plugin/plugin.json`
      (the convention per the repo CLAUDE.md for `denubis-hook-*` plugins).
    """
    paths: list[Path] = []
    for plugin_dir in sorted(_PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        candidates = [
            plugin_dir / ".claude-plugin" / "plugin.json",
            plugin_dir / "hooks" / ".claude-plugin" / "plugin.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                paths.append(candidate)
                break
    return paths


def _plugin_name(plugin_json_path: Path) -> str:
    """Extract the plugin directory name from any of the accepted layouts.

    The plugin name is the directory immediately under `plugins/`.
    """
    for ancestor in plugin_json_path.parents:
        if ancestor.parent.name == "plugins":
            return ancestor.name
    raise ValueError(f"could not derive plugin name from {plugin_json_path}")


def _load_marketplace() -> dict[str, str]:
    """Map plugin name -> version from marketplace.json."""
    with _MARKETPLACE_JSON.open() as fh:
        marketplace = json.load(fh)
    return {p["name"]: p["version"] for p in marketplace["plugins"]}


def test_marketplace_json_exists() -> None:
    assert _MARKETPLACE_JSON.exists(), f"missing: {_MARKETPLACE_JSON}"


def test_at_least_one_plugin_json_discovered() -> None:
    """Sanity: the glob actually finds plugins. Catches silent layout regressions."""
    paths = _plugin_json_paths()
    assert paths, f"no plugin.json files under {_PLUGINS_DIR}"


@pytest.mark.parametrize(
    "plugin_json_path",
    _plugin_json_paths(),
    ids=_plugin_name,
)
def test_plugin_json_version_matches_marketplace(plugin_json_path: Path) -> None:
    """Every plugin's plugin.json version string MUST match its marketplace.json entry.

    Enforces the repo CLAUDE.md "Version Updates Require Marketplace and Changelog
    Sync" rule. A future version bump that forgets the marketplace update fails
    this test.
    """
    with plugin_json_path.open() as fh:
        plugin = json.load(fh)
    plugin_name = plugin["name"]
    plugin_version = plugin["version"]

    marketplace = _load_marketplace()
    assert plugin_name in marketplace, (
        f"{plugin_name} has plugin.json at {plugin_json_path}"
        f" but no marketplace.json entry"
    )
    marketplace_version = marketplace[plugin_name]
    assert plugin_version == marketplace_version, (
        f"version drift for {plugin_name}: "
        f"plugin.json={plugin_version} vs marketplace.json={marketplace_version}"
    )


def test_no_orphan_marketplace_entries() -> None:
    """Every name in marketplace.json must correspond to an on-disk plugin.json.

    Catches the reverse failure: a plugin directory was deleted but its marketplace
    entry was left behind.
    """
    marketplace = _load_marketplace()
    on_disk_names = {_plugin_name(p) for p in _plugin_json_paths()}
    orphans = set(marketplace) - on_disk_names
    assert not orphans, (
        f"marketplace.json lists plugins with no on-disk plugin.json: {sorted(orphans)}"
    )
