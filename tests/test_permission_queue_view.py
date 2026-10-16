"""Check independent viewers through command boundaries and real scratch PTYs."""

from __future__ import annotations

import importlib.util
import os
import pty
import select
import shlex
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


def test_ghostty_opens_standalone_terminals_with_captured_socket(monkeypatch, tmp_path):
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
    for arguments, kwargs in fixture.terminals:
        assert arguments == [
            "/usr/bin/ghostty",
            "--gtk-single-instance=false",
            "-e",
            sys.executable,
            "-P",
            str(HELPER),
            "--socket",
            str(socket),
            "--watch-session",
            "main",
        ]
        assert "TMUX" not in kwargs["env"]
        assert "TMUX_PANE" not in kwargs["env"]
    assert os.environ["TMUX"] == f"{socket},123,0"
    assert os.environ["TMUX_PANE"] == "%77"
    queries = [
        arguments for arguments, _ in fixture.calls if "display-message" in arguments
    ]
    assert all(arguments[:3] == ["tmux", "-S", str(socket)] for arguments in queries)


def test_explicit_socket_and_source_are_forwarded_without_shell_parsing(
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
                "--watch-session",
                "work",
            ]
        )
        == 0
    )
    arguments = fixture.terminals[0][0]
    assert arguments[arguments.index("--watch-session") + 1] == "work"
    assert arguments[arguments.index("--socket") + 1] == str(socket)
    assert fixture.calls[0][0][:3] == ["tmux", "-S", str(socket)]


def test_obsolete_viewer_session_option_is_rejected_with_standalone_explanation(capsys):
    with pytest.raises(SystemExit) as exit_status:
        VIEW.main(["--session", "old-viewer"])
    assert exit_status.value.code == 2
    assert "standalone" in capsys.readouterr().err.lower()


def test_current_terminal_executes_board_with_captured_socket_and_clean_environment(
    monkeypatch, tmp_path
):
    socket = tmp_path / "source.sock"
    fixture = Commands(socket)
    monkeypatch.setenv("TMUX", f"{socket},123,0")
    monkeypatch.setenv("TMUX_PANE", "%77")
    monkeypatch.setattr(VIEW.subprocess, "run", fixture.run)
    executed = []

    class ExecBoard(Exception):
        pass

    def execute(program, arguments, environment):
        executed.append((program, arguments, environment))
        raise ExecBoard

    monkeypatch.setattr(VIEW.os, "execve", execute)
    monkeypatch.setattr(VIEW.os, "execvpe", execute)
    with pytest.raises(ExecBoard):
        VIEW.main([])
    program, arguments, environment = executed[0]
    assert program == sys.executable
    assert arguments == [
        sys.executable,
        "-P",
        str(HELPER.with_name("board.py")),
        "--socket",
        str(socket),
        "--watch-session",
        "main",
    ]
    assert "TMUX" not in environment and "TMUX_PANE" not in environment


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


def include_unknown_pane(master, output, config):
    until(lambda: b"Add panes" in output, "viewer did not expose its pane selector")
    os.write(master, b"a")
    until(
        lambda: b"STANDALONE_SOURCE_FIXTURE" in output,
        "pane selector did not list the unknown source",
    )
    os.write(master, b" ")
    until(
        (config / "permission-queue" / "panes.json").exists,
        "pane selection was not persisted",
    )
    os.write(master, b"\x1b")


@pytest.mark.parametrize("quit_key", [b"\x03", b"\x11"], ids=["ctrl-c", "ctrl-q"])
def test_two_standalone_viewers_create_no_sessions_and_quit_to_their_calling_shells(
    tmp_path,
    quit_key,
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
        server.command("select-pane", "-t", "main:", "-T", "STANDALONE_SOURCE_FIXTURE")
        sessions_before = server.command(
            "list-sessions", "-F", "#{session_id}\t#{session_name}"
        ).stdout
        assert sessions_before.endswith("\tmain\n")
        original = server.command(
            "display-message", "-p", "-t", "main:", "#{window_id}\t#{pane_id}"
        ).stdout
        assert original.startswith("@") and "%" in original
        viewers = []
        for viewer_index in range(2):
            master, slave = pty.openpty()
            arguments = [
                sys.executable,
                "-P",
                str(HELPER),
                "--socket",
                str(server.socket),
            ]
            environment = {
                **os.environ,
                "TERM": "xterm-256color",
                "XDG_CONFIG_HOME": str(tmp_path / "viewer-config"),
            }
            # Socket discovery must precede clearing the inherited tmux identity.
            environment["TMUX"] = f"{server.socket},123,0"
            environment["TMUX_PANE"] = "%999"
            child = subprocess.Popen(
                [
                    "bash",
                    "--noprofile",
                    "--norc",
                    "-c",
                    shlex.join(arguments) + "; printf '\\nCALLER_SHELL_RESUMED\\n'",
                ],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                env=environment,
            )
            os.close(slave)
            server.clients.append((child, master))

            output = bytearray()

            def drain(terminal=master, output=output):
                while not stop.is_set():
                    ready, _, _ = select.select([terminal], [], [], 0.05)
                    if ready:
                        try:
                            output.extend(os.read(terminal, 65536))
                        except OSError:
                            return

            reader = threading.Thread(target=drain)
            reader.start()
            readers.append(reader)
            if viewer_index == 0:
                include_unknown_pane(master, output, tmp_path / "viewer-config")
            until(
                lambda output=output: b"REAL_SOURCE_READY" in output,
                "standalone viewer did not replay the opted-in source pane",
            )
            viewers.append((master, child, output))
        assert (
            server.command(
                "list-sessions", "-F", "#{session_id}\t#{session_name}"
            ).stdout
            == sessions_before
        )
        for index, (master, child, output) in enumerate(viewers):
            os.write(master, quit_key)
            until(
                lambda output=output: b"CALLER_SHELL_RESUMED" in output,
                "quit key did not return to the invoking shell",
            )
            assert child.wait(timeout=5) == 0
            if index == 0:
                assert viewers[1][1].poll() is None
        assert (
            server.command(
                "list-sessions", "-F", "#{session_id}\t#{session_name}"
            ).stdout
            == sessions_before
        )
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
