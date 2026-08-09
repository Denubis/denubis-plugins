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
import yaml

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
    error: str | None = None


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Return the frontmatter mapping, raising ValueError when it is malformed.

    Raises rather than asserts because the caller turns the failure into data.
    An assertion here reads as a test verdict, and this runs at import.
    """
    if not text.startswith("---\n"):
        raise ValueError("missing opening YAML fence")

    try:
        frontmatter_text, _body = text.removeprefix("---\n").split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("missing closing YAML fence") from exc

    try:
        parsed = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("frontmatter is not a mapping")
    return parsed


def _load_skill(path: Path) -> SkillFile:
    """Load one SKILL.md, recording a parse failure instead of raising it.

    `_collect_skills` runs at module import, so an exception escaping here
    fails collection for every test in this file and names no path.
    """
    name = f"{path.parents[2].name}/{path.parent.name}"
    try:
        fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return SkillFile(
            path=path, name=name, description="", when_to_use="", error=str(exc)
        )

    return SkillFile(
        path=path,
        name=name,
        description=fm.get("description", ""),
        when_to_use=fm.get("when_to_use", ""),
    )


def _collect_skills() -> list[SkillFile]:
    return [_load_skill(p) for p in sorted(REPO_ROOT.glob(PLUGIN_GLOB))]


SKILLS: list[SkillFile] = _collect_skills()


def _assert_all_parsed(skills: list[SkillFile]) -> None:
    broken = [s for s in skills if s.error is not None]
    assert not broken, "SKILL.md frontmatter did not parse:\n" + "\n".join(
        f"  {s.path}: {s.error}" for s in broken
    )


def _skill_or_skip(candidate: SkillFile) -> SkillFile:
    """Hand a parsed skill to a quality test, or skip if it never parsed.

    Skipping keeps a fence error from surfacing as "missing description" on
    every rule below. It hides nothing: `test_every_skill_frontmatter_parsed`
    fails on the same file, and pytest counts a skip apart from a pass.
    """
    if candidate.error is not None:
        pytest.skip(f"{candidate.path}: frontmatter did not parse — {candidate.error}")
    return candidate


@pytest.fixture(params=SKILLS, ids=lambda s: s.name)
def skill(request: pytest.FixtureRequest) -> SkillFile:
    return _skill_or_skip(request.param)


# --- Collection gate: a malformed file fails here, once, by name ---


def test_every_skill_frontmatter_parsed() -> None:
    _assert_all_parsed(SKILLS)


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


def test_malformed_frontmatter_is_reported_rather_than_raised(tmp_path: Path) -> None:
    """A broken SKILL.md must not take the whole module down at import.

    `SKILLS` is built at collection time, so an exception escaping `_load_skill`
    errors every test in this file and the traceback names no path. The failure
    has to survive as data on the `SkillFile` instead.
    """
    skill_path = tmp_path / "denubis-example" / "skills" / "no-fence" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("name: no-fence\ndescription: Use when\n", encoding="utf-8")

    loaded = _load_skill(skill_path)

    assert loaded.error is not None
    assert "opening YAML fence" in loaded.error


def test_unparseable_skill_fails_the_gate_naming_its_path(tmp_path: Path) -> None:
    skill_path = tmp_path / "denubis-example" / "skills" / "bad-yaml" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("---\nname: [unclosed\n---\nbody\n", encoding="utf-8")

    broken = _load_skill(skill_path)
    assert broken.error is not None

    with pytest.raises(AssertionError, match="bad-yaml"):
        _assert_all_parsed([broken])


def test_quality_tests_skip_rather_than_misreport_an_unparseable_skill() -> None:
    """The skip keeps `test_description_present` from blaming a fence error.

    Nothing passes silently: `_assert_all_parsed` still fails, and pytest counts
    a skip separately from a pass.
    """
    broken = SkillFile(
        path=Path("plugins/denubis-example/skills/broken/SKILL.md"),
        name="denubis-example/broken",
        description="",
        when_to_use="",
        error="missing closing YAML fence",
    )

    with pytest.raises(pytest.skip.Exception):
        _skill_or_skip(broken)


def test_quoted_description_with_colon_leads_with_trigger(tmp_path: Path) -> None:
    skill_path = tmp_path / "denubis-example" / "skills" / "quoted-colon" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "---\n"
        "name: quoted-colon\n"
        'description: "Use when parsing frontmatter: preserve YAML scalar semantics"\n'
        "---\n",
        encoding="utf-8",
    )

    test_description_leads_with_trigger(_load_skill(skill_path))


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
