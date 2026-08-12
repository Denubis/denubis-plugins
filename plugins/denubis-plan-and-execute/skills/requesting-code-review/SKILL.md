---
name: requesting-code-review
description: Use when a requested, project-required, or risk-targeted review could falsify a concrete implementation claim before handoff or integration
user-invocable: false
---

# Requesting Code Review

## Purpose

Obtain an independent attempt to falsify concrete claims about a bounded change. Review
produces candidate findings. It does not certify correctness, replace tests, approve a
transition, or grant authority for follow-up work.

Review is invoked only when the human requested it, project instructions or the governing
plan require it, a branch-lifecycle procedure calls it, or a named risk makes independent
inspection worthwhile. It is not an automatic consequence of completing every task or
phase.

## Define the review surface

Resolve before review:

- the absolute working directory;
- the requirement, design, issue, or acceptance criteria being checked;
- the exact changed-file surface, including staged, unstaged, and untracked files when
  they are in scope;
- a base and head when a commit range exists; and
- pre-existing changes that must remain outside the review claim.

Do not invent a commit merely to create a review range. For a committed branch, use the
actual merge base or caller-supplied base. For a working tree, inspect `git diff`,
`git diff --cached`, and the relevant untracked files explicitly.

State the falsifiable review questions. “Review the code” is not enough. Useful questions
name a behavior, boundary, failure mode, compatibility contract, or acceptance criterion.

## Perform the review

The caller may inspect directly or delegate the bounded surface to the available code
review specialist. If delegating, adapt `code-reviewer.md` with exact requirements,
paths or Git range, and review questions. Do not give the reviewer permission to edit,
commit, publish, or expand scope.

For database changes, include schema, migration, constraint, transaction, and restore
behavior in the questions. A separate database specialist is optional when those risks
need independent expertise; it is not triggered by filename alone.

Every finding is a lead and contains:

- exact file and line, symbol, command output, or current documentation pointer;
- the claim that may be false;
- the concrete consequence if it is false;
- the observation that supports the concern; and
- a check that would confirm or falsify it.

Omit generic praise, model self-assessment, and ritual severity labels that do not change
the action. Severity is useful only when it states impact and urgency.

## Resolve findings

The caller verifies confirmed findings against observable evidence by opening the cited
source and running the relevant check. Classify each finding as confirmed, not reproduced,
outside scope, or requiring a human design decision. An unsupported review assertion does
not become true because it was repeated.

If correction is within the caller's existing authority, fix the confirmed defect through
the repository's normal test-first procedure and rerun affected checks. If review was
requested without implementation authority, report the finding without editing. Ask one
pointed question when a confirmed finding exposes a genuine design or authority choice.

Re-review only when the correction materially changed the surface or the original
falsifier remains uncertain. Scope the re-review to the changed claim. Do not loop until a
model emits a favorable status.

## Return

Report the bounded surface, confirmed findings, rejected or unresolved leads, and exact
verification results. State what the review could not see.

Do not write a review certificate. Create a durable findings document only when a named
human or workflow will consume it, and keep it as findings with resolvable evidence—not as
an approval token.
