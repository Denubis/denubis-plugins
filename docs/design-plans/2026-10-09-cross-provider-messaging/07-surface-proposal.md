> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Function 7, Human surface: proposal (propose-7-surface, Fable medium, 2026-10-09)

Labels: O = observed by me today, I = inferred, A = assumed. Third-party reports (01-04,
Argon) are cited only where I re-checked the fact.

## 1. The challenge

Brian wants one view on a side monitor: messages pinging between sessions, and a list of
things only he can unblock (approvals, tickets, questions), where an item leaves only when
he answers it. The assumption it protects is property 2 (2026-08-09): a human obligation
cannot fall out of context, and nothing but an answer settles it. The surface must achieve
this without becoming the second monitor ADR 0009 forbids (it never nudges, repeats, or
re-arms anything), and without being a picker (Brian: "alt-s picker is worthless").

## 2. Proposed mechanism

**Surface.** A standalone Textual TUI, `agent-surface`, a uv project (Python 3.14,
`textual>=8.2.8` as the prior attention manager pinned (O: its `pyproject.toml:8`),
`psycopg[binary]`). It runs in its own tmux session, `tmux new -A -s surface
agent-surface`, in a Ghostty window on the side monitor; the same command over Tailscale
SSH reattaches. It is not a window of the main byobu session, so it never competes for the
312x62 client Brian works in (O: `tmux display`). Not a Claude mod: a mod pane draws inside
one Claude session's terminal (O: `plugin-authoring/examples/pane.tsx`, `$.ui.open`) and
sees nothing of Codex or agy, so it cannot be the one view. A mod is an optional complement
(§6).

**Reads.** Only the Record (function 1), through two views it must publish:

```
record.needs_human(kind, ref, requester, requester_label, repo_root, summary, body_ref,
                   created_at, state, locator_note)
   kind ∈ approval | ticket | question ; state ∈ pending | expired | orphaned
record.traffic(message_id, sender, recipients[], subject, created_at,
               delivered_at[], acked_at[], thread_id)
```

Startup: `SELECT` both views, paint. Then `LISTEN record_changed` on a dedicated
connection, re-`SELECT` on each notification, and a 5 s poll regardless, because NOTIFY
is a hint, not storage (sql-notify doc, cited in 03; not re-opened). The TUI keeps no
state beyond cursor and filters; every row is a projection of the Record. A ticket's `body_ref` is the path to
`<repo>/.notes/project_open-questions.md` plus the ticket heading; the surface reads that
file read-only at render, so ADR 0008 stays the owner of ticket text and the Record holds
only "unanswered" (brief, function 1).

**Actions.** Four, all writes to the Record addressed to an owner; none touch a pane.

| Key | Item | What is written | Who acts on it |
|---|---|---|---|
| `a` / `d` | approval | `authority.human_decision(request_id, behavior allow\|deny, principal 'brian', decided_at)`; unique on `request_id` | Function 6. Its `PermissionRequest` hook minted `request_id`, inserted the item, and is blocking on the decision row; on read it returns `hookSpecificOutput.decision.behavior` (O: code.claude.com hooks, PermissionRequest decision control; default `timeout` 600 s). Codex's `PermissionRequest` hook supports the same decision shape (O: learn.chatgpt.com hooks.md:129, 420, 519). |
| `Enter` | ticket | a Record message from `brian` to the filing session's stable address (function 2), `kind='human_ruling'`, `ticket_ref` set, body verbatim | Function 3 delivers; the recipient agent records the ADR and removes the ticket (ADR 0008). The item leaves the needs-Brian list the instant the row exists; the answer then shows in traffic until acked (function 4). |
| `Enter` | question | same as ticket without `ticket_ref`, replying in the thread | same |
| `x` | approval, `expired`/`orphaned` only | `actuation.request(kind='approve-by-reference', request_id)` | Function 3's guarded actuator, if the Record still shows the dialog pending on a live pane. The surface requests by reference; it never types. |

`v` views the full body (command text in full for approvals, the ticket heading and body
for tickets) in a modal; `Esc` closes. There is no dismiss, snooze, or acknowledge key:
an item leaves when its owner changes its state. There is no pane list, no "switch", and
no `tmux` invocation anywhere in the program; the only subprocess is `psql`-free psycopg.

**Screen** (Ghostty, ~120x50):

```
┌ needs Brian (3) ───────────────────────────────── Record ok · 14:02:11 ┐
│ ▶ APPROVAL  2m   Cl:brian-ed3d-plugins(a3f1)  Bash: remove example worktree│
│   TICKET    41m  codex:melica(9c02)  Q7 "Which register for Hunan rulings?"│
│   QUESTION  3h   Cl:approver(77de)   "Ship 0.23 with the bun rule off?"    │
│   (expired · 11h)  APPROVAL  codex:caller-spec(1b0e)  apply_patch  [x]    │
├ traffic ─────────────────────────────────────────────── filter: all ────┤
│ 14:01:58  Cl:plugins(a3f1) → codex:melica(9c02)   re: Q7       ✓ acked  │
│ 14:01:12  brian → Cl:approver(77de)   re: 0.23          delivered, no ack│
│ 13:58:40  codex:melica(9c02) → brian  Q7 opened                  ·      │
│ 13:55:02  Cl:plugins(a3f1) → codex:caller-spec(1b0e) spawn ack  ✓ acked │
└ a approve  d deny  Enter answer  v view  x re-raise  f filter  q quit ───┘
```

Top pane sorted oldest-first; expired and orphaned rows sink and grey. Traffic shows the
last 200 rows, newest at bottom, with per-recipient ack state.

**Restart correctness.** Because every row is a Record projection and every action is an
idempotent insert keyed by `request_id` or `message_id`, killing and restarting the TUI
loses nothing; the first paint is the committed state (the pattern the prior attention
manager used, O: its README "first paint comes from committed SQLite state"). A second
instance over SSH is harmless: the unique key makes a double approve a no-op.

**Why it is not a second monitor.** Its only write path to a session is a message Brian
composes. It never polls panes, re-sends, or counts a wait aloud; age is a column, not a
repeat. A pane idle on Brian gets what ADR 0009 ordered: nothing, until he answers here.

## 3. Verification (falsifying tests)

1. *Restart loses nothing.* Seed three pending rows, kill `agent-surface` with SIGKILL,
   restart: all three present with the same refs. Fails if any is missing.
2. *NOTIFY is not load-bearing.* Revoke the LISTEN connection (`pg_terminate_backend`),
   insert a row: the row appears within 5 s via poll. Fails if it needs a restart.
3. *Approval round trip.* A test Claude session with function 6's hook runs `Bash(echo
   probe)` under `default` mode; the item appears; `a` in the surface; the command runs
   and the item leaves. Repeat with `d`: Claude receives the deny `message`. Fails if the
   dialog has to be touched in the pane.
4. *No pane writes.* Run the whole action suite with `PATH` lacking `tmux` and an audit
   (`strace -f -e execve`) on the TUI: zero `execve` of anything but the interpreter.
5. *Items leave only on answer.* Hold a ticket item 60 min with no keystroke: still
   present; remove the ticket heading from the `.notes` file: item leaves within one
   function 1 reconcile cycle. Fails if age alone removes it or an answer does not.
6. *Expired handling.* Let a hook time out (set function 6's `timeout` to 20 s): the item
   turns `expired`, `a` is refused with a reason, `x` writes an actuation request.

## 4. Interfaces

Needs: from **1 (Record)** the two views above, `LISTEN record_changed`, and a reconcile
that marks ticket items answered when the heading leaves the file; from **2 (Identity)**
a stable address and a short display label per session and the principal address
`brian`; from **3 (Deliver)** acceptance of `brian`-sent messages and an
`actuation.request` table consumed by the guarded actuator; from **4 (Acknowledge)**
per-recipient `acked_at` on traffic; from **5 (Supervise)** that a supervisor parked on
Brian (ADR 0009) files its question as a Record message to `brian`, not only in its own
transcript; from **6 (Authority)** `request_id` minted at `PermissionRequest`, the hook
blocking on `human_decision`, and a `state` transition to `expired` when the hook times
out and to `resolved` when the pane dialog is answered locally.

Gives: a single decision write path with human provenance (property 8: the decision row
cites the exact `request_id` or `ticket_ref`), and nothing else; no session depends on the
surface running.

## 5. Failure modes

- *Postgres unreachable*: header turns `Record unreachable since 14:02`, rows grey, keys
  refused with that reason; reconnect with backoff; no local queue of decisions (a queued
  approve applied later is the fail-open the approver exists to prevent).
- *Hook timeout before Brian answers* (600 s default): the dialog is now on screen in the
  pane and the item is `expired`; `x` re-raises by reference, or Brian answers in the
  pane and function 6 marks it `resolved`. Not hidden; not repeated.
- *Session gone with a pending item*: liveness (3/5) marks `orphaned`; the row greys and
  the locator is labelled historical; `a` is refused.
- *Two surfaces*: unique key on the decision; the loser sees "already decided".
- *Ticket edited by hand*: function 1's file reconcile owns the state; the surface shows
  whatever it says and a `body_ref` that no longer resolves as "heading not found".
- *Codex approval not hookable* (approver CLAUDE.md: `PermissionRequest` only when Codex
  independently needs approval; O): the dialog is still visible to the actuator, so the
  item can arrive from function 5's screen observation with `state=expired` semantics
  (no hook to satisfy) and `x` is the only action. Flagged for 6 and 5 to confirm.

## 6. Alternatives rejected

- *Claude mod as the surface*: per-session, Claude-only, drawn inside that session's
  terminal (O: pane.tsx). Kept as an optional complement: a band above the prompt that
  says "2 items wait on you for this session", reading the same view, no actions.
- *Resurrect `tmux-agent-attention`*: SQLite, wrapper-only enrolment, Codex pinned to
  0.144.x (O: `adapters/codex.py` per the peer review's C1; I did not re-open it; A), and a
  session-state model ADR 0009 rejects. Its TUI idioms (first paint from committed state,
  keyed rows, text-not-colour) are borrowed.
- *Desktop GTK/Qt app*: no SSH path, a second toolchain, no gain over a TUI.
- *fzf popup / tmux status `#()`*: ruled worthless; `#()` jobs crashed tmux before (O:
  `~/.byobu/tmux.conf:66-67`). *OSC 7501*: tmux swallows it (Argon §1.1; not re-verified).
- *Surface types the approval keystroke itself*: contradicts "approve by reference".

## 7. Could not check

- Whether Claude shows the permission dialog while a `PermissionRequest` hook is still
  running, or only after it returns; the doc says hooks and the host decide "whichever
  first" only for `canUseTool` sessions. Test 3 settles it.
- Whether a Codex `PermissionRequest` hook may block for minutes without side effects
  (doc gives `timeout` 600 default; no statement on the dialog).
- Textual is not installed system-wide (O: import fails); the prior project's pin is the
  only local evidence that 8.x runs here.
- `agy` has no `PermissionRequest` hook event (02); agy approvals would be screen-only.
- Argon's report: prior art only; environment claims re-verified only for `tmux.conf`,
  `settings.json`, `hooks.json`.

## 8. Questions for Brian

- Should pressing `a` in the surface grant the permission outright (the hook returns
  allow, the command runs, you never look at the pane)? Blocks function 6's hook design;
  my default is yes, with the full command text shown before the key is accepted.
- Does the surface live in its own tmux session on the side monitor (my default,
  reattachable over SSH), or as a window inside the main byobu session?
- Should completions ("done", crash) appear in needs-Brian, or only in traffic as
  ordinary messages? My default is traffic only; the list stays things you must answer.
