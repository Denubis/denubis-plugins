# 2026-11-18 — The question check does not re-index a chat index under five minutes old

**Status:** Accepted (2026-11-18).

## Authority evidence

Original human messages in Claude Code session
df736ff6-7aff-45a9-9d02-b9a279a93026 (project
`cc-search-chats-plugin-python`), resolvable with `cc-search-chats resolve`:

- `ccchat:v1:claude:df736ff6-7aff-45a9-9d02-b9a279a93026:uuid:c1fe1db2-4b8f-4865-8620-851f9e54228d`,
  2026-11-18T03:57:45Z: "yes, that's why I said there's a 5minute debounce"
- `ccchat:v1:claude:df736ff6-7aff-45a9-9d02-b9a279a93026:uuid:7a4f4b34-5125-46b0-8153-a8cb8f04b66c`,
  2026-11-18T04:12:12Z, answering "May I have a worker change the
  question-screening plugin, in your plugins repository, so that it skips
  re-indexing when the chat index is less than five minutes old?": "yes"
- `ccchat:v1:claude:df736ff6-7aff-45a9-9d02-b9a279a93026:uuid:dfa599bf-3424-46c7-ac26-484d0b5afaa4`,
  2026-11-18T05:54:24Z, answering "When the question check skips re-indexing
  because the chat index is under five minutes old, should the question go
  through with no warning?": "um... argh. so the common thing would be that I
  answer it within 5 minutes if I see it scrolling past, but I don't need to
  see a warning"

## Context

The question check brought the chat index up to date whenever
`cc-search-chats index --status --json` reported changes not yet indexed. Live
sessions write continuously, so nearly every question started an index run,
which loads the embedding model onto the graphics card while other sessions'
semantic searches need it.

## Decision

When the status reports `index_state.age_ms` below 300000, the check searches
the index as it is and runs no `index`. An unknown age is never treated as
recent. A search skipped into this way shows no history warning and does not
hold the question.

## Consequences

Something the person typed after the index was made, within those five
minutes, may be unsearched by the check, and nothing says so. The person
accepted that in the third message above. The 2026-11-10 ruling still governs
failed commands and partial coverage. Question Zone 0.2.4 carries the change.
