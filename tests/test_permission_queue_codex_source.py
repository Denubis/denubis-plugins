"""Exercise the pane view's current-daemon state and exact request routing."""

from types import SimpleNamespace

import pytest
from test_permission_queue_source import SOURCE, SourceFixture

THREAD = "11111111-1111-4111-8111-111111111111"


class Server:
    def __init__(self):
        self.reads = []
        self.selected = []
        self.answers = []
        self.failure = None
        self.thread = SimpleNamespace(
            thread_id=THREAD,
            state="idle",
            state_since=1020.0,
            state_since_source="Codex turn completedAt",
            requests=(),
            title="Task",
            cwd="/repo/project",
            recent_turns=(),
        )

    def loaded_threads(self):
        if self.failure:
            raise RuntimeError(self.failure)
        return [THREAD]

    def snapshot(self, thread_id):
        self.reads.append(thread_id)
        return self.thread

    def select(self, thread_id):
        self.selected.append(thread_id)
        return self.thread

    def answer(self, occurrence_id, decision):
        self.answers.append((occurrence_id, decision))
        return SimpleNamespace(resolved=True)

    def close(self):
        pass


@pytest.fixture
def linked(monkeypatch):
    fixture = SourceFixture()
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    monkeypatch.setattr(SOURCE, "foreground_identity", lambda pid: (42, 99))
    server = Server()
    source = SOURCE.TmuxSource(codex=server)
    monkeypatch.setattr(source, "thread_for_pane", lambda data, preview, loaded: THREAD)
    return source, server, fixture


def test_daemon_state_and_history_override_stale_native_title_without_attaching(linked):
    source, server, fixture = linked
    fixture.title = "Working | stale terminal title"
    pane = source.snapshots()[0]
    assert (pane.state, pane.state_since, pane.thread_id) == ("idle", 1020.0, THREAD)
    assert server.reads == [THREAD]
    assert server.selected == []
    server.thread.state = "blocked"
    server.thread.state_since = None
    assert source.snapshots()[0].state == "blocked"


def test_unlinked_codex_stays_visible_and_never_guesses_by_directory(
    linked, monkeypatch
):
    source, server, fixture = linked
    monkeypatch.setattr(source, "thread_for_pane", lambda *args: None)
    pane = source.snapshots()[0]
    assert pane.state == "idle"
    assert "statusline" not in pane.status_detail
    assert server.selected == []
    assert pane.thread_id == ""
    fixture.command = "fish"
    assert source.snapshots()[0].state == "unknown"


def test_disconnect_discards_old_state_and_reports_reason(linked):
    source, server, _ = linked
    assert source.snapshots()[0].state == "idle"
    server.failure = "daemon disconnected"
    pane = source.snapshots()[0]
    assert pane.state == "idle"
    assert pane.state_since is None
    assert "daemon disconnected" in source.last_error


def test_selected_request_answers_exact_occurrence_without_tmux_input(linked):
    source, server, fixture = linked
    request = SimpleNamespace(
        occurrence_id="connection1:request8",
        thread_id=THREAD,
        decisions=("accept", "decline", "cancel"),
    )
    server.thread.requests = (request,)
    pane = source.select(source.snapshots()[0])
    assert pane.approvals == (request,)
    source.answer(pane, request.occurrence_id, "decline")
    assert server.answers == [(request.occurrence_id, "decline")]
    assert not any("send-keys" in call for call in fixture.calls)


def test_request_from_another_thread_is_refused_before_answer(linked):
    source, server, _ = linked
    pane = source.snapshots()[0]
    with pytest.raises(RuntimeError, match="not part"):
        source.answer(pane, "other-request", "accept")
    assert server.answers == []


def test_footer_disappearing_keeps_one_real_pane_row_without_standalone_sessions(
    linked, monkeypatch
):
    source, _server, _ = linked
    original = source.snapshots()[0]
    monkeypatch.setattr(source, "thread_for_pane", lambda *args: None)
    panes = source.snapshots()
    assert len(panes) == 1
    assert panes[0].pane_id == original.pane_id == "%4"
    assert panes[0].thread_id == ""
    assert panes[0].state == "idle"
    assert panes[0].header_spans == original.header_spans


def test_one_thread_read_failure_does_not_hide_healthy_sessions(linked, monkeypatch):
    source, server, _ = linked
    monkeypatch.setattr(server, "loaded_threads", lambda: ["gone", THREAD])
    original = server.snapshot

    def read(thread_id):
        if thread_id == "gone":
            raise RuntimeError("thread unloaded")
        return original(thread_id)

    monkeypatch.setattr(server, "snapshot", read)
    panes = source.snapshots()
    assert any(pane.thread_id == THREAD and pane.state == "idle" for pane in panes)
    assert "thread unloaded" in source.last_error


def test_changed_native_footer_uses_server_conversation_not_wrong_pane(
    linked, monkeypatch
):
    source, server, fixture = linked
    server.thread.recent_turns = (
        {"items": [{"type": "agentMessage", "text": "Exact server context"}]},
    )
    pane = source.snapshots()[0]
    fixture.screen = "UNRELATED CURRENT SESSION"
    monkeypatch.setattr(source, "thread_for_pane", lambda *args: None)
    assert "Exact server context" in source.capture(pane)
    assert "UNRELATED" not in source.capture(pane)


def test_daemon_without_any_pane_never_appears_in_window_view(linked, monkeypatch):
    source, _server, _ = linked
    command = source.command
    monkeypatch.setattr(
        source,
        "command",
        lambda verb, *args, **kwargs: (
            "" if verb == "list-panes" else command(verb, *args, **kwargs)
        ),
    )
    assert source.snapshots() == []


@pytest.mark.parametrize("native_state", ["idle", "running", "blocked", "unknown"])
def test_claude_native_record_enriches_actual_pane(linked, monkeypatch, native_state):
    source, _, fixture = linked
    fixture.command = "claude"
    monkeypatch.setattr(source, "thread_for_pane", lambda *args: None)
    source.claude = SimpleNamespace(
        for_pane=lambda pane: SimpleNamespace(
            state=native_state,
            state_since=1020.0,
            state_since_source="Claude native statusUpdatedAt",
            approximate=True,
            status_detail="Claude native status",
        )
    )
    panes = source.snapshots()
    assert len(panes) == 1
    pane = panes[0]
    assert pane.pane_id == "%4"
    assert pane.state == ("unverified" if native_state == "unknown" else native_state)
    assert pane.state_since == 1020.0
    assert pane.state_approximate
    assert pane.thread_id == ""
