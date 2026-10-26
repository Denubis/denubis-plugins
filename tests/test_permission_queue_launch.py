"""Exercise detached launch and quit through an isolated tmux server and real PTYs."""

from __future__ import annotations

import os
import pty
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "experiments" / "permission-queue" / "launch.py"
TMUX = shutil.which("tmux")


def until(predicate, message: str, timeout: float = 8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    pytest.fail(message)


class ScratchServer:
    def __init__(self, directory: Path):
        self.socket = directory / "tmux.sock"
        self.clients: list[tuple[subprocess.Popen, int]] = []

    def command(self, *arguments: str, check: bool = True):
        return subprocess.run(
            [TMUX, "-S", str(self.socket), "-f", "/dev/null", *arguments],
            capture_output=True,
            text=True,
            timeout=5,
            check=check,
        )

    def new_work(self, name: str):
        self.command("new-session", "-d", "-s", name, "sleep 3600")

    def attached(self):
        result = self.command(
            "list-clients", "-F", "#{client_name}\t#{client_session}", check=False
        )
        return dict(line.split("\t") for line in result.stdout.splitlines())

    def attach(self, name: str):
        master, slave = pty.openpty()
        previous = set(self.attached())
        child = subprocess.Popen(
            [TMUX, "-S", str(self.socket), "attach-session", "-t", f"={name}"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        os.close(slave)
        self.clients.append((child, master))
        client = until(
            lambda: next(
                (client for client in self.attached() if client not in previous), None
            ),
            f"client did not attach to {name}",
        )
        return child, master, client

    def launch(self, run_dir: Path, *arguments: str):
        return subprocess.run(
            [
                sys.executable,
                "-P",
                str(LAUNCHER),
                "--socket",
                str(self.socket),
                "--run-dir",
                str(run_dir),
                *arguments,
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=5,
        )

    def quit_board(self, master: int):
        output = bytearray()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.05)
            if readable:
                output.extend(os.read(master, 65536))
            if b"DEMO" in output:
                os.write(master, b"q")
                return
        pytest.fail(f"board did not render: {output.decode(errors='replace')}")

    def close(self):
        self.command("kill-server", check=False)
        for child, master in self.clients:
            # Closing the PTY releases a client blocked flushing terminal output.
            os.close(master)
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)


@pytest.fixture
def server(tmp_path):
    if TMUX is None:
        pytest.skip("tmux is required for the actual terminal integration")
    instance = ScratchServer(tmp_path)
    yield instance
    instance.close()


def test_quit_returns_client_to_exact_last_work_without_detaching(server, tmp_path):
    server.new_work("alpha-work")
    server.new_work("beta-other")
    server.command("new-window", "-d", "-t", "alpha-work", "sleep 3600")
    client_process, master, client = server.attach("alpha-work")
    other_process, _, other_client = server.attach("beta-other")
    work_pane = server.command(
        "display-message", "-p", "-t", "alpha-work:", "#{pane_id}"
    ).stdout
    assert work_pane.strip().startswith("%")
    global_before = server.command("show-options", "-gv", "detach-on-destroy").stdout
    started = server.launch(tmp_path / "requests", "--return-session", "alpha-work")
    assert started.returncode == 0, started.stderr
    assert server.attached()[client] == "alpha-work", "launch must stay detached"
    server.command("switch-client", "-c", client, "-t", "=permission-queue-demo")
    server.command("switch-client", "-c", other_client, "-t", "=permission-queue-demo")
    server.quit_board(master)
    until(
        lambda: server.attached().get(client) == "alpha-work",
        "q detached the client or returned it to the wrong session",
    )
    assert client_process.poll() is None
    assert other_process.poll() is None
    until(
        lambda: server.attached().get(other_client) == "beta-other",
        "second viewer did not return to its own work session",
    )
    assert (
        server.command(
            "display-message", "-p", "-t", "alpha-work:", "#{pane_id}"
        ).stdout
        == work_pane
    )
    assert (
        server.command("show-options", "-gv", "detach-on-destroy").stdout
        == global_before
    )
    assert (
        server.command("has-session", "-t", "=beta-other", check=False).returncode == 0
    )
    # The launcher returns the clients before it exits; tmux then ends the session.
    until(
        lambda: (
            server.command(
                "has-session", "-t", "=permission-queue-demo", check=False
            ).returncode
            != 0
        ),
        "the scratch session outlived the board after q",
    )


def test_relaunch_reuses_owned_session_without_changing_attached_work(server, tmp_path):
    server.new_work("work")
    child, _, client = server.attach("work")
    first = server.launch(tmp_path / "requests", "--return-session", "work")
    assert first.returncode == 0, first.stderr
    session_id = server.command(
        "display-message", "-p", "-t", "permission-queue-demo:", "#{session_id}"
    ).stdout
    assert session_id.strip().startswith("$")
    second = server.launch(
        tmp_path / "other-unused-requests", "--return-session", "work"
    )
    assert second.returncode == 0, second.stderr
    assert (
        server.command(
            "display-message", "-p", "-t", "permission-queue-demo:", "#{session_id}"
        ).stdout
        == session_id
    )
    assert server.attached()[client] == "work"
    assert child.poll() is None
    names = server.command("list-sessions", "-F", "#{session_name}").stdout.splitlines()
    assert set(names) == {"work", "permission-queue-demo"}


def test_same_name_unowned_session_is_refused_and_preserved(server, tmp_path):
    server.new_work("permission-queue-demo")
    pane = server.command(
        "display-message", "-p", "-t", "permission-queue-demo:", "#{pane_id}"
    ).stdout
    assert pane.strip().startswith("%")
    started = server.launch(tmp_path / "requests")
    assert started.returncode != 0
    assert "not owned" in started.stderr
    assert (
        server.command(
            "display-message", "-p", "-t", "permission-queue-demo:", "#{pane_id}"
        ).stdout
        == pane
    )
    assert (
        server.command("show-options", "-gv", "detach-on-destroy").stdout.strip()
        == "on"
    )


def test_direct_attach_without_last_session_uses_explicit_return_session(
    server, tmp_path
):
    server.new_work("work")
    started = server.launch(tmp_path / "requests", "--return-session", "work")
    assert started.returncode == 0, started.stderr
    child, master, client = server.attach("permission-queue-demo")
    server.quit_board(master)
    until(
        lambda: server.attached().get(client) == "work",
        "explicit return session was not used",
    )
    assert child.poll() is None


def test_quit_when_no_work_session_remains_closes_only_the_scratch_client(
    server, tmp_path
):
    server.new_work("bootstrap")
    started = server.launch(tmp_path / "requests", "--return-session", "missing-work")
    assert started.returncode == 0, started.stderr
    server.command("kill-session", "-t", "=bootstrap")
    child, master, _ = server.attach("permission-queue-demo")
    server.quit_board(master)
    assert child.wait(timeout=5) == 0
