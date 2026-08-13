# Instruction-control review rubric

Use this rubric when reviewing changes to the global or project instructions,
`denubis-plan-and-execute`, its bundled agents, or the instruction-control architecture.
These are judgment expectations, not automated acceptance criteria.

Open the changed documents and their consumers. Evaluate the scenarios below without
searching for prescribed wording. For each defect, return the exact source location, the
scenario that fails, the consequence, and the smallest observation that would confirm or
falsify it. Do not return an approval token or a general verdict.

## Always-on instructions

- The global Claude and Codex files contain only cross-project invariants that remain useful
  throughout a session. Situational procedures have a named skill or executable owner.
- The project file contains project runtime boundaries, repository contracts, and finding
  aids without duplicating the global file or preserving incident arguments.
- Each rule changes an identifiable action. A reminder with no distinct boundary or
  consumer is removed rather than restated.
- A non-trivial task entry can identify its goal, applicable procedure, relevant memory or
  feedback, and accepted decisions before mutation. Open-ended work decomposes around
  materially different protected decisions rather than presenting a batch questionnaire.
- Any cited local Codex authority source remains under parsed `save-all` history with no
  byte cap; a prose assurance or existence check is not retention evidence.

## Design and planning

- The workflow inspects recoverable facts before asking the human and asks one question
  only when the answer changes the design.
- Alternatives represent materially different designs; the workflow does not manufacture
  options to satisfy a fixed count.
- A design records present evidence, authority sources, decisions, exclusions, and
  acceptance criteria without committing, publishing, or describing future state as
  implemented architecture.
- An implementation plan can be executed without reconstructing the design conversation.
  It contains exact paths, dependencies, acceptance ownership, automated checks, and only
  irreducible human judgments.
- Every implementation plan states whether it changes meaningful data or control flow.
  Applicable plans map the predicted system boundary, participants, flows, contracts,
  failure routes, consumers, and inter-phase seams breadth-first. Non-applicable plans name
  the specific preserved boundary rather than emitting an empty diagram.
- Execution derives implemented flow independently and compares it with the prediction. A
  change in internal how updates living architecture; a load-bearing change in what is
  fixed or resolved through an accepted design and ADR carrying why. Model agreement does
  not ratify drift.
- The implemented map starts from a complete bounded-change inventory before comparison
  with the prediction. Every changed code, schema, configuration, generated, and runtime
  surface is accounted for; neither an omitted flow nor an empty search self-certifies
  conformance. Architecture maintenance runs only when a current architecture-owned claim
  or reference actually needs to change.
- UAT planning maps the built surface and its existing-system seams before selecting
  individual probes. The agent supplies actions covering wanted and plausible unwanted
  behavior; one narrow success case does not silently exhaust the human-judgment boundary.

## Execution and debugging

- Direct work is possible without mandatory delegation, repeated model review, context
  clearing, checkpoint commits, or workflow certificates.
- Existing user work is preserved. Commit, push, publication, deployment, and destructive
  cleanup remain separate authorities.
- Completion claims point to fresh observable evidence. Model reports and green review
  verdicts remain leads.
- Debugging establishes and falsifies a causal hypothesis before the minimal fix. It stops
  after three failed fixes for the same condition and restores the last verified owned
  state.

## Review, challenge, and UAT

- Review is read-only unless separately authorised and returns evidence-bearing candidate
  defects rather than an approval state.
- Proleptic challenge presents only a supported uncertainty that could change action; it
  does not manufacture objections or burden the human with an unfiltered list.
- UAT contains only judgments automation cannot make. Each entry presents one falsifiable
  claim and the built surface on which the human can decide it.
- A UAT judgment can still fail after every automated prerequisite passes. If automated
  facts settle the verdict, or a multi-step scenario reduces to separately automatable
  checks, it belongs in test requirements.
- Informed observers could reasonably disagree about a genuine UAT result. Mixed entries
  are split so a deterministic boundary cannot be laundered by attaching experiential
  wording.

## Agents and analysis tools

- Mutating workers stay within the supplied task, preserve unrelated changes, and do not
  commit, push, publish, deploy, or destructively restore the workspace.
- Reviewers are read-only. Their findings cite current sources and discriminating checks;
  no status file or token binds later work.
- Refactoring, architecture, and assumption tools operate only on a named question with a
  consumer. Metrics, smell names, frameworks, and self-critique do not authorise work.
- Model guidance names only the current roster and current operational differences.
  Volatile vendor claims cite a primary vendor page and verification date; operator
  routing rules point to the exact human record and resolver. Superseded tiers and
  correction narratives remain in Git rather than a live reference file.

## Git and terminal lifecycle

- Worktree creation, pull-request creation, local merge, branch finishing, and dependency
  upgrades perform only their named action and report the resulting external state.
- No procedure silently rebases, edits issue metadata, deletes branches or worktrees,
  relocates caches, invents setup files, or creates commits outside explicit authority.
- A substantial tmux session exposes a short repository-and-purpose name and verifies the
  actual window changed, without model dispatch or persistent naming state.

## Testing

Authority: `/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl:9797`,
bound as `TEST01` in the instruction-control candidate manifest.

- Automated checks exercise behaviour, parse a declared structure, or compute a property
  independently of the edit that satisfies them.
- A test does not lock prose by asserting that selected words appear or disappear from a
  source document. Rewording with unchanged meaning does not fail automation.
- Empty-result gates have a positive control and a stated coverage boundary.
- Expectations that require reading and judgment remain in this rubric or another named
  rubric. A reviewer reports evidence against them; no exact-string test stands in for
  that reading.
