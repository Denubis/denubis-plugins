"""Port handling and stopping of the dots.mocr escalation tier (renderer.mocr_server).

The plugin drives a dots.mocr checkout through its fish wrappers. These tests
build a stand-in checkout whose wrappers record their arguments and launch the
same shape of process tree as the real `dots-serve.fish` (fish, then a
`uv run`-like launcher, then a server with an engine-worker child), so the
plugin's real subprocess, curl readiness probe and stop paths run. No vLLM.

The contract under test: with no pinned port, one run starts the server on a
free local port and OCRs against that same port; a pinned port is used for both,
and a server already answering there is reused and left running. A run stops
exactly the process tree it started, and nothing else, including what a failed
start leaves behind.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_SKILL = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "denubis-academic"
    / "skills"
    / "using-bibliography"
)


def _load_renderer():
    spec = importlib.util.spec_from_file_location(
        "renderer_mocr_under_test", _SKILL / "renderer.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["renderer_mocr_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


renderer = _load_renderer()

needs_fish_and_curl = pytest.mark.skipif(
    shutil.which("fish") is None or shutil.which("curl") is None,
    reason="the mocr tier runs fish wrappers and probes with curl",
)

# One script plays the three processes `dots-serve.fish` starts: `uv run`
# (launcher), `vllm serve` (server) and vLLM's engine core (worker). Each
# appends its pid to rec/tree-<TREE_TAG>.pids.
_FAKE_VLLM = """\
import json, os, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer

role, rec = sys.argv[1], sys.argv[2]
tag = os.environ.get("TREE_TAG", "run")
with open(os.path.join(rec, f"tree-{tag}.pids"), "a") as f:
    f.write(f"{os.getpid()}\\n")

if role == "launcher":
    sys.exit(subprocess.call([sys.executable, __file__, "server", rec, *sys.argv[3:]]))
if role == "worker":
    time.sleep(3600)
    sys.exit(0)

port, model = int(sys.argv[3]), sys.argv[4]
subprocess.Popen([sys.executable, __file__, "worker", rec])
# FAKE_VLLM_STARTUP plays a start-up that goes wrong: "hang" never becomes
# ready (a model load that stalls), "crash" exits and leaves its worker behind.
startup = os.environ.get("FAKE_VLLM_STARTUP")
if startup == "hang":
    time.sleep(3600)
if startup == "crash":
    sys.exit(1)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        found = self.path == "/v1/models"
        self.send_response(200 if found else 404)
        self.end_headers()
        if found:
            self.wfile.write(json.dumps({"data": [{"id": model}]}).encode())

    def log_message(self, *args):
        pass


HTTPServer(("127.0.0.1", port), Handler).serve_forever()
"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _answers(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _port_arg(argv_file: Path) -> int:
    argv = argv_file.read_text().splitlines()
    assert "--port" in argv, f"{argv_file.name} got no --port: {argv}"
    return int(argv[argv.index("--port") + 1])


def _tree(rec: Path, tag: str) -> list[int]:
    pids = rec / f"tree-{tag}.pids"
    return [int(p) for p in pids.read_text().split()] if pids.exists() else []


@pytest.fixture
def deploy(tmp_path):
    """A stand-in dots.mocr checkout. `rec` holds what each wrapper received."""
    repo = tmp_path / "dots.mocr"
    rec = tmp_path / "rec"
    (repo / "tools").mkdir(parents=True)
    rec.mkdir()
    fake_vllm = tmp_path / "fake_vllm.py"
    fake_vllm.write_text(_FAKE_VLLM)
    py = sys.executable
    # Like the real dots-serve.fish, fish waits on `uv run ... vllm serve`. It
    # refuses to start without --port so a test can never bind a shared port.
    (repo / "dots-serve.fish").write_text(
        "set -q TREE_TAG; or set TREE_TAG run\n"
        f"printf '%s\\n' $argv > {rec}/serve-$TREE_TAG.argv\n"
        "argparse --ignore-unknown 'port=' -- $argv; or exit 2\n"
        "set -q _flag_port; or exit 3\n"
        f"{py} {fake_vllm} launcher {rec} $_flag_port dots.mocr\n"
    )
    # Like the old dots-stop.fish, stops every server on the machine.
    (repo / "dots-stop.fish").write_text(
        f"touch {rec}/stop.called\nfor f in {rec}/tree-*.pids\n    kill (cat $f)\nend\n"
    )
    (repo / "dots-ocr.fish").write_text(
        f"printf '%s\\n' $argv > {rec}/ocr.argv\n"
        "mkdir -p $argv[2]\n"
        "echo '{}' > $argv[2]/doc.jsonl\n"
    )
    (repo / "tools" / "combine_markdown.py").write_text(
        "import pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "(p.parent / (p.stem + '_nohf.md')).write_text("
        "'<!-- ===== page 1 ===== -->\\nOCR text\\n')\n"
    )
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    others: list[subprocess.Popen] = []

    def serve_outside_the_run(port: int) -> None:
        """Start a server from the same checkout by hand, as a person would."""
        others.append(
            subprocess.Popen(
                ["fish", str(repo / "dots-serve.fish"), "--port", str(port)],
                env={**os.environ, "TREE_TAG": "other"},
                start_new_session=True,
            )
        )
        end = time.monotonic() + 10
        while not _answers(port):
            assert time.monotonic() < end, f"stand-in server never answered on {port}"
            time.sleep(0.05)

    yield SimpleNamespace(
        repo=repo, rec=rec, pdf=pdf, serve_outside_the_run=serve_outside_the_run
    )

    for proc in others:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
    for pid in _tree(rec, "run"):
        if _alive(pid):
            os.kill(pid, signal.SIGKILL)


def _session(deploy, **kw):
    kw = {"startup_timeout": 30, "progress": lambda _msg: None, **kw}
    return renderer.mocr_server(deploy.repo, **kw)


@needs_fish_and_curl
def test_unpinned_run_serves_and_ocrs_on_one_free_high_port(deploy):
    with _session(deploy) as session:
        pages, _ = session.render(deploy.pdf)

    served_on = _port_arg(deploy.rec / "serve-run.argv")
    assert _port_arg(deploy.rec / "ocr.argv") == served_on
    assert served_on > 1023
    assert pages == ["OCR text"]


@needs_fish_and_curl
def test_a_run_stops_exactly_the_process_tree_it_started(deploy):
    deploy.serve_outside_the_run(_free_port())

    with _session(deploy) as session:
        session.render(deploy.pdf)

    started = _tree(deploy.rec, "run")
    assert len(started) == 3, f"launcher, server and worker expected: {started}"
    assert [p for p in started if _alive(p)] == [], "the started tree is gone"
    # The old stop script stopped every server on the machine.
    assert not (deploy.rec / "stop.called").exists()
    assert all(_alive(p) for p in _tree(deploy.rec, "other"))


@needs_fish_and_curl
def test_pinned_port_is_passed_to_both_wrappers(deploy):
    pinned = _free_port()
    assert pinned != 8000, "a pin other than dots-serve.fish's own default"

    with _session(deploy, port=pinned) as session:
        session.render(deploy.pdf)

    assert _port_arg(deploy.rec / "serve-run.argv") == pinned
    assert _port_arg(deploy.rec / "ocr.argv") == pinned


@needs_fish_and_curl
def test_pinned_port_reuses_a_running_server_and_leaves_it_running(deploy):
    pinned = _free_port()
    deploy.serve_outside_the_run(pinned)

    with _session(deploy, port=pinned) as session:
        session.render(deploy.pdf)

    assert not (deploy.rec / "serve-run.argv").exists(), "no second server started"
    assert _port_arg(deploy.rec / "ocr.argv") == pinned
    assert not (deploy.rec / "stop.called").exists()
    assert all(_alive(p) for p in _tree(deploy.rec, "other"))


@needs_fish_and_curl
def test_starts_that_time_out_leave_no_server_running(deploy, monkeypatch):
    # ingest.py catches each document's error and moves on to the next, so a
    # second escalation in the same run starts a second server.
    monkeypatch.setenv("FAKE_VLLM_STARTUP", "hang")

    with _session(deploy, startup_timeout=1) as session:
        for _document in range(2):
            with pytest.raises(RuntimeError, match="not ready within"):
                session.render(deploy.pdf)

    started = _tree(deploy.rec, "run")
    assert len(started) == 6, f"two launcher-server-worker trees expected: {started}"
    assert [p for p in started if _alive(p)] == [], "every started tree is gone"


@needs_fish_and_curl
def test_a_start_that_dies_stops_what_it_left_before_raising(deploy, monkeypatch):
    monkeypatch.setenv("FAKE_VLLM_STARTUP", "crash")

    with _session(deploy) as session:
        with pytest.raises(RuntimeError, match="exited during startup"):
            session.render(deploy.pdf)
        started = _tree(deploy.rec, "run")
        assert len(started) == 3, f"launcher, server and worker expected: {started}"
        assert [p for p in started if _alive(p)] == [], "the worker left is gone"


@needs_fish_and_curl
def test_a_start_whose_processes_all_exited_raises_its_own_error(deploy):
    (deploy.repo / "dots-serve.fish").write_text("exit 1\n")

    with (
        _session(deploy) as session,
        pytest.raises(RuntimeError, match="exited during startup"),
    ):
        session.render(deploy.pdf)


@needs_fish_and_curl
def test_a_server_that_stops_answering_is_stopped_before_another_starts(deploy):
    with _session(deploy) as session:
        session.render(deploy.pdf)
        first = _tree(deploy.rec, "run")
        assert len(first) == 3, f"launcher, server and worker expected: {first}"
        # The server records its pid after the launcher and before its worker.
        os.kill(first[1], signal.SIGKILL)
        pages, _ = session.render(deploy.pdf)

    started = _tree(deploy.rec, "run")
    assert len(started) == 6, f"a second tree was started: {started}"
    assert pages == ["OCR text"]
    assert [p for p in started if _alive(p)] == [], "both started trees are gone"


@pytest.mark.parametrize(
    ("mocr_section", "expected_port"),
    [('repo = "~/dots.mocr"\n', None), ('repo = "~/dots.mocr"\nport = 8123\n', 8123)],
)
def test_config_readers_pin_a_port_only_when_one_is_set(
    tmp_path, monkeypatch, mocr_section, expected_port
):
    monkeypatch.syspath_prepend(str(_SKILL))
    import ingest
    import render

    config = tmp_path / "config.toml"
    config.write_text(f'zettelkasten_root = "{tmp_path}"\n\n[mocr]\n{mocr_section}')
    monkeypatch.setattr(render, "CONFIG_PATH", config)
    monkeypatch.setattr(ingest, "CONFIG_PATH", config)

    assert render.load_mocr_cfg()["port"] == expected_port
    assert ingest.load_config()["mocr"]["port"] == expected_port
