# agent-notice-log

A Claude Code mod (a plugin built from a hooks module) that records what reaches the main
conversation, so you can see how agent notices really arrive. It was built to check what
`denubis-hook-quiet-agents` matches on. It changes nothing: every prompt and delivery passes on
exactly as it came.

## It writes what you type to disk

**This plugin writes the first 300 characters of every prompt submitted to the main
conversation, including everything you type yourself, to a plain-text file on disk.** It
does the same for every message delivered to the session from another agent or session,
such as a teammate's report or idle notice. Characters are counted in UTF-16 code units,
so an emoji counts as two.

The file is never rotated, trimmed or read back, so it grows for as long as the plugin is
enabled. Anyone who can read the file can read the start of every prompt. Enable the
plugin while you need the observations, then disable it and delete the file.

## Where the file is

By default the file is `agent-notice-log.jsonl` in the Claude config directory:

- `$CLAUDE_CONFIG_DIR/agent-notice-log.jsonl` when `CLAUDE_CONFIG_DIR` is set;
- otherwise `~/.claude/agent-notice-log.jsonl`.

Set the `log_path` option to put it elsewhere, in the dialog shown at install or as the
plugin's row in `/config`. The value must be an absolute path or start with `~/`, which
is expanded with `HOME`. The directory must already exist. A relative path is refused,
because it would resolve against whatever directory the session runs in.

## How it writes

Each observation is one JSON line, appended with `tee -a <file>`, the line given on
standard input and no shell involved. The plugin waits for each write before the next, so
lines keep the order the hooks saw them in. It needs `tee` on the `PATH`.

A line from a prompt holds `ts`, `door` (`prompt.submit`), `origin`, `isMeta`, `keys`
(every field the event carried), `textLength`, `head` (the first 300 characters) and,
when the prompt carries one, `turnId`. A line from a delivery holds the same fields with
`door` set to `session.receive`, no `isMeta` or `turnId`, and `agentId` when the delivery
went to an agent's own loop rather than the main conversation.

When a line cannot be written, the prompt or delivery still passes on. The plugin first
tries to append an error line to the same file. When that fails too, or when no log path
can be worked out, the reason goes to the debug log (`claude --debug`) and the status line
reads `agent-notice-log: the log is not being written (see the debug log)`.

## Not yet verified

- The default path and the `log_path` option are established by the plugin's tests. A
  live install has not yet written to them.
- The plugin reads `CLAUDE_CONFIG_DIR` and `HOME` from the environment Claude Code runs
  in. A `CLAUDE_CONFIG_DIR` set only in a settings file has not been checked to reach it.

## Install

At the prompt of a Claude Code terminal session:

```text
/plugin install denubis-hook-agent-notice-log --marketplace Denubis/denubis-plugins
```

With the `denubis-plugins` marketplace already added:

```text
/plugin install denubis-hook-agent-notice-log@denubis-plugins
```

The plugin needs a Claude Code build that loads mods. It was written against the mods API
of Claude Code 2.1.309 and tested with 2.1.310.

## Development

```bash
claude plugin validate plugins/denubis-hook-agent-notice-log
claude plugin test plugins/denubis-hook-agent-notice-log
```

The top-level `tsconfig.json` extends `.claude-plugin/types/tsconfig.json`, which Claude
Code writes, and keeps out of git, only when it loads this folder as a mod under
development (`claude --plugin-dir`). Elsewhere, type-check with a config kept outside the
plugin folder that includes the `claude-code.d.ts` your build writes for the
plugin-authoring skill, plus this folder's `hooks` and `tests`.
