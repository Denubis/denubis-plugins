> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Verification 2: Identity

Verifier: Claude Fable 5.1, high (named by Brian 2026-10-09). Read-only; scope ruled by
Brian: vendor docs, this repository, on-disk agy docs; no process, socket, `/proc`,
transcript, settings, or pane inspection. Sources read 2026-10-09: Claude Code docs
(hooks, cli-reference, sessions, env-vars, cross-session-messaging, agent-teams,
claude-directory), Codex docs (hooks, developer-commands, config-reference, app-server),
agy `hooks.md`, ADRs 0007, 0011, 0018, 0019, the proposal, the August properties.

## Claims checked

**C1. Claude `/clear` changes `session_id`; compact and resume keep it; fork is new.**
Confirmed: `CLAUDE_CODE_SESSION_ID` "is updated on `/clear`"; SessionEnd `reason: clear`;
SessionStart `source` is `startup|resume|clear|compact|fork`.

**C2. A Claude SessionStart hook process gets pane and new session id together.**
Confirmed for the id, inferred for the pane. Documented: payload `session_id`;
`CLAUDE_CODE_SESSION_ID` in hook subprocesses, matching the payload; `CLAUDE_PID` in hook
subprocesses (2.1.214+). Not documented: `TMUX_PANE`; it reaches the hook only by ordinary
environment inheritance, which the proposal observed in PreToolUse, not SessionStart.
One correction: on `--continue` or `--resume` without an explicit id the env variable
"may receive the initial startup ID instead", so enrolment must read the payload, never
the env. The proposal lists both without ranking them.

**C3. `claude --name` exists and persists.** Confirmed, and it refutes the proposal's
"could not check: whether the native name survives resume". `--name`/`-n` and `/rename`
set a name; `claude --resume <name>` resumes by it; `/clear` with no argument "keeps a
name you set with `--name` or `/rename`". Limit: a live-session collision renames the
newcomer to a two-word-suffix variant (2.1.232+). So the name is a documented, clear- and
resume-stable *alias source*, not an address. The proposal's rejection reason
("PID-keyed") describes the registry file, not the name.

**C4. `agent_id` in sub-agent hook payloads (proposal: A).** Now documented: "Present
only when the hook fires inside a subagent call." Now documented.

**C5. Codex hook `session_id` for a sub-agent is the parent's.** Confirmed:
"Subagent hooks use the parent session id." Supports ADR 0019(a) and the `via` stamp.
SessionStart's row is "When a session or subagent starts" with no sub-agent `source`,
so a binding hook refires with the parent id; idempotent rule 1 absorbs that.

**C6. Codex docs say when SessionStart fires relative to `/clear`.** Refuted. The only
timing sentence is for compaction: "After Codex compacts a root session, SessionStart
hooks that match `source: "compact"` run before the next model request." ADR 0019(b)
generalises this to the clear case ("Codex's hooks documentation says it fires before the
next model request"); the doc does not say that for `clear`. ADR 0007's observation (no event at the instant of clear on 0.157.0) is the only
evidence. `/clear` is documented as "starts a fresh chat in
the same CLI session"; only `/fork` is documented as giving "a fresh ID". A new thread id
on `/clear` rests on ADR 0007's `e2e.log`.

**C7. The Codex SessionStart hook runs in the pane's environment and sees `TMUX_PANE`
(ADR 0019(b)).** Not supported by the docs and contradicted by the proposal's own
observation. The hooks doc states only "Commands run with the session `cwd` as their
working directory" and lists no inherited variables. The proposal observed (section 5)
that hand-launched panes hold no session lock and one `codex app-server` process with no
tty and no `TMUX_PANE` holds five locks. Third-party reports on 0.160 agree
(asserted, not vendor-documented): the TUI attaches to a shared per-machine daemon when
`$CODEX_HOME/app-server-control/app-server-control.sock` answers, and the daemon runs
every session's hooks with the environment of whichever session started it
(sean-brydon/berthd#8, tarakanof/Ember#263, openai/codex#51098). If that holds here, a hand-launched Codex's SessionStart hook sees
either no `TMUX_PANE` or the pane of the first session that started the daemon, and
binds the new thread to the wrong pane silently. The config reference shows no `daemon_auto_start`; `--no-daemon` appears only in a
third-party PR. Unverified.

**C8. `CODEX_THREAD_ID` in tool calls.** Not in the official environment reference;
source mirrors show commit #10096 injecting it "when applicable". Proposal observed it
on 0.153–0.156 only. Under the daemon it is still the thread's own (inference);
`TMUX_PANE` in that shell is the open question (C7).

**C9. `/status` shows the thread id (ladder step 4).** Not supported by the current
docs: `/status` is documented as model, approval policy, writable roots, token usage;
"session id" is documented only as a `/statusline` footer item. ADR 0007 read the panel
on 0.157.0. Live test needed on the installed version; the statusline item is a
documented alternative.

**C10. `~/.claude/sessions/<pid>.json` (ladder step 3).** Undocumented, as the proposal
says: absent from the `.claude` directory page; a second search finds only third-party
readers. Step 3 rests on an unstable file.

**C11. A Claude teammate is a full session with its own pane and session id.**
Confirmed: "Each teammate is a full, independent Claude Code session"; team config
"holds ... session IDs and tmux pane IDs". `--parent-session-id` is undocumented.

**C12. agy `PreInvocation` carries `conversationId`.** Confirmed (`hooks.md` line 146);
no SessionStart event (lines 72–79).

**C13. Enrolment ladder under ADR 0019.** Rules 1, 2, 4, 5 and the Claude branch of
rule 3 are consistent with 0019 (same hook route for Claude). The Codex branch of rule 3
(process triple of "the interactive vendor process") is unavailable under the daemon, as
the proposal concedes, and 0019(b) replaces it with pane binding from the hook's
environment, which C7 undermines. The ladder has no Codex step that works when the hook
runs in the daemon; 0019's own fallback ("unresolved rather than a fresh address") is
what remains. Rulings 0011 and 0018 do not touch identity.

**C14. Property 12's card acknowledgement.** Replaced by 0019(c); proposal matches.

**C15. Version drift.** Codex SessionEnd is now documented as archive, delete, normal
close, or 30 minutes idle; ADR 0007 saw it 61 s after a clear on 0.157.0. Codex hook
timing does not carry across versions.

## Strongest failure in Brian's environment

Hand-launched Codex panes. The proposal observed on 2026-10-09 that they run in a shared
app-server daemon with no tty and no `TMUX_PANE`. ADR 0019(b) assumes the SessionStart
hook "runs inside the pane's environment"; nothing in the Codex docs says so, and the
daemon topology says the hook process is the daemon. Result: after a hand-typed `/clear`
the new thread cannot be bound to its pane from the hook, and `who --pane` steps 2–3
fail too. Only the spawned path (rule 4, `AGENT_EXPECT`) and whatever makes a pane own
its session (the proposal infers the `-s … -c model_catalog_json=…` flags) work.
Consequence: identity across clear for hand-launched Codex is unresolved, and Deliver
has no pane evidence for them.

## What survives

The address scheme, the four tables, rules 1, 2, 4 and 5, the Claude path end to end
(with payload-not-env for the id), sub-agents sending as parent with `via`, `whoami` as
acknowledgement, the alias scheme (now with `--name` as a documented vendor stem that
survives clear and resume), and the agy conversation-id enrolment.

## Live tests needed

1. Hand-launched Codex, installed version: a SessionStart hook and a shell tool call
   that log `source`, `session_id`, `PPID`, `TMUX_PANE`, `CODEX_THREAD_ID` before and
   after `/clear` (C6, C7, C8).
2. Whether `-s`/`-c model_catalog_json`, or any documented flag, keeps a pane's threads
   out of the daemon.
3. `/status` versus `/statusline` for the thread id (C9).
4. Claude: `TMUX_PANE` and `CLAUDE_PID` in a SessionStart hook for `source: clear`.

## Questions for Brian

None; the tests above come first.
