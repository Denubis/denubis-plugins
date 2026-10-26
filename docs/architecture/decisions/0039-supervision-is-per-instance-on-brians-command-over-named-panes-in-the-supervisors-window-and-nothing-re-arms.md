# ADR 0039 — Supervision is per instance, on Brian's command, over named panes in the supervisor's own window; nothing persists a binding and no monitor re-arms

**Status:** Accepted (2026-10-24). Withdraws design decision D3 ("Operational persistence
and the Record boundary") of the stage-1 Codex-supervises-Claude design, Sol's draft
against `docs/design-plans/2026-10-24-claude-supervision-spec.md`. Applies ADR 0014's own-window rule
and ADR 0009's "idle pane gets no monitor". Sets the direction that ADR 0018's
ping-and-pull is realised by one local service; ADR 0040 rules where that service lives.

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 1172, `user` record `51006e7d-26b8-4c24-bfb5-1de63008d809` (2026-10-23T22:51:22Z,
  2026-10-24 09:51 Australia/Sydney), answering "Do you want to strike the
  supervisor-restart reconciliation requirement from the first release?": "yeah, that's
  entirely wrong. Supervision is a instance by instance thing, commanded only by me. A
  supervisor should know what window-pane things it is allowed to monitor. Monitors
  should be able to do it. (Also fuck that 30 minute rearm bullshit. that just creates
  log spam.) Do we need to have the session comms package done before we progress on
  this?"
- Line 1211, `user` record `d59e4667-1e63-4801-a570-b7f897a3f451` (2026-10-23T22:56:07Z),
  answering "Does the allowlist drop the own-window restriction?" (the first words were
  cut by an interrupt): "s figure out a better way of handling this that doesn't involve
  a wall of "I'm waiting, rearming" overnight. WAste of tokens. Frustrating. Everything
  that leads to passive agressive bullshit on your part should be examined. And yes, it
  should only drive panes in its tmux window. Note pane*s*."
- Line 1323, `user` record `83727183-8de8-4b6a-891f-a4e107acfa5a` (2026-10-23T23:14:02Z),
  answering "Is a per-supervisor watcher plus a blocking wait call the service shape you
  had in mind?": "ok, do we just build a connectivity daemon backed by postgres that can
  also serve for comms? My very strong preference is to bake most of these things into
  stop hooks and pull rather than push, so that if a session is idle and supervising it
  gets a ping, but if it's working it just goes until it pauses (obviously we can go up
  the priority ladder) does this just pull in some of the local comms plans that we had?"
- Line 1351, `user` record `20eff1ac-54a7-4d01-9d5a-9f656344de42` (2026-10-23T23:17:42Z),
  rejecting a per-session listener: "... which is a new daemon? Do better. If we don't
  have things shelling out (and that *must* not ever be multiple calls) would it not be
  better to just have something that can do pings and mailboxes directly?"

Exact raw-record resolver:

```sh
sed -n '1172p;1211p;1323p;1351p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

## Context

Astra's specification asked for persisted supervision state and reconciliation after
either process restarts. Sol's design combined that with ADR 0014's "supervision edges in
the Record" into D3: whether the first release must store pane bindings in the Record,
which does not exist on this machine, or in a scoped journal. Brian rejected the premise:
a binding is live state between two processes and means nothing once the worker has
exited.

Separately, the shipped watch loop (`codex_supervisor.py`, `run_monitor`) never ends on
its own. Under Claude Code's Monitor tool, capped at thirty minutes, that guarantees an
expiry notice every half hour and a re-arm, which overnight produces a wall of waiting
messages. Brian: a waste of tokens, and the source of the "passive aggressive" filler
the supervisor emits when woken with nothing to say.

## Decision

1. Supervision is per supervisor instance and exists only because Brian commanded it:
   either by having the supervisor spawn a worker, or by naming an existing pane to it.
   The supervisor holds the set of panes it may drive and monitor. That set lives with
   the instance and dies with it. Nothing persists a binding across a restart, and there
   is no restart reconciliation of bindings. D3 is withdrawn, not answered.
2. A supervisor drives only panes in its own tmux window (ADR 0014 stands), and may hold
   several of them.
3. No monitor re-arms. A supervisor that is working is not interrupted; one that has
   paused pulls what has arrived for it; one that is idle gets a ping. The preferred
   mechanism is Stop-hook pull, with the escalation ladder (ADRs 0015–0017, 0021) deciding
   when a ping becomes a nudge. This is ADR 0018's ping-and-pull, now binding on the pane
   drivers too.
4. The mechanism is one local service, backed by Postgres, that serves both supervision
   events and mail, not a watcher per session. Hooks make exactly one call to it and
   exit; they never shell out repeatedly and never touch Postgres themselves. Where that
   service lives is ADR 0040's ruling.

## Consequences

- Sol's design loses its `monitor` verb and its persistence section; `bind` joins the
  minimum tranche; `spawn` and `bind` register panes with the supervisor's instance.
- The `supervising-codex` skill's Monitor-tool instructions (thirty-minute cap, re-arm on
  expiry) are retired. A supervisor says nothing when woken without an event.
- The Record (ADR 0026) is a prerequisite of the pull path, so the Claude driver depends
  on the comms work.
- The supervisor's pane closing retires its registered panes, and a pane exiting (Ctrl-D)
  retires itself; both require live detection, demonstrated rather than assumed.
