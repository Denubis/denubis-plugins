"""Two clients, installed Codex, loopback canned responses; no real model calls."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from websockets.sync.client import unix_connect

from test_permission_queue_codex_server import adapter_module


class FixtureClient:
    def __init__(self, path):
        self.connection = unix_connect(str(path), open_timeout=1, close_timeout=0.2)
        self.sequence = 0
        self.messages = []
        self.call("initialize", {"clientInfo": {"name": "fixture_native_peer", "version": "0"}, "capabilities": {"experimentalApi": True}})
        self.send({"method": "initialized"})

    def send(self, message):
        self.connection.send(json.dumps(message))

    def until(self, predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            message = json.loads(self.connection.recv(timeout=max(0.01, deadline - time.monotonic())))
            self.messages.append(message)
            if predicate(message):
                return message
        raise AssertionError("Installed daemon did not deliver expected event")

    def call(self, method, params):
        self.sequence += 1
        identifier = self.sequence
        self.send({"id": identifier, "method": method, "params": params})
        message = self.until(lambda value: "method" not in value and value.get("id") == identifier)
        assert "error" not in message, message
        return message["result"]

    def notification(self, method):
        return self.until(lambda value: value.get("method") == method)


@pytest.fixture
def installed_daemon(tmp_path):
    executable = shutil.which("codex")
    if executable is None:
        pytest.skip("Installed Codex CLI is required for this integration")
    sentinel = tmp_path / "executions.txt"
    command = shlex.join([sys.executable, "-c", f"from pathlib import Path; p=Path({str(sentinel)!r}); p.open('a').write('executed\\n')"])
    model_requests = []

    class Model(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            model_requests.append(body)
            assert body["model"] == "gpt-6.1-sol"
            index = len(model_requests) - 1
            response_id = f"fixture-response-{index}"
            if index in (1, 3):
                item = {"type": "function_call", "call_id": f"fixture-command-{index}", "name": "exec_command", "arguments": json.dumps({"cmd": command, "workdir": str(tmp_path), "yield_time_ms": 1000, "sandbox_permissions": "require_escalated", "justification": "Isolated harmless fixture sentinel only."})}
            else:
                item = {"type": "message", "role": "assistant", "id": f"fixture-message-{index}", "content": [{"type": "output_text", "text": "Canned local fixture response."}]}
            events = [
                {"type": "response.created", "response": {"id": response_id}},
                {"type": "response.output_item.done", "item": item},
                {"type": "response.completed", "response": {"id": response_id, "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
            ]
            encoded = "".join(f"data: {json.dumps(event)}\n\n" for event in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    model_thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    model_thread.start()
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text(
        'model="gpt-6.1-sol"\nmodel_reasoning_effort="xhigh"\n'
        'model_provider="fixture"\napproval_policy="on-request"\n'
        'sandbox_mode="workspace-write"\n'
        '[analytics]\nenabled=false\n'
        '[model_providers.fixture]\nname="Local canned fixture"\n'
        f'base_url="http://127.0.0.1:{server.server_port}/v1"\n'
        'wire_api="responses"\nrequires_openai_auth=false\n'
        'supports_websockets=false\nrequest_max_retries=0\nstream_max_retries=0\n'
    )
    path = tmp_path / "daemon.sock"
    env = dict(os.environ, CODEX_HOME=str(home), OPENAI_API_KEY="local-fixture-only")
    env.pop("CODEX_API_KEY", None)
    log = (tmp_path / "daemon.log").open("w")
    process = subprocess.Popen([executable, "app-server", "--listen", f"unix://{path}"], cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 10
        while not path.exists() and time.monotonic() < deadline:
            assert process.poll() is None, (tmp_path / "daemon.log").read_text()
            time.sleep(0.02)
        assert path.exists(), (tmp_path / "daemon.log").read_text()
        yield path, sentinel, model_requests
    finally:
        process.terminate()
        process.wait(timeout=5)
        log.close()
        server.shutdown()
        server.server_close()
        model_thread.join(timeout=3)
        assert not model_thread.is_alive()


def test_installed_daemon_shares_occurrences_and_only_first_answer_applies(installed_daemon, tmp_path):
    module = adapter_module()
    path, sentinel, model_requests = installed_daemon
    primary = FixtureClient(path)
    try:
        started = primary.call("thread/start", {"model": "gpt-6.1-sol", "modelProvider": "fixture", "cwd": str(tmp_path), "approvalPolicy": "on-request", "sandbox": "workspaceWrite"})
        thread_id = started["thread"]["id"]
        primary.call("thread/name/set", {"threadId": thread_id, "name": "Isolated approval fixture"})
        primary.call("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Seed the local fixture."}]})
        primary.notification("turn/completed")
        primary.call("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Display the harmless fixture command."}]})
        first = primary.until(lambda value: value.get("method") == "item/commandExecution/requestApproval")
        with module.CodexServer(path, timeout=3, snapshot_timeout=8) as secondary:
            selected = secondary.select(thread_id)
            assert selected.state == "blocked"
            occurrence, = selected.requests
            assert occurrence.request_id == first["id"]
            assert occurrence.params == first["params"]
            assert secondary.answer(occurrence.occurrence_id, "accept").status == "resolved"
            resolved = primary.notification("serverRequest/resolved")
            assert resolved["params"]["requestId"] == first["id"]
            primary.notification("turn/completed")
            assert sentinel.read_text() == "executed\n"
            primary.call("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Display the same command again."}]})
            current = primary.until(lambda value: value.get("method") == "item/commandExecution/requestApproval")
            assert current["id"] != first["id"]
            # Mimic a late native answer for the already retired first occurrence.
            primary.send({"id": first["id"], "result": {"decision": "accept"}})
            remaining, = secondary.snapshot(thread_id).requests
            assert remaining.request_id == current["id"]
            assert sentinel.read_text() == "executed\n"
            primary.send({"id": current["id"], "result": {"decision": "decline"}})
            primary.notification("serverRequest/resolved")
            primary.notification("turn/completed")
            assert secondary.snapshot(thread_id).requests == ()
            with pytest.raises(module.CodexError, match=r"stale|resolved"):
                secondary.answer(remaining.occurrence_id, "accept")
            assert sentinel.read_text() == "executed\n"
            assert len(model_requests) == 5
    finally:
        primary.connection.close()
