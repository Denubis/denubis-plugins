## bash
- Invocation: `bash`
- Version: 5.2.21
- Path: /usr/bin/bash
- Notes: target runtime for local wrapper scripts

## bats
- Invocation: `bats`
- Version: 1.10.0
- Path: /usr/bin/bats
- Notes: shell integration tests

## codex
- Invocation: `codex`
- Version: 0.144.1
- Path: /home/brian/.volta/bin/codex
- Notes: emitted commands must match this CLI

## claude
- Invocation: `claude`
- Version: 2.1.232
- Path: /home/brian/.local/bin/claude
- Notes: plugin validation and marketplace commands must match this CLI

## Context7
- Invocation: `mcp__context7__resolve_library_id`, then `mcp__context7__query_docs`
- Prohibited: `npx ctx7`
- Notes: use the authenticated MCP tools; shell subprocesses do not inherit the MCP credential and fall back to a separate quota

## cc-search-chats
- Invocation: `cc-search-chats`
- Version: 2.0.0a5
- Path: /home/brian/.local/bin/cc-search-chats
- Notes: exact transcript resolution uses `cc-search-chats context <message-uuid> --json`

## fish
- Invocation: `fish`
- Version: 4.8.1
- Path: /usr/bin/fish
- Notes: emitted commands are pasted into the user's interactive shell

## git
- Invocation: `git`
- Version: 2.43.0
- Path: /usr/bin/git

## node
- Invocation: `node`
- Version: 26.5.0
- Path: /home/brian/.volta/bin/node
- Notes: used by the official Codex manual helper

## shellcheck
- Invocation: `shellcheck`
- Version: 0.9.0
- Path: /usr/bin/shellcheck

## uv
- Invocation: `uv`
- Version: 0.10.8
- Path: /home/brian/.local/bin/uv
- Notes: configured cache is `/media/brian/storage/.cache/uv`

## ruff
- Invocation: `uvx ruff`
- Version: 0.15.21
- Notes: not declared in the project environment; `uvx` uses the configured uv cache
