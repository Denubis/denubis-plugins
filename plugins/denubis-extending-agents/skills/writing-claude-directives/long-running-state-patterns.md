# Long-running state patterns

Optional reference for work that may cross context compaction, a cleared session, or a
handover. The goal is recoverable task state, not a second narrative of the conversation.

## Choose the existing owner first

| State | Durable owner |
|---|---|
| Implemented behaviour | Code, tests, and current architecture |
| Work still required by an accepted plan | Current implementation-plan phase |
| Deferred defect with a future consumer | Existing issue tracker |
| Project observation or preference | Human-approved project `.notes/` record |
| Human ruling | Original transcript record plus exact resolver |
| Verification result | Output bound to the artifact and invocation it checked |

Do not create a generic progress file when one of these owners already exists. Do not use
an experimental model-memory store as durable project memory.

## Minimal handover state

Before a context boundary that could lose working state, record only what the next session
cannot cheaply reconstruct:

```markdown
## Current task

- Goal: <current authorised outcome>
- Repository/worktree: <absolute path and branch>
- Current owner: <phase, issue, or source file>
- Changed surface: <paths, not a prose replay>
- Last verified evidence: <command, result, subject identity>
- Unresolved blocker: <one concrete condition, or none>
- Next action: <one executable step>
- Exclusions: <nearby work deliberately not authorised>
```

Put this state in the accepted implementation plan, issue, or other named owner. A
standalone handover is temporary and should be consumed or deleted when its contents reach
their real owners.

## Crossing the boundary

1. Read the current project instructions and the named state owner.
2. Confirm the repository, worktree, branch, and dirty state rather than trusting the
   handover's label.
3. Re-run the smallest positive check that establishes the working baseline.
4. Resume from the recorded next action.
5. Update the owner when the state changes; do not append correction layers.

Use `/compact` or `/clear` only when the context boundary is useful. A clear session is not
a completion criterion. Preserve durable state before clearing; do not ask the model to
summarise work that the repository and tests already reveal.

## Direct work and delegation

Direct implementation is the default. Delegate only an independent, bounded subproblem
when the task permits it and the separate context or expertise adds value. The main
session keeps responsibility for scope, evidence review, and integration. A delegated
summary is a lead, not durable state or proof of completion.

When model selection matters, consult [`model-tier-notes.md`](model-tier-notes.md) for the
current roster and its raw authority sources. Do not copy model versions into this file.

## Verification across sessions

- Bind evidence to the exact artifact, revision or full digest, command, and relevant
  environment.
- Rerun a check after the subject changes; do not carry a green label forward.
- Record an expected red gate as red with its blocking condition. Do not relabel it green
  because the failure was anticipated.
- Keep user acceptance focused on judgment automation cannot settle.

## Failure modes

| Failure | Repair |
|---|---|
| Next session repeats discovery | Put the map and next action in the current owner. |
| Handover claims work is complete | Open the artifact and rerun its verification. |
| Progress file duplicates an issue or phase | Move the current consequence to the owner and remove the duplicate. |
| Context clear loses an unresolved decision | Record the exact human source and dependent action before clearing. |
| Delegated summary becomes accepted fact | Resolve its cited evidence and separate observation from inference. |
| Checkpoint commit, stash, branch, or worktree is invented | Use only lifecycle actions already authorised by the task. |

## References

- [Anthropic: effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic: effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

Vendor references verified 2026-08-12. Their examples do not override project authority,
repository lifecycle rules, or the boundary of the current request.
