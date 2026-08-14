"""Every skill frontmatter block must be valid YAML, not just line-parseable text."""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_FILES = tuple(sorted(REPO_ROOT.glob("plugins/denubis-*/skills/*/SKILL.md")))


@pytest.mark.parametrize("skill_path", SKILL_FILES, ids=lambda path: path.parent.name)
def test_skill_frontmatter_is_valid_yaml(skill_path: Path) -> None:
    text = skill_path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{skill_path}: missing opening YAML fence"

    try:
        frontmatter_text, _body = text.removeprefix("---\n").split("\n---\n", 1)
    except ValueError as exc:
        raise AssertionError(f"{skill_path}: missing closing YAML fence") from exc

    parsed = yaml.safe_load(frontmatter_text)
    assert isinstance(parsed, dict), f"{skill_path}: frontmatter is not a mapping"
    assert parsed.get("name"), f"{skill_path}: frontmatter has no name"
    assert parsed["name"] == skill_path.parent.name, (
        f"{skill_path}: frontmatter name {parsed['name']!r} does not match "
        f"skill directory {skill_path.parent.name!r}"
    )
