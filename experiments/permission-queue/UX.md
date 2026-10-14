# Permission queue interaction experiment

The conversation-first fixture flow was accepted by Brian. The next trial adds
source-window identity and four answer-key shortcuts to the main tmux windows.
Scope authority: [ADR 0030](../../docs/architecture/decisions/0030-permission-queue-starts-with-an-experiment-and-does-not-preclude-later-messaging.md).

## Starting point

Brian currently moves between work windows with Alt-Left/Right. Read-only observations
on 2026-10-14 from the default tmux server:

| Command | Result |
| --- | --- |
| `tmux list-keys -T root M-Left` | `previous-window` |
| `tmux list-keys -T root M-Right` | `next-window` |
| `tmux list-keys -T root M-Up` | `switch-client -p` |
| `tmux list-keys -T root M-Down` | `switch-client -n` |
| `tmux list-clients -F '#{client_width}x#{client_height}'` | `107x93` for the one attached client |
| `tmux show-options -gv window-size` | `latest` |
| `tmux show-options -gv aggressive-resize` | `on` |

Window counts changed during inspection; do not use window indices or a captured count
as permanent identity. The initial navigation assessment did not read or modify active work panes. The
subsequent source-window trial reads their native terminal content as requested.

## Candidate placement

Try one named queue session on the existing server, outside the main work session.
This retains Alt-Left/Right's current meaning and makes the queue reachable through
the already-bound Alt-Up/Down. A separate server would not be reachable through those
session bindings. This candidate is compatible with ADR 0020's outside-main-session
boundary; the unaccepted draft's separate-server choice is not required by that ADR.

The cost is dependence on the same tmux server and another navigation level. A separate
terminal showing the queue may be more comfortable on the side monitor; Brian must
judge that with the actual screen. Do not nest byobu, rebind keys, split existing
work panes, steal focus when an item arrives, or switch the main session's current
window from a remote client.

For a phone, test a separate viewer process over SSH rather than sharing the desktop
TUI process. With the observed sizing policy, attaching a differently sized client to
the same window may resize its terminal; shared screen selection is another source of
interference. Independent viewers still need to contend on the same request decision.
The terminal demo supports fixture viewing; independent phone access has not been tested.

## Revised trial: conversations needing attention

The first trial exposed three problems: a second confirmation after choosing an
answer, answered rows remaining in the queue, and quitting the demo detaching the
Byobu client. Brian's requested interaction is to read the conversation leading up
to an approval, see the complete request, answer once, and have that session leave
the queue so the next waiting conversation comes to the top.

The revised fixture trial follows that sequence. New arrivals wait behind the
conversation being read. An accepted answer removes the pending item; a failed
submission remains visible with its error. The reading area, rather than the last
answer button, receives focus when the next conversation appears. The empty state
must clearly say there is nothing waiting. Generated conversation text is labelled
as demo content, never presented as recovered live conversation.

Quitting must close only the demo and return the client to its previous work session.
The correction belongs to the demo session's lifecycle, not global Byobu bindings.

## Source-window orientation

Brian's next requirement is to recognise a conversation as the same window he
normally visits: the existing person/repository/branch/task colour strip, source
background, full directory, window number/name and pane locator. The native pane
preview carries the provider's own model, effort, context meter and conversation
where the provider renders them. Missing metadata must not be invented.

The attention view lists blocked panes first, then observed idle panes with the
longest observed idle duration first. A Ready conversation containing an ordinary
question remains in the idle group; an explicit action-required dialog is blocked.
Running and unknown panes remain reachable, preserving coverage of the source
window set. New priorities must not move the conversation being inspected.

Existing status observations do not retain the true start of an idle period. The
trial therefore labels idle duration as time observed Ready by this viewer. It
resets that observation on non-idle evidence or source process replacement. A
silent terminal, cached colour-file timestamp, and recent output time are not idle
evidence.

The queue passes only 1, 2, 3 and Enter to the displayed source. They work
regardless of which queue reader has focus, without a second confirmation.
Other interaction uses Open source (`o`), which jumps to the original window/pane.
Ctrl+q closes the viewer without detaching Byobu.

After native state leaves blocked, or an idle conversation resumes after input,
the next waiting conversation appears. A successful key send alone is not
completion evidence. Queued keys retain their original destination. A 750 ms
quiet interval after advancement suppresses the tested desktop held-key burst;
the next source then accepts answer keys automatically.

This shortcut is separate from the held-hook fixture approval mechanism; it does
not establish exact approval occurrence correlation or vendor race semantics.

## What live integration still needs to establish

- A request names its project, provider, originating session and current window label;
  full command/input is available before answering. Pane identity is a locator, not
  request identity.
- New arrivals do not move the selection or change which request an answer targets.
- An item answered at its source cannot remain an actionable central item. A timed-out
  or uncertain item is visibly different from one still answerable.
- Status names observations: waiting for permission, last activity, ended, or unknown.
  Silence alone does not establish idle or finished.
- A notification does not repeatedly ring while Brian is already inspecting the item.

## Live source-window trial

1. Reach `permission-queue-demo` with the existing session navigation. Recognise a
   source from its original window number, coloured strip, directory and native
   conversation/footer. Every split pane must remain selectable.
2. Check blocked panes precede observed Ready panes, with the oldest observation
   first. Verify a new priority does not displace the pane being read.
3. Press a displayed native choice (1–3) and Enter. Check it reaches that pane
   once and the next waiting conversation accepts those keys without activation.
4. Press o to open the source for other interaction. Use Ctrl+q to close the viewer
   and check Byobu stays attached.

Terminal output remains a bounded capture rather than a full terminal emulator;
input goes to the existing original process. Unsupported provider status remains
unknown, so automatic advancement for those providers is not established.

## Accepted fixture trial

1. Read a generated conversation and its complete request. Answer once. Check that
   the answered item leaves and the next waiting conversation appears.
2. Add a request while reading. Check that the current conversation and scroll
   position stay put. Answer the queue down to its empty state.
3. Quit the demo. Check that Byobu stays open at the work session's original window.

The following require live integration beyond this fixture demo:

4. Answer at the original pane first, then inspect the board. Attempting a stale
   answer must not affect another request, including an identical command.
5. Answer from a separate narrow SSH viewer and disconnect during the answer. The
   desktop must agree on the result without changing size, focus or selected request.

These are proposed acceptance checks. Neither phone/Tailscale reach nor human comfort
has been tested by the CLI experiment.
