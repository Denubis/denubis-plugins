---
name: using-local-mail
description: Use for durable, low-interruption coordination among local Codex sessions.
---

# Using Local Mail

Use the `local-mail` MCP tools. Never invoke the implementation through Bash.

Register a chosen username once. The MCP server binds it to the session worktree;
the username is the human-facing alert boundary. Observer mailboxes are configured
only through the administrative CLI. Launch the session with the same username in
`LOCAL_MAIL_USERNAME` so its Stop hook checks the correct mailbox.

If registration warns that other usernames share the worktree, immediately send
them a thread stating your task and intended files. Agree on file ownership before
editing overlapping paths; mail delivery does not prevent filesystem races.

Use `send` for contradictions, decisions, dependencies, corrections, and handoffs.
Keep subjects short and put detail in the body. Use `inbox` to inspect subjects,
`pull` to read a relevant thread, and `reply` to continue it.

The Stop hook may continue a completed turn once with a subject-only "you've got
mail" prompt. It never includes bodies, and a recursive Stop remains silent.

Local mail is not the supervisor control channel. Approvals, interrupts, prompts,
completion, and crashes remain with the guarded supervisor tools.
