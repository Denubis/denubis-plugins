# denubis-local-mail

PostgreSQL-backed peer mail for collaborating local Codex and Claude sessions.

The bundled MCP server gives Codex native `register`, `send`, `inbox`, `pull`,
and `reply` tools. Agents do not invoke a Python CLI through Bash. PostgreSQL is
authoritative for message bodies, routing, threads, and per-mailbox
`new`/`notified`/`read` state; nothing is written to a parent worktree.

Each MCP caller chooses a username. Registration binds that username to the
server's worktree, cannot move an existing registration, and later calls require
both to match. Observer access is available only through the administrative CLI.
Multiple usernames may share a worktree. Set `LOCAL_MAIL_USERNAME` before launch
so the Stop hook knows which mailbox to notify. Registration warns when other
usernames share the worktree; coordinate file ownership before editing.

The Stop hook emits a valid Codex continuation when new subjects are waiting.
It shows subjects once, never bodies, and stays silent when `stop_hook_active`
prevents recursion.

By default the plugin connects to the local `postgres` database and uses the
`local_mail` schema. Set `LOCAL_MAIL_DATABASE_URL` or `LOCAL_MAIL_SCHEMA` before
starting Codex to override either value.

Active supervision, approvals, interrupts, crashes, and completion remain outside
the mail channel.

For local Claude development from the repository root:

```console
LOCAL_MAIL_USERNAME=claude-cross-model \
  claude --plugin-dir ./plugins/denubis-local-mail
```

## Verified

A live Claude 2.1.226 and Codex 0.145.0 session registered separate usernames
in this worktree, exchanged messages both ways, pulled bodies deliberately, and
received a subject-only Stop notification. The focused suite also exercises the
PostgreSQL round trip, identity binding, shared-worktree registration, and hook
recursion guard.

## Current limits and next work

Single-host and text-only. There is no daemon, attachment support, receipt, address
directory, write lock, or idle-session actuator. File ownership is advisory: agents
must mail intended paths before overlapping edits. Add enforcement only if real
collisions show that advisory coordination is insufficient. A five-minute Ready-state
reminder belongs in the guarded supervisor because MCP and background hooks cannot
safely start an idle Codex turn.
