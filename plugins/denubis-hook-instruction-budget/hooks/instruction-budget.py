#!/usr/bin/env python3
"""Alarm when always-on agent instructions exceed their agreed budget."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib as tomllib_module
except ImportError:  # pragma: no cover - exercised by the Python 3.9 hook runtime
    tomllib_module: Any = None

LINE_LIMIT = 200
BYTE_LIMIT = 32_768
DEFAULT_CODEX_PROJECT_LIMIT = 32_768
CLAUDE_IMPORT_DEPTH = 4
CLAUDE_IMPORT_PATTERN = re.compile(r"(?<![\w`])@([~/\.\w-][^\s`]*)")


@dataclass(frozen=True)
class InstructionSource:
    """One non-empty instruction file expected in startup context."""

    path: Path
    scope: str
    lines: int
    bytes: int


@dataclass(frozen=True)
class BudgetReport:
    """Measured provider instruction load and its two policy decisions."""

    provider: str
    sources: tuple[InstructionSource, ...]
    project_bytes: int
    project_limit: int

    @property
    def total_lines(self) -> int:
        return sum(source.lines for source in self.sources)

    @property
    def total_bytes(self) -> int:
        return sum(source.bytes for source in self.sources)

    @property
    def over_line_limit(self) -> bool:
        return self.total_lines > LINE_LIMIT

    @property
    def over_byte_limit(self) -> bool:
        return self.total_bytes > BYTE_LIMIT

    @property
    def within_limits(self) -> bool:
        return not self.over_line_limit and not self.over_byte_limit

    @property
    def project_truncated(self) -> bool:
        return self.provider == "codex" and self.project_bytes > self.project_limit


def _read_source(path: Path, scope: str) -> Optional[InstructionSource]:
    try:
        data = path.read_bytes()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return None
    if not data.strip():
        return None
    return InstructionSource(
        path=path,
        scope=scope,
        lines=len(data.splitlines()),
        bytes=len(data),
    )


def _directories(project_root: Path, cwd: Path) -> tuple[Path, ...]:
    project_root = project_root.resolve()
    cwd = cwd.resolve()
    try:
        relative = cwd.relative_to(project_root)
    except ValueError:
        return (cwd,)
    directories = [project_root]
    cursor = project_root
    for part in relative.parts:
        cursor /= part
        directories.append(cursor)
    return tuple(directories)


def _first_non_empty(paths: tuple[Path, ...], scope: str) -> Optional[InstructionSource]:
    for path in paths:
        source = _read_source(path, scope)
        if source is not None:
            return source
    return None


def _is_path_scoped_rule(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError):
        return False
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.startswith("paths:"):
            return True
    return False


def _rule_candidates(root: Path, scope: str) -> list[tuple[Path, str]]:
    rules_root = root / "rules"
    if not rules_root.is_dir():
        return []
    return [
        (path, scope)
        for path in sorted(rules_root.rglob("*.md"))
        if not _is_path_scoped_rule(path)
    ]


def _claude_imports(source: InstructionSource, home: Path) -> tuple[Path, ...]:
    try:
        text = source.path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError):
        return ()
    imports: list[Path] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible = re.sub(r"`[^`]*`", "", line)
        for match in CLAUDE_IMPORT_PATTERN.finditer(visible):
            raw_path = match.group(1).rstrip(",.;:)")
            if raw_path.startswith("~/"):
                path = home / raw_path[2:]
            else:
                path = Path(raw_path)
                if not path.is_absolute():
                    path = source.path.parent / path
            imports.append(path)
    return tuple(imports)


def _expand_claude_imports(
    initial: tuple[InstructionSource, ...],
    home: Path,
) -> tuple[InstructionSource, ...]:
    expanded: list[InstructionSource] = []
    seen: set[Path] = set()

    def visit(source: InstructionSource, depth: int) -> None:
        resolved = source.path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        expanded.append(source)
        if depth >= CLAUDE_IMPORT_DEPTH:
            return
        for path in _claude_imports(source, home):
            imported = _read_source(path, source.scope)
            if imported is not None:
                visit(imported, depth + 1)

    for source in initial:
        visit(source, 0)
    return tuple(expanded)


def _claude_sources(
    cwd: Path,
    home: Path,
    project_root: Path,
    config_root: Optional[Path],
) -> tuple[InstructionSource, ...]:
    config_root = config_root or home / ".claude"
    candidates: list[tuple[Path, str]] = [(config_root / "CLAUDE.md", "global")]
    candidates.extend(_rule_candidates(config_root, "global"))
    for directory in _directories(project_root, cwd):
        candidates.extend(
            (
                (directory / "CLAUDE.md", "project"),
                (directory / ".claude" / "CLAUDE.md", "project"),
                (directory / "CLAUDE.local.md", "project"),
            )
        )
        candidates.extend(_rule_candidates(directory / ".claude", "project"))

    sources: list[InstructionSource] = []
    seen: set[Path] = set()
    for path, scope in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        source = _read_source(path, scope)
        if source is not None:
            sources.append(source)
    return _expand_claude_imports(tuple(sources), home)


def _codex_sources(
    cwd: Path,
    home: Path,
    project_root: Path,
    config_root: Optional[Path],
    fallback_filenames: tuple[str, ...],
) -> tuple[InstructionSource, ...]:
    config_root = config_root or home / ".codex"
    sources: list[InstructionSource] = []
    global_source = _first_non_empty(
        (
            config_root / "AGENTS.override.md",
            config_root / "AGENTS.md",
        ),
        "global",
    )
    if global_source is not None:
        sources.append(global_source)

    for directory in _directories(project_root, cwd):
        source = _first_non_empty(
            tuple(
                [
                    directory / "AGENTS.override.md",
                    directory / "AGENTS.md",
                ]
                + [directory / name for name in fallback_filenames]
            ),
            "project",
        )
        if source is not None:
            sources.append(source)
    return tuple(sources)


def _fallback_codex_config(text: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if "=" not in line:
            continue
        key, raw_value = (part.strip() for part in line.split("=", 1))
        if key not in {"project_doc_max_bytes", "project_doc_fallback_filenames"}:
            continue
        try:
            values[key] = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError):
            continue
    return values


def _codex_config(config_root: Path) -> tuple[int, tuple[str, ...]]:
    path = config_root / "config.toml"
    try:
        data = path.read_bytes()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return DEFAULT_CODEX_PROJECT_LIMIT, ()
    if tomllib_module is not None:
        values = tomllib_module.loads(data.decode("utf-8"))
    else:
        values = _fallback_codex_config(data.decode("utf-8"))
    configured_limit = values.get(
        "project_doc_max_bytes",
        DEFAULT_CODEX_PROJECT_LIMIT,
    )
    configured_fallbacks = values.get("project_doc_fallback_filenames", [])
    project_limit = (
        configured_limit
        if isinstance(configured_limit, int) and configured_limit >= 0
        else DEFAULT_CODEX_PROJECT_LIMIT
    )
    fallbacks = tuple(
        name for name in configured_fallbacks if isinstance(name, str) and name
    )
    return project_limit, fallbacks


def inspect_instruction_budget(
    *,
    provider: str,
    cwd: Path,
    home: Path,
    project_root: Path,
    config_root: Optional[Path] = None,
    project_limit: Optional[int] = None,
) -> BudgetReport:
    """Measure applicable global and project files as one policy budget."""

    if provider == "claude":
        sources = _claude_sources(cwd, home, project_root, config_root)
        resolved_project_limit = project_limit or DEFAULT_CODEX_PROJECT_LIMIT
    elif provider == "codex":
        resolved_config_root = config_root or home / ".codex"
        configured_limit, fallback_filenames = _codex_config(resolved_config_root)
        resolved_project_limit = (
            configured_limit if project_limit is None else project_limit
        )
        sources = _codex_sources(
            cwd,
            home,
            project_root,
            resolved_config_root,
            fallback_filenames,
        )
    else:
        raise ValueError(f"unsupported provider: {provider}")
    return BudgetReport(
        provider=provider,
        sources=sources,
        project_bytes=sum(source.bytes for source in sources if source.scope == "project"),
        project_limit=resolved_project_limit,
    )


def warning_output(report: BudgetReport) -> Optional[dict[str, str]]:
    """Return a visible advisory without adding more model instructions."""

    if report.within_limits and not report.project_truncated:
        return None
    source_summary = ", ".join(
        f"{source.path} ({source.lines:,} lines, {source.bytes:,} bytes)"
        for source in report.sources
    )
    if report.within_limits:
        message = f"Always-on {report.provider} instructions risk truncation."
    else:
        message = (
            f"Always-on {report.provider} instruction budget exceeded: "
            f"{report.total_lines:,} lines and {report.total_bytes:,} bytes across "
            f"{len(report.sources)} file(s); limits are {LINE_LIMIT:,} lines and "
            f"{BYTE_LIMIT:,} bytes for the combined global + local chain."
        )
    if report.project_truncated:
        message += (
            f" Codex's project chain is {report.project_bytes:,} bytes, above its "
            f"configured {report.project_limit:,}-byte loader limit; "
            "later project instructions can be truncated."
        )
    message += f" Sources: {source_summary}."
    return {"systemMessage": message}


def _git_root(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return cwd


def _runtime_report(provider: str, cwd: Path) -> BudgetReport:
    home = Path.home()
    if provider == "claude":
        config_root = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude"))
        project_root = Path(cwd.anchor)
    else:
        config_root = Path(os.environ.get("CODEX_HOME", home / ".codex"))
        project_root = _git_root(cwd)
    return inspect_instruction_budget(
        provider=provider,
        cwd=cwd,
        home=home,
        project_root=project_root,
        config_root=config_root,
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("claude", "codex"), required=True)
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    try:
        payload = json.load(sys.stdin)
        payload_cwd = payload.get("cwd") if isinstance(payload, dict) else None
        cwd = Path(payload_cwd) if isinstance(payload_cwd, str) else Path.cwd()
        output = warning_output(_runtime_report(arguments.provider, cwd))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        output = {
            "systemMessage": (
                "Instruction budget guard could not inspect the startup chain: "
                f"{error}"
            )
        }
    if output is not None:
        json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()
