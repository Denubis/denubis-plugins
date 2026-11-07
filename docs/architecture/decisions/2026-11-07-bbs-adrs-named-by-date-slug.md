# ADR 2026-11-07-bbs-adrs-named-by-date-slug — A new decision record is named by its date, the ruler's initials and a short slug; existing numbers stay

**Status:** Accepted (2026-11-07). Applies in every repository that follows Brian's global
instructions. The first record in this register under the new form.

## Authority evidence

Original human messages in session `d280d2b3-8069-40c1-8f99-fcd0694017d7`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl`):

- Line 2708, a `queue-operation` record (2026-11-07T02:49:10Z, 13:49 Australia/Sydney), typed
  while the supervisor was recording the ADR 0043 amendment: "and I think we need namespaces
  on ADRs, because even on the same machine, there's adr fighting. and just having a simple
  namespace three-character thing is a way to reduce this friction?"
- Line 2783, `user` record `3ffcd9c1-3293-4a23-ab53-a99b91b366b3` (2026-11-07T03:25:59Z),
  after the supervisor proposed one prefix per line of work: "um, ok, what's going on? but
  yeah, sure, the only thing is that prefixses need to be unique. I... hrm... slugs means
  it's easier to search so what, date and no more than 5 words? and author initials?"
- Line 2793, `user` record `48b44be3-5572-4afb-9939-e18a4f96f3d8` (2026-11-07T03:34:29Z),
  asked whether the rule covers every repository or this one first: "every repo, thouugh we
  will need to gradually change"
- Line 2819, `user` record `fb25ede5-9ec7-4fee-87f5-2d269357c240` (2026-11-07T03:36:45Z):
  "yes", approving the supervisor's five-step plan. That plan read "author initials" as the
  initials of the person whose ruling the record holds; the reading is the supervisor's,
  approved with the plan, not Brian's own wording.

```sh
sed -n '2708p;2783p;2793p;2819p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d280d2b3-8069-40c1-8f99-fcd0694017d7.jsonl
```

## Context

Records were numbered by taking the next free number. Work on a branch takes that number
from the branch's own base, so two branches on the same machine can take the same one. On
2026-11-06 `main` took 0047 to 0052 while the `supervision-infrastructure` branch, based on
an older `main`, wrote its own ADR 0048; after a merge, "ADR 0048" would name two decisions.
A per-branch prefix would need a list of prefixes kept unique by hand. A name built from the
date, the ruler's initials and a short slug needs no allocation, rarely collides, sorts by
date and is searchable by its words.

## Decision

1. A new decision record is a file named `YYYY-MM-DD-<initials>-<slug>.md`: the date of the
   ruling, the lowercase initials of the person whose ruling it records, and a kebab-case
   slug of at most five words. It is cited by that name, as this record is.
2. If the name already exists in the register, the slug changes; the date and initials
   stay.
3. Existing numbered records keep their numbers and file names. No repository renames its
   register, and citations of numbered records stay valid.
4. Adoption is gradual: each repository uses the new form for its next record, and its
   index lists both forms. A one-file register titles a new entry with the same name.
5. A branch's numbered record that collides with one on `main` takes a dated name when the
   branch merges.

## Consequences

- Brian's global Claude and Codex instructions state the naming rule next to the default
  register.
- `recording-project-notes` states it where it describes decision records (project-notes
  0.3.2). `supervising-codex` defers the record format to that skill and is unchanged.
- The `supervision-infrastructure` branch's ADR 0048 takes a dated name at its merge.
- The commit checker selects registers by directory, not by file name, so it reads dated
  records as it reads numbered ones.
