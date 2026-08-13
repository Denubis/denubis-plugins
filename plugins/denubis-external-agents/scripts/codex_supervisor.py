"""Repo-local Codex supervision monitor.

The pure functions classify and deduplicate observations. The command-line
shell is deliberately narrow: tmux provides conservative fallback inspection,
while Codex hooks send sanitized datagrams for low-latency lifecycle events.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from types import TracebackType
    from typing import BinaryIO, Self

MAX_HOOK_BYTES = 1_048_576
MAX_DATAGRAM_BYTES = 4096
TMUX_PANE_FORMAT = "#{pane_id}\t#{pane_current_command}\t#{pane_pid}"
PROMPT_MARKER = "\N{SINGLE RIGHT-POINTING ANGLE QUOTATION MARK}"
# A pending action is raised again after two minutes, then five, then every ten.
# Announcing once was deliberate, because a stationary screen is re-observed every poll
# and an ungated repeat trains the reader to ignore it. A clock is the repair; removing
# the guard is not. Operator ruling 2026-07-28, after a pane sat blocked for 57 minutes.
REMINDER_BACKOFF_SECONDS = (120.0, 300.0, 600.0)
# ...and stops at the hour (Brian, 2026-08-04). The supervisor reading these lines can
# be blocked on a permission prompt in its own pane, where the ten-minute drum queues a
# repeat per ten minutes the human is away, so fifteen hours produced ninety lines
# carrying one fact between them. The last line says it is the last, because a monitor
# that simply stops printing reads exactly like one that has died.
REMINDER_GIVE_UP_SECONDS = 3600.0
SUBMIT_ATTEMPTS = 3
SUBMIT_POLLS = 4
SUBMIT_POLL_SECONDS = 1.0
# How long an approval waits for Codex to say what it did before reporting silence.
RESPONSE_POLLS = 30
# How long a context verb waits for the pane to come back Ready. A compaction is a model
# call over the whole transcript and a clear restarts the MCP servers, so both are slow
# in a way an approval is not; three minutes bounds it without cutting a real one short.
SETTLE_POLLS = 180
# Below this much context left, a dispatch stops and asks rather than filling a pane
# that cannot hold the answer. Brian, 2026-08-01: compaction is to run aggressively
# here, because the meter falls fast. `--under-floor` carries a human ruling past it.
CONTEXT_FLOOR_PERCENT = 30
# Typed into the composer as keystrokes, never pasted. Codex reads a pasted or narrated
# instruction as a task, so it reads files to answer it and the meter goes down.
SLASH_COMMANDS = ("/clear", "/compact", "/status")
CODEX_SPAWN_COMMAND = (
    # Containment is the sandbox rather than a dialog per command: `workspace-write`
    # bounds writes to the working tree, and `on-request` leaves codex to escalate
    # only when it needs to leave it. Spawning with neither raised one dialog for
    # every probe in a verification pass, which is the loop this pairing removes.
    "exec codex -c check_for_update_on_startup=false -s workspace-write -a on-request"
)
CODEX_LABEL_OPTION = "@codex_label"
CODEX_PING_INSTRUCTION = (
    "If anything is unclear, ambiguous, or contradictory, stop and ask one "
    "specific, critical, and pointed question at a time until you have "
    "sufficient information. Surface any decision rather than deciding it "
    "silently, so the supervisor documents it."
)
BUSY_SPINNERS = frozenset(
    "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"
)

Command = tuple[str, ...]
CommandRunner = Callable[[Command], str]


class MonitorError(RuntimeError):
    """An operational condition that prevents safe monitoring."""


class NoCodexPaneError(MonitorError):
    """No Codex pane exists in the caller's tmux window."""


class ObservationKind(StrEnum):
    """States understood by the monitor's policy core."""

    BUSY = "busy"
    APPROVAL = "approval"
    QUESTION = "question"
    DONE = "done"
    CRASH = "crash"


@dataclass(frozen=True)
class Observation:
    """A privacy-safe classified Codex state."""

    kind: ObservationKind
    key: str | None = None
    detail: str | None = None
    correlation_key: str | None = None
    scoped: bool = False
    # Set only on a re-raise, so a reminder can say how long the pane has been waiting.
    # Never transported: serialize_observation whitelists four fields and not this one.
    waited_seconds: float | None = None
    # Set only on the raise that gives up, so the quiet after it reads as a decision
    # rather than a failure. Not transported either, for the same reason.
    final: bool = False


@dataclass(frozen=True)
class Reminder:
    """A pending action and when to raise it again."""

    action: Observation
    armed_at: float
    due_at: float
    step: int = 0


@dataclass(frozen=True)
class MonitorState:
    """Deduplication state for one monitor lifetime."""

    seen_activity: bool = False
    emitted_keys: frozenset[str] = frozenset()
    last_correlation_key: str | None = None
    last_action_scoped: bool = False
    reminder: Reminder | None = None
    # The correlation key of a prompt whose hour ran out. Without it a busy frame
    # refunds the hour, because the returning screen looks like any other pending thing
    # that has lost its clock, and _ensure_reminder would start the ladder again.
    abandoned_key: str | None = None


@dataclass(frozen=True)
class Transition:
    """Result of applying one observation to monitor state."""

    state: MonitorState
    action: Observation | None


@dataclass(frozen=True)
class PaneCandidate:
    """Tmux pane identity plus the process tmux started for it."""

    pane_id: str
    pane_pid: int


@dataclass(frozen=True)
class PaneRef:
    """Stable tmux pane identity plus its foreground process-group identity."""

    pane_id: str
    process_group_id: int


@dataclass(frozen=True)
class TopologyResult:
    """Result of checking the joined Codex pane."""

    tracker: TopologyTracker
    crash: Observation | None


@dataclass(frozen=True)
class TopologyTracker:
    """Allow a short redock gap without accepting a replaced process."""

    target: PaneRef
    miss_limit: int
    misses: int = 0

    def observe(self, candidate: PaneRef | None) -> TopologyResult:
        """Record one same-window discovery result."""
        if candidate == self.target:
            return TopologyResult(
                TopologyTracker(self.target, self.miss_limit),
                None,
            )
        if candidate is not None:
            return TopologyResult(
                self,
                _crash(
                    "joined Codex process was replaced "
                    f"({self.target.pane_id}/{self.target.process_group_id} -> "
                    f"{candidate.pane_id}/{candidate.process_group_id})"
                ),
            )

        misses = self.misses + 1
        tracker = TopologyTracker(self.target, self.miss_limit, misses)
        if misses < self.miss_limit:
            return TopologyResult(tracker, None)
        return TopologyResult(
            tracker,
            _crash(f"joined Codex pane {self.target.pane_id} disappeared"),
        )


_BULLET = re.compile(r"^\s*•(?:\s|$)")
# The dialog's own furniture, which a wrapped command must never be joined to.
_DIALOG_CHROME = re.compile(
    r"^(?:would you like to|press enter to confirm|environment:|reason:|esc to cancel)",
    re.IGNORECASE,
)
_STATUS_BULLET = re.compile(r"^(?:working|thinking|waiting)\b", re.IGNORECASE)


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _digest(*parts: object) -> str:
    encoded = json.dumps(
        parts,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _action_key(kind: ObservationKind, material: str) -> str:
    return _digest(kind.value, _normalized(material))


def _command_line(lines: list[str]) -> str | None:
    """Return the last `$` command in a slice, rejoined across any wrap.

    Codex wraps a command too long for the pane, so reading the `$` line alone
    names a command nobody approved, cut at whatever column the pane happens to
    be. The remainder runs to the blank line or the option list below it.
    """
    for index in range(len(lines) - 1, -1, -1):
        stripped = lines[index].strip()
        if stripped.startswith("$ ") and len(stripped) > 2:
            parts = [stripped[2:]]
            for line in lines[index + 1 :]:
                following = line.strip()
                if (
                    not following
                    or _is_option_line(line)
                    or _DIALOG_CHROME.match(following)
                ):
                    break
                parts.append(following)
            return " ".join(parts)
    return None


def _approval_material(content: str) -> str:
    """Return the command a dialog is asking about, or its question if it has none.

    The command does not sit at a fixed offset from the question. It is drawn
    above the question on the older dialog and below the reason block on the
    taller one, so a window of a few lines either way finds it on one shape and
    a slab of option text on the other. The search instead runs across the whole
    dialog and stops at the boundaries marking where it begins and ends. A
    bullet or a rule above the question closes the previous turn, and the option
    list below it closes the dialog, which together keep a command from an
    earlier turn from being named as this one.
    """
    lines = content.splitlines()
    openers = [
        index
        for index, line in enumerate(lines)
        if re.search(r"would you like to", line, re.IGNORECASE)
    ] or [
        index
        for index, line in enumerate(lines)
        if re.search(r"press enter to confirm", line, re.IGNORECASE)
    ]
    if not openers:
        return _command_line(lines) or _normalized(content)

    opener = openers[-1]
    start = 0
    for index in range(opener - 1, -1, -1):
        if _BULLET.match(lines[index]) or lines[index].strip().startswith("─"):
            start = index + 1
            break
    end = next(
        (index for index in range(opener, len(lines)) if _is_option_line(lines[index])),
        len(lines),
    )
    return _command_line(lines[start:end]) or _normalized(lines[opener].strip())


def _message_block(lines: list[str], start: int) -> str:
    """Read one bullet and the lines belonging to it, stopping at the next turn."""
    message_lines = [_BULLET.sub("", lines[start])]
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if _BULLET.match(line):
            break
        if stripped.startswith((PROMPT_MARKER, "─")) or stripped.endswith(
            "context left"
        ):
            break
        if stripped and stripped != "? for shortcuts":
            message_lines.append(stripped)
    return _normalized("\n".join(message_lines))


def _bullet_indexes(lines: list[str]) -> list[int]:
    return [index for index, line in enumerate(lines) if _BULLET.match(line)]


def _bullet_texts(content: str) -> set[str]:
    """Return every bullet already on screen, for telling a new one from an old one."""
    lines = content.splitlines()
    return {_BULLET.sub("", lines[index]).strip() for index in _bullet_indexes(lines)}


def _first_new_message(seen: set[str], content: str) -> str | None:
    """Return the first bullet Codex has drawn that was not on screen before.

    The working spinner is drawn as a bullet and says only that Codex is alive,
    so it is passed over in favour of something Codex actually did.
    """
    lines = content.splitlines()
    for index in _bullet_indexes(lines):
        text = _BULLET.sub("", lines[index]).strip()
        if text and text not in seen and not _STATUS_BULLET.match(text):
            return _message_block(lines, index)
    return None


def _assistant_message(content: str) -> str:
    lines = content.splitlines()
    bullet_indexes = _bullet_indexes(lines)
    if bullet_indexes:
        return _message_block(lines, bullet_indexes[-1])
    return _normalized(content)


def _looks_like_question(message: str) -> bool:
    return message.rstrip().endswith("?")


def _crash(detail: str) -> Observation:
    return Observation(
        ObservationKind.CRASH,
        _action_key(ObservationKind.CRASH, detail),
        detail,
    )


def _action_observation(kind: ObservationKind, material: str) -> Observation:
    key = _action_key(kind, material)
    return Observation(kind, key, correlation_key=key)


def _fatal_observation(text: str) -> Observation | None:
    fatal_match = re.search(
        (
            r"stream disconnected before completion|"
            r"codex process (?:exited|terminated)|"
            r"thread ['\"].*['\"] panicked|"
            r"fatal (?:codex )?error|"
            r"(?:usage|rate) limit (?:has been )?reached"
        ),
        text,
        re.IGNORECASE,
    )
    if fatal_match is None:
        return None
    return _crash(_normalized(fatal_match.group(0)))


def _ready_observation(title: str, content: str) -> Observation:
    message = _assistant_message(content)
    if fatal := _fatal_observation(f"{title}\n{message}"):
        return fatal
    kind = (
        ObservationKind.QUESTION
        if _looks_like_question(message)
        else ObservationKind.DONE
    )
    return _action_observation(kind, message)


def _approval_is_pending(recent_content: str) -> bool:
    """Report whether approval text is still awaiting an answer.

    Codex leaves answered approval text in the scrollback, so the words alone cannot
    say whether it is waiting. A bullet opens an assistant message, per
    `_assistant_message`, so a bullet after the last approval marker means Codex
    answered and moved on. Nothing after it means the prompt is still on screen.
    """
    prompts = list(
        re.finditer(
            r"would you like to run|press enter to confirm",
            recent_content,
            re.IGNORECASE,
        )
    )
    if not prompts:
        return False
    after_last_prompt = recent_content[prompts[-1].end() :]
    return not re.search(r"^\s*•(?:\s|$)", after_last_prompt, re.MULTILINE)


_OPTION = re.compile(r"(\d+)\.\s*(.+?)(?=\s{2,}\d+\.|\s*$)")
_OPTION_LINE_LEAD = re.compile(rf"^[\s>{PROMPT_MARKER}]+")
_OPTION_START = re.compile(rf"^[\s>{PROMPT_MARKER}]*(\d+)\.")
_OPTION_KEY = re.compile(r"\(([A-Za-z]+)\)\s*$")
_AFFIRMATIVE = re.compile(r"yes\b", re.IGNORECASE)
_STANDING_GRANT = re.compile(
    r"ask again|don'?t ask|do not ask|always|approve all|every time|no longer ask",
    re.IGNORECASE,
)


def _option_column(line: str) -> int | None:
    """Return the column a choice number starts at, past any cursor marker."""
    match = _OPTION_START.match(line)
    return match.start(1) if match else None


def _is_option_line(line: str) -> bool:
    return _option_column(line) is not None


def _is_continuation(line: str, column: int) -> bool:
    """Report whether a line is the wrapped remainder of the option above it.

    Codex indents what it wraps past the column its numbers start at, which is
    what tells a continuation from the reason block sitting above the list.
    """
    return bool(line.strip()) and len(line) - len(line.lstrip()) > column


def _approval_options(content: str) -> list[tuple[str, str]]:
    """Read the numbered choices from the last option list Codex drew.

    Codex draws the list either as one line carrying every option or as one
    option per line, and wraps any option too long for the pane onto a further
    indented line. That remainder is not itself numbered, so a block read as a
    run of numbered lines ends at the first wrap and loses every option above
    it, which is how a three-option dialog came back as no options at all. The
    block is instead bounded from the last numbered line outwards, taking in
    both numbered lines and the continuations belonging to them. Requiring at
    least two options that count up from one keeps a numbered line inside the
    command being approved from being read as the dialog.
    """
    lines = content.splitlines()
    columns = {
        index: column
        for index, line in enumerate(lines)
        if (column := _option_column(line)) is not None
    }
    if not columns:
        return []

    last = max(columns)
    end = last
    while end + 1 < len(lines) and _is_continuation(lines[end + 1], columns[last]):
        end += 1
    start, column, index = last, columns[last], last - 1
    while index >= 0:
        if index in columns:
            start, column = index, columns[index]
        elif not _is_continuation(lines[index], column):
            break
        index -= 1

    collected: list[list[str]] = []
    for index in range(start, end + 1):
        if index in columns:
            body = _OPTION_LINE_LEAD.sub("", lines[index])
            collected.extend(
                [match[1], match[2].strip()] for match in _OPTION.finditer(body)
            )
        elif collected:
            collected[-1][1] = f"{collected[-1][1]} {lines[index].strip()}"

    counted = [number for number, _ in collected]
    if len(collected) < 2 or counted != [str(n) for n in range(1, len(collected) + 1)]:
        return []
    return [(number, label) for number, label in collected]


def approval_choice(content: str) -> str:
    """Return the key answering a pending approval for the command on screen alone.

    The older dialog offers `Yes` and `No`, and the commoner one sits a standing
    grant between the two, so selection reads each option's own label rather than
    assuming a position and takes the affirmative that grants nothing beyond this
    command. An option offering to stop asking grants standing permission for
    everything matching, which changes the session's posture and is the human's
    to give. Where two affirmatives both read as narrow, the choice is refused,
    which is what keeps a standing grant worded in some unrecognised way from
    being pressed on the strength of the likelier reading. The key returned is
    the one the label advertises wherever Codex prints one, falling back to the
    option's list number.
    """
    if not _approval_is_pending(content):
        raise MonitorError("no pending approval on the joined pane")
    options = _approval_options(content)
    narrow = [
        (number, label)
        for number, label in options
        if _AFFIRMATIVE.match(label) and not _STANDING_GRANT.search(label)
    ]
    if len(narrow) == 1:
        number, label = narrow[0]
        advertised = _OPTION_KEY.search(label)
        return advertised[1] if advertised else number
    complaint = (
        "no affirmative granting only this command"
        if not narrow
        else f"{len(narrow)} affirmatives, none of them clearly the narrow one"
    )
    rendered = "   ".join(f"{number}. {label}" for number, label in options)
    raise MonitorError(f"{complaint}, so this one is yours to answer: {rendered}")


def classify_snapshot(title: str, content: str) -> Observation:
    """Classify a bounded TUI snapshot, defaulting unknown states to busy."""
    if re.search(r"action required", title, re.IGNORECASE):
        material = _approval_material(content)
        return _action_observation(ObservationKind.APPROVAL, material)

    if any(spinner in title for spinner in BUSY_SPINNERS) or re.search(
        r"\bworking\b|\bwaiting\b",
        title,
        re.IGNORECASE,
    ):
        return Observation(ObservationKind.BUSY)

    recent_content = "\n".join(content.splitlines()[-12:])
    # A pending approval is checked before the title, because Codex's steady-state
    # title is "Ready" and it keeps saying Ready while drawing an approval prompt.
    # Returning on the title first reported those as DONE, telling the supervisor
    # Codex had finished at the moment it was blocked on them (observed 2026-07-27).
    # Only a *pending* approval may pre-empt the title: answered approval text stays
    # in the scrollback, and treating that as pending would report a finished pane as
    # waiting. The busy branch above still wins outright, since a spinner means Codex
    # is mid-turn and anything below it may be stale.
    if _approval_is_pending(recent_content):
        return _action_observation(
            ObservationKind.APPROVAL,
            _approval_material(recent_content),
        )

    if re.search(r"\bready\b", title, re.IGNORECASE):
        return _ready_observation(title, content)

    if fatal := _fatal_observation(f"{title}\n{recent_content}"):
        return fatal

    return Observation(ObservationKind.BUSY)


def _correlation_of(observation: Observation) -> str:
    """The key identifying one waiting thing across both the poll and hook channels."""
    return (
        observation.correlation_key
        or observation.key
        or _digest(observation.kind.value)
    )


def advance(state: MonitorState, observation: Observation) -> Transition:
    """Emit each actionable observation once and keep all busy states silent."""
    if observation.kind is ObservationKind.BUSY:
        return Transition(
            MonitorState(
                seen_activity=True,
                emitted_keys=state.emitted_keys,
                last_correlation_key=state.last_correlation_key,
                last_action_scoped=state.last_action_scoped,
                # Busy means Codex is mid-turn, so nothing waits on the human and a
                # pending reminder would nag about a prompt already answered.
                #
                # This does not re-arm by itself, and a comment here claimed it did
                # until 2026-08-04. A returning approval carries the correlation key
                # already recorded, so it takes the unchanged branch below, which
                # neither emits nor arms. _ensure_reminder is what restores the clock,
                # and it is all that stands between a spinner frame and a silent pane.
                reminder=None,
                abandoned_key=state.abandoned_key,
            ),
            None,
        )
    if (
        observation.kind in {ObservationKind.QUESTION, ObservationKind.DONE}
        and not state.seen_activity
    ):
        return Transition(state, None)

    key = observation.key or _digest(observation.kind.value)
    correlation_key = _correlation_of(observation)
    if observation.scoped:
        if key in state.emitted_keys:
            return Transition(state, None)
        emitted_keys = state.emitted_keys | {key}
        # One action reaches the monitor twice, once as a hook and once as rendered
        # pane text, and they carry compatible correlation keys precisely so this can
        # tell them apart. A scoped hook event matching the correlation key an
        # unscoped pane snapshot already reported is the same action seen a second
        # way, so it updates state and stays silent rather than double-emitting.
        matched_snapshot = (
            correlation_key == state.last_correlation_key
            and not state.last_action_scoped
        )
        next_state = MonitorState(
            seen_activity=True,
            emitted_keys=emitted_keys,
            last_correlation_key=correlation_key,
            last_action_scoped=True,
            reminder=state.reminder,
            abandoned_key=state.abandoned_key,
        )
        return Transition(next_state, None if matched_snapshot else observation)

    if correlation_key == state.last_correlation_key:
        return Transition(state, None)
    next_state = MonitorState(
        seen_activity=True,
        emitted_keys=state.emitted_keys,
        last_correlation_key=correlation_key,
        last_action_scoped=False,
        reminder=state.reminder,
        abandoned_key=state.abandoned_key,
    )
    return Transition(next_state, observation)


def select_codex_pane(panes: str) -> PaneCandidate:
    """Require exactly one foreground Codex process in formatted tmux rows."""
    candidates: list[PaneCandidate] = []
    for line in panes.splitlines():
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise MonitorError(f"malformed tmux pane row: {line!r}")
        pane_id, command, pid_text = fields
        if re.fullmatch(r"%(?:0|[1-9]\d*)", pane_id) is None or not command:
            raise MonitorError(f"malformed tmux pane row: {line!r}")
        try:
            pane_pid = int(pid_text)
        except ValueError as error:
            raise MonitorError(f"malformed tmux pane row: {line!r}") from error
        if pane_pid <= 0:
            raise MonitorError(f"malformed tmux pane row: {line!r}")
        if Path(command).name.casefold() != "codex":
            continue
        candidates.append(PaneCandidate(pane_id, pane_pid))

    if not candidates:
        raise NoCodexPaneError("no Codex pane in Claude's current tmux window")
    if len(candidates) > 1:
        pane_ids = ", ".join(candidate.pane_id for candidate in candidates)
        raise MonitorError(
            f"multiple Codex panes in Claude's current tmux window: {pane_ids}"
        )
    return candidates[0]


def resolve_foreground_process_group(
    candidate: PaneCandidate,
    runner: CommandRunner,
) -> PaneRef:
    """Resolve the pane root's current terminal foreground process group."""
    raw_process_group = runner(
        ("ps", "-o", "tpgid=", "-p", str(candidate.pane_pid))
    ).strip()
    try:
        process_group_id = int(raw_process_group)
    except ValueError as error:
        raise MonitorError(
            f"could not resolve foreground process for {candidate.pane_id}"
        ) from error
    if process_group_id <= 0:
        raise MonitorError(
            f"could not resolve foreground process for {candidate.pane_id}"
        )
    return PaneRef(candidate.pane_id, process_group_id)


def run_command(argv: Command) -> str:
    """Run one argv-only command and return stdout."""
    try:
        result = subprocess.run(  # argv is fixed by callers; S603 is ignored repo-wide.
            argv,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise MonitorError(f"command not found: {argv[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or "command failed"
        raise MonitorError(detail) from error
    return result.stdout


def discover_codex_pane(
    caller_pane: str,
    runner: CommandRunner = run_command,
) -> PaneRef:
    """Find Codex only inside the tmux window containing the caller pane."""
    window_id = runner(
        ("tmux", "display-message", "-p", "-t", caller_pane, "#{window_id}")
    ).strip()
    if not window_id.startswith("@"):
        raise MonitorError(f"could not resolve tmux window for {caller_pane}")
    panes = runner(
        (
            "tmux",
            "list-panes",
            "-t",
            window_id,
            "-F",
            TMUX_PANE_FORMAT,
        )
    )
    candidate = select_codex_pane(panes)
    return resolve_foreground_process_group(candidate, runner)


def capture_snapshot(
    pane_id: str,
    tail_lines: int,
    runner: CommandRunner = run_command,
) -> Observation:
    """Capture and classify a bounded pane tail."""
    title = runner(
        ("tmux", "display-message", "-p", "-t", pane_id, "#{pane_title}")
    ).strip()
    content = runner(
        (
            "tmux",
            "capture-pane",
            "-p",
            "-t",
            pane_id,
            "-S",
            f"-{tail_lines}",
        )
    )
    return classify_snapshot(title, content)


def _permission_material(payload: Mapping[str, object]) -> str:
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, Mapping):
        for field in ("command", "cmd", "patch"):
            value = tool_input.get(field)
            if isinstance(value, str):
                return value
    return json.dumps(
        {
            "tool_name": payload.get("tool_name"),
            "tool_input": tool_input,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _hook_action(
    kind: ObservationKind,
    material: str,
    payload: Mapping[str, object],
) -> Observation:
    correlation_key = _action_key(kind, material)
    # The occurrence key digests session, turn and tool-call identity on top of the
    # correlation key, so the identical action in a later turn still emits. Keying on
    # the command alone would announce `pytest` once and then never again, however
    # many turns later Codex asks to run it a second time. The scope fields are
    # identities rather than content, so this costs no disclosure.
    scope = {
        field: value
        for field in ("session_id", "turn_id", "tool_use_id", "tool_call_id")
        if isinstance((value := payload.get(field)), str) and value
    }
    scoped = bool(scope)
    key = (
        _digest("hook", kind.value, correlation_key, scope)
        if scoped
        else correlation_key
    )
    return Observation(
        kind,
        key,
        correlation_key=correlation_key,
        scoped=scoped,
    )


def normalize_hook(payload: object) -> Observation | None:
    """Discard private hook fields and retain only an actionable digest."""
    if not isinstance(payload, Mapping):
        return None
    hook_payload = cast("Mapping[str, object]", payload)
    event_name = hook_payload.get("hook_event_name")
    if event_name in {"SessionStart", "UserPromptSubmit", "PostToolUse"}:
        return Observation(ObservationKind.BUSY)
    if event_name == "PermissionRequest":
        material = _permission_material(hook_payload)
        return _hook_action(
            ObservationKind.APPROVAL,
            material,
            hook_payload,
        )
    if event_name == "Stop":
        raw_message = hook_payload.get("last_assistant_message")
        message = raw_message if isinstance(raw_message, str) else ""
        kind = (
            ObservationKind.QUESTION
            if _looks_like_question(message)
            else ObservationKind.DONE
        )
        return _hook_action(kind, message, hook_payload)
    return None


def serialize_observation(observation: Observation) -> str:
    """Serialize only the privacy-safe transport contract."""
    return json.dumps(
        {
            "correlation_key": observation.correlation_key,
            "kind": observation.kind.value,
            "key": observation.key,
            "scoped": observation.scoped,
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def deserialize_observation(raw: bytes) -> Observation | None:  # noqa: PLR0911
    """Parse one bounded privacy-safe datagram.

    PLR0911 is suppressed rather than satisfied: three of the seven returns exist only
    because the excepts below must stay as separate clauses to keep this file parseable
    on Python 3.9. The branching is a portability artefact, not complexity.
    """
    try:
        payload = json.loads(raw)
        kind = ObservationKind(payload["kind"])
        key = payload["key"]
        correlation_key = payload["correlation_key"]
        scoped = payload["scoped"]
    # Do not recombine into a tuple. --hook makes this file a hook entry point, run
    # through whatever `python3` the consuming machine resolves, so it must parse on
    # 3.9+; the PEP 758 form is 3.14-only and dies with a SyntaxError before any logic
    # runs. A parenthesised tuple does not hold either, because `ruff format` rewrites
    # `except (A, B):` back to the 3.14 form under target-version = py314. Separate
    # clauses are the only stable portable spelling. json.JSONDecodeError is absent
    # because it subclasses ValueError.
    except KeyError:
        return None
    except TypeError:
        return None
    except ValueError:
        return None
    if key is not None and not isinstance(key, str):
        return None
    if correlation_key is not None and not isinstance(correlation_key, str):
        return None
    if not isinstance(scoped, bool):
        return None
    return Observation(
        kind,
        key,
        correlation_key=correlation_key,
        scoped=scoped,
    )


def runtime_directory(explicit: Path | None = None) -> Path:
    """Choose per-user volatile storage for the relay socket."""
    if explicit is not None:
        return explicit
    configured = os.environ.get("XDG_RUNTIME_DIR")
    if configured:
        return Path(configured) / "codex-watch"
    return Path(tempfile.gettempdir()) / f"codex-watch-{os.getuid()}"


def relay_socket_path(pane_id: str, runtime_dir: Path | None = None) -> Path:
    """Map a tmux pane identity to its relay socket."""
    pane_number = pane_id.removeprefix("%")
    if not pane_number.isdigit():
        raise MonitorError(f"invalid tmux pane identity: {pane_id!r}")
    return runtime_directory(runtime_dir) / f"pane-{pane_number}.sock"


def send_hook_observation(
    observation: Observation,
    pane_id: str,
    *,
    runtime_dir: Path | None = None,
) -> bool:
    """Send one non-blocking hook event; no listener is a silent no-op."""
    path = relay_socket_path(pane_id, runtime_dir)
    payload = serialize_observation(observation).encode()
    sender = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sender.setblocking(False)
        sender.sendto(payload, str(path))
    except OSError:
        return False
    finally:
        sender.close()
    return True


class HookReceiver:
    """Exclusive per-pane Unix datagram receiver."""

    def __init__(self, pane_id: str, runtime_dir: Path | None = None) -> None:
        self._path = relay_socket_path(pane_id, runtime_dir)
        self._lock_path = self._path.with_suffix(".lock")
        self._socket: socket.socket | None = None
        self._lock_file: BinaryIO | None = None

    def __enter__(self) -> Self:
        # The lock is advisory and per-pane, and it exists so one monitor cannot
        # replace another monitor's socket. Binding unlinks the path first, so without
        # it a second monitor would silently steal the relay from the first, which
        # would then sit reading a socket nothing writes to. Recorded here because the
        # only written account of it lived in a superseded design plan.
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_file = self._lock_path.open("a+b")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            lock_file.close()
            raise MonitorError(
                f"a monitor is already watching {self._path.stem}"
            ) from error

        receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self._path.unlink(missing_ok=True)
            receiver.bind(str(self._path))
        except OSError:
            receiver.close()
            lock_file.close()
            raise
        self._lock_file = lock_file
        self._socket = receiver
        return self

    def receive(self, timeout: float) -> Observation | None:
        """Wait for one hook event or the next fallback-inspection deadline."""
        if self._socket is None:
            raise MonitorError("hook receiver is not open")
        self._socket.settimeout(timeout)
        try:
            raw = self._socket.recv(MAX_DATAGRAM_BYTES)
        except TimeoutError:
            return None
        return deserialize_observation(raw)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._path.unlink(missing_ok=True)
        if self._lock_file is not None:
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()
            self._lock_file = None


def arm_reminder(
    state: MonitorState,
    action: Observation,
    now: float,
) -> MonitorState:
    """Schedule an emitted action to be raised again, unless it is terminal."""
    if action.kind in {ObservationKind.CRASH, ObservationKind.BUSY}:
        return replace(state, reminder=None)
    return replace(
        state,
        reminder=Reminder(
            action=action,
            armed_at=now,
            due_at=now + REMINDER_BACKOFF_SECONDS[0],
        ),
    )


def due_reminder(
    state: MonitorState,
    now: float,
) -> tuple[MonitorState, Observation | None]:
    """Raise the pending action again once its interval has elapsed."""
    reminder = state.reminder
    if reminder is None or now < reminder.due_at:
        return state, None
    waited = now - reminder.armed_at
    if waited >= REMINDER_GIVE_UP_SECONDS:
        # Naming what was abandoned is what makes the give-up stick. Disarming alone is
        # not enough, because a busy frame followed by the same screen returning reaches
        # _ensure_reminder as a pending prompt that has lost its clock, which is exactly
        # the case that must get one back.
        raised = replace(reminder.action, waited_seconds=waited, final=True)
        abandoned = replace(
            state,
            reminder=None,
            abandoned_key=_correlation_of(reminder.action),
        )
        return abandoned, raised
    step = min(reminder.step + 1, len(REMINDER_BACKOFF_SECONDS) - 1)
    rearmed = Reminder(
        action=reminder.action,
        armed_at=reminder.armed_at,
        due_at=now + REMINDER_BACKOFF_SECONDS[step],
        step=step,
    )
    raised = replace(reminder.action, waited_seconds=now - reminder.armed_at)
    return replace(state, reminder=rearmed), raised


def _humanise_wait(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h{minutes % 60:02d}m"


def _emit(pane_id: str, action: Observation) -> None:
    labels = {
        ObservationKind.APPROVAL: "NEEDS APPROVAL",
        ObservationKind.QUESTION: "QUESTION",
        ObservationKind.DONE: "DONE",
        ObservationKind.CRASH: "CRASH",
    }
    parts = []
    if action.detail:
        parts.append(action.detail)
    if action.kind is ObservationKind.DONE:
        # A finished pane is not an all-clear. It is the moment to decide what happens
        # to its context, and the moment the numbered-prompt loop expects a clear.
        parts.append("compact, clear, or quit?")
    if action.waited_seconds is not None:
        parts.append(f"still waiting {_humanise_wait(action.waited_seconds)}")
    if action.final:
        parts.append("no further reminders")
    detail = f": {' | '.join(parts)}" if parts else ""
    print(f"codex {pane_id} — {labels[action.kind]}{detail}", flush=True)


def _ensure_reminder(
    state: MonitorState,
    observation: Observation,
    now: float,
) -> MonitorState:
    """Give the announced prompt its clock back when a busy frame took it away."""
    if state.reminder is not None:
        return state
    correlation_key = _correlation_of(observation)
    # Only the thing most recently announced. Anything else either was never introduced,
    # so a "still waiting" line about it would be the first the reader heard of it, or
    # has had its hour and been let go.
    if correlation_key != state.last_correlation_key:
        return state
    if correlation_key == state.abandoned_key:
        return state
    return arm_reminder(state, observation, now)


def _apply_observation(
    state: MonitorState,
    observation: Observation,
    pane_id: str,
    now: float,
) -> tuple[MonitorState, bool]:
    transition = advance(state, observation)
    if transition.action is None:
        return _ensure_reminder(transition.state, observation, now), False
    _emit(pane_id, transition.action)
    if transition.action.kind is ObservationKind.CRASH:
        return transition.state, True
    return arm_reminder(transition.state, transition.action, now), False


def _try_discover(caller_pane: str) -> PaneRef | None:
    try:
        return discover_codex_pane(caller_pane)
    except MonitorError:
        return None


def run_monitor(
    caller_pane: str,
    *,
    poll_seconds: float,
    tail_lines: int,
    miss_limit: int,
) -> int:
    """Run the same-window monitor until cancellation or terminal failure."""
    try:
        target = discover_codex_pane(caller_pane)
    except MonitorError as error:
        print(f"codex monitor: {error}", file=sys.stderr)
        return 2

    tracker = TopologyTracker(target, miss_limit)
    state = MonitorState()
    try:
        with HookReceiver(target.pane_id) as receiver:
            while True:
                candidate = _try_discover(caller_pane)
                snapshot: Observation | None = None
                if candidate == tracker.target:
                    try:
                        snapshot = capture_snapshot(target.pane_id, tail_lines)
                    except MonitorError:
                        candidate = None

                topology = tracker.observe(candidate)
                tracker = topology.tracker
                if topology.crash is not None:
                    _emit(target.pane_id, topology.crash)
                    return 1

                if snapshot is not None:
                    state, crashed = _apply_observation(
                        state,
                        snapshot,
                        target.pane_id,
                        time.monotonic(),
                    )
                    if crashed:
                        return 1

                # Raise anything still pending before blocking on the next event, so a
                # quiet pane reports itself rather than reading as "nothing wrong".
                state, reminder = due_reminder(state, time.monotonic())
                if reminder is not None:
                    _emit(target.pane_id, reminder)

                hook_observation = receiver.receive(poll_seconds)
                if hook_observation is not None:
                    state, crashed = _apply_observation(
                        state,
                        hook_observation,
                        target.pane_id,
                        time.monotonic(),
                    )
                    if crashed:
                        return 1
    except (MonitorError, OSError) as error:
        print(f"codex monitor: {error}", file=sys.stderr)
        return 2


def run_hook() -> int:
    """Relay one hook payload without delaying or speaking to Codex."""
    pane_id = os.environ.get("TMUX_PANE")
    if pane_id is None:
        return 0
    raw = sys.stdin.buffer.read(MAX_HOOK_BYTES + 1)
    if len(raw) > MAX_HOOK_BYTES:
        while sys.stdin.buffer.read(64 * 1024):
            pass
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0
    observation = normalize_hook(payload)
    if observation is not None:
        send_hook_observation(observation, pane_id)
    return 0


def _positive_float(raw: str) -> float:
    value = float(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return value


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return value


def _caller_pane() -> str:
    """Return this process's own pane ID, or fail with a clear reason."""
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        raise MonitorError("TMUX_PANE is unset; run this from Claude's tmux pane")
    return pane


def joined_pane() -> str:
    """Return the joined Codex pane ID under the same-window uniqueness rule."""
    return discover_codex_pane(_caller_pane()).pane_id


def pane_tail(lines: int) -> str:
    """Return the joined pane's non-blank tail, for triaging before acting."""
    captured = run_command(("tmux", "capture-pane", "-p", "-t", joined_pane()))
    kept = [line for line in captured.splitlines() if line.strip()]
    return "\n".join(kept[-lines:])


def spawn_pane(label: str | None = None) -> str:
    """Open a Codex pane beside this one, refusing when one already runs."""
    pane = _caller_pane()
    try:
        existing = joined_pane()
    except NoCodexPaneError:
        existing = ""
    if existing:
        raise MonitorError(f"Codex already runs at {existing}; close it first")
    cwd = run_command(
        ("tmux", "display-message", "-p", "-t", pane, "#{pane_current_path}")
    ).strip()
    pane_id = run_command(
        (
            "tmux",
            "split-window",
            "-h",
            "-t",
            pane,
            "-c",
            cwd,
            "-P",
            "-F",
            "#{pane_id}",
            CODEX_SPAWN_COMMAND,
        )
    ).strip()
    pane_label = label or Path(cwd).name or "codex"
    run_command(
        (
            "tmux",
            "set-option",
            "-p",
            "-t",
            pane_id,
            CODEX_LABEL_OPTION,
            pane_label,
        )
    )
    return pane_id


def pane_status(pane_id: str) -> str:
    """Return the pane's tmux title, which carries Codex's status line."""
    return run_command(
        ("tmux", "display-message", "-p", "-t", pane_id, "#{pane_title}")
    ).strip()


SGR = re.compile(r"\x1b\[([0-9;]*)m")
FAINT_ON, FAINT_OFF, RESET = 2, 22, 0
EXTENDED_COLOUR = {38, 48, 58}


def _sets_faint(params: str) -> bool | None:
    """Return the faint state this SGR sequence establishes, or None to keep it.

    Extended-colour selectors carry their own parameters, and a truecolor
    sequence such as `48;2;65;69;76` contains a literal 2 that means colour
    space, not faint. Consuming those parameters is what keeps a background
    colour from reading as dimmed placeholder text.
    """
    values = [int(value) for value in params.split(";") if value.isdigit()]
    state: bool | None = None
    index = 0
    while index < len(values):
        value = values[index]
        if value in EXTENDED_COLOUR and index + 1 < len(values):
            index += 2 if values[index + 1] == 5 else 4
            continue
        if value == FAINT_ON:
            state = True
        elif value in {FAINT_OFF, RESET}:
            state = False
        index += 1
    return state


def visible_text(line: str, *, keep_faint: bool) -> str:
    """Return the line's printable text, optionally dropping faint spans."""
    shown: list[str] = []
    faint = False
    cursor = 0
    for match in SGR.finditer(line):
        if not faint or keep_faint:
            shown.append(line[cursor : match.start()])
        cursor = match.end()
        state = _sets_faint(match.group(1))
        if state is not None:
            faint = state
    if not faint or keep_faint:
        shown.append(line[cursor:])
    return "".join(shown)


def _composer_text(snapshot: str) -> str | None:
    """Return what the composer holds, or None when no composer is on screen.

    Codex renders its composer hint faint, so faint spans are dropped before the
    line is read. Reading the hint as an unfinished message blocked every send
    on 2026-07-23.
    """
    prompt_lines = [
        stripped
        for line in snapshot.splitlines()
        if (stripped := visible_text(line, keep_faint=False).lstrip()).startswith(
            PROMPT_MARKER
        )
    ]
    if not prompt_lines:
        return None
    return prompt_lines[-1].removeprefix(PROMPT_MARKER).strip()


def _composer_is_empty(snapshot: str) -> bool:
    """Report whether the composer holds typed text.

    A snapshot with no composer at all is not empty: it is a pane that does not
    look the way this code assumes, which is a reason to refuse rather than send.
    """
    return _composer_text(snapshot) == ""


def _plain(snapshot: str) -> str:
    """Strip the escape sequences from a coloured capture, keeping every character."""
    return "\n".join(
        visible_text(line, keep_faint=True) for line in snapshot.splitlines()
    )


_CONTEXT_METER = re.compile(r"Context\s+(\d{1,3})%")
_SESSION_ID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_COMPLETION = re.compile(r"^\s{1,4}(/[a-z][a-z0-9-]*)\s{2,}\S")


def context_left(content: str) -> int | None:
    """Return the percentage of context Codex reports remaining, if it is on screen.

    The footer reads `Context N% left` and is truncated at the pane width, so a
    narrow pane shows `Context 50% …` with the word cut off. The number arrives
    before the cut in both widths observed on 2026-08-01, and the word is
    therefore not required. None means the meter could not be read, which is a
    different answer from a reading that cleared the floor.
    """
    readings = _CONTEXT_METER.findall(_plain(content))
    return int(readings[-1]) if readings else None


def session_identity(title: str) -> str | None:
    """Return the Codex session id carried in the pane title.

    `/clear` starts a new session and the id changes with it, which is what
    confirms a clear afterwards. It is found by its shape because the title drops
    its `weekly` segment while Codex restarts, so counting separators reads the
    wrong field at exactly the moment the answer matters.
    """
    found = _SESSION_ID.search(title)
    return found[0] if found else None


def slash_completions(content: str) -> list[str]:
    """Return the commands the composer's completion list is currently offering.

    Typing `/` opens the list, and a partial command leaves the wrong entry
    selected: `/c` offers `/compact`, `/copy`, `/clear` in that order with
    `/compact` highlighted, so Enter compacts a pane meant to be cleared. Typing
    the command in full narrows the list to one entry, which is the state this
    reading exists to confirm.

    The selected entry is drawn bold and coloured while the rest are faint, so the
    escape sequences are stripped here rather than by each caller: reading the list
    from a faint-dropped view would delete every entry but the highlighted one, and
    the highlight is exactly what must not be trusted.
    """
    return [
        found[1]
        for line in _plain(content).splitlines()
        if (found := _COMPLETION.match(line)) is not None
    ]


def selected_completion(content: str) -> str | None:
    """Return the completion Enter would take, read from Codex's own highlighting.

    Narrowing cannot be what Enter is gated on, because a command typed in full does
    not always leave one entry: `/status` still lists `/statusline` beside it. What
    always holds is that Codex draws the selected entry's description at full
    brightness and leaves every other description faint, so dropping the faint spans
    strips the unselected rows of everything past their command and only the
    highlighted row still reads as a completion.
    """
    highlighted = [
        found[1]
        for line in content.splitlines()
        if (found := _COMPLETION.match(visible_text(line, keep_faint=False)))
        is not None
    ]
    return highlighted[0] if len(highlighted) == 1 else None


def _preflight_pane(pane_id: str) -> tuple[str, str]:
    """Return the pane's title and coloured snapshot once it is safe to type into.

    The approval check is here rather than left to the operator because every
    keystroke answers whatever dialog is on screen, and a dialog leaves the title
    `Ready` and the composer empty, so the two older guards both pass over the one
    state where typing is most destructive.
    """
    title = pane_status(pane_id)
    if re.search(r"\bready\b", title, re.IGNORECASE) is None:
        raise MonitorError(f"joined Codex pane {pane_id} is not Ready: {title!r}")
    snapshot = run_command(("tmux", "capture-pane", "-p", "-e", "-t", pane_id))
    content = _plain(snapshot)
    if _approval_is_pending("\n".join(content.splitlines()[-12:])):
        raise MonitorError(
            f"joined Codex pane {pane_id} holds a pending approval, and any keystroke "
            f"would answer it; clear it with --approve or read it with --tail"
        )
    composer = _composer_text(snapshot)
    if composer is None:
        # Codex sizes its TUI to the pane, so a short pane draws no composer at
        # all. That is unreadable rather than full, and reporting it as full
        # sends the reader hunting for typed text that was never there: on
        # 2026-08-09 a 127x5 pane produced "composer is not empty" and cost an
        # hour, while a 182x41 pane of the same build drew its composer and
        # passed. No capture flag recovers this, because the composer was never
        # drawn and so is not in the scrollback either.
        # Height and the window's pane count come back in one call, because the
        # usual cause is layout pressure rather than a deliberately short pane:
        # panes get squeezed when a window accumulates agent panes.
        geometry = run_command(
            (
                "tmux",
                "display-message",
                "-p",
                "-t",
                pane_id,
                "#{pane_height} #{window_panes}",
            )
        ).strip()
        height, _, panes = geometry.partition(" ")
        raise MonitorError(
            f"no composer drawn on joined Codex pane {pane_id} ({height} lines "
            f"tall, sharing its window with {panes} panes), so its contents "
            f"cannot be read; close a pane or re-run the layout to give it "
            f"height, or inspect with --tail"
        )
    if composer:
        raise MonitorError(
            f"joined Codex pane {pane_id} composer holds {composer!r}; "
            f"inspect with --tail"
        )
    return title, snapshot


def _check_context_floor(pane_id: str, snapshot: str, *, under_floor: bool) -> None:
    """Refuse to dispatch into a pane with too little context left to hold the answer.

    An unreadable meter refuses too. Passing on it would be the absence-read-as-a-pass
    this repo keeps paying for, and the meter was on screen at both pane widths
    measured on 2026-08-01, so an unreadable one means the pane is not rendering the
    way this code assumes rather than that all is well.

    Width was the wrong variable to have measured. Height is what removes the
    meter: on 2026-08-09 a 127x5 codex pane captured five lines of status bar
    holding no `Context` meter at all, while a 182x41 pane of the same build
    rendered one. That case no longer reaches here, because `_preflight_pane`
    runs first and refuses a pane too short to draw its composer, but the
    justification above should not be read as covering a geometry it never
    tested.
    """
    if under_floor:
        return
    reading = context_left(snapshot)
    if reading is None:
        raise MonitorError(
            f"could not read the context meter on {pane_id}, so the {
                CONTEXT_FLOOR_PERCENT
            }% floor cannot be checked; inspect with --tail, or pass --under-floor "
            f"once a human has ruled"
        )
    if reading < CONTEXT_FLOOR_PERCENT:
        raise MonitorError(
            f"context {reading}% left on {pane_id} is below the "
            f"{CONTEXT_FLOOR_PERCENT}% floor; run --compact, or --clear and restate "
            f"the prompt, or pass --under-floor once a human has ruled"
        )


_PASTED_PLACEHOLDER = re.compile(r"\[Pasted Content (\d+) chars\]")


def _confirm_paste(pane_id: str, message: str) -> None:
    """Refuse to submit a paste the composer counts as a different message.

    A paste too long for the composer is drawn as `[Pasted Content N chars]`,
    and N is a count the sender already holds, so comparing the two is the one
    cheap check a partial paste cannot pass. Codex's counting of non-ASCII has
    not been measured, so a count matching either the character length or the
    UTF-8 byte length is accepted. A message short enough to be drawn literally
    has no placeholder to read, which is why absence is not a failure here and
    submission is confirmed separately.
    """
    time.sleep(SUBMIT_POLL_SECONDS)
    snapshot = run_command(("tmux", "capture-pane", "-p", "-t", pane_id))
    found = _PASTED_PLACEHOLDER.search(snapshot)
    if found is None:
        return
    counted = int(found[1])
    if counted in {len(message), len(message.encode())}:
        return
    raise MonitorError(
        f"composer on {pane_id} holds {counted} chars where the message is "
        f"{len(message)}, so the paste is partial; inspect with --tail"
    )


def _submitted(pane_id: str) -> bool:
    """Report whether the composer has accepted and cleared our message.

    Both signals are positive evidence of a submission. Hunting the message's
    own text on screen and calling its absence a clear is not, because a paste
    too long for the composer is drawn as `[Pasted Content N chars]`, so text
    that was never displayed reads exactly like text that submitted. Verified
    against a live pane on 2026-07-31, where a 1584-character paste sat unsent
    in the composer and the old check called it submitted on the first poll.
    """
    for _ in range(SUBMIT_POLLS):
        time.sleep(SUBMIT_POLL_SECONDS)
        if "Working" in pane_status(pane_id):
            return True
        snapshot = run_command(("tmux", "capture-pane", "-p", "-e", "-t", pane_id))
        if _composer_is_empty(snapshot):
            return True
    return False


def send_message(pane_id: str, message: str, *, under_floor: bool = False) -> str:
    """Paste one message into the joined pane and confirm it submitted.

    Bracketed paste keeps embedded newlines as soft newlines rather than
    premature Enters. The Codex composer sometimes swallows the first Enter
    after a paste, so submission is confirmed rather than assumed.
    """
    if not message:
        raise MonitorError("refusing to send an empty message")
    _, snapshot = _preflight_pane(pane_id)
    _check_context_floor(pane_id, snapshot, under_floor=under_floor)
    load_argv: Command = ("tmux", "load-buffer", "-b", "codex-send", "-")
    subprocess.run(  # argv is fixed above; text arrives on stdin.
        load_argv,
        input=message,
        text=True,
        check=True,
    )
    run_command(("tmux", "paste-buffer", "-b", "codex-send", "-t", pane_id, "-p", "-d"))
    _confirm_paste(pane_id, message)
    for _ in range(SUBMIT_ATTEMPTS):
        run_command(("tmux", "send-keys", "-t", pane_id, "Enter"))
        if _submitted(pane_id):
            return f"submitted to {pane_id}"
    raise MonitorError(
        f"not submitted after {SUBMIT_ATTEMPTS} Enter attempts; inspect {pane_id}"
    )


def approve_pending() -> str:
    """Answer the joined pane's pending approval, and report what Codex then did.

    A dialog is a select list rather than the composer, so this needs neither
    the literal-then-Enter split nor the `Ready` preflight that `send_message`
    runs, and the guard is instead `approval_choice` refusing anything that is
    not a live dialog. The cleared screen is then confirmed, because a keypress
    can race the dialog and "approved" on screen is not evidence that anything
    ran. Clearing the dialog still says nothing about the outcome, which is the
    whole reason for approving, so the verb waits a bounded while for Codex to
    draw something and carries back the first thing it says. A pane that has
    stayed silent by then is reported as still working rather than guessed at.
    """
    pane_id = joined_pane()
    capture = ("tmux", "capture-pane", "-p", "-t", pane_id)
    content = run_command(capture)
    choice = approval_choice(content)
    command = _approval_material(content)
    seen = _bullet_texts(content)
    run_command(("tmux", "send-keys", "-t", pane_id, choice))
    for _ in range(SUBMIT_POLLS):
        time.sleep(SUBMIT_POLL_SECONDS)
        if not _approval_is_pending(run_command(capture)):
            break
    else:
        raise MonitorError(
            f"key {choice!r} did not clear the dialog on {pane_id}; inspect with --tail"
        )
    for _ in range(RESPONSE_POLLS):
        reply = _first_new_message(seen, run_command(capture))
        if reply:
            return f"approved on {pane_id}: {command}\n{reply}"
        time.sleep(SUBMIT_POLL_SECONDS)
    return f"approved on {pane_id}: {command}\nstill working; nothing reported yet"


def _clear_composer(pane_id: str) -> None:
    """Empty the composer, so a refused command does not block the next send."""
    run_command(("tmux", "send-keys", "-t", pane_id, "C-a"))
    run_command(("tmux", "send-keys", "-t", pane_id, "C-k"))


def _confirm_selection(pane_id: str, snapshot: str, command: str) -> None:
    """Refuse to submit unless Enter would take the command that was asked for.

    The completion list is the hazard rather than the composer text, because Enter
    takes the highlight rather than the typing, and `/c` leaves `/compact`
    highlighted, so a `/clear` typed one character short compacts instead. The gate
    is therefore the highlight, not the list having narrowed to one entry: typing a
    command in full does not always narrow it, since `/status` still lists
    `/statusline` beside itself.
    """
    typed = _composer_text(snapshot)
    selected = selected_completion(snapshot)
    if typed == command and selected == command:
        return
    _clear_composer(pane_id)
    offered = slash_completions(snapshot)
    raise MonitorError(
        f"refusing to submit {command} on {pane_id}: composer holds {typed!r} and "
        f"Enter would take {selected or 'nothing recognisable'} out of "
        f"{offered or 'an empty list'}"
    )


def _wait_ready(pane_id: str) -> str | None:
    """Wait for the pane to come back to `Ready`, or report that it never did.

    Both context verbs leave Codex busy for a while, a clear because it restarts the
    session and its MCP servers and a compaction because it is a model call over the
    whole transcript. Returning the moment the effect is visible hands back a pane
    that the next dispatch then refuses as not Ready, which costs a supervisor round
    to discover something this call already knew.
    """
    for _ in range(SETTLE_POLLS):
        title = pane_status(pane_id)
        if re.search(r"\bready\b", title, re.IGNORECASE) is not None:
            return title
        time.sleep(SUBMIT_POLL_SECONDS)
    return None


# The panel's own wording. A second model's allowance is reported beneath the first and
# carries a name in front of `Weekly limit:`, so the anchor keeps the primary one.
_WEEKLY_LIMIT = re.compile(
    r"^[\s│|]*Weekly limit:\s*(?:\[[^\]]*\]\s*)?(\d{1,3})%\s*left",
    re.MULTILINE,
)
_RESETS = re.compile(r"\(resets\s+([^)]+?)\)")


def weekly_quota(
    content: str,
    *,
    below: str | None = None,
) -> tuple[int, str | None] | None:
    """Return the weekly allowance left and when it resets, from a `/status` panel.

    A percentage on its own cannot say whether the burn is on track, because half the
    allowance left on day two is a problem and the same figure on day six is fine. The
    reset is the half of that answer the pane title does not carry, which is the whole
    reason this reads the panel rather than the title.

    `below` names a command whose echo the panel must sit under. Codex prints the
    submitted command on its own line and draws the panel beneath it, and an answered
    `/status` stays on screen afterwards, so the echo is what separates the panel this
    invocation drew from the one the last invocation left behind. Counting panels
    cannot do it, because drawing a new one scrolls the older one off the visible
    capture, so the count goes from one to one and a good second reading is refused.
    Observed on pane %58, 2026-08-01.

    Only the figures are returned. The panel also names the signed-in account, and the
    quota question has no use for it.
    """
    lines = _plain(content).splitlines()
    start = 0
    if below is not None:
        echoes = [index for index, line in enumerate(lines) if line.strip() == below]
        if not echoes:
            return None
        start = echoes[-1] + 1
    for index in range(start, len(lines)):
        found = _WEEKLY_LIMIT.match(lines[index])
        if found is None:
            continue
        window = " ".join(lines[index : index + 3])
        resets = _RESETS.search(window)
        return int(found[1]), resets[1].strip() if resets else None
    return None


def _confirm_quota(pane_id: str) -> str:
    """Wait for the panel Codex drew for this invocation and read its figures.

    The pane state is reported alongside them for the same reason the other two verbs
    report it: a caller left wondering whether the pane can take a prompt has to ask,
    and that round is the one the verb exists to save.
    """
    capture: Command = ("tmux", "capture-pane", "-p", "-e", "-t", pane_id)
    for _ in range(RESPONSE_POLLS):
        reading = weekly_quota(run_command(capture), below="/status")
        if reading is not None:
            left, resets = reading
            when = f", resets {resets}" if resets else ", reset date not on screen"
            state = "Ready" if _wait_ready(pane_id) is not None else "still working"
            return f"quota on {pane_id}: weekly {left}% left{when}; {state}"
        time.sleep(SUBMIT_POLL_SECONDS)
    raise MonitorError(f"{pane_id} drew no status panel; inspect with --tail")


def _settled_meter(pane_id: str) -> int | None:
    """Read the context meter once Codex has finished redrawing its footer.

    The footer is missing for a moment after the title reports `Ready`: a cleared
    pane prints its token-usage summary and its resume line first, and only then
    redraws. A single read lands in that gap and reports a meter that is on screen a
    second later, which was observed on pane %57 on 2026-08-01 turning a clear that
    had worked into one reported as unreadable.
    """
    capture: Command = ("tmux", "capture-pane", "-p", "-e", "-t", pane_id)
    for _ in range(SUBMIT_POLLS):
        left = context_left(run_command(capture))
        if left is not None:
            return left
        time.sleep(SUBMIT_POLL_SECONDS)
    return None


def _confirm_clear(pane_id: str, previous_id: str) -> str:
    """Confirm a clear by the session id rotating, which only `/clear` does."""
    rotated: str | None = None
    for _ in range(RESPONSE_POLLS):
        current = session_identity(pane_status(pane_id))
        if current is not None and current != previous_id:
            rotated = current
            break
        time.sleep(SUBMIT_POLL_SECONDS)
    if rotated is None:
        raise MonitorError(
            f"session {previous_id} is still current on {pane_id}, so /clear did not "
            f"run; inspect with --tail"
        )
    cleared = f"cleared {pane_id}: session {previous_id} -> {rotated}"
    if _wait_ready(pane_id) is None:
        return f"{cleared}; still starting, not Ready yet"
    left = _settled_meter(pane_id)
    meter = f"context {left}% left" if left is not None else "meter unreadable"
    return f"{cleared}; Ready, {meter}"


def _confirm_compact(pane_id: str, before: int | None, seen: set[str]) -> str:
    """Confirm a compaction by Codex's own marker and then by the settled meter.

    Waiting for the marker rather than for a `Ready` title is what keeps this from
    reading the pane before the compaction has run, since Codex is briefly still
    Ready after Enter. The marker alone is not the verdict, because the failure this
    guards against is Codex reporting success while the meter falls: a keep/drop brief
    took a live pane from 21% to 18% on 2026-07-28 and said it had compacted.

    The meter is then read from a settled pane rather than from the screen carrying
    the marker. Codex draws the marker before the footer catches up, so the earlier
    figure is one that is about to change, and reading it there reports a compaction
    that worked as one that cost context.
    """
    capture: Command = ("tmux", "capture-pane", "-p", "-e", "-t", pane_id)
    marked = False
    for _ in range(SETTLE_POLLS):
        content = _plain(run_command(capture))
        if any(
            "context compacted" in text.casefold()
            for text in _bullet_texts(content) - seen
        ):
            marked = True
            break
        time.sleep(SUBMIT_POLL_SECONDS)
    if not marked:
        raise MonitorError(
            f"{pane_id} never reported that it compacted; inspect with --tail"
        )

    settled = _wait_ready(pane_id)
    after = _settled_meter(pane_id)
    if after is None:
        raise MonitorError(
            f"{pane_id} reports it compacted, but the meter is unreadable, so "
            f"nothing confirms it; inspect with --tail"
        )
    if before is not None and after < before:
        raise MonitorError(
            f"{pane_id} reports it compacted while context fell from "
            f"{before}% to {after}% left, which is what a task does rather "
            f"than a compaction; inspect with --tail"
        )
    state = "Ready" if settled is not None else "still working"
    return f"compacted {pane_id}: context {before}% -> {after}% left; {state}"


def run_slash_command(command: str) -> str:
    """Type one slash command into the joined composer and confirm what it did.

    The command goes in the way the composer accepts it, as keystrokes on their own
    line, typed and confirmed before Enter is a separate call.
    """
    if command not in SLASH_COMMANDS:
        offered = ", ".join(SLASH_COMMANDS)
        raise MonitorError(
            f"unsupported slash command {command!r}; this sends {offered}"
        )
    pane_id = joined_pane()
    title, snapshot = _preflight_pane(pane_id)
    # Deliberately no context-floor check: these are the two verbs that relieve it,
    # and gating them would leave an exhausted pane with no way back.
    previous_id = session_identity(title)
    if command == "/clear" and previous_id is None:
        raise MonitorError(
            f"no session id in the title of {pane_id}, so a clear could not be "
            f"confirmed: {title!r}"
        )
    before = context_left(snapshot)
    seen = _bullet_texts(_plain(snapshot))

    run_command(("tmux", "send-keys", "-t", pane_id, "-l", command))
    time.sleep(SUBMIT_POLL_SECONDS)
    typed = run_command(("tmux", "capture-pane", "-p", "-e", "-t", pane_id))
    _confirm_selection(pane_id, typed, command)
    run_command(("tmux", "send-keys", "-t", pane_id, "Enter"))

    if command == "/clear":
        # previous_id is not None here; the guard above returned otherwise.
        return _confirm_clear(pane_id, cast("str", previous_id))
    if command == "/status":
        return _confirm_quota(pane_id)
    return _confirm_compact(pane_id, before, seen)


def send_prompt(prompt_file: str, *, under_floor: bool = False) -> str:
    """Send the standard ping for a numbered prompt file.

    The ping states no write scope. Each prompt declares its own output
    contract, because a drafting stage writes one document under
    `codex-prompts/out/` while a code phase writes source, tests, and generated
    data into a worktree, and a ping asserting one would contradict the other,
    which is exactly what happened on 2026-07-23. It does carry the standing
    instruction (`CODEX_PING_INSTRUCTION`) to ask one pointed question rather
    than guess when anything is unclear and to surface decisions for the
    supervisor to document, so a bare "carry out exactly" never reads as "do
    not ask" (Brian, 2026-07-24).
    """
    path = Path(prompt_file)
    if not path.is_file():
        raise MonitorError(f"prompt file does not exist: {path}")
    ping = (
        f"Read {path.as_posix()} and carry out that task exactly. "
        f"{CODEX_PING_INSTRUCTION}"
    )
    result = send_message(joined_pane(), ping, under_floor=under_floor)
    return f"{result}: {path.name}"


def run_verb(args: argparse.Namespace) -> int | None:
    """Run a one-shot verb, or return None to fall through to the monitor."""
    if args.resolve:
        print(joined_pane())
    elif args.spawn:
        print(spawn_pane(args.label))
    elif args.send is not None:
        print(send_prompt(args.send, under_floor=args.under_floor))
    elif args.tail is not None:
        print(pane_tail(args.tail))
    elif args.status:
        print(pane_status(joined_pane()))
    elif args.message is not None:
        text = sys.stdin.read() if args.message == "-" else args.message
        print(send_message(joined_pane(), text, under_floor=args.under_floor))
    elif args.approve:
        print(approve_pending())
    elif args.clear:
        print(run_slash_command("/clear"))
    elif args.compact:
        print(run_slash_command("/compact"))
    elif args.quota:
        print(run_slash_command("/status"))
    else:
        return None
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit only actionable events from joined Codex",
    )
    parser.add_argument("--poll-seconds", type=_positive_float, default=8.0)
    parser.add_argument("--tail-lines", type=_positive_int, default=80)
    parser.add_argument("--miss-limit", type=_positive_int, default=2)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--hook", action="store_true", help=argparse.SUPPRESS)
    action.add_argument(
        "--resolve", action="store_true", help="print the joined Codex pane ID"
    )
    action.add_argument(
        "--spawn", action="store_true", help="open a Codex pane beside this one"
    )
    parser.add_argument(
        "--label",
        metavar="NAME",
        help="label a spawned pane (default: working-directory name)",
    )
    action.add_argument(
        "--approve",
        action="store_true",
        help="answer a pending approval and report what codex did next",
    )
    action.add_argument(
        "--clear",
        action="store_true",
        help=(
            "start codex on a fresh session, confirmed by the session id in the "
            "pane title changing"
        ),
    )
    action.add_argument(
        "--compact",
        action="store_true",
        help=(
            "have codex summarise its transcript, confirmed by its context meter "
            "going up rather than by what codex says it did"
        ),
    )
    action.add_argument(
        "--quota",
        action="store_true",
        help=("report how much of the weekly allowance is left and when it resets"),
    )
    parser.add_argument(
        "--under-floor",
        action="store_true",
        # The doubled sign is required: argparse expands `%` in a help string.
        help=(
            f"dispatch below the {CONTEXT_FLOOR_PERCENT}%% context floor; "
            f"for carrying a human ruling, not for getting past the refusal"
        ),
    )
    action.add_argument("--send", metavar="PROMPT_FILE", help="send one prompt file")
    action.add_argument(
        "--status", action="store_true", help="print the joined pane's status line"
    )
    action.add_argument(
        "--message", metavar="TEXT", help="send one literal message ('-' reads stdin)"
    )
    action.add_argument(
        "--tail",
        nargs="?",
        const=12,
        type=_positive_int,
        metavar="N",
        help="print the joined pane's non-blank tail (default 12 lines)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.hook:
        return run_hook()
    try:
        verb_status = run_verb(args)
    except MonitorError as error:
        print(f"codex monitor: {error}", file=sys.stderr)
        return 2
    if verb_status is not None:
        return verb_status
    caller_pane = os.environ.get("TMUX_PANE")
    if caller_pane is None:
        print(
            "codex monitor: TMUX_PANE is unset; run it from Claude's tmux pane",
            file=sys.stderr,
        )
        return 2
    return run_monitor(
        caller_pane,
        poll_seconds=args.poll_seconds,
        tail_lines=args.tail_lines,
        miss_limit=args.miss_limit,
    )


if __name__ == "__main__":
    raise SystemExit(main())
