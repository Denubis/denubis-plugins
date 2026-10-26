# ADR 0043 — The notes directory holds nothing durable that other machines rely on; durable content lives in `docs/`, and a register citation of a path in the notes directory is a defect

**Status:** Accepted (2026-10-26). Applies ADR 0042 to the one case it left open. Amends
ADR 0005 and ADR 0028 as stated under Consequences.

## Authority evidence

Original human message in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 3901, `user` record `5427bd64-7ed8-4e34-8e29-627bf5d9ce89` (2026-10-25T23:20:34Z,
  2026-10-26 10:20 Australia/Sydney), answering whether citations of paths in the notes
  directory should be exempt from the no-gitignored-citation rule:
  ".notes shouldn't have anything
  durable that multiple machines would rely upon, that's what docs are for!"

Exact raw-record resolver:

```sh
sed -n '3901p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

## Context

ADR 0042 ruled that no durable record cites a gitignored object and put the check into the
commit skill. The notes directory is ignored by Brian's global gitignore, so the first
run of that check flagged nine register citations of paths in the notes directory, and
the question whether it deserved an exemption was asked three times across 2026-10-24
and 2026-10-25.

The citations fall into three kinds. ADR 0028 cites a 288-line review
(`project_cross-provider-messaging-critical-review`) as the evidence for a design claim:
durable content, living only on one machine. ADR 0015 cites a Local Mail message file as a
bug report: evidence that no other checkout can open. ADRs 0005, 0008 and 0010 name the
open-questions queue's path as the convention they establish, not as evidence.

## Decision

1. The notes directory holds nothing durable that another machine would rely on.
   Reviews, design evidence, references and anything a decision rests on live under
   `docs/`, in the
   repository, where every clone has them. The notes directory keeps per-machine memory:
   the open-questions queue, feedback, local preferences and working context.
2. No exemption. A durable record that cites a path in the notes directory as evidence
   is a defect under ADR 0042, and the check keeps flagging it. The repair is to move the
   content into `docs/`
   and cite it there, or to reword the claim so it rests on evidence a clone can open.
3. A record that establishes where the open-questions queue lives states that as a
   convention, written so the check does not read it as a citation of a file that must
   exist; the queue itself remains per-machine and gitignored under ADR 0005 and 0008.

## Consequences

- The messaging critical review moves from the notes directory into `docs/` beside the
  landed 2026-10-09 messaging documents it reviews, and ADR 0028 cites it there.
- ADR 0015's bug-report citation is reworded to carry the claim without the per-machine
  file path, or to cite a durable copy.
- ADR 0005's statement that the notes directory is "durable passive memory" is narrowed
  by this decision: durable in the sense of surviving sessions on one machine, never the
  home of content other machines rely on.
- The commit-skill check's `IGNORED` classification for paths in the notes directory is
  the intended behaviour and needs no exemption switch.
