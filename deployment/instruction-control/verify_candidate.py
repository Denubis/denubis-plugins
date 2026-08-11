#!/usr/bin/env python3
"""Recompute instruction-control source, baseline, and deployment bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_IGNORED_TREE_PARTS = {".in_use", ".pytest_cache", "__pycache__"}


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


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _authority_errors(manifest: dict[str, Any]) -> list[str]:
    authority = manifest.get("authority", {})
    source = Path(authority["human_source"])
    wanted = set(authority["human_source_lines"])
    found: dict[int, Any] = {}
    if not source.is_file():
        return [f"authority source is missing: {source}"]

    with source.open(encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if line_number in wanted:
                try:
                    found[line_number] = json.loads(raw_line)
                except json.JSONDecodeError:
                    found[line_number] = None

    errors: list[str] = []
    for line_number in sorted(wanted):
        record = found.get(line_number)
        payload = record.get("payload", {}) if isinstance(record, dict) else {}
        content = payload.get("content", [])
        input_text = [
            item.get("text")
            for item in content
            if isinstance(item, dict) and item.get("type") == "input_text"
        ]
        valid = (
            isinstance(record, dict)
            and record.get("type") == "response_item"
            and payload.get("type") == "message"
            and payload.get("role") == "user"
            and len(input_text) == 1
            and isinstance(input_text[0], str)
            and bool(input_text[0])
        )
        if not valid:
            errors.append(
                f"authority line {line_number} is not one non-empty user "
                "input_text record"
            )
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
                errors.append(f'catalogue still publishes retired plugin {retired["name"]}')
    return errors


def verify_source(repo_root: Path, manifest_path: Path) -> list[str]:
    """Verify all source artifacts and human-authority records in a manifest."""
    manifest = _load_manifest(manifest_path)
    return [
        *_candidate_errors(repo_root, manifest),
        *_authority_errors(manifest),
        *_plugin_source_errors(repo_root, manifest),
    ]


def verify_baselines(manifest: dict[str, Any]) -> list[str]:
    """Reject deployment if a mutable live file changed after candidate preparation."""
    errors: list[str] = []
    for name, record in manifest.get("baselines", {}).items():
        path = Path(record["path"])
        if not path.is_absolute():
            continue
        if not path.is_file():
            errors.append(f"live baseline {name} is missing: {path}")
            continue
        if path.stat().st_size != record["bytes"]:
            errors.append(f"live baseline {name} bytes changed")
        if sha256_file(path) != record["sha256"]:
            errors.append(f"live baseline {name} sha256 changed")
    return errors


def verify_deployed(
    manifest: dict[str, Any], *, cache_root: Path
) -> list[str]:
    """Compare live files and installed plugin trees with the source candidate."""
    errors: list[str] = []
    for name, record in manifest.get("candidates", {}).items():
        live_path_value = record.get("live_path")
        if not live_path_value:
            continue
        live_path = Path(live_path_value)
        if not live_path.is_file():
            errors.append(f"deployed candidate {name} is missing: {live_path}")
            continue
        if live_path.stat().st_size != record["bytes"]:
            errors.append(f"deployed candidate {name} bytes do not match")
        if sha256_file(live_path) != record["sha256"]:
            errors.append(f"deployed candidate {name} sha256 does not match")

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
            if not any(entry.get("version") == release["version"] for entry in selected):
                errors.append(
                    f'plugin registry does not select {release["name"]}@{release["version"]}'
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
    parser.add_argument("mode", choices=("source", "baseline", "deployed"))
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
        errors = verify_baselines(manifest)
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
