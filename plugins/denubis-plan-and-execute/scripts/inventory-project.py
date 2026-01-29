#!/usr/bin/env python3
"""Project context inventory discovery script.

Discovers and extracts project context for Claude Code subagents:
- CLAUDE.md and AGENTS.md file locations
- Command patterns (uv run, pytest, ruff, etc.)
- MCP server configurations
- Installed plugins

Outputs structured markdown to stdout or specified file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def get_git_root() -> Path | None:
    """Get the git repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_current_commit_sha() -> str | None:
    """Get the current HEAD commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_markdown_files(root: Path, filename: str) -> list[dict[str, str | list[str]]]:
    """Find all files matching filename recursively under root.

    Returns list of dicts with 'path' and 'sections' (H2 headers).
    """
    results = []
    for path in root.rglob(filename):
        # Skip files in .git, node_modules, __pycache__, etc.
        parts = path.parts
        if any(part.startswith(".") and part != "." for part in parts):
            continue
        if any(part in ("node_modules", "__pycache__", "venv", ".venv") for part in parts):
            continue

        sections = extract_h2_headers(path)
        results.append({
            "path": str(path.relative_to(root)),
            "sections": sections,
        })

    return sorted(results, key=lambda x: x["path"])


def extract_h2_headers(filepath: Path) -> list[str]:
    """Extract H2 (##) headers from a markdown file."""
    headers = []
    try:
        content = filepath.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("## "):
                headers.append(line[3:].strip())
    except (OSError, UnicodeDecodeError):
        pass
    return headers


def format_markdown_files_section(
    files: list[dict[str, str | list[str]]],
    title: str,
    description: str,
) -> str:
    """Format a section listing markdown files."""
    lines = [f"## {title}", "", description, ""]

    if not files:
        lines.append("*None found*")
        lines.append("")
        return "\n".join(lines)

    for file_info in files:
        path = file_info["path"]
        sections = file_info["sections"]
        lines.append(f"### `{path}`")
        lines.append("")
        if sections:
            lines.append("Sections:")
            for section in sections:
                lines.append(f"- {section}")
        else:
            lines.append("*No sections found*")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discover project context for Claude Code subagents"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: git root or cwd)",
    )
    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = args.project_root.resolve()
    else:
        git_root = get_git_root()
        project_root = git_root if git_root else Path.cwd()

    if not project_root.is_dir():
        print(f"Error: {project_root} is not a directory", file=sys.stderr)
        return 1

    # Get commit SHA for staleness detection
    commit_sha = get_current_commit_sha()

    # Discover files
    claude_files = find_markdown_files(project_root, "CLAUDE.md")
    agents_files = find_markdown_files(project_root, "AGENTS.md")

    # Build output
    output_lines = [
        "# Project Context Inventory",
        "",
        f"Generated at commit: `{commit_sha or 'unknown'}`",
        "",
    ]

    output_lines.append(format_markdown_files_section(
        claude_files,
        "CLAUDE.md Files",
        "Project instruction files that Claude Code reads for context.",
    ))

    output_lines.append(format_markdown_files_section(
        agents_files,
        "AGENTS.md Files",
        "Subagent configuration and documentation files.",
    ))

    output = "\n".join(output_lines)

    # Write output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"Wrote inventory to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
