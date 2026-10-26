> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 04 Acknowledge: verification

Verifier: Claude Fable 5.1 at high, named by Brian 2026-10-09. Scope: web vendor docs,
this repository, `~/.gemini/antigravity-cli/builtin/`; no session files, processes, or
panes. Labels: **C** confirmed, **R** refuted, **U** could not check. Docs read
2026-10-09: `code.claude.com/docs/en/hooks` (chars 0 to 200,000 of 258,323),
`code.claude.com/docs/en/mcp` (0 to 100,000), `learn.chatgpt.com/docs/hooks`,
`learn.chatgpt.com/docs/extend/mcp?surface=cli`, agy `docs/hooks.md` on disk.

## Claims against sources

1. **Today's plugin breaks property 4 twice (§1).** C. `stop.py` calls
   `store.notify()`; `notify` returns `_inbox(..., only_new=True)` then sets every `new`
   delivery to `notified`, and the only-new digest never lists `notified` rows, so the
   Stop hook shows an item once. `pull` sets `state='read'` as a side effect
   (`local_mail_store.py` lines 296 to 346). The "Codex turn" docstring in `stop.py`
   is stale; its `hooks.json` is Claude's.

2. **Claude has an `mcp_tool` hook type with `${path}` substitution from hook input
   (§2 premise correction).** C, verbatim: "call a tool on a configured MCP server";
   "String values support `${path}` substitution from the hook's JSON input". Whether
   such a call is recorded in the transcript: U, the page is silent. Substitution comes
   only from hook input, so an `mcp_tool` hook cannot chain `read` then `ack`, but a
   command hook can drive the stdio server and do both; only the audit guards against
   a hook, as the proposal says.

3. **Stop returns `decision: block` once per turn via `stop_hook_active`, on both
   vendors.** C. Claude: `stop_hook_active` "is `true` when Claude Code is already
   continuing as a result of a stop hook"; `decision: "block"` "prevents Claude from
   stopping"; after eight consecutive continuations Claude "overrides the next block and
   ends the turn". Codex: `stop_hook_active` "Whether this turn was already continued by
   `Stop`"; block "creates a new continuation prompt". Stop fires only "when the main
   Claude Code agent has finished responding"; nothing wakes an idle session, hence
   rung 3. agy's Stop has no `stop_hook_active`; nothing is claimed for it.

4. **SessionStart carries `compact` and `clear` and its stdout enters context.**
   C on Claude (`startup`, `resume`, `clear`, `compact`, `fork` since 2.1.214; stdout
   is "added to Claude's context"). C on Codex for values, injection ("extra developer
   context"), and compaction timing: "after Codex compacts a root session, matching
   SessionStart hooks run before the next model request". Timing for `clear`
   on Codex: U; ADR 0007 observed no event at the instant of a clear on 0.157.0. The §7
   fallback is the right hedge. Claude's `fork` source is absent from the `ctx` rule;
   Identity owns it.

5. **MCP server lifecycle across `/clear`.** Claude: C by implication, the hooks page
   says SessionStart at launch fires "before the session's MCP servers are available to
   hooks" but when it "fires again later in the session, after `/clear` or a
   compaction, its `mcp_tool` hooks run", so the stdio server persists across both.
   This settles the §7 worry the way it feared: the server's startup environment goes
   stale, so address and `ctx` must be resolved per call from the Record (by pane,
   ADR 0019 b). Codex: U; neither page says.

6. **Codex `approval_mode` values `auto | prompt | writes | approve`.** C that the
   values exist (`default_tools_approval_mode`, `tools.<tool>.approval_mode`); only
   `writes` is defined. The never-prompt value remains undocumented.

7. **Codex "Subagent hooks use the parent session id".** C, verbatim. Claude's
   SubagentStop example implies the same (`agent_transcript_path` nested under the
   parent's id). See failure below.

8. **Codex code-mode `exec` wrapping; Claude `tool_use` records for MCP calls; the
   version numbers.** U under the scope limit.

## Claims against the rulings made since

- **ADR 0015 (`withdrawn`).** R as written. The model has per-delivery `closed_at,
  closed_by` and no reason; ADR 0015 requires a message-level terminal fact with actor
  and reason, a tombstone removing the obligation from every list, writable only by
  sender or Brian. §2's "only answer, acknowledge, or close removes a row" needs
  withdraw. Q3 is answered.
- **ADR 0015 (ladder).** R. "Give up" is no longer stop-and-list: nudge, guarded
  interrupt through the actuator (function 5), then `stuck`, listed only after the
  interrupt ran or was refused, with the reason. Q1 is answered; delete it. Flagged,
  not resolved: ADR 0016 runs the clocks only while the supervisee is idle, and an
  interrupt of an idle pane has nothing to interrupt. For the dispatcher to raise.
- **ADR 0016 (block pause).** R. `claim_due` runs on wall time ("last surfaced over
  R ago"; `stuck` "older than T1"), and failure mode "ack held by a permission prompt:
  `stuck` after N" advances the ladder inside a block. ADR 0016 forbids both ("neither
  may use elapsed wall time alone"). `delivery_context` has no ledger of unblocked
  idle time, so the sketched SQL cannot be written without function 5's idle predicate
  and a per-delivery accumulator of paused clocks.
- **ADR 0017 (numbers).** Partly C: N=2, R=10 min, T1=30 min, T2=2 h match. Missing:
  the 120 s idle grace and the interrupt after the second gap. Q2 is answered. One
  conflation: the Stop-hook digest fires at zero idle time, so under ADR 0017 it cannot
  be a nudge; under ADR 0018 it is the ping. The proposal counts it in N. Separate
  ping from nudge, or the first nudge breaks the grace.
- **ADR 0018 (ping, pull body).** C on shape: digests carry ids and subjects, never
  bodies; `read` is the pull. Not covered: the Claude socket ping (a `SendMessage`
  arrives as a prompt and runs UserPromptSubmit hooks, documented) and the Stop-launched
  listener; `claim_due` must gate those channels too.
- **ADR 0019 (identity).** R on one line: §4 asks for "a separate address for a
  sub-agent (property 12)"; ADR 0019 (a) rules sub-agents send as their parent with a
  `via` stamp. `whoami` (c) and the read-code scheme are different acts; no collision.

## Strongest reason it fails in Brian's environment

A Claude or Codex session that delegates "check the mail" to a sub-agent receives a
valid receipt without the body ever entering the supervisee's own context. The
sub-agent calls `read` and `ack` on the same server in the same `ctx`, so the code is
valid by the proposal's own definition, and on both vendors the hook-visible session id
is the parent's (claim 7); ADR 0019 (a) makes this the normal addressing path. The
protected assumption ("the recipient's live context having had the item") is not
enforced by the mechanism, and the audit cannot see it unless it also walks sub-agent
transcripts (Claude: `agent_transcript_path` under `<session>/subagents/`). Falsifier:
live, per vendor, delegate read-plus-ack to a sub-agent and check whether the parent's
transcript ever holds the body. A design gap, not a source error; it needs a ruling on
whether a sub-agent's receipt counts, or a server-side refusal the server cannot make
today because it never sees `agent_id`.

## What survives

Surfaced, read, and acknowledged kept apart; `acked_at` writable only by `ack`/`reply`;
the per-context code; derived state and derived needs-Brian view; `claim_due` as the
single surfacer; no-write resurfacing at context start; `held_until_ctx` for
future-self mail; the rejected alternatives. All three Questions for Brian are answered
by ADRs 0015 and 0017.

## Live tests needed

1. Codex stdio MCP server survival across `/clear` and compaction.
2. Whether a hook-driven `ack` leaves a transcript record on Claude; whether Codex
   records a code-mode `exec` MCP call as `McpToolCall`.
3. The sub-agent receipt hole, on both vendors.
4. Codex SessionStart timing on `clear` for 0.160 and later.
5. The Codex `approval_mode` value that never prompts.
