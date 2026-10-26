# ADR 0036 — The Claude supervision mode is project-neutral; charsheet is its first consuming project and charsheet's backlog is not plugin work

**Status:** Accepted (2026-10-24). Resolves the "Remediation TODO source" ticket raised
by the stage-1 Codex worker on 2026-10-24.

## Authority evidence

Original human message in session `3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29`
(`/home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl`):

- Line 589, a `queue-operation` (`enqueue`) record timestamped 2026-10-23T20:32:53Z
  (2026-10-24 07:32 Australia/Sydney). Brian forwarded, mid-turn, his exchange with
  Astra (the Codex session on `gpt-6-astra` that wrote the specification). The record
  kind is a queue operation because the message arrived while the supervising session's
  turn was running; the same text is reproduced in the `api-request-blob` record at
  line 615.

Exact raw-record resolver:

```sh
sed -n '589p' /home/brian/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/3d3778b3-cc7f-4fd5-9aaa-8bc5704aeb29.jsonl
```

The forwarded exchange, verbatim. Brian's own words in it are the two short lines; the
rest is Astra's:

> "- "The remediation TODO" was not found in this repository, so Sol is told not to
> invent one. I will treat it as not applicable unless you point me at it." is that you?
>
> No—that isn't a message I wrote here. I can't identify its author from the quote.
>
> The remediation TODO is in charsheet, not the plugin repository:
>
> /home/brian/ArsMagica/charsheet/docs/implementation-plans/2026-10-23-seasonal-character-builder-interface/todo.md
>
> My spec's "For this project" paragraph referred to charsheet. The plugin instance
> should build the supervision capability; that TODO is the workload we'll supervise
> afterward.
>
> yes, so this is an implication that you put into the spec to the plugin
>
> Yes. I put a charsheet-specific instruction into the plugin spec without identifying
> its repository or path. That created the ambiguity.
>
> Replace that paragraph with:
>
> > Integration context only: The consuming project is /home/brian/ArsMagica/charsheet.
> > Its remediation backlog is
> > docs/implementation-plans/2026-10-23-seasonal-character-builder-interface/todo.md.
> > Do not execute that backlog during plugin development. The plugin must support
> > project-supplied briefs and constraints without hard-coding charsheet's workflow.

The question it answered, asked by the supervising session: "Which file does 'the
remediation TODO' refer to, or should that sentence be dropped?"

## Context

Astra's specification for the Codex-supervises-Claude mode ended with "For this project:
retain the existing work, use the remediation TODO, load all eight required quality skills
before coding, and prohibit automatic commits, shared Google writes or Discord posts." No
remediation TODO exists in this repository. Astra's clarification locates it in a separate
project, charsheet, and reframes the sentence as integration context.

## Decision

1. The Claude supervision mode is project-neutral. It supports project-supplied briefs
   and constraints and does not hard-code any consuming project's workflow.
2. charsheet is the first intended consuming project. Its remediation backlog is the
   workload to be supervised after the plugin capability exists, not work for the plugin
   development itself.
3. The specification's "For this project" paragraph is replaced by Astra's replacement
   text, as carried in `docs/design-plans/2026-10-24-claude-supervision-spec.md`.
   The eight-skills and no-commit clauses of the original sentence are retained because
   the replacement did not withdraw them.

## Consequences

- The "Remediation TODO source" ticket is removed from the `project_open-questions` file
  in the notes directory.
- The path Astra supplied does not resolve on this machine: `/home/brian/ArsMagica` does
  not exist, and a bounded search (`find /home/brian /media/brian/storage -maxdepth 4
  -type d -iname 'charsheet*'`, plus a depth-7 search for the named `todo.md`) found
  nothing on 2026-10-24. Astra evidently runs against another checkout or host. Nothing in
  the plugin design depends on the path; the later consumer-setup example (design phase
  P6) must take the consuming project's path as input rather than assume this one.
- The minimal project setup example required by the specification should be written so
  that charsheet can be its first instance without the plugin naming charsheet.
