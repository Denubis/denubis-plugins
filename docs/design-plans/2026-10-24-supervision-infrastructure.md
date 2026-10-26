---
status: Draft
date: 2026-10-24
---

# Supervision infrastructure

This revises the Claude-supervision design under ADRs 0035–0042. It is a design,
not implemented architecture. It preserves the safety preflight, bounded briefs,
challenged checkpoints and independent verification. The exchange becomes the Record;
driving authority remains live, per instance and commanded by Brian.

## Revision map

Every stage-1 section is accounted for. “Superseded” withdraws its mechanism, not the
safety outcome identified in the replacement column.

| Stage-1 section or contract | Disposition | Current home and consequence |
|---|---|---|
| 1. Equivalence map | amended (ADRs 0038, 0041) | §6.1 retains vendor distinctions; hooks supply telemetry and code uses the repository floor. |
| 2. Driver contract, including D1 | amended (ADRs 0037, 0039, 0040, 0041) | §§1, 3, 6: thin drivers, installable package, bind/pending in the minimum, send by dispatch ID. |
| 3. Pane resolution | amended (ADRs 0037, 0039) | §6.2: named edges, many workers, self excluded, live instance and own window checked every action. |
| 4. Send path | amended (ADR 0041) | §6.3 retains literal input, identity/composer/dialog preflight and uncertain submission; envelope points to a Record dispatch. |
| 5. Checkpoint protocol | amended (ADR 0041) | §8 retains manifest, fixed final-line fields, correlated Stop, cooperative pause and exact-revision release. |
| 6. Persistence and restart | superseded (ADRs 0039, 0041) | §§2, 8: Record history survives; driving authority does not. No journal or automatic binding recovery. Uncertain sends cannot replay themselves. |
| 7. Monitor | superseded (ADR 0039) | §§3–5: one service, Stop pull, idle ping and existing ladder; no monitor verb, host wait loop or re-arming. |
| 8. Conflicts and open decisions | amended (ADRs 0035–0042) | Authority below and §12: D1/D2/D4/D5 ruled; D3 withdrawn. Remaining human decisions explicit. |
| 9. Test plan, T01–T25 and smoke | amended (ADRs 0038–0041) | §11 maps surviving outcomes to revised checks, including refusal, no replay and human acceptance. |
| 10. Phases, P0–P6 | amended (ADRs 0039–0041) | §§9, 11: deterministic bootstrap precedes daemon integration and permission-dependent live captures. |
| 11. Unverified | retained | §12 preserves surviving limits and adds service, Record and wake boundaries. |
| C1: cooperative pause without tool gate | retained | §8: end turn, prohibit background work, verify quiescence and rehash; no OS freeze claimed. |
| C2: file-only publication, no worker client | superseded (ADR 0041) | Worker puts a return through the package client in one call; publication is not review/release. |
| C3: explicit ordinary-worker defaults | retained | §6.2 quotes standing defaults; actual configuration verified separately. |
| C4: tranche boundary | amended (ADR 0039) | §6.4 names twelve minimum verbs; monitor disappears; bind/pending required. |
| C5: existing architecture owner | retained | §10 updates existing context page after implementation exists. |
| Python 3.12 facade and Python 3.9 installer | superseded (ADRs 0038, 0040) | §§1, 10: package, drivers, relay and migrated installer use 3.14; retire old floor suite with installer migration. |

## Authority and evidence

The [specification](2026-10-24-claude-supervision-spec.md) supplies the goal.
The [decision register](../architecture/decisions/README.md) supplies the rulings.
Where they conflict, the ADR wins. Quotations below are verbatim; the accompanying
operational constraints also bind.

| Ruling | Text or constraint carried into this design | Authority and original locator |
|---|---|---|
| R1 | “Supervision is a instance by instance thing, commanded only by me. A supervisor should know what window-pane things it is allowed to monitor. Monitors should be able to do it.” and “it should only drive panes in its tmux window. Note pane*s*.” | [ADR 0039](../architecture/decisions/0039-supervision-is-per-instance-on-brians-command-over-named-panes-in-the-supervisors-window-and-nothing-re-arms.md), session 3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29, lines 1172 and 1211. |
| R2 | “My very strong preference is to bake most of these things into stop hooks and pull rather than push, so that if a session is idle and supervising it gets a ping, but if it's working it just goes until it pauses (obviously we can go up the priority ladder)” | ADR 0039, same session, line 1323. |
| R3 | “If we don't have things shelling out (and that *must* not ever be multiple calls) would it not be better to just have something that can do pings and mailboxes directly?” | ADR 0039, same session, line 1351. |
| R4 | “So long as we're consistent, and building a library that handles common things, rather than a bunch of oneoff scripts” | [ADR 0040](../architecture/decisions/0040-the-shared-supervision-library-is-an-installable-package-in-this-plugin-and-the-daemon-lives-in-the-private-repository.md), same session, lines 1561 and 1571. Installable library here; daemon there; dependency one way. |
| R5 | “d2 I'd prefer we just have this be postgres? ... d4 yes and hooks as needed, d5 yeah, I hate the ask user question tool, it needs to go into open questions, then the supervisor needs to understand project context, search decisions and notes, and figure out if we've already answered it, and only then it stays in open questions. When answered it leaves open questions either into a decision or into some sort of useful documentation reference.” | [ADR 0041](../architecture/decisions/0041-the-prompt-exchange-is-the-record-not-a-directory-telemetry-comes-from-hooks-and-askuserquestion-is-denied-with-questions-living-in-open-questions.md), same session, line 1639. |
| R6 | hooks launch as <code>uv run --script --python '>=3.14'</code> with the fixed missing-uv preflight; they may import the package. | [ADR 0038](../architecture/decisions/0038-hooks-run-under-uv-run-script-at-the-repository-python-floor.md), same session, lines 1370 and 1432, plus its Codex-driver floor consequence. |
| R7 | both drivers are thin entry points over the package; same-harness pairs supported; self excluded. | [ADR 0037](../architecture/decisions/0037-claude-driver-is-a-sibling-script-over-shared-tooling-and-supervision-is-binding-based-for-any-harness-pair.md), same session, lines 781, 813 and 859. |
| R8 | the Codex host may answer obviously safe, narrow dialogs for a Claude worker, logged; everything else escalates to Brian. | [ADR 0035](../architecture/decisions/0035-adr-0013-stands-for-a-claude-worker-obviously-safe-dialogs-may-be-answered.md), same session, line 369 (enqueue) and line 484 (user). |
| R9 | project-neutral; charsheet is context only. | [ADR 0036](../architecture/decisions/0036-the-claude-supervision-mode-is-project-neutral-and-charsheets-backlog-is-not-its-workload.md), same session, line 589; ADR 0037, lines 773 and 781. |

These exact resolver invocations share the following explicit path binding. Each sed
invocation selects one original record; the table above supplies its ruling context.

~~~fish
set supervision_transcript_record /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
sed -n '1172p' $supervision_transcript_record
sed -n '1211p' $supervision_transcript_record
sed -n '1323p' $supervision_transcript_record
sed -n '1351p' $supervision_transcript_record
sed -n '1561p' $supervision_transcript_record
sed -n '1571p' $supervision_transcript_record
sed -n '1639p' $supervision_transcript_record
sed -n '1370p' $supervision_transcript_record
sed -n '1432p' $supervision_transcript_record
sed -n '781p' $supervision_transcript_record
sed -n '813p' $supervision_transcript_record
sed -n '859p' $supervision_transcript_record
sed -n '369p' $supervision_transcript_record
sed -n '484p' $supervision_transcript_record
sed -n '589p' $supervision_transcript_record
sed -n '773p' $supervision_transcript_record
~~~

These resolvers are recorded, **not executed here**: this stage prohibits transcript
reads. The task explicitly adopts the ADRs; this worker checked their text/locators,
not their underlying human records. The supervisor applied the runtime consequence
in ADR 0038 and owns that record.

Any further human ruling belongs in the indexed ADR register, recorded by the
supervisor; the mechanical proposals here do not manufacture such a ruling.

Other continuing constraints are [0006](../architecture/decisions/0006-astra-fable-require-explicit-model-and-effort.md),
[0009](../architecture/decisions/0009-monitor-announces-once-and-idle-panes-are-unwatched.md),
[0011](../architecture/decisions/0011-same-family-sessions-use-native-infrastructure.md),
[0013](../architecture/decisions/0013-a-driving-supervisor-answers-only-what-its-task-narrowly-needs.md),
[0014](../architecture/decisions/0014-one-supervisor-many-supervisees-all-in-its-own-tmux-window.md),
[0015](../architecture/decisions/0015-unacknowledged-mail-climbs-an-escalation-ladder-and-withdrawals-leave-tombstones.md),
[0016](../architecture/decisions/0016-ladder-clocks-run-only-while-the-supervisee-is-unblocked.md),
[0017](../architecture/decisions/0017-ladder-timing-defaults.md),
[0018](../architecture/decisions/0018-every-session-gets-a-ping-through-its-own-channel-and-pulls-mail-from-the-record.md),
[0021](../architecture/decisions/0021-ladder-runs-while-unblocked-busy-or-idle-and-a-blocked-supervisor-is-brians-item.md),
[0022](../architecture/decisions/0022-mandate-rails-are-expiry-and-directory-only-and-the-blind-approve-is-soft-retired.md),
[0025](../architecture/decisions/0025-identity-follows-the-pane-and-paneless-sub-agents-do-not-message.md),
[0026](../architecture/decisions/0026-the-record-lives-in-its-own-database-agent-record-with-three-roles.md),
[0027](../architecture/decisions/0027-the-default-codex-model-is-the-latest-sol-class-release-at-xhigh.md),
[0028](../architecture/decisions/0028-a-pane-sessions-you-should-know-offer-is-mail-to-its-supervisor.md),
[0034](../architecture/decisions/0034-permission-queue-leaves-the-plugins-repository-for-its-own-private-repository.md)
and [0042](../architecture/decisions/0042-citation-and-memory-checks-belong-to-the-commit-skill-and-run-in-every-repository.md).
Their authority sections retain their own exact resolvers; none was run here.

Conflicts are explicit:

- Spec's blanket approval prohibition is superseded by ADR 0035's narrow, audited
  authority, bounded by ADRs 0013/0022 and existing policy denies.
- Spec's restart reconciliation of driving bindings is withdrawn by ADR 0039.
  Persisting a dispatch does not persist permission to drive its former worker.
- Spec's exchange-directory requirement and stage-1 journal/publication choices are
  superseded by ADR 0041. Durable outputs live at proper project paths.
- ADR 0037 permits same-family pane driving despite ADR 0011's former exclusion.
  Property 7 still forbids same-family approval mandates pending Brian's ruling.
- Stage-1 statusline composition is withdrawn by ADR 0041. A payload's existence does
  not establish a permitted, working transport for it.

**Observed** means current source/command inspected here; **documented** means current
official documentation checked on 2026-10-24; **unverified** identifies a missing runtime
check. Proposed guarantees describe future code, not vendor behavior.

## 1. Package and ownership

### Proposed package

Use distribution **denubis-supervision**, import package **denubis_supervision**, with
its project at <code>plugins/denubis-external-agents/pyproject.toml</code>. Add that
plugin root to the existing uv workspace. Name/layout are draft mechanics for review,
not additional human rulings.

~~~text
plugins/denubis-external-agents/
  pyproject.toml
  src/denubis_supervision/
    __init__.py                 version and explicit public exports
    protocol.py                 request/response types and validation
    client.py                   one-request Unix-socket client and availability
    service.py                  shared handling and domain transitions
    record.py                   Record operations; host supplies connection
    migrations/                 ordered SQL and version/checksum metadata
    identity.py                 pane/process/session joins and edge validation
    tmux.py                     bounded inspection, locks and literal transport
    driver.py                   control engine; owns every keystroke
    hooks.py                    normalization and vendor output mapping
    offers.py                   offer parsing/attribution, one owner
    vendors/
      codex.py                  classifier, session and lifecycle mechanics
      claude.py                 registry, composer and lifecycle mechanics
  scripts/codex_supervisor.py    thin compatibility CLI and --hook entry
  scripts/claude_supervisor.py   thin Claude CLI
~~~

Use the existing workspace packages' src layout and Hatchling convention. Package,
drivers and migrated clients/installers require **>=3.14**. Package version equals
plugin release version, including both provider manifests, marketplace and changelog.
Working-tree manifests currently say 0.24.1; this design selects no future release number.

The library owns protocol, schema/migrations, transitions, inspection, registry readers,
classification, hook client, verbs and reusable service handling. The private repository
hosts the daemon and supplies credentials, connections, socket configuration, service
unit and existing permission viewer. It composes the shared handler rather than
reimplementing policy/schema; its deployment/viewer migrations cannot redefine Record
tables. No plugin import/startup/installation depends on the private repository.

| Public surface | First consumer and boundary |
|---|---|
| protocol.Request, Response, Pointer, Event and validation | Both hook adapters/CLIs, fixture transport and daemon; unknown versions refuse. |
| client.Client.request(request) | One connection/request/response; typed availability. Worker dispatch/return clients use it too. |
| client.main via supervision-record console entry | Worker data client: dispatch get, return put from stdin, pending, mail read/ack and ping-ack. One operation makes one request; stdout returns the body/result to the calling model. These are data operations, not extra pane-driving verbs. |
| record.Record(connection), apply_migrations(connection) | Private daemon and isolated PostgreSQL tests; host supplies connection/credentials. |
| service.handle(request, record, runtime, driver) | Real daemon and fixture server share domain handling; deployment stays outside. |
| driver.SupervisorDriver.execute(command, caller), deliver_ping(recipient, pointer) | Service invokes common actuator; ping cannot become a general send/approval bypass. |
| vendors.codex: BUSY_SPINNERS, classify_snapshot, ObservationKind, held_sessions, _main_rollout | Replaces private script path-loader. These ADR 0040 names have one owner; the underscore helper is explicitly exported for this consumer, not copied. |
| hooks.handle_hook(payload, client), vendor normalizers and offer parsing | Thin relay entries and retained offer client; client-only import needs no database implementation. |

Scripts parse/translate CLI arguments, resolve their own packaged source and delegate.
No duplicate classifier, target algorithm or state machine. In a shipped tree, bootstrap
selects src relative to the script's resolved file, never CWD or a first-found cache.
Installed wheels provide the same modules to the daemon. Client-only imports remain
usable without database extras/private service. Neither mode silently selects another
installed version.

Legacy <code>uv run --no-project --no-config python</code> invocation can still delegate
on >=3.14 with the complete tree; no lower interpreter is promised. Documented launch
uses <code>uv run --script --python '>=3.14' --no-project --no-config</code> and PEP 723.
Imports need no daemon; service operations do.

### Workspace and private dependency

Current uv documentation supports explicit members, workspace sources, path sources,
and Git rev/subdirectory sources. Workspace consumers declare the dependency and
<code>workspace = true</code>; members share resolution.
[Workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/),
[dependency sources](https://docs.astral.sh/uv/concepts/projects/dependencies/),
checked 2026-10-24. No install was performed.

Add the plugin root without replacing the two existing members or creating another
workspace lockfile. If the root test project depends on the package, use its workspace
source. The private repository instead declares the package and normally imports the
five classifier/session exports. Development may use:

~~~toml
[project]
dependencies = ["denubis-supervision==<matching-plugin-version>"]

[tool.uv.sources]
denubis-supervision = { path = "../brian-ed3d-plugins/plugins/denubis-external-agents", editable = true }
~~~

A path is mutable, **not** an immutable content pin; diagnostics record checkout
revision/dirty state. Proposed reproducible deployment uses the verified repository
origin, an exact commit and package subdirectory:

~~~toml
[tool.uv.sources]
denubis-supervision = { git = "<verified-repository-origin>", rev = "<full-commit-id>", subdirectory = "plugins/denubis-external-agents" }
~~~

Placeholders are deliberate: no future commit or deployment pin exists. Private owner
selects/records its deployed revision at integration. No floating branch, copied
classifier or fallback path-loader is the deployment contract.

## 2. Record schema and live authority

Database **agent_record** has owner/migration, app and reader roles under ADR 0026;
local_mail is untouched. Hooks connect only to the service. The package owns SQL,
constraints, queries/migration ordering; private host owns provisioning, credentials
and connection lifecycle. No daemon-specific table is an alternative Record.

These are proposed logical relations. Exact SQL/migration numbers belong to
implementation; consumers derive checked value sets from its actual schema.

| Relation | Contents, invariants and consumer |
|---|---|
| participants | Pane participant ID, harness, vendor session, project realpath, tmux server/window/pane, PID/start/domain, lifecycle generation, observation source/time. Paneless agents have no address (0025). Identity/mail consume it. |
| supervisor_instances | Instance UUID, supervisor participant/process/session, created_by human-command reference, started_at, ended_at/reason, daemon epoch. Enrollment history, not recoverable capability. |
| supervision_edges | UUID, supervisor instance/pane, supervisee participant/pane, window/server, harness pair, process/session evidence, created_by, task statement, created_at, retired_at/reason, generation. Self/cross-window activation refuses; every action needs live activation. |
| tasks | ID/project, current dispatch/return, checkpoint, review state and revision counter; updates compare expected revision. Workflow history does not grant actuation. |
| dispatches | Stable UUID, task/intended edge/worker/session generation, supervisor instance, subject, exact prompt/digest, rulings/original locators, context references, allowed files, constraints, evidence requirements, predecessor/expected return, request ID/time. Immutable; changes create another dispatch. |
| dispatch_receipts / control_attempts | Dispatch/action, intended identities, intent/staged/Enter/receipt observations, vendor prompt/turn, confirmed/refused/uncertain state, input digest, times/evidence. Same request ID with different content refuses. Missing receipt never proves unsent. |
| returns | Stable UUID, dispatch/task/edge/generation, checkpoint, exact manifest bytes/SHA-256, parsed manifest, deliverable text or proper project-file references, notes/evidence, superseded return/time. Store digest bytes, not a reserialized JSON substitute. Publication cannot approve itself. |
| reviews / releases | Exact return/digest, reviewer instance, disposition, independent evidence/durable report reference; release names exact revision and next dispatch. Compare-and-set rejects stale release. |
| events | Immutable UUID/producer occurrence, participant/edge/instance, vendor prompt/turn, hook source, observed/received times, kind and bounded payload/digest. Kinds: checkpoint, question, permission_request, completion, failure, telemetry. Lifecycle/activity are telemetry subtypes. Unknown cannot grant readiness/success. |
| mail / deliveries / ping_attempts | Mail ID, sender/recipient/context, subject/body/digest/references; read/ack/answer/withdrawal facts, pointer attempt/channel/outcome and unblocked-time ladder state. Offers use this mail path. |
| permission_requests / decisions / mandates | Occurrence-specific request, task statement, expiry/root, deciding actor/reason; policy denial terminal. Edge alone is not an approval mandate. |

FKs/transactions bind returns to actual dispatches and intended workers. Unique
producer occurrence absorbs duplicate hooks; identical text in a different proven
occurrence is new. Unknown occurrence is not joined by oldest command text.
Indexes support pending recipient deliveries/events and exact active-edge lookup.
Queries require both historical nonretirement and current live activation.

### History does not restore bindings

Service holds active membership for the positively identified supervisor instance and
current service epoch. Record rows preserve audit history; a row lacking live
registration authorizes nothing. Supervisor exit/process-session replacement/pane
closure invalidates its whole set; worker exit retires its edge. Reused pane/PID,
tmux server or boot cannot inherit it.

On service restart, prior activation is unavailable and never reconstructed from rows.
Proposed conservative failure behavior retires old activation and requires renewed
Brian-commanded enrollment. No restart-binding reconciliation. Ctrl-D/pane closure
need demonstrated live detection; missing hooks do not prove liveness. One shared
topology integration and bounded process checks serve registrations, not a watcher
per session. Platform detection remains unverified.

status/pending may expose history explicitly labelled inactive, never reenroll.
Vendor conversation resume is separate from restoring an edge (§6.4).
Mail/dispatch history remains readable under address/project rules. Withdrawal keeps
content, history, actor and reason as a tombstone and removes the obligation.
No pruning rule is introduced; a transcript pointer would not prove body retention.

## 3. One-call service protocol

### Explicit draft mechanics

Acceptance would accept these proposals; they are not asserted as previously ruled.

| Choice | Proposal and reason |
|---|---|
| Transport | Per-user AF_UNIX stream socket; one service for mail and supervision. |
| Discovery | DENUBIS_SUPERVISION_SOCKET override; else XDG_RUNTIME_DIR/denubis-supervision/service.sock; else platform temporary directory's denubis-supervision-UID/service.sock. No scan/auto-start. |
| Off | DENUBIS_SUPERVISION=off; zero connection attempts. Unset uses convention. |
| Permissions | Current-UID parent 0700/socket 0600; reject foreign owner, unsafe parent or symlink substitution. Same-user socket is not cryptographic authority. |
| Framing | One UTF-8 JSON object plus LF each direction, then close; maximum encoded frame 1 MiB including LF. Reject truncated/additional frames, malformed types and unknown versions before action. |
| Correlation | protocol_version=1, stable request UUID, explicit identities and expected revision. |
| Deadlines | Hook: 250 ms connect/1 s total. Driver read/write and worker get/put: 5 s total. Lifecycle/control: at most 190 s, allowing existing 180 s settle budget plus margin. No automatic retry; measure these proposed bounds. |

**Absent** means enabled with no socket at its configured path. **Down** means socket
exists but connection/protocol/deadline/Record readiness fails. **Off** is configuration,
not outage. A responding service without Record readiness returns unavailable with a
specific code. Invalid configuration never triggers another endpoint search.

Server validates peer UID where supported, then independently joins caller claims to
live process/pane/session. created_by text and client identity are audit inputs, not
proof that Brian commanded enrollment; the supervisor must carry his actual instruction.
Platform credential/process joins need tests.

~~~json
{
  "protocol_version": 1,
  "request_id": "<uuid>",
  "type": "pull",
  "caller": {
    "participant_id": "<id>",
    "session_id": "<vendor-id>",
    "pane_id": "<pane>",
    "supervisor_instance_id": "<current-instance>"
  },
  "expected_revision": 7,
  "payload": {"observations": [], "stop_hook_active": false}
}
~~~

Roles come from current registration, not caller assertions. A hook batches its
observations and pull in **one request**, never event then pull.

| Type | Operations, consumers and response data |
|---|---|
| event | Append one event/bounded batch from a hook/report; accepted IDs/duplicate status. Completion claim is not verification. |
| pull | Supervisor Stop ingests observations then offers one pointer or null for its instance/context; no body. |
| register-edge | spawn/bind: record intent, execute package driver validation/spawn, activate confirmed edge; actual IDs/configuration or pending/refused/uncertain. |
| retire-edge | Retire exact edge/ending instance set. shutdown mode first attempts guarded owned-process exit; uncertain exit prevents further driving and preserves unresolved outcome. |
| dispatch | create/get/send/receipt are deliberate separate operations. send executes full guarded action in the shared handler; get returns only assigned brief. |
| return | put/get/review/release. Release uses prepared dispatch and exact return/revision, without a client read-then-write race. |
| pending | Scoped outstanding pointers and blocked/inactive/uncertain state; no acknowledgement. |
| ping-ack | Pointer attempt observed by recipient/context; not body read, comprehension, mail ack, review or release. |
| control | Extra type needed by status/interrupt/compact/fresh/resume; commands are not disguised as events. |
| mail | Extra type for put/read/ack/withdraw; first consumers are mail and offers. Body reading and acknowledgement remain deliberate separate calls. |

A driver command is one RPC; the server calls the package driver engine. It commits
intent before terminal effects without multiple client/service calls. Internal tmux
preflight/input/confirmation stays inside that driver action. Hooks neither shell out
for repeated lookups nor touch Postgres.

An action holds a per-edge control lock with short transactions around external effects.
It does not hold a DB transaction/event-ingestion lock while waiting for hook receipts:
concurrent hooks must be ingested during send, or the action deadlocks its own receipt.
Same request ID returns saved result/pending/uncertain; changed payload refuses.
Database idempotency does not make terminal input exactly-once.

Responses carry version/request ID, status and data. Pull success:

~~~json
{"protocol_version":1,"request_id":"<uuid>","status":"ok","data":{"pointer":{"id":"return:<uuid>","subject":"Contract checkpoint"}}}
~~~

Empty pull has <code>"pointer": null</code>. Prefix types the ID; subject is bounded,
printable single-line text. No brief/answer/offer explanation/body crosses ping channels.
Deliberate get/read returns bodies. Errors carry refused/unsupported/unavailable/
uncertain status, stable code and bounded diagnostic, no credentials/arbitrary output.

### Exact unavailable behavior

| Situation | Hook | Driver/worker client |
|---|---|---|
| Off | Exit 0; one stderr line “supervision: disabled”; no connection/block. | Typed disabled, nonzero for requested service operation; no side effect. |
| Socket absent | Exit 0; one stderr line “supervision: absent: service socket not found”; no block. | Unavailable/absent, nonzero; no actuation. |
| Down/timeout/Record unavailable | Exit 0; one stderr line “supervision: down: CODE”; no retry/block. | Unavailable before action, uncertain if effect/commit may have occurred; nonzero, no replay. |
| Malformed/unsupported input or response | Exit 0; one bounded stderr diagnostic; no authority change. | Refused/unsupported, nonzero. |
| uv missing | Fixed launcher emits its single installation diagnostic and exits 1 before Python, distinct from service absence. | Explicit launcher failure, no bare-Python fallback. |

Stop's nonblocking stdout is an empty JSON object; other observational hooks emit none.
One package diagnostic maximum per invocation; ordinary no-work success is silent.
Diagnostics distinguish availability, not model-facing mail. uv startup/install failures
are outside the service-call deadline. Failed events are reported, not spooled into a
parallel journal; observation gaps make corresponding state unknown.

## 4. Pull, idle ping and the ladder

A registered supervisor's Stop hook sends pull with its Stop observation. The service
records that boundary/valid return reference, then selects one unhandled item. For a
pointer the hook exits 0 with:

~~~json
{"decision":"block","reason":"Read Record return:<uuid>: Contract checkpoint"}
~~~

Vendor adapters use their documented Stop continuation shape. The supervisor resumes
to read the body, inspect actual artifacts and decide; this does not approve the worker.
No item returns an empty object and lets Stop finish. A worker's Stop reports its
checkpoint and ends, rather than returning block to hold a checkpoint.

Record distinguishes offered/attempted, ping-ack, body-read, mail-ack, reviewed and
released. A pull claims one pointer attempt per recipient context/item; the next Stop
must not block again on the same unacknowledged offer. Supervisor reads it and sends
ping-ack deliberately. Ignoring it leaves an obligation for the ruled ladder.
stop_hook_active is recorded/tested, neither blocked forever nor used to discard new
events. No continuation cap is changed to sustain the loop.

An **idle candidate** exists only after this supervisor's Stop pull returned null and
no subsequent turn-start/activity superseded that Stop. UserPromptSubmit, continued-turn/
tool activity, lifecycle changes and detected background work invalidate it. Missing
events without demonstrated hook coverage mean unknown. Before ping, the driver checks
live identity/window, unblocked state and empty composer/UI. Busy/changed target refuses.
The missing-event/concurrent-human-input race is not an atomic tmux transaction.

During ordinary work, queue until Stop. For proven idle supervisor, offer one pointer:

- **Claude:** proposed native channel is messagingSocketPath from
  <code>~/.claude/sessions/&lt;pid&gt;.json</code>, bound to actual process/start/session.
  **Socket protocol and fully idle interactive wake are unverified; this is the first
  live test.** Prior registry metadata is not proof of a supported delivery API.
- **Codex:** checked hooks docs establish no fully idle native wake. Use the package
  driver's guarded tmux one-line ID/subject delivery. deliver_ping accepts only the
  enrolled recipient and pointer, never a body, command, approval key or arbitrary target.
- ADR 0018 allows the guarded fallback when native Claude delivery is unsupported or
  fails. A possibly delivered native ping cannot trigger a blind second terminal send.

Recipient notification differs from supervisor control of workers. Enrollment permits
notifications to that supervisor itself, not a self-edge or self-control via ordinary
verbs. Shared driver owns keystrokes in both cases, under distinct narrow contracts.

Each actionable occurrence is announced once; an empty wake produces no user-facing
waiting message. No per-supervisor monitor/listener, blocking watch or thirty-minute
re-arm remains. One daemon owns shared topology/event integration and due delivery
state, including while models are idle; running service does not prove model receipt.

Ladder clocks follow ADRs 0015–0017 **as amended by 0021**: unblocked time, busy or idle.
One configuration owner supplies 120 s grace, two nudges at least 10 min apart,
interrupt after the second gap, stuck 30 min after first nudge or immediately on refused
interrupt, and stale at 2 h for acknowledged unanswered question. Blocks pause clocks;
clearing them resumes elapsed time rather than restarting.

Due nudge/interrupt is an intent for the live supervisor. An unblocked supervisor may
interrupt its busy supervisee through the driver, confirming stopped turn before re-ping.
Dialog/unknown identity/unreadable state refuses. Recipient without supervisor skips
interrupt. **A blocked supervisor is Brian's item: daemon never exercises its judgement
or interrupt authority for it.** Ordinary busy work waits for Stop except when the
accepted ladder calls for escalation. No clock answers questions or acknowledges mail.

## 5. Hooks as one-call clients

Relay is operational metadata, not generic instruction injection. Install lifecycle
registrations separately at user level for each vendor, preserving
[the marketplace action boundary](../../tests/test_instruction_delivery.py).
Do not put UserPromptSubmit in marketplace hook files. Global installation does not
create supervision: only Brian-commanded live enrollments activate routing/continuation.

### Documentation boundary

On 2026-10-24 [Claude's hooks reference](https://code.claude.com/docs/en/hooks) documented
prompt correlation, effort observations, lifecycle/model events, Stop background arrays
and block-with-reason continuation. Missing arrays are unknown. PermissionRequest lacks
tool_use_id; suggestions are not dialog options. These are docs, not actual hook
emissions observed in this stage.

[Codex's hooks reference](https://learn.chatgpt.com/docs/hooks), checked the same day,
documents SessionStart/End, UserPromptSubmit, tool events, PermissionRequest,
Pre/PostCompact, Stop and Interrupt. Stop block-with-reason continues; turn_id correlates
a turn. Its checked event list provides no PostModelSwitch, StopFailure or Claude-style
background arrays. Model is common input; hook-provided effort/context was not established.
Actual trust/loading requires a canary, not a configuration file.

### Four roles

An instance may be worker and supervisor. One invocation sends its observations in one
request, and the service resolves roles. A worker paused for review cannot auto-continue
because it also supervises another pane; its blocked supervisor obligations are exposed
under ADR 0021 until that pause ends.

| Role | Vendor events registered by installer | One-call contents and output |
|---|---|---|
| Claude worker | SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, Notification(permission_prompt and idle_prompt), PreCompact, PostCompact, PostModelSwitch, Stop, StopFailure | Non-Stop event batches report activity/lifecycle, permission hints/requests, tool/API failures and allowlisted telemetry. Stop sends event with return/checkpoint/question reference and quiescence; exit 0, no continuation. |
| Claude supervisor | Same Claude set | Non-Stop clears idle evidence and updates known block/configuration. Stop sends pull with observations, block/reason only for an eligible new pointer; otherwise empty object. |
| Codex worker | SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, PreCompact, PostCompact, Stop, Interrupt | event reports activity, receipts, compact/interruption and actual supplied telemetry. Stop sends correlated claim and ends normally. No invented Claude event. |
| Codex supervisor | Same Codex set | Non-Stop reports state; Stop sends pull and Codex block/reason for eligible new pointer. Interrupt/SessionEnd never resume work. |

PermissionRequest in the minimum is **observational**: report and return no permission
decision. Existing permission policy runs first. Hook input is not proof a dialog
survived sibling policy hooks. Notification hints prove neither completion nor a native
question tool. Explicit ticket/return identifies questions, not trailing punctuation.

An executed tool error is activity telemetry, not a process crash or automatic task
failure. Meaningful RED can deliberately include a nonzero tool result. Only a
confirmed process/API failure produces the corresponding failure observation.

Minimum reports permissions and parks judgement requests. Ruled narrow approval is not
withdrawn; its later application tranche needs occurrence/first-answer evidence (§11).
A future held-hook adapter uses one held invocation/request and typed vendor result,
not repeated shell calls. Its accepted deadlines/application path are separate from
the 1 s observational client, which is not claimed to implement held approvals.

### Telemetry and offers

ADR 0041 allows values actually supplied by the worker's own hook or already available
statusline payload, with source event, session/generation, time, units and null/unknown
distinction. Requested model/effort remain separate launch inputs. Clear/switch/missing/
wrong-generation readings invalidate configuration; effective mismatch/unsupported
settings block substantive dispatch without substitution. A setup canary can establish
supported fields before actual work.

[Statusline documentation](https://code.claude.com/docs/en/statusline), checked
2026-10-24, exposes model/effort/context and optional quota, including absent/null
readings. Install no replacement, wrapper or composed exporter over the operator's
statusline. Accept an already integrated bound producer's allowlist via event if present;
otherwise context/quota are unknown. Hooks are not asserted to receive statusline JSON
automatically. Codex normalized telemetry follows the same reported-value rule.
Its screen context floor remains a safety preflight, not fabricated hook telemetry.

Reuse [supervisee-offers.py](../../plugins/denubis-external-agents/hooks/supervisee-offers.py)
and its pure parsing/attribution where ADR 0028 fits. Move shared behavior into the
package once. Current source finds team members via team/transcript layouts, reads
the builtin store, emits bodies as additionalContext and updates a pane option before
display. That is observed source, not the new transport.

Migrated hook makes one request asking shared service to collect caller's registered
supervisee offers. Package adapter uses current edge/session identities and retained
store parsing, commits bodies as mail with sending pane/session/digest, then offers a
pointer. Hook no longer enumerates transcripts or shells out for dedup. Standalone
registered workers are addressable without inferring team membership. Unbound team
members never silently become edges. Keep interim behavior until Record integration;
replace its transport together rather than create two simultaneous stores.
Missing/unreadable store or attribution is visible; view lifetime/native layout remain
unverified.

Client hooks ignore transcript_path and arbitrary results. Retain only bounded
correlation/configuration fields; scoped request details follow permission-record audit.
Detected paneless callers are refused as participants and recorded as anomalies.
Where detection is unavailable, report that limit.

## 6. Driver contract, resolution and send safety

### 6.1 Retained vendor equivalence map

[Current Codex driver](../../plugins/denubis-external-agents/scripts/codex_supervisor.py)
is the source baseline, not a Claude API.

| Existing Codex mechanism | Claude counterpart or evidence limit |
|---|---|
| Unique foreground Codex discovery | Live edge/process/registry join; multiple workers and self exclusion replace uniqueness. Bash wrapper is not Claude identity. |
| Ready/Working title and spinners | Separate native/UI evidence; absent spinner is not readiness. Unknown refuses. |
| Codex composer marker/ANSI placeholder | Claude empty/nonempty/unreadable recognizer, no copied marker or hidden-draft assumption. |
| Approval labels/narrow choice | Current Claude occurrence plus verified dialog; suggestions/position insufficient. |
| Queued widget/catalogue stripping | Spawned Claude denies AskUserQuestion; §7 ticket path. Bound native dialogs remain blocked for human handling. |
| Codex process-held session | Claude registry session/PID/start/domain joined to process/foreground; no transcript heuristic. |
| Clear/new held Codex session | Claude correlated clear lifecycle, changed session, later idle/configuration evidence. |
| Compact/same session/marker/meter | Claude manual completion and same session; no assumed percentage gain. |
| Codex context floor | No Claude floor introduced; reported telemetry or unknown. Preserve Codex preflight floor. |
| Codex rollout quota/status fallback | No Claude transcript/account scrape; supplied telemetry or unknown. Keep existing bounded Codex quota behavior. |
| Topology failure | Claude process/session loss or actual failure, distinct from expected exit/unavailable observation. |
| Codex hook normalizer | Separate Claude normalization retains prompt/Stop/return; end of turn is not verification. |
| Codex global installer/trust | Vendor-specific merge/trust/canary; no copied Codex trust recipe for Claude. |
| Codex model catalogue/spawn flags | Claude explicit Opus/effort/restriction/session flags checked in help; launch request is not effective proof. |
| Per-pane datagram monitor | Shared RPC/Stop pull/idle delivery, no receiver or re-arm. |

### 6.2 Identity and standing defaults

Live edge binds supervisor instance/pane/process/session, worker pane/harness/process/
session, tmux server/window, boot/process domain, project realpath and generation.
Every operation resolves caller's current pane/window, selects named edge, excludes
caller pane/process/session, then revalidates immediately before actuation.
Another valid worker is not ambiguity for the edge; conflicting matches are.
A lost target never falls back to the only remaining agent. Wrapper ancestry, redocking
and PID reuse need positive evidence.

Worker defaults at /home/brian/.claude/CLAUDE.md lines 31–34, read here:

> Workers default to the latest available Opus at xhigh in Claude and Sol at xhigh in Codex, on the same infrastructure as their supervisor.
> Set and verify model and effort explicitly at dispatch; these defaults need no further permission. Carry them into delegated prompts.
> Launching a new Astra or Fable worker requires the human to name that model and effort; this does not require reauthorizing the supervisor
> session the human already selected. If a required model or effort is unavailable, report the limitation before substituting.

spawn resolves/passes explicit model/effort. Codex keeps ADR 0027's one catalogue read
and visible fallback. Claude passes latest-available Opus/xhigh; an alias is a request
until the session reports its actual model. Astra/Fable require Brian's named model
and effort; task difficulty/inheritance supply neither. No new selection permission for
ordinary defaults. Scratch permission remains separate; no Astra supervisor launches here.

### 6.3 Retained send sequence

Every keystroke, including service pointer delivery, goes through the package driver.
No raw tmux escape hatch.

1. Validate live edge/project/session/configuration, checkpoint and immutable dispatch.
   Commit intent before typing.
2. Require ready/idle, visible known-empty composer and no permission/question/trust/
   selection dialog. Unknown/busy refuses; keep Codex context-floor preflight.
3. Type short ID/subject literally via argv/stdin, not shell interpolation. Use a unique
   buffer if paste is necessary.
4. Capture before Enter; require expected literal content or verified vendor representation.
   Do not clear another person's draft or use Escape/Enter to discover state.
5. Revalidate identity, submit, correlate exact envelope with UserPromptSubmit and vendor
   prompt/turn ID. Receipt differs from accepted/running: another hook can still block.
6. Missing/mismatched confirmation is uncertain. Quiet/idle never justifies resend.
   Proven-unsent retry is explicit; uncertainty remains pending.

New Claude dispatch uses **one Enter**, no automatic retry. Existing Codex send has up
to three Enter attempts; extraction preserves it unless separately reviewed Codex work
changes that behavior. New Record dispatch adds no retries around it and reports its
existing confirmation limits. Working/empty composer alone does not satisfy the stronger
Record receipt needed for checkpoint release.

Literal multiline remains later work until byte correlation is demonstrated.
Paste placeholders differ. Private paste cache is not a session-bound receipt API and
is not read. Detected UI change refuses, but driver lock cannot prevent human typing
between capture and Enter; no atomic terminal transaction is promised.

### 6.4 Minimum verbs

Results name edge/task/session, source/age, confirmed facts and uncertainty.
These **twelve** verbs are the minimum; no monitor or journal.

| Verb | Preconditions, confirmation and refusal |
|---|---|
| spawn | Brian-commanded; explicit resolved model/effort, real project directory. Record intent, spawn in caller window, verify actual identity/configuration then activate edge. Other worker does not prevent distinct edge; uncertain startup never repeated. |
| bind | Brian names existing pane in supervisor window; validate project/process/session, exclude self/conflicting ownership. Discovery alone cannot enroll. |
| status | Bounded identity/UI/edge/checkpoint/pending evidence and reported telemetry or unknown. Refuse unrelated capture; history labelled inactive. |
| send &lt;dispatch-id&gt; | Exact immutable dispatch intended for this live edge/current checkpoint. Guarded pointer send; changed/reused IDs and unresolved prior submission refuse. |
| pending | Scoped outstanding items including blocked/inactive/uncertain; no read/ack/release. |
| review | §8 stopped/quiescent barrier; exact return/digest, accept/correction-needed/needs-human and independent evidence. Human source must resolve; no implicit continuation. |
| release | Compare current return/review/revision and dependencies; send prepared next dispatch once for exact revision. Stale review/completion cannot advance newer work. |
| interrupt | Known running target, no modal; one vendor interrupt and confirmed stop. Dialog/unknown/idle refuses; interrupted is not complete. |
| compact | Parked idle/empty/no unsettled action. Dedicated full command/selected completion, correlated manual completion/same session; unknown is not context gain. |
| fresh | Parked plus self-contained next brief; dedicated clear, changed session/generation and later idle. Update existing live commanded process relationship, invalidate receipts/configuration; no substantive dispatch until configuration known. |
| resume | Same live relationship: inspect and explicitly continue settled checkpoint, never replay uncertain send. Ended process/instance requires renewed Brian enrollment and new edge before exact vendor resume. |
| shutdown | Guarded owned-process exit plus observed end/edge retirement. Instance shutdown retires its whole set. Unknown/background detach is not shutdown or task success. |

Existing Codex resolve/tail, quota, default-model, literal message, widget inspection/
answer and soft-retired approve retain suitable regression coverage and edge scope.
New Claude literal-message/answer convenience/approval application remain later work,
not minimum prerequisites. Unsupported operations report that, never type approximations.

Approval is task-specific judgement (0013/0035), expiry/root, policy-deny precedence
and request/task/reason audit (0022), separate from send/release. Property 7 prevents
same-family approval mandates until Brian rules, while same-family pane control works.
This design authorizes no commits, publication, shared Google writes or Discord posts.

## 7. Questions and their answer path

Spawned Claude workers receive <code>--disallowed-tools AskUserQuestion</code>.
The [CLI reference](https://code.claude.com/docs/en/cli-reference), checked 2026-10-24,
documents tool denial and explicit model/effort/session flags. Installed 2.1.305 help
lists the relied-on options. Enforcement/effective model support is unverified.

Worker writes one specific ticket in the operational destination:
the <code>project_open-questions</code> file in the main checkout's notes directory,
resolved through Git's common directory. Include question, blocking consequence, evidence and raising
worker; put its ID/reference in a return and end the turn. Stop event and supervisor
pull carry its pointer; supervisor reads body from Record/project ticket. Failed return
publication stays unconfirmed, never answered.

Supervisor reads project context and relevant open ticket, searches decisions/notes,
then prior chats only if needed. An existing answer closes it only after original human
record, scope and supersession are verified; cite that record rather than restating an
inference. If no valid answer exists, ask Brian once, as one plain-text question, and
end the turn. Supervisor's own permission block is Brian's item too.

A new ruling goes to the indexed register with question, Brian's words verbatim and
original-message resolver. A factual answer goes to useful documentation with a
resolvable source. Remove answered ticket. Record answer reference against its blocked
return/dispatch; release only that dependency. Silence, expiry, time and confidence
cannot answer. Codex spawn keeps question-tool exclusion; a manually bound native
dialog is surfaced, never silently dismissed.

These paths specify future operational destinations, not citations to ignored memory
as evidence. §12 lists the unresolved citation exemption without granting it.

## 8. Checkpoints, cooperative pause and failure

### Manifest and publication

Retained brief names task/dispatch/checkpoint, allowed files, constraints, acceptance,
required evidence, verbatim rulings/resolvers and supervisor-asserted claims marked
verify-before-relying with source commands. Prohibit background jobs, paneless delegates
and scheduled work spanning submission, automatic commits/publication and unrelated work.

Worker uses the package's supervision-record data client to read its assigned dispatch
in one call and put its return from stdin in one call. It is provisioned with the
package in the controlled worker environment, not installed ad hoc during a checkpoint.
Files stay in their repository; Record refers to them rather than copying a source tree.
Return text/bounded evidence can be deliverables. Durable documents land at proper
project paths before being cited.

Amended manifest:

~~~text
schema_version, task_id, worker_id, edge_id, binding_generation, session_id,
dispatch_id, dispatch_sha256, checkpoint, submission_id,
artifacts[{project_relative_path, bytes, sha256}],
evidence[{command_argv, cwd, exit_status, output_ref, output_sha256}],
unresolved_question_ids, claimed_result, supersedes_submission_id
~~~

Store exact bytes/digest. output_ref names return evidence or an existing proper project
file. Resolve paths inside allowed roots with no traversal/symlink escape; check bounds,
readability, actual changed-file inventory and exact output digest. Hashing identifies
bytes, not correctness or completeness of a worker's declared set.

After successful return put, retain final-line fields with stable return ID replacing
the ephemeral file locator:

~~~text
CHECKPOINT task=<T> dispatch=<ID> manifest=return:<return-id> sha256=<manifest-digest>
~~~

Return row carries that manifest digest. Generic DONE, quiet pane, exit or Stop without
matching return is an observation/claim only. Independently correlate vendor receipt/
turn; never rewrite a worker manifest to manufacture its binding.

### Barrier and loop

Review needs exact live edge/session/generation, dispatch, vendor prompt/turn, return
and digest, correlated Stop and positive idle/quiescence. For Claude both background
arrays must be present/empty. Codex has no established equivalent: require verified
lifecycle/tool completion, no outstanding registered work and positive process/UI
evidence. If that cannot establish quiescence, hold review/release as unknown, never
turn absent fields into empty lists. Fresh activity invalidates the barrier. Rehash
manifest/evidence/working artifacts before disposition/release; drift needs new return.

**Paused** without a gate means cooperative worker has ended its turn and receives no
continuation while supervisor verifies. There is no parked-worker PreToolUse denial
gate or OS freeze. Same-turn post-publication edits cannot be reviewed until Stop;
persistent drift rejects the revision. Hashes do not detect every transient write and
restore or stop arbitrary same-user processes. A gate is future work only if an
authorized live check demonstrates existing checks insufficient; uncertainty holds
release rather than silently adding enforcement.

~~~mermaid
stateDiagram-v2
    [*] --> Prepared
    Prepared --> SubmissionPending: commit intent and submit
    SubmissionPending --> Running: correlated receipt and accepted activity
    SubmissionPending --> Uncertain: interrupted or missing confirmation
    Running --> ReturnPending: return plus matching Stop
    ReturnPending --> Reviewing: identity, quiescence and digest
    Reviewing --> Prepared: exact review and explicit next release
    Reviewing --> NeedsHuman: unresolved requirement or permission
    NeedsHuman --> Reviewing: original answer recorded
    Reviewing --> Verified: independent final checks
    Running --> Interrupted: confirmed interrupt or process loss
~~~

Loop remains contract proposal → supervisor review → behavioral RED → supervisor checks
actual failure → minimal implementation → independent verification → correction or
final review. Each release names exact preceding return/digest. Green worker report
starts verification, not dependent work. Final review differs from Brian's UAT/commit/
publication authority.

### Failure and resumption

Record preserves dispatches, returns, questions, reviews and delivery uncertainty;
instance termination ends live edges. New supervisor can read history but needs Brian's
command before driving. Worker death records failure/interrupted, retires edge and
preserves artifacts/findings. Vendor resume requires newly commanded validated edge;
old release cannot confer driving authority.

Crashes before/after intent, paste, Enter, receipt or commit can leave uncertain effects.
Reuse matching receipt, but missing receipt is not proof of no submission. Next caller
inspects saved attempt and actual bound state, never auto-retries. Old Stop/return/
review/release replay after new dispatch cannot advance its revision. Same request
deduplicates in Record; terminal delivery is not exactly-once.

Ping attempt and recipient acknowledgement differ likewise. Response loss after commit
leaves visible uncertainty. No delivery claim from an attempt row and no automatically
repeated human question. Deliberate pending/read recovers work without reviving an edge.

## 9. Bootstrap and prerequisites

Record and proposed supervision daemon are **not available** as the design's starting
condition. Existing permission-queue viewer is not proof otherwise. This stage creates
no database, implementation or live session.

Build/test in dependency order:

1. Package classifier and first real CLI/import consumer together; preserve covered
   behavior while amending explicit target/runtime rules. Installed wheel exposes same
   classifier to private consumer, with no private checkout needed for imports/tests.
2. Ship migrations with Record operations and actual PostgreSQL tests. Tests create an
   isolated local cluster/database, socket directory and owner/app/reader roles, never
   reuse developer agent_record/local_mail. Exercise constraints/transactions/role
   access and concurrent stale release. Locate installed PostgreSQL binaries; missing
   binaries/cache access block gate, not trigger invented cache/download paths.
3. Fixture AF_UNIX server uses shared handler with controlled Record/process/tmux
   collaborators. Real hook/driver CLIs exercise framing, one call, availability and
   side-effect confirmation without private daemon. Fixture mode is labelled, never
   automatic production fallback. Another integration fixture uses isolated PostgreSQL
   with that handler.
4. Private repository supplies real daemon process, config/connections, systemd user
   unit and viewer integration, pinned to package. Deployment becomes required before
   actual Record exchange, Stop pull, idle wake or end-to-end supervision. No file
   journal/old monitor substitutes.
5. After design acceptance and explicit scratch/setup permission, first test idle
   Claude socket wake, then captures/full demonstration. New Astra/Fable additionally
   requires Brian's model/effort. Parked scratch ticket remains binding.

A colleague without private repository can install plugin/package, use nonservice
tooling and deterministic fixtures. Requested supervision reports unavailable until
compatible service is configured; hooks retain §3 nonblocking diagnostics. Package
installation alone does not deploy a Postgres-backed service.

## 10. Supervising-codex and runtime migration

Revise [existing skill](../../plugins/denubis-external-agents/skills/supervising-codex/SKILL.md)
with its driver. Preserve distrust of both worker and supervisor claims, verbatim rulings,
independent verification, human-owned commits, redaction, literal transport, context
hygiene and escalation.

| Existing boundary | Replacement |
|---|---|
| Ignored file exchange/numbered prompt/output directory | Immutable dispatch/get and return/put IDs, proper durable outputs (0041/0042). |
| Unique agent in window/no enrollment | Brian-commanded spawn/bind, many live edges and self exclusion (0037/0039). |
| Bare invocation watches; Monitor timeout/re-arm instructions | Bare invocation shows help/refuses missing verb. Stop pull/idle ping replace loop and host wait/re-arm recipe (0039). |
| Quiet/DONE starts settling | Correlated return/Stop/quiescence/digest, then independent review. |
| Per-pane datagram HookReceiver | One service request, events/pending pointers; no second listener/store. |
| Offer body in additionalContext | Commit mail first, ID/subject pointer (0018/0028/0041). |
| File-only publication | Worker return put, supervisor review/release (0041). |
| Driver 3.12 / installer 3.9 | Repository floor 3.14 throughout migrated package/entry/client (0038 consequence/0040). |

[install-codex-hooks.py](../../plugins/denubis-external-agents/skills/supervising-codex/hooks/install-codex-hooks.py)
is **operator-run setup**, despite its directory name, not a lifecycle hook. It writes
global .codex/hooks.json entries running driver's --hook relay. Current source declares
>=3.9 and emits uv run --no-project --no-config python followed by that relay: the
launcher defect being migrated.

Add PEP 723 >=3.14 metadata to relay and change generated registrations to the fixed
preflight/script launcher. This is shell text emitted into configuration, not an
instruction to run a new registration during this stage:

~~~sh
command -v uv >/dev/null 2>&1 || { echo "codex_supervisor: uv is required to run this hook; install it from https://docs.astral.sh/uv/getting-started/installation/" >&2; exit 1; }; uv run --script --python '>=3.14' --no-project --no-config "<resolved-plugin-root>/scripts/codex_supervisor.py" --hook
~~~

Installer itself moves to >=3.14, invoked **by hand** through uv script mode at that floor;
retire its own py39 root-pyproject row then. Preserve foreign hooks, merge/idempotency,
moved-path repair and human trust review. No settings/cache edits in this design stage.

Retire [test_codex_supervisor_python_floor.py](../../tests/test_codex_supervisor_python_floor.py)
**with installer/relay migration**, never hollow it into a passing different contract.
Its lower-floor consumers disappear with script-mode relay and private package dependency.
Separate deserialize_observation except clauses may collapse under 3.14, permitted by
changed runtime boundary, not mandatory source wording.

[Current launcher suite](../../tests/test_hook_uv_script_contract.py) covers marketplace
hooks, not installed user relay or nested installer. Extend observable coverage or add
integration checks that execute installer-generated commands under temporary HOME/PATH/
old UV_PYTHON, safe fixture endpoint and missing-uv control. Marketplace glob is not
evidence for installed relay. Exact preflight is a declared launcher contract, but actual
execution must also be checked.

Keep Codex catalogue filtering/resolver, context floor, literal send/refusal, slash
selection, distinct clear/compact confirmations, quota scope and queued-question handling
unless named ADR changes them. Explicit parser/help migration must not silently treat a
prompt-file argument as dispatch ID.

After implementation, update [existing context owner](../architecture/plugins/denubis-external-agents/0-context.md)
to actual package/service boundary and ADR 0027 default rule. Do not describe future
architecture there as already implemented.

## 11. Behavioral tests, phases and acceptance

This is a future test plan. No product/database suite, installer, daemon or live session
ran during drafting. Root pyproject owns runner configuration; retain each command's
own exit/output. Use red-green-refactor for behavioral changes. No source wording,
private-structure or incidental snapshot tests.

### Outcomes and retained stage-1 coverage

| Outcome / old coverage | Consumer-visible success and refusal/failure control |
|---|---|
| A1 identity/pairs (T01/T02) | Both CLIs route to selected edge among two workers in all four harness pairs. Self, wrong window/project/session, reused PID/start/domain/server, unbound/conflicting edge cause no typing. Lost target never substitutes another. |
| A2 safe send (T03–T07) | Exact pointer reaches intended worker with correlated receipt. Busy/shell, visible or hidden draft, cropped/unknown UI, dialog, identity/selection change refuses before Enter. Missing receipt is uncertain with no surrounding resend; preserve named legacy Codex boundary. |
| A3 exact checkpoint (T08/T09) | Matching return/Stop, positive quiescence and unchanged bytes permit review. Old generation/turn, missing/nonempty arrays, outstanding work/drift prevent review/release. No continuation while reviewing. |
| A4 artifacts/RED (T10/T11) | Actual changed inventory, allowed paths/digests and exact command output support review. Traversal/symlink escape, omitted changed files, changed evidence, collection errors/unrelated RED cannot release implementation. |
| A5 challenged correction (T12) | Independent counterexample rejects plausible wrong revision; same real worker corrects under new return, old acceptance cannot release new bytes. |
| A6 lifecycle/loss (T13/T14/T16/T24) | Distinct interrupt/compact/fresh/shutdown effects. Death retires edge; new supervisor/service epoch cannot drive from old rows. Renewed Brian command/exact vendor resume creates new edge without replay. |
| A7 uncertain effects (T15/T21) | Kill fixture handler around intent/paste/Enter/receipt/commit. Reuse proven result, keep uncertainty pending; terminal gets no duplicate dispatch on reconnect/response loss. Attempt row never claims pointer receipt. |
| A8 questions (T17) | Denied tool control and one ticket/return reach pull. Existing answer requires original-source/scope/supersession proof; new answer gets indexed owner and ticket removal. Empty/expired answer never settles. |
| A9 permissions (T18/T19) | Minimum reports current request/refuses ordinary send into dialog. Later application checks occurrence/task/expiry/root/policy/audit with valid-request control; same-family mandates unavailable. Competing held/native answers need separately authorized first-answer-wins test. |
| A10 pull/ping/ladder (T20) | Busy supervisor gets no ordinary push; Stop one pointer; empty Stop silent; idle uses guarded pointer. Duplicate/busy-flicker/ignored-Stop does not loop/re-ask Brian. Scripted clocks follow accepted ladder; block pauses them, blocked supervisor never causes daemon substitution. |
| A11 hook/install (T22) | Generated relay executes >=3.14 despite older UV_PYTHON. Missing uv: one line/exit 1; absent/down service: one line/exit 0; off: no connection. Foreign hooks survive, moved path repairs once. Malformed/oversized/wrong-session/paneless input grants nothing. |
| A12 telemetry (T23) | Bound values report source/age; absent/null/stale/wrong-generation unknown. Clear with no model cannot reuse old one. Default args are not effective proof. No statusline replacement. |
| A13 package/consumer (T25 amended) | Install wheel in isolated consumer and exercise five exported classifier/session results from foreign CWD. Complete plugin scripts work; no private checkout/CWD shadow import. Revised supported floor is 3.14 only. |
| A14 Record/protocol (new) | Real isolated PostgreSQL tests constraints/occurrence/idempotency/CAS release. Stream fixtures test partial/extra/oversized frames, old version, timeout/response loss, concurrent hook receipt during send and one client request. Malformed traffic causes no actuation. |
| A15 mail/offers (new) | Read recovers exact body/sender after mail commit; ping only ID/subject. Duplicate view yields no second delivery; failed commit never marks delivered. Withdrawal preserves tombstone; store/identity errors visible. |

Inspect actual consumers: bytes/target/Enter, Record constraints/rows, public refusal/
status, hook stdout/exit and delivered body. Mock count alone cannot prove delivery or
pause. Every refusal has a permitted positive control. Fixture Postgres/processes own
cleanup; missing required binaries mean an unrun gate, not a successful skipped suite.

| Existing suite | Migration reason and retained behavior |
|---|---|
| test_codex_supervisor.py | Replace test_select_codex_pane_requires_exactly_one_candidate/test_spawn_refuses_multiple_joined_codex_panes with selected-edge success among several and conflicting-edge refusal. Extend test_discovery_lists_only_callers_exact_window for self. Keep malformed-row/cwd/sandbox/model/send controls. |
| test_codex_supervisor_announce_once.py | Exercise announce-once/busy-flicker/new occurrence through Record pull/ping. Retire removed monitor-loop termination expectations; preserve notification/loss outcome. |
| test_codex_hooks_installer.py | Preserve foreign/idempotent/moved-path behavior; execute generated relay and vendor outputs for absence/down/off/old UV_PYTHON. |
| test_codex_supervisor_python_floor.py | Retire whole suite with installer/relay migration (0038); replace consumer outcome with 3.14 launch/import integration. |
| test_hook_uv_script_contract.py | Keep marketplace contract; cover installed relay/nested installer gap through execution. |
| test_supervisee_offers.py | Keep parser/attribution/store errors; transport commits mail before pointer instead of context body/pane-option dedup. |
| test_codex_supervisor_classify.py, test_codex_supervisor_approve.py, test_codex_supervisor_default_model.py, test_codex_supervisor_queued_questions.py, test_codex_supervisor_slash.py | Preserve behavior outside ruled changes; update import/patch boundaries after extraction, not outcomes to hide defects. |
| test_instruction_delivery.py, test_marketplace_sync.py, test_codex_marketplace.py | Keep action boundary and release consistency; user lifecycle registration stays separate. |

### Coherent phases

Future outcomes, not implementation or launch authorization:

| Phase | Dependencies, usable outcome and gates |
|---|---|
| P0 — package and coordinated consumers | Accepted design and private owner's authorization for classifier migration; package/extract with thin Codex entry and installed-wheel consumer. Migrate installer/relay to 3.14, retire 3.12 suite, and replace private classifier path-load with pinned package dependency as one coordinated outcome. Preserve existing transport until P2 changes it. Relevant regressions and ruff/format/ty/complexipy on all moved/new code, maximum 15; A1/A13 and A11 runtime boundary. No new daemon/model needed. |
| P1 — Record/protocol with fixture clients | P0; migrations/transactions plus fixture stream handler and first real hook/CLI consumers. A7/A11/A14 and deterministic mail bodies. Isolated Postgres, malformed/absent/down/off and concurrent receipt gates pass; no production fallback. |
| P2 — instance control/checkpoint clients | P1; twelve minimum verbs, both adapters, return/review/release, questions, role-aware pull, telemetry and offer transport in fixtures. Switch relays from old transport to shared-service clients; P0 already owns launcher/floor migration. A1–A4/A6–A12/A15 deterministic behavior. Unverified vendor states stay unsupported. |
| P3 — private deployment | P1/P2 and private owner's authorized scope; advance its package pin to the service-capable version and deploy daemon/Record credentials/unit/viewer. Classifier dependency migration is already P0's gate. Verify actual schema/version/readiness/client failures without model work. Required for real exchange. |
| P4 — authorized live evidence, wake first | P3 plus scratch/setup permission. First establish/refute idle Claude socket wake, then owned versioned identity/composer/dialog/receipt/quiescence/lifecycle/same-pair captures. Unknown blocks dependent capability; no inferred gate/approval. |
| P5 — checkpoint demonstration and Brian UAT | P4; actual host/Opus loop below, independent counterexample/correction and same-harness paths. Mechanical gates pass before Brian judges usability. New Astra host needs named effort too. |
| P6 — generic setup/release preparation | Verified outcomes and accepted UAT; document project-path setup, Record/client/trust/canary, edges/questions/failures. Update existing architecture/skills and coupled release metadata. Commit/publish needs explicit request. |

Later approval tranche owns held/native ordering and any soft-retired keypress removal.
Later literal-message tranche owns multiline correlation. Neither becomes a hidden
minimum prerequisite. Demonstrated pause defects return to their owner, not permission
to silently install a gate.

Focused checks name actual files created in implementation. Existing post-migration
regressions include:

~~~fish
uv run --frozen --all-packages pytest -q tests/test_codex_supervisor.py tests/test_codex_supervisor_classify.py tests/test_codex_supervisor_approve.py tests/test_codex_supervisor_default_model.py tests/test_codex_supervisor_queued_questions.py tests/test_codex_supervisor_slash.py tests/test_codex_supervisor_announce_once.py tests/test_codex_hooks_installer.py tests/test_hook_uv_script_contract.py tests/test_supervisee_offers.py tests/test_instruction_delivery.py tests/test_marketplace_sync.py tests/test_codex_marketplace.py
bats tests/test_codex_peer_review.bats tests/test_codex_ponytail.bats tests/test_claude_ponytail.bats
uv run --frozen --all-packages pytest -q
claude plugin validate . --strict
~~~

Do not use retired floor file as post-migration gate. Run private classifier/identity/
deployment suites from their actual owner at integration, not stale paths here.
Use repository-pinned lint/format/type/complexity/pre-commit gates with command statuses:
warn-only wrapper zero is not clean lint. Use configured caches exactly; inaccessible
cache blocks installs/downloads.

### Live demonstration and permission dependency

Writing this plan authorizes none of these actions.

1. After scratch/setup approval, test fully idle Claude socket wake. Record identity,
   controlled pointer, receipt and actual new turn, distinguishing delivery from field
   presence. If unsupported, test ruled guarded fallback; do not claim native wake.
   Preparing that first test includes the owned process/session join and a benign
   canary whose Stop pull returns null; those establish its idle starting condition.
2. In isolated project, record versions/default inputs/actual identities and loaded-hook
   canary. Brian handles trust. Spawn or explicitly bind correct worker; create bounded
   Record dispatch.
3. Retain stage-1 clamp(value, lower, upper): integers, inclusive bounds, saturation,
   ValueError for lower greater than upper. Allow fixture implementation/tests/agreed
   evidence only. Opus returns proposed contract and pauses; Codex reads artifacts and
   releases RED.
4. Opus produces behavioral RED; Codex checks actual command/output before implementation
   release. Opus returns green; Codex independently runs boundary/invalid-bound examples.
5. Distinct explicitly planted challenge revision returns lower bound for invalid bounds.
   Codex executes counterexample, rejects and releases correction to same actual Opus
   process, then verifies new revision. It demonstrates challenge/correction, not
   spontaneous Opus error.
6. One real plain-text question, “Which label should the smoke-test report carry?”,
   follows ticket/triage/actual human answer/indexed owner/removal/dependency release.
   No fabricated answer to complete demonstration.
7. Parked compact/fresh have distinct confirmations. Interrupt benign running fixture
   once, explicitly resume without replay, then demonstrate shutdown/retirement.
   Controlled crashes test uncertainty; smoke is not reboot/power-loss proof.
8. Separately authorized Claude→Claude and Codex→Codex windows contain supervisor plus
   two workers. Only selected worker receives pointer; self/stale bindings refuse.
   This grants no same-family approval authority.
9. Collect owned process final statuses and stop unneeded fixture/daemon resources,
   preserving human peers. Report unsupported/unrun steps.

Brian's UAT: receive a checkpoint, inspect/challenge stable artifacts, resume correct
worker without relaying messages; manage named panes; avoid repeated idle notices.
Mechanical checks cannot supply this judgement. Design stays Draft until Brian accepts,
and major implementation remains incomplete without explicit UAT.

## 12. Unverified mechanisms and open human decisions

Known human decisions are not reopened to finish the draft. Hold their dependent
capabilities; absence/silence never becomes permission.

| Item | Evidence now, missing check/decision and consequence |
|---|---|
| ADR 0011 property 7 | 0037 changes pairing, not mandates. Brian must rule before same-family approval mandate; pane driving still in scope. |
| Project-memory citation exemption | 0042/work queue leave ignored .notes exemption to Brian. ADR/source/spec evidence used here; no exemption granted. |
| Scratch/setup sessions | Parked ticket open. No actual Claude/Codex/agy session, wake/capture/approval experiment until explicit permission. |
| Astra effort | 0006/0035 name no effort for new Astra supervisor; Brian must name it before launch. Existing selected supervisor/ordinary Opus/Sol defaults need no reselection. |
| Original authority authentication | ADR text/locators read, raw resolvers deliberately not run. Supervisor authentication/acceptance separate; quotes alone do not prove it occurred here. |
| Draft mechanics | Package name/layout, socket/framing/deadlines, control mapping, handshake and failure defaults in §§1–3 are explicit proposals, not prior rulings or code; design acceptance owns them. |
| Record/daemon | Starting condition not built; isolated Postgres/schema/concurrency tests and private deployment required. Viewer existence proves neither. |
| Claude idle socket — first live test | Prior registry metadata reported, not current supported protocol or observed wake. Owned pointer/receipt/new-turn test required. |
| Codex idle pointer | Guard source/docs only; no live daemon-to-driver wake here. Test receipt/UI controls/no body/no blind resend. |
| Hook loading/continuation | Current docs checked, no loaded-session emissions. Canary, recursion/ignored pointer, continuation cap/concurrent hooks/blocks need tests; no automatic cap change. |
| Idle race | Hook gaps/out-of-order events/background wake/human typing untested. Fresh process/UI checks must refuse ambiguity; no atomic tmux claim. |
| Liveness/platforms | Ctrl-D/pane/instance exit, PID/registry reuse, tmux restart/redock, macOS process/peer credentials need evidence. Unknown forbids control; uv portability is not supervision portability. |
| Claude UI/identity/paste | No live capture here. Versioned fixture checks need wrapper/hidden draft/short pane/selection/Unicode/multiline controls. |
| Telemetry/configuration | Flags observed, actual model/effort/denial untested. No exporter installed; missing data unknown. Clear/switch/null/context need bound observations. |
| Cooperative pause | No live Stop/background/process/digest ordering proof. Codex lacks established equivalent arrays; unknown quiescence holds release. No gate/transient-write guarantee inferred. |
| Submission/notification uncertainty | Proposed DB idempotency/attempt-ack semantics are not exactly-once external delivery. Fault injection must inspect received bytes and retained pending work. |
| Lifecycle/resume | Dedicated command/session confirmations untested live. Vendor transcript resume never restores dead edge; detach is not shutdown. |
| Approval application | Narrow authority ruled; occurrence/first-answer/keypress audit unverified. Minimum reports/parks; no retry permission for existing parked experiment supplied. |
| Offers | Parser/source read, no live store/standalone delivery test. Verify layout/attribution/expiring view/commit-before-pointer before replacing interim delivery. |
| Package/private migration | No wheel/import/private dependency test run. Verify foreign CWD and actual participant revisions; old path-loader retires deliberately. |
| Ladder/mail semantics | Defaults accepted revisable, not measured effectiveness. Test unblocked busy clocks/blocks/supervisor block/withdrawal/body read separately from pointer ack; acknowledgement is not comprehension. |
| Regression/acceptance | No product suite/build/lint/UAT in drafting. Future commands prove actual coverage only; Brian owns design acceptance and later UAT. |

No source/test/configuration changes, deployment, commit or publication are authorized
by this document. It is the permanent draft and its evidence boundary.
