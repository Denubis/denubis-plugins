---
name: exec-session-naming
family: executing-an-implementation-plan,starting-an-implementation-plan,starting-a-design-plan,systematic-debugging
description: Use when a substantial session starts or changes purpose - directly gives the current tmux window a short repository-and-task name and verifies the terminal side effect
user-invocable: true
---

# Name the Current Session Window

## Purpose

Make concurrent sessions distinguishable in tmux or Byobu. This is one terminal side
effect, not a planning stage or a model-selection problem.

## Derive the name

Derive the name directly from the current task. Use:

```text
<repo>:<verb>-<noun>
```

- `repo` is the current repository's short directory name, shortened only when the common
  project abbreviation is unambiguous.
- `verb` names the current kind of work: `design`, `plan`, `exec`, `debug`, `review`,
  `test`, `docs`, or another concrete action.
- `noun` is the most specific stable subject from the human request or governing artifact.

Examples: `ed3:debug-hooks`, `ccs:exec-importer`, `mel:design-ontology`.

Use lowercase ASCII letters, digits, colons, and hyphens. Collapse repeated punctuation and
keep the name short enough to remain visible beside other windows. If the human supplied
an exact name, use it after removing characters tmux cannot display safely.

Do not ask another model to invent the slug. Do not create a cache. A later meaningful
change of purpose may rename the window again; elapsed time alone does not.

## Apply and verify

If `TMUX_PANE` is absent, make no change and report that the session is not running inside
tmux. Do not rename whichever window happens to be focused.

Set a local `slug` value, then target the window containing this exact pane:

```bash
tmux rename-window -t "$TMUX_PANE" "$slug"
tmux display-message -p -t "$TMUX_PANE" '#W'
```

The displayed value is the evidence that the rename reached the intended window. If it
does not equal the requested slug, report the observed name and error; do not claim the
side effect succeeded.
