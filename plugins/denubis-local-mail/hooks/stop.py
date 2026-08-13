#!/usr/bin/env python3
# /// script
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Continue a stopping Codex turn once when local mail is waiting."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from local_mail_store import MailStore, MailStoreError


def handle(payload: dict) -> dict:
    if payload.get("stop_hook_active") is True:
        return {}
    username = os.environ.get("LOCAL_MAIL_USERNAME")
    if not username:
        return {"systemMessage": "Local mail hook needs LOCAL_MAIL_USERNAME"}
    digest = MailStore().notify(username, Path(payload["cwd"]))
    if not digest:
        return {}
    lines = ["You've got local mail. Use the local-mail MCP tools to inspect it:"]
    lines.extend(
        f"- {item['thread_id']} — {item['subject']} "
        f"({item['message_count']} from {item['from']})"
        for item in digest
    )
    return {"decision": "block", "reason": "\n".join(lines)}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        output = handle(payload) if isinstance(payload, dict) else {}
    except (KeyError, MailStoreError, OSError) as error:
        output = {"systemMessage": f"Local mail unavailable: {error}"}
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
