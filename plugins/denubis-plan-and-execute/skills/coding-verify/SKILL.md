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

## Check what the first check could miss

Use this pass before a consequential completion claim when the existing checks follow a
narrow list: changed files, registered claims, selected examples, or expected consumers.
Keep it bounded to the omitted surface that could change the decision.

1. Name what the existing check actually examines and what it cannot see. A checklist
   supplied by the producer is not proof of complete coverage.
2. Choose another route through the delivered artifact. Derive that route from what the
   user receives: installed commands, rendered pages, narrative claims, or exported data.
   For example, enumerate commands from the installed help rather than the changed-file
   list; inspect figures in prose as well as the registered tables.
3. Use the artifact to produce a concrete result: run a documented workflow, reconstruct
   a total from raw records, or build a timeline from source events. Record contradictions,
   missing information, and steps that cannot be completed. Re-ground findings in source
   evidence; an awkward step or stage-specific definition is a finding to investigate,
   not automatically a defect. Do not invent a resolution to make the result fit.
4. When introducing or changing this verification method, trial it on known defects and
   a valid control. Record misses and false alarms as well as catches. A method that
   misses the seeded defect is unproven for that defect; do not generalise from a pass
   count or one successful trial.

A fresh context can reduce inherited assumptions, but another model walking the same
list can miss the same items. Use a task-specific second pass; do not add a generic
verifier agent or mandatory delegation. Existing model authorization still applies.

Saved summaries and handoffs are pointers. Re-derive consequential specifics from their
sources before relying on them; a resolving path or citation establishes existence, not
support for the claim. When correcting a claim, inspect its appearances in the delivered
artifact as well as the dependencies already recorded in a register.

Adapted from Shawn Ross's [apparatus inventory](https://github.com/saross/personal-assistant/blob/main/wiki/docs/anti-confabulation-apparatus.md)
and [orthogonal-verification proposal](https://github.com/saross/personal-assistant/blob/main/wiki/docs/orthogonal-verification.md),
read 2026-09-25. These documents describe practices and proposals; their reported catches
do not establish how many errors escaped.

## Read the result

Inspect exit status, failure and error counts, relevant output, and the target actually
exercised. A command returning no matches or rows needs known coverage and a positive
control before it supports absence. A TUI observation may be truncated or stale; read the
underlying state when possible.

The evidence-producing command owns the status. Prefer its native quiet or reporting
options and run it directly. If output must be shortened, `tail` is safe only when the
same Bash command enables `set -o pipefail`, or captures `${PIPESTATUS[0]}` immediately
after the pipeline and reports or exits with that value. A plain `pytest ... | tail ...`
reports `tail`'s status, not pytest's. Do not use `head` on verification output: it can
close the pipe early and replace the producer's result with a SIGPIPE failure.

State scope and exclusions. A focused test can establish its behavior but not the entire
suite. A linter cannot establish runtime correctness. A successful build cannot establish
human usability.

A delegated report is not evidence. Inspect the diff or artifact and rerun the check in the
owning session. A commit or generated findings file proves only that the record exists.

## Report

Report each command or observation, its exit status or value, the positive signal, and any
unverified boundary. If a check fails or cannot run, state the actual status and blocker;
do not convert expected future success into a completion claim.
