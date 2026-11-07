# ADR 2026-11-02-bbs-claude-codex-adapter-no-scraping — Claude drives Codex through a per-client adapter without reading its screen; a send needs no typing protection, and a clear is a new session

**Status:** Accepted direction (2026-11-02). The transport is not yet adopted: a live experiment
tests it first. Answers the transport question ADR 0039 left to the service design; ADRs 0014 and
0039 otherwise stand.

## Authority evidence

Original human messages in
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f31135e5-0253-441f-8140-bdd86e8940bc.jsonl`:

- Line 742 (2026-11-02T02:57Z, queued mid-turn, unprompted): "Again, I would prefer we figure out
  a way to do this that doesn't require tmux scraping and generalises to support the any to any"
- Line 826, record `8cb99ed1-678a-4f0a-b426-ea1eb15df739` (03:05Z), after the report that driving
  Claude from Codex was unproven: "It is fine if we have one adapter per client that any client can
  engage with. And the task here is just to make Claude to codex less shit. Go do proper research.
  Is 166 inside the 14 day age gate?"
- Line 918, record `fc7aab13-9951-489c-9fc3-979eeb072ebe` (03:08Z), after the report that 0.166.0 is
  inside the gate and the daemon updates itself past it: "I mean, id this is their recommended line,
  we can put in an exception. No point in not designing for this"
- Line 1126 (04:09Z, queued mid-turn), answering "Shall I go ahead with this on a scratch session?"
  after the report that a send goes to the server and nothing is typed into the pane, and that
  clearing needs a new session: "then we don't care about typing protection. and compact is fine, if
  we want a clear, we just make a new session as you say. Just make it a single-line so we can start
  --new or what have you. Yes, make the experiment."

Exact raw-record resolver:

```sh
sed -n '742p;826p;918p;1126p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/f31135e5-0253-441f-8140-bdd86e8940bc.jsonl
```

## Decision

1. Each client gets one adapter, and any client may use it. This work builds the path from Claude to
   Codex only.
2. Control does not depend on reading the Codex screen.
3. A send that does not type into the pane needs no check for what the human has half-typed. The
   ruling rests on that premise, which the experiment must confirm.
4. Compacting stays. A clear is a new session, started by a single command.
5. If the app-server line is the vendor's recommended one, the age gate gets a named exception rather
   than shaping the design. The condition is unsettled: the vendor recommends app-server for deep
   integrations and also says it is experimental and not supported for production. No exception has
   been applied.
6. Scratch Codex sessions are authorised for this experiment. This does not answer the wider parked
   question about scratch sessions for Deliver.

## Consequences

- If the experiment shows a send can disturb a draft, item 3's premise fails and returns to Brian.
- The refuse-on-a-non-empty-composer guard stays in the scraping route while that route exists.
