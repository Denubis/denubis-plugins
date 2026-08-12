---
name: supervising-codex
description: Use when dispatching, monitoring, or verifying Codex in a joined tmux pane - prompt loop, event monitor, context hygiene, verification pass
user-invocable: true
---

# Supervising Codex

## Overview

Three roles, never merged. **Codex drafts** (OpenAI GPT-5.6 Sol, `gpt-5.6-sol`, via the
codex CLI, as of 2026-07-17). **Claude supervises**: stages the context, writes the
prompt, verifies the output against the repo. **The human rules**: adjudicates decisions
and owns every commit.

The split exists because a model cannot reliably verify its own work and favours its own
output. The supervisor must be a different model from the doer, and the doer's self-report
is never evidence. Field record (2026-07-16/17): codex twice self-reported "zero findings"
on its own drafts, and the supervision pass found a decision smuggled past the human in
one and a real collection-breaking defect in the other.

**The supervisor is not the trusted party either.** Brian's ruling (2026-07-21): "the
fundamental task for the various supporters to do is to doubt what you say, and make
reality prove it." Doubt runs in every direction, and the supervisor's staged context is
the least-checked thing in the loop precisely because it arrives labelled as verified. See
*Supervisor-asserted context*.

## Division of labour

**Anything beyond a single trivial edit routes through codex** (Brian, 2026-07-19). The
reason is budget rather than role purity: the supervising model's usage is the scarce
resource and codex's is separate. Multi-file changes, edit batches, revision passes and
anything substantive are codex tasks. The supervisor may still make a one-off trivial
edit directly, a comment or a docstring line, when a dispatch would cost more than it
saves.

Supervision artefacts are always the supervisor's to edit: `codex-prompts/`, findings
documents, and plan documents. Handing codex its own prompt to revise loses the boundary
the whole arrangement depends on.

This is the same concern the weekly quota check answers from the other side. Routing work
to codex protects the supervisor's budget, and codex has a budget too, so check its
headroom before handing it a long phase.

## What the consuming project must provide

This skill supervises codex **in someone else's repo**. Two things must exist there before
the loop works, and neither is optional (Brian, 2026-07-28):

- **An untracked `codex-prompts/` directory**, gitignored, as the file-exchange surface.
  Prompts go in as `NN-<task>.md`; codex writes deliverables to `codex-prompts/out/`;
  anything staged from outside the repo is copied under `codex-prompts/context/`. It is
  gitignored because it is working space, and because staging decides the disclosure
  surface rather than the commit history.
- **An ADR register.** Anything ruled along the way belongs in the project's decision
  records, indexed. Codex is told to say so when a prompt produces a ruling, because a
  decision that lives only in a pane is a decision that gets re-litigated next week. The
  project names its own location (`docs/decisions/adr-register.md` and
  `docs/architecture/decisions/` are both in use across Brian's repos); the skill requires
  that one exist, not that it sit anywhere in particular.

If either is missing, say so and stop rather than improvising a substitute. A prompt
directory that is tracked leaks working drafts into history; a project with no register
turns every ruling into oral tradition.

## Invoking the supervisor

Every command below is this script:

```sh
uv run --no-project --no-config python "${CLAUDE_PLUGIN_ROOT}/scripts/codex_supervisor.py"
```

Written as `codex_supervisor.py …` from here on, for readability.

`${CLAUDE_PLUGIN_ROOT}` is set when Claude Code invokes a plugin component, and unset in a
plain shell. When it is unset, resolve the path rather than guessing at one:

```sh
# In a checkout of this repo, from any subdirectory:
"$(git rev-parse --show-toplevel)/plugins/denubis-external-agents/scripts/codex_supervisor.py"

# From the marketplace install (stable path, no version component):
~/.claude/plugins/marketplaces/denubis-plugins/plugins/denubis-external-agents/scripts/codex_supervisor.py
```

The repo form goes through `git rev-parse` because a bare relative path resolves only at the
repository root and fails one directory below it.

If neither path is present, list every match rather than taking the first. `~/.claude/plugins/cache/`
holds one copy per installed version, and `find … | head -1` was observed returning a
different file on two consecutive runs, so it can hand you a stale version silently:

```sh
find ~/.claude/plugins -name codex_supervisor.py -path '*denubis-external-agents*'
```

There is no shell wrapper for this tool: the Python file is the whole interface. **This plugin
ships no `codex-watch.sh` and none is planned.** That filename comes from the google-live repo,
so looking for one here sends you hunting for a file this plugin has never contained.

The verbs, read from the parser rather than from memory:

| Verb | Effect |
|---|---|
| *(none)* | run the watch loop, emitting only actionable events |
| `--resolve` | print the joined Codex pane ID |
| `--spawn [--label NAME]` | open a Codex pane beside this one |
| `--send PROMPT_FILE` | send the standard ping for one prompt file |
| `--message TEXT` | send one literal message (`-` reads stdin) |
| `--clear` | start codex on a fresh session, confirmed by its session id changing |
| `--compact` | have codex summarise its transcript, confirmed by the context meter |
| `--quota` | run `/status` and report the weekly allowance and its reset |
| `--under-floor` | dispatch below the 30% context floor, carrying a human ruling |
| `--tail [N]` | print the joined pane's non-blank tail (default 12 lines) |
| `--status` | print the joined pane's status line |

None of them takes a pane ID. Each resolves the pane itself, for the reasons under
*Sending a prompt*.

Every verb that types into the pane refuses first unless the title is `Ready`, the
composer is empty, and **no approval dialog is pending**. That last guard is the tool's
rather than the operator's, because a dialog leaves the title `Ready` and the composer
empty, so the other two checks pass over precisely the state where a keystroke does the
most damage.

## The supervisor is the only way in

**Every keystroke reaching the joined pane goes through `codex_supervisor.py`.** A raw
`tmux send-keys`, a `tmux paste-buffer`, or anything else aimed at the pane by hand is
out of bounds, whatever it is for and however small it looks.

The verbs are not a convenience wrapper over the tmux calls. They resolve the pane,
refuse approval dialogs, catch half-typed slash commands before Enter takes a neighbouring
entry, and confirm the effect from the resulting pane state.

**When the tool cannot do what you need, that is a bug report, not an invitation to
improvise.** Tell the human what you were about to type and why the verbs did not cover
it, and let them rule on whether the tool grows a verb.

There is no exception. Every slash command this skill needs has a verb, and the last one
without one, the `/status` quota panel, became `--quota` on 2026-08-01 rather than being
left as a documented licence to improvise.

## The loop

1. **Claude writes a numbered prompt** to `codex-prompts/NN-<task>.md`, staging everything
   codex needs:
   - paths to context files, with copies of anything outside the repo staged under
     `codex-prompts/context/`;
   - every human ruling, numbered and carried **verbatim**, so codex cites rulings instead
     of re-deciding them;
   - the deliverable's format contract;
   - the standing rules, which almost every prompt should end with: *do not reopen ruled
     decisions; flag contradictions loudly rather than resolving them silently; report
     what you could not check rather than inferring it; never assert an absence from a
     single search; if there is any uncertainty, stop and ask the human one specific,
     critical, pointed question at a time, never bundled and never resolved by silent
     assumption, until the uncertainty resolves; and anything ruled along the way probably
     belongs in the project's decision records, indexed in its ADR register*. The
     one-question rule binds the supervisor too: when Claude is unsure, it asks the human
     the same way;
   - **the write scope, stated by the prompt itself.** A drafting stage writes one
     document under `codex-prompts/out/`; a code phase writes source, tests, and generated
     data into its own worktree. Neither the skill nor the sending tool may assert one
     globally, because whichever it picked would contradict the other kind of task. This
     bit on 2026-07-23: the ping hardcoded the drafting-stage scope, contradicted an
     implementation prompt, and codex correctly stopped to ask which governed rather than
     scattering files;
   - for a **code phase**, the vendor-guidance rule (Brian, 2026-07-17): before
     implementing each component, codex checks the current official documentation for the
     parts that task touches, implements the mechanics per that guidance within the ruled
     contracts, records each check in `notes.md`, and stops to ask when guidance
     contradicts the phase file. Mechanics only; ruled decisions stay closed.
2. **The prompt reaches codex.** The human pastes this ping by default:

   ```
   Read codex-prompts/NN-<task>.md and carry out that task exactly. If
   anything is unclear, ambiguous, or contradictory, stop and ask one
   specific, critical, and pointed question at a time until you have
   sufficient information. Surface any decision rather than deciding it
   silently, so the supervisor documents it.
   ```

   Claude does not drive codex unless the human has explicitly said this session may. When
   it may, `codex_supervisor.py --send` delivers that same ping; the prompt's own output
   contract governs, and the sending mechanics below are not optional.
3. **Claude verifies the output against the repo** before any of it lands in tracked
   documentation (see *Verification pass*).
4. **The human validates.** Rulings from that discussion go into the next prompt, numbered.

## Codex does not commit

**Ruled by Brian, 2026-07-19.** Every git command codex issues needs a per-dialog
approval, so letting it stage and commit traps the supervisor in an approval loop. Worse,
keypress approvals race the dialogs, so "approved" on screen is not evidence that anything
ran.

Prompts therefore tell codex to **edit and verify only**. The supervisor stages and commits
from outside the pane, split by concern, after verifying.

**Ground truth for what landed is `git log` and `git status`, never the pane scrollback.**
A pane showing a successful commit is showing a rendering, and the two come apart exactly
when an approval was raced. Verify a push at the remote with `git ls-remote` rather than
trusting an exit code, for the same reason.

## Staging context: redact before you stage

Anything staged under `codex-prompts/context/` is sent to OpenAI when the prompt runs.
Sessions, transcripts, and data directories can carry participant material and credentials
captured in passing, so raw records are never staged. Stage a **structural digest**
instead: record types, frequencies, and key skeletons with every string and number
replaced by a type marker, keeping only discriminator fields verbatim. Say in the prompt
that content was withheld and why, so codex reports what it could not verify rather than
inventing it.

## Sending a prompt to the joined pane

`codex_supervisor.py --send codex-prompts/NN-<task>.md` sends the standard ping in one
call, and `--message TEXT` (or `--message -` for stdin) sends arbitrary text. Both resolve
and capture the pane themselves, refuse unless the title is `Ready` and the composer is
empty, and never take a pane ID. The supervisor still inspects `--tail` to confirm that
the uniquely resolved pane contains the expected prior exchange. The guards exist because:

- **Resolve the pane every single time; never reuse a coordinate.** tmux renumbers windows
  as windows open and close, so `session:window.pane` goes stale mid-task and can type into
  another project's session. Pane IDs (the `%`-prefixed form) are stable for the pane's
  life. Resolution is by `$TMUX_PANE` and the same-window uniqueness rule the monitor uses.
- **Path alone does not identify the pane.** Several codex sessions can share one working
  directory; one field repo had three at once. Confirm by scrollback that the candidate
  holds *your* prior prompt and output.
- **Capture before sending.** Confirm the composer is empty and the pane is `Ready`. Never
  send into a pane you have not just looked at, and never into one you cannot positively
  identify.
- **Type literally, verify, then submit separately**, so a stray key name is never
  interpreted and a partial paste is never executed.

**A paste too long for the composer is drawn as `[Pasted Content N chars]`.** The full
text is there, and the placeholder is how codex draws it rather than evidence of a
truncated or mangled paste. Observed on a live pane on 2026-07-31, where 1584 characters
rendered as one cyan placeholder. So nothing needs splitting into shorter sends and the
composer needs no clearing. What does follow is that the message's own text is never on
screen at all, and its absence therefore cannot be read as a composer that accepted and
cleared. `--send` and `--message` confirm a submission by the pane going `Working` or the
composer emptying, and they raise rather than return when neither happens within three
Enter attempts.

**Re-capture after Enter and confirm the pane moved to `Working`.** Seeing the text in the
composer before Enter is not evidence that it submitted, because an Enter after a large
paste has been seen to leave the content sitting there unsent, for reasons nobody has
established. The check costs one call and catches the failure whatever its mechanism turns
out to be. Clearing a composer is `C-a` then `C-k`, and `C-u` does not do it.

**Never send a prompt or a slash command into a pane holding a pending approval.** Any
keystroke answers the dialog that is on screen, so a `/clear` typed blind approves
whatever was waiting. Every verb now refuses on that state rather than leaving it to the
operator to remember, which is the whole argument for routing keystrokes through the
tool: the guard runs whether or not anyone was thinking about it.

**Codex revises after it first reports done.** A stage-2 output grew by 393 bytes two
minutes after the pane read `Ready`. `DONE` starts a file-settling check; it does not prove
that the output bytes have settled. Verify a draft only once its size and mtime remain
stable, or the pass burns on a half-written file and pins line numbers that then move.

## Who answers an approval

The rule above is about sending blind. Answering a dialog you have read is a different
act, and it belongs to whoever is driving codex.

**The human answers supervisor approvals**, meaning the rulings, scope calls and design
decisions that surface in Claude's own pane. **Codex's per-command sandbox dialogs belong
to the driver.** When the human has said this session may drive codex, Claude answers
those with `codex_supervisor.py --approve` rather than handing back each keypress. A pass
made of probes and pytest runs generates one dialog per command, so routing every one to
the human is the approval loop that *Codex does not commit* was ruled to prevent.

The verb refuses unless a dialog is genuinely pending, names the command it approved
and nothing else, confirms the screen cleared, and then carries back the first thing
Codex went on to do, so one call covers the whole round trip from announcement to
outcome. A pane that has said nothing within the wait is reported as still working,
which is a different answer from a pane that failed. Codex draws two dialogs, an
older `Yes` and `No` pair on a single line and a commoner three-option list running
`Yes, proceed`, a standing grant, and `No`, one to a line, so the verb reads each
option's label rather than counting positions and answers with the key the label
advertises where Codex prints one. It takes the affirmative granting nothing beyond the
command on screen. A `Yes, and don't ask again` is refused and goes to the human,
because a standing grant changes the posture of the whole session. Two affirmatives that
both read as narrow are refused on the same grounds, so a standing grant worded in some
way the verb does not recognise reaches the human rather than being pressed.

## Checking the quota before you dispatch

Codex meters a weekly allowance. The pane title carries a percentage, and a percentage on
its own cannot say whether you are on track: half the allowance left on day two is a
problem, and the same figure on day six is fine. What settles it is the reset date, which
`/status` reports and the title does not.

```sh
codex_supervisor.py --quota
```

It reports both halves of the answer and nothing else:

```
quota on %58: weekly 99% left, resets 14:41 on 8 Aug
```

The panel itself carries the signed-in account and the session id, so the verb reads the
figures out and leaves the rest on screen rather than carrying it back.

Two details of the panel are worth knowing, because both have already caught a naive
reading. A second model's allowance is reported directly beneath the first, so the
`resets` line belonging to the primary limit is the one above it rather than the last one
on screen. And an answered `/status` stays on screen, so the verb anchors on codex's echo
of the command and reads the panel below it. Counting panels does not work, since drawing
a new one scrolls the older one off the visible capture and the count goes from one to
one, which refused a perfectly good second reading when it was tried on 2026-08-01.

Compare what remains against how much of the week remains. If the burn is running ahead of
the calendar, hand codex a smaller phase, split the work, or wait for the reset. Run the
check when a pane first comes up, and again every few clears, since a long drafting phase
can move the figure a long way in one turn.

## Context hygiene: clear between prompts

**Compacting the pane is `/compact`, and nothing else is. Clearing it is `/clear`.** Type
the slash command into the composer. A prose request is a task, not a compaction, and a
self-report is not evidence that the TUI command ran. Read the meter through the verb.

**Cadence (Brian, 2026-07-28): aggressively, between tasks, rather than once the meter has
run low.**

- **`/clear` between prompts, as the default.** Each prompt is written to
  `codex-prompts/NN-<task>.md` as a self-contained brief carrying its own rulings, so
  context lost to a clear is restated rather than remembered. That restatement is the cost
  the numbered-prompt discipline already exists to pay.
- **`/compact` when the next prompt follows directly on** from the one just finished.
- **A clear carries less risk than a compaction when the prompt is good** (Brian,
  2026-07-28). A clear starts from a known-empty state, whereas a compaction leaves behind
  a summary whose fidelity nothing checks.

Authority records:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/494077d8-3c4e-49eb-ba60-beb1ba5f38fe.jsonl:1347`
  (`cc-search-chats context d7875278-05ce-42e4-bf7f-7ff42f6a06d0 --json`)
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/494077d8-3c4e-49eb-ba60-beb1ba5f38fe.jsonl:1375`
  (`cc-search-chats context 64d0c6c7-eebf-4d4c-b8b8-c9d3428209f4 --json`)

Both are verbs, and neither is a message:

```sh
codex_supervisor.py --clear
codex_supervisor.py --compact
```

Each types the command as keystrokes on its own line, confirms what the composer holds
before Enter is a separate call, and then waits for the pane to come back `Ready` before
reporting. The waiting is the point: a clear restarts codex and its MCP servers, and a
compaction is a model call over the whole transcript, so a verb returning the moment the
effect appears hands back a pane that the next dispatch refuses as not Ready, which costs
a supervisor round to discover something the verb already knew.

**Each is confirmed by evidence, and the evidence differs because the two commands do
different things.**

`/clear` does not wipe a screen. It ends codex's session and starts another one, and the
pane title carries that session's id:

```
Ready | brian-ed3d-plugins | main | weekly 99% left | 019fbc8c-ac0b-79d3-… | gpt-5.6-sol
                                                      ^^^^^^^^^^^^^^^^^^^ the session id
```

So a clear that ran leaves a different id there from the one that was there before, and
`--clear` reads it either side and reports both.

`/compact` keeps the same session and the same transcript, so its id is unchanged and
cannot say anything. What moves instead is the context meter, and `--compact` reports it
either side and refuses when the figure has fallen.

The confirmations cannot be shared, and that is what makes them worth having. Codex's
completion list puts `/compact` first on the prefix `/c`, so a `/clear` typed one
character short and submitted would compact instead. A shared confirmation would call
that a success.

Typing the command in full narrows the list to the one entry, which is the state the
verb requires before it presses Enter. Where the list has not narrowed to exactly the
command asked for, the verb empties the composer and refuses, so an unrecognised
neighbour reaches the human rather than being submitted on the likelier reading.

## The context floor

**Below 30% context left, `--send` and `--message` refuse** (Brian, 2026-08-01). A pane
that far down cannot hold the answer to the prompt you are about to give it, and the
meter falls faster than it looks like it will, so the floor is set high on purpose.

The refusal names the reading and the remedies, which are `--compact`, or `--clear`
followed by restating the prompt. Neither `--clear`, `--compact`, nor `--approve` is
gated: the first two are what relieve the floor, and refusing to answer a dialog would
strand codex mid-task with nothing able to release it.

`--under-floor` carries a human ruling past the refusal. It exists so that a human can
say yes, not so that the supervisor has a way around a halt, and reaching for it without
having asked is the same improvisation as reaching for `send-keys`. An unreadable meter
refuses on the same terms, because a gate that passes when it cannot see is not a gate.

## Same-window event monitor

Launch the joined Codex pane through the monitor rather than assembling a tmux command by
hand:

```sh
codex_supervisor.py --spawn --label <name>
```

`--label` is optional and defaults to the spawned pane's working-directory name. The label
is stored as the pane-local tmux user option `@codex_label`; inspect it with
`tmux display-message -p -t '%10' '#{@codex_label}'` (substitute the pane ID printed by
`--spawn`). It deliberately does not use `#{pane_title}`, because Codex writes its live
status there and the monitor's status reading depends on that status line.

The spawn command is `exec codex -c check_for_update_on_startup=false -s workspace-write
-a on-request`. tmux gives that command to the configured login shell, which resolves
`codex` through `PATH`, and `exec` then replaces the shell instead of leaving it as the
pane process. This is load-bearing: the monitor accepts a pane only when
`pane_current_command=codex`, so a shell left running as the pane process makes the new
pane undiscoverable. The `-c` override uses Codex's documented configuration key to
suppress the startup update check; the official
[Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)
documents `check_for_update_on_startup` and its default of `true`.

**The sandbox is what bounds the damage, not the dialog count.** `-s workspace-write`
confines writes to the working tree, so a pass of probes and pytest runs needs no
per-command permission to do its job, and `-a on-request` leaves Codex to escalate only
when it wants to step outside that. Spawning with neither, as this skill did until
2026-07-30, inherits whatever `~/.codex/config.toml` or the built-in default supplies,
and a single verification pass then raised one dialog per command.

The trade is worth naming. `on-request` lets Codex decide when to ask, which is a model's
judgement rather than a policy, where `-a untrusted` would drive the same decision from an
allowlist and ask far more often. The sandbox is the containment either way, and the
allowlist buys its extra caution in dialogs. Pass `-a untrusted` by hand for a pane whose
work you have reason to distrust.

When Claude and Codex are joined as panes in one tmux window, start the monitor from
Claude's pane under the background Monitor tool.

**This plugin ships the monitor. Do not hand-craft one.** Arm it with exactly this and
nothing else:

| Monitor field | Value |
|---|---|
| `command` | `uv run --no-project --no-config python "<resolved>/codex_supervisor.py"` |
| `persistent` | `true` |
| `description` | what is being supervised, e.g. `codex prompt 08 cross-check` |

No other field. In particular:

- **No `timeout_ms`.** Supervision lasts as long as the session, so it is a persistent
  watch. A timeout kills the monitor mid-prompt, and a dead monitor is indistinguishable
  from a pane with nothing to say.
- **No `2>&1`.** The tool puts events on stdout and diagnostics on stderr deliberately.
  Merging them turns every diagnostic into a notification.
- **No `| grep`, `| tail`, `while` loop, or filter of any kind.** The monitor already
  emits only the four actionable events; anything wrapped around it can only subtract.
- **No pane ID, and no bare `tmux` command.** See below.

Then say plainly, in the reply, that the monitor is running **from this plugin** and what
it is watching. The human otherwise cannot tell a real monitor from an improvised one, and
the two fail in opposite directions.

Reach for a bespoke Monitor invocation only to watch something that is *not* the Codex
pane. If the plugin's monitor will not do what a Codex supervision task needs, that is a
bug report for the human, not a licence to assemble a replacement — the same rule, and the
same reasoning, as *The supervisor is the only way in*.

Do not pass a pane ID. The monitor resolves Claude's `$TMUX_PANE`, searches only that exact
tmux window, and requires exactly one foreground `codex` process. No match or multiple
matches is an error; it never searches other windows or guesses from a worktree name.

The monitor is silent for `Working`, `Waiting`, background terminals, compaction, output,
status flicker, and unknown TUI states. It emits only:

- `NEEDS APPROVAL`
- `QUESTION`
- `DONE`
- `CRASH`

Each line includes the joined Codex pane ID. Run `codex_supervisor.py --tail` to inspect
the joined pane's non-blank tail before acting; it resolves the pane itself rather than
taking an ID.

**Anything still pending is raised again on a backoff**, at two minutes, then five, then
every ten, with the repeat saying how long the pane has been waiting. The monitor used to
announce once and go quiet, which meant a line missed was a line gone; a pane sat blocked
for 57 minutes that way on 2026-07-27. A `CRASH` is not repeated, because it is terminal
and nothing can be done to the pane in response.

**After an hour unanswered it stops**, and the last line says `no further reminders` so
the quiet that follows reads as a decision rather than a dead monitor (Brian,
2026-08-04). The repeats exist to survive a line you missed, not to outlast a supervisor
that cannot answer, and a supervisor blocked on its own permission prompt is exactly the
case where the drum kept queueing: fifteen hours of ten-minute repeats delivered ninety
lines at once, all of them saying what the newest already said. The hour is spent per
waiting thing, so a genuinely new prompt gets the full ladder.

`DONE` is raised again like anything else, because a finished pane is waiting on a
decision rather than reporting an all-clear. Its line asks whether to compact, clear, or
quit, which is the choice the numbered-prompt loop expects at exactly that moment.

The reminder lapses as soon as Codex is busy, since a spinner means nothing is waiting on
you, and the clock is restored when the prompt is still there on the next poll. Until
2026-08-04 it was not: one busy frame disarmed a live approval permanently, and only
`classify_snapshot` matching approval text ahead of busy kept that from silencing panes.
That ordering is the guard that regressed in `fa54c31`, so the schedule no longer rests
on it alone.

Lifecycle hooks wake the monitor immediately for activity, permission requests, and turn
stops. They are installed **globally**, once per machine, rather than per project:

```sh
uv run "${CLAUDE_PLUGIN_ROOT}/skills/supervising-codex/hooks/install-codex-hooks.py"
```

A project-local `.codex/hooks.json` only wakes the monitor in directories somebody set up
in advance, which leaves a Codex started in a fresh directory unsupervised exactly when
nobody was thinking about supervision. The relay is project-local in its upstream home
only because the script it called lived in the project, and that is no longer true.

The installer merges rather than overwrites, is safe to re-run, and repairs a relay left
pointing at a script that has moved. `hooks/README.md` covers the `hooks = true` feature
flag it needs and which copy of the plugin to run it from. Trust the result with `/hooks`
in Codex, then restart any running Codex session, because hooks are read at startup. Until
they are trusted and loaded, the monitor keeps working through conservative tmux inspection
on its poll deadline.

The hook relay sends only event kinds, scope flags, and opaque digests; it does not
transport prompts, commands, tool results, transcripts, or assistant messages. It is also
safe to leave installed when nothing is watching, since a hook that finds no listener is a
silent no-op and exits 0.

The crash signal proves that the pane or foreground Codex process disappeared, was
replaced, or reached a recognized terminal error outside a busy title. Error-looking tool
output remains silent while Codex is working. The monitor cannot distinguish a legitimately
slow live subprocess from a hung one without a task-specific deadline or heartbeat.

**Do not go hunting for a second event source.** These hooks are the event source. A
desktop notifier that fires `notify-send` and exits leaves nothing to tail, and a
filesystem watcher needs `inotify-tools` installed plus something that actually writes a
file.

A candidate can also have been wired once and switched off since, which is the case that
misleads hardest, because the code is present, executable, and does nothing. The field
host's global `~/.codex/hooks.json` drove a tmux status glyph on four events until
2026-07-20, when it was deliberately cut back to a single desktop notification; the script
it called is still on disk and still executable. A survey on 07-23 therefore found nothing
live, and the same survey three days earlier would have found plenty. So check what a
candidate writes **now**, and check when its configuration last changed, because "the
script exists" and "the script runs" are different claims.

## Verification pass

Read the entire output. Check every load-bearing claim against the thing it claims about,
not against codex's report of it:

- **Paths and line pins.** Open each cited file; a pin that does not resolve voids the
  claim it supports.
- **Quotes.** Grep quoted phrases against the file they are attributed to.
- **Library and API claims.** Fetch the actual source or docs for anything the draft's
  correctness leans on, version-sensitive parameters especially.
- **Claimed repo state.** Re-run the checks codex says it ran (test counts, lint state)
  rather than transcribing them.
- **Rulings carried.** Confirm every numbered ruling appears intact and none was reopened.
- **Grepping the gitignored workspace.** `rg` silently skips gitignored paths, and
  `codex-prompts/` is gitignored, so a self-check or verification grep aimed at it must
  pass `--no-ignore` or name files explicitly. A bare `rg <pattern> codex-prompts/...`
  searches nothing and reports a vacuous pass (caught 2026-07-18: a codex self-check
  claimed zero legacy names while one remained).

A defect found in verification is fixed in the copy that lands in tracked documentation,
with the fix disclosed to the human. The `codex-prompts/out/` original stays untouched.

## Supervisor-asserted context

The pass above runs one direction, the supervisor checking the doer. It must run the other
way too. **Everything the supervisor stages into a prompt is a claim for the doer to doubt
and for reality to settle**, and a prompt is written so that doubting it is possible.

Field record (2026-07-21): in one session the supervisor asserted five false things, every
one the same shape, a negative drawn from a search that stopped one level short. It
searched for a concept in its own words rather than the repo's and reported the concept
absent while a shipped enum carried it. It scoped a corpus sweep to the issue mirror and
left out the decision records, the authority. It grepped one module for an invariant, found
nothing, and reported the invariant unenforced when the call it had not followed enforced
it in exactly the place a human ruling required. Every one of those reached the doer inside
a section headed *do not re-derive these and do not contradict them*, which is the
instruction that stopped the doer looking.

Second field record (2026-07-23), same shape, and this time the doer caught it. The
supervisor staged "Codex records `cwd`, never a branch. No git branch appears anywhere" as
established evidence, and built a design question to the human on top of it. It had
inspected the `session_meta` payload by printing its first 600 characters, which
`base_instructions.text` consumes entirely, so the inspection could not have reached the
`git` block it went on to deny existed. Codex flagged the contradiction against a staged
schema digest at stage 1 and refused to design over it. The withdrawn claim and its cause
are kept in the working findings rather than deleted, because the reasoning that produced
it is the thing worth recognising: **an absence asserted from an inspection that was
structurally incapable of finding the thing.** Truncated output is not a search.

That was not an isolated slip. The same supervisor repeated the identical shape **five
times in one session**, having written the rule above:

| The check | Why it could not have found it |
|---|---|
| printed 600 chars of a JSON payload | `base_instructions.text` consumed all of it |
| `complexipy <explicit path>` | the explicit path overrode the configured scope, inventing a blocker |
| `grep -c 'add_argument("--x"'` | the source wraps those calls across lines |
| regex `[0-9a-f]{7}$` on `name(sha)` | the string ends in `)`, so it matched nothing |
| glob `<project>/*.jsonl` for sidechains | sub-agent shards live in `<session-uuid>/subagents/` |

Every one produced a confident finding. Two reached the human as false alarms, one
propagated into a committed design document, and the last would have made 3607 real records
invisible had codex not tripped over them.

**The exhortation is not the fix, because the rule was already written here.** The fix is
procedural, and it costs one extra line per check:

- **Never report an absence from a check you have not seen succeed.** Before trusting "not
  found", feed the check something that *must* match. A detector whose control does not
  fire is BROKEN, and broken is no evidence, not a pass.
- **A pass over an empty set is VACUOUS, not a pass.** Zero findings across zero inputs
  proves nothing; say so rather than banking it.
- **Search the code's vocabulary, not your own.** `is_ready` found nothing because the
  guard was called `_preflight_send`; the capability was there all along.
- **Prefer the tool's own interface to a grep of its source.** `--help` listed all six
  verbs that `grep -c` had counted as two.
- **When a check contradicts a plain reading, suspect the check first.** `git log` showed
  the ancestor that `merge-base` denied; the regex was wrong, not git.
- **Label staged findings by provenance.** Human rulings and frozen evidence are
  do-not-contradict. Anything the supervisor derived is **supervisor-asserted, verify
  before relying**, and it names the command that produced it so the doer can re-run it.
- **Never assert an absence from one search.** "X is not enforced", "Y appears nowhere",
  "no production code constructs Z" each need the call chain followed, or a positive
  control proving the search would have found the thing had it been there.
- **A doubter beats an agreeable second opinion.** Where a supervisor conclusion is
  load-bearing, hand it to a different model to *falsify*, told to write its own probes
  rather than reuse the supervisor's, since reusing them inherits their errors. On
  2026-07-20 that pass reversed a human ruling the supervisor had argued for on reasoning
  resting on a composition that does not exist in production.
- **Human rulings are quoted, and their question comes with them.** An answer like "queue
  as necessary" is not interpretable without the question it answered. Stage both, marking
  which words are the human's.

## Evidence freezing

Anything a committed document cites from `codex-prompts/` must be frozen first: copy the
cited files byte-for-byte into a dated directory beside the document, rewrite the citation
prefix, and add the directory to the project's repo index in the same commit. Line numbers
in frozen snapshots are load-bearing; never edit them.

## Quick reference

| Situation | Action |
|---|---|
| Starting a codex session | `codex_supervisor.py --spawn --label <name>` |
| Checking weekly headroom | `codex_supervisor.py --quota` |
| Watching it | `codex_supervisor.py` under Monitor, `persistent: true`, nothing else added |
| Checking what a pane holds | `codex_supervisor.py --tail` |
| Dispatching a prompt | `codex_supervisor.py --send codex-prompts/NN-<task>.md` |
| Between prompts | `codex_supervisor.py --clear` |
| Directly-following prompt | `codex_supervisor.py --compact` |
| Dispatch refused below 30% | `--compact`, or `--clear` and restate the prompt |
| The human rules to push on anyway | add `--under-floor` to that one dispatch |
| Codex asks to run a command | `codex_supervisor.py --approve` |
| The approval wants a ruling, not a keypress | that one is the human's |
| Codex reports done | wait for size and mtime to settle, then verify |
| Tempted to reach for `tmux send-keys` | tell the human what the verbs do not cover |

## Red flags

- "Codex's review found nothing, so this is done." The doer's self-review is input, not a
  gate; the supervision pass still runs in full.
- "The pin is probably fine." Unresolved pins void claims. Open the file.
- "I'll tidy the frozen snapshot." Frozen means byte-for-byte, forever.
- "This decision is obvious, codex can just pick." If it is obvious, record it as an
  adopted default; if it is not, it goes to the human. Codex decides neither.
- "I grepped and it wasn't there." One search proves nothing absent. Follow the call chain,
  or run a positive control that would have found it.
- "This is verified context, codex can rely on it." Only when a human ruled it or it is
  frozen evidence. Everything else is the supervisor's claim and is labelled as one.
- "Settle the limit" / "settle the policy" in a prompt. An instruction to settle a number
  invites an invented number, which then hardens into an acceptance criterion and a test.
  Assign the concern to its owner instead.
- "I asked codex to compress its context." That is a task, not a compaction. Run
  `--compact`.
- "I'll just send `/clear` with `--message`." That pastes the text into the composer as a
  message. `--clear` types it, and the difference is whether codex runs the command or
  reads it.
- "The verbs don't cover this, so I'll use `tmux send-keys` this once." That is the bug
  report. Say what you were about to type and let the human rule.
- "I'll add a timeout / `2>&1` / a grep to the monitor command." Every addition is a
  hand-crafted monitor. The plugin ships one; arm it bare and `persistent: true`.
- "Context is at 22%, but this prompt is small." The floor is not a suggestion about
  prompt size. Compact, or clear and restate, or get the ruling.
- "It said DONE, so that one is finished." DONE is a decision point, not an all-clear.
  Clear or compact the pane before the next prompt, or the context you did not reset
  becomes the context the next task inherits.
