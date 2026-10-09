# Handover: status-line mod design (build 2.1.295)

Written 2026-10-09 by a Fable 5.1 subagent at medium effort (human-authorised). Design
only; nothing was written under `~/.claude/dev-mods`. Every claim is **observed**
(path:line) or **inferred**. Types file: `T` =
`/tmp/claude-1000/bundled-skills/2.1.295/fef47aa1ab5b0dbeb7f8648a4c0ff1f8/plugin-authoring/types/claude-code.d.ts`
(21,416 lines; regenerated per process, so re-grep after a restart). Status-line package:
`S` = `plugins/denubis-plan-and-execute/scripts/workflow_statusline/`.

## 1a. Correction (2026-10-09, dispatching session, Fable 5.1): Fable quota IS reachable

The headline below is right about `$.session.usage()` and wrong about the mod API as a
whole. Two routes exist; both **observed**, neither run.

- **The usage endpoint carries a per-model bucket.** The engine's own schema for
  `GET /api/oauth/usage` (found in the 2.1.295 binary, the zod schema next to
  `rate_limits_available`) includes `model_scoped: [{ display_name, utilization,
  resets_at }]`, described as "Per-model weekly windows from the server limits[] array"
  with the example label `'Fable'`. This is what `/usage` draws. The binary also knows
  rate-limit types `seven_day_opus` and `seven_day_sonnet`.
- **A mod can call it with the session's credential without seeing the secret.**
  `$.session.authorize()` returns an opaque handle (T, `authorize:` doc); spend it via
  `$.http.fetch(url, { auth: handle })` (T, `http.fetch` doc). Null for third-party
  providers or gateways. Refused when `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set.
- **`$.command.run({ command: "status" })` is not a route.** `CommandRunResult.text` is
  "undefined when the command showed nothing as text (a panel ...)" (T:1837 to 1842);
  `/status` and `/usage` are panels.

**Human ruling 2026-10-09 (Brian, this session):** "I don't need that query to be
aggressive, once every 5 minutes is fine." Poll the usage endpoint at most every five
minutes (`$.clock`), not per turn.

**Observed live 2026-10-09 (direct GET with the session token, same call `/usage`
makes):** the response has a `limits` array; entries have `kind` (`session`,
`weekly_all`, `weekly_scoped`), `group`, `percent`, `severity`, `resets_at`, `scope`,
`is_active`. The Fable pool is the `weekly_scoped` entry with
`scope.model.display_name == "Fable"` (73% at the time, against 59% weekly-all and 48%
session). The legacy top-level `seven_day_opus` / `seven_day_sonnet` fields were null;
read `limits[]`, not those. Also present: `seven_day_breakdown.rows` by surface and
`weekly_scoped_shares`.

**Not checked:** the exact response shape and query flags (`?at_wall=1`,
`?cedar_ember=1` variants exist), polling etiquette for that endpoint, and whether
`sec-default` restricts `auth` fetches. The implementer should fetch once by hand with
the handle and log the JSON before designing the display.

## 1. Headline: the mod API does not expose Fable usage as its own quota

**Observed.** `SessionRateLimit` is `{ kind: string; percentUsed: number; resetsAt?:
string }` with `kind` documented as "`five_hour`, `seven_day`, or a Claude gateway's
`spend_limit`" (T:11282–11297). `SessionUsage.rateLimits` and
`SessionMeasureInput.rateLimits` are arrays of that type (T:11725, T:11107). No field
names a model or pool. A grep of `T` for `fable|per-model|overage|limitStatus` finds
only a tool parameter enum (T:15996). The package README already records that the
status-line JSON omits the Fable quota (S:README.md:31, written against 2.1.268).

**Inferred.** `kind` is an open `string`, so the engine *could* emit a Fable-pool entry
without a type change. I could not check what the live API returns: transcripts do not
carry `rate_limits`, and the engine is a bundled binary. The implementing session
should log `e.rateLimits.map(r => r.kind)` from one `session.measure` hook for a day
and treat any unknown `kind` as evidence. Until then: **Fable quota percentage is not
derivable from the mod API.**

**Partial fallback (derivable, with accuracy limits).** `turn.step` input carries
`model` and `effort` per request (T:13444, T:13449); its `stop` chunk carries
`usage: TurnUsage | null` = `ModelUsage` (`input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`) plus `model` as the API
reported it (T:13573–13577, T:ModelUsage). Accumulating those per model in `$.store`
gives **Fable tokens consumed this window**, not Fable percent-of-pool. Limits:

- Pool size is unknown, so no percentage and no burn-to-reset.
- Subagents a hook itself spawns via `$.agent.spawn` step past that hook (T:13462–13465); subagents spawned by the engine (Agent tool, teams) are seen. A Fable subagent dispatched from another session is counted only by that session's copy of the mod, so cross-session totals need `$.store` (see §3).
- Reset time must be inferred from the `five_hour`/`seven_day` `resetsAt` and assumed to coincide with Fable's pool; unverified.

## 2. What moves into the mod, what stays in the shell status line

| Side effect (S:src/workflow_statusline/__main__.py) | Where |
|---|---|
| Append rate sample to locked cross-session file (`:182`, `:202`) | **Mod**, `session.measure` hook. Event fires "after each main-thread turn, and when a rate-limit window moves a whole point" (T:4405–4407). Also keep `$.clock.every` (T:3462) only if §6's idle gap matters. |
| Write quota snapshot for Byobu (`:189`, `:208`) | **Mod**, same hook, via `$.fs.write` (§4). |
| tmux rename (`:235`, `tmux.py`) | Decision for Brian (§5). Either side can do it; mod via `$.process.run` (T:3515). |
| Two-line coloured render with context bar, `$`, duration, forecast cells | **Stays in shell.** `$.ui.status` pins one plain-text line per plugin, first 2000 chars (T:2469–2476). No colour. `AbovePrompt` can draw a styled tree (T:10255–10300) but it is a band above the prompt, not the status line, and it is collapsible by the person. |

**Inferred.** The clean split is: mod owns data collection and side effects, shell
status line becomes a pure reader of the snapshot/sample files (no writes, no tmux).
That removes the 30-second polling writer entirely.

## 3. Burn rate relative to reset

**Observed.** `$.session.usage()` returns `rateLimits` with `percentUsed` (one
decimal) and `resetsAt` (ISO) (T:11282–11297, T:2836). It is a point reading. Burn
rate needs a history of readings across sessions, which is what the sample file holds
today (`cache.append_rate_sample`, S:cache.py:132–200, flock + atomic rename).

**`$.store` is not safe for concurrent sessions.** It is "a JSON file of the plugin's
own under the user's Claude Code configuration directory" with `get`/`set` and no
compare-and-swap or lock (T:3351–3375). Two sessions doing read-modify-write on a
sample array will lose samples. `$.state` has `ifVersion` (T:3410) but is per-session.

**Recommendation (inferred).** Keep the existing locked sample file as the shared
history. The mod cannot `flock`, but it can keep the existing semantics by appending
through `$.process.run` into a tiny Python entry point of the package (`uv run
--project S append-sample ...`), or by writing one file per session
(`rate-seven_day.<sessionId>`) with `$.fs.write` and letting the reader merge. The
second needs no lock and no subprocess; the reader (`read_rate_samples`) already
tolerates extra fields and would need a glob. Do not use `$.store` for the history.

## 4. `$.fs.write` outside the plugin folder

**Observed.** `$.fs.write(path, text)`: "`path` relative to the working directory, or
absolute" (T:3244–3250). `$.fs.read` is bounded at 4 MiB, no path restriction stated
(T:3224–3240). So `~/.cache/claude-statusline/quota-seven_day` is writable. The write
is not documented as atomic; the Byobu reader (S:src/workflow_statusline/claude_quota.py:56–66)
returns an empty cell on a malformed line, so a torn read costs one 30-second tick.
Write to a temp name then rename if atomicity matters; `$.fs` has no rename, so that
path also needs `$.process.run(["mv", ...])`.

## 5. tmux rename: two writers (decision for Brian)

**Observed.** `tmux.py:29` checks `/tmp/claude-statusline-tmux-lock-<pane_id>`.
The original design (`docs/design-plans/2026-03-21-statusline-v2.md:157,174`) said the
session-naming skill's subagent writes that lock, keyed by `{session_id}`. Neither
holds now: the code keys by pane id, and the current `exec-session-naming` skill
(`denubis-plan-and-execute/4.2.2/skills/exec-session-naming/SKILL.md`) renames
directly and says "Do not create a cache". `rg claude-statusline-tmux-lock` over the
repository finds no writer, only `tmux.py`, its test, the design plan and
`plugins/denubis-plan-and-execute/docs/workflow-status-line.md:33`. So the skill's name
is overwritten by the status line within 30 s once git location changes. **Flagged
contradiction:** the design plan's AC5.3 is not implemented and the key differs.

Options:

- **A. Status line (or mod) owns it; skill writes the lock before renaming.** Keeps `Cl:<location>` default. Change the skill to touch the lock file (contradicts its "no cache" line; needs a skill edit).
- **B. Skill owns it; drop `maybe_rename` from both.** Windows show `Cl:` nothing until a session invokes the skill. Simplest code; loses the free default.
- **C. Mod owns it, renames once at `session.start` and on `classic.CwdChanged` (T:3625), never again.** The skill then wins any later rename without a lock. Loses "rename when location changes mid-session" only if cwd does not change.

I do not decide this. C is the least coupling but changes current behaviour.

## 6. What does not fire while idle

**Observed.** `session.measure` fires after a main-thread turn or when a window moves
a whole point (T:4405–4407); the mover is "the last API response" (T:11722). No
response, no event. `$.clock.every` timers keep running until cancelled or the module
reloads (reference.md:160–162), but `$.session.usage()` only reports the last
response's reading, so a timer cannot fetch a fresher percentage.

**Consequence (inferred).** An idle session's display is as stale as its last turn.
Today's shell status line is the same: it is handed the engine's cached figures.
Cross-session freshness comes from *any* active session writing the snapshot, which
is why the shared file matters more than the timer. A timer is still useful for
recomputing pace against wall-clock (the "pace %" cell drifts without new samples).

## Not checked

- Whether the live `rateLimits` ever carries a Fable `kind` (needs the one-day log in §1).
- Whether `$.fs.write` is atomic.
- `claude plugin validate` and `tsc` were not run (no mod written).
- ADRs 0001–0010 were listed; none governs the status line. ADR 0006 governs Fable
  dispatch, not display, and is not reopened here.
