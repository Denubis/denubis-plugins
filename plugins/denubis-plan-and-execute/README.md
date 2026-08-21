# denubis-plan-and-execute

Design, outcome planning, implementation, verification, architecture, and Git-lifecycle
procedures.

    human intent
        ↓
    accepted design
        ↓
    stable plan + pending todo + completed worklog
        ↓
    coherent implementation outcomes in task-owned isolation
        ↓
    mechanically verified finished surface
        ↓
    human implication-level UAT
        ↓
    normalized private history and selected integration

Stage boundaries exist only where authority, evidence, recoverability, or safe next actions
change. They are not a required narration format.

## Main workflow

### Design

    /denubis-plan-and-execute:starting-a-design-plan <request or topic>

The design workflow inspects project evidence, resolves one material decision at a time,
and writes one current design under docs/design-plans/. Living architecture changes only
when implementation changes the system.

### Outcome planning

    /denubis-plan-and-execute:starting-an-implementation-plan <absolute-design-path>

Planning creates one directory with `plan.md`, `todo.md`, and `worklog.md`. The plan owns
stable outcomes, the todo owns unresolved work, and the worklog owns completed work and
evidence. It splits outcome files only when independently resumable loading makes that
useful. Boundary-flow, verification, and UAT appendices exist only when they have a real
cross-outcome consumer.

### Execution and acceptance

    /denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-path> <absolute-working-directory>

Before editing, execution applies an isolation rubric. Concurrent agents, overlapping
files, or unrelated dirty state require a task-owned worktree. An existing task-owned
branch or worktree is suitable. Work on the default branch begins only after a warning and
human assent.

The main session executes directly by default. Behavior changes use the project-native
red-green-refactor cycle; operational work uses a real consumer or positive probe.
Mechanical gates, an independent sanity pass, documentation reconciliation, and complete
diff/status inspection precede human UAT.

Executing an approved plan authorises private checkpoint commits on its isolated task
branch without routine prompts. It does not authorise pushing or publication. Fix rounds
and superseded checkpoints fold into coherent outcomes only after the human accepts UAT on
the finished implication. Normalization must preserve the exact accepted tree and is
reverified before integration. A selected delivery route integrates the accepted tree,
pushes the intended branch when authorised, verifies the remote ref, and removes only the
task-owned branch or worktree. Skill-development requests such as `commit, marketplace,
push` mean that complete delivery, not publication of the current feature ref.

During execution, finished items move from `todo.md` to `worklog.md`; the files never
become a mixed checked-task ledger. A resume instruction points to the plan, todo, worklog,
and working root rather than copying their contents.

## Explicit lifecycle skills

- using-git-worktrees: create and verify one isolated checkout.
- systematic-debugging: establish a cause and fix only the demonstrated mechanism.
- maintain-architecture: reconcile current implementation and living architecture.
- controlled-dependency-upgrade: audit or upgrade one direct dependency at a time.
- critical-peer-review: falsify a bounded artifact against current evidence.
- restate-our-assumptions: test a scoped assumption.
- make-pr: verify, push, create, and read back one pull request.
- merge-to-main: perform and verify one local integration.
- exec-session-naming: optional tmux-window naming.

Worktree cleanup, history rewriting outside the private feature series, destructive
discard, publication, and deployment retain separate authority.

## Agents and project guidance

Bundled agents are provider-specific role adapters for bounded implementation, review, and
analysis. Their report is a lead; the main session inspects their diff or cited evidence
and reruns relevant checks.

Optional project guidance lives at .ed3d/design-plan-guidance.md and
.ed3d/implementation-plan-guidance.md. /how-to-customize describes these files.
/flesh-it-out provides standalone clarification.

## Claude runtime surfaces

The Claude package includes a SessionStart adapter that keeps the crash-recovery plugin's
live-transcript marker current, plus the claudew wrapper and workflow statusline. The
live-marker contract is Claude-specific and is not part of provider-neutral planning
semantics. Textual pre-write quality detectors are not shipped.

See the [architecture context](../../docs/architecture/plugins/denubis-plan-and-execute/0-context.md).
