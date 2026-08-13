#!/usr/bin/env python3
# /// script
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Administrative CLI for PostgreSQL-backed local mail; agents use MCP tools."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from local_mail_core import require_text, validate_subject
from local_mail_store import MailStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as", dest="actor")
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register")
    register.add_argument("address")
    register.add_argument("--location", required=True, type=Path)
    register.add_argument("--observe-all", action="store_true")
    send = commands.add_parser("send")
    send.add_argument("--to", action="append", required=True)
    send.add_argument("--subject", required=True)
    send.add_argument("--body", required=True)
    commands.add_parser("inbox")
    pull = commands.add_parser("pull")
    pull.add_argument("thread_id")
    reply = commands.add_parser("reply")
    reply.add_argument("thread_id")
    reply.add_argument("--body", required=True)
    args = parser.parse_args()
    store = MailStore()
    if args.command == "register":
        store.register(args.address, args.location, args.observe_all)
        result = {"address": args.address}
    elif not args.actor:
        parser.error("--as ADDRESS is required")
    elif args.command == "send":
        result = store.send(
            sender=args.actor,
            recipients=args.to,
            subject=validate_subject(args.subject),
            body=require_text(args.body, "body"),
            thread_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
        )
    elif args.command == "inbox":
        result = store.inbox(args.actor)
    elif args.command == "pull":
        result = store.pull(args.actor, args.thread_id)
    else:
        result = store.reply(
            sender=args.actor,
            thread_id=args.thread_id,
            body=require_text(args.body, "body"),
            message_id=str(uuid.uuid4()),
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
