# ADR 2026-11-15-bbs-plans-run-agents-in-worktrees — implementation plans run independent work with several agents, each in a skill-made worktree that is cleaned up

**Status:** Accepted (2026-11-15). Records human rulings. Applied in
`denubis-plan-and-execute` 4.3.0. It extends the private-checkpoint lifecycle that the
planning and execution skills already carried; ADR 2026-11-08-bbs-proposer-never-verifies
still holds for the final fresh verification.

## Authority evidence

Claude Code session `c06f9205-3224-4dbf-b681-82abb13bdb37`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl`.
Times are UTC on 2026-11-15. The `queued_command` attachments are messages Brian sent
while the assistant was working.

- Line 9, human, record `4b931702-e597-4100-9a99-be37031905e1` (04:35:35.506Z): "3 things
  to change, 1) implementation planning should plan how to execute the design plan with
  multiple agents, both to do and to check, so it can be both multithreaded and efficient
  with worktrees, 2) it should specify cleaning up worktrees when done, …"
- Line 1038, attachment record `36d79326-7990-4e22-8fcb-d95dc1f67e95` (05:07:09.835Z):
  "and we should not use helper agent worktrees, unless there's a really really good
  reason for not using the skill's worktree".
- Line 1327, human, record `45cd9c41-8ce2-4612-9399-16a9b01ac735` (05:15:51.324Z),
  answering the question-zone question "Should your approval of a plan whose cleanup step
  names the agent branches it creates count as your say-so to delete each of those
  branches once it is merged?", whose context said the cleanup step would use git's safe
  delete, which refuses any branch not fully merged: "yes".
- Line 1328, attachment record `5eb143d6-f248-47c5-9e33-4fb8c8cf6d1a` (05:16:11.466Z):
  "and commits inside these spawned sub-worktrees are authorized".
- Line 1339, attachment record `ce91e4f1-c9b4-470c-af9f-4423ca5e6f22` (05:16:25.158Z):
  "and the final merge is also permission to commit once we discuss".
- Line 2970, human (2026-11-15), after the assistant described how the
  coordinating session joins each agent branch into the task worktree: "then yes, I want
  those subworktrees merged into the main worktree without issue?"
- Lines 2976 and 2991, human (2026-11-15), about the last merge,
  from the task branch into main: "no, that's for me to normally authorize" and "that's
  not automatic".
- Line 3009, human (2026-11-15): "I just don't want to babysit commits and
  squashing commits of subworktrees into a single coherent set of (few) commits for the
  worktree".
- Line 3025, human (2026-11-15): "and that squash is authorized, because
  there's no way to integration test without merging, and no way to merge without
  committing, sooooo".
- Line 2942, assistant, record `4ce24fb6-4471-4f07-9e15-fccfcec82aee` (06:16:50.953Z),
  the question as put through the question zone. Its context, in full: "The new planning
  rules say that approving an implementation plan also authorises its final merge into
  the main branch, once you have discussed the finished work and accepted your hands-on
  check. The reviewer found that this cannot happen as written: the merge procedure the
  rules point to is set so that only a person can start it, by typing its slash command,
  and a session that tries is blocked. That procedure's cleanup also deletes the task
  branch along with the worktree, which the plan's approval does not cover. Your answer
  decides whether I change the merge procedure so a session can run it under a plan's
  approval (removing the worktree but keeping the branch), or change the planning rules
  to say that you start the merge yourself." Its question: "After you have accepted a
  plan's finished work, should the session run the merge into main itself, rather than
  you typing the merge command?"
- Line 2987, assistant, record `733b0a24-9e8b-419f-84b0-bf0e7bbde492` (06:19:20.431Z):
  the assistant withdrew that question from the question zone, after lines 2976 and 2991.
- Line 3038, human, record `2c673284-3d0f-4008-8e98-4767d4f9a86c` (06:24:38.663Z),
  given after that withdrawal, verbatim: `""After you have accepted a plan's finished
  work, should the session run the merge into main itself, rather than you typing the
  merge command?"" no`.
- Line 3049, human, record `93d51067-12ba-45f9-a134-cb238ee30bd6` (06:24:53.190Z): "just
  killed that question zone... thing".

A later ruling, on a typed delivery request, comes from Claude Code session
`7f501634-c03c-4433-8523-95513d15bd18`, transcript
`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/7f501634-c03c-4433-8523-95513d15bd18.jsonl`.
Times are UTC on 2026-11-17 (2026-11-18 in Sydney).

- Line 336, assistant, record `9e5b238a-03e6-4932-8c82-38e5ad63d12a` (23:01:04.150Z),
  the question as put through the question zone. Its context, in full: "On 15 November
  you were asked 'After you have accepted a plan's finished work, should the session run
  the merge into main itself, rather than you typing the merge command?' and you answered
  'no'. Older wording in the plan-and-execute and git-commit plugins, written before
  that answer and already released, says something different for one case: when you
  type a delivery request such as 'ship' or 'commit, marketplace, push' for a skill
  or plugin change, the session itself merges into main, pushes and cleans up. A review
  of the unmerged planning change found the two rules side by side, and nothing records
  which one wins. If you answer yes, the older wording stays and a typed 'ship' remains
  your order for the session to do the whole delivery, merge included. If you answer no,
  I will have the older wording changed so that even after 'ship' the session prepares
  everything and hands you the merge command to run." Its question: "When you type
  'ship' or 'commit, marketplace, push', should the session itself run the merge into
  main?" (Inner quotation marks shown as single; the record has double.)
- Line 367, human, record `c36b097d-7b93-4be0-a197-a9a375908c48` (23:09:40.507Z),
  quoting that question: "yes".

Exact raw resolver:

```sh
sed -n '9p;1038p;1327p;1328p;1339p;2942p;2970p;2976p;2987p;2991p;3009p;3025p;3038p;3049p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/c06f9205-3224-4dbf-b681-82abb13bdb37.jsonl
sed -n '336p;367p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/7f501634-c03c-4433-8523-95513d15bd18.jsonl
```

The final merge from the task branch into the integration branch is not covered by the
plan's approval: Brian authorises it at that point. The assistant reads line 1339 with
that ruling: Brian's authorisation of the final merge, given once the finished work has
been discussed, also permits that merge's commit. That reading is the assistant's.

## Context

Before this change, a plan named outcomes, their dependencies and their evidence, but not
how agents would split them, so execution ran one outcome at a time. A worktree skill
created isolation and claimed no cleanup authority; cleanup happened only at delivery.

Documented by Claude Code's worktrees page (https://code.claude.com/docs/en/worktrees,
read 2026-11-15): a subagent's own worktree (`isolation: "worktree"`) branches from the
remote's default branch unless `worktree.baseRef` is `"head"`, and cannot be set to a
branch name. It is removed automatically only when the subagent made no changes; a
worktree with work stays until a periodic sweep can remove it without losing work. A
research subagent's survey of multi-agent coding practice, read the same day, found that
parallel work paid off when the work was split into tasks with disjoint files and
independent checks, and that a checker which did not share the implementer's context
worked best. Those findings are leads with their own citations, not measurements of this
repository.

## Decision

A plan carries an execution layout:

- work runs at the same time only when it edits no common file and has its own check
  that can fail; each shared file has one owner; dependent work waits for its join;
- each concurrent implementer works in a worktree and branch the coordinating session
  creates from the task branch through the worktree skill, not a runtime's own agent
  worktree unless the plan records a compelling reason (line 1038);
- each piece has a checker that did not write it, which reads the recorded results and
  runs only the narrowest falsifying check;
- verified branches join the task branch one at a time, with a combined re-check after
  each, their checkpoints squashed first into a few coherent commits; and
- each agent worktree is removed, and its branch safely deleted, once its join passes
  (lines 9 and 1327). Line 9 asks for "cleaning up worktrees when done"; reading it as
  removing each agent worktree once its join passes is the assistant's.

Approving and executing the plan authorise, without further prompts, commits in the agent
worktrees (line 1328), the joins (line 2970), the commits and squashes on the
task branch that keep it to a few coherent commits, before integration testing (lines
3009 and 3025), and that cleanup. Squashing each agent branch
before it joins, so that the safe delete of line 1327 still finds it merged, is the
assistant's design. The final merge into the integration branch is never automatic:
Brian authorises it at that point (lines 2976 and 2991), and that
authorisation also permits its commit (line 1339, as read above). After Brian accepts the
finished work, he starts that merge by running the merge command himself; the session
does not run it, and hands him the command instead (line 3038). A delivery request Brian
types, such as `ship` or `commit, marketplace, push` for a skill or plugin change, is his
order for the session itself to run the whole delivery, the merge into main included
(line 367 of session `7f501634`). The task worktree is
removed, and the task branch deleted, only as Brian names then; pushing and publication
keep their own say-so.

## Open items

- The routes into `merge-to-main` cannot run as written. That skill is
  `disable-model-invocation: true`, so a session cannot start it, yet
  `finishing-a-development-branch` has a requested local merge invoke it, and its direct
  delivery passes push and cleanup authority to it. With the line-367 ruling, a session
  told to deliver after `ship` is sent to run the merge through a skill it cannot start.
  Unresolved; neither the skill's setting nor a merge path outside it has been changed.

## Consequences

- Applied in `plugins/denubis-plan-and-execute/skills/impl-plan-write/SKILL.md`,
  `starting-an-implementation-plan`, `executing-an-implementation-plan`,
  `using-git-worktrees` and `finishing-a-development-branch`, with the plugin README and
  `docs/architecture/plugins/denubis-plan-and-execute/0-context.md`.
- A single coupled outcome keeps one implementer and gets no layout beyond saying so.
- Evaluated with the skill-eval case
  `tests/skill-evals/plan-and-execute/parallel-execution-planning/` and the existing
  `outcome-planning` case as a control; the results are recorded in the release's
  changelog entry.
- Not yet observed in a real plan's execution.
