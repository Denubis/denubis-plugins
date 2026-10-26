> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 04 Acknowledge: proposal

Proposer: Claude Opus 5.5 at xhigh, named by Brian 2026-10-09. Labels: **O** observed by
me today, **D** vendor-documented, **I** inferred. Nothing was run in a live pane.

Flagged, not resolved: property 4 against ADR 0009 (Q1); Codex's hook documentation
against ADR 0007 (§7); the brief says Codex 0.157 to 0.159, I observed 0.160.1 and
0.162.0; an MCP call is not model-only on Claude (§2).

## 1. Challenge

Receipt must be a fact that exists only because the recipient model, in its current
context, said so about a body it was actually served. It stays separate from three facts
other parts can produce: delivered (a pointer was shown), read (a tool returned the
body), and settled (answered or closed). The assumption protected is property 4's:
whoever reads "acknowledged" can rely on the recipient's live context having had the
item, so nothing owed disappears because a hook fired, a pane was typed into, or a
context was compacted away. Today's plugin breaks this twice (O): `store.notify()`,
called from `stop.py`, moves `new` to `notified` and never shows the item again, and
`pull` sets `read` as a side effect.

## 2. Mechanism

A **context** is one span of a session's memory; compaction or `/clear` starts the next.
Identity numbers them per address (`ctx`).

**Columns I need from Record**

```
message(id, sender, subject, body, needs_answer, in_reply_to, answers,
        ref_path, ref_anchor)                      -- immutable
delivery(id, message_id, recipient, held_until_ctx, closed_at, closed_by)
delivery_context(delivery_id, ctx,                 -- one row per recipient context
    surfaced_at, surface_count, actuated_at,       -- Deliver writes
    read_at, code,                                 -- read() writes
    acked_at, ack_session,                         -- ack()/reply() only
    PRIMARY KEY (delivery_id, ctx))
```

State is a view over these facts, never stored: held, pending, surfaced, read,
acknowledged, answered, closed. A new context has no `delivery_context` row, so anything
unsettled is owed again with no write at compaction, and the earlier acknowledgement
stays as history (DR6).

Settlement: `needs_answer=false` is finished once acknowledged. `needs_answer=true`
stays open until the recipient replies with `answers=true`, or it is closed. An
assignment's answer is a completion claim, not verification (property 9).

**The act.** Three MCP tools on one stdio server, the same on every vendor:

- `read(ids)` returns each body as one text block ending in an eight-character code
  minted for that delivery and context.
- `ack(id, code)` records receipt; refused unless the code was minted in the caller's
  current context. Repeats are no-ops.
- `reply(id, code, body, answers)` acknowledges by citing the id and, with
  `answers=true`, settles.

The code makes receipt causally later than the body reaching the caller: it cannot come
from a subject-only nudge, from the same tool batch as `read`, or from a compaction
summary.

| Vendor | Act | Evidence the model did it |
|---|---|---|
| Claude Code 2.1.295 (O) | MCP call `mcp__…__ack` | assistant `tool_use` record in the session file (O for other MCP tools) |
| Codex 0.160.1 on PATH, 0.162.0 in today's session files (O) | same server; per-tool `approval_mode` set never to prompt (key D, value unverified) | `item_completed` record with `item.type="McpToolCall"` (O for context7) |
| agy 1.3.1 (O) | same server via `agy mcp add` (D, untested), else shown unacknowledged | none designed |

**Premise correction.** An MCP call alone does not prove a model act: Claude Code hooks
have an `mcp_tool` type that calls a server's tool with values substituted from hook
input (D). Receipt therefore rests on three things together: only `ack`/`reply` write
`acked_at`; the code; and an audit matching every receipt to a tool-call record in the
recipient's own session file.

**Resurfacing without duplicate pane input.** Hooks only surface. Every channel first
calls `claim_due(address)`, one `UPDATE … RETURNING` that stamps `surfaced_at`; a
channel that gets no rows stays silent. Due means unacknowledged in this context, not
held, and never surfaced here or last surfaced over R ago with fewer than N surfaces.

1. Context start: `SessionStart` with source `compact` or `clear` prints the digest as
   added context, with no pane input. Claude: D, and the events are O in this
   repository's transcripts. Codex: D.
2. Turn end: Stop returns `decision: block` with the digest, once per turn
   (`stop_hook_active`, D on both).
3. Idle and never surfaced in this context: Deliver's actuator types one pointer line,
   once per delivery per context (`actuated_at`).

The digest holds ids and subjects, never bodies.

**Future-self mail**

- Written: `send(to="self", when="next-context")` sets `held_until_ctx = ctx + 1`: not
  due now, owed and unacknowledged in the successor.
- Derived: the context-start digest lists everything still owed to the address and what
  it awaits from others. It is computed from the Record, so a missed PreCompact loses
  nothing (property 5).

```
mail: you are plugins-ad, context 7. Acknowledge 2:
 m-41c2 note to self "resume: half-written proposal" (from context 6)
 m-3f90 QUESTION from codex-otter "which table owns ctx?" (acknowledged in context 6, unanswered)
```

**Needs Brian** is a view, so only the underlying fact can remove a row:

1. `answer`: recipient is Brian, `needs_answer`, unanswered. Tickets are pointer rows
   (`ref_path` into the `project_open-questions.md` file in the main checkout's notes directory, no body). Approvals come from
   Authority.
2. `stuck`: agent recipient, unacknowledged, and nudges exhausted, no live session, or
   older than T1.
3. `stale`: agent recipient, acknowledged, `needs_answer`, unanswered longer than T2.

**Retry and give-up.** Hook nudges: at most N per context, at least R apart. Pane input:
once per context. Giving up means nudging stops and the item joins Brian's list as
`stuck`; nothing is auto-acknowledged, expired, or dropped, and a new context starts a
fresh count. Recommended N=2, R=10 min, T1=30 min, T2=2 h. One retry covers a crash
between claim and display; Brian's observation in ADR 0009 is that further repeats sit
behind a prompt they cannot clear.

## 3. Verification

| Claim | Falsified if |
|---|---|
| No hook, actuator, or reader produces a receipt | Every hook entry point and `claim_due`, run 100 times against one pending delivery, leaves any `read_at` or `acked_at` |
| Receipt needs the body served in this context | `ack` succeeds with no `read`, a wrong code, a previous context's code, or (Claude) in the same batch as `read` |
| Every receipt is a model tool call | Live per vendor, an `acked_at` row lacks a matching session-file record; or a Claude `mcp_tool` hook wired to `ack` passes the audit |
| Context loss re-owes without duplicate input | Live `/compact` and `/clear` holding an acknowledged unanswered question and a note to self: the digest appears other than once, the actuator types, the earlier `acked_at` changes, or an item is not owed |
| One claim, one surfacer | Two concurrent `claim_due` calls return the same row in any of 1,000 rounds |
| A lost hook loses nothing | With hooks disabled across a compaction, an owed item stops being owed |
| The list is derived | Any event except answer, acknowledge, or close removes a row |
| Give-up is bounded and visible | A silent recipient gets more than N nudges or two typed lines per context, or is missing from the list |

## 4. Interfaces

- **Record:** the columns above; immutable bodies; `acked_at` writable only through
  `ack`/`reply`; prune only when every delivery is acknowledged and not awaiting an
  answer. An acknowledged body is already in both transcripts (I).
- **Identity:** a stable address; `ctx` raised exactly once per compaction or clear, not
  on resume; both resolvable inside a tool call and a hook; liveness; the vendor session
  id; a separate address for a sub-agent (property 12).
- **Deliver:** calls `claim_due` before showing anything; pointer-only pane input; never
  writes `read_at` or `acked_at`.
- **Supervise:** may request a note to self before `--clear` or `--compact`; a receipt
  is never completion.
- **Authority:** `ack` and `reply` never approve; approvals settle only by request id.
- **Human surface:** renders the view; Brian's answer is a reply as `brian`; Brian can
  close a `stuck` item.

## 5. Failure modes

- **Surfaced or read, never acknowledged:** stays unacknowledged; one retry; then
  `stuck`.
- **`ack` held by a permission prompt:** no receipt; the prompt is Authority's item;
  `stuck` after N.
- **Context change undetected:** an old code is still accepted and carry-over waits
  until the next detected change.
- **Context change counted twice:** one extra resurfacing; no loss.
- **Postgres down:** tools fail loudly; hooks print a notice without blocking; nothing
  is acknowledged.
- **Recipient session ended:** no nudge possible; `stuck` at once.

## 6. Alternatives rejected

- **Reading is receipt:** a tool return is a harness fact, and a batch pull marks
  everything.
- **Receipt by id alone:** assertable from the nudge or a summary.
- **Stop hook parses `last_assistant_message`** (Codex, D): a hook asserting for the
  model.
- **PostToolUse hook as witness:** the session file holds the same evidence more
  reliably (ADR 0007).
- **Clearing the acknowledgement at compaction:** destroys receipt history (DR6).
- **PreCompact manifest and fence** (August AC5): depends on a hook firing before
  context loss, and no hook can make the model write.
- **A stored needs-Brian table:** something must clear it, and it can drift.

## 7. Could not check

- Codex `SessionStart` timing on 0.160 to 0.162. ADR 0007 measured 0.157.0 and saw no
  event at the moment of `/clear`. Documented and observed disagree, so `ctx` on Codex
  must also accept the supervisor's `--clear`/`--compact` confirmations and the session
  file's `compacted` record, whose keys include `window_number` (O).
- The meaning of each Codex `approval_mode` value (`auto | prompt | writes | approve`).
- Whether Codex's MCP process reaches Postgres under the sandbox; `network_access =
  true` is set here (O).
- **Codex code mode.** MCP calls appear nested inside an `exec` call (I, from record
  shapes). A model could script `read` then `ack` in one `exec` without the body
  entering its context. The audit can flag that, not prevent it.
- Whether Claude records an MCP call made by an `mcp_tool` hook. The hooks page was read
  to 100,000 of 258,323 characters.
- Whether the MCP server can learn the caller's address and `ctx` per call. `/clear`
  appears to start a new Claude transcript (I), so a long-lived server's environment
  would go stale.
- Whether a sub-agent's call is distinguishable from its parent's. Codex: "Subagent
  hooks use the parent session id" (D).
- agy: nothing tested.

## 8. Questions for Brian

1. May "give up" mean "stop nudging the model and put the item on your list"? Property 4
   says retry until acknowledged; ADR 0009 says announce once. Blocks the retry policy.
2. Do you adopt the §2 numbers (N, R, T1, T2)? Blocks when `stuck` and `stale` rows
   appear.
3. May a sender close its own unanswered message, or only you? Blocks whether a row can
   leave your list without you.

Defaults adopted, yours to overturn: your own deliveries carry no receipt state; agy
without the MCP server shows as unacknowledged.
