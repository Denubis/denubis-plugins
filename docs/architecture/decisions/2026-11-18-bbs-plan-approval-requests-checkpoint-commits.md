# ADR 2026-11-18-bbs-plan-approval-requests-checkpoint-commits — Approving a plan's execution is the explicit request for local checkpoint commits on that plan's work branch

**Status:** Accepted (2026-11-18). Records a human ruling. Applied the same day to the
global instruction files `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` (line 119 of
each), which this repository does not track. No plugin text changed.

## Authority evidence

Claude Code session `7f501634-c03c-4433-8523-95513d15bd18`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/7f501634-c03c-4433-8523-95513d15bd18.jsonl`.
Times are UTC on 2026-11-17 (2026-11-18 in Sydney).

- Line 107, assistant, record `7a3dc237-1225-487d-9d75-af04ad649bf0` (22:01:48.283Z): the
  question as put through the question zone, with its context. The question: "Should
  approving a plan's execution count as your explicit request for local, unpushed
  checkpoint commits on that plan's own work branch?"
- Line 114, human, record `2d236aec-cd80-498a-b7bb-3d388b09c4e5` (22:02:41.452Z), quoting
  that question. Brian, verbatim: "yes, I believe I have already said this, but yep."

Exact raw resolver:

```sh
sed -n '107p;114p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/7f501634-c03c-4433-8523-95513d15bd18.jsonl
```

The earlier statement Brian refers to was not located by search: two `cc-search-chats`
literal searches on 2026-11-18 timed out and returned no result. The nearest recorded
ruling is narrower: ADR 2026-11-15-bbs-plans-run-agents-in-worktrees, line 1328 of
session `c06f9205-3224-4dbf-b681-82abb13bdb37`, "and commits inside these spawned
sub-worktrees are authorized". Whether that is the statement he meant is unconfirmed.

## Context

The global instruction files said, since February 2026, "Never commit unless explicitly
requested". Since August 2026 `executing-an-implementation-plan` has said that approving
a plan's execution authorises local private checkpoint commits on the isolated task
branch "unless the human or project explicitly prohibits them". Sessions read the global
line as that prohibition. A supervising session in another project made no checkpoints
through two designs, two plans and the build work, and a permission check refused its
attempt to start checkpointing; its report is quoted in the first human message of the
session above (line numbers not recorded here).

## Decision

Approving an implementation plan's execution is the explicit request for local, unpushed
checkpoint commits on that plan's own work branch. The global line now reads:

> Never commit unless explicitly requested. Approving an implementation plan's execution
> is that request for local, unpushed checkpoint commits on the plan's own work branches
> (its task branch and the agent branches it names), never on the default branch.
> Pushing, merging into the main branch, or deleting a branch needs the human's explicit
> say-so

"Work branches" is plural so the line does not narrow the 2026-11-15 ruling that commits
inside a plan's agent worktrees are authorised (ADR
2026-11-15-bbs-plans-run-agents-in-worktrees, line 1328 of that session). The plural is
the assistant's reconciliation of the two rulings, not a separate human answer.

## Consequences

- The 2026-11-15 ruling that approving a plan which names its agent branches is the
  say-so to safe-delete each once merged (line 1327 of that session) still holds; this
  ruling did not address branch deletion.

- A commit outside an approved plan's execution still needs a direct request.
- Pushing, merging into the main branch and deleting a branch are unchanged by this
  ruling.
- The edited global files are local to this machine until the settings sync is pushed.
- Unproven as of 2026-11-18: that a session's permission check accepts a checkpoint
  under the new wording. No session has tried one since the edit.
