"""Fixture-only permission screen; launch Python with -P to avoid queue.py shadowing."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, TextArea

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.binding import BindingType
    from tmux_source import PaneSnapshot, TmuxSource

DIRECTORY = Path(__file__).resolve().parent
INPUT_QUIET_SECONDS = 0.75
ANSWER_READY_MESSAGE = "Ready: 1/2/3 + Enter → selected pane"
ANSWER_KEYS = frozenset({"1", "2", "3", "enter"})


class QueueClient:
    """Use the existing experiment CLI as the sole queue/decision owner."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir.resolve()

    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(DIRECTORY / "queue.py"),
                arguments[0],
                "--run-dir",
                str(self.run_dir),
                *arguments[1:],
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            cwd=DIRECTORY,
        )

    def records(self) -> list[dict]:
        result = self.command("list", "--json")
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)

    def decide(self, request_id: str, choice: str) -> subprocess.CompletedProcess[str]:
        return self.command(
            "decide",
            "--request",
            request_id,
            "--decision",
            choice,
            "--reason",
            f"Human {choice} via fixture-only experiment board",
        )


class DemoProducer:
    """Own harmless hook processes; their displayed commands are never executed."""

    def __init__(self, run_dir: Path, *, hold_seconds: float = 600):
        self.client = QueueClient(run_dir)
        self.hold_seconds = hold_seconds
        self.children: list[subprocess.Popen[str]] = []
        self.counter = 0

    def add(self) -> str:
        previous = {request["request_id"] for request in self.client.records()}
        self.counter += 1
        command = f"printf 'Demo fixture {self.counter}: never executed\\n'"
        if self.counter % 3 == 2:
            command += "\nprintf '[red]literal brackets[/red]\\n'"
        elif self.counter % 3 == 0:
            command += (
                "\nprintf '" + "Long input remains fully inspectable. " * 12 + "\\n'"
            )
        payload = {
            "hook_event_name": "PermissionRequest",
            "session_id": f"fixture-session-{self.counter:02}",
            "cwd": f"/fixture/project-{(self.counter - 1) % 3 + 1}",
            "tool_name": "Bash",
            "tool_input": {"command": command, "description": "Never executed"},
            "experiment_fixture": True,
            "session_label": ("Report preview", "Release notes", "Export sample")[
                (self.counter - 1) % 3
            ],
            "conversation_source": "generated-demo",
            "conversation": [
                {
                    "role": "user",
                    "content": (
                        "Please check the report preview before I share it.",
                        "Show me the release notes before we publish them.",
                        "Can you inspect the sample export format?",
                    )[(self.counter - 1) % 3],
                },
                {
                    "role": "assistant",
                    "content": (
                        "I'll start with a small preview "
                        "and keep the scope to that check."
                    ),
                },
                {
                    "role": "user",
                    "content": "Yes. Show me the request before running anything.",
                },
                {
                    "role": "assistant",
                    "content": (
                        "The complete request is below. "
                        "This generated demo never executes it."
                    ),
                },
            ],
        }
        child = subprocess.Popen(
            [
                sys.executable,
                str(DIRECTORY / "queue.py"),
                "hook",
                "--run-dir",
                str(self.client.run_dir),
                "--vendor",
                "claude",
                "--vendor-version",
                "fixture-demo",
                "--hold-seconds",
                str(self.hold_seconds),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=DIRECTORY,
        )
        self.children.append(child)
        if child.stdin is None:
            raise RuntimeError("Cannot connect the fixture hook's input pipe")
        child.stdin.write(json.dumps(payload))
        child.stdin.close()
        child.stdin = None
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            for request in self.client.records():
                if request["request_id"] not in previous:
                    return request["request_id"]
            if child.poll() is not None:
                _, error = child.communicate()
                raise RuntimeError(f"fixture hook failed to publish: {error}")
            time.sleep(0.01)
        raise RuntimeError("fixture hook did not publish within three seconds")

    def close(self) -> None:
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            child.communicate(timeout=3)

    def __enter__(self) -> DemoProducer:
        return self

    def __exit__(self, *_exception: object) -> None:
        self.close()


def fixture(request: dict) -> bool:
    return request.get("payload", {}).get("experiment_fixture") is True


def actionable(request: dict) -> bool:
    return (
        fixture(request)
        and request["state"] == "pending"
        and request["expires_monotonic_s"] > time.monotonic()
    )


def plain(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=True)[1:-1]


def state_label(request: dict) -> str:
    if not fixture(request):
        return "Live excluded"
    return {
        "pending": "Waiting for your demo answer",
        "decided": "Sending demo answer",
        "returned": "Demo answer sent",
        "expired": "Expired; answer unavailable",
        "retired": "Retired; answer unavailable",
        "unknown": "Unavailable; original request ended",
    }.get(request["state"], "Unavailable")


def project(request: dict) -> str:
    return plain(Path(str(request.get("cwd") or "unknown")).name)


def details(request: dict) -> str:
    tool_input = request["tool_input"]
    command = tool_input.get("command")
    if isinstance(command, str):
        displayed = "\n".join(plain(line) for line in command.split("\n"))
        content = f"COMMAND\n{displayed}"
        other_input = {
            key: value for key, value in tool_input.items() if key != "command"
        }
    else:
        content = "TOOL INPUT\n" + json.dumps(tool_input, ensure_ascii=True, indent=2)
        other_input = {}
    content += (
        f"\n\nProject: {plain(request.get('cwd'))}"
        f"\nProvider: {plain(request['vendor'])}"
        f"\nSession: {plain(request['session_id'])}"
        f"\nState: {state_label(request)}"
        f"\nRequest: {request['request_id']}"
    )
    if other_input:
        content += "\n\nOTHER TOOL INPUT\n" + json.dumps(
            other_input, ensure_ascii=True, indent=2
        )
    return content


def session_key(request: dict) -> tuple[str, str]:
    return request["vendor"], str(request.get("session_id") or request["request_id"])


def conversation(request: dict) -> str:
    payload = request["payload"]
    turns = payload.get("conversation")
    if payload.get("conversation_source") != "generated-demo" or not isinstance(
        turns, list
    ):
        return "No generated conversation was supplied for this fixture."
    lines = []
    for turn in turns:
        if isinstance(turn, dict) and isinstance(turn.get("content"), str):
            role = plain(turn.get("role", "speaker")).capitalize()
            content = "\n".join(plain(line) for line in turn["content"].split("\n"))
            lines.append(f"{role}:\n{content}")
    return (
        "\n\n".join(lines) or "No generated conversation was supplied for this fixture."
    )


class PermissionBoard(App):
    TITLE = "Permission experiment"
    BINDINGS: ClassVar[list[BindingType]] = [
        ("a", "answer('allow')", "Approve demo"),
        ("d", "answer('deny')", "Deny demo"),
        ("s", "next_session", "Next session"),
        ("n", "new_fixture", "New demo request"),
        ("q", "quit", "Close demo"),
    ]
    CSS = """
    Screen { padding: 0 1; }
    #mode { height: 2; color: $warning; text-style: bold; }
    #session { height: 1; text-style: bold; }
    .section-label { height: 1; color: $text-muted; }
    #conversation { height: 1fr; min-height: 3; }
    #details { height: 1fr; min-height: 3; }
    #waiting { height: 1; }
    #actions { height: 3; }
    #actions Button { width: 1fr; min-width: 8; }
    #status { height: 1; }
    #keys { height: 2; }
    """

    def __init__(self, run_dir: Path, *, demo: bool = False):
        super().__init__()
        self.run_dir = run_dir
        self.client = QueueClient(run_dir)
        self.producer = DemoProducer(run_dir) if demo else None
        self.selected_id: str | None = None
        self.records: dict[str, dict] = {}
        self.resolved: set[str] = set()
        self.preferred_session: tuple[str, str] | None = None
        self.message = "Read the conversation and complete request; answer once."
        self.last_error = ""
        self.refreshing = False
        self.refresh_failed = False
        self.answering = False

    @property
    def session_groups(self) -> list[list[dict]]:
        grouped: dict[tuple[str, str], list[dict]] = {}
        for request in sorted(
            self.records.values(), key=lambda item: item["opened_monotonic_s"]
        ):
            if actionable(request) and request["request_id"] not in self.resolved:
                grouped.setdefault(session_key(request), []).append(request)
        return list(grouped.values())

    @property
    def pending_ids(self) -> list[str]:
        return [
            request["request_id"] for group in self.session_groups for request in group
        ]

    @property
    def waiting_count(self) -> int:
        return len(self.session_groups)

    def compose(self) -> ComposeResult:
        yield Static(
            "DEMO — generated conversations; commands are not executed\n"
            "Live sessions are excluded from this experiment.",
            markup=False,
            id="mode",
        )
        yield Static("Loading demo requests…", markup=False, id="session")
        yield Static(
            "CONVERSATION · generated example · Tab/arrows scroll",
            id="context-label",
            classes="section-label",
        )
        yield TextArea(read_only=True, id="conversation")
        yield Static(
            "COMPLETE REQUEST · Tab/arrows scroll",
            id="request-label",
            classes="section-label",
        )
        yield TextArea(read_only=True, id="details")
        yield Static("", markup=False, id="waiting")
        with Horizontal(id="actions"):
            yield Button("Approve [a]", id="allow", variant="success", disabled=True)
            yield Button("Deny [d]", id="deny", variant="error", disabled=True)
            yield Button("Next [s]", id="next", disabled=True)
            yield Button("New [n]", id="new", disabled=self.producer is None)
        yield Static(self.message, markup=False, id="status")
        yield Static(
            "a/d answer once · s next · n new · q close demo\n"
            "Tab focuses reading · Alt-Up/Down sessions (tmux)",
            markup=False,
            id="keys",
        )

    async def on_mount(self) -> None:
        self.context_view = self.query_one("#conversation", TextArea)
        self.detail_view = self.query_one("#details", TextArea)
        self.session_view = self.query_one("#session", Static)
        self.waiting_view = self.query_one("#waiting", Static)
        self.status_view = self.query_one("#status", Static)
        self.allow_button = self.query_one("#allow", Button)
        self.deny_button = self.query_one("#deny", Button)
        self.next_button = self.query_one("#next", Button)
        if self.producer is not None:
            for _ in range(3):
                await asyncio.to_thread(self.producer.add)
        await self.refresh_board()
        self.context_view.focus()
        self.set_interval(0.5, self.refresh_board)

    async def refresh_board(self) -> None:
        if self.refreshing:
            return
        self.refreshing = True
        try:
            snapshot = await asyncio.to_thread(self.client.records)
            self.refresh_failed = False
            present = {request["request_id"] for request in snapshot}
            for request_id, old in self.records.items():
                if request_id not in present:
                    old["state"] = "unknown"
            self.records.update(
                (request["request_id"], request) for request in snapshot
            )
            current = self.records.get(self.selected_id)
            observed_resolution = (
                current is not None
                and current["state"] in {"decided", "returned"}
                and not self.answering
                and not self.last_error
            )
            if observed_resolution:
                self.resolved.add(current["request_id"])
                self.selected_id = None
                self.preferred_session = session_key(current)
                self.message = (
                    "Demo answer received elsewhere; showing the next request."
                )
            groups = self.session_groups
            if self.selected_id is None and groups:
                chosen = next(
                    (
                        group
                        for group in groups
                        if session_key(group[0]) == self.preferred_session
                    ),
                    groups[0],
                )
                self.selected_id = chosen[0]["request_id"]
                self.preferred_session = None
            self.update_card()
            if observed_resolution:
                self.context_view.focus()
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            self.refresh_failed = True
            self.last_error = str(error)
            self.message = "Requests unavailable. Error below; answers disabled."
            self.update_card()
        finally:
            self.refreshing = False

    def update_card(self) -> None:
        request = self.records.get(self.selected_id)
        groups = self.session_groups
        if request is None:
            context = (
                "No demo approvals are waiting.\n"
                "Press n to create another generated conversation."
            )
            content = "No demo request is waiting for an answer."
            title = "No demo approvals waiting"
        else:
            context = conversation(request)
            content = details(request)
            label = request["payload"].get("session_label") or project(request)
            same_session = next(
                (
                    group
                    for group in groups
                    if session_key(group[0]) == session_key(request)
                ),
                [],
            )
            title = (
                f"{plain(label)} · {plain(request['vendor'])} demo · "
                f"{len(same_session)} request(s)"
            )
        if self.last_error:
            content += f"\n\nACTION ERROR\n{plain(self.last_error)}"
        if self.context_view.text != context:
            self.context_view.load_text(context)
        if self.detail_view.text != content:
            self.detail_view.load_text(content)
        self.session_view.update(title)
        next_groups = [
            group
            for group in groups
            if request is None or session_key(group[0]) != session_key(request)
        ]
        next_label = ""
        if next_groups:
            next_request = next_groups[0][0]
            next_label = " · Next: " + plain(
                next_request["payload"].get("session_label") or project(next_request)
            )
        self.waiting_view.update(
            f"{len(groups)} session(s) waiting · {len(self.pending_ids)} request(s)"
            + next_label
        )
        enabled = (
            request is not None
            and actionable(request)
            and not self.answering
            and not self.refresh_failed
        )
        self.allow_button.disabled = not enabled
        self.deny_button.disabled = not enabled
        self.next_button.disabled = self.answering or not groups
        self.status_view.update(self.message)

    async def action_answer(self, choice: str) -> None:
        request = self.records.get(self.selected_id)
        if self.answering:
            return
        if request is None or not actionable(request) or self.refresh_failed:
            self.message = (
                "Already answered or unavailable. Next shows another waiting session."
            )
            self.status_view.update(self.message)
            return
        request_id = request["request_id"]
        origin = session_key(request)
        self.answering = True
        self.update_card()
        try:
            result = await asyncio.to_thread(self.client.decide, request_id, choice)
            if result.returncode:
                self.last_error = result.stderr.strip()
                self.message = (
                    "Answer unavailable. s: next session; error below request."
                )
            else:
                self.resolved.add(request_id)
                self.last_error = ""
                self.message = "Demo approved." if choice == "allow" else "Demo denied."
                self.selected_id = None
                self.preferred_session = origin
            await self.refresh_board()
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            self.last_error = str(error)
            self.message = "Could not send answer. Error below; s moves on."
        finally:
            self.answering = False
            self.update_card()
            self.context_view.focus()

    async def action_next_session(self) -> None:
        if self.answering:
            return
        groups = self.session_groups
        request = self.records.get(self.selected_id)
        if groups:
            current_index = next(
                (
                    index
                    for index, group in enumerate(groups)
                    if request is not None
                    and session_key(group[0]) == session_key(request)
                ),
                -1,
            )
            group = groups[(current_index + 1) % len(groups)]
            self.selected_id = group[0]["request_id"]
        else:
            self.selected_id = None
        self.last_error = ""
        self.message = "Read this session's conversation and request, then answer once."
        self.update_card()
        self.context_view.focus()

    async def action_new_fixture(self) -> None:
        if self.producer is not None:
            await asyncio.to_thread(self.producer.add)
            self.message = (
                "New generated request added; the current conversation stays in place."
            )
            await self.refresh_board()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("allow", "deny"):
            await self.action_answer("allow" if event.button.id == "allow" else "deny")
        elif event.button.id == "next":
            await self.action_next_session()
        elif event.button.id == "new":
            await self.action_new_fixture()

    def on_unmount(self) -> None:
        if self.producer is not None:
            self.producer.close()


def source_identity(snapshot: PaneSnapshot) -> Text:
    content = Text()
    for span in snapshot.header_spans:
        content.append(
            str(span["text"]),
            Style(color=span["fg"], bgcolor=span["bg"], bold=span["bold"]),
        )
    if not content.plain:
        if getattr(snapshot, "thread_id", ""):
            content.append(
                "Codex · " + plain(Path(snapshot.cwd).name) + " · ", style="bold"
            )
        content.append(plain(snapshot.title) or "Source header unavailable")
    return content


def attention_key(
    snapshot: PaneSnapshot, observed_since: float | None
) -> tuple[int, bool, float, int, int]:
    rank = {"blocked": 0, "idle": 1, "running": 2, "unknown": 3}.get(snapshot.state, 3)
    return (
        rank,
        observed_since is None,
        -(observed_since or 0),
        snapshot.window_index,
        snapshot.pane_index,
    )


class PanePreferences:
    """Persist individual unknown-pane choices for a verified tmux pane lifetime."""

    def __init__(self, path: Path | None = None):
        config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        self.path = path or config / "permission-queue" / "panes.json"

    @staticmethod
    def identity(snapshot: PaneSnapshot) -> str:
        socket = getattr(snapshot, "socket_path", "")
        numbers = [
            getattr(snapshot, field, None)
            for field in (
                "server_pid",
                "server_start_ticks",
                "pane_pid",
                "pane_start_ticks",
            )
        ]
        if (
            not socket
            or not Path(socket).is_absolute()
            or any(type(number) is not int or number <= 0 for number in numbers)
        ):
            raise RuntimeError("Pane identity unavailable; cannot save this choice.")
        return json.dumps(
            [
                str(Path(socket).resolve()),
                numbers[0],
                numbers[1],
                snapshot.session_id,
                snapshot.pane_id,
                numbers[2],
                numbers[3],
            ]
        )

    def read(self) -> set[str]:
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            return set()
        except (OSError, ValueError) as error:
            raise RuntimeError(f"Cannot read pane choices: {error}") from error
        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("included"), list)
            or not all(isinstance(value, str) for value in data["included"])
        ):
            raise RuntimeError("Cannot read pane choices: unsupported file contents.")
        return set(data["included"])

    def includes(self, snapshot: PaneSnapshot) -> bool:
        try:
            identity = self.identity(snapshot)
        except RuntimeError:
            return False
        return identity in self.read()

    def set_included(self, snapshot: PaneSnapshot, included: bool) -> None:
        identity = self.identity(snapshot)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(str(self.path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            values = self.read()
            if included:
                values.add(identity)
            else:
                values.discard(identity)
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.path.parent, prefix=".panes-", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                try:
                    json.dump({"version": 1, "included": sorted(values)}, temporary)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                    temporary_path.replace(self.path)
                finally:
                    temporary_path.unlink(missing_ok=True)


class PanePicker(ModalScreen[str | None]):
    """Choose which currently unknown panes belong in this viewer."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("space", "toggle_pane", "Include / remove", priority=True),
        Binding("escape", "close_picker", "Back", priority=True),
    ]
    CSS = """
    PanePicker { padding: 0 1; background: $surface; }
    #picker-title, #picker-help, #picker-status { height: auto; }
    #pane-picker { height: 1fr; }
    """

    def __init__(self, panes: list[PaneSnapshot], preferences: PanePreferences):
        super().__init__()
        self.panes = panes
        self.preferences = preferences
        self.last_included: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("Add panes — unknown panes", id="picker-title", markup=False)
        yield Static("↑↓ choose · Space include / remove · Esc back", id="picker-help")
        yield DataTable(id="pane-picker", cursor_type="row", zebra_stripes=True)
        yield Static("", id="picker-status", markup=False)

    def on_mount(self) -> None:
        self.table = self.query_one(DataTable)
        self.table.add_column("Win.p", width=5)
        self.table.add_column("Project / task", width=max(12, self.size.width - 26))
        self.table.add_column("Included", width=10)
        self.render_choices()
        self.table.focus()

    def render_choices(self) -> None:
        selected = self.table.cursor_row
        self.table.clear()
        try:
            choices = self.preferences.read()
        except RuntimeError as error:
            choices = set()
            self.query_one("#picker-status", Static).update(plain(error))
        for pane in self.panes:
            try:
                included = self.preferences.identity(pane) in choices
            except RuntimeError:
                included = False
            self.table.add_row(
                f"{pane.window_index}.{pane.pane_index}",
                source_identity(pane),
                "Yes" if included else "No",
                key=pane.pane_id,
            )
        self.table.move_cursor(row=selected)
        if not self.panes:
            self.query_one("#picker-status", Static).update("No unknown panes found.")

    def action_toggle_pane(self) -> None:
        if not self.panes:
            return
        pane = self.panes[self.table.cursor_row]
        try:
            included = not self.preferences.includes(pane)
            self.preferences.set_included(pane, included)
            self.last_included = pane.pane_id if included else None
            self.render_choices()
            self.query_one("#picker-status", Static).update(
                "Included in the main list."
                if included
                else "Removed from the main list."
            )
        except (RuntimeError, OSError) as error:
            self.query_one("#picker-status", Static).update(plain(error))

    def action_close_picker(self) -> None:
        self.dismiss(self.last_included)


def source_process_identity(snapshot: PaneSnapshot) -> tuple:
    if (
        getattr(snapshot, "thread_id", "")
        and getattr(snapshot, "native_pane", None) is None
    ):
        return ("codex", snapshot.thread_id)
    return (
        snapshot.session_id,
        snapshot.window_id,
        snapshot.pane_id,
        snapshot.pane_pid,
        snapshot.pane_current_command,
        getattr(snapshot, "foreground_pid", None),
        getattr(snapshot, "foreground_start_ticks", None),
    )


def visible_capture(captured: str) -> Text:
    """Retain native rows, excluding unused blank rows at the viewport's end."""
    rows = captured.splitlines()
    while rows and not Text.from_ansi(rows[-1]).plain.strip():
        rows.pop()
    return Text.from_ansi("\n".join(rows))


class SourceTable(DataTable):
    """A single row click selects its source, rather than requiring a second click."""

    def on_click(self, event: events.Click) -> None:
        row = event.style.meta.get("row", -1)
        if row < 0 or row >= self.row_count:
            return
        event.stop()
        event.prevent_default()
        self.move_cursor(row=row)
        self.post_message(DataTable.RowSelected(self, row, self.ordered_rows[row].key))


class WindowBoard(App):
    """Attention view forwarding only native choices 1, 2, 3 and Enter."""

    AUTO_FOCUS = "#window-list"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("1", "answer_choice('1')", "Send 1", priority=True),
        Binding("2", "answer_choice('2')", "Send 2", priority=True),
        Binding("3", "answer_choice('3')", "Send 3", priority=True),
        Binding("enter", "answer_choice('enter')", "Send Enter", priority=True),
        ("o", "open_source", "Open source"),
        ("s", "next_window", "Next window"),
        ("r", "refresh_source", "Refresh source"),
        ("h", "read_identity", "Read identity"),
        ("v", "toggle_readback", "Toggle readback"),
        ("a", "add_panes", "Add panes"),
        Binding("alt+p", "browse_sources", "Browse", priority=True),
        Binding("ctrl+q", "quit", "Close view", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]
    CSS = """
    Screen { padding: 0 1; }
    #watch-mode { height: 1; color: $warning; }
    #pane-body { height: 1fr; }
    #window-list { height: 62%; width: 1fr; min-height: 4; }
    #source-readback { height: 38%; width: 1fr; min-height: 5; }
    #source-header { height: 2fr; min-height: 2; max-height: 40%; }
    #source-identity, #source-facts, #native-footer { height: auto; }
    #native-source { height: 3fr; min-height: 2; background: $surface; color: $text; }
    #native-context { height: auto; }
    #watch-actions { height: 3; }
    #watch-actions Button { width: 1fr; min-width: 8; }
    #watch-status { height: 1; }
    #watch-keys { height: 2; }
    """

    def __init__(
        self,
        source: TmuxSource,
        *,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        preference_path: Path | None = None,
    ):
        super().__init__()
        self.source = source
        self.clock = clock
        self.wall_clock = wall_clock
        self.clock_epoch = wall_clock() - clock()
        self.preferences = PanePreferences(preference_path)
        self.preference_error = ""
        self.picker_open = False
        self.state_observed: dict[str, tuple[str, tuple, float | None]] = {}
        self.selected_pane_id: str | None = None
        self.snapshots: dict[str, PaneSnapshot] = {}
        self.window_order: list[str] = []
        self.pane_order: list[str] = []
        self.representatives: dict[str, PaneSnapshot] = {}
        self.displayed: PaneSnapshot | None = None
        self.input_destination: PaneSnapshot | None = None
        self.input_identity: tuple | None = None
        self.source_replaced = False
        self.refreshing = False
        self.observed_state: str | None = None
        self.input_forwarded = False
        self.resolution_pending = False
        self.input_error = ""
        self.input_ready = False
        self.destination_since = 0.0
        self.focus_epoch = 0
        self.readback: Vertical | None = None
        self.pane_body: Vertical | None = None
        self.list_width = 0
        self.answer_event_time: float | None = None
        self.approval_choice: tuple[str, str] | None = None
        self.answered_occurrences: set[str] = set()
        self.input_queue: deque[tuple[PaneSnapshot, str, str | None]] = deque()
        self.input_task: asyncio.Task | None = None
        self.sending = False
        self.guarding_input = False
        self.guard_timer = None
        self.resolved_panes: dict[str, tuple] = {}
        self.exhausted = False
        self.message = "Preparing source…"

    def compose(self) -> ComposeResult:
        yield Static(
            "SOURCE WINDOWS — known states + chosen panes",
            id="watch-mode",
        )
        with Vertical(id="pane-body"):
            yield SourceTable(id="window-list", cursor_type="row", zebra_stripes=True)
            with Vertical(id="source-readback"):
                with VerticalScroll(id="source-header"):
                    yield Static(
                        "Source not selected", id="source-identity", markup=False
                    )
                    yield Static("", id="native-footer", markup=False)
                    yield Static("", id="source-facts", markup=False)
                with VerticalScroll(id="native-source"):
                    yield Static("", id="native-context", markup=False)
                with Horizontal(id="watch-actions"):
                    yield Button("Open source [o]", id="open-source", disabled=True)
                    yield Button("Next window [s]", id="next-window", disabled=True)
                    yield Button("Refresh [r]", id="refresh-source")
        yield Static(self.message, id="watch-status", markup=False)
        yield Static(
            "Alt+P list · ↑↓ panes · a Add panes\nv preview · o open · Ctrl+C quit",
            id="watch-keys",
            markup=False,
        )

    async def on_mount(self) -> None:
        self.table = self.query_one("#window-list", DataTable)
        self.readback = self.query_one("#source-readback", Vertical)
        self.identity_view = self.query_one("#source-identity", Static)
        self.facts_view = self.query_one("#source-facts", Static)
        self.footer_view = self.query_one("#native-footer", Static)
        self.native_view = self.query_one("#native-context", Static)
        self.native_scroll = self.query_one("#native-source", VerticalScroll)
        self.header_scroll = self.query_one("#source-header", VerticalScroll)
        self.status_view = self.query_one("#watch-status", Static)
        self.open_button = self.query_one("#open-source", Button)
        self.next_button = self.query_one("#next-window", Button)
        self.pane_body = self.query_one("#pane-body", Vertical)
        self.update_layout(self.size.width, self.size.height)
        await self.refresh_windows()
        self.set_interval(1, self.refresh_windows)

    def on_resize(self, event: events.Resize) -> None:
        if self.pane_body is not None:
            self.update_layout(event.size.width, event.size.height)

    def update_layout(self, width: int, height: int) -> None:
        if self.pane_body is None or self.readback is None:
            return
        needed = len(self.pane_order) + 2
        landscape = (
            width >= 120 and width >= 2 * height and needed >= (height - 3) * 0.5
        )
        self.pane_body.styles.layout = "horizontal" if landscape else "vertical"
        shared = self.readback.display
        self.table.styles.width = "58%" if landscape and shared else "1fr"
        self.table.styles.height = (
            min(max(4, needed), max(4, int((height - 3) * 0.62)))
            if not landscape and shared
            else "1fr"
        )
        self.readback.styles.width = "42%" if landscape else "1fr"
        self.readback.styles.height = "1fr"
        self.list_width = int((width - 2) * 0.58) if landscape and shared else width - 2
        self.query_one("#watch-actions", Horizontal).display = height >= 30
        if self.snapshots:
            self.render_source_list(list(self.snapshots.values()))

    async def on_event(self, event: events.Event) -> None:
        if isinstance(event, events.Paste):
            event.stop()
            event.prevent_default()
            return
        if (
            isinstance(event, events.Key)
            and not event.is_forwarded
            and event.key in ANSWER_KEYS
        ):
            previous_time = self.answer_event_time
            self.answer_event_time = event.time
            try:
                await super().on_event(event)
            finally:
                self.answer_event_time = previous_time
        else:
            await super().on_event(event)

    def action_answer_choice(self, choice: str) -> None:
        if not self.picker_open and self.answer_event_time is not None:
            self.queue_input(
                choice,
                choice if choice != "enter" else None,
                event_time=self.answer_event_time,
            )

    async def refresh_windows(self) -> None:
        if self.refreshing or self.picker_open:
            return
        self.refreshing = True
        try:
            items = await asyncio.to_thread(self.source.snapshots)
            if not self.is_running:
                # The view closed while the source answered; leave its DOM alone.
                return
            self.snapshots = {item.pane_id: item for item in items}
            self.observe_states(items)
            self.render_source_list(items)
            self.update_layout(self.size.width, self.size.height)
            if self.selected_pane_id is None:
                target = (
                    self.waiting_pane()
                    if self.exhausted
                    else (self.pane_order[0] if self.pane_order else None)
                )
                if target is not None:
                    await self.show_source(self.snapshots[target])
                else:
                    self.message = (
                        "Nothing waiting. a Add panes; Alt+P browses; Ctrl+c closes."
                    )
            elif self.selected_pane_id not in self.snapshots:
                self.message = (
                    "Source pane unavailable. Choose another window; no input was sent."
                )
                self.open_button.disabled = True
                self.input_ready = False
            elif self.selected_pane_id not in self.pane_order:
                self.input_ready = False
                self.open_button.disabled = True
                self.displayed = self.input_destination = None
                self.identity_view.update("Unknown pane hidden")
                self.footer_view.update("")
                self.facts_view.update("")
                self.native_view.update(
                    "a Add panes to include it, or choose another row."
                )
                self.message = "Unknown pane hidden. a Add panes; no input was sent."
            else:
                await self.refresh_selected_source(
                    self.snapshots[self.selected_pane_id]
                )
            self.next_button.disabled = not self.window_order
            self.status_view.update(self.preference_error or self.message)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            self.message = plain(error)
            self.open_button.disabled = True
            self.input_ready = False
            self.status_view.update(self.message)
        finally:
            self.refreshing = False

    @staticmethod
    def observation_key(snapshot: PaneSnapshot) -> tuple:
        return (
            snapshot.state,
            snapshot.idle_since,
            getattr(snapshot, "state_since", None),
            source_process_identity(snapshot),
        )

    def observe_states(self, items: list[PaneSnapshot]) -> None:
        now = self.clock()
        observed = {}
        for pane in items:
            identity = source_process_identity(pane)
            previous = self.state_observed.get(pane.pane_id)
            since = None
            if previous and previous[1] == identity:
                since = previous[2] if previous[0] == pane.state else now
            observed[pane.pane_id] = (pane.state, identity, since)
        self.state_observed = observed

    def pane_attention(self, pane: PaneSnapshot) -> tuple[int, bool, float, int, int]:
        return attention_key(pane, self.state_start(pane)[0])

    def state_start(self, pane: PaneSnapshot) -> tuple[float | None, bool]:
        recorded = getattr(pane, "state_since", None)
        provenance = getattr(pane, "state_since_source", "")
        if (
            isinstance(recorded, (int, float))
            and math.isfinite(recorded)
            and 0 < recorded <= self.wall_clock()
            and provenance
        ):
            return recorded, True
        observed = self.state_observed[pane.pane_id][2]
        return (self.clock_epoch + observed if observed is not None else None), False

    def state_label(self, pane: PaneSnapshot) -> Text:
        since, historical = self.state_start(pane)
        if pane.state == "unverified":
            return Text("state ?")
        if pane.state in {"unlinked", "unavailable"}:
            return Text("link needed" if pane.state == "unlinked" else "disconnected")
        if since is None:
            return Text(f"{pane.state} age ?")
        elapsed = max(
            0,
            int(
                (self.wall_clock() if historical else self.clock_epoch + self.clock())
                - since
            ),
        )
        if elapsed >= 86400:
            duration = f"{elapsed // 86400}d"
        elif elapsed >= 3600:
            duration = f"{elapsed // 3600}h"
        elif elapsed >= 60:
            duration = f"{elapsed // 60}m"
        else:
            duration = f"{elapsed}s"
        marker = (
            "~"
            if getattr(pane, "state_approximate", False)
            else ("" if historical else "≥")
        )
        return Text(f"{pane.state} {marker}{duration}")

    def render_source_list(self, items: list[PaneSnapshot]) -> None:
        self.resolved_panes = {
            pane: observation
            for pane, observation in self.resolved_panes.items()
            if pane in self.snapshots
            and self.observation_key(self.snapshots[pane]) == observation
        }
        try:
            choices = self.preferences.read()
            self.preference_error = ""
        except RuntimeError as error:
            choices = set()
            self.preference_error = plain(error)
        visible = []
        for pane in items:
            try:
                included = PanePreferences.identity(pane) in choices
            except RuntimeError:
                included = False
            if pane.state != "unknown" or included:
                visible.append(pane)
        grouped: dict[str, list[PaneSnapshot]] = {}
        for snapshot in visible:
            grouped.setdefault(snapshot.window_id, []).append(snapshot)
        self.representatives = {
            key: min(panes, key=self.pane_attention) for key, panes in grouped.items()
        }
        self.window_order = sorted(
            self.representatives,
            key=lambda key: self.pane_attention(self.representatives[key]),
        )
        self.pane_order = [
            pane.pane_id for pane in sorted(visible, key=self.pane_attention)
        ]
        with self.table.prevent(DataTable.RowHighlighted):
            self.table.clear(columns=True)
            self.table.add_column("Win.p", key="index", width=5)
            self.table.add_column(
                "Project / task", key="identity", width=max(12, self.list_width - 29)
            )
            self.table.add_column("State · age", key="state", width=18)
            for pane_id in self.pane_order:
                pane = self.snapshots[pane_id]
                self.table.add_row(
                    (
                        f"{pane.window_index}.{pane.pane_index}"
                        if not getattr(pane, "thread_id", "")
                        or getattr(pane, "native_pane", None)
                        else "—"
                    ),
                    source_identity(pane),
                    self.state_label(pane),
                    key=pane_id,
                )
            if self.selected_pane_id in self.pane_order:
                self.table.move_cursor(row=self.pane_order.index(self.selected_pane_id))

    def waiting_pane(self, *, excluding: str | None = None) -> str | None:
        return next(
            (
                pane
                for pane in self.pane_order
                if pane != excluding
                and pane not in self.resolved_panes
                and self.snapshots[pane].state in ("blocked", "idle")
            ),
            None,
        )

    async def refresh_selected_source(self, current: PaneSnapshot) -> None:
        if source_process_identity(current) != self.input_identity:
            self.source_replaced = True
            self.input_ready = False
            self.message = "Source process changed. Select its row to type into it."
        if (
            self.observed_state == "blocked" and current.state in ("running", "idle")
        ) or (
            self.observed_state == "idle"
            and current.state == "running"
            and self.input_forwarded
        ):
            self.resolution_pending = True
        if current.state == "unknown":
            self.resolution_pending = False
        self.observed_state = current.state
        if self.resolution_pending and not (
            self.sending or self.input_queue or self.input_error or self.source_replaced
        ):
            await self.advance_source(current)
        elif self.native_scroll.has_focus or (
            self.native_scroll.scroll_offset.y >= self.native_scroll.max_scroll_y
        ):
            await self.show_source(current, preserve_scroll=True, focus_input=False)

    async def advance_source(self, current: PaneSnapshot) -> None:
        target = self.waiting_pane(excluding=current.pane_id)
        self.resolved_panes[current.pane_id] = self.observation_key(current)
        self.input_ready = False
        self.render_source_list(list(self.snapshots.values()))
        if target is not None:
            await self.show_source(self.snapshots[target], hold_input=True)
            with self.table.prevent(DataTable.RowHighlighted):
                self.table.move_cursor(row=self.pane_order.index(target))
            return
        self.exhausted = True
        self.selected_pane_id = None
        self.displayed = self.input_destination = None
        self.resolution_pending = False
        self.open_button.disabled = True
        self.native_view.update(
            Text("No known waiting sources. Browse the list to inspect another pane.")
        )
        self.message = "Nothing waiting. Alt+P browses sources; Ctrl+c closes."
        self.screen.set_focus(self.table, scroll_visible=False)

    async def show_source(
        self,
        snapshot: PaneSnapshot,
        *,
        preserve_scroll: bool = False,
        focus_input: bool = True,
        adopt_input: bool = False,
        hold_input: bool = False,
    ) -> None:
        changing = snapshot.pane_id != self.selected_pane_id
        if changing and (self.sending or self.input_queue):
            self.message = "Finishing input to the current source before switching."
            self.status_view.update(self.message)
            return
        if focus_input:
            self.focus_epoch += 1
        activation_epoch = self.focus_epoch
        if changing:
            self.input_ready = False
        try:
            if getattr(snapshot, "thread_id", ""):
                snapshot = await asyncio.to_thread(self.source.select, snapshot)
            captured = await asyncio.to_thread(self.source.capture, snapshot)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            self.message = "Could not capture source: " + plain(error)
            self.open_button.disabled = True
            self.input_ready = False
            self.status_view.update(self.message)
            return
        retain_position = preserve_scroll and snapshot.pane_id == self.selected_pane_id
        was_at_bottom = (
            self.native_scroll.scroll_offset.y >= self.native_scroll.max_scroll_y
        )
        native_position = self.native_scroll.scroll_offset
        header_position = self.header_scroll.scroll_offset
        self.selected_pane_id = snapshot.pane_id
        self.displayed = snapshot
        if changing or adopt_input:
            self.input_destination = snapshot
            self.input_identity = source_process_identity(snapshot)
            self.source_replaced = False
            self.destination_since = events.Event().time
            self.guarding_input = False
            if self.guard_timer is not None:
                self.guard_timer.stop()
        if changing:
            self.observed_state = snapshot.state
            self.exhausted = False
            self.input_forwarded = False
            self.resolution_pending = False
            self.input_error = ""
        self.render_source_content(snapshot, captured)
        if retain_position and not was_at_bottom:
            self.call_after_refresh(
                self.native_scroll.scroll_to,
                x=native_position.x,
                y=native_position.y,
                animate=False,
            )
            self.call_after_refresh(
                self.header_scroll.scroll_to,
                x=header_position.x,
                y=header_position.y,
                animate=False,
            )
        else:
            self.call_after_refresh(self.native_scroll.scroll_end, animate=False)
            self.call_after_refresh(self.header_scroll.scroll_home, animate=False)
        self.open_button.disabled = bool(
            getattr(snapshot, "thread_id", "")
            and not getattr(snapshot, "native_pane", None)
        )
        self.update_input_status(hold_input=hold_input)
        if focus_input:
            self.call_after_refresh(self.activate_terminal, activation_epoch)

    def render_source_content(self, snapshot, captured: str) -> None:
        self.update_source_metadata(snapshot)
        self.native_view.update(self.source_content(snapshot, captured))
        self.input_destination = snapshot
        self.native_scroll.styles.background = (
            snapshot.pane_bg if snapshot.pane_bg.startswith("#") else None
        )
        self.native_scroll.styles.color = (
            snapshot.pane_fg if snapshot.pane_fg.startswith("#") else None
        )

    def update_input_status(self, *, hold_input: bool) -> None:
        self.message = self.input_error or "Preparing source…"
        if self.source_replaced:
            self.input_ready = False
            self.message = "Source process changed. Select its row to type into it."
        elif self.displayed is not None and getattr(self.displayed, "thread_id", ""):
            request = self.current_approval(self.displayed)
            self.input_ready = bool(
                request and self.approval_options(request) and not self.guarding_input
            )
        elif self.displayed is not None and self.displayed.state in {
            "unlinked",
            "unavailable",
        }:
            self.input_ready = False
            self.message = self.displayed.status_detail
        elif not self.open_button.disabled and not self.guarding_input:
            self.input_ready = True
        if hold_input:
            self.restart_input_guard()
        elif self.guarding_input:
            self.message = "Releasing previous input…"
        elif self.input_ready:
            self.message = self.input_error or self.ready_message()
        elif self.displayed is not None and getattr(self.displayed, "thread_id", ""):
            self.message = (
                self.input_error
                or "No supported pending approval. Continue this conversation in Codex."
            )
        self.status_view.update(self.message)

    def source_content(self, snapshot, captured: str) -> Text:
        content = visible_capture(captured)
        for request in getattr(snapshot, "approvals", ()):
            content.append("\n\nApproval request\n", style="bold")
            details = {
                key: value
                for key, value in request.params.items()
                if key not in {"threadId", "turnId", "itemId"}
            }
            content.append(json.dumps(details, indent=2, ensure_ascii=False))
            choices = self.approval_options(request)
            if choices:
                content.append(
                    "\n"
                    + " · ".join(
                        f"{index}. {label}"
                        for index, (_, label) in enumerate(choices, 1)
                    )
                    + "\nChoose 1/2/3, then Enter."
                )
            else:
                content.append(
                    "\nAnswer this request in Codex; "
                    "this request type is not supported here."
                )
        return content

    @staticmethod
    def approval_options(request) -> list[tuple[str, str]]:
        if request.method not in {
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
        }:
            return []
        labels = {
            "accept": "Approve once",
            "decline": "Decline",
            "cancel": "Cancel turn",
        }
        return [
            (decision, label)
            for decision, label in labels.items()
            if decision in request.decisions
        ]

    def current_approval(self, snapshot):
        requests = getattr(snapshot, "approvals", ())
        if len(requests) != 1 or requests[0].occurrence_id in self.answered_occurrences:
            return None
        return requests[0]

    def ready_message(self) -> str:
        if self.displayed is None or not getattr(self.displayed, "thread_id", ""):
            return ANSWER_READY_MESSAGE
        request = self.current_approval(self.displayed)
        if request is None:
            return "No supported pending approval; continue in Codex."
        options = self.approval_options(request)
        if self.approval_choice and self.approval_choice[0] == request.occurrence_id:
            label = next(
                label
                for decision, label in options
                if decision == self.approval_choice[1]
            )
            return label + " selected · Enter sends · 1/2/3 changes choice"
        return (
            " · ".join(
                f"{index} {label}" for index, (_, label) in enumerate(options, 1)
            )
            + " · Enter sends"
        )

    async def submit_approval(
        self, snapshot, occurrence_id: str, decision: str
    ) -> None:
        self.sending = True
        try:
            await asyncio.to_thread(
                self.source.answer, snapshot, occurrence_id, decision
            )
            self.input_forwarded = True
            self.message = "Request resolved or cleared; refreshing."
        except (RuntimeError, OSError) as error:
            self.input_error = (
                "Answer outcome: " + plain(error) + "; inspect Codex before retrying."
            )
            self.message = self.input_error
        finally:
            self.sending = False
            self.status_view.update(self.message)
            await self.refresh_windows()

    def update_source_metadata(self, snapshot: PaneSnapshot) -> None:
        self.identity_view.update(source_identity(snapshot))
        provenance = (
            "State age: " + plain(getattr(snapshot, "state_since_source", ""))
            if self.state_start(snapshot)[1]
            else (
                "State age ≥ since transition observed by this viewer."
                if self.state_start(snapshot)[0] is not None
                else "State age unknown; no transition observed by this viewer."
            )
        )
        if getattr(snapshot, "thread_id", ""):
            link = snapshot.native_pane
            location = (
                f"Session {plain(link.session_name)} · window {link.window_index} · "
                f"pane {link.pane_index} ({link.pane_id})"
                if link
                else "No verified terminal link; showing Codex conversation history"
            )
            identity = f"Codex session {snapshot.thread_id}\n{location}"
        else:
            identity = (
                f"Session {plain(snapshot.session_name)} · "
                f"window {snapshot.window_index} · "
                f"pane {snapshot.pane_index} ({snapshot.pane_id})"
            )
        self.facts_view.update(
            f"{identity}\n{plain(snapshot.status_detail)}\n{provenance}\n"
            f"Cwd: {plain(snapshot.cwd)}\nTitle: {plain(snapshot.title)}"
        )
        footer_lines = [
            Text.from_ansi(line)
            for line in snapshot.preview_ansi.splitlines()[-4:]
            if Text.from_ansi(line).plain.strip()
        ]
        self.footer_view.update(Text("\n").join(footer_lines))

    def activate_terminal(self, expected_epoch: int | None = None) -> None:
        if expected_epoch is not None and expected_epoch != self.focus_epoch:
            return
        if expected_epoch is None:
            self.focus_epoch += 1
        self.screen.set_focus(self.table, scroll_visible=False)

    def restart_input_guard(self) -> None:
        self.guarding_input = True
        self.input_ready = False
        if self.guard_timer is not None:
            self.guard_timer.stop()
        self.guard_timer = self.set_timer(INPUT_QUIET_SECONDS, self.finish_input_guard)
        self.message = "Releasing previous input…"
        self.status_view.update(self.message)

    def finish_input_guard(self) -> None:
        self.guarding_input = False
        self.destination_since = events.Event().time
        self.input_ready = not (self.source_replaced or self.exhausted)
        self.update_input_status(hold_input=False)

    def queue_input(
        self, key: str, character: str | None, *, event_time: float
    ) -> None:
        if key not in ANSWER_KEYS:
            return
        if self.guarding_input:
            self.restart_input_guard()
            return
        if (
            not self.input_ready
            or self.input_destination is None
            or event_time < self.destination_since
        ):
            return
        if getattr(self.input_destination, "thread_id", ""):
            request = self.current_approval(self.input_destination)
            if request is None:
                return
            options = self.approval_options(request)
            if key in {"1", "2", "3"}:
                index = int(key) - 1
                if index < len(options):
                    self.approval_choice = (request.occurrence_id, options[index][0])
                    self.status_view.update(self.ready_message())
            elif (
                key == "enter"
                and self.approval_choice
                and self.approval_choice[0] == request.occurrence_id
            ):
                self.answered_occurrences.add(request.occurrence_id)
                self.input_ready = False
                self.input_task = asyncio.create_task(
                    self.submit_approval(self.input_destination, *self.approval_choice)
                )
                self.approval_choice = None
            return
        self.input_queue.append((self.input_destination, key, character))
        if self.input_task is None or self.input_task.done():
            self.input_task = asyncio.create_task(self.drain_input())

    async def drain_input(self) -> None:
        try:
            while True:
                while self.input_queue:
                    snapshot, key, character = self.input_queue.popleft()
                    self.sending = True
                    try:
                        await asyncio.to_thread(
                            self.source.send_key, snapshot, key, character
                        )
                        self.input_forwarded = True
                        self.input_error = ""
                    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                        self.input_error = "Could not send input: " + plain(error)
                        self.input_queue.clear()
                        self.message = self.input_error
                        self.status_view.update(self.message)
                        break
                    finally:
                        self.sending = False
                await self.refresh_windows()
                if not self.input_queue:
                    break
        finally:
            self.sending = False

    def action_browse_sources(self) -> None:
        self.focus_epoch += 1
        self.screen.set_focus(self.table, scroll_visible=False)

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        snapshot = self.snapshots.get(event.row_key.value)
        if snapshot is not None and snapshot.pane_id != self.selected_pane_id:
            await self.show_source(snapshot, focus_input=False)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        snapshot = self.snapshots.get(event.row_key.value)
        if snapshot is not None:
            if self.readback is not None:
                self.readback.display = True
                self.update_layout(self.size.width, self.size.height)
            if snapshot.pane_id != self.selected_pane_id or self.source_replaced:
                await self.show_source(snapshot, adopt_input=True)
            else:
                self.activate_terminal()

    async def action_next_window(self) -> None:
        if not self.window_order:
            return
        current_window = (
            self.displayed.window_id if self.displayed is not None else None
        )
        index = (
            self.window_order.index(current_window)
            if current_window in self.window_order
            else -1
        )
        next_window = self.window_order[(index + 1) % len(self.window_order)]
        await self.show_source(self.representatives[next_window])
        with self.table.prevent(DataTable.RowHighlighted):
            self.table.move_cursor(
                row=self.pane_order.index(self.representatives[next_window].pane_id)
            )

    async def action_refresh_source(self) -> None:
        await self.refresh_windows()
        snapshot = self.snapshots.get(self.selected_pane_id)
        if snapshot is not None:
            await self.show_source(snapshot, preserve_scroll=True)

    def action_read_identity(self) -> None:
        self.focus_epoch += 1
        if self.readback is not None:
            self.readback.display = True
            self.update_layout(self.size.width, self.size.height)
        self.screen.set_focus(self.header_scroll, scroll_visible=False)

    def action_toggle_readback(self) -> None:
        if self.readback is None:
            return
        self.focus_epoch += 1
        self.readback.display = not self.readback.display
        self.update_layout(self.size.width, self.size.height)
        target = self.native_scroll if self.readback.display else self.table
        self.screen.set_focus(target, scroll_visible=False)
        if self.readback.display:
            self.call_after_refresh(self.native_scroll.scroll_end, animate=False)

    def action_add_panes(self) -> None:
        if self.picker_open or self.sending or self.input_queue:
            return
        self.focus_epoch += 1
        self.picker_open = True
        panes = sorted(
            (pane for pane in self.snapshots.values() if pane.state == "unknown"),
            key=lambda pane: (pane.window_index, pane.pane_index),
        )
        self.push_screen(PanePicker(panes, self.preferences), self.picker_closed)

    async def picker_closed(self, included: str | None) -> None:
        self.picker_open = False
        await self.refresh_windows()
        if included in self.pane_order:
            self.readback.display = True
            self.update_layout(self.size.width, self.size.height)
            await self.show_source(self.snapshots[included], adopt_input=True)
            with self.table.prevent(DataTable.RowHighlighted):
                self.table.move_cursor(row=self.pane_order.index(included))

    async def action_open_source(self) -> None:
        if self.displayed is None or self.open_button.disabled:
            return
        try:
            await asyncio.to_thread(self.source.open_source, self.displayed)
            self.message = (
                "Opened the exact source window and pane; no approval was sent."
            )
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            self.message = "Could not open source: " + plain(error)
        self.status_view.update(self.message)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-source":
            await self.action_open_source()
        elif event.button.id == "next-window":
            await self.action_next_window()
        elif event.button.id == "refresh-source":
            await self.action_refresh_source()


def load_source(session: str, socket: str | None) -> TmuxSource:
    spec = importlib.util.spec_from_file_location(
        "permission_queue_tmux_source", DIRECTORY / "tmux_source.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Source adapter unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.TmuxSource(session=session, socket=socket)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--socket", help="tmux socket path for source watch mode")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="own harmless fixture hooks")
    mode.add_argument(
        "--fixture-only", action="store_true", help="view supplied fixture hooks"
    )
    mode.add_argument(
        "--watch-session", metavar="NAME", help="watch existing source windows"
    )
    arguments = parser.parse_args()
    if arguments.watch_session:
        source = load_source(arguments.watch_session, arguments.socket)
        try:
            WindowBoard(source).run()
        finally:
            source.close()
        return 0
    if arguments.run_dir is None and not arguments.demo:
        parser.error("--fixture-only requires --run-dir")
    run_dir = arguments.run_dir or Path(
        tempfile.mkdtemp(prefix="permission-board-demo-")
    )
    app = PermissionBoard(run_dir, demo=arguments.demo)
    try:
        app.run()
    finally:
        if app.producer is not None:
            app.producer.close()
    print(f"Experiment evidence: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
