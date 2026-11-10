"""Repository contracts for always-on instruction delivery.

The inventory comes from the marketplace and each listed plugin's ``hooks.json``.
The PreToolUse assertion is a positive control: a clean result is meaningful only if
the same traversal finds a known active hook boundary.

A ``hooks.json`` may instead name hooks modules (mods) under ``modules``. Their
counterparts of these boundaries are a ``prompt.submit`` hook that attaches
``context`` (per-prompt delivery), a ``prompt.compose`` hook that adds a
system-prompt section (always-on delivery), and a conversation row the model
reads, appended with ``$.session.append`` or rewritten by a ``session.append``
hook. ``_module_hooks`` and ``_module_deliveries`` read them from the TypeScript
source; their docstrings state the parse and its coverage boundary. The mod
inventory has its own positive and non-match controls.

Mods keep the settings rule's default: a mod delivery fails. A delivery the human
has permitted is listed in ``PERMITTED_MOD_DELIVERIES``, keyed by plugin and door
(``prompt.submit`` for context, ``prompt.compose`` for a section,
``session.append`` for a row) and valued by
the authority: the decision record and the original message's raw record. An
allowance covers every text that door of that plugin delivers. An allowance whose
delivery is gone fails too, so no exemption outlives its subject.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PROJECT_NOTES_ROOT = REPO_ROOT / "plugins" / "denubis-project-notes"
PLAN_HOOKS = (
    REPO_ROOT / "plugins" / "denubis-plan-and-execute" / "hooks" / "claude-hooks.json"
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
_MESSAGE_KEY = re.compile(r"(?<![\w$.])message\s*:|[{,]\s*message\s*[,}]")
_SECTIONS_KEY = re.compile(r"(?<![\w$.])sections\s*:\s*")
# A call of the engine's `$.session.append`, under whatever name the module
# gives `$`: it writes a row into the conversation.
_APPEND_CALL = re.compile(r"\.\s*session\s*\.\s*append\s*\(")
APPEND_DOOR = "session.append"


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
       non-spread element, or with a value that is not an array literal. A
       ``session.append`` hook delivers when its arguments write a ``message``
       key: it rewrites a row the model reads.

    Coverage boundary: an input or answer a helper outside the hook's own call
    builds is not followed. Step 3 errs towards delivery: a ``context:`` type
    annotation, a destructured ``{ message }`` or a list of sections built
    elsewhere counts. ``_module_deliveries`` adds the rows a module appends.
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
        elif event == APPEND_DOOR:
            delivers = _MESSAGE_KEY.search(arguments) is not None
        else:
            delivers = False
        hooks.append(ModuleHook(plugin, event, delivers))
    return hooks


def _module_deliveries(plugin: str, source: str) -> set[tuple[str, str]]:
    """The doors, ``(plugin, door)``, through which a hooks module delivers.

    Its delivering hooks, and ``session.append`` when the module's code calls
    ``$.session.append`` anywhere: a row appended to the conversation that the
    model reads. The call is found in the whole module, so a helper outside any
    hook's own call is seen. Coverage boundary: a call through another
    spelling (a destructured ``session``, ``session['append']``) is not, and a
    notice the model never reads (``type: 'system'``) counts as a delivery.
    """
    deliveries = {
        (hook.plugin, hook.event)
        for hook in _module_hooks(plugin, source)
        if hook.delivers
    }
    if _APPEND_CALL.search(_mask_non_code(source)) is not None:
        deliveries.add((plugin, APPEND_DOOR))
    return deliveries


def _marketplace_module_sources() -> list[tuple[str, str]]:
    """``(plugin, source)`` of every hooks module a marketplace plugin names."""
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    sources: list[tuple[str, str]] = []

    for plugin in marketplace["plugins"]:
        plugin_root = REPO_ROOT / plugin["source"].removeprefix("./")
        hooks_path = _claude_hooks_path(plugin_root)
        if not hooks_path.is_file():
            continue
        modules = json.loads(hooks_path.read_text(encoding="utf-8")).get("modules", [])
        for module in modules:
            source = (hooks_path.parent / module).read_text(encoding="utf-8")
            sources.append((plugin["name"], source))

    return sources


def _marketplace_module_hooks() -> list[ModuleHook]:
    """Every hook of every hooks module a marketplace plugin's hooks.json names."""
    return [
        hook
        for plugin, source in _marketplace_module_sources()
        for hook in _module_hooks(plugin, source)
    ]


def _marketplace_module_deliveries() -> set[tuple[str, str]]:
    """Every ``(plugin, door)`` through which a marketplace mod delivers."""
    deliveries: set[tuple[str, str]] = set()
    for plugin, source in _marketplace_module_sources():
        deliveries |= _module_deliveries(plugin, source)
    return deliveries


QUIET_AGENTS = "denubis-hook-quiet-agents"
NOTICE_LOG = "denubis-hook-agent-notice-log"

# The human's ruling of 2026-10-25, "I... system prompt adjusting in the plugin is
# fine. And context line is fine.", answering whether quiet-agents' two
# deliveries may stand under the extended contract.
_QUIET_AGENTS_RULING = (
    "docs/architecture/decisions/0051-instruction-delivery-contract-reads-mods.md; "
    "raw record "
    "/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/"
    "e159b867-7a1e-4e2a-a524-058f6b7e72b6.jsonl:1237 "
    "(message 2e705937-f326-469e-b25c-9e95e1441cea)"
)

QUESTION_ZONE = "denubis-hook-question-zone"

# The human's ruling of 2026-11-08, "um, yes, do add the standing instruction.",
# answering whether question-zone may add its standing rule to the system prompt.
_QUESTION_ZONE_RULING = (
    "docs/architecture/decisions/2026-11-08-bbs-questions-go-in-question-zone.md; "
    "raw record "
    "/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/"
    "d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl:6416 "
    "(message 4e874a67-67a2-4d13-9481-fa753100772f)"
)

# The human's rulings of 2026-11-08: "can we just have all the necessary line-cite
# stuff come along with the message when I hit enter? It's silly that it needs to
# be done by llm if it can be derived", read as the allowance for question-zone to
# append each answer's citation as a row the model reads (item 9 of the record);
# and "we need to make sure we have a buffer for this shit?", read as the
# allowance to hand each question its check sends back to the model the same way,
# in place of a prompt of its own. Both readings are the supervisor's.
_QUESTION_ZONE_CITATION_RULING = (
    "docs/architecture/decisions/2026-11-08-bbs-questions-go-in-question-zone.md; "
    "raw records "
    "/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/"
    "d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl:8529 "
    "(message 8a47c801-4a7c-4ec2-bca8-c8af7da515b6) and :10371 "
    "(message a07592ea-7d4e-4608-aeb2-d5dfd191a006)"
)

COMPACT_NAG = "denubis-hook-compact-nag"

# The human's rulings of 2026-11-10: "no, it should inject a note that we need to
# prepare for compact at 40% and let the session call for a compact when it's
# ready" (:699) and "no, but it should fire a more urgent nag each stop after 50%"
# (:794), read as the allowance for compact-nag to append its notes to a session
# as rows the model reads; and "(also, if there's now a trivial way of surfacing
# the heads-up alerts in subagents to main, include that, ...)" (:871), read as
# the allowance for the notice it appends to the main conversation when a
# subagent is noted. The readings are the supervisor's.
_COMPACT_NAG_RULING = (
    "docs/architecture/decisions/2026-11-10-bbs-compact-nag-leaves-engine-threshold.md; "
    "raw records "
    "/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/"
    "d4590dde-909a-4cc7-a999-be56c975149c.jsonl:699 "
    "(record 97f87105-e87a-4406-b237-19783a2d694b), :794 "
    "(record 58780c7e-a3c6-4b43-a6fa-5139428b329a) and :871 "
    "(record 4e449354-3185-4a4c-b7fc-defa05861f94)"
)

# (plugin, door) -> the authority that permits that mod delivery. An entry needs a
# human ruling; the door is the event `ModuleHook` reports, or `session.append`
# for a row the module appends.
PERMITTED_MOD_DELIVERIES: dict[tuple[str, str], str] = {
    (QUIET_AGENTS, "prompt.compose"): _QUIET_AGENTS_RULING,
    (QUIET_AGENTS, "prompt.submit"): _QUIET_AGENTS_RULING,
    (QUESTION_ZONE, "prompt.compose"): _QUESTION_ZONE_RULING,
    (QUESTION_ZONE, APPEND_DOOR): _QUESTION_ZONE_CITATION_RULING,
    (COMPACT_NAG, APPEND_DOOR): _COMPACT_NAG_RULING,
}


def _unlisted_mod_deliveries(deliveries: set[tuple[str, str]]) -> list[tuple[str, str]]:
    """The deliveries no recorded human allowance covers."""
    return sorted(deliveries - PERMITTED_MOD_DELIVERIES.keys())


def test_module_inventory_reaches_known_mod_deliveries() -> None:
    """Positive control: marketplace traversal reads hooks modules.

    quiet-agents attaches context at ``prompt.submit`` and adds a system-prompt
    section at ``prompt.compose``; question-zone appends a row the model reads.
    A clean result over mods means something only if the same traversal finds
    these.
    """
    assert {
        (QUIET_AGENTS, "prompt.submit"),
        (QUIET_AGENTS, "prompt.compose"),
        (QUESTION_ZONE, APPEND_DOOR),
    } <= _marketplace_module_deliveries()


def test_no_marketplace_mod_delivers_without_a_recorded_allowance() -> None:
    """A mod's context, section or row for the model needs a human allowance."""
    unlisted = _unlisted_mod_deliveries(_marketplace_module_deliveries())

    assert not unlisted, (
        "a mod delivers per-prompt context, an always-on system-prompt section "
        "or a conversation row with no recorded human allowance; drop the "
        f"delivery or record the ruling in PERMITTED_MOD_DELIVERIES: {unlisted}"
    )


def test_every_mod_allowance_names_a_current_delivery() -> None:
    """An allowance outlives its delivery only as a stale exemption."""
    delivering = _marketplace_module_deliveries()

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


_APPENDS_A_ROW = """\
const note = (text: string) => ({ message: { type: 'user', content: [{ type: 'text', text }] } })
const tell = async ($: EngineInterface, text: string): Promise<void> => {
  await $.session.append(note(text))
}
export const register: Register = on => {
  on('turn.complete', async ($, e, next) => {
    void tell($, 'Remember to run the gates.')
    return next(e)
  })
}
"""

_REWRITES_A_ROW = """\
export const register: Register = on => {
  on('session.append', async ($, e, next) => {
    const content = [...e.message.content, { type: 'text', text: 'Remember to run the gates.' }]
    return next({ ...e, message: { ...e.message, content } })
  })
}
"""

_READS_ROWS_ONLY = """\
export const register: Register = on => {
  // $.session.append(note) in a comment appends nothing.
  on('session.append', async ($, e, next) => {
    const kept = await next(e)
    $.ui.log(`kept ${kept.uuid}; no $.session.append(row) here`, { to: 'debug' })
    return kept
  })
}
"""


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (_APPENDS_A_ROW, {("fixture", "session.append")}),
        (_REWRITES_A_ROW, {("fixture", "session.append")}),
        (_READS_ROWS_ONLY, set()),
    ],
    ids=[
        "appends-a-row-from-a-helper",
        "rewrites-a-row-it-is-handed",
        "reads-rows-and-names-the-call-only-in-text",
    ],
)
def test_module_parse_finds_rows_written_for_the_model(
    source: str, expected: set[tuple[str, str]]
) -> None:
    """A row the model reads, appended or rewritten, is a delivery."""
    assert _module_deliveries("fixture", source) == expected


def test_a_mod_that_delivers_only_through_rows_needs_an_allowance() -> None:
    """The allowance check fails a mod whose one delivery is an appended row."""
    assert _unlisted_mod_deliveries(_module_deliveries("fixture", _APPENDS_A_ROW)) == [
        ("fixture", "session.append")
    ]


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


def test_session_start_keeps_side_effects_without_generic_workflow_context(
    tmp_path: Path,
) -> None:
    events = _marketplace_hook_events()
    plan_hooks = json.loads(PLAN_HOOKS.read_text(encoding="utf-8"))["hooks"]
    session_commands = [
        hook["command"]
        for registration in plan_hooks["SessionStart"]
        for hook in registration["hooks"]
    ]

    assert ("denubis-basic-agents", "SessionStart") not in events
    assert len(session_commands) == 1
    marker = tmp_path / "session.live"
    marker.write_text("session_id=old\nstart_time=unchanged\n", encoding="utf-8")
    session_id = "01234567-89ab-cdef-0123-456789abcdef"
    result = subprocess.run(
        ["/bin/sh", "-c", session_commands[0]],
        env={
            **os.environ,
            "CLAUDE_PLUGIN_ROOT": str(PLAN_HOOKS.parents[1]),
            "CR_LIVE_FILE": str(marker),
        },
        input=json.dumps(
            {
                "hook_event_name": "SessionStart",
                "transcript_path": str(tmp_path / f"{session_id}.jsonl"),
            }
        ),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert marker.read_text(encoding="utf-8") == (
        f"session_id={session_id}\nstart_time=unchanged\n"
    )
