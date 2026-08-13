"""PostgreSQL storage for local mail."""

from __future__ import annotations

import os
import re
from contextlib import closing
from pathlib import Path
from typing import Any

import psycopg
from local_mail_core import validate_address
from psycopg.rows import dict_row

SCHEMA_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
DDL = """
CREATE TABLE IF NOT EXISTS mailboxes (
    address text PRIMARY KEY,
    location text NOT NULL,
    observe_all boolean NOT NULL DEFAULT false
);
ALTER TABLE mailboxes DROP CONSTRAINT IF EXISTS mailboxes_location_key;
CREATE INDEX IF NOT EXISTS mailboxes_location ON mailboxes(location);
CREATE TABLE IF NOT EXISTS threads (
    id uuid PRIMARY KEY,
    subject text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS participants (
    thread_id uuid NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    address text NOT NULL REFERENCES mailboxes(address),
    PRIMARY KEY (thread_id, address)
);
CREATE TABLE IF NOT EXISTS messages (
    id uuid PRIMARY KEY,
    thread_id uuid NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    sender text NOT NULL REFERENCES mailboxes(address),
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS deliveries (
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    recipient text NOT NULL REFERENCES mailboxes(address),
    state text NOT NULL DEFAULT 'new' CHECK (state IN ('new', 'notified', 'read')),
    notified_at timestamptz,
    read_at timestamptz,
    PRIMARY KEY (message_id, recipient)
);
CREATE INDEX IF NOT EXISTS deliveries_recipient_state
    ON deliveries(recipient, state);
CREATE INDEX IF NOT EXISTS messages_thread_created
    ON messages(thread_id, created_at, id);
"""


class MailStoreError(RuntimeError):
    """Raised when mail cannot be routed or read."""


class MailStore:
    """Persist complete mail messages in PostgreSQL."""

    def __init__(self, dsn: str | None = None, schema: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("LOCAL_MAIL_DATABASE_URL", "dbname=postgres")
        self.schema = schema or os.environ.get("LOCAL_MAIL_SCHEMA", "local_mail")
        if not SCHEMA_NAME.fullmatch(self.schema):
            raise MailStoreError("LOCAL_MAIL_SCHEMA must be a PostgreSQL identifier")

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        connection = psycopg.connect(self.dsn, row_factory=dict_row)
        connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
        connection.execute(f'SET search_path TO "{self.schema}"')
        connection.execute(DDL)
        return connection

    def register(
        self, address: str, location: Path, observe_all: bool = False
    ) -> list[str]:
        canonical = validate_address(address)
        if not location.is_dir():
            raise MailStoreError(f"mailbox location must exist: {location}")
        location = location.resolve()
        with closing(self._connect()) as connection, connection:
            inserted = connection.execute(
                """INSERT INTO mailboxes(address, location, observe_all)
                   VALUES (%s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (canonical, str(location), observe_all),
            )
            if inserted.rowcount == 0:
                existing = connection.execute(
                    "SELECT location, observe_all FROM mailboxes WHERE address = %s",
                    (canonical,),
                ).fetchone()
                if existing != {"location": str(location), "observe_all": observe_all}:
                    raise MailStoreError(f"mailbox already registered: {canonical}")
            return [
                row["address"]
                for row in connection.execute(
                    """SELECT address FROM mailboxes
                       WHERE location = %s AND address <> %s ORDER BY address""",
                    (str(location), canonical),
                )
            ]

    def send(
        self,
        *,
        sender: str,
        recipients: list[str],
        subject: str,
        body: str,
        thread_id: str,
        message_id: str,
    ) -> dict[str, Any]:
        sender = validate_address(sender)
        recipients = sorted({validate_address(value) for value in recipients})
        if not recipients:
            raise MailStoreError("at least one recipient is required")
        with closing(self._connect()) as connection, connection:
            self._require_mailboxes(connection, [sender, *recipients])
            observers = {
                row["address"]
                for row in connection.execute(
                    "SELECT address FROM mailboxes WHERE observe_all"
                )
            }
            delivered_to = sorted((set(recipients) | observers) - {sender})
            if not delivered_to:
                raise MailStoreError("message has no recipients after routing")
            connection.execute(
                "INSERT INTO threads(id, subject) VALUES (%s, %s)",
                (thread_id, subject),
            )
            connection.cursor().executemany(
                "INSERT INTO participants(thread_id, address) VALUES (%s, %s)",
                [(thread_id, address) for address in sorted({sender, *recipients})],
            )
            self._insert_message(
                connection, message_id, thread_id, sender, body, delivered_to
            )
        return {
            "delivered_to": delivered_to,
            "message_id": message_id,
            "thread_id": thread_id,
        }

    def reply(
        self, *, sender: str, thread_id: str, body: str, message_id: str
    ) -> dict[str, Any]:
        sender = validate_address(sender)
        with closing(self._connect()) as connection, connection:
            self._require_mailboxes(connection, [sender])
            allowed = connection.execute(
                """SELECT EXISTS(
                       SELECT 1 FROM participants WHERE thread_id = %s AND address = %s
                       UNION ALL
                       SELECT 1 FROM mailboxes WHERE address = %s AND observe_all
                   ) AS allowed""",
                (thread_id, sender, sender),
            ).fetchone()
            if not allowed or not allowed["allowed"]:
                raise MailStoreError(
                    f"thread is not available to {sender}: {thread_id}"
                )
            delivered_to = [
                row["address"]
                for row in connection.execute(
                    """SELECT address FROM (
                           SELECT address FROM participants WHERE thread_id = %s
                           UNION SELECT address FROM mailboxes WHERE observe_all
                       ) recipients WHERE address <> %s ORDER BY address""",
                    (thread_id, sender),
                )
            ]
            self._insert_message(
                connection, message_id, thread_id, sender, body, delivered_to
            )
        return {
            "delivered_to": delivered_to,
            "message_id": message_id,
            "thread_id": thread_id,
        }

    def inbox(self, recipient: str, *, only_new: bool = False) -> list[dict[str, Any]]:
        recipient = validate_address(recipient)
        with closing(self._connect()) as connection:
            self._require_mailboxes(connection, [recipient])
            return self._inbox(connection, recipient, only_new)

    def notify(self, username: str, location: Path) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection, connection:
            username = self._require_actor(connection, username, location)
            digest = self._inbox(connection, username, True)
            connection.execute(
                """UPDATE deliveries SET state = 'notified', notified_at = now()
                   WHERE recipient = %s AND state = 'new'""",
                (username,),
            )
            return digest

    def require_actor(self, username: str, location: Path) -> str:
        """Return username only when it is registered to this worktree."""
        username = validate_address(username)
        with closing(self._connect()) as connection:
            return self._require_actor(connection, username, location)

    def pull(self, recipient: str, thread_id: str) -> dict[str, Any]:
        recipient = validate_address(recipient)
        with closing(self._connect()) as connection, connection:
            thread = connection.execute(
                """SELECT subject FROM threads WHERE id = %s AND EXISTS (
                       SELECT 1 FROM messages m JOIN deliveries d ON d.message_id = m.id
                       WHERE m.thread_id = threads.id AND d.recipient = %s
                   )""",
                (thread_id, recipient),
            ).fetchone()
            if thread is None:
                raise MailStoreError(
                    f"thread is not available to {recipient}: {thread_id}"
                )
            messages = list(
                connection.execute(
                    """SELECT sender AS "from", body, id::text AS message_id
                       FROM messages WHERE thread_id = %s ORDER BY created_at, id""",
                    (thread_id,),
                )
            )
            connection.execute(
                """UPDATE deliveries SET state = 'read', read_at = now()
                   WHERE recipient = %s AND message_id IN
                       (SELECT id FROM messages WHERE thread_id = %s)""",
                (recipient, thread_id),
            )
        return {"subject": thread["subject"], "messages": messages}

    @staticmethod
    def _insert_message(  # noqa: PLR0917
        connection, message_id, thread_id, sender, body, recipients
    ):
        connection.execute(
            "INSERT INTO messages(id, thread_id, sender, body) VALUES (%s, %s, %s, %s)",
            (message_id, thread_id, sender, body),
        )
        connection.cursor().executemany(
            "INSERT INTO deliveries(message_id, recipient) VALUES (%s, %s)",
            [(message_id, recipient) for recipient in recipients],
        )

    @staticmethod
    def _require_mailboxes(connection, addresses: list[str]) -> None:
        found = {
            row["address"]
            for row in connection.execute(
                "SELECT address FROM mailboxes WHERE address = ANY(%s)", (addresses,)
            )
        }
        missing = sorted(set(addresses) - found)
        if missing:
            raise MailStoreError(f"unknown mailbox: {', '.join(missing)}")

    @staticmethod
    def _inbox(connection, recipient: str, only_new: bool) -> list[dict[str, Any]]:
        return list(
            connection.execute(
                """SELECT t.id::text AS thread_id, t.subject,
                          min(m.sender) AS "from", count(*)::int AS message_count,
                          CASE WHEN bool_or(d.state = 'new')
                               THEN 'new' ELSE 'notified' END AS state
                   FROM deliveries d
                   JOIN messages m ON m.id = d.message_id
                   JOIN threads t ON t.id = m.thread_id
                   WHERE d.recipient = %s
                     AND (CASE WHEN %s THEN d.state = 'new' ELSE d.state <> 'read' END)
                   GROUP BY t.id, t.subject ORDER BY max(m.created_at), t.id""",
                (recipient, only_new),
            )
        )

    @staticmethod
    def _require_actor(connection, username: str, location: Path) -> str:
        resolved = location.resolve()
        locations = [
            Path(row["location"])
            for row in connection.execute(
                "SELECT location FROM mailboxes WHERE address = %s", (username,)
            )
        ]
        if not any(
            resolved == registered or registered in resolved.parents
            for registered in locations
        ):
            raise MailStoreError(f"{username} is not registered for {resolved}")
        return username
