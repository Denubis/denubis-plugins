> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Function 1, Record: proposal

Proposer: Claude Opus 5.5 at xhigh, named by Brian 2026-10-09. Labels: **O** observed by
me today; **D** read in the cited document, behaviour not observed; **I** inferred;
**A** assumed.

## 1. Challenge

Hold every message, acknowledgement, and wait-on-Brian in Postgres from the moment it is
accepted until its owner has demonstrably taken it, so compaction, `/clear`, scroll, or a
crash of any process cannot lose it, and hold nothing else. The assumption protected: a
model's context and a pane's screen are disposable, so the only safe copy of an
unfinished exchange is a committed row; once a transcript or a `.notes` file holds the
content, that file is the lasting copy and the row goes.

## 2. Mechanism

**Where.** A new database `agent_record`, schema `record`, on the existing PostgreSQL
18.6 server (O). The dormant `local_mail` schema stays untouched and unmigrated.

**Tables** (shorthand; `line(n)` is `CHECK (x !~ '[\n\r]' AND length(x) BETWEEN 1 AND n)`):

```
agent        (address text PK, kind IN (session, role, human, system),
              context_epoch int DEFAULT 0, transcript_path, ended_at)
thread       (id uuid PK DEFAULT uuidv7(), subject line(160), created_at)
message      (id uuid PK DEFAULT uuidv7(), thread_id -> thread ON DELETE CASCADE,
              sender -> agent, in_reply_to, expects_reply bool DEFAULT false,
              body text NOT NULL, dedupe_key, sender_transcript, created_at,
              UNIQUE (thread_id, id), UNIQUE (sender, dedupe_key),
              FK (thread_id, in_reply_to) -> message (thread_id, id))
delivery     (message_id -> message ON DELETE CASCADE, recipient -> agent,
              PK (message_id, recipient), ack_token text DEFAULT <8 random hex>,
              surfaced_at, surfaced_epoch,
              acked_at, acked_by -> agent, acked_epoch, acked_transcript,
              closed_at, closed_how IN (acked, replied, withdrawn),
              CHECK (num_nulls(acked_at, acked_by, acked_epoch) IN (0, 3)),
              CHECK (num_nulls(closed_at, closed_how) IN (0, 2)),
              CHECK (closed_how NOT IN ('acked','replied') OR acked_at IS NOT NULL))
pending_item (id uuid PK DEFAULT uuidv7(), kind IN (approval, ticket, question),
              owner_ref line(400), requester -> agent, label line(160),
              opened_at, seen_at, closed_at, closed_how IN (answered, withdrawn),
              answer_ref line(400), UNIQUE (kind, owner_ref),
              CHECK ((closed_how IS NOT DISTINCT FROM 'answered') = (answer_ref IS NOT NULL)))
schema_migration (version int PK, resource_name, sha256, applied_at)
INDEX delivery_open (recipient) WHERE closed_at IS NULL
INDEX pending_open  (opened_at) WHERE closed_at IS NULL
```

**Keys.** Message ids are `uuidv7()` (present on this server, O) because an id outlives
its row inside transcripts and must stay unambiguous after a rebuild. A delivery is the
pair (message, recipient). A pending item's natural key is (kind, owner pointer), so
registering it again after a crash returns the same row.

**Per-recipient state** is three separate facts.
- *Surfaced*: a hook or the actuator showed the subject. Proves nothing; it exists so two
  surfacers never nudge twice (`claim_surface_v1`, compare-and-set).
- *Acked*: the model called `ack_v1` with the token that only `fetch_v1` returns beside
  the body. Listing and fetching never set it.
- *Closed*: an FYI closes on ack. A message sent with `expects_reply` closes only when
  the recipient replies (`in_reply_to`) or the sender withdraws it.

Identity bumps `agent.context_epoch` whenever a session's context is replaced. A delivery
acked under an older epoch and still open is *carried over*: the next check lists it for
a fresh ack. That is property 5 in one integer.

**Pending on Brian** is a pointer and a state, never content. `owner_ref` names the
owner: a ticket is `<main-repo-root>/.notes/project_open-questions.md#<ticket id>`; an
approval is the request id function 6 defines; a question a session parks on (ADR 0009)
is the asking session plus its transcript record. It closes two ways only: `answered`,
which the schema refuses without a one-line `answer_ref` (the decision record's path),
or `withdrawn` (ADR 0008's ticket nobody needs; a dead requester). Nothing closes on age.
Closing as answered inserts, in the same transaction, an ordinary message to the
requester carrying only `answer_ref`, which the requester must ack. The ticket file is
written first and stays the truth; a sweep at task entry upserts by key, so a ticket
filed while Postgres was down is registered later. `label` is a display line, not the
question. Mail to a `human` address is refused: what needs Brian is a pending item.

**Bodies** are stored while in flight, because fetch must not depend on parsing a vendor
transcript. **Pruning** deletes a thread whole, with no tombstone, when every delivery
in it is closed, the retention window has passed, and the pruner has found each message
id in the transcript files recorded at send and at ack. Presence is observed, not
inferred from the ack. Threads whose transcripts cannot be read are kept and counted.
Open pending items are never pruned.

**NOTIFY is a hint.** Write functions call `pg_notify('record', <address or id>)`, never
content. Hooks scan when they fire. Long-lived listeners (side monitor, actuator) scan
on connect, on notify, and every 5 seconds (adopted default; function 7 may change it),
on autocommit connections.

**Roles.** `agent_record_owner` owns the schema and runs migrations. `agent_record_app`
may only EXECUTE the `_v1` functions (SECURITY DEFINER, fixed `search_path`), with
`statement_timeout`, `lock_timeout`, and `idle_in_transaction_session_timeout` set so a
hook cannot hang a turn. `agent_record_reader` reads two body-free views, `traffic` and
`needs_brian`. Login is scram over 127.0.0.1 from `~/.pgpass`, as
`cc_search_chats_owner`/`_app` already do here (O). Each call is one autocommit
statement, so the function owns the transaction. **Limit (O):** every session runs as OS
user `brian`, whom peer authentication makes a superuser. The roles stop accidents; they
are not an authority boundary, and nothing may read authority from a Record row.

**Versioning.** Numbered SQL files applied by `record migrate` as the owner, each logged
with its sha256 (the shape `cc_search_chats.schema_migration` has, O). No DDL from hooks
or on connect. A client needing a newer schema refuses and prints the migrate command.
Breaking changes add `_v2` and keep `_v1`, because each vendor's plugin cache upgrades
separately.

API: `send_v1`, `open_for_v1`, `fetch_v1`, `claim_surface_v1`, `ack_v1`, `withdraw_v1`,
`pending_open_v1`, `pending_seen_v1`, `pending_close_v1`, `epoch_bump_v1`,
`prune_candidates_v1`, `prune_threads_v1`.

## 3. How it is verified

Run today on a private throwaway 18.6 cluster, since removed; scratch files are in
`/tmp/record-proposal-avs8Kz/` (disposable).

| Claim | Falsifying test | Status |
|---|---|---|
| The schema refuses invalid states | 17 checks: partial ack, close without ack, reply into another thread, duplicate dedupe key, two-line subject or `answer_ref`, answered without a reference, duplicate owner | Run; all refused. A first draft's `{1,400}` regex passed DDL and failed every insert, found only by running. |
| A harness cannot ack | As the app role: direct UPDATE; `ack_v1` with a wrong token | Run; both refused, zero acks. Not run: a real hook driven 100 times. |
| Context loss resurfaces an unanswered request | Ack an `expects_reply` message, bump the epoch, list | Run in SQL; listed, and the FYI was not. Not run: a live `/compact` or `/clear`. |
| Pruning cannot lose a reply in flight | A reply commits while the prune runs | Run. A one-statement prune with no lock deleted a committed open reply with no error. The proposed function (lock thread rows, re-read, delete) kept it; in the other order the reply fails loudly on the foreign key. |
| One nudge under concurrency | Two simultaneous claimers | Run; one true, one false; true again after an epoch bump. |
| Pending items leave only when answered | Prune with the clock ten years on; remove a ticket from the file without closing | Not run. |
| Pruning needs observed transcript presence | Point `acked_transcript` at a file lacking the id | Not run. |
| NOTIFY is only a hint | Kill the listener, send three, restart | Not run. Semantics D: PostgreSQL 18 `sql-notify`, `sql-listen`. |
| Version skew is survivable | A v1 client against v2 functions; a v2 client against v1 | Not run. |

## 4. Interfaces

- **Identity** gives a stable `address`, an epoch bump on every context replacement, the
  current `transcript_path`, and `ended_at`. Callers derive identity from the
  environment, never from a model-supplied sender.
- **Deliver** gets `open_for_v1(addresses[])` (subjects only, classed new / carried over
  / reply owed), `claim_surface_v1`, and `fetch_v1`. Only an id is typed into a pane.
- **Acknowledge** gets `ack_v1`. It owns when an un-acked item is surfaced again; the
  Record supplies `surfaced_at`, not the interval.
- **Supervise**: a prompt is a message with `expects_reply`; a clear is an epoch bump; a
  role mailbox is an address of kind `role`. Its role tables are its own.
- **Authority** supplies the exact request id and resolution reference. A Record row is
  never evidence of approval.
- **Human surface** gets the two views, the `record` channel, and `pending_seen_v1`.
- **`recording-project-notes`** (outside the seven) must put a stable id in each ticket
  heading.

## 5. Failure modes

- Postgres down: sends fail visibly; hooks emit a system message; tickets still land in
  `.notes` and are swept in later.
- Sender dies after commit: the message is durable; a retry with the same `dedupe_key`
  returns it. An unkeyed model send can duplicate.
- Recipient dies after fetch, before ack: the delivery stays new.
- Epoch bump missed (Codex compaction detection is "not established", ADR 0007): carried
  over never fires; reply-owed items are still listed at Stop regardless of epoch.
- Recipient ended: the delivery stays open and shows its age until the sender or Brian
  withdraws it.
- Reply to a pruned thread: foreign-key error; the tool says start a new thread.
- Ticket removed with no close call: shown as "owner missing", not closed.
- Listener left in a transaction: notifications stall (D); the role timeout ends it and
  the poll stays correct.
- Database lost: in-flight mail is lost from Postgres; tickets and live dialogs are
  re-registered from their owners. No backup is proposed.

## 6. Alternatives rejected

- Digest plus transcript locator only: fetch would parse two private transcript formats
  (ADR 0007 quotes Codex: "isn't a stable interface"), and hook-originated messages have
  no sender transcript.
- pgmq: not available on this server (O); one consumer per message, no per-recipient
  ack, threads, or identity (report 04, asserted).
- Extending `local_mail`: `read` is set by `pull`, a harness side effect; DDL runs on
  every connection; the live tables already lack the code's `alias` and `session_key` (O).
- Pending items as mail to `brian`: a recipient closes mail, only the owner closes a
  pending item.
- Append-only ack history (August DR6), tombstones, or an archive table: each is a
  second transcript.
- Integer ids: they restart after a rebuild.
- LISTEN inside hooks: hooks are short-lived.

## 7. Could not check

- Epoch detection on a live `/compact` or `/clear`, either vendor; whether Claude's
  `/clear` changes the transcript path (A).
- Whether a transcript is flushed before the pruner reads it; the window is the margin.
- Codex hook payloads carrying `transcript_path` (D, ADR 0007). Claude's do (D, Agent
  SDK hook input reference).
- Message volume: tens to hundreds a day (A). The indexes are reasoned, not measured.
- Antigravity: nothing.

Contradictions flagged, not resolved by me:
1. Property 10 says cited mail resolves to a file under the primary checkout; today's
   ruling makes the transcript the lasting copy.
2. The August design says "no automatic pruning"; today's ruling supersedes it (I).
3. The accepted position says "archive"; I read the ruling as delete.
4. Function 6 says "exact request id"; the approver's log has no such field (O: field
   names in 34 rows of one day's log, plus two source searches; not an audit). Hook
   payloads carry `tool_use_id`/`tool_call_id` per `codex_supervisor.py:822` (O, code).
5. Ticket headings have no stable id (O: `recording-project-notes` defines none).
6. Claude's docs show a fifth SessionStart `source`, `fork` (D), absent from the brief.

## 8. Questions for Brian

1. How many days should a finished, transcript-verified thread stay in Postgres before deletion? Recommended 7. Blocks: the pruner's default and how far back the traffic pane scrolls.
2. For a message a decision record cites, is a transcript locator plus sha256 enough, despite property 10's message file? Recommended yes. Blocks: whether the Record needs a write-body-to-file path.
3. May each ticket heading in `project_open-questions.md` carry a stable id such as `Q-20261009-a3f1`? Recommended yes. Blocks: without it the needs-Brian list can show only "N open tickets in this repo".
4. Is it acceptable that database roles only prevent accidents, given every agent session is a Postgres superuser? Recommended yes. Blocks: otherwise the build starts with a server authentication change only you can make.
5. May the build create database `agent_record` and three roles on your server? Recommended yes. Blocks: migration 1 has nowhere to run except a schema beside `local_mail`.
