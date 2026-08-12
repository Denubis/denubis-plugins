# Instruction control system simplification

**Status:** Current design. No simplification change is deployed yet.

## Purpose

Reduce repeated corrective interaction by giving each instruction, prohibition,
procedure, memory, decision, and historical account one owner. A mechanism may claim
only what its observable boundary proves. Chat narration and model-authored certificates
do not bind or release work.

This work includes the global Codex `AGENTS.md`, global and project `CLAUDE.md`, global
Codex history retention, enabled plugins and hooks, `.notes/`, architecture and decision
records, the completed implementation-plan rewrite branch, and the cross-vendor
chat-search interface used to resolve human authority.

## Authority evidence

The exact authority registry is
`deployment/instruction-control/foa4008439/candidate-manifest.json`. Each record binds a
raw JSONL path, one-based line, provider format, and SHA-256 of the exact human text.
Each action names its supporting records; every candidate, plugin release, retirement,
and settings transition names the action it consumes. Check the registry and its sources
with:

```fish
uv run python deployment/instruction-control/verify_candidate.py source deployment/instruction-control/foa4008439/candidate-manifest.json --repo-root .
```

For manual review of a Codex record before provider-qualified exact resolution ships,
substitute its manifest line and path into:

```fish
jq -s -e --argjson line LINE '[.[($line - 1)] | select(.type == "response_item" and .payload.type == "message" and .payload.role == "user") | .payload.content[] | select(.type == "input_text") | .text] | select(length == 1 and (.[0] | length > 0)) | .[0]' SOURCE.jsonl
```

The main-register cleanup is bound as `NOTES01` at line `11105` of the Codex source
named in the manifest. It broadened the already approved two-note cleanup to the other
project notes before the register-wide inventory and disposition work began.

Claude records that already have exact search locators also retain those invocations at
their point of use. The project uv records are:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/64611e50-8793-451a-82ca-0b4fc5264e02.jsonl:58`; resolve with
  `cc-search-chats context e3d35d8d-bfe1-4677-adc1-e92ef3ad6e9d --json`.
- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/64611e50-8793-451a-82ca-0b4fc5264e02.jsonl:69`; resolve with
  `cc-search-chats context 8fc827c0-b9d3-4e7d-8f92-268a7743e930 --json`.

The implementation-planning decisions resolve at:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-impl-plan-decision-discipline/1bbd42e5-3ec5-4deb-8002-334332edffaa.jsonl:508`; resolve with
  `cc-search-chats context 5e877b26-6972-4f16-b8f7-7c83fb55e10a --json`;
- the same source at line `514`; resolve with
  `cc-search-chats context a403f0a6-be0f-4d06-998a-5b2e2cc57345 --json`;
- the same source at line `542`; resolve with
  `cc-search-chats context bc2f9ded-c5a8-4ef3-a0f9-d7e13865ddfe --json`; and
- the same source at line `556`; resolve with
  `cc-search-chats context 3420ba58-fdbc-46c9-9523-b9b18fbee208 --json`.

The conditional DFD applicability and boundary-documentation decision is bound as
`DFD01` at line `14052` of the Codex source named in the manifest. Until
provider-qualified exact resolution supports this record, use the manifest's manual
Codex resolver.

The UAT coverage decisions resolve at:

- `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/ffb5f905-06db-4e41-8c36-e5ca981120e2.jsonl:294`; resolve with
  `cc-search-chats context 55f67edb-72e8-4d2f-a8c4-63c6e08a0338 --json`; and
- the same source at line `313`; resolve with
  `cc-search-chats context 581a12b2-60ad-4ddc-b10e-143e8554dd6a --json`.

## Current system map

| Surface | Current state | Intended owner |
|---|---|---|
| Global Codex `AGENTS.md` | Continuous rules and detailed search/reference procedures are mixed; a source candidate now adds recursive request entry, memory/decision inspection, failure anticipation, and local/remote environment boundaries | Continuous cross-project Codex invariants; detailed procedures remain in skills and project rules |
| Codex history retention | Live `/home/brian/.codex/config.toml` now explicitly sets `history.persistence = "save-all"` and leaves `history.max_bytes` unset; current Codex documentation exposes no age-expiry key | Parsed live configuration checked by the candidate verifier; raw rollouts remain the authority store |
| Global `CLAUDE.md` | 21,369 bytes; continuous rules, procedures, historical explanations, style, search reference, settings sync, and project-memory rules are mixed | Continuous cross-project invariants only |
| Project `CLAUDE.md` | Project conventions plus duplicates of global reviewer and halting rules | Project boundaries, current conventions, and finding aids |
| `denubis-hook-skill-reinforcement` | Source retired; installed 1.2.0 remains enabled until the deployment slice | Remove from live settings and cache only after source verification |
| `denubis-hook-claudemd-reminder` | Source retired; installed 1.1.4 remains enabled until the deployment slice | Commit preparation owns the documentation-freshness check |
| Project notes | Source provides `denubis-project-notes`, but the core deployment does not install it while cross-vendor exact search is unfinished | Global task-entry inventory and raw-source resolution replace the advisor; the skill is a later deployment slice |
| `denubis-plan-and-execute` SessionStart context | Source removes generic context while retaining the live-marker side effect; two distinct planning gates remain in `using-plan-and-execute` | Deploy plan-and-execute 4.0.0 after source verification |
| `denubis-basic-agents` SessionStart context | Source removes the hook; routing remains in `using-generic-agents` | Deploy basic-agents 2.2.1 after source verification |
| `denubis-hook-branch-bg` | Source preserves the terminal side effect and is silent on ordinary success; installed 0.2.5 still injects `Success` | Deploy the verified source change in the live fulfilment slice |
| PreToolUse dispatcher and global approver | Some command-specific decisions and advice overlap without a complete ownership contract | Narrow, separately tested enforcement boundaries |
| `.notes/` | No top-level project-memory Markdown remains after source cleanup; local-mail coordination state remains below `.notes/local-mail/` | Memory only; direct retrieval; human-derived claims resolve to the source invocation |
| ADRs and architecture | Decisions and topology exist, but some documents retain correction narratives or describe targets as current | Decisions in ADRs; present topology in living architecture; arguments in Git or explicit archives |
| `impl-plan-decision-discipline` | The one-route planner from `aa41464`, filesystem-derived reference test from `b8ca31b`, breadth-first seam planning, conditional predicted DFD, implemented-state reconciliation, and load-bearing ADR threshold are incorporated. Release tip `a724452` is not integration proof | Keep the reconciled current owners and `using-code-search`; do not merge the branch's unrelated history or obsolete planning apparatus |
| `cc-search-chats` cross-vendor work | Phases 1–2 are independent; Phase 3 currently contains exact resolution beside receipt correlation | Search owns provider identity, exact resolution, coverage, and reference-only output; receipts remain optional provenance evidence |
| Live plugin cache and settings | Enabled source, marketplace metadata, cache versions, global hooks, and output style can drift independently | Verification compares exact declared source candidates with the live consumers |

The current enabled reminder paths remain live. No behavioural reduction has happened merely
because this design names them.

### Implementation-plan branch reconciliation

The branch is an evidence source, not a merge unit. Its current disposition is:

| Branch content | Disposition | Current owner |
|---|---|---|
| One planning route; recover facts before asking; only genuine human decisions escalate | Preserved | `impl-plan-write` and `using-plan-and-execute` |
| Universal anti-smuggling boundary for UAT | Preserved compactly; the former 270-line apparatus and model-authored stamps remain obsolete | `impl-plan-write`, `exec-uat-gate`, and the instruction-control review rubric |
| Test/UAT requirements, consumer tracing, direct work, optional bounded review, filesystem-derived reference checks | Preserved | Planner, executor, review skills, and `tests/test_skill_reference_integrity.py` |
| Mandatory proposer/verifier dispatch, plan index, phase lattices, review modes, forced worktrees, forced clears, checkpoint commits, vote or approval machinery | Obviated by the current direct-work and observable-evidence design | Git history only |
| Breadth-first inter-phase seam map and first-class predicted DFD | Restored conditionally for changes to meaningful data or control flow; every plan records the boundary decision | `flow-boundaries.md`, owned by `impl-plan-write` and checked at plan entry |
| Comparison of predicted and implemented DFD; load-bearing changes in what the system does produce an ADR carrying why | Restored; execution derives implemented state independently and architecture maintenance reconciles it | Executor, `maintain-architecture`, and `architecture-update`, with bounded coherence review only for a named residual risk |
| Agent-authored UAT probes spanning wanted and plausible unwanted behavior at user and existing-system seams | Restored in source | `impl-plan-write` and `exec-uat-gate` |

The historical resumes, alternative proposals, critiques, and task queues do not become
living plans here. Their resolved consequences are in the owners above; their arguments
remain in commits `97057ac`, `8f56ee4`, `30aeeba`, `a118d92`, and `aedc537`.

DFD applicability follows the boundary effect. Every plan records the decision in
`flow-boundaries.md`. A predicted DFD is required when work changes what crosses an actor,
system, runtime-component, process, or durable-store boundary. Plan phases are delivery
boundaries mapped separately; merely having several phases does not trigger a DFD. An
internal change in how is exempt only when participants, inputs, outputs, meaning,
ordering, persistence, effects, control, consumers, and failure behavior remain unchanged;
the plan names that preserved boundary rather than emitting an empty diagram.

Execution audits the boundary after implementation even when planning said a DFD was not
applicable. It inventories every changed code, schema, configuration, generated, and
runtime surface before comparing implemented state with the prediction, so an omitted flow
or empty search cannot establish conformance. This is evidence ordering, not a
model-authored seal. Architecture maintenance runs only when that reconciliation exposes
an architecture-owned claim, relationship, source pointer, or decision record that must
change.

The `impl-plan-decision-discipline` branch and worktree remain unchanged as read-only
evidence until this candidate is integrated. They are not a merge unit. Retiring either
is a separate destructive action and is not authorised by this work.

### Always-on ownership disposition

The source candidate at `deployment/instruction-control/foa4008439/CLAUDE.md` and the
project `CLAUDE.md` apply this ownership map. Its manifest binds both candidates to the
exact live/source baselines; it does not claim deployment.

| Previous always-on section | Disposition | Owner |
|---|---|---|
| Working philosophy, uncertainty, pushback | Keep as continuous relationship invariants | Global `CLAUDE.md` |
| Request classification and one-question discipline | Keep in compressed boundary form | Global `CLAUDE.md` |
| Codebase adaptation procedure | Reduce to “inspect instructions/config/patterns”; detailed method belongs to coding procedures | Global invariant plus coding skills |
| TDD, minimal bug fixes, cache safety, no commit, verification | Keep as cross-project engineering boundaries | Global `CLAUDE.md` |
| Detailed good-test catalogue | Move out of always-on prose | `coding-good-tests` and project test guidance |
| Skill-selection reminder | Keep one task-entry invariant; retire repeated hook delivery | Global `CLAUDE.md` plus the selected skill |
| Reviewer incident and batch-fix history | Remove from living instructions | Review skills; old argument in Git/archives |
| Prose revision procedure | Move out of global context | `academic-writing` or the selected output style |
| Note discovery, search, keyword repair, advisor route | Replace with direct task-entry procedure | `denubis-project-notes:scanning-project-notes` |
| Git commit splitting and command procedure | Remove from global context | `denubis-git-commit:commit` |
| Shell distinction | Keep as a short machine invariant | Global `CLAUDE.md` |
| Settings distribution (`A2`) | Remove; the recorded procedure is retired and SSH is human access, not a sync contract | No agent-owned always-on procedure |
| Search tool diagnostics and measured edge cases | Remove from global context | Project search rules and `using-code-search` |
| Project HALT/reviewer duplicate | Remove from project file | Global integrity boundary and review/design skills |
| Task-invocation XML template | Move to directive authoring | `writing-claude-directives` |
| Python 3.14 application / Python 3.9 hook split | Keep without incident history | Project `CLAUDE.md` |
| Repository Python and tooling invocation (`A3`, `A4`) | Keep the uv-project rule and hook exception without the correction history | Project `CLAUDE.md` and `.ed3d/worktree-setup.md` |
| Schema constants, source conflicts, version sync | Keep without incident history | Project `CLAUDE.md` |

The disposition is based on semantic owner and distinct responsibilities, not a byte-count
target.

## Operating principles

### 1. One semantic owner

Every behavioural requirement has one owner. A second control is valid only when it
governs a different boundary and has its own test. A successor retires its predecessor
in the same coherent change.

### 2. Claim only the observed boundary

A hook can claim only the event and matcher it controls. A skill supplies a procedure.
A note preserves memory. A log records an event. A test establishes only the conditions
it exercised. None proves that a model understood or obeyed prose.

### 3. Put each requirement where it can work

| Requirement | Owner |
|---|---|
| Mechanical prohibition or state transition | Hook, permission decision, or executable gate |
| Continuous cross-project invariant without a discrete boundary | Global `CLAUDE.md` |
| Continuous project invariant | Project `CLAUDE.md` |
| Situational procedure | Skill |
| Durable local observation or preference | `.notes/` |
| Decision and its consequences | ADR or dated decision record |
| Present system topology | Living architecture |
| Superseded text, dispute, or incident history | Git or explicit archive |

### 4. Anticipate rather than accumulate corrections

Repeated correction is evidence that the owner or boundary is wrong. Change or remove
that mechanism. Do not add another reminder describing the previous failure.

Before consequential work, identify the failure made plausible by present conditions and
the observation that would expose it early. This is a situated check, not a generic risk
list or model self-critique ceremony.

Accepted decisions and stated constraints remain active until the human revises them.
Research and review findings are inputs, not authority to reopen a settled boundary.

### 5. External evidence binds transitions

A consequential transition consumes an observation produced outside the model's
narration. The evidence identifies its producer, subject, result, invalidation condition,
and consumer. Serialization alone is not external evidence; a consumer must recompute the
binding and compare the claimed result with the cited artifact.

Cross-repository and cross-worktree artifact identity consists of repository identity,
revision, repository-relative path, and a full algorithm-labelled digest. Checkout mtime,
branch name, and truncated digest are not identity or authority.

Use stamps only where a later consumer can recompute the binding and fail for the right
reason. Ordinary edits do not earn ceremonial certificates.

A probe establishes only the invocation, configuration, and path it exercised. A
successful path does not establish another path, and one failed probe does not establish
general absence.

### 6. Human authority must resolve

A document that relies on a human instruction points to the original human record and an
exact resolver. It does not substitute a quotation, paraphrase, model summary, or session
UUID without a message locator. A note is memory; an ADR memorialises a decision; neither
creates human authority.

The authority store is part of reference integrity. Codex history must remain `save-all`
and uncapped while its rollout JSONLs are cited. The verifier parses the live TOML and
rejects disabled persistence or a `history.max_bytes` cap; model prose does not certify
retention.

### 7. Repair integrity defects when found

Missing, ambiguous, stale, or falsely classified authority blocks the dependent action.
Repair the reference or obtain a new focused human invocation. Do not work around it.

### 8. No palimpsests

Things state what they are now. Living instructions carry current instructions. Skills
carry current procedures. ADRs carry the decision and its present consequences. Notes
carry current memory. Arguments with earlier versions belong in Git or explicit archives.

### 9. Expose the universe of discourse

The system map names the relevant entities, owners, boundaries, consumers, evidence, and
exclusions. Discovery covers hidden, ignored, global, installed, and worktree-specific
surfaces before absence is asserted. Future work consumes the map rather than repeating
the archaeology.

At entry to non-trivial work, inspect applicable skills, relevant project memory and
feedback, and accepted decisions and constraints, then say what changes the work. For an
open-ended request, recursively separate components that protect materially different
decisions and settle the current component's goal and mechanism before opening the next.

### 10. Every control answers “so what?”

A control identifies the action it changes, the boundary where it changes it, and the
observable failure it prevents. Text with no effect beyond reminding or explaining is
reference material, not a control.

### 11. Tests observe something independent

An automated test does not read instruction text, assert a chosen phrase is present or
absent, and then treat writing that phrase as correctness. It exercises behaviour or
processes the subject into a structural or semantic observation that is independent of
the satisfying edit. When prose quality cannot be decided mechanically, its expectations
belong in a review rubric for a human or reviewing agent.

### 12. Review the evidence, not the label

Severity and summary verdicts route attention; they do not decide disposition. Every
finding is assessed against its evidence, consequence, and hidden assumptions before it
is accepted, rejected, or fixed.

## Method

For each responsibility:

1. Map its current producers, consumers, duplicates, and exclusions.
2. Document the target owner, boundary, evidence, and failure behavior.
3. Update one coherent responsibility and retire its predecessors.
4. Verify source behavior and the live consumer separately.

Breadth-first means the map covers the whole control system before any one mechanism
grows a deep supporting bureaucracy. It does not mean batching unrelated edits.

## Cross-vendor search boundary

`cc-search-chats` supplies:

- a provider-qualified canonical message locator;
- exact source resolution independent of ranked text search;
- distinct resolved, absent, ambiguous, stale, unavailable, malformed, and unsupported
  outcomes;
- source-coverage and cardinality diagnostics with positive controls; and
- reference-only output containing the locator, resolver invocation, and uniqueness
  result without documentary interpretation.

Receipt correlation may add conservative `submitted_by` evidence. It is not a
prerequisite for literal search, exact resolution, or reference-only output. The
simplification can use raw source locators until the resolver ships; this dependency does
not block reminder removal, document repair, `CLAUDE.md` ownership, or integration of the
existing implementation-plan rewrite.

## Implementation slices

Each slice must leave the repository and live system coherent on its own.

1. **Document integrity.** Correct known false current claims and remove false review
   certificates. Add resolvable human locators only where a document relies on human
   authority.
2. **Generic reminder retirement.** Remove the per-prompt skill reminder first. Remove the
   post-git reminder separately. Preserve unique procedures or gates before removing their
   current carrier.
3. **Silent ordinary hooks.** Remove no-op model context from branch background and other
   telemetry while preserving their actual side effects.
4. **Notes ownership.** Give the main agent direct task-entry retrieval and retire the
   SessionStart request, advisor route, and contradictory keyword-repair prose. Keep the
   project-notes skill as source only; install it separately after provider-qualified
   exact resolution is available and verified.
5. **Always-on ownership.** Rewrite global Codex `AGENTS.md` and global and project
   `CLAUDE.md` by distinct rule count and owner, not by word count. Move search diagnostics,
   authoring templates, settings sync, commit procedure, reviewer incident history, and
   academic style to their situational owners.
6. **Implementation workflow reconciliation.** Preserve the one-route planner and
   reference-integrity test already incorporated from `aa41464` and `b8ca31b`. Restore the
   accepted breadth-first seam, predicted/observed DFD, ADR-threshold, and UAT-coverage
   decisions in their current owners. Keep direct work and observable evidence; do not
   restore self-certification, mandatory delegation, fixed review ceremony, or obsolete
   branch documents.
7. **Mechanical boundaries.** Retain or build only hook decisions with an exact matcher,
   structured outcome, positive/non-match controls, and named failure behavior.
   Candidate settings are parsed as data: the manifest rejects global subagent-model
   override and subprocess PID isolation while the selected agents and crash-recovery
   design depend on per-agent models and host-process visibility.
8. **Live fulfilment.** Verify source, enabled settings, installed cache, global files,
   parsed Codex history retention, and selected output style. Deployment requires a
   recoverable exact candidate and direct post-change observation.

The first seven slices do not require PostgreSQL receipt completion. Exact chat resolution
is required before documentary validation can replace raw-source locators, but it does not
block correcting a locator already proven against its raw source.

## Evidence policy

- Positive evidence is required before an empty result authorizes work.
- Model-authored review summaries are leads. The cited artifacts and observable checks
  determine the result.
- A structured record is useful only when its consumer recomputes the subject and can
  reject stale or contradictory input.
- Human acceptance is reserved for judgments automation cannot make. It is not a request
  to rerun a test by hand.
- Behavioural improvement is assessed prospectively from actual action boundaries. Raw
  word count, reminder count, or skill-call totals without eligible opportunities do not
  establish compliance.

## Definition of done

This simplification is done when:

- the live system map identifies every enabled instruction/control surface and its owner;
- generic unconditional reminder delivery is absent;
- every remaining always-on rule has a unique continuous responsibility and an observable
  action consequence;
- mechanical controls have positive, negative, and non-match tests at their real boundary;
- current notes, ADRs, plans, and architecture in scope contain no known unresolved human
  authority reference or correction palimpsest;
- cited Codex rollout sources remain under explicit uncapped `save-all` history
  configuration;
- the committed implementation-plan rewrite is integrated rather than duplicated;
- applicable plans map inter-phase seams before elaboration and reconcile predicted
  behavior with implemented architecture at the load-bearing what-and-why boundary;
- cross-vendor exact references round-trip when that interface becomes available;
- source changes and live settings/cache/global files are separately verified; and
- an ordinary session can proceed without repeated generic correction or coordination
  ceremony from the operator.

Out of scope: proving that fewer words alone improve compliance, historical transcript
backfill, deploying PostgreSQL receipts, building a universal instruction controller, or
using a model's self-assessment as completion evidence.
