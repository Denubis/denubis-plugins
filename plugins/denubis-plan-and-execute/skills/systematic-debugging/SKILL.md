---
name: systematic-debugging
family: standalone
description: Use for bugs, failing tests, crashes, or unexpected behavior - establishes the failure boundary, tests causal hypotheses, and fixes only the demonstrated mechanism
user-invocable: true
---

# Systematic Debugging

## Purpose

Explain the failure well enough to make one justified change and know whether it worked.
Debugging is an evidence loop, not a sequence of plausible edits or a performance of
self-criticism.

Direct investigation is the default. Delegation and independent review are optional for a
bounded question; the main session still verifies returned evidence.

At the start, use `denubis-plan-and-execute:exec-session-naming` so concurrent terminal
sessions expose this work's repository and purpose to the human.

## Establish the failure

Before proposing a fix:

1. Read the complete error, stack, log, failing assertion, and command output.
2. Reproduce the failure or establish the strongest observable boundary available. Record
   the exact input, environment, version, command, and result.
3. Identify what the user expected and its source: specification, test, documentation,
   prior working behavior, or explicit human instruction.
4. Inspect the relevant source and callers far enough to trace the bad state from its
   producer to the observed failure.
5. Preserve pre-existing repository changes and separate them from diagnostic edits.

If the failure is intermittent, repeat with controlled inputs and capture timing, ordering,
state, and resource differences. “Flaky” describes the observation; it is not permission
to ignore it.

For a multi-component path, observe data at the boundaries first. Prefer existing logs and
read-only diagnostics. Add temporary instrumentation only when needed, keep sensitive data
out of output, and remove the instrumentation before completion unless it is useful
operational telemetry requested by the change.

## Choose the relevant comparison

Choose a reference state relevant to this failure: a last passing run, prior version,
working input, alternate environment, sibling implementation, specification, or Git
baseline. Do not assume every bug was introduced by the current Git diff.

Compare one dimension at a time and state the coverage of the comparison. An empty diff,
search, or log query is not evidence until its scope and exclusions are known and a
positive control shows it could have observed the target.

When a library, framework, API, CLI, or service contract is implicated, consult current
authoritative documentation for the installed version. Read source as needed to establish
actual behavior, but distinguish public contract from implementation detail.

## Form and test a cause

Separate observation from inference:

- **Observed:** direct source, runtime, test, log, or configuration result.
- **Inferred:** explanation connecting observations, with its assumptions stated.
- **Unverified:** plausible mechanism without a discriminating experiment yet.

State one causal hypothesis and its falsifier. Name why the observed evidence favors it,
what experiment changes one relevant variable, the predicted result if the hypothesis is
right, and the result that would reject it.

Run the smallest safe diagnostic experiment. Change one variable. Confirm the experiment
exercised the actual relevant path rather than a transcription, mock, wrong process,
truncated UI, or malformed query. Where practical, corroborate the observation through a
different boundary.

A contradicted prediction updates the model: record what was predicted, what was observed,
and which assumption no longer holds. Return to evidence before trying another mechanism.
Do not ask the human to choose a new technical hypothesis when the available evidence can
settle it.

A diagnostic experiment is not automatically the fix. A mechanism earns a strong causal
claim when the failure appears with it and stops when that mechanism alone is removed on
the relevant path. When only one border or a synthetic path was tested, say what remains
inferred.

## Decide whether to fix

A diagnosis request authorizes investigation and explanation, not code changes. A bug-fix
request authorizes the smallest in-scope repair. If the demonstrated cause requires a
material architecture, compatibility, migration, or external-state decision beyond that
scope, present the evidence and ask one pointed question.

For an authorised fix:

1. Write or identify the smallest regression test for the observed behavior.
2. Observe the regression test fail for the intended reason.
3. Make the smallest fix at the earliest reliable boundary in the causal chain.
4. Run the focused test and inspect its positive signal.
5. Run affected integration and repository gates in proportion to the blast radius.
6. Remove diagnostic-only changes and rerun any check they could affect.

Do not bundle unrelated cleanup, refactor untested code, weaken the specification, or
delete a failing test. Validation or type changes belong in the fix when they make the
demonstrated invalid state unrepresentable at the responsible boundary.

If a fix attempt fails, remove only the changes made by that attempt, preserve the
observation, and return to causal investigation. After three failed fixes for the same
condition, stop, restore the last verified state for work owned by this debugging session
using a recoverable method, record the three predictions and results, and ask one pointed
question before changing approach. Do not disturb pre-existing user work.

## Verify and report

Fresh completion evidence includes:

- the original reproducer now passing or the failure no longer appearing at its observed
  boundary;
- the regression test demonstrating the before/after behavior;
- affected project checks passing;
- a diff inspection showing the fix is minimal and diagnostics are removed; and
- any production or external boundary explicitly left untested.

Report the causal chain at the strength established by those observations. Do not claim a
universal root cause when the experiment covered one environment or path.

Do not write an investigation document unless the human asked for one, project policy
requires one, or a named future consumer needs the durable record. If written, it contains
current findings and exact evidence pointers rather than a transcript of mistaken theories.

Do not commit, publish, or deploy without separate authority. Do not force a fresh context
or independent model review; use either only when it has a concrete consumer and can
materially test an unresolved claim.
