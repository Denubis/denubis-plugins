# denubis-git-commit — Context (Level 0)

> System boundary: one discoverable shared skill that records an authorized coherent
> outcome as a local Git commit without publishing it.

## Context

```mermaid
flowchart LR
    H[Human or approved execution lifecycle]
    A[Claude Code or Codex session]
    S[Shared commit skill]
    G[Git repository]

    H -->|bounded commit authority| A
    A -->|loads provider-neutral procedure| S
    S -->|inspect, stage owned paths, commit| G
    G -->|status, diff, log, new commit id| A
```

## Current contracts

| Boundary | Contract |
|---|---|
| Authority | A direct commit request or an approved plan's private-checkpoint lifecycle authorizes the owned local commit. A combined skill/plugin release request routes onward to default-branch delivery; it never authorizes pushing the current task branch. |
| Workspace | Concurrent or overlapping work uses task-owned isolation. Before the first edit on the default branch, warn and obtain human assent; at commit time, do not invent a branch to relocate completed default-branch work. |
| Outcome | Stage one coherent completed outcome rather than files grouped by authoring chronology. If the changes cannot be explained as one outcome, separate them by behavior and dependency. |
| Preflight | Inspect repository root, branch, worktree status, staged and unstaged diffs, untracked files, recent message convention, and applicable project instructions before mutation. |
| Documentation | Update living documentation when the changed behavior makes it false. Do not turn commit messages into the only durable design or operating documentation. |
| Verification | Run the checks that own the staged behavior, inspect the exact staged diff, commit through literal stdin or a message file, then verify the resulting commit and remaining status. |
| Lifecycle | Private checkpoints may be frequent on an isolated task branch. Fix rounds and superseded checkpoints fold into their coherent outcome only after accepted finished-work human UAT; integration, publication, and cleanup are verified delivery steps. |

The skill is discoverable in Codex metadata and can also be invoked explicitly.
Discovery supplies the procedure; commit authority still comes from the human or an
approved lifecycle. Claude's `/commit` remains available. A quoted Bash heredoc can
supply the message to `git commit -F -`; other hosts may use a literal message file.
Neither provider may infer permission to push from permission to commit.

## Packaging

- Shared procedure: `plugins/denubis-git-commit/skills/commit/SKILL.md`.
- Claude manifest: `plugins/denubis-git-commit/.claude-plugin/plugin.json`.
- Codex manifest: `plugins/denubis-git-commit/.codex-plugin/plugin.json`.
- Codex invocation policy:
  `plugins/denubis-git-commit/skills/commit/agents/openai.yaml`.
