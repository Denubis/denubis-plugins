---
name: testing-skills-with-subagents
description: Use when creating or editing skills to separate executable checks from falsifiable review expectations.
user-invocable: false
---

# Testing skills with review rubrics

A skill is mostly prose. Do not pretend that prompting a model before and after an edit is
the same evidential boundary as a code test. Verify executable behaviour mechanically and
express prose quality as a falsifiable rubric that a human, the main agent, or an
authorised reviewer can apply.

Authority: `/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl:9797`,
bound as `TEST01` in the instruction-control candidate manifest.

## Map the claims

For each changed responsibility, identify:

- the consumer that selects or uses the skill;
- the action the instruction is meant to change;
- the observable failure it is meant to prevent;
- the part, if any, that a machine can determine independently; and
- the judgment that remains after those checks pass.

If there is no identifiable action or failure, remove or re-scope the instruction instead
of inventing a test for it.

## Mechanise only independent properties

Automate a property when the expectation comes from a real consumer or separately owned
contract. Examples include:

- parseable frontmatter and supported metadata;
- resolvable skill, agent, file, and authority references;
- executable helper behaviour, including failure paths;
- runtime selection or permission behaviour observed at the actual boundary; and
- generated structure parsed through the same interface its consumer uses.

Use positive, negative, and non-match controls where absence could otherwise pass by
accident. A source scan may be a bounded lint, but it is not proof of instruction meaning
or model compliance.

Do not write a test that reads a prose file, looks for the wording introduced by the same
change, and calls that correctness. Normalising, tokenising, or walking an AST does not
make a self-authored wording expectation independent.

## Put judgment in a rubric

For every non-mechanical claim, write one review entry with:

```markdown
### <claim>

- Surface to inspect: <skill and relevant consumer>
- Scenario: <a realistic use that exercises this responsibility>
- Expected consequence: <the action that should change>
- Failure evidence: <an observation that would falsify the claim>
- Exclusions: <nearby behavior this entry does not judge>
```

Good entries can fail without requiring a prescribed phrase. They name the relevant
surface and consequence, so a reviewer can explain a defect with evidence rather than
returning an approval token.

Keep the rubric close to its consumer. Project-wide expectations belong in a named review
rubric; skill-specific expectations may stay in the skill's implementation plan or review
brief. Do not create a permanent status or certificate file merely to say the review ran.

## Use another model only when it adds signal

Independent review is optional. Use it when the human requested it, when the task permits
delegation, or when a genuinely different perspective could change the decision. The
reviewer receives the rubric, the changed artifact, its consumer, and current automated
evidence. It does not receive the desired verdict.

Require findings to identify the exact current source, consequence, and falsifying
observation. Treat findings as leads. Open their cited evidence before changing anything.
Do not ask the reviewer for generic self-critique, hidden reasoning, or a pass/fail label.

A synthetic scenario can expose an ambiguity, but one model following a skill once does
not establish future compliance. Record the invocation, model, loaded skill version,
prompt, and observable result if the probe will inform a later action.

## Workflow

1. Apply `denubis-extending-claude:epistemic-humility` when scope or claimed capability
   changes.
2. Map consumers, actions, failures, and exclusions.
3. Write failing executable checks only for independent properties.
4. Write or revise the smallest skill content that owns the responsibility.
5. Run the mechanical checks.
6. Apply the rubric directly, or give it to an authorised reviewer when that adds signal.
7. Fix evidence-backed defects and rerun only the checks or entries affected.
8. Present any remaining irreducible judgment as focused UAT.

## Completion boundary

The skill change is ready for review when:

- every mechanisable claim has fresh evidence from its real boundary;
- every prose claim has a falsifiable rubric entry or has been removed;
- references resolve to current sources;
- the review found no unresolved evidence-backed defect; and
- no model verdict is being used as authority to commit, publish, install, or deploy.
