#!/usr/bin/env python3
"""`.token-estimator` mapper: bind directories (current AND moved/historical) to one
canonical (person, project) so the estimator rolls them up together across dir shuffles.

A mapper file is TOML:

    person  = "Jodie"
    project = "BJET-Phase1"
    paths   = ["/abs/dir/now", "/abs/dir/old-moved", ...]

Matching is pure longest-prefix on the cwd STRING recorded in the logs — listed paths
need not still exist on disk (that is the point: a moved dir's history lives only in the
logs under its old path). Applied BEFORE default attribution; subdir = remainder after
the matched path.
"""

from __future__ import annotations
import tomllib
from pathlib import Path


def discover(roots, extra_files=None):
    """Find .token-estimator files a few levels under each root (fast; no deep walk)."""
    files = []
    for r in roots:
        rp = Path(r)
        if not rp.is_dir():
            continue
        for depth in (1, 2, 3, 4):
            files.extend(rp.glob("/".join(["*"] * depth) + "/.token-estimator"))
    if extra_files:
        files.extend(Path(f) for f in extra_files)
    return files


def load(roots, extra_files=None):
    """Return aliases [(path, person, project)] longest-prefix first. Raises on conflict."""
    aliases = []
    claimed = {}
    for f in discover(roots, extra_files):
        try:
            data = tomllib.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as e:
            raise ValueError(f"unreadable mapper {f}: {e}") from e
        person, project = data.get("person"), data.get("project")
        if not person or not project:
            if (
                "roots" in data
            ):  # a ~/.token-estimator global config, not a project mapper
                continue
            raise ValueError(f"{f}: both 'person' and 'project' are required")
        for p in data.get("paths") or []:
            p = p.rstrip("/")
            if p in claimed and claimed[p] != (person, project):
                raise ValueError(
                    f"mapper conflict: {p} claimed by {claimed[p]} and {(person, project)} (in {f})"
                )
            claimed[p] = (person, project)
            aliases.append((p, person, project))
    aliases.sort(key=lambda a: -len(a[0]))
    return aliases


def attribute(cwd, aliases, default_attribute):
    """Mapper-aware attribution → (person, project, subdir). Falls back to default."""
    if cwd:
        for path, person, project in aliases:
            if cwd == path or cwd.startswith(path + "/"):
                return (person, project, cwd[len(path) :].lstrip("/"))
    return default_attribute(cwd)
