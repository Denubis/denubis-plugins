# Held approval experiment

The Unix, standard-library `queue.py` harness captures one `PermissionRequest` per UUID and
returns an explicitly chosen allow or deny through that invocation's stdout.
It never executes the requested command, types into a pane, changes live settings,
launches an agent, or emits a standing permission grant. The run directory is
temporary fixture transport and experiment evidence, with no mail or supervision
infrastructure. Those later features remain possible.

See [RESULTS.md](RESULTS.md) for the retained Claude 2.1.299 live experiment and
[UX.md](UX.md) for navigation and remaining human checks.

The fixture tests establish the harness contract. They do **not** establish whether
Claude or Codex displays a pane prompt while the hook is held, ignores a late hook
allow after a pane denial, or provides a reliable pane-retirement event. Those need
an isolated, authorized live vendor run. A `returned` item means stdout was written;
it does not mean the command ran or the vendor accepted the decision.

Use a new run directory for each experiment. Do not treat old directories as an
approval queue after a reboot: deadlines use the current boot's monotonic clock.
An interrupted hook is labelled `unknown` and refuses further answers. An unanswered
hook expires without emitting a decision, leaving the vendor's normal permission
flow in charge. Hold limits are greater than zero and at most 600 seconds.

## Live window view

To inspect the real windows in the `main` tmux session:

```fish
permission-queue --watch-session main
```

The viewer runs directly in its invoking terminal, outside Byobu. It creates no
tmux viewer session and does not attach the terminal to one. Recognized agent
panes appear automatically; unknown panes (including ordinary shells) are hidden
until individually included. `a` opens Add panes, Space toggles the selected pane,
and Escape returns. These choices persist across viewer restarts, scoped to the
source pane's lifetime so recycled pane IDs do not inherit them.

The selected-pane preview is visible by default. Clicking a row selects its source
and reveals the preview if hidden. Wide windows place the list beside the preview;
tall or narrow windows stack them. The list uses space for its actual rows instead
of reserving a large empty area. `v` hides or shows the preview.

The view retains source window/pane numbers, colours, directory and native terminal
content. Groups are blocked, idle, running, then explicitly included unknown panes.
Within each group the most recent state change comes first, so the conversations
you have just been working on remain near the top. A Ready conversation containing
a normal question remains idle; unknown does not imply idle or stuck.

Each row represents an actual tmux pane. Loaded daemon sessions without a pane
are excluded. State and age do not require manual linking or statusline changes.

Codex uses its native pane state. Recorded ages come from process-owned rollout
history where available. Otherwise a unique daemon session with the exact directory,
complete task title and agreeing state can supply a display-only approximate age,
marked `~`. This correlation never authorizes API approval routing. Ambiguous or
truncated titles do not supply an age. No private SQLite tables are read.

Claude uses its native `~/.claude/sessions/<PID>.json` registry (respecting
`CLAUDE_CONFIG_DIR`), verified against the live process, process start time and tmux
pane. Busy/shell is running, idle is idle, and supported human-wait reasons are
blocked. The native status timestamp may reflect a change within the same state,
so its age is marked `~`. No hooks or global configuration changes are required.

Unavailable ages show `?`; transitions first observed by the viewer show `≥`.
Recognized clients with unavailable state remain visible as `state ?`.

The optional Codex daemon connection uses
`$CODEX_HOME/app-server-control/app-server-control.sock`, defaulting to `~/.codex`.
It only connects to an existing server. A complete native footer thread UUID can
add an exact API connection to the same pane row. No separate session row is added.
Without that exact connection, the preview and answer keys use the actual pane.

Selecting an exactly linked Codex pane attaches this viewer to its approval stream and replays
pending requests. Browsing the list without selecting a session is read-only.
Switching sessions unsubscribes the previous selection. Attachment can cold-load a
thread if it unloads between the precheck and resume; there is no atomic
attach-only-if-loaded operation in this version.

For supported command and file-change approvals, the viewer shows the complete
request parameters and labels its available one-shot choices. Press `1`, `2`, or
`3` to choose, then Enter to send; Enter alone sends nothing. Session-wide grants,
policy amendments and other request types must be answered in Codex. Unsupported
requests stay visible. Without an exact API link, 1/2/3 and Enter are forwarded
to the selected native pane, with process-identity checks. API approval answers
are never automatically retried after a disconnect. A resolved event means
answered or cleared; it does not prove this viewer's decision won or a tool ran.

`Ctrl+c` closes the standalone viewer and returns to its invoking shell. Open source (`o`) is not yet wired for standalone operation: whether it should
switch the primary Byobu window is awaiting a human decision.

The display refreshes while following its latest output and preserves a scrolled
reading position. The next waiting conversation comes forward when the source
shows that the selected approval has ended. Sending an answer alone does not
establish resolution. An occurrence can be sent only once by this viewer; a new
request requires a fresh numeric choice. After automatic advance, the existing
750 ms quiet interval protects against a held-key burst.


## Local Ghostty and remote viewers

From any directory, open the viewer in your current terminal:

```fish
permission-queue
```

`~/.local/bin/permission-queue` is a symlink to this experiment's launcher in
the main repository checkout (`~/people/Brian/brian-ed3d-plugins`). Use `permission-queue --ghostty` only when
you want a new Ghostty window. `--terminal` remains an alias for the default;
`permission-queue --help` lists the options. The wrapper uses the checkout's configured uv environment. It needs `uv`, `tmux`
and, for this local option, `ghostty` on PATH. No desktop shortcut or global Byobu
binding is installed. Alt+P focuses the pane list; Up/Down chooses a pane.
1/2/3 selects a displayed approval choice; Enter sends it. Ctrl+c closes
the viewer and returns to the invoking shell. The viewer does not install Byobu
keybindings or add another tmux navigation layer.

For remote access, SSH into the machine where your agents and tmux run, as the
same user. Use its existing SSH hostname or Tailscale hostname in place of
`YOUR-HOST`; this does not configure SSH or Tailscale. The paths below refer to
this checkout on that host. In terminal A:

```fish
ssh -t brian@YOUR-HOST '/home/brian/.local/bin/permission-queue'
```

In terminal B (or a second device):

```fish
ssh -t brian@YOUR-HOST '/home/brian/.local/bin/permission-queue'
```

Each command runs an independent viewer process with its own selection, scroll
position and size. Both observe the same `main` source session. No viewer names
or tmux viewer sessions are needed. After an SSH disconnect, run the command
again; the underlying work in Byobu continues. Ctrl+c exits the viewer. With
`ssh -t host command`, that also ends the remote command and returns to the local
shell; when started inside an interactive SSH shell, it returns to that shell.

For another source session, add `--watch-session NAME`. If work runs on a
non-default tmux server, add `--socket /absolute/path/to/tmux.sock` to the wrapper.
Find the source socket from inside your existing Byobu terminal with:

```fish
tmux display-message -p '#{socket_path}'
```

Use that same socket on the host over SSH. A socket path is local to that host;
it is not an address to connect to from your laptop. The wrapper preserves the
current tmux server when launched inside it, while clearing nesting variables
before starting the standalone viewer.

If SSH reports unknown `xterm-ghostty` terminal capabilities, use this compatibility
form (the viewer still receives Alt+P):

```fish
env TERM=xterm-256color ssh -t brian@YOUR-HOST '/home/brian/.local/bin/permission-queue'
```

Remote limits: Open source targeting is pending for the standalone viewer.
Multiple viewers connect to the same daemon and use exact request occurrences;
the native server owns arbitration. Actual SSH/Tailscale connectivity and phone
usability remain human checks. Other providers remain unknown and individually
opt-in; their state and approval protocols are not implemented. This backend does
not preclude later supervision or other provider adapters.

Command references: [Ghostty command launching](https://ghostty.org/docs/config/reference#initial-command)
and [OpenSSH terminal allocation](https://man.openbsd.org/ssh#t).

## Approval interaction demo

From this worktree, create the detached demo on the existing tmux server:

```fish
uv run --frozen python -P experiments/permission-queue/launch.py --return-session main
```

The launcher uses the single session `permission-queue-demo`. Existing Alt-Up/Down
switches sessions; Alt-Left/Right still switches work windows. It does not add key
bindings or switch your attached client when starting. Quitting the board returns
clients viewing it to their last work session; `main` is the explicit fallback if
that session is gone. The return happens before the demo session exits.

The screen creates three generated conversations with harmless approval requests.
Their command text is never executed. Read the conversation and complete request,
then press `a` or `d`, or click the corresponding answer once. An accepted answer
leaves the pending view and the next waiting conversation comes forward. Arrivals
wait behind the current conversation and preserve its reading position. Tab moves
between the conversation and request readers; arrows/PageDown scroll the focused
reader. `s` moves to another waiting session. Failed submissions remain visible
with an error. `n` adds another generated request; `q`
exits and stops only the demo's held hooks. Requests expire after ten minutes.

To run directly in an ordinary terminal instead:

```fish
uv run --frozen python -P experiments/permission-queue/board.py --demo
```

Keep `-P`: the adjacent harness is named `queue.py`, which would otherwise shadow
Python's standard-library module when importing Textual. Textual is pinned in the
repository's development dependencies.

`board.py --fixture-only --run-dir PATH` views existing fixture requests; records
without the experiment marker cannot be answered. Conversation text is generated
demo content, not recovered live history. No live hooks or notifications are
installed. Native-answer retirement remains unresolved (see RESULTS.md).

## Operator interface

From the repository root, these commands use the configured uv environment and cache.
The examples are fish syntax. Replace `/tmp/permission-queue-fixture` with your run
directory and `UUID` with the complete ID printed by `list`.

```fish
uv run --frozen python experiments/permission-queue/queue.py hook \
    --run-dir /tmp/permission-queue-fixture --vendor claude \
    --vendor-version fixture --hold-seconds 45 \
    < experiments/permission-queue/fixtures/permission-request.json
```

In another terminal:

```fish
uv run --frozen python experiments/permission-queue/queue.py list \
    --run-dir /tmp/permission-queue-fixture

uv run --frozen python experiments/permission-queue/queue.py decide \
    --run-dir /tmp/permission-queue-fixture --request UUID \
    --decision allow --reason 'Approved this exact fixture occurrence'
```

`list --json` returns machine-readable records. Plain `list` shows every captured
field, including the complete command and tool input. JSON escaping prevents
terminal controls and invisible Unicode controls from acting on the display.
The hook accepts `--vendor claude|codex`; this is an operator-supplied evidence label,
as is `--vendor-version`. Both vendors use the same minimal decision shape. Deny
includes the explicit reason as `message`; allow carries no permission updates.

`decide` refuses expired, retired, dead, already decided, and already returned
requests. Decisions for identical command text remain separate because commands
are never used to select a request. Two competing answers accept at most one.

```fish
uv run --frozen python experiments/permission-queue/queue.py note \
    --run-dir /tmp/permission-queue-fixture --request UUID \
    --event pane-denied --detail 'Observed denial in the vendor pane; trace PATH'

uv run --frozen python experiments/permission-queue/queue.py retire \
    --run-dir /tmp/permission-queue-fixture --request UUID \
    --reason 'Operator explicitly retires this occurrence'
```

`note` records an observation without altering request state. Available events are
`pane-denied`, `pane-allowed`, `command-observed`, and `operator-note`.
`retire` explicitly releases a held request without emitting a permission decision.
It does not infer which live vendor dialog is on screen.

## Discriminating live checks

Keep the native pane reachable through the existing Alt Left/Right workflow.
The central experiment commands add another answer path without changing that
navigation. Capture the native pane, exact command marker, vendor version, and
transcript alongside the run directory's `evidence.jsonl`.

1. **Central control:** hold a harmless, uniquely marked command, inspect its full
   request, answer its UUID centrally, and record whether the marker actually ran.
   Also deny a separate control and inspect the vendor's visible denial.
2. **Pane first, then central:** hold another unique marker; deny in the native pane;
   record `pane-denied` with `note`; then deliberately send `decide --decision allow`
   for that same UUID while the hold is still open. Do **not** retire the request
   first, because suppressing the late allow would hide the vendor race being tested.
   Record hook stdout separately from the command outcome. Failure is that denied
   command running; a mere missing file without a functioning allow control and
   completed vendor turn is insufficient evidence.
3. **Repeated identical command:** record request A and its native outcome, then
   request B with identical input. Capture both UUIDs and vendor traces. The harness
   can prove its own exact-ID retirement refuses A while B remains answerable; it
   cannot infer that vendor lifecycle events identify A's dialog occurrence.

No automatic approval or pane-retirement adapter is enabled by these checks. A
passing fixture suite is not a live first-answer-wins result.

## Verification

```fish
uv run --frozen pytest tests/test_permission_queue_experiment.py \
    tests/test_permission_queue_board.py tests/test_permission_queue_launch.py \
    tests/test_permission_queue_source.py tests/test_permission_queue_watch_launch.py -q
uv tool run --offline ruff check experiments/permission-queue/queue.py \
    experiments/permission-queue/board.py experiments/permission-queue/launch.py \
    tests/test_permission_queue_experiment.py tests/test_permission_queue_board.py \
    tests/test_permission_queue_launch.py experiments/permission-queue/tmux_source.py \
    tests/test_permission_queue_source.py tests/test_permission_queue_watch_launch.py
```

The run directory contains atomic JSON request snapshots, OS liveness locks, and an
append-only JSONL evidence log. Log entries distinguish opening, observation,
decision acceptance/refusal, expiry/unknown state, and successfully written hook
stdout. These files are not a transactional or durable record and should be kept
only as long as needed for the experiment's evidence.
