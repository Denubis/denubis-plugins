> Produced by the 2026-10-09 design fanout.
> Landed on 2026-10-25 under ADR 0041; exchange references rewritten, with no other change.

# Function 1, Record: verification

Verifier: Fable 5.1 at high, named by Brian 2026-10-09. Artifact: `01-record-proposal.md`
as read 2026-10-09 (2,060 words by `wc -w`; the brief caps proposals at 1,800). Scope
ruled by Brian: web documentation and files under this repository only. No Postgres
connection, transcripts, processes, or panes. Labels: **D** read in the cited document,
**R** read in a repository file, **L** live test needed, **I** inferred.

## Verdict

**Does not hold against the rulings made after it was written.** The storage shape is
sound Postgres and the retention rule honours Brian's transcript ruling, but the schema
cannot carry ADRs 0013-0017: no act history for nudges and interrupts, no idle or block
evidence for the clocks, no actor or reason on a withdrawal, no supervision edges, no
home for a mandate's task statement. Its single static `ack_token` also lets a previous
context acknowledge in a new one, which proposal 04 and property 5 forbid.

## Claim by claim

1. **NOTIFY delivered only at commit; payload under 8000 bytes by default; a listener
   inside a transaction receives nothing until it ends; `pg_notify(text, text)`.**
   Confirmed (D, `sql-notify`). Identical payloads in one transaction fold to one event;
   harmless for a hint. A listener killed by the idle timeout loses its LISTEN
   registration (D, `sql-listen`), so the proposal's reconnect-then-scan order is required.
2. **`uuidv7()` exists.** Confirmed for PostgreSQL 18 (D, `functions-uuid`, "18.6
   Documentation"). That this server is 18.6: **L** (`SELECT version(), uuidv7()`).
3. **Prune race: lock thread rows, re-read, delete; a reply racing the other order
   fails on the foreign key.** Consistent with the docs (D, `explicit-locking` 13.3.2):
   `FOR UPDATE` on the parent conflicts with a referencing INSERT's `FOR KEY SHARE`, so
   the reply waits, then fails against the deleted row. The proposer's 17 constraint checks
   and race runs: not reproducible by me. `/tmp/record-proposal-avs8Kz/` still exists
   (`ddl.sql`, `t_constraints.sql`, `t_races.sh`) but is outside my ruled scope.
4. **SKIP LOCKED.** Not used; `claim_surface_v1` is a compare-and-set UPDATE. Proposal 03
   asks for "`SKIP LOCKED` claims per address" (D, `sql-select`: suited to "a queue-like
   table"). Unagreed interface, not a defect.
5. **Local Mail: `read` set by `pull`; DDL on every connection.** Confirmed (R,
   `local_mail_store.py`: `pull()` runs `UPDATE deliveries SET state='read'`; `_connect`
   executes `DDL`). "Live tables lack `alias` and `session_key`": **L**, and immaterial,
   because that DDL has `ADD COLUMN IF NOT EXISTS` for both. Local Mail also has no
   acknowledgement by the model at all, which is the real reason not to extend it.
6. **ADR 0015, withdrawal as a terminal fact with actor and reason.** Refuted (R).
   `delivery.closed_how='withdrawn'` and `pending_item.closed_how='withdrawn'` carry no
   actor and no reason. The ADR requires "the withdrawal reason" kept and restricts the
   act to "the sender or Brian", which the schema cannot audit or enforce. §6 also
   rejects tombstones outright; Brian ruled "Tombstones are important". Further, the
   prune rule needs `acked_transcript`, which a withdrawn-unacked delivery never has, so
   such threads are either immortal or need a rule the proposal does not state.
7. **ADR 0015 and 0017, interrupt attempts and nudges as recorded acts.** Refuted (R).
   The only per-recipient fact is one `surfaced_at`/`surfaced_epoch` pair. ADR 0017
   needs "2 nudges per context, 10 minutes apart", an interrupt rung, a "stuck" listing
   with the refusal reason, and a log of "every nudge, interrupt, and listing with its
   elapsed unblocked time". Nothing in the schema counts to two, records an interrupt,
   or holds a refusal reason; `pending_item.kind` has no `stuck`. Proposals 03
   (`delivery_attempt`) and 05 (event rows) both ask Record for this table; Record
   answers "its role tables are its own".
8. **ADR 0016, clocks pause while blocked.** Refuted (R). §4: "the Record supplies
   `surfaced_at`, not the interval" is elapsed wall time, which the ADR says "neither
   may use ... alone". The schema holds no last-Stop, pending-approval, or tool-running
   evidence, so no consumer can compute unblocked idle time from it.
9. **ADR 0013 and 0014, edges and task statement.** Refuted (R). ADR 0014: the
   supervisee set "is recorded as supervision edges in the Record ... the Record's edge
   table (function 1)". The proposal has no edge table. ADR 0013: a mandate "carries the
   supervisor's task statement"; proposal 06 places its four authority tables in Record.
   Proposal 01 is silent on both. Edges are cross-provider only (ADR 0011).
10. **ADR 0012, first answer wins.** Partly refuted (R). `pending_item` closes only as
    `answered` (requires `answer_ref`, "the decision record's path") or `withdrawn`. A
    pane-answered approval has no decision record (06: `resolved_at_pane`, "nothing is
    issued"), so the CHECK forces either a fabricated reference or a row that never
    retires: the stale obligation verification 07 condemned.
11. **ADR 0008, tickets by pointer only.** Confirmed (R): `owner_ref` is a path plus
    heading id, `label` is display only. The proposal correctly observes (R,
    `recording-project-notes/SKILL.md`) that headings carry no stable id (Q3 stands).
    Conflict: 07 removes the item when Brian's answer row exists; 01 only once an agent
    has written the ADR. Property 8 favours 01, the "false obligation" argument 07.
12. **Retention honours "present in transcripts is unimportant".** Confirmed in
    direction, stricter than the ruling (both transcripts must hold the id). Two gaps:
    hook-originated and `human`-sent messages have no sender transcript (the proposal's
    own §6 point), so under "cannot be read are kept" every Brian answer is immortal;
    and the accepted position says "archive", the proposal deletes (its contradiction 3,
    unresolved). The August "no automatic pruning" line (R, design plan line 1992) is
    superseded by today's ruling, as the proposal infers.
13. **`ack_token` proves the body reached the current context.** Refuted by comparison
    (R, proposal 04 §2 and property 5). One token per delivery, fixed at insert, is valid
    in every epoch; a compaction summary carrying it lets the new context ack without
    `fetch_v1`. 04's falsifier "ack succeeds with a previous context's code" fails here.
    Minting per (delivery, epoch) at fetch time closes it.
14. **ADR 0019(a), sub-agents send as parent with `via`.** Gap: `message` has no `via`.
15. **ADR 0018, record first, ping by native channel.** Compatible; 03 assumed
    `mail_<address>` channels where 01 has one `record` channel. Interface only.
16. **`agent` table.** Proposals 01 and 02 define it differently; one must own it.
17. **Roles are not an authority boundary (peer auth makes `brian` superuser).**
    Internally consistent with scram-over-TCP for the app role. pg_hba state: **L**.

## Strongest failure in Brian's environment

Brian's ladder rulings (0015, 0016, 0017) came after this proposal, and he expects the
numbers to be retuned "from evidence rather than re-guessed". This Record cannot produce
that evidence: it has no act log, no block intervals, no withdrawal reason. Functions 4
and 5 would have to build their own tables, which is the split store property 11 and the
brief's single-Record decomposition forbid, and the first field period would log nothing
retunable.

## What survives

Separate database and schema, `uuidv7()` ids, per-recipient delivery rows with ack
separate from surface and close, `expects_reply` closing only on reply or withdrawal, the
epoch integer, body in flight only, pointer-only pending items keyed `(kind, owner_ref)`,
content-free `pg_notify`, SECURITY DEFINER `_v1` functions with timeouts, sha256-logged
migrations, the locked prune, refusing mail to a `human` address, and the five questions
for Brian.

## Live tests needed

`SELECT version(), uuidv7()`; pg_hba peer and scram lines; `local_mail.mailboxes`
columns; the proposer's scratch DDL and race scripts re-run by an authorised agent.
