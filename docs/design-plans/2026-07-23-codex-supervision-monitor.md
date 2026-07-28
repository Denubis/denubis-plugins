# Codex Supervision Monitor Design

**Status:** implemented, shipping in `denubis-external-agents` 0.9.0
**Origin:** drafted 2026-07-23 in the project the monitor grew in; adopted here 2026-07-28

## Provenance

The monitor was built inside a working repository, where the script was project-local
and the design record sat beside it. It now lives in this plugin, so the record does
too. The upstream copy is superseded and slated for deletion with the rest of that
lineage.

Three things in this document differ from the upstream text, and each is a correction
rather than a restatement:

- The relay is a **Unix datagram socket**, not a FIFO. The upstream record said FIFO in
  three places. The distinction matters to anyone debugging a stall, because a FIFO
  blocks when the pipe fills and nobody reads, and a datagram socket does not. Someone
  reading the old text would hunt for a blocked writer that could not exist.
- Hooks are **global**, not project-local. See AC3.
- Three architectural rationales are recorded that survived only in a branch that has
  since been deleted: the advisory lock, the scoped occurrence key, and the pane/hook
  double-emit guard.

## Summary

The monitor combines Codex lifecycle hooks with conservative tmux inspection. Hooks give
low-latency signals for approvals, tool progress and turn completion; tmux inspection
covers hook gaps, verifies that events belong to the joined Codex pane, and detects
terminal failure.

It follows Claude's exact tmux window identity rather than session names, numeric window
indexes, worktree paths, or hard-coded pane IDs. Only approval, question, completion and
crash are actionable. Every other recognised or unknown state is busy and silent.

## Acceptance criteria

### AC1: Select only the joined Codex pane

- **AC1.1** With exactly one Codex pane in Claude's current tmux window, observe it.
- **AC1.2** With none, startup fails with a clear nonzero error.
- **AC1.3** With several, startup fails rather than choosing one.
- **AC1.4** Re-resolve after topology changes without following a Codex pane into an
  unrelated window.

### AC2: Emit only actionable state changes

- **AC2.1** Each distinct approval emits once, keyed by the pending tool command or
  input rather than by a sampled busy-to-idle transition.
- **AC2.2** An explicit question emits once.
- **AC2.3** Genuine turn completion emits once.
- **AC2.4** `Working`, spinner titles, `Waiting`, background terminals, compaction,
  running tools, streaming output and progress states emit nothing.
- **AC2.5** Unknown states default to busy and emit nothing.
- **AC2.6** Flicker among busy labels neither emits nor rearms an unchanged actionable
  event.
- **AC2.7** *(added 2026-07-28)* A pending action is **raised again** on a lengthening
  interval: two minutes, five, then every ten, with the repeat stating how long the pane
  has waited. A crash is exempt, being terminal. The reminder lapses while Codex is busy.

**AC2.7 does not contradict AC2.1, AC2.3 or AC2.6, and the distinction is load-bearing.**
Those criteria forbid emitting twice for *the same observation*; AC2.7 re-raises on
*elapsed time*. Flicker carries no elapsed time, so AC2.6 holds unchanged and its test
passes untouched. What "emits once" was protecting against was a stationary screen
re-announcing every poll, which would train the reader to ignore the monitor. It was
never a decision that a human who missed the one notice deserved silence, and reading it
that way cost roughly three hours on 2026-07-27.

### AC3: Use hooks without making them a dependency

- **AC3.1** Hooks wake the monitor for permission requests, activity and turn stops
  without storing or emitting prompts, commands, transcripts or tool results.
- **AC3.2** A hook invocation with no active monitor exits successfully and silently.
- **AC3.3** Untrusted, unavailable or not-yet-loaded hooks do not disable conservative
  pane-based monitoring.
- **AC3.4** *(amended 2026-07-28)* Hooks are installed **globally**, in
  `~/.codex/hooks.json`, not per project.

**Why AC3.4 changed.** The relay was project-local upstream because the script it called
lived in the project, and `.codex/hooks.json` could resolve it through
`git rev-parse --show-toplevel`. With the script at a stable path in an installed plugin,
that reason is gone, and per-project wiring has a real cost: it only wakes the monitor in
directories somebody set up in advance, so a Codex started in a fresh directory is
unsupervised exactly when nobody was thinking about supervision.

Global wiring is safe because of AC3.2. The relay addresses a per-pane socket derived
from its inherited `$TMUX_PANE`, so it only ever reaches the monitor watching that exact
pane, and with nothing listening it prints nothing and exits 0. The cost is one
short-lived process per hook event, bounded by a five-second timeout.

### AC4: Surface terminal failure

- **AC4.1** A dead or replaced Codex process, a vanished joined pane, or a recognised
  fatal TUI state emits one crash event and terminates nonzero.
- **AC4.2** A single transient discovery miss during pane movement does not emit a crash.

### AC5: Prove the supervision sequence

- **AC5.1** A healthy sequence with a long busy lane, one approval, one explicit
  question and one completion emits exactly three events.
- **AC5.2** Crash handling is exercised separately and emits exactly one crash event.

## Glossary

- **Actionable state** — approval, explicit question, genuine completion, or crash; the
  only states that produce output.
- **Busy family** — all routine progress states, including `Working`, `Waiting`, spinner
  titles, background terminals, compaction, and unknown transients.
- **Hook relay** — the silent handler that forwards a sanitised event to an active
  monitor.
- **Joined pane** — the unique Codex pane sharing Claude's exact tmux window.
- **Pane identity** — tmux's stable `%pane` identifier, distinct from its mutable index.
- **Window identity** — tmux's stable `@window` identifier, distinct from grouped-session
  aliases and mutable indexes.

## Architecture

A functional classification core with a thin imperative shell around tmux, hook ingress,
waiting and output. `scripts/codex_supervisor.py` owns pane-candidate parsing, snapshot
classification, hook-payload normalisation, action deduplication, the state transition
policy, and the operator verbs. No third-party package is required.

At startup the monitor requires `$TMUX_PANE`, resolves that pane's current `@window`, and
lists panes only in that window. Exactly one foreground `codex` command must be present.
It repeats the resolution after topology changes, never searches every session, and never
selects by worktree slug. An initial zero-or-many result is an error; a bounded number of
mid-run misses lets a redock settle before reporting terminal failure.

### The relay

`~/.codex/hooks.json` registers `SessionStart`, `UserPromptSubmit`, `PermissionRequest`,
`PostToolUse` and `Stop`. The relay uses the hook process's inherited `$TMUX_PANE` to
address a **per-pane Unix datagram socket** in the user's volatile runtime directory. A
non-blocking sender degrades silently when no receiver exists.

**An advisory per-pane lock prevents one monitor replacing another's socket.** Binding
unlinks the path first, so without the lock a second monitor would silently steal the
relay and leave the first reading a socket nothing writes to.

### Correlation

Permission correlation keys digest normalised command or tool input, preserving
command-keyed deduplication without disclosing the command.

**Hook occurrence keys additionally digest session, turn and tool-call identity**, so the
identical action in a later turn still emits. Keying on the command alone would announce
`pytest` once and never again, however many turns later Codex asked to run it. Those
fields are identities rather than content, so this costs no disclosure.

**Pane fallback applies compatible correlation keys, preventing hook and pane views of
one action from double-emitting.** An action reaches the monitor twice, once as a hook
and once as rendered pane text, and their keys are compatible precisely so a scoped hook
event matching a correlation key an unscoped snapshot already reported can update state
and stay silent.

Stop hooks inspect the last assistant message only to classify question versus
completion, then discard it.

### Classification

The monitor waits on the relay socket with a timeout. A hook wakes it immediately; the
timeout triggers topology and pane inspection. Hook absence reduces responsiveness, not
correctness.

Classification checks the busy title first, then a **pending** approval, then a `Ready`
title, then fatal signals, then defaults to busy. Only a `Ready` state reached after
observed activity can become a question or completion.

**The approval check must precede the title check, and for a long time it did not.**
Codex's steady-state title is `Ready`, so an approval drawn under it classified as `DONE`
and the supervisor was told Codex had finished at the moment it was blocked. That was a
divergence from this document, which specified approval-first from the start. The repair
cannot simply read the body first, because answered approval text stays in the scrollback
and a finished pane would then read as waiting; pending is distinguished by whether an
assistant bullet appears after the last approval marker.

## Limitations

**Hook trust.** Codex requires review of new or changed hooks through `/hooks`, and
existing sessions need a restart before they load. Pane fallback covers the gap.

**Observability.** The monitor distinguishes a process or pane crash from ordinary
progress. It cannot prove that a still-running background command is hung rather than
legitimately slow without a command-specific deadline or heartbeat.

**Event detail.** Emitted events carry pane id, kind, and now elapsed wait. They carry no
command or digest, so an event log cannot say *which* approval it announced. This made
the 2026-07-27 postmortem harder than it needed to be and is not yet addressed.

**Privacy.** Hook normalisation retains event kind, pane identity, turn identity and
opaque digests only. Raw prompts, commands, tool inputs and results, assistant messages
and transcripts never enter transport or output. `serialize_observation` whitelists four
fields, so a field added to `Observation` cannot leak by default, and a generative
property test over arbitrary text pins the guarantee.
