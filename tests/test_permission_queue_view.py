"""Check independent viewers through command boundaries and real scratch PTYs."""

from __future__ import annotations

import importlib.util
import os
import pty
import select
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from test_permission_queue_launch import TMUX, ScratchServer, until

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "experiments" / "permission-queue" / "view.py"
WRAPPER = HELPER.with_name("open-viewer")
SPEC = importlib.util.spec_from_file_location("permission_queue_view", HELPER)
assert SPEC is not None and SPEC.loader is not None
VIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VIEW)


class Commands:
    def __init__(self, socket):
        self.socket = socket
        self.calls = []
        self.terminals = []

    def run(self, arguments, **kwargs):
        self.calls.append((arguments, kwargs))
        output = str(self.socket) + "\n" if "display-message" in arguments else ""
        return subprocess.CompletedProcess(arguments, 0, output, "")

    def popen(self, arguments, **kwargs):
        self.terminals.append((arguments, kwargs))


def test_ghostty_opens_new_terminal_with_captured_socket_and_unique_viewers(
    monkeypatch, tmp_path
):
    socket = tmp_path / "original,server.sock"
    fixture = Commands(socket)
    monkeypatch.setenv("TMUX", f"{socket},123,0")
    monkeypatch.setenv("TMUX_PANE", "%77")
    monkeypatch.setattr(VIEW.subprocess, "run", fixture.run)
    monkeypatch.setattr(VIEW.subprocess, "Popen", fixture.popen)
    monkeypatch.setattr(VIEW.shutil, "which", lambda name: "/usr/bin/ghostty")
    assert VIEW.main(["--ghostty"]) == 0
    assert VIEW.main(["--ghostty"]) == 0
    assert len(fixture.terminals) == 2
    sessions = []
    for arguments, kwargs in fixture.terminals:
        assert arguments[:3] == [
            "/usr/bin/ghostty",
            "--gtk-single-instance=false",
            "-e",
        ]
        assert arguments[3:6] == [sys.executable, "-P", str(HELPER)]
        assert arguments[arguments.index("--socket") + 1] == str(socket)
        assert arguments[arguments.index("--watch-session") + 1] == "main"
        sessions.append(arguments[arguments.index("--session") + 1])
        assert "TMUX" not in kwargs["env"]
        assert "TMUX_PANE" not in kwargs["env"]
    assert sessions[0] != sessions[1]
    assert all(name.startswith("permission-queue-view-") for name in sessions)
    assert os.environ["TMUX"] == f"{socket},123,0"
    assert os.environ["TMUX_PANE"] == "%77"
    queries = [
        arguments for arguments, _ in fixture.calls if "display-message" in arguments
    ]
    assert all(arguments[:3] == ["tmux", "-S", str(socket)] for arguments in queries)


def test_explicit_socket_session_and_source_are_forwarded_without_shell_parsing(
    monkeypatch, tmp_path
):
    socket = tmp_path / "chosen socket.sock"
    fixture = Commands(socket)
    monkeypatch.setenv("TMUX", "/wrong/server.sock,123,0")
    monkeypatch.setattr(VIEW.subprocess, "run", fixture.run)
    monkeypatch.setattr(VIEW.subprocess, "Popen", fixture.popen)
    monkeypatch.setattr(VIEW.shutil, "which", lambda name: "/usr/bin/ghostty")
    assert (
        VIEW.main(
            [
                "--ghostty",
                "--socket",
                str(socket),
                "--session",
                "reuse-me",
                "--watch-session",
                "work",
            ]
        )
        == 0
    )
    arguments = fixture.terminals[0][0]
    assert arguments[arguments.index("--session") + 1] == "reuse-me"
    assert arguments[arguments.index("--watch-session") + 1] == "work"
    assert arguments[arguments.index("--socket") + 1] == str(socket)
    assert fixture.calls[0][0][:3] == ["tmux", "-S", str(socket)]


def test_missing_ghostty_reports_error_without_creating_a_viewer(
    monkeypatch, tmp_path, capsys
):
    fixture = Commands(tmp_path / "server.sock")
    monkeypatch.setattr(VIEW.subprocess, "run", fixture.run)
    monkeypatch.setattr(VIEW.subprocess, "Popen", fixture.popen)
    monkeypatch.setattr(VIEW.shutil, "which", lambda name: None)
    assert VIEW.main(["--ghostty", "--socket", str(fixture.socket)]) != 0
    assert "ghostty" in capsys.readouterr().err.lower()
    assert fixture.terminals == []
    assert all(
        str(HELPER.with_name("launch.py")) not in args for args, _ in fixture.calls
    )


def test_ghostty_spawn_failure_does_not_create_a_detached_viewer(
    monkeypatch, tmp_path, capsys
):
    fixture = Commands(tmp_path / "server.sock")
    monkeypatch.setattr(VIEW.subprocess, "run", fixture.run)
    monkeypatch.setattr(VIEW.shutil, "which", lambda name: "/usr/bin/ghostty")

    def fail_spawn(*arguments, **kwargs):
        raise OSError("controlled terminal launch failure")

    monkeypatch.setattr(VIEW.subprocess, "Popen", fail_spawn)
    assert VIEW.main(["--ghostty", "--socket", str(fixture.socket)]) != 0
    assert "controlled terminal launch failure" in capsys.readouterr().err
    assert all(
        str(HELPER.with_name("launch.py")) not in args for args, _ in fixture.calls
    )


def test_missing_source_reports_error_without_creating_session(tmp_path, capsys):
    server = ScratchServer(tmp_path)
    try:
        server.new_work("main")
        assert (
            VIEW.main(["--socket", str(server.socket), "--watch-session", "missing"])
            != 0
        )
        assert "source tmux session 'missing' is unavailable" in capsys.readouterr().err
        assert (
            server.command("list-sessions", "-F", "#{session_name}").stdout == "main\n"
        )
    finally:
        server.close()


@pytest.mark.parametrize("reuse", [False, True])
def test_direct_terminal_invocations_attach_independently_unless_name_requested(
    tmp_path, reuse
):
    if TMUX is None:
        pytest.skip("tmux is required for the real terminal integration")
    server = ScratchServer(tmp_path)
    stop = threading.Event()
    readers = []
    try:
        server.command(
            "new-session",
            "-d",
            "-s",
            "main",
            "printf 'REAL_SOURCE_READY\\n'; exec sleep 3600",
        )
        original = server.command(
            "display-message", "-p", "-t", "main:", "#{window_id}\t#{pane_id}"
        ).stdout
        assert original.startswith("@") and "%" in original
        viewers = []
        for _ in range(2):
            master, slave = pty.openpty()
            previous = set(server.attached())
            arguments = [
                sys.executable,
                "-P",
                str(HELPER),
                "--socket",
                str(server.socket),
            ]
            if reuse:
                arguments += ["--session", "named-viewer"]
            environment = {**os.environ, "TERM": "xterm-256color"}
            # The helper must clear inherited nesting identity before native attach.
            environment["TMUX"] = f"{server.socket},123,0"
            environment["TMUX_PANE"] = "%999"
            child = subprocess.Popen(
                arguments, stdin=slave, stdout=slave, stderr=slave, env=environment
            )
            os.close(slave)
            server.clients.append((child, master))

            def drain(terminal=master):
                while not stop.is_set():
                    ready, _, _ = select.select([terminal], [], [], 0.05)
                    if ready:
                        try:
                            os.read(terminal, 65536)
                        except OSError:
                            return

            reader = threading.Thread(target=drain)
            reader.start()
            readers.append(reader)
            client = until(
                lambda previous=previous: next(
                    (name for name in server.attached() if name not in previous), None
                ),
                "new terminal did not attach its own viewer client",
            )
            session = server.attached()[client]
            assert session != "main"
            until(
                lambda session=session: (
                    "REAL_SOURCE_READY"
                    in server.command("capture-pane", "-p", "-t", session + ":").stdout
                ),
                "new viewer did not replay the requested source",
            )
            viewers.append((master, client, session))
        assert (viewers[0][2] == viewers[1][2]) is reuse
        if reuse:
            assert viewers[0][2] == "named-viewer"
        else:
            os.write(viewers[0][0], b"\x11")
            until(
                lambda: server.attached().get(viewers[0][1]) == "main",
                "closing one independent viewer did not return its client to work",
            )
            assert server.attached()[viewers[1][1]] == viewers[1][2]
        assert (
            server.command(
                "display-message", "-p", "-t", "main:", "#{window_id}\t#{pane_id}"
            ).stdout
            == original
        )
    finally:
        stop.set()
        for reader in readers:
            reader.join(timeout=2)
        server.close()


def test_executable_wrapper_resolves_project_from_another_directory(tmp_path):
    result = subprocess.run(
        [str(WRAPPER), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "--ghostty" in result.stdout and "--watch-session" in result.stdout
