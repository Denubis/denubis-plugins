"""Structural integrity of denubis-* SKILL.md files.

Expectations come from the filesystem, never from the skill text under test. A skill
cannot make these pass by asserting something about itself, which is what keeps them
gates rather than tautologies.

Scope is deliberately narrow. Two checks over an unambiguous token, `plugin:name`.
Two other checks were attempted and dropped, and the reasons are worth keeping:

- **Paths mentioned in prose.** Asserting that every backticked repo-ish path resolves
  fired on eight skills, almost all of them worked examples describing the *reader's*
  project (`docs/design-plans/2025-01-18-oauth2-svc-authn.md`) rather than pointers into
  this repo. Nothing separates the two mechanically, so it reported change rather than
  defect.

- **Undefined shell variables in snippets.** A real defect class: `impl-plan-write`
  expands `$PLAN_DIR`, which the skill only ever introduces as a value the planner
  "notes". But detecting it by regex means parsing shell, and the attempt produced more
  bugs in the checker than it found in the corpus, mis-binding a variable named
  `local_main` and discarding assignments from any block containing `awk`. The right
  tool is `shellcheck` (SC2154 is exactly this), run over extracted fenced blocks. Until
  that is wired up, the defect is tracked as ordinary work rather than approximated here.

Also not tested: whether the instructions are any good. No structural assertion catches
a workflow that reads coherently and cannot be used. That is a field test.

Run ad hoc with `uv run pytest tests/test_skill_reference_integrity.py -v`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_GLOB = "plugins/denubis-*/skills/*/SKILL.md"
AGENT_GLOB = "plugins/denubis-*/agents/*.md"

PLACEHOLDER_MARKERS = ("[", "<", "{")

SKILL_REFERENCE = re.compile(r"\b(denubis-[a-z0-9-]+):([a-z0-9-]+)\b")
SUBAGENT_TYPE = re.compile(r'<parameter name="subagent_type">([^<]+)</parameter>')


class Skill(NamedTuple):
    path: Path
    plugin: str
    name: str
    text: str

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(REPO_ROOT))


def _load_skills() -> list[Skill]:
    return [
        Skill(
            path=p,
            plugin=p.parent.parent.parent.name,
            name=p.parent.name,
            text=p.read_text(encoding="utf-8"),
        )
        for p in sorted(REPO_ROOT.glob(SKILL_GLOB))
    ]


def _referenceable() -> set[tuple[str, str]]:
    """Skills and agents share the `plugin:name` namespace at the call site."""
    names = {(s.plugin, s.name) for s in _load_skills()}
    for p in REPO_ROOT.glob(AGENT_GLOB):
        names.add((p.parent.parent.name, p.stem))
    return names


SKILLS = _load_skills()
SKILL_IDS = [f"{s.plugin}:{s.name}" for s in SKILLS]
REFERENCEABLE = _referenceable()


def test_corpus_was_discovered() -> None:
    """Guard the globs. A silently-empty corpus makes every test below vacuous."""
    assert len(SKILLS) > 20, f"expected the full skill corpus, found {len(SKILLS)}"
    assert len(REFERENCEABLE) > len(SKILLS), "no agents discovered alongside the skills"


@pytest.mark.parametrize("skill", SKILLS, ids=SKILL_IDS)
def test_plugin_qualified_references_resolve(skill: Skill) -> None:
    """`denubis-plugin:name` must name a skill or agent that ships in this repo.

    Catches a rename that updates the definition and leaves callers pointing at the old
    name, which proof-reading does not reliably catch across fifty-odd skills.
    """
    broken = [
        f"{plugin}:{name}"
        for plugin, name in SKILL_REFERENCE.findall(skill.text)
        if (plugin, name) not in REFERENCEABLE
    ]
    assert not broken, f"{skill.rel} references unknown skills/agents: {sorted(set(broken))}"


@pytest.mark.parametrize("skill", SKILLS, ids=SKILL_IDS)
def test_dispatched_agents_exist(skill: Skill) -> None:
    """Every subagent_type in a dispatch block must name an agent definition on disk."""
    broken = []
    for raw in SUBAGENT_TYPE.findall(skill.text):
        agent = raw.strip()
        if not agent or any(marker in agent for marker in PLACEHOLDER_MARKERS):
            continue
        plugin, _, bare = agent.rpartition(":")
        candidates = (
            [REPO_ROOT / "plugins" / plugin / "agents" / f"{bare}.md"]
            if plugin
            else list(REPO_ROOT.glob(f"plugins/denubis-*/agents/{bare}.md"))
        )
        if not any(c.exists() for c in candidates):
            broken.append(agent)
    assert not broken, f"{skill.rel} dispatches agents that do not exist: {sorted(set(broken))}"
