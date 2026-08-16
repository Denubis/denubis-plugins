---
name: testing-skills-with-subagents
description: Use when creating or editing skills - separates an acting agent's realistic instructions from a hidden evaluator oracle and observes consequential behavior
user-invocable: false
---

# Testing Skills with Acting Agents

A prose skill changes an agent's method. Evaluate that method by giving an acting agent a
realistic task and observing what it does. Do not call a prompt-and-verdict loop equivalent
to a deterministic code test, and do not lock the edited wording in place.

## Map the claim

For every changed responsibility identify:

- the consumer that selects or applies the skill;
- the decision or action the instruction should change;
- the observable failure it should prevent;
- a real permitted action or positive control proving the path was reachable; and
- any independently machine-checkable contract.

If no identifiable action, consequence, or consumer exists, remove or narrow the
instruction rather than inventing a test.

## Separate the actor from the oracle

Each methodological case has at least two artifacts with different audiences:

1. **Actor brief.** The task, accessible workspace, applicable skill, granted authority,
   and ordinary project constraints. It must not contain expected answers, scoring
   criteria, the protected rule restated as a hint, or the oracle path.
2. **Evaluator oracle.** The protected behavior, evidence to inspect, acceptable
   variation, failure observations, and positive or non-match controls. The acting agent
   cannot read this artifact while performing the task.

Keep fixtures separate when their contents would disclose the answer. Give the acting
agent only a fresh scratch copy and the named skills it should apply. A reviewer who sees
both actor output and oracle is an evaluator, not the actor. Record that role distinction
when the run informs a later decision.

Never put scenario instructions and their expected consequence in one “rubric” handed to
the actor. That measures whether the actor can repeat the answer it was shown.

## Make the case capable of failing usefully

Use a task on which the actor can make a concrete decision or take a real bounded action.
Capture the artifacts that expose consequences: repository diff and log, filesystem state,
tool trace, test output, generated structure, or the public behavior of a safe fixture.

Include at least one control that distinguishes the intended method from a system that
always refuses, always succeeds, or never reaches the boundary. Depending on the claim,
use:

- a permitted-action case showing that safe work proceeds;
- a failure-path case in which the unsafe action is reachable;
- a non-match fixture the method must leave alone; or
- a deliberately defective fixture the mechanical probe must reject.

“Nothing was deleted,” “no matches were found,” and “the agent said it complied” are not
evidence without this discrimination.

## Mechanize independent contracts only

Automate properties owned by a real consumer or separate contract: parseable metadata,
resolvable references, helper exit behavior, runtime selection or permissions, and
generated structure parsed through its actual interface. Run positive and negative
controls where empty output could pass accidentally.

Do not read prose, search for the newly written series of words, and call that behavioral
correctness. Tokenization, normalization, regex length, and AST traversal do not make a
self-authored wording expectation independent. Such scans may locate review candidates;
they are not acceptance evidence.

## Develop the evaluation red-green-refactor

1. Create the smallest actor brief, hidden oracle, and fixture that expose the claimed
   failure.
2. Run the actor against the pre-change skill without oracle access.
3. Inspect observable artifacts in the evaluator role and confirm the oracle fails for
   the intended reason. A broken fixture or actor that never reached the decision is not a
   useful red state.
4. Make the smallest skill change that owns the method.
5. Run a fresh actor with a fresh fixture, then evaluate it against the same hidden oracle.
6. Run controls and mechanical contracts.
7. Refactor only the instruction covered by those observations, then rerun affected
   cases.

Do not weaken the oracle because the edited skill failed. Change the oracle only when the
protected behavior or independent contract was wrong, and record that design correction.

One acting-agent run demonstrates one observed run, not universal future compliance.
Record the actor runtime/model, loaded skill version, brief, fixture identity, tool and
filesystem evidence, and result when the observation will authorise later work.

## Completion boundary

The skill change is ready for finished-work verification when independent mechanical
contracts pass, pre-change failure and post-change behavior have been observed with the
same hidden oracle, controls discriminate correctly, and every finding has been checked
against current artifacts. Any irreducible human judgment remains focused UAT; a model
verdict grants no commit, publication, installation, or deployment authority.
