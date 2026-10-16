"""Drive the fixture screen through Textual's public pilot and real hook processes."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import pty
import select
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from textual import events
from textual.color import Color
from textual.widgets import Button, Static

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "experiments" / "permission-queue"
QUEUE = DIRECTORY / "queue.py"
SPEC = importlib.util.spec_from_file_location(
    "permission_board_experiment", DIRECTORY / "board.py"
)
assert SPEC is not None and SPEC.loader is not None
BOARD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BOARD
SPEC.loader.exec_module(BOARD)


def queue(run_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(QUEUE), args[0], "--run-dir", str(run_dir), *args[1:]],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=5,
    )


def records(run_dir: Path) -> list[dict]:
    result = queue(run_dir, "list", "--json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def fixture_hook(tmp_path):
    children = []
    counter = 0

    def create(
        command="printf 'harmless fixture\\n'",
        marked=True,
        hold=10,
        session=None,
        turns=None,
    ):
        nonlocal counter
        counter += 1
        payload = {
            "hook_event_name": "PermissionRequest",
            "session_id": session or f"fixture-board-{counter}",
            "session_label": f"Session {counter}",
            "conversation_source": "generated-demo",
            "conversation": turns
            or [
                {"role": "user", "content": "Please inspect this demo preview."},
                {"role": "assistant", "content": "The complete demo request is below."},
            ],
            "tool_name": "Bash",
            "cwd": str(tmp_path),
            "tool_input": {"command": command},
            "experiment_fixture": marked,
        }
        previous = {record["request_id"] for record in records(tmp_path)}
        child = subprocess.Popen(
            [
                sys.executable,
                str(QUEUE),
                "hook",
                "--run-dir",
                str(tmp_path),
                "--vendor",
                "claude",
                "--vendor-version",
                "fixture",
                "--hold-seconds",
                str(hold),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=ROOT,
        )
        assert child.stdin is not None
        child.stdin.write(json.dumps(payload))
        child.stdin.close()
        child.stdin = None
        children.append(child)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            new = [
                record
                for record in records(tmp_path)
                if record["request_id"] not in previous
            ]
            if new:
                return child, new[0]
            time.sleep(0.01)
        pytest.fail("controlled fixture hook did not publish")

    yield create
    for child in children:
        if child.poll() is None:
            child.terminate()
        child.communicate(timeout=3)


async def wait_ui(pilot, predicate):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if predicate():
            return
        await pilot.pause(0.05)
    pytest.fail("screen did not reach the expected observable state")


@pytest.mark.parametrize("size", [(60, 20), (107, 93)])
def test_generated_conversation_and_complete_request_are_visible(
    tmp_path, fixture_hook, size
):
    turns = [
        {"role": "user", "content": "Please show [red]literal preview[/red]."},
        {"role": "assistant", "content": "This demo request needs your answer.\x07"},
    ]
    _, request = fixture_hook("printf '[red]literal[/red]\\n'\x1b[2J", turns=turns)

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            assert app.selected_id == request["request_id"]
            assert app.waiting_count == 1
            assert "Please show [red]literal preview[/red]." in app.context_view.text
            assert "\\u0007" in app.context_view.text
            displayed = app.detail_view.text
            escaped_command = json.dumps(request["tool_input"]["command"])[1:-1]
            assert escaped_command in displayed
            assert displayed.index(escaped_command) < displayed.index(
                request["request_id"]
            )
            assert "\x1b" not in displayed
            assert not app.query_one("#allow", Button).disabled
            assert not app.query_one("#deny", Button).disabled
            assert app.query_one("#allow", Button).region.bottom <= size[1]

    asyncio.run(exercise())


@pytest.mark.parametrize(("key", "choice"), [("a", "allow"), ("d", "deny")])
def test_one_key_answers_exact_request_and_brings_next_forward(
    tmp_path, fixture_hook, key, choice
):
    first_child, first = fixture_hook("printf 'First approval'")
    second_child, second = fixture_hook("printf 'Second approval'")

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.selected_id == first["request_id"]
            await pilot.press(key)
            await wait_ui(pilot, lambda: app.selected_id == second["request_id"])
            stdout, stderr = first_child.communicate(timeout=3)
            assert first_child.returncode == 0, stderr
            assert (
                json.loads(stdout)["hookSpecificOutput"]["decision"]["behavior"]
                == choice
            )
            assert second_child.poll() is None
            assert first["request_id"] not in app.pending_ids
            assert app.waiting_count == 1
            assert app.context_view.has_focus
            assert len(app.screen_stack) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize(("button", "choice"), [("#allow", "allow"), ("#deny", "deny")])
def test_one_click_answers_and_enter_does_not_answer_next_item(
    tmp_path, fixture_hook, button, choice
):
    first_child, first = fixture_hook()
    second_child, second = fixture_hook()

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.click(button)
            await wait_ui(pilot, lambda: app.selected_id == second["request_id"])
            stdout, _ = first_child.communicate(timeout=3)
            assert (
                json.loads(stdout)["hookSpecificOutput"]["decision"]["behavior"]
                == choice
            )
            assert app.context_view.has_focus
            await pilot.press("enter")
            assert app.selected_id == second["request_id"]
            assert second_child.poll() is None
            stored = {record["request_id"]: record for record in records(tmp_path)}
            assert stored[first["request_id"]]["decision"]["behavior"] == choice
            assert stored[second["request_id"]]["decision"] is None

    asyncio.run(exercise())


def test_another_consumer_answer_advances_current_card_without_local_click(
    tmp_path, fixture_hook
):
    first_child, first = fixture_hook("printf 'First approval'")
    second_child, second = fixture_hook("printf 'Second approval'")

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.selected_id == first["request_id"]
            result = await asyncio.to_thread(
                queue,
                tmp_path,
                "decide",
                "--request",
                first["request_id"],
                "--decision",
                "deny",
                "--reason",
                "Explicit answer from another fixture consumer",
            )
            assert result.returncode == 0, result.stderr
            first_child.communicate(timeout=3)
            await wait_ui(pilot, lambda: app.selected_id == second["request_id"])
            assert second_child.poll() is None
            assert first["request_id"] not in app.pending_ids
            assert app.context_view.has_focus

    asyncio.run(exercise())


def test_arrival_preserves_current_conversation_and_both_scroll_positions(
    tmp_path, fixture_hook
):
    turns = [
        {"role": "user", "content": "First conversation " * 100},
        {"role": "assistant", "content": "This request is the one being inspected."},
    ]
    _, first = fixture_hook("printf '" + "long command " * 100 + "'", turns=turns)

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("pagedown")
            app.detail_view.focus()
            await pilot.press("pagedown")
            context_scroll = app.context_view.scroll_offset
            request_scroll = app.detail_view.scroll_offset
            assert context_scroll.y > 0
            assert request_scroll.y > 0
            context = app.context_view.text
            request = app.detail_view.text
            focus = app.focused
            await asyncio.to_thread(fixture_hook, "printf 'New arrival'")
            await wait_ui(pilot, lambda: app.waiting_count == 2)
            assert app.selected_id == first["request_id"]
            assert app.context_view.text == context
            assert app.detail_view.text == request
            assert app.context_view.scroll_offset == context_scroll
            assert app.detail_view.scroll_offset == request_scroll
            assert app.focused is focus

    asyncio.run(exercise())


def test_same_session_requests_stay_grouped_until_session_is_resolved(
    tmp_path, fixture_hook
):
    first_child, _first = fixture_hook("printf 'Session A first'", session="session-a")
    other_child, other = fixture_hook("printf 'Session B'", session="session-b")
    last_child, last = fixture_hook("printf 'Session A second'", session="session-a")

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.waiting_count == 2
            assert len(app.pending_ids) == 3
            assert "2" in str(app.query_one("#waiting", Static).render())
            await pilot.press("a")
            await wait_ui(pilot, lambda: app.selected_id == last["request_id"])
            first_child.communicate(timeout=3)
            assert app.waiting_count == 2
            assert other_child.poll() is None
            await pilot.press("d")
            await wait_ui(pilot, lambda: app.selected_id == other["request_id"])
            stdout, _ = last_child.communicate(timeout=3)
            assert (
                json.loads(stdout)["hookSpecificOutput"]["decision"]["behavior"]
                == "deny"
            )
            assert app.waiting_count == 1
            assert app.pending_ids == [other["request_id"]]

    asyncio.run(exercise())


def test_competing_submission_failure_stays_with_current_conversation(
    tmp_path, fixture_hook, monkeypatch
):
    first_child, first = fixture_hook()
    second_child, second = fixture_hook()

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        actual_decide = app.client.decide

        def competing_decide(request_id, choice):
            result = queue(
                tmp_path,
                "decide",
                "--request",
                request_id,
                "--decision",
                "deny",
                "--reason",
                "Competing explicit fixture answer",
            )
            assert result.returncode == 0, result.stderr
            first_child.communicate(timeout=3)
            return actual_decide(request_id, choice)

        monkeypatch.setattr(app.client, "decide", competing_decide)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await wait_ui(pilot, lambda: bool(app.last_error))
            assert app.selected_id == first["request_id"]
            assert "returned" in app.last_error
            assert json.dumps(app.last_error)[1:-1] in app.detail_view.text
            assert app.query_one("#allow", Button).disabled
            await app.refresh_board()
            assert app.selected_id == first["request_id"]
            assert second_child.poll() is None
            await pilot.press("s")
            assert app.selected_id == second["request_id"]
            assert app.last_error == ""

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "error",
    [
        subprocess.TimeoutExpired("fixture-decide", 5),
        OSError("controlled fixture I/O failure"),
    ],
)
def test_submission_io_failure_remains_visible_and_current(
    tmp_path, fixture_hook, monkeypatch, error
):
    child, request = fixture_hook()

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)

        def fail_decide(*_arguments):
            raise error

        monkeypatch.setattr(app.client, "decide", fail_decide)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("a")
            await wait_ui(pilot, lambda: bool(app.last_error))
            assert app.selected_id == request["request_id"]
            assert json.dumps(str(error))[1:-1] in app.detail_view.text
            assert app.answering is False
            assert child.poll() is None
            assert records(tmp_path)[0]["decision"] is None

    asyncio.run(exercise())


def test_refresh_io_failure_is_visible_and_disables_answers(
    tmp_path, fixture_hook, monkeypatch
):
    child, request = fixture_hook()

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()

            def failed_records():
                raise OSError("controlled fixture read failure")

            monkeypatch.setattr(app.client, "records", failed_records)
            await app.refresh_board()
            assert app.selected_id == request["request_id"]
            assert "controlled fixture read failure" in app.last_error
            assert app.query_one("#allow", Button).disabled
            assert app.query_one("#deny", Button).disabled
            assert child.poll() is None

    asyncio.run(exercise())


def test_all_demo_sessions_bubble_away_empty_then_new_request(tmp_path):
    async def exercise():
        app = BOARD.PermissionBoard(tmp_path, demo=True)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.waiting_count == 3
            original_ids = app.pending_ids.copy()
            assert all(
                record["payload"]["conversation_source"] == "generated-demo"
                for record in records(tmp_path)
            )
            for key in ("a", "d", "a"):
                previous = app.selected_id
                await pilot.press(key)
                await wait_ui(pilot, lambda old=previous: app.selected_id != old)
            assert app.selected_id is None
            assert app.pending_ids == []
            assert app.waiting_count == 0
            assert app.query_one("#allow", Button).disabled
            assert app.query_one("#deny", Button).disabled
            assert all(
                records(tmp_path)[index]["decision"] is not None for index in range(3)
            )
            assert "0" in str(app.query_one("#waiting", Static).render())
            await pilot.press("n")
            await wait_ui(pilot, lambda: app.waiting_count == 1)
            assert app.selected_id not in original_ids
            assert app.selected_id == app.pending_ids[0]
            await pilot.press("q")
        assert all(child.poll() is not None for child in app.producer.children)

    asyncio.run(exercise())


@pytest.mark.parametrize("state", ["unknown", "expired", "returned"])
def test_terminal_items_cannot_be_answered(tmp_path, fixture_hook, state):
    child, request = fixture_hook(hold=0.15 if state == "expired" else 10)
    if state == "unknown":
        child.kill()
        child.communicate(timeout=3)
    elif state == "returned":
        result = queue(
            tmp_path,
            "decide",
            "--request",
            request["request_id"],
            "--decision",
            "deny",
            "--reason",
            "Already answered control",
        )
        assert result.returncode == 0, result.stderr
        child.communicate(timeout=3)
    else:
        stdout, stderr = child.communicate(timeout=3)
        assert child.returncode == 0, stderr
        assert stdout == ""

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.records[request["request_id"]]["state"] == state
            assert app.pending_ids == []
            assert app.query_one("#allow", Button).disabled
            assert app.query_one("#deny", Button).disabled
            await pilot.press("a", "d")
            assert records(tmp_path)[0]["state"] == state

    asyncio.run(exercise())


def test_unmarked_live_request_is_excluded_from_answers(tmp_path, fixture_hook):
    child, request = fixture_hook(marked=False)

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert request["request_id"] not in app.pending_ids
            assert app.selected_id is None
            assert app.query_one("#allow", Button).disabled
            assert app.query_one("#deny", Button).disabled
            await pilot.press("a", "d")
            assert child.poll() is None
            assert records(tmp_path)[0]["decision"] is None

    asyncio.run(exercise())


def test_resizing_conversation_card_preserves_request_and_visible_controls(
    tmp_path, fixture_hook
):
    _, request = fixture_hook()

    async def exercise():
        app = BOARD.PermissionBoard(tmp_path)
        async with app.run_test(size=(107, 93)) as pilot:
            await pilot.pause()
            await pilot.resize_terminal(60, 20)
            await pilot.pause()
            assert app.selected_id == request["request_id"]
            assert "Please inspect this demo preview." in app.context_view.text
            assert (
                json.dumps(request["tool_input"]["command"])[1:-1]
                in app.detail_view.text
            )
            for selector in ("#allow", "#deny", "#next", "#new"):
                region = app.query_one(selector, Button).region
                assert region.right <= 60
                assert region.bottom <= 20

    asyncio.run(exercise())


def test_delivered_python_safe_path_command_starts_demo_in_terminal_and_quits(tmp_path):
    master, slave = pty.openpty()
    child = subprocess.Popen(
        [
            sys.executable,
            "-P",
            str(DIRECTORY / "board.py"),
            "--demo",
            "--run-dir",
            str(tmp_path),
        ],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=ROOT,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    os.close(slave)
    output = bytearray()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                output.extend(os.read(master, 65536))
            if b"DEMO" in output and len(records(tmp_path)) == 3:
                break
        assert b"DEMO" in output, output.decode(errors="replace")
        assert len(records(tmp_path)) == 3
        os.write(master, b"q")
        assert child.wait(timeout=5) == 0, output.decode(errors="replace")
        assert {record["state"] for record in records(tmp_path)} == {"unknown"}
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        os.close(master)


def source_snapshot(pane_id, window_index, *, state="running", idle_since=None):
    return SimpleNamespace(
        session_id="$0",
        session_name="main",
        window_id=f"@{window_index}",
        window_index=window_index,
        window_name="codex",
        pane_id=pane_id,
        pane_index=0,
        pane_pid=1234,
        pane_start_ticks=100,
        socket_path="/tmp/permission-board-fixture.sock",
        server_pid=123,
        server_start_ticks=50,
        state_since=None,
        state_since_source="",
        title=f"Task {window_index}",
        cwd=f"/fixture/people/Brian/project-{window_index}",
        pane_current_command="codex",
        pane_bg="#1b0e00",
        pane_fg="#ffffff",
        header_spans=[
            {"text": " Brian ", "fg": "#000000", "bg": "#6987f0", "bold": True},
            {
                "text": f" project-{window_index} ",
                "fg": "#ffffff",
                "bg": "#874600",
                "bold": True,
            },
            {"text": " main ", "fg": "#000000", "bg": "#ff0000", "bold": True},
            {
                "text": f" Task {window_index} ",
                "fg": "#000000",
                "bg": "#ffff78",
                "bold": True,
            },
        ],
        state=state,
        idle_since=idle_since,
        status_detail="Ready observed >=5 seconds" if state == "idle" else state,
        preview_ansi=(
            f"Native pane {pane_id}\nModel unavailable in fixture\n"
            "Context unavailable in fixture"
        ),
    )


class FakeSource:
    def __init__(self, snapshots):
        self.items = snapshots
        self.opened = []
        self.captured = []
        self.inputs = []

    def snapshots(self):
        return self.items.copy()

    def capture(self, snapshot):
        self.captured.append(snapshot.pane_id)
        return (
            "\x1b[31mQuestion from source "
            + snapshot.pane_id
            + "\x1b[0m\n"
            + snapshot.preview_ansi
        )

    def open_source(self, snapshot):
        self.opened.append(snapshot.pane_id)

    def send_key(self, snapshot, key, character=None):
        self.inputs.append((snapshot.pane_id, key, character))

    def send_text(self, snapshot, text):
        self.inputs.append((snapshot.pane_id, "paste", text))


async def terminal_ready(app, pilot):
    deadline = time.monotonic() + 2
    while not app.input_ready and time.monotonic() < deadline:
        await pilot.pause(0.02)
    assert app.input_ready


def test_watch_overview_lists_known_and_opted_in_panes_with_compact_readback():
    items = [source_snapshot(f"%{index}", index) for index in range(1, 51)]
    items[20].state = "unknown"
    items[20].pane_current_command = "fish"
    items[20].title = "Ordinary shell terminal"
    source = FakeSource(items)

    async def exercise():
        app = BOARD.WindowBoard(source)
        app.preferences.set_included(items[20], True)
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            assert app.table.row_count == 50
            assert app.table.virtual_size.height <= app.table.content_region.height
            assert app.focused is app.table
            assert app.native_scroll.is_on_screen
            assert app.header_scroll.is_on_screen
            assert app.table.get_row_at(49)[0] == "21.0"
            assert app.table.region.right <= app.readback.region.x
            assert app.snapshots["%21"].pane_current_command == "fish"
            await pilot.press("1", "enter")
            assert source.inputs == [("%1", "1", "1"), ("%1", "enter", None)]

    asyncio.run(exercise())


@pytest.mark.parametrize("size", [(60, 20), (107, 93), (180, 60)])
def test_watch_visible_preview_has_responsive_orientation_and_explicit_collapse(size):
    source = FakeSource([source_snapshot(f"%{index}", index) for index in range(1, 16)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            shared_area = app.table.region.area
            selected = app.selected_pane_id
            assert app.native_scroll.is_on_screen
            preview = app.readback.region
            assert app.table.region.bottom <= preview.y
            assert app.table.region.height <= len(source.items) + 2
            assert app.native_scroll.region.bottom <= app.status_view.region.y
            assert "Question from source %1" in app.native_view.content.plain
            assert app.table.virtual_size.width <= app.table.region.width
            await pilot.press("v")
            await pilot.pause()
            assert not app.native_scroll.is_on_screen
            assert app.table.region.area > shared_area
            assert app.selected_pane_id == selected
            assert app.focused is app.table
            await pilot.press("v")
            await pilot.pause()
            assert app.native_scroll.is_on_screen
            assert app.table.region.area == shared_area

    asyncio.run(exercise())


@pytest.mark.parametrize("size", [(60, 20), (180, 60)])
def test_watch_one_blocked_row_click_reveals_its_preview_after_collapse(size):
    source = FakeSource(
        [
            source_snapshot("%11", 1, state="blocked"),
            source_snapshot("%22", 2, state="blocked"),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            assert app.native_scroll.is_on_screen
            await pilot.press("v")
            await pilot.pause()
            assert not app.native_scroll.is_on_screen
            await pilot.click("#window-list", offset=(2, 2))
            await pilot.pause()
            assert app.selected_pane_id == "%22"
            assert app.native_scroll.is_on_screen
            assert "Question from source %22" in app.native_view.content.plain
            assert app.native_view.region.y >= app.native_scroll.region.y
            assert app.native_view.region.bottom <= app.native_scroll.region.bottom
            await pilot.press("2", "enter")
            assert source.inputs == [("%22", "2", "2"), ("%22", "enter", None)]

    asyncio.run(exercise())


def test_watch_resize_keeps_selection_destination_and_scrolled_preview():
    source = FakeSource([source_snapshot("%11", 1), source_snapshot("%22", 2)])
    source.capture = lambda snapshot: "\n".join(
        f"Source {snapshot.pane_id} line {index}" for index in range(150)
    )

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(107, 93)) as pilot:
            await pilot.pause()
            await pilot.click("#window-list", offset=(2, 2))
            await pilot.pause()
            app.native_scroll.scroll_to(y=20, animate=False)
            await pilot.pause()
            assert app.native_scroll.scroll_offset.y == 20
            destination = app.input_destination
            for width, height in [(180, 60), (107, 93)]:
                await pilot.resize_terminal(width, height)
                await pilot.pause()
                assert app.selected_pane_id == "%22"
                assert app.input_destination is destination
                assert app.native_scroll.scroll_offset.y == 20
                assert app.table.virtual_size.width <= app.table.region.width
            await pilot.press("3", "enter")
            assert source.inputs == [("%22", "3", "3"), ("%22", "enter", None)]

    asyncio.run(exercise())


def test_watch_age_starts_only_after_observed_transition_and_resets_on_replacement():
    now = [100.0]
    source = FakeSource(
        [
            source_snapshot("%11", 1, state="blocked"),
            source_snapshot("%22", 2, state="idle", idle_since=1),
            source_snapshot("%33", 3, state="running"),
            source_snapshot("%44", 4, state="unknown"),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source, clock=lambda: now[0])
        app.preferences.set_included(source.items[3], True)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert [app.table.get_row_at(row)[2].plain for row in range(4)] == [
                "blocked age ?",
                "idle age ?",
                "running age ?",
                "unknown age ?",
            ]
            now[0] = 175
            source.items[1].idle_since = 170
            await app.refresh_windows()
            assert [app.table.get_row_at(row)[2].plain for row in range(4)] == [
                "blocked age ?",
                "idle age ?",
                "running age ?",
                "unknown age ?",
            ]
            source.items[3].state = "running"
            await app.refresh_windows()
            assert [app.table.get_row_at(row)[2].plain for row in range(4)] == [
                "blocked age ?",
                "idle age ?",
                "running ≥0s",
                "running age ?",
            ]
            replacement = source_snapshot("%44", 4, state="running")
            replacement.pane_pid = 9999
            source.items[3] = replacement
            now[0] = 180
            await app.refresh_windows()
            assert [app.table.get_row_at(row)[0] for row in range(4)] == [
                "1.0",
                "2.0",
                "3.0",
                "4.0",
            ]
            assert app.table.get_row_at(3)[2].plain == "running age ?"

    asyncio.run(exercise())


def test_watch_resolved_running_pane_stays_before_unknown_and_newest_state_first():
    now = [100.0]
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource(
        [
            first,
            source_snapshot("%22", 2, state="unknown"),
            source_snapshot("%33", 3, state="idle"),
            source_snapshot("%44", 4, state="running"),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source, clock=lambda: now[0])
        app.preferences.set_included(
            next(p for p in source.items if p.pane_id == "%22"), True
        )
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            now[0] = 120
            first.state = "running"
            await app.refresh_windows()
            await pilot.pause()
            assert [app.table.get_row_at(row)[0] for row in range(4)] == [
                "3.0",
                "1.0",
                "4.0",
                "2.0",
            ]
            assert app.selected_pane_id == "%33"
            assert app.table.cursor_row == 0

    asyncio.run(exercise())


def test_watch_runtime_reordering_preserves_selected_pane_and_input_destination():
    now = [100.0]
    source = FakeSource(
        [
            source_snapshot("%11", 1, state="blocked"),
            source_snapshot("%22", 2, state="unknown"),
            source_snapshot("%33", 3, state="idle"),
            source_snapshot("%44", 4, state="running"),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source, clock=lambda: now[0])
        app.preferences.set_included(
            next(p for p in source.items if p.pane_id == "%22"), True
        )
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            await pilot.click("#window-list", offset=(2, 3))
            await pilot.pause()
            assert app.selected_pane_id == "%44"
            destination = app.input_destination
            source.items[1].state = "blocked"
            now[0] = 120
            await app.refresh_windows()
            await pilot.pause()
            assert [app.table.get_row_at(row)[0] for row in range(4)] == [
                "2.0",
                "1.0",
                "3.0",
                "4.0",
            ]
            assert app.selected_pane_id == "%44"
            assert app.table.cursor_row == 3
            assert app.input_destination is destination
            await pilot.press("3", "enter")
            assert source.inputs == [("%44", "3", "3"), ("%44", "enter", None)]

    asyncio.run(exercise())


def test_watch_view_selects_blocked_source_before_idle_and_unknown():
    source = FakeSource(
        [
            source_snapshot("%11", 1, state="idle", idle_since=10),
            source_snapshot("%22", 2, state="blocked"),
            source_snapshot("%33", 3),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.selected_pane_id == "%22"

    asyncio.run(exercise())


def test_watch_view_reaches_every_pane_and_opens_exact_selection():
    first = source_snapshot("%11", 1)
    second = source_snapshot("%12", 1, state="blocked")
    second.pane_index = 1
    source = FakeSource([first, second, source_snapshot("%22", 2)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.table.row_count == 3
            assert app.selected_pane_id == "%12"
            await pilot.press("alt+p", "down", "o")
            assert app.selected_pane_id == "%11"
            assert source.opened == ["%11"]

    asyncio.run(exercise())


def test_watch_attention_order_covers_all_panes_before_window_grouping():
    blocked_sibling = source_snapshot("%12", 1, state="blocked")
    blocked_sibling.pane_index = 1
    source = FakeSource(
        [
            source_snapshot("%11", 1, state="unknown"),
            blocked_sibling,
            source_snapshot("%22", 2, state="blocked"),
            source_snapshot("%33", 3, state="idle", idle_since=20),
            source_snapshot("%44", 4, state="idle", idle_since=10),
            source_snapshot("%55", 5, state="running"),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source)
        app.preferences.set_included(
            next(p for p in source.items if p.pane_id == "%11"), True
        )
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert [app.table.get_row_at(row)[0] for row in range(6)] == [
                "1.1",
                "2.0",
                "3.0",
                "4.0",
                "5.0",
                "1.0",
            ]
            await pilot.press("alt+p", "down", "o")
            assert source.opened == ["%22"]

    asyncio.run(exercise())


def test_watch_capture_failure_stays_visible_and_does_not_open_old_source():
    source = FakeSource([source_snapshot("%11", 1), source_snapshot("%22", 2)])
    original_capture = source.capture

    def capture(snapshot):
        if snapshot.pane_id == "%22":
            raise RuntimeError("pane disappeared while capturing")
        return original_capture(snapshot)

    source.capture = capture

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("alt+p", "down")
            assert "pane disappeared" in app.message
            assert app.displayed.pane_id == "%11"
            assert app.open_button.disabled
            await pilot.press("o")
            assert source.opened == []

    asyncio.run(exercise())


def test_watch_latest_text_and_refresh_preserve_actual_reading_position():
    source = FakeSource([source_snapshot("%11", 1)])

    def capture(snapshot):
        source.captured.append(snapshot.pane_id)
        return "\n".join(
            [f"Earlier conversation {n}" for n in range(100)] + ["Latest question"]
        )

    source.capture = capture

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.native_scroll.is_on_screen
            assert app.native_scroll.scroll_offset.y == app.native_scroll.max_scroll_y
            assert app.native_scroll.scroll_offset.y > 0
            app.native_scroll.focus()
            app.native_scroll.scroll_to(
                y=app.native_scroll.max_scroll_y - 5, animate=False
            )
            await pilot.pause()
            position = app.native_scroll.scroll_offset.y
            assert 0 < position < app.native_scroll.max_scroll_y
            await pilot.press("alt+p", "r")
            await pilot.pause()
            assert len(source.captured) >= 2
            assert app.native_scroll.scroll_offset.y == position
            source.items.append(source_snapshot("%22", 2, state="blocked"))
            await app.refresh_windows()
            await pilot.pause()
            assert app.table.row_count == 2
            assert app.selected_pane_id == "%11"
            assert app.native_scroll.scroll_offset.y == position
            assert len(source.captured) >= 2

    asyncio.run(exercise())


def test_watch_source_background_fills_reader_and_resets_for_default_pane():
    default = source_snapshot("%22", 2)
    default.pane_bg = default.pane_fg = "default"
    source = FakeSource([source_snapshot("%11", 1), default])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.native_scroll.is_on_screen
            assert app.native_scroll.styles.background == Color.parse("#1b0e00")
            assert app.native_scroll.styles.color == Color.parse("#ffffff")
            assert app.native_view.background_colors[1] == Color.parse("#1b0e00")
            await pilot.press("alt+p", "s")
            assert app.selected_pane_id == "%22"
            assert app.native_scroll.styles.background != Color.parse("#1b0e00")
            assert (
                app.native_view.background_colors[1]
                == app.native_scroll.background_colors[1]
            )

    asyncio.run(exercise())


def test_watch_metadata_remains_scrollable_when_readback_is_expanded():
    source = FakeSource([source_snapshot("%11", 1)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause()
            assert app.header_scroll.is_on_screen
            assert app.footer_view.region.y < app.facts_view.region.y
            assert app.identity_view.content.plain == "".join(
                span["text"] for span in source.items[0].header_spans
            )
            await pilot.press("pagedown")
            await pilot.pause()
            assert app.header_scroll.scroll_offset.y > 0
            await pilot.resize_terminal(107, 93)
            await pilot.resize_terminal(60, 20)
            await pilot.press("alt+p", "r")
            await pilot.pause()
            assert app.table.virtual_size.width <= app.table.region.width

    asyncio.run(exercise())


@pytest.mark.parametrize("focus", ["#window-list", "#source-header", "#native-source"])
def test_watch_four_answer_keys_work_from_each_area_and_other_input_is_rejected(focus):
    source = FakeSource([source_snapshot("%11", 1, state="blocked")])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            app.screen.set_focus(app.query_one(focus), scroll_visible=False)
            assert app.focused is app.query_one(focus)
            await pilot.press("1", "2", "3", "enter")
            await pilot.press("x", "y", "z", "4", "0", "backspace", "escape")
            app.post_message(events.Paste("literal [red]paste[/red]\n"))
            await pilot.pause()
            assert source.inputs == [
                ("%11", "1", "1"),
                ("%11", "2", "2"),
                ("%11", "3", "3"),
                ("%11", "enter", None),
            ]
            assert app.selected_pane_id == "%11"
            await pilot.press("o")
            assert source.opened == ["%11"]
            await pilot.press("ctrl+q")

    asyncio.run(exercise())


def test_watch_one_mouse_selection_targets_exact_pane_for_answers():
    source = FakeSource([source_snapshot("%11", 1), source_snapshot("%22", 2)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.click("#window-list", offset=(2, 2))
            await pilot.pause()
            assert app.selected_pane_id == "%22"
            assert app.focused is app.table
            await pilot.press("2", "enter")
            assert source.inputs == [("%22", "2", "2"), ("%22", "enter", None)]

    asyncio.run(exercise())


def test_watch_verified_resolution_advances_without_requiring_local_submit():
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2, state="blocked")])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            first.state = "running"
            await app.refresh_windows()
            await pilot.pause()
            assert app.selected_pane_id == "%22"
            assert app.focused is app.table
            assert app.table.row_count == 2
            await terminal_ready(app, pilot)
            await pilot.press("1", "enter")
            assert source.inputs == [("%22", "1", "1"), ("%22", "enter", None)]

    asyncio.run(exercise())


def test_watch_unknown_transition_and_arrival_do_not_advance():
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2, state="blocked")])

    async def exercise():
        app = BOARD.WindowBoard(source)
        app.preferences.set_included(
            next(p for p in source.items if p.pane_id == "%11"), True
        )
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            assert app.selected_pane_id == "%11"
            first.state = "unknown"
            source.items.append(source_snapshot("%33", 3, state="blocked"))
            await app.refresh_windows()
            await pilot.pause()
            assert app.table.row_count == 3
            assert app.selected_pane_id == "%11"

    asyncio.run(exercise())


def test_watch_idle_to_running_advances_only_after_successful_user_input():
    first = source_snapshot("%11", 1, state="idle", idle_since=10)
    source = FakeSource([first, source_snapshot("%22", 2, state="idle", idle_since=20)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("1", "enter")
            first.state = "running"
            await app.refresh_windows()
            await pilot.pause()
            assert app.selected_pane_id == "%22"
            assert app.focused is app.table

    asyncio.run(exercise())


def test_watch_failed_native_input_keeps_source_and_error_visible():
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2, state="blocked")])

    def fail(*_args):
        raise RuntimeError("source process was replaced")

    source.send_key = fail

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            assert "source process was replaced" in app.message
            first.state = "running"
            await app.refresh_windows()
            await pilot.pause()
            assert app.selected_pane_id == "%11"
            assert "source process was replaced" in app.message

    asyncio.run(exercise())


def test_watch_queued_input_never_retargets_after_observed_resolution():
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2, state="blocked")])
    entered = threading.Event()
    release = threading.Event()

    def send(snapshot, key, character=None):
        if key == "enter":
            entered.set()
            if not release.wait(timeout=3):
                raise RuntimeError("test input collector not released")
        source.inputs.append((snapshot.pane_id, key, character))

    source.send_key = send

    async def exercise():
        app = BOARD.WindowBoard(source)
        try:
            async with app.run_test(size=(60, 20)) as pilot:
                await pilot.pause()
                app.post_message(events.Key("enter", None))
                assert await asyncio.to_thread(entered.wait, 1)
                stale = [events.Key("1", "1"), events.Key("enter", None)]
                app.post_message(events.Key("3", "3"))
                await pilot.pause()
                first.state = "running"
                await app.refresh_windows()
                assert app.selected_pane_id == "%11"
                release.set()
                await pilot.pause()
                await app.refresh_windows()
                await pilot.pause()
                assert app.selected_pane_id == "%22"
                await terminal_ready(app, pilot)
                for event in stale:
                    app.post_message(event)
                await pilot.press("2")
                assert source.inputs == [
                    ("%11", "enter", None),
                    ("%11", "3", "3"),
                    ("%22", "2", "2"),
                ]
        finally:
            release.set()

    asyncio.run(exercise())


def test_watch_repeated_enter_is_suppressed_until_next_source_input_is_quiet():
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2, state="blocked")])
    original_send = source.send_key

    def send(snapshot, key, character=None):
        original_send(snapshot, key, character)
        if snapshot.pane_id == "%11" and key == "enter":
            first.state = "running"

    source.send_key = send

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.selected_pane_id == "%22"
            assert "Releasing previous input" in app.message
            assert not app.input_ready
            await pilot.pause(0.5)
            assert not app.input_ready
            for _ in range(3):
                await pilot.press("enter")
                await app.refresh_windows()
                assert not app.input_ready
            await terminal_ready(app, pilot)
            assert "Ready: 1/2/3 + Enter" in app.message
            assert app.focused is app.table
            await pilot.press("2", "enter")
            assert source.inputs == [
                ("%11", "enter", None),
                ("%22", "2", "2"),
                ("%22", "enter", None),
            ]

    asyncio.run(exercise())


def test_watch_browse_key_batch_changes_route_before_open_key():
    source = FakeSource([source_snapshot("%11", 1)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            app.post_message(events.Key("alt+p", None))
            app.post_message(events.Key("o", "o"))
            await pilot.pause()
            assert source.opened == ["%11"]
            assert source.inputs == []
            assert app.focused is app.table
            await app.refresh_windows()
            assert "Ready: 1/2/3 + Enter" in app.message

    asyncio.run(exercise())


def test_terminal_alt_p_bytes_focus_source_list(tmp_path):
    probe = tmp_path / "alt_p_probe.py"
    state = tmp_path / "focus.json"
    probe.write_text(f"""import importlib.util, json, sys
from pathlib import Path
from types import SimpleNamespace
spec = importlib.util.spec_from_file_location(
    'alt_p_board', {str(DIRECTORY / "board.py")!r})
board = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = board
spec.loader.exec_module(board)
snapshot = SimpleNamespace(**{vars(source_snapshot("%11", 1))!r})
target = Path({str(state)!r})
class Source:
    def snapshots(self): return [snapshot]
    def capture(self, snapshot): return 'ALT_P_TERMINAL_FIXTURE'
class Probe(board.WindowBoard):
    async def on_mount(self):
        await super().on_mount()
        self.action_read_identity()
        self.set_interval(0.02, self.observe)
    def observe(self):
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps({{'focus': getattr(self.focused, 'id', None)}}))
        temporary.replace(target)
Probe(Source()).run()
""")
    master, slave = pty.openpty()
    child = subprocess.Popen(
        [sys.executable, "-P", str(probe)],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=ROOT,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    os.close(slave)
    output = bytearray()

    def until_focus(expected):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.02)[0]:
                output.extend(os.read(master, 65536))
            if state.exists() and json.loads(state.read_text())["focus"] == expected:
                return
        pytest.fail(output.decode(errors="replace"))

    try:
        until_focus("source-header")
        os.write(master, b"\x1bp")
        until_focus("window-list")
        os.write(master, b"\x11")
        assert child.wait(timeout=5) == 0, output.decode(errors="replace")
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        os.close(master)


def test_watch_browsing_is_not_overridden_by_pending_terminal_activation():
    source = FakeSource([source_snapshot("%11", 1)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            await app.action_refresh_source()
            app.action_browse_sources()
            await pilot.pause()
            assert app.focused is app.table
            assert "Ready: 1/2/3 + Enter" in app.message
            await pilot.press("o")
            assert source.opened == ["%11"]
            assert source.inputs == []

    asyncio.run(exercise())


def test_watch_sparse_terminal_keeps_latest_approval_visible_above_blank_tail():
    source = FakeSource([source_snapshot("%11", 1, state="blocked")])
    source.capture = lambda _snapshot: (
        "\x1b[31mVisible native approval\n1. Yes\n2. No\x1b[0m\n"
        + "\x1b[44m \x1b[0m\n" * 70
    )

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.native_scroll.is_on_screen
            assert "Visible native approval" in app.native_view.content.plain
            assert app.native_view.region.bottom <= app.native_scroll.region.bottom
            assert app.native_scroll.scroll_offset.y == 0

    asyncio.run(exercise())


def test_watch_failed_observation_disables_input_until_same_source_recovers():
    source = FakeSource([source_snapshot("%11", 1)])
    original = source.snapshots

    def fail():
        raise RuntimeError("source scan unavailable")

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            source.snapshots = fail
            await app.refresh_windows()
            assert "source scan unavailable" in app.message
            assert not app.input_ready
            await pilot.press("enter")
            assert source.inputs == []
            source.snapshots = original
            await app.refresh_windows()
            await terminal_ready(app, pilot)
            await pilot.press("3")
            assert source.inputs == [("%11", "3", "3")]

    asyncio.run(exercise())


def test_watch_no_known_waiting_source_stops_forwarding_and_keeps_list_available():
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            first.state = "running"
            await app.refresh_windows()
            await pilot.pause()
            assert app.selected_pane_id is None
            assert "Nothing waiting" in app.message
            assert app.table.row_count == 2
            await pilot.press("enter")
            assert source.inputs == []

    asyncio.run(exercise())


def test_watch_same_pane_process_replacement_requires_deliberate_selection():
    first = source_snapshot("%11", 1, state="blocked")
    first.foreground_pid = 100
    first.foreground_start_ticks = 500
    source = FakeSource([first])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            replacement = source_snapshot("%11", 1)
            replacement.pane_current_command = "fish"
            replacement.foreground_pid = 200
            replacement.foreground_start_ticks = 600
            source.items[0] = replacement
            await app.refresh_windows()
            await pilot.pause()
            assert "Source process changed" in app.message
            await pilot.press("enter")
            assert source.inputs == []
            await pilot.click("#window-list", offset=(2, 1))
            await pilot.pause()
            await pilot.press("3")
            assert source.inputs == [("%11", "3", "3")]

    asyncio.run(exercise())


@pytest.mark.parametrize("arrival", ["new-ready", "new-blocked"])
def test_watch_empty_attention_accepts_new_work_without_resurrecting_same_idle(arrival):
    first = source_snapshot("%11", 1, state="blocked")
    source = FakeSource([first, source_snapshot("%22", 2)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            first.state = "idle"
            first.idle_since = 20
            await app.refresh_windows()
            await pilot.pause()
            assert app.selected_pane_id is None
            await app.refresh_windows()
            assert app.selected_pane_id is None
            assert "Nothing waiting" in app.message
            if arrival == "new-ready":
                first.idle_since = 30
                expected = "%11"
            else:
                source.items.append(source_snapshot("%33", 3, state="blocked"))
                expected = "%33"
            await app.refresh_windows()
            await pilot.pause()
            assert app.selected_pane_id == expected
            assert app.focused is app.table
            await pilot.press("3")
            assert source.inputs == [(expected, "3", "3")]

    asyncio.run(exercise())


@pytest.fixture(autouse=True)
def isolated_viewer_preferences(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


def test_watch_unknown_panes_are_individually_added_removed_and_persisted(tmp_path):
    known = source_snapshot("%11", 1, state="blocked")
    unknown = source_snapshot("%22", 2, state="unknown")
    other = source_snapshot("%33", 3, state="unknown")
    source = FakeSource([known, unknown, other])
    preference_path = tmp_path / "preferences" / "panes.json"

    async def exercise():
        app = BOARD.WindowBoard(source, preference_path=preference_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.table.row_count == 1
            assert "Add panes" in str(app.query_one("#watch-keys", Static).content)
            await pilot.press("a")
            await pilot.pause()
            picker = app.screen
            assert picker.table.row_count == 2
            assert picker.table.get_row_at(picker.table.cursor_row)[1].plain.endswith(
                "Task 2 "
            )
            await pilot.press("1", "enter", "3")
            assert source.inputs == []
            await pilot.press("space", "escape")
            await pilot.pause()
            assert app.table.row_count == 2
            assert app.selected_pane_id == "%22"
            assert app.native_scroll.is_on_screen
            assert "Question from source %22" in app.native_view.content.plain
        restarted = BOARD.WindowBoard(source, preference_path=preference_path)
        async with restarted.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert restarted.pane_order == ["%11", "%22"]
            await pilot.press("a", "space", "escape")
            await pilot.pause()
            assert restarted.pane_order == ["%11"]
        final = BOARD.WindowBoard(source, preference_path=preference_path)
        async with final.run_test() as pilot:
            await pilot.pause()
            assert final.pane_order == ["%11"]

    asyncio.run(exercise())


def test_pane_preferences_follow_base_pane_but_refuse_reused_server_or_pane(tmp_path):
    preferences = BOARD.PanePreferences(tmp_path / "panes.json")
    pane = source_snapshot("%11", 1, state="unknown")
    preferences.set_included(pane, True)
    assert preferences.includes(pane)
    pane.pane_current_command = "fish"
    pane.foreground_pid = 9876
    assert BOARD.PanePreferences(preferences.path).includes(pane)
    pane.pane_start_ticks += 1
    assert not preferences.includes(pane)
    preferences.set_included(pane, True)
    assert preferences.includes(pane)
    pane.server_start_ticks += 1
    assert not preferences.includes(pane)
    pane.pane_start_ticks = None
    with pytest.raises(RuntimeError, match="identity"):
        preferences.set_included(pane, True)


def test_watch_newest_state_first_prefers_verified_history_without_changing_selection():
    recent = source_snapshot("%11", 1, state="blocked")
    old = source_snapshot("%22", 2, state="blocked")
    recent.state_since, recent.state_since_source = 990, "fixture transition record"
    old.state_since, old.state_since_source = 900, "fixture transition record"
    source = FakeSource([old, recent])

    async def exercise():
        app = BOARD.WindowBoard(source, clock=lambda: 100, wall_clock=lambda: 1000)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.pane_order == ["%11", "%22"]
            assert app.table.get_row_at(0)[2].plain == "blocked 10s"
            assert "fixture transition record" in app.facts_view.content
            recent.state_since = 850
            await app.refresh_windows()
            assert app.pane_order == ["%22", "%11"]
            assert app.selected_pane_id == "%11"
            assert app.table.cursor_row == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("size", [(60, 30), (107, 93), (180, 60)])
def test_watch_small_list_gives_unused_space_to_preview(size):
    source = FakeSource([source_snapshot("%11", 1), source_snapshot("%22", 2)])

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            assert app.table.region.height <= app.table.row_count + 3
            assert app.native_scroll.region.height >= 5
            assert app.native_scroll.is_on_screen

    asyncio.run(exercise())


def test_watch_invalid_preferences_remain_visible_and_are_never_overwritten(tmp_path):
    preference_path = tmp_path / "panes.json"
    preference_path.write_text("not valid JSON")
    source = FakeSource(
        [
            source_snapshot("%11", 1, state="blocked"),
            source_snapshot("%22", 2, state="unknown"),
        ]
    )

    async def exercise():
        app = BOARD.WindowBoard(source, preference_path=preference_path)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.pane_order == ["%11"]
            assert "Cannot read pane choices" in app.status_view.content
            await pilot.press("a")
            await pilot.pause()
            assert (
                "Cannot read pane choices"
                in app.screen.query_one("#picker-status", Static).content
            )
            await pilot.press("space", "1", "enter", "escape")
            await pilot.pause()
            assert preference_path.read_text() == "not valid JSON"
            assert source.inputs == []
            assert app.pane_order == ["%11"]

    asyncio.run(exercise())


def test_watch_unmeasured_initial_state_follows_timed_states_without_inventing_age():
    unmeasured = source_snapshot("%11", 1, state="idle")
    measured = source_snapshot("%22", 2, state="idle")
    measured.state_since, measured.state_since_source = 900, "fixture transition record"
    source = FakeSource([unmeasured, measured])
    now = [100.0]

    async def exercise():
        app = BOARD.WindowBoard(source, clock=lambda: now[0], wall_clock=lambda: 1000)
        async with app.run_test(size=(60, 20)) as pilot:
            await pilot.pause()
            assert app.pane_order == ["%22", "%11"]
            assert app.selected_pane_id == "%22"
            assert app.table.get_row_at(1)[2].plain == "idle age ?"
            now[0] = 175
            await app.refresh_windows()
            assert app.pane_order == ["%22", "%11"]
            assert app.table.get_row_at(1)[2].plain == "idle age ?"
            unmeasured.state = "running"
            await app.refresh_windows()
            assert app.table.get_row_at(1)[2].plain == "running ≥0s"
            now[0] = 250
            await app.refresh_windows()
            assert app.table.get_row_at(1)[2].plain == "running ≥1m"
            assert app.selected_pane_id == "%22"

    asyncio.run(exercise())


def test_daemon_approval_displays_full_request_and_enter_sends_exact_choice_once():
    pane = source_snapshot("codex:thread-a", 0, state="blocked")
    pane.thread_id = "thread-a"
    pane.native_pane = None
    pane.approvals = (
        SimpleNamespace(
            occurrence_id="generation:request-a",
            thread_id="thread-a",
            method="item/commandExecution/requestApproval",
            params={"command": "printf harmless", "reason": "Full approval reason"},
            decisions=("accept", "decline", "cancel"),
        ),
    )
    source = FakeSource([pane])
    source.select = lambda selected: selected
    answered = []
    source.answer = lambda selected, occurrence, decision: answered.append(
        (selected.thread_id, occurrence, decision)
    )

    async def exercise():
        app = BOARD.WindowBoard(source)
        async with app.run_test(size=(90, 30)) as pilot:
            await pilot.pause()
            assert "Full approval reason" in app.native_view.render().plain
            await pilot.press("enter")
            assert answered == []
            await pilot.press("2")
            assert answered == []
            await pilot.press("enter")
            await pilot.pause()
            assert answered == [("thread-a", "generation:request-a", "decline")]
            assert source.inputs == []
            await pilot.press("enter")
            await pilot.pause()
            assert len(answered) == 1

    asyncio.run(exercise())
