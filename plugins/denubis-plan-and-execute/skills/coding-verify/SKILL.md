---
name: coding-verify
description: Use before reporting code complete, fixed, clean, or passing - runs the check that owns each claim and reports its fresh result, scope, and exclusions
user-invocable: false
---

# Verify Before Reporting Completion

## Claim-to-evidence mapping

For each completion claim, identify the exact command or observation capable of proving
it at the relevant boundary:

| Claim | Evidence owner |
|---|---|
| Focused behavior works | Focused behavioral or integration test |
| Regression test is meaningful | Observed red state followed by green state |
| Test suite passes | Project-native full test command and zero failing/error result |
| Types or lint are clean | Configured checker over the stated file or project scope |
| Build/install succeeds | Actual build or install command and resulting artifact |
| Bug is fixed | Original reproducer plus regression test |
| Requirements are met | Acceptance-criterion coverage plus each owning check |
| External state changed | Read-back from the external consumer |

Run the check after the last change that could affect it. Fresh evidence means the exact
code and environment being reported were exercised after that change; an earlier run or a
different checkout is historical evidence.

## Read the result

Inspect exit status, failure and error counts, relevant output, and the target actually
exercised. A command returning no matches or rows needs known coverage and a positive
control before it supports absence. A TUI observation may be truncated or stale; read the
underlying state when possible.

State scope and exclusions. A focused test can establish its behavior but not the entire
suite. A linter cannot establish runtime correctness. A successful build cannot establish
human usability.

A delegated report is not evidence. Inspect the diff or artifact and rerun the check in the
owning session. A commit or generated findings file proves only that the record exists.

## Report

Report each command or observation, its exit status or value, the positive signal, and any
unverified boundary. If a check fails or cannot run, state the actual status and blocker;
do not convert expected future success into a completion claim.
