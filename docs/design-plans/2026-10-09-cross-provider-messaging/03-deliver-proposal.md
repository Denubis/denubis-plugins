> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Proposal 03 — Deliver (Fable, medium; named by Brian 2026-10-09)

Labels: **O** observed by me today, **D** documented (vendor page or local vendor doc),
**I** inferred, **A** assumed. Versions observed: Claude Code 2.1.295, codex-cli 0.160.1,
agy 1.3.1, tmux under byobu.

## 1. The challenge

A message in the Record must reach a live model on Claude Code, Codex, or (best effort)
agy, whether that model is mid-turn or idle, without the delivery itself becoming a
second control path into the pane. The assumption protected: **"written is not
received."** A row in Postgres, a socket write, or a keystroke is only an attempt; the
model's own acknowledgement (function 4) is the only completion. Deliver therefore has
to be safe to repeat and must never answer a dialog by accident (DR9, DR13, property 4).

## 2. Mechanism

### 2.1 Two paths, one actuator

- **Check path (hooks):** at every point the vendor's loop already reaches, a hook reads
  the Record for this address and injects a *pointer* (ids and subjects, never bodies):
  mid-turn delivery on all three vendors, plus the "about to idle" moment.
- **Wake path:** for an idle session, a vendor-native wake where one exists (Claude
  socket, Claude asyncRewake), otherwise the **tmux actuator**, the one verb that types
  into a pane. Supervision verbs call it with `kind=command`, mail with `kind=mail`;
  nothing else runs `send-keys`/`paste-buffer` on an enrolled pane.

What is typed is always a one-line pointer, never the body (agent-bridge pattern, 04 §4):
`mail <msg_id> from <sender>: "<subject>" — run \`msgctl read <msg_id>\``. One line avoids
Codex's paste placeholder, keeps bodies out of scrollback, and makes a duplicate
keystroke one redundant read rather than a duplicated instruction.

### 2.2 Adapter order per vendor

**Claude Code** (preference order):
1. *Inbox socket.* Path from `CLAUDE_CODE_MESSAGING_SOCKET` (O: `/run/user/1000/cc-socks/<pid>.sock`,
   ten listening now), recorded by the session's SessionStart hook into the Record.
   Wire format O from the 2.1.295 bundle's own log line: first line
   `{"type":"auth","token":"$CLAUDE_CODE_MESSAGING_TOKEN"}` (optional on Linux, D), then
   `{"type":"user","message":{"role":"user","content":"..."}}`. D: "read between tool
   calls during an active turn… When the receiving session is idle, Claude Code starts a
   new turn." Complete line within 30 s or the connection closes (D).
   *Caveat (D):* a non-child sender asserts no permission class, so a
   `bypassPermissions` receiver **holds** the message behind a dialog that drops after
   `dialogExpiry` (5 min); auto/acceptEdits/default receivers deliver it. The socket is
   primary only when Identity has recorded the recipient's `permission_mode` (D hook
   field on both vendors).
2. *Stop-launched asyncRewake watcher.* A Stop hook starts a command hook with
   `asyncRewake: true` that `LISTEN`s on `mail_<address>` and exits 2 when a row for this
   address commits. D: "an asyncRewake hook that exits with code 2 wakes Claude
   immediately even when the session is idle"; D: timeout *is* enforced on asyncRewake,
   so the watcher re-arms itself from each Stop with a bounded timeout (value is Brian's;
   default 30 min). Payload under 8000 bytes, NOTIFY only at commit (03 §lesson 4).
3. *Check-path hooks:* Stop → `hookSpecificOutput.additionalContext` listing unread
   pointers (D; not `decision:block`, which caps at eight continuations and reads as an
   error). UserPromptSubmit and PostToolUse → `additionalContext` for mid-turn (D).
4. *tmux actuator* (below).

**Codex:**
1. *Check-path hooks:* Stop `decision:block` with the pointer list, exactly the shape
   that ran on 2026-08-13 (O: worktree `hooks/stop.py`, D: Stop block "keeps Codex
   going"); PostToolUse/UserPromptSubmit `additionalContext` mid-turn (D). D: no hook
   wakes an idle Codex: "Finishing a background hook doesn't start a new turn."
2. *tmux actuator* is the idle path. This is today's `send_message` with its guards
   (O: `_preflight_pane`, `_confirm_paste`, `_submitted`), moved behind the shared verb.
3. *App-server* is **not** in the order yet. D: `turn/steer` needs an active turn and
   `expectedTurnId`; `turn/start` on a TUI-owned thread is undocumented. O: a shared
   daemon socket exists (`~/.codex/app-server-control/app-server-control.sock` →
   `/tmp/codex-daemon-1000/<hash>`, listening) and `codex app-server proxy` exists, but my
   read-only `initialize`/`thread/list` probe through the proxy returned nothing (exit 0,
   no bytes). Keep as an experiment behind a version pin; it is marked "experimental and
   unsupported" by OpenAI (D).

**agy (best effort, never gating):**
1. *Check path:* Stop hook returning `{"decision":"continue","reason":"<pointers>"}` (D,
   local `hooks.md` lines 300-330: reason "injected as a system message if continuing");
   `PreInvocation` → `injectSteps:[{"userMessage":...}]` mid-turn (D). Runtime behaviour
   unverified (02 §Could not check). No SessionStart, so identity comes from the first
   hook's `conversationId` (D).
2. *tmux actuator* with screen-only guards. No title signal known; the dialog regexes are
   agent-bridge's ("Do you want to proceed?" + lowercase "esc to cancel",
   "Requesting permission for:"), which its author documents as fragile (04 §4).

### 2.3 The actuator: `msgctl deliver --to <address> --message <id>`

Target comes from the Record's endpoint row (pane id recorded at enrolment), never from
scanning the caller's window; the window-scan selector in `discover_codex_pane` stays
only as the supervisor's legacy `--resolve`. Per-pane `flock` and per-delivery tmux
buffer name `msg-<attempt_id>` (both exist in the receipts worktree, O: lines 963, 1817)
close the shared-buffer race.

Preflight (all refusals are recorded, §5):

| Guard | Codex | Claude | agy |
|---|---|---|---|
| pane exists, `#{pane_in_mode}`=0, foreground process matches vendor | O/D tmux | same; note `pane_current_command` is the shell (`fish`/`bash`) for Claude panes, so match on title prefix `✳`/`◐`/`◑` (O: bundle `D6="✳"`, `E6=["◐","◑"]`) | process name `agy` (A) |
| idle | title matches `Ready` (O) | title starts `✳`, and no ` esc to interrupt` in the tail (O: bundle strings; semantics I) | no busy spinner line (A) |
| no pending dialog | `_approval_is_pending` on last 12 lines (O) | "Do you want to proceed?" / "Esc to cancel" / "Press Esc to cancel" in last 14 lines (O: bundle strings) | agent-bridge regexes (04) |
| composer empty and drawn | `_composer_text` (O) | last non-blank line is the bare prompt marker (A; needs the capture test in §3) | A |

Submission: `load-buffer` → `paste-buffer -p` → `send-keys Enter` up to 3 times, each
confirmed by positive evidence only: Codex `Working` in title or composer cleared (O);
Claude title flips to `◐`/`◑` or ` esc to interrupt` appears (I); agy pointer gone plus
new output (A). No evidence → `unknown`, **no further keystrokes** (DR13).

### 2.4 Record shapes (what Deliver writes)

```
session_endpoint(address PK, vendor, pane_id, socket_path, permission_mode,
                 hooks_seen_at, updated_at)
delivery_attempt(attempt_id uuid PK, message_id, recipient, adapter
                 ∈ {claude_socket, asyncRewake, hook_stop, hook_midturn, tmux, agy_hook},
                 outcome ∈ {submitted, deferred, refused, failed, unknown},
                 reason text, evidence text, at timestamptz)
```
`delivery_attempt` is append-only and immutable (receipts invariant: attempt row commits
before any pane input, O: 01 §c). Delivery state on the message is derived from attempts
plus the ack (function 4), never stored twice.

## 3. Verification (falsifying tests)

1. **Socket wire format works and wakes idle.** Scratch `claude -p` with
   `crossSessionInbound: accept`; post the two lines; expect a new turn whose first user
   content is the text. Failure retires adapter 1.
2. **Hold rule bites.** Same, in `bypassPermissions`; expect a held dialog, not a turn.
   Failure means the mode gate is unnecessary; pass means it is required.
3. **asyncRewake wakes idle.** Stop hook with `asyncRewake` that sleeps 20 s then exits
   2 on an idle scratch session; expect a turn carrying stderr. Failure retires adapter 2.
4. **Codex Stop block re-proven on 0.160.1** and **async hook does not wake**: fire an
   async hook, let the session idle, assert no turn starts.
5. **agy Stop `continue` at runtime**, and PreInvocation `userMessage` lands mid-turn.
6. **Guard fixtures.** Captured screens (dialog, copy-mode, working, no composer) for
   each vendor must make the actuator refuse; the Codex set already exists in the
   supervisor tests, Claude and agy sets must be captured from scratch sessions.
7. **Claude title semantics.** Watch a scratch session's `#{pane_title}` across one tool
   call: expect `◐/◑` while working, `✳` idle. This pins adapter 4's idle test.
8. **Duplicate safety.** Deliver the same message twice; the second must be a `deferred`
   or `refused` row, never a second keystroke, once an attempt is `submitted` or `unknown`.

## 4. Interfaces

- **Record (1):** owns both tables and `NOTIFY` on insert; I need `SKIP LOCKED` claims
  per address.
- **Identity (2):** gives the endpoint row (vendor, pane id, socket, mode, hooks-seen)
  and refreshes it on resume/clear/compact. No pane id → check path only.
- **Acknowledge (4):** I never set ack; `submitted` without ack resurfaces, citing the
  attempt id.
- **Supervise (5):** same actuator, `kind=command`, every guard inherited.
- **Authority (6):** `refused: dialog pending` routes to approver/Brian by request id;
  Deliver never clears a dialog.
- **Human surface (7):** shows `refused`, `unknown`, stale `deferred`, and sessions with
  no hooks seen and no socket ("unreachable").

## 5. Failure modes

| Failure | Design response |
|---|---|
| Socket path stale | `ECONNREFUSED` → `failed`, next adapter; Identity re-records on SessionStart. |
| Message held and expired in Claude | No signal back (D); `submitted` without ack resurfaces via the check path at next Stop. |
| Pane busy | `deferred`; hooks carry the pointer mid-turn; actuator retried only on the next Stop/idle event. |
| Dialog pending | `refused`, raised once to the human surface (ADR 0009). |
| Composer unreadable / short pane | `refused` with geometry, as today. |
| Enter swallowed | 3 Enters with positive confirmation; then `unknown`, no retry, human item. |
| NOTIFY lost | watcher also polls every 60 s; `deliver` is idempotent per message. |
| Vendor TUI strings change | guards fail closed (`refused: unrecognised screen`); build pinned in `session_endpoint.vendor`; a failing fixture names the pin. |
| agy anything | best effort: `failed` rows only; never blocks Claude/Codex. |

## 6. Rejected alternatives

- **Typing the body into the pane:** paste placeholder, scrollback leakage, duplicated
  instruction on retry (DR9/DR13).
- **Claude channels:** research preview, no acknowledgement, dropped under MCP
  2026-07-28 (03 §3).
- **Codex app-server as primary:** unsupported transport, TUI ownership undocumented,
  probe silent.
- **`decision:block` on Claude's Stop:** reads as an error, eight-block cap.
- **Polling the pane for mail:** idle panes get no monitor (ADR 0009).
- **Window-scan pane selection:** ties delivery to the caller's window; the Record knows
  the pane.

## 7. Could not check

- Claude socket accepting a non-child sender in auto mode (D says yes; not exercised).
- Claude title idle/working semantics and composer-empty signal (bundle strings only);
  whether `asyncRewake` survives `/clear`.
- Codex daemon: whether TUI threads live on it and accept `turn/start`; the proxy probe
  returned nothing (WebSocket framing may be needed).
- agy: every runtime claim; no agy pane was running.
- Claude socket wire format: only the bundle's log line and the docs' auth line were
  found; no protocol page.
- Whether `crossSessionInbound` is set in Brian's settings (not read).

## 8. Questions for Brian

- Should an idle Claude session be woken by the socket at all when its mode is
  `bypassPermissions`, given the 5-minute hold-and-drop, or should those sessions get
  `crossSessionInbound: accept` in user settings? Blocks adapter 1's gate.
- Is an `asyncRewake` watcher that re-arms itself from every Stop acceptable (one extra
  process per idle Claude session), and what timeout? Blocks adapter 2.
- May Deliver run scratch `claude -p` / `codex` / `agy` sessions for the §3 fixture
  captures (they type into *scratch* panes only)? Blocks §3.1-3.7.
