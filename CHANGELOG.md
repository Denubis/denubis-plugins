# Changelog

## [marketplace] 2.1.0

`denubis-external-agents` 0.12.0. No plugin added or removed, so the catalogue itself takes a minor bump.

## [denubis-external-agents] 0.12.0

Context handling for a joined codex pane becomes tool behaviour instead of prose the supervisor had to re-derive each session.

**New:**
- `--clear`, `--compact` and `--quota` verbs on `codex_supervisor.py`. Each types the slash command as keystrokes on its own line, so codex runs it. Delivered as prose or through `--message`, codex reads it as a task and the context meter goes down.
- Each verb confirms its own effect and waits for the pane to return to `Ready` before reporting, so no follow-up call is needed to learn whether the pane can take the next prompt. A clear is confirmed by codex's session id changing in the pane title, a compaction by its context meter not falling, and a quota check by the panel drawn below codex's echo of the command.
- A 30% context floor on `--send` and `--message`. Below it the dispatch refuses and names the reading and the remedies. `--under-floor` carries a human ruling past it, and an unreadable meter refuses on the same terms.

**Changed:**
- The pending-approval guard moved into the shared preflight, so `--send` and `--message` refuse it too. A dialog leaves the title `Ready` and the composer empty, so both older guards passed over the one state where a keystroke does the most damage.
- `supervising-codex` now routes every keystroke through the tool and names a hand-typed `tmux send-keys` as a bug report rather than a fallback.

## [denubis-external-agents] 0.11.4

`--send` reported a message as delivered while it was still sitting in the composer. A paste too long for the composer is drawn as `[Pasted Content N chars]`, so the message's own text is never on screen at all, and the check that went looking for it read that absence as a composer which had accepted and cleared.

**Fixed:**
- `_submitted` confirms a submission by positive evidence, the pane going `Working` or the composer emptying, rather than by failing to find the message's text in the last few lines of the pane. The old check fired on the first poll for any collapsed paste, and equally for any message whose first line had scrolled out of that window, so it was not only long pastes that could be called sent while unsent.

**New:**
- The paste is counted before it is submitted. Codex reports a length in its placeholder and the sender already knows what it wrote, so `--send` and `--message` compare the two and refuse a partial paste instead of pressing Enter at it. Codex's counting of non-ASCII text has not been measured, so a count matching either the character length or the UTF-8 byte length is accepted.

**Changed:**
- The `supervising-codex` skill records that the placeholder is display compression rather than a mangled paste, so a long instruction needs no splitting into shorter sends and the composer needs no clearing. A hand-typed send is confirmed by re-capturing and watching the pane move to `Working`, because an Enter after a large paste has been seen to leave the content unsent for reasons nobody has established. Clearing a composer is `C-a` then `C-k`.

## [denubis-external-agents] 0.11.3

Codex wraps a long option and a long command, and 0.11.2 could read neither. Since Codex commands are routinely long, this was the ordinary dialog rather than an unusual one.

**Fixed:**
- `_approval_options` reads an option whose label wraps. Codex indents the remainder past the column its numbers start at, and that remainder is not itself a numbered line, so a block read as a run of numbered lines ended at the first wrap and lost every option above it. A three-option dialog came back as no options at all, and the refusal rendered an empty list. The block is now bounded outwards from the last numbered line, taking in the continuations belonging to each option, which also keeps a standing grant from being read as narrow because its `don't ask again` fell on the far side of a wrap.
- `_approval_material` rejoins a command across its wrap instead of naming it as far as the pane was wide. The join stops at a blank line, at the option list, or at the dialog's own furniture, so a `Press enter to confirm` below the command is not read as part of it.

## [denubis-external-agents] 0.11.2

One `--approve` call now covers the whole round trip, from the command being asked about to what Codex did once it ran.

**Fixed:**
- `--approve` names the command and nothing else. `_approval_material` had read a fixed window of a few lines around the last marker on screen, which finds the command on the older dialog, where it is drawn above the question, and returns a slab of option text on the taller one, where it sits below the reason block. The search now runs across the whole dialog, bounded above by the bullet or rule closing the previous turn and below by the option list, so a command from an earlier turn cannot be named as this one. An approval carrying no command names its question instead. This also fixes what the monitor announces for an approval, not only what the verb prints.

**Changed:**
- `--approve` waits a bounded while after the dialog clears and reports the first thing Codex draws, so the answer says what happened rather than only that a key landed. The working spinner is drawn as a bullet and is passed over, and a pane that has stayed silent is reported as still working rather than guessed at.

## [denubis-external-agents] 0.11.1

`--approve` could not answer the dialog Codex most often draws, and sent it back to the human as having no affirmative on offer. A separate defect the repair exposed, `_approval_material` missing the `$` command line on a dialog this tall, is left for its own change.

**Fixed:**
- `approval_choice` reads the three-option dialog, where each option sits on its own line and a standing grant sits between `Yes, proceed` and `No`. The option parser had required two options on a single line, which is the older shape, so on the commoner one it returned nothing at all and every such dialog was refused. Selection now reads each option's own label rather than requiring a bare `Yes`, takes the affirmative that grants nothing beyond the command on screen, and answers with the key the label advertises, `y` rather than a list number, wherever Codex prints one.
- Two affirmatives that both read as narrow are refused rather than guessed between, so a standing grant worded in some way the check does not recognise reaches the human instead of being pressed.

## [denubis-external-agents] 0.11.0

Codex approvals stop being a keypress treadmill for the human, from both ends: fewer dialogs are raised, and the ones that are raised can be answered in one call.

**New:**
- `codex_supervisor.py --approve` answers a pending approval dialog. It refuses unless a dialog is genuinely pending, selects the plain `Yes` by the number printed beside it rather than assuming a position, prints the command it approved, and confirms the screen cleared before reporting success. A dialog whose only affirmative is `Yes, and don't ask again` is refused and left for the human, because a standing grant changes the posture of the whole session.
- `supervising-codex` gains a *Who answers an approval* section. The human answers supervisor approvals, meaning rulings and scope calls; Codex's per-command sandbox dialogs belong to whoever is driving Codex.

**Changed:**
- `--spawn` now passes `-s workspace-write -a on-request`. Containment comes from the sandbox rather than from a dialog per command, so a verification pass of probes and pytest runs no longer raises one approval per command. The skill records the trade against `-a untrusted`, which drives the same decision from an allowlist and asks far more often.
- The rule against sending into a pane holding an approval now says what it was always about, sending a *prompt or slash command* blind. Its quick-reference row, which compressed to "send nothing; the human answers it", was read as assigning every dialog to the human and became two rows that cannot be quoted into that reading.

## [denubis-external-agents] 0.10.1

A documentation fix in `supervising-codex`, after an agent went hunting for a script this plugin has never contained.

**Fixed:**
- `supervising-codex` gave the supervisor's location as `"${CLAUDE_PLUGIN_ROOT}/scripts/codex_supervisor.py"`, with only a prose fallback for when that variable is unset, which it is in any plain shell. It now gives two resolutions that work: a `git rev-parse --show-toplevel` form valid from any subdirectory of a checkout, and the marketplace install path, which carries no version component and so stays stable across releases.
- The listing fallback no longer pipes `find` through `head -1`. `~/.claude/plugins/cache/` holds one copy per installed version, and `head -1` was observed returning a different file on two consecutive runs, so it could hand over a stale version without saying so.
- The same section now states that the tool has no shell wrapper and that this plugin ships no `codex-watch.sh`. Looking for that shim here, on the strength of a note describing the google-live repo, is what produced a false report that the skill pointed at a missing script.

## [denubis-external-agents] 0.10.0

Two operator rulings rescued from hand-rolled copies of the skill before those copies are retired.

**New:**
- **Codex does not commit** (Brian, 2026-07-19). Every git command codex issues needs a per-dialog approval, so letting it stage and commit traps the supervisor in an approval loop, and keypress approvals race those dialogs, so "approved" on screen is not evidence anything ran. Prompts tell codex to edit and verify only; the supervisor commits from outside the pane. Ground truth for what landed is `git log` and `git status`, never the scrollback, and a push is verified at the remote with `git ls-remote` rather than by an exit code.
- **Division of labour** (Brian, 2026-07-19). Anything beyond a single trivial edit routes through codex, for budget rather than role purity: the supervising model's usage is the scarce resource and codex's is separate. Supervision artefacts stay the supervisor's to edit.

**Note:** a third section unique to those copies was deliberately not ported. It prescribed compressing a codex pane with a prose keep/drop brief, which 0.8.0 recorded as falsified: the brief is read as work and the context meter goes down.

## [denubis-external-agents] 0.9.1

**Fixed:**
- `advisor-send.sh` refuses to drive a pane that is not an agent pane in the caller's own window. It previously asked only whether the pane existed *somewhere*, and `list-panes -a` is every pane in every session, so a stale or mistyped id passed the check and typed the message into whatever pane now holds that id. Pane ids are reused as panes close, which is the same hazard `codex_supervisor.py` avoids by resolving the pane itself rather than accepting one.
- There is deliberately no fallback. An earlier draft degraded to the old existence check with a warning on the grounds that this was no worse than before, but "no worse than before" means a stale id still types into somebody else's window, which is the defect. A guard with a documented bypass is a suggestion.

**New:**
- `scripts/tmux-send-guard` ships with the plugin, so a marketplace install carries its own copy and there is no machine where the guard can be missing. It scopes to the caller's window and requires the pane to be running claude, codex or agy2, walking process descendants because a Claude pane reports its foreground command as `bash`.

## [denubis-external-agents] 0.9.0

The codex hook relay becomes global, because per-project wiring left new directories unsupervised.

**Changed:**
- The relay installs into `~/.codex/hooks.json` once per machine rather than into each project's `.codex/hooks.json`. A project-local hook only wakes the monitor in directories somebody set up in advance, which leaves a Codex started in a fresh directory unsupervised exactly when nobody was thinking about supervision. The relay was project-local upstream only because the script it called lived in the project, and that stopped being true when the script moved into this plugin.

**New:**
- `skills/supervising-codex/hooks/install-codex-hooks.py` merges the five relayed events into the user's global hooks. It preserves hooks it did not write, since it edits a machine-level file other tools also configure; it backs up before writing; it is idempotent; and it repairs a relay left pointing at a script that has moved, because the command names an absolute path and a check that only asked "is a relay present?" would leave every hook on the machine invoking something that is gone.

**Removed:**
- `hooks/project-codex-hooks.json` and `hooks/global-codex-hooks.json`, superseded by the installer.

## [denubis-external-agents] 0.8.2

**Fixed:**
- The shipped `.codex/hooks.json` template told the reader to copy it to `.codex/hooks.json`, which reads as nonsense once it is that file. It now says what is still true in place: trust with `/hooks` and restart any running session.

## [denubis-external-agents] 0.8.1

**New:**
- `supervising-codex` checks the weekly quota before dispatching. Codex meters a weekly allowance, and the pane title carries only a percentage, which alone cannot say whether the burn is on track: half left on day two is a problem and the same figure on day six is fine. `/status` reports the reset date the title omits, so the check is the slash command read against the calendar, sent as two `send-keys` calls and gated on the pane not holding an approval, then read back with `--tail`. Run at spinup and every few clears, since one long drafting phase moves the figure a long way.

## [denubis-external-agents] 0.8.0

The monitor stops going quiet on you, and ships the hook wiring it always assumed.

**New:**
- A pending action is raised again on a backoff: two minutes, then five, then every ten, with the repeat saying how long the pane has been waiting. Announcing once was deliberate, since a stationary screen is re-observed every poll and an ungated repeat trains the reader to ignore it, so the repair is a clock rather than a removed guard. `CRASH` is exempt, being terminal. The reminder lapses while Codex is busy, which cannot lose a live approval because a waiting pane classifies as `APPROVAL` on every poll and re-arms.
- `DONE` now asks whether to compact, clear, or quit. A finished pane is waiting on a decision about its context rather than reporting an all-clear, and that is the moment the numbered-prompt loop expects a clear.
- `consulting-a-fable-advisor` stops prescribing a compaction that does not compact. The keep/drop judgement now rides on `/compact`'s instruction argument rather than a chat message, and the claim that any persistent external session wants the same treatment is withdrawn: codex is a different tool, where a prose brief is read as work. Sending one there moved a pane's meter from 21% to 18% while codex reported "Context compressed as specified" and nothing had been compacted.
- `skills/supervising-codex/hooks/` ships the wiring itself: a five-event `.codex/hooks.json` for a supervised project, the machine-level `~/.codex/hooks.json`, and a README covering the `hooks = true` flag, the trust step, and why the hook points at the `marketplaces/` git checkout rather than the version-pinned plugin cache, which is replaced on every release and would break the wiring at each bump. Recorded because `claude-sync` covers `~/.claude` and nothing covers `~/.codex`, so this was otherwise rediscovered per machine. The relay is safe to leave installed unwatched: with no listener the hook is a silent no-op returning 0.

**Fixed:**
- The 0.7.0 changelog entry claimed a known gap that this release closes, and briefly carried a bullet for the hook templates that shipped after it. Both corrected here rather than by editing a published entry.

## [denubis-external-agents] 0.7.0

Gives the codex supervision monitor a home in the plugin, with the skill that drives it.

**New:**
- `supervising-codex` ports the practice from the field repo it grew in and generalises it for a plugin that runs in someone else's project. Three roles that never merge: codex drafts, Claude supervises, the human rules. It carries the numbered-prompt loop, the pane-resolution guards, the verification pass, and the supervisor-asserted-context discipline that says everything the supervisor stages is a claim for the doer to doubt.
- `scripts/codex_supervisor.py` is the one tool for the job: it resolves, spawns, sends, tails, reports status, relays Codex lifecycle hooks, and runs the watch loop that emits only `NEEDS APPROVAL`, `QUESTION`, `DONE` and `CRASH`. No verb takes a pane ID, because tmux renumbers windows and a stale coordinate types into another project's session.
- Context hygiene, which no upstream copy had. `/clear` between prompts as the default cadence and `/compact` only when the next prompt follows straight on, both sent as the actual slash command in two `send-keys` calls. A prose brief asking codex to compress itself is a task, so codex reads files to answer it and the meter goes down: observed 2026-07-28 moving 21% to 18% while codex reported "Context compressed as specified" and nothing had been compacted.
- The skill states two requirements on the consuming project and says to stop rather than improvise if either is missing: an untracked `codex-prompts/` as the file-exchange surface, and an ADR register for anything ruled along the way.

**Fixed:**
- `classify_snapshot` returned on a `Ready` pane title before examining the body for approval text. Codex's steady-state title *is* `Ready`, so an approval drawn under it classified as `DONE`, telling the supervisor codex had finished at the moment it was blocked. Reproduced live against a pane that had sat unattended for 57 minutes. The repair cannot simply read the body first, because answered approval text stays in the scrollback; pending is distinguished by whether an assistant bullet appears after the last approval marker.

## [denubis-extending-claude] 1.10.0 / [denubis-research-agents] 1.3.0 / [denubis-basic-agents] 2.1.0 / [denubis-plan-and-execute] 2.39.0

Sonnet 5 becomes the model floor across the suite.

**Changed:**
- Operator ruling 2026-07-25 makes Sonnet the floor rather than merely barring Haiku from judgement work, on the grounds that the hallucination rate below it is unacceptable. It extends the 2026-04-22 position rather than replacing it, so both falsifiers stand, and both are overturned only by Haiku 5 shipping plus a dated operator trial.
- `internet-researcher`, `codebase-investigator`, `combined-researcher` and `remote-code-researcher` move from haiku to sonnet. They were the last agents in the suite still on haiku, so the suite had been contradicting the April position since April. Research is the sharpest case, because judging whether a source is credible is judgement work rather than mechanical retrieval.
- `testing-skills-with-subagents` runs its GREEN phase at the weakest sanctioned tier instead of one tier below production, which collapses once the floor and the default are the same tier. Pressure now comes from harder adversarial scenarios. The lost diagnostic bite is recorded rather than glossed.
- `haiku-general-purpose` stays callable, because removing it would foreclose a decision that is not ripe, but it no longer advertises research or summarisation. Dispatching it needs a positive justification naming a bounded mechanical task.
- `creating-an-agent` defaults a new agent definition to sonnet or opus.
- `exec-session-naming` and `design-clarify` dispatch `sonnet-general-purpose` in place of `haiku-general-purpose`. A 2026-07-26 amendment extends the floor to live dispatch sites with no carve-out for cosmetic work, and `design-clarify` was investigating remote datastores rather than running a bounded mechanical task. Prose in both names the subagent by role rather than by tier, so the next retiering needs no prose sweep.
- The version skips 2.37.0 and 2.38.0, which are claimed by PR #11 and by concurrent uncommitted work respectively.

## [denubis-external-agents] 0.6.0

Review findings on 0.5.0, from a codex peer review and a Fable advisor consulted on the same diff. Both are recorded in PR #11.

**New:**
- `--include` now stops for an explicit decision before transmitting. The manifest enumerates every file each include actually stages, and a non-interactive run aborts unless `--include-confirmed` is passed. Printing the paths afterwards was a receipt, not a control: the files were already in flight, and the usual reader of that receipt is a model composing the command line rather than the operator whose files are being sent.
- `advisor-send.sh` ships with the advisor skill. The spawn script previously told operators to drive the pane with `codex-send.sh`, which this plugin does not ship — it existed only in two unrelated project checkouts, so a marketplace install was handed an invocation that did not exist on the machine.

**Changed:**
- The advisor's documented default is now a dispatched background agent rather than a pane, so consultations return a completion notification instead of finishing silently. The Agent tool has no tool-restriction parameter, so the skill now states plainly that a dispatched advisor *can* write, that its writes are permission-prompted rather than blocked, and that "advises, never implements" is a brief it is asked to honour rather than a property the harness enforces. The pane variant remains for when the restriction must be real.
- `EndConversation` is no longer denied to the pane advisor. An advisor that cannot end its own session is worse than one that can (operator ruling).
- Tool-surface re-verification is now keyed to each consultation rather than to edits of the deny list. The second verification run found `EndConversation` already present in the advisor's schema while the deny list still named it: no local edit had occurred, and the harness had re-injected a deferred tool underneath a claim that was stale at ship time.
- The advisor pane splits the caller's pane via `-t "$TMUX_PANE"`. Without it tmux split whatever window was active, so an advisor dispatched from a background session landed on top of unrelated work.
- Unrecognised options and surplus positionals are fatal. A mistyped `--includ evidence.md` previously became a focus note reading `--includ` and dropped the evidence silently.
- The reviewer's grounding rules now permit citing `./included/`. They asserted that only `./context/` existed, which contradicted the tree includes stage into, leaving a rule-following reviewer unable to cite the evidence it had been given.

**Fixed:**
- `tests/test_fable_cost_gate.py` scans every text file under `plugins/` rather than four named categories, and its detector matches the phrase "Fable advisor". It previously could not catch the breach its own docstring names as the canonical example, and saw neither auxiliary skill files nor plugin scripts. Both shapes were injected and watched fail before the widening. The module now also records the two shapes no lexical scan can reach: semantic paraphrase that names no token, and ambient model inheritance through session-model fan-out.

## [denubis-plan-and-execute] 2.37.0 / [denubis-crash-recovery] 1.2.0

Liveness markers stop recording the user's command line, and correlation moves to the session id.

**Changed:**
- `claude-wrapper.sh` no longer writes `argv=` into the liveness marker. A resumed session's command line carries prompt text, and the marker is a plaintext file on disk that triage reads, so the prompt was being persisted where it did not need to be.
- `crash-recovery` correlates on `session_id` first, which the wrapper already stamps. The `--resume <uuid>` argv parse is demoted to an optional legacy path so markers written by older wrappers still resolve, and the mtime-window fallback is unchanged behind both.
- `liveness.argv` is now optional, and neither `list-live` nor the CLI table displays it.

## [denubis-external-agents] 0.5.0

Adds a human-invocable different-model advisor, and lets a review be given evidence the default staging excludes.

**New:**
- `consulting-a-fable-advisor` spawns an advisor in a tmux pane on a different model, briefed to advise and prevented from implementing by a 37-name `--disallowed-tools` list plus `--disable-slash-commands`. The surviving surface is `Glob`, `Grep`, `Read`, and `ReportFindings`; a write attempt returns `No such tool available: Write. Write exists but is not enabled in this context.` The list was derived from an advisor enumerating its own loaded schema rather than written from memory, and it is re-verified the same way whenever it changes, because a name-based deny list fails open on every rename and addition. Note that `--allowed-tools` pre-approves rather than restricts, and does not hide anything.
- The advisor's brief instructs it to doubt supervisor assertions and make reality prove them. Only material marked as a human ruling is frozen; a supervisor's claim is a thing to falsify, because supervisor searches routinely stop one level short.
- The advisor is human-invocable only, per the Fable cost gate. `tests/test_fable_cost_gate.py` enforces that mechanically: no other skill may reference it, no agent, hook, or command may dispatch it, and no agent may declare a Fable-tier model. Prose guarding a cost gate is a silent failure mode, and the breach would otherwise surface on the bill rather than in review.
- Fable-tier access is intermittent, so an unavailable advisor exits non-zero rather than substituting a fallback. Choosing Opus 4.8 instead is the operator's decision, and the consultation is then labelled as the fallback model.
- `codex-peer-review.sh` takes a repeatable `--include <path>`, force-staged the way the target already is, so a run can be given cited papers, a generated diff, or a named artefact the default surface excludes. Included paths may sit outside the repository and every one is printed, since each is a disclosure decision.

**Changed:**
- The reviewer prompt accepts a directory target: it enumerates the directory's files, reads every reviewable text file, and treats that set as the target. A directory review now opens with a target-set manifest marking each file read or skipped, so silent partial coverage is visible rather than invisible.
- The provenance gate is described as establishing provenance and nothing further. A review that passes it is *provenance-checked*, never *verified*: a quote can be verbatim while the claim built on it is false, its severity inflated, or the finding a false positive against a design the reviewer could not see.

**Fixed:**
- A directory target inside a git repository crashed the runner (`cp` without `-r`).
- A directory target then staged binaries, bypassing the text-only filter every other path honours, silently widening the disclosure surface. Bulk inclusion now honours the filter; an explicitly named single file may still be a binary, because naming it is deliberate.

## [denubis-external-agents] 0.4.0

The peer reviewer no longer pins a model version. It follows whatever codex is set to, so new releases need no edit here.

**Changed:**
- `codex-peer-review.sh` reads the top-level `model` key from `$CODEX_HOME/config.toml` (defaulting to `~/.codex`) and passes it through as `-m`. Parsing stops at the first `[section]` header, so a profile's model is never mistaken for the default. With no key, or no config file, `-m` is omitted and codex picks its own default.
- The run now prints the resolved model on a `model:` line, and the skill's presentation step labels the review with that reported value instead of a fixed model name.
- `--ignore-user-config` is retained. The reviewer stays clear of the operator's MCP servers, hooks, and instructions, and the model is the single setting allowed through that isolation.
- Plugin and marketplace descriptions no longer name a model version.

## [denubis-plan-and-execute] 2.36.4

**Fixed:**
- The workflow statusline now targets `tmux rename-window` at its own `$TMUX_PANE`. Previously, an untargeted rename could name whichever Byobu window was active and then suppress correction through the pane-specific 24-hour cache.

## [denubis-hook-pretooluse-dispatcher] 1.1.3 / [denubis-hook-gh-fork-guard] 1.2.2 / [denubis-plan-and-execute] 2.36.3

Every emitted `hookSpecificOutput` now carries the required `hookEventName`.

**Fixed:**
- Claude Code validates `hookSpecificOutput.hookEventName` on every hook response, not only permission decisions. The dispatcher's `build_output` stamped it only on the decision branch, so context-only annotations (the common case) were rejected with "missing required field hookEventName"; the deny passthrough forwarded sub-hook output verbatim with the same hole. Both now stamp the field. `gh-fork-guard` (deny + advisory) and `code-quality-guard` (deny + warn) stamp it at source as well. Regression tests in all three suites, including dispatcher bats cases for context-only and deny-passthrough output.

## [denubis-hook-pretooluse-dispatcher] 1.1.2

Hook launcher made independent of the caller's working directory.

**Fixed:**
- `hooks.json` launches the dispatcher with `uv run --no-project --no-config`. A malformed `pyproject.toml` in the caller's cwd (e.g. git conflict markers mid-merge) previously wedged `uv` in settings discovery before the hook ran; because this dispatcher gates every `Bash` call, that wedge was self-blocking during a merge. Guarded by `tests/test_hook_launcher_cwd_independence.py`.

## [denubis-plan-and-execute] 2.36.2

Both `uv`-launched hooks made independent of the caller's working directory.

**Fixed:**
- `session-start.py` and `code-quality-guard.py` launch with `uv run --no-project --no-config`, so a malformed `pyproject.toml` in the caller's cwd (e.g. git conflict markers mid-merge) can no longer wedge `uv` in settings discovery before the hook runs. `update-live-marker.py` was already immune (deliberate bare `python3`) and is unchanged.

## [denubis-hook-claudemd-reminder] 1.1.4

Hook launcher made independent of the caller's working directory.

**Fixed:**
- `git-command-reminder.py` launches with `uv run --no-project --no-config`, so a malformed `pyproject.toml` in the caller's cwd (e.g. git conflict markers mid-merge) can no longer wedge `uv` in settings discovery before the hook runs.

## [denubis-hook-branch-bg] 0.2.5

Hook launcher made independent of the caller's working directory.

**Fixed:**
- `branch-bg.py` launches with `uv run --no-project --no-config`, so a malformed `pyproject.toml` in the caller's cwd (e.g. git conflict markers mid-merge) can no longer wedge `uv` in settings discovery before the hook runs.

## [denubis-extending-claude] 1.9.1

Fable-pass review fixes across the skill-authoring triad: scar-tissue removal, announce cadence, and checklist tracking discipline.

**Changed:**
- `epistemic-humility`: announce-and-temper fires once per session when the skill loads, not at every presentation.
- `writing-skills`: checklist preamble mandates TaskCreate with a durable on-disk checklist mirror; intro sub-skill order aligned with the Iron Law workflow; skip-testing counter restored; SKILL.md template frontmatter gains `user-invocable`; consolidation scar scrubbed from the worked example (ISSUE-13).
- `maintaining-project-context`: stale Called-by step pointers corrected.

**Fixed:**
- `testing-skills-with-subagents`: scar-tissue removal — unresolvable design-plan pointer cut, consolidation narration replaced with plain cross-references.

## [denubis-plan-and-execute] 2.36.1

Small release: exec-session-naming becomes user-invocable.

**Changed:**
- `exec-session-naming`: user-invocable, so `/exec-session-naming` can be called directly at session start.

## [denubis-plan-and-execute] 2.36.0

impl-plan-write gains UAT-collation discipline and non-determinism self-audits; small fixes ride along in proleptic-challenger, exec-refactoring-rubric, design-write, exec-uat-gate, and systematic-debugging.

**New:**
- `impl-plan-write`: per-phase non-determinism self-audit (step 6.5), a Finalization existence gate on `uat-requirements.md` with a UAT Requirements Collation audit, mandated What's-automatable / What's-NOT-automatable template lines with worked examples, a mixed-signal SPLIT exception, a disclosed-oracle check, and an angle-bracket placeholder convention for illustrative paths.

**Changed:**
- `impl-plan-write`: Test/UAT phases reordered before Finalization; the collation stamp is an honest attestation of what was audited; UAT write-path reconciled (per-phase append vs collation stamp).
- `proleptic-challenger` agent: counterarguments must name the claim they argue against.
- `exec-refactoring-rubric`: References section citing the sources actually consulted; Popper, Carnap, and Fowler cited at first use.

## [denubis-extending-claude] 1.9.0

Upstream-sync overhaul of the skill-authoring chain: a new epistemic-humility rubric skill, writing-skills rebuilt as an orchestrator, and major reworks of testing-skills-with-subagents and writing-claude-directives.

**New:**
- `epistemic-humility` skill: four-screen rubric (Scope, Observability, Process, Failure-pattern) with paragraph-level source citations and a self-application walk-through. Presenting results, conclusions, or findings now falls in scope: the skill requires an explicit announcement and language tempered to the evidence.
- `writing-claude-directives`: `model-tier-notes.md` behavioural notes for the 2026-06 model tier (Fable 5, Opus 4.8, Sonnet 5, Haiku 4.5), with supersession history in a sibling log file.
- `writing-skills`: obra/superpowers imports pinned at `6fd4507` — `anthropic-best-practices.md` (verbatim), the `render-graphs.js` authoring tool, and an `examples/CLAUDE_MD_TESTING.md` worked example — plus a README covering their dependencies.

**Changed:**
- `writing-skills` rewritten as a thin orchestrator sequencing epistemic-humility (scope check), testing-skills-with-subagents (RED baseline before authoring), and writing-claude-directives (phrasing). Deployment now requires explicit human acceptance, and editing an existing skill re-enters the sequence scoped to the change.
- `testing-skills-with-subagents`: conversation-precedent protocol requiring independently sourced RED baselines, letter-vs-spirit distinction promoted to foundational guidance, hardened RED-baseline gate, AskUserQuestion fallbacks.
- `writing-claude-directives`: restructured for the current model tier, rubric callback into epistemic-humility, plan-workflow vocabulary scrubbed from shipped guidance, supersession narratives moved out of SKILL.md.

## [denubis-hook-shortcut-detection] removed

Retired the plugin. Its `shortcut-detector.py` Stop hook is deleted, the marketplace entry and README references are gone, and the dedicated `tests/test_shortcut_detector.py` is removed.

**Why:** an audit of chat history found 50 genuine firings across Sonnet and Opus sessions and zero true positives. The hook greps the last assistant message for narration connectives (`easier to`, `directly rather than`, `simpler approach`, `for simplicity`), which saturate ordinary explanation. Its two most common triggers were the model choosing the more rigorous path (`directly rather than guess`) and a plain comparative (`easier to diagnose`). A Stop hook reading prose cannot tell a mention of a phrase from its use, nor a change of code approach from a tooling workaround, so precision was zero. It also fired on this very investigation for quoting a trigger phrase.

**Removed:**
- `plugins/denubis-hook-shortcut-detection/` (the Stop hook, `hooks.json`, manifest)
- `tests/test_shortcut_detector.py`
- The `denubis-hook-shortcut-detection` entry in `.claude-plugin/marketplace.json` and its three README references

## [denubis-bibliography] 0.12.0

`resolve.py` near matches now carry a distinct exit code, and SKILL.md directs the caller to use the real key the resolver returns rather than construct one.

**New:**
- Exit code `2` for a citekey query with no exact hit but near matches surfaced (missing suffix / truncation / typo), distinct from `1` (genuinely absent or an error). A caller can branch on "wrong key, here is the right one" and re-run with the real key. Documented in the module docstring (`--help`) and SKILL.md.

**Changed:**
- SKILL.md front-door guidance gains "pass the citekey you have, not one you construct" — BBT's disambiguation suffix cannot be reliably guessed, and a fabricated key is the most common way a present paper is misreported as absent — plus the 0/1/2 exit-code table. The stale "a constructed citekey returns an honest No matches" line is retired: a near key now returns the real paper without rendering.

## [denubis-bibliography] 0.11.0

Citekey resolution is now near-match aware: a query that misses the exact key (a missing BBT disambiguation suffix, a truncation, or a typo) surfaces the real paper instead of reporting "no matches", and never renders on a near match.

**Fixed:**
- A citekey query whose key lacked BBT's trailing disambiguation suffix (`chengGenerativeAIRequirements2026` for the stored `…2026a`) was surfaced by BBT's prefix search but then discarded by the exact-equality filter, so `resolve.py` reported "no matches" — repeatedly misread as "the paper has no PDF". The exact filter no longer silently drops the near hit.

**New:**
- Near-match resolution for citekey queries: `classify_citekey` / `rank_citekey_candidates` grade each BBT hit as exact / variant (a disambiguation sibling) / prefix / fuzzy (difflib similarity, tunable threshold). With no exact hit, the nearest paper(s) are RETURNED with their real citekey, library, and PDF status but NEVER rendered — the caller re-runs with the exact key. Base-variant siblings of an exact match are listed as possible duplicates with their library, so duplicates can be merged in Zotero. Recall is widened for the citekey path (base key + author surname) so a mid-string typo still surfaces the neighbourhood. 17 new unit tests; the shell path verified live against Zotero + BBT.

## [denubis-bibliography] 0.10.0

On-demand project-bib refresh: `resolve.py --bib` triggers a paper's registered BBT auto-export and verifies the citekey lands in a well-formed bib, retiring the hand-rolled `item.export` + diff splice and the wrong-scope library pull.

**New:**
- `resolve.py --bib <abs path> --citekey <key>` makes a resolved paper citeable in a project bib. It forces the registered "Keep updated" export via `POST /api/plus/run-autoexport` (zotero-api-plus >= 0.4.0), then verifies the citekey is present in a WELL-FORMED bib using a real BibLaTeX parse (bibtexparser v2 `failed_blocks`, not a grep a truncated write could fool), with the wait/timeout caller-side. On `no-autoexport` it surfaces the setup gap and lists the registered paths; when the endpoint is absent it directs the user to install/upgrade rather than doing a wrong-scope library pull. Trigger-only by design — success is proven against the written file, never the endpoint response.
- Adds a `bibtexparser>=2.0.0b9` dependency (the v2 `failed_blocks` API; v2 is the only line that detects malformed/truncated blocks). 16 unit tests cover the new pure core (`check_bib`, `classify_autoexport_response`, `bib_arg_error`, `explain_autoexport_failure`); the `--bib` shell flow was verified live against BBT 9.0.31.

**Changed:**
- SKILL.md "Refreshing the on-disk bib" now documents the trigger-plus-verify endpoint; the prior guidance (force a refresh with the library pull-export, or that no force-run exists) is retired as wrong-scope/incorrect. Common-mistakes gains rows naming the hand-rolled `item.export` + diff splice and the wrong-scope library pull, both pointing at `resolve.py --bib`.

## [denubis-external-agents] 0.3.0

The codex-peer-review skill now takes a one-line focus note and tells Claude to lean on the runner's staging instead of hand-building context for the reviewer.

**New:**
- Optional second argument: a one-line focus note (e.g. `"check the RQ2 fixes hold and that RQ1 calibration matches the prereg"`) injected into codex's prompt as a priority hint. It sits after the anti-fabrication grounding rules and never narrows the target's scope or relaxes the verbatim-quote requirement. A specific ask is what makes a run worth it; with none, codex roams the repo and returns a sprawling, low-signal review. The note is echoed in the run banner.

**Changed:**
- The skill instructs Claude to pass a focus note and NOT to assemble a hand-picked `context/` directory or write the reviewer an orientation README — the runner already stages the surrounding repo, so that scaffolding was a `0.1.0`-era workaround for the old single-file staging. Quick-reference and common-mistakes updated to match.

## [denubis-external-agents] 0.2.0

The codex-peer-review skill now runs with repository context and persists reviews in a gitignored `.review/`, replacing the single-file `/tmp` smoke test.

**Changed:**
- The runner stages the target's git repo — minus gitignored files and binaries — as `./context/` and points codex at it, so the review can follow the target's cross-references (cited code, run logs) instead of flagging "I wasn't given that." Context stops at the repo; references outside it (papers, external datasets) are flagged `[unverified]`, not chased. Gitignored files (raw data, secrets) are absent from codex's tree; a target that is itself gitignored is still staged as an explicit override.
- Review output moved from `/tmp` to `./.review/<target>.<timestamp>.REVIEW.md` in the working directory (gitignored, persistent); the script auto-drops a self-ignoring `.gitignore` so output never leaks into the repo under review.
- Honest bound: `-s read-only` does not confine reads, so staging bounds the repo's own files (codex runs in `/tmp`, never told the real repo path) but does not stop codex reading its own `~/.codex`/`~/.ssh` — an external sandbox (bwrap) remains the follow-up.

## [denubis-crash-recovery] 1.1.0

Triage output overhaul after a UAT run found it unreadable and ~9,000 lines long with the crash sections empty.

**New:**
- Lean triage terminal view (default): crash victims, live, ambiguous, and genuine investigation rows render in full; concluded, irrecoverable, and unrecognised-ending sessions collapse to a `## Collapsed` count summary. `triage --all` and `~/llm-resume.md` keep the full all-means-all roster. On a real database this was 9,127 → 120 lines.
- `uncorrelated_markers` table + a supplementary "Uncorrelated crash markers" render section: a dead or previous-boot `.live` marker that cannot be correlated to a session is now surfaced as crash evidence (cwd + time) instead of being silently dropped. `reason` is CHECK-enforced from `MARKER_REASON_VALUES`.
- `triage --all` flag for the full roster.

**Changed:**
- A dead marker with a concluded tail (a turn finished, then the process was killed) classifies as `borderline/liveness_dead_pid_concluded_tail` with a calm "likely nothing to resume" note instead of the generic `unmatched` "Something fucky" route. `unmatched` is now a defensive-only fallback. `CLASSIFIER_VERSION` → 2.

**Fixed:**
- `last_substantive` is single-lined (whitespace and newlines collapsed) so a multi-line markdown assistant message no longer spills across rows and shatters the report; render also single-lines already-stored rows defensively.
- After upgrade, run `crash-recovery init` once to add the `uncorrelated_markers` table; `open_db` asserts its presence.

## [denubis-plan-and-execute] 2.35.3

**Fixed:**
- `claude-wrapper.sh` removes the crash-recovery `.live` marker immediately on a clean exit, before the transcript-archive prompt (which blocks on input). Previously, closing the terminal at that prompt stranded a marker on a cleanly-concluded session, which crash-recovery triage misread as a crash.

## [denubis-hook-shortcut-detection] 2.0.4

Restore portability so the Stop hook runs under the user's interpreter, not only 3.14.

**Fixed:**
- `shortcut-detector.py` is invoked `uv run python …` from the user's working directory, where the resolved interpreter may be older than 3.14, so the 3.14-only syntax it had acquired killed the hook before any logic ran. A stock-3.9 machine hit a def-time `TypeError` on the `str | None` annotation; the parenthesis-less `except` would have raised `SyntaxError` on the same interpreter. Added `from __future__ import annotations` and collapsed the except to `except OSError:` (which already covers `FileNotFoundError` and `PermissionError`). The hook now imports and runs on Python 3.9 through 3.14.

## [denubis-hook-branch-bg] 0.2.4

Restore portability for the SessionStart hook.

**Fixed:**
- `branch-bg.py` carried three parenthesis-less excepts (3.14-only) and runtime-evaluated union annotations, so it failed on pre-3.14 interpreters. Added `from __future__ import annotations` and rewrote the excepts in portable form (collapsed `except OSError:` where a base class subsumes the others, split into single-exception clauses otherwise).

## [denubis-hook-gh-fork-guard] 1.2.1

Restore portability for the fork-guard hook.

**Fixed:**
- `gh-fork-guard.py` declared several `str | None` return annotations that are evaluated at definition time, raising `TypeError` on Python below 3.10. Added `from __future__ import annotations` so the annotations stay strings. The hook runs via the dispatcher's `uv run python3`, which inherits the user's interpreter.

## [denubis-plan-and-execute] 2.35.2

Restore portability for the code-quality PreToolUse hook.

**Fixed:**
- `code-quality-guard.py` used a parenthesis-less `except json.JSONDecodeError, EOFError:` (3.14-only) and a runtime union annotation. Added `from __future__ import annotations` and split the except into single-exception clauses so the hook parses and runs on Python 3.9 through 3.14.

## [denubis-bibliography] 0.9.0

Fan-out reader protocol for investigating many corpus papers at once, and citekey made the primary handle for paper work.

**New:**
- "Fanning out readers over a rendered corpus" section in `using-bibliography`: the orchestrator resolves and renders each paper once, then dispatches one reader subagent per paper given only the rendered `full.md` path. A reader that never receives a PDF cannot reach for `pdftotext`, so the extraction-improvisation failure dissolves by construction rather than being policed.
- A reader-prompt template and a dispatch gate that stats the rendered file on disk before dispatch, never trusting a "rendered" report unverified.

**Changed:**
- "Work by citekey": the citekey is the stable handle for the render dir, citation, note, and dispatch. Resolve by citekey wherever you have one, and use first-author plus a title word only to find the citekey before switching to it.

## [denubis-research-agents] 1.2.0

Academic Research Protocol rewritten to route through the Zotero corpus instead of a parallel `docs/papers/` PDF pile.

**Changed:**
- The protocol is now identify, load, read. Discovery returns locators (DOI preferred, then a stable id, then an unstable locator flagged unverified), papers are loaded into Zotero via `fetch.py` behind confirmation (or the connector for paywalled work with no open-access copy), and reading uses the `using-bibliography` fan-out.
- Removed the "Use the Read tool on the PDF" step and the `docs/papers/{slug}.md` discussion-file model, which forked a second corpus outside Zotero and invited hand-rolled PDF extraction.

**Note:**
- A project still relying on the old `docs/papers/` discussion files is a migration, not covered by this change.

## [denubis-external-agents] 0.1.0

New plugin: dispatch review tasks to external CLI models as a heterogeneous second voice. First skill packages the codex peer-review smoke test that was validated end-to-end.

**New:**
- `codex-peer-review` skill: runs OpenAI's codex (GPT-5.5) as a critical peer reviewer of a file or directory, shaped by a bundled copy of the `critical-peer-review` rubric. The script stages rubric + target into one throwaway working dir and runs `codex exec -s read-only`, so codex sees only that root; it writes the review and prints a provenance smoke-check.
- The SKILL.md makes the provenance gate non-negotiable: every review's quotes are `grep -F`'d against the real target before anything is presented, because codex will confabulate a fluent, correctly-formatted review (faked "Verification" section included) of a document it never read. A review is a claim until its quotes are verified.
- Codex's voice is presented source-tagged and unmerged — a second opinion for the human to weigh, not folded into Claude's own review.

## [denubis-bibliography] 0.8.0

Diacritic-insensitive citation search, so queries match regardless of accents.

**New:**
- `resolve.py` `search_tokens` with ASCII-folding (`_ascii_fold`): both the query and the corpus text are folded to ASCII before matching, so a plain-ASCII query resolves accented author and title tokens (e.g. "Lowenthal" finds "Löwenthal").
- `print_no_match` reports a clear miss instead of a silent empty result.

**Changed:**
- The `using-bibliography` skill scripts are ruff-clean under the repo-wide strict config.

## [denubis-plan-and-execute] 2.35.1

Port the SessionStart hook from bash to Python.

**Changed:**
- `hooks/session-start.py` replaces `session-start.sh`: JSON encoding is delegated to `json.dumps`, correct for every control character rather than the five the bash hand-rolled. The injected SessionStart context is byte-identical to the prior output. Invoked via `uv run python`.

## [denubis-hook-pretooluse-dispatcher] 1.1.1

Port the PreToolUse:Bash dispatcher from bash to Python.

**Changed:**
- `hooks/pretooluse-bash-dispatcher.py` replaces the 255-line jq-driven shell script, gated on the existing 17-test bats contract: identical discovery, priority merge, deny short-circuit, caching, and `--list` diagnostics. Kept portable (runs on interpreters older than 3.14) because it executes via `uv run python` under the user's own project. Invoked via `uv run python`.

**Fixed:**
- `additionalContext` and `systemMessage` from multiple hooks now join with real newlines instead of a literal `\n\n`.

## [denubis-token-estimator] 0.1.0

New plugin: measure AI token/word usage from Claude Code and Codex logs for an AI-use disclosure. Reports two real measures — output tokens and human input words — not proxies.

**New:**
- `/estimate` command and `using-token-estimator` skill: per-project AI usage rolled up from the directory, split into main-thread vs subagent output tokens and human-authored input words, optionally by month or as CSV leaf grain. The `.token-estimator` mapper binds moved/renamed dirs to one canonical project (pure longest-prefix match on the recorded cwd string, so defunct paths still resolve).
- Corrected, reproducible methodology (`docs/DESIGN.md`, nodes 1–5): origin-based dedup for Claude (`message.id`, classify by where work originated, since subagent transcripts replay the parent); additive per-file accounting for Codex (subagents have independent token counters — merging them into the parent erases real work); human-word counting via a named machine-tag allow-list, not "starts with `<`/`#`" (humans paste markup and write headings).
- `scripts/verify.py`: single source of truth for the rules and an audit harness that re-derives every headline number from the live logs, asserting structural invariants (no Codex resumes, subagents additive across all of them, person-grain reconciliation) separately from point-in-time counts that drift as logs grow.
- `~/.token-estimator` config for people-roots; absent it, the tool scopes to the local directory.
- `docs/AUDIT-BRIEF.md` + `docs/findings.schema.json`: adversarial brief to hand the methodology to a different engine for independent falsification (pending).

## [denubis-plan-and-execute] 2.35.0

The academic-writing register as an always-on output style, and the prose skill renamed for discoverability.

**New:**
- `Academic Writing` output style (`output-styles/academic-writing.md`): the prose register (cut scar tissue, em-dash never, rebuild crammed sentences, pinpoint-citation discipline) as a system-prompt-level style applied to every response once selected via `/config`. Sets `keep-coding-instructions: true`, so it shapes prose without dropping Claude Code's built-in coding behaviour. Not force-applied; you opt in per session.

**Changed:**
- Renamed the `writing-academic-prose` skill to `academic-writing`, so it answers to `/academic-writing`. The skill runs the `.notes/` gate and the revision-pass workflow, the output style is the always-on floor, both carry the same register, and the project's `.notes/` overrides both.

## [denubis-bibliography] 0.7.0

One-call paper resolution by any key, plus a pass to genericise project-identifying strings ahead of a public deposit.

**New:**
- `resolve.py`: resolve a paper in Zotero by citekey, author, year, title, date, or DOI in a single live call (BBT JSON-RPC, no stale `.bib` cache). Reports which libraries and collections hold the paper, takes an optional `--library` constraint, and auto-renders the match. Classifies pipeline state (not-in-zotero / no-pdf / pdf-unknown / ready-to-render / rendered) and is truthful — a paper that is in Zotero is never reported as NOT FOUND. Pure functional core unit-tested in `tests/test_bibliography_resolve.py` (26 tests); the httpx/subprocess shell verified live.
- `using-bibliography` SKILL.md documents `resolve.py` as the front door for paper lookup.

**Changed:**
- Genericised project-identifying strings (an old venue label and a collaborator name) in the skill docs and test fixtures, so the publicly-linked plugin and the registered-report deposit carry a neutral worked-example library name. No behaviour change.
- Trimmed the `using-bibliography` skill description back under the 200-character lint.

## [denubis-plan-and-execute] 2.34.0

New `writing-academic-prose` skill: a portable academic-writing discipline that fires the project's own register rules before drafting and keeps prose clean across revision passes.

**New:**
- `writing-academic-prose` skill. Before the first prose edit each session it opens the project's full `.notes/` register and writing rules, the gate that a CLAUDE.md summary alone does not enforce. It then cuts scar tissue (sentences whose subject is the manuscript rather than the study), holds a punctuation hierarchy (em-dash never, semicolon exceptionally rare, colon sparing for lists and definitions), and rebuilds crammed sentences from the idea rather than laundering the mark into a semicolon or lapsing into staccato. Carries pinpoint-citation (APA paraphrase) discipline. Built with RED-GREEN-REFACTOR subagent testing: a baseline agent under deadline pressure skipped the notes and grew scar tissue, while the skill fires the gate and produces genuine rebuilds on Haiku.

## [denubis-bibliography] 0.6.0

Annotate cited passages back onto the source PDF: `annotate.py` highlights a quoted passage in the Zotero PDF with the pandoc citation as its note, via the zotero-api-plus position (rects) mode.

**New:**
- `annotate.py`: given (citekey, page, verbatim quote, note), highlights that passage in the Zotero PDF carrying `[@citekey, p. N]` as the annotation comment. Computes the geometry locally with PyMuPDF (`search_for` + page height) and posts position (rects) mode, so highlights work on any page — the recogniser's text mode caps at 5. Idempotent via a per-quote `⟦ax:<fp>⟧` marker read back through `read-annotations`; falls back to a page-anchored note when the quote has no text layer (scanned/OCR'd pages). `--batch` applies a JSONL of passages; `--dry-run` and `--list` preview and inspect.
- 26 unit tests for the functional core (`tests/test_bibliography_annotate.py`): item-key extraction, quote fingerprint, comment/marker round-trip, payload building, response/structured-error parsing, and multi-library copy selection.

**Changed:**
- `using-bibliography` SKILL.md documents the annotate-back workflow and the zotero-api-plus annotation endpoints (`add-highlight` rects mode, `read-annotations`, `add-note`, `open-pdf`, `delete-annotation`); plugin description notes the new capability.

## [denubis-plan-and-execute] 2.33.0

Removes the four command wrappers that shared a name with their skills. Commands and skills share one namespace, and the Skill tool was resolving the namespaced name to the command wrapper — whose `$1`/`$2` substitution mangled model-passed arguments and whose "now invoke the skill" instruction was circular. The skills are user-invocable and serve the slash-command role directly.

**Changed:**
- `executing-an-implementation-plan` skill gains `argument-hint: "[absolute-plan-dir] [absolute-working-dir]"` frontmatter, preserving the autocomplete hint the command provided.

**Fixed:**
- Removed shadowing command wrappers: `executing-an-implementation-plan`, `maintain-architecture`, `starting-a-design-plan`, `starting-an-implementation-plan`. `/name` invocations now load the skill itself; model Skill-tool invocations no longer dead-end in the wrapper. `flesh-it-out` and `how-to-customize` remain (command-only, no collision).

## [denubis-extending-claude] 1.8.0

Plugin-authoring guidance catches up with commands-merged-into-skills, and repairs byte corruption in creating-a-plugin.

**New:**
- `creating-a-plugin`: "Commands vs Skills: One Artefact Per Name" section — new behaviour belongs in user-invocable skills; never define a command and skill with the same name (documents the observed Skill-tool wrapper-shadowing failure); Component Reference reordered to put Skills first and mark Commands legacy.

**Fixed:**
- `creating-a-plugin`: restored 48 mangled bytes in the two directory-tree code blocks (UTF-8 box-drawing characters had been reduced to their low bytes, e.g. `├──` → `1C 00 00`), which made the file register as binary to grep/file and other text tools.

## [denubis-bibliography] 0.5.0

DOI in, working paper out — `fetch.py` now renders by default — plus a `dots.mocr` GPU escalation tier for scanned books the docling cascade can't handle.

**New:**
- `fetch.py --fetch` renders each fetched paper to per-page markdown by default (delegating to `ingest.py`); `--no-render` opts out.
- Fourth renderer tier: `dots.mocr` (local vLLM VLM-OCR), confirm-gated behind `--allow-mocr`. The cascade starts the server once, OCRs, folds output into the standard `papers/` layout (`renderer.fold_mocr_markdown`, `renderer.mocr_server`), and stops the server on exit. Configured via a `[mocr]` section in `config.toml`; inert if absent.
- `--allow-mocr` plumbed through `render.py`, `ingest.py`, and `fetch.py`.

**Changed:**
- Near-empty-page quality gate tightened from 50% to 30%. The Polanyi *Tacit Dimension* docling+OCR render came out 39% near-empty (~46% of the book lost) and silently passed the old gate. On cascade exhaustion a render is now refused (`NeedsMocr`, `render.py` exit 3) rather than writing lossy pages; re-run with `--allow-mocr` to escalate.
- SKILL.md: explicit directive that PDF→text is always the Python cascade (never `pdftotext`/manual OCR/hand-rolled mocr); `[mocr]` config docs; common-mistakes row.

## [denubis-bibliography] 0.4.0

Adds `fetch.py`, a helper for the missing-paper fetch path. Resolving a human group + collection name into the numeric `groupID` and `collectionKey` that `add-item-by-id` needs used to be improvised as a multi-line `python3 -c "…"` block in bash, which broke on shell quoting. The helper does it in one tested call.

**New:**
- `fetch.py` — resolves `--group`/`--collection` (by name or numeric groupID) to a target and fetches via `add-item-by-id`. Pure functional core (`resolve_target`, `parse_add_item_response`) with 13 unit tests in `tests/test_bibliography_fetch.py`; thin httpx shell.
- Structural confirm-gate: a bare run resolves and previews without writing; `--fetch` is required to write to the library. Unknown/ambiguous names list the available targets and exit non-zero.

**Changed:**
- SKILL.md "Fetching a missing paper" now drives resolution + fetch through `fetch.py` instead of raw curl plus hand-parsed JSON. `create-collection` remains a raw-curl escape hatch for new collections.

## [denubis-hook-rtk-rewrite] REMOVED

Plugin deleted. RTK (Rust Token Killer) ambient command-rewriting corrupted verbatim-read output — `rtk read --max-lines` cherry-picks non-contiguous lines, `rtk grep` reorders and caps results, `rtk find`/`ls` truncate file lists. RTK is no longer used anywhere in this marketplace. Removed the plugin directory, its test (`test_rtk_rewrite.bats`), and its architecture context doc.

## [denubis-00-getting-started] 1.4.2

Removes all RTK handling from `/setup` (supersedes 1.4.1 — there is no RTK plugin left to disable).

**Changed:**
- Step 2 no longer references `denubis-hook-rtk-rewrite` (deleted) in its enablement checks.
- Removed the RTK wiring step (old 5d) and renumbered; the standalone-hook-removal step now exempts the approver (`approver.py`), which is intentionally standalone.

## [denubis-plan-and-execute] 2.32.3

Removes RTK from agent and skill commands so subagents never invoke the deleted `rtk` binary.

**Changed:**
- code-reviewer, task-implementor, task-bug-fixer, systematic-debugging, requesting-code-review, design-write, executing-an-implementation-plan, impl-plan-write: `rtk git …` → `git …`, `uv run rtk ruff …` → `uv run ruff …`.

## [denubis-hook-claudemd-reminder] 1.1.3

**Changed:**
- `git-command-reminder` no longer matches `rtk`-prefixed git commands (RTK purged); regex simplified from `^(rtk\s+)?git\s+…` to `^git\s+…`. Removed the two `rtk`-specific tests.

## [denubis-00-getting-started] 1.4.1

Stops `/setup` from re-enabling RTK ambient command-rewriting. RTK's output
filtering corrupts verbatim-read commands (grep/find/ls/cat/head); it is now
opt-in only, invoked by hand for build/test/lint noise.

**Changed:**
- Step 2 treats `denubis-hook-rtk-rewrite` as intentionally disabled (no longer
  flagged as a missing plugin to enable) and warns if it is `true`.
- Step 5d no longer symlinks `rtk-rewrite.sh` into the dispatcher drop directory;
  it now verifies RTK is *not* wired as an ambient hook. See `~/.claude/RTK.md`.

## [denubis-bibliography] 0.3.0

Documents a confirm-gated path to fetch a missing paper into Zotero via the
`zotero-api-plus` plugin (v0.3.0+), closing the skill's long-standing "does not
fetch papers" gap. Documentation-only in this plugin; the HTTP capability lives
in the separate `zotero-api-plus` Zotero plugin.

**New:**
- SKILL.md "Fetching a missing paper" section: capability probe (`/api/plus`),
  resolve-first dedup guard, target selection via `selected-collection` /
  `libraries` / `create-collection`, and a mandatory HALT-and-confirm before any
  write to the user's library. Per-item `pdf` status handling
  (`present` / `fetched` / `unavailable` / `error`).

**Changed:**
- Removed the now-false "never fetches papers" / "does not fetch papers" claims.
  Fetching is supported behind explicit confirmation when `zotero-api-plus` is
  installed; paywalled papers with no open-access copy remain metadata-only.

**Verified:**
- End-to-end on `10.1007/s13347-024-00760-w` (Conradie & Nagel, CC-BY):
  `create-collection` → `add-item-by-id` (PDF attached) → `ingest.py` rendered
  24 pages via pymupdf4llm.

## [denubis-crash-recovery] 1.0.0

First user-ready release. Identifies and resumes Claude Code sessions that ended abnormally (kernel kill, terminal disconnect, process crash). Combines liveness-file detection (via `denubis-plan-and-execute`'s patched wrapper, ≥2.32.2) with JSONL-tail-only heuristics; deterministic Python rule table classifies every session as `live`, `hard_crash`, `borderline`, `concluded`, or `irrecoverable`; SQLite at `~/.claude/crash-recovery.db` is the source of truth; `~/llm-resume.md` regenerates byte-identically from DB state.

**New:**
- `crash-recovery` CLI with nine subcommands: `init`, `scan`, `render`, `triage`, `regenerate`, `note`, `history`, `prune`, `list-live`.
- `denubis-crash-recovery:triage` skill orchestrates scan + annotation prompt + gated prune.
- SQLite schema: `sessions`, `scan_runs`, `classification_history` with `classifier_version` column for forward-compat re-classification.
- Deterministic rule table; one assertion per row via parametrised tests.
- Atomic resume-file write (`tempfile + os.replace`).

**Requires:**
- `denubis-plan-and-execute ≥ 2.32.2` for the wrapper patch.
- Linux for the `scan` subcommand: it reads `/proc/sys/kernel/random/boot_id` for reboot detection and exits with code 2 on non-Linux platforms. The remaining subcommands (`init`, `render`, `triage`, `note`, `history`, `prune`, `list-live`) are filesystem/DB-only and run anywhere — but `triage` invokes `scan` internally, so the practical effect is "this plugin needs Linux".

**Out of scope (future plans):**
- byobu/tmux-resurrect helpers.
- OOM-hardening for the wrapper itself.
- LLM judgement on borderline cases (deterministic rules only; user annotates manually via `crash-recovery note`).
- Automatic pruning (explicit `prune --dry-run` then `--confirm` only).

## [denubis-plan-and-execute] 2.32.2

Wrapper patch: claude-wrapper.sh now writes a per-PID liveness file at `~/.claude/run/<pid>.live` containing `cwd`, `started`, `argv`, and `boot_id` at startup; on clean exit (status 0) or Ctrl-C (status 130), the file is removed. Any other exit status leaves the file in place. This is the writer side of the denubis-crash-recovery plugin's session triage; install both plugins together for the full crash-recovery workflow.

**Changed:**
- `claude-wrapper.sh`: write `~/.claude/run/$$.live` at startup (atomic via temp+mv), inspect Claude's exit status post-invocation, conditionally remove the liveness file.
- `claude-wrapper.sh`: the post-session transcript-archive prompt ("Press Enter to archive transcript") now fires only on clean Claude exit (status 0). Previously, abnormal exits (SIGKILL 137, SIGSEGV 139, generic non-zero 1, Ctrl-C 130) silently bypassed the prompt because `set -euo pipefail` aborted the wrapper before reaching it; making the cleanup block reachable for non-zero exits required adding `|| EXIT_CODE=$?` to the claude invocation, which also made the transcript-archive block reachable. The exit-0 gate preserves the previous effective behaviour intentionally.

**Compatibility:**
- The wrapper itself runs cross-platform: on non-Linux hosts the `cat /proc/sys/kernel/random/boot_id` falls through to `echo unknown`, so the wrapper writes `boot_id=unknown` rather than crashing.
- `crash-recovery scan` (the reader side, in the `denubis-crash-recovery` plugin) is Linux-only by design — it exits with code 2 and a clear error on non-Linux platforms. The wrapper-side fallback exists so that the `denubis-plan-and-execute` plugin remains usable on macOS / BSD for the rest of its features.
- `crash-recovery scan` also refuses to run when `CRASH_RECOVERY_RUN_DIR` is on a network or union filesystem (NFS, CIFS, sshfs, FUSE-family, etc.) because the atomic-rename semantics liveness-file writes depend on are not guaranteed there. The wrapper itself does NOT make this check — it just writes the file; the reader-side guard catches the unsafe configuration before any scan-time damage.
- `CRASH_RECOVERY_RUN_DIR` env-var overrides the default `~/.claude/run/` path (used in tests, and as the workaround for users whose `$HOME` is network-mounted).

## [denubis-bibliography] 0.2.3

Cascade now catches image-only pages that pymupdf4llm renders as placeholder markers. Discovered when Levenson 1973 (`10.1037/h0035357`, J. Consulting and Clinical Psychology) needed a manual `docling+OCR` one-off under 0.2.2 — the paper's 8 pages were emitted as `**==> picture [W x H] intentionally omitted <==**` markers, which are ~50 chars and slipped just above the empty-page threshold, so the cascade did not escalate.

**Fixed:**
- `renderer.quality_assessment` now strips pymupdf4llm's `==> picture [WxH] intentionally omitted <==` placeholder before measuring page content length. A page whose only content is one or more such markers correctly registers as empty and triggers cascade escalation. Real pages with embedded image markers (e.g. Vanlissa 2024 page 1, with three markers in 1908 chars of real content) still pass — only the marker-only case changes behaviour.

**New:**
- `tests/test_bibliography_renderer.py` — 14 unit tests covering empty pages, marker-only pages, marker+content pages, multi-marker pages, U+FFFD ratio (Stephens 2000 regression), and threshold edges.
- `SKILL.md` — quality-check description updated to explain the marker-stripping; provenance addendum records the discovery.

**Verified:**
- Existing unit tests for `bbt.parse_pdf_paths` and skill descriptions still pass (485 tests in the python suite).
- Heuristic is renderer-specific: docling and EasyOCR don't emit image placeholders for image-only pages (they produce actual empty pages, which the existing heuristic catches).

## [denubis-bibliography] 0.2.2

Defensive Windows hardening ahead of a colleague's first run on Windows. No behaviour change on Linux/macOS.

**Fixed:**
- `parse_pdf_paths` did not handle Windows drive-letter colons. The BBT `file = {label:path:mime}` field on Windows contains `C:\Users\...`, whose colon collided with the previous naive `split(":")`. Symptom on 0.2.0–0.2.1: `ingest.py` reported `no PDF attachment in this item` for items that clearly had a PDF. Parser now handles both unescaped (`C:\...`) and BibLaTeX-escaped (`C\:\...`) forms, plus forward-slash variants (`C:/...`).

**New:**
- `bbt.py` — Better BibTeX parsing helpers, extracted from `ingest.py` so the parser is unit-testable without httpx or a running Zotero. Single public function so far (`parse_pdf_paths`); add to it when BBT formats change.
- `tests/test_bibliography_bbt.py` — 14 unit tests covering Linux/macOS, Windows unescaped, Windows escaped, forward-slash variants, multi-attachment entries (PDF + HTML snapshot), multiple PDFs per item, case variations, and negative cases.
- `SKILL.md` — new **Platform notes** section documenting PowerShell quirks (`curl.exe`/`Invoke-RestMethod` instead of BSD `curl`; `Get-Content` for stdin batch DOIs; drive-letter colon handling), plus two new Common-mistakes rows for the PowerShell `curl` alias and the 0.2.1-on-Windows symptom.

**Untested:**
- Windows is still not exercised end-to-end. Hardening done defensively from the Linux side based on parser mental-simulation. If Windows BBT emits a shape the tests don't cover, add it to `tests/test_bibliography_bbt.py` before re-tuning the parser.

## [denubis-bibliography] 0.2.1

Patch: `ingest.py`'s PEP 723 dependency block was missing `easyocr`, so the docling+OCR fallback path crashed with `ImportError: EasyOCR is not installed` whenever the cascade escalated past docling-no-OCR. Caught when `ingest.py 10.1006/ceps.1994.1033` (Schraw 1994) reached the OCR step in a fresh uv environment.

**Fixed:**
- `ingest.py` — `dependencies = [..., "easyocr"]` added to the PEP 723 block. Verified by re-running the Schraw DOI end-to-end through ingest.py: `1 rendered, 0 cached, 0 failed`.

The 0.2.0 release was only manually verified via `render.py` invoked with `--with easyocr` explicitly; the ingest.py path was not exercised end-to-end before release.

## [denubis-bibliography] 0.2.0

Auto-escalating renderer cascade. PDFs that pymupdf4llm can't handle — Unicode-replacement-character output (Stephens 2000) or no-text-layer scans (Schraw 1994) — now fall back automatically to docling, then docling+OCR, without the user dropping into one-off shell scripts.

**New:**
- `renderer.py` — shared rendering module with quality heuristic (>50% near-empty pages or >0.5% U+FFFD chars triggers escalation) and cascade orchestrator `render_pdf_with_fallback`. `render.py` and `ingest.py` both delegate to it, removing the previously duplicated render block.
- docling+EasyOCR fallback path. `EasyOcrOptions(lang=["en"])` pinned explicitly because recent docling builds default to RapidOCR (downloads ONNX models from `modelscope.cn`; unreliable outside China).
- `meta.json` schema additions: `renderer` (`pymupdf4llm` or `docling`), `ocr` (bool), and `renderer_note` (only when escalation fired; records the chain). Pre-existing fields (`source_pdf`, `page_count`, `sha256_prefix`) are unchanged.
- `SKILL.md` — "auto-escalating cascade" section under Render. New Dependencies subsection documents docling + easyocr install (~1-2 GB first run; cached afterward), Apache-2.0 licence summary, and the EasyOCR pin rationale.
- `SKILL.md` — three new Common-mistakes rows: treating OCR substitutions as faithful transcription, assuming docling defaults to EasyOCR, bypassing the cascade and silently rendering empty pages.

**Changed:**
- `ingest.py` PEP 723 dependency block adds `docling`.
- `render.py` is now a thin CLI entry into `renderer.render_pdf_with_fallback`.
- Render-failure semantics: previously, a PDF with no text layer silently produced 16 empty `.md` files. Now, if every renderer fails the quality check, `render.py` exits non-zero and `ingest.py` logs the paper as a per-paper failure.

**Verified:**
- Schraw 1994 (`schrawAssessingMetacognitiveAwareness1994`) — 1980s Acrobat PDFWriter PDF, no embedded text layer. pymupdf4llm and docling-no-OCR both produced 16/16 empty pages; docling+OCR produced 43 KB of clean text across 16 pages, structurally usable for quote location.
- Regression: Arksey & O'Malley 2005 still renders via pymupdf4llm on the first try (`renderer: pymupdf4llm`, `ocr: false` in `meta.json`); no spurious escalation.

## [denubis-bibliography] 0.1.1

Documentation patch from the BJET-RR 42-paper rendering pass on 2026-05-12. No behaviour changes; closes a workflow gap that was sending the user to the Zotero UI when the on-disk bib looked stale.

**New:**
- `SKILL.md` — "Refreshing the on-disk bib" section. Documents BBT's HTTP pull-export endpoint (`curl http://localhost:23119/better-bibtex/library?/<libraryID>/library.biblatex`) as the on-demand refresh path. Explicit note that BBT JSON-RPC has no `autoexport.run`-style method, verified against the published method list at <https://retorque.re/zotero-better-bibtex/exporting/json-rpc/>. Output is byte-identical to BBT's auto-export — verified against `2026-bbs-jt-em-bjet-AI-metacognitive-1` (libraryID 27, 42 entries, 47 KB).
- `SKILL.md` — four new Common-mistakes rows: bouncing the user to the Zotero UI for a stale auto-export refresh; assuming the first `item.search` hit is the canonical copy when items live in multiple libraries; Wiley chapter DOIs (`10.1002/<book>.chN`) failing `ingest.py` because Crossref returns empty `author` for them; giving up on `blockquote.py` NO MATCH without trying adjusted substrings (Unicode apostrophes, HTML-rendered table cells, paraphrases).
- `SKILL.md` — Provenance addendum noting the 2026-05-12 BJET-RR session and the empirical scope (35 articles + 8 burst chapter PDFs + 7 late adds = 42 papers, 0 render failures).

## [denubis-crash-recovery] 0.1.0

New plugin. Identify and resume Claude Code sessions that ended abnormally; classifies live/crashed/concluded sessions deterministically and renders `~/llm-resume.md`. This release ships the plugin scaffold, SQLite schema, and `crash-recovery init` subcommand. Subsequent phases land the classification rule table, scan/render/note/prune subcommands, the triage skill, and the wrapper patch in `denubis-plan-and-execute`.

**New:**
- `plugins/denubis-crash-recovery/` plugin scaffold (plugin.json, LICENSE, README).
- `crash-recovery` CLI (typer-based) with `init` subcommand creating `~/.claude/crash-recovery.db` (overridable via `CRASH_RECOVERY_DB`).
- SQLite schema for `sessions`, `scan_runs`, `classification_history` tables; WAL journal mode set persistently in init.
## [denubis-bibliography] 0.1.0

New plugin. Renders PDFs from a Zotero corpus to per-page markdown so future Claude sessions can engage with paper content via verified, page-keyed blockquotes. WIP — documents only what has been proven end-to-end.

**New:**
- `using-bibliography` skill: cite-key → BBT lookup → PDF file path → per-page markdown render under `~/zettelkasten/papers/<citekey>/`. Hard preconditions documented (Zotero running, BBT loaded, config + zettelkasten present, `pymupdf4llm` installed).
- `ingest.py`: PEP 723 self-contained CLI. Takes DOIs, resolves first-author surname via Crossref (BBT search does not index DOIs), filters BBT search results by exact DOI, exports BibLaTeX, parses the `file = {…}` field, renders idempotently with SHA-prefix cache. `--force` to re-render. Verified end-to-end on 8 methodology DOIs (Keshav 2007, Scherbakov 2025, Wohlin 2014, Arksey 2005, Levac 2010, Tricco 2018, Naeem 2024, Magesh 2025).
- `render.py` and `blockquote.py`: standalone single-purpose utilities. `blockquote.py` exits non-zero with `NO MATCH` rather than fabricating a quote, per Magesh & Scherbakov span-verification grounding.
- Documented note-creation process: literature-note template (per-project, in git) and permanent-note template (central zettelkasten, in git). Wikilinks for note↔note, pandoc cite syntax for note→source. Two-bib resolution at pandoc render time.
- Bootstrap-in-fresh-project section: skill prompts user with the BBT auto-export setup steps rather than silently creating directories.

**Known gaps (explicit in SKILL.md):**
- No paper fetching — Zotero is the only thing that talks to publishers.
- No auto-build of central `~/zettelkasten/references.bib` (designed only).
- No `note new` command — literature notes are written by hand from the template.
- No post-hoc quote verification across an existing note.
- No SSL bypass for EZProxy (designed: dated stamp file in project dir).

## [denubis-git-commit] 1.2.1

Tune commit-splitting guidance to concern-driven rather than file-count.

**Changed:**
- `commit` skill: replaced file-count splitting table (1-2 = 1 commit, 3-4 = 2 commits, 5+ = 3+ commits) with concern-driven guidance. A 30-file refactor doing one thing is one commit; two unrelated fixes in one file are two commits.

## [denubis-extending-claude] 1.7.2

Shorten skill descriptions to reduce skill-listing budget pressure.

**Changed:**
- 6 skill descriptions tightened to ~110-170 chars: `creating-a-plugin`, `maintaining-a-marketplace`, `maintaining-project-context`, `testing-skills-with-subagents`, `writing-claude-md-files`, `writing-skills`. Triggers preserved; trailing rationale clauses dropped.

## [denubis-plan-and-execute] 2.32.1

Shorten skill descriptions to reduce skill-listing budget pressure; remove scholar name-drops and parenthetical enumerations.

**Changed:**
- 22 skill descriptions tightened. Notable cuts: `using-ast-grep` (378→176), `systematic-debugging` (345→120, drops Toulmin), `critical-peer-review` (310→159), `impl-plan-write` (273→148), `restate-our-assumptions` (258→162, drops Popper/Lakatos/Haraway), `exec-refactoring-rubric` (drops Mantyla/Fowler). Triggers preserved; trailing rationale and technique-name dropping removed since user-side trigger words don't include scholar surnames.

## [denubis-research-agents] 1.1.1

Shorten skill descriptions to reduce skill-listing budget pressure.

**Changed:**
- 3 skill descriptions tightened: `investigating-a-codebase` (309→136), `researching-on-the-internet` (297→138), `using-research-agents` (226→171, fixes parenthetical enumeration).

## [denubis-plan-and-execute] 2.32.0

Bound the code-review fix loop to a single re-review cycle, then HALT for user direction. The previous unbounded "review → fix → re-review until zero issues" loop generated runaway agent ceremony for tiny edits.

**Changed:**
- `requesting-code-review` skill: at most one fix-then-re-review cycle, then HALT. Four user-resolution options on HALT: fix-now (user-authorised), defer to a future phase plan (mark review complete and append issues to the named plan file), accept remaining issues, or halt for discussion.
- `code-reviewer` agent: writes findings to `code-review-findings-{SCOPE}.md` (e.g. `phase-2`, `pre-merge`, `plan-validation`) in the plan directory so per-scope findings coexist rather than clobbering each other. Re-review mode reads `PRIOR_FINDINGS_FILE` and reports each prior issue as Resolved / Partially resolved / Unresolved.
- `code-reviewer` agent: Python tooling MUST be wrapped in `uv run` (e.g. `uv run pytest`, `uv run ruff check`); bare invocations are forbidden.
- `executing-an-implementation-plan` skill: per-phase and pre-merge review sections updated to call the bounded skill with `SCOPE: phase-N` / `SCOPE: pre-merge`. Removed the now-unreachable three-strike rule. Test analysis (5b) gates on terminal outcome rather than strict zero-issues so accept/defer paths still proceed to test coverage.
- `impl-plan-write` skill: plan-validation finalization uses the bounded one-cycle behaviour with `SCOPE: plan-validation`. Step 3 finalization completes on terminal outcome rather than strict zero-issues.

## [denubis-plan-and-execute] 2.31.0

Revise `exec-session-naming` skill: structured slug format with project code, verb-noun slot, issue number, and phase; anti-drift pane targeting so tmux window names no longer get schmeared onto the focused window.

**Changed:**
- Slug format is now `<Person>/<p3>:<verb>-<noun>:#<issue>:P<phase>` (e.g. `Adela/mel:design-ontology:#19:P2`). Components drop when unavailable; `<p3>:<verb>-<noun>` is always present.
- Project code (`p3`) strips leading `<$USER>-` or `<Person>-` prefix before taking the first 3 alphanumeric chars, so `brian-ed3d-plugins` → `ed3`, not `bri`.
- Slot is now `<verb>-<noun>`. For canonical skills (`starting-a-design-plan`, `starting-an-implementation-plan`, `executing-an-implementation-plan`, `systematic-debugging`) the verb is fixed (`design`/`plan`/`exec`/`debug`) and Haiku picks the noun. For non-canonical skills, Haiku picks both verb and noun. Haiku is fed the full conversation up to the skill invocation.
- `tmux rename-window` now uses `-t "$TMUX_PANE"` to pin the rename to the window containing Claude's own pane (anti-drift). Previously the rename targeted whichever window the user was focused on, which caused names to land on the wrong window.
- `$TMUX_PANE` is now re-read at apply time rather than during context gathering, to ensure the lock file key and rename target reflect the current pane.

## [denubis-plan-and-execute] 2.30.1

Complete the M25 skill-rename ripple. Internal refactor; no behaviour change.

**Changed:**
- Frontmatter `name:` fields aligned with prefixed directory names across 20+ worker skills (`coding-tdd`, `coding-verify`, `design-clarify`, `exec-session-naming`, etc.). Directory renames + most cross-references landed in e180b55; the `name:` field inside SKILL.md frontmatter had been missed.
- `family:` taxonomy field added to every worker skill, grouping into `coding-effectively` / `starting-a-design-plan` / `starting-an-implementation-plan` / `executing-an-implementation-plan`.
- Agent / command / doc / test cross-references swept for old skill names (`test-driven-development`, `verification-before-completion`, `asking-clarifying-questions`, `session-naming`).
- Root `CLAUDE.md`: `ed3d-plugins` → `denubis-plugins` identity + `ed3d-basic-agents:` → `denubis-basic-agents:` prefix updates; "HALT When Things Feel Sideways" working-philosophy section added.
- `scripts/m25-rename-skills.sh` committed as the tool that produced the ripple (two-pass placeholder replacement, frontmatter `family:` addition after replacements).

## [denubis-extending-claude] 1.7.1

Internal refactor ripple; no behaviour change.

**Changed:**
- Cross-reference updates inside `creating-a-plugin/SKILL.md` and `testing-skills-with-subagents/SKILL.md` swept for old `denubis-plan-and-execute` skill names affected by M25 (primarily `test-driven-development` → `coding-tdd`).

## [denubis-plan-and-execute] 2.30.0

Rate-limit statusline: persistent per-user cache, active-hours pace display, Theil–Sen forecast.

- Persistent cache at `$XDG_CACHE_HOME/claude-statusline/rate-{window}` with `fcntl.flock` + atomic rename; each line records `timestamp|used_pct|pid|session_id` for provenance.
- Display `5h:22% < 20%` (under pace, green) or `7d:19% ≮ 14%` (not-less-than pace, red). Pace = elapsed fraction of *active hours* (07:00–22:00 local); 7d budget = 7 × 15h = 105h.
- Theil–Sen median-of-pairwise-slopes estimator over last 24h (cap 500 for O(n²) bound); unfiltered so the slope is %/clock-second and composes directly with clock-time.
- DayStop cell: ETA to end-of-today's active-pace target, or `DayStop:go to sleep!` when already past. WeekStop cell: ETA to 100%; suppressed when reset comes first.
- Setup: add `"refreshInterval": 30` to the `statusLine` block in `~/.claude/settings.json` so samples accumulate on a timer rather than only on redraw events.

## [denubis-plan-and-execute] 2.27.0

Replace tautological UAT gates with coherence review for foundational phases.

**New:**
- Coherence-reviewer agent (Opus): checks conformance, traceability, baked-in assumptions, forward fitness, and situated accountability against design intent. Grounded in Perry & Wolf (1992), Gotel & Finkelstein (1994), Ford et al. (2017), Haraway (1988).
- Coherence-review skill: dispatch and presentation for phases without human-judgment UAT
- Deterministic routing rubric in execution skill: Phase Type and Popper UAT entry presence determine path (no LLM judgment)
- Popper three-way sort in implementation planning: automatable predictions → test requirements, human judgment → UAT entries, deferred → future phase with back-reference
- Worked example for Popper sort (Token Service, 4 decisions across 3 buckets)

**Changed:**
- Human-uat-gate scoped to phases where human judgment adds signal that automation cannot
- UAT items reframed as "interact and evaluate" rather than "confirm these / probe boundaries"
- Execution skill example workflow shows both routing paths (infrastructure→coherence, functionality→UAT)
- Coherence reviewer's situated accountability check skips with "Nothing to add" for infrastructure phases without domain-encoding decisions
- No-findings coherence review enumerates what was checked and why nothing stood out

**Fixed:**
- `.denubis/` → `.ed3d/` path inconsistency for implementation-plan-guidance.md in writing-implementation-plans
- Knodel & Popescu (2007) attribution clarified (compliance comparison, not reflexion models); added Murphy, Notkin & Sullivan (2001) reference

## [denubis-extending-claude] 1.7.0

Transcript archiving moved to standalone `transcript-archive` plugin.

**Changed:**
- Removed `/transcript` command and skill — now provided by the separate [`transcript-archive`](https://github.com/Denubis/claude-code-research-transcript-hook) marketplace plugin
- Removed `transcript` and `idw2025` keywords from plugin metadata

## [denubis-plan-and-execute] 2.26.0

Rewrite worktree skill for compatibility with Claude Code's built-in `claude -w` support.

**New:**
- LFS handling: automatic `assume-unchanged` on dirty LFS-tracked files to prevent pre-commit stash failures in worktrees
- `.ed3d/worktree-setup.md`: project-specific worktree setup instructions (database creation, migrations, service config)
- `.worktreeinclude` awareness: suggests creating one when `.env` files exist without it
- Issue-based worktree naming via `gh issue view`
- Worktree skill is now user-invocable (`/using-git-worktrees`)
- `how-to-customize` documents `.ed3d/worktree-setup.md` alongside existing guidance files

**Changed:**
- Worktree skill rewritten to layer on top of `claude -w` rather than reimplementing worktree management
- Two worktree locations documented: `.worktrees/` (mid-session) and `.claude/worktrees/` (claude -w)
- `.gitignore` check uses `git check-ignore` instead of rigid grep pattern
- Setup steps merged to enforce explicit ordering: auto-detect dependencies first, then `.ed3d/worktree-setup.md` instructions
- Removed stale brainstorming Phase 4 cross-reference

## [denubis-plan-and-execute] 2.25.0

Incorporate lessons from Cantrill's "The Peril of Laziness Lost" and Oxide RFD 576 on LLM coding discipline.

**New:**
- `coding-effectively`: "Virtuous Laziness" section — 4-point pre-addition checklist, deletion test, code-as-liability framing
- `refactoring-rubric`: "Accretion (Layercake)" smell in Additional Structural Smells — detects new code added without consolidating what it supersedes
- `code-reviewer` agent: accretion quality check (Important severity), scoped to diff context; Consolidation Opportunities output section
- `requesting-code-review`: bug-fixer constraint requiring targeted edits, not wholesale file regeneration

**Changed:**
- `coding-effectively`: new common mistake ("I'll add a new module for this"), three new red flags for monotonic growth
- `code-reviewer`: new Important-severity entries for superseded code and deletion opportunities

## [denubis-plan-and-execute] 2.24.0

Three-subagent refactoring pipeline replacing the non-functional code-simplifier dispatch.

**New:**
- `refactoring-rubric` skill: Mantyla taxonomy checklist, Fowler smell-to-refactoring mapping, evidence grading, ast-grep structural detection rules
- `smell-assessor` agent (Sonnet, purple): structured smell detection against Mantyla taxonomy using measurement data + LLM reasoning
- `refactoring-executor` agent (Opus, magenta): applies reviewed refactoring prescriptions with ast-grep preference and revert-on-red discipline
- Preparatory refactoring: planner can insert "preparatory-refactor" phases when codebase investigation finds structural impediments
- `Phase Type:` header field for implementation plan phases (infrastructure, functionality, preparatory-refactor)
- Tier 3 deferred smells registry with detection approaches for future codebase-level refactoring

**Changed:**
- `executing-an-implementation-plan` section 3d: replaced code-simplifier dispatch with measurement → smell-assessor → critical-peer-review → refactoring-executor pipeline with gate short-circuits
- `writing-implementation-plans`: extended codebase investigation with structural readiness question for phases modifying existing files
- Turn budget table: removed code-simplifier, added smell-assessor and refactoring-executor (150 turns each)

## Windows compatibility fixes

Cross-cutting patch release for Windows/Git Bash support.

**Fixed:**
- `uv run python3` → `uv run python` in all hook commands (`python3` doesn't exist on Windows)
- Hardcoded `/tmp` path in shortcut-detector.py → `tempfile.gettempdir()` for cross-platform temp dirs
- Restored `.gitattributes` to force LF line endings on `.sh`/`.py` files (prevents broken shebangs on Windows clones)

**Affected plugins:**
- [denubis-plan-and-execute] 2.21.0 → 2.21.1
- [denubis-hook-shortcut-detection] 2.0.2 → 2.0.3
- [denubis-hook-claudemd-reminder] 1.1.1 → 1.1.2
- [denubis-hook-branch-bg] 0.2.2 → 0.2.3

## [denubis-00-getting-started] 1.4.0

Windows/Git Bash setup guide and full plugin catalogue.

**New:**
- `/setup` skill now detects platform (Windows/macOS/Linux) and adjusts steps accordingly
- Windows line-ending check (warns if `core.autocrlf=true` would break hook shebangs)
- uv availability check with Windows-specific PATH guidance
- Windows users are warned about Unix-only plugins and offered to disable them

**Changed:**
- README updated with complete 13-plugin catalogue (was 7), grouped into tiers: Core, Recommended, Infrastructure (Unix-only), Terminal-specific, and Onboarding
- Installation section now offers tiered plugin sets with cross-platform guidance
- Added Prerequisites table, Windows Setup section, and Forking instructions

## [denubis-plan-and-execute] 2.23.0

ADR enrichment of design plan and database architecture templates.

**New:**
- Decision Record section in `writing-design-plans` skill template (DR[N] subsections with Status, Confidence, Reevaluation triggers, Consequences, Alternatives)
- Writer guidance for decision identification with brainstorming mapping and Fowler's superseding rule
- ADR fields (Status, Confidence, Reevaluation triggers, structured Consequences) in `template-database.md` Design Decisions section

## [denubis-plan-and-execute] 2.22.0

Post-session transcript archival via claude-wrapper.

**New:**
- claude-wrapper pre-assigns `--session-id` for fresh interactive sessions
- After session exit, prompts "Press Enter to archive transcript, or Ctrl-C to skip"
- Enter launches a new interactive session running `/transcript <uuid>`
- Resumed sessions get a reminder to run `/transcript` next time

## [denubis-extending-claude] 1.6.0

Transcript skill now supports archiving prior sessions by UUID.

**New:**
- `/transcript <session-uuid>` reads the JSONL transcript directly instead of analysing the current conversation
- Step 0 derives transcript path from CWD and reads the JSONL file
- Archive command passes `--session-id` and `--transcript` for prior sessions
- Command file forwards arguments to the skill
## [denubis-plan-and-execute] 2.21.0

Enhanced critical-peer-review with research-backed methodologies (ACH, GRADE, ABP, pre-mortem) and merged Codex variant improvements for broader artifact scope, mandatory checklists, and pattern-level defect tracking.

**New:**
- `critical-peer-review` agent (Opus, red): dedicated subagent for falsification-first audit — previously only a skill with no agent, causing dispatch failures
- ACH matrix step (Heuer, 1999): evaluates evidence individually against all hypotheses to break narrative coherence bias
- GRADE downgrade criteria (Guyatt et al., 2008): five-factor checklist for evidence quality assessment
- Assumption-Based Planning step (Dewar/RAND, 2002): extracts hidden load-bearing assumptions and flags those lacking evidence
- Pre-mortem step (Klein, 2007): assumes the conclusion is wrong and works backward to surface alternative failure scenarios
- Diagnostic timeout step (Croskerry, 2003): forced metacognitive reflection before finalising findings
- Artifact classification step: reviewer must declare type before reviewing (debugging-analysis, incident-analysis, design-plan, implementation-plan, generated-artifact, technical-reasoning)
- Artifact-specific mandatory checklists for all five artifact types
- Pattern-Level Review Rule: classify defects as local-only or pattern-level, require full sweep for systemic issues
- Per-finding fields: Type, Scope, Evidence grade, Pattern level, Next proof step

**Changed:**
- Skill and agent now in sync with 12-step protocol (was 8 steps)
- Output format expanded with Source Inventory, Hidden Assumptions, ACH Matrix, GRADE factors, and Pre-Mortem sections
- Evidence grading scoped to causal/behavioural claims only; non-causal plan findings no longer forced into the grading model
- Severity table expanded with richer descriptions (impossible step, critical omission, vague verification path, ACH/GRADE findings)
- Citation verification extended with plan-specific checks (referenced files/modules exist, constraints represented accurately)
- Provenance checks now include branch/commit-range verification
- Methodological references section added to both skill and agent
## [denubis-plan-and-execute] 2.20.1

**Fixed:**
- ✗MAIN warning now shows alongside location name instead of replacing it

## [denubis-plan-and-execute] 2.20.0

Statusline v2: upgraded status bar with boss HP context bar, rate limit burn-rate projections, location-first line 1 with MAIN warning, and tmux window rename. New session-naming skill for domain-specific session identification.

**New:**
- Boss HP context bar: 20-char bar with colour per 200k-token segment (green→cyan→yellow→magenta→red for 1M context)
- Rate limit display with burn-rate projection and time-to-exhaustion warnings
- tmux window rename as statusline side-effect with lock file deference
- Session-naming skill: Haiku subagent generates domain-specific session slugs
- Red `✗MAIN` warning when on main/master outside a worktree
- Agent name display (`agt:<name>`) when agent is active

**Changed:**
- Statusline refactored from single script to uv-managed package at `scripts/workflow_statusline/`
- Line 1 redesigned: location-first, model removed from line 1
- Context bar expanded from 10 to 20 characters with segment-aware colouring
- Four skills (design plan, impl plan, execution, debugging) invoke session-naming
- Implementation skills invoke critical-peer-review at completion
- Systematic debugging enforces context clear between hypothesis generation and testing

## [denubis-hook-rtk-rewrite] 1.1.0

Add rewrites for mypy, env, wc, psql, and aws CLI commands.

**New:**
- `mypy` and `uv run mypy` → `rtk mypy` / `uv run rtk mypy`
- `env` → `rtk env` (bare env and env with pipes; skips `env VAR=val cmd` assignments)
- `wc` → `rtk wc`
- `psql` → `rtk psql`
- `aws` → `rtk aws`

## [denubis-plan-and-execute] 2.19.0

Epistemic discipline overhaul for systematic debugging; new critical peer review skill.

**New:**
- `critical-peer-review` skill: falsification-first audit of debugging analyses, postmortems, and incident investigations — checks evidence grades, internal consistency, scope claims, and overclaiming
- Evidence grading framework (demonstrated/plausible/possible/speculative) with boundary requirements: "demonstrated" requires both positive and negative borders tested on production path
- Phase 3d self-audit: dispatches clean subagent for hostile peer review before presenting analysis to human
- Investigation write-to-file requirement: analyses written to file with structured format so peer reviewers can be pointed at the document directly
- Ripple rule and full editing pass requirement when fixing review findings

**Changed:**
- Systematic debugging rewritten from "root cause" framing to "causal chain" framing — "root cause" is a social stopping point, not an objective fact (Dekker, Hollnagel)
- "Root cause confirmed" language replaced with evidence-graded language: never write "confirmed" or "root cause found"
- Third Iron Law added: "No claiming beyond your evidence"
- Bayesian updates now use posterior credibility language, not binary confirmed/falsified
- Toulmin qualifier field now uses evidence grades instead of free-text confidence
- Output template restructured: Causal Analysis with Evidence Grading table, Claim Verification table, Epistemic Boundary section, Peer Review section
- Phase numbering updated: seven phases (1, 2, 3, 3b, 3c, 3d, 4, 5)

## [denubis-git-commit] 1.2.0

Fast test gate and shell injection hardening for /commit.

**New:**
- Pre-commit fast test gate: discovers and runs `(fast)` test suites from `.ed3d/testing-guidance.md` before committing

**Changed:**
- Commit messages written via Write tool to `.commit-msg.tmp`, committed with fixed `git commit -F .commit-msg.tmp` command — no shell involvement in message content, immune to injection, and the Bash command is allowable once for all future commits

## [denubis-plan-and-execute] 2.18.0

Standalone PR and merge skills with defensive test gates.

**New:**
- `make-pr` skill (user-invocable): discovers project test commands from `.ed3d/testing-guidance.md` → CLAUDE.md → `.ed3d/implementation-plan-guidance.md` → fallback pytest; syncs with remote and rebases before testing; blocks on any test failure; pushes and creates PR via `gh`
- `merge-to-main` skill (user-invocable): same test discovery and sync; runs gates pre-merge AND post-merge; reverts merge automatically if post-merge tests fail; cleans up branch and worktree
- `.ed3d/testing-guidance.md` convention for project-specific test suites and gates

**Changed:**
- `finishing-a-development-branch` refactored to delegate Options 1 and 2 to `merge-to-main` and `make-pr` respectively; retains menu/orchestration role

## [denubis-plan-and-execute] 2.17.0

Epistemic discipline improvements and session isolation, inspired by upstream ed3d-plugins.

**New:**
- Systematic debugging: second Iron Law (no changes without written predictions), "Read the Documentation" phase, mandatory Bayesian update with human checkpoint, preexisting bug protocol
- Session isolation: SCRATCHPAD_DIR for parallel planning/execution sessions

**Fixed:**
- Slash command names in handoff instructions (starting-a-design-plan, starting-an-implementation-plan)

## [denubis-extending-claude] 1.5.0

Model-tier testing guidance, anti-flakiness rules, and marketplace skill.

**New:**
- Testing skills with subagents: model-tier guidance (RED at production, GREEN one tier down), "No Blaming the Model" section, no-silent-flaky rule
- Maintaining-a-marketplace skill (adapted from upstream ed3d-plugins)

## [denubis-hook-branch-bg] 0.2.2

Reduce base lightness to 0.12 — still too bright at 0.15.

**Changed:**
- Base lightness 0.15 → 0.12, branch range 0.11–0.19 → 0.08–0.16

## [denubis-hook-branch-bg] 0.2.1

Reduce base lightness from 0.18 to 0.15 — two clicks darker per user feedback.

**Changed:**
- Base lightness 0.18 → 0.15, branch range 0.14–0.22 → 0.11–0.19

## [denubis-git-commit] 1.1.0

Avoid command substitution injection warnings in commit commands.

**Changed:**
- Replace `git commit -m "$(cat <<'EOF'...)"` with `printf > /tmp/commit-msg.txt && git commit -F` approach
- No `$()` or backticks in the commit command, so Claude Code's injection detection doesn't trigger

## [denubis-plan-and-execute] 2.16.0

Remove workflow state machinery from statusline and all skills.

**Changed:**
- Statusline now derives all data from session JSON — no external state files, no Bash permission prompts
- Added session-level code churn (+lines/-lines) to statusline line 1
- Removed workflow breadcrumb (feature/skill/context) from statusline
- Haraway lens now conditional ("only when someone bears invisible cost") instead of mandatory on every decision
- Approval prompts must summarise what's being approved (key deliverables, AC coverage, flags raised)

**Removed:**
- `workflow-state.sh` and `workflow-state-wrapper.sh` (state writer scripts)
- `workflow-statusline.sh` (Bash duplicate of statusline renderer)
- "Workflow Status Line" sections from all 16 skills
- `~/.claude/workflow-state/` directory dependency

## [denubis-hook-branch-bg] 0.2.0

Fix colour differentiation — visible repo identity and worktree distinction.

**Changed:**
- Use `git-common-dir` instead of `--show-toplevel` so all worktrees of the same repo share a colour family
- `main`/`master` sits at the exact base colour (H=base, L=0.18, S=0.60); branches offset from it
- Branch hash offsets hue (±40°), lightness (±0.03), and saturation (±0.10)
- Lightness 0.10 → 0.18 (doubles perceptible colour range while maintaining WCAG AAA contrast)

**Fixed:**
- Worktrees appeared as unrelated colours (different `--show-toplevel` paths → different hues)
- At L=0.10 only ~3 hue groups were perceptible (brown/green/purple); now 12+ distinguishable

## [denubis-hook-branch-bg] 0.1.0

SessionStart hook for visual terminal differentiation via background colour.

**New:**
- Sets terminal background colour via OSC 11 escape sequence on session start
- Repo path controls hue (project identity), branch controls saturation (branch differentiation)
- Fixed 10% lightness for dark terminal backgrounds
- Process tree walk to find controlling TTY device, bypassing Claude Code's sandbox
- Caches nothing — deterministic colour from hash, computed each time

## [denubis-hook-rtk-rewrite] 1.0.0

Initial release as a tracked plugin (previously an unversioned file at `~/.claude/hooks/`).

**New:**
- Convention file for dispatcher auto-discovery (priority 50)
- bats test suite (33 tests)
- README with rewrite rule documentation and maintenance instructions

**Fixed:**
- `uv run pytest/ruff/playwright` no longer strips the `uv run` wrapper (was invoking system tool instead of venv tool)
- `uv pip list/install/...` now rewrites to `rtk uv pip ...` (preserves uv's pip wrapper)

**New patterns:**
- `uv run ty check` / `uvx ty check`
- `bandit` / `uv run bandit` / `uvx bandit`

## [denubis-hook-pretooluse-dispatcher] 1.1.0

**New:**
- Auto-discovery of plugin hooks via `hooks/pretooluse-bash.sh` convention file
- Plugins declare priority with `# dispatcher-priority: N` comment (default 50)
- Cache with hash-based invalidation (marketplace changes, settings changes, drop dir changes)
- `--list` diagnostics flag showing discovered hooks, sources, and cache state
- Environment variable overrides for all paths (testability)

**Changed:**
- Drop directory kept for non-plugin hooks (e.g., rtk-rewrite.sh); plugin hooks no longer need symlinks

## [denubis-hook-gh-fork-guard] 1.2.0

**Changed:**
- Replaced `gh-fork-guard-wrapper.sh` with `pretooluse-bash.sh` convention file for auto-discovery
- No manual symlink required — dispatcher discovers it from the marketplace

## [denubis-plan-and-execute] 2.15.1

**Changed:**
- Phase 3c now includes Quine-Duhem awareness: falsification experiments must interrogate their own auxiliary hypotheses before concluding, and require corroboration via a different method
- Added mandatory human checkpoint when experiment and corroboration disagree
- Added subagent delegation protocol for falsification experiments
- Credit: Ben Recht, ["Devezer's Urn"](https://www.argmin.net/p/devezers-urn) for the Quine-Duhem framing

## [denubis-hook-pretooluse-dispatcher] 1.0.0

Single PreToolUse:Bash dispatcher solving Claude Code's parallel hook execution conflict.

**New:**
- Drop directory `~/.claude/hooks/pretooluse-bash.d/` for numbered hook scripts
- Sequential execution with deterministic merge: deny > updatedInput > additionalContext
- README documenting the drop directory convention and merge rules

## [denubis-plan-and-execute] 2.15.0

**New:**
- Phase 3c (Toulmin Claim Verification) in systematic-debugging skill — every factual claim in a bug analysis must be individually verified via falsification experiments before proceeding to implementation

## [denubis-hook-gh-fork-guard] 1.1.0

**Changed:**
- Removed self-registration as PreToolUse:Bash hook — now called via the pretooluse-bash dispatcher
- Added wrapper shell script for dispatcher integration

## [denubis-00-getting-started] 1.3.0

**Changed:**
- Setup now configures the PreToolUse:Bash dispatcher, drop directory, and symlinks instead of registering standalone hooks

## [denubis-00-getting-started] 1.2.0

**New:**
- RTK (Rust Token Killer) verification step in setup — checks binary, rewrite hook, and settings registration

## [denubis-hook-claudemd-reminder] 1.1.1

**Fixed:**
- Regex now matches rtk-rewritten commands (`rtk git status`, `rtk git log`)
- Use `uv run python3` for reliable Python resolution in hook context

## [denubis-hook-gh-fork-guard] 1.0.1

**Fixed:**
- Use `uv run python3` for reliable Python resolution in hook context

## [denubis-hook-shortcut-detection] 2.0.2

**Fixed:**
- Use `uv run python3` for reliable Python resolution in hook context

## [denubis-plan-and-execute] 2.14.1

**Fixed:**
- Use `uv run python3` for code-quality-guard hook invocation

## [denubis-plan-and-execute] 2.14.0

Architecture documentation maintenance system.

**New:**
- `update-architecture-docs` inner skill for detecting contradictions and proposing architecture doc changes
- `maintain-architecture` wrapper skill and `/maintain-architecture` command for standalone maintenance sessions
- Architecture doc templates (DFD context, DFD process, database, personae, glossary, constraints, state)
- `docs/architecture/` directory convention with hierarchical DFD numbering

**Changed:**
- `writing-design-plans` now invokes `update-architecture-docs` after proleptic challenge
- `dba-reviewer` and `howto-develop-with-postgres` reference `docs/architecture/database.md` instead of `docs/database.md`
- Removed "Before Commit: Database Documentation" section from `writing-design-plans` (superseded by architecture docs step)

## denubis-hook-gh-fork-guard 1.0.0

PreToolUse hook that prevents Claude from interacting with any GitHub repo other than the user's fork.

**New:**
- Hard DENY on `gh` commands with `--repo`/`-R` targeting non-fork repos
- Hard DENY on `gh api` paths referencing non-fork repos
- Hard DENY on `gh repo` subcommands with explicit non-fork targets
- Advisory context injection on repo-interacting commands without explicit `--repo`
- Configurable via `ALLOWED_GH_REPO` environment variable (defaults to `Denubis/denubis-plugins`)

## denubis-plan-and-execute 2.13.0

First-class database documentation as a living project document.

**New:**
- `docs/database.md` convention — universe of discourse, Mermaid ERDs, data flow diagrams, data dictionary with business definitions, design decisions with rationale, denormalisation register
- `writing-design-plans` creates or updates `docs/database.md` when designs involve schema work
- `dba-reviewer` validates `docs/database.md` exists and is current during reviews; gains Edit/Write tools to update it

**Changed:**
- Missing or stale `docs/database.md` is now a HALT condition in DBA review

## denubis-plan-and-execute 2.12.0

Database schema design review and subagent turn budget management.

**New:**
- `dba-reviewer` agent — opus-model schema reviewer that halts for human decisions on normalisation, key selection, constraint completeness, and PostgreSQL anti-patterns
- Parallel DBA review in `requesting-code-review` — fires alongside code-reviewer when database changes are detected; DBA HALTs take priority
- Schema Design section in `howto-develop-with-postgres` — normalisation forms (1NF-BCNF), natural vs surrogate key decision rules, constraint strategy, relationship modelling, PG type anti-patterns
- Null/empty response detection — halts and tells the human when a subagent exhausts its turn budget

**Changed:**
- All subagent invocations now have explicit `max_turns`: task-implementor (45), bug-fixer (30), code-reviewer (25), test-analyst (20), code-simplifier (20), proleptic-challenger (15), project-claude-librarian (15), dba-reviewer (15)
- "Flaky tests" treated as halt condition — the DBA agent investigates root causes rather than accepting "flaky" as an explanation

## denubis-plan-and-execute 2.11.1

Fix code-reviewer subagent returning empty output to parent.

**Fixed:**
- Code-reviewer agent exhausting turns on mandatory skill loading before producing review output
- Missing `max_turns` on code-reviewer Task invocations (now set to 25)

**Changed:**
- Skill loading in code-reviewer is now optional (max 1 turn) — key review criteria are inlined in the prompt
- Added "Output Priority" section: structured review is the primary deliverable, agent must produce it even if investigation is incomplete
- Added `uvx bandit -r .` security scan to Python project verification commands

## denubis-plan-and-execute 2.11.0

GitHub issue lifecycle tracking across the plan-and-execute workflow.

**New:**
- Design plans gain a `**GitHub Issue:**` field linking to a GitHub issue (`#123`, `org/repo#123`, or URL)
- `design-planned` label (yellow) applied when a design plan is committed
- `implementation-planned` label (blue) replaces `design-planned` when an implementation plan is created
- Labels removed when a PR is created or branch is merged
- `workflow-state.sh` gains `--issue` flag to carry the issue reference across skills
- Labels are auto-created on the repo if they don't exist

**Changed:**
- `starting-a-design-plan` Phase 1 asks for GitHub issue reference
- `writing-design-plans` applies label after commit
- `starting-an-implementation-plan` transitions label after branch setup
- `finishing-a-development-branch` removes label on merge/PR (new Step 4b)

## denubis-plan-and-execute 2.10.0

Anti-patterns, worktree enforcement, performance fix, and fence fix.

**New:**
- "I Think This Should Work" anti-pattern in systematic-debugging and executing-an-implementation-plan
- Worktree requirement precondition in executing-an-implementation-plan
- Integration section in executing-an-implementation-plan (required workflow skills)
- cc-search-chats reference in debugging Phase 1 for searching past sessions

**Fixed:**
- Session-start hook: replaced sed/awk pipeline with bash parameter substitution (no subprocess spawns)
- Writing-implementation-plans: 4-backtick fence for infrastructure task template with nested code blocks

## denubis-plan-and-execute 2.9.0

Hard gates and data flow diagrams for the design pipeline.

**New:**
- HARD-GATE in brainstorming: no implementation until design is approved
- Anti-pattern callout: "This Is Too Simple To Need A Design"
- DFD Level 0 (context diagram) and Level 1 (pipeline decomposition) in starting-a-design-plan
- DFD Process 4.0 decomposition in brainstorming skill
- EnterPlanMode interception in using-plan-and-execute: routes through starting-a-design-plan if brainstorming hasn't happened

**Changed:**
- Mermaid diagrams use `<br>` for line breaks (VSCode compatibility)

## denubis-plan-and-execute 2.8.0

Redesigned workflow status line breadcrumbs and added experimental discipline.

**Changed:**
- Status line breadcrumb: `feature ❯ step ❯ human_verb` → `feature ❯ skill_name ❯ context_phrase`
- Smart location: worktree-aware display with `@branch` when it adds information
- `workflow-state.sh`: `--step`/`--human` replaced by `--skill`/`--context`
- Skill colours by category (design=blue, planning=magenta, execution=green, defensive=yellow, gates=cyan)
- All 14 skill files updated with new `--skill`/`--context` transition tables

**New:**
- No cut-and-try discipline in systematic-debugging and executing-an-implementation-plan: state falsifiable predictions before experiments, do the reading first, pause for feedback on contradiction
- Worktree detection in statusline (compares git-common-dir to git-dir)

## denubis-plan-and-execute 2.7.0

Code quality guards as a PreToolUse hook.

**New:**
- `code-quality-guard.py` — PreToolUse hook that checks Write/Edit operations against 6 code quality rules
- Blocking checks: E2E JavaScript injection (use Playwright APIs), `metadata.create_all()` outside Alembic
- Warning checks: Alembic migration edits, debug statements in production code, shortcut/deferral patterns, test weakening (skip/xfail)

## denubis-git-commit 1.0.0

Git commit as a proper skill, so `/commit` actually works.

**New:**
- `commit` skill — analyses changes, drafts messages, splits commits by concern, matches repo style conventions

## denubis-plan-and-execute 2.6.1

**Removed:**
- `commands/commit.md` — alias to `commit-commands:commit`, which is no longer installed

## denubis-plan-and-execute 2.6.0

Workflow status line for multi-tab awareness.

**New:**
- `scripts/workflow-state.sh` — state writer that skills call at workflow transitions, keyed by working directory
- `scripts/workflow-statusline.sh` — ANSI-coloured breadcrumb renderer for Claude Code's status line
- `docs/workflow-status-line.md` — setup documentation
- 14 skill files gain `## Workflow Status Line` sections documenting their transition points

**How it works:**
- Skills write JSON state to `~/.claude/workflow-state/<hash>.json` at each transition
- Status line renders: `feature ❯ phase ❯ step ❯ human action`
- Level 4 (human action) only appears when Claude is waiting; colours escalate with effort: dim white (Approve) → cyan (Review) → yellow (Respond) → bold magenta (Think) → red bg (ENGAGE)
- Guard pattern (`[ -x ~/.claude/bin/workflow-state ] && ...`) makes it opt-in — workflows unchanged without install

## denubis-plan-and-execute 2.5.0

Three-lens design review mode for implementation planning.

**New:**
- `writing-implementation-plans` gains a third review mode: "Review design decisions per phase (three-lens analysis)"
- Applies Popper (falsification → human-testable UAT), Lakatos (only when degenerating or genuinely progressive), and Haraway (perspective, benefit, cost) to each design decision
- Separates WHAT (decisions for human judgement) from HOW (implementation tasks for subagents)
- Lens analysis is ephemeral (conversation only) — phase files remain subagent-ready

**Changed:**
- Lakatos lens fires selectively: omitted for routine choices, present only when there's evidence of degeneration or progression worth flagging
- Requirements checklist and test requirements updated for the new mode

## denubis-hook-shortcut-detection 2.0.1

Data-driven phrase tuning from transcript mining across 708 saved sessions.

**Changed:**
- Removed "instead of" from medium-signal phrases (310 hits, ~99% false positives — overwhelmingly legitimate technical explanations)
- Added "directly rather than" as high-signal phrase (2/3 real hits were genuine process-bypassing)

**Fixed:**
- Synced local plugin.json version with marketplace (was 1.1.0, should have been 2.0.0 from E-STOP rewrite)

## denubis-plan-and-execute 2.4.0

Dependency management skills and rationale documentation.

**New:**
- `controlled-dependency-upgrade` skill — methodical one-at-a-time upgrade cycle with changelog review, falsifiable package audit, and per-package commits using uv
- `restate-our-assumptions` skill — periodic philosophical audit of dependency rationale through Popper (falsification), Lakatos (research programmes), and Haraway (situated knowledge)

**Changed:**
- `writing-design-plans` now documents new dependencies in `docs/dependency-rationale.md` with falsifiable claims before committing designs

## denubis-extending-claude 1.4.0

Librarian gains dependency and test documentation responsibilities.

**Changed:**
- `project-claude-librarian` now updates `docs/dependency-rationale.md` when dependency files change during a branch
- `project-claude-librarian` now maintains `tests/test-pseudocode.md` — human-readable test logic organised by domain, updated when test files change

## denubis-hook-shortcut-detection 2.0.0

E-STOP behavior and reliable loop prevention.

**Changed:**
- Blocks now surface the detected phrase to the user for go/no-go decision instead of asking Claude to justify itself
- Replaced message-counting loop prevention with session-keyed lockfile (one detection per session, no re-trigger loops)
- Added `suppressOutput: true` to hide hook logs from chat window

**Fixed:**
- Loop prevention no longer breaks due to system-injected messages inflating user message counts

## denubis-hook-skill-reinforcement 1.1.1

**Changed:**
- Added `suppressOutput: true` to hide hook logs from chat window

## denubis-hook-claudemd-reminder 1.1.1

**Changed:**
- Added `suppressOutput: true` to hide hook logs from chat window

## denubis-basic-agents 2.0.1

**Changed:**
- Added `suppressOutput: true` to SessionStart hook

## denubis-plan-and-execute 2.3.1

**Changed:**
- Added `suppressOutput: true` to SessionStart hook

## denubis-plan-and-execute 2.3.0

Merged upstream test planning and AC traceability features.

**New:**
- `test-analyst` agent - Analyzes test coverage and suggests test strategies
- Acceptance criteria (AC) traceability in implementation plans
- AC coverage check in final code review
- Scoped AC identifiers for cross-plan uniqueness
- Verbatim task name requirement (prevents paraphrasing that loses context)
- `user-invocable: false` for sub-skills (entry points remain invocable)

**Changed:**
- `writing-design-plans` now includes test planning workflow
- `writing-implementation-plans` adds AC traceability and skill activation during investigation
- `executing-an-implementation-plan` tracks AC coverage
- `proleptic-challenger` generates only genuine objections (no forced categories)

**Philosophy:**
- Dynamic skill activation during investigation (belt-and-suspenders with hooks)
- Tests tied to acceptance criteria at design time
- Verbatim task names preserve context through compaction

**Upstream commits:** fa258cb..bd4341f from ed3dai/ed3d-plugins

## denubis-hook-shortcut-detection 1.1.0

Loop prevention to avoid blocking repeatedly when Claude explains itself.

**Fixed:**
- Hook no longer fires repeatedly when Claude re-explains after being blocked
- After blocking, skips the next assistant message (Claude's explanation)
- Re-arms after user sends a message (user stop)

## denubis-plan-and-execute 2.2.0

Python-focused coding standards for code-reviewer agent.

**New:**
- `coding-effectively` skill - Main orchestrator for coding standards
- `python-idioms` skill - Python 3.14+, t-strings, ty, security, tooling
- `functional-core-imperative-shell` skill - FCIS pattern for testability
- `defense-in-depth` skill - Validation at system boundaries
- `writing-good-tests` skill - pytest patterns, mock strategy
- `property-based-testing` skill - Hypothesis patterns
- `howto-develop-with-postgres` skill - Transactions, ACID, naming
- `docs/coding-effectively-design.md` - Design decisions document

**Changed:**
- `code-reviewer` agent now references Python-specific skills
- Removed dependency on `ed3d-house-style` plugin

## denubis-extending-claude 1.3.0

Added upstream sync skill and rename automation script.

**New:**
- `syncing-with-upstream` skill - Documents process for integrating changes from upstream ed3d-plugins
- `scripts/rename-upstream.sh` - Automates ed3d-* to denubis-* renaming after cherry-picks

## denubis-plan-and-execute 2.1.0

Proleptic reasoning and human UAT gates.

**New:**
- `proleptic-challenger` agent - Generates counterarguments at phase transitions based on Kudina, Ballsun-Stanton & Alfano (2025) proleptic reasoning framework (DOI: 10.1007/s44204-025-00247-1)
- `proleptic-challenge` skill - Documents when and how to invoke the challenger (design finalisation, between phases, during UAT)
- `human-uat-gate` skill - Presents acceptance criteria and waits for explicit human verification after code review
- `/how-to-customize` command - Documents `.ed3d/` guidance files for project-specific customisation

**Changed:**
- `writing-design-plans` now invokes proleptic challenge before committing design
- `executing-an-implementation-plan` now includes proleptic challenge between phases and UAT gate after code review
- `requesting-code-review` now leads to proleptic challenge → UAT gate flow
- `starting-a-design-plan` loads `.ed3d/design-plan-guidance.md` before clarification (if exists)
- `starting-an-implementation-plan` loads `.ed3d/implementation-plan-guidance.md` at start (if exists)
- Code reviewers now receive implementation guidance for project-specific standards (if exists)

**Philosophy:**
- Proleptic reasoning forces deliberate evaluation before phase transitions
- "Drunk tutor" framing: both proposals AND counterarguments may be flawed
- Human UAT ensures implementations meet actual needs, not just automated checks
- Guidance files enable project-specific customisation without modifying plugin code

## [denubis-hook-shortcut-detection] 1.0.0

Initial release of shortcut detection hook.

**New:**
- Stop hook that reads Claude's transcript for shortcut phrases
- Detects high-signal phrases: "let me try a different approach", "simpler approach", "for simplicity", etc.
- Detects medium-signal phrases: "instead of", "easier to", "more efficient", etc.
- Blocks response and requires Claude to explain the problem, what was tried, and ask for explicit approval

## denubis-extending-claude 1.2.0

Added transcript archiving skill with markdown output.

**New:**
- `transcript` skill - Archive conversations with IDW2025 research metadata (Three Ps: Prompt/Process/Provenance)
- `/transcript` command to invoke the skill
- **SUMMARY.md output** - Human-readable markdown summary of archived sessions
- Integrates with `claude-transcript-archive` CLI tool

**Outputs:**
- `SUMMARY.md` - Markdown summary with Three Ps, artifacts, statistics
- `index.html` - Full HTML transcript (via claude-code-transcripts)
- `session.meta.json` - Complete structured metadata
- `raw-transcript.jsonl` - Raw conversation data

## denubis-00-getting-started 1.1.0

Renamed from ed3d-00-getting-started.

**Changed:**
- Renamed plugin from `ed3d-00-getting-started` to `denubis-00-getting-started`
- Updated all references from ed3d-plugins to denubis-plugins
- Updated author and license info

## denubis-hook-skill-reinforcement 1.1.0

Renamed from ed3d-hook-skill-reinforcement.

**Changed:**
- Renamed plugin from `ed3d-hook-skill-reinforcement` to `denubis-hook-skill-reinforcement`
- Removed "EXPERIMENTAL" label (validated by practice)
- Updated author and license info

**Proleptic Review Notes:**
- Claim: Skills should be auto-invoked via hook reminders
- Objection: Adds overhead to every prompt
- Response: Small latency cost vs. quality benefit of using appropriate skills

## denubis-hook-claudemd-reminder 1.1.0

Renamed from ed3d-hook-claudemd-reminder.

**Changed:**
- Renamed plugin from `ed3d-hook-claudemd-reminder` to `denubis-hook-claudemd-reminder`
- Updated reference from `ed3d-extending-claude` to `denubis-extending-claude`
- Updated author and license info

**Proleptic Review Notes:**
- Claim: CLAUDE.md should be maintained before commits
- Objection: Adds friction to commit workflow
- Response: Documentation drift is real; small reminder cost is worth it

## [REMOVED] ed3d-playwright

Removed JavaScript/TypeScript E2E testing plugin. Not relevant to Python/SQL/LaTeX workflow.

**Removed:**
- `playwright-explorer` agent (browser automation via MCP)
- `playwright-patterns` skill (test writing patterns)
- `playwright-debugging` skill (debugging test scripts)

Same reasoning as ed3d-house-style removal: wrong ecosystem.

## denubis-extending-claude 1.1.0

Renamed from ed3d-extending-claude.

**Changed:**
- Renamed plugin from `ed3d-extending-claude` to `denubis-extending-claude`
- Updated all internal references

**Proleptic Review Notes:**
- TDD for skills validated: pressure scenarios verify behavior change
- "One excellent example" principle validated (use Python for Brian's workflow)
- project-claude-librarian useful for maintaining documentation

## denubis-plan-and-execute 2.0.0

Renamed from ed3d-plan-and-execute with significant philosophy changes.

**Changed:**
- Renamed plugin from `ed3d-plan-and-execute` to `denubis-plan-and-execute`
- **task-implementor now uses Opus** (was Haiku) - fewer mistakes, fewer review cycles
- Renamed `task-implementor-fast` to `task-implementor` (no longer optimizing for speed)
- Updated Python references (pytest, ruff instead of npm/eslint)

**New:**
- **Halt-on-non-obvious-failures policy**: If test fails in non-obvious way, STOP immediately and report. No grinding for 30 minutes working around problems.

**Proleptic Review Notes:**
- Kept "block on ALL severities" (quality over velocity)
- Three-phase workflow validated (not for simple tasks, but boundary guidance could be clearer)
- /clear between phases validated (artifacts are committed, can re-read)

## denubis-research-agents 1.1.0

Renamed from ed3d-research-agents.

**Changed:**
- Renamed plugin from `ed3d-research-agents` to `denubis-research-agents`
- Updated author and license info

**Proleptic Review Notes:**
- Design validated: response-only output prevents file pollution while design docs capture findings
- Shallow cloning (`--depth 1`) addresses performance concerns
- Sequential exploration appropriate for iterative investigation (parallelization better for independent checks)

## [REMOVED] ed3d-house-style

Removed TypeScript/React-focused house style plugin. Not relevant to Python/SQL/LaTeX workflow.

**Removed skills:**
- howto-code-in-typescript (and typebox, type-fest sub-resources)
- programming-in-react (and useEffect, react-testing sub-resources)
- coding-effectively (TypeScript-focused)
- All other Ed's opinionated standards

May create denubis-house-style with Python/SQL/LaTeX focus later.

## denubis-basic-agents 2.0.0

Renamed from ed3d-basic-agents and customized for Python/academic workflows.

**New:**
- `python-developer` agent - Sonnet-based agent with Python 3.14 idioms:
  - T-strings for security-sensitive string processing (SQL, HTML, shell)
  - Deferred annotations (no string quotes for forward references)
  - Bracketless exception handling (PEP 758)
  - Finally block discipline (PEP 765)
  - Unified compression module with zstd preference (PEP 784)
  - concurrent.interpreters for CPU-bound parallelism (PEP 734)
- `academic-researcher` agent - Opus-based agent with academic rigor (citations, argument structure, LaTeX conventions) baked in

**Changed:**
- Renamed plugin from `ed3d-basic-agents` to `denubis-basic-agents`
- Updated `using-generic-agents` skill to document domain agents alongside generic agents
- Model characterizations reframed as "heuristics, not absolute truths"
- Added explicit "when to use domain agents" guidance

**Proleptic Review Notes:**
- Addressed objection that "unprompted" agents lack domain guidance by adding domain variants
- Addressed objection that model tier hierarchy is oversimplified by reframing as heuristics
- Kept mandatory skill-checking (latency cost is small vs. quality benefit)

## ed3d-plan-and-execute 1.6.2

Fixes "Re-read skill" task dependency ordering.

**Fixed:**
- "Re-read skill" task must be re-pointed to Finalization task after granular tasks are created (was incorrectly blocked by "Create implementation plan")
- Added "After Planning: Update Dependencies" step to ensure correct task ordering

## ed3d-plan-and-execute 1.6.1

Fixes task tracking to include dependencies and absolute paths.

**Fixed:**
- Tasks now use addBlockedBy to enforce execution order (NA→NB→NC→ND, then next phase)
- Task descriptions include absolute paths for design file and output file, so tasks remain actionable after compaction

## ed3d-plan-and-execute 1.6.0

Adds granular task tracking to implementation plan writing to survive context compaction.

**New in `writing-implementation-plans`:**
- **Granular per-phase tasks:** Instead of one task per phase, now creates sub-tasks for each step:
  - Phase NA: Read [Phase Name] from design plan
  - Phase NB: Dispatch codebase-investigator to verify current state
  - Phase NC: Research external dependencies (if applicable)
  - Phase ND: Write phase file to disk
- **Finalization task:** Explicitly states "fix ALL issues including minor ones" — model cannot rationalize skipping minor issues
- **Plan validation as tracked task:** Must complete with zero issues before handoff

**New in `writing-design-plans`:**
- **Phase markers:** Design plans now require `<!-- START_PHASE_N -->` / `<!-- END_PHASE_N -->` markers around each implementation phase, enabling granular parsing

**New in `starting-an-implementation-plan`:**
- **Orchestration tasks:** Tracks Branch setup, Create implementation plan, Re-read skill, Execution handoff
- **Restore context step:** Re-reads skill before handoff to restore instructions post-compaction
- **Terminology clarification:** Renamed "Phase 1/2/3" to descriptive names (Branch Setup, Planning, Execution Handoff) to avoid confusion with implementation plan phases

**Fixed:**
- Code reviewer step was being forgotten after compaction — now tracked as explicit Finalization task
- Minor issues were being skipped — task text now makes fixing them mandatory

## ed3d-plan-and-execute 1.5.1

Updates task tracking references for compatibility with new Claude Code task system.

**Changed:**
- All references to `TodoWrite` now prefer `TaskCreate`/`TaskUpdate`/`TaskList` (the new task tools in Claude Code)
- Backwards-compatibility notes added for older Claude Code versions that still use `TodoWrite`

## ed3d-extending-claude 1.0.1

Updates task tracking references for compatibility with new Claude Code task system.

**Changed:**
- Tool tables and examples now reference `TaskCreate`/`TaskUpdate` instead of `TodoWrite`
- Backwards-compatibility notes added for older Claude Code versions

## ed3d-house-style 1.0.1

Updates task tracking references for compatibility with new Claude Code task system.

**Changed:**
- Persuasion principles documentation now references `TaskCreate`/`TaskUpdate` instead of `TodoWrite`
- Backwards-compatibility notes added for older Claude Code versions

## ed3d-plan-and-execute 1.5.0

Promotes experimental execution workflow to stable.

**Changed:**
- Execution workflow now uses just-in-time phase loading (reads one phase at a time, not all upfront)
- Code review happens once per phase instead of between every task
- TodoWrite structure: three entries per phase (Read, Execute, Code review) with absolute paths and titles
- Subagents receive phase file path and read it themselves

**Removed:**
- Experimental skill and command (merged into stable)
- Task grouping by subcomponent (plan phases now define grouping via markers)
- Task-level code review (replaced with phase-level review)

## ed3d-plan-and-execute 1.4.3

Removes misleading directive from implementation plan header.

**Fixed:**
- Removed "For Claude: REQUIRED SUB-SKILL" directive from plan header template — was being parsed by task-implementor subagent when it should only be used at the top-level orchestrator

## ed3d-plan-and-execute 1.4.2

Simplifies experimental execution workflow.

**Changed:**
- Experimental skill now reads first 10 lines (not 3) to capture Goal in header
- Subagents (task-implementor, bug-fixer) now read entire phase file instead of extracted sections
- Removed context window extraction logic — simpler approach, let subagents see full phase context

## ed3d-plan-and-execute 1.4.1

Adds experimental execution workflow and task markers. (1.4.0 was a buggy mis-push.)

**New:**
- **Task and subcomponent markers** in implementation plans: `<!-- START_TASK_N -->`, `<!-- END_TASK_N -->`, `<!-- START_SUBCOMPONENT_A (tasks 3-5) -->`, etc.
- **Experimental execution skill** (`executing-an-implementation-plan-experimental`) with just-in-time phase loading, context windows for subagents, and marker-based extraction
- **Experimental command** (`/execute-implementation-plan-experimental`) to invoke the experimental workflow

**Changed:**
- `writing-implementation-plans` now generates markers in all task templates (backwards compatible — old execution skill ignores them)

## ed3d-plan-and-execute 1.3.3

Fixes execution handoff to use absolute paths, preventing wrong-directory issues after /clear.

**Fixed:**
- Execution handoff now captures absolute paths via `git rev-parse --show-toplevel` and verifies plan directory exists before outputting command
- After `/clear`, users land in the original session directory (often repo root, not worktree) — absolute paths ensure execution happens in the correct directory regardless

**Changed:**
- `/execute-implementation-plan` command now accepts two arguments: `[absolute-plan-dir]` and `[absolute-working-dir]`
- Command verifies both paths exist and changes to working directory before engaging skill

## ed3d-plan-and-execute 1.3.2

Fixes execution handoff to pass plan directory instead of single phase file.

**Fixed:**
- Execute-implementation-plan instructions now pass the plan directory (e.g., `@docs/implementation-plans/YYYY-MM-DD-feature/`) instead of a single phase file — prevents agent from only implementing the first phase

## ed3d-plan-and-execute 1.3.1

Improves resolution of Definition of Done in design plans.

**Changed:**
- Definition of Done is now written to the design document immediately after user confirmation (Phase 3), rather than being reconstructed later during documentation (Phase 5)
- Design document file is created in Phase 3 with DoD and placeholders for Summary/Glossary
- writing-design-plans skill now appends body sections and generates only Summary/Glossary

**Fixed:**
- Corrected stale skill name references ("subagent-driven-development", "executing-plans") to "executing-an-implementation-plan"
- Reinforced that Minor issues from code review must be fixed (model was skipping them)
- Changed `/compact` to `/clear` between phases, with warning to copy next command first

## ed3d-plan-and-execute 1.3.0

Adds legibility header to design plans for human reviewers.

**New:**
- **Phase 3: Definition of Done** — New checkpoint after clarification to confirm deliverables before brainstorming
- **Legibility header** — Design plans now include Definition of Done, Summary, and Glossary sections at the top
- **Subagent extraction** — Uses fresh-context subagent to generate legibility header after writing body
- **Glossary transparency** — Subagent reports omitted "obvious" terms so user can request additions

**Changed:**
- Phases renumbered 1-6 (was 1, 2, 2b, 3, 4, 5)
- Task invocations in skills now use XML block format

## ed3d-plan-and-execute 1.2.0

Added external dependency research capabilities to implementation planning.

**Changed:**
- **writing-implementation-plans**: Added tiered external dependency research workflow. Phases involving external libraries now trigger research via `internet-researcher` (for docs/standards) with escalation to `remote-code-researcher` (for source code) when documentation is insufficient.

**New capabilities:**
- Decision framework for when to research external dependencies
- Tiered research approach: docs first, source code when needed
- External dependency findings section in phase output templates
- Updated per-phase workflow to include research step
- New rationalizations to prevent skipping external research

## ed3d-plan-and-execute 1.1.0

Corrects design plan level of detail. These changes were a missed port from the internal plugin marketplace and were intended for 1.0.0. This release represents the plugin "as intended."

**Changed:**
- **writing-design-plans**: Design plans now stay at component/module level, not task level. Contracts/interfaces can be fully specified; implementation code cannot.
- **brainstorming**: Added guidance on level of detail in Phase 3. Validates boundaries, not behavior.
- **writing-implementation-plans**: Strengthened codebase verification as source of truth. Implementation plans generate code fresh from investigation, never copy from design.
- **README**: Added "Philosophy: What Each Phase Produces" section explaining archival vs just-in-time distinction.

## ed3d-research-agents 1.1.0

Added `remote-code-researcher` agent for investigating external codebases by cloning and analyzing their source code.

**New agent:**
- `remote-code-researcher` - Answers questions about external libraries/frameworks by cloning repos to temp directories and investigating the actual source code. Combines web search (to find repos) with codebase investigation (to analyze cloned code).

## All plugins 1.0.0

Initial release of ed3d-plugins collection.
