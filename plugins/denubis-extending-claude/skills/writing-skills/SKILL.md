---
name: writing-skills
description: Use when creating or editing skills to scope the responsibility, write the procedure, and define honest verification.
user-invocable: false
---

# Writing skills

A skill owns one situational procedure or reference. Make the trigger discoverable, the
body useful when loaded, and every verification claim proportionate to what can actually
be observed.

The verification boundary is authorised by
`/home/brian/.codex/sessions/2026/08/10/rollout-2026-08-10T14-13-59-019fe9e0-9c27-70b2-b485-2a603b698ecb.jsonl:9797`
and bound as `TEST01` in the instruction-control candidate manifest.

## Decide whether a skill is the right owner

Create or extend a skill when the content is reusable across tasks and should load only in
a named situation. Use another owner when the responsibility is different:

| Content | Owner |
|---|---|
| Continuous cross-project invariant | Global instructions |
| Continuous project boundary | Project instructions |
| Project-specific memory or preference | Human-approved `.notes/` record |
| Mechanical prohibition or state transition | Executable gate or hook |
| Current decision and consequences | ADR or decision record |
| Historical argument | Git or an explicit archive |

Apply `denubis-extending-claude:epistemic-humility` when the proposed skill changes scope,
claims a new capability, or automates judgment. A narrower procedure is usually better
than a broad skill defended by more instructions.

## Skill shape

```text
skills/
  skill-name/
    SKILL.md
    supporting-reference.md
    examples/
      worked-example.md
```

`SKILL.md` contains the trigger, boundary, core procedure, failure handling, and pointers
to material needed only sometimes. Keep a supporting file only when it has a distinct
consumer or materially reduces the loaded body. Do not split a short procedure merely to
claim progressive disclosure.

Frontmatter:

```yaml
---
name: skill-name-with-hyphens
description: Use when <observable triggers or symptoms> to <specific responsibility>.
user-invocable: false
---
```

The description says when selection is appropriate. It does not promise outcomes the body
or runtime cannot guarantee. Add platform metadata only when the platform consumes it.

## Authoring workflow

1. **Map the consumer.** Identify what selects the skill, what it acts on, and the action
   its instructions are meant to change.
2. **State the boundary.** Name in-scope work, exclusions, authority requirements, and the
   observable failure the skill handles.
3. **Inspect current evidence.** Read relevant current skills, platform documentation, and
   executable consumers before borrowing a pattern.
4. **Write the smallest complete procedure.** Put one current path through the task in the
   body. Remove incident dialogue, self-critique, and rebuttals to earlier versions.
5. **Phrase for the target surface.** Use
   `denubis-extending-claude:writing-claude-directives` for metadata and directive details.
6. **Define honest checks.** Use
   `denubis-extending-claude:testing-skills-with-subagents` to separate executable checks
   from a falsifiable review rubric.
7. **Verify references and mechanics.** Run the repository's actual parsers, reference
   checks, helper tests, and plugin validation where applicable.
8. **Review the prose against its rubric.** The main agent may do this directly. Use a
   separate reviewer only when authorised and likely to add signal.

Editing an existing skill re-enters only the affected steps. A wording-only correction
does not require a staged failure performance; a changed helper still follows code TDD.

## Review questions

- Does the description identify selection conditions without encoding the entire body?
- Does the procedure change one named action at one intelligible boundary?
- Can a reader distinguish requirements, references, examples, and optional advice?
- Does each current factual or authority claim point to a resolvable source?
- Do executable checks observe a consumer-owned property rather than chosen wording?
- Are judgment expectations written as falsifiable scenarios rather than approval labels?
- Can old arguments be removed without losing a current instruction or decision?

## Supporting files

- `anthropic-best-practices.md` is a pinned upstream reference. Recheck current official
  documentation before relying on volatile platform details.
- `render-graphs.js` renders Graphviz blocks for human review; it is author tooling, not a
  runtime requirement.
- `examples/CLAUDE_MD_TESTING.md` is a historical upstream example of prompt variants. It
  may suggest scenarios, but its model responses are observations rather than gates.

## Completion boundary

A skill change is ready for human review when its frontmatter parses, references resolve,
executable helpers pass their real tests, prose expectations have been reviewed against a
falsifiable rubric, and no unresolved defect remains. Commit, publication, installation,
and deployment are separate actions.
