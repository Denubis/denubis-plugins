"""Mechanical enforcement of the Fable-tier cost gate.

The gate (``plugins/denubis-extending-claude/skills/writing-claude-directives/
model-tier-notes.md``, "Cost gate", operator-empirical 2026-06-10) says
Fable-tier invocations are human-triggered only: no directive, skill, plan, or
agent prompt may auto-dispatch Fable-tier work.

Prose cannot enforce that. A skill added months from now saying "then consult
the Fable advisor" is auto-dispatch, and the breach surfaces on the operator's
bill rather than in review — a silent failure, which fails Jones's third
condition (every miss surfaces fast enough for a human to decide). These tests
turn the silent breach into a red run.

They are structural tripwires, in the same spirit as
``test_model_tier_freshness.py``: they check how the gate is respected, not
whether Fable is any good. The gate's own falsifier is operator-owned — only a
dated note from the operator revokes it — so if these tests ever need to change,
that note must exist first.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS = REPO_ROOT / "plugins"

ADVISOR_SKILL = "consulting-a-fable-advisor"
ADVISOR_DIR = PLUGINS / "denubis-external-agents" / "skills" / ADVISOR_SKILL

# Fable-tier model identifiers and the skill that dispatches them.
FABLE_TOKENS = re.compile(r"claude-fable-\d|fable-advisor-spawn|consulting-a-fable-advisor")


def _skill_files() -> list[Path]:
    return sorted(PLUGINS.glob("*/skills/*/SKILL.md"))


def _agent_files() -> list[Path]:
    return sorted(PLUGINS.glob("*/agents/*.md"))


def _hook_and_command_files() -> list[Path]:
    return sorted(
        [*PLUGINS.glob("*/hooks/*"), *PLUGINS.glob("*/commands/*.md")],
    )


def test_advisor_skill_is_user_invocable() -> None:
    """The dispatching skill must declare itself human-invocable.

    A skill without ``user-invocable: true`` is one the model reaches for on its
    own, which is the auto-dispatch the gate forbids.
    """
    text = (ADVISOR_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "user-invocable: true" in text, (
        f"{ADVISOR_SKILL} must declare 'user-invocable: true'; without it the "
        "model may reach for it unprompted, which breaches the Fable cost gate."
    )


def test_no_other_skill_references_the_fable_advisor() -> None:
    """No other skill may name the advisor skill or its spawn script.

    A reference from another skill turns a human-triggered consultation into a
    step in an automated flow. That is the breach the gate exists to prevent.
    """
    offenders = []
    for path in _skill_files():
        if path.parent.name == ADVISOR_SKILL:
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if FABLE_TOKENS.search(line):
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "These skills reference the Fable advisor, making it an automatic step "
        "and breaching the cost gate (model-tier-notes.md, 'Cost gate'). Only a "
        "human may trigger a Fable-tier dispatch:\n  " + "\n  ".join(offenders)
    )


def test_no_agent_hook_or_command_dispatches_fable() -> None:
    """Agents, hooks, and commands must not dispatch Fable-tier work.

    Agent prompts are named in the gate explicitly. Hooks and commands fire
    without a human in the loop by construction, so a Fable reference in either
    is auto-dispatch regardless of intent.
    """
    offenders = []
    for path in [*_agent_files(), *_hook_and_command_files()]:
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            if FABLE_TOKENS.search(line):
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Agents, hooks, and commands may not dispatch Fable-tier work "
        "(model-tier-notes.md, 'Cost gate'):\n  " + "\n  ".join(offenders)
    )


def test_no_agent_definition_declares_a_fable_model() -> None:
    """No agent may declare a Fable-tier model in its frontmatter.

    An agent with ``model: fable`` is dispatchable by any skill that names it,
    which routes around every other check here.
    """
    offenders = []
    for path in _agent_files():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if re.match(r"^model:\s*(claude-)?fable", line.strip(), re.IGNORECASE):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Agent definitions may not declare a Fable-tier model:\n  "
        + "\n  ".join(offenders)
    )


def test_spawn_script_records_the_gate() -> None:
    """The spawn script must carry the gate in-file.

    The script is runnable directly, without its skill. Someone reading only the
    script must still learn that nothing may call it automatically.
    """
    text = (ADVISOR_DIR / "fable-advisor-spawn.sh").read_text(encoding="utf-8")
    assert "human-triggered only" in text, (
        "fable-advisor-spawn.sh must state that Fable invocations are "
        "human-triggered only; the script is runnable without its SKILL.md."
    )
