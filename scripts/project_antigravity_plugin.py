#!/usr/bin/env python3
"""Project a shared plugin into an Antigravity-compatible temporary directory.

The Claude source is never edited. Only provider-specific agent frontmatter is
changed; plugin assets, skill instructions, agent bodies, and commands are copied.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

# Source values observed in the shared Claude agent files. An unrecognized value
# must be reviewed rather than silently mapped to another provider's model.
CLAUDE_MODELS = frozenset({"sonnet", "opus", "haiku", "claude-opus-5-5"})
AGY_MODEL = "inherit"
CLAUDE_TO_AGY_TOOLS = {
    "Read": "view_file",
    "Grep": "grep_search",
    "Glob": "find_by_name",
    "Bash": "run_command",
}


class ProjectionError(ValueError):
    """The source cannot be projected without an explicit provider decision."""


def _replace_field(
    lines: list[str], field: str, replacement: str, path: Path
) -> None:
    indexes = [i for i, line in enumerate(lines) if line.startswith(f"{field}:")]
    if len(indexes) != 1:
        raise ProjectionError(f"{path}: {field} frontmatter must have one simple line")
    original = lines[indexes[0]]
    if field == "tools" and not original.partition(":")[2].strip():
        raise ProjectionError(f"{path}: tools frontmatter needs one inline value")
    newline = "\n" if original.endswith("\n") else ""
    lines[indexes[0]] = f"{field}: {replacement}{newline}"


def project_agent(text: str, path: Path) -> str:
    if not text.startswith("---\n"):
        raise ProjectionError(f"{path}: frontmatter must start with ---")
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ProjectionError(f"{path}: frontmatter closing delimiter is missing")
    frontmatter = text[4:closing]
    body = text[closing + len("\n---\n") :]
    try:
        metadata = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        raise ProjectionError(f"{path}: invalid frontmatter YAML: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ProjectionError(f"{path}: frontmatter must be a mapping")
    for required in ("name", "description"):
        value = metadata.get(required)
        if not isinstance(value, str) or not value.strip():
            raise ProjectionError(f"{path}: frontmatter {required} is missing")

    lines = frontmatter.splitlines(keepends=True)
    if "model" in metadata:
        model = metadata["model"]
        if not isinstance(model, str):
            raise ProjectionError(f"{path}: model must be a string")
        if model not in CLAUDE_MODELS and model != AGY_MODEL:
            raise ProjectionError(f"{path}: unknown model {model!r}")
        _replace_field(lines, "model", AGY_MODEL, path)

    if "tools" in metadata:
        tools = metadata["tools"]
        if isinstance(tools, str):
            names = [name.strip() for name in tools.split(",")]
        elif isinstance(tools, list) and all(isinstance(name, str) for name in tools):
            names = tools
        else:
            raise ProjectionError(f"{path}: tools must be a string or string list")
        if not names or any(not name for name in names):
            raise ProjectionError(f"{path}: tools list is empty or malformed")
        unknown = [name for name in names if name not in CLAUDE_TO_AGY_TOOLS]
        if unknown:
            raise ProjectionError(f"{path}: unknown tool {unknown[0]!r}")
        converted = ", ".join(CLAUDE_TO_AGY_TOOLS[name] for name in names)
        _replace_field(lines, "tools", f"[{converted}]", path)

    return "---\n" + "".join(lines) + "\n---\n" + body


def project_plugin(source: Path, target: Path) -> None:
    source = source.resolve()
    target = target.resolve(strict=False)
    if not source.is_dir() or not (source / "plugin.json").is_file():
        raise ProjectionError(f"{source}: plugin directory or manifest is missing")
    if target.exists() or target.is_relative_to(source):
        raise ProjectionError(f"{target}: target exists or lies inside source")
    if not target.parent.is_dir():
        raise ProjectionError(f"{target}: target parent does not exist")

    agents = source / "agents"
    if agents.is_symlink():
        raise ProjectionError(f"{agents}: agents directory symlink is not projectable")
    agent_files = sorted(agents.glob("*.md"))
    for path in agent_files:
        if path.is_symlink():
            raise ProjectionError(f"{path}: agent symlink is not projectable")
    projected_agents = {
        path.relative_to(source): project_agent(path.read_text(encoding="utf-8"), path)
        for path in agent_files
    }

    with tempfile.TemporaryDirectory(
        prefix="agy-projection-", dir=target.parent
    ) as tmp:
        projected = Path(tmp) / source.name
        shutil.copytree(
            source,
            projected,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".venv", "__pycache__", ".pytest_cache", "*.pyc"
            ),
        )
        for relative, transformed in projected_agents.items():
            destination = projected / relative
            if (projected / "agents").is_symlink() or destination.is_symlink():
                raise ProjectionError(
                    f"{destination}: projected agent symlink is not writable"
                )
            destination.write_text(transformed, encoding="utf-8")
        projected.rename(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        project_plugin(args.source, args.target)
    except ProjectionError as exc:
        print(f"projection: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
