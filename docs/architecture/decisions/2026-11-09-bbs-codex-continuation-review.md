# ADR 2026-11-09-bbs-codex-continuation-review — Terra reviews Codex stops, inactivity and completion of all workers

**Status:** Accepted (2026-11-09). Records the approved behavior of a Codex-specific
continuation plugin; implementation and live verification remain separate work.

## Authority evidence

Original records in Codex session `01a1bd25-e2b8-7e60-987b-6dd4546cbb35`:
`/home/brian/.codex/sessions/2026/11/09/rollout-2026-11-09T08-52-19-01a1bd25-e2b8-7e60-987b-6dd4546cbb35.jsonl`.
The timestamps below are UTC on 2026-11-08, the morning of 2026-11-09 in Sydney.

- Line 231, the supervisor's question (`assistant` message
  `msg_0abdc2fd9784aff0016af0f043ec0087d0bf370ace93d4bc02`, 21:57:35.459Z):
  "Should every normal Codex stop trigger an automatic completion check, accepting that
  extra latency and token use?"
- Line 238, Brian (`user` message `msg_01a1bd2d-0e1b-7aa2-a19c-b01afe3adcef`,
  22:00:08.987Z): "I... can we just have this trigger Terra or something? I don't know
  ... or is this just literally a \"Is this the end of requested...\" argh, I don't know
  how to design for this, but it's so frustrating"
- Line 243, the supervisor's proposal (`assistant` message
  `msg_0abdc2fd9784aff0016af0f0f8652887d0b470d2021388b2d5`, 22:00:35.845Z): use
  Terra as an independent reviewer when Astra tries to stop. The proposed review question
  was "Is there still an authorized next action that the main agent can take without the
  user?" The proposal specified the evidence and three outcomes recorded below, respect
  for an explicit interruption, and avoiding endlessly repeated ineffective nudges.
- Line 250, Brian's approval of that proposal (`user` message
  `msg_01a1bd2e-d0a2-7ca2-be41-661f7466bc9a`, 22:02:04.322Z), verbatim: "sures"
- Line 260, Brian (`user` message `msg_01a1bd2f-17a7-7a31-8d97-2e33fee5591c`,
  22:02:22.503Z): "sure, and it should trigger when absolutely nothing is happening"
- Line 277, Brian (`user` message `msg_01a1bd2f-6dbb-7f63-9077-385aa0fa42e3`,
  22:02:44.539Z): "it should also trigger when all workers are done"
- Line 280, the supervisor's restatement (`assistant` message
  `msg_0abdc2fd9784aff0016af0f186ac1887d09ec2914bf3918c25`, 22:02:49.699Z), named
  the three triggers below, then ended its turn. Brian reported that same failure in
  line 287 (`user` message `msg_01a1bd2f-fb4e-7653-a390-2da6f76f3597`,
  22:03:20.783Z): "... ... you just did it in this conversation"

Exact raw resolver, which does not require an index refresh:

```sh
sed -n '231p;238p;243p;250p;260p;277p;280p;287p' /home/brian/.codex/sessions/2026/11/09/rollout-2026-11-09T08-52-19-01a1bd25-e2b8-7e60-987b-6dd4546cbb35.jsonl
```

## Context

Brian requested a Codex-specific plugin because the main agent repeatedly stopped while
authorized work remained, including after workers completed. The original question was
whether every normal stop should receive a completion check. Brian suggested Terra; the
supervisor proposed an independent review with a concrete next action, and Brian approved
it and added inactivity and completion of all workers as triggers.

## Decision

1. Use Terra as an independent continuation reviewer for Codex. Its question is whether
   an authorized next action remains that the main agent can take without the user.
2. Trigger review when the main agent tries to finish, when it is idle with no work
   running, and when all workers have finished, including after the main agent stopped.
3. Give the reviewer the actual request, subsequent decisions, recent actions and worker
   status. The main agent's final paragraph alone is insufficient.
4. The accepted proposal has three outcomes: continue with a specific unfinished action;
   wait for an identified running worker or command and collect its result; or stop
   because the request is fulfilled or a specific unanswered human decision prevents
   further progress.
5. Distinguish a completed step or worker from the completed request, and check whether
   an alleged blocker was already answered. Remaining review, integration and verification
   can require continuation after every worker has finished.
6. Respect an explicit interruption and avoid endlessly repeating an ineffective nudge.

Items 1 and 3 to 6 are the supervisor's design approved by Brian's line-250 answer.
Item 2 combines its stop trigger with Brian's explicit additions at lines 260 and 277;
the wording about an idle main agent and work after it stopped is the supervisor's
restatement, rather than a verbatim human definition.

## Consequences

- A generic reminder to continue does not satisfy the accepted design: review must
  identify the concrete work that remains or the reason to wait or stop.
- The implementation must cover inactivity and completion after the parent has stopped;
  recording a worker result alone does not establish continuation.
- This record does not claim that a Stop hook alone covers all three triggers, or that
  the plugin has been implemented or verified. The wake mechanism and precise inactivity
  detection remain implementation work.
