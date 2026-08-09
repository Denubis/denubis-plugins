---
name: scanning-project-notes
description: Use when the session's purpose is clear and before writing files or dispatching work, to find which project notes and past sessions bear on the task and whether they still hold.
---

# Scanning Project Notes

## Overview

`.notes/` holds what this project has already learnt: prior failures, standing
decisions, and facts the code does not reveal. The global CLAUDE.md already
instructs you to read it. That instruction is ignored in practice, so this skill
replaces the instruction with a mechanism.

**Announce at start:** "I'm using the scanning-project-notes skill to check what
this project already knows about this."

## When this fires

The SessionStart hook injects a `<notes-advisory …>` block carrying `dir`,
`notes`, `transcript`, and a `dispatch` attribute.

| `dispatch` | Meaning |
|---|---|
| `now` | The transcript already holds the purpose. Scan immediately. |
| `first-request` | Cold start. Scan once the first substantive request lands. |

Also fire this skill, regardless of the hook, when you are about to write a
project file, dispatch a subagent, or produce a design artefact, and you have not
scanned this session.

**Do not fire it** on a one-word reply, a question about your own prior output, or
a trivial lookup you have already grounded.

## The dispatch

Fill in the purpose paragraph from what the user actually asked. Copy `dir`,
`notes`, and `transcript` from the hook block verbatim.

<invoke name="Task">
<parameter name="subagent_type">denubis-notes-advisory:notes-advisor</parameter>
<parameter name="description">Scan notes and chat logs for this session</parameter>
<parameter name="prompt">
Notes directory: <dir from the hook block>
Note count: <notes from the hook block>
Transcript: <transcript from the hook block>

What this session is for:
<one paragraph, in the user's own terms, saying what is about to be done and
which files, hosts, or systems it touches>

Read every note's frontmatter, search the chat logs several ways, and report
which notes and prior sessions bear on this work and whether they still hold.
</parameter>
</invoke>

## What to do with the result

**Open what it names.** The advisor returns pinpoints and is forbidden to quote
or paraphrase, so there is nothing to act on until you have opened one.

**Control your check before you call a pinpoint bad.** A location that will not
open is a fact about your lookup until you have shown otherwise. Use the
identifier in full — `cc-search-chats context` takes a whole message uuid and
answers a prefix with "Message not found". Case-fold the search. Then run a
positive control: feed the same check something that must match and watch it
fire. A check whose control does not fire is broken, and broken is no evidence.

**A pinpoint that survives a controlled check and still will not open is a void
finding.** Discard that advisory. Do not escalate it: "I could not open this" is
a report about your check, and calling it fabrication is a claim about the
advisor that needs a control that fired.

**Read the coverage line.** If it reports `read 12/43`, it did not do the scan.
Send it back.

**Treat "nothing found" as bounded.** An empty result names what was searched, and
nothing more.

**Ask before you build on it.** Where a note bears on the work but looks stale, or
two notes disagree, raise one pointed question and wait. Do not resolve it
silently.

## Anti-patterns

**Grepping instead of scanning.** `.notes/` is hidden *and* gitignored, so `rg`
skips it under `--hidden` alone and under `--no-ignore` alone. A search corrected
halfway still returns nothing and now carries false confidence.

**Scanning after the fact.** A scan run once the design is written is an audit of
your own work, not an input to it.

**Reporting the scan as done when a subagent returned nothing.** Absence of
evidence is not evidence of absence until you know what the query could not see.
