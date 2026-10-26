> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# 03 — Deliver: verification

Verifier: Fable 5.1 at high, named by Brian 2026-10-09.
Artifact: `03-deliver-proposal.md` as read 2026-10-09. Scope ruled by Brian: vendor docs,
this repository, agy `hooks.md` on disk; no process, socket, transcript, settings or
bundle inspection; nothing typed. Sources: Claude `cross-session-messaging.md` and
`hooks.md` (full, fetched 2026-10-09), Codex `hooks.md` and `app-server.md` (same date),
agy `~/.gemini/antigravity-cli/builtin/skills/agy-customizations/docs/hooks.md`,
`codex_supervisor.py` on main and the `agent-submission-receipts` branch, local-mail
`hooks/stop.py`, ADRs 0014–0018, verification 05, open ticket M10.

## Claims

1. **Socket: idle → new turn; mid-turn → between tool calls.** Confirmed (cross-session
   doc L59). Scripts and hooks posting to a session's socket are a documented use (L237);
   socket path exported before SessionStart (L245); `-p` binds a socket (L222); complete
   line within 30 s (L256).
2. **Socket wire format** `{"type":"user","message":{...}}`. Could not check: the doc
   documents only the auth line (L251); the second line is the proposer's bundle reading,
   which is outside my scope. Live test needed (proposal §3.1).
3. **Hold rule.** Confirmed with one gap. A sender asserting no class is delivered to a
   prompting receiver and held by a bypassing one (L203–206, L263); `auto`, `acceptEdits`,
   `dontAsk` count as prompting (L203). Gap: "plan mode counts as bypassing in
   interactive terminal sessions with bypass permissions available" (L203), so a Claude
   pane in plan mode holds a daemon-posted ping for `dialogExpiry` (5 min, L212) then
   drops it. Bypass is moot (ADR 0018); plan mode is not, and the mode gate must treat
   `plan` as holding.
4. **asyncRewake exit 2 wakes an idle session.** Confirmed as documented (hooks L459,
   L3978). Timeout is enforced on asyncRewake (L3906); the default command timeout is
   600 s (L426), so a 30-minute watcher needs an explicit `timeout`. A cancelled hook's
   output is discarded (L845), so a timeout is silent, not a wake. Not documented: that
   the field is honoured on the `Stop` event specifically, and what happens to a running
   watcher across `/clear` (L1119 covers only SessionStart). Live test needed, as ADR 0018
   already says.
5. **Stop `additionalContext` is a passive pointer, unlike `decision:block`.** Refuted.
   Doc: `additionalContext` on Stop "keeps the conversation going through the same loop
   protections as `decision: "block"`, namely the `stop_hook_active` input and the
   8-consecutive-continuation cap"; only the transcript label differs (L2659–2668). The
   cap "resets each time Claude calls a tool" (L2589). So every Claude Stop with unread
   mail is a forced continuation, not a deferrable nudge, and a `read` tool call resets
   the cap for a session that reads but never acknowledges. Codex is the same: Stop
   `decision:block` "creates a new continuation prompt that acts as a new user prompt"
   (Codex hooks L1085–1091). Falsifier: one unacknowledged message, one session told to
   stop; count continuations over ten minutes.
6. **Claude mid-turn injection** via UserPromptSubmit/PostToolUse `additionalContext`.
   Confirmed (L1023, L1378, L2072). UserPromptSubmit also fires on a cross-session
   message (L1336), so a socket ping is itself hookable.
7. **Codex: no hook wakes an idle session.** Confirmed: "Finishing a background hook
   doesn't start a new turn" (Codex hooks L625–626); the only continuation is a
   synchronous Stop block. PostToolUse/UserPromptSubmit `additionalContext`: confirmed
   (L918–927, L1004–1010); default context budget 2,500 tokens (L555). Codex has an
   `Interrupt` hook event (L1099) fired on an interrupted main-thread turn; the proposal
   does not use it, and it is the vendor-native confirmation that an interrupt landed.
8. **App-server.** `turn/steer` needs `expectedTurnId` and fails with no active turn:
   confirmed (L1042–1045). "turn/start on a TUI-owned thread undocumented": confirmed
   within this page (it documents `codex --remote` against an app-server, not a second
   client driving a TUI's thread). "Experimental and unsupported": confirmed (L54–55,
   L64). The silent probe has a documented cause: the unix-socket listener uses
   WebSocket framing (L66), so raw JSON lines get no reply.
9. **agy.** Stop `{"decision":"continue","reason":...}` with reason "injected as a system
   message if continuing": confirmed (hooks.md L315–322, not L300–330). PreInvocation
   `injectSteps:[{"userMessage":...}]` before each model call: confirmed (L257–269).
   Hooks are synchronous only (L328), so no idle wake. No SessionStart: confirmed (L74–83).
10. **Local-code observations.** `_preflight_pane`, `_confirm_paste`, `_submitted`,
    `_approval_is_pending` on 12 lines, `_composer_text`: confirmed on main (L1632,
    L1724, L1749, L1645, L1490). Receipts worktree: per-attempt buffer `codex-send-<id>`
    at L1817 confirmed; the per-pane send `flock` is at L1027, not L963 (L963 locks the
    monitor socket). Local-mail `stop.py` returns `decision:block`: confirmed (L39).
11. **Claude title and composer.** Refuted by verification 05 claim 3: titles never
    changed between busy, idle and dialog panes; all begin `✳`. The `✳` idle test passes
    on every Claude pane and the confirmation "title flips to `◐`/`◑`" never fires; only
    " esc to interrupt" (labelled I) can confirm. The composer marker is `❯` (05 claim
    10), left as A. The title-prefix vendor guard is the weak-liveness finding ADR 0014
    orders fixed (pgrp → `claude` pid → socket).
12. **Pane resolution against ADR 0014.** Contradiction. The proposal takes the pane id
    from the Record and explicitly never looks at the caller's window; ADR 0014 requires
    the pane to be in the caller's window and its live identity to match the edge, with
    refusal naming both ids. Neither guard is in §2.3.
13. **Adapter order against ADR 0018.** Divergence. The ruling is socket ping for a
    Claude sender, hook listener for any other sender, tmux fallback. The proposal makes
    the socket primary for every sender. The doc allows it (claim 1), but it is not the
    ruled order; amend 0018 or reorder.
14. **Interrupt verb.** ADR 0015 adds `interrupt` through the same actuator; the
    proposal's actuator has only `kind ∈ {command, mail}` and an Enter-only submission.
    The shape is needed now (Escape per vendor, same guards, confirmation by Codex
    `Interrupt` hook or screen). Its semantics are open ticket M10 (idle pane has nothing
    to interrupt); I did not resolve it.
15. **ADR 0016.** Consistent: `deferred` on busy, retried only on the next Stop/idle.
    But claim 5 means a session under Stop continuation is never idle by 0016's
    predicate, so the ladder clocks never start for exactly the sessions ignoring mail.

## Strongest failure in Brian's environment

Claims 5 and 15 together. Every Claude and Codex pane carries a Stop hook that injects
unread pointers at every Stop. On both vendors that is a forced continuation with no
grace, repeated until acknowledgement, and the Claude cap resets on the `read` tool
call: a token-burning loop on every session holding one unacknowledged item, which also
keeps those sessions "busy" so ADR 0016's clocks never run and the ladder never reaches
Brian. The fix fits the proposal's frame: the Stop hook injects once per message
(ADR 0009) and is otherwise silent; the wake path owns later rungs under ADR 0017.

## What survives

Pointer-not-body; attempt rows committed before pane input; `unknown` with no further
keystrokes; the Codex adapter (Stop block and no idle wake both confirmed); agy hook
shapes; the socket as a wake with the plan-mode caveat; asyncRewake pending ADR 0018's
live test; the app-server rejection; the failure-mode table; §3 tests 1–8, with test 7
already answered negatively by verification 05.

## Live tests needed

Socket second-line format and non-child delivery to a prompting receiver; asyncRewake
on Stop, exit 2 from idle, across `/clear`, with duplicate watchers from successive Stops
(the proposal has no single-instance lock); Claude " esc to interrupt" as the only
busy signal; Codex `Interrupt` hook as interrupt confirmation; agy runtime.

## Questions for Brian

None new; M10 and proposal Q2–Q3 stand.
