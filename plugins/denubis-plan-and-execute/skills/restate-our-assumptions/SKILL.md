---
name: restate-our-assumptions
description: Use when reviewing dependency or architecture assumptions - tests current evidence, invalidation conditions, beneficiaries, costs, and the action each finding would change
user-invocable: true
argument-hint: "[assumption, dependency, or review scope]"
---

# Restate Our Assumptions

## Purpose

Test whether a scoped dependency or architecture assumption still describes the system and
still justifies an action. The result is a bounded evidence review, not a compulsory
philosophical exercise or periodic report.

## Establish scope

Use the assumption, dependency, or decision named by the human. If the request names a
release or subsystem, inventory the direct assumptions that can materially affect it and
state exclusions. Do not expand automatically to every dependency.

Read current rationale or decision records when present, plus manifests, lockfiles, source,
tests, Git history relevant to the assumption, operational evidence, consumers, and current
authoritative external documentation. A rationale file states an earlier justification;
it does not prove current use.

## Test current warrant

Test each scoped assumption against current evidence:

- Is the claim precise enough to falsify?
- Do its cited files, symbols, users, and external contracts still exist?
- Does actual use remain within the claimed scope?
- What observation would invalidate the choice?
- Has the dependency or boundary accumulated compatibility workarounds, pins, incidents,
  or migration cost?
- Who currently benefits, and who bears maintenance, security, performance, accessibility,
  financial, or lock-in cost?
- Is an existing capability now able to serve the same current consumers with less cost?

Use a conceptual lens only when it changes what evidence is inspected or what action could
follow. Falsification is useful for vague claims; programme health is useful for accumulating
workarounds; situated cost is useful when benefits and burdens fall on different actors.
Do not manufacture an essay for a single-purpose utility with no disputed consequence.

Negative import searches are insufficient for dependency removal. Inspect entry points,
plugins, configuration, build and type-only use, dynamic loading, and the lock graph, with
positive controls.

## Findings and action

For each finding, return:

- exact assumption and current source;
- evidence supporting or contradicting it;
- current consumers and costs;
- invalidation or missing evidence;
- whether the claim remains current, needs narrower wording, or no longer holds; and
- state the action that changes if the finding is accepted.

If evidence determines a factual correction, say so directly. If materially different
choices remain about risk, cost, compatibility, or ownership, ask one pointed question at
a time with what each answer implies.

Do not edit rationale or dependency files unless the human separately authorised updates.
Do not remove or upgrade a dependency under an assumption-review request, and do not create
a durable report without a named future consumer.
