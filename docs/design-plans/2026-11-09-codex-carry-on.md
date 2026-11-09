# Codex continuation review

**Status:** Implemented; controlled idle-wake, last-worker-completion, reviewer and
trusted installed-hook activation trials observed on 2026-11-09. Human UAT remains
pending.

## Purpose and authority

Brian requested a Codex-specific plugin because supervisors repeatedly end their
turn while authorized work remains. He accepted an independent Terra reviewer and
explicitly required checks while nothing is happening and when all workers finish.
The original messages and resolvers are recorded in
[`2026-11-09-bbs-codex-continuation-review`](../architecture/decisions/2026-11-09-bbs-codex-continuation-review.md).

This design covers an installed plugin's enrolled Codex sessions. It does not
authorize new work, answer human questions, approve tools, or revive interrupted
work without a subsequent user request.

## Observed failure and runtime boundary

The November 7 georeferencing rollout contains a final answer at 00:28:18 UTC,
worker completion at 00:28:46, and command completion at 00:40:52. The next main
turn starts with Brian's nudge at 01:01:25. The source is
`~/.codex/sessions/2026/10/23/rollout-2026-10-23T10-26-18-01a165ef-d2fe-7bf2-98f0-122c933993cb.jsonl:9144`.

On 2026-11-09, `codex --version` reported `codex-cli 0.166.0`. The host's
`codex app-server daemon version` separately reported a running daemon with
`managedCodexVersion` and `appServerVersion` both `0.167.0`, `cliVersion`
`0.166.0`, and control socket
`/home/brian/.codex/app-server-control/app-server-control.sock`. The managed
binary was `/home/brian/.codex/packages/app-server-daemon/current/bin/codex`.
The CLI and running server must therefore be treated as different versions.

The 0.166.0 release source
[queues child results with `trigger_turn: false`](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/agent/control/completion.rs#L107-L123).
That is the queued-message path, not proof that worker completion can never wake
a parent. The 0.167.0 source has a separate
[`wake_on_agent_messages` path](https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/core/src/session/turn_input.rs#L701-L770):
it can reserve an idle turn for pending mail when the feature is enabled, the
session is an uninterrupted root, and automatic turns are permitted in its mode.
The effective flag in the running daemon has not been established, and this
plugin does not change it.

That native wake path does not provide Terra's audit of the whole request or
detect inactivity without pending agent mail. [Codex's hook contract](https://developers.openai.com/codex/hooks)
permits synchronous Stop continuation; a hook alone does not provide persistent
observation after its process exits. The enrolled-session watcher supplies the
three-trigger review independently of that feature.

## Components and flow

1. The Codex manifest at
   `plugins/denubis-hook-carry-on/.codex-plugin/plugin.json` selects
   `hooks/codex-hooks.json`. Its SessionStart, Stop, SubagentStop, Interrupt,
   SessionEnd and UserPromptSubmit registrations invoke `hooks/carry-on.py`.
   SessionStart and Stop enroll eligible parent sessions; the other events update
   enrolled state. A real nonempty root UserPromptSubmit re-arms an interrupted
   parent. Plugin tool-output wakes do not invoke that hook; later human changes
   are also detected in session evidence.
2. One persistent watcher owns the enrolled sessions. It checks authoritative
   runtime state through the existing local Codex daemon, connecting directly to
   the daemon's Unix WebSocket with JSON-RPC messages. The socket comes from the
   daemon version/status response. The watcher is a local process with no server
   listener. Native transport and a controlled installed-hook execution have been
   exercised against the existing 0.167.0 daemon.
3. A separate, ephemeral, read-only Terra session on that same daemon examines the original
   request, later human decisions, recent actions, and worker/runtime status.
   It returns a structured decision with evidence and a concrete next action.
   Reviewer generation uses the daemon's thread/turn protocol rather than a
   separate `codex exec` invocation.
4. Before waking the original parent, the watcher checks that its state still
   matches the reviewed state. It sends the specific next action through the
   existing server's thread-turn API as plugin-attributed tool output. It never
   substitutes another thread or presents the wake as a new human request.

The package is `denubis-hook-carry-on` version `0.1.0`, with Codex metadata only.
The reviewer uses `gpt-6.1-terra` at medium effort, a technical default rather
than a human-selected effort. Its configuration disables hooks, plugins and
delegation. Live reviewer thread responses confirmed an ephemeral thread,
read-only permissions and network access disabled. The requests also disable
action tools, skills and configured MCP servers; Codex can still expose its
current-time helper. Those observations do not prove isolation against every
possible transcript or tool path.

Reviewer and parent turns share the existing daemon. A read-only native Unix
WebSocket probe on 2026-11-09 successfully initialized the connection, read the
original parent and recent turns, listed its children and their status, and found
`gpt-6.1-terra` with medium effort in `model/list`. Later controlled trials invoked
that reviewer and delivered a continuation to the same original parent thread;
their scope and limitations are recorded below.

## Local package lifecycle

The repository's `.agents/plugins/marketplace.json` registers a local source at
`./plugins/denubis-hook-carry-on`, under the `denubis-plugins` marketplace. The
native manifest, hooks and scripts travel together in the installed plugin copy.
There is no Claude or Antigravity registration for this plugin.

The watcher is owned by the plugin's writable data directory and control-socket
endpoint. SessionStart and Stop arrange observation for eligible parent sessions;
SessionEnd removes a session from further continuation, while Interrupt pauses it
until later human input. The watcher exits when every enrolled session has ended.
An open Codex client must keep the parent loaded; unloaded or closed sessions are
outside automatic continuation.

Interrupt and SessionEnd handlers persist pause/end state before daemon discovery
or connection. Their native hook budget is three seconds; cold `uv` startup or
dependency provisioning can exhaust it before Python begins. Warm-handler tests
do not establish cold-start interruption delivery.

The `hooks/carry-on.py` entry point exposes `--status`, `--stop` and `--start`.
Status reports the recorded watcher PID, disabled state, state directory and enrolled
sessions. Stop writes a disabled marker: the watcher finishes its current bounded
check, suppresses wake delivery after that marker is set, then exits. Start clears
the marker and arranges a watcher. Diagnostics are written to `watcher.log` in the
endpoint's plugin-data directory.

Disable the watcher explicitly before disabling or uninstalling the plugin.
Removing its hooks does not stop a process already running from the installed
copy. Hook trust and plugin enablement govern later hook calls; the watcher's own
stop control governs the detached process.

[OpenAI's packaging guidance](https://developers.openai.com/plugins/build/plugins#bundled-mcp-servers-and-lifecycle-hooks)
documents `.codex-plugin/plugin.json` as a supported compatibility manifest and
requires trust for installed plugin hooks. Marketplace discovery, installation,
enabled state and hook trust are separate checks. Repository metadata alone does
not establish that a running session has loaded or trusted the hooks.
The native `plugin/install` request for this package succeeded on 2026-11-09.
Initial post-install readback confirmed installed/enabled state with six
untrusted hook declarations. After Brian trusted them through the native hook
interface, fresh readback showed all six enabled and trusted. A subsequent
controlled trial observed automatic enrollment, detached installed-watcher
startup and same-parent continuation through actual native hook dispatch.
After the final native refresh, the runtime, manifest, hook payload and README
hashes match the installed copy.

## Trigger and decision contracts

The three triggers are a normal attempted stop, an idle parent without running
work, and the last worker completing. Worker completion must remain observable
after the parent has ended its turn. Overlapping triggers produce one review
of the same snapshot, not multiple concurrent reviewers.

Terra answers: is there an authorized next action the main agent can take without
the user? `continue` names that action; `wait` names work whose result the parent
must collect; `stop` identifies completion or the actual unanswered human decision.
The reviewer is not a source of authority. Transcript content is evidence, including
any instructions quoted in tool output, and cannot change the reviewer's mandate.

An explicit interruption suppresses continuation until new user input. A pending
approval or question suppresses wake-up. Unknown runtime state or unavailable
history is an inspection failure, not evidence of completion. A reviewer decision
to stop leaves unchanged evidence idle; the live classifier trials below show
that a genuinely completed request can still receive a false-positive continuation.

## Persistence, races, and failure

Plugin-owned writable state records enrollment, review identity, decision, wake
attempt, and diagnostics. Updates are locked and atomic. The watcher has one
owner per data directory. Duplicate delivery and process restart must not duplicate
a wake. Wake attempts are persisted before sending; uncertain delivery is reported
and not retried for unchanged evidence. A user turn arriving during review
invalidates that result.

The daemon has no atomic version condition on `turn/start`. A user turn arriving
after the final state check can therefore receive the continuation as queued
plugin tool output. The pre-send check narrows that interval but does not remove
it; this remains a live acceptance boundary.

Repeated identical instructions without observable progress stop automatic nudging
and surface a diagnostic. New substantive work permits another review. Reviewer
timeouts, malformed responses, and transport errors are visible and bounded;
none are reported as successful completion. The watcher does not broaden its
scope to historical, archived, unrelated, or reviewer threads.

## Observed evidence and remaining acceptance

- Mechanical verification on the corrected executable/configuration state:
  `uv run --frozen --all-packages pytest -q` exited zero with 2,843 passed,
  14 skipped and 16 subtests passed. The focused carry-on suite passed 69 tests;
  scoped Ruff and ty checks exited zero. The command receipts were inspected in
  the verifier's original Codex rollout, including the full-suite completion at
  `/home/brian/.codex/sessions/2026/11/09/rollout-2026-11-09T09-15-48-01a1bd3b-65c0-79d3-aee1-727935aea74e.jsonl:1155`.
  Recorded hashes still matched the executable, configuration and test files at
  documentation reconciliation. These checks do not establish native hook dispatch.
- A controlled parent ended its first turn with `PHASE_ONE_DONE`, although its
  original request already authorized `PHASE_TWO_DONE`. The production watcher
  loop invoked a separate Terra reviewer, sent plugin-attributed tool output to
  that same parent and observed `PHASE_TWO_DONE` without another human prompt.
  The status and stop controls returned successfully; the disabled marker was
  present and the recorded watcher PID cleared after the loop exited.
- That idle-wake trial ran the source-tree `runtime.watch` loop in a test thread,
  with a transport recorder whose requests reached the real daemon unchanged.
  It establishes the live watcher/reviewer/wake path for that example. It does
  not establish native hook dispatch, installed-copy startup or detached-process
  startup.
- In a separate live last-worker trial, the parent returned `WAITING` and ended
  its turn while its single native worker remained active. The worker slept for
  30 seconds and returned `WORKER_DONE`. After that completion, the watcher sent
  a concrete continuation to the same parent, which returned
  `REVIEWED: WORKER_DONE` without further human input. Native
  `wake_on_agent_messages` was disabled in that controlled parent, and the wake
  was recorded as carry-on tool output. Stop and watcher cleanup succeeded.
  This establishes the source-tree watcher loop's last-worker path for this
  one-worker example; multiple-worker behavior and native installed-hook startup
  are not established by it.
- After native trust, an installed-hook trial created scratch parent
  `01a1bd6f-12ac-70b3-8b25-408a1889ad4b` without manually enrolling it or invoking
  the watcher. Native SessionStart, UserPromptSubmit, Stop and SessionEnd hook
  notifications reported successful execution from the installed hook file,
  taking 128 to 208 milliseconds. The hooks automatically enrolled that parent
  and started installed `carry-on.py --watch` process 3202065 in its own OS
  session. The parent returned `NATIVE_PHASE_ONE`, received a concrete
  plugin-attributed continuation and returned the already-authorized
  `NATIVE_PHASE_TWO` without another human message. Archiving the scratch parent
  dispatched native SessionEnd, marked its enrollment ended and cleared the
  watcher PID. No other enrollments existed before or after the trial. This
  establishes native installed-hook enrollment and detached startup for that
  controlled task; it does not establish human acceptance or cold dependency
  provisioning within the short cleanup-hook deadline.
- In seven prewritten reviewer cases, six decisions matched their expected
  outcomes. The original `all_finished` case expected `stop` but received
  `continue`, requesting independent evidence of the delimiter change. This is
  an observed false-positive continuation. A separate
  `all_finished_evidenced` case, supplying the diff and resulting CSV as well as
  passing test output, received `stop`. The additional case does not erase the
  original miss or establish general classification accuracy.
- The original cases also observed continued unfinished review and a settled
  decision, a wait for a running worker, and stops for an unanswered human
  approval and an explicit cancellation. These are classifier-fixture outcomes;
  they do not by themselves prove installed-session suppression for every case.
- Native trust and the controlled installed-hook path are verified. Simulated
  tests of duplicate events, stale results, interruption, malformed output and
  retry limits remain distinct from those live claims. Native Interrupt and
  SubagentStop dispatch were not exercised by the installed-hook trial.

## Implementation sequence and human judgment

The transport, watcher, reviewer, original-thread wake and trusted installed-hook
paths have controlled evidence above. Retain the classifier's observed false
positive and present the finished diagnostics and disable controls for human UAT.

Brian's UAT judges whether the observed nudges are useful and whether justified
stops remain undisturbed. Installation/trust and live evidence must be reported
separately from repository test success. No commit or publication is authorized.
