# ADR 0037 — The Claude driver is a sibling `claude_supervisor.py` over shared plugin tooling; supervision works for any harness pair and resolves supervisees by binding, not by same-window uniqueness

**Status:** Accepted (2026-10-24). Resolves design decision D1 of the stage-1
Codex-supervises-Claude design; applies ADR 0014's binding-based resolution to both
drivers. Amends ADR 0011 in one respect: the tmux pane drivers may now serve same-family
pairs (Claude supervising Claude, Codex supervising Codex). ADR 0011's property 7, that
no same-family supervisor holds an approval mandate, is not touched by this ruling.

## Authority evidence

Original human messages in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 773, `user` record `909685dd-48b6-4ed4-9dde-0bbc1cce3b62` (2026-10-23T20:40:25Z,
  2026-10-24 07:40 Australia/Sydney), the opening of a message Brian interrupted and then
  re-sent in full: "no, don't engage with the charsheet at all, this is.. just context
  elsewise."
- Line 781, `queue-operation` (`enqueue`) record (2026-10-23T20:41:24Z), the full message:
  "no, don't engage with the charsheet at all, this is.. just context elsewise. and yeah,
  we can just do a claude_supervisor.py. Also given that things are going to reach for
  it, we need to make sure both supervisors can do same harness to same harness calls.
  the tmux blocker for one and only one supervisor to runner... isn't holding well."
- Line 813, `user` record `86a939f4-f90b-4765-9970-88ed4faf047b` (2026-10-23T20:42:39Z),
  sent after a `[Request interrupted by user]` (line 807 holds the interrupted shorter
  form): "what? No, it's fine if we hav... right, yes. though also please *generalise*
  now? amke sure we've gut ruff, ty, complexipy, and if there are common functions, don't
  duplicate them? It's fine if we make this part of common tooling for this plugin...
  infra... somehow... I don't know."
- Line 859, `queue-operation` (`enqueue`) record (2026-10-23T20:44:27Z), sent mid-turn:
  "making this a proper package seems like the direction we're heading in. so refactor in
  that direction?"

Exact raw-record resolver:

```sh
sed -n '773p;781p;813p;859p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

The question they answered, asked by the supervising session: layout decision D1 of the
stage-1 Codex-supervises-Claude design (Sol's draft against
`docs/design-plans/2026-10-24-claude-supervision-spec.md`), with the recommendation
"a new Claude package beside a thin sibling entry point, leaving `codex_supervisor.py`
untouched. Do you want that, or the single sibling script that mirrors the Codex
driver's shape?"

## Context

The stage-1 design offered three layouts for the Claude driver: a sibling script that
duplicates small plumbing, a new package beside a thin entry point, or shared modules
extracted from `codex_supervisor.py`. It also inherited the Codex driver's "exactly one
agent pane in the supervisor's window" discovery rule, which ADR 0014 had already
replaced in principle with binding-based resolution. Brian reports that rule "isn't
holding well" in practice, and that the drivers will be reached for in same-harness pairs
(Claude supervising Claude, Codex supervising Codex), where the supervisor's own pane is
in the same window as its supervisee.

## Decision

1. The supervision tooling becomes a proper Python package inside the plugin. The two
   drivers are thin sibling entry points over it:
   `plugins/denubis-external-agents/scripts/codex_supervisor.py` (existing name, kept)
   and its planned sibling, `claude_supervisor.py` (new). The refactor of the
   existing driver moves in that direction rather than stopping at an extracted module.
2. Functions common to both drivers live once, in the package, not duplicated. The
   package and both entry points meet the repository's ruff, ty and complexipy gates.
3. Both drivers support any harness pair, including same-harness supervision. The
   supervisor's own pane is always excluded. Supervisees are resolved by recorded binding
   confirmed live (ADR 0014), not by "the only agent pane in this window".
4. charsheet is context only (ADR 0036) and is not engaged by this work.

## Consequences

- `codex_supervisor.py` changes: its discovery drops the uniqueness rule for binding-based
  resolution, and shared functions move out of it. Its behaviour for existing callers is
  preserved and its existing tests stay green or are amended with the reason recorded.
- The permission-queue consumer that path-loads `codex_supervisor.py` as a single
  standard-library file (open ticket under "permission-queue move (ADR 0034)") is affected
  by extraction. The design must state how that consumer keeps working or what migration
  it needs; this does not answer that ticket.
- Supervisor-pane exclusion needs process identity, not command name, because a Claude
  supervisor's pane reports `bash` as its current command (`tmux-send-guard`).
- The `supervising-codex` skill's "same-window uniqueness rule" prose becomes stale and is
  revised with the implementation.
