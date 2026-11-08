# ADR 2026-11-08-bbs-questions-go-in-question-zone — Questions for Brian go in a question zone, a queue he takes one at a time with a key, each with its full context and no jargon; quiet-agents points at it

**Status:** Accepted (2026-11-08). Supersedes the quiet-agents nudge text marked "The ruled
text (2026-10-24)" at `plugins/denubis-hook-quiet-agents/hooks/register.tsx:325`, and
`denubis-hook-quiet-agents` README line 73. The box is built for Claude Code. The
cross-check before asking (items 5 and 6) binds Claude and Codex.

## Authority evidence

Session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`),
2026-11-08 UTC:

- Line 4964, Brian (`user` record `5fee3fe6-42a8-4188-81e7-8ab8979850f8`, 00:16:39Z): "there
  ... ok, sorry, let's fix something, there is a wall of you muttering to yourself, and then a
  passive agressive "I've stopped because you've not answered. How do we fix this behaviour
  because it is the primary thing pissing me off in interactions"
- Line 4992, Brian (`user` record `1b111877-7b06-42bf-9df3-56139b7271f8`, 00:18:02Z): "there is
  no fucking question that I can see in three screens. right, it's the final line of you
  muttering to yourself. FFS. this is... so frustrating. I hate this passive agressive bullshit.
  If we need to make a mod to have a special question zone so you don't need to keep being a
  pious little shit, I'd quite like that? And yes, let's drop risks. that's fine."
- Line 5275, Brian (`user` record `94501ebc-515b-4b0f-8f56-89a099120797`, 00:22:45Z): "I mean
  the nudge is whatever, but maybe it should just nudge to use this question queue?"
- Line 5278, the supervisor's reply (`assistant` record
  `67aaac15-308f-40c5-908d-0fc83d238cc9`, 00:23:07Z), its three bullets joined here: the new nudge will "stop finished agents;
  carry on with any agent whose work is unfinished; ask you anything through the question zone,
  never in chat", dropping "the "work through the pending questions" instruction".
- Line 5288, Brian (`user` record `f9cfd59c-c07c-4ef8-a4b1-b2b208fa2701`, 00:25:43Z): "and the
  question zone has what, a queue with context or... How does it work? Like, I kind of like the
  idea of something like the "have you noticed" whatever, where I hit a key to trigger next
  question, and there's enough context int eh question (AND NO INTERNAL REFERENTS. NO MADE UP
  JARGON. full and clear explanation) where it pastes the question in and then I answer it?"

```sh
sed -n '4964p;4992p;5275p;5278p;5288p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

## Context

Brian's global instructions already forbid repeated waiting notices, and require exactly one
clear question per ask. The model kept placing its question as the last line of a long message
and then restating that it was waiting. Brian called this "the primary thing pissing me off in
interactions".

## Decision

1. A mod gives questions for Brian a special question zone, which holds a queue of them.
2. Each question carries enough context to stand alone, in a full and clear explanation, with no
   internal referents and no made-up jargon.
3. Brian presses a key to take the next question. It is pasted into his prompt, and he answers
   it there.
4. The quiet-agents nudge tells the model to use the question queue, in place of its earlier
   instruction to work through the open-questions file.
5. Before a question is presented to Brian, a Sonnet or Terra model cross-checks it against
   the decision records and the chat logs. Brian, line 5564 (`user` record
   `bb9d8fc9-4b2e-4022-97b2-3d331450e0f8`, 2026-11-08T01:04:21Z): "and yes, questions should
   be cross-checked against ADRs and chat logs before being presented to be by a sonnet or
   terra". Resolver: `sed -n '5564p'` on the same transcript.
6. Codex does the same cross-check before it asks, using its own question tool. The supervisor
   had said the box exists only in Claude, so Terra "would apply only to a Codex version"
   (line 5589, `assistant` record `74f12da4-e06c-4b19-8173-1622262cc6b9`). Brian, line 5590 (`user` record `da8fee15-381d-43ba-af16-2d4f038b2be6`,
   2026-11-08T01:06:24Z): "yes, but codex can do the same, even if it just does a normal
   question, because it, unlike you, has a question tool". Resolver: `sed -n '5589p;5590p'`.
7. The question-zone plugin may add its standing instruction to Claude's system prompt. This is
   the allowance ADR 0051's contract requires, recorded in `tests/test_instruction_delivery.py`.
   The supervisor's question went through the box (line 5458, `assistant` record
   `27f74151-096b-4102-836e-8ecd731dc1de`, 2026-11-08T00:30:41Z): "Do you approve the
   question-box plugin adding that standing instruction to Claude's system prompt?" Brian,
   line 6416 (`user` record `4e874a67-67a2-4d13-9481-fa753100772f`, 02:35:05Z): "um, yes, do
   add the standing instruction." Resolver: `sed -n '5458p;6416p'`.
8. A turn started by an agent notification that carries nothing new gets no reply. This replaces
   quiet-agents' "one line or none". The supervisor had answered a late idle notice in one line
   (line 6263, `assistant` record `54447245-c1ec-4969-9e01-178c4efd584d`, 02:17:17Z: "That's the
   fixer's earlier report arriving late. It now has the redo for the lost-question fix."). Brian,
   line 6265 (`user` record `098e8a3e-bbda-49da-98c1-da08ca0d0d29`, 02:20:24Z): "sorry, I'm so
   fucking frustrated. I thought we have a mod for you not to whine about late reports". Reading
   this as a ruling on that case is the supervisor's interpretation. Resolver:
   `sed -n '6263p;6265p'`.

## Consequences

The following is the supervisor's design, not Brian's wording:

- Item 3 rests on line 5288, which Brian phrased as a question ("I kind of like the idea …
  then I answer it?"). It is built as he described it. Brian confirmed it in use, answering
  "Does the question box work the way you wanted?" through the box (line 7350, queued
  `attachment` record `61b6ab6f-e192-4de7-8dfd-e1602277c2a9`, 2026-11-08T04:08:29Z): "yep, this
  works just fine. We have a count, I push a button, I have a very clear question that I can
  answer. This is much better." Resolver: `sed -n '7350p'`.
- The queue is shown in a box above his prompt.

- The model asks only through the mod's `ask` tool, with the context and the question given
  separately. A standing system-prompt section forbids writing a question in chat, or
  mentioning that questions are waiting.
- Under ADR 2026-11-08-bbs-proposer-never-verifies, a fresh subagent reads each question cold
  before it joins the queue. If the question doesn't stand alone, it goes back to the model to
  rewrite.
- The key is `1` in an empty prompt. Submitting the pasted question with an answer removes it
  from the queue. The model receives the question and the answer in one message, so a decision
  record can quote both from a single original record.
- The open-questions ticket file stays. Its tickets are put to Brian through the queue.
- Unproven: that the model stops restating questions once the queue exists. No test can show
  that; only use can.
- In Claude, the queue replaces the global rule "Resolve that question before raising the next"
  (`~/.claude/CLAUDE.md:154-155`): several questions may wait while Brian takes them one at a
  time. Each entry is still one question. Codex has no queue and keeps the rule.
