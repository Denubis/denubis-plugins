---
name: exec-session-naming
family: executing-an-implementation-plan,starting-an-implementation-plan,starting-a-design-plan,systematic-debugging
description: Use when starting an implementation, design, or debugging session - builds a structured slug and renames the current tmux pane's window
user-invocable: false
---

# Session Naming

Build a compact structured slug for the current Claude session, then rename the tmux window of the **current pane** (so the name does not schmear onto whichever window happens to be focused).

## Slug Format

```
<Person>/<p3>:<verb>-<noun>:#<issue>:P<phase>
```

Example: `Adela/mel:design-ontology:#19:P2`

Required: `<p3>` and `<verb>-<noun>`.
Dropped when not available:
- `<Person>/` when Person equals the current shell user (case-insensitive).
- `:#<issue>` when no issue number is present.
- `:P<phase>` when phase is unknown.

## 1. Gather Components

### Path-derived: Person and project

Run once:

```bash
git rev-parse --show-toplevel
```

From the absolute path returned, attempt to match `.../people/<Person>/<project>/...` (the literal segment `people` followed by two directory components).

- **Person** = `<Person>` (e.g. `Adela`, `Brian`).
- **Project** = `<project>` (e.g. `melica`, `brian-ed3d-plugins`).

If the path does not contain a `/people/<X>/<Y>/` segment, set Person = none and Project = basename of the git root.

**Username elision:** read `$USER`. If `Person.lower() == $USER.lower()`, set Person = none.

**Project code (`p3`):**

1. If Project starts with `<$USER>-` (case-insensitive), strip that prefix.
2. Otherwise, if Person is known and Project starts with `<Person>-` (case-insensitive), strip that prefix.
3. If stripping leaves an empty string, revert to the unstripped Project.
4. Take the first 3 alphanumeric characters of the result, lowercased. If fewer than 3 alphanumeric chars exist, use what there is.

Examples:
- `melica` + user=brian → no prefix match → `melica` → `mel`
- `brian-ed3d-plugins` + user=brian → strip `brian-` → `ed3d-plugins` → `ed3`
- `adela-melica` + Person=Adela → strip `adela-` → `melica` → `mel`
- `brian` + user=brian → strip leaves empty → revert to `brian` → `bri`

### Issue number

```bash
git branch --show-current
```

If the branch name matches `^(\d+)[-_]`, capture the digits as the issue number. Otherwise issue = none. Worktree branches like `19-tag-ontology-design` → `#19`.

### Phase

Take the current phase number from the invoking skill's context (the orchestrator passes it as an argument: `{phase}`). If no phase is tracked or known, phase = none.

### Verb-noun (via Haiku subagent)

The slot is always a `<verb>-<noun>` pair. Generic single verbs (e.g. `coding`, `writing`) carry no information — every session involves coding or writing. The noun gives the slot meaning.

**Verb rules:**

| Invoking skill | Verb |
|---|---|
| `starting-a-design-plan` | `design` (fixed) |
| `starting-an-implementation-plan` | `plan` (fixed) |
| `executing-an-implementation-plan` | `exec` (fixed) |
| `systematic-debugging` | `debug` (fixed) |
| anything else | Haiku picks the verb from the user's prompts |

**Noun rule:** Haiku always picks the noun from the user's prompts.

**Haiku input:** the full conversation from the start of the session up to the moment `exec-session-naming` is invoked — prompts, clarifications, chosen direction. Clarifications often reshape the real topic, so the later context matters as much as the first message.

**Substitute the gathered values, then invoke:**

```
<invoke name="Task">
<parameter name="subagent_type">denubis-basic-agents:haiku-general-purpose</parameter>
<parameter name="description">Pick verb-noun slot for session slug</parameter>
<parameter name="prompt">
Produce a compact slot label for a tmux window name summarising this Claude Code session.

Conversation so far (user prompts and clarifications only):
{conversation_so_far}

Invoking skill: {invoking_skill}
Fixed verb (use exactly this if non-empty): {fixed_verb}

Rules:
- Output format: always "<verb>-<noun>" (a single hyphen joining two tokens).
- If a fixed verb is given, the verb MUST be exactly that fixed verb. Pick only the noun.
- If no fixed verb is given, pick both verb and noun from the conversation.
- Each token: lowercase, letters only, <=8 characters, single word (no internal hyphens).
- The noun must reflect what this session is actually about (the topic, not a generic activity).
- Prefer domain terms from the conversation over generic ones. Never output "code", "coding", "writing", "stuff".
- Output ONLY "<verb>-<noun>", nothing else (even if a fixed verb was given — concatenate and return the full pair).
</parameter>
</invoke>
```

Capture the returned string. Trim whitespace. Validate: must match `^[a-z]{1,8}-[a-z]{1,8}$`. If it fails validation, fall back:
- Canonical skill: use the fixed verb alone (no noun).
- Non-canonical skill: use the first hyphen-separated token of the invoking skill name.

### TMUX pane

Read `$TMUX_PANE` at **apply time** (Step 3), not during context gathering. This is critical for anti-drift — any cached value may be stale.

## 2. Assemble the Slug

```
person_part = f"{Person}/" if Person else ""
issue_part  = f":#{issue}" if issue else ""
phase_part  = f":P{phase}" if phase else ""
slug        = f"{person_part}{p3}:{slot}{issue_part}{phase_part}"
```

Worked example for `/media/brian/.../people/Adela/melica/.worktrees/19-tag-ontology-design` on branch `19-tag-ontology-design`, invoked by `starting-a-design-plan` at phase 2, with `$USER=brian`, Haiku returns `design-ontology`:

- Person = `Adela` (≠ brian → kept)
- p3 = `mel`
- slot = `design-ontology`
- issue = `19`
- phase = `2`
- slug = `Adela/mel:design-ontology:#19:P2`

Second worked example for this repo (`/home/brian/people/Brian/brian-ed3d-plugins`), branch `revise-exec-session-naming`, invoked by `writing-skills` (non-canonical), no phase, Haiku returns `redo-session`:

- Person = `Brian` → equals user `brian` → dropped
- Project = `brian-ed3d-plugins` → strip `brian-` → `ed3d-plugins` → p3 = `ed3`
- slot = `redo-session`
- issue = none
- phase = none
- slug = `ed3:redo-session`

## 3. Apply the Slug — anti-drift pane targeting

**Re-read `$TMUX_PANE` at this step.** Do not use any value captured during context gathering — the pane that matters is the one this Bash call runs in, right now.

If `$TMUX` or `$TMUX_PANE` is unset, this session is not inside tmux. Skip both the rename and the lock file; just report the slug to the user.

Otherwise run, in a **single Bash invocation** so the pane id is captured atomically:

```bash
: "${TMUX_PANE:?not in tmux}"
pane_id="${TMUX_PANE#%}"
tmux rename-window -t "$TMUX_PANE" "Cl:<slug>"
echo "<slug>" > "/tmp/claude-statusline-tmux-lock-${pane_id}"
```

Substitute the actual slug string for `<slug>`.

**Why `-t "$TMUX_PANE"`:** without `-t`, `tmux rename-window` targets the **currently focused** window of the attached client — which is whichever window the user is looking at, not necessarily Claude's. When the user is hopping panes, the name gets schmeared onto the wrong window. `-t "$TMUX_PANE"` pins the rename to the window containing this Claude's own pane, so the slug lands where it belongs.

The lock file key (`pane_id`) must match what the statusline reads from its own `$TMUX_PANE` — using the current value guarantees that.

## 4. Tell the User

Print exactly:

```
Session: <slug>
To rename this Claude session too: /rename <slug>
```

## Notes

- **Fallbacks.** When path, branch, phase, or Haiku output is missing or malformed, components drop out cleanly. The slug is never empty: `<p3>:<verb>` is always available (verb falls back to the fixed canonical verb or the first token of the invoking skill name).
- **No generic verbs.** The Haiku prompt explicitly bans `code`, `coding`, `writing`, `stuff`. If you find Haiku still emitting generic slots, tighten the ban list.
