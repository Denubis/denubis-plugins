# Permission round-trip experiment — 2026-10-14

## Native pane state correction, 2026-10-16

The preceding daemon-only list did not satisfy the window overview requirement.
The current view returns one row per actual tmux pane, enriches it with native
Claude/Codex state and age, and preserves its colours and window identity.
Manual linking is not required. Daemon-only sessions are excluded.

A read-only host inventory returned 13 actual panes: five idle, two running,
and six unknown. All seven client panes had ages: two process-owned Codex history
ages and five display-only approximate daemon correlations, marked `~`. No exact
UUID links were present. At 107×93, 180×40 and 60×20 the UI showed seven rows,
hid the six ordinary unknown panes, and retained positive preview height and
native pane context. Selection/answers were disabled for this live observation.
Counts describe this snapshot, not hard-coded configuration.

No active Claude process or native registry record was available in the host
snapshot. Claude registry validation is covered by native-shaped fixtures and a
harmless real kernel process, including refusal after process exit; a live Claude
session remains unchecked. No model, GUI terminal or live approval was launched.

Verification against this correction:

- `uv run --frozen pytest -q`: 2,285 passed and 16 subtests passed in 51.08s.
- Ruff check and format check passed for the seven active viewer/provider modules
  and all permission-queue test modules (19 files).
- `git diff --check` passed.
- Native pane answer-key routing is exercised through an isolated tmux fixture;
  Claude unknown-status visibility has a red-to-green integration regression.

The installed-server approval experiment below remains stopped and excluded from
normal test discovery. The state/age correction does not establish that proof.

## Previous Codex daemon implementation, 2026-10-16 (superseded list design)

The current viewer reads Codex 0.162.1 through its Unix WebSocket app-server API.
State and history no longer depend on process-owned rollout files or private SQLite
projection tables. Answers use connection-bound request occurrences. The tmux
association supplies display context only; a missing footer does not prevent the
server session from appearing or being answered.

Verification performed by the parent against the delivered source:

- `uv run --frozen pytest -q`: 2,211 passed and 16 subtests passed in 53.03s,
  excluding the stopped installed-server candidate described below.
- Ruff checks passed for the changed production modules and active daemon/UI tests;
  `git diff --check` passed.

- A real read-only daemon/tmux inventory returned 18 rows: five root daemon sessions,
  six unlinked Codex panes and seven unknown panes; four sessions had recorded ages.
  Zero native UUID footer links were available because live configuration was not
  changed. Counts are an observation, not configuration constants.
- Rendering those records at 107×93, 180×40 and 60×20 produced 11 visible rows and
  positive conversation previews at each size. Seven unknown panes stayed hidden.
  This check disabled attachment and answers to avoid changing live sessions.
- Unix WebSocket protocol fixtures exercise replay, explicit selection, external
  resolution, changed-payload rejection, disconnect invalidation and no answer retry.
- Public UI tests exercise complete request display, choosing before Enter, no
  inherited choice for a replacement request, external resolution advancing to the
  next session, and closing the connection when Ctrl+C exits.
- Focused regressions demonstrate one failed thread read cannot remove healthy
  sessions, and a changed native footer falls back to the correct server history.

**Installed-server approval proof is incomplete.** The preserved candidate is
[pending/installed_daemon.py](pending/installed_daemon.py). Three setup failures
occurred before any local model response or approval: removed `untrusted` policy,
sandbox-hidden Unix socket directory, and `thread/start` rejecting `workspaceWrite`
(the installed runtime expects `workspace-write`). Work on that experiment stopped
under the human's three-failure rule. Permission to correct the final fixture field
and retry is recorded in the main repository's open-question register. The candidate
is retained outside normal test discovery as the rollback to the tested adapter
baseline; normal-suite success does not establish this missing vendor proof.

Retained logs: `/tmp/pytest-of-brian/pytest-1113/`, `pytest-1115/`, and `pytest-1160/`.
The last failure is in
`pytest-1160/test_installed_daemon_shares_o0/daemon.log`.
No live approvals, global Codex settings, Byobu windows or GUI terminals were changed.
No external model request was made. Native TUI prompt dismissal, live statusline
setup, SSH/Tailscale connectivity and human usability remain unverified.

The following sections retain the earlier experiments as historical evidence.

Central allow and deny worked in an isolated Claude Code 2.1.299 terminal. Native
answers behaved differently: Escape and No cancelled the held hook; Yes executed the
command but left the hook alive. This supports a small approval board experiment, but
does not establish production request retirement or Codex parity.

## Scope and provenance

- Worktree: `.worktrees/permission-queue`, base `e63f3474e2b95ddab752fc57a50b694559403281`.
- Three delegated workers: `gpt-6.1-sol`, xhigh; implementation, contract review, UX
  review. The parent inspected source and performed the live experiment.
- Native test subject: Claude Code 2.1.299, Sonnet 5.5 low, with a custom one-command
  system prompt, Bash only, manual permissions, restricted settings, no MCP servers.
  This subject exercised Claude's native permission dialog; it was not an implementation
  worker. Codex was not launched.
- Temporary scratch directory: `/tmp/permission-queue-live-gjdlewvu`.
- Dedicated experimental tmux server `permission-queue-experiment`, session `probe`,
  size 120×40. This isolated the mechanical test; it is not the recommended placement
  for Brian's eventual screen.
- Five calls used the **same command text**. Each execution appended a fresh UUID to
  the sentinel log, allowing separate executions to be distinguished.
- The frozen hook source is [queue-source.py.txt](evidence/2026-10-14-claude-2.1.299/queue-source.py.txt),
  SHA-256 `e8ca8e46257db232d3e62f112acf7b9453b97635cf2bd68f86679f6c78b2a8d9`.
  The working source may subsequently receive formatter-only changes; the frozen copy
  owns these live observations.

## Observed results

Times below are UTC. Request IDs are shortened here; the complete values are in
[requests.json](evidence/2026-10-14-claude-2.1.299/requests.json).

| Request | Action | Observed result |
| --- | --- | --- |
| `bd22c98f` | Central allow at 03:46:45 | Hook emitted allow; native dialog closed; sentinel executed; PostToolUse and transcript tool result confirm success. |
| `83784817` | Native Escape at 03:47:31 | Transcript records user rejection; vendor debug reports hook cancelled. Late central allow was refused as unknown by the harness because the hook was gone. |
| `c73c6158` | Select native No with Down×3, Enter at 03:48:06 | Same positive rejection and hook-cancellation evidence. Late central allow was refused. A further stale answer attempt while the next identical command waited was also refused. |
| `b3a782ab` | Native Yes at 03:48:45 | Sentinel executed and PostToolUse confirmed it; the held hook remained pending. A late hook deny at 03:49:36 was emitted, while the next request's native dialog remained open. |
| `6b978c6b` | Central deny at 03:49:45 | Native dialog closed with the supplied denial reason; transcript records an error result for this exact tool call. |

The sentinel log has two execution UUIDs, corresponding to the central-allow and
native-allow controls. Denial conclusions are not based solely on a missing execution:
the transcript contains a positive rejected/error result for each denied call.

The next dialog after the old hook's denial is captured in
[09-next-dialog-after-old-hook-deny.txt](evidence/2026-10-14-claude-2.1.299/09-next-dialog-after-old-hook-deny.txt).
The old request was read back as `returned` before that capture; only afterward was the
new request centrally denied.

## What this changes

The draft's broad claim that a native answer leaves the hook running needs narrowing
for this version: native allow did; native denial did not. The actual late-allow-after-
native-denial path was **not reached**, because the vendor cancelled the process. This
is useful evidence about cancellation, not proof covering every timing of competing
answers. No near-simultaneous race, alternate tool, or alternate vendor version was tested.

Hook liveness is insufficient for the future screen's pending status. The native-allow
case left a demonstrably stale actionable harness item. The harness intentionally has
no automatic retirement so the experiment can expose this. Before a usable board offers
central answers, completion evidence must retire the correct request. Correlation when
identical calls overlap is still unproven; the UUID alone does not solve the link from a
vendor completion event to a hook invocation. Do not add command-text matching as if
this experiment had validated it.

The experiment uses temporary JSON fixtures and process locks, not the product database
or a second mail store. It does not implement notification delivery, status tracking,
policy integration, or automatic pane-input fallback. A separate fixture-only terminal
board now exercises selection and confirmation without live approvals. Future
supervision and messaging are not precluded; they were not built here.

## Evidence and cleanup

The [evidence directory](evidence/2026-10-14-claude-2.1.299/) contains launch settings,
the sentinel and event recorder, ten terminal captures, hook events, vendor events,
request rows, and transcript/debug excerpts with original source line numbers.
[sha256.json](evidence/2026-10-14-claude-2.1.299/sha256.json) identifies the retained files.
Raw debug and transcript sources remain machine-local; no credentials were copied.
`vendor_version` was omitted at launch and is honestly `unknown` in request rows;
the captured native banner establishes 2.1.299 for this run.

After the last denial, the parent terminated only the scratch `probe` session.
A direct lookup reported no server on its named socket, and none of the five recorded
hook PIDs remained. The main work session and key bindings were not changed. Scratch
evidence was retained.

## UX recommendation and remaining checks

[UX.md](UX.md) records the observed bindings and proposed human trial. Prefer testing a
dedicated session on the existing server: Alt-Up/Down reaches it, while Alt-Left/Right
continues cycling work windows. Opening it must be the human's action; arrivals must
not steal focus or move selection. A phone should use an independent viewer rather
than resize and share the desktop TUI's cursor.

These are recommendations, not passed UAT. The fixture board was rendered and exercised
at 60×20 and 107×93. Command-first confirmation, stable selection through arrivals,
default Enter cancellation, long-command scrolling, and child cleanup were checked.
No phone/Tailscale connection or human keyboard trial was exercised. Codex 0.162.1 was inspected only: its inherited
hooks merge with supplied hooks, so a suitably isolated interactive test remains to
be established before claiming the same behavior there.

## Delivered harness verification

The parent ran `uv run --frozen pytest -q`: exit 0, **2076 passed, 16 subtests
passed**, including the 21 new experiment cases. `uv tool run --offline ruff check`
and `ruff format --check` on the harness and its tests passed; `git diff --check`
passed. Review found and corrected a test setup race: the expiry test could suspend
the hook while it held the state lock, accidentally testing lock contention. Its
setup now owns that lock before suspending the hook.

The parent independently checked all 21 archived file hashes and reconstructed five
distinct requests with identical command text, two unique execution records, and
five transcript results (two successful, three rejected). The final source differs
from the frozen live source only in wrapping and `timezone.utc` becoming its `UTC`
alias. The tests exercise the final source; live observations remain attached to the
frozen copy. No code was committed or deployed.

## First terminal trial

The initial board and harness suite passed: `uv run --frozen pytest -q`, exit 0,
**2088 passed, 16 subtests passed**, including 12 board and 21 harness tests.
Ruff check and format-check passed for both modules and both test files. The
board tests exercise confirmation, competing answers, stable selection, expiry,
resizing from 107 to 60 columns, and real `python -P` terminal startup and quit.
Independent rendered inspection found and corrected command visibility and resize
defects before the human trial. These checks do not establish live queue safety.

## Conversation trial revision

Human feedback rejected the extra confirmation and retained answered rows. The
revised fixture screen presents a generated conversation and its complete request,
accepts one answer, removes the resolved request, and shows the next waiting
conversation. Multiple pending requests from one session remain grouped. Arrivals
preserve the current conversation and reading positions. A failed submission stays
visible; independently observed completion advances without another local click.

The first trial's application-only quit check missed a tmux lifecycle effect:
`detach-on-destroy on` detached the Byobu client when the demo session ended. The
new launcher returns attached demo clients to their own last session before exit,
with an explicitly supplied fallback session and a demo-local crash fallback. It
leaves global options and the work session's selected window/pane unchanged.

This revision still uses generated conversations and held fixture hooks. It does
not recover live conversation history or solve native approval retirement.

Final parent verification for this revision: `uv run --frozen pytest -q` exited 0
with **2101 passed, 16 subtests passed**, including 20 board, 21 hook, and 5 launcher
tests. Ruff check and format-check passed for all three modules and their tests.
The parent independently exercised the 60×20 conversation → single answer → next →
empty → new request flow, inspected rendered screenshots, and reran the attached
terminal return tests. Review additionally checked scrolling away from the top in
both readers before an arrival and actual visible failure handling. Human acceptance
of the revised fixture flow followed this check; source-window orientation was the
next requested revision.


## Source-window replay revision

The next experiment reads existing tmux windows rather than fabricating their
identity. The adapter retains session/window/pane IDs, original indices, working
directory, native title, cached branch-strip colours, pane background and ANSI
terminal content. The initial read-only desktop inventory found 18 panes across
16 windows, with 12 exact cached colour strips. The pictured plugin session
matched Brian `#6987f0`, repository `#874600`, main `#ff0000`, task `#ffff78`,
and pane background `#1b0e00`. Missing cached strips remain explicitly unavailable.

Codex's leading native state and pending-dialog evidence determine blocked/Ready
classification. Task words cannot spoof that state. Ordinary Ready questions remain
idle; unsupported providers remain unknown and visible. Ready age starts when the
viewer observes the current final message, resets on changed evidence/process, and
does not recover the true historical idle start.

The preview includes at most 200 history rows plus the native viewport, retaining
ANSI colours and trailing coloured cells. Open source navigates to the validated
source window and pane without sending an answer. It refuses ambiguous viewer
clients or another client attached to the source session. The fixture approval
flow remains separate; native-answer retirement and live central answers remain
unresolved.

Review exposed a test-evidence defect: `display-message -t =session` could return
an empty pane identifier, making an unchanged-pane assertion vacuous. The launcher
checks now target `session:` and positively require a pane or session ID before
comparing it. The watch launcher additionally renders a unique real terminal
marker and checks that quitting returns an attached client to its work session.

Final parent verification for the source-window revision: `uv run --frozen pytest
-q` exited 0 with **2126 passed, 16 subtests passed**. Ruff check and format-check
passed for all four experiment modules and five test files; `git diff --check`
passed. The parent separately exercised the real launcher, Open source, return to
the viewer, and quit against an isolated tmux server.

Rendered checks at 107×93 and 60×20 found and corrected hidden split panes,
window-grouping priority errors, initially old scrollback, hidden native footer,
and stale background inheritance. The final parent live-source render enumerated
all 18 panes and checked global priority order. The narrow view preserves the
identity/footer but leaves little conversation height; scrolling is required and
phone usability is not established.

The owned old fixture session was closed with its own `q` and replaced with the
watch view in `permission-queue-demo`. Read-back showed `watch:main`, native source
content and ANSI colour, while the existing attached client remained at its work
window/pane. No source input, new agent process, global tmux setting, or additional
viewer session was introduced. Human acceptance of this live view remains open.


## Four answer keys, 2026-10-14

Brian narrowed the interaction to passing 1, 2, 3 and Enter through to the
currently displayed source. Other interaction uses Open source. General typing
and paste are not part of the viewer interface. The earlier general-input
candidate was not deployed after intermittent first-input failures.

The four keys are App-level priority bindings, independent of list, identity or
conversation focus. Their original event timestamps and source destinations are
retained. Readiness is set before the visible Ready message, without waiting for
a focus callback. Unknown state does not establish resolution; verified blocked
resolution or idle-to-running after input advances to a known waiting pane.
A 750 ms quiet interval prevents the tested desktop repeat sequence from answering
the next source. It is not a universal key-release detector.

The installed-launcher scratch test sends unrelated letters followed by 1/Enter
and observes exactly `1\n` in the first source, then sends 2/Enter to the automatically
advanced second source and observes exactly `2\n`. No selection click intervenes.
It also verifies direct o navigation and Ctrl+q returning the attached viewer to
work. All eight launch/watch integration tests passed. Focus-boundary tests
exercise all four keys from each reader and reject unrelated keys and paste.

The broad regression check exposed an older test timing defect: the launcher
returns multiple attached clients sequentially, but the test checked the second
immediately after the first returned. It now waits for the second client's own
positive return signal. No runtime change was needed for that correction.

These are scratch terminal checks, not new live-provider approval probes. Exact
approval-occurrence correlation and the older held-hook retirement race remain
unresolved. No test input was sent to live working panes.

Final parent verification: `uv run --frozen pytest -q` exited 0 with **2152 passed,
16 subtests passed** in 42.76 s. Ruff check and format-check passed for the experiment
and its five test files; `git diff --check` passed. The owned read-only viewer was
closed and replaced in the existing `permission-queue-demo` session name. Live
read-back showed `SOURCE WINDOWS — 1/2/3/Enter only`, the answer-ready hint, and
`watch:main`; the attached client remained in `main`. Human usability acceptance
of these four shortcuts remains open.


## Alt navigation and independent terminal launchers

Brian accepted the four-key viewer and requested Alt navigation, a local Ghostty
launcher, and multiple SSH viewers. Alt+P replaces Ctrl+]; the live footer was
read back after restart. An actual PTY test sends ESC+p and observes list focus.
The current Byobu root key table has no Alt+p binding; its Alt-arrow bindings
remain unchanged.

`open-viewer` reuses `launch.py`, creates a unique viewer by default, and supports
explicit names for reconnection. `view.py` captures the source server socket
before clearing TMUX nesting variables. Two scratch terminal clients proved
independent default sessions, named reuse, and closing one without disturbing
the other or the source window. Missing source and Ghostty failures are covered.
The Ghostty command boundary is tested without launching the GUI. An exploratory
`ghostty +new-window --help` command apparently opened a window unexpectedly;
that is not evidence that the finished graphical launcher ran successfully.
Actual SSH/Tailscale connectivity is not tested.

The installed `~/.local/bin/permission-queue` symlink resolves to this worktree's
launcher. It defaults to Ghostty; `--terminal` uses the current terminal. Parent
checks exercised the installed symlink from PATH, help output, and both command
routes using a recording uv stand-in. It remains dependent on this worktree.

Final parent gates: **2161 passed, 16 subtests passed** (44.52 s), Ruff check and
format-check clean for all experiment modules and six test files, shell syntax
checks clean, and `git diff --check` clean.

Launcher default corrected after human feedback: `permission-queue` now uses the
current terminal; only explicit `--ghostty` opens a new window. `--terminal` remains
a compatibility alias. Parent checked all three routes through the installed
symlink with a recording uv stand-in; all eight viewer tests passed. No GUI
window was opened by those checks.


## Standalone pane overview, 2026-10-16

The new candidate runs the board directly in the invoking terminal, with no
viewer tmux session or attachment. Ghostty remains explicit. The overview lists
all source panes and starts focused; v shows/hides a 33%-height details region.
Parent read-only inspection of the actual main session observed all 13 current
panes, a 57-row list at 107×60, and a 38-row list with details expanded. No source
input was sent. The desktop fixture also fits 50 panes including an ordinary shell.

Parent verification: 2165 tests and 16 subtests passed in 45.73 s; 12 actual
watch/standalone launcher checks passed. After test-only formatting cleanup, the
three affected watch tests passed again. Ruff checks passed. Scratch PTYs verify
that two viewers create no tmux sessions, preserve source selection, and each
returns to its invoking shell on Ctrl+q. GUI and network SSH remain unchecked.

Open source from the standalone runner is unfinished pending the human decision
about switching the primary Byobu window. The previous implementation depends on
a viewer tmux client; it has not been silently retargeted. This candidate is not
committed or declared accepted. Existing running tmux viewers were not restarted.

Ctrl+C now uses the viewer quit action; Ctrl+Q remains an alias. A scratch
PTY regression first failed because Ctrl+C displayed help instead of returning
to the invoking shell, then passed after the binding change. The affected board
and launcher suites passed 62 tests; after removing the unused help action, all
13 launcher tests passed again. Checks cover standalone shell return and the
legacy tmux-hosted viewer returning its attached client to work without detaching.
No live terminal was sent a quit or interrupt key. Ruff and diff checks passed.

## Visible responsive readback and state durations, 2026-10-16

The earlier collapsed-by-default trial above was rejected: the user asked for a
smaller preview, not a hidden one. Readback now starts visible; one row click
selects and reveals it. Wide terminals place the list beside it, while tall or
narrow terminals stack the regions. The list keeps the larger share.

The answered-pane demotion previously overrode state ordering, putting resolved
running panes below unknown panes. Rows now stay grouped as blocked, idle, running,
then unknown, with oldest observed state first within each group. Every state
shows a lower-bound duration (for example, `idle ≥1m`) under `State · seen`. These
are viewer-local monotonic observations, reset on state or source-process change;
refreshes and backend idle timestamp changes do not reset them.

Parent read-only rendering of the actual main session retained all 13 panes and
the selected source through 107×60 → 180×40 → 60×20 → 107×60. Preview content was
visible at every size; native content had 12, 21, 5, then 12 rows respectively.
No input was sent to the source. Regression checks exercise one-click reveal,
resize with preserved reading position and answer destination, all four state
ages, and resolved running panes sorting before unknown panes.

Parent verification after the final code/test changes: `uv run --frozen pytest -q`
passed 2173 tests and 16 subtests in 51.39 seconds. Ruff check and formatting checks
passed for the changed Python files. Actual SSH, Ghostty GUI, and human acceptance
of the new layout remain unverified.

## Recency, individual inclusion, and existing history, 2026-10-16

The user's subsequent correction supersedes the oldest-first and all-panes defaults
above: blocked → idle → running → included unknown, most recent dated state first
within each group. Unknown panes are hidden unless individually included through
`a` Add panes, Space, Escape. Preferences are atomically saved and merged under a
lock in XDG_CONFIG_HOME/permission-queue/panes.json (default ~/.config), keyed by
socket, server PID/start ticks, session/pane IDs, and pane PID/start ticks. They
survive viewer restarts without transferring to recycled panes or servers.

Short lists now occupy their rows rather than most of a tall terminal. Actual main
read-only checks at 107×93, 180×40, and 60×20 showed six classified panes out of 13,
an eight-row list, visible native content, and preserved selection on resizing back.
The final 107×93 preview occupied 81 rows. The Alt+P and Add panes shortcuts remain
visible in a two-line footer.

The source reader reuses codex_supervisor's foreground-process lock/rollout identity
and queries thread_history_1.sqlite read-only. Latest-turn native state must agree,
and the database projection must exactly cover the stable rollout file size.
Completion time supplies idle age; active turn start supplies running turn age.
This is not an approval wait timestamp. The final host check recovered persisted
idle times for panes %115 and %79; the 13-pane snapshot took 0.407 seconds.

Initial states lacking historical evidence show age ?, after dated states within
the same group. Only a same-process transition observed by this viewer starts a
lower-bound ≥ timer. Restarting the viewer never invents new recency. Metadata no
longer repeats a conflicting viewer-start idle timer.

The daemon-backed clients lack the lock/rollout link in their TUI process. Checked
native process descendants/FDs, installed RPC schema and CLI, and matching 0.162.1
TUI source. No supported per-TUI process-to-current-thread lookup was found in
those surfaces. Shell snapshot TMUX_PANE was rejected after a concrete mismatch
(actual %14, inherited %10). Ordinary hook file mtimes were rejected because
working hooks repeatedly overwrite them. Matching a title/directory is not used.
Full session-id can be rendered by a future configured native status line; the
terminal-title version truncates it. No client configuration was changed, no
live source input sent, and no daemon restarted. Claude historical state and
historical blocked duration remain unsupported.

Final parent verification: uv run --frozen pytest -q passed 2190 tests and 16
subtests in 52.27 seconds. The 13 launcher checks include selecting an actual
unknown scratch pane in one viewer and observing its persisted inclusion in a
second viewer. Ctrl+C/Ctrl+Q return to the calling shell. Ruff and diff checks
passed. Network SSH, Ghostty GUI, and human acceptance remain unverified.
