"""Drive daemon-backed approvals through Textual and a fixture Unix WebSocket."""

from __future__ import annotations

import asyncio
import time

from test_permission_queue_board import BOARD
from test_permission_queue_codex_server import (
    adapter_module,
)
from test_permission_queue_codex_server import (
    daemon as daemon,  # noqa: PLC0414 — pytest fixture re-export
)
from test_permission_queue_source import SOURCE


class DaemonSource(SOURCE.TmuxSource):
    """Exercise the production session/answer paths without requiring tmux."""

    def snapshots(self):
        return [
            self.thread_view(self.client().snapshot(thread_id))
            for thread_id in self.client().loaded_threads()
        ]


async def wait_for(pilot, condition, *, timeout=3):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        await pilot.pause(0.02)
    assert condition()


def test_new_request_requires_fresh_choice_and_shows_daemon_context(daemon, tmp_path):
    daemon.status = {"type": "active", "activeFlags": ["waitingOnApproval"]}
    module = adapter_module()

    async def exercise(client):
        source = DaemonSource(codex=client)
        app = BOARD.WindowBoard(source, preference_path=tmp_path / "panes.json")
        async with app.run_test(size=(100, 38)) as pilot:
            await wait_for(pilot, lambda: app.input_ready)
            assert app.native_view.is_on_screen
            assert app.facts_view.is_on_screen
            assert "Full conversation context" in app.native_view.render().plain
            assert "printf 'harmless fixture'" in app.native_view.render().plain
            assert "thread-1" in app.facts_view.render().plain
            assert "/fixture" in app.facts_view.render().plain
            await pilot.press("1")

            daemon.resolved()
            replacement = daemon.request()
            replacement["id"] = 43
            replacement["params"]["command"] = "printf 'replacement request'"
            daemon.broadcast(replacement)
            daemon.resolved = lambda: daemon.broadcast(
                {
                    "method": "serverRequest/resolved",
                    "params": {"threadId": "thread-1", "requestId": 43},
                }
            )
            await app.action_refresh_source()
            assert "replacement request" in app.native_view.render().plain

            await pilot.press("enter")
            # Establish an RPC ordering barrier after the attempted stale choice.
            await asyncio.to_thread(client.snapshot, "thread-1")
            assert daemon.answers == []

            await pilot.press("2", "enter")
            await wait_for(pilot, lambda: bool(daemon.answers) and not app.sending)
            assert daemon.answers == [{"id": 43, "result": {"decision": "decline"}}]
            await pilot.press("enter")
            await asyncio.to_thread(client.snapshot, "thread-1")
            assert len(daemon.answers) == 1

    with module.CodexServer(daemon.path) as client:
        asyncio.run(exercise(client))


def test_external_resolution_advances_to_next_daemon_session(daemon, tmp_path):
    daemon.loaded = ["thread-1", "thread-2"]
    daemon.status = {"type": "active", "activeFlags": ["waitingOnApproval"]}
    module = adapter_module()

    async def exercise(client):
        app = BOARD.WindowBoard(
            DaemonSource(codex=client), preference_path=tmp_path / "panes.json"
        )
        async with app.run_test(size=(100, 38)) as pilot:
            await wait_for(pilot, lambda: app.input_ready)
            assert app.displayed.thread_id == "thread-1"
            daemon.resolved()
            daemon.status = {"type": "idle"}
            await app.refresh_windows()
            await wait_for(
                pilot,
                lambda: (
                    app.displayed is not None and app.displayed.thread_id == "thread-2"
                ),
            )
            assert app.displayed.state == "idle"
            assert "Full conversation context" in app.native_view.render().plain
            assert app.displayed.approvals[0].thread_id == "thread-2"
            assert daemon.answers == []

    with module.CodexServer(daemon.path) as client:
        asyncio.run(exercise(client))


def test_ctrl_c_closes_view_and_main_releases_daemon_connection(
    daemon, tmp_path, monkeypatch
):
    module = adapter_module()
    client = module.CodexServer(daemon.path)
    source = DaemonSource(codex=client)

    async def exercise(app):
        async with app.run_test(size=(100, 38)) as pilot:
            await wait_for(pilot, lambda: app.displayed is not None)
            assert daemon.connections
            await pilot.press("ctrl+c")
            await wait_for(pilot, lambda: not app.is_running)

    monkeypatch.setattr(BOARD, "load_source", lambda session, socket: source)
    monkeypatch.setattr(
        BOARD.WindowBoard, "run", lambda app: asyncio.run(exercise(app))
    )
    monkeypatch.setattr(BOARD.sys, "argv", ["board.py", "--watch-session", "fixture"])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    try:
        assert BOARD.main() == 0
        assert daemon.connections
        assert all(
            connection.close_code is not None for connection in daemon.connections
        )
        assert daemon.answers == []
    finally:
        source.close()
