# Work completed

## 2026-08-21 — Root-cause diagnosis

- Git reflog established that Codex created `provider-mirror-uat` in the primary checkout
  on 2026-08-17 and never returned it to `main`.
- Archived session `01a007ae-7f19-7dd1-aef9-603cc1e29513` established that Codex selected
  and later published the branch after an unnamed commit/marketplace/push request.
- Git history identified the policy regression in `d057d4b` and `d1321f3`: private
  checkpoints became feature-branch-only, integration defaulted to leaving the branch,
  and protected-base commits required the branch to be named.
- Current state was positively resolved: local `main` is ten commits ahead of
  `origin/main`; `provider-mirror-uat` is three commits ahead of local `main` and tracks
  the same-named remote branch.

## 2026-08-21 — Lifecycle clarification

- Isolation is desirable during implementation: use a task-owned branch or worktree, and
  require it when concurrent agents, overlapping files, or unrelated dirty state make the
  default checkout unsafe.
- If work would begin on the default branch, warn first and proceed there only after human
  assent.
- Preserve private checkpoints through human UAT. After acceptance, normalize them;
  `commit, marketplace, push` for skill development means complete delivery through the
  intended default branch and cleanup, not publication of the current feature ref.
- A scratch RED actor launched under the earlier interpretation was interrupted before it
  could produce evidence. Its oracle was corrected rather than counting the invalid run.

## 2026-08-21 — Implementation and release evidence

- Planning and execution skills now keep stable plans, unresolved todos, and completed
  worklogs separate; resume instructions point to those durable owners.
- Workspace guidance now selects isolation from concurrency, overlap, and dirty-state
  evidence, and requires warning plus human assent before work begins on the default
  branch.
- Commit and finishing guidance now treats an authorized skill/plugin release as delivery
  through the intended default branch, with exact remote verification and task-owned
  cleanup rather than publication of the current branch.
- Claude and Codex manifests agree at `denubis-plan-and-execute` 4.1.3 and
  `denubis-git-commit` 1.3.1; the Claude marketplace carries the same versions.
- `tests/test_marketplace_sync.py` and `tests/test_codex_marketplace.py`: 29 passed.
- The broader suite reached 479 passed before the unrelated hook-launcher test timed out
  while spawning `uv`; no dependency operation was retried. `git diff --check` passed.
