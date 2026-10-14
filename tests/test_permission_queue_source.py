"""Check source observations without changing any user's tmux server."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from test_permission_queue_launch import ScratchServer, until

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments" / "permission-queue" / "tmux_source.py"
SPEC = importlib.util.spec_from_file_location("permission_tmux_source", PATH)
assert SPEC is not None and SPEC.loader is not None
SOURCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SOURCE
SPEC.loader.exec_module(SOURCE)


class SourceFixture:
    def __init__(self):
        self.title = "Ready | project | main | Ask about wording | GPT-6-Astra medium"
        self.command = "codex"
        self.pid = "123"
        self.screen = "• Is this wording suitable?\n\u203a \nContext 59% left\n"
        self.calls = []
        self.runtime = None

    def run(self, arguments, **_kwargs):
        self.calls.append(arguments)
        verb = arguments[1]
        if verb == "list-panes":
            output = (
                "\t".join(
                    [
                        "$0",
                        "main",
                        "@3",
                        "7",
                        "codex",
                        "%4",
                        "0",
                        self.pid,
                        self.title,
                        "/repo/project",
                        self.command,
                        "#1b0e00",
                        "default",
                        "20",
                    ]
                )
                + "\n"
            )
        elif verb == "capture-pane":
            output = (
                "Earlier bounded history\n" if "-200" in arguments else ""
            ) + self.screen
        elif verb == "show-environment":
            if self.runtime is None:
                return subprocess.CompletedProcess(arguments, 1, "", "unknown variable")
            output = f"XDG_RUNTIME_DIR={self.runtime}\n"
        elif verb == "display-message":
            output = f"$0\t@3\t%4\t{self.pid}\t20\n"
        else:
            raise AssertionError(f"unexpected fixture command: {arguments}")
        return subprocess.CompletedProcess(arguments, 0, output, "")


def test_native_ready_question_is_idle_observation_not_terminal_silence(monkeypatch):
    fixture = SourceFixture()
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    monkeypatch.setattr(SOURCE.time, "monotonic", lambda: 100.0)
    source = SOURCE.TmuxSource()
    snapshot = source.snapshots()[0]
    assert snapshot.state == "idle"
    assert snapshot.idle_since == 100.0
    assert "observed" in snapshot.status_detail.lower()
    assert snapshot.preview_ansi == fixture.screen
    assert snapshot.pane_id == "%4"
    assert snapshot.window_id == "@3"
    assert snapshot.window_index == 7
    assert snapshot.pane_bg == "#1b0e00"


def test_ready_age_resets_for_new_message_busy_state_and_process(monkeypatch):
    fixture = SourceFixture()
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    clock = [100.0]
    monkeypatch.setattr(SOURCE.time, "monotonic", lambda: clock[0])
    source = SOURCE.TmuxSource()
    assert source.snapshots()[0].idle_since == 100.0
    clock[0] = 160.0
    same = source.snapshots()[0]
    assert same.idle_since == 100.0
    assert "60s ago" in same.status_detail
    fixture.screen = "• A different question?\n\u203a \nContext 58% left\n"
    clock[0] = 200.0
    assert source.snapshots()[0].idle_since == 200.0
    fixture.title = (
        "Working | project | main | Ready is a task label | GPT-6-Astra medium"
    )
    assert source.snapshots()[0].state == "running"
    fixture.title = "Ready | project | main | Task | GPT-6-Astra medium"
    clock[0] = 250.0
    assert source.snapshots()[0].idle_since == 250.0
    fixture.pid = "456"
    clock[0] = 300.0
    assert source.snapshots()[0].idle_since == 300.0


@pytest.mark.parametrize(
    "title,screen",
    [
        (
            "Ready | project | main | Task | model",
            "Would you like to run this command?\n1. Yes\n2. No\n",
        ),
        (
            "[ ! ] Action Required | project | main | Task | model",
            "1 question queued\n",
        ),
    ],
)
def test_native_pending_action_preempts_idle_without_permission_hook(
    monkeypatch, title, screen
):
    fixture = SourceFixture()
    fixture.title, fixture.screen = title, screen
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    snapshot = SOURCE.TmuxSource().snapshots()[0]
    assert snapshot.state == "blocked"
    assert snapshot.idle_since is None


@pytest.mark.parametrize(
    "command,title",
    [
        ("bash", "✳ Ready task"),
        ("fish", "Ready | project | main | Task | model"),
        ("codex", "Unknown | project | main | Ready task | model"),
    ],
)
def test_unverified_provider_or_title_remains_unknown(monkeypatch, command, title):
    fixture = SourceFixture()
    fixture.command, fixture.title, fixture.screen = command, title, ""
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    snapshot = SOURCE.TmuxSource().snapshots()[0]
    assert snapshot.state == "unknown"
    assert snapshot.idle_since is None
    assert "unknown" in snapshot.status_detail.lower()


@pytest.mark.parametrize(
    "task", ["Fix working directory", "Review action required wording"]
)
def test_task_words_cannot_spoof_the_leading_ready_state(monkeypatch, task):
    fixture = SourceFixture()
    fixture.title = f"Ready | project | main | {task} | GPT-6-Astra medium"
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    assert SOURCE.TmuxSource().snapshots()[0].state == "idle"


def test_exact_cached_header_colours_and_literal_escaped_style_are_read_only(
    monkeypatch, tmp_path
):
    fixture = SourceFixture()
    fixture.runtime = tmp_path
    key = hashlib.md5(
        ("/repo/project\n" + fixture.title).encode(), usedforsecurity=False
    ).hexdigest()
    cache = tmp_path / f"branch-bg-{os.getuid()}" / key
    cache.parent.mkdir()
    content = (
        "#[bg=#874600,fg=#ffffff,bold] project ##[bg=#ff0000] "
        "#[bg=#ff0000,fg=#000000,bold] main #[default]\n#1b0e00\n"
    )
    cache.write_text(content)
    before = cache.stat().st_mtime_ns
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    snapshot = SOURCE.TmuxSource().snapshots()[0]
    assert snapshot.header_spans == [
        {
            "text": " project #[bg=#ff0000] ",
            "fg": "#ffffff",
            "bg": "#874600",
            "bold": True,
        },
        {"text": " main ", "fg": "#000000", "bg": "#ff0000", "bold": True},
    ]
    assert cache.read_text() == content
    assert cache.stat().st_mtime_ns == before
    assert "header unavailable" not in snapshot.status_detail
    assert all(
        call[1] in {"list-panes", "capture-pane", "show-environment"}
        for call in fixture.calls
    )


def test_capture_includes_bounded_history_and_preserves_native_ansi(monkeypatch):
    fixture = SourceFixture()
    fixture.screen += "\x1b[38;2;246;226;183mGPT-6-Astra medium\x1b[0m\n"
    monkeypatch.setattr(SOURCE.subprocess, "run", fixture.run)
    source = SOURCE.TmuxSource()
    snapshot = source.snapshots()[0]
    captured = source.capture(snapshot)
    assert captured == "Earlier bounded history\n" + fixture.screen


@pytest.fixture
def scratch(tmp_path):
    server = ScratchServer(tmp_path)
    yield server
    server.close()


def test_open_source_switches_only_sole_viewer_to_exact_source_window_pane(
    scratch, monkeypatch
):
    scratch.new_work("work")
    scratch.command("new-window", "-d", "-t", "work", "sleep 3600")
    scratch.command("split-window", "-d", "-t", "work:1", "sleep 3600")
    scratch.new_work("board")
    _, _, client = scratch.attach("board")
    board_pane = scratch.command(
        "display-message", "-p", "-t", "board:", "#{pane_id}"
    ).stdout.strip()
    assert board_pane.startswith("%")
    monkeypatch.setenv("TMUX_PANE", board_pane)
    source = SOURCE.TmuxSource(session="work", socket=scratch.socket)
    target = next(
        pane
        for pane in source.snapshots()
        if pane.window_index == 1 and pane.pane_index == 1
    )
    source.open_source(target)
    actual = scratch.command(
        "display-message",
        "-p",
        "-c",
        client,
        "-t",
        "work:",
        "#{client_session}\t#{window_id}\t#{pane_id}",
    ).stdout.strip()
    assert actual == f"work\t{target.window_id}\t{target.pane_id}"


def test_open_source_refuses_to_move_a_spectators_source_window_pane(
    scratch, monkeypatch
):
    scratch.new_work("work")
    scratch.command("new-window", "-d", "-t", "work", "sleep 3600")
    scratch.new_work("board")
    _, _, viewer = scratch.attach("board")
    _, _, spectator = scratch.attach("work")
    before = scratch.command(
        "display-message", "-p", "-t", "work:", "#{window_id}\t#{pane_id}"
    ).stdout
    assert before.startswith("@") and "%" in before
    board_pane = scratch.command(
        "display-message", "-p", "-t", "board:", "#{pane_id}"
    ).stdout.strip()
    assert board_pane.startswith("%")
    monkeypatch.setenv("TMUX_PANE", board_pane)
    source = SOURCE.TmuxSource(session="work", socket=scratch.socket)
    target = next(pane for pane in source.snapshots() if pane.window_index == 1)
    with pytest.raises(SOURCE.SourceError, match="other client"):
        source.open_source(target)
    assert scratch.attached()[viewer] == "board"
    assert scratch.attached()[spectator] == "work"
    assert (
        scratch.command(
            "display-message", "-p", "-t", "work:", "#{window_id}\t#{pane_id}"
        ).stdout
        == before
    )


def test_multiple_board_viewers_make_navigation_ambiguous(scratch, monkeypatch):
    scratch.new_work("work")
    scratch.new_work("board")
    _, _, first = scratch.attach("board")
    _, _, second = scratch.attach("board")
    pane = scratch.command(
        "display-message", "-p", "-t", "board:", "#{pane_id}"
    ).stdout.strip()
    assert pane.startswith("%")
    monkeypatch.setenv("TMUX_PANE", pane)
    source = SOURCE.TmuxSource(session="work", socket=scratch.socket)
    target = source.snapshots()[0]
    with pytest.raises(SOURCE.SourceError, match="one attached viewer"):
        source.open_source(target)
    assert scratch.attached()[first] == "board"
    assert scratch.attached()[second] == "board"


def test_replaced_source_process_refuses_old_snapshot(scratch, monkeypatch):
    scratch.new_work("work")
    scratch.new_work("board")
    _, _, viewer = scratch.attach("board")
    pane = scratch.command(
        "display-message", "-p", "-t", "board:", "#{pane_id}"
    ).stdout.strip()
    assert pane.startswith("%")
    monkeypatch.setenv("TMUX_PANE", pane)
    source = SOURCE.TmuxSource(session="work", socket=scratch.socket)
    target = source.snapshots()[0]
    scratch.command("respawn-pane", "-k", "-t", target.pane_id, "sleep 3600")
    until(
        lambda: source.snapshots()[0].pane_pid != target.pane_pid,
        "source process did not change",
    )
    with pytest.raises(SOURCE.SourceError, match="process changed"):
        source.open_source(target)
    assert scratch.attached()[viewer] == "board"


def test_native_coloured_blank_cells_survive_capture(scratch):
    scratch.command(
        "new-session",
        "-d",
        "-s",
        "colour",
        "printf '\033[48;2;54;42;30m          \033[0m'; sleep 3600",
    )
    source = SOURCE.TmuxSource(session="colour", socket=scratch.socket)
    snapshot = until(
        lambda: next(
            (
                item
                for item in source.snapshots()
                if "\x1b[48;2;54;42;30m" in item.preview_ansi
            ),
            None,
        ),
        "controlled background colour did not appear",
    )
    assert "\x1b[48;2;54;42;30m          " in snapshot.preview_ansi
    assert "\x1b[48;2;54;42;30m          " in source.capture(snapshot)


def input_receiver(scratch, name="input", *, bracketed=False, interactive_shell=False):
    """Run a real raw tty reader; its byte file is the observable input boundary."""
    script = scratch.socket.parent / f"{name}.py"
    received = scratch.socket.parent / f"{name}.bytes"
    received.write_bytes(b"")
    script.write_text(
        "import os, sys, tty\n"
        "tty.setraw(0)\n"
        "if sys.argv[2] == '1': os.write(1, b'\\x1b[?2004h')\n"
        "os.write(1, b'RECEIVER_READY')\n"
        "with open(sys.argv[1], 'ab', buffering=0) as output:\n"
        " while True:\n"
        "  data = os.read(0, 65536)\n"
        "  if not data: break\n"
        "  output.write(data)\n"
    )
    invocation = shlex.join(
        [sys.executable, "-u", str(script), str(received), str(int(bracketed))]
    )
    scratch.command(
        "new-session",
        "-d",
        "-s",
        name,
        "exec bash --noprofile --norc -i"
        if interactive_shell
        else "exec " + invocation,
    )
    if interactive_shell:
        scratch.command("send-keys", "-t", f"{name}:", "-l", invocation)
        scratch.command("send-keys", "-t", f"{name}:", "Enter")
    source = SOURCE.TmuxSource(session=name, socket=scratch.socket)
    snapshot = until(
        lambda: next(
            (
                pane
                for pane in source.snapshots()
                if "RECEIVER_READY" in pane.preview_ansi
                and pane.pane_current_command not in {"fish", "bash"}
            ),
            None,
        ),
        "raw receiver did not become the foreground source",
    )
    return source, snapshot, received, invocation


def test_input_keys_reach_exact_receiver_once_as_literal_unicode(scratch):
    source, snapshot, received, _ = input_receiver(scratch)
    _, _, other, _ = input_receiver(scratch, "other")
    text = "字é $();'\"\\"
    for character in text:
        source.send_key(snapshot, character, character)
    special = [
        ("enter", b"\r"),
        ("escape", b"\x1b"),
        ("tab", b"\t"),
        ("backspace", b"\x7f"),
        ("delete", b"\x1b[3~"),
        ("up", b"\x1b[A"),
        ("down", b"\x1b[B"),
        ("right", b"\x1b[C"),
        ("left", b"\x1b[D"),
        ("ctrl+a", b"\x01"),
        ("ctrl+c", b"\x03"),
        ("ctrl+left", b"\x1b[1;5D"),
    ]
    for key, _ in special:
        source.send_key(snapshot, key)
    expected = text.encode() + b"".join(value for _, value in special)
    until(lambda: received.read_bytes() == expected, "input bytes changed or repeated")
    assert other.read_bytes() == b""
    # A final positive marker establishes completion past the checked input burst.
    source.send_key(snapshot, "z", "z")
    until(lambda: received.read_bytes() == expected + b"z", "input did not finish")


@pytest.mark.parametrize("bracketed", [False, True])
def test_paste_preserves_exact_text_and_native_bracketing(scratch, bracketed):
    source, snapshot, received, _ = input_receiver(scratch, bracketed=bracketed)
    text = "字é $();'\"\\\nsecond\tline\x1b"
    source.send_text(snapshot, text)
    expected = text.encode()
    if bracketed:
        expected = b"\x1b[200~" + expected + b"\x1b[201~"
    until(lambda: received.read_bytes() == expected, "paste text or brackets changed")
    source.send_key(snapshot, "z", "z")
    until(
        lambda: received.read_bytes() == expected + b"z", "paste repeated or unfinished"
    )
    assert scratch.command("list-buffers", "-F", "#{buffer_name}").stdout == ""


def test_input_refuses_shell_after_foreground_exits_with_same_pane_pid(scratch):
    source, snapshot, received, _ = input_receiver(scratch, interactive_shell=True)
    assert snapshot.foreground_pid is not None
    os.kill(snapshot.foreground_pid, signal.SIGTERM)
    replacement = until(
        lambda: next(
            (
                pane
                for pane in source.snapshots()
                if pane.pane_current_command == "bash"
            ),
            None,
        ),
        "receiver did not return to its shell",
    )
    assert replacement.pane_pid == snapshot.pane_pid
    with pytest.raises(SOURCE.SourceError, match="process changed"):
        source.send_key(snapshot, "x", "x")
    with pytest.raises(SOURCE.SourceError, match="process changed"):
        source.send_text(snapshot, "must not reach the shell\n")
    # The shell can still start a new receiver, but the old identity remains stale.
    scratch.command("send-keys", "-t", snapshot.pane_id, "-l", "printf SHELL_ALIVE")
    scratch.command("send-keys", "-t", snapshot.pane_id, "Enter")
    until(
        lambda: "SHELL_ALIVE" in source.capture(replacement),
        "replacement shell was not positively observed",
    )
    assert received.read_bytes() == b""


def test_input_refuses_restarted_same_command(scratch):
    source, snapshot, _, invocation = input_receiver(scratch, interactive_shell=True)
    os.kill(snapshot.foreground_pid, signal.SIGTERM)
    until(
        lambda: source.snapshots()[0].pane_current_command == "bash",
        "receiver did not exit",
    )
    scratch.command("send-keys", "-t", snapshot.pane_id, "-l", invocation)
    scratch.command("send-keys", "-t", snapshot.pane_id, "Enter")
    restarted = until(
        lambda: next(
            (
                pane
                for pane in source.snapshots()
                if pane.pane_current_command == snapshot.pane_current_command
                and pane.foreground_pid != snapshot.foreground_pid
            ),
            None,
        ),
        "new same-command receiver did not start",
    )
    assert restarted.pane_pid == snapshot.pane_pid
    with pytest.raises(SOURCE.SourceError, match="process changed"):
        source.send_key(snapshot, "x", "x")


def test_input_refuses_synchronized_window_and_oversized_paste(scratch):
    source, snapshot, received, invocation = input_receiver(scratch)
    other = scratch.socket.parent / "other.bytes"
    other.write_bytes(b"")
    scratch.command(
        "split-window",
        "-d",
        "-t",
        snapshot.pane_id,
        invocation.replace(str(received), str(other)),
    )
    until(
        lambda: (
            len(source.snapshots()) == 2
            and all(
                "RECEIVER_READY" in pane.preview_ansi for pane in source.snapshots()
            )
        ),
        "both synchronized receivers did not start",
    )
    scratch.command(
        "set-option", "-w", "-t", snapshot.window_id, "synchronize-panes", "on"
    )
    with pytest.raises(SOURCE.SourceError, match="synchroniz"):
        source.send_key(snapshot, "x", "x")
    with pytest.raises(SOURCE.SourceError, match="synchroniz"):
        source.send_text(snapshot, "refused")
    scratch.command(
        "set-option", "-w", "-t", snapshot.window_id, "synchronize-panes", "off"
    )
    with pytest.raises(SOURCE.SourceError, match="64 KiB"):
        source.send_text(snapshot, "字" * 21846)
    source.send_key(snapshot, "z", "z")
    until(lambda: received.read_bytes() == b"z", "refused input reached the receiver")
    assert other.read_bytes() == b""


def test_unknown_input_key_is_an_explicit_error(scratch):
    source, snapshot, received, _ = input_receiver(scratch)
    with pytest.raises(SOURCE.SourceError, match="unsupported"):
        source.send_key(snapshot, "unsupported-key")
    source.send_key(snapshot, "z", "z")
    until(lambda: received.read_bytes() == b"z", "unsupported key reached receiver")
