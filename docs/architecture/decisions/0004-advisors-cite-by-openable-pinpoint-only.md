# ADR 0004 — Advisors cite by openable pinpoint and callers validate the lookup

**Status:** Accepted (2026-08-09)

## Authority evidence

- Human invocation:
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/a711c799-c718-49e9-84a6-3e7560f803ad.jsonl:2243`
- Exact resolver:
  `cc-search-chats context db51c3ba-d6db-449e-874a-7259a377bec7 --json`
- Positive resolution observed: schema version 1, target role `user`, exact UUID
  `db51c3ba-d6db-449e-874a-7259a377bec7`.

The invocation is authority for the citation form. The resolver output supplies the
human message; this ADR does not reproduce it.

## Decision

An advisor returns an openable location, why that location bears on the task, and whether
the advisor believes it still applies. It does not quote or paraphrase the source.

An openable location is a full message UUID with session identity, `path:line`, or an
equally exact source coordinate. A bare filename or abbreviated identifier is not an
openable pinpoint.

Before acting on a finding, the caller opens the pinpoint and reads the source. Before
classifying a non-opening pinpoint as invalid, the caller must:

1. use the complete identifier;
2. account for case and source scope;
3. run a positive control through the same lookup path; and
4. report lookup failure as a property of the lookup until those controls pass.

## Consequences

- Advisory output directs the caller to primary material without substituting model prose
  for it.
- A resolvable but irrelevant pinpoint still requires human or agent judgment after the
  source is opened.
- A failed lookup cannot support an accusation or dependent decision unless the lookup's
  positive control succeeds.
- Line-based pinpoints can drift. The caller repairs the locator or treats the dependent
  finding as unresolved.
- This decision supplies a procedure, not a compliance claim. No test can prove that a
  model advisor follows its brief on every invocation.

## Verification reference

`cc-search-chats context 1ceeda30-fb5e-443d-a6a2-15c8e54e02d3 --json` is the positive
fixture for full-UUID resolution used by the current advisor/caller contract.
