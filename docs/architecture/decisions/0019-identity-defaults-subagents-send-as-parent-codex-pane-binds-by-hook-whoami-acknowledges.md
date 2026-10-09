# ADR 0019 — Identity defaults: sub-agents send as their parent, a Codex pane keeps its address across clear by a hook binding, and a model-run whoami acknowledges identity

**Status:** Accepted (2026-10-09). Qualifies property 12 of the 2026-08-09 design.

## Authority evidence

Original human message in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`:

- Line 973, record `9f39c3fc-ec49-443b-85a2-a9eaaaeab9eb` (2026-10-09T03:33:04Z),
  answering ticket M8 ("(a) sub-agents send as their parent, only a Claude teammate gets
  its own address; (b) a hand-launched Codex gets a new address after a hand-typed
  /clear; (c) a model-run whoami is sufficient identity acknowledgement. Accept all
  three defaults, or change one?"):
  "yes, though it'd be nice if b had a hook or something, because clearing subagents is
  going to be very tedious. And uh... how the hell does it have no context of place?
  fancywhoami is fine"

Exact raw-record resolver:

```sh
sed -n '973p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl
```

## Context

Proposal 02 (Identity) found no vendor identifier that survives clear, compact, and
resume together, so each session gets an address of our own with vendor ids bound as
evidence. Its probe read Codex session locks from `/proc` and found that a hand-launched
Codex pane holds none, because current Codex hands session writing to a shared
app-server daemon. From that it proposed a new address after a hand-typed `/clear`.
Brian rejected the tedium and asked why the pane has "no context of place".

## Decision

- **(a)** In-process Claude sub-agents and Codex's own sub-agents have no address; they
  send as their parent with a `via` stamp naming the sub-agent. A Claude teammate, which
  is a full session, gets its own address with a parent link.
- **(b)** A Codex pane should keep its address across `/clear` by a hook binding rather
  than by lock inspection, so that clearing is not tedious. That is the ruling. The
  mechanism is not yet established, and the dispatcher's first wording of this clause
  overstated it; verification 02 (2026-10-09, docs only) corrected it:
  - Codex's hooks documentation says hook commands run with the session's working
    directory and says nothing about their environment, so "the hook sees `TMUX_PANE`"
    is unverified. Proposal 02's probe found hand-launched panes hosted by a shared
    app-server daemon with no tty, and third-party reports on 0.160 say that daemon runs
    every session's hooks with the first session's environment. A hand-typed `/clear`
    may therefore bind to no pane or the wrong one.
  - "Fires before the next model request" is documented only for `source: compact`; for
    `clear` the documentation says nothing, and ADR 0007's observation (no event at the
    instant of a clear on 0.157.0) stands alone.
  - Codex now lists the session id as a `/statusline` item, not in `/status`, so the
    ADR 0007 fallback needs re-checking on the installed version.
  Until live tests settle it (a hand-launched Codex on the installed version logging
  `source`, `session_id`, `PPID`, `TMUX_PANE`, and `CODEX_THREAD_ID` from a SessionStart
  hook and a shell tool call before and after `/clear`; whether any launch flag keeps a
  pane out of the daemon), a pane whose binding is missing is reported as unresolved
  rather than given a fresh address silently, and the lock route plus the `/status` or
  `/statusline` fallback remain the evidence of last resort.
- **(c)** A model-run `whoami` tool call, returning the session's address and alias, is
  sufficient acknowledgement of identity. Property 12's exact identity-card
  acknowledgement is replaced by it.

## Consequences

- Function 2 implements the Codex binding as a hook and must test it on the installed
  Codex version, including the gap between `/clear` and the next prompt, during which
  the pane's old session id is still the bound one.
- The same hook route is intended for Claude, whose SessionStart carries a source of
  `clear`, `compact`, or `resume`. Verification 02 notes the documented caveat that
  `CLAUDE_CODE_SESSION_ID` in a hook's environment may hold the initial startup id on
  `--continue` or `--resume`, so enrolment reads the session id from the hook payload,
  not the environment; whether the hook sees `TMUX_PANE` on a `source: clear` start is
  a live test. `claude --name` is documented as a resume handle that survives `/clear`,
  which gives Claude a documented alias source.
- The proposer's observation that a hand-launched Codex holds no lock stands as a fact
  about the probe, not about the pane; it is recorded in proposal 02 and should not be
  read as "Codex cannot be identified".
