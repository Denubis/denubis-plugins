# Architectural Decision Records

This directory holds short, dated records of architectural decisions whose
rationale would otherwise be lost. Format is loosely MADR (Markdown
Architectural Decision Records): each file has a status, context, decision,
and consequences section. One ADR per decision.

## Decisions

- [0006 — Astra and Fable require explicit model and effort](0006-astra-fable-require-explicit-model-and-effort.md)
- [0007 — The Codex supervisor reads session files; hooks cannot confirm a clear](0007-supervisor-reads-codex-session-files.md),
  with frozen evidence in [`0007-evidence-2026-09-28/`](0007-evidence-2026-09-28/)
- [0008 — The open-questions file holds open questions only](0008-open-questions-hold-open-questions-only.md)
  (amends 0005)
- [0009 — The Codex monitor announces once, and an idle pane gets no monitor](0009-monitor-announces-once-and-idle-panes-are-unwatched.md)
- [0010 — A spawned Codex has no queued-question widget, and `--spawn` takes `--cwd`](0010-spawned-codex-has-no-question-widget-and-takes-cwd.md)
- [0011 — Same-family sessions use their native infrastructure; the messaging system is cross-provider](0011-same-family-sessions-use-native-infrastructure.md)
- [0012 — Approvals are answerable from the side-monitor surface and from the pane; first answer wins](0012-approvals-answerable-from-the-surface-and-the-pane.md)
- [0013 — A driving supervisor answers only what its own task narrowly needs; anything with other implications pauses and escalates](0013-a-driving-supervisor-answers-only-what-its-task-narrowly-needs.md)
- [0014 — One supervisor may drive many supervisees, and all of them sit in the supervisor's own tmux window](0014-one-supervisor-many-supervisees-all-in-its-own-tmux-window.md)
- [0015 — Unacknowledged mail climbs an escalation ladder ending in an interrupt and Brian; a sender may withdraw a mooted message, leaving a tombstone](0015-unacknowledged-mail-climbs-an-escalation-ladder-and-withdrawals-leave-tombstones.md)
- [0016 — The escalation ladder's clocks run only while the supervisee is idle and unblocked; a block is listed, not nudged](0016-ladder-clocks-run-only-while-the-supervisee-is-unblocked.md)
- [0017 — Escalation ladder timing defaults, accepted as revisable](0017-ladder-timing-defaults.md)
- [0018 — Every session gets a ping that it has mail through its vendor's own channel, and pulls the body from the record; Claude-to-Claude mail goes through the record too](0018-every-session-gets-a-ping-through-its-own-channel-and-pulls-mail-from-the-record.md)
  (qualifies 0011)
- [0019 — Identity defaults: sub-agents send as their parent, a Codex pane keeps its address across clear by a hook binding, and a model-run whoami acknowledges identity](0019-identity-defaults-subagents-send-as-parent-codex-pane-binds-by-hook-whoami-acknowledges.md)
- [0020 — The human surface runs outside the main byobu session, is reachable from anywhere over SSH or Tailscale, is launched from a terminal on this machine, and is whatever is durable and simple](0020-the-human-surface-runs-outside-byobu-reachable-over-ssh-durable-simple-tailscale-only.md)
- [0021 — The ladder runs whenever the supervisee is unblocked, busy or idle; an agent that keeps working past two nudges is interrupted; a blocked supervisor is Brian's item](0021-ladder-runs-while-unblocked-busy-or-idle-and-a-blocked-supervisor-is-brians-item.md)
  (amends 0016)
- [0022 — A supervisor's mandate carries expiry and a directory root as hard stops, no decision count; the screen-reading `--approve` keypress is soft-retired pending the hooks](0022-mandate-rails-are-expiry-and-directory-only-and-the-blind-approve-is-soft-retired.md)
- [0023 — A cited agent-to-agent message resolves by transcript locator, like every other citation; the record may prune a cited thread](0023-a-cited-agent-message-resolves-by-transcript-locator-and-the-record-may-prune-it.md)
  (supersedes property 10 of the 2026-08-09 design for the Postgres record)
- [0024 — Agents on this box act with Brian's authority; the record's decision table is not a security boundary against them, and no Postgres authentication change is made](0024-agents-run-with-brians-authority-and-the-decision-table-is-not-a-security-boundary.md)
- [0025 — Identity follows the pane: anything with its own pane is itself; a paneless sub-agent is not a messaging participant, and an attempt is an anomaly](0025-identity-follows-the-pane-and-paneless-sub-agents-do-not-message.md)
  (amends 0019, withdrawing clause (a); closes M14)
- [0026 — The record lives in its own database, `agent_record`, with owner, app, and reader roles; `local_mail` is left untouched](0026-the-record-lives-in-its-own-database-agent-record-with-three-roles.md)
- [0027 — The default Codex model is whatever the latest Sol-class release is, at xhigh, read from the catalogue rather than pinned](0027-the-default-codex-model-is-the-latest-sol-class-release-at-xhigh.md)
- [0028 — A pane session's "You should know" offer is mail from that pane to its supervising session; kept, not suppressed, with the sending pane identified](0028-a-pane-sessions-you-should-know-offer-is-mail-to-its-supervisor.md)
  (applies 0018 and 0025)
- [0029 — Zotero writes go through Zotero 10's stock local API, delete means trash, and zotero-api-plus is kept only for what stock cannot do](0029-zotero-writes-use-the-stock-local-api-and-delete-means-trash.md)
- [0030 — Start with a permission experiment; later messaging is not precluded](0030-permission-queue-starts-with-an-experiment-and-does-not-preclude-later-messaging.md)
- [0031 — `ruff format` covers Markdown code blocks; vendored upstream files are excluded](0031-ruff-formats-markdown-code-blocks-except-vendored-files.md)
- [0032 — PEP 723 scripts and workspace members carry the root lint standards in their own configuration](0032-pep-723-scripts-and-workspace-members-carry-the-root-lint-standards.md)
- [0033 — The Zotero local-API transport stays on httpx; pyzotero is not adopted](0033-the-zotero-transport-stays-on-httpx-pyzotero-is-not-adopted.md)
- [0034 — permission-queue leaves the plugins repository for its own private repository](0034-permission-queue-leaves-the-plugins-repository-for-its-own-private-repository.md)
  (supersedes the placement in 0030)
- [0035 — ADR 0013 stands for a Claude worker: the driving Codex supervisor may answer obviously safe, narrow dialogs; everything else is Brian's](0035-adr-0013-stands-for-a-claude-worker-obviously-safe-dialogs-may-be-answered.md)
  (applies 0013 and 0022)
- [0036 — The Claude supervision mode is project-neutral; charsheet is its first consuming project and charsheet's backlog is not plugin work](0036-the-claude-supervision-mode-is-project-neutral-and-charsheets-backlog-is-not-its-workload.md)
- [0037 — The Claude driver is a sibling `claude_supervisor.py` over shared plugin tooling; supervision works for any harness pair and resolves supervisees by binding](0037-claude-driver-is-a-sibling-script-over-shared-tooling-and-supervision-is-binding-based-for-any-harness-pair.md)
  (applies 0014; amends 0011 for pane drivers; resolves design decision D1)
- [0038 — Hooks run under `uv run --script` at the repository Python floor; the 3.9 hook carve-out is retired](0038-hooks-run-under-uv-run-script-at-the-repository-python-floor.md)
- [0039 — Supervision is per instance, on Brian's command, over named panes in the supervisor's own window; nothing persists a binding and no monitor re-arms](0039-supervision-is-per-instance-on-brians-command-over-named-panes-in-the-supervisors-window-and-nothing-re-arms.md)
  (withdraws design decision D3; applies 0009, 0014 and 0018)
- [0040 — The shared supervision library is an installable package in this plugin; the daemon lives in the private repository and depends on it, never the reverse](0040-the-shared-supervision-library-is-an-installable-package-in-this-plugin-and-the-daemon-lives-in-the-private-repository.md)
  (completes 0039; extends 0037; closes the 0034 classifier ticket)
- [0041 — The prompt exchange is the Record, not a gitignored directory; telemetry comes from hooks; AskUserQuestion is denied and a worker's question lives in open-questions until a human answer moves it out](0041-the-prompt-exchange-is-the-record-not-a-directory-telemetry-comes-from-hooks-and-askuserquestion-is-denied-with-questions-living-in-open-questions.md)
  (resolves design decisions D2, D4 and D5; applies 0008 and 0039)
- [0042 — No durable record cites a gitignored object; the check for that, and proper note-taking, belong to the commit skill and run in every repository](0042-citation-and-memory-checks-belong-to-the-commit-skill-and-run-in-every-repository.md)
  (applies 0008 and 0041; extends `denubis-git-commit:commit`)
- [0043 — The notes directory holds nothing durable that other machines rely on; durable content lives in `docs/`, and a register citation of a path in the notes directory is a defect](0043-notes-hold-nothing-durable-that-other-machines-rely-on-durable-content-lives-in-docs.md)
  (applies 0042; amends 0005 and 0028)
- [0044 — The ticket file stays in the notes directory: an open question is situational, and its answer moves to a record about its subject](0044-the-ticket-file-stays-in-the-notes-directory-because-open-questions-are-situational-and-answers-move-to-records-about-their-subject.md)
  (confirms 0005 and 0008; bounds 0043)

## Status lifecycle

- **Proposed** — decision drafted during implementation; awaits acceptance
  in the post-implementation review.
- **Accepted** — decision has been used and the post-acceptance pass
  promoted it from Proposed.
- **Superseded by ADR-NNNN** — the replacement records the current decision. Retire the
  superseded document to Git or an explicit archive rather than layering corrections
  into a living decision.

## Numbering

Four-digit zero-padded, in the order ADRs were authored. Numbers are never reused. A gap
means that Git or an explicit archive holds a retired decision; it is not an invitation
to reconstruct the old argument in the living set.

## Decision-source integrity

Every accepted ADR identifies what selected the decision. When a human instruction or
approval selected it, include the raw source path and line plus an exact resolver
invocation that opens the original human message. Do not substitute a quotation,
paraphrase, model summary, or bare session identifier. When current technical evidence
determines the decision, label and cite that evidence without inventing human approval.

A missing, stale, ambiguous, or wrong-role source is an integrity defect. Repair it when
found or return the ADR to Proposed until a focused human invocation resolves it.

## When to write an ADR vs. a constraint row

- **Constraint row** (in `../constraints.md`): an enforced invariant the
  codebase tests for. Lives close to verification evidence.
- **ADR** (here): a decision whose rationale needs preserving across time
  — what was considered, what was chosen, what consequences followed. ADRs
  may pair with a constraint row that locks the same decision in code; the
  ADR captures the *why* and the constraint row captures the *how to verify*.
