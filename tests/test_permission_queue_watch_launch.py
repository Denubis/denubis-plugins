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
def source_server(tmp_path):
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

    until(actual_preview, "launched viewer did not replay the source terminal")
    assert not (tmp_path / "unused-demo-fixtures").exists()
    source_server.command("switch-client", "-c", client, "-t", "=permission-queue-demo")
    os.write(master, b"o")
    until(
        lambda: source_server.attached().get(client) == "source-work",
        "Open source did not navigate the viewing client to its work pane",
    )
    source_server.command("switch-client", "-c", client, "-t", "=permission-queue-demo")
    os.write(master, b"\x11")
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


def test_answer_keys_in_launched_view_answer_once_and_advance_without_another_click(
    tmp_path,
):
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
print('NATIVE_INPUT_FIXTURE_' + sys.argv[2], flush=True)
print('Would you like to run this command?\\n1. Yes\\n2. No', flush=True)
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
        first = tmp_path / "first.json"
        second = tmp_path / "second.json"

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

        until(
            lambda: (
                "NATIVE_INPUT_FIXTURE_FIRST" in (current := screen())
                and "Ready: 1/2/3 + Enter" in current
            ),
            "first native prompt was not displayed",
        )
        # Unrelated text stays local; only the native answer keys reach the source.
        os.write(master, b"xyz1\r")
        until(
            first.exists,
            "answer keys did not reach the first source",
        )
        assert json.loads(first.read_text()) == ["1\n"]
        until(
            lambda: (
                "NATIVE_INPUT_FIXTURE_SECOND" in (current := screen())
                and "Ready: 1/2/3 + Enter" in current
            ),
            "resolved source did not advance to the second prompt",
        )
        assert server.attached()[client] == "permission-queue-demo"
        # The next prompt accepts input without another focus click or confirmation.
        os.write(master, b"2\r")
        until(second.exists, "next prompt required an extra activation")
        assert json.loads(second.read_text()) == ["2\n"]
        assert json.loads(first.read_text()) == ["1\n"]
        os.write(master, b"\x11")
        until(
            lambda: server.attached().get(client) == "source-work",
            "closing interactive viewer detached work",
        )
    finally:
        stopped.set()
        if reader is not None:
            reader.join(timeout=2)
        server.close()
