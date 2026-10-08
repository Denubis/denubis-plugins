# ADR 0009 — The Codex monitor announces once, and an idle pane gets no monitor

**Status:** Accepted (2026-10-08). Supersedes the operator rulings of 2026-07-28
(repeat on a backoff) and 2026-08-04 (stop at the hour) that the monitor's reminder
ladder implemented. Released as `denubis-external-agents` 0.22.0.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/0d6c5c17-8b49-4d6b-a132-63beecccf129.jsonl`:

- Line 9, record `bb3f0f03-2afe-4b26-a249-688f27a0d4ca`: "we need to fix the 'rearm
  monitor'", with a pasted transcript of a supervising session re-arming its monitor
  every thirty minutes and restating two open questions each time while the Codex pane
  sat idle on his ruling: "If it's waiting on my input, and it's a screen full of passive
  agressive bullshit, I come back to see... a screen of passive agresive bullshit."
- Line 98, record `14b58d35-082c-49d3-8d3c-495e8211cbb2`, answering "stop the monitor
  while parked on the human, or keep it armed with silent one-line re-arms?":
  "we don't need repeated reminders for supervising codex, 1 is fine, and 2) we don't
  need 'rearm' if waiting for user input. basically the repeats are always caused by an
  approve prompt on my end, as far as I can tell. And yeah, I don't care about a crash
  while away. But if the pane is idle, there shouldn't be a monitor! So yes, it should
  stop and wait for me to respond if it's genuinely a block that doesn't go into open
  questions."
- Line 138, a `queue-operation` record sent mid-turn, pasting a second session that
  wrote "Monitor re-armed", "Still working on 06a; monitor re-armed", and "Monitor
  re-armed for the finish" while Codex worked, and received the monitor's own
  "still waiting 2m / 7m / 17m" repeats on a DONE line.

Exact raw-record resolver:

```sh
sed -n '9p;98p;138p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/0d6c5c17-8b49-4d6b-a132-63beecccf129.jsonl
```

## Context

Claude Code's Monitor tool requires a `timeout_ms` capped at thirty minutes. The skill
told the supervisor to re-arm on every expiry and to say so in the reply. The monitor
script separately raised any pending prompt again on a backoff (two minutes, five, then
ten, giving up after an hour). The two together produced, for a pane idle on a human
ruling, a wake-up every thirty minutes in which the supervisor had nothing to say and
said it anyway: the re-arm, the restated questions, and a harness recap. Brian's
observation is that every repeat he has ever received was queued behind a permission
prompt on his own side, where repeating cannot help.

## Decision

- Each actionable thing (approval, question, completion, crash) is announced once. The
  reminder ladder, its "still waiting" count, and its "no further reminders" line are
  removed from `codex_supervisor.py`. A prompt that returns after a busy flicker is not
  announced again; a new prompt is.
- While Codex works and the host's Monitor tool expires, the supervisor re-arms and says
  nothing about it.
- When the pane is idle on something only the human can supply, the supervisor asks
  once, at the end of the turn, stops the monitor or lets it lapse, and writes nothing
  further until the answer arrives: no restated question, no count of the wait, no
  re-arm notice. On the answer it runs `--tail`, delivers, and arms the monitor again.
  A crash during the unwatched wait is found by that `--tail`; Brian accepted this.
- A supervisor must not block itself on a permission prompt; the prompt is what to raise
  with the human.

## Consequences

- `tests/test_codex_supervisor_reminders.py` (the ladder's tests) is removed;
  `tests/test_codex_supervisor_announce_once.py` drives the monitor's poll step across
  an hour of identical screens and expects one line.
- The 57-minute blocked pane of 2026-07-27, which the ladder was built for, is again
  possible if a supervisor misses a line. The ruling accepts that: the supervisor that
  missed it was blocked behind a permission prompt, and a repeat would not have reached
  it either.
- The harness-level "recap" lines in the pasted transcripts are not produced by this
  plugin and are untouched by this decision; with no idle wake-ups they stop appearing
  during a wait.
