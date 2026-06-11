"""Standing enforcement of AC2.6.8 era-claim invariants for model-tier-notes.md.

Promoted from a per-phase manual grep (Phase 2.6 GREEN verification, upstream-sync
plan) to a standing test by the 2026-06-11 coherence-review disposition: the same
staleness class recurs in Phases 3/4, so the invariant belongs in pytest, not in a
transcript.

Mechanisable subset of AC2.6.8 only. Judgement-laden checks (benchmark-number
claims, whether a behavioural claim "sits under" a dated header) stay with human
review; these tests catch the failure modes a regex can prove:

1. The frontmatter ``last-verified`` header exists and parses as an ISO date.
2. Every external citation ``<https://...>`` carries a same-line
   ``(verified YYYY-MM-DD)`` marker — one per URL.
3. No bare generation era-claims ("4.x"-style).
4. Every "current models / current Claude tier" phrase is anchored by a nearby
   model-name enumeration, never left floating.

Run ad hoc with `uv run pytest tests/test_model_tier_freshness.py -v`.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_TIER_NOTES = (
    REPO_ROOT
    / "plugins/denubis-extending-claude/skills/writing-claude-directives/model-tier-notes.md"
)

URL_PATTERN = re.compile(r"<https?://[^>]+>")
VERIFIED_PATTERN = re.compile(r"\(verified \d{4}-\d{2}-\d{2}\)")
BARE_GENERATION_PATTERN = re.compile(r"\b\d\.x\b", re.IGNORECASE)
CURRENT_TIER_PATTERN = re.compile(r"current\s+(?:Claude\s+)?(?:models?|tier)", re.IGNORECASE)
# Any concrete model name counts as an enumeration anchor.
MODEL_NAME_PATTERN = re.compile(r"(?:Fable|Opus|Sonnet|Haiku)\s+\d")
ANCHOR_WINDOW = 80  # chars after the phrase within which an anchor must appear


def find_unverified_citations(text: str) -> list[str]:
    """Return one violation message per line whose URL count exceeds its
    same-line ``(verified YYYY-MM-DD)`` count."""
    violations: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        n_urls = len(URL_PATTERN.findall(line))
        n_verified = len(VERIFIED_PATTERN.findall(line))
        if n_urls > n_verified:
            violations.append(
                f"line {lineno}: {n_urls} citation URL(s) but only "
                f"{n_verified} (verified YYYY-MM-DD) marker(s): {line.strip()[:120]}"
            )
    return violations


def find_bare_generation_claims(text: str) -> list[str]:
    """Return one violation message per line containing a bare 'N.x' era-claim."""
    return [
        f"line {lineno}: {line.strip()[:120]}"
        for lineno, line in enumerate(text.splitlines(), start=1)
        if BARE_GENERATION_PATTERN.search(line)
    ]


def find_unanchored_current_tier(text: str) -> list[str]:
    """Return one violation message per 'current models/tier' phrase not followed
    within ANCHOR_WINDOW chars by a concrete model-name enumeration."""
    violations: list[str] = []
    for match in CURRENT_TIER_PATTERN.finditer(text):
        window = text[match.end() : match.end() + ANCHOR_WINDOW]
        if not MODEL_NAME_PATTERN.search(window):
            lineno = text.count("\n", 0, match.start()) + 1
            violations.append(
                f"line {lineno}: {match.group(0)!r} not anchored by a model-name "
                f"enumeration within {ANCHOR_WINDOW} chars"
            )
    return violations


def parse_last_verified(text: str) -> date:
    """Return the frontmatter ``last-verified`` value as a date; raise ValueError
    if the field is missing or malformed."""
    match = re.search(r"^last-verified:\s*(\d{4})-(\d{2})-(\d{2})\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError("frontmatter has no parseable 'last-verified: YYYY-MM-DD' field")
    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))


# --- Checker unit tests (negative cases prove the checkers detect violations) ---


def test_checker_flags_url_without_verified_marker() -> None:
    bad = "Source: <https://example.com/docs> describes the behaviour."
    assert find_unverified_citations(bad), "URL without (verified ...) must be flagged"


def test_checker_flags_partial_verification_on_multi_url_line() -> None:
    bad = (
        "Sources: <https://a.example> (verified 2026-06-10), "
        "<https://b.example> and nothing else."
    )
    assert find_unverified_citations(bad), "two URLs with one marker must be flagged"


def test_checker_accepts_fully_verified_line() -> None:
    good = (
        "Sources: <https://a.example> (verified 2026-06-10), "
        "<https://b.example> (verified 2026-06-11)."
    )
    assert find_unverified_citations(good) == []


def test_checker_flags_bare_generation_claim() -> None:
    assert find_bare_generation_claims("Typical 4.x models do this.")
    assert find_bare_generation_claims("the 5.X tier") , "case-insensitive"


def test_checker_accepts_concrete_versions() -> None:
    good = "Opus 4.8 keeps the same API surface as Opus 4.7."
    assert find_bare_generation_claims(good) == []


def test_checker_flags_floating_current_models() -> None:
    bad = "Current models handle this well, so no guidance is needed."
    assert find_unanchored_current_tier(bad)


def test_checker_accepts_enumerated_current_models() -> None:
    good = "The current models (Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5) share this."
    also_good = "the current Claude tier: Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5."
    assert find_unanchored_current_tier(good) == []
    assert find_unanchored_current_tier(also_good) == []


def test_parse_last_verified_rejects_missing_field() -> None:
    with pytest.raises(ValueError):
        parse_last_verified("---\nname: x\n---\nbody\n")


# --- File-level invariants (the standing AC2.6.8 enforcement) ---


@pytest.fixture(scope="module")
def notes_text() -> str:
    assert MODEL_TIER_NOTES.is_file(), f"missing file: {MODEL_TIER_NOTES}"
    return MODEL_TIER_NOTES.read_text(encoding="utf-8")


def test_last_verified_header_parses(notes_text: str) -> None:
    parsed = parse_last_verified(notes_text)
    assert parsed <= date.today(), (
        f"last-verified {parsed} is in the future — header is wrong, not fresh."
    )


def test_every_citation_carries_verified_date(notes_text: str) -> None:
    violations = find_unverified_citations(notes_text)
    assert not violations, (
        "AC2.6.8: every external citation must carry a same-line "
        "(verified YYYY-MM-DD) marker:\n" + "\n".join(violations)
    )


def test_no_bare_generation_era_claims(notes_text: str) -> None:
    violations = find_bare_generation_claims(notes_text)
    assert not violations, (
        "AC2.6.8: bare 'N.x' generation claims are banned — name concrete "
        "model versions:\n" + "\n".join(violations)
    )


def test_current_tier_phrases_are_anchored(notes_text: str) -> None:
    violations = find_unanchored_current_tier(notes_text)
    assert not violations, (
        "AC2.6.8: 'current models/tier' must be anchored by a model-name "
        "enumeration within the same sentence:\n" + "\n".join(violations)
    )
