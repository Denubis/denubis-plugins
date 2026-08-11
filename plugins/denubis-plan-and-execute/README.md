# denubis-plan-and-execute

Design, implementation, debugging, verification, architecture, and Git lifecycle
procedures for Claude Code.

The plugin separates three kinds of work:

```text
human request
    ↓
current design
    ↓
just-in-time implementation plan
    ↓
verified repository state
```

Each transition has one owner and one evidence boundary. The workflow does not create
commits, worktrees, reviews, pull requests, merges, deployments, or human gates merely
because the preceding stage finished.

## Main workflow

### 1. Design

Invoke:

```text
/denubis-plan-and-execute:starting-a-design-plan <request or topic>
```

The design workflow inspects the project directly, asks only about intent or material
tradeoffs that evidence cannot recover, compares genuine alternatives, and writes one
current design under `docs/design-plans/`.

Human-derived decisions carry an exact source locator and resolver. Proposed components
remain in the design plan; living architecture changes only when implementation changes
the system.

### 2. Implementation planning

Invoke the exact handoff returned by design:

```text
/denubis-plan-and-execute:starting-an-implementation-plan <absolute-design-path>
```

Planning uses the current workspace unless isolation is requested, required by project
instructions, or needed to avoid overlapping edits. It produces:

- `phase_##.md` files containing coherent tasks and acceptance ownership;
- `test-requirements.md` for automated and operational evidence; and
- `uat-requirements.md` for irreducible human judgment, which may contain no entries.

Planning inspects the repository directly. Delegated investigation and review are optional.
No model-authored stamp or verdict certifies the plan.

### 3. Execution

Invoke the exact plan and working directory:

```text
/denubis-plan-and-execute:executing-an-implementation-plan <absolute-plan-directory> <absolute-working-directory>
```

The main session executes one phase at a time by default. Behavior changes use the
project-native red–green–refactor cycle. Tests, type checks, builds, and operational
read-backs establish deterministic claims. Human UAT runs only for a planned item that
automation cannot decide.

Execution preserves pre-existing changes and does not commit, publish, deploy, or mutate
another system without separate authority.

## Explicit lifecycle skills

These user-invocable skills perform only their named action:

| Skill | Boundary |
|---|---|
| `using-git-worktrees` | Create and verify one isolated checkout |
| `systematic-debugging` | Diagnose a failure; fix only when the request includes a fix |
| `maintain-architecture` | Reconcile living docs with implemented state |
| `controlled-dependency-upgrade` | Audit or upgrade one direct dependency at a time |
| `critical-peer-review` | Read-only falsification review of a bounded artifact |
| `restate-our-assumptions` | Test a scoped assumption against current evidence |
| `make-pr` | Verify, push, create, and read back one pull request |
| `merge-to-main` | Perform and verify one local integration |
| `exec-session-naming` | Rename the tmux window containing the current pane |

`make-pr` does not merge or edit issue labels. `merge-to-main` does not push or delete the
feature branch. Worktree cleanup and destructive discard are separate actions.

## Optional agents

Bundled agents are bounded tools, not workflow stages. Implementors and fixers may edit
only their assigned scope and never commit. Reviewers are read-only and return exact-source
leads without approval tokens or persistent findings files. The main session verifies any
delegated result before acting on it.

The plugin does not require the research-agent or extending-Claude plugins to complete its
main workflow. Their specialists may be used when a bounded task genuinely benefits from
them.

## Project customization

Optional project guidance lives at:

- `.ed3d/design-plan-guidance.md`
- `.ed3d/implementation-plan-guidance.md`

`/how-to-customize` describes their supported shape. `/flesh-it-out` provides standalone
clarification without starting the full design workflow.

## Runtime surfaces

The plugin also ships:

- a `SessionStart` hook that updates the wrapper's live-transcript marker and emits no
  ordinary workflow prose;
- a `PreToolUse:Write|Edit` quality guard for its explicitly implemented banned patterns;
- the `claudew` wrapper and workflow statusline.

The hook, wrapper, and statusline report or control only their actual runtime boundaries.
They do not establish that a model followed a skill.

See the [architecture context](../../docs/architecture/plugins/denubis-plan-and-execute/0-context.md)
for the current system map and failure boundaries.
