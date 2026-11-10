# 2026-11-10 — History failure warns instead of blocking questions

**Status:** Accepted (2026-11-10).

## Authority evidence

Original human response-item messages in Codex session
01a1c3f1-d508-7003-a7e5-a499d9825714, native source
/home/brian/.codex/sessions/2026/11/10/rollout-2026-11-10T16-32-48-01a1c3f1-d508-7003-a7e5-a499d9825714.jsonl:

- Line 972, ordinal 971, message
  msg_01a1c41f-d73c-7bc3-b4f7-a7e5b1b1e453, timestamp
  2026-11-10T06:23:03.484Z: "to me, the escape hatch is that search-chats shouldn't be an absolute blocker"
- Line 976, ordinal 975, message
  msg_01a1c420-2db0-7ea2-b1d7-1f7cc4e4a654, timestamp
  2026-11-10T06:23:25.616Z: "yes, failed history is just a warn"

## Context

The history reviewer returned unavailable after successful searches with partial
coverage, and the question hook denied presentation. Repairing history then
needed a question which the same dependency held back.

## Decision

Failed or incomplete history lookup produces a visible warning and permits an
otherwise-clear question. This applies generally, rather than only to questions
about repairing history. Clarity remains a separate prerequisite, and verified
existing human answers are reused instead of asking again.

A warning permits asking only. It does not authorize the requested operation,
claim unread history was searched, or establish that no historical answer exists.
Malformed question/checker data and unrelated checker or cleanup failures remain
separate from the history-lookup warning.

## Consequences

The earlier QZ1 ticket's history-coverage gate for queue and persistence tests is
settled by this general ruling. Its six excluded files remain unread evidence,
rather than becoming a claim of complete coverage. Question Zone 0.2.2 carries
the warning in both Claude's queue and Codex's native question path.
