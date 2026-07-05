"""Tests for the `.token-estimator` mapper — the dual-role TOML file.

A project-dir mapper binds directories (current AND moved) to one canonical
(person, project) so a dir shuffle doesn't fragment a project's history. A home
`~/.token-estimator` is a global *config* (it has `roots`, no person/project) and
must be skipped, not treated as a broken mapper. Matching is longest-prefix on the
recorded cwd string, so moved/defunct paths still resolve.
"""

from __future__ import annotations

import mapper as M
import pytest


def _mapper(path, person, project, paths):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f'person = "{person}"', f'project = "{project}"', "paths = ["]
    body += [f'  "{p}",' for p in paths]
    body += ["]", ""]
    path.write_text("\n".join(body), encoding="utf-8")


def _unmapped(cwd):
    # sentinel default-attribution: uses cwd so it stays ruff-clean (no unused arg).
    return ("UNMAPPED", "UNMAPPED", cwd)


def test_load_and_attribute_maps_moved_dir(tmp_path):
    root = tmp_path / "people"
    _mapper(
        root / "Jodie" / "BJET" / ".token-estimator",
        "Jodie",
        "BJET-Phase1",
        ["/home/x/people/Jodie/BJET-current", "/home/x/people/Jodie/old-moved"],
    )
    aliases = M.load([str(root)])
    assert ("/home/x/people/Jodie/old-moved", "Jodie", "BJET-Phase1") in aliases
    # a recorded cwd under the moved (now-defunct) path still resolves to the project.
    assert M.attribute("/home/x/people/Jodie/old-moved/sub", aliases, _unmapped) == (
        "Jodie",
        "BJET-Phase1",
        "sub",
    )
    # a cwd under no mapped path falls through to the default attribution.
    assert M.attribute("/somewhere/else", aliases, _unmapped) == (
        "UNMAPPED",
        "UNMAPPED",
        "/somewhere/else",
    )


def test_global_config_file_is_skipped_not_an_error(tmp_path):
    root = tmp_path / "people"
    cfg = root / "Person" / ".token-estimator"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('roots = ["/a", "/b"]\n', encoding="utf-8")
    assert M.load([str(root)]) == []  # a roots-only file is config, not a mapper


def test_missing_person_or_project_raises(tmp_path):
    root = tmp_path / "people"
    bad = root / "P" / "Q" / ".token-estimator"
    bad.parent.mkdir(parents=True)
    bad.write_text('project = "X"\npaths = ["/a"]\n', encoding="utf-8")  # no person
    with pytest.raises(ValueError, match=r"person.*project"):
        M.load([str(root)])


def test_conflicting_claims_raise(tmp_path):
    root = tmp_path / "people"
    _mapper(root / "A" / "m" / ".token-estimator", "Alice", "P1", ["/shared/path"])
    _mapper(root / "B" / "m" / ".token-estimator", "Bob", "P2", ["/shared/path"])
    with pytest.raises(ValueError, match="conflict"):
        M.load([str(root)])


def test_longest_prefix_wins(tmp_path):
    root = tmp_path / "people"
    _mapper(root / "A" / "m" / ".token-estimator", "Alice", "Outer", ["/data"])
    _mapper(root / "A" / "n" / ".token-estimator", "Alice", "Inner", ["/data/inner"])
    aliases = M.load([str(root)])
    assert M.attribute("/data/inner/x", aliases, _unmapped) == ("Alice", "Inner", "x")
    assert M.attribute("/data/other", aliases, _unmapped) == ("Alice", "Outer", "other")
