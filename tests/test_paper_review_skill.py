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
    expected_rows = (
        "| 0 | Serial | Source lock, register/venue gate, paragraph and claim map |",
        "| 1 | Parallel wave | `ARG`, `APP`, `TRN` |",
        "| 2 | Serial | Substantive synthesis and validity-blocker assessment |",
        "| 3 | Parallel wave | `SRC`, `COH`, `SCAR` |",
        "| 4 | Serial | Source-fidelity/argument/coherence/cold-reader synthesis |",
        "| 5 | Parallel wave | `REG`, `CUT` |",
        "| 6 | Serial | Final synthesis, promotion triage, hostile recheck, coverage audit |",
    )
    absent = [row for row in expected_rows if row not in skill]
    assert not absent, f"paper-review schedule has drifted: {absent}"


def test_source_fidelity_lane_requires_a_pinpoint_ledger() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    source_lane = (SKILL_ROOT / "references/source-fidelity.md").read_text(
        encoding="utf-8"
    )
    records = (SKILL_ROOT / "references/review-records.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((skill, source_lane, records))
    for required in (
        "source-claims.md",
        "using-bibliography",
        "physical page",
        "SUPPORTED",
        "PARTIAL",
        "QUALIFIED",
        "CONTRADICTED",
        "NOT-FOUND",
        "UNVERIFIED",
    ):
        assert required in combined, f"source-fidelity contract is missing: {required}"


def test_evidence_base_retains_source_identifiers() -> None:
    evidence = (SKILL_ROOT / "references/evidence-base.md").read_text(
        encoding="utf-8"
    )
    for identifier in (
        "10.1038/s41559-018-0545-z",
        "10.1177/14782715251369964",
        "9780521847131",
    ):
        assert identifier in evidence, f"missing evidence identifier: {identifier}"


def test_author_facing_findings_pass_mode_aware_promotion_triage() -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    records = (SKILL_ROOT / "references/review-records.md").read_text(
        encoding="utf-8"
    )
    triage = (SKILL_ROOT / "references/promotion-triage.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((skill, records, triage)).lower()

    for required in (
        "evidence-only",
        "same author decision",
        "batch local faults",
        "hostile recheck",
        "merely arguable",
        "textual recovery",
        "no target count",
        "critical-friend",
        "adversarial",
    ):
        assert required in combined, f"promotion-triage contract is missing: {required}"

    assert "candidate for author-facing feedback: yes | no | defer" not in combined
