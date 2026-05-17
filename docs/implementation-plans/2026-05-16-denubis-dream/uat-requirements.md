# UAT Requirements

Human-judgment falsification entries. Each requires a human to USE the built thing and exercise judgment that automated tests cannot capture.

**Quality gate:** every entry must have (1) what the human DOES (an action, not inspection), (2) what they're JUDGING (subjective quality), (3) what FAILURE looks like (concrete experience).

This file was collated incrementally as phases were reviewed in three-lens mode. 8 entries across Phases 1-6. Phase 7 has no UAT-requirements entry because the Phase 7 deliverable IS itself a UAT artefact — `plugins/denubis-dream/docs/uat-checklist.md` covers the 10 DoD criteria + 5 design-specified edge cases operationally; the human-judgement aspect of Phase 7 (DR7-1's scheduler-agnostic framing) is verifiable only by running the cron path with a real scheduler, which the uat-checklist's A.5 case requires.

**How this file is used:** the `exec-uat-gate` skill reads this file during execution. At the end of each phase whose entries appear below, the implementer runs the phase's UAT entries through the `exec-uat-gate` skill, which presents each entry to the user for human judgement. A NEEDS_REVISION verdict on any entry halts the phase pending revision.

**Relationship to `uat-checklist.md` (Phase 7):**
- `uat-requirements.md` (this file): per-phase human-judgement gates, evaluated at phase boundaries.
- `uat-checklist.md` (Phase 7 deliverable): end-to-end pre-release verification of the 10 DoD criteria + 5 integrity edge cases, evaluated once before declaring the plugin releasable.

The two files have non-overlapping responsibilities — neither subsumes the other.

---

## Phase 1: Plugin scaffolding

### DR1-1: `/dream` short command routing

**This decision assumes:** the two-file pattern (`commands/dream.md` aliasing the `denubis-dream:dreaming` skill) reliably triggers the skill in fresh sessions, in the same way `/commit` triggers `denubis-git-commit:commit`. The user discovers `/dream` as a short command, types it, and the audit workflow begins — they never need to remember the long form `/denubis-dream:dreaming`.

**To shatter it:** in a fresh Claude Code session opened in this repo (after Phase 1 commits land and `/plugin install` or equivalent has refreshed the local cache), type `/` and verify `dream` appears in the command list with a sensible description. Then type `/dream` and observe the skill execution.

**It's wrong if:**
- `/dream` doesn't autocomplete or appear in the slash-command list;
- typing `/dream` reports "command not found" or routes to a different skill;
- the skill executes but the announcement / scaffold-status message looks wrong (typo, missing newlines, doesn't identify itself as denubis-dream:dreaming);
- the user feels they need to type the long form `/denubis-dream:dreaming` to get the workflow to start.

---

## Phase 2: Autonomous-pass orchestration

### DR2-1: Slug resolution via `git rev-parse --show-toplevel` (and the non-git-dir failure mode)

**This decision assumes:** the dream is a repo-scoped workflow. The user invoking `/dream` is doing so inside a git repository (or worktree) that they want to audit — the requirement to be inside a git repo is intuitive, and the failure mode when they aren't is clear enough not to confuse them.

**To shatter it:** `cd /tmp` (or any non-git directory), invoke `/dream`, and judge the failure experience. Does the message tell you why it failed and what to do? Does the absence of a dated-dir creation feel like the right outcome, or does it feel like the command silently broke?

**It's wrong if:**
- the message blames the user (e.g., "cwd is not a git repo — you must `cd` to a repo root") without explaining what `/dream` is supposed to do;
- the message is missing entirely and the command just exits silently (the user can't tell whether `/dream` worked or not);
- the user reasonably expected `/dream` to work outside git repos (e.g., they wanted to audit memory for a project that isn't in version control).

---

## Phase 3: Sonnet retrieval subagents

### DR3-5: Corpus-wide flagged-region quality

**This decision assumes:** the Sonnet subagent, given only memory descriptions (not bodies) as the cross-reference list and a windowed `_corpus.jsonl` stream, surfaces flagged regions that you'd actually want to consider promoting — and skips regions that an existing memory already covers, even when only the description is available for the comparison.

**To shatter it:** after the autonomous pass completes (in either a real `/dream` run or a fixture-corpus run), read the contents of `<dated_dir>/flagged/region-*.flagged.md` files end-to-end. Then read the existing memory descriptions in `<main_dir>/memory/*.md` (just the frontmatter). Form your own judgement: are the flagged regions plausibly memory-worthy? Are any of them obviously already covered by an existing memory's description?

**It's wrong if:**
- a flagged region's `## Why memory-worthy` is generic ("the user said something about X") rather than a durable claim/preference;
- a flagged region duplicates an existing memory whose description plainly covers it (the subagent failed the cross-reference);
- the `## Coverage` header on flagged files reports far fewer lines than you'd expect for the window (suggesting silent truncation);
- the subagent surfaced 0 flagged regions despite a corpus with obvious memory-worthy moments (false-negative — the cross-reference is over-eager).

---

## Phase 4: Opus judgement

### DR4-3: MEMORY.md byte-level conservation (regeneration is line-deletion only)

**This decision assumes:** the user's hand-curated MEMORY.md structure — topical section headings, prose hooks per memory, ordering — is information that Phase 4 must not regenerate from frontmatter descriptions. The right place to update a hook line is the Phase 5 reconciliation walk where the user sees the body edit and can update the hook in the same turn.

**To shatter it:** after a dream pass that includes at least one `prune` disposition, open the live `<main_dir>/memory/MEMORY.md` and the proposed `<dated_dir>/MEMORY.md` side-by-side (or `diff` them). Read the result as a human and judge whether the proposed regeneration would be acceptable to apply at finalisation — i.e., whether the only changes are the line-deletions for pruned memories, and the rest of the file (sections, prose, ordering, hooks for kept/edited memories) is preserved exactly.

**It's wrong if:**
- the diff shows changes outside pruned-link removals (re-ordered sections, rewritten prose hooks, re-categorised entries);
- an `edit`-disposition memory's hook line was rewritten without your sign-off;
- the section headings (`## Feedback`, `## Active Design Work`, etc.) were renamed, merged, or split;
- the conservative behaviour feels too conservative — i.e., you wanted Phase 4 to update a clearly-misleading hook line, but it didn't, and you have no clear path to fix it short of the Phase 5 edit turn.

---

## Phase 5: Reconciliation walk

### DR5-7: Skipped-memory retry workflow

**This decision assumes:** when a Phase 3 subagent failure produces a skipped memory, the right user-facing recovery is `retry` — kicking the subagent again from the walk, with the rest of the audit state already in place. The skipped memory surfaces FIRST in the walk so the user can attempt recovery while context is fresh, rather than burying it after dozens of regular turns.

**To shatter it:** force a skipped-memory state (e.g., by deleting one `.windowed/<name>.jsonl` after Phase 3 starts but before the per-memory dispatch returns, or by interrupting one specific subagent). Run `/dream` to the walk. Triage: does the skipped-memory turn feel like recoverable error-handling, or does it feel like noise that obscures the actual audit work?

**It's wrong if:**
- the skipped-memory prompt is buried mid-walk where you can't easily prioritise it;
- the `retry` verb doesn't actually re-dispatch the subagent (it gives up too easily, or it re-runs the whole Phase 3 instead of just this one memory);
- the failure mode is opaque — the user can't tell WHY the memory was skipped (transient model failure? bad jsonl input? subagent prompt mismatch?);
- after a successful retry, the memory doesn't slot back into the regular walk in its correct mtime position.

### DR5-walk: The walk itself

**This decision assumes:** the chat-blockquote presentation of `## Evidence`, `## Code-artefact flags`, `## Changes` (per turn) plus the `accept / reject / edit <x> / prune` verb set lets you reconcile a memory in under 60 seconds when the recommendation is correct, and under 3 minutes when you need to override or revise. The batched keep-clean prompt eliminates 5-10 minutes of tedious individual-accepts per dream on a stable memory set.

**To shatter it:** run a full real `/dream` against this project's actual memory set after Phases 1-6 are in place. Walk every entry (don't accept the batched-keep-clean; force every individual turn). Estimate your time per turn. Form a judgement: would you actually use `/dream` weekly at this cadence? Would you prefer a different UI shape (terminal TUI, editor handoff, web view)?

**It's wrong if:**
- the per-turn time is so long that you'd dread running `/dream` monthly, let alone weekly;
- the blockquoted evidence presentation is hard to read in your terminal (line wrapping, ANSI escapes, narrow window);
- the `edit <instructions>` free-form input feels imprecise — Opus mis-applies your instruction often enough that you'd prefer a structured diff input;
- you find yourself wanting to re-decide entries but the path (delete decisions.log line, re-invoke) feels too manual;
- the walk-end summary is wrong (counts don't match what you remember deciding) or the y/n prompt fires before you're actually done.

---

## Phase 6: Finalisation

### DR6-2: MEMORY.md type→section auto-placement of promoted entries

**This decision assumes:** the type→section heuristic (`feedback`→`## Feedback`, `project`→`## Active Design Work`, `user`→`## User Communication Signals`, `reference`→`## Reference`, fallback `## Promoted`) places newly-promoted memories in approximately the right place in your hand-curated MEMORY.md — close enough that you only need to hand-reorganise occasionally, rather than every dream.

**To shatter it:** after a dream that promotes at least one flagged region across multiple types (e.g., one `feedback` and one `project`), read the resulting live MEMORY.md. Form your judgement: are the new entries under the section you'd have chosen yourself? Would you actually hand-edit MEMORY.md after most dreams to re-categorise auto-placed entries, or does the auto-placement get it right ≥80% of the time?

**It's wrong if:**
- the auto-placement consistently misses (e.g., `feedback`-type memories landed under the wrong section because your MEMORY.md uses `## Lessons` instead of `## Feedback`);
- the fallback `## Promoted` section appears in your MEMORY.md when you'd have preferred the entry land in an existing section (suggests the type-to-heading mapping needs adjustment);
- you find the auto-placement so off that you'd rather Phase 6 NOT touch MEMORY.md and let you add promoted entries by hand.

### DR6-7: Self-check abort experience

**This decision assumes:** if the DoD #8 self-check ever fires (transcript UUIDs or line-ranges leaked into live `memory/`), the abort message is clear enough that you immediately understand what happened and how to recover, without needing to re-read the design plan.

**To shatter it:** force a self-check failure (edit one live memory file's body to include `transcript abc12345xx` before invoking a fresh `/dream`). Walk to walk-end, type `y`, and let Phase 6 abort. Read the abort message as a human encountering it for the first time. Form your judgement: do you know what went wrong, where, and what to do?

**It's wrong if:**
- the abort message says "self-check failed" without identifying which file or line;
- the message blames the user without distinguishing between "you typed a citation by hand into a memory body" (genuine user error) and "Phase 5's walk leaked something during edit" (a bug we'd want to know about);
- the message says "dated dir preserved" but the dated dir is actually gone (mismatched message and state);
- you find the recovery instructions ("edit the offending file by hand, then re-invoke /dream and finalise again") confusing or insufficient.

---
