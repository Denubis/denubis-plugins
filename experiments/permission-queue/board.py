"""Fixture-only permission screen; launch Python with -P to avoid queue.py shadowing."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
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
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, DataTable, Static, TextArea

if TYPE_CHECKING:
    from textual.binding import BindingType
    from tmux_source import PaneSnapshot, TmuxSource

DIRECTORY = Path(__file__).resolve().parent
INPUT_QUIET_SECONDS = 0.75
ANSWER_READY_MESSAGE = "Ready: 1/2/3 + Enter → displayed source"
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
        content.append(plain(snapshot.title) or "Source header unavailable")
    return content


def attention_key(snapshot: PaneSnapshot) -> tuple[int, float, int, int]:
    rank = {"blocked": 0, "idle": 1, "running": 2, "unknown": 3}.get(snapshot.state, 3)
    age = (
        snapshot.idle_since
        if snapshot.state == "idle" and snapshot.idle_since is not None
        else float("inf")
    )
    return rank, age, snapshot.window_index, snapshot.pane_index


def source_process_identity(snapshot: PaneSnapshot) -> tuple:
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

    AUTO_FOCUS = "#native-source"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("1", "answer_choice('1')", "Send 1", priority=True),
        Binding("2", "answer_choice('2')", "Send 2", priority=True),
        Binding("3", "answer_choice('3')", "Send 3", priority=True),
        Binding("enter", "answer_choice('enter')", "Send Enter", priority=True),
        ("o", "open_source", "Open source"),
        ("s", "next_window", "Next window"),
        ("r", "refresh_source", "Refresh source"),
        ("h", "read_identity", "Read identity"),
        ("v", "read_source", "Read source text"),
        Binding("alt+p", "browse_sources", "Browse", priority=True),
        Binding("ctrl+q", "quit", "Close view", priority=True),
        Binding("ctrl+c", "answer_help", "Other input: open source"),
    ]
    CSS = """
    Screen { padding: 0 1; }
    #watch-mode { height: 1; color: $warning; }
    #window-list { height: 23%; min-height: 4; max-height: 12; }
    #source-header { height: auto; min-height: 3; max-height: 35%; }
    #source-identity, #source-facts, #native-footer { height: auto; }
    #native-source { height: 1fr; min-height: 3; background: $surface; color: $text; }
    #native-context { height: auto; }
    #watch-actions { height: 3; }
    #watch-actions Button { width: 1fr; min-width: 8; }
    #watch-status, #watch-keys { height: 1; }
    """

    def __init__(self, source: TmuxSource):
        super().__init__()
        self.source = source
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
        self.answer_event_time: float | None = None
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
            "SOURCE WINDOWS — 1/2/3/Enter only · o opens source",
            id="watch-mode",
        )
        yield SourceTable(id="window-list", cursor_type="row", zebra_stripes=True)
        with VerticalScroll(id="source-header"):
            yield Static("Source not selected", id="source-identity", markup=False)
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
            "Alt+P browse panes · ↑↓ choose · o open · Ctrl+q close",
            id="watch-keys",
            markup=False,
        )

    async def on_mount(self) -> None:
        self.table = self.query_one("#window-list", DataTable)
        self.identity_view = self.query_one("#source-identity", Static)
        self.facts_view = self.query_one("#source-facts", Static)
        self.footer_view = self.query_one("#native-footer", Static)
        self.native_view = self.query_one("#native-context", Static)
        self.native_scroll = self.query_one("#native-source", VerticalScroll)
        self.header_scroll = self.query_one("#source-header", VerticalScroll)
        self.status_view = self.query_one("#watch-status", Static)
        self.open_button = self.query_one("#open-source", Button)
        self.next_button = self.query_one("#next-window", Button)
        await self.refresh_windows()
        self.set_interval(1, self.refresh_windows)

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
        if self.answer_event_time is not None:
            self.queue_input(
                choice,
                choice if choice != "enter" else None,
                event_time=self.answer_event_time,
            )

    async def refresh_windows(self) -> None:
        if self.refreshing:
            return
        self.refreshing = True
        try:
            items = await asyncio.to_thread(self.source.snapshots)
            self.snapshots = {item.pane_id: item for item in items}
            self.render_source_list(items)
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
                        "Nothing waiting. Alt+P browses sources; Ctrl+q closes."
                    )
            elif self.selected_pane_id not in self.snapshots:
                self.message = (
                    "Source pane unavailable. Choose another window; no input was sent."
                )
                self.open_button.disabled = True
                self.input_ready = False
            else:
                await self.refresh_selected_source(
                    self.snapshots[self.selected_pane_id]
                )
            self.next_button.disabled = not self.window_order
            self.status_view.update(self.message)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            self.message = plain(error)
            self.open_button.disabled = True
            self.input_ready = False
            self.status_view.update(self.message)
        finally:
            self.refreshing = False

    @staticmethod
    def observation_key(snapshot: PaneSnapshot) -> tuple:
        return snapshot.state, snapshot.idle_since, source_process_identity(snapshot)

    def render_source_list(self, items: list[PaneSnapshot]) -> None:
        self.resolved_panes = {
            pane: observation
            for pane, observation in self.resolved_panes.items()
            if pane in self.snapshots
            and self.observation_key(self.snapshots[pane]) == observation
        }
        grouped: dict[str, list[PaneSnapshot]] = {}
        for snapshot in items:
            grouped.setdefault(snapshot.window_id, []).append(snapshot)
        self.representatives = {
            key: min(panes, key=attention_key) for key, panes in grouped.items()
        }
        self.window_order = sorted(
            self.representatives,
            key=lambda key: attention_key(self.representatives[key]),
        )
        self.pane_order = [
            pane.pane_id
            for pane in sorted(
                items,
                key=lambda pane: (
                    pane.pane_id in self.resolved_panes,
                    attention_key(pane),
                ),
            )
        ]
        with self.table.prevent(DataTable.RowHighlighted):
            self.table.clear(columns=True)
            self.table.add_column("Win.p", key="index", width=5)
            self.table.add_column(
                "Project / task", key="identity", width=max(12, self.size.width - 27)
            )
            self.table.add_column("State", key="state", width=14)
            for pane_id in self.pane_order:
                pane = self.snapshots[pane_id]
                self.table.add_row(
                    f"{pane.window_index}.{pane.pane_index}",
                    source_identity(pane),
                    Text(pane.state),
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
        self.message = "Nothing waiting. Alt+P browses sources; Ctrl+q closes."
        self.screen.set_focus(self.native_scroll, scroll_visible=False)

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
        self.update_source_metadata(snapshot)
        self.native_view.update(visible_capture(captured))
        self.native_scroll.styles.background = (
            snapshot.pane_bg if snapshot.pane_bg.startswith("#") else None
        )
        self.native_scroll.styles.color = (
            snapshot.pane_fg if snapshot.pane_fg.startswith("#") else None
        )
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
        self.open_button.disabled = False
        self.update_input_status(hold_input=hold_input)
        if focus_input:
            self.call_after_refresh(self.activate_terminal, activation_epoch)

    def update_input_status(self, *, hold_input: bool) -> None:
        self.message = self.input_error or "Preparing source…"
        if self.source_replaced:
            self.input_ready = False
            self.message = "Source process changed. Select its row to type into it."
        elif not self.open_button.disabled and not self.guarding_input:
            self.input_ready = True
        if hold_input:
            self.restart_input_guard()
        elif self.guarding_input:
            self.message = "Releasing previous input…"
        elif self.input_ready:
            self.message = self.input_error or ANSWER_READY_MESSAGE
        self.status_view.update(self.message)

    def update_source_metadata(self, snapshot: PaneSnapshot) -> None:
        self.identity_view.update(source_identity(snapshot))
        self.facts_view.update(
            f"Session {plain(snapshot.session_name)} ({snapshot.session_id}) · "
            f"window {snapshot.window_index} {plain(snapshot.window_name)} "
            f"({snapshot.window_id}) · "
            f"pane {snapshot.pane_index} ({snapshot.pane_id})\n"
            f"{plain(snapshot.status_detail)}\nCwd: {plain(snapshot.cwd)}\n"
            f"Title: {plain(snapshot.title)} · "
            f"Process: {plain(snapshot.pane_current_command)}"
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
        self.screen.set_focus(self.native_scroll, scroll_visible=False)

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
        self.input_ready = not (
            self.open_button.disabled or self.source_replaced or self.exhausted
        )
        if self.input_ready:
            self.message = self.input_error or ANSWER_READY_MESSAGE
            self.status_view.update(self.message)

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

    def action_answer_help(self) -> None:
        self.message = (
            "Only 1/2/3 and Enter are sent here. o opens source for other input."
        )
        self.status_view.update(self.message)

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        snapshot = self.snapshots.get(event.row_key.value)
        if snapshot is not None and snapshot.pane_id != self.selected_pane_id:
            await self.show_source(snapshot, focus_input=False)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        snapshot = self.snapshots.get(event.row_key.value)
        if snapshot is not None:
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
        self.screen.set_focus(self.header_scroll, scroll_visible=False)

    def action_read_source(self) -> None:
        self.activate_terminal()

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
        WindowBoard(load_source(arguments.watch_session, arguments.socket)).run()
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
