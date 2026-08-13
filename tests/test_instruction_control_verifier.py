"""Deployment evidence must be recomputed from the files it claims to bind."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    REPO_ROOT / "deployment" / "instruction-control" / "verify_candidate.py"
)
SPEC = importlib.util.spec_from_file_location(
    "instruction_control_verifier", VERIFIER_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_tree_digest_ignores_virtual_environments(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "SKILL.md").write_text("procedure\n", encoding="utf-8")
    expected = verifier.sha256_tree(plugin)
    environment_file = plugin / "tools" / ".venv" / "lib" / "runtime.py"
    environment_file.parent.mkdir(parents=True)
    environment_file.write_text("runtime residue\n", encoding="utf-8")

    assert verifier.sha256_tree(plugin) == expected


def test_tree_digest_binds_virtual_environment_near_miss(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "SKILL.md").write_text("procedure\n", encoding="utf-8")
    expected = verifier.sha256_tree(plugin)
    source_file = plugin / "tools" / ".venv-source" / "runtime.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("authoritative source\n", encoding="utf-8")

    assert verifier.sha256_tree(plugin) != expected


def test_manifest_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"schema_version": 1, "schema_version": 2}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="duplicate JSON key: schema_version"):
        verifier._load_manifest(manifest)


def test_manifest_loader_rejects_unknown_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version": 2}', encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported manifest schema_version: 2"):
        verifier._load_manifest(manifest)


def _write_fixture(tmp_path: Path, *, role: str = "user") -> Path:
    candidate = tmp_path / "candidate.md"
    candidate.write_text("candidate\n", encoding="utf-8")
    plugin = tmp_path / "plugins" / "example"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "example", "version": "1.2.3"}), encoding="utf-8"
    )
    (plugin / "SKILL.md").write_text("procedure\n", encoding="utf-8")
    source = tmp_path / "session.jsonl"
    source.write_text(
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": role,
                    "content": [{"type": "input_text", "text": "authority"}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    authority_text = "authority"
    manifest = {
        "schema_version": 1,
        "authority": {
            "records": {
                "A1": {
                    "path": str(source),
                    "line": 1,
                    "format": "codex_user_text",
                    "text_sha256": hashlib.sha256(
                        authority_text.encode()
                    ).hexdigest(),
                }
            },
            "actions": {"test-change": {"records": ["A1"]}},
        },
        "candidates": {
            "global_claude": {
                "path": "candidate.md",
                "bytes": candidate.stat().st_size,
                "sha256": verifier.sha256_file(candidate),
                "authority_actions": ["test-change"],
            }
        },
        "plugin_releases": {
            "install": [
                {
                    "name": "example",
                    "version": "1.2.3",
                    "source": "plugins/example",
                    "tree_sha256": verifier.sha256_tree(plugin),
                    "authority_actions": ["test-change"],
                }
            ],
            "retire": [],
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_source_verification_recomputes_every_binding(tmp_path: Path) -> None:
    manifest = _write_fixture(tmp_path)

    assert verifier.verify_source(tmp_path, manifest) == []


def test_source_verification_rejects_changed_candidate(tmp_path: Path) -> None:
    manifest = _write_fixture(tmp_path)
    (tmp_path / "candidate.md").write_text("changed\n", encoding="utf-8")

    errors = verifier.verify_source(tmp_path, manifest)

    assert any("candidate global_claude sha256" in error for error in errors)
    assert any("candidate global_claude bytes" in error for error in errors)


def test_source_verification_rejects_wrong_authority_role(tmp_path: Path) -> None:
    manifest = _write_fixture(tmp_path, role="assistant")

    errors = verifier.verify_source(tmp_path, manifest)

    assert errors == [
        "authority record A1 line 1 is not one non-empty Codex user input_text record"
    ]


def test_source_verification_checks_claude_authority_source(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    additional = tmp_path / "additional-session.jsonl"
    authority_text = "additional authority"
    additional.write_text(
        json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": authority_text},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest["authority"]["records"]["A2"] = {
        "path": str(additional),
        "line": 1,
        "format": "claude_user_text",
        "text_sha256": hashlib.sha256(authority_text.encode()).hexdigest(),
    }
    manifest["authority"]["actions"]["test-change"]["records"].append(
        "A2"
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == []


def test_source_verification_rejects_authority_text_substitution(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    source = tmp_path / "session.jsonl"
    record = json.loads(source.read_text(encoding="utf-8"))
    record["payload"]["content"][0]["text"] = "different authority"
    source.write_text(json.dumps(record) + "\n", encoding="utf-8")

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == ["authority record A1 text sha256 does not match"]


def test_source_verification_rejects_unknown_authority_action(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidates"]["global_claude"]["authority_actions"] = [
        "missing-action"
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == [
        "candidate global_claude names unknown authority action missing-action"
    ]


def test_source_verification_requires_candidate_authority_mapping(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["candidates"]["global_claude"]["authority_actions"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == ["candidate global_claude has no authority action"]


def test_source_verification_rejects_forbidden_settings_env(tmp_path: Path) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"env": {"BLOCKED": "1"}}), encoding="utf-8")
    manifest["candidates"]["settings"] = {
        "path": settings.name,
        "bytes": settings.stat().st_size,
        "sha256": verifier.sha256_file(settings),
        "authority_actions": ["test-change"],
    }
    manifest["settings_contract"] = {
        "candidate": "settings",
        "forbidden_env": ["BLOCKED"],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == [
        "settings candidate contains forbidden environment variable BLOCKED"
    ]


def _add_codex_history_contract(
    manifest_path: Path,
    config_path: Path,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["codex_history_contract"] = {
        "path": str(config_path),
        "persistence": "save-all",
        "forbid_max_bytes": True,
        "authority_actions": ["test-change"],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_source_verification_rejects_disabled_codex_history(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    config = tmp_path / "config.toml"
    config.write_text('[history]\npersistence = "none"\n', encoding="utf-8")
    _add_codex_history_contract(manifest_path, config)

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == ["Codex history persistence is none, expected save-all"]


def test_source_verification_rejects_codex_history_size_cap(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    config = tmp_path / "config.toml"
    config.write_text(
        '[history]\npersistence = "save-all"\nmax_bytes = 1024\n',
        encoding="utf-8",
    )
    _add_codex_history_contract(manifest_path, config)

    errors = verifier.verify_source(tmp_path, manifest_path)

    assert errors == ["Codex history max_bytes must remain unset"]


def test_source_verification_accepts_uncapped_saved_codex_history(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    config = tmp_path / "config.toml"
    config.write_text(
        '[history]\npersistence = "save-all"\n', encoding="utf-8"
    )
    _add_codex_history_contract(manifest_path, config)

    assert verifier.verify_source(tmp_path, manifest_path) == []


def test_baseline_verification_rejects_historical_git_binding() -> None:
    manifest = {
        "baselines": {
            "project_claude": {
                "path": "git:HEAD:CLAUDE.md",
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            }
        }
    }

    assert verifier.verify_baselines(manifest, repo_root=REPO_ROOT) == [
        "live baseline project_claude has unsupported binding: git:HEAD:CLAUDE.md"
    ]


def test_baseline_verification_rejects_unknown_relative_binding(
    tmp_path: Path,
) -> None:
    manifest = {
        "baselines": {
            "ambiguous": {
                "path": "relative/file.md",
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            }
        }
    }

    assert verifier.verify_baselines(manifest, repo_root=tmp_path) == [
        "live baseline ambiguous has unsupported binding: relative/file.md"
    ]


def _settings_transition_manifest(
    tmp_path: Path, *, candidate_model: str
) -> dict[str, object]:
    live = tmp_path / "live-settings.json"
    live.write_text(
        json.dumps(
            {
                "model": "fable",
                "enabledPlugins": {"retired@example": True, "kept@example": True},
                "permissions": {"allow": ["Old permission", "Kept permission"]},
            }
        ),
        encoding="utf-8",
    )
    candidate = tmp_path / "candidate-settings.json"
    candidate.write_text(
        json.dumps(
            {
                "model": candidate_model,
                "enabledPlugins": {"kept@example": True},
                "permissions": {"allow": ["Kept permission", "New permission"]},
            }
        ),
        encoding="utf-8",
    )
    return {
        "baselines": {
            "settings": {
                "path": str(live),
                "bytes": live.stat().st_size,
                "sha256": verifier.sha256_file(live),
            }
        },
        "candidates": {"settings": {"path": candidate.name}},
        "settings_transition": {
            "baseline": "settings",
            "candidate": "settings",
            "enabled_plugins": {
                "remove": ["retired@example"],
                "add": {},
            },
            "permission_allow": {
                "remove": ["Old permission"],
                "add": ["New permission"],
            },
        },
    }


def test_settings_transition_accepts_only_declared_changes(tmp_path: Path) -> None:
    manifest = _settings_transition_manifest(tmp_path, candidate_model="fable")

    assert verifier.verify_baselines(manifest, repo_root=tmp_path) == []


def test_settings_transition_rejects_unowned_change(tmp_path: Path) -> None:
    manifest = _settings_transition_manifest(tmp_path, candidate_model="opus")

    errors = verifier.verify_baselines(manifest, repo_root=tmp_path)

    assert errors == [
        "settings transition changes values outside its declared ownership"
    ]


def test_project_integration_requires_exact_candidate_at_live_path(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    live = tmp_path / "live-project-CLAUDE.md"
    live.write_text("old\n", encoding="utf-8")
    manifest["candidates"]["global_claude"]["live_path"] = str(live)
    manifest["project_integration"] = {"candidate": "global_claude"}

    assert verifier.verify_project_integration(manifest) == [
        "project integration global_claude bytes do not match",
        "project integration global_claude sha256 does not match",
    ]

    live.write_bytes((tmp_path / "candidate.md").read_bytes())
    assert verifier.verify_project_integration(manifest) == []


def test_deployed_verification_compares_live_files_and_cache(tmp_path: Path) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    live_global = tmp_path / "live" / "CLAUDE.md"
    live_global.parent.mkdir()
    live_global.write_bytes((tmp_path / "candidate.md").read_bytes())
    manifest["candidates"]["global_claude"]["live_path"] = str(live_global)
    registry = tmp_path / "installed_plugins.json"
    registry.write_text(
        json.dumps(
            {
                "plugins": {
                    "example@denubis-plugins": [
                        {
                            "scope": "user",
                            "version": "1.2.3",
                            "installPath": str(tmp_path / "cache/example/1.2.3"),
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    manifest["plugin_registry_path"] = str(registry)
    cache = tmp_path / "cache" / "example" / "1.2.3"
    cache.mkdir(parents=True)
    for source in (tmp_path / "plugins" / "example").rglob("*"):
        if source.is_file():
            target = cache / source.relative_to(tmp_path / "plugins" / "example")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (cache / ".in_use" / "session").mkdir(parents=True)

    assert verifier.verify_deployed(manifest, cache_root=tmp_path / "cache") == []

    (cache / "SKILL.md").write_text("drift\n", encoding="utf-8")
    assert verifier.verify_deployed(manifest, cache_root=tmp_path / "cache") == [
        "installed plugin example@1.2.3 tree sha256 does not match source candidate"
    ]


def test_deployed_verification_rejects_candidate_without_live_path(
    tmp_path: Path,
) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    errors = verifier.verify_deployed(manifest, cache_root=tmp_path / "cache")

    assert "deployed candidate global_claude has no live_path" in errors


def test_deployed_verification_rejects_retired_registry_entry(tmp_path: Path) -> None:
    manifest_path = _write_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry = tmp_path / "installed_plugins.json"
    registry.write_text(
        json.dumps(
            {
                "plugins": {
                    "retired@denubis-plugins": [
                        {"scope": "user", "version": "0.1.0", "installPath": "/old"}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    manifest["plugin_registry_path"] = str(registry)
    manifest["plugin_releases"]["retire"] = [
        {"name": "retired", "last_version": "0.1.0"}
    ]

    errors = verifier.verify_deployed(manifest, cache_root=tmp_path / "cache")

    assert "plugin registry does not select example@1.2.3" in errors
    assert "plugin registry still selects retired plugin retired" in errors
