# Codex Marketplace Semantic Mirror

**Status:** Current design; installed-runtime UAT correction is in progress.

## Objective

Make this repository the single semantic source of truth for Brian's customised
Claude Code and Codex plugins. Codex should install the compatible capabilities
through a repository marketplace without maintaining a second copy of shared skill
prose in `brian-ed3d-plugins-codex`.

The migration must improve the living skills before packaging them. Existing skill
files are evidence of current behaviour, not normative examples: some still contain
phase narration, dense tables, repeated ceremony, and provider assumptions that
conflict with newer project rules.

## Authority and safety boundaries

Authority, in descending order:

1. The active project `AGENTS.md` and explicit operator decisions.
2. This design's normative contract and recorded decisions.
3. Current semantic behaviour in this repository, after cross-checking it against
   the normative rules.
4. `brian-ed3d-plugins-codex` as evidence for Codex transport and runtime
   innovations only.

Neither repository's existing examples override the normative rules merely because
they already exist.

The primary checkout was dirty before this work began. Preserve all of those changes.
The Codex mirror also contains unrelated modified Ponytail files and untracked resume
material. Do not overwrite, clean, or delete them. All implementation work belongs in
the isolated `codex-marketplace-semantic-mirror` worktree.

## Normative behavioural contract

### Skills

- A skill states durable invariants, decisions, failure conditions, and the smallest
  procedure needed to apply them.
- Phase narration is presumptively removable. A stage boundary survives only when it
  changes authority, evidence, recoverable state, or the set of safe next actions.
- Tables are for exact mappings or comparisons that become clearer in tabular form.
  They are not compressed storage for procedural prose.
- Repeated announcements, mandatory worker counts, fixed review quotas, and named
  intellectual frameworks require demonstrated functional value.
- Safe in-scope work proceeds autonomously. A question represents a genuine
  human-held decision, not routine progress narration or manufactured choice.
- Provider-neutral semantics live once. Claude- or Codex-specific material describes
  transport, tool syntax, permissions, installation, or another genuinely different
  runtime fact.

### Tests and methodological evaluations

- A test is useful only when it can fail for the intended behavioural reason.
- Change detectors and phrase locks are not behavioural tests. They do not become
  sound merely by matching a longer or more carefully chosen series of words.
- A methodological evaluation gives the acting agent its task and instructions in
  one artifact. The answers, scoring criteria, or oracle live in a separate artifact
  unavailable to that actor.
- Evaluation includes a genuine failure case or positive control. An empty search or
  absent string is not sufficient evidence.
- The same rules apply while developing tests: red-green-refactor, no weakening a
  failing test to accept the implementation, and no tests for unexamined code that is
  being refactored.

### Verification and UAT

- Agents complete mechanical checks and independent sanity checks before asking for
  human UAT.
- Human UAT touches the implications of the finished behaviour through a real,
  falsifiable interaction. Reviewing a test report alone is not UAT.
- Failed UAT returns the work to implementation. Relevant checks run again before the
  next UAT attempt.

### Commit lifecycle

- Executing an approved plan authorises private checkpoint commits without repeated
  prompts. Frequent checkpoints are acceptable when they do not interrupt the user.
- Superseded checkpoints, fix rounds, and review-response commits fold into their
  owning coherent outcome. A checkpoint survives only if it matures into an outcome
  that is independently understandable and reversible.
- Final history normalisation occurs only after human UAT acceptance.
- Rewriting must preserve the exact accepted tree; the resulting series and tree are
  then re-audited and reverified.
- Accepted design plans land with the implementation they describe. ADRs may land
  independently because the accepted decision is itself their durable outcome.
- Commit messages name outcomes concisely. Design reasoning, alternatives, review
  findings, and verification narratives belong in project documentation.
- Do not rewrite inherited or already-published history.
- There is no target commit count. A design may commonly produce two or three durable
  outcomes, but the boundaries follow the work rather than a quota.

## Cross-check before packaging

The first audit target is `denubis-plan-and-execute`, because every later port would
inherit its rules for planning, implementation, testing, review, UAT, and Git history.

For each living skill and directly coupled support file:

1. State the actual behavioural obligation.
2. Identify narration, presentation structure, or provider mechanics that do not
   enforce that obligation.
3. Classify each mechanism as keep, simplify, move to a reference, replace with a
   runtime adapter, or remove.
4. Check consumers before changing a shared contract.
5. Specify behavioural evidence for the proposed result before implementation.

The audit must not use absence-only phrase searches as its conclusion. Searches may
locate candidates, but the finding requires reading the relevant context and checking
the mechanism's consumers.

The completed cross-check is recorded in
`docs/audits/2026-08-16-plan-and-execute-normative-cross-check.md`. It found that the
August simplification improved the workflow substantially but left fixed phase artifacts,
per-phase UAT, obsolete commit authority, unsafe universal Python/PostgreSQL rules,
disclosed-answer skill tests, a textual code-quality hook, duplicated agent procedures,
and 22 support artifacts with no active consumer. Those findings define the first two
implementation outcomes below.

## Codex innovations to preserve

The Codex mirror and current Codex documentation provide useful runtime mechanisms:

- A repository marketplace at `.agents/plugins/marketplace.json` and a
  `.codex-plugin/plugin.json` manifest in each installable plugin.
- Per-skill `agents/openai.yaml`, including deliberate implicit-invocation policy.
  The existing generated display text is mostly filler and is not authoritative.
- Native plugin lifecycle hooks, explicit hook trust review, `PLUGIN_ROOT`, and
  `PLUGIN_DATA`. Codex also supplies the Claude plugin environment variables for
  compatibility.
- Codex-native managed-worktree behaviour, `.worktreeinclude`, `/worktree`, and
  `/rename` where they materially affect a workflow.
- Translation invariants from the deleted generator: complete preflight before
  mutation, fail closed on incomplete transport constructs, exact removal of stale
  generated output, no user-specific paths, and preservation of complete worker
  briefs.

The current official Codex manual documents plugin hooks, although the installed
plugin-creator validator's reference text still says the manifest rejects hooks. The
manual and the installed `codex-cli 0.145.0` feature list both report hooks as stable.
Treat the validator note as stale and verify hook manifests against Codex itself.

## Codex material not to preserve

- The duplicated shared skill tree in `brian-ed3d-plugins-codex`.
- The deleted bulk generator as an architecture. Its useful safety invariants survive
  without restoring semantic duplication.
- Generated descriptions such as “Help with X workflows.”
- Old forced phases, `/clear` handoffs, mandatory trackers or subagents, per-phase
  review quotas, frustration-signal searches, and obligatory named-framework tables.
- The separate `using-ast-grep` skill; current `using-code-search` already contains
  the useful search, rewrite-safety, and debugging material.
- The Codex pre-tool dispatcher. Codex now loads and trusts enabled plugin hooks
  natively.
- The plan-and-execute code-quality hook as a Codex guard. It is primarily a set of
  textual change detectors and its Claude Write/Edit payload assumptions do not match
  Codex `apply_patch` input.
- The crash-recovery live-marker hook in Codex. Its transcript and marker contract is
  Claude-specific.
- Independent naming workers and caches for session names. Keep only a direct runtime
  handoff when naming has user value.

Ponytail and Gemini support remain in `brian-ed3d-plugins-codex` while they are
genuinely Codex/Gemini runtime infrastructure rather than duplicated semantic skills.

## Initial plugin classification

This is an audit starting point, not permission to expose an unverified plugin.

- Share one semantic core with thin Codex metadata: `denubis-academic`,
  `denubis-git-commit`, `denubis-project-notes`, and
  `denubis-token-estimator`.
- Share after the normative cross-check: `denubis-plan-and-execute`.
- Translate provider transport: `denubis-basic-agents`,
  `denubis-research-agents`, `denubis-hook-branch-bg`, and
  `denubis-hook-gh-fork-guard`.
- Redesign selectively: `denubis-extending-claude`,
  `denubis-external-agents`, and `denubis-crash-recovery`.
- Obsolete in Codex: `denubis-hook-pretooluse-dispatcher`, because Codex provides
  native plugin hook aggregation and trust.

The first marketplace should expose only components whose Codex behaviour has passed
mechanical checks and fresh-session UAT. Whether an unready plugin should appear as an
explicit unavailable catalogue entry remains an open presentation decision; it does
not block the semantic audit.

## Intended dual-runtime layout

```text
.agents/plugins/marketplace.json
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/.codex-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md
plugins/<plugin>/skills/<skill>/agents/openai.yaml
plugins/<plugin>/hooks/claude-hooks.json      # when Claude transport is explicit
plugins/<plugin>/hooks/codex-hooks.json       # when Codex transport differs
```

`SKILL.md` and its provider-neutral references own behaviour. Codex metadata and
provider references own only discovery and transport. A deeply provider-specific
capability may have two implementations, but both are evaluated against one separate
behavioural contract and hidden oracle.

## Work order

1. Freeze this normative contract.
2. Cross-check the full plan-and-execute skill and consumer graph.
3. Revisit the Codex evidence only for runtime mechanisms affected by each finding.
4. Write the final per-plugin share/translate/redesign/retire matrix.
5. Refactor canonical skills and add Codex packaging in coherent plugin-sized
   outcomes.
6. Run structural, mechanical, and methodological verification.
7. Install the local marketplace and test it from fresh Codex sessions.
8. Ask Brian to perform implication-level UAT.
9. After acceptance, normalise the private commit series and retire the duplicated
   Codex skill mirror.

## Verification expectations

- Existing project test and lint commands remain green.
- Every Codex manifest and marketplace entry is parsed and validated against the
  runtime actually used for UAT.
- Every exposed skill has intentional discovery metadata rather than generated filler.
- Provider scans are leads for review, not phrase-lock acceptance tests.
- Methodological evaluations keep actor instructions separate from answer keys and
  demonstrate both success and failure discrimination.
- A fresh Codex session can discover and invoke each installed plugin as intended.
- The final rewritten commit series produces exactly the tree accepted in UAT.

## Current durable state

- Repository: `/home/brian/people/Brian/brian-ed3d-plugins`
- Branch: `codex-marketplace-semantic-mirror`
- Worktree:
  `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/codex-marketplace-semantic-mirror`
- Original base: `main` at `293036ccab3e2b0c5939b1248856718c92c17c05`; updated
  `main` through `16582b3` is merged into the private candidate without rewriting its
  pre-UAT history.
- The normative cross-check and initial canonical skill corrections are implemented as
  private checkpoints. The old Codex repository cleanup is isolated on its own branch;
  its unrelated adapter work remains untouched.
- Baseline verification: `uv run pytest -q` — `1579 passed in 6.41s`.
- Post-cross-check verification: `uv run pytest -q` — `1525 passed in 4.83s`; removed
  tests were phrase, fixed-schedule, or orphan-artifact detectors rather than behavior.
- The six-plugin Codex marketplace was temporarily registered and installed from this
  worktree. That registration was removed because a stable marketplace must not point at a
  disposable worktree. A fresh ephemeral Codex process had independently selected
  `executing-an-implementation-plan` from the installed cache and reported the corrected
  checkpoint → complete mechanical/sanity verification → human UAT → normalization order.
- The first human CLI run was invalidated after inspection showed that Codex had loaded a
  stale pre-rewrite plugin cache. The corrected run loaded
  `denubis-plan-and-execute/4.0.1`, demonstrated the intended checkpoint and final-UAT
  lifecycle, and preserved the feature branch without normalization.
- Brian rejected that corrected run on proportionality. A three-file greeting change
  automatically invoked project-memory retrieval, performed irrelevant prior-chat
  searches, loaded six overlapping workflow skills, copied the supplied plan into another
  tracker, narrated routine transitions, and manufactured a disposable defect to re-prove
  a secondary Git hygiene check. Functional output passed; workflow UAT did not.
- The correction makes ordinary plan execution self-contained and proportional, and makes
  Codex project-memory retrieval explicit. A fresh actor-only source evaluation produced
  one private checkpoint without another tracker or reported workflow fan-out; repository
  inspection found no oracle failure. A fresh installed-runtime UAT is still required for
  transient skill-load, search, and narration behavior.
- The duplicated old skill tree and its 37 global Codex symlinks were retired after the
  invalid first acceptance. That cleanup is isolated on its own branch and remains
  reversible; Ponytail, Gemini adapter files, and all pre-existing uncommitted
  old-repository work remain.
- The existing canonical commits remain independently coherent. The failed-UAT correction
  and updated-main merge remain visible as private checkpoints; no normalization or main
  integration is authorised before corrected installed-runtime UAT acceptance.
