import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "denubis-local-mail"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

from local_mail_store import MailStore  # noqa: E402


@pytest.fixture
def store():
    schema = f"local_mail_test_{uuid.uuid4().hex}"
    value = MailStore(schema=schema)
    yield value
    with psycopg.connect("dbname=postgres", autocommit=True) as connection:
        connection.execute(f'DROP SCHEMA "{schema}" CASCADE')


def register_pair(store: MailStore, tmp_path: Path) -> tuple[Path, Path]:
    alice, bob = tmp_path / "alice", tmp_path / "bob"
    alice.mkdir()
    bob.mkdir()
    store.register("alice", alice)
    store.register("bob", bob)
    return alice, bob


def test_postgres_round_trip_has_no_message_files(
    store: MailStore, tmp_path: Path
) -> None:
    register_pair(store, tmp_path)
    receipt = store.send(
        sender="alice",
        recipients=["bob"],
        subject="Check the timeout",
        body="The body stays in PostgreSQL.",
        thread_id=str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
    )

    assert store.inbox("bob")[0]["subject"] == "Check the timeout"
    assert store.pull("bob", receipt["thread_id"])["messages"][0]["body"] == (
        "The body stays in PostgreSQL."
    )
    assert store.inbox("bob") == []
    assert list(tmp_path.rglob("*.md")) == []


def test_stop_hook_returns_codex_continuation_once(
    store: MailStore, tmp_path: Path
) -> None:
    _, bob = register_pair(store, tmp_path)
    store.send(
        sender="alice",
        recipients=["bob"],
        subject="You've got mail regression",
        body="quiet body",
        thread_id=str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
    )
    environment = os.environ | {
        "LOCAL_MAIL_SCHEMA": store.schema,
        "LOCAL_MAIL_USERNAME": "bob",
    }

    def run(active: bool = False):
        return subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--no-config",
                str(PLUGIN / "hooks" / "stop.py"),
            ],
            input=json.dumps({"cwd": str(bob), "stop_hook_active": active}),
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )

    first = run()
    assert first.returncode == 0, first.stderr
    output = json.loads(first.stdout)
    assert output["decision"] == "block"
    assert "You've got mail regression" in output["reason"]
    assert "quiet body" not in first.stdout
    assert json.loads(run(active=True).stdout) == {}
    assert json.loads(run().stdout) == {}


def test_codex_plugin_exposes_mcp_and_valid_stop_hook() -> None:
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    mcp_config = json.loads((PLUGIN / ".mcp.json").read_text())
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    skill = (PLUGIN / "skills" / "using-local-mail" / "SKILL.md").read_text()

    assert manifest["mcpServers"] == "./.mcp.json"
    assert "local-mail" in mcp_config["mcpServers"]
    assert (
        "${CLAUDE_PLUGIN_ROOT}/scripts/mcp_server.py"
        in mcp_config["mcpServers"]["local-mail"]["args"]
    )
    assert json.loads(
        (PLUGIN / ".claude-plugin" / "plugin.json").read_text()
    )["name"] == "denubis-local-mail"
    assert "suppressOutput" not in hooks["hooks"]["Stop"][0]["hooks"][0]
    assert "Never invoke the implementation through Bash" in skill


def test_actor_requires_username_and_worktree(store: MailStore, tmp_path: Path) -> None:
    alice, _ = register_pair(store, tmp_path)

    assert store.require_actor("alice", alice / "src") == "alice"
    with pytest.raises(RuntimeError, match="bob is not registered"):
        store.require_actor("bob", alice)


def test_registration_cannot_move_username(store: MailStore, tmp_path: Path) -> None:
    alice, bob = register_pair(store, tmp_path)

    store.register("alice", alice)
    with pytest.raises(RuntimeError, match="mailbox already registered"):
        store.register("alice", bob)
    assert store.require_actor("alice", alice) == "alice"


def test_multiple_users_share_worktree(store: MailStore, tmp_path: Path) -> None:
    worktree = tmp_path / "shared"
    worktree.mkdir()

    assert store.register("claude", worktree) == []
    assert store.register("codex", worktree) == ["claude"]

    assert store.require_actor("claude", worktree) == "claude"
    assert store.require_actor("codex", worktree) == "codex"


def test_mcp_registration_warns_on_shared_worktree(
    store: MailStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = tmp_path / "shared"
    worktree.mkdir()
    store.register("claude", worktree)
    monkeypatch.chdir(worktree)
    monkeypatch.setenv("LOCAL_MAIL_SCHEMA", store.schema)
    from mcp_server import register

    warning = register("codex")

    assert "WARNING: shared worktree with claude" in warning
    assert "coordinate file ownership" in warning
