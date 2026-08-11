# Instruction control system simplification

**Status:** Current design. No simplification change is deployed yet.

## Purpose

Reduce repeated corrective interaction by giving each instruction, prohibition,
procedure, memory, decision, and historical account one owner. A mechanism may claim
only what its observable boundary proves. Chat narration and model-authored certificates
do not bind or release work.

This work includes the global and project `CLAUDE.md`, enabled plugins and hooks,
`.notes/`, architecture and decision records, the completed implementation-plan rewrite
branch, and the cross-vendor chat-search interface used to resolve human authority.

## Authority evidence

The current human instructions are canonical `response_item/message/role=user` records
in:

`/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl`

Relevant source lines: `126`, `227`, `304`, `314`, `324`, `334`, `352`, `362`,
`383`, `403`, `423`, `433`, and `7809`.

Until `cc-search-chats` supplies its provider-qualified exact resolver, each locator is
checked directly with:

```fish
jq -s -e --argjson line LINE '[.[($line - 1)] | select(.type == "response_item" and .payload.type == "message" and .payload.role == "user") | .payload.content[] | select(.type == "input_text") | .text] | select(length == 1 and (.[0] | length > 0)) | .[0]' /home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl
```

The line number is one-based. Resolution must return exactly one non-empty input-text
record. A missing, ambiguous, or non-user record is an integrity defect.

Additional authority record `A2`:

`/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T16-44-15-019fea6a-2e86-7931-ad4d-e6b25bfa666a.jsonl:358`

Resolve it directly with:

```fish
jq -s -e '[.[357] | select(.type == "response_item" and .payload.type == "message" and .payload.role == "user") | .payload.content[] | select(.type == "input_text") | .text] | select(length == 1 and (.[0] | length > 0)) | .[0]' /home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T16-44-15-019fea6a-2e86-7931-ad4d-e6b25bfa666a.jsonl
```

## Current system map

| Surface | Current state | Intended owner |
|---|---|---|
| Global `CLAUDE.md` | 21,369 bytes; continuous rules, procedures, historical explanations, style, search reference, settings sync, and project-memory rules are mixed | Continuous cross-project invariants only |
| Project `CLAUDE.md` | Project conventions plus duplicates of global reviewer and halting rules | Project boundaries, current conventions, and finding aids |
| `denubis-hook-skill-reinforcement` | Source retired; installed 1.2.0 remains enabled until the deployment slice | Remove from live settings and cache only after source verification |
| `denubis-hook-claudemd-reminder` | Source retired; installed 1.1.4 remains enabled until the deployment slice | Commit preparation owns the documentation-freshness check |
| Project notes | Source provides `denubis-project-notes`, but the core deployment does not install it while cross-vendor exact search is unfinished | Global task-entry inventory and raw-source resolution replace the advisor; the skill is a later deployment slice |
| `denubis-plan-and-execute` SessionStart context | Source removes generic context while retaining the live-marker side effect; two distinct planning gates remain in `using-plan-and-execute` | Deploy plan-and-execute 4.0.0 after source verification |
| `denubis-basic-agents` SessionStart context | Source removes the hook; routing remains in `using-generic-agents` | Deploy basic-agents 2.2.1 after source verification |
| `denubis-hook-branch-bg` | Source preserves the terminal side effect and is silent on ordinary success; installed 0.2.5 still injects `Success` | Deploy the verified source change in the live fulfilment slice |
| PreToolUse dispatcher and global approver | Some command-specific decisions and advice overlap without a complete ownership contract | Narrow, separately tested enforcement boundaries |
| `.notes/` | Project memory exists at the main repository root; some records contain stale or unresolvable authority claims | Memory only; direct retrieval; human-derived claims resolve to the source invocation |
| ADRs and architecture | Decisions and topology exist, but some documents retain correction narratives or describe targets as current | Decisions in ADRs; present topology in living architecture; arguments in Git or explicit archives |
| `impl-plan-decision-discipline` | Final `impl-plan-write` and its reference-integrity test integrated from `a724452`; current `using-code-search` name retained as the sole source conflict | Verify as part of plan-and-execute 4.0.0; do not merge the branch's unrelated mainline churn |
| `cc-search-chats` cross-vendor work | Phases 1–2 are independent; Phase 3 currently contains exact resolution beside receipt correlation | Search owns provider identity, exact resolution, coverage, and reference-only output; receipts remain optional provenance evidence |
| Live plugin cache and settings | Enabled source, marketplace metadata, cache versions, global hooks, and output style can drift independently | Verification compares exact declared source candidates with the live consumers |

The current enabled reminder paths remain live. No behavioural reduction has happened merely
because this design names them.

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
| Schema constants, source conflicts, version sync | Keep without incident history | Project `CLAUDE.md` |

The disposition is based on semantic owner and rule count, not the reduction from 29,386
combined bytes to 7,532 candidate bytes.

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

### 5. External evidence binds transitions

A consequential transition consumes an observation produced outside the model's
narration. The evidence identifies its producer, subject, result, invalidation condition,
and consumer. Serialization alone is not external evidence; a consumer must recompute the
binding and compare the claimed result with the cited artifact.

Use stamps only where a later consumer can recompute the binding and fail for the right
reason. Ordinary edits do not earn ceremonial certificates.

### 6. Human authority must resolve

A document that relies on a human instruction points to the original human record and an
exact resolver. It does not substitute a quotation, paraphrase, model summary, or session
UUID without a message locator. A note is memory; an ADR memorialises a decision; neither
creates human authority.

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
5. **Always-on ownership.** Rewrite global and project `CLAUDE.md` by distinct rule count
   and owner, not by word count. Move search diagnostics, authoring templates, settings
   sync, commit procedure, reviewer incident history, and academic style to their
   situational owners.
6. **Implementation workflow reconciliation.** Integrate the committed
   `impl-plan-decision-discipline` work as existing work. Simplify planning and execution
   around direct work and observable evidence; remove self-certification, mandatory
   delegation, and fixed review ceremony. Resolve current conflicts and release metadata;
   do not selectively recreate decisions from an old draft.
7. **Mechanical boundaries.** Retain or build only hook decisions with an exact matcher,
   structured outcome, positive/non-match controls, and named failure behavior.
8. **Live fulfilment.** Verify source, enabled settings, installed cache, global files, and
   selected output style. Deployment requires a recoverable exact candidate and direct
   post-change observation.

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
- the committed implementation-plan rewrite is integrated rather than duplicated;
- cross-vendor exact references round-trip when that interface becomes available;
- source changes and live settings/cache/global files are separately verified; and
- an ordinary session can proceed without repeated generic correction or coordination
  ceremony from the operator.

Out of scope: proving that fewer words alone improve compliance, historical transcript
backfill, deploying PostgreSQL receipts, building a universal instruction controller, or
using a model's self-assessment as completion evidence.
