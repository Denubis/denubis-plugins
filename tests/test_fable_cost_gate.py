"""Mechanical enforcement of the Fable-tier cost gate.

The gate (``plugins/denubis-extending-claude/skills/writing-claude-directives/
model-tier-notes.md``, "Cost gate", operator-empirical 2026-06-10) says
Fable-tier invocations are human-triggered only: no directive, skill, plan, or
agent prompt may auto-dispatch Fable-tier work.

Prose cannot enforce that. A skill added months from now saying "then consult
the Fable advisor" is auto-dispatch, and the breach surfaces on the operator's
bill rather than in review — a silent failure, which fails Jones's third
condition (every miss surfaces fast enough for a human to decide). These tests
turn a lexical breach into a red run.

WHAT THIS DOES NOT CATCH. The detector is lexical, so it enforces "no Fable
reference in text under plugins/" and not the policy itself. Two shapes evade it
by construction, and naming them here is the point: a test that implies more
than it checks is the failure mode it was written against.

- Semantic dispatch. "Then spawn the different-model advisor pane from the
  external-agents plugin" names nothing this matches, yet the consumer of that
  sentence is a model that resolves descriptions rather than names. An innocent
  paraphrase during a doc edit defeats the tripwire.
- Ambient model inheritance. ``Workflow`` and agent fan-out inherit the session
  model, so when the human is already running on Fable, any skill that fans out
  dispatches Fable-tier work with no Fable token anywhere in the repository.

The first was found by a Fable advisor reading this module (2026-07-21); the
second is recorded in fable-advisor-spawn.sh's own header. Neither is greppable,
and no amount of widening the globs reaches them.

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

# Fable-tier model identifiers, the skill that dispatches them, and the phrase a
# dispatching instruction actually uses. The first three are exact names; the
# fourth exists because this module's own docstring names "then consult the
# Fable advisor" as the canonical breach, and a detector blind to its own worked
# example enforces nothing it claims to.
FABLE_TOKENS = re.compile(
    r"claude-fable-\d|fable-advisor-spawn|consulting-a-fable-advisor|fable[ -]advisor",
    re.IGNORECASE,
)

# Files that must discuss the gate to define or implement it. Everything else
# under plugins/ is scanned, because dispatch is not confined to SKILL.md.
ADVISOR_AGENT = PLUGINS / "denubis-external-agents" / "agents" / "fable-advisor.md"

EXEMPT_DIRS = (ADVISOR_DIR,)
EXEMPT_FILES = (
    PLUGINS
    / "denubis-extending-claude"
    / "skills"
    / "writing-claude-directives"
    / "model-tier-notes.md",
    # The advisor agent names itself, exactly as the advisor skill does. It is
    # exempt from the lexical scan and covered instead by the stricter
    # test_fable_agent_definitions_carry_the_human_trigger_constraint, which
    # asserts what it must contain rather than what it must not.
    ADVISOR_AGENT,
)


def _is_exempt(path: Path) -> bool:
    return any(path.is_relative_to(d) for d in EXEMPT_DIRS) or path in EXEMPT_FILES


def _scanned_files() -> list[Path]:
    """Every readable text file under plugins/, minus the gate's own documents.

    Deliberately broader than the four categories this module first checked. A
    skill's auxiliary payload files and a plugin's scripts both dispatch, and
    both were unwatched: `_skill_files()` globbed only ``*/skills/*/SKILL.md``,
    and nothing globbed ``plugins/*/scripts/**`` at all.
    """
    found = []
    for path in sorted(PLUGINS.rglob("*")):
        if not path.is_file() or _is_exempt(path):
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        found.append(path)
    return found


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

    The advisor agent is excluded because it names itself, exactly as the
    advisor skill does in ``test_no_other_skill_references_the_fable_advisor``.
    A definition cannot be forbidden from stating its own identity. It is
    covered instead by
    ``test_fable_agent_definitions_carry_the_human_trigger_constraint``, which
    is stricter: it asserts what the file must contain rather than what it
    must not.
    """
    offenders = []
    for path in [*_agent_files(), *_hook_and_command_files()]:
        if not path.is_file() or path == ADVISOR_AGENT:
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


def test_fable_agent_definitions_carry_the_human_trigger_constraint() -> None:
    """A Fable-tier agent is allowed, but only with its constraints in-file.

    This was an outright prohibition until the operator ruling of 2026-07-25
    (recorded in model-tier-notes.md's Cost gate section, which is the dated
    note this gate's falsifier requires). The original reasoning still holds
    and is why the prohibition became a conditional rather than disappearing:
    an agent with ``model: fable`` is dispatchable by any skill that names it.

    What replaced the prohibition is two checks, because the ruling moved the
    restriction from "no such agent exists" to "the agent exists and is
    constrained". A reader of the definition alone must learn both constraints,
    for the same reason ``test_spawn_script_records_the_gate`` exists: the file
    is consumed without its documentation.

    The reference-level rule is unchanged and lives in
    ``test_no_other_skill_references_the_fable_advisor``: nothing may name the
    advisor as a step. That check is the mechanical half. The human-trigger
    sentence asserted here is prose the dispatching model is asked to honour,
    so it is the weaker half, and this test verifies only that it is present,
    never that it is obeyed.
    """
    missing_trigger = []
    unrestricted_tools = []

    for path in _agent_files():
        text = path.read_text(encoding="utf-8")
        declares_fable = any(
            re.match(r"^model:\s*(claude-)?fable", line.strip(), re.IGNORECASE)
            for line in text.splitlines()
        )
        if not declares_fable:
            continue

        rel = path.relative_to(REPO_ROOT)
        if "human has asked" not in text:
            missing_trigger.append(str(rel))

        # A `tools:` allowlist denies what it omits, MCP tools included, so the
        # absence of the field means the agent inherits a surface it was never
        # scoped for. Bash is called out because it reaches the filesystem
        # regardless of what Write/Edit are doing.
        tools_line = next(
            (l for l in text.splitlines() if l.strip().lower().startswith("tools:")),
            None,
        )
        if tools_line is None or re.search(r"\b(Bash|Write|Edit)\b", tools_line):
            unrestricted_tools.append(f"{rel}: {tools_line or '(no tools: field)'}")

    assert not missing_trigger, (
        "A Fable-tier agent must state in-file that it is dispatched only when "
        "the human has asked for it (the literal phrase 'human has asked'); "
        "the definition is read without its documentation:\n  "
        + "\n  ".join(missing_trigger)
    )
    assert not unrestricted_tools, (
        "A Fable-tier agent must carry a read-only 'tools:' allowlist, without "
        "Bash, Write or Edit:\n  " + "\n  ".join(unrestricted_tools)
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


def test_detector_matches_the_canonical_breach_named_in_this_docstring() -> None:
    """The example breach this module names must be one it can catch.

    The module docstring justifies these tests with a skill saying "then consult
    the Fable advisor". Until the phrase token was added, that sentence passed
    the detector untouched, so the worked example that motivated the tests was
    itself undetectable by them.
    """
    assert FABLE_TOKENS.search("then consult the Fable advisor"), (
        "The detector does not match the breach this module's own docstring "
        "uses to justify its existence."
    )


def test_scan_reaches_auxiliary_skill_files_and_plugin_scripts() -> None:
    """Dispatch lives in more than SKILL.md.

    Skills carry payload files the model is told to read and run, and plugins
    carry scripts that run unattended on a session hook. A scan restricted to
    SKILL.md, agents, hooks, and commands leaves both classes unwatched.
    """
    scanned = {p.relative_to(REPO_ROOT).as_posix() for p in _scanned_files()}
    auxiliary = [p for p in scanned if "/skills/" in p and not p.endswith("SKILL.md")]
    scripts = [p for p in scanned if "/scripts/" in p]
    assert auxiliary, "no auxiliary (non-SKILL.md) skill files are scanned"
    assert scripts, "no plugin scripts are scanned"


def test_nothing_under_plugins_dispatches_fable() -> None:
    """The widened scan: no Fable reference anywhere under plugins/.

    Supersedes the per-category checks above in breadth. They are kept because a
    failure in one of them names the category, which is a faster read than a
    path in a list.
    """
    offenders = []
    for path in _scanned_files():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if FABLE_TOKENS.search(line):
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Fable-tier dispatch may not be referenced anywhere under plugins/ "
        "outside the advisor's own skill (model-tier-notes.md, 'Cost gate'). "
        "Only a human may trigger a Fable-tier dispatch:\n  " + "\n  ".join(offenders)
    )
