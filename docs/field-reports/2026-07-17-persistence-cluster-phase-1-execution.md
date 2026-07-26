# Field report: persistence-cluster-53 phase-1 execution

Authored by Claude (Fable 5), from the 2026-07-17 execution session in
`google-live` (`.worktrees/postgres-schema-53`), companion to the same-day
planning field report. Brian supervised; codex (GPT-5.6 Sol) drafted
interactively in a tmux pane; observations are mine.

## What the session ran

Phase 1 of seven (documentary contract freeze): one codex prompt drafting
two dated records, codex running interactively in a tmux split with Brian
watching, a one-question-at-a-time gate, a full supervision verification
pass, landing plus per-task commits, a fresh-context bounded code review
with findings written to a file, one fix cycle with re-review, and an
end-of-phase rebase onto main.

## What held up

- **Interactive pause-and-ask beat batch-draft-then-verify on decision
  quality.** Codex asked eight questions; every one surfaced something
  real (two stale paths, five underdetermined fixture conventions, one
  genuine plan tension). None would have been visible in a batch draft
  until verification, and two would likely have shipped as silent wrong
  guesses.
- **Question triage between human and supervisor worked once delegated.**
  Brian answered the early questions, then delegated trivial/derivable
  ones to the supervising Claude mid-phase. The split held: five
  supervisor answers (each grounded in a checked source and disclosed in
  the notes file), three Brian answers.
- **Findings-to-file discipline paid for itself the same day.** The
  reviewer's re-review verdict initially arrived as an idle notification
  with no text — the exact planning-session failure — and the appended
  findings file carried the content anyway after one nudge.
- **Doer honesty held under the new contract.** Codex recorded all eight
  Q&As, its assumptions, and both contradictions faithfully in its notes
  file, including which answers came from the supervisor.

## Observations for the rebalance

1. **The supervising-codex skill only describes paste mode.** This session
   ran a third mode: the human launches codex interactively in a tmux
   pane, the supervisor sends and reads via tmux, and the human watches
   live. The skill's "Claude does not run the codex CLI" line does not
   anticipate it, and the pause-and-ask rule (added mid-session to the
   prompt template) is what makes the mode safe. The skill should name
   the mode and its contract.
2. **Line pins rot within hours under an active main.** Three incidents in
   one session: a design-time path landed elsewhere (`docs/infra/` →
   `docs/database/`), a ruling's deliverable path superseded by a re-homing
   commit, and a rebase shifting a cited function by three lines between
   review and re-review. Dated records should carry a symbol anchor
   (function name, heading) beside every volatile line pin; the pin
   locates, the symbol survives.
3. **Supervisor prompts need the same path verification as doer output.**
   Both stale-path incidents entered through the supervisor's own prompt,
   copied from frozen snapshots without checking the tree. The staging
   checklist now says: verify every staged path against the current tree,
   never against frozen evidence.
4. **A busy/idle pane monitor is a workable question channel, with known
   noise.** Polling the codex TUI status line every 15s and emitting on
   Working→idle transitions caught every question and the completion;
   mid-work render flickers produced roughly one spurious event per three
   real ones. Fine for a watched session; a debounce (idle for 45s) would
   fix it.
5. **Bounded review plus rebase interact badly with line pins.** The
   end-of-phase rebase invalidated a citation the fix cycle had just
   added, consuming the re-review on a mechanical artefact. Rebase first,
   then review, when both are due at a phase boundary.
