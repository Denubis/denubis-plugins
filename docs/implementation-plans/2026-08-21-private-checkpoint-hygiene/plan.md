# Private checkpoint hygiene

## Required behavior

- Execution may create local checkpoint commits on an isolated branch or worktree while
  work is in progress. Keep that isolation through mechanical verification and human UAT;
  do not normalize provisional history before acceptance.
- Select the workspace through an explicit rubric: concurrent agents, overlapping files,
  or unrelated dirty state require isolation; an existing task-owned branch or worktree is
  suitable; starting on the default branch requires a warning and human assent before the
  first edit there.
- After accepted UAT, fold provisional commits into coherent outcomes. A delivery request
  then integrates the accepted tree into the intended branch, verifies it, and removes the
  internal branch or worktree.
- Never publish an internal checkpoint ref. For skill development, `commit, marketplace,
  push` or `ship` is a delivery request: update the release metadata, integrate the
  accepted tree into the intended default branch, push and verify that branch, then clean
  the temporary branch or worktree. The checkout alone never selects the destination.
- Keep durable pending work in `todo.md`. Move completed work and its evidence to
  `worklog.md`; do not turn either file into a mixed status ledger.
- A resume instruction points to the plan, todo, worklog, and working root. It does not
  duplicate their contents.

## Evidence

- The observed pre-change failure is the current repository: after accepted work and an
  explicit commit/marketplace/push request, Codex published `provider-mirror-uat` and left
  the default branch and cleanup unfinished.
- The execution fixture's hidden oracle requires private isolation through UAT, distinct
  todo/worklog ownership, and pointer-only resume text.
- Provider manifests and marketplace versions must agree, the owning marketplace tests
  must pass, and the exact delivered default ref must be read back before cleanup.

## Integration boundary

The current `provider-mirror-uat` branch is the accidental published checkpoint surface.
After verification, fast-forward local `main` to the accepted tree, push `origin/main`,
verify the remote tree, then remove only `provider-mirror-uat` locally and remotely. Leave
all unrelated branches and worktrees untouched.
