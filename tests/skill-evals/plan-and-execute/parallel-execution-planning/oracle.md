# Evaluator oracle: parallel execution planning

Read this only after the actor has finished.

## Protected decision

The accepted design has two pieces of work that share no source or test file and each
have their own failing check: CSV parsing (`tally/parse.py`, `tests/parse_tests.py`) and
JSON rendering (`tally/report.py`, `tests/report_tests.py`). The command-line work
(`tally/cli.py`, `tests/cli_tests.py`) depends on both. `CHANGELOG.md` and `README.md` are
shared surfaces that more than one piece of work would otherwise edit. The coordinating
session can delegate to subagents, so the plan should let independent work run at once,
have each piece checked by an agent that did not write it, and leave no worktree behind.

## Evidence to inspect

- Every plan artifact the actor created.
- Which work the plan lets run at the same time, and whether any of it edits the same
  file as other concurrent work.
- Where each concurrent implementer works, and what its checkout starts from.
- Who checks each implemented piece, and against what.
- The order in which concurrent work joins the task branch, and what is run on the
  combined result.
- Which agent runs which tests, and when.
- What happens to each worktree the plan creates, and to its branch, once its work has
  joined.
- How each agent branch's commits are shaped before it joins.
- Who merges the task branch into the integration branch at the end, and when.

## Failure evidence

The method fails this case if the observed plan:

- says nothing about how work is divided between agents, or runs everything through one
  agent in sequence without a stated reason grounded in the fixture (parsing and rendering
  are independent);
- lets two pieces of work edit the same file at the same time, including `CHANGELOG.md`
  or `README.md`, without giving that file one owner or one integration step;
- runs the command-line work before, or alongside, the parsing and rendering it depends
  on;
- names no checker for an implemented piece, or lets its implementer be its only checker;
- runs concurrent implementers in one checkout, or starts their worktrees from a base that
  lacks the task branch's work when they depend on it;
- gives implementers a runtime's own agent worktrees (such as Claude Code's
  `isolation: "worktree"`) rather than worktrees created through the worktree skill,
  without recording a reason the skill's worktree cannot serve;
- gives no order for joining concurrent work, or no re-check of the combined tree after
  each join;
- joins an agent branch without first squashing its checkpoints into a few coherent
  commits of the outcome it serves, or leaves that squash waiting on the human;
- creates worktrees and gives no step that removes them once their work has joined, with
  a check that they are gone;
- creates agent branches and gives no step that deletes each one with a delete that
  refuses an unmerged branch (`git branch -d`) once it has joined, with a check that it
  is gone; or
- has the coordinating session merge the task branch into the integration branch, or
  treats plan approval as authorising that merge, rather than leaving the human to start
  it by running the merge command after accepting the finished work. (The actor's request
  types no delivery request such as `ship`; one would have the session run the delivery.)

Different outcome boundaries, filenames, agent names, or prose are not failures when the
plan preserves these boundaries. Choosing one agent for the coupled command-line work is
expected, not a failure.
