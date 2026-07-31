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
SUBMIT_ATTEMPTS = 3
SUBMIT_POLLS = 4
SUBMIT_POLL_SECONDS = 1.0
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


def _approval_material(content: str) -> str:
    lines = content.splitlines()
    approval_indexes = [
        index
        for index, line in enumerate(lines)
        if re.search(
            r"would you like to run|press enter to confirm",
            line,
            re.IGNORECASE,
        )
    ]
    if not approval_indexes:
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("$ ") and len(stripped) > 2:
                return stripped[2:]
        return content

    last = approval_indexes[-1]
    nearby_lines = lines[max(0, last - 5) : min(len(lines), last + 4)]
    for line in reversed(nearby_lines):
        stripped = line.strip()
        if stripped.startswith("$ ") and len(stripped) > 2:
            return stripped[2:]
    return "\n".join(nearby_lines)


def _assistant_message(content: str) -> str:
    lines = content.splitlines()
    bullet_indexes = [
        index for index, line in enumerate(lines) if re.match(r"^\s*•(?:\s|$)", line)
    ]
    if bullet_indexes:
        start = bullet_indexes[-1]
        message_lines = [re.sub(r"^\s*•\s?", "", lines[start])]
        for line in lines[start + 1 :]:
            stripped = line.strip()
            if stripped.startswith((PROMPT_MARKER, "─")) or stripped.endswith(
                "context left"
            ):
                break
            if stripped and stripped != "? for shortcuts":
                message_lines.append(stripped)
        return _normalized("\n".join(message_lines))
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
_OPTION_KEY = re.compile(r"\(([A-Za-z]+)\)\s*$")
_AFFIRMATIVE = re.compile(r"yes\b", re.IGNORECASE)
_STANDING_GRANT = re.compile(
    r"ask again|don'?t ask|do not ask|always|approve all|every time|no longer ask",
    re.IGNORECASE,
)


def _approval_options(content: str) -> list[tuple[str, str]]:
    """Read the numbered choices from the last option list Codex drew.

    Codex draws the list either as one line carrying every option or as one
    option per line, so the block is collected by walking back from the foot of
    the pane through consecutive lines that open with a number, past the cursor
    marker where the selected line carries one. Requiring at least two options
    that count up from one keeps a numbered line inside the command being
    approved, or a version string sitting in the scrollback, from being read as
    the dialog.
    """
    block: list[tuple[str, str]] = []
    for line in reversed(content.splitlines()):
        body = _OPTION_LINE_LEAD.sub("", line)
        matches = (
            [(match[1], match[2].strip()) for match in _OPTION.finditer(body)]
            if _OPTION.match(body)
            else []
        )
        if matches:
            block[:0] = matches
        elif block:
            break
    counted = [number for number, _ in block]
    if len(block) < 2 or counted != [str(n) for n in range(1, len(block) + 1)]:
        return []
    return block


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


def advance(state: MonitorState, observation: Observation) -> Transition:
    """Emit each actionable observation once and keep all busy states silent."""
    if observation.kind is ObservationKind.BUSY:
        return Transition(
            MonitorState(
                seen_activity=True,
                emitted_keys=state.emitted_keys,
                last_correlation_key=state.last_correlation_key,
                last_action_scoped=state.last_action_scoped,
                # Busy means Codex is mid-turn, so nothing is waiting on the human and
                # a pending reminder would nag about a prompt already answered. Dropping
                # it cannot lose a live approval: classify_snapshot matches pending
                # approval text before falling through to busy, so a pane genuinely
                # waiting classifies as APPROVAL on every poll and re-arms.
                reminder=None,
            ),
            None,
        )
    if (
        observation.kind in {ObservationKind.QUESTION, ObservationKind.DONE}
        and not state.seen_activity
    ):
        return Transition(state, None)

    key = observation.key or _digest(observation.kind.value)
    correlation_key = observation.correlation_key or key
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
    detail = f": {' | '.join(parts)}" if parts else ""
    print(f"codex {pane_id} — {labels[action.kind]}{detail}", flush=True)


def _apply_observation(
    state: MonitorState,
    observation: Observation,
    pane_id: str,
    now: float,
) -> tuple[MonitorState, bool]:
    transition = advance(state, observation)
    if transition.action is None:
        return transition.state, False
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


def _composer_is_empty(snapshot: str) -> bool:
    """Report whether the composer holds typed text.

    Codex renders its composer hint faint, so faint spans are dropped before the
    line is judged. Reading the hint as an unfinished message blocked every send
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
        return False
    return not prompt_lines[-1].removeprefix(PROMPT_MARKER).strip()


def _preflight_send(pane_id: str) -> None:
    """Refuse to write unless the joined Codex composer is visibly ready."""
    title = pane_status(pane_id)
    if re.search(r"\bready\b", title, re.IGNORECASE) is None:
        raise MonitorError(f"joined Codex pane {pane_id} is not Ready: {title!r}")
    snapshot = run_command(("tmux", "capture-pane", "-p", "-e", "-t", pane_id))
    if not _composer_is_empty(snapshot):
        raise MonitorError(
            f"joined Codex pane {pane_id} composer is not empty; inspect with --tail"
        )


def _submitted(pane_id: str, probe: str) -> bool:
    """Report whether the composer has accepted and cleared our message."""
    for _ in range(SUBMIT_POLLS):
        time.sleep(SUBMIT_POLL_SECONDS)
        title = pane_status(pane_id)
        if "Working" in title:
            return True
        visible = run_command(("tmux", "capture-pane", "-t", pane_id, "-p"))
        if probe not in "\n".join(visible.splitlines()[-6:]):
            return True
    return False


def send_message(pane_id: str, message: str) -> str:
    """Paste one message into the joined pane and confirm it submitted.

    Bracketed paste keeps embedded newlines as soft newlines rather than
    premature Enters. The Codex composer sometimes swallows the first Enter
    after a paste, so submission is confirmed rather than assumed.
    """
    if not message:
        raise MonitorError("refusing to send an empty message")
    _preflight_send(pane_id)
    load_argv: Command = ("tmux", "load-buffer", "-b", "codex-send", "-")
    subprocess.run(  # argv is fixed above; text arrives on stdin.
        load_argv,
        input=message,
        text=True,
        check=True,
    )
    run_command(("tmux", "paste-buffer", "-b", "codex-send", "-t", pane_id, "-p", "-d"))
    probe = message.splitlines()[0][:40]
    for _ in range(SUBMIT_ATTEMPTS):
        run_command(("tmux", "send-keys", "-t", pane_id, "Enter"))
        if _submitted(pane_id, probe):
            return f"submitted to {pane_id}"
    raise MonitorError(
        f"not submitted after {SUBMIT_ATTEMPTS} Enter attempts; inspect {pane_id}"
    )


def approve_pending() -> str:
    """Answer the joined pane's pending approval with one keypress.

    A dialog is a select list rather than the composer, so this needs neither
    the literal-then-Enter split nor the `Ready` preflight that `send_message`
    runs; the guard is `approval_choice` refusing anything that is not a live
    dialog. The cleared screen is then confirmed, because a keypress can race
    the dialog and "approved" on screen is not evidence that anything ran.
    """
    pane_id = joined_pane()
    content = run_command(("tmux", "capture-pane", "-p", "-t", pane_id))
    choice = approval_choice(content)
    command = _approval_material(content)
    run_command(("tmux", "send-keys", "-t", pane_id, choice))
    for _ in range(SUBMIT_POLLS):
        time.sleep(SUBMIT_POLL_SECONDS)
        if not _approval_is_pending(
            run_command(("tmux", "capture-pane", "-p", "-t", pane_id))
        ):
            return f"approved on {pane_id}: {command}"
    raise MonitorError(
        f"key {choice!r} did not clear the dialog on {pane_id}; inspect with --tail"
    )


def send_prompt(prompt_file: str) -> str:
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
    result = send_message(joined_pane(), ping)
    return f"{result}: {path.name}"


def run_verb(args: argparse.Namespace) -> int | None:
    """Run a one-shot verb, or return None to fall through to the monitor."""
    if args.resolve:
        print(joined_pane())
    elif args.spawn:
        print(spawn_pane(args.label))
    elif args.send is not None:
        print(send_prompt(args.send))
    elif args.tail is not None:
        print(pane_tail(args.tail))
    elif args.status:
        print(pane_status(joined_pane()))
    elif args.message is not None:
        text = sys.stdin.read() if args.message == "-" else args.message
        print(send_message(joined_pane(), text))
    elif args.approve:
        print(approve_pending())
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
        help="answer a pending approval with one keypress",
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
