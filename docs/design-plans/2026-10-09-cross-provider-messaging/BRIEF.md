> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Brief: generalised inter-agent messaging and supervision (2026-10-09)

Dispatcher: the supervising Claude session (brian-ed3d-plugins-ad). Main repository:
`/home/brian/people/Brian/brian-ed3d-plugins` (branch main, clean). Work is read-only
except for your own deliverable file under `./`.

## Goal

Any session of Claude Code or Codex CLI (Antigravity `agy` best effort, never gating) can
supervise any other; messages between sessions are durable and acknowledged; Brian sees
everything that needs him on one side-monitor surface. We are building our own. Prior
work is input, not something to preserve.

## Functional decomposition (accepted by Brian, 2026-10-09)

1. **Record.** One Postgres store holds operational state only: messages in flight,
   delivery and acknowledgement state, pending items waiting on Brian. Decisions and
   rulings stay in the notes directory and ADR registers; a record may point at one by path, never
   contain it. Open tickets stay owned by the `project_open-questions.md` file in the main checkout's notes directory (ADR 0008);
   the Record only tracks that a ticket is undelivered or unanswered.
2. **Identity.** Every session has a stable address it knows and keeps across clear,
   compact, and resume; a fresh launch gets a new one.
3. **Deliver.** A message reaches a live model, mid-turn and from idle. Hooks are the
   check path; a guarded tmux actuator is the universal path, and the same actuator is
   what supervision drives.
4. **Acknowledge.** The recipient model, not a hook or harness, marks receipt;
   unacknowledged items resurface.
5. **Supervise.** Roles are data; supervisor verbs (send, tail, clear, approve by
   reference, spawn) work on any vendor's pane; direction can invert. ("multi-chat" in
   Brian's words = this: generalising the supervisor from any agent to any agent.)
6. **Authority.** Approvals are decided by the approver (`/home/brian/people/Brian/approver/`)
   or Brian, referenced by exact request id, never by mail content.
7. **Human surface.** A side-monitor view of traffic plus a "needs Brian" list
   (approvals, tickets, questions). Items leave only when answered.

## Human rulings (verbatim, do-not-contradict)

Brian, 2026-10-09, this session:
- "I want any [codex,claude,agy] to be able to supervise any other, and I want messages to be able to be exchanged properly between sessions."
- "It's fine if we move from a local .notes thing to a postgres mediated thing"
- "Let's just generalise."
- "I don't really care about agy if it's hard."
- "I don't really care about reusing prior work"
- "alt-s picker is worthless, I never use it. I don't care about picking, I care about seeing the 'approve' requests in a new byobu terminal or app or... whatever I need."
- "I wouldn't mind a control UX thing on one of my side monitors where I can see messages pinging back and forth and have a list of things that I need to prod"
- "hooks are fine for checking things, but we do need to be able to tmux-send for this to also be able to eat supervision. I've got another you looking at Claude 'Mods'"
- "if a message appears in a transcript, we can treat it not important in postgres." (So once both sender and recipient transcripts hold a message, the Postgres copy is prunable; the Record is not a transcript mirror.)
- "you're not going to drive Astra or Argon, we'll just launch both with critical peer review mode once we've figured out what we're doing."

Brian, 2026-08-09 (cross-model-coordination design, lines 11-147 of
`2026-08-09-cross-model-coordination.md` on the `cross-model-coordination` branch):
the 14 confirmed properties. Read them. Properties 2, 4, 7, 10, 12, 14 bind this work
directly. Note ADRs 0007-0009 on main supersede that design's state model where they
conflict (typed hooks are not reliable enrolment on Codex; idle panes get no monitor;
announce once).

ADRs on main, binding: `docs/architecture/decisions/0005`, `0007`, `0008`, `0009`, `0010`.

## Accepted positions from the dispatcher (asserted; Brian said "ok, that's fine")

- Record is not replacing ADRs; it is transport and liveness state.
- No double-tracking of transcripts. Pruning: archive once every recipient acknowledged
  and a retention window passed; pending items live until answered.
- Hooks for compact/clear where reliable (Claude SessionStart carries source
  startup|resume|clear|compact); on Codex identity comes from session locks and session
  files (ADR 0007). Stop hooks are the "you have mail" nudge on both.

## Staged research (asserted-verify-before-relying)

The context documents 01-our-prior-attempts.md, 02-local-mail-and-vendors.md,
03-protocols-survey.md and 04-implementations.md, and the context README. Primary sources
to open yourself are listed in that README. The working Postgres Local Mail plugin is at
`denubis-local-mail` on the `cross-model-coordination` branch. The Codex supervisor
is `plugins/denubis-external-agents/scripts/codex_supervisor.py` with its skill at
`plugins/denubis-external-agents/skills/supervising-codex/SKILL.md`.

Environment facts (observed by the dispatcher 2026-10-09): Postgres on localhost:5432,
database `postgres`, schema `local_mail` exists and is dormant. Claude Code here has
SendMessage/ListAgents over a per-session Unix socket. Codex is 0.157-0.159. `agy` has
`--model`, `--effort`, `-p`, `--input-format stream-json`, hooks (no SessionStart), MCP.
tmux under byobu, ~20 windows.

## Standing rules for every agent

Do not reopen ruled decisions. Flag contradictions loudly rather than resolving them
silently. Report what you could not check rather than inferring it. Never assert an
absence from a single search; search a second way or run a positive control. Surface any
decision rather than deciding it silently; if a choice is Brian's, say so and give your
recommended default. Label every claim observed, inferred, or assumed. Never select
Astra or Fable yourself; your model and effort were named by Brian for this task on
2026-10-09 ("High effort for verifier, medium for proposer (Fable), xhigh for proposer
(opus)"). Pushing back on scope, premise, or approach is welcome. Questions only Brian
can answer go in your report under "Questions for Brian", one per line with its blocking
consequence; do not write to the notes directory.

## Deliverable format (proposers)

Write the function's numbered proposal document (filename pattern `0N-<function>-proposal.md`), under 1,800
words:
1. The challenge restated in one paragraph, naming the assumption it protects.
2. Proposed mechanism, concrete: schema or data shapes, commands, hook events, file
   paths, vendor surfaces, with the specific version or doc you relied on.
3. How it is verified: the falsifying test for each load-bearing claim.
4. Interfaces to the other six functions: what you need from them, what you give them.
5. Failure modes and what the design does when each happens.
6. Alternatives you rejected and why.
7. Could not check.
8. Questions for Brian.

## Deliverable format (verifiers)

Write the function's numbered verification document (filename pattern `0N-<function>-verification.md`), under
1,200 words. Falsification-first: for each load-bearing claim in the proposal, state
whether you confirmed it against the source, refuted it, or could not check, with the
evidence. Then the strongest reason the proposal fails in Brian's actual environment.
Then what survives. Do not rewrite the proposal.
