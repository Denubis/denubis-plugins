# 2026-11-24 — Codex shows a question with no check before it, and the search for an earlier answer runs afterwards in the background

**Status:** Accepted (2026-11-24). Amends, for Codex, item 5 of the Decision and the Codex
consequence of [2026-11-23-bbs-question-search-runs-after-queueing](2026-11-23-bbs-question-search-runs-after-queueing.md),
and, for its check before asking, item 6 of
[2026-11-08-bbs-questions-go-in-question-zone](2026-11-08-bbs-questions-go-in-question-zone.md).
Both stand for everything else they say. Item 5 of the Decision was added on 2026-11-25
(line 2890). Question Zone 0.3.0 carries the change.

## Authority evidence

Original human messages in Claude Code session `4508c81e-d079-4469-a8e7-aaaa7b0469e2`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/4508c81e-d079-4469-a8e7-aaaa7b0469e2.jsonl`):

- Line 1708 (`user` record `5dac4e50-2a1d-4a08-8c38-fd16e9fcce32`, origin human,
  2026-11-24T01:13:43.747Z), typed through the question box, answering "May a worker
  build the background search for Codex questions as described, including a live test
  in a throwaway Codex session?": "yes"
- Line 2615 (`user` record `ab7e13ab-7180-4b96-b07a-8de58d0455c9`, origin human,
  2026-11-24T05:44:36.446Z), after pasting two Codex questions that the clarity read had
  sent back ("Blocked by hook … question-zone (rewrite)"): ":( that's really bad, just
  drop the... thing from codex, it doesn't have enough question conversation"
- Line 2626 (`attachment` record `2ea8d944-e2a5-4b4d-a607-de3aa7d60a66`, a
  `queued_command` with origin human, sent while the supervisor was working,
  2026-11-24T05:44:44.396Z): "unless terra search-chats to find the context"
- Line 2731 (`user` record `dc1bd03b-dd64-47fa-b941-1663664b7dd6`, origin human,
  2026-11-24T06:03:20.053Z): "yes, remove the blocking check". It replies to the
  supervisor's message at line 2727 (`assistant` record
  `6f643a1c-ff3c-4ced-b66f-882a5c0c1e3d`, 2026-11-24T05:51:27.023Z), which set out both
  readings:

  > I'm taking your "just drop the thing from Codex" as the answer: the blocking check
  > comes out of Codex, and only the background search you approved earlier stays. A
  > fresh worker is building that now.
  >
  > I read your "unless Terra searches the chats" as an alternative you'd accept, not a
  > second requirement, so it isn't being built.
- Line 2890 (`user` record `e375c5f5-cca2-48db-b6cf-f22f0260e298`, origin human,
  2026-11-25T02:45:03.545Z), typed through the question box: "yes". The row quotes the
  question and the context he read:

  > The new Codex behaviour is built: a question from a Codex agent now reaches you at
  > once, and a background search then looks through your past chats for an earlier answer
  > and hands it to the agent as context. That search relies on a searchable index of your
  > chats. When the index is more than five minutes old and there are new chats to add,
  > the search first tries to bring it up to date, and inside Codex's restricted
  > environment that update fails. As built, any failed step ends the search with a
  > warning, so in practice the search finds an earlier answer only when the index happens
  > to be fresh. The alternative is to search the index as it stands when the update
  > fails, and attach a note that the newest chats were not covered. That would make the
  > search useful most of the time, at the cost of sometimes missing something you said
  > very recently. Your answer decides whether the worker changes this before the work is
  > committed.
  >
  > When the chat index can't be brought up to date inside Codex, should the background
  > search still search the older index and note that recent chats weren't covered?

The description Brian approved at line 1708 is the supervisor's, quoted in the same
record above his answer:

> You said that in Codex you still want a search of your past decisions and chats, run
> after a question is shown rather than before it. A worker has drafted how, without
> building anything. The short clarity read stays as the gate before a question appears.
> A second hook then runs in the background once the question is on screen and does the
> search, using the search code from the previous release, including its check that any
> quoted earlier answer really is in the original chat line. Go-ahead questions such as
> "may I commit" skip the search. If the search finds your earlier answer, Codex itself
> hands that to the asking session as extra context at its next step, or on your next
> message if the turn has ended. A failed search shows as a warning. The question cannot
> be removed from Codex's question box from outside, so you may still see a question you
> already answered. The whole delivery path rests on Codex's documentation and source
> code and has never been run, so the build would include a live test in a throwaway
> Codex session before anything is relied on. If you say yes, a worker builds this in the
> same working copy as the rest of today's question change; if no, the Codex side stays
> as built today, with the clarity read and no search.

```sh
sed -n '1708p;2615p;2626p;2727p;2731p;2890p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/4508c81e-d079-4469-a8e7-aaaa7b0469e2.jsonl
```

## Context

The 2026-11-23 record left Codex with the clarity read alone, before a question is shown,
and no search (its item 5), because a question Codex has shown cannot be taken back. At
line 1708 Brian approved a search that runs after the question is shown, with the
clarity read kept as the gate. Before that was built, the clarity read sent back the two
questions he pasted at line 2615, and he asked for it to be dropped from Codex.

## Decision

1. Codex shows a question with no check before it: the clarity read, and the hook that
   could hold a question back, are removed from Codex (line 2731, "yes, remove the
   blocking check", after line 2727 read line 2615 that way). The background search he
   approved at line 1708 stays. Line 2626 may set a condition instead, that the clarity
   read stay if Terra searches the chats for the conversation the question came from.
   Line 2727 read it as an alternative he would accept and said it was not being built;
   whether his reply at line 2731 also declines that alternative is not ruled. It is not
   built.
2. Once Codex has shown a question, a background hook searches the decision records and
   chat logs for an answer Brian already gave, with the previous release's search,
   including its check that a quoted earlier answer is in the original chat line (line
   1708). After review on 2026-11-25 that check was tightened: it now accepts only words a
   row shows Brian typed (see Consequences), so typed Codex messages, and Claude prompts
   from before June 2026, can no longer be cited. That narrowing is the supervisor's
   response to a review finding, not a ruling by Brian.
3. Go-ahead questions such as "may I commit" get no search (line 1708).
4. An earlier answer the search finds reaches the asking session as extra context at its
   next step, or with Brian's next message if the turn has ended. A failed search shows
   as a warning (line 1708).
5. When the chat index cannot be brought up to date inside Codex, the search still
   searches the index as it stands and notes that recent chats were not covered (line
   2890). The adapter applies this to a failed `cc-search-chats index` run: the search
   continues, a later search and a verified answer are used, and the note goes out as a
   warning beside an answer, or alone when none is found. A failed status, search or
   context command still ends the search with a warning.

This withdraws item 5 of the 2026-11-23 record for Codex, and the part of item 6 of the
2026-11-08 record that checks a Codex question before it is asked. The 2026-11-18 ruling
(an index under five minutes old is searched as it is, with no warning) and the
2026-11-10 ruling (a failed or incomplete lookup warns and never holds a question) govern
the Codex search again.

Item 5 relaxes, for a failed index run inside Codex only, the 2026-11-10 ruling as the
2026-11-18 record applies it ("The 2026-11-10 ruling still governs failed commands"): such
a failure no longer ends the search. The 2026-11-10 record's own words ask only that a
failed lookup warn, not that the search end there; ending at the first failed command
was 0.2.4's practice, which the question at line 2890 described ("As built, any failed
step ends the search with a warning"). The note keeps that warning, and says recent chats
were not searched rather than claiming they were. Whether item 5 changes the 2026-11-10
ruling itself or only that practice is the supervisor's reading, not ruled by Brian.

## Consequences

The following is the supervisor's design and the choices made in building it, not
Brian's words:

- Nothing in the Codex adapter can deny, hold or rewrite a question. The hook is a
  background `PostToolUse` hook on `request_user_input_async`; Codex documents that a
  background hook cannot block or rewrite the operation that started it, and the adapter
  returns only `additionalContext` or `systemMessage`.
- The rule of one question per call was part of the removed check and is no longer
  enforced in Codex. A call with several questions is searched as one.
- The synchronous `request_user_input` gets no search, on the inference that its
  `PostToolUse` runs only after Brian has answered. That was inferred from reading the
  asynchronous handler in Codex's source, and has not been tested.
- With no clarity read left, the searcher is told to decide first whether a question is
  a go-ahead and then to search nothing, and when unsure to search. The adapter does not
  enforce this: a go-ahead verdict gives no output whatever the turn ran. How Terra
  judges go-aheads has not been tried, and no live run asked one.
- An earlier answer reaches the asking model only once its quoted words are found among
  words Brian typed in the cited row of the original transcript (next item). The context says these are Brian's own earlier
  words, quotes them with their path and line, and tells the model to show them to him
  and let him confirm or change the answer, not to act on them before he replies, and not
  to take them as approval of what the question asks. The proposal before line 1708 left
  what the model does with a found answer to Brian (its question D1); that instruction
  is the supervisor's choice.
- What counts as words Brian typed was set from real transcripts after review. In
  Claude Code, a prompt row or queued prompt marked `origin` kind `human` (the marker
  appears from June 2026; earlier prompts have none and cannot be cited), less lines
  quoted with `>` or `▎` and the blocks Claude Code inserts for pastes and slash
  commands. Rows without the marker include teammate messages. In Codex, only the
  answers in a reply from its question box: typed Codex messages are recorded exactly
  like the briefs a Claude supervisor types into a Codex pane through tmux (170 rows
  beginning "Read codex-prompts/" in ordinary Codex sessions), and older `user_message`
  events hold such briefs too, so neither can be cited.
- A failed, incomplete or unreadable lookup, a quote not shown to be words Brian typed, a permission request from the search, and a cleanup failure each become a
  short `systemMessage`. Codex 0.169.0 shows it only as a count of warnings on the status
  line, read with F2. Partial coverage warns beside a verified answer too. A failed index
  run is the exception of item 5: the search goes on, and its note is a `systemMessage`
  too. Otherwise a search that finds nothing leaves no output.
- A command is read as a chat-search report only when it is a single `cc-search-chats`
  call with `--json`, alone or wrapped in a shell's `-c`. In live runs Terra piped a
  search into `python3` and asked for `--help`, and reading those outputs as reports
  ended the search with a warning.
- The search has 150 seconds and cleanup ten, inside a 180-second hook timeout. These
  are 0.2.4's figures for its clarity and history turns together; the search alone has
  not been timed beyond the live runs recorded in the CHANGELOG.
- Limits: the search may end after Brian has already answered in the box, and a question
  cannot be taken back from Codex's box. Codex runs at most eight background hooks per
  session; several searches at once may each try to refresh the chat index, and whether
  that needs a lock is unproven.
- A live limit, decided by item 5: inside the Codex sandbox, `cc-search-chats index
  --json` could not create its systemd scope ("You are probably blocked by your
  sandbox"). Until 2026-11-25 that ended the search with a warning, as in 0.2.4, so the
  search could find an answer only while the chat index was under five minutes old or had
  nothing new to index. Now the index is searched as it stands, with the note. The
  adapter takes any failed `index` run without `--status` as the index not being brought
  up to date, and adds the note even if a later index run succeeds. The searcher is told
  not to rerun a failed index run or ask for approval to: the failure's own report tells
  a model to ask for approval to run it on the host, and any approval request ends the
  search with a warning. Whether Terra follows that has not been tried. No live run has
  followed a failed index run with a search; that path is shown only by tests against a
  stand-in daemon.
- Unproven: the live runs used Codex 0.169.0 in embedded mode, with a throwaway Codex
  home and a separate app-server for the search. The shared background server (0.172.0
  on the machine), which Brian's sessions use, has not run this hook.
- Unproven: a supervisor answering a Codex question through the terminal (this
  repository's `codex_supervisor.py --answer` types into Codex's question widget) may be
  recorded like Brian's own question-box reply, and so be cited as his words. That is
  untested on Codex 0.169 and later, and no real use of `--answer` was found.
