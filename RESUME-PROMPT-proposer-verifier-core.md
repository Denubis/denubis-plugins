# Proposer/verifier core — reference (2026-07-06, trimmed 2026-07-27)

Worktree: **impl-plan-decision-discipline** (this branch).

> **STATUS: reference, not current truth.** Current truth is
> `docs/design-plans/2026-07-27-planner-rebuild-rulings.md`. Where that record and this
> file disagree, it wins.
>
> Trimmed on 2026-07-27. The PARKED block was removed because the wait it described ended
> when `skill-skills-upstream-sync` merged on 2026-07-10, and this branch merged `main` at
> `447d633`. The build-versus-cut fork was removed from Open decisions because Brian
> settled it toward the full rebuild. What remains below is still live: the Dead list, the
> Contested fork, the verified-against-source facts, and the ADR checklist.

This file superseded the 2026-06-25 version (which said "build Step 0, verifier first").
Step 0 is dead — see Dead, below.

`.notes/project_proposer-verifier-decisions.md`
(dated 2026-06-29, human-ratified — do not edit it without Brian) is still useful for
the *reasoning*, but it PRE-DATES this thread's kills and is stale on three points:
its "Multiple-k" item and its "Home: a new plan-and-execute v2 plugin, grown from the
ground up" are DEAD (k-proposers rejected; the no-build vs tiny-mechanical fork is
open, not a committed v2 build), and its calling the quote-grep a "hardened …
provenance gate" is the exact mechanism-overclaim this thread disproved (see
Verified-facts). Trust this resume over those three lines.

## PARK — RELEASED, resolved 2026-07-27

The park is over and nothing here needs acting on. `skill-skills-upstream-sync` merged to
`main` on 2026-07-10, its probe returns MERGED, and this branch merged `main` at `447d633`
on 2026-07-27, closing a 201-commit gap.

The `e138cc0` collision it warned about resolved in this branch's favour. The three-filter
decision gate, zero-decisions-as-normal, the plain-language DR1 and the rewritten
AskUserQuestion summary all auto-merged intact. Two edits were dropped to `main`'s side,
the "Where I lean" line and the collapsed DR2-DR4 example run, and the codex critique had
already flagged the first as M2.

## What this is

A ground-up redesign of the lifecycle skill spine (design → impl-plan → execute →
review → ADR) into a proposer/verifier loop, by STRIPPING an ornate apparatus down to
something that earns its keep. The premise (the building model cannot verify its own
work, so the verifier must be a DIFFERENT, ideally cross-family model) is stated in
full — with the Huang/Tyen/Panickssery citations — in the still-valid Premise section
of `docs/design-plans/2026-06-25-innermost-core-proposer-verifier.md`. Not repeated
here to avoid two copies drifting.

## The loop, as clarified (qualitative — no scoring/pass-fail gate)

Orchestrator DISPATCHES (does no work in the main stream) → a DIFFERENT model
CRITIQUES the artefact against the human's intent → the critique reaches the human
**RAW** (the orchestrator summing-up the critiques is "poison" — self-preference +
the multi-agent literature) → the HUMAN RULES. Critique is prose: what worked, what
didn't, how well it engages what was asked. No voting, no grading, no points, no
scored pass/fail. (This does NOT by itself decide the Contested fork below: whether a
*single mechanical* step — the anti-fabrication gate, a human-triggered dispatch — has
a place is still open. "No scoring gate" ≠ "no mechanism of any kind.")

## Dead (Brian's calls this thread — do not rebuild)

- The whole **Step-0 two-skills apparatus**: a proposer skill + verifier skill, each
  emitting/reading CHECKLISTS and RUBRICS grown in `.notes/`, the proposer's "I did X
  based on Y" **provenance line**, the **basis-taxonomy** (artifact vs intent basis),
  the **ADR-index script**, the **Task-Condition-Standard doctrine mapping**,
  **k-proposers / divergence-as-signal**, and the bibliography-as-design-input.
- **All scoring / voting / grading / pass-conditions.** The "mechanise the gate" and
  "seeded-defect scoring harness" round-0 proposals were both rejected.

## Contested — NOT settled (do not record as decided)

- **"No build — the loop is a discipline, not a mechanism."** This is the emerging
  endpoint, but three critics attacked it and it has not been ratified:
  - It asks the untrusted orchestrator (a Claude model) to self-govern — faithfully
    dispatch critics and relay raw. That is the same self-preference the design forbids
    one layer up; the discretion to skip a critic or relay it softly is the poison
    again, just without a summary.
  - A discipline with no artifact leaves no independently inspectable evidence that it
    ran — unfalsifiable, and this repo's history shows head-resident discipline gets
    re-litigated every session until it sets into scar.
  - Steelman of the critics' counter: the non-ornate MIDDLE was never priced. The
    discipline's home could be tiny and already exists — amend the `codex-peer-review`
    raw-relay contract + the dispatch prompts + correct the stale docs. A few dozen
    lines, not an apparatus, and not the scored harness Brian rejected. The gate that
    evicts the suspect model from adjudicating findings against its own work, plus a
    human-TRIGGERED dispatch it cannot skip, are the candidate mechanical minimum — if
    Brian wants any mechanism at all.
  This fork (pure-discipline vs tiny-mechanical-home) is unresolved and is Brian's.

## Verified against source this thread (facts, not claims)

- The codex "gate" is **honour-system prose, not a mechanism.** `codex-peer-review.sh:116-118`
  only ECHOES a suggested grep; `SKILL.md:46,50` tells the *presenting* (suspect) model
  to hand-pick "2–3 verbatim quoted phrases," grep them, and judge "broadly." A same-
  family (Opus) critic re-asserted it WAS mechanical from the doc's self-description —
  the correlated-blind-spot thesis, demonstrated live. Cross-family reads caught it.
- The 06-25 design doc still bold-asserts "**The gate is mechanical, not prose**"
  (currently line 41 — grep the phrase, don't trust the number; banner insertions
  shift it). That is an aspirational PRINCIPLE, not a description of the current gate;
  codex separately flagged the line as too broad (scope to artifact gates, human-
  judgment for the rest) and that scoping was never written back. Banner added.
- The 06-25 resume said "build Step 0"; the design docs point at the killed apparatus.
  Docs bannered this session so a future session doesn't rebuild it.
- **`impl-plan-write` has ALREADY been cut on this branch.** Commit `e138cc0`
  (`refactor(impl-plan-write): strengthen decision gate, cut options-considered
  scaffold`) is +25/−44 against main on this exact file — that is why this branch is
  1329 lines vs main's 1348. So the PARKED section below is **breach-management, not
  prevention**: a −44 cut already sits on this branch and WILL collide with
  `skill-skills-upstream-sync`'s +174 whenever either merges. Do not add more cuts on
  top; the existing one is the thing to reconcile when their branch lands. (An earlier
  draft of this resume said "untouched this thread / nothing was actually cut" — false,
  caught by a cross-family review against git. Corrected here.)

## Open decisions (Brian's)

1. **The Contested fork** (above): pure-discipline vs a tiny mechanical home (the
   anti-fabrication gate mechanised + a human-triggered dispatch). Unresolved; Brian's.
2. ~~**The build-vs-cut fork.**~~ **SETTLED 2026-07-27** toward the full rebuild. Brian:
   *"let us treat the entire core of this as in-scope."* See
   `docs/design-plans/2026-07-27-planner-rebuild-rulings.md`.
3. **Two design gaps this thread exposed** (record only — do NOT reopen as a design
   round; noted so they aren't rediscovered from scratch): the loop has no way for a
   proposer to hold a correct position when the operator pushes back (twice the
   orchestrator folded and a cross-model critic had to resurrect the argument); and it
   assumes a fixed human criterion, but Brian was defining and checking the goal at
   once and the criterion moved mid-thread (gate: in-scope → out).

## First action — DONE 2026-07-27

Both the park check and the fork it gated are resolved. The standing guardrail survives
and still binds: **do not open a new design-process round**, because this thread's lesson
is that design-process-about-the-design was itself the ornament.

The live task list is in `docs/design-plans/2026-07-27-planner-rebuild-rulings.md`.

## Persistence

This resume and the two design-doc banners were committed 2026-07-06 (`a28b061`,
`ea7334e`) and pushed 2026-07-25, so the decisions survive a worktree cleanup. `.notes/`
stays uncommitted per its convention; its durability is the human's, not git's.

## ADRs — NOT written yet (checklist for when the forks close)

No ADR exists for this work (`docs/architecture/decisions/` holds only the three
crash-recovery ADRs). Deliberately deferred: the test (from the 06-24 doc) is that an
ADR records "a discovery made by looking, a refuted assumption" — NOT "Status:
Accepted" decision-theatre. Most of this thread is still contested/parked, so ADR-ing
it now would be theatre. When resolved, check each:

- [ ] **ADR: the codex quote-grep "gate" is not a mechanism** (READY on the merits —
  a discovery made by looking, an assumption refuted against source; see
  Verified-facts). Held back only because it belongs to the `codex-peer-review` skill
  in `denubis-external-agents`, which `skill-skills-upstream-sync` may be touching —
  confirm no collision there first, and decide whether the ADR lives in that plugin's
  scope rather than here.
- [ ] **ADR: the loop is qualitative cross-model critique, human-terminal** — write
  ONLY after the Contested fork (pure-discipline vs tiny-mechanical-home) closes.
  Writing it now records an unfinished decision = theatre.
- [ ] **ADR: what got killed and why** (Step-0 apparatus, scoring/harness) — optional;
  a "refuted approach" ADR is legitimate, but the resume's Dead section may suffice.
  Decide whether it earns a separate record or is just log noise.
- [ ] Before writing any of them, re-read `docs/architecture/decisions/README.md` for
  the repo's ADR convention (numbering, template) and match it.

## Recovering this thread's reasoning (context is lost across sessions)

The full argument — including three critics' raw outputs (two Fable/cross-family, one
Opus, one Sonnet) — lives only in the session transcripts. Recover via cc-search-chats
on distinctive phrases: `"deeply ornate bullshit"`, `"it's just looking for keys"`,
`"summing up is poison"`, `"no build it's a discipline"`, `"deference dressed as insight"`.
