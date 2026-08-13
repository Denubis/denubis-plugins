#!/usr/bin/env python3
# /// script
# dependencies = ["mcp[cli]>=1.29,<2", "psycopg[binary]>=3.2"]
# ///
"""Native Codex tools for PostgreSQL-backed local mail."""

from __future__ import annotations

import uuid
from pathlib import Path

from local_mail_core import require_text, validate_subject
from local_mail_store import MailStore
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "local-mail",
    instructions=(
        "Use these tools for durable coordination with other local Codex sessions."
    ),
)


def actor(username: str) -> str:
    return MailStore().require_actor(username, Path.cwd())


@mcp.tool()
def register(username: str) -> str:
    """Register a chosen username for this MCP session's worktree."""
    peers = MailStore().register(username, Path.cwd())
    if peers:
        return (
            f"registered {username} at {Path.cwd()}\n"
            f"WARNING: shared worktree with {', '.join(peers)}; coordinate file "
            "ownership before editing"
        )
    return f"registered {username} at {Path.cwd()}"


@mcp.tool()
def send(username: str, recipients: list[str], subject: str, body: str) -> dict:
    """Send a new subject-and-body thread to registered mailboxes."""
    return MailStore().send(
        sender=actor(username),
        recipients=recipients,
        subject=validate_subject(subject),
        body=require_text(body, "body"),
        thread_id=str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
    )


@mcp.tool()
def inbox(username: str) -> list[dict]:
    """List unread thread subjects without exposing message bodies."""
    return MailStore().inbox(actor(username))


@mcp.tool()
def pull(username: str, thread_id: str) -> dict:
    """Read a thread and mark its deliveries read for this mailbox."""
    return MailStore().pull(actor(username), thread_id)


@mcp.tool()
def reply(username: str, thread_id: str, body: str) -> dict:
    """Reply to an existing thread as a participant or observer."""
    return MailStore().reply(
        sender=actor(username),
        thread_id=thread_id,
        body=require_text(body, "body"),
        message_id=str(uuid.uuid4()),
    )


if __name__ == "__main__":
    mcp.run()
