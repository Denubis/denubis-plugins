"""QA enforcement for `description:` frontmatter in denubis-* plugin SKILL.md files.

Rules derive from Claude Code skill spec (https://code.claude.com/docs/en/skills.md,
May 2026) and from chat-history audit showing scholar name-drops are noise.

The tests *are* the tool — pre-commit runs pytest, so any new SKILL.md violation
fails the commit. Run ad hoc with `uv run pytest tests/test_skill_descriptions.py -v`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_GLOB = "plugins/denubis-*/skills/*/SKILL.md"

# Hard limits — exceed these and Claude Code itself will truncate or drop content.
PER_SKILL_LISTING_CAP = 1536  # description + when_to_use combined; official spec
DESCRIPTION_SAFETY_CAP = 500  # well under per-skill cap, leaves truncation headroom

# Soft target — keep aggregate comfortably under 1% of context window.
# Spec: budget = 1% of context (10k chars at 1M context, 2k at 200k). When
# overflowing, least-used skill descriptions are dropped whole. 9,500 leaves
# headroom under the 1M-context budget; small-context sessions will rely on
# the system's graceful least-used-first drop behaviour.
DESCRIPTION_TARGET = 200
AGGREGATE_BUDGET = 9500

# Scholar deny-list — name-dropping in `description:` is noise. Audit evidence:
# user said "popper is complete noise, mate" (2026-04-16); Toulmin/Lakatos/Mantyla
# never appeared as user-side trigger words in chat history. Names belong in the
# skill body, where they document technique without burning skill-listing budget.
SCHOLAR_NAMES: frozenset[str] = frozenset(
    {
        "Toulmin",
        "Popper",
        "Lakatos",
        "Haraway",
        "Mantyla",
        "Fowler",
        "Schön",
        "Schon",
        "Wirth",
        "Kudina",
        "Ballsun",
        "Alfano",
    }
)

TRIGGER_PREFIXES: tuple[str, ...] = (
    "use when",
    "use after",
    "use before",
    "use for",
    "use to",
)


class SkillFile(NamedTuple):
    path: Path
    name: str
    description: str
    when_to_use: str


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []
    for line in match.group(1).splitlines():
        if m := re.match(r"^([a-z][a-z0-9_-]*):\s*(.*)$", line):
            if current_key is not None:
                fields[current_key] = "\n".join(current_value).strip()
            current_key = m.group(1)
            current_value = [m.group(2)]
        elif current_key is not None:
            current_value.append(line)
    if current_key is not None:
        fields[current_key] = "\n".join(current_value).strip()
    return fields


def _load_skill(path: Path) -> SkillFile:
    fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
    plugin = path.parents[2].name
    skill = path.parent.name
    return SkillFile(
        path=path,
        name=f"{plugin}/{skill}",
        description=fm.get("description", ""),
        when_to_use=fm.get("when_to_use", ""),
    )


def _collect_skills() -> list[SkillFile]:
    return [_load_skill(p) for p in sorted(REPO_ROOT.glob(PLUGIN_GLOB))]


SKILLS: list[SkillFile] = _collect_skills()


@pytest.fixture(params=SKILLS, ids=lambda s: s.name)
def skill(request: pytest.FixtureRequest) -> SkillFile:
    return request.param


# --- Hard rules: violate Claude Code spec or risk truncation ---


def test_description_present(skill: SkillFile) -> None:
    assert skill.description, (
        f"{skill.name}: missing or empty `description:` frontmatter. "
        f"Without a description, Claude cannot auto-invoke the skill."
    )


def test_combined_under_listing_cap(skill: SkillFile) -> None:
    combined = len(skill.description) + len(skill.when_to_use)
    assert combined <= PER_SKILL_LISTING_CAP, (
        f"{skill.name}: description+when_to_use is {combined} chars, "
        f"exceeds Claude Code listing cap of {PER_SKILL_LISTING_CAP}. "
        f"Tail content will be silently truncated."
    )


def test_description_under_safety_cap(skill: SkillFile) -> None:
    n = len(skill.description)
    assert n <= DESCRIPTION_SAFETY_CAP, (
        f"{skill.name}: description is {n} chars, exceeds safety cap "
        f"({DESCRIPTION_SAFETY_CAP}). Risk of truncation in low-budget contexts."
    )


# --- Soft rules: bloat patterns from audit ---


def test_description_under_target_length(skill: SkillFile) -> None:
    n = len(skill.description)
    assert n <= DESCRIPTION_TARGET, (
        f"{skill.name}: description is {n} chars, target is <={DESCRIPTION_TARGET}. "
        f"Strip implementation enumerations, scholar surnames, and trailing "
        f"'... that ensures X' clauses. Triggers and verbs only."
    )


def test_no_scholar_namedrops(skill: SkillFile) -> None:
    found = sorted({n for n in SCHOLAR_NAMES if n in skill.description})
    assert not found, (
        f"{skill.name}: description name-drops {found}. Users do not search "
        f"by surname; scholar names belong in the skill body."
    )


def test_no_parenthetical_enumeration(skill: SkillFile) -> None:
    if re.search(r"\([^)]*?,[^)]*?,[^)]*?\)", skill.description):
        pytest.fail(
            f"{skill.name}: description contains parenthetical enumeration "
            f"`(a, b, c)`. Implementation lists belong in the skill body. "
            f"Description: {skill.description!r}"
        )


def test_description_leads_with_trigger(skill: SkillFile) -> None:
    head = skill.description[:100].lower()
    has_trigger = any(head.startswith(p) or f" {p}" in head for p in TRIGGER_PREFIXES)
    assert has_trigger, (
        f"{skill.name}: description does not lead with a trigger phrase "
        f"({TRIGGER_PREFIXES}). Per official spec, descriptions are truncated "
        f"tail-first; triggers must come first. "
        f"First 100 chars: {skill.description[:100]!r}"
    )


# --- Aggregate rule: total budget across all denubis skills ---


def test_aggregate_description_budget() -> None:
    total = sum(len(s.description) for s in SKILLS)
    assert total <= AGGREGATE_BUDGET, (
        f"All denubis skill descriptions total {total} chars "
        f"(~{total // 4} tokens), exceeds aggregate budget {AGGREGATE_BUDGET}. "
        f"Top 5 offenders: "
        + ", ".join(
            f"{s.name}={len(s.description)}"
            for s in sorted(SKILLS, key=lambda x: -len(x.description))[:5]
        )
    )
