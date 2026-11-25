# 2026-11-23 — A question joins the queue after its clarity read; the search for an earlier answer runs afterwards, never for a go-ahead, and not in Codex

**Status:** Accepted (2026-11-23). Amends items 5 and 6 of
[2026-11-08-bbs-questions-go-in-question-zone](2026-11-08-bbs-questions-go-in-question-zone.md),
which stands for everything else it says. Question Zone 0.3.0 carries the change.
For Codex, item 5 and the Codex consequence are amended 2026-11-24 by
[2026-11-24-bbs-codex-question-search-runs-after-showing](2026-11-24-bbs-codex-question-search-runs-after-showing.md):
Codex shows a question with no check before it, and the search runs afterwards in the
background.

## Authority evidence

Original human messages in Claude Code session `4508c81e-d079-4469-a8e7-aaaa7b0469e2`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/4508c81e-d079-4469-a8e7-aaaa7b0469e2.jsonl`),
both typed through the question box, each below the question it answers:

- Line 580 (`user` record `35e74104-3dec-4309-8457-12f2714c2b5e`, origin human,
  2026-11-23T08:59:27.697Z), answering "Should questions reach you after the quick
  clarity read alone, with the search of past decisions and chats removed from the
  check?": "it's more that... maybe  that's a backend thing if it's a question that isn't
  an immediate operational one? I don't know"
- Line 641 (`user` record `125a32f7-7af4-4a43-86ed-b1c195eaeb40`, origin human,
  2026-11-23T10:19:40.084Z), answering "Shall a worker build that proposal, where every
  question reaches you after the short clarity read and the search of past answers runs
  afterwards in the background only for questions that are not go-aheads?": "yes"

The proposal Brian approved is the supervisor's wording, quoted in the same record
above his answer:

> This follows your answer that the search of past decisions and chats could be a
> background thing for questions that are not immediate operational ones. The proposal
> is this. Every question an assistant asks gets only the quick clarity read, about 11
> seconds, and then appears in the queue above your prompt. During that read, the fresh
> reader also says whether the question is a go-ahead for something the session is about
> to do, such as a commit, a push, or running an approved plan. Go-ahead questions get no
> search at all. For every other question, the search of your decision records and past
> chats starts after the question is already in the queue, so it never delays you. If
> that search finds an answer you gave earlier, the question is taken out of the queue
> and the assistant is handed your earlier words with their source, as happens now; if
> you have already pulled the question into your prompt box, it is left alone. In Codex
> the question box belongs to Codex and a question cannot be taken back once shown, so
> there the check would be the clarity read only, with no search. If you say yes, a
> worker designs and builds this in the question plugin; if you say no, nothing changes
> yet.

```sh
sed -n '580p;641p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/4508c81e-d079-4469-a8e7-aaaa7b0469e2.jsonl
```

## Context

Items 5 and 6 of the 2026-11-08 record put a cross-check against the decision records
and the chat logs before a question is presented, in Claude and in Codex. The figures
behind the change are the supervisor's, from a survey made for the question Brian
answered at line 580. That question, quoted in the same record above his answer,
reported them so:

> ...survey of the 444 questions asked in Claude sessions between 8 and 23 November
> found that the clarity read takes about 11 seconds, while the search makes the whole
> check take about four minutes. The search sent 125 questions back as "already
> answered", but in 98 of those you had answered in chat while the check was still
> running, and in only 4 was your answer more than an hour older than the question.

The survey's table was temporary and is not kept, so the figures are not re-derived here
and cannot be re-checked from this repository. The proposal he approved at line 641,
quoted above, repeats the 11 seconds.

## Decision

As the approved proposal puts it:

1. Every question gets only the quick clarity read, and then appears in the queue.
2. During that read the fresh reader also says whether the question is a go-ahead for
   something the session is about to do, such as a commit, a push, or running an
   approved plan. A go-ahead gets no search.
3. For every other question, the search of the decision records and past chats starts
   after the question is already in the queue.
4. If that search finds an answer Brian gave earlier, the question is taken out of the
   queue and the assistant is handed his earlier words with their source. If he has
   already pulled the question into his prompt box, it is left alone.
5. In Codex the check is the clarity read only, with no search. (Amended 2026-11-24 by
   the record named under Status: in Codex there is no check before a question is
   shown, and the search runs afterwards.)

This amends item 5, whose cross-check no longer comes before a question is presented,
and item 6, whose Codex cross-check against the records and chats is withdrawn. The
2026-11-18 ruling (an index under five minutes old is searched as it is, with no
warning) still governs the search in Claude. The 2026-11-10 ruling (a failed or
incomplete lookup warns and never holds a question) holds there only while the question
waits in the queue. That is a limit: a search that fails or is incomplete after the
question was taken into the prompt box leaves no warning, because the text in the box
is not rewritten and the approved proposal leaves a taken question alone. Codex no
longer has a lookup for either ruling to govern.

## Consequences

The following is the supervisor's design and the choices made in building it, not
Brian's words:

- The reader, never the asking model, says whether a question is a go-ahead; the `ask`
  tool gains no way to claim it. A reader unsure counts the question as not a go-ahead,
  since a wrongly named go-ahead skips the search while a missed one costs only a
  background search.
- In Claude the reader has no tools. The search is a second subagent type, with `Read`
  and `Bash`, on Sonnet at `xhigh` like the reader.
- A search's end acts only on a question still waiting in the queue that has never been
  taken into the prompt box. Taking it puts it out of the search's reach for good, even
  if Brian clears the box and it returns to the queue. Answering or withdrawing it does
  the same, and nothing is said about it.
- Taking a question claims it in the queue before its text goes into the box, so a
  search that ends meanwhile either took it out first, leaving the box empty, or finds
  it claimed and keeps its result until the box answers. If the text goes in, the kept
  result is dropped. If the box refuses the text, the claim is undone, and a result kept
  meanwhile acts on the question as if the take had never been tried; a search whose
  turn comes during the claim starts, since the box may yet refuse.
- A search that fails, reports incomplete coverage, or gives a reply the plugin cannot
  read leaves the question queued with a warning, shown above the prompt while it is
  first in the queue and in the text copied into the answer box. A warning that arrives
  after the question was taken is dropped (the limit stated under Decision).
- The band counts a question whose search still runs as waiting, and counts only
  clarity reads as being checked.
- Searches run one at a time, in the order their questions joined the queue (as their
  clarity reads ended, which need not be the order asked), and each tries for a
  subagent slot only while no clarity read is waiting to start (the supervisor's choice
  after the 2026-11-23 review). Between them they hold at most one slot, so a question's
  read waits on a search only when every other slot is taken. No run has a time limit,
  so a search that never ends holds back every later search until the plugin reloads.
- The prompt that carries unread notes waits until no clarity read and no search is
  running or waiting its turn, or five minutes, following the supervisor's reading
  recorded in item 10 of the 2026-11-08 record (counting searches is the supervisor's
  choice after the 2026-11-23 review). A search waiting its turn counts as running, so
  searches that each take a question out one after another send one prompt when the
  last ends, not one each.
- On a reload, a queued question whose search had not ended, and that has not been
  taken, is searched again.
- The Codex adapter makes one clarity turn and keeps nothing of its history path: no
  search tracing, index pause, citation verification, or already-answered outcome. Its
  review budget is 90 seconds and its hook timeout 120, down from 150 and 180.
  (Superseded 2026-11-24 by the record named under Status: the Codex adapter has no
  clarity turn, and runs the history search in the background after a question is
  shown.)
- Unproven: everything above is shown only by tests with stand-ins for the subagents and
  the Codex daemon. No live session has run the two-stage check.
