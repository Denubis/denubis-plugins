# Proposer/verifier core — resume (2026-07-06)

Worktree: **impl-plan-decision-discipline** (this branch). NOT main. Do not work on main.

This resume SUPERSEDES the 2026-06-25 version of this file (which said "build Step 0,
verifier first"). Step 0 is dead — see Dead, below.

**THIS resume is the current truth for the decisions; where it and any older doc
disagree, this wins.** Read it first. `.notes/project_proposer-verifier-decisions.md`
(dated 2026-06-29, human-ratified — do not edit it without Brian) is still useful for
the *reasoning*, but it PRE-DATES this thread's kills and is stale on three points:
its "Multiple-k" item and its "Home: a new plan-and-execute v2 plugin, grown from the
ground up" are DEAD (k-proposers rejected; the no-build vs tiny-mechanical fork is
open, not a committed v2 build), and its calling the quote-grep a "hardened …
provenance gate" is the exact mechanism-overclaim this thread disproved (see
Verified-facts). Trust this resume over those three lines.

## PARKED — read this first

**Do not add MORE cuts to `impl-plan-write` yet, and do not try to reconcile the
existing one yet.** The `.worktrees/skill-skills-upstream-sync` branch is mid-rebuild
of the SAME file in the opposite direction — it is *growing* it (hardening), at
phase-06 ("impl+hardening done, resume at coherence review"). At the 2026-07-06
snapshot: their file ~1467 lines, this branch 1329, main 1348 — numbers drift as they
commit, so re-measure rather than trust these. This branch already carries a −44 cut
(commit `e138cc0`, see Verified-facts below), so a collision with their +174 is
already latent; the task is to reconcile ONE cut when they land, not to pile on more.

**Park condition:** wait until `skill-skills-upstream-sync`'s work is **in main**, then
reconcile this branch's existing cut against that finished result. Check by testing
whether main CONTAINS their work, not whether a branch label survives (a squash-merge
or a post-merge branch deletion both leave `--merged` empty and would read as "still
parked" forever):

```bash
cd /home/brian/people/Brian/brian-ed3d-plugins
git fetch -q 2>/dev/null
# Probe for a distinctive marker their rebuild introduced (adjust the pattern to a
# phrase you confirm is in their shipped impl-plan-write, e.g. from commit fe13d35):
git show main:plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md \
  | grep -q "disclosed-oracle" && echo "MERGED — reconcile now" || echo "NOT in main — still parked"
git -C .worktrees/skill-skills-upstream-sync log --oneline -3 2>/dev/null || echo "(sync worktree gone — check main directly)"
```

Open question for when it lands: their `impl-plan-write` hardening may itself be more
of the scar we want gone. Glance at their finished result before reconciling — "wait,
then strip" could mean stripping work they just finished. Brian's call.

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
2. **The build-vs-cut fork.** Did this project aim at the wrong half — debating what to
   BUILD when the charter was to CUT `impl-plan-write`'s scar? Honest read: not purely
   wrong — you can't cut scar until you know the replacement, and the loop got
   clarified — but the only concrete strip so far is commit `e138cc0`, and further
   cutting is parked behind the other branch (see PARKED / Verified-facts).
3. **Two design gaps this thread exposed** (record only — do NOT reopen as a design
   round; noted so they aren't rediscovered from scratch): the loop has no way for a
   proposer to hold a correct position when the operator pushes back (twice the
   orchestrator folded and a cross-model critic had to resurrect the argument); and it
   assumes a fixed human criterion, but Brian was defining and checking the goal at
   once and the criterion moved mid-thread (gate: in-scope → out).

## First action next session

`cd` into this worktree. Run the PARKED check (above). 
- If their work is **NOT in main**: the `impl-plan-write` cut stays parked. Do only
  non-colliding work. Do NOT open a new design-process round — this thread's lesson is
  that design-process-about-the-design was itself the ornament.
- If their work **IS in main**: bring Brian the build-vs-cut fork (Open #2), and — only
  if he wants to proceed — the Contested fork (Open #1), since whether the strip lands
  in a pure-discipline or tiny-mechanical world changes what "strip" even means. Glance
  at their finished `impl-plan-write` before reconciling this branch's `e138cc0` cut.

Either way: **commit these three files first** (see below) — right now they are
untracked dirty state.

## Persistence (READ — the record is not durable yet)

This resume and the two design-doc banners are **untracked worktree state**; `.notes/`
is gitignored by design. One `git worktree` cleanup and this entire record is gone.
**Commit the two tracked-able files** (`RESUME-PROMPT-proposer-verifier-core.md` and
the two `docs/design-plans/*.md` banners) so the decisions survive. `.notes/` stays
uncommitted per its convention; its durability is the human's, not git's.

## Recovering this thread's reasoning (context is lost across sessions)

The full argument — including three critics' raw outputs (two Fable/cross-family, one
Opus, one Sonnet) — lives only in the session transcripts. Recover via cc-search-chats
on distinctive phrases: `"deeply ornate bullshit"`, `"it's just looking for keys"`,
`"summing up is poison"`, `"no build it's a discipline"`, `"deference dressed as insight"`.
