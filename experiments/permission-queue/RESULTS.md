# Permission round-trip experiment — 2026-10-14

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
