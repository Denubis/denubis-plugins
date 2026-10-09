# Handover: Codex supervision watch and "waiting on me" indicator as a Claude Code mod

Written 2026-10-09 by a Claude Code session (Fable 5.1) for ingestion by a separate
session. Nothing here is implemented. Nothing here is a ruling. Items marked
**human** are Brian's words or existing ADRs; items marked **asserted** were derived by
Opus xhigh audit agents and spot-checked by the dispatching session against this
build's mod API types file, and must be re-verified before relying on them.

## 0. What a mod is

A mod is a TypeScript hooks module inside a plugin (`hooks/hooks.json` ->
`{"modules": ["./register.tsx"]}`, `export const register: Register = (on, options)`).
Hooks are `($, e, next)` and can run before, after, instead of, or around engine events.
Load the bundled `plugin-authoring` skill before designing; it writes the API types file
for the running build (2.1.295 at time of writing, 21,416 lines) and holds `reference.md`
and `examples/pane.tsx`. Line numbers below refer to that `claude-code.d.ts`; they will
drift between builds, so grep by name.

Mods are not sandboxed. They do not run under `claude -p` with a surface (reference.md
line 164). A `sec-default` mod loads first on Team/Enterprise or managed-settings
machines; what it blocks has **not been checked** and its source is not bundled.

## 1. Problem A: the Codex supervision loop costs model turns

### Current mechanism (asserted, paths verified)

- `plugins/denubis-external-agents/scripts/codex_supervisor.py` (about 2,850 lines) is
  run under Claude Code's Monitor tool. It listens on a per-pane UNIX datagram socket
  fed by Codex hooks (around lines 950 and 986) and falls back to tmux screen polling
  (around 1099 to 1137).
- `plugins/denubis-external-agents/skills/supervising-codex/SKILL.md` lines 585 to 772
  tell the model how to arm, re-arm, and stop the watch.
- `~/.claude/bin/tmux-send-guard` polices what may be typed into the Codex pane.

### The limitation (human)

ADR 0009 line 38: Monitor "requires a `timeout_ms` capped at thirty minutes". Every
expiry wakes the model for a re-arm turn.

Brian, 2026-07-23: "why are you on a timer? This is not at all the correct way to
monitor" (`ccchat:v1:claude:7f5a7a4d-e1b5-44d4-beb2-203476ea4726:uuid:4cd872cb-3bf4-4775-bc93-ef720b06b13a`).

Brian, 2026-10-08: "if the pane is idle, there shouldn't be a monitor!" (raw record
`14b58d35-082c-49d3-8d3c-495e8211cbb2`, line 98; this session file was not in the chat
index at the time of the scan).

### Mod capabilities that address it (asserted; names confirmed in the types file)

| Need | API | Where |
| --- | --- | --- |
| A watch with no cap and no re-arm | `$.process.spawn(request)` returns a `HookStream`; a session-life child | D:3534 to 3553 |
| Wake the session only on an actionable event | `$.prompt.submit(input)` | D:2938 to 2949, 4721 |
| Show Codex state without a model turn | `$.ui.open({id,title})` plus `ui.render` on `Pane` | D:2500, examples/pane.tsx |
| Approve or answer from the pane | `Button` elements in the pane tree, handlers call `$.process.run` to tmux send-keys | examples/pane.tsx |
| Notify | `$.ui.notify(text)` / `$.ui.toast(text)` | D:2465, 2447 |
| Persist watch state across reload | `$.state` (session) / `$.store` (cross-session), declared in `types/index.d.ts` | reference.md |

### Shape (asserted, a proposal not a design)

1. `session.start`: register `/codex-watch` via `$.command.register`; do not spawn.
2. `command.run` for `/codex-watch <pane>`: `$.process.spawn` the existing
   `codex_supervisor.py` in a streaming mode (it already owns the socket and the tmux
   fallback); record the pane id in `$.state`.
3. On each stream chunk that is one of the four actionable events the supervisor
   already classifies, call `$.prompt.submit` with a one-line announcement. Non-actionable
   chunks only update the pane atom. This puts ADR 0009's "announce once" into code.
4. `ui.render` on `Pane` draws the supervisor's last state and buttons for the allowed
   send-keys verbs, routed through `tmux-send-guard`.
5. Idle pane: the child keeps the socket open at no model cost. Whether ADR 0009's
   "an idle pane gets no monitor" still has a purpose once a watch costs no turns is
   **a decision for Brian**, not for the implementer.

### What stays

- The Python supervisor, its verbs, its tests, and its Codex-side hooks.
- tmux as the transport into the Codex pane; `tmux-send-guard`; the send-keys scope
  policy of 2026-07-28 quoted in that guard.
- ADR 0007: the supervisor reads Codex session files and `/proc` locks; untouched.
- ADR 0010: spawned Codex has no question widget; untouched.

### Risks (asserted)

- The spawned child dies on module hot-reload (D:3520 to 3522). The mod must re-spawn
  from `$.state` on `session.start`.
- An unasked pane only seats from 144 columns (D:2482 to 2484); a tmux window already
  split for Codex may be narrower. A pane the person opens seats at any width.
- No surface under `claude -p`; the Monitor route or a headless fallback remains for
  that case.
- Hook errors fail open unless caught (`.catch`); the watch must log, not vanish.
- Runtime behaviour of any of this is untested. The API is early access.

## 2. Problem B: "which session is waiting on me"

### The need (human)

- 2026-05-18: "there's no useful way to see when they're waiting for my feedback. We
  must continue to run via ssh/byobu"
  (`ccchat:v1:claude:1db0be1f-f2bb-49aa-83fa-919e30a0c872:uuid:9743687c-9aff-4af1-b081-5b0931c87ea8`).
- 2026-05-19: "'agent working' isn't super useful, since it doesn't indicate *which*
  of the agents"
  (`ccchat:v1:claude:1db0be1f-f2bb-49aa-83fa-919e30a0c872:uuid:0be77112-ff64-4aec-a283-897d73c7d1de`).
- 2026-07-17: "20 tmux things in byobu all stacking up with no state so I can't tell
  what's waiting for me"
  (`ccchat:v1:codex:019f6d93-c8ba-71d1-9d6d-7c413c28cb29:ordinal:8:sha256:122835fc0ac534b0a9b0a8e247df8ec81ca6632082ee0567852f24b77cadfa7a`).
- 2026-08-08 ruling (human): prefer shipped inboxes, "it's better than inventing our
  own" (message following
  `ccchat:v1:codex:019fe39a-4c80-7fc2-9cdf-65e8ba571bb6:ordinal:142:sha256:fdeeb3e22249a2526817a3896d9c38156f7cdea19be496818d35f3194d3b87cb`).
  Verify this ruling at source before designing; it may constrain Problem B to a view
  over existing notification channels.

### Current mechanism (asserted)

- `Notification` hook in `~/.claude/settings.json` ->
  `~/people/Brian/session-runner/bin/notify-agent.sh` (contents not read).
- A Byobu status segment, and the paused `tmux-agent-attention` project in
  `~/people/Brian/permission-notifier-manager`.

### Mod capabilities (asserted)

- `tool.check` (permission request pending) and `turn.complete` / `session.end` hooks
  write `{sessionId, tmuxWindow, state, since}` into `$.store` (cross-session).
- A `Pane` or `AbovePrompt` band in any session lists every session's state from
  `$.store`; a `Button` runs `tmux select-window` via `$.process.run`.
- `$.ui.notify` for the transition into "waiting".

### Limits

- Per Claude session only. Codex panes still need the Byobu route or the Problem A
  pane. The two could share the `$.store` record shape.
- `$.store` concurrency semantics across simultaneously running sessions are
  **not checked**.

## 3. Related, not in scope here

- tmux window naming: two writers conflict today (`exec-session-naming` skill and
  `workflow_statusline/tmux.py` lines 29 to 39, which renames to `Cl:<location>` unless
  a lock file nobody writes exists). Brian wants proper renaming. A mod could be the
  single owner via `session.start`, `classic.CwdChanged` (D:3626) and `$.process.run`.
  Native `sessionTitle` (D:1296 to 1298, classic `UserPromptSubmit`/`SessionStart`
  hook output) sets the Claude session title, not the tmux window name; both may be
  wanted. Being handled separately.
- Status line and quota: being handled by a separate Fable agent.

## 4. Open decisions for Brian (do not resolve in the implementing session)

1. Does ADR 0009's "idle pane is unwatched" survive a zero-cost watch?
2. Grant grammar for which supervisor events may call `$.prompt.submit`.
3. Whether Problem B is a view over existing notification channels (per the 2026-08-08
   ruling) or a new store.
