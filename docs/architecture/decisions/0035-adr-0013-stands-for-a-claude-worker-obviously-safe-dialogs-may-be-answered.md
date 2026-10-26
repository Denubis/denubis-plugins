# ADR 0035 — ADR 0013 stands for a Claude worker: the driving Codex supervisor may answer obviously safe, narrow dialogs; everything else is Brian's

**Status:** Accepted (2026-10-24). Applies ADR 0013 and ADR 0022 to the
Codex-supervises-Claude mode.

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 369, a `queue-operation` (`enqueue`) record timestamped 2026-10-23T20:19:07Z
  (2026-10-24 07:19 Australia/Sydney), carrying the message Brian sent mid-turn:
  "yes, for stupid shit that is obviously safe, delegate to Astra"
- Line 484, `user` record `fb9f2f8b-b9c1-4bd8-a187-8df9b90432f2`
  (2026-10-23T20:27:14Z), answering the supervising session's question about what
  "delegate to Astra" meant: "um, Codex runs gpt-6-astra"

The first record's kind is a queue operation rather than a normal user-message record
because the message arrived while the supervising session's turn was running; the same
text is reproduced in the `api-request-blob` record at line 390.

Exact raw-record resolver:

```sh
sed -n '369p;484p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

The questions they answered, asked by the supervising session immediately before each:

1. "Do you want ADR 0013 to stand for the Claude worker too?", preceded by the
   recommendation "keep ADR 0013. Give the driver an approve path under the narrow-task
   test with the audit logging ADR 0022 asks for, and treat Astra's sentence as a conflict
   the spec author did not know about."
2. Whether "delegate to Astra" meant (1) the agent driving the Claude worker, the Codex
   host, presses Yes on obviously safe dialogs itself, or (2) a separate session is the
   approving party and the Codex host never approves. The supervising session had wrongly
   described Astra as a Claude session in that question; Brian's answer corrects it.

## Context

Astra's specification for the Codex-supervises-Claude mode
(`docs/design-plans/2026-10-24-claude-supervision-spec.md`, adopted by Brian on
2026-10-24; Astra is a Codex session on `gpt-6-astra`) says "Neither agent may approve
permission dialogs on the human's behalf or treat silence as approval." ADR 0013 rules
that a supervisor told it may drive answers a supervisee's dialog only when the request
fulfils the supervisor's own task "as narrowly scoped as possible" and escalates anything
with wider implications. ADR 0022 soft-retires the screen-reading keypress in favour of
decisions by reference through held hooks, and requires every remaining keypress approval
to be logged against the request it answered.

For a Claude Code worker the conflict is material: Claude prompts for most shell commands
and for writes outside its allow list, so under the spec's reading every such prompt stops
the loop for Brian and the spec's own "without you acting as the message relay" goal
holds only for prompt-free tasks.

## Decision

- ADR 0013 stands for a Claude worker. The spec's sentence is read as a conflict its
  author did not know about, not as a new ruling.
- The approving party is the driving supervisor, the Codex host, which in this mode runs
  `gpt-6-astra`. Reading (1) above.
- The approve path is limited to requests that are obviously safe and narrowly serve the
  task the supervisor was given (Brian's words: "stupid shit that is obviously safe").
  Anything else pauses and goes to Brian, as ADR 0013 already requires.
- ADR 0022's audit requirement applies: every supervisor-answered approval records the
  request, the task it was judged against, and the one-line reason.

## Consequences

- The Claude driver design (stage 1, prompt 11) drops the "no approve verb at all" branch
  as the default and keeps it only as the fallback for when no obviously-safe test can be
  applied.
- The "obviously safe" test needs an owner. It is not a number or a class list (ADR 0022
  rejected a decision count; ADR 0013 rejected a class list); it is the supervisor's
  judgement against its task statement, logged.
- Claude's own permission allow list and the approver hook policy still run first; only
  requests they leave to judgement reach the supervisor (ADR 0013 context).
- ADR 0006 still governs launching the supervisor itself: starting a Codex host on
  `gpt-6-astra` needs Brian to name the effort as well as the model. This ADR names the
  model for the role; it does not supply an effort.
