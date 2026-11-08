# ADR 2026-11-08-bbs-proposer-never-verifies — Work is verified by a second, fresh worker before it reaches Brian; the proposer never verifies; Fable and Astra inspect, dispatch and evaluate

**Status:** Accepted (2026-11-08). For verification, it supersedes the August instruction
design's retirement of proposer and verifier dispatch
(`docs/design-plans/2026-08-11-instruction-control-system.md:105`). It also supersedes the
global instruction that supervisors keep verification and small edits direct
(`~/.claude/CLAUDE.md:27`, `~/.codex/AGENTS.md:27`).

## Authority evidence

Session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`).
Times are UTC on 2026-11-07, which is the morning of 2026-11-08 in Sydney. Where Brian extended
a message while it was queued, the fullest record is cited.

- Line 4659, Brian (`user` record `93aeccc1-2d79-4d07-ba0a-568529f9ec29`, 23:47:03Z): "ok, the
  other thing we need to build in is the idea of verifier. That any work should be checked
  before being given to me. And that fable and astra are mostly there to critique and
  supervise. And if they're chatting with me, they are directing subagents (sol/opus) not doing
  the work. And yep, that works well. (We also have to shorten global claude/agents anways)"
- Line 4688, the supervisor's question (`assistant` record
  `fbc3aeb9-f73f-419a-a216-e993a989e185`, 23:48:14Z): "Before work reaches you, who checks it:
  Fable or Astra themselves, or a separate fresh verifier agent that they send it to?"
- Line 4703, Brian (`user` record `634bf073-01b9-487f-a594-823be9e36f18`, 23:49:54Z): "well,
  they certainly don't do... any of those three first bullets. And no separate verifier. I mean,
  I don't know, the ceremony wasn't working. the lack of ceremony wasn't working. What does
  moving a few clicks to goldfish do?"
- Line 4709, the supervisor's question (`assistant` record
  `12cb9344-b5db-420e-9f49-73e42cd99cbc`, 23:50:33Z). It came after the reading "Fable and Astra
  do no hands-on work at all. No inspecting, no checking, no small edits": "Should Fable and
  Astra send finished work to one fresh checker like this before it reaches you?"
- Line 4719, Brian (`user` record `e64f9777-84d5-423e-92cc-7bba93d47842`, 23:53:13Z): "no they
  should inspect, but their job is to dispatch, and *evaluate* -- is what is delivered, is what
  is verified, is what is rebutted serving my goals or not? And, is what I'm saying coherent,
  are there questions to be asked, are there things to push back on?"
- Line 4725, the supervisor's question (`assistant` record
  `c8760150-ab05-497a-aa8b-900f468eb055`, 23:53:31Z): "Who should do the verifying: the worker
  that did the work, or a second fresh worker?"
- Line 4727, Brian (`user` record `e8a62182-5170-4a48-bbc9-b9f55ad908e1`, 23:53:46Z): "second
  fresh. proposer must never verify. that's the absolute firewall"

```sh
sed -n '4659p;4688p;4703p;4709p;4719p;4725p;4727p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

## Decision

1. Work is checked before it is given to Brian.
2. The proposer never verifies its own work. A second, fresh worker does. This is an absolute
   firewall.
3. Fable and Astra inspect, dispatch and evaluate. They judge whether what is delivered, what is
   verified and what is rebutted serves Brian's goals.
4. Fable and Astra also test what Brian says: whether it is coherent, what questions to ask, and
   what to push back on.
5. While talking with Brian, Fable and Astra direct workers such as Sol and Opus. They do not do
   the work themselves.
6. Fable and Astra poke around themselves, but hand a full verification checklist to workers.
   The supervisor's question (line 6381, `assistant` record
   `a391e6ec-df04-4c5f-aa34-1b8700b0fe71`, 2026-11-08T02:30:35Z): "Should Fable and Astra run
   diagnostics themselves, or hand them to workers?" Brian, line 6416 (`user` record
   `4e874a67-67a2-4d13-9481-fa753100772f`, 02:35:05Z): "fable and astra should poke around
   themselves, but hand a full verify checklist to workers." Resolver: `sed -n '6381p;6416p'`.

## Consequences

The following reading is the supervisor's, not Brian's wording:

- "No separate verifier" (line 4703) and "second fresh" (line 4727) are read together. The
  verifier is an ordinary fresh worker sent to check, not a standing verifier role, vote or
  approval machinery. Brian also said "the ceremony wasn't working. the lack of ceremony wasn't
  working."
- The verifying worker works under ADR 2026-11-08-bbs-critiques-need-demonstrated-flaws. It is
  not told what to find, keeps the instruction files, and reports only demonstrated flaws.
- The firewall is stated without a model, so it applies to every proposer, including a
  supervisor that drafts something itself.
- For Fable and Astra, inspection stays direct. Verification goes to a second fresh worker, and
  small edits go to workers.
- Each hand-off to Brian costs one extra worker.
- Item 6's "full verify checklist" and ADR 2026-11-08-bbs-critiques-need-demonstrated-flaws
  item 1 ("never tell them what to find") are read together. The checklist names what to check:
  the requirements, gates and sources. It never names an expected defect or outcome.
