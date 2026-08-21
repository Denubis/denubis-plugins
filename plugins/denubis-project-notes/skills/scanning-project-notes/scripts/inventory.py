#!/usr/bin/env python3
"""Inventory project-note frontmatter without loading note bodies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


FRONTMATTER_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def repository_root(cwd: Path) -> Path:
    """Return the main checkout root shared by linked Git worktrees."""
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--git-common-dir"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "not a git repository" in result.stderr.lower():
            return cwd.resolve()
        detail = result.stderr.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"could not resolve Git common directory: {detail}")
    if not result.stdout.strip():
        raise RuntimeError("could not resolve Git common directory: empty result")

    common_dir = Path(result.stdout.strip())
    if not common_dir.is_absolute():
        common_dir = cwd / common_dir
    return common_dir.resolve().parent


def _is_flat_mapping(lines: list[str]) -> bool:
    keys: set[str] = set()
    for line in lines:
        if not line or line.lstrip().startswith("#"):
            continue
        if line != line.lstrip():
            return False
        key, separator, _value = line.partition(":")
        if not separator or FRONTMATTER_KEY.fullmatch(key) is None or key in keys:
            return False
        keys.add(key)
    return True


def extract_frontmatter(path: Path) -> tuple[str, str | None]:
    """Return frontmatter status and content without reading a delimited body."""
    if path.is_symlink():
        return "symlink", None

    try:
        stream = path.open("rb", buffering=0)
    except OSError:
        return "unreadable", None

    with stream:
        if stream.readline().rstrip(b"\r\n") != b"---":
            return "missing", None

        frontmatter: list[str] = []
        for raw_line in stream:
            line = raw_line.rstrip(b"\r\n")
            if line == b"---":
                if not _is_flat_mapping(frontmatter):
                    return "malformed", None
                return "present", "\n".join(frontmatter)
            try:
                frontmatter.append(line.decode("utf-8"))
            except UnicodeDecodeError:
                return "unreadable", None

        return "malformed", None


def _notes_root_status(notes_root: Path) -> str:
    if notes_root.is_symlink():
        return "symlink"
    if not notes_root.exists():
        return "absent"
    if not notes_root.is_dir():
        return "not-directory"
    return "directory"


def inventory(cwd: Path) -> dict[str, object]:
    root = repository_root(cwd)
    notes_root = root / ".notes"
    notes: list[dict[str, str | None]] = []
    excluded: list[dict[str, str]] = []
    excluded_markdown_count = 0
    root_status = _notes_root_status(notes_root)

    if root_status == "directory":
        paths = sorted(
            path
            for path in notes_root.rglob("*")
            if (path.is_file() or path.is_symlink())
            and path.suffix.lower() == ".md"
        )
        for path in paths:
            relative_path = path.relative_to(root).as_posix()
            relative_to_notes = path.relative_to(notes_root)
            if relative_to_notes.parts[0] == "local-mail":
                excluded_markdown_count += 1
                continue
            status, frontmatter = extract_frontmatter(path)
            notes.append(
                {
                    "path": relative_path,
                    "frontmatter_status": status,
                    "frontmatter": frontmatter,
                }
            )
        local_mail = notes_root / "local-mail"
        if local_mail.exists() or local_mail.is_symlink():
            excluded.append(
                {
                    "path": local_mail.relative_to(root).as_posix(),
                    "reason": "operational-state",
                }
            )

    return {
        "repository_root": str(root),
        "notes_root": str(notes_root.absolute()),
        "notes_root_exists": root_status != "absent",
        "notes_root_status": root_status,
        "markdown_count": len(notes),
        "excluded_markdown_count": excluded_markdown_count,
        "excluded": excluded,
        "notes": notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit every project note's frontmatter as one JSON inventory."
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="project path to inspect (default: current directory)",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if not arguments.cwd.is_dir():
        print(f"error: not a directory: {arguments.cwd}", file=sys.stderr)
        return 2

    try:
        result = inventory(arguments.cwd)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
