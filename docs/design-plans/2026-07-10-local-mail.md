# Local Mail Design

**GitHub Issue:** None

## Summary

Replace shared append-only chat monitors with an explicitly opted-in, machine-local
mailbox. Peer agents send durable messages carrying a required subject and thread ID.
Recipients receive a compact digest at Stop and pull bodies deliberately. One supervising
mailbox may observe all peer traffic without causing every worker to read every message.

This is adjacent to active supervision, not a replacement for it. A supervisor continues
to drive its joined Codex pane through `codex_supervisor.py`, whose immediate monitor owns
approvals, questions, completion, and crashes. Local mail owns peer contradictions,
dependencies, decision requests, corrected claims, and handoffs.

## Evidence and problem shape

The prototype's shared Markdown outboxes carried useful corrections, but a pushed
`tail -F` monitor made every session pay for all coordination. In one track, eighteen
outbound messages produced only four code-changing interactions; the rest were
coordination overhead. Fixed-glob monitors missed newly created outboxes, hot-swapped
filters replayed whole histories, and repeated notification eventually led workers to
disconnect their monitors. Removing peer dialogue entirely would also be wrong: several
cross-track claims were corrected through it.

The design therefore preserves durable peer exchange while changing delivery from
"push every body" to "announce a subject once, then pull".

## Channel boundary

| Concern | Mechanism | Urgency |
|---|---|---|
| Supervised Codex lifecycle, approval, question, command, done, crash | guarded `codex_supervisor.py` verbs and monitor | immediate |
| Peer contradiction, dependency, decision request, correction, handoff | local-mail subject/thread | next safe Stop |
| Durable project ruling | the consuming project's ADR register | persistent project authority |
| Track narrative and evidence | project-owned `.notes/` track records | durable working record |

Mail must not become a second control path into a supervised pane. ADRs must not live only
in mail: a ruling received in a thread is written to the project's indexed decision
records by the track that owns it.

## Identity and routing

Each mailbox registers a chosen username bound to an absolute worktree location. Several
usernames may share one worktree so Claude and Codex can coordinate there independently.
The MCP process checks both username and launch directory on every operation. The Stop
hook takes its username from `LOCAL_MAIL_USERNAME`, making the alert boundary explicit.
Registration warns when other usernames already share the worktree; peers then exchange
their intended paths before editing. This is coordination, not a filesystem lock.

New messages have one or more explicit recipients. A mailbox registered with
`--observe-all` receives a copy of every peer message, except its own. Workers receive
only mail explicitly addressed to them or replies in a thread in which they participate.
The first version deliberately omits lists, `everyone`, project broadcasts, and dynamic
subscriptions.

## Storage and transaction boundary

PostgreSQL is authoritative for mailboxes, locations, threads, participants, message
bodies, delivery routing, and the `new`/`notified`/`read` state machine. All values are
parameterised and all related writes commit in one database transaction. No message files
are written into a worktree or shared parent checkout.

## Threads and state

A new thread requires a non-blank, single-line subject of at most 160 characters. This is
a security boundary: pushed subjects cannot inject a fake digest line or command. Replies
inherit the subject and route to thread participants plus current observers. An authorised
participant pulling a thread sees the whole ordered conversation, including its own sent
messages.

Each delivery moves monotonically:

```text
new --Stop digest--> notified --pull--> read
  \--------------------pull----------/
```

`inbox` shows `new` and `notified` threads without bodies. `pull` returns the body and
marks that mailbox's available deliveries read. Read state is per mailbox.

## Stop notification

The Stop hook does nothing unless `LOCAL_MAIL_USERNAME` and the event working directory
match a registered mailbox with `new` deliveries. It emits a one-shot continuation with
thread ID, subject, sender, and count—never the body—then marks those deliveries
`notified`. A later Stop is silent while the digest remains visible in `inbox`. If
`stop_hook_active` is true, the hook neither emits nor consumes mail, preventing loops.

The commit-before-output order chooses no replay over guaranteed notification after a
process crash in the few instructions between commit and stdout. Such mail remains
`notified` and visible in `inbox`; it is not marked read or lost. A future acknowledgement
protocol may revisit this trade only if field evidence warrants the added state.

## Commands

- MCP: `register(username)`, `send`, `inbox`, `pull`, and `reply`
- Admin CLI: `register ADDRESS --location PATH [--observe-all]`
- `--as ADDRESS send --to ADDRESS --subject TEXT --body TEXT`
- `--as ADDRESS inbox`
- `--as ADDRESS pull THREAD_ID`
- `--as ADDRESS reply THREAD_ID --body TEXT`

Agents use MCP tools; the CLI remains for human diagnostics and observer registration.

## Deliberately deferred

No daemon, network transport, five-minute escalation, delivery receipt, attachment,
scheduled send, address list, correction/deletion UI, administrative TUI, multi-host
operation, or peer-review/k-agent integration is part of 0.1.0. The first field iteration
should measure missed mail, unnecessary wakeups, and thread volume before choosing among
those mechanisms.

## Definition of Done

- Explicit usernames bound to launch worktrees, with multiple users per worktree.
- Transactional direct delivery, observer copies, subjects, threads, replies, digest-only
  inboxes, body pulls, and per-mailbox read state.
- PostgreSQL-authoritative message bodies, routing, threads, and delivery state.
- A portable Stop hook that notifies once, does not expose bodies, and does not loop.
- Native Claude and Codex manifests, marketplace entries, changelog, usage skill, and
  documented boundary from active Codex supervision.
- Targeted behavior tests, hook portability, marketplace sync, lint, and the repository's
  full test gate run with any unrelated baseline failure reported rather than hidden.

## Acceptance Criteria

1. Sending to one explicit peer does not put the message in another worker's inbox.
2. An `--observe-all` supervisor receives the same message without becoming its sender.
3. `inbox` and Stop output contain the subject and routing metadata but no body text.
4. `pull` returns the whole authorised thread and changes only that mailbox's deliveries
   to `read`.
5. A reply keeps the thread ID and subject and reaches every participant except its sender.
6. A multiline, blank, overlong, or control-character subject is rejected before a
   message file or delivery exists.
7. The first non-recursive Stop with new mail emits one digest and marks it `notified`;
   the next Stop emits nothing; `stop_hook_active` consumes nothing.
8. The hook and MCP launcher ignore the caller's Python project/config.
9. Empty inbox and hook checks are silent and exit successfully.
10. No peer-mail code types into, approves, or substitutes for a supervised Codex pane.

## Glossary

- **Control channel:** Immediate, guarded interaction between a supervisor and the agent
  it supervises.
- **Peer mail:** Durable, low-interruption coordination between collaborating tracks.
- **Observer:** A mailbox receiving copies of all peer deliveries for supervisory review.
- **Digest:** Subject and routing metadata without message bodies.
- **Pull:** Deliberate retrieval of a thread body, which marks available deliveries read.
- **Worktree peer:** Another registered username sharing the same worktree and therefore
  requiring an explicit intended-path handshake before edits.
