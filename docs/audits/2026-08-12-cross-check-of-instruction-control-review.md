# Cross-check of the instruction-control cross-check — 2026-08-12

## Scope

This audit reviews the source at `dc89860`, the source audit in
`docs/audits/2026-08-11-critical-peer-review-b33b22c.md`, and the Claude response preserved
as the assistant record at line `654` of the Claude transcript below. The untracked copy
originally written to `docs/audits/2026-08-11-reviewer-response-to-codex.md` was removed
after this cross-check: it duplicated the raw record while violating the pointer-only
authority contract. A review statement is retained only when a current source, a
reproducible observation, or an external primary source supports it.

The human authority for the governing design remains the raw sources and locators in
`docs/design-plans/2026-08-11-instruction-control-system.md:16-44`. This document does
not reproduce or paraphrase those instructions. The Claude review's additional source is:

`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins--worktrees-simplify-instruction-context/4c787afd-76b2-4fac-af63-0e75609fecb3.jsonl`

Its records used as R1-R5 are canonical user messages at lines `404`, `476`, `562`,
`583`, and `590`. R6 at line `604` is an `enqueue` queue-operation containing a human
interjection, not a record accepted by the response's stated resolver. It can evidence
permission to make suggestions; it cannot authorise their implementation.

This follow-up did make two classes of live write. `NOTES01` authorised the
main-repository note cleanup whose per-note dispositions appear below. `RETENTION01`
authorised making Codex history retention explicit; that edit also repaired a pre-existing
TOML representation defect without changing its values. No deployment, installation,
commit, or publication follows from this audit.

## Result

The simplification's architecture survives: one semantic owner, small continuous
instructions, situational skills, mechanical controls at exact action boundaries, and
external evidence for consequential transitions. The generic reminder retirement remains
a reasonable product decision. It is not established as a causal compliance improvement.

The source controls that overclaimed their evidence have been repaired. The source
candidate is ready for repository review, not deployment: live fulfilment remains blocked
on explicit commit/publication authority, project integration, a green project-integration
check, and the separately authorised user-level transition. The duplicate or misleading
documentary evidence sources found by this audit have been removed.

| Area | Result | Consequence |
|---|---|---|
| Settings transition | Retain | It reconstructs the candidate from the live baseline and rejects undeclared changes. |
| Generic reminder retirement | Retain as a design decision | The sources show duplicate cost and no unique enforcement boundary, not a measured causal improvement. |
| UAT rubric | Retain | It asks for irreducible judgment and a falsifier without manufacturing human ceremony. |
| Claude reviewer response | Removed | It embedded human text, promoted scoped records into standing rules, and contained stale measurement. |
| Prose-test AST gate | Reworked | It is explicitly a bounded lint with adversarial positive controls; prose meaning stays in the review rubric. |
| Skill-prose testing | Reworked | Executable properties use independent checks; prose claims use falsifiable review expectations. A separate model is optional evidence, not a gate. |
| Internal-skill caller graph | Removed | Claude invocation controls are documented from the platform boundary; unsupported `family:` metadata and its test are gone. |
| Project-notes source | Keep uninstalled; narrow claims | It supplies a procedure when selected. It does not demonstrate task-entry delivery. |
| Research note | Removed | This dated audit owns the bounded evidence and external links without duplicating them into project memory. |
| Deployment evidence | Repaired in source | Authority text and action mappings are bound; the mutable project target and a pre-live integration gate are explicit. The gate remains red until integration. |

## Confirmed defects

### 1. The Claude response is evidence-bearing correspondence, not a decision record

The raw assistant response at transcript line `654` shows that its documentary copy
reproduced human text even though the design and global candidate require pointer-only
human authority. The copy also created another instruction surface inside an audit.

The record scopes do not support the response's stronger conclusions:

- R1 constrains ceremony; it does not specify the particular UAT implementation.
- R2 changes the corpus of one search; it is not a general control-system rule.
- R3-R5 constrain the diagnosis and defer one proposed mechanism. They do not establish
  that mechanical boundaries are the only useful intervention.
- R6 licenses suggestions only.

The response should therefore remain a review lead. Confirmed defects may be carried into
their actual owners with the raw source locator; the response itself should not be promoted
into an ADR, note, or instruction source.

### 2. The local transcript measurement is no longer reproducible as stated

The deleted note is preserved exactly in the raw Claude assistant record at line `2439` of
session `a711c799`. It recorded measurements without a byte length, digest, record cutoff,
or end timestamp. The transcript continued growing after the note was written. Its final
observed state on 2026-08-12 is:

- path:
  `/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/a711c799-c718-49e9-84a6-3e7560f803ad.jsonl`;
- 4,097 records and 8,037,258 bytes;
- six notes-advisory attachments, not zero;
- 42 tool operands containing `.notes/`, not 17;
- 230 lines containing `scanning-project-notes`, not 124; and
- zero invocations of `scanning-project-notes`, which still holds.

The measurement does still demonstrate that name mentions are not invocation evidence. It
does not preserve the historical 0/17/124 observation. Any future transcript measurement
used by a decision must freeze the observed subject with at least its exact path, byte
length or record cutoff, digest, query, and timestamp.

The hook is retired and the observation has no continuing operational consumer. The stale
note and its live references were therefore removed rather than rewritten.

The related three-arm pressure test also produced no valid treatment comparison. The
green arm disclosed that it had read the dispatcher's evaluation criterion from the live
transcript; that peer relay is preserved at line `1283` of the same raw session. It is
behavioral evidence from another model, not human authority. The advisor locator used in
the third arm resolves with
`cc-search-chats context 1ceeda30-fb5e-443d-a6a2-15c8e54e02d3 --json`, so the earlier
fabrication diagnosis is false. The pressure-test and transcript-contamination notes are
therefore retired: this audit preserves the bounded result and its openable evidence.

### 3. The prose-test gate overclaimed its named property

`tests/test_test_quality.py:73-85` claims that the repository has no prose
change-detection tests. It scans only Python files matching `tests/test_*.py` and
`plugins/**/tests/test_*.py`. The detector in `scripts/test_quality.py:340-408` recognises
only a subset of Python `assert` shapes and raw-text data flows.

Three ordinary exact-wording tests all return no violations:

```text
assert "required" in Path("SKILL.md").read_text()
assert all(word in text for word in ("required",))
assert re.search("required", Path("SKILL.md").read_text())
```

The same detector reports no violation for either
`tests/test_always_on_instruction_ownership.py` or
`tests/test_skill_reference_integrity.py`. Yet the first locks exact Markdown heading names
at lines `28-59`, and the second derives a required caller from the callee's own `family:`
field and code-span wording at lines `88-90` and `142-166`.

Processing text is necessary but not sufficient to make a check independent. A check is
independent only when the expected property comes from a real consumer, schema, runtime
boundary, or separately owned contract. Extracting headings and then asserting the headings
authored by the same change remains a change detector.

The AST detector now remains only as an explicitly incomplete lint for supported Python
patterns. Adversarial positive controls cover inline reads, nested comparisons, regular
expressions, and normalised helper returns. The repository test names its Python-test
scope. The exact-heading tests were removed; their semantic expectations remain in
`docs/review-rubrics/instruction-control.md`.

### 4. The internal-skill caller graph used the wrong runtime model

The project glossary says at `docs/architecture/glossary.md:14` that a skill without
`user-invocable: true` is invoked by other skills or agents. Current Claude Code
documentation says `user-invocable: false` hides human invocation while Claude may still
invoke the skill; its description remains in context and the full body loads on invocation.
See [Claude Code skill invocation controls](https://code.claude.com/docs/en/slash-commands#control-who-invokes-a-skill).

The repository's `family:` field is not a Claude Code runtime field. The graph test uses
that self-declared field as its expected caller set, so deleting the field skips the test
and changing it to another existing skill changes the requirement. `_routes_to` then treats
backticked prose as a call edge, despite the test claiming that rewording does not affect
the graph.

Explicit workflow links remain where a workflow actually requires the callee. The glossary
now describes the documented invocation controls. Unsupported `family:` fields, the
prose-derived route parser, and the universal caller test have been removed.

### 5. The deleted research note exceeded the evidence

The exact deleted note is preserved in the raw Claude assistant record at line `4087` of
session `a711c799`. It turned bounded findings into general control-system claims.

The configuration-file study tested one static comment-insertion instruction across
25-500-line files, two TypeScript repositories, five feature-addition tasks, and Claude
Code's single-turn `--print` mode. It found Bayes-supported nulls for size and conflict
within those conditions; position and architecture were only failures to reject. The
paper explicitly leaves demanding rules, multi-turn compaction and reinjection, debugging,
infrastructure, dependency work, review, and other agents untested. Its “within-session”
variable is generated-function order, not conversational distance. It did not test an
action-time reminder, so the note's claim that action-time firing resets distance to zero
is unsupported. See [McMillan, arXiv 2605.10039](https://arxiv.org/abs/2605.10039) and its
[limitations](https://arxiv.org/pdf/2605.10039#page=14).

The instruction-count preprint tested 10-160 programmatically verifiable essay rules on one
fictional corpus. The paper itself says its numeric thresholds should not be transferred to
other models or domains, and lists distributing rules across turns, tools, or validation as
future work. “Distinct simultaneous rule count is worth measuring” is supported; “rule
count is the unit, not word count” is too strong. See
[Eliav, arXiv 2607.19257](https://arxiv.org/html/2607.19257#S9).

The adjacent-repetition result repeated the complete prompt immediately in the same input.
It reported 47 significant wins and no losses in 70 non-reasoning benchmark/model
combinations, while multi-turn applicability remained future work. It neither rescues nor
tests a spaced per-turn meta-reminder. See
[Leviathan, Kalman, and Matias, arXiv 2512.14982](https://arxiv.org/html/2512.14982).

Chroma found no notable position effect in one specific needle-in-a-haystack task, while
its broader experiments still found degradation with input length, semantic ambiguity,
distractors, and structure. That does not establish that simple positional blindness is
generally solved. See [Chroma, Context Rot](https://www.trychroma.com/research/context-rot).

These sources support scoped instruction ownership and empirical measurement. They do not
prove that shrinking, repetition, or action-time restatement is universally good or bad.

### 6. Project-notes is a procedure, not demonstrated delivery

`plugins/denubis-project-notes/.claude-plugin/plugin.json:3` describes direct task-entry
retrieval with complete note coverage. The skill description at
`plugins/denubis-project-notes/skills/scanning-project-notes/SKILL.md:3` also describes a
task-entry outcome. The body does define a complete procedure, but there is no observed
selection or execution of that procedure. The final transcript measurement above records
zero invocations.

The decision to keep the plugin out of this deployment is sound. The global candidate's
`.notes/` rule remains model-mediated context, not proof that retrieval occurred. Until a
real invocation path is observed, the plugin and design should claim only that the procedure
is available when selected. Exact source resolution remains a separate prerequisite for
using a chat hit as authority, not evidence that skill selection works.

### 7. Source verification formerly validated shape, not authorisation content

`deployment/instruction-control/verify_candidate.py:68-126` checks that each selected line
is one non-empty user record. It does not bind the message text or digest, state which
candidate action the record authorises, or reject substitution of a different non-empty
user record. A green source result therefore proves candidate bytes, plugin trees, and
record shape. It does not prove that the records authorise every candidate change.

The manifest now binds each authority locator to the SHA-256 of its exact human text,
groups records by action, and requires every candidate, release, retirement, and settings
transition to name a known action. The verifier rejects substituted human text, malformed
provider records, missing mappings, and unknown actions without copying the human text
into a memorial document.

### 8. The deployment precondition formerly missed the mutable project target

The manifest's project candidate targets
`/home/brian/people/Brian/brian-ed3d-plugins/CLAUDE.md`, but its baseline at
`candidate-manifest.json:84-88` is `git:c6882d2:CLAUDE.md`. That proves historical Git
content still resolves. It cannot detect a change to the live project file between
candidate preparation and deployment.

The runbook's live transition at `deployment/instruction-control/foa4008439/README.md:34-57`
updates the marketplace, plugins, global `CLAUDE.md`, and settings. It never integrates the
project candidate into the target checkout. The deployed verifier will fail afterward if
the project file was not separately integrated, but by then other live state may already
have changed.

The project baseline now binds the actual main-checkout file and rejects historical Git
bindings. The runbook separates repository integration from user-level deployment, and a
dedicated verifier compares the integrated project file with the reviewed candidate before
any global, settings, registry, or cache mutation. That check is intentionally red until
the project change is integrated.

### 9. Skill “TDD” was a model-compliance performance, not an independent test

The former `writing-skills` and `testing-skills-with-subagents` procedures equated a model
response to a pressure prompt with RED/GREEN code TDD, required an independent-session
failure before prose could be authored, and treated the absence of new rationalisations as
“bulletproof.” The expected result and its judge were both supplied by the same authoring
procedure. A model following the resulting prose once could not establish future
selection, interpretation, or compliance.

Human authority for the replacement boundary is the Codex user record at
`/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl:9797`.
It is bound as `TEST01` to action `test_evidence_boundary` in the deployment manifest and
validated by the source verifier; cross-vendor `cc-search-chats` resolution is not yet
available for this Codex record.

The two live authoring skills now separate executable properties from prose judgment.
Metadata, references, helpers, and runtime behavior can be checked at their real
boundaries. Prose receives a scenario, expected consequence, falsifier, and exclusions in
a review rubric. A human-requested or otherwise authorised reviewer may apply that rubric,
but its verdict does not bind later action. The long-running-state reference was rebuilt at
the same boundary: it no longer mandates orchestration-only work, checkpoint commits, or
model-memory files.

## Claude suggestions that do not survive the cross-check

- New dated records for the model-tier and note-retrieval exchanges would duplicate current
  owners and create the scar tissue the design removes. Update a current owner only when its
  current statement is false or incomplete.
- A rule that makes the finder own every pre-existing or flaky failure would broaden normal
  task authority. `systematic-debugging` already says flakiness is not permission to ignore
  a failure, while preserving unrelated user work and minimal fix scope.
- Accepted deferred findings already have owners: the current phase file or existing tracker
  in the executor, and a durable review file when a named consumer exists in the review
  skill. No generic findings ledger is needed.
- Tool-call counting is the correct way to distinguish invocation from discussion, but the
  cited historical counts are not reusable without a frozen subject.

## Project-note universe and target owners

The main repository's `.notes/` was inventoried through the Git common directory rather
than through this worktree. At mapping time it contained 48 top-level Markdown files after
the two evidence records removed above. Every frontmatter block and every body was read. The two
`local-mail/messages/*.md` files and `local-mail/index.sqlite3` are operational mailbox
state, not project memory, and are excluded from this cleanup.

No mapped top-level note met the new authority contract. Thirty-nine records either
duplicate an existing owner, preserve closed or superseded work, or are model reviews and
experiment diaries rather than current memory. Nine carry a fact or unresolved decision
that still changes an action; those must move to the named consumer with resolvable
evidence before the note is retired. Moving an item means replacing the note with its
current owner, not copying its correction history into another document.

Cleanup result: zero top-level project-memory Markdown files remain. `.notes/` now contains
only the excluded local-mail state. The tables below are the complete disposition map for
the original 48-file universe.

### Retire after removing live references

| Notes | Current owner or reason |
|---|---|
| `feedback_4-7-retrieval-hallucination.md` | Unsupported model-comparison hearsay; source verification is already a global evidence boundary. |
| `feedback_absence-is-not-a-signal.md` | Global evidence rule and `using-code-search`. |
| `feedback_announce-the-working-directory.md` | Planning, execution, worktree, and session-naming procedures already report the absolute working directory. |
| `feedback_commit-cadence.md` | Explicit commit authority plus `denubis-git-commit:commit`; the note is an incident narrative. |
| `feedback_compact-idle-external-sessions.md` | Retired after moving the cadence authority to `supervising-codex` as raw transcript plus `cc-search-chats context` locators; mechanism and confirmation remain in code and behavior tests. |
| `feedback_fable-context-pruning.md` | The Fable consultation procedure; this record is an old operating brief without an exact human locator. |
| `feedback_functional-decomposition-readbacks.md`, `feedback_readback-restraint.md` | Global one-question/request-boundary rules. |
| `feedback_haiku-no-judgement.md` | Retired after consolidating the dispatch floor in `writing-claude-directives/model-tier-notes.md`; every dependent live document now carries the same raw source and resolver rather than citing the note as authority. |
| `feedback_honour-prior-architectural-decisions.md` | Retired after the global candidate made accepted decisions and constraints active until the human revises them. |
| `feedback_no-unverified-capability-claims.md`, `feedback_reviewer-fabrication.md`, `feedback_supervisor-assertions-are-not-frozen.md` | Retired after the global evidence boundary limited probes to their exercised invocation, configuration, and path. |
| `feedback_resume-prompts-not-committed.md` | `tests/test_resume_prompts_untracked.py` and the workflow that writes the prompt. |
| `feedback_review-all-levels.md` | Retired into the global evidence-first review rule: labels route attention; evidence, consequence, and assumptions determine disposition. |
| `feedback_scar-tissue.md` | Retired into the global no-palimpsest rule and the design's explicit document-owner table. |
| `feedback_uat-tautology.md` | `impl-plan-write` and the instruction-control review rubric. |
| `feedback_version-bumps-after-working.md` | Project release contract and `impl-plan-write` release boundary. |
| `feedback_worktrees-are-visibility.md` | Worktree and branch-finishing procedures preserve unfinished work and forbid implicit cleanup. |
| `project_agent-teams-design-wip.md` | Retired with stale ISSUE-02: it is a paused design transcript, not a current decision or actionable defect. |
| `project_codex-council-charter-closed.md` | Closed branch history; a corrective note about stale commit prose is itself archaeology. |
| `project_directive-softening-2026-08-09.md` | Current instruction-control design; the experiment never established a treatment effect. |
| `project_external-agents-delegation-expansion.md` | Superseded by the current external-agents plugin and instruction-control design. |
| `project_merge-ceremony-gate.md` | Superseded by the current merge procedure and the decision not to require a generic ceremony token. |
| `project_notes-advisory-pressure-test-2026-08-09.md` | This dated audit owns the bounded result; the invalid experiment is not active memory. |
| `project_notes-migration-pilot-debrief.md` | Historical migration report with stale project counts and proposed future work. |
| `project_proposer-verifier-decisions.md` | Superseded workflow design; current execution does not require mandatory proposer/verifier dispatch. |
| `reference_approver-script.md` | `/home/brian/.claude/hooks/approver/` owns its current code, tests, and local documentation. This copy has stale counts and points to a report and `RESUME.md` that no longer exist. |
| `reference_bbt-item-search-constraints.md`, `reference_zotero-api-plus.md` | `denubis-academic:using-bibliography`; both notes are older and less complete than the current procedure. |
| `reference_codex-pane-geometry-breaks-the-guards.md` | Supervisor code, tests, and procedure own the current behavior. |
| `reference_council-groupthink-constraint.md` | An unverified blog-derived percentage attached to a dropped council design. |
| `reference_external-dispatch-prior-art.md` | Historical prior-art report for a superseded proposer/verifier design. |
| `reference_ruff-format-not-check-rewrites-except.md` | Project hook-portability contract and executable Python-3.9 parsing tests. |
| `reference_skill-description-quoting-breaks-the-trigger-check.md` | Already fixed in `tests/test_skill_descriptions.py`: YAML frontmatter parsing and the quoted-colon behavior test landed in `12b145e` and `7c339f0`; the stale workaround note is retired. |
| `reference_subagent-bypass-permissions-bash.md` | Dated harness behavior with no current consumer and no stable platform evidence. |
| `reference_pretooluse-hook-semantics.md` | Dated platform observations with no source pin or current consumer; retire rather than promote them as a standing contract. |
| `reference_subagent-tests-read-the-live-transcript.md` | `testing-skills-with-subagents` owns test isolation; the invalid pressure-test record is also retired. |
| `reference_tool-search-deferral.md` | Candidate settings and deployment verification own `ENABLE_TOOL_SEARCH`; the incident is historical. |
| `reference_uv-workspace-pytest-collection.md` | `.ed3d/worktree-setup.md`, root workspace configuration, and test guidance now own the current setup; historical pass counts are retired. |
| `review_run-autoexport-spec-cpr.md` | Raw model review of a removed spec; current bibliography procedure already contains the surviving technical result. |

### Move the current consequence, then retire the note

| Note | Target owner and required repair |
|---|---|
| `feedback_absencejudgement-codes-fabricated.md` | Retired after an exhaustive scoped search found no live skill or instruction using the invented codes; removed the correction-only plan apparatus and ISSUE-05 with it. |
| `feedback_ahead-count-is-not-risk.md` | Moved to `finishing-a-development-branch`: upstream divergence is now explicitly separated from containment before claiming commits are unpushed or at risk. |
| `project_codex-supervision-monitor-findings.md` | Current failures reproduced and moved to `docs/issues.md` ISSUE-14; implemented behavior stays in code, tests, and `supervising-codex`, not a running incident diary. |
| `project_message-provenance-attribution.md` | Retired as an invalid memorial: its only source session contains a Fable review request, not a human acceptance record. Exact chat resolution remains independent of optional receipt correlation. |
| `reference_artifact-identity-across-worktrees.md` | Moved to the global evidence boundary and governing design; the dated multi-worktree incident narrative is retired. |
| `reference_env-vars-that-would-break-us.md` | Replaced by the parsed candidate settings contract, its verifier test, and current official documentation links; the dated count and inventory prose are retired. |
| `user_uv-run-conventions.md` | Moved to project `CLAUDE.md` with exact raw and `cc-search-chats` locators; the note's overbroad wording is retired. |

Every live reference was removed or retargeted before its note disappeared. Each moved
consequence is verified at its consumer boundary below.

## Note cleanup, request entry, decisions, and Codex retention

Authority record `NOTES01` binds the register-wide cleanup. `REQUEST01` binds request
entry, and `RETENTION01` binds the Codex-retention check. None substitutes for another.
The findings are:

- The main-repository `.notes/` contains zero top-level project-memory Markdown files.
  Task entry still needs to inventory it because the empty state is contingent, not a
  reason to remove the boundary.
- `using-plan-and-execute` previously selected a workflow but did not require the main
  agent to inspect relevant memory, feedback, accepted decisions, and constraints or say
  which findings changed the work. The design procedures already handled one-question
  clarification and evidence-filtered proleptic challenge. The missing owner was task
  entry, not another reminder hook.
- Open-ended decomposition was present in the global Codex instructions but absent from
  the Claude candidate and task-entry workflow. Both now decompose around independently
  material decisions and settle the current component's goal and mechanism before opening
  another.
- ADRs 0001–0003 were marked Accepted without pointing to their resolvable human source.
  Their raw records and exact `cc-search-chats context` invocations were recovered and
  added. ADR 0004 already met the contract.
- The live global Codex config had no history table. That inherited the documented
  `save-all` default and imposed no `history.max_bytes` cap, but left the retention
  dependency implicit. `/home/brian/.codex/config.toml` now states `save-all` explicitly
  and remains uncapped. The manifest's parsed contract rejects either disabled persistence
  or a future byte cap. The current Codex reference documents no age-expiry key; explicit
  deletion and ephemeral execution remain separate user actions. See
  [Advanced Configuration](https://learn.chatgpt.com/docs/config-file/config-advanced.md)
  and the [CLI command reference](https://learn.chatgpt.com/docs/developer-commands.md?surface=cli).
- Parsing also exposed a pre-existing multiline inline table under
  `shell_environment_policy.set` that Codex accepted but Python's standards-compliant TOML
  parser rejected. It was converted to an ordinary table without changing any of its eight
  cache and tool-directory values. `tomllib` now parses the complete file and the Codex CLI
  accepts it.
- A scoped search of the live global Codex config, hooks, rules, and installed plugins
  found no `codex delete`, `/delete`, `--ephemeral`, history byte cap, or session-directory
  cleanup. Positive controls found the configured hook registrations. This establishes
  only those global Codex surfaces, not every external cron job or human shell command.

The initial interpretation of the retention instruction as a prose prohibition on agent
deletion was wrong. That prohibition and the resulting crash-recovery wording change were
removed; retention is owned by parsed global configuration instead.

## Implementation-plan worktree reconciliation

A separate read-only subagent compared the branch-only commits and every branch-only
design, critique, field report, and resume against the current planner, executor, review,
architecture, design, tests, and this audit. Its absence claims were repeated with both
`rg` over the current worktree and `git grep` over the named branch. The earlier claim that
the branch was integrated at `a724452` was false in two ways: that commit contains only
release metadata, and semantic integration remained incomplete.

Human authority is the raw Claude source and exact resolvers now listed under Authority
evidence in the governing design and bound as `PLAN01`–`PLAN04`, `DFD01`, and
`UAT01`–`UAT02` in the candidate manifest. No branch-authored summary substitutes for
those records.

| Item checked | Result | Consequence |
|---|---|---|
| One planning route; filter recoverable facts and invented alternatives; escalate only surviving human decisions | Preserved in `impl-plan-write` | Keep the compact current owner |
| Small-question triage | Preserved as direct inspection plus optional bounded delegation | Do not restore mandatory supervisor or subagent machinery |
| UAT anti-smuggling | Preserved compactly in planning, execution, and the review rubric | Do not restore the 270-line apparatus or planner-authored stamps |
| Test/UAT requirement files, consumer tracing, direct work, optional targeted review, reference-integrity test | Preserved and consumed | Keep current owners |
| Mandatory proposer/verifier, plan index, review modes, phase lattice, forced worktrees or clears, checkpoint commits, votes and certificates | Obviated by the accepted direct-work and external-evidence design | Leave their arguments in branch history |
| Breadth-first seam and contract mapping before phase elaboration | Restored in `flow-boundaries.md` | Applicable plans map producer, consumer, inter-phase, adjacent-system, and failure seams before phase detail |
| Planner-predicted DFD, implemented-state DFD, and their reconciliation | Restored across planning, execution, and architecture maintenance | The plan records what should be made; execution derives what was made independently |
| ADR threshold for a load-bearing change in what the system does, with why | Restored in execution and architecture update | Internal how does not create ceremony; a continuing change in boundary what requires an accepted design and ADR carrying why |
| UAT coverage across wanted and plausible unwanted behavior, including existing-system seams | Previously incomplete; restored in source | One narrow successful workflow no longer exhausts the planned human-judgment surface |

The retained historical evidence is addressable by commit rather than copied into living
documents: the earlier decision and alternative plans are in `97057ac` and `8f56ee4`, the
dated critiques and field reports in `30aeeba`, the consolidated ruling/task record in
`a118d92`, and superseded resumes in `aedc537`. Their current consequences are either in
the named owners above or explicitly missing. Copying the old files into this worktree
would preserve model inference, quotations, stale queues, and superseded alternatives as
another live palimpsest.

The branch and worktree remain unchanged as read-only evidence until this candidate is
integrated. They are not a merge unit; retiring them is a separate destructive action
outside this follow-up's authority.

Applicability is now settled by `DFD01`: every plan records the boundary decision, while
the predicted DFD is required only for a change to meaningful data or control flow. A
specific preserved-boundary reason replaces an empty diagram for non-applicable work.
Planning owns predicted state; architecture update owns implemented state and the material
divergence record.

The control is an unconditional implementation-first boundary audit: enumerate every
changed code, schema, configuration, generated, and runtime surface before comparing
against the prediction, including when planning said no DFD applied. Architecture update
is invoked only for an observed architecture-owned change; it is not a ritual
reconciliation receipt.

## External architecture check

Current product documentation consistently distinguishes scopes rather than relying on one
large universal prompt:

- Claude Code treats `CLAUDE.md` as context, not enforcement; it recommends hooks for hard
  action blocking, path-scoped rules for matching files, and skills for task-specific work.
  See [Claude Code memory](https://code.claude.com/docs/en/memory) and
  [hooks](https://code.claude.com/docs/en/hooks).
- GitHub Copilot supports repository-wide and path-specific review instructions. See
  [GitHub Copilot code-review instructions](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review#customizing-copilots-reviews-with-custom-instructions).
- The AGENTS.md specification uses nested files with nearest-file precedence. See
  [AGENTS.md](https://agents.md/#how-to-use-agentsmd).

This supports the design's division into continuous, path-scoped, situational, and
mechanical owners. It does not establish that model-selected skills are reliable or that a
particular word or rule budget is optimal.

## Repair order used

1. Removed or narrowed the self-justifying tests: heading locks, the family-caller graph,
   and the universal AST-gate claim. Behavior, schema, reference-resolution, and
   adversarial heuristic tests remain.
2. Narrowed project-notes descriptions to the procedure actually supplied and kept it out
   of the current deployment.
3. Bound the live project baseline, added the explicit project-integration boundary, and
   separated authority-reference integrity from authorisation.
4. Recomputed source, baseline, test, and live evidence separately. No deployment was
   performed.

## Pre-repair reproduced checks

- Candidate source verifier: `ok: true`.
- Candidate baseline verifier: `ok: true`; this result is bounded by the historical project
  binding defect above.
- Focused instruction-control tests: 158 passed, 47 skipped.
- Repository test runner: 1,145 passed, 47 skipped.
- `git diff --check`: passed.
- Three adversarial prose-test cases: all incorrectly returned zero violations.
- Final `a711c799` transcript query: 6 notes attachments, 42 note-path operands, 230 name
  mentions, and 0 project-notes skill invocations.

Passing checks establish their exercised boundaries only. They do not clear the defects
listed above.

## Disposition of the critical peer review

The follow-up review at
`docs/audits/2026-08-12-critical-peer-review-of-cross-check.md` produced six findings.
Their current dispositions are:

| Finding | Disposition |
|---|---|
| Note-cleanup authority | Resolved by binding the pre-cleanup user record as `NOTES01` and assigning only the cleanup action to it. |
| Stale final evidence | Resolved by the subject-bound checks below; earlier counts and digests are retained only under pre-repair evidence. |
| Candidate changes `opus` to `fable` | Rejected against the settled state. The review observed live `opus`; shortly afterward the live file again exactly matched the manifest's pre-existing `fable` baseline at 6,703 bytes and SHA-256 `14f32d5ab7d9c4affd133a9b5e30bd7f3a4cf8f014329d41cd964e052e3741f0`. The cause of the temporary state is not proven. The candidate also retains `fable`, and the parsed transition verifier is green. No model edit follows from this review. |
| Review rubric has no consumer | Resolved by the project `CLAUDE.md` finding aid for instruction, skill, hook, evidence, and deployment-control reviews. |
| Implementation-plan branch overclaim | Resolved by the per-mechanism reconciliation above and the explicit branch/worktree fate. `a724452` is no longer cited as integration proof. |
| Audit obscures live writes | Resolved by the live-write boundary at the start of this audit and the distinct `NOTES01` and `RETENTION01` authorities. |

## Final source checks

- Evidence subject: `candidate-manifest.json`, 18,642 bytes, SHA-256
  `c8d348fdc7741cbaa19f59689fd2404a41ddf10d196c080e75c0f0d68a624a79`.
- Candidate source verifier: `ok: true` against that exact subject at
  `2026-08-12T10:32:05Z`.
- Candidate baseline verifier: `ok: true` against that exact subject and the live files
  at `2026-08-12T10:32:05Z`.
- Project-integration verifier: intentionally red with candidate byte and SHA mismatch;
  the main checkout has not integrated this worktree's project `CLAUDE.md`.
- Focused instruction-control suite: 151 passed.
- Repository pre-commit runner: 1,128 passed.
- Full configured pytest suite: 1,566 passed.
- `git diff --check`: passed.

These results bind only the named manifest subject and live baselines. A change to either
invalidates them. They establish source readiness for review, not authority to commit,
publish, integrate, install, or deploy.
