# ADR 2026-11-08-bbs-critiques-need-demonstrated-flaws — A critique, or a check someone adds, is acted on only when it shows a flaw that exists now; reviewers are never told what to find

**Status:** Accepted (2026-11-08). Binds reviewers, supervisors and implementers in Claude and
Codex, through both global instruction files, `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`
(item 7).

## Authority evidence

Session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`).
Times are UTC on 2026-11-07, which is the morning of 2026-11-08 in Sydney. Where Brian extended
a message while it was queued, the fullest record is cited.

- Line 4301, the supervisor's question (`assistant` record
  `288b3d8e-f318-4d40-bce9-01995f740660`, 22:30:10Z): "Should reviewers start clean, seeing
  only the thing under review and its sources, not my conclusions or your CLAUDE.md?"
- Line 4311, Brian (`user` record `7dc9fcde-051a-4be3-b13c-ba55150c2daa`, 22:33:21Z): "um, we
  should never tell them what to find, they'll find it. But I'm ... unpack the no global/local
  Claude.md thing? also go pull discussion and research around this framework, do they ever
  explain *Why* they have done things?"
- Line 4341, the supervisor's lean (`assistant` record `aaa1a4df-62f5-4941-aabc-ea5084f72e79`,
  22:34:39Z): "My lean is to keep CLAUDE.md for code and plan reviews".
- Line 4359, Brian (`user` record `da3e6fd6-4fbe-4a32-8384-784393858c2a`, 22:40:51Z): "I...
  yeah, most times I want to keep my claude.md files? What evidence is there for isolation
  being good"
- Line 4410, Brian (`user` record `5bebf8f3-f4aa-4d67-9b91-3e3c3517df27`, 22:46:53Z): "there's
  also the problem, since we're fixing this, of critical reviews creating epicycles. Critiques
  must be grounded in demonstrated facts, not anticipated future edge cases. We do not want to
  add ever-increasing epicycles of complexity as claude and codex review each other."
- Line 4464, Brian (`user` record `f65557ea-702c-4841-848d-0e44576c1c8a`, 22:50:09Z): "except
  the reviewers very very very much do not discard here. Because it is more of a "demonstrate
  the flaw" issue, rather than ... premature not even optimisation, but armour against issues?
  I want reviewrs to focus on code quality, not anticipating future issues. Of course, any issue
  they can prove is valid. I wonder if it's a "a thing needs to be fixed when a red test is
  handed back?""
- Line 4470, the supervisor's question (`assistant` record
  `00e8204a-36b0-44b0-b898-486706053cd9`, 22:50:34Z): "Since most code-quality findings can't
  come with a red test, is pointing at the exact lines and the written rule they break enough
  proof for one?"
- Line 4476, Brian (`user` record `3869998b-bdd5-40e6-9c37-fff07ad703ee`, 22:53:01Z): "yes, and
  go see if that would genuinely catch fable/astra epicycles?"
- Line 4619, the supervisor's question (`assistant` record
  `b7569871-e520-47c6-9adc-3695b1bba752`, 23:35:42Z), after reporting that half the rejected
  cases were supervisors' own additions, "so the rule only works if it binds them as well as
  reviewers": "Should the rule go into both global instruction files?"
- Line 4659, Brian (`user` record `93aeccc1-2d79-4d07-ba0a-568529f9ec29`, 23:47:03Z), ending:
  "And yep, that works well. (We also have to shorten global claude/agents anways)"

```sh
sed -n '4301p;4311p;4341p;4359p;4410p;4464p;4470p;4476p;4619p;4659p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

Earlier statements of the same rule in Brian's words. Neither global instruction file nor any
plugin skill or agent carried them on 2026-11-08:

- 2026-10-12T00:47:35Z, `ccchat:v1:codex:01a12d75-33be-7c82-b7d4-4f10ef64e26d:id:msg_01a12d94-4ba1-7861-a57f-98c804c113de`:
  "again, no epicycles. Generalise your critiques, don't invent hypotheticals"
- 2026-10-12T00:47:59Z, `ccchat:v1:codex:01a12d75-33be-7c82-b7d4-4f10ef64e26d:id:msg_01a12d94-a8ed-7bd2-a8aa-f3941678ce51`:
  "please fix your critique to actual specific flaws that have been demonstrated, not
  hyptohetical scenarios for a thing you don't know about"
- 2026-10-18T05:14:08Z, `ccchat:v1:codex:01a14c1c-fb01-7c62-a73a-ee426792ed80:id:msg_01a14d6e-7a08-7663-8e00-792ef11c04a4`:
  "the judgement is to *not* implement the suggested fixes because they are for ever more
  extreme hypotheticals rather than real world failures"
- 2026-10-28T04:18:58Z, `ccchat:v1:claude:a6c33ae6-c8c3-4cfd-ae40-9004da527e28:uuid:8227922e-b06b-4337-ab1a-cdd6a5aba0ba`:
  "the goal here is to simplify, not add extra complixity for unanticipated problems. Either
  prove the problems, discuss the class of problems, or stop borrowing future problems"
- 2026-10-28T23:48:55Z, `ccchat:v1:codex:01a1755a-0eea-7fe2-b51e-21efabfef24b:id:msg_01a184ea-af66-7e42-8e17-e62e812729d3`:
  "also, above all else, no epicycles. You must, if there is a critique show where there is a
  problem in fact, not a problem in possibility. We want professional standards here, but no
  ever increasing epicycles"
- Recorded in project documents: the approver's ADR-0073
  (`/home/brian/people/Brian/approver/docs/decisions/adr-register.md:4309`), and in this
  repository `docs/design-plans/2026-10-09-cross-provider-messaging/critical-review.md:11` and
  `docs/design-plans/2026-10-12-bibliography-0.19-scan-detection-and-zotero-crud.md:43`.

## Context

- A comparison with Google's Elephant-Goldfish Model on 2026-11-08 found little evidence that
  isolating reviewers helps. The one direct test, a single-author preprint using planted errors,
  found a review in a fresh session significantly better only than a second look in the same
  session, and not significantly better than the author's first look (Song, arXiv:2603.12123
  v2).
- A chat-search worker reported on 2026-11-08 at least 28 statements of this rule since 2026-09-14. Our
  own reviewer wording asks each lead for "a check that could settle it"
  (`plugins/denubis-plan-and-execute/agents/code-reviewer.md:12-13`), which an unsettled guess
  satisfies. Of 12 past cases Brian rejected, half were a supervisor's or implementer's own
  added checks, not review findings.
- A blind test of a draft of this rule on those cases dropped the speculative findings and kept
  the strongly accepted ones. It kept some real findings whose fixes Brian had rejected as
  piling up special cases.

## Decision

1. A reviewer is never told what to find.
2. Reviewers keep the user and project instruction files most of the time. Brian has not named
   the exceptions.
3. A critique is acted on only when it is grounded in a demonstrated fact: a flaw that exists
   now, not an anticipated future edge case. Any flaw a reviewer can prove is valid.
4. For a code-quality finding, the exact lines and the written rule they break are enough proof.
5. The rule binds a supervisor's or implementer's own added checks, safeguards and special cases
   as well as review findings, so that Claude and Codex reviewing each other do not add
   ever-increasing epicycles of complexity.
6. A proven flaw is fixed for its class of problem, not with another special case ("Find the
   *patterns* of problems", 2026-10-28T04:18:17Z,
   `ccchat:v1:claude:a6c33ae6-c8c3-4cfd-ae40-9004da527e28:uuid:91a0427d-9e94-4845-a217-af3c65f36d84`;
   "discuss the class of problems", above).
7. The rule goes into both global instruction files.
8. The global instruction to "critique work proleptically: expose weaknesses, tradeoffs, risks,
   and assumptions before presenting" (`~/.claude/CLAUDE.md:7`, `~/.codex/AGENTS.md:7`) drops
   "risks". The supervisor's question (line 4942, `assistant` record
   `f8364bfc-638e-42ec-a388-ce9994d7b483`, 2026-11-08T00:15:46Z) proposed dropping it and saying
   the weaknesses must be in the work itself. Brian's answer (line 4992, `user` record
   `1b111877-7b06-42bf-9df3-56139b7271f8`, 00:18:02Z): "And yes, let's drop risks. that's fine."
   Resolver: `sed -n '4942p;4992p'` on the same transcript.
9. Codex's global instruction file carries the rule to halt after review findings, as Claude's
   does. The supervisor's question (line 6381, `assistant` record
   `a391e6ec-df04-4c5f-aa34-1b8700b0fe71`, 2026-11-08T02:30:35Z): "Should Codex's file also
   carry the rules on halting after review findings and on push needing your say-so?" Brian,
   line 6416 (`user` record `4e874a67-67a2-4d13-9481-fa753100772f`, 02:35:05Z): "codex should
   halt after review findings, yes." His answer does not cover push authority; ADR
   2026-11-08-bbs-codex-push-needs-say-so records that ruling. Resolver: `sed -n '6381p;6416p'`.
10. Claims are still actively tested. Reading his answer as removing only the imagined
    counterexample, "imagined" taken from the question's own premise, is the supervisor's. The supervisor's
    question, put through the question box, asked whether the shortened files should drop "test
    the strongest plausible counterexample" (`~/.claude/CLAUDE.md:15`, `~/.codex/AGENTS.md:15`).
    Brian, line 8177 (`user` record `0d4216b0-a6ff-4740-9c75-d5e7676ef085`,
    2026-11-08T05:40:34Z), with the question pasted above his answer: "um... arrgghhhhhh. The
    goal here is to actually *test*. If something is bad, why is it bad. If something is good,
    what can we shatter? But yes, I also don't want this to endlessly popper ad hoc". Resolver:
    `sed -n '8177p'`.
11. A model may always push back, including on another model's premise. This general rule is
    promoted from the Codex supervision skill into both global files; it also stays in the
    skill. Reading "this is what search-chats is for?" as "evidence a reviewer could not see is
    found with chat search, not taken to Brian" is the supervisor's. The supervisor's question, through the box,
    asked whether both global files should carry its proposed rule on answering a reviewer's
    finding (cite evidence the reviewer could read; otherwise take the finding to Brian; never
    rebut "I could not follow this"; wanting to disagree is not evidence). Brian, line 8256
    (`user` record `907c5eb0-3fda-41b7-9cfc-4b676db6b475`, 2026-11-08T05:41:51Z), with the
    question pasted above his answer: "I mean, this is what search-chats is for? and a model
    absolutely is allowed to push back on the premise from a different model. that's core to
    supervising codex and should actually be promoted to global. It is always OK to push back
    on assumptions or a badly worded request or something that doesn't make sense. The goal is
    to be clear and to have a coherent vision. Not to create endless complexity. And never to
    assume". Brian did not approve the proposed rule's other clauses; dropping them is the
    supervisor's choice. Resolver:
    `sed -n '8256p'`.
12. A check that crashed, timed out, or could not read what it was meant to check has produced
    no result; its silence is never a pass. A check's silence counts only when it is shown to fail when it should, pass when it
    should, and cover the thing's proper extent. The supervisor's question, through the box,
    asked whether both global files should say that a check, reviewer or verifier that failed or
    could not read its inputs counts as not run, never as "found nothing". Brian, line 8664
    (`user` record `5a0f2997-59ee-4c7c-b41f-d622bc743135`, 2026-11-08T05:57:21Z), with the
    question pasted above his answer: "absence of evidence is not evidence of absence. But there
    are ways to demonstrate a grap. So no, this is an important thing. We care about the
    epistimological boundaries. Do things fail when they should and pass when they should? Do we
    know the thing is at it's *proper* extent?" The supervisor read "So no" as keeping the
    clause, and a fresh checker found that reading reversed his literal answer. The
    supervisor then put the question again through the box. Brian, line 10893 (`user` record
    `e5e030f4-99a2-4cb5-9577-6d6b213344bd`, 08:57:47Z), with the question pasted above his
    answer: "that's strange wording?" The supervisor reworded the clause and asked whether
    both files should carry "A check that crashed, timed out, or could not read what it was
    meant to check has produced no result; its silence is never a pass". Brian, line 10929
    (`user` record `e55b1c54-4ea6-476e-959a-2c75f4becc13`, 09:04:26Z), with that question
    pasted above his answer: "yes, silence is not a pass". Resolver:
    `sed -n '8664p;10893p;10929p'`.
13. The proleptic challenge, which tests a design or decision before it binds later work, may
    anticipate failures; this rule does not bind it. The supervisor's question, through the box,
    asked whether that skill should keep asking the model to anticipate failures. Brian, line
    8933 (`user` record `beee8e9b-dd4b-4b0d-ab22-1aa00f1c58f9`, 2026-11-08T06:10:25Z), with the
    question pasted above his answer: "yes, proleptic gets to anticipate. It's not involved in
    code review, right?" Searched on 2026-11-08, the skill is routed from the design skills
    (`starting-a-design-plan`, `design-write`) and named in the instruction-control rubric, and
    from no code-review skill or agent. Resolver: `sed -n '8933p'`.

## Consequences

The following reading is the supervisor's, drawn from the blind test, not Brian's wording:

- A behaviour bug is proved by a failing test, a reproduction, or the exact lines that make a
  current or stated path fail.
- A document, plan or claim is proved wrong by the source that contradicts it.
- A gap in a design not yet built counts only when a stated requirement or another part of the
  design needs what is missing, and the finding cites both.
- Keeping an existing check is not an addition.
- The proof travels with each finding; "as said last round" is not proof.
- Wording that invites anticipation is replaced, not supplemented. That covers
  `code-reviewer.md:12-13` and the global instruction to "test the strongest plausible
  counterexample" (`~/.claude/CLAUDE.md:15`, `~/.codex/AGENTS.md:15`).
- Unproven: whether the new wording reduces epicycles in live work.
