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
    "references/review-records.md",
    "references/source-fidelity.md",
    "references/toulmin-analysis.md",
)


def _markdown_files() -> list[Path]:
    return sorted(SKILL_ROOT.rglob("*.md"))


def _schedule_rows(text: str) -> list[tuple[int, str, set[str]]]:
    rows: list[tuple[int, str, set[str]]] = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[0].isdigit():
            continue
        lanes = set(re.findall(r"`([A-Z]+)`", cells[2]))
        rows.append((int(cells[0]), cells[1], lanes))
    return rows


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


def test_hybrid_schedule_preserves_independent_lanes_and_serial_gates() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    rows = _schedule_rows(skill)

    assert [stage for stage, _mode, _lanes in rows] == list(range(7))
    assert [mode for _stage, mode, _lanes in rows] == [
        "Serial",
        "Parallel wave",
        "Serial",
        "Parallel wave",
        "Serial",
        "Parallel wave",
        "Serial",
    ]
    assert [lanes for _stage, _mode, lanes in rows if lanes] == [
        {"ARG", "APP", "TRN"},
        {"SRC", "COH", "SCAR"},
        {"REG", "CUT"},
    ]


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
