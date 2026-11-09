# Carry On

Carry On reviews enrolled Codex parent sessions when they stop, when nothing is
running, and when their workers finish. A separate Terra session checks the request,
later human decisions, recent actions, and worker reports. It resumes the original
parent only when it identifies a concrete action the user already authorized.

This is a Codex-only plugin. Install and trust its hooks through Codex's plugin
manager. It requires `uv`, Python 3.14 or newer (resolved by `uv`), `websockets==16.0`,
and an existing Codex app-server daemon with the 0.167 thread/turn protocol.
The plugin uses the configured `uv` cache and existing Codex authentication.

SessionStart and Stop enroll the current root session. A detached watcher persists
after the hook and main turn exit, polls every five seconds, and observes only those
enrolled roots and their descendants. It connects directly to the daemon's Unix
WebSocket control socket, discovered from `codex app-server daemon version`.
It does not launch another app-server. An open Codex client must keep the parent
loaded; an unloaded or closed session is not resumed.

The reviewer is `gpt-6.1-terra` at medium effort, ephemeral, read-only, and isolated
from project instructions. Hooks, plugins, built-in action tools (including sleep),
skills, and configured MCP servers are disabled in its thread. Codex may still expose
the clock's current-time helper under its native tool selection. The reviewer reads
conversation evidence and returns `continue`, `wait` for work still running, or
`stop` for completion,
cancellation, or a decision only the human can make. It cannot authorize new work.
Reviews consume model tokens, including checks that correctly leave the parent idle.

Interruptions, pending approvals/input, busy parents, and unknown runtime state
suppress wake-ups. A real nonempty UserPromptSubmit re-arms an interrupted parent;
the plugin's own tool output does not run that hook. SessionEnd ends enrollment.
Unchanged evidence is checked once.
Two continuation attempts without new user input, tool results, or worker evidence stop
further automatic nudges. Repeating the same failed command and output does not count
as progress. Reviewer failures retry at most
three times for unchanged evidence and remain visible in the state and log.

Interrupt and SessionEnd have Codex's native three-second hook budget. Their Python
handler writes pause/end state for the exact enrolled session before any daemon
discovery or connection, then exits. Cold `uv` startup or interpreter/dependency
provisioning can still exhaust that budget before Python starts; warm-hook checks
do not establish cold-start delivery.

Long conversations are read in pages. Review input keeps the first request, recent
human decisions, recent actions, and worker evidence under a bounded budget. Omitted
context is explicit: it may still establish specific unfinished work, but cannot
establish completion. Missing evidence leaves the parent idle with a diagnostic.

The watcher checks the parent again immediately before waking it. The daemon has no
atomic version condition on `turn/start`, so a user turn arriving in the final interval
can still receive the continuation as queued tool output. The wake is attributed to
the plugin, rather than appearing as a new human request. Wake attempts are persisted
before sending; an uncertain delivery is not retried against unchanged evidence.

## Controls and diagnostics

Run controls with the installed plugin's `PLUGIN_ROOT` and `PLUGIN_DATA` values.
In Codex 0.167, hook data is derived as
`<codexHome>/plugins/data/<plugin-name>-<marketplace-name>`
([store](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/core-plugins/src/store.rs#L79-L116),
[hook environment](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/hooks/src/engine/discovery.rs#L294-L302)).
The installed hook source path and daemon's Codex home were read back on this
machine. These fish commands use those values and the source-derived data path:

```fish
set -x PLUGIN_ROOT /home/brian/.codex/plugins/cache/denubis-plugins/denubis-hook-carry-on/0.1.0
set -x PLUGIN_DATA /home/brian/.codex/plugins/data/denubis-hook-carry-on-denubis-plugins
uv run --script "$PLUGIN_ROOT/hooks/carry-on.py" --status
uv run --script "$PLUGIN_ROOT/hooks/carry-on.py" --stop
uv run --script "$PLUGIN_ROOT/hooks/carry-on.py" --start
```

For another Codex home or plugin version, use that host's installed hook source
path from `/hooks` and its Codex home. The data path above is derived from the
0.167 implementation; untrusted hooks have not yet supplied a live environment
readback for this installation.

`--status` prints the endpoint state directory, watcher PID, enrollments, last
outcomes, and errors. `watcher.log` in that directory contains runtime diagnostics.
`CARRY_ON_SOCKET` or `--socket` selects a control socket explicitly for local testing.
State files are locked and atomically replaced under `PLUGIN_DATA`, separate for
each daemon endpoint. The process lock permits one watcher per data root and endpoint.

**Run `--stop` before disabling or uninstalling the plugin.** Removing hooks does not
terminate an already detached watcher. Stop writes a persistent disabled marker,
prevents the current review from waking the parent, and lets the watcher exit after
its bounded operation. Hooks leave it disabled until `--start` removes that marker.
Start resumes observation of existing enrollments; a later SessionStart or Stop
enrolls a new parent. A lost wake response is reported as `delivery_uncertain` and
requires changed session evidence before another automatic attempt.

Repository checks:

```fish
uv run --frozen pytest -q tests/test_carry_on.py
uv run --frozen ruff check plugins/denubis-hook-carry-on/hooks tests/test_carry_on.py
uv run --frozen ty check --extra-search-path plugins/denubis-hook-carry-on/hooks plugins/denubis-hook-carry-on/hooks tests/test_carry_on.py
```

These checks establish deterministic behavior at simulated transport boundaries.

## Observed live checks and limits

On 2026-11-09, a controlled source-tree watcher loop connected to the existing
0.167.0 daemon, asked a separate Terra reviewer about an idle synthetic parent and
resumed that same parent from `PHASE_ONE_DONE` to its already-authorized
`PHASE_TWO_DONE`. The continuation arrived as plugin-attributed tool output.
Status and stop controls succeeded, and the stopped loop cleared its recorded PID.
The trial used the real watcher loop in a test thread; native installed-hook
dispatch and detached-process startup are separate checks.

Seven prewritten Terra cases matched six expected decisions. The completed
`all_finished` case incorrectly received `continue`, requesting independent
evidence of the change. A separate completed case with a diff and resulting CSV
received `stop`. That additional case does not erase the original false positive.
These examples establish neither general classification accuracy nor that every
legitimate stop will remain undisturbed.

The native installation request succeeded, and post-install readback reports the
plugin installed and enabled. Its six hook declarations are enabled but
`untrusted`, so Codex skips their execution until the person reviews and trusts
them through `/hooks`. Installed-hook execution and the live
last-worker-completion path are still being verified. Human acceptance of useful
nudges and justified stops remains pending.
