> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Cross-provider messaging and supervision

**Status:** Draft (2026-10-09, revised 2026-10-10 for ADRs 0021 to 0026). Not accepted;
no design tickets are open and phase 0 has not run.

Labels: **D** documented, **O** observed (reporter named), **I** inferred, **A**
assumed, **L** live test needed (phase 0 number). Line numbers are from pages fetched
2026-10-09: `H` = code.claude.com/docs/en/hooks.md, `X` =
code.claude.com/docs/en/cross-session-messaging.md, `C` =
learn.chatgpt.com/docs/hooks.md. "V03 c5" is verification 03, claim 5. agy's bundled
`hooks.md` is cited through the verifications only.

## Purpose

Any Claude Code or Codex CLI session (agy best effort, never gating) can send durable,
acknowledged mail to any other and can supervise a session of another vendor. Brian sees
and answers everything that needs him on one surface. One Postgres record holds the
operational state.

## Authority sources

Human rulings reach this design through the ADR register; each ADR carries its
raw-record resolver. ADRs 0011 to 0020 resolve into
`F = /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f919e797-d858-4463-b37f-90a764516ed6.jsonl`
with `sed -n '<lines>p' F`, at these lines: 0011 (614); 0012 (680); 0013 (709, 716);
0014 (752, 758); 0015 (786); 0016 (823); 0017 (859); 0018 (908, 918); 0019 (973);
0020 (1006, 1019, 1033, 1047, 1063). The resolvers were not run here.

Also binding: ADRs 0005 and 0007 to 0010; the fourteen properties of 2026-08-09, cited
P1 to P14
(the design plan `2026-08-09-cross-model-coordination.md` on the `cross-model-coordination` branch,
lines 11 to 147); Brian's 2026-10-09 rulings quoted in
`BRIEF.md`.

**Integrity gap.** The brief quotes those rulings without line locators and the
properties file gives no resolver. Both need locators before this design can become
current.

## Glossary

- **Address:** `ag-` plus ten base32 characters, ours and immutable; vendor ids are
  evidence bound to it.
- **Ping, nudge, pointer:** the single notice that a message exists; a later, counted
  reminder; the one line either takes when typed into a pane.
- **Edge, mandate:** a recorded cross-provider supervision relationship; Brian's grant
  letting its supervisor decide approvals against a task statement.

## Scope and current state

Out of scope: same-family supervision and approvals (ADR 0011), panes in another tmux
window (ADR 0014), and ruling or ticket text, which stays in ADRs and the notes directory
(ADR 0008).

Current state (O): `plugins/denubis-external-agents/scripts/codex_supervisor.py` drives
one Codex pane in the caller's window. `local_mail` is dormant and records no model
acknowledgement (V01 c5, V04 c1). The proposers report Claude Code 2.1.295, codex-cli
0.160.1 with a daemon at 0.162.0, and agy 1.3.1; the brief's "Codex 0.157–0.159" is
stale.

## Goals and non-goals

- **G1** Mail is durable and acknowledged by the recipient model in its current context
  (P4, P5).
- **G2** An address survives clear, compact and resume; a fresh launch gets a new one
  (ADR 0019, P12).
- **G3** One ping per message per context through the vendor's channel; the body is
  pulled (ADR 0018).
- **G4** Unacknowledged mail climbs a ladder whose clocks pause on a block and whose
  acts are recorded (ADR 0015 to 0017).
- **G5** Cross-provider supervision in either direction, guards kept (ADR 0011, 0014;
  P13, P14).
- **G6** Approvals decided by exact request id, on the surface or at the pane
  (ADR 0012, 0013; P7).
- **G7** One surface shows everything that needs Brian (ADR 0020, P2).

Non-goals: mirroring transcripts (Brian: "if a message appears in a transcript, we can
treat it not important in postgres"); a per-pane monitor (ADR 0009); migrating
`local_mail`; agy parity.

## Design

### Shape

Five parts over one Record. Names are placeholders.

1. **Hooks**, per vendor, report events and inject pings. They never acknowledge,
   decide, or type.
2. **`agentmail`**: `whoami`, `send`, `read`, `ack`, `reply`, `withdraw`, run by the
   model through its shell tool (D2).
3. **`agentctl`**: supervisor verbs over the actuator: `bind`, `tail`, `send`, `nudge`,
   `interrupt`, `clear`, `compact`, `spawn`, `decide`, `escalate`, `approve --request`.
4. **`authority-intake`**: the PermissionRequest hook command.
5. **`agent-surface`**: Brian's view.

Writers call versioned SQL functions (`*_v1`). The caller's address is resolved from
its environment and process ancestry, never from an argument (P12).

### Record schema

Database `agent_record`, schema `record` (D1; ADR 0026). `line(n)` is one line of 1
to n characters; `id` columns default to `uuidv7()`; `->` is a foreign key.

```
-- Identity (ADR 0019)
agent(address text PK, kind IN (session, teammate, human, system),
      vendor IN (claude, codex, agy) NULL, parent -> agent, forked_from -> agent,
      ctx int NOT NULL DEFAULT 0, whoami_at, created_at, ended_at)
agent_alias(alias, address -> agent, source IN (brian, task, vendor, generated),
      since, until;  UNIQUE (alias) WHERE until IS NULL)
agent_session(vendor_session text PK, vendor, source, first_seen,
      address -> agent NULL, unresolved_reason)
agent_presence(address PK -> agent, vendor_session -> agent_session,
      boot_id, pid, proc_start,  UNIQUE (boot_id, pid, proc_start),
      tmux_server_pid, tmux_window, tmux_pane,
      pane_evidence IN (env, spawn, vendor-file, proc-lock, status-panel),
      socket_path, permission_mode, vendor_version,
      hooks_seen_at, listener_until, seen_at)

-- Mail
thread(id PK, subject line(160), created_at)
message(id PK, thread_id -> thread, sender -> agent,
      in_reply_to, answers bool, expects_reply bool, body text NOT NULL,
      ref_path, ref_anchor,                 -- pointer into .notes or an ADR
      dedupe_key, sender_transcript, created_at,
      UNIQUE (thread_id, id), UNIQUE (sender, dedupe_key),
      FK (thread_id, in_reply_to) -> message (thread_id, id))
withdrawal(message_id PK -> message, actor -> agent, reason line(400) NOT NULL, at)
delivery(id PK, message_id -> message, recipient -> agent,
      held_until_ctx int NULL, landed_at,  UNIQUE (message_id, recipient))
delivery_context(delivery_id -> delivery, ctx int,  PRIMARY KEY (delivery_id, ctx),
      pinged_at, ping_channel IN (socket, listener, hook, tmux),
      read_at, code text,
      acked_at, ack_session -> agent_session, ack_transcript,
      CHECK (acked_at IS NULL OR read_at IS NOT NULL))

-- Clock evidence, acts, numbers (ADR 0015 to 0017)
idle_span(address -> agent, started_at, ended_at NULL, opened_by, closed_by,
      PRIMARY KEY (address, started_at),  UNIQUE (address) WHERE ended_at IS NULL)
act(id PK, kind IN (pointer, nudge, interrupt, send, clear, compact, spawn,
                    approve_key, stuck_listed, stale_listed),
      actor -> agent NULL, target -> agent, edge_id -> supervision_edge NULL,
      delivery_id NULL, ctx NULL, seq int NULL, request_id NULL,
      channel IN (socket, listener, hook, tmux, view),
      outcome IN (intended, confirmed, refused, failed, unknown),
      refusal_reason, evidence, unblocked_s int NULL,
      intended_at, settled_at,  UNIQUE (delivery_id, ctx, kind, seq))
config(key PK, value jsonb NOT NULL, source_ref line(400))

-- Supervision (ADR 0011, 0014)
supervision_edge(id PK, supervisor -> agent, supervisee -> agent,
      supervisor_vendor, supervisee_vendor,
      CHECK (supervisor_vendor <> supervisee_vendor),
      tmux_server_pid, tmux_window NOT NULL, pane_id NOT NULL,   -- supervisee's pane
      bound_session -> agent_session, granted_by -> agent,
      created_at, ended_at, end_reason,
      UNIQUE (supervisee) WHERE ended_at IS NULL)

-- Authority (ADR 0012, 0013)
mandate(id PK, edge_id -> supervision_edge,
      task_statement text NOT NULL CHECK (btrim(task_statement) <> ''),
      ruling_ref line(400) NOT NULL, granted_by CHECK (granted_by = 'brian'),
      expires_at NULL, cwd_root NULL,                           -- ADR 0022
      created_at, revoked_at, revoke_reason)
approval_request(id PK, address -> agent,
      vendor_locator jsonb,                 -- evidence, never a key
      tool_name, input_sha256, input_text, cwd, pane_id,
      policy_verdict, policy_reason, danger bool,  -- copied from the approver
      hold_until NULL, opened_at, closed_at,
      closed_how IN (decided, answered_at_pane, orphaned))
approval_decision(request_id PK -> approval_request, outcome IN (allow_once, deny),
      decider_kind IN (brian, supervisor), decider -> agent,
      mandate_id -> mandate NULL, reason line(400) NOT NULL, decided_at,
      CHECK ((decider_kind = 'supervisor') = (mandate_id IS NOT NULL)))
approval_application(request_id PK -> approval_decision,
      method IN (hook_return, pane_key),
      result IN (applied, too_late, uncertain), evidence, at)
approval_escalation(request_id PK -> approval_request, supervisor -> agent,
      mandate_id -> mandate, question line(400) NOT NULL,
      pending_id -> pending_item, at)

-- Waiting on Brian: pointers only (ADR 0008; P2, P8)
pending_item(id PK, kind IN (ticket, question), owner_ref line(400),
      requester -> agent, label line(160), opened_at, seen_at,
      answer_message_id -> message NULL, answered_at,
      closed_at, closed_how IN (recorded, withdrawn, answered_at_pane),
      close_ref line(400) NULL,  UNIQUE (kind, owner_ref),
      CHECK ((closed_how IS NOT DISTINCT FROM 'recorded') = (close_ref IS NOT NULL)))
```

Reconciled with verification 01: a withdrawal has actor and reason and is written only
for the sender or `brian` (c6); acts and clock evidence live here, so functions 4 and 5
keep no private tables (c7, c8; P11); edges and mandates are tables (c9); a pane answer
closes without a decision-record reference (c10); codes are minted per delivery and
context at `read` (c13); Identity owns `agent` (c16). The `via` stamp (c14) is removed
by ADR 0025: a paneless sub-agent is not a participant.

Views derive all state: `traffic` (no bodies), `edges_by_window`, `block_span` (open
approvals and pending items per address), `clock` (unblocked idle seconds per delivery
and context) and `needs_brian` (open approvals and pending items, deliveries listed
stuck or stale, unresolved identities). Nothing leaves `needs_brian` on age (P2).

`pg_notify` carries an address or id as a hint; listeners also poll (V01 c1). An owner
role runs sha256-logged migrations, an app role may only execute `_v1` functions under
timeouts, and a reader role sees the views. The roles separate concerns and keep the
audit legible; they are not a security boundary against agents, which act with Brian's
authority and could type at any pane regardless (ADR 0024).

Pruning deletes a thread once every delivery is settled, the retention window has
passed (D4), and each message id is found in the transcripts named at send and
acknowledgement (recipient transcripts only when the sender has none, V01 c12), locking
the thread rows first (V01 c3). Withdrawn threads (ADR 0015) and open pending items are
never pruned. A thread cited by a decision record is prunable: the citation is a
transcript locator, as for every other citation (ADR 0023).

### Identity

Enrolment is one idempotent call, from a hook where reliable and otherwise from the
session's first `agentmail` command. Resolution, in one transaction:

1. Vendor session already known: its address (compact, resume, repeated hooks).
2. Fork marker: a new address with `forked_from`.
3. New vendor session whose process triple `(boot_id, pid, proc_start)` already owns a
   presence row: the same address, `ctx + 1`. Claude only, on `source=clear`.
4. An `AGENT_EXPECT` token from a spawn: the pre-allocated address.
5. Otherwise a new address and alias.

A context (`ctx`) is one span of a session's memory; compaction raises it and keeps the
address.

A hand-launched Codex pane cannot use rule 3 while a shared app-server daemon hosts its
session (O: proposal 02 §5; V02 c7). Until T5 to T7 settle a binding, such a session is
stored with a null address and listed as unresolved; it is never given a fresh address
silently and cannot send or acknowledge (ADR 0019b).

Identity follows the pane: every pane-owning session has its own address, including a
Claude teammate in its own pane. Paneless in-process sub-agents on every vendor are not
participants; `whoami`, `send`, `ack` and `reply` refuse a detected sub-agent caller and
record the attempt as an anomaly on `needs_brian` (ADR 0025, replacing ADR 0019a). A model-run `agentmail whoami` is the identity acknowledgement
(ADR 0019c), and every `agentmail` result starts with the identity line, so identity
returns after compaction without a hook. `claude --name` is a documented alias stem that
survives `/clear` and resume (V02 c3).

### Deliver: one ping, then silence

`send` writes the message and deliveries, commits, and notifies. Each channel then calls
`claim_ping_v1(delivery, ctx)`, a compare-and-set on `pinged_at`. Only the winner shows
the pointer, `mail <id> from <alias>: "<subject>" — agentmail read <id>`. A channel
that loses the claim prints nothing.

This designs out the loop V03 c5 found. On both vendors a Stop-hook injection is a
forced continuation (H L2668, L2589; C L1093), so a hook listing unread mail at every
Stop would continue the turn until acknowledgement and keep the session busy, and the
ladder would never start. Here the Stop hook wins the claim at most once per message per
context and is then silent whatever the acknowledgement state (ADR 0009, 0018).

Typing is the fallback, and only by a supervisor
into its own supervisee (ADR 0014, 0018). A session with no idle channel and no
supervisor gets its ping at its next hook event; the ladder still lists it for Brian.

### Acknowledge

Surfaced, read and acknowledged are separate facts (P4). `read` returns the body ending
in a code minted for this delivery and context. `ack <id> <code>` and
`reply <id> <code>` are the only writers of `acked_at` and refuse a code from another
context.

A message without `expects_reply` is settled by one acknowledgement. One with it stays
open until a reply marked `answers`, or a withdrawal; in a new context it has no
`delivery_context` row, so it is owed again with no write at compaction (P5).
`send --to self --when next-context` sets `held_until_ctx` (P3). An acknowledgement
proves receipt only (P4, P9).

Unproven: a hook or one shell pipeline can run `read` then `ack` without the body
entering the model's context. The guard is an audit matching each acknowledgement to a
tool-call record in the recipient's session file (V04 c2; T19). A sub-agent's
acknowledgement never counts: it is refused wherever a hook can see `agent_id` (H L743)
and listed as an anomaly; where Codex or agy cannot distinguish one, the structural guard
is that no sub-agent is ever pinged (ADR 0025, D9).

### Ladder

Times are seconds on the delivery's unblocked clock, read from `config` (ADR 0017).

| Step | Clock | Actor and channel | Recorded as |
|---|---|---|---|
| Ping | 0 | first channel to claim | `pinged_at` |
| Nudge 1 | 120 | Claude recipient: its own listener. Codex or agy recipient: its supervisor types the pointer | `act` nudge 1 |
| Nudge 2 | 720 | same | nudge 2 |
| Interrupt | 1,320 | supervisor only (ADR 0021) | `act` interrupt, with any refusal reason |
| Stuck | 1,920; or 1,320 when the interrupt is refused or no supervisor exists | `needs_brian` | `act` stuck_listed |
| Stale | 7,200 after acknowledging an unanswered `expects_reply` message | `needs_brian` | `act` stale_listed |

- **Clock.** `block_span` covers every open approval request and every open question or
  ticket that address raised. The clock counts all unblocked time, busy or idle; a block
  pauses it and it resumes where it stopped (ADR 0016 as amended by 0021, P6). No rung
  reads wall time, so nothing fires inside an approval chain. An `idle_span` (opens on a
  Stop with no background task and no hook continuation, closes on the next prompt, tool
  call or session start) is still recorded, because a pointer-line nudge needs an empty
  composer and an interrupt needs a running turn.
- **Acts belong to a session, never a daemon** (D3). The Claude listener sleeps until
  mail arrives or its own next rung falls due, then exits 2. A supervisor learns a
  supervisee's rung is due through its own ping channel and runs `agentctl nudge` or
  `agentctl interrupt`; a refusal is recorded with its reason. A Codex supervisor has
  no idle wake (C L626), so its rungs wait for its next turn. The stuck listing is a
  view and waits for neither.
- **Every act row carries `unblocked_s`**, the retuning evidence ADR 0017 asks for.
  Nothing is auto-acknowledged, expired or dropped (ADR 0015).
- **Interrupt** (ADR 0021). A supervisee still working past nudge 2 without
  acknowledging is interrupted by its supervisor through the guarded actuator (Escape or
  the vendor equivalent), which confirms the turn stopped and re-pings. A supervisee with
  no supervisor skips this rung and is listed stuck. A blocked supervisor is itself the
  item on `needs_brian`; nothing acts in its place.

### Supervise

`agentctl bind <address> --pane %N` writes an edge and prints it; `spawn` writes its
own. A same-vendor edge is refused by constraint, including for clear, compact and
spawn, which ADR 0011 leaves "not permitted until asked". One live edge per supervisee
keeps one pane writer (P13).

Every actuator verb, in order:

1. reads the pane id from the edge;
2. requires that pane to be in the caller's own tmux window;
3. proves the pane's live identity against the edge's session, refusing with both ids
   on a mismatch (ADR 0014);
4. asks the vendor adapter for the pane's state, where UNKNOWN refuses;
5. commits an `act` row as `intended` before any input;
6. pastes one line, presses Enter, and settles the row only on positive evidence.

`unknown` means no further keystrokes (P4). The core owns tmux; adapters own every
vendor fact. Direction inverts by binding the other way (P14).

### Authority

**Intake.** One command sits at each vendor's PermissionRequest (ADR 0012). It runs the
approver's classifier in-process, because the Codex front end prints nothing on `ask`
(O: `codex_permission.permission_output` returns `None`; entry point
`pipeline.classify_pipeline`). A policy allow or deny passes through unchanged; a policy
deny is terminal (ADR 0013). Otherwise intake mints a request id for this invocation,
commits the `approval_request`, and may hold.

**Decide.** `approval_decide_v1` is the only writer of a decision; its primary key gives
one decision per request and it refuses a closed request.

- Brian decides on the surface.
- A supervisor decides with `agentctl decide --request <id> --allow|--deny --reason`,
  only under a live mandate on its own edge, only for a request the policy left open
  and did not mark dangerous, and only as allow-once or deny (ADR 0013, P7). The
  mandate's task statement is the grant; the decision row links it and keeps the reason.
- `agentctl escalate --request <id> --question` lists the request for Brian and files a
  ticket where it is a question rather than a keypress (ADR 0013).
- Mail never decides (P7; X L161).

**Apply.** The held hook prints the typed allow or deny for its own request id; no key
is pressed and no standing grant is emitted. `agentctl approve --request <id>` is the
guarded pane key for a decision that arrived after the hold: Codex only at first, one
key, never resent, and only when the dialog's command equals the request's.

**First answer wins** (ADR 0012). A pane allow retires the row through the following
PostToolUse (same session, agent, tool and input hash, oldest open first). A pane deny
retires it through whichever event T24 finds, because PermissionDenied fires only in
auto mode (H L2252). A request whose hold has passed stays listed as "answer at the
pane".

**Hard gate.** On Claude the dialog is on screen from the start and a pane answer does
not cancel the hook (field reports, V07 c2; V06 c4). No source says what Claude does
with a hook `allow` returned after a pane deny (V06 c5). Until T23 passes:

- `approval_decide_v1` refuses every supervisor decision on a Claude request;
- intake holds a Claude hook only for Brian's own surface answer, which ADR 0012
  allows;
- a supervisor of a Claude supervisee can only escalate.

The gate opens by a migration citing the passing test. If T23 fails, a stale surface
row could also override Brian's own pane deny; that needs its own redesign and is not
decided here.

**Mandate rails** (ADR 0022). `expires_at` and `cwd_root` are the two mechanical hard
stops, checked when set; there is no decision count. The screen-reading
`codex_supervisor.py --approve` is soft-retired: it stays in the tool, marked deprecated
with a pointer to `decide --request <id>`, and every use is logged as a keypress approval
against the request id, until the hook route passes T22 to T26 and Brian removes it.
Evidence noted: the approver allows the pinned script on its file digest alone (O:
`trusted_reason` in `rules/trusted_scripts.py`); the whole pipeline was not traced (T27).

### Human surface

`agent-surface` is a Textual terminal app in its own tmux server and session (D7):
`tmux -L surface new -A -s surface agent-surface`. ADR 0020 leaves the choice between
this and a web app to durability and simplicity.

- **Durable.** It holds no state: every row is a view of the Record and every action an
  idempotent insert keyed by request or message id, so a kill or a dropped connection
  loses nothing. There is no service to keep alive and no port. Its own tmux server
  shares neither byobu's configuration nor the main server's fate (V07 c6, c7).
- **Simple.** One process, two dependencies (Textual 8.2.8, cached here: V07 c5;
  psycopg), no HTTP server, and no login system, which ADR 0020 requires of a web
  variant. SSH is the only door, so it is reachable on Tailscale and nowhere else.
- **Cost.** A terminal is clumsier than a web page on a phone; Brian has SSH there.

Reach: attach from the side monitor; from home or the phone,
`ssh <box> -t agent-surface` starts an independent instance sized to that screen, safe
because instances share only the Record.

**Reach test.** From the phone over Tailscale SSH: answer one approval and one ticket,
drop the connection mid-answer, reconnect. Pass when each answer exists exactly once,
the side-monitor instance agrees within one poll, and the layout is usable at 60
columns.

Panes: needs Brian (approvals with full command and policy reason, tickets, questions,
escalations, stuck, stale, unresolved identities); traffic (no bodies; completions and
crashes appear only here, ADR 0020); edges by window (ADR 0014). Actions: allow or deny
an approval; answer a ticket or question; withdraw mail with a reason (ADR 0015). An
answered ticket shows as "answered, awaiting record" until the agent records the ADR
(D6). There is no dismiss or snooze. The program never invokes tmux, types into a pane,
re-sends, counts or nags (ADR 0009, 0012).

### Vendor adapters

**Claude Code**

| Function | Mechanism, status and source |
|---|---|
| Identity binding | SessionStart hook on every `source`; session id from the payload, never the environment (D: V02 c1, c2); pane and pid visible there on `source=clear` (L T8). Actuator's live probe: foreground process group, `claude` pid, its socket (O: V05 c4; L T9) |
| Ping | (1) Claude sender: pointer posted to the recipient's socket (D: X L59; wire format L T10); plan and bypass recipients hold then drop it and are skipped (D: X L203, L212; L T11). (2) Any sender: Stop-launched `asyncRewake` listener, one per address, exits 2 (D: H L459, L3906, L3978; L T12). (3) Mid-turn `additionalContext`, and at Stop once (D: V03 c6, H L2668; L T13). (4) Supervisor's typed pointer (L T15) |
| Idle evidence | Stop with no background task or continuation, no prompt since (D: V05 c5); `idle_prompt` about 60 s later confirms (D: H L2307, L2329). The title carries no signal (O: V05 c3); the screen is an act-time guard only (L T15) |
| Dialog detection | PermissionRequest, without `tool_use_id` (D: H L1937). Question: PreToolUse and PostToolUse on `AskUserQuestion` (D: H L1587, L1890; L T29). Screen: `Do you want to proceed?`, `Esc to cancel`, composer `❯` (O: V05 c10; fragile) |
| Interrupt | Escape through the actuator; confirming event unknown (L T16) |
| Clear and compact confirmation | SessionStart `source=clear` with a new session id; `source=compact` with the same id (D: V02 c1; O: proposal 02) |
| Approval intake | Held PermissionRequest command hook, 600 s default, returns `decision.behavior`; an allow never overrides a deny rule (D: H L426, L1972). Dialog drawn alongside the hook; a pane answer leaves it running (field reports, V07 c2; L T22). Late allow after a pane deny (L T23, gate). Retiring a pane answer (L T24) |

**Codex CLI**

| Function | Mechanism, status and source |
|---|---|
| Identity binding | Spawned pane: `AGENT_EXPECT` passed by `tmux split-window -e` (designed; L T5). Hand-launched: SessionStart hook binding; hooks are documented only to run in the session `cwd` (C L195) and panes were seen daemon-hosted with no pane variable (O: proposal 02 §5): unresolved until L T5, T6. Session locks under `/proc` (O: ADR 0007 on 0.157.0; spawned panes only on 0.160.1). `CODEX_THREAD_ID` in tool calls (O on 0.153 to 0.156; L T5) |
| Ping | Mid-turn `additionalContext`; Stop `decision: block`, once (D: V03 c7, C L1093; L T13). No hook wakes an idle session (D: C L626; L T14). Idle: supervisor's typed pointer under today's guards (O: `send_message`, `_preflight_pane`, `_confirm_paste`, `_submitted`) |
| Idle evidence | Stop without continuation, no UserPromptSubmit since; no idle event exists (D: V05 c7). Title `Ready` confirms at act time (O: supervisor) |
| Dialog detection | PermissionRequest with `turn_id`, `tool_name`, `tool_input`, no request id (D: V06 c1). Screen: `_approval_is_pending`; question widget title `[ ! ] Action Required` (O: supervisor; ADR 0010) |
| Interrupt | Escape; the `Interrupt` hook confirms a main-thread interrupt, 1 s default, 3 s maximum (D: C L26, L184, L1099–1106; L T16) |
| Clear and compact confirmation | Clear: a new session lock id (O: ADR 0007; spawned panes); SessionStart `source=clear` timing undocumented, `/status` or `/statusline` as fallback (L T5, T7). Compact: `PreCompact`, `PostCompact`, and SessionStart `source=compact` before the next model request (D: C L25, L422–423, L675; L T30) |
| Approval intake | PermissionRequest hook; any deny wins; an allow skips the prompt; Codex waits for the hook; 600 s default; standing-grant fields fail closed (D: V06 c9; C L570, L614, L882, L886). Prompt during the hold, timeout, `apply_patch` and MCP approvals, slowest-hook wait (L T26). By-reference pane key (O: `approval_choice`; L T28) |

**agy.** Best effort, never gating. Every cell is from the bundled `hooks.md` as read
by V02, V03 and V05; nothing was observed at runtime.

| Function | Mechanism, status and source |
|---|---|
| Identity binding | `conversationId` from the first PreInvocation hook; no SessionStart event (D: V02 c12) |
| Ping | PreInvocation `injectSteps`; Stop `continue` with a reason, once; hooks are synchronous, so no idle wake (D: V03 c9; L T17) |
| Idle evidence | Stop with `fullyIdle: true` (D: V05 c8) |
| Dialog detection | No approval event; screen patterns borrowed from agent-bridge (A); an unrecognised screen refuses |
| Interrupt | Not established; the verb refuses |
| Clear and compact confirmation | Unconfirmable without SessionStart; the verbs refuse (D: V03 c9) |
| Approval intake | The approver's PreToolUse returns `ask`; shown on the surface, not answerable there (ADR 0012) |

## Failure and recovery

- **Postgres down.** Sends and acknowledgements fail loudly; hooks print one notice and
  exit 0; intake passes the approver's result through with no hold; tickets still land
  in the notes directory and register later. Nothing is allowed by default.
- **Listener dead or timed out.** No wake; `listener_until` shows it; the next hook
  pings; the ladder lists.
- **Session ended.** Its deliveries stay open and show their age; its requests close
  `orphaned`.
- **Untested vendor version.** The adapter fails closed and raises one item.
- **Record lost.** In-flight mail is lost; tickets re-register from their files. No
  backup is designed. Flagged, not decided.

## Decisions

Adopted defaults. Brian may overturn any of them.

- **D1** New database `agent_record`; `local_mail` untouched. Ruled by ADR 0026. No
  model acknowledgement there (V01 c5); "I don't really care about reusing prior work".
- **D2** The CLI is the act surface on every vendor; an MCP front end is optional after
  T18. A stdio server's environment goes stale across `/clear` (V04 c5).
- **D3** Ladder acts are made by the recipient's listener or its supervisor, never a
  daemon (ADR 0009, 0014, 0015; P13).
- **D4** Retention 7 days, then delete, not archive (proposal 01 Q1; the transcript
  ruling).
- **D5** A ticket pointer is the file path plus the heading's id (as `M10`); tickets
  without one are counted, not itemised. The skill defines no id (V01 c11).
- **D6** A ticket answered on the surface stays listed as "answered, awaiting record"
  (P8, ADR 0008; V01 c11).
- **D7** Terminal surface in its own tmux server (ADR 0020 delegates the choice).
- **D8** Surface-answer hold 600 s, the vendor default (H L426); listener timeout 12 h,
  subject to T12.
- **D9** A sub-agent's acknowledgement is refused where detectable and listed as an
  anomaly (ADR 0025).
- **D10** Removed: cited threads are prunable (ADR 0023).
- **D11** Socket channel for Claude senders only, off until T10 passes (ADR 0018's
  order; undocumented wire format).

Contradictions found and not resolved here:

1. **ADR 0012** names PermissionDenied as a candidate for retiring a pane-answered row;
   the hooks page says it fires only in auto mode (H L2252). The ruling stands; its
   mechanism clause needs the correction ADR 0019(b) received.
2. **P10** against the transcript ruling is resolved by ADR 0023 (transcript locator
   suffices); **ADR 0015** against **ADR 0016** is resolved by ADR 0021 (clocks run while
   unblocked, busy or idle).
3. The brief's accepted position, "Stop hooks are the 'you have mail' nudge on both",
   is refuted as a repeating mechanism by V03 c5; it was dispatcher-asserted.
4. V05 c6 says a Claude question has no hook signal; the hooks page lists
   `AskUserQuestion` under PreToolUse (H L1587, L1890). T29 settles it.

## Acceptance criteria

- **AC1 (G1).** `ack` succeeds only after `read` in the same context. Fails if it
  succeeds without a read or with a wrong or old-context code, or if a hook or actuator
  path sets `acked_at`.
- **AC2 (G1).** After a live `/clear` and `/compact`, an acknowledged unanswered
  question and a note to self are owed again and pinged once, nothing typed. Fails if
  not owed or pinged twice.
- **AC3 (G2).** The address survives clear, compact and resume, is new on a fresh
  launch, and differs for two sessions in one worktree. Fails on any merge, or an
  unresolved Codex session silently given a new address.
- **AC4 (G3).** One unacknowledged message yields one ping per context and no further
  hook output for ten minutes, on Claude and Codex. Fails on a second continuation.
- **AC5 (G4).** While an approval is open no ladder act fires and the clock stands
  still, then resumes from its paused value. Fails on an act row inside a block or a
  restart from zero.
- **AC6 (G4).** A silent recipient gets at most two nudges per context, then an
  interrupt if it has a supervisor and is working, then is listed stuck with the refusal
  reason; each act row has `unblocked_s`. Fails on a third nudge, or an item leaving unacknowledged and
  unwithdrawn.
- **AC7 (G4).** Withdrawal by the sender or Brian clears the obligation everywhere and
  keeps message, deliveries, actor and reason. Fails if a recipient can withdraw or a
  row is erased.
- **AC8 (G5).** Claude to Codex and Codex to Claude, `bind`, `send`, `tail`, `clear`
  and `compact` work. Fails on any keystroke with a dialog up, in copy mode, in another
  window, or after the supervisee is replaced, or if a same-vendor `bind` succeeds.
- **AC9 (G6).** Two identical commands give two requests, decided separately. Fails if
  a forged "approved by Brian" message, an override of a policy deny, or a mandate with
  the wrong supervisee, an ended edge, an exceeded rail or a dangerous request is
  accepted.
- **AC10 (G6).** A supervisor decision on a Claude request is refused until T23's
  evidence is recorded.
- **AC11 (G6, G7).** A pane-answered approval leaves no stale row; a surface-answered
  one resolves with no pane input. Fails on a row that outlives the turn.
- **AC12 (G7).** Killing the surface loses nothing; it executes no tmux; items leave
  only when answered, recorded or withdrawn; the reach test passes. Fails if age removes
  an item.
- **AC13 (P11).** With every hook, listener, pane and the surface killed, the Record
  still yields open mail, edges, mandates, requests and pending items.

## Implementation phases

### Phase 0: live tests

**This phase cannot start without the scratch-session permission parked in
the `project_open-questions.md` file in the main checkout's notes directory.** Tests 1, 3 and 4 run against `agent_record`
(ADR 0026). Nothing marked L is
built before its test. "T5" means item 5. Each item gives the claim, the pass
condition, and the verification that demanded it; 29 and 30 are this synthesis's.

1. **The server is PostgreSQL 18 with `uuidv7()`.** `SELECT version(), uuidv7()`
   returns both. (V01)
2. Dropped by ADR 0024: roles are not a security boundary, so the `pg_hba` state is not
   a gate. Number retained so later references hold.
3. **Constraints, prune race, single claimer.** Invalid states are refused; no committed
   reply is lost; one of two concurrent claims wins. (V01)
4. **`local_mail.mailboxes` columns.** Recorded; nothing depends on it. (V01)
5. **A Codex hook or tool call can bind a pane across `/clear`.** On a hand-launched
   pane, a SessionStart hook and a shell call log `source`, `session_id`, `PPID`,
   `TMUX_PANE`, `CODEX_THREAD_ID` before and after `/clear`; the pane's id and the new
   thread id appear before the next model request. (V02, V04)
6. **A launch flag keeps a pane out of the daemon.** The pane's process holds its own
   session lock. (V02)
7. **Where Codex shows the thread id.** `/status` or `/statusline` prints it at 200x25.
   (V02)
8. **Claude's SessionStart hook on `source=clear` sees pane and pid.** `TMUX_PANE`,
   `CLAUDE_PID` and the new payload id are present. (V02)
9. **A replaced supervisee is detected without hooks.** After kill and relaunch in the
   pane, the verb refuses naming both ids, on both vendors. (V05)
10. **Claude socket wire format, non-child sender.** An auth line plus a pointer line to
    an idle default-mode session starts a turn holding the pointer. (V03)
11. **Plan mode holds a socket ping.** The same post to a plan-mode session is held.
    (V03)
12. **The `asyncRewake` listener.** Armed from Stop, exit 2 wakes an idle session; it
    survives or re-arms across `/clear` and compaction; a second Stop starts no second
    listener. Recorded: timeout behaviour, largest timeout, whether the wake fires
    UserPromptSubmit. (V03, ADR 0018)
13. **One ping, no loop.** One unacknowledged message, session told to stop: exactly one
    continuation in ten minutes, on Claude and Codex. (V03)
14. **No hook wakes an idle Codex.** A finished background hook starts no turn. (V03)
15. **Guard fixtures.** The actuator refuses captured dialog, copy-mode, working and
    squeezed screens per vendor; Claude busy is read from the screen, not the title.
    (V03, V05)
16. **An interrupt can be confirmed.** Escape on a busy Codex fires `Interrupt` within
    3 s; Claude's following event is recorded. Otherwise the act stays `unknown`. (V03)
17. **agy hooks at runtime.** Stop `continue` and PreInvocation `injectSteps` reach the
    model. Never gating. (V03)
18. **Caller identity per call.** `whoami` from a shell call gives the same address and
    the right `ctx` across `/clear` and resume, on both vendors. Recorded: Codex stdio
    MCP server survival. (V04)
19. **The audit separates a model's acknowledgement from a hook's.** Each model `ack`
    has a session-file record; a hook-driven one fails the audit. (V04)
20. **A sub-agent cannot acknowledge.** A sub-agent attempts `ack` on each vendor.
    Pass on Claude: refused and listed as an anomaly. On Codex and agy: recorded whether
    a hook can distinguish the caller; if not, the documented limit is confirmed and the
    structural guard (no ping to a sub-agent) is checked instead. (V04, ADR 0025)
21. **Mail verbs run unprompted.** `ack` raises no approval prompt on either vendor.
    (V04)
22. **Claude's dialog under a held hook.** With a 60 s hold the dialog appears at once;
    a late hook `allow` resolves it with no pane input; a pane answer leaves the hook
    running. (V07, ADR 0012)
23. **Gate: pane deny, then hook allow.** Hold 60 s, deny at the pane, return `allow`
    at 30 s. Pass only if the command does not run. (V06)
24. **A pane answer can be retired.** PostToolUse matches a pane allow; some event marks
    a pane deny; the row is gone before the turn ends. (V06, V07)
25. **Identical requests stay distinct.** The same command twice, in one turn and
    across two prompts, gives two rows; a sub-agent's dialog fires the hook and its ids
    are recorded. (V05, V06)
26. **Codex's prompt under a held hook.** Recorded: prompt drawn during the hold;
    timeout falls to the prompt; `apply_patch` and MCP approvals fire the event; Codex
    waits for the slowest hook. (V06, V07)
27. **What the supervisor pin authorises.** Full trace of the approver's handling of
    `--approve` arguments; Codex `network_access` read with Brian's leave; informs the
    soft retirement's review (ADR 0022).
    (V06)
28. **By-reference pane key on 0.160.** `approve --request` presses one key on the named
    dialog only. (V05)
29. **A Claude question is a hook-visible block.** PreToolUse fires when
    `AskUserQuestion` opens, PostToolUse when answered. (synthesis)
30. **Codex compaction is hook-confirmable.** `PreCompact` and `PostCompact` fire on
    `/compact`. (synthesis)

### Later phases

1. **Record, identity, mail by hook.** Migrations, hooks and `agentmail` on Claude and
   Codex. Owns AC1 to AC3, AC7, AC13. Leaves the two vendors exchanging acknowledged mail
   with nothing typed.
2. **Surface.** Views and `agent-surface` with tickets, questions and withdrawal. Owns
   AC12. Leaves Brian reading traffic and answering tickets from any machine.
3. **Wake and ladder.** Listener, socket channel, clock, nudges, stuck and stale. Owns
   AC4 to AC6. Needs T10 to T14.
4. **Actuator and supervision.** Today's Codex guards behind the adapter, then the
   Claude adapter, edges and the `agentctl` verbs. Owns AC8. Needs T9, T15, T16.
5. **Authority.** Intake on Codex then Claude; surface allow and deny; mandates,
   `decide`, `escalate`; the by-reference key. Owns AC9 to AC11. Needs T22 to T28;
   Claude supervisor holds need T23.
6. **agy and the pruner.** Best effort. Needs T17.

## Verification and human judgment

Automation can prove the acceptance criteria. Three things remain Brian's judgment in
use: whether the ladder's timings are tolerable (ADR 0017); whether the surface is
readable on the phone; and whether supervisor decisions read as "narrowly scoped", which
only the decision rows can show (V06 c6).

Open tickets: none from the design; the parked scratch-session permission is raised at
phase 0. M10 to M15 are ADRs 0021 to 0026.

Not checked by this synthesis: the transcript resolvers; agy's bundled docs; any live
behaviour; installed settings and hook registrations; the Postgres server.
