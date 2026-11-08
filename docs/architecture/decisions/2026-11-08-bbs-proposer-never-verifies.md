# ADR 2026-11-08-bbs-proposer-never-verifies — Work is verified by a second, fresh worker before it reaches Brian; the proposer never verifies; Fable and Astra inspect, dispatch and evaluate

**Status:** Accepted (2026-11-08). For verification, it supersedes the August instruction
design's retirement of proposer and verifier dispatch
(`docs/design-plans/2026-08-11-instruction-control-system.md:105`). It also supersedes the
global instruction that supervisors keep verification and small edits direct
(`~/.claude/CLAUDE.md:27`, `~/.codex/AGENTS.md:27`): verification goes to a fresh worker, and
by default Fable and Astra delegate anything substantive (item 7). Item 8 narrows the default
that workers run "on the same infrastructure as their supervisor" (`~/.claude/CLAUDE.md:31`).
Item 7 narrows item 5: a trivial change is made directly. Items 9–11 narrow item 2 and the
Consequences below: a trivial change needs no fresh checker.

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
7. Fable and Astra make a trivial change themselves, such as a one-line edit; by default they
   delegate anything substantive. The supervisor's question, through the question box, asked
   whether a Fable or Astra session given a trivial change should make it itself rather than
   send it to a worker. Brian, line 8377 (`user` record `a83ee6da-aaad-4399-bf01-6f7ebd95ab92`,
   2026-11-08T05:50:22Z), with the question pasted above his answer: "yes. It's just that by
   default, for anything substantive, I want them to delegate. But spinning up a worker for a
   oneliner is silly. How do we make this the rubric?" Resolver: `sed -n '8377p'`.
8. A Claude session may use Claude or Sol workers. Using Codex through `supervising-codex` as
   the fresh cross-check of Claude's work is highly desirable. Codex sessions use only Codex
   workers until Brian's cross-platform route for them exists. The supervisor's question,
   through the box, asked whether the fresh checker may run on the other platform. Brian, line
   8711 (`user` record `7469cdb3-acf0-4818-8b68-7a46d5d6ca74`, 2026-11-08T05:59:07Z), with the
   question pasted above his answer: "claude sessions can use claude or sol workers, codex
   sessions right now only use codex workers but that's deeply frustrating and I'm building out
   the solution. so yes, having supervising-codex as a cross check is highly desirable. Codex
   will need to wait for same." Resolver: `sed -n '8711p'`.
9. A trivial change that Fable or Astra makes itself needs no fresh checker, and "trivial" is
   defined strictly. Calling it the firewall's one exception is the supervisor's wording. The
   supervisor's question, through the box, asked whether a fresh worker should still check such a change before it
   reaches Brian. Brian, line 8756 (`user` record `550d18a5-6b1b-47bc-9700-9709b92c395b`,
   2026-11-08T06:00:59Z), with the question pasted above his answer: "no, but we need to have a
   really strict rubric on trivial." Resolver: `sed -n '8756p'`. The rubric's wording in the
   instruction files is the supervisor's; item 11 removes the three-line limit it first had.
10. Item 9 applies to every session, not only Fable and Astra: no fresh worker checks a
    trivial change, whoever makes it. Reading item 7's first clause, making a trivial change
    yourself, as covering every session too is the supervisor's; the question asked about the
    check. The supervisor's question, through
    the box, asked whether the trivial-change exception applies to every session or only to
    Fable and Astra sessions. Brian, line 10016 (`user` record
    `d1eadb40-cf26-4e39-818f-2928154cac16`, 2026-11-08T08:09:58Z), with the question pasted
    above his answer: "any session. This is a common sense thing that I suspect I will
    regret". Resolver: `sed -n '10016p'`.
11. The strict definition of a trivial change does not count lines. A side agent's note told
    Brian that the draft instruction files defined "trivial" as at most three lines in one
    file, and told every session to delegate anything more. Brian, line 10104 (`user` record
    `3b2730a8-cf7c-499a-8049-f2c468c39c4d`, 2026-11-08T08:12:14Z), with the note pasted above
    his answer: "we can't do counting. that's... no this is a bad heuristic". Resolver:
    `sed -n '10104p'`. The supervisor's response, not Brian's wording: the drafts drop the
    limit of three lines in one file and keep the rest of the definition, and "delegate anything more" is
    limited to Fable and Astra, as items 5 and 7 rule. The supervisor then set out the
    remaining definition (line 10192, `assistant` record `14ee1ccd-38b5-42b1-9aa4-04c5be3d6bd1`,
    08:14:12Z): the exact edit can be stated before making it; it needs no investigation,
    design choice, ruling or new test; the diff alone shows it is right; in doubt, it is not
    trivial. Brian, line 10194 (`user` record `4e60b1fb-5009-4c94-95ce-4508186851c0`,
    08:15:47Z): "yep, that's fine as a heuristic". Resolver: `sed -n '10192p;10194p'`.

## Consequences

The following reading is the supervisor's, not Brian's wording:

- "No separate verifier" (line 4703) and "second fresh" (line 4727) are read together. The
  verifier is an ordinary fresh worker sent to check, not a standing verifier role, vote or
  approval machinery. Brian also said "the ceremony wasn't working. the lack of ceremony wasn't
  working."
- The verifying worker works under ADR 2026-11-08-bbs-critiques-need-demonstrated-flaws. It is
  not told what to find, keeps the instruction files, and reports only demonstrated flaws.
- The firewall is stated without a model, so it applies to every proposer, including a
  supervisor that drafts something itself. A trivial change is the exception (items 9–11).
- For Fable and Astra, inspection and trivial changes stay direct. Verification goes to a
  second fresh worker, and by default anything substantive goes to workers.
- Each hand-off to Brian costs one extra worker, unless the change is trivial.
- Item 6's "full verify checklist" and ADR 2026-11-08-bbs-critiques-need-demonstrated-flaws
  item 1 ("never tell them what to find") are read together. The checklist names what to check:
  the requirements, gates and sources. It never names an expected defect or outcome.
