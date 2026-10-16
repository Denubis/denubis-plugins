"""The installed launch path displays source windows and returns to work."""

from __future__ import annotations

import json
import os
import select
import shlex
import sys
import threading

import pytest
from test_permission_queue_launch import TMUX, ScratchServer, until


@pytest.fixture
def source_server(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    if TMUX is None:
        pytest.skip("tmux is required for the actual terminal integration")
    instance = ScratchServer(tmp_path)
    instance.command(
        "new-session",
        "-d",
        "-s",
        "source-work",
        "printf 'SOURCE_CONVERSATION_LAUNCH_CHECK\\n'; exec sleep 3600",
    )
    instance.command("select-pane", "-t", "source-work:", "-T", "WATCH_UNKNOWN_FIXTURE")
    instance.command(
        "set-environment", "-g", "XDG_CONFIG_HOME", str(tmp_path / "viewer-config")
    )
    instance.command(
        "set-environment", "-g", "CODEX_HOME", str(tmp_path / "codex-home")
    )
    yield instance
    instance.close()


@pytest.fixture
def source_client(source_server):
    client = source_server.attach("source-work")
    master = client[1]
    stopped = threading.Event()

    def drain():
        while not stopped.is_set():
            ready, _, _ = select.select([master], [], [], 0.05)
            if ready:
                try:
                    os.read(master, 65536)
                except OSError:
                    return

    reader = threading.Thread(target=drain)
    reader.start()
    yield client
    stopped.set()
    reader.join(timeout=2)


def test_watch_launcher_displays_actual_source_and_quit_returns_to_work(
    source_server, source_client, tmp_path
):
    process, master, client = source_client
    started = source_server.launch(
        tmp_path / "unused-demo-fixtures",
        "--watch-session",
        "source-work",
        "--return-session",
        "source-work",
    )
    assert started.returncode == 0, started.stderr
    assert source_server.attached()[client] == "source-work"

    def actual_preview():
        capture = source_server.command(
            "capture-pane", "-p", "-t", "permission-queue-demo:", check=False
        )
        return "SOURCE_CONVERSATION_LAUNCH_CHECK" in capture.stdout

    until(
        lambda: (
            "Add panes"
            in source_server.command(
                "capture-pane", "-p", "-t", "permission-queue-demo:"
            ).stdout
        ),
        "viewer did not expose pane selection",
    )
    source_server.command("send-keys", "-t", "permission-queue-demo:", "a")
    until(
        lambda: (
            "WATCH_UNKNOWN_FIXTURE"
            in source_server.command(
                "capture-pane", "-p", "-t", "permission-queue-demo:"
            ).stdout
        ),
        "pane selector did not list the source",
    )
    source_server.command("send-keys", "-t", "permission-queue-demo:", "Space")
    until(
        (tmp_path / "viewer-config" / "permission-queue" / "panes.json").exists,
        "source opt-in was not persisted",
    )
    source_server.command("send-keys", "-t", "permission-queue-demo:", "Escape")
    until(
        lambda: (
            "Ready: 1/2/3 + Enter"
            in source_server.command(
                "capture-pane", "-p", "-t", "permission-queue-demo:"
            ).stdout
        ),
        "viewer did not become ready",
    )
    until(actual_preview, "viewer did not replay the source terminal")
    assert not (tmp_path / "unused-demo-fixtures").exists()
    source_server.command("switch-client", "-c", client, "-t", "=permission-queue-demo")
    os.write(master, b"o")
    until(
        lambda: source_server.attached().get(client) == "source-work",
        "Open source did not navigate the viewing client to its work pane",
    )
    source_server.command("switch-client", "-c", client, "-t", "=permission-queue-demo")
    os.write(master, b"\x03")
    until(
        lambda: source_server.attached().get(client) == "source-work",
        "quitting the live viewer did not return to work",
    )
    assert process.poll() is None


def test_existing_demo_is_not_silently_reused_as_a_live_view(source_server, tmp_path):
    started = source_server.launch(tmp_path / "fixtures")
    assert started.returncode == 0, started.stderr
    before = source_server.command(
        "display-message", "-p", "-t", "permission-queue-demo:", "#{pane_id}"
    ).stdout
    assert before.strip().startswith("%")
    different_mode = source_server.launch(
        tmp_path / "unused", "--watch-session", "source-work"
    )
    assert different_mode.returncode != 0
    assert "different view" in different_mode.stderr
    assert (
        source_server.command(
            "display-message", "-p", "-t", "permission-queue-demo:", "#{pane_id}"
        ).stdout
        == before
    )


def test_native_codex_answer_keys_work_without_manual_link_and_advance(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    if TMUX is None:
        pytest.skip("tmux is required for terminal input integration")
    executable = tmp_path / "codex"
    executable.symlink_to(sys.executable)
    fixture = tmp_path / "native_fixture.py"
    fixture.write_text("""import ctypes, json, os, sys, time
from pathlib import Path
ctypes.CDLL(None).prctl(15, b'codex', 0, 0, 0)
record = Path(sys.argv[1])
def title(state):
    text = state + ' | fixture | main | ' + sys.argv[2] + ' | fixture'
    print('\\x1b]0;' + text + '\\x07', end='', flush=True)
title('Action Required')
print('Would you like to run this command?\\n1. Yes\\n2. No', flush=True)
print('NATIVE_INPUT_FIXTURE_' + sys.argv[2], flush=True)
responses = []
for line in sys.stdin:
    responses.append(line)
    record.write_text(json.dumps(responses))
    title('Working')
    print('RESPONSE_RECEIVED_' + sys.argv[2], flush=True)
""")
    server = ScratchServer(tmp_path)
    stopped = threading.Event()
    reader = None
    try:
        first, second = tmp_path / "first.json", tmp_path / "second.json"

        def command(output, label):
            return "exec " + shlex.join(
                [str(executable), str(fixture), str(output), label]
            )

        server.command(
            "new-session", "-d", "-s", "source-work", command(first, "FIRST")
        )
        server.command(
            "new-window", "-d", "-t", "source-work", command(second, "SECOND")
        )
        until(
            lambda: (
                "Action Required"
                in server.command(
                    "list-panes", "-s", "-t", "source-work", "-F", "#{pane_title}"
                ).stdout
            ),
            "fixture did not publish native state",
        )
        until(
            lambda: (
                server.command(
                    "list-panes",
                    "-s",
                    "-t",
                    "source-work",
                    "-F",
                    "#{pane_current_command}",
                ).stdout.splitlines()
                == ["codex", "codex"]
            ),
            "fixture process names were not observable as intended",
        )
        _, master, client = server.attach("source-work")

        def drain():
            while not stopped.is_set():
                ready, _, _ = select.select([master], [], [], 0.05)
                if ready:
                    try:
                        os.read(master, 65536)
                    except OSError:
                        return

        reader = threading.Thread(target=drain)
        reader.start()
        started = server.launch(
            tmp_path / "unused",
            "--watch-session",
            "source-work",
            "--return-session",
            "source-work",
        )
        assert started.returncode == 0, started.stderr
        server.command("switch-client", "-c", client, "-t", "=permission-queue-demo")

        def screen():
            return server.command(
                "capture-pane", "-p", "-t", "permission-queue-demo:", check=False
            ).stdout

        until(lambda: "Ready: 1/2/3 + Enter" in screen(), "native input not ready")
        until(lambda: "NATIVE_INPUT_FIXTURE_FIRST" in screen(), "first context missing")
        os.write(master, b"xyz1\r")
        until(first.exists, "native answer did not reach first pane")
        assert json.loads(first.read_text()) == ["1\n"]
        until(
            lambda: (
                "NATIVE_INPUT_FIXTURE_SECOND" in screen()
                and "Ready: 1/2/3 + Enter" in screen()
            ),
            "next pane was not ready after resolution",
        )
        os.write(master, b"2\r")
        until(second.exists, "next pane required another activation")
        assert json.loads(second.read_text()) == ["2\n"]
        assert json.loads(first.read_text()) == ["1\n"]
        os.write(master, b"\x03")
        until(
            lambda: server.attached().get(client) == "source-work",
            "closing interactive viewer detached work",
        )
    finally:
        stopped.set()
        if reader is not None:
            reader.join(timeout=2)
        server.close()
