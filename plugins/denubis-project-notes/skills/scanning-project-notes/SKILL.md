---
name: scanning-project-notes
description: Use before consequential project work to inspect relevant project-owned .notes, and after durable findings to propose evidence-linked note or ADR changes; prior-chat recovery stays conditional
---

# Scanning Project Notes

Use project memory as a task loop: inspect it before the first consequential project
action, apply relevant records during the work, and maintain a durable owner only when
the work changes what future work should know. Keep local retrieval bounded: inventory
every note, read enough frontmatter to select by the current task, and open only relevant
bodies. Prior-chat recovery is a separate, conditional action.

Ordinary repository instructions, current code, and an accepted plan remain the first
owners of implementation facts. Notes carry durable project facts, preferences,
references, and feedback.

Notes do not create authority or decisions: resolve any human instruction they rely on to
the original human record. Do not dispatch an advisor and do not wait for a SessionStart
reminder.

## 1. Inventory frontmatter

Run the bundled inventory helper before selecting any note body. Do not substitute a
filename listing, keyword search, or remembered inventory.

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:?plugin root unavailable}}"
python3 "$PLUGIN_DIR/skills/scanning-project-notes/scripts/inventory.py" --cwd "$PWD"
```

The helper resolves the main repository root through Git's common directory so linked
worktrees share the main checkout's `.notes/`. It reads each project-memory Markdown
entry only through the closing frontmatter delimiter even when `.notes/` is hidden or
ignored. It reports missing, malformed, unreadable, and symlink entries without emitting
note bodies or following links outside the project. The reserved `.notes/local-mail/`
subtree is reported as excluded operational state, not treated as project memory.

Require one complete JSON document and confirm `markdown_count` equals the number of
returned note entries before selection; a truncated prefix is not an inventory. A
`symlink` or `not-directory` notes-root status is an unresolved boundary, not an absent
notes set. Outside Git the helper treats the requested working directory as the project
root. If `.notes/` is absent, record that bounded result and continue unless prior-chat
recovery is independently required.

## 2. Read before selecting

Consider every returned frontmatter block before choosing which bodies could change the
task, then open those bodies completely. Select from the metadata's meaning, not the
filename. For a missing, malformed, or unreadable entry, inspect enough of that file to
determine whether it is a project note and whether it could change the task; do not
silently exclude it. Do not follow a symlink entry. Ignore reported local-mail state
unless the task independently concerns that mailbox. Keep the inventory and selection
boundary available as working evidence without turning the scan into a ceremonial
report.

Do not select notes with a keyword grep. Keywords are finding aids written for an earlier
task, not the boundary of the current task's subject.

## 3. Search prior chats

Search prior chats only when the user requested prior-work recovery or the current task
depends on a historical decision that notes and repository artifacts do not resolve. Run
one narrowly scoped search first. Reframe or widen it only when a concrete unresolved
question remains; do not search the whole task in several ways by default. Use `--all` or
`--everything` only when the required source is known to cross those boundaries. Treat an
empty result as bounded by the command's reported coverage.

Resolve a relevant message with `cc-search-chats context <full-message-id> --json` before
using it. Prefer provider-qualified exact locators when the installed resolver supports
them. A ranked search hit is a lead, not the authority record itself.

## 4. Check reference integrity

Open every note or document pointer on which the task would rely. For a human-derived
claim, the pointer must resolve to the original human message; a note, ADR, quotation, or
paraphrase does not substitute for it.

If a pointer is missing, ambiguous, stale, or resolves to the wrong role, stop the
dependent action and repair the reference. If the source cannot be recovered, write a
focused prompt for the human to open in a new session, resolve, and return with a new
authority record.

## 5. Use the result

Carry relevant findings into the work itself. Do not produce a ceremonial advisory report
unless the user asked for one. If sources disagree or a note is stale, raise the one
decision that changes the next action.

## 6. Close the memory loop

After a failure, correction, or newly verified constraint, decide whether the evidence
changes durable project knowledge. Routine debugging, transient state, and facts already
owned by code or tests do not earn a memory record.

Choose the current semantic owner:

- revise an existing `.notes/` record for a durable project fact, preference, reference,
  or feedback;
- revise an existing ADR for a current architectural decision and its rationale; or
- when no existing owner fits, propose one new `.notes/` path and use
  `denubis-project-notes:recording-project-notes` only after the user approves it; or
- use code, tests, or ordinary documentation when they already reveal the fact.

Prefer revising the existing owner over appending a new lesson. Before changing a note or
ADR, present one maintenance proposal containing:

1. the exact owner path and whether it exists;
2. the exact semantic change or proposed wording;
3. why the change would alter future work; and
4. the resolvable evidence to link, such as a focused test result, log, diff, current
   source, or original human instruction.

Wait for the user to approve that proposal before editing the note or ADR. After approval,
apply only the agreed change and verify every evidence pointer. If no durable change clears
this gate, finish without proposing or writing project memory.

## Completion check

- The helper reported the main-repository notes path, every project-memory Markdown
  entry, and any excluded operational Markdown count.
- Every returned frontmatter block was considered before body selection.
- Relevant note bodies were opened.
- Prior chats were searched only when independently required, with reported coverage.
- Every relied-on pointer resolves exactly.
- An absent or irrelevant notes set did not stop the ordinary task.
- Any note or ADR maintenance proposal names its owner, change, consequence, and evidence.
- The user approved the maintenance proposal before its owner was edited.
- Routine failures did not produce performative memory records.
- No advisor or SessionStart request stands between the task and retrieval.
