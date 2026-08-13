---
name: critical-peer-review
description: Use for a falsification-first audit of technical reasoning, plans, incidents, or generated artifacts against their exact sources and evidence boundaries
user-invocable: true
---

# Critical Peer Review

## Purpose

Find claims whose confidence, scope, or conclusion exceeds the evidence. Review the named
artifact, not the person or conversation that produced it. Do not infer anything from the
human's tone, frustration, wording, or willingness to continue.

Every finding remains a lead until its source and discriminating check are verified.

## Resolve the review surface

Resolve the exact artifact and evidence universe:

- artifact path, version, commit, time window, and requested review question;
- source code, tests, logs, screenshots, outputs, plans, decisions, and documentation it
  cites;
- repository, environment, timezone, and producer identity where relevant; and
- evidence the artifact could not access.

Open every load-bearing source. Treat copied outputs, temporary files, “latest” artifacts,
and prior model summaries as potentially stale until their subject and producer bind. A
missing, contaminated, ambiguous, or wrong-version source is an integrity finding.

## Falsify proportionately

Select only checks relevant to the artifact's claims:

- distinguish direct observation, inference, and untested possibility;
- reproduce counts, dates, links, and source pinpoints;
- test negative results for coverage and a positive control;
- compare scope words such as “all,” “only,” and “never” with the actual universe checked;
- inspect whether summaries and conclusions agree with detailed results;
- for causal claims, test whether the failure appears with the proposed mechanism and
  stops under a controlled removal on the relevant path;
- compare plausible alternative explanations when the same evidence supports more than
  one; and
- for plans, resolve every required file, interface, command, consumer, dependency, and
  acceptance owner.

Do not force every review through a named philosophical framework or matrix. Use a matrix,
timeline, or table only when several hypotheses or sources genuinely become clearer that
way.

## Findings

Each surviving finding states:

- exact disputed claim and source pointer;
- observed contradiction, unsupported step, or missing evidence;
- concrete consequence;
- current evidence boundary;
- smallest check that could settle it; and
- corrected wording or action when evidence already determines one.

Discard stylistic preferences, invented alternatives, generic risks, and objections that
the inspected sources refute. Trace a confirmed correction through every summary, count,
criterion, and downstream conclusion that depends on it.

## Return

Return findings ordered by consequence, followed by the exact sources and checks used and
the relevant surface not inspected. When none survive, state that bounded result without
certifying the whole artifact.

Do not write a review file unless the human requested one or a named workflow has a durable
consumer for it. Do not edit the reviewed artifact, issue an approval status, or require a
second model review to validate this one.
