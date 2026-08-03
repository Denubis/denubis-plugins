# Local Mail Design

**GitHub Issue:** None

## Summary
<!-- TO BE GENERATED after body is written -->

## Definition of Done

- A machine-local, explicitly opted-in bridge for Claude and Codex, exposed through plugins and one CLI, with no daemon or network transport.
- Canonical Markdown message files, atomic delivery, and a rebuildable SQLite WAL index for routing and per-session read state. Session identity survives clear, compact, and resume; only a fresh launch creates a new identity.
- Direct, path, project, named-list, and everyone addressing snapshots currently subscribed sessions. The MVP includes basic threads, text-only messages, compact start/prompt notifications, silent empty checks, and the conditional stop-time communication prompt.
- A basic admin TUI can inspect sessions, subscriptions, queued/read mail, and threads; compose/interject; manage lists; and correct or remove messages. Attachments, future scheduling, human receipts, multi-host operation, audit-history implementation, and peer-review/k-agent integration are deferred.

## Acceptance Criteria
<!-- TO BE GENERATED and validated before glossary -->

## Glossary
<!-- TO BE GENERATED after body is written -->
