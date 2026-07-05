"""Tests for the on-disk plugin manifest and marketplace entry.

Covers AC1.3 (version sync between ``plugin.json`` and ``marketplace.json``)
and AC1.4 (the manifest is well-formed JSON with the required fields, which
is the well-formed-ness gate ``claude plugin install`` relies on).

These tests walk up from the test file to locate the plugin root and the
repo root, so they work whether invoked at the per-plugin path or from the
repo root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# tests/ -> scripts/crash_recovery/ -> scripts/ -> denubis-crash-recovery/
_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
# denubis-crash-recovery/ -> plugins/ -> repo root.
_REPO_ROOT = _PLUGIN_ROOT.parents[1]

_PLUGIN_JSON = _PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
_MARKETPLACE_JSON = _REPO_ROOT / ".claude-plugin" / "marketplace.json"

_REQUIRED_PLUGIN_FIELDS: tuple[str, ...] = (
    "name",
    "description",
    "version",
    "author",
    "license",
)


class TestPluginJson:
    def test_plugin_json_exists(self) -> None:
        assert _PLUGIN_JSON.exists(), f"missing: {_PLUGIN_JSON}"

    def test_plugin_json_is_valid(self) -> None:
        """Well-formed JSON with all AC1.3-required fields."""
        with _PLUGIN_JSON.open() as fh:
            data = json.load(fh)
        for field in _REQUIRED_PLUGIN_FIELDS:
            assert field in data, (field, sorted(data.keys()))
        assert data["name"] == "denubis-crash-recovery", data["name"]

    def test_plugin_json_version_string_shape(self) -> None:
        """Version is a non-empty string (semver-ish; full semver enforced elsewhere).
        """
        with _PLUGIN_JSON.open() as fh:
            data = json.load(fh)
        assert isinstance(data["version"], str), type(data["version"])
        assert data["version"], "version must not be empty"


class TestMarketplaceEntry:
    def test_marketplace_json_exists(self) -> None:
        assert _MARKETPLACE_JSON.exists(), f"missing: {_MARKETPLACE_JSON}"

    def test_marketplace_lists_crash_recovery(self) -> None:
        """The repo-root marketplace.json has a denubis-crash-recovery entry."""
        with _MARKETPLACE_JSON.open() as fh:
            marketplace = json.load(fh)
        names = [p["name"] for p in marketplace["plugins"]]
        assert "denubis-crash-recovery" in names, names

    def test_versions_match(self) -> None:
        """plugin.json and the marketplace entry agree on the version string (AC1.3)."""
        with _PLUGIN_JSON.open() as fh:
            plugin = json.load(fh)
        with _MARKETPLACE_JSON.open() as fh:
            marketplace = json.load(fh)
        entry = next(
            (
                p
                for p in marketplace["plugins"]
                if p["name"] == "denubis-crash-recovery"
            ),
            None,
        )
        assert entry is not None, "denubis-crash-recovery missing from marketplace.json"
        assert entry["version"] == plugin["version"], (
            entry["version"],
            plugin["version"],
        )


class TestMalformedPluginJsonDetectable:
    def test_json_load_rejects_malformed_manifest(self, tmp_path: Path) -> None:
        """AC1.4: ``json.load`` raises on a malformed manifest, so the well-formed-ness
        gate is meaningful. The real plugin.json is asserted parseable above; this
        test proves that the gate would catch a bad manifest.
        """
        bad = tmp_path / "plugin.json"
        bad.write_text("{not valid json")
        with pytest.raises(json.JSONDecodeError), bad.open() as fh:
            json.load(fh)
