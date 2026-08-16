#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit==0.15.1",
# ]
# ///
"""Update the launcher-owned portion of a Codex profile."""

import os
import sys
from pathlib import Path

import tomlkit
from tomlkit.items import InlineTable, Table


def _dump_with_source_newlines(document: tomlkit.TOMLDocument, source: str) -> str:
    """Render the document without changing a consistently CRLF source."""
    result = tomlkit.dumps(document)
    if "\r\n" in source and "\n" not in source.replace("\r\n", ""):
        return result.replace("\r\n", "\n").replace("\n", "\r\n")
    return result


def rewrite_profile(source: str, skill_paths: list[str]) -> str:
    """Return a profile with the launcher-owned skill policy refreshed."""
    document = tomlkit.parse(source)
    skills = document.get("skills")

    if skills is not None and not isinstance(skills, (InlineTable, Table)):
        raise ValueError("top-level 'skills' must be a table")

    if not skill_paths:
        if skills is not None and "config" in skills:
            del skills["config"]
        return _dump_with_source_newlines(document, source)

    if skills is None:
        skills = tomlkit.table()
        document["skills"] = skills
    elif isinstance(skills, InlineTable):
        expanded_skills = tomlkit.table()
        for key, value in skills.items():
            if key != "config":
                expanded_skills.add(key, value)
        document["skills"] = expanded_skills
        skills = expanded_skills

    config = tomlkit.aot()
    for skill_path in skill_paths:
        entry = tomlkit.table()
        entry.add("path", skill_path)
        entry.add("enabled", False)
        config.append(entry)
    skills["config"] = config
    return _dump_with_source_newlines(document, source)


def read_skill_paths(path: Path) -> list[str]:
    """Read the launcher's NUL-delimited skill-path list."""
    raw = path.read_bytes()
    if not raw:
        return []
    if not raw.endswith(b"\0"):
        raise ValueError(f"skill path list is not NUL terminated: {path}")
    return [os.fsdecode(value) for value in raw[:-1].split(b"\0")]


def update_file(profile: Path, output: Path, skill_list: Path) -> None:
    """Read, rewrite, and stage a profile for the shell's atomic replacement."""
    if profile.exists():
        with profile.open("r", encoding="utf-8", newline="") as stream:
            source = stream.read()
    else:
        source = ""
    result = rewrite_profile(source, read_skill_paths(skill_list))
    output.write_text(result, encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    """Update one staged profile, reporting parse and filesystem errors cleanly."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        sys.stderr.write(
            "usage: update_codex_profile.py PROFILE OUTPUT SKILL_LIST\n"
        )
        return 2

    profile, output, skill_list = map(Path, arguments)
    try:
        update_file(profile, output, skill_list)
    except (OSError, UnicodeError, ValueError, tomlkit.exceptions.ParseError) as error:
        sys.stderr.write(f"could not update Codex profile {profile}: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
