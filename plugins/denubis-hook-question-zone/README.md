# question-zone

A Claude Code mod (a plugin built from a hooks module) that keeps the model's questions
for the person out of the chat. Each question waits in a queue shown above the prompt,
and the person answers when ready.

Codex uses a separate adapter in the same package: a fresh Terra reader checks its
native question calls before Codex presents them. The Claude mod is unchanged.

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
the call returns at once, saying the entry is being checked.

**A fresh reader checks each entry before it joins the queue.** A subagent that has not
seen the conversation makes two checks:

1. Does the entry stand alone? It looks for an unexplained term, a missing referent, or
   more than one question.
2. Has the person already answered it? It searches the project's decision records
   (`docs/architecture/decisions/` and `docs/decisions/` in the main checkout) and the
   chat logs (`cc-search-chats`). Only the person's own words count: a message they typed,
   or their words quoted in a record, never a paraphrase. Before searching the chats it
   runs `cc-search-chats index --status --json`. If that reports an index made less
   than five minutes ago (`index_state.age_ms` below 300000), it searches the index as
   it is. Otherwise it brings the index up to date, running
   `cc-search-chats index --json` whenever the status reports changes not yet indexed.
   Live sessions keep writing, so without that pause nearly every check would rebuild
   the index, which loads the embedding model onto the graphics card. Searching a
   recent index this way adds no history warning. A missing or non-integer age counts
   as old.

The check runs in the background, because a search takes up to a minute or more and a
hook may spend only ten seconds of its own time; waiting for a subagent counts against
that. An entry that passes clarity joins the end of the queue when its check ends. Failed
history lookup or incomplete coverage adds a visible warning above the prompt and in
the question copied into the answer box. A clarity rejection or verified prior answer
still sends the question back. Nothing without a clarity check joins the queue. The checker's reply reaches the model as a
note from this plugin, a row of the conversation the person does not see as typed, which
starts no turn. The reply may say what a reader could not understand, or give the
person's existing answer with where and in what words. Or it may say why the clarity checker could not run, with a reason the person can act on.
History warnings permit asking only; they do not authorize the action or prove that no
earlier answer exists in unread records.

The model reads a note at its next request. A note can come after a turn's last request,
or while the session is idle, and then nothing would carry it. So once no turn of the
model's is running and no check is running, the plugin sends one short prompt. Its
turn's first request carries every unread note. The plugin waits no more than 5 minutes
for running checks. The prompt says only that questions came back, so each reply reaches
the model once, and a burst of asks costs one message the person sees; a check still
running after the 5-minute wait can add one more when it ends. A note
counts as read once a request of the model's main loop (`turn.step`) starts after it. A
prompt is sent for a note at most once, so a turn that fails before its first request
cannot set off a run of prompts.

The model hears of a check only through that note. In a session in auto mode each
subagent also hands its final report back to the main conversation, which would start a
turn of its own: the bare word `CLEAR`, or the refusal a second time. The plugin drops a
report whose sender is one of its checkers, as `$.agent.list()` names it. Another agent's
report reaches the model as before.

A question is never refused because too many subagents are running. Claude Code runs only
so many at once (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) and refuses a checker past that
limit. The plugin knows that refusal by its wording, keeps the question in the list of
those being checked, and tries again every 15 seconds until a checker starts. Checkers
start one at a time, in the order the questions were asked, so a question asked later
never starts ahead of one that is waiting. Any other refusal still sends the question
back, with a note.

The checker is registered as `denubis-hook-question-zone:checker`. It runs on Sonnet at
effort `xhigh`, following the ruling that a Sonnet or Terra cross-checks questions; Terra
is the Codex-side choice and does not apply to this plugin. Its tools are `Read` and
`Bash`, for reading the records and running `rg`, `git rev-parse` and `cc-search-chats`.
Its commands go through the session's permission rules like any other. It keeps the
person's and the project's instruction files, as reviewers do by default. It is never
offered to the model, so only the plugin starts it.

**The band above the prompt.** With nothing waiting and nothing being checked, the band
shows nothing. Otherwise one line says how many questions are waiting and how many are
being checked, so questions still under check never look like an empty box. While any
question waits, a button follows, `1: Take the next question into the prompt box`. With
the prompt box empty, pressing `1` presses it, as it does for a survey.

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
It removes a question that is being checked, waiting, or already in the prompt box (whose
quoted text stays in the box). A question withdrawn while it is checked neither joins the
queue nor comes back when its check ends. One withdrawn while it waits for a free
subagent never starts a checker. It refuses a text that matches no question, and any call from a
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
For a question that comes back, the section, the `ask` tool's description and the note
itself tell the model what to do. If a reader could not follow it, it rewrites it and
asks again; if the person already answered it, it uses that answer; either way it says
nothing in chat. If the clarity checker could not run, it tells the person once, in plain
words, what stopped that check and what they can do. The question stays held until
clarity can be checked. History failures and gaps instead appear as warnings on the
queued question, following the
[2026-11-10 ruling](../../docs/architecture/decisions/2026-11-10-bbs-history-failure-warns.md).
The section also says that questions in the project's
open-questions file (`.notes/project_open-questions.md` in the main checkout) are put to
the person through `ask` in plain words, never in their ticket wording; the plugin never
reads or writes that file. It tells the model to ask only when the answer changes its next
action, naming that decision; to put exactly one question in each entry, never a list,
options or a compound sentence; to ask only for answers that are missing or conflicting;
and to continue work already authorized while a question waits. The section then lists every question not yet answered, those
in the prompt box included, as already in front of the person, and those still being
checked, so the model does not ask them again. The engine composes the system prompt for every request it
sends, so the list stays current. An in-process teammate's copy of the lead's prompt does
not get the section, because only the main session may ask.

The queue lives in the session's state. It survives a reload of the plugin and starts
empty in a new session. A check still running when the plugin reloads ends with the old
code. As the plugin loads again, each entry still being checked is checked afresh, and
joins the queue only if that check passes. Reloads happen when the plugin's files change
or on `/reload-plugins`.

## Not yet verified

- **The background check was first timed live under `claude -p`.** Later the same day it
  ran many times in the person's own session, in 0.1.0. On 2026-11-08 a `claude -p`
  session made two asks; each returned in under a tenth of a second. The checkers, on
  `claude-sonnet-5-5`, ran `cc-search-chats index --json`, which failed because the
  graphics card was nearly full. The check of a question the person had already answered
  took 68.7 seconds and came back with the decision record's path and lines and the
  person's words, checked against the original chat message. The check of a question
  never answered took 39.5 seconds and came back saying the check could not be made, and
  naming the program holding the graphics card. A clear entry joining the queue was seen
  later that day, in the person's own use of the box (below).
- **Earlier versions held questions when history refresh failed.** The 0.2.2
  policy permits otherwise-clear questions with a warning when the graphics card
  is busy or history cannot be refreshed. A warning does not claim fresh or
  complete history.

- **The five-minute pause before re-indexing has not been seen live.** The Codex
  adapter's tests show it accepting a search of a recent index without a refresh or a
  warning, and still warning for an older or undated one with changes not yet indexed
  that was not refreshed. The
  Claude checker follows the pause only as written instruction, with no code checking
  its commands. In one reading trial on 2026-11-18, a Sonnet reader given the new
  instruction said it would skip the refresh for a one-minute-old index and refresh
  for a six-minute-old or undated one; given the old instruction, it refreshed all
  three. Terra's reading of the Codex instruction has not been tried.
- **Some chat files are not indexed.** On 2026-11-08, 29 files were blocked by a record
  type `cc-search-chats` does not yet read; an index run does not clear them, and the
  checker does not search them.
- **A question waiting for a free subagent has not been seen live.** The plugin's tests
  stand for the engine's limit with a stand-in that refuses in the engine's words. The
  plugin knows that refusal only by its wording, which reads the same in Claude Code
  2.1.312 and 2.1.318. If a later build words it differently, the question comes back with
  a note, as any check that cannot run does. Whether the person sees anything when the
  engine refuses a plugin's checker has not been checked.
- **A note's display, and the prompt that follows notes, have not been seen in a terminal.**
  The types say the person does not see the note as typed, and that it is stored as meta.
  They do not say it is never shown, and a meta row in the terminal has not been looked
  at. Under `claude -p` on 2026-11-08 (Claude Code 2.1.318), a probe that appended such a
  row while the session was idle started no turn, and the next turn's request carried the
  row. A row appended mid-turn added no turn either. The prompt that follows unread notes,
  and the model staying silent about questions it rewrote or dropped, have not been seen
  live.
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
- **A check restarted after a reload has not been seen live.** The plugin's tests stand
  for a reload by giving the plugin, as it loads, a stored queue with entries being checked.
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

The Codex manifest selects `hooks/codex-hooks.json`, which intercepts native
`request_user_input` and `request_user_input_async` calls. It does not load the
Claude hooks module. Each call must contain one question; native answer options
are preserved and included in the review. Codex owns the question queue and answer
UI. The adapter adds no prompt band, standing instruction, or automatic citation
of the person's later answer.

The hook starts a fresh ephemeral `gpt-6.1-terra` checker at `xhigh`, at the project
directory. Normal global/project instruction discovery is retained; the proposing
conversation is not supplied. The checker retrieves decision records and chat
evidence itself. Configured plugins retain their normal selection, including
their skills. Hooks, agent delegation, apps, memories and the checker's own
question tool are disabled; native read/search tools remain available. It may
only read/search and refresh the configured chat index.

Codex checks clarity in a first turn, before history retrieval in a second turn
of the same ephemeral thread. A clarity rejection holds the native call. After
clarity passes, failed or incomplete history permits the question with a visible
history warning. An already-answered result still needs an original human
transcript path, line and exact words; the adapter verifies that row before
reusing the answer. Current Codex response-item evidence requires retained human
provenance, rather than trusting every user-role row. This verifies attribution
and the quote; whether those words settle the decision remains Terra's judgment.

The adapter observes completed chat-search commands. Failed history commands,
missing fresh-search evidence and partial coverage warn after clarity passes.
A search is fresh when the status before it reports no source changes or an
index less than five minutes old, or when an index run precedes it.
History permission interruptions are warnings only when the adapter can identify
the request as a direct cc-search-chats history command; it never grants that
approval. Unrelated permission requests, malformed responses, unavailable
clarity checking and cleanup failures remain denials. A warning does not claim
unread records were searched or that no prior answer exists, and it never
authorizes the operation the question asks about.

Requirements: Codex CLI/daemon 0.167.0, `uv`, Python 3.14+, `websockets==16.0`,
`cc-search-chats`, an accessible configured index/cache, and access to the Terra
model. The hook connects to the existing daemon reported by
`codex app-server daemon version`; it does not start another one. It uses existing
Codex authentication and permission configuration, requests ordinary approval
when required, and never grants an approval. An unrelated checker approval/elicitation request
makes the check unavailable; a recognized history-lookup request warns after clarity
passes. Complete any needed search approval through its normal permission flow. No cache or writable directory is invented.

Checks are synchronous and add latency before the native UI appears. The review
has a 150-second budget, original-citation lookup five seconds, and cleanup ten
seconds inside a 180-second hook timeout. Incomplete checks interrupt the checker
turn; all started checkers are unsubscribed and their connection closed. Cleanup
failure denies the question and reports the error. Unsubscribing is a request to
release the ephemeral thread, not proof that every host process has stopped.

Non-history failures handled inside the running Python checker return explicit denial. The
standard hook launcher reports missing `uv` to stderr and exits one; interpreter
or dependency startup failures likewise remain host launch failures. These,
disabled/untrusted hooks, cold startup, process crashes and host-level timeout
handling remain outside this guarantee; this is a question guard, not a security
boundary. The hook cannot
intercept questions written directly in chat. The existing global instructions
still direct the main session to use the native question tool.

For this repository's configured local marketplace, install with:

```fish
codex plugin add denubis-hook-question-zone@denubis-plugins --json
codex plugin list --marketplace denubis-plugins --available --json
```

Then use `/hooks` in Codex to review and trust Question Zone's new hook. A successful
install alone does not establish trusted execution; verify the hook is enabled and
trusted in the session used for acceptance. Re-review changed hooks after updates.

`QUESTION_ZONE_CODEX_SOCKET` can select an existing daemon socket for a controlled
test. It does not launch a daemon or change permissions. Running the entry point
directly with a hook payload checks the gate without presenting a question to the
person. The Python integration tests use that boundary and a fake Unix WebSocket
daemon; they establish protocol and gate behavior, not model judgment accuracy or
native installed-hook execution.

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

In the tests a stand-in answers for the checker. Under the `claude plugin test` kit of
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
