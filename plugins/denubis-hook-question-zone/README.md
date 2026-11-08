# question-zone

A Claude Code mod (a plugin built from a hooks module) that keeps the model's questions
for the person out of the chat. Each question waits in a queue shown above the prompt,
and the person answers when ready.

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
   brings their index up to date, running `cc-search-chats index --json` whenever
   `cc-search-chats index --status --json` reports changes not yet indexed.

The check runs in the background, because a search takes up to a minute or more and a
hook may spend only ten seconds of its own time; waiting for a subagent counts against
that. A clear entry joins the end of the queue when its check ends. Otherwise one message
from this plugin starts a turn for the model, carrying the checker's reply: what a reader
could not understand, the person's existing answer with where and in what words, or why
the check could not run, such as an index that could not be updated, with a reason the
person can act on. Nothing unchecked joins the queue.

The checker is registered as `denubis-hook-question-zone:checker`. It runs on Sonnet at
effort `xhigh`, following the ruling that a Sonnet or Terra cross-checks questions; Terra
is the Codex-side choice and does not apply to this plugin. Its tools are `Read` and
`Bash`, for reading the records and running `rg`, `git rev-parse` and `cc-search-chats`.
Its commands go through the session's permission rules like any other. It keeps the
person's and the project's instruction files, as reviewers do by default. It is never
offered to the model, so only the plugin starts it.

**The band above the prompt.** With nothing queued the band shows nothing. Otherwise it
shows how many questions are waiting and a button, `1: Take the next question into the
prompt box`. With the prompt box empty, pressing `1` presses it, as it does for a survey.

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

**Withdrawing.** The `withdraw` tool (`mcp__denubis-hook-question-zone__withdraw`)
removes a question the model no longer needs. It takes the question's text exactly as
asked, because positions in the queue move as the person takes and answers questions.
It removes a question that is being checked, waiting, or already in the prompt box (whose
quoted text stays in the box). A question withdrawn while it is checked neither joins the
queue nor comes back when its check ends. It refuses a text that matches no question, and any call from a
subagent or teammate.

**The model's standing rule.** The system prompt ends with a short section. It says that
every question for the person goes through `ask`, that the model never writes a question
to the person in chat, and that it never mentions, lists or reminds the person of waiting
questions, or says it is waiting. It also says that questions in the project's
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

- **The background check has run live once.** On 2026-11-08 a `claude -p` session made
  two asks; each returned in under a tenth of a second. The checkers, on
  `claude-sonnet-5-5`, ran `cc-search-chats index --json`, which failed because the
  graphics card was nearly full. The check of a question the person had already answered
  took 68.7 seconds and came back with the decision record's path and lines and the
  person's words, checked against the original chat message. The check of a question
  never answered took 39.5 seconds and came back saying the check could not be made, and
  naming the program holding the graphics card. A clear entry joining the queue has not
  been seen live.
- **While the graphics card is busy, every check fails.** Sessions keep writing to the
  chat logs, so the index is rarely up to date and the checker tries to update it each
  time. The person has said that telling them to stop the program using the card is a
  fine answer.
- **Some chat files are not indexed.** On 2026-11-08, 29 files were blocked by a record
  type `cc-search-chats` does not yet read; an index run does not clear them, and the
  checker does not search them.
- **A check restarted after a reload has not been seen live.** The plugin's tests stand
  for a reload by giving the plugin, as it loads, a stored queue with entries being checked.
- **The band, the button and the prompt box have not been used live.** Their behaviour is
  established by the plugin's tests only.
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
