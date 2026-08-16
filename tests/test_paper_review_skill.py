"""Packaging and workflow invariants for the academic paper-review skill."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = (
    REPO_ROOT
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "paper-review"
)

REQUIRED_FILES = (
    "SKILL.md",
    "references/evidence-base.md",
    "references/promotion-triage.md",
    "references/review-lanes.md",
    "references/source-fidelity.md",
    "references/toulmin-analysis.md",
)


def _markdown_files() -> list[Path]:
    return sorted(SKILL_ROOT.rglob("*.md"))


def test_paper_review_package_is_complete() -> None:
    missing = [name for name in REQUIRED_FILES if not (SKILL_ROOT / name).is_file()]
    assert not missing, f"paper-review package is missing: {missing}"


def test_paper_review_package_is_portable() -> None:
    forbidden = ("/home/", "planning/copyedit-")
    violations = {
        str(path.relative_to(SKILL_ROOT)): token
        for path in _markdown_files()
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    }
    assert not violations, f"machine- or project-specific references: {violations}"


def test_relative_markdown_links_resolve() -> None:
    missing: list[tuple[str, str]] = []
    link_pattern = re.compile(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")
    for path in _markdown_files():
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if "://" not in target and not (path.parent / target).resolve().exists():
                missing.append((str(path.relative_to(SKILL_ROOT)), target))
    assert not missing, f"broken relative links: {missing}"


def test_reference_material_is_reachable_from_the_skill() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    linked = set(re.findall(r"\[[^]]+\]\((references/[^)#]+)", skill))
    expected = {name for name in REQUIRED_FILES if name.startswith("references/")}

    assert expected <= linked, f"unreachable paper-review references: {expected - linked}"


def test_evidence_base_retains_source_identifiers() -> None:
    evidence = (SKILL_ROOT / "references/evidence-base.md").read_text(
        encoding="utf-8"
    )
    observed = set(
        re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+|\b\d{13}\b", evidence)
    )
    required = {
        "10.1038/s41559-018-0545-z",
        "10.1177/14782715251369964",
        "9780521847131",
    }

    assert required <= observed
