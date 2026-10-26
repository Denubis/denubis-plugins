> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 05 — Supervise: any agent supervises any agent (proposal)

Proposer: Fable 5.1 at medium, named by Brian 2026-10-09 ("medium for proposer (Fable)").
Status: asserted-verify-before-relying unless a line says observed. Versions observed
today: codex-cli 0.160.1, Claude Code 2.1.295, agy 1.3.1, tmux under byobu.

## 1. The challenge

`codex_supervisor.py` hard-codes one direction: the caller is `$TMUX_PANE`, the
supervisee is the single `codex` in the same window, and every guard (`Ready` title,
composer, approval dialog, context meter, `/proc` locks, question widget) is a Codex
screen fact. The challenge is roles as data and invertible direction (Brian: "any
[codex,claude,agy] ... supervise any other"; property 14; DR4) without losing property
13's guards. The assumption protected: **a verb never types into a pane whose state it
has not positively established, and that evidence differs per vendor.** Generalising
verbs without generalising evidence turns `--message` into a blind `send-keys`.

## 2. Proposed mechanism

### 2.1 Split: one actuator core, one adapter per vendor

The core is the vendor-neutral tmux actuator (property 3's "guarded tmux actuator" and
property 13's sole pane writer). It owns: pane capture, `load-buffer`/`paste-buffer -p`/
`Enter` with submission confirmation (`send_message` lines 1769-1795 today), bounded
polling, the one-announcement dedup (`advance`, ADR 0009), and the refusal path. Every
predicate the core needs is supplied by a `VendorAdapter`:

```python
class VendorAdapter(Protocol):
    def match_pane(pane_pid, command, title) -> bool
    def live_identity(pane) -> str | None          # None = unprovable
    def classify(title, screen, record) -> State   # READY|BUSY|DIALOG|QUESTION|CRASH|UNKNOWN
    def composer_empty(screen) -> bool | None
    def context_left(screen) -> int | None
    def dialog_choice(screen, request) -> str | None   # key, or None = refuse
    def spawn_argv(model, effort, cwd, label) -> list[str]
    def clear() -> SlashOp; def compact() -> SlashOp   # (command, confirm(before, after))
    def quota(pane) -> QuotaReading | None             # optional
```

`UNKNOWN` and `None` refuse; they are never a pass.

| Verb | Core | Adapter supplies | Codex | Claude | agy |
|---|---|---|---|---|---|
| resolve | edge lookup + live check | `match_pane`, `live_identity` | `codex` cmd; `/proc` locks (observed, ADR 0007) | shell cmd, `✳` title; Claude session id from hook-written state (documented) | shell cmd; no identity probe |
| tail / status | capture | `classify` | title `Ready/Working` | hook state + screen | screen only |
| send / message | paste+Enter+confirm | `classify`, `composer_empty`, `context_left` | as today | Stop-after-last-prompt + `>` box empty (unverified) | screen only |
| spawn | split-window + wait ready | `spawn_argv`, `classify` | pinned catalogue (ADR 0010) | `claude --name <addr>` (unverified flag) | `agy` (one-shot CLI only; interactive unverified) |
| approve by reference | id match + keypress + cleared check | `dialog_choice` | 2-/3-option parser (today) | `Do you want to`/`Esc to cancel` (agent-bridge patterns, fragile) | `Do you want to proceed?` (agent-bridge) |
| clear / compact | type-literally + confirm + wait | `clear`, `compact` | lock delta / marker+meter (today) | SessionStart `source` hook → Record (documented) | no SessionStart: **unconfirmable** |
| quota | — | `quota` | session file (ADR 0007) | statusline `7d:53%` is Brian's statusline config, not a contract | none |
| question / answer | — | Codex-only widget verbs | `M-,` (unproven, ADR 0010) | AskUserQuestion is a dialog, not a widget → `approve`-style option parser | unknown |

### 2.2 Roles as data, binding recorded

The Record (function 1) holds one row per supervision edge:

```sql
create table local_mail.supervision_edge (
  edge_id       uuid primary key,
  supervisor    text not null references session_address,
  supervisee    text not null references session_address,
  kind          text not null check (kind in ('supervise','actuate','approve-mandate')),
  pane_id       text,            -- '%NN' of the supervisee's pane when actuate is granted
  vendor        text not null check (vendor in ('codex','claude','agy')),
  granted_by    text not null,   -- 'brian' or a supervisor address (no transitive mandate: DR12/prop 7)
  active        boolean not null default true,
  created_at    timestamptz not null default now()
);
```

A supervisor is told its supervisee by one explicit call, `supervise.py --bind
<supervisee-address> [--pane %NN]`, which writes the edge and prints it. Every later verb
resolves the pane from the edge, then **re-establishes liveness**: pane exists, the
adapter's `match_pane` holds, and `live_identity` equals the Record's current session id
for that address (Identity, function 2). Mismatch is a refusal naming both ids. This
replaces "the single `codex` in my window", which cannot express inversion or a
~20-window layout. `--spawn` writes the edge itself. Direction inverts by inserting the
edge the other way; the core never knows which vendor is "the supervisor", and a Codex or
agy supervisor runs the same script from its shell tool.

### 2.3 What replaces the monitor

No process watches a pane. Vendor hooks write typed events to the Record; the Record's
`needs-attention` rows are delivered to the supervisor's address through Deliver (function
3). Announce-once (ADR 0009) becomes a uniqueness constraint on
`(supervisee, kind, correlation_key)`, not a poll-loop memory.

| Event | Codex 0.160 (hooks doc, read today) | Claude 2.1.295 (hooks doc) | agy 1.3.1 (local hooks.md, observed) |
|---|---|---|---|
| turn ended | `Stop` {`turn_id`,`stop_hook_active`,`last_assistant_message`} | `Stop` {same + `background_tasks`} | `Stop` {`terminationReason`,`fullyIdle`,`error`} |
| approval pending | `PermissionRequest` {`turn_id`,`tool_name`,`tool_input`}; no request id | `PermissionRequest` {`tool_name`,`tool_input`,`permission_suggestions`}; no id; plus `Notification` `permission_prompt` after ~6 s | none (`PreToolUse` can `ask`/`deny` only) |
| idle | none | `Notification` `idle_prompt` (~60 s after Stop, no typing, no background agent) | `Stop` with `fullyIdle: true` |
| context reset | `SessionStart` `source` (does not fire at clear time: ADR 0007) | `SessionStart` `source` ∈ startup/resume/clear/compact/fork | none |

Because neither vendor gives an approval id, Authority (function 6) mints the exact
request id as `sha256(vendor, session_id, turn_id?, tool_name, canonical tool_input)` at
the hook, and `approve --request <id>` presses a key only if the adapter's dialog parser
finds that same command on screen now (today's live-state guard, kept).

**"Idle with unfinished work" (property 6) is a Record-derived predicate, never a screen
read:** last event for the supervisee is `Stop` with `stop_hook_active=false`; no
`UserPromptSubmit` since; an assignment addressed to it is open; no needs-Brian item
(approval, ticket, question) names it; and the idle grace has elapsed. Per-vendor evidence
that meets it: Claude — `idle_prompt` fired (positive, ~60 s); Codex — `Stop` plus title
`Ready` plus no `busy` datagram since (the title is confirmation, not truth); agy —
`fullyIdle=true` on `Stop` only. A nudge is one `send` of a pointer ("you have mail:
<id>"), never the body, recorded as a delivery attempt so retry cannot double-type
(property 4, DR13).

### 2.4 Codex guards, re-homed per vendor

| Guard today | Claude supervisee | agy supervisee |
|---|---|---|
| title `Ready` | Record state READY (Stop, no later prompt) **and** screen shows the `>` input box | screen only; title is static |
| composer empty | `>` box empty (needs one observation of the box geometry) | unknown |
| approval dialog pending | `PermissionRequest` row open **and** screen matches; the hook alone is a wake-up (same as today) | screen pattern only |
| 30 % context floor | statusline percentage if Brian's statusline prints one; else refuse | refuse (no meter) |
| `/proc` session locks | not applicable: Claude's foreground process group is a statusline `bash` (observed on %60 and %71 today), so identity comes from hook-written state keyed by `session_id` | launch `conversation_id` only |
| queued-question widget | AskUserQuestion dialog → option parser; `Notification` `agent_needs_input` as wake-up | unknown |

Same-family: property 7 / DR11 keep Claude→Claude and Codex→Codex on native facilities
(SendMessage/ListAgents, Codex sub-agents). Under this proposal the adapter still exists
for same-family `clear`, `compact`, `spawn` (native paths cannot do those), but
`send`/`tail` go native, and "never Claude as approver for Claude" stands (see Q1).

## 3. Verification (falsifiers)

1. *Adapter boundary is complete.* Grep the core for `codex`, `Ready`, `/proc`,
   `thread-writer-locks`: any hit outside `adapters/codex.py` fails.
2. *Inversion works.* Spawn a Codex pane; from inside it run `supervise.py --bind
   <claude-addr>`, then `--message` into the Claude pane; the Claude transcript must hold
   the text, and the Record must hold a delivery row. Repeat Claude→Codex.
3. *No blind keystroke.* For each adapter, present a live approval dialog and run
   `--message`; it must refuse. Positive control: clear the dialog, re-run, it must send.
4. *Liveness beats the edge.* Kill the supervisee and start a new one in the same pane;
   `--message` must refuse on identity mismatch, not type.
5. *Announce once.* Hold a Codex dialog for an hour under hook+poll; exactly one
   needs-attention row and one delivery to the supervisor.
6. *Idle predicate.* Claude supervisee with a long `Bash` tool running: no nudge (no
   `idle_prompt`, `background_tasks` non-empty). Same session after Stop with an open
   assignment: one nudge, recorded.
7. *Clear confirmed per vendor.* Claude: `--clear` must produce a `SessionStart
   source=clear` row with a new `session_id`; Codex: a new lock id (today's test).

## 4. Interfaces

- Record (1): needs `supervision_edge`, `session_state` (last hook event), needs-attention
  rows unique on correlation key; gives typed hook events.
- Identity (2): needs the address↔live-session resolver; gives pane binding and mismatches.
- Deliver (3): the actuator **is** its universal path; gives adapters, takes the
  supervisor-side event nudge.
- Acknowledge (4): a nudge is done only when the supervisee model acks; gives attempt rows.
- Authority (6): needs request ids and the mandate check before `approve` presses a key.
- Human surface (7): receives every refusal and needs-attention row with its pane id.

## 5. Failure modes

- Hook not installed or untrusted: Record state stale → UNKNOWN → verbs refuse and the
  surface shows "no hook evidence for <addr>". Screen is never lifecycle truth.
- Pane squeezed (Codex composer undrawn; Claude box pushed off by the agents list, seen on
  %60 today): refuse with geometry, as today.
- Supervisee replaced in-pane: identity mismatch refusal (test 4).
- Two supervisors bind one supervisee: allowed for `supervise`, refused for a second
  active `actuate` edge (one pane writer, property 13).
- agy anything: best effort; a refused agy verb is a report, not a block (Brian: "I don't
  really care about agy if it's hard").

## 6. Rejected alternatives

- **Same-window uniqueness rule.** Cannot express inversion; the edge plus liveness
  check is stricter.
- **Codex app-server / Claude socket as the universal path.** Undocumented or
  experimental (03 report); future adapters behind the same Protocol only.
- **Screen-scraped idleness.** Violates property 6; agent-bridge measured 79 % false
  positives scraping dialogs.
- **A daemon per supervisor.** Reintroduces the monitor ADR 0009 removed.

## 7. Could not check

- Claude's input box geometry and whether its pane title changes while working (title was
  `✳ …` on every Claude pane listed; no busy-state capture taken).
- Whether `claude --name` sets a stable address at launch; the cross-session doc was not
  opened.
- Claude hooks doc beyond char 200 000; Codex `--approve` on 0.160 (no live pane driven).
- agy's interactive TUI at all: dialog text, title, composer.

## 8. Questions for Brian

1. Does "any supervises any" override property 7/DR11 for same-family pairs, so a Claude
   supervising a Claude uses the tmux actuator for `send` too, or do same-family `send`
   and `tail` stay on SendMessage/ListAgents with tmux only for clear/compact/spawn?
   Blocks: adapter scope and whether a Claude→Claude edge may carry `actuate`.
2. May a supervisor drive a supervisee in a different tmux window once the Record edge and
   liveness check pass? Blocks: replacing the same-window rule.
3. The idle grace before a "mail pointer" nudge (Claude's `idle_prompt` is ~60 s; Codex
   has no idle event). Blocks: the predicate in 2.3; recommended default 120 s.
