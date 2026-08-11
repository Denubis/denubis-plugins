# Instruction-control review rubric

Use this rubric when reviewing changes to the global or project instructions,
`denubis-plan-and-execute`, its bundled agents, or the instruction-control architecture.
These are judgment expectations, not automated acceptance criteria.

Open the changed documents and their consumers. Evaluate the scenarios below without
searching for prescribed wording. For each defect, return the exact source location, the
scenario that fails, the consequence, and the smallest observation that would confirm or
falsify it. Do not return an approval token or a general verdict.

## Always-on instructions

- The global file contains only cross-project invariants that remain useful throughout a
  session. Situational procedures have a named skill or executable owner.
- The project file contains project runtime boundaries, repository contracts, and finding
  aids without duplicating the global file or preserving incident arguments.
- Each rule changes an identifiable action. A reminder with no distinct boundary or
  consumer is removed rather than restated.

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

## Git and terminal lifecycle

- Worktree creation, pull-request creation, local merge, branch finishing, and dependency
  upgrades perform only their named action and report the resulting external state.
- No procedure silently rebases, edits issue metadata, deletes branches or worktrees,
  relocates caches, invents setup files, or creates commits outside explicit authority.
- A substantial tmux session exposes a short repository-and-purpose name and verifies the
  actual window changed, without model dispatch or persistent naming state.

## Testing

- Automated checks exercise behaviour, parse a declared structure, or compute a property
  independently of the edit that satisfies them.
- A test does not lock prose by asserting that selected words appear or disappear from a
  source document. Rewording with unchanged meaning does not fail automation.
- Empty-result gates have a positive control and a stated coverage boundary.
- Expectations that require reading and judgment remain in this rubric or another named
  rubric. A reviewer reports evidence against them; no exact-string test stands in for
  that reading.
