"""Repository contracts for always-on instruction delivery.

The inventory comes from the marketplace and each listed plugin's ``hooks.json``.
The PreToolUse assertion is a positive control: a clean result is meaningful only if
the same traversal finds a known active hook boundary.

A ``hooks.json`` may instead name hooks modules (mods) under ``modules``. Their
counterparts of these boundaries are a ``prompt.submit`` hook that attaches
``context`` (per-prompt delivery) and a ``prompt.compose`` hook that adds a
system-prompt section (always-on delivery). ``_module_hooks`` reads them from the
TypeScript source; its docstring states the parse and its coverage boundary. The
mod inventory has its own positive and non-match controls.

Mods keep the settings rule's default: a mod delivery fails. A delivery the human
has permitted is listed in ``PERMITTED_MOD_DELIVERIES``, keyed by plugin and door
(``prompt.submit`` for context, ``prompt.compose`` for a section) and valued by
the authority: the decision record and the original message's raw record. An
allowance covers every text that door of that plugin delivers. An allowance whose
delivery is gone fails too, so no exemption outlives its subject.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PROJECT_NOTES_ROOT = REPO_ROOT / "plugins" / "denubis-project-notes"
PLAN_HOOKS = (
    REPO_ROOT
    / "plugins"
    / "denubis-plan-and-execute"
    / "hooks"
    / "claude-hooks.json"
)


def _claude_hooks_path(plugin_root: Path) -> Path:
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return plugin_root / manifest.get("hooks", "hooks/hooks.json")


def _marketplace_hook_events() -> set[tuple[str, str]]:
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    events: set[tuple[str, str]] = set()

    for plugin in marketplace["plugins"]:
        source = plugin["source"]
        plugin_root = REPO_ROOT / source.removeprefix("./")
        hooks_path = _claude_hooks_path(plugin_root)
        if not hooks_path.is_file():
            continue
        # A hooks file that names only a hooks module (`modules`) registers no
        # settings-hook events; its function hooks are outside this inventory.
        hooks = json.loads(hooks_path.read_text(encoding="utf-8")).get("hooks", {})
        events.update((plugin["name"], event) for event in hooks)

    return events


@dataclass(frozen=True)
class ModuleHook:
    """One function hook a hooks module registers.

    ``delivers`` is True for a ``prompt.submit`` hook that attaches ``context``
    (per-prompt delivery, the counterpart of a settings ``UserPromptSubmit``
    hook) and for a ``prompt.compose`` hook that adds a system-prompt section
    (always-on delivery); False for every other hook.
    """

    plugin: str
    event: str
    delivers: bool


_REGEX_PRECEDERS = frozenset("(,=:[!&|?{};+-*%<>~^")
_REGEX_KEYWORDS = frozenset(
    {"return", "typeof", "case", "do", "else", "in", "of", "void", "yield", "await"}
)


def _mask_non_code(source: str) -> str:
    """Blank string, template-text, comment and regex bodies to spaces.

    Lengths, newlines, quotes and ``${...}`` substitutions are kept, so an index
    into the result is an index into ``source`` and brackets and keys found in
    the result are code. A ``/`` starts a regular expression after an operator,
    an opening bracket, a keyword such as ``return``, or nothing; elsewhere it
    divides. JSX text is outside this scanner: a quote or ``/`` in it fails the
    scan with ``ValueError`` rather than passing silently.
    """
    masked = list(source)
    end_of_source = len(source)

    def blank(start: int, end: int) -> None:
        for index in range(start, end):
            if masked[index] != "\n":
                masked[index] = " "

    def regex_allowed(index: int) -> bool:
        before = source[:index].rstrip()
        if not before:
            return True
        last = before[-1]
        if last in _REGEX_PRECEDERS:
            return not before.endswith("<")  # `</` closes a JSX tag
        word = before[len(before.rstrip("abcdefghijklmnopqrstuvwxyz")) :]
        return word in _REGEX_KEYWORDS

    def quoted(index: int, quote: str) -> int:
        cursor = index + 1
        while cursor < end_of_source:
            char = source[cursor]
            if char == "\\":
                cursor += 2
            elif char == quote:
                blank(index + 1, cursor)
                return cursor + 1
            elif char == "\n":
                break
            else:
                cursor += 1
        raise ValueError(f"unterminated {quote} literal at offset {index}")

    def regex(index: int) -> int:
        cursor = index + 1
        in_class = False
        while cursor < end_of_source and source[cursor] != "\n":
            char = source[cursor]
            if char == "\\":
                cursor += 2
                continue
            if char == "[":
                in_class = True
            elif char == "]":
                in_class = False
            elif char == "/" and not in_class:
                blank(index + 1, cursor)
                return cursor + 1
            cursor += 1
        raise ValueError(f"unterminated regular expression at offset {index}")

    def template(index: int) -> int:
        cursor = index + 1
        text_start = cursor
        while cursor < end_of_source:
            if source[cursor] == "\\":
                cursor += 2
            elif source[cursor] == "`":
                blank(text_start, cursor)
                return cursor + 1
            elif source.startswith("${", cursor):
                blank(text_start, cursor)
                cursor = code(cursor + 2, closes_substitution=True)
                text_start = cursor
            else:
                cursor += 1
        raise ValueError(f"unterminated template literal at offset {index}")

    def code(index: int, *, closes_substitution: bool) -> int:
        braces = 0
        cursor = index
        while cursor < end_of_source:
            char = source[cursor]
            if char in "'\"":
                cursor = quoted(cursor, char)
            elif char == "`":
                cursor = template(cursor)
            elif source.startswith("//", cursor):
                line_end = source.find("\n", cursor)
                line_end = end_of_source if line_end == -1 else line_end
                blank(cursor, line_end)
                cursor = line_end
            elif source.startswith("/*", cursor):
                comment_end = source.find("*/", cursor + 2)
                if comment_end == -1:
                    raise ValueError(f"unterminated comment at offset {cursor}")
                blank(cursor, comment_end + 2)
                cursor = comment_end + 2
            elif char == "/" and regex_allowed(cursor):
                cursor = regex(cursor)
            elif char == "}" and braces == 0 and closes_substitution:
                return cursor + 1
            else:
                braces += {"{": 1, "}": -1}.get(char, 0)
                cursor += 1
        if closes_substitution:
            raise ValueError(f"unterminated template substitution at offset {index}")
        return cursor

    code(0, closes_substitution=False)
    return "".join(masked)


_OPENERS = {"(": ")", "[": "]", "{": "}"}


def _closing(masked: str, opening: int) -> int:
    """Index of the bracket that closes ``masked[opening]``."""
    expected: list[str] = []
    for index in range(opening, len(masked)):
        char = masked[index]
        if char in _OPENERS:
            expected.append(_OPENERS[char])
        elif char in ")]}":
            if not expected or char != expected.pop():
                raise ValueError(f"unbalanced {char!r} at offset {index}")
            if not expected:
                return index
    raise ValueError(f"unclosed {masked[opening]!r} at offset {opening}")


def _top_level_elements(masked: str, opening: int) -> list[str]:
    """The comma-separated elements of the array literal opening at ``opening``."""
    closing = _closing(masked, opening)
    elements: list[str] = []
    depth = 0
    start = opening + 1
    for index in range(opening + 1, closing):
        char = masked[index]
        if char in _OPENERS:
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            elements.append(masked[start:index].strip())
            start = index + 1
    elements.append(masked[start:closing].strip())
    return [element for element in elements if element]


_REGISTER = re.compile(
    r"export\s+const\s+register\b[^=]*=\s*(?:async\s+)?\(?\s*(?P<on>[A-Za-z_$][\w$]*)"
    r"|export\s+(?:async\s+)?function\s+register\s*\(\s*(?P<on_fn>[A-Za-z_$][\w$]*)"
)
_CONTEXT_KEY = re.compile(r"(?<![\w$.])context\s*:|[{,]\s*context\s*[,}]")
_SECTIONS_KEY = re.compile(r"(?<![\w$.])sections\s*:\s*")


def _adds_section(arguments: str) -> bool:
    for key in _SECTIONS_KEY.finditer(arguments):
        if not arguments.startswith("[", key.end()):
            return True  # a list built elsewhere: counted rather than hidden
        if any(
            not element.startswith("...")
            for element in _top_level_elements(arguments, key.end())
        ):
            return True
    return False


def _module_hooks(plugin: str, source: str) -> list[ModuleHook]:
    """The hooks a hooks module's ``register`` adds, read from its source.

    A light, deterministic parse, not an evaluation:

    1. ``_mask_non_code`` blanks everything that is not code.
    2. ``register``'s first parameter is the registrar. Each call of it is one
       hook: its first argument names the event, and its arguments run to the
       matching parenthesis. Any other use of the registrar (passing it to a
       helper) raises ``ValueError``, as the hooks it adds would go unseen.
    3. A ``prompt.submit`` hook delivers when its arguments write a ``context``
       key (``context:`` or the ``{ ...e, context }`` shorthand). A
       ``prompt.compose`` hook delivers when it writes ``sections:`` with a
       non-spread element, or with a value that is not an array literal.

    Coverage boundary: an input or answer a helper outside the hook's own call
    builds is not followed. Step 3 errs towards delivery: a ``context:`` type
    annotation or a list of sections built elsewhere counts.
    """
    masked = _mask_non_code(source)
    declaration = _REGISTER.search(masked)
    if declaration is None:
        raise ValueError(f"{plugin}: no exported register function")
    group = "on" if declaration.group("on") is not None else "on_fn"
    registrar = declaration.group(group)

    hooks: list[ModuleHook] = []
    for use in re.finditer(rf"(?<![\w$.]){re.escape(registrar)}(?![\w$])", masked):
        if use.start() == declaration.start(group):
            continue
        call = re.compile(r"\s*\(\s*(['\"])").match(masked, use.end())
        if call is None:
            raise ValueError(
                f"{plugin}: the registrar {registrar!r} is used other than as a "
                f"call at offset {use.start()}, so its hooks cannot be followed"
            )
        quote_at = call.start(1)
        event_end = masked.index(call.group(1), quote_at + 1)
        event = source[quote_at + 1 : event_end]
        opening = masked.index("(", use.end())
        arguments = masked[opening + 1 : _closing(masked, opening)]
        if event == "prompt.submit":
            delivers = _CONTEXT_KEY.search(arguments) is not None
        elif event == "prompt.compose":
            delivers = _adds_section(arguments)
        else:
            delivers = False
        hooks.append(ModuleHook(plugin, event, delivers))
    return hooks


def _marketplace_module_hooks() -> list[ModuleHook]:
    """Every hook of every hooks module a marketplace plugin's hooks.json names."""
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    hooks: list[ModuleHook] = []

    for plugin in marketplace["plugins"]:
        plugin_root = REPO_ROOT / plugin["source"].removeprefix("./")
        hooks_path = _claude_hooks_path(plugin_root)
        if not hooks_path.is_file():
            continue
        modules = json.loads(hooks_path.read_text(encoding="utf-8")).get("modules", [])
        for module in modules:
            source = (hooks_path.parent / module).read_text(encoding="utf-8")
            hooks.extend(_module_hooks(plugin["name"], source))

    return hooks


QUIET_AGENTS = "denubis-hook-quiet-agents"
NOTICE_LOG = "denubis-hook-agent-notice-log"

# The human's ruling of 2026-10-25, "I... system prompt adjusting in the plugin is
# fine. And context line is fine.", answering whether quiet-agents' two
# deliveries may stand under the extended contract.
_QUIET_AGENTS_RULING = (
    ".notes/decisions/0005-instruction-delivery-contract-reads-mods.md; raw record "
    "/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/"
    "e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl:1237 "
    "(message 2e705937-f326-469e-b25c-9e95e1441cea)"
)

# (plugin, door) -> the authority that permits that mod delivery. An entry needs a
# human ruling; the door is the event `ModuleHook` reports.
PERMITTED_MOD_DELIVERIES: dict[tuple[str, str], str] = {
    (QUIET_AGENTS, "prompt.compose"): _QUIET_AGENTS_RULING,
    (QUIET_AGENTS, "prompt.submit"): _QUIET_AGENTS_RULING,
}


def test_module_inventory_reaches_known_mod_deliveries() -> None:
    """Positive control: marketplace traversal reads hooks modules.

    quiet-agents attaches context at ``prompt.submit`` and adds a system-prompt
    section at ``prompt.compose``. A clean result over mods means something only
    if the same traversal finds these.
    """
    delivering = {
        (hook.plugin, hook.event)
        for hook in _marketplace_module_hooks()
        if hook.delivers
    }

    assert {
        (QUIET_AGENTS, "prompt.submit"),
        (QUIET_AGENTS, "prompt.compose"),
    } <= delivering


def test_no_marketplace_mod_delivers_without_a_recorded_allowance() -> None:
    """A mod's per-prompt context or always-on section needs a human allowance."""
    unlisted = sorted(
        {
            (hook.plugin, hook.event)
            for hook in _marketplace_module_hooks()
            if hook.delivers
        }
        - PERMITTED_MOD_DELIVERIES.keys()
    )

    assert not unlisted, (
        "a mod delivers per-prompt context or an always-on system-prompt section "
        "with no recorded human allowance; drop the delivery or record the "
        f"ruling in PERMITTED_MOD_DELIVERIES: {unlisted}"
    )


def test_every_mod_allowance_names_a_current_delivery() -> None:
    """An allowance outlives its delivery only as a stale exemption."""
    delivering = {
        (hook.plugin, hook.event)
        for hook in _marketplace_module_hooks()
        if hook.delivers
    }

    assert PERMITTED_MOD_DELIVERIES.keys() <= delivering, sorted(
        PERMITTED_MOD_DELIVERIES.keys() - delivering
    )


def test_observation_only_mod_is_read_and_delivers_nothing() -> None:
    """Non-match control: agent-notice-log's prompt hook passes the prompt on."""
    hooks = [
        hook for hook in _marketplace_module_hooks() if hook.plugin == NOTICE_LOG
    ]

    assert ModuleHook(NOTICE_LOG, "prompt.submit", delivers=False) in hooks
    assert not [hook for hook in hooks if hook.delivers]


_STRING_IS_NOT_A_KEY = """\
export const register: Register = on => {
  // on('prompt.compose', ...) in a comment registers nothing.
  on('prompt.submit', ($, e, next) => {
    $.ui.log("context: none attached", { to: 'debug' })
    const isQuoted = /["(]/.test(e.text)
    return next(isQuoted ? e : e)
  })
}
"""

_SHORTHAND_UNDER_ANOTHER_NAME = """\
export const register: Register = (hook, options) => {
  hook('prompt.submit', async ($, e, next) => {
    const context = [...(e.context ?? []), `now ${await $.clock.now()} (local)`]
    return next({ ...e, context })
  })
}
"""

_COMPOSE_DROPS_ONLY = """\
export const register: Register = on => {
  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    return { sections: [...composed.sections.filter(s => s.id !== 'memory')] }
  })
}
"""

_COMPOSE_ADDS = """\
const MINE = { id: 'fixture:mine', text: 'Always do the thing.', scope: 'session' }
export const register: Register = on => {
  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    return { sections: [...composed.sections, MINE] }
  })
}
"""


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (_STRING_IS_NOT_A_KEY, [ModuleHook("fixture", "prompt.submit", False)]),
        (
            _SHORTHAND_UNDER_ANOTHER_NAME,
            [ModuleHook("fixture", "prompt.submit", True)],
        ),
        (_COMPOSE_DROPS_ONLY, [ModuleHook("fixture", "prompt.compose", False)]),
        (_COMPOSE_ADDS, [ModuleHook("fixture", "prompt.compose", True)]),
    ],
    ids=[
        "string-comment-regex-are-not-code",
        "shorthand-context-registrar-renamed",
        "compose-that-only-drops",
        "compose-that-adds",
    ],
)
def test_module_parse_classifies_delivery(
    source: str, expected: list[ModuleHook]
) -> None:
    assert _module_hooks("fixture", source) == expected


def test_module_parse_refuses_a_registrar_it_cannot_follow() -> None:
    """A hook added through a helper is outside the parse, so it fails loudly."""
    source = """\
export const register: Register = on => {
  addHooks(on)
}
"""

    with pytest.raises(ValueError, match="registrar"):
        _module_hooks("fixture", source)


def test_hook_inventory_reaches_a_known_mechanical_boundary() -> None:
    """Positive control: marketplace traversal reaches the Bash dispatcher."""
    assert (
        "denubis-hook-pretooluse-dispatcher",
        "PreToolUse",
    ) in _marketplace_hook_events()


def test_no_marketplace_plugin_runs_on_every_user_prompt() -> None:
    """UserPromptSubmit is not an action boundary for this marketplace."""
    offenders = sorted(
        plugin
        for plugin, event in _marketplace_hook_events()
        if event == "UserPromptSubmit"
    )

    assert not offenders, (
        "generic per-prompt delivery has no reliable action boundary; "
        f"retire or relocate these hooks: {offenders}"
    )


def test_no_marketplace_plugin_reminds_after_git_review() -> None:
    """A read-only git command is not the commit-preparation boundary."""
    assert (
        "denubis-hook-claudemd-reminder",
        "PostToolUse",
    ) not in _marketplace_hook_events()


def test_notes_retrieval_does_not_run_at_session_start() -> None:
    """Project-memory retrieval starts from a task, not an empty session."""
    assert (
        "denubis-notes-advisory",
        "SessionStart",
    ) not in _marketplace_hook_events()


def test_project_notes_retrieval_is_direct_main_agent_work() -> None:
    """The plugin exposes one skill without hook or agent machinery."""

    assert not (PROJECT_NOTES_ROOT / "hooks").exists()
    assert not (PROJECT_NOTES_ROOT / "agents").exists()
    assert (PROJECT_NOTES_ROOT / ".claude-plugin" / "plugin.json").is_file()
    assert (
        PROJECT_NOTES_ROOT / "skills" / "scanning-project-notes" / "SKILL.md"
    ).is_file()


def test_session_start_keeps_side_effects_without_generic_workflow_context() -> None:
    events = _marketplace_hook_events()
    plan_hooks = json.loads(PLAN_HOOKS.read_text(encoding="utf-8"))["hooks"]
    session_commands = [
        hook["command"]
        for registration in plan_hooks["SessionStart"]
        for hook in registration["hooks"]
    ]

    assert ("denubis-basic-agents", "SessionStart") not in events
    assert session_commands == [
        'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/update-live-marker.py"'
    ]
