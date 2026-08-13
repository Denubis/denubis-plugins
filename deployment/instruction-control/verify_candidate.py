#!/usr/bin/env python3
"""Recompute instruction-control source, baseline, and deployment bindings."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Exact components below are generated runtime state, not release source.
_IGNORED_TREE_PARTS = {".in_use", ".pytest_cache", ".venv", "__pycache__"}


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    """Bind a tree's relative paths and file contents, excluding runtime residue."""
    digest = hashlib.sha256()
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not (_IGNORED_TREE_PARTS & set(path.relative_to(root).parts))
        and path.suffix != ".pyc"
    )
    for path in files:
        relative = path.relative_to(root).as_posix().encode()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\n")
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
    )
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be an object")
    schema_version = manifest.get("schema_version")
    if schema_version != 1:
        raise ValueError(
            f"unsupported manifest schema_version: {schema_version}"
        )
    return manifest


def _candidate_errors(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    resolved_root = repo_root.resolve()
    for name, record in manifest.get("candidates", {}).items():
        path = (repo_root / record["path"]).resolve()
        if not path.is_relative_to(resolved_root):
            errors.append(f"candidate {name} escapes repository root")
            continue
        if not path.is_file():
            errors.append(f"candidate {name} is missing: {path}")
            continue
        if path.stat().st_size != record["bytes"]:
            errors.append(f"candidate {name} bytes do not match manifest")
        if sha256_file(path) != record["sha256"]:
            errors.append(f"candidate {name} sha256 does not match manifest")
    return errors


def _jsonl_record(path: Path, line_number: int) -> dict[str, Any] | None:
    if not path.is_file() or line_number < 1:
        return None
    with path.open(encoding="utf-8") as stream:
        for current_line, raw_line in enumerate(stream, start=1):
            if current_line != line_number:
                continue
            try:
                value = json.loads(raw_line)
            except json.JSONDecodeError:
                return None
            return value if isinstance(value, dict) else None
    return None


def _codex_user_text(record: dict[str, Any] | None) -> str | None:
    if not isinstance(record, dict) or record.get("type") != "response_item":
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    content = payload.get("content")
    if (
        payload.get("type") != "message"
        or payload.get("role") != "user"
        or not isinstance(content, list)
    ):
        return None
    text_items = [
        item.get("text")
        for item in content
        if isinstance(item, dict) and item.get("type") == "input_text"
    ]
    if len(text_items) != 1 or not isinstance(text_items[0], str):
        return None
    return text_items[0] or None


def _claude_user_text(record: dict[str, Any] | None) -> str | None:
    if not isinstance(record, dict) or record.get("type") != "user":
        return None
    message = record.get("message")
    if not isinstance(message, dict) or message.get("role") != "user":
        return None
    content = message.get("content")
    return content if isinstance(content, str) and content else None


def _authority_record_errors(
    record_id: str, binding: dict[str, Any]
) -> list[str]:
    path = Path(binding["path"])
    line_number = binding["line"]
    if not path.is_file():
        return [f"authority record {record_id} source is missing: {path}"]

    record = _jsonl_record(path, line_number)
    record_format = binding.get("format")
    if record_format == "codex_user_text":
        text = _codex_user_text(record)
        invalid = (
            f"authority record {record_id} line {line_number} is not one "
            "non-empty Codex user input_text record"
        )
    elif record_format == "claude_user_text":
        text = _claude_user_text(record)
        invalid = (
            f"authority record {record_id} line {line_number} is not one "
            "non-empty Claude user text record"
        )
    else:
        return [
            f"authority record {record_id} has unsupported format: {record_format}"
        ]

    if text is None:
        return [invalid]
    if hashlib.sha256(text.encode()).hexdigest() != binding.get("text_sha256"):
        return [f"authority record {record_id} text sha256 does not match"]
    return []


def _authority_mapping_errors(
    manifest: dict[str, Any], actions: dict[str, Any]
) -> list[str]:
    errors: list[str] = []

    def check(label: str, record: dict[str, Any]) -> None:
        selected = record.get("authority_actions")
        if not isinstance(selected, list) or not selected:
            errors.append(f"{label} has no authority action")
            return
        for action in selected:
            if action not in actions:
                errors.append(f"{label} names unknown authority action {action}")

    for name, record in manifest.get("candidates", {}).items():
        check(f"candidate {name}", record)
    releases = manifest.get("plugin_releases", {})
    for release in releases.get("install", []):
        check(f'plugin release {release["name"]}@{release["version"]}', release)
    for release in releases.get("retire", []):
        check(f'retired plugin {release["name"]}', release)
    transition = manifest.get("settings_transition")
    if transition:
        check("settings transition", transition)
    history_contract = manifest.get("codex_history_contract")
    if history_contract:
        check("Codex history contract", history_contract)
    return errors


def _authority_errors(manifest: dict[str, Any]) -> list[str]:
    authority = manifest.get("authority", {})
    records = authority.get("records", {})
    actions = authority.get("actions", {})
    errors: list[str] = []
    for record_id, binding in records.items():
        errors.extend(_authority_record_errors(record_id, binding))
    for action_name, action in actions.items():
        selected = action.get("records")
        if not isinstance(selected, list) or not selected:
            errors.append(f"authority action {action_name} has no records")
            continue
        for record_id in selected:
            if record_id not in records:
                errors.append(
                    f"authority action {action_name} names unknown record {record_id}"
                )
    errors.extend(_authority_mapping_errors(manifest, actions))
    return errors


def _settings_contract_errors(
    repo_root: Path, manifest: dict[str, Any]
) -> list[str]:
    contract = manifest.get("settings_contract")
    if not contract:
        return []

    candidate_name = contract.get("candidate")
    candidate = manifest.get("candidates", {}).get(candidate_name)
    if not candidate:
        return ["settings contract names an unknown candidate"]

    path = (repo_root / candidate["path"]).resolve()
    if not path.is_relative_to(repo_root.resolve()) or not path.is_file():
        return []  # `_candidate_errors` reports the binding failure.

    settings = json.loads(path.read_text(encoding="utf-8"))
    env = settings.get("env", {})
    forbidden = set(contract.get("forbidden_env", []))
    return [
        f"settings candidate contains forbidden environment variable {name}"
        for name in sorted(forbidden & set(env))
    ]


def _codex_history_contract_errors(manifest: dict[str, Any]) -> list[str]:
    contract = manifest.get("codex_history_contract")
    if not contract:
        return []

    path = Path(contract["path"])
    if not path.is_absolute() or not path.is_file():
        return [f"Codex history config is missing: {path}"]
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        return [f"Codex history config is invalid TOML: {error}"]

    history = config.get("history", {})
    expected = contract.get("persistence", "save-all")
    actual = history.get("persistence")
    errors: list[str] = []
    if actual != expected:
        errors.append(
            f"Codex history persistence is {actual}, expected {expected}"
        )
    if contract.get("forbid_max_bytes") and "max_bytes" in history:
        errors.append("Codex history max_bytes must remain unset")
    return errors


def _plugin_source_errors(repo_root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    installs = manifest.get("plugin_releases", {}).get("install", [])
    for release in installs:
        label = f'{release["name"]}@{release["version"]}'
        source = repo_root / release["source"]
        plugin_json = source / ".claude-plugin" / "plugin.json"
        if not plugin_json.is_file():
            errors.append(f"plugin release {label} has no source manifest")
            continue
        plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
        if (plugin.get("name"), plugin.get("version")) != (
            release["name"],
            release["version"],
        ):
            errors.append(f"plugin release {label} source identity does not match")
        if sha256_tree(source) != release["tree_sha256"]:
            errors.append(f"plugin release {label} tree sha256 does not match manifest")

    catalogue_path = manifest.get("catalogue_path")
    if catalogue_path:
        catalogue = json.loads(
            (repo_root / catalogue_path).read_text(encoding="utf-8")
        )
        versions = {
            plugin["name"]: plugin["version"] for plugin in catalogue["plugins"]
        }
        for release in installs:
            if versions.get(release["name"]) != release["version"]:
                errors.append(
                    f'catalogue does not publish {release["name"]}@{release["version"]}'
                )
        for retired in manifest.get("plugin_releases", {}).get("retire", []):
            if retired["name"] in versions:
                errors.append(
                    f'catalogue still publishes retired plugin {retired["name"]}'
                )
    return errors


def verify_source(repo_root: Path, manifest_path: Path) -> list[str]:
    """Verify all source artifacts and human-authority records in a manifest."""
    manifest = _load_manifest(manifest_path)
    return [
        *_candidate_errors(repo_root, manifest),
        *_authority_errors(manifest),
        *_settings_contract_errors(repo_root, manifest),
        *_codex_history_contract_errors(manifest),
        *_plugin_source_errors(repo_root, manifest),
    ]


def _apply_enabled_plugin_changes(
    settings: dict[str, Any], changes: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    enabled_plugins = settings.get("enabledPlugins", {})
    for plugin_id in changes.get("remove", []):
        if plugin_id not in enabled_plugins:
            errors.append(
                f"settings transition cannot remove missing plugin {plugin_id}"
            )
        else:
            del enabled_plugins[plugin_id]
    for plugin_id, value in changes.get("add", {}).items():
        enabled_plugins[plugin_id] = value
    return errors


def _apply_permission_changes(
    settings: dict[str, Any], changes: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    allowed = settings.get("permissions", {}).get("allow", [])
    for permission in changes.get("remove", []):
        if permission not in allowed:
            errors.append(
                f"settings transition cannot remove missing permission {permission}"
            )
        else:
            allowed.remove(permission)
    for permission in changes.get("add", []):
        if permission not in allowed:
            allowed.append(permission)
    return errors


def _settings_transition_errors(
    manifest: dict[str, Any], *, repo_root: Path
) -> list[str]:
    transition = manifest.get("settings_transition")
    if not transition:
        return []

    baseline_name = transition.get("baseline")
    candidate_name = transition.get("candidate")
    baseline_record = manifest.get("baselines", {}).get(baseline_name)
    candidate_record = manifest.get("candidates", {}).get(candidate_name)
    if not baseline_record or not candidate_record:
        return ["settings transition names an unknown baseline or candidate"]

    baseline_path = Path(baseline_record["path"])
    candidate_path = (repo_root / candidate_record["path"]).resolve()
    if not baseline_path.is_absolute() or not baseline_path.is_file():
        return ["settings transition baseline is not a live absolute file"]
    if not candidate_path.is_relative_to(repo_root.resolve()):
        return ["settings transition candidate escapes repository root"]
    if not candidate_path.is_file():
        return [f"settings transition candidate is missing: {candidate_path}"]

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    expected = copy.deepcopy(baseline)
    errors = _apply_enabled_plugin_changes(
        expected, transition.get("enabled_plugins", {})
    )
    errors.extend(
        _apply_permission_changes(
            expected, transition.get("permission_allow", {})
        )
    )

    if not errors and expected != candidate:
        errors.append(
            "settings transition changes values outside its declared ownership"
        )
    return errors


def verify_baselines(
    manifest: dict[str, Any], *, repo_root: Path
) -> list[str]:
    """Reject deployment if a mutable live file changed after candidate preparation."""
    errors: list[str] = []
    for name, record in manifest.get("baselines", {}).items():
        binding = record["path"]
        path = Path(binding)
        if path.is_absolute():
            if not path.is_file():
                errors.append(f"live baseline {name} is missing: {path}")
                continue
            content = path.read_bytes()
        else:
            errors.append(
                f"live baseline {name} has unsupported binding: {binding}"
            )
            continue

        if len(content) != record["bytes"]:
            errors.append(f"live baseline {name} bytes changed")
        if hashlib.sha256(content).hexdigest() != record["sha256"]:
            errors.append(f"live baseline {name} sha256 changed")
    errors.extend(_settings_transition_errors(manifest, repo_root=repo_root))
    return errors


def verify_project_integration(manifest: dict[str, Any]) -> list[str]:
    """Require the project-owned live file to equal its reviewed candidate."""
    integration = manifest.get("project_integration")
    if not integration:
        return ["manifest has no project integration contract"]
    candidate_name = integration.get("candidate")
    candidate = manifest.get("candidates", {}).get(candidate_name)
    if not candidate:
        return ["project integration names an unknown candidate"]
    live_path_value = candidate.get("live_path")
    if not live_path_value:
        return [f"project integration {candidate_name} has no live_path"]
    live_path = Path(live_path_value)
    if not live_path.is_file():
        return [f"project integration {candidate_name} is missing: {live_path}"]

    errors: list[str] = []
    if live_path.stat().st_size != candidate["bytes"]:
        errors.append(f"project integration {candidate_name} bytes do not match")
    if sha256_file(live_path) != candidate["sha256"]:
        errors.append(f"project integration {candidate_name} sha256 does not match")
    return errors


def _deployed_candidate_errors(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name, record in manifest.get("candidates", {}).items():
        live_path_value = record.get("live_path")
        if not live_path_value:
            errors.append(f"deployed candidate {name} has no live_path")
            continue
        live_path = Path(live_path_value)
        if not live_path.is_file():
            errors.append(f"deployed candidate {name} is missing: {live_path}")
            continue
        if live_path.stat().st_size != record["bytes"]:
            errors.append(f"deployed candidate {name} bytes do not match")
        if sha256_file(live_path) != record["sha256"]:
            errors.append(f"deployed candidate {name} sha256 does not match")
    return errors


def verify_deployed(
    manifest: dict[str, Any], *, cache_root: Path
) -> list[str]:
    """Compare live files and installed plugin trees with the source candidate."""
    errors = [
        *_deployed_candidate_errors(manifest),
        *_codex_history_contract_errors(manifest),
    ]

    releases = manifest.get("plugin_releases", {})
    installs = releases.get("install", [])
    registry_path_value = manifest.get("plugin_registry_path")
    registry_plugins: dict[str, list[dict[str, Any]]] | None = None
    if registry_path_value:
        registry_path = Path(registry_path_value)
        if not registry_path.is_file():
            errors.append(f"plugin registry is missing: {registry_path}")
        else:
            registry_plugins = json.loads(
                registry_path.read_text(encoding="utf-8")
            ).get("plugins", {})

    if registry_plugins is not None:
        for release in installs:
            plugin_id = f'{release["name"]}@denubis-plugins'
            selected = registry_plugins.get(plugin_id, [])
            if not any(
                entry.get("version") == release["version"] for entry in selected
            ):
                errors.append(
                    "plugin registry does not select "
                    f'{release["name"]}@{release["version"]}'
                )
        for retired in releases.get("retire", []):
            plugin_id = f'{retired["name"]}@denubis-plugins'
            if registry_plugins.get(plugin_id):
                errors.append(
                    f'plugin registry still selects retired plugin {retired["name"]}'
                )

    for release in installs:
        label = f'{release["name"]}@{release["version"]}'
        installed = cache_root / release["name"] / release["version"]
        if not installed.is_dir():
            errors.append(f"installed plugin {label} is missing")
        elif sha256_tree(installed) != release["tree_sha256"]:
            errors.append(
                f"installed plugin {label} tree sha256 does not match source candidate"
            )
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("source", "baseline", "project", "deployed")
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path.home() / ".claude/plugins/cache/denubis-plugins",
    )
    return parser


def _infer_repo_root(manifest_path: Path) -> Path:
    for parent in manifest_path.parents:
        if (parent / ".claude-plugin" / "marketplace.json").is_file():
            return parent
    raise ValueError("cannot infer repository root; pass --repo-root")


def main() -> int:
    args = _parser().parse_args()
    manifest_path = args.manifest.resolve()
    manifest = _load_manifest(manifest_path)
    repo_root = args.repo_root or _infer_repo_root(manifest_path)
    if args.mode == "source":
        errors = verify_source(repo_root, manifest_path)
    elif args.mode == "baseline":
        errors = verify_baselines(manifest, repo_root=repo_root)
    elif args.mode == "project":
        errors = verify_project_integration(manifest)
    else:
        errors = verify_deployed(manifest, cache_root=args.cache_root)

    evidence = {
        "schema_version": 1,
        "mode": args.mode,
        "observed_at": datetime.now(UTC).isoformat(),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "ok": not errors,
        "errors": errors,
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
