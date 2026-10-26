# Supervision infrastructure — work queue

State lives here, not in ADRs or `CLAUDE.md`. Rulings: ADRs 0035 to 0042. Specification:
`docs/design-plans/2026-10-24-claude-supervision-spec.md`. Worker: Sol (Codex, xhigh) in
pane `%237`, one dispatch at a time; the supervisor verifies each before the next.

## Awaiting Brian

- Commit-skill durable-record checks (prompts 13 and 15, ADR 0042): verified, ready for
  acceptance and commit. Needs: the citation exemption ruling for the notes directory,
  then the dispatcher pin for `check_durable_records.py`.

- Citation repairs (prompt 17, ADRs 0041 and 0042): verified 2026-10-25, ready for
  acceptance and commit. Sixteen historical documents landed under
  `docs/design-plans/2026-10-09-cross-provider-messaging/`; ADRs 0007, 0009, 0011 and the
  critical-review note repointed. Default-mode checker is clean apart from `.notes`.
  Committing the landed documents is itself blocked: the checker fails on the historical
  documents' own stale citations once they are staged (see "Open with Brian").

- Hook launcher migration (prompt 14, ADR 0038): verified, ready for acceptance and
  commit. Seven plugins bumped. Pre-existing lint debt left in place: ty flags
  `gh-fork-guard.py:147` (`str | None` `.lower()`), complexipy 16 in two hook functions;
  both identical at HEAD, tracked under the lint-baseline tickets.

## In progress

- Prompt 18 (Sol, fresh session): tidy the register's citations into the notes directory
  under ADR 0043 (ruled 2026-10-26, no exemption): move the messaging critical review into
  `docs/design-plans/2026-10-09-cross-provider-messaging/`, repoint ADR 0028, reword ADR
  0015 and the convention statements in ADRs 0005/0008/0010, diagnose the checker's
  misclassification of a tracked `experiments/` path in the open-questions file. After
  verification the commit gate passes and the concern-split commits can go, which also
  unblocks the other session's pull of the three incoming origin commits (six bookkeeping
  files overlap: CHANGELOG, CLAUDE.md, marketplace, ADR index, pyproject, one test).
- ADR 0034 move unfinished: the private permission-queue repository has no commits and the
  live tool runs from `experiments/permission-queue/` here (39 tracked files, 12 tests).
  ADR 0040 stands; finishing that move, or an explicit ruling that the daemon stays here
  for now, is a prerequisite before any implementation phase. Raised to Brian 2026-10-26.

- Stage-2 design (prompt 16) delivered as a Draft at
  `docs/design-plans/2026-10-24-supervision-infrastructure.md`. Opus review: NEEDS
  REVISION (1 Critical, 12 Important, 9 Minor); see the Opus review staged in the exchange
  directory on 2026-10-25 with the supervisor's verification. Halted on C1 for Brian:
  whether the direct, service-less Codex driving path stays supported (recommended), so
  the service is an optional layer and the colleague's plugin works without it. Prompt 18
  (design corrections to Sol) is written after that answer.
- claude-sync: Brian asked for a fresh push when possible (2026-10-24). Blocked. The push
  exports a snapshot of the approver checkout (`~/people/Brian/approver`) and the
  exporter (`~/.claude/bin/claude-sync-projects.py`) refuses while that checkout has
  uncommitted changes. Observed 2026-10-25: 44 modified and 13 untracked files there,
  about 1,700 lines, the in-progress resource-budget work
  (`docs/implementation-plans/2026-10-23-resource-budget/`) from another session. That
  work is not this session's to commit; the push waits until its own session commits it,
  or Brian rules otherwise. Then `~/.claude/bin/claude-sync push` after reading
  `~/.claude-sync/CLAUDE.md`.

## Open with Brian

- Pin for `plugins/denubis-git-commit/scripts/check_durable_records.py` (digest changes
  with prompt 19's fixes; re-read before pinning).
- The word "commit": everything below is verified and the gate passes; the concern-split
  commits wait for Brian to say so.
- Acceptance of: commit-skill checker (prompts 13/15), hook migration (prompt 14).
- claude-sync: whether the approver resource-budget work gets committed so the push can
  proceed (see above).
- ADR 0011 property 7: whether a same-family supervisor may hold an approval mandate.
- Scratch-session authorisation for live captures.
- Effort for any `gpt-6-astra` supervisor launch (ADR 0006).

## Queued, in order

1. Consume the Opus review of the stage-2 design; return verified defects to Sol as a
   correction prompt; present the design to Brian for acceptance.
2. Implementation phases P0 to P6 from the accepted design. P0 (package extraction,
   `install-codex-hooks.py` migration, 3.12-floor retirement) needs no daemon. Live
   captures need Brian's scratch-session authorisation.
