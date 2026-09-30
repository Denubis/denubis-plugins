# ADR 0007 — The Codex supervisor reads session files; hooks cannot confirm a clear

**Status:** Accepted (2026-09-28). Released as `denubis-external-agents` 0.20.0, commit
`302fbb4`.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/48519351-cd50-49c9-ad66-8812b026f487.jsonl`:

- Line 357, record `9669cfee-0af3-4566-8ada-600a40bcce71`, answering the question "shall I
  have Opus 5.5 build the session-file route now?":
  "yes please? and frankly, uh, is session file more durable for *all* this work anyways?"
- Line 655, record `36a97fee-dd4e-410c-ad1e-9064567b6e72`, answering the question "when a
  pane holds several session files, should `--quota` read the main thread's file?":
  "if ... this is talking about the pane of a codex instance and its subagents, we don't
  care about codex's own subagents"

Line 655 is a message sent while a turn was running, so the record is an `attachment` of
type `queued_command`, not a `user` record.

Exact raw-record resolver, independent of chat-index freshness:

```sh
sed -n '357p;655p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/48519351-cd50-49c9-ad66-8812b026f487.jsonl
```

`cc-search-chats context <record id> --json` returned `malformed_locator` for both ids on
2026-09-30, so the raw resolver is the one to use.

The human messages select the session-file route and the treatment of sub-agents. The
ruling-out of hooks, and every mechanism below, rests on the technical evidence.

## Technical evidence

All observed on codex-cli 0.157.0 on 2026-09-28. The logs are frozen byte-for-byte in
[`0007-evidence-2026-09-28/`](0007-evidence-2026-09-28/); the two instruments carry a
`.txt` suffix so nothing treats them as project code.

| File | What it shows |
|---|---|
| `listen.py.txt` | The listener: binds the relay socket of one pane and prints each datagram. |
| `control.log` | Control. A synthetic `SessionStart` payload piped through the installed relay command produced one `busy` datagram, so the listener can hear the relay. |
| `hook-events.log` | 45 seconds covering Codex start-up and a `/clear` with no prompt sent: no datagram. |
| `hook-events3.log` | A second prompt in one session: one `busy`, one `done`. |
| `hook-events4.log` | The first prompt after a `/clear`: two `busy` 0.1 s apart, one `done`. |
| `log-session-end.sh.txt` | The temporary `SessionEnd` logger. It records identities only. |
| `session-end.log` | `SessionEnd` for a cleared session at 18:05:46.582; two more at 18:05:50, when Codex quit. |
| `e2e.log` | `--clear` then `--quota` run end to end against a throwaway pane. |

Observed outside the frozen files, in the session record named above:

- The `/clear` whose `SessionEnd` is the first line of `session-end.log` was submitted at
  about 18:04:45, so the hook fired about 61 seconds later. A second `/clear`, at about
  18:05:22, had produced no `SessionEnd` when Codex quit about 28 seconds later; the quit
  produced it.
- Codex holds a lock under `thread-writer-locks/` for each session before it writes
  anything else, keeps the old session's lock after `/clear`, and released it 59 seconds
  later in one measurement.
- A `/status` panel on a 200x25 pane lost its top rows and the `/status` echo line, and
  Codex keeps no scrollback, so the fresh panel could not be told from a stale one.
- One session file held rate-limit records for three allowances: 825 for `codex`
  (unnamed, one week), 414 for `base_model_inference` ("gpt-reserve", one week) and 587
  for `codex_bengalfox` (five hours). The newest record was not the weekly one.
- In every live pane that held session files, exactly one file's first record named
  itself as its own session, and the rest were sub-agent threads naming that one.

Documented, not observed: Codex's hooks reference (`https://learn.chatgpt.com/docs/hooks`,
read 2026-09-28) lists `SessionStart` with `source` values `startup`, `resume`, `clear`
and `compact`, and says the transcript format "isn't a stable interface". Codex's source
on `main` adds `fork`. Neither says when `SessionStart` fires. The observation above is
that it does not fire at the moment of a clear.

Inferred, not observed: the extra `busy` datagram in `hook-events4.log` is `SessionStart`
arriving with the first prompt. The relay strips event names, so the log cannot say.

## Context

`--clear`, `--compact` and `--quota` each typed `/status` and read the panel off the
screen. On 0.157.0 that failed twice: the completion menu changed shape, and the panel
grew taller than a squeezed pane. The screen is the least stable surface Codex offers.

Hooks looked like the durable alternative, because every hook payload carries
`session_id`, `transcript_path` and `model` under a documented contract.

## Decision

- Session identity for `--clear` and `--compact` comes from the session locks the pane's
  Codex process holds, read from `/proc`. `--clear` requires an id that was not held
  before. `--compact` requires that no new id appeared.
- `--quota` reads the plain weekly allowance from the main thread's session file and
  prints the reading's age. It ignores sub-agent files, other allowances, and any record
  whose reset time has passed.
- When the files cannot answer, each verb falls back to typing `/status`.
- Hooks are not used to confirm a clear. They stay what they were: wake-ups for the
  monitor.
- No age limit is applied to a quota reading. Whether one should exist is the human's to
  rule.

## Consequences

- A squeezed pane no longer breaks `--clear`, or `--quota` on a pane that has done work.
- A pane that has just been cleared, or never been sent a prompt, has no session file, so
  `--quota` still reads the screen there and still needs a pane tall enough for the panel.
- A file reading is an upper bound on what is left. Every pane draws on one allowance, and
  an idle pane's file stops updating: on 2026-09-28 six panes against the same reset read
  44% left from a reading one minute old and 66% from one four and a half hours old.
- The session file format is not a published contract, and Codex ships a
  `migrate-rollouts` command, so the format is in motion. The fallback is what keeps a
  format change from becoming an outage.
- The `/proc` route is Linux-only. Elsewhere the verbs use the fallback.

## Not established

- `--compact` against a live pane.
- Whether an old session's sub-agent locks are still held after `/clear`.
- Whether the `PreCompact` and `PostCompact` hooks, which 0.157.0 lists and this project
  does not register, could confirm a compaction.
- The mapping from `limit_id: "codex"` to the panel's plain `Weekly limit:` row against
  the 0.157.0 source. It was read on `main` only.
