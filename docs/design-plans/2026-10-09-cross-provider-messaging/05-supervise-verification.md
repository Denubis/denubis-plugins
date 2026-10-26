> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 05 — Supervise: verification

Verifier: Fable 5.1 at high, named by Brian 2026-10-09 ("High effort for verifier").
Artifact: `05-supervise-proposal.md` as read 2026-10-09 (1,906 words by `wc -w`; the brief
caps proposals at 1,800). Sources opened: `codex_supervisor.py` (2,850 lines),
`supervising-codex/SKILL.md`, ADRs 0007/0009/0010, the August design (properties 1-14,
DR4, DR11-13), Claude hooks doc (code.claude.com, all 258k chars), Codex hooks doc
(learn.chatgpt.com), agy `hooks.md` (local, 1.3.1), agent-bridge `notify.rs` at the
pinned commit, `tmux list-panes -a`, read-only `capture-pane` of %60/%71/%12, `ps`,
`/proc`, `ss -xlp`. Nothing was typed into any pane.

## Claims

1. **Versions** (codex 0.160.1, Claude 2.1.295, agy 1.3.1): confirmed by running each.
2. **Supervisor hard-codes one direction; same-window uniqueness; `send_message`
   1769-1795; `advance` dedup; 30 % floor; `/proc` locks**: confirmed
   (`discover_codex_pane` 764-790, `joined_pane` 1195, `send_message` 1769,
   `advance` 637, `CONTEXT_FLOOR_PERCENT = 30`, `held_sessions` 2036).
3. **How Claude panes present in tmux**: confirmed with a correction. `pane_current_command`
   is `bash` on seven main-session panes and `fish` on nine teammate panes; every title
   begins `✳`. The title did not change between a busy pane (%12, screen
   `✶ Spinning… 16m 24s`) and an idle one (%71, `✻ Churned … done 12:06 pm`), nor on %60
   while it held a permission dialog. So the title carries no busy/idle/dialog signal; the
   screen's spinner line does. This settles the proposal's could-not-check item 1.
4. **"Claude's foreground process group is a statusline `bash`"**: refuted. On %60 the
   foreground group (tpgid 1760716) is `claude-wrapper.sh` from denubis-plan-and-execute,
   and the `claude` process 1760741 sits in the same group. Consequence: the existing
   pgrp walk (`resolve_foreground_process_group` + `/proc`) does reach the Claude process.
   Moreover every Claude process listens on `/run/user/1000/cc-socks/<pid>.sock` (observed
   via `ss -xlp`, ten processes), and %60's argv carries `--session-id f919e797-…`. A
   live, hook-independent identity probe for Claude therefore exists; the proposal's
   "not applicable" cell reasons from a false premise. What is true: Claude holds no
   session file open, so a *session uuid* is not readable from fds alone.
5. **Claude hooks doc**: `Stop` carries `background_tasks` and `stop_hook_active`;
   `PermissionRequest` carries `permission_suggestions`, no id, no `turn_id`;
   `SessionStart.source` includes `fork`; `permission_prompt` after "about six seconds"
   (suppressed if a PermissionRequest hook answers first); `idle_prompt` "about 60 seconds
   after Claude finishes responding", not while a background subagent runs and not while
   waiting on a usage-limit reset; `UserPromptSubmit` fires for cross-session messages and
   subagent report-backs. All confirmed against the doc text.
6. **`agent_needs_input` as the AskUserQuestion wake-up**: refuted. The doc defines it as a
   *background* session waiting on input while agent view is open, a teammate's terminal
   setup question, or the auto-mode billing notice. No notification type is documented
   for a foreground `AskUserQuestion`. Consequence: a Claude supervisee parked on
   AskUserQuestion has no hook wake-up in this design; only a screen read sees it.
7. **Codex hooks doc**: `PermissionRequest` {`turn_id`,`tool_name`,`tool_input`}, no
   request id; `Stop` {`turn_id`,`stop_hook_active`,`last_assistant_message`};
   `UserPromptSubmit` exists; no idle event; `SessionStart.source` ∈
   startup/resume/clear/compact. Confirmed. ADR 0007's "does not fire at clear time"
   confirmed as the ADR's own observation.
8. **agy `Stop` {`terminationReason`,`fullyIdle`,`error`}**: confirmed in local
   `hooks.md` lines 299-307. Minor: `PreToolUse` decisions are allow/deny/ask/force_ask,
   not "ask/deny only"; immaterial to the claim that agy has no approval-pending event.
9. **`claude --name`**: exists on 2.1.295 (`-n, --name <name>  Set a display name`).
   Stability across clear/compact/resume not checked (Identity's concern).
10. **agent-bridge "79 % false positives"**: confirmed in `notify.rs` (19/24 on a working
    coordinator pane), but it measures *dialog* scraping, not idleness. The proposal cites
    it to reject screen-scraped idleness while keeping the same dialog patterns
    (`Do you want to` / `Esc to cancel`) for Claude `approve`. The evidence cuts against
    the kept path, not the rejected one. Observed on %60 now: Claude's dialog is
    `Do you want to proceed?` / `❯ 1. Yes` / `2. No` / `Esc to cancel · Tab to amend`;
    the composer prompt is `❯`, not `>`.
11. **Minted request id** `sha256(vendor, session_id, turn_id?, tool_name, canonical
    tool_input)`: unsupported as an *exact* identity. Claude gives no `turn_id`, so two
    requests for the same command in one session hash identically; within a Codex turn
    a retried command does too. With the proposed uniqueness on
    `(supervisee, kind, correlation_key)` the second request is swallowed by announce-once
    and never surfaces, and an approval minted for the first clears the second because
    "the same command on screen now" is exactly the colliding case. Violates property 4
    (one occurrence, one keypress) and property 7 (exact request). Falsifier: have a Claude
    supervisee run the identical Bash command in two prompts and check the Record holds
    two needs-attention rows. Fix is Authority's: add a hook-arrival sequence or the
    PermissionRequest timestamp to the key.
12. **Citation**: "property 3's guarded tmux actuator" is the brief's function 3; design
    property 3 is agent continuity. Harmless mislabel.
13. **DR4, DR11, DR12, DR13, properties 6, 7, 13, 14**: the proposal's readings match the
    text. `supervision_edge.kind='approve-mandate'` carries none of DR12's scope columns
    (request class, consequence bounds, assignment); Authority (6) must own that.
14. **Same-window rule replacement**: the current rule is as described. The replacement
    (edge + `match_pane` + `live_identity`) is sound for Codex because `/proc` locks are a
    live probe. For Claude the proposal's `live_identity` is "hook-written state keyed by
    session_id", compared with the Record's current session id for the address: the
    Record is checked against itself. Falsifier 4 (kill and relaunch in the same pane)
    passes only if the replacement enrols via SessionStart; a replacement with hooks
    disabled, a bare shell that kept the `✳` title, or an agy would pass `match_pane`
    and never mismatch. The probe in claim 4 (pgrp → claude pid → `cc-socks/<pid>.sock`)
    closes this and the proposal does not use it.

## Strongest failure in Brian's environment

Claude liveness and identity are hook-derived only (claims 4, 14), on a premise the
live processes refute. In Brian's layout (~20 windows, nine teammate panes in @24 alone,
panes replaced by wrappers and sub-sessions) the edge's `pane_id` goes stale often; when
it does, the only Claude-side guard before `paste-buffer` is "shell command + `✳` title",
which every pane in @24 satisfies. Combined with claim 11, the design can both type into
a replaced pane and silently drop a repeated approval request, the two things property 13
exists to prevent.

## What survives

The adapter split and `UNKNOWN`/`None`-refuse rule; roles as Record rows; announce-once
as a uniqueness constraint (with a non-colliding key); the hook event tables for all
three vendors (corrected at claim 6); the idle predicate's shape, since `idle_prompt`,
`background_tasks`, `fullyIdle` and `UserPromptSubmit`-on-cross-session-message are all
documented as the proposal says; the Codex side unchanged; the rejection of a daemon and
of app-server/socket as universal path; Q1-Q3 for Brian, with one addition to Q2: a
cross-window edge means the typed text lands where Brian is not looking, which the
same-window rule gave him for free.

## Could not check

- Whether `PermissionRequest` fires for an in-process subagent's prompt (the %60 dialog
  is a subagent's) and which `session_id` it carries.
- Whether tmux keeps a dead Claude's `✳` title until the shell redraws it.
- Codex `--approve` on 0.160; agy's interactive TUI; `claude --name` persistence.
- "Claude box pushed off by the agents list on %60": the pane showed a dialog instead.

## Questions for Brian

None beyond the proposal's Q1-Q3; the Q2 consequence above is for that decision.
