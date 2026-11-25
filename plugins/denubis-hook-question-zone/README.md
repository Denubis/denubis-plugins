# question-zone

A Claude Code mod (a plugin built from a hooks module) that keeps the model's questions
for the person out of the chat. Each question waits in a queue shown above the prompt,
and the person answers when ready.

Codex uses a separate adapter in the same package: once Codex has shown one of its native
questions, a fresh Terra reader searches in the background for an answer the person
already gave, and an earlier answer whose quote checks out reaches the asking session.

## The problem

The model tends to put its one question at the end of a long message, where it is easy to
miss, and then to keep saying that it is still waiting for an answer.

## What it does

**Asking.** The model asks through the `ask` tool
(`mcp__denubis-hook-question-zone__ask`). Each call has a `context` and a `question`, both
needed and neither empty. The tool's description tells the model what a good entry is:

- it is written for someone who has not read the conversation;
- it uses no file names, ticket or record numbers, agent names, or labels coined in the
  conversation, unless each is explained in plain words;
- it says what the answer will change;
- it asks one question.

Only the main session may ask. A call from a subagent or teammate is refused. Otherwise
the call returns at once, saying the entry is being read for clarity.

**A fresh reader reads each entry for clarity before it joins the queue.** A subagent
that has not seen the conversation, and has no tools, asks whether the entry stands
alone: it looks for an unexplained term, a missing referent, or more than one question.
If the entry stands alone, the reader also says whether it is a go-ahead: a question
asking the person to let the assistant go ahead with something it is about to do, such
as a commit, a push, or running an approved plan. The reader decides that, never the
model that asked; the `ask` tool has no way to claim it. When unsure, the reader treats
the entry as not a go-ahead.

An entry that passes joins the end of the queue as soon as the read ends. Nothing
without a clarity read joins the queue. A read that rejects the entry, or that could
not run, reaches the model as a note from this plugin, a row of the conversation the
person does not see as typed, which starts no turn. The note says what a reader could
not understand, or why the read could not run, with a reason the person can act on.

**Then, for every queued entry but a go-ahead, a search for an earlier answer.** Once
the entry is in the queue, a second subagent searches the project's decision records
(`docs/architecture/decisions/` and `docs/decisions/` in the main checkout) and the chat
logs (`cc-search-chats`) for an answer the person already gave. Only the person's own
words count: a message they typed, or their words quoted in a record, never a
paraphrase. Before searching the chats it runs `cc-search-chats index --status --json`.
If that reports an index made less than five minutes ago (`index_state.age_ms` below
300000), it searches the index as it is. Otherwise it brings the index up to date,
running `cc-search-chats index --json` whenever the status reports changes not yet
indexed. Live sessions keep writing, so without that pause nearly every search would
rebuild the index, which loads the embedding model onto the graphics card. Searching a
recent index this way adds no warning. A missing or non-integer age counts as old.

The search never delays the question: it runs while the question waits. Its end acts
only on an entry still waiting in the queue that has never been taken into the prompt
box:

- If it finds an answer the person already gave, the entry leaves the queue, and a note
  gives the model the person's words and where they are, telling it to use that answer.
  The plugin accepts that reply by its shape (`ANSWERED:` and some text); no code checks
  the quoted words against the record or chat row it names.
- If a lookup failed or its coverage was incomplete, or the search itself could not
  start, finish or give a reply the plugin can read, the entry stays in the queue with a
  visible warning, shown above the prompt while it is first in the queue and in the
  question copied into the answer box. A warning permits asking only; it does not
  authorize the action or prove that no earlier answer exists in unread records.
- If it finds nothing, the entry stays as it is.

Once the person has taken the entry into the prompt box, answered it, or the model has
withdrawn it, the search's end changes nothing and says nothing, to the model or the
person. That holds even if the person clears the box and the entry goes back to the
queue. It is a limit: a search that fails, or covers its sources only in part, after the
entry was taken leaves no warning anywhere, because the text already in the box is not
rewritten. The warning the
[2026-11-10 ruling](../../docs/architecture/decisions/2026-11-10-bbs-history-failure-warns.md)
asks for is given only for an entry still waiting in the queue.

Taking an entry claims it in the queue before its text goes into the box. A search that
ends while the person presses the button has either taken the entry out first, and the
box stays empty, or finds it claimed and keeps its result until the box answers. If the
text goes in, the kept result is dropped and nothing is said. If the box refuses the
text, the claim is undone: the entry is next again, a result kept meanwhile acts on it
then, a search still running acts on it when it ends, and a question taken before it is
taken again.

Both subagents run in the background, because a hook may spend only ten seconds of its
own time and waiting for a subagent counts against that.

The model reads a note at its next request. A note can come after a turn's last request,
or while the session is idle, and then nothing would carry it. So once no turn of the
model's is running and no clarity read or search is running or waiting its turn, the
plugin sends one short prompt. Its turn's first request carries every unread note. The
plugin waits no more than 5 minutes for them. The prompt says only that questions came
back or left the queue, so each note reaches the model once, and a burst of asks costs
one message the person sees; a read or search still running after the 5-minute wait can
add one more when it ends. A search waiting its turn behind another counts as running,
so searches that take questions out of the queue one after another send one prompt when
the last ends, not one each. A note
counts as read once a request of the model's main loop (`turn.step`) starts after it. A
prompt is sent for a note at most once, so a turn that fails before its first request
cannot set off a run of prompts.

The model hears of a read or a search only through a note. In a session in auto mode
each subagent also hands its final report back to the main conversation, which would
start a turn of its own: the bare word `CLEAR` or `NOT_ANSWERED`, or a refusal or an
earlier answer a second time. The plugin drops a report whose sender is one of its two
checkers, as `$.agent.list()` names it. Another agent's report reaches the model as
before.

A question is never refused because too many subagents are running. Claude Code runs only
so many at once (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) and refuses a subagent past that
limit. The plugin knows that refusal by its wording, keeps the question in the list of
those being read, and tries again every 15 seconds until the reader starts. Readers start
one at a time, in the order the questions were asked, so a question asked later never
starts ahead of one that is waiting. Any other refusal of a reader sends the question
back, with a note. Searches run one at a time, in the order their questions joined the
queue, which is the order their clarity reads ended and need not be the order asked. So
between them they hold at most one subagent slot, and a question's read waits on a
search only when every other slot is taken. A search waits for its slot the same way a
reader does, and tries for one only while no clarity read is waiting to start, so it
never takes the slot a question's read is waiting for. A withdrawn question, or one
taken into the prompt box, starts no search that has not started yet; one whose turn
comes while its take is still being put into the box starts, since the box may refuse
it. No read or search
has a time limit, so a search that never ends holds back every later search until the
plugin reloads.

The reader is registered as `denubis-hook-question-zone:checker` and has no tools. The
search is registered as `denubis-hook-question-zone:searcher`; its tools are `Read` and
`Bash`, for reading the records and running `rg`, `git rev-parse` and `cc-search-chats`,
and its commands go through the session's permission rules like any other. Both run on
Sonnet at effort `xhigh`, following the ruling that a Sonnet or Terra cross-checks
questions; Terra is the Codex-side choice and does not apply to this plugin. Both keep the
person's and the project's instruction files, as reviewers do by default. Neither is
offered to the model, so only the plugin starts them.

**The band above the prompt.** With nothing waiting and nothing being read, the band
shows nothing. Otherwise one line says how many questions are waiting and how many are
being checked, so questions still being read never look like an empty box. A question
whose search is still running counts as waiting: it is already in front of the person.
While any question waits, a button follows, `1: Take the next question into the prompt
box`. With the prompt box empty, pressing `1` presses it, as it does for a survey.

**Taking a question.** The button puts the first entry in the queue into the prompt box,
quoted, context first and question second, followed by a blank line where the answer
goes:

```text
> The team is choosing a day next week for a one-hour planning meeting.
>
> Would you prefer Tuesday morning or Thursday morning for the meeting?

```

The box is filled only when it is empty. If it holds anything, the box is left exactly as
it is, a toast asks the person to send or clear what they typed first, and the question
stays first in the queue. The box offers no way to put text ahead of a draft without
rewriting the draft, and a rewrite could lose pasted content, so the plugin does not try.

One question is taken at a time. Taking another, after clearing the box by hand, puts the
one taken before back at the front of the queue, so it is never settled by another
question's text that happens to quote it.

**Answering.** When the person sends a prompt, each question they took is settled:

- If the prompt still contains the question exactly as it was quoted, the question is
  answered and leaves the queue. The model receives the person's message, which already
  carries the question and its context.
- If not, the question goes back to the front of the queue.

The quoted question is what identifies the entry, so typing below or above the quote,
or trimming the context above it, does not matter. Editing inside the quoted question, or
deleting it, sends the question back to the queue. Only a prompt the person sends from
the prompt box counts. A notification or another plugin's prompt that arrives meanwhile
leaves the question in the box, waiting.

**Citing an answer.** For each answered question, the plugin gives the model what a
decision record needs to cite the answer, read from the transcript file, with no model
searching for it:

```text
question-zone: the person's answer to "<question>" is recorded here, ready to cite:
- transcript: <the transcript file's absolute path>
- line: <the line of the record holding the answer>
- record uuid: <that record's uuid>
- timestamp: <that record's timestamp>
- resolver: sed -n '<line>p' <path>
```

The engine reports the transcript's path (`transcript_path`) at the session's start and
with each prompt the person sends. The row that keeps the answer is the one carrying the
quoted question: a `user` record when the person typed at an idle prompt, a
`queued_command` attachment when they sent it while the model worked. Its uuid comes with
the row. The engine writes a row to the file only after the row's hooks have all run, so
the plugin looks for the record afterwards: `grep -n -F` for `"uuid":"<uuid>"`, every
tenth of a second for up to 30 seconds. The line it cites is the one whose record carries
that uuid as its own; the timestamp is that record's. The citation then joins the
conversation as a row the model reads and the person does not see.

That is the earliest the model can have it. The turn's first request is sent before the
record is in the file, so the citation reaches the model in the turn's next request
(after its first tool call), or in the next turn's first. Where the plugin cannot derive
a citation, because the engine has not reported the transcript's path since the plugin
last loaded, or the record is not found in time, the row says so and gives the record's
uuid alone. Nothing is guessed.

**Withdrawing.** The `withdraw` tool (`mcp__denubis-hook-question-zone__withdraw`)
removes a question the model no longer needs. It takes the question's text exactly as
asked, because positions in the queue move as the person takes and answers questions.
It removes a question that is being read, waiting, or already in the prompt box (whose
quoted text stays in the box). A question withdrawn while it is read neither joins the
queue nor comes back when its read ends. One withdrawn while its search runs is not
touched by the search's end, and one withdrawn while its reader or search waits for a free
subagent never starts it. It refuses a text that matches no question, and any call from a
subagent or teammate.

**The model's standing rule.** The system prompt ends with a short section. It says that
every question for the person goes through `ask`, that the model never writes a question
to the person in chat, never says it is waiting, and never mentions, lists or reminds the
person of waiting questions. There is one exception, from the person's ruling of
2026-10-22: "So when I engage after a long absence, then discuss, without referent, the
set of open questions and pose the first one to me." When the person asks where things
stand, or returns after a long absence, the model describes each decision still open and
what its answer will change, in plain words and without referring to earlier messages.
The questions themselves stay in the queue, where the person takes the first one next;
one not yet queued goes through `ask`. The `ask` tool's reply carries the same exception.
For a question that comes back from its read, or leaves the queue because a search found
an earlier answer, the section, the `ask` tool's description and the note itself tell the
model what to do. If a reader could not follow it, it rewrites it and asks again; if the
person already answered it, it uses that answer; either way it says nothing in chat. If
the clarity read could not run, it tells the person once, in plain words, what stopped
that check and what they can do. The question stays held until clarity can be checked.
A failed or incomplete search instead appears as a warning on the queued question,
following the
[2026-11-10 ruling](../../docs/architecture/decisions/2026-11-10-bbs-history-failure-warns.md).
The section also says that questions in the project's
open-questions file (`.notes/project_open-questions.md` in the main checkout) are put to
the person through `ask` in plain words, never in their ticket wording; the plugin never
reads or writes that file. It tells the model to ask only when the answer changes its next
action, naming that decision; to put exactly one question in each entry, never a list,
options or a compound sentence; to ask only for answers that are missing or conflicting;
and to continue work already authorized while a question waits. The section then lists every question not yet answered, those
in the prompt box included, as already in front of the person, and those still being
read, so the model does not ask them again. A question whose search still runs is listed
as in front of the person. The engine composes the system prompt for every request it
sends, so the list stays current. An in-process teammate's copy of the lead's prompt does
not get the section, because only the main session may ask.

The queue lives in the session's state. It survives a reload of the plugin and starts
empty in a new session. A read or search still running when the plugin reloads ends with
the old code. As the plugin loads again, each entry still being read is read afresh, and
joins the queue only if that read passes; each queued entry whose search had not ended,
and that has not been taken since, is searched afresh. Reloads happen when the plugin's
files change or on `/reload-plugins`.

## Not yet verified

- **The two-stage check of 0.3.0 has not been run live.** Its behaviour is established
  only by `claude plugin test`, where a stand-in answers for both subagents. No real
  session has yet had a clarity read queue a question and a search then take it out,
  warn on it, or leave it. The supervisor's survey of 444 questions asked in Claude
  sessions from 2026-11-08 to 2026-11-23, as the question that led to this change
  reported it, found that the clarity read takes about 11 seconds, while the search
  makes the whole check take about four minutes. The survey's table was temporary and is
  not kept, so those figures cannot be re-checked from this repository. The new reader,
  with no tools and a shorter prompt, has not been timed.
- **The reader's empty tool list has not been seen live.** That `tools: []` gives the
  reader no tools, rather than every tool, was read from Claude Code 2.1.327's own code
  (an empty list is not the wildcard), not observed. The reader keeps the person's and
  the project's instruction files, which may ask it to read files it now cannot; whether
  it still answers in the `CLEAR` form has not been tried.
- **The reader's go-ahead judgment has not been tried on real questions.** Nothing shows
  yet how often Sonnet names a go-ahead, or names one wrongly. A go-ahead named wrongly
  skips the search; one missed costs only a background search.
- **The combined check of earlier versions was timed live under `claude -p`.** On
  2026-11-08, in 0.1.0, a `claude -p` session made two asks; each returned in under a
  tenth of a second. The checkers, on `claude-sonnet-5-5`, ran
  `cc-search-chats index --json`, which failed because the graphics card was nearly full.
  The check of a question the person had already answered took 68.7 seconds and came back
  with the decision record's path and lines and the person's words, checked against the
  original chat message. The check of a question never answered took 39.5 seconds and
  came back saying the check could not be made, and naming the program holding the
  graphics card. Versions before 0.2.2 held a question when history refresh failed; from
  0.2.2 a failed or incomplete lookup warns instead. A warning does not claim fresh or
  complete history.
- **The five-minute pause before re-indexing has not been seen live.** The searcher
  follows it only as written instruction, with no code checking its commands. In one
  reading trial on 2026-11-18, a Sonnet reader given that instruction said it would skip
  the refresh for a one-minute-old index and refresh for a six-minute-old or undated
  one; given the instruction before it, it refreshed all three.
- **Some chat files are not indexed.** On 2026-11-08, 29 files were blocked by a record
  type `cc-search-chats` does not yet read; an index run does not clear them, and the
  search does not read them.
- **A question waiting for a free subagent has not been seen live.** The plugin's tests
  stand for the engine's limit with a stand-in that refuses in the engine's words. The
  plugin knows that refusal only by its wording, which reads the same in Claude Code
  2.1.312 and 2.1.318. If a later build words it differently, a question whose reader is
  refused so comes back with a note, as any read that cannot run does, and a search
  refused so leaves a warning. Searches running one at a time and yielding slots to
  waiting reads is shown only by those tests. Whether the person sees anything when the engine refuses a plugin's
  subagent has not been checked.
- **A note's display, and the prompt that follows notes, have not been seen in a terminal.**
  The types say the person does not see the note as typed, and that it is stored as meta.
  They do not say it is never shown, and a meta row in the terminal has not been looked
  at. Under `claude -p` on 2026-11-08 (Claude Code 2.1.318), a probe that appended such a
  row while the session was idle started no turn, and the next turn's request carried the
  row. A row appended mid-turn added no turn either. The prompt that follows unread notes,
  the note that an earlier answer took a question out of the queue, and the model staying
  silent about questions it rewrote or dropped, have not been seen live.
- **A citation has been seen live only under `claude -p`, through a throwaway probe mod.**
  On 2026-11-08, under Claude Code 2.1.318, a probe that ran the same steps found a typed
  prompt's record and a mid-turn prompt's record each 100 ms after its row was kept. Its
  note reached the model, which repeated the line and timestamp, and they matched the
  file. The prompts there came from the SDK, not the prompt box. The plugin itself, with
  a question taken from the box and answered, has not been run live. The doors the plugin
  reads (`prompt` for a typed prompt, `delivery` for one sent mid-turn) were seen there
  alone.
- **Dropping a checker's report has not been seen live.** The plugin finds the report the
  way the agent notice log recorded every hand-back on 2026-11-08: at `prompt.submit`,
  from a `peer`, hidden, opening `<agent-message from="<agent id>">`. Whether the person
  sees the drop's reason as a line has not been checked.
- **A read or search restarted after a reload has not been seen live.** The plugin's
  tests stand for a reload by giving the plugin, as it loads, a stored queue with entries
  being read and a queued entry whose search had not ended.
- **The box was used live in 0.1.0; what 0.1.1 changes in it has not been.** On
  2026-11-08 the person answered "Does the question box work the way you wanted?" through
  the box (session `d280d2b3-8069-40c1-8f99-fcd0694017d7`, transcript line 7350): "yep,
  this works just fine. We have a count, I push a button, I have a very clear question
  that I can answer. This is much better." That use showed the question passing its check
  and joining the queue, the band showing the count, and the button putting the question
  into the prompt box quoted with its context. It also showed the answer, typed below the
  quote and sent while the model was working, arriving as a `queued_command` record with
  the quote intact. It did not show the entry leaving the queue. In 0.1.1, not yet seen
  live: the band's one line with both counts, a question waiting for a subagent slot, the
  citation of an answer, and the dropped checker report (the last three have notes above).
- **A question whose text holds characters the prompt box drops** (characters a terminal
  draws as nothing) would not match its quote when sent, and so would go back to the
  queue each time.
- **The Codex search has found an answer live once, in a throwaway setup.** On
  2026-11-24, under Codex CLI 0.169.0 in embedded mode, with a throwaway Codex home and
  the search on a separate app-server, a model asked a question with
  `request_user_input_async` at 10:54:19Z. The search's context reached it as a developer
  message 36 seconds later, while its turn still ran, and four seconds after that it
  showed the person the earlier answer with its source and invited them to confirm or
  change it; the question stayed in the box. The earlier answer was a planted decision
  record and transcript row, not the person's words, and the worker had brought the chat
  index up to date just before. Earlier runs that day ended in warnings: inside the Codex
  sandbox `cc-search-chats index --json` could not create its systemd scope, which then
  ended the search; and Terra twice ran a command whose output was not a report (a search
  piped into `python3`, and `--help`), which the adapter now ignores. Since 2026-11-25 a
  failed index run no longer ends the search; no live run has yet followed one with a
  search of the index as it stands, so that path is shown only by the tests against a
  stand-in daemon. Delivery after a turn has ended
  was seen only with a probe hook that day, not with this one. Not run: the shared
  background server (0.172.0 on the machine), which the person's sessions use; trusting
  the hook through `/hooks`; several searches at once. The live run predates the review
  fixes of 2026-11-25 (which rows count as the person's words, and a warning beside an
  answer); its planted row still counts under them.
- **How Terra judges go-aheads has not been tried.** No live run asked one, and the
  adapter does not check that a go-ahead verdict ran no search.
- **That the synchronous question tool's `PostToolUse` runs only after the answer is an
  inference** from reading Codex's source for the asynchronous tool, not tested.
- **A supervisor's answer typed into Codex's question box may count as the person's.**
  This repository's `codex_supervisor.py --answer` types into Codex's question widget
  through the terminal, and Codex may record that like the person's own reply, which the
  adapter cites as their words. Untested on Codex 0.169 and later; no real use of
  `--answer` was found.

## Install

At the prompt of a Claude Code terminal session:

```text
/plugin install denubis-hook-question-zone --marketplace Denubis/denubis-plugins
```

With the `denubis-plugins` marketplace already added:

```text
/plugin install denubis-hook-question-zone@denubis-plugins
```

The plugin needs a Claude Code build that loads mods. It was written against the mods API
of Claude Code 2.1.312 and tested with 2.1.318. `denubis-hook-quiet-agents` 0.1.2 and
later points the model to this plugin's `ask` tool.

## Development

### Codex adapter

The Codex manifest selects `hooks/codex-hooks.json`, which registers one background
(`"async": true`) `PostToolUse` hook on native `request_user_input_async` calls. It does
not load the Claude hooks module. Nothing runs before Codex shows a question, and nothing
in the adapter can hold, deny or rewrite one: Codex documents that a background hook
cannot block or rewrite the call that started it, and the adapter only ever returns
`additionalContext` or `systemMessage`. The check before asking was removed at the
person's request on 2026-11-24, after it sent back questions it could not follow without
their conversation; the search that runs afterwards is the one approved earlier that day
([decision record](../../docs/architecture/decisions/2026-11-24-bbs-codex-question-search-runs-after-showing.md)).
The synchronous `request_user_input` gets no search, on the untested inference, from
reading Codex's source for the asynchronous tool, that its `PostToolUse` runs only once
the person has answered. A call with several questions is searched as one. Codex
owns the question queue and answer UI; the adapter adds no prompt band or standing
instruction.

Once a question is shown, the hook starts a fresh ephemeral `gpt-6.1-terra` searcher at
`xhigh`, at the project directory. Normal global/project instruction discovery is
retained; the asking conversation is not supplied. Configured plugins retain their
normal selection, including their skills. Hooks, agent delegation, apps, memories and
the searcher's own question tool are disabled. In one turn the searcher is told first to
decide whether the question is a go-ahead for something the session is about to do,
such as a commit, a push or running an approved plan, and for one to search nothing, and
when unsure to search. The adapter does not enforce this: a go-ahead verdict gives no
output whatever the turn ran. Otherwise it searches the decision records and chats with `cc-search-chats`,
searching an index under five minutes old without bringing it up to date (the person's
ruling of 2026-11-18).

Its result reaches the session at Codex's next safe point: the next model request if
the asking turn is still running, otherwise the person's next message.

- An earlier answer is passed on only once its quoted words are found among words the
  person typed in the cited row of the original transcript. In Claude Code that is a
  prompt or queued prompt marked `origin` kind `human` (from June 2026; earlier prompts
  carry no marker and cannot be cited), less lines quoted with `>` or `▎` and the blocks
  Claude Code inserts for pastes and slash commands; teammate messages carry no marker.
  In Codex it is only the answers in a reply from Codex's question box: Codex records the
  person's typed messages exactly like briefs a Claude supervisor types into the pane
  through tmux, so those cannot be cited. The model then gets
  `additionalContext` saying these are the person's own earlier words, with the quote and
  its `path:line`, and telling it to show them to the person and let them confirm or
  change the answer, not to act on it before they reply, and not to take it as approval
  of what the question asks.
- A failed, incomplete or unreadable lookup, a quote not shown to be words the person typed,
  any permission or input request from the searcher, and a cleanup failure each become a
  short `systemMessage`. Codex 0.169.0 shows it as a count of warnings on the status
  line, read with F2. Partial coverage warns beside a verified answer too. The adapter
  never grants an approval.
- When `cc-search-chats index --json` fails, as it does inside the Codex sandbox, the
  index is searched as it stands and a `systemMessage` notes that chats since it was last
  indexed were not searched: beside a verified answer, or alone when nothing is found
  (the person's ruling of 2026-11-25, in the decision record above).
- Otherwise a search that finds nothing leaves no output.

The adapter reads a command's output as a chat-search report only when the command is a
single `cc-search-chats index`, `search` or `context` call with `--json`, alone or wrapped
in a shell's `-c`. A search counts only after an index status showing nothing new to
index or an index under five minutes old, or after an index run, whether that run
succeeded or failed. Any other history command that fails ends the search with a
warning, and nothing the searcher finds after it is used. The searcher is told both, and
not to rerun a failed index run or ask for approval to.

Requirements: Codex CLI 0.169.0 or later with hooks enabled, `uv`, Python 3.14+,
`websockets==16.0`, and access to the Terra model. The hook connects to the existing
daemon reported by `codex app-server daemon version`; it does not start another one. It
uses existing Codex authentication and permission configuration. No cache or writable
directory is invented.

The search has a 150-second budget and cleanup ten seconds inside a 180-second hook
timeout, 0.2.4's figures for its clarity and history turns together; a timed-out hook's
process group is killed, so both stay inside the timeout. An incomplete search
interrupts its turn; every started searcher is unsubscribed and its connection closed.
Unsubscribing is a request to release the ephemeral thread, not proof that every host
process has stopped. The standard hook launcher reports missing `uv` to stderr and exits
one; interpreter or dependency startup failures likewise remain host launch failures,
and the question stays shown. The hook cannot see questions written directly in chat.

For this repository's configured local marketplace, install with:

```fish
codex plugin add denubis-hook-question-zone@denubis-plugins --json
codex plugin list --marketplace denubis-plugins --available --json
```

Then use `/hooks` in Codex to review and trust Question Zone's new hook. A successful
install alone does not establish trusted execution; verify the hook is enabled and
trusted in the session used for acceptance. Re-review changed hooks after updates.

`QUESTION_ZONE_CODEX_SOCKET` can select an existing app-server socket for a controlled
test. It does not launch a daemon or change permissions. Running the entry point
directly with a `PostToolUse` payload runs the search without showing anything to the
person. The Python integration tests use that boundary and a fake Unix WebSocket
daemon; they establish protocol and output behavior, not model judgment or native
installed-hook execution.

```fish
uv run --frozen pytest -q tests/test_question_zone_codex.py
uv run --frozen ruff check plugins/denubis-hook-question-zone/hooks/question_zone_codex plugins/denubis-hook-question-zone/hooks/codex-question-zone.py tests/test_question_zone_codex.py
uv run --frozen ty check --extra-search-path plugins/denubis-hook-question-zone/hooks plugins/denubis-hook-question-zone/hooks/question_zone_codex plugins/denubis-hook-question-zone/hooks/codex-question-zone.py tests/test_question_zone_codex.py
```

### Claude mod

```bash
claude plugin validate plugins/denubis-hook-question-zone
claude plugin test plugins/denubis-hook-question-zone
```

The top-level `tsconfig.json` extends `.claude-plugin/types/tsconfig.json`, which Claude
Code writes, and keeps out of git, only when it loads this folder as a mod under
development (`claude --plugin-dir`). Elsewhere, type-check with a config kept outside the
plugin folder that includes the `claude-code.d.ts` your build writes for the
plugin-authoring skill, plus this folder's `hooks`, `types` and `tests`.

In the tests a stand-in answers for both the reader and the search, telling them apart
by whether the agent type the plugin registered can run commands. Under the `claude plugin test` kit of
Claude Code 2.1.318, a plugin's `$.agent.spawn` reaches that stand-in as the Agent tool's
input. The plugin reads the started agent's id from the Agent tool's record, not from
the `agentId` that `AgentSpawnResult` documents. Also, the checker's run can end before
the spawn's answer reaches the plugin, and the plugin keeps such an early end for the
check that is waiting on it. A plugin cannot wait for an agent through
`$.tool.call({ tool: 'Agent' })`: the engine refuses it as `$.agent.spawn`'s job.

The tests also stand for the transcript file. They keep its lines in memory and answer
the plugin's `grep -n -F -e <pattern> <file>` over them, because a test has no files or
processes of its own. `$.fs.read` is no use for the real file: it refuses anything over
4 MiB, and a long session's transcript is larger (21.5 MB on 2026-11-08).
