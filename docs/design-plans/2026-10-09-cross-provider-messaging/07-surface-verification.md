> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Function 7, Human surface: verification (verify-7-surface, Fable high, 2026-10-09)

Labels: O = observed by me today, I = inferred, A = assumed. Nothing was typed into any
session.

## Verdict

**Does not hold as written on Claude; survives with one semantic change.** The
load-bearing claim ("approval returned through a blocking `PermissionRequest` hook without
the pane ever being typed into") is half right: a hook *can* block for up to 600 s and its
late `allow`/`deny` resolves the request, but Claude Code draws its own permission dialog
in the pane **immediately**, concurrently with the hook, and does not cancel the hook when
Brian answers that dialog. The proposal's `expired` state (dialog appears only after
timeout) and its "no race" framing are therefore wrong; the race is the normal case.

## Claim-by-claim

1. **Claude `PermissionRequest` hook may block and return a decision; default timeout
   600 s.** *Confirmed (doc).* code.claude.com/docs/en/hooks: `timeout` "Defaults: 600 for
   `command`"; decision via `hookSpecificOutput.decision.behavior` allow/deny with
   `message` on deny; "Only the `decision` object can grant or deny the request"; a hook
   "that reaches its `timeout`" has its output discarded and "renders no decision" (O).
   Also: "a hook returning `allow` doesn't override a matching deny rule" (O), so a
   surface `a` cannot override `settings.json` deny rules.

2. **The pane is never touched / the dialog appears only on timeout (§5).** *Refuted
   for Claude.* The doc states concurrency only for `--permission-prompt-tool`/`canUseTool`
   hosts ("hooks run alongside your host, and whichever decides first applies") and is
   silent for the terminal (O). Three independent field reports fill the gap:
   anthropics/claude-code#79651 (v2.1.211, 2026-07-21): "The local dialog is shown
   concurrently with the running hook (first responder wins)" and "When the user answers
   the local dialog, the still-running hook is not cancelled (observed alive 50+ seconds
   after the dialog was answered, until it timed out on its own)"; #12176 (v2.0.50,
   closed, no fix linked): "PermissionRequest hooks execute asynchronously in parallel with
   permission dialogs being displayed"; yooz-labs/remi#1126: "Claude's native dialog
   renders immediately while remi holds the `PermissionRequest` hook ... the held hook's
   later `allow`/`deny` resolves that dialog" (O, all three). Consequences: (a) the pane
   shows a dialog from t=0, so the existing `Notification` hook (`notify-agent.sh Claude`,
   `~/.claude/settings.json`, O) fires ~6 s later as it does today, and any function 5
   screen observation will classify the pane as "approval pending" at once; (b) a local
   answer leaves the hook, and so the Record row, pending until timeout: "resolved when
   the pane dialog is answered locally" (§4) has no named mechanism, and the hook process
   itself cannot observe it (#79651). A `PostToolUse` or `PermissionDenied` event is the
   only candidate; untested. Only a live test on 2.1.295 (installed, O) settles whether
   this is still current.

3. **Codex `PermissionRequest` supports the same decision shape; may block for
   minutes.** *Confirmed shape, timeout default; dialog behaviour unknown.*
   learn.chatgpt.com/docs/hooks: runs "when Codex is about to ask for approval, such as a
   shell escalation or managed-network approval"; "If `timeout` is omitted, Codex uses
   `600` seconds"; "By default, Codex waits for a command hook to finish before
   continuing"; matching hooks are "launched concurrently"; "any `deny` wins ... If no
   matching hook decides, Codex uses the normal approval flow"; `updatedInput`,
   `updatedPermissions`, `interrupt` "fail closed today" (O). The doc says nothing about
   whether the prompt is drawn while a synchronous hook runs, and no field report was
   found; the `statusMessage` field ("message shown while the hook runs") suggests a
   status line rather than a dialog (I). The proposal's `hooks.md:129, 420, 519` line
   cites were not checked; the raw `hooks.md` loads but line numbers were not counted.

4. **Contradiction note: "Codex approval not hookable" (§5).** *Refuted as stated.* The
   approver's sentence ("`PermissionRequest` only runs when Codex independently needs
   approval", O) means a hook cannot *force* a prompt (no early `ask`), not that approvals
   are unhookable. Every approval Codex itself raises fires `PermissionRequest`, and
   `~/.codex/hooks.json` already registers two such hooks (supervisor and
   `codex_approver.py`, both `timeout: 5`, O). The real residual gaps: the doc names only
   two example triggers ("such as"), so `apply_patch` and MCP approvals are unverified; a
   timed-out hook falls open to the normal prompt; a third, 600 s hook runs beside the 5 s
   ones (concurrent launch, O doc; whether Codex waits for the slowest is unstated).
   `agy`: no `PermissionRequest` (brief, not re-checked).

5. **Textual `>=8.2.8` is current and available locally.** *Confirmed.* PyPI JSON: latest
   8.2.8, uploaded 2026-06-30, `requires_python >=3.9,<4.0`; uv archive holds wheels
   8.0.0, 8.0.2, 8.2.5, 8.2.8; `permission-notifier-manager/.venv` has textual 8.2.8
   installed (O), stronger than the proposal's "pin is the only evidence". psycopg not
   found in the cache by name (single search; not asserted absent).

6. **Separate tmux session on a side monitor.** *Confirmed in principle.* One server
   (`/tmp/tmux-1000/default`), one session `main`, 21 windows, client 312x62, tmux 3.7c,
   byobu 7.20, Ghostty installed (O). A second session on the same server is permitted;
   it inherits byobu's global status options (cosmetic, I). Actual use there is A.

7. **`#()` crashed tmux.** *Confirmed*, `~/.byobu/tmux.conf:64-65` (proposal says 66-67).

8. **Prior attention manager claims.** *Confirmed.* `README.md:50` has "first paint
   comes from committed SQLite state"; `tests/adapters/test_codex.py:192` asserts
   `SUPPORTED_VERSION == "0.144.6"` (adapter lives under `src/`, O). Codex here is 0.160.1.

9. **`pane.tsx` exists** under `/tmp/claude-1000/bundled-skills/2.1.295/*/plugin-authoring/examples/`
   (O); contents not read.

10. **ADR 0008/0009 and the August section.** *Consistent.* Ticket leaves when the
    recipient agent records the ADR and removes the heading (0008); surface never nudges
    (0009). The August design's queue explicitly includes "vendor approval dialogs" and
    lists five secretary actions including "acknowledge seeing ... without settling it"
    and "mark ordinary mail handled" (lines 1062-1068, O); the proposal drops both. A
    deliberate narrowing, not a contradiction, but unstated.

11. **Internal consistency.** Test 3 ("fails if the dialog has to be touched") does not
    falsify the mechanism: the dialog is visible regardless; it must assert the dialog
    *resolves* without input. §5's `expired` row and §4's `resolved` transition both
    presume a dialog that appears late.

## Strongest failure in Brian's environment

Every Claude approval already draws its dialog and pings `notify-agent.sh` the moment it
arises. Adding a 600 s blocking hook changes nothing visible in the pane and creates a
second answer path: Brian answers in the pane (habit), the hook lives on up to ten
minutes, and the surface shows a stale "needs Brian" row that no event retires unless
function 6 wires `PostToolUse`/`PermissionDenied` to it. Under ADR 0009's "items leave
only when answered" that row is a false obligation, exactly what property 2 forbids.

## What survives

A Record-projected TUI with keyed, idempotent decision rows; `a`/`d` returning the
decision through the blocking hook (the hook's late allow does resolve the dialog, per
remi#1126); the Codex path with the same shape; ticket flow under ADR 0008; Textual
8.2.8 and the side-monitor session. Surviving design must treat "dialog visible in pane"
as the steady state, add a local-answer reconcile, and rename `expired` to
"hook timed out, pane dialog still open".

## Could not check

- Live Claude 2.1.295 behaviour (dialog timing, whether a local answer kills the hook).
- Codex 0.160.1: whether the prompt is drawn during a synchronous hook; which approval
  kinds fire the event; wait-for-slowest semantics across concurrent hooks.
- `pane.tsx` contents; the `hooks.md` line numbers cited; psycopg in the uv cache.
