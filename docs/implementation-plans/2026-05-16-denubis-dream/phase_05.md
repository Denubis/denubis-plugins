# denubis-dream Implementation Plan — Phase 5: Reconciliation walk

**Goal:** In manual mode, after Phase 4's autonomous pass completes (or on re-invocation when a dated dir exists), the user walks the dated-dir state memory-by-memory: skipped memories first (triage), then existing memories in mtime-ascending order (stalest first, batched when keep-clean), then flagged regions with Opus-drafted promote scaffolds. Each decision persists to the dated dir before the next turn begins (mirror first, log last). Abandoned walks resume cleanly. Walk-end auto-presents the finalisation y/n prompt.

**Architecture:** In-session Opus runs the walk turn-by-turn using chat blockquotes for evidence presentation (no terminal UI). All persistence is Bash + skill text. The decisions.log is JSONL (per design — eliminates escaping ambiguity for instructions containing spaces, quotes, newlines). Resume detection is `jq` over decisions.log to build a decided-set, then walk-from-first-undecided per stream.

**Tech Stack:** Read/Write/Edit (mirror updates, `.audit.md` appends), Bash (jq decisions.log parsing, mtime sort, file checks), Claude Code chat (blockquoted evidence presentation, free-form user responses).

**Scope:** Phase 5 of 7.

**Codebase verified:** 2026-05-17 (memory set is 12 entries — manual walk is practical; `jq` available at `/usr/bin/jq` — decisions.log parsing unblocked).

**Phase Type:** functionality

**Deviations from design's literal text (user-approved):**

1. **Mid-walk persistence order is `mirror → ## User edits → decisions.log`** (the design's literal order is log first; that ordering has a resume-safety bug where a crash between log and mirror writes leaves the walk thinking the decision is applied when the mirror is stale). The deviation preserves the design's invariant that "dated-dir state is what gets applied at finalisation".
2. **Existing-memory turns offer a 4th verb `reject` not in design DR3's vocabulary** (`keep` / `prune` / `edit`). `reject` is a meta-verb meaning "revert the mirror to byte-for-byte live state, discarding Phase 4's recommendation entirely". Its action-outcome table (see Task 4 below) makes it: a no-op when the recommendation was `keep` (mirror was already at live); a revert-to-live when the recommendation was `edit` (drops Opus's revision); a don't-prune when the recommendation was `prune`. This adds a clean user-facing way to discard a recommendation without typing the full revert as an `edit` instruction; without it, the user would have to compose long edit instructions to undo Opus's proposed edits. The deviation also touches the walk-end summary (Task 9: rejected memories are counted in the `kept` total because their final mirror state equals live), the decisions.log action enum (Task 6 lists `reject` as a valid action), and the resume terminal-action set (Task 8 lists `reject` as a memory-stream terminal action). The design plan's DR3 should be patched in a separate design-plan commit to reflect this extension to the memory-stream vocabulary.

---

## Acceptance Criteria Coverage

This phase implements and verifies:

### denubis-dream.AC5: Reconciliation walk — existing memories
- **denubis-dream.AC5.1 Success:** Walk visits existing memories in `mtime` ascending order (stalest first).
- **denubis-dream.AC5.2 Success:** Memories with `keep` disposition and no code-artefact flags are batched ("N memories pass cleanly — confirm batch keep? [y/n]").
- **denubis-dream.AC5.3 Success:** Per-memory turn quotes `## Evidence` and `## Changes` from `.audit.md` as chat blockquotes; offers the recommended disposition.
- **denubis-dream.AC5.4 Success:** User verb `accept` applies the proposed mirror state (the dated-dir mirror is already correct; no live `memory/` write occurs).
- **denubis-dream.AC5.5 Success:** User verb `prune` writes `<!-- PRUNE -->` marker to the dated-dir mirror; disposition updates to `prune`.
- **denubis-dream.AC5.6 Success:** User verb `edit <instructions>` revises the dated-dir mirror per instructions; appends `## User edits` section to `.audit.md` noting the deviation from auto-recommendation.
- **denubis-dream.AC5.7 Success:** Abandoning the walk mid-stream and re-invoking `/dream` resumes from the first entry not yet present in `memory.dream-DATE/decisions.log`.
- **denubis-dream.AC5.8 Failure:** Live `memory/` file mtimes are unchanged after the walk (verified pre/post the walk; only finalisation may modify them).
- **denubis-dream.AC5.9 Success:** Every per-turn decision appends one JSON object on its own line to `memory.dream-DATE/decisions.log` (fields: `ts`, `action`, `stream`, `identifier`, `instruction`) before the next turn begins. Each line is independently parseable; instructions containing spaces, quotes, or newlines do not break parsing.
- **denubis-dream.AC5.10 Success:** Walk-end is reached when every existing memory + every flagged region has at least one entry in `decisions.log`; at walk-end Opus automatically presents the finalisation summary and `y/n` prompt.
- **denubis-dream.AC5.11 Success:** Re-decisions append fresh lines to `decisions.log`; finalisation reads the most recent line per identifier (last-write-wins per entry).

### denubis-dream.AC6: Reconciliation walk — flagged regions and promote
- **denubis-dream.AC6.1 Success:** After existing memories, walk visits `flagged/region-NNN.flagged.md` files in numeric order.
- **denubis-dream.AC6.2 Success:** Per-flagged-region turn quotes the transcript excerpt + why-memory-worthy note as blockquotes; Opus drafts a scaffold (`name`, `description`, `type`, body grounded in the excerpt).
- **denubis-dream.AC6.3 Success:** User verb `accept` writes the scaffold to `memory.dream-DATE/promoted/<name>.md`.
- **denubis-dream.AC6.4 Success:** User verb `edit <instructions>` revises the scaffold; user can re-accept the revision.
- **denubis-dream.AC6.5 Success:** User verb `dismiss` leaves the flagged file in place; no `promoted/` entry is written; the flagged file is discarded at finalisation.

**Note:** the design's `metadata.type` in AC6.2 is implemented as flat `type:` (per the lastAudited cascade fix established in Phase 3).

---

<!-- START_TASK_1 -->
### Task 1: `## Walk entry` section

**Verifies:** entry-point routing for AC5.* / AC6.* (a precondition for the walk)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after Phase 4's `## Autonomous exit` section.

**Implementation:**

Add a `## Walk entry` section. Two cases lead here:

````markdown
## Walk entry

Manual mode enters the walk in two situations:

1. **Phase 4 just completed in this same session** — autonomous-pass tail flows directly into the walk. No dated-dir-existence check needed; the dated dir was just created/completed.
2. **Re-invocation when a dated dir exists** — `/dream` was invoked again after Phase 2's no-op detection detected an existing dated dir for today. Resume detection (`## Resume detection`) determines which entries are already decided; walk continues from there.

Both paths converge on the same walk loop. The only difference is that case (2) reads `decisions.log` to skip already-decided entries; case (1) has an empty (or missing) decisions.log and starts from the first entry in walk order.

Before the walk loop starts:

- Snapshot live `memory/*.md` mtimes — re-check at walk-end to verify AC5.8 (no live mutation during the walk).
- Print a one-line walk preamble: `denubis-dream: walk start. S skipped, E existing, F flagged. mtime baseline captured.`
````

**Verification (operational):**

- After Phase 4 completes in manual mode, confirm the walk-entry preamble prints before the first turn.
- After deleting decisions.log mid-dream and re-invoking `/dream`, confirm the same preamble prints (re-entry) and walk starts from the first entry.
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: `## Walk order` section

**Verifies:** AC5.1 (mtime ascending), AC5.2 (batched keep-clean), AC6.1 (flagged regions in numeric order)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Walk entry`.

**Implementation:**

Add a `## Walk order` section that documents the three-stream walk order and the batching rule.

The section text:

````markdown
## Walk order

The walk visits entries in three streams, in this order:

1. **Skipped memories** (any entry in `<dated_dir>/SKIPPED.md`) — surfaced first. Triage with `keep / prune / retry` (see `## Skipped-memory turn`).
2. **Existing memories** in `mtime`-ascending order (stalest first, per design DR13). Determined by:
   ```bash
   ls -tr "$MAIN_DIR"/memory/*.md | xargs -n1 basename
   ```
   Filter out `MEMORY.md` (the index, not a memory). For each, the corresponding `<dated_dir>/<name>.audit.md` carries the recommendation.
3. **Flagged regions** in numeric order (`region-001.flagged.md`, `region-002.flagged.md`, …). Determined by:
   ```bash
   ls "$DATED_DIR"/flagged/region-*.flagged.md 2>/dev/null | sort
   ```

**Batched keep-clean (AC5.2).** Before walking existing memories individually, identify the subset that are "keep-clean":

- `## Disposition` in `.audit.md` is `keep` (the trim line, case-insensitive, leading/trailing whitespace ignored).
- `## Code-artefact flags` in `.audit.md` contains no MISS lines (the literal substring `"verify or edit"` is absent — that's the marker Phase 3 uses for misses).

If ≥2 keep-clean memories exist, batch them with a single prompt:

```
denubis-dream: 7 memories pass cleanly (keep disposition, no code-artefact misses):
  - feedback_halt-when-sideways
  - feedback_readback-restraint
  - ...

Confirm batch keep? [y/n]
```

If the user answers `y`: write one decisions.log line per memory (`action: "accept"`, `instruction: null`) — the mirrors are already correct (Phase 4 wrote byte-for-byte copies). The walk proceeds straight to the first non-keep-clean memory.

If the user answers `n`: each keep-clean memory falls through to its own individual turn (the user gets to see each one).

**Why batch.** Walking 12 individually-keep-clean memories one-by-one wastes the user's time on entries that need no decision. The batched prompt preserves "yes, I want to see each one" as a fallback for users who want full visibility.

**Skipped memories aren't batched** even if there are many — they need individual triage because the user's options (keep/prune/retry) are decision-bearing, not the same routine accept.
````

**Verification (operational):**

- After a Phase 4 pass that produces ≥2 keep-disposition + no-flag memories, the walk prints the batched prompt with all those memories listed.
- After answering `y` to the batched prompt, `decisions.log` contains one line per batched memory.
- The walk's next turn is the first non-keep-clean memory in mtime-ascending order.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: `## Skipped-memory turn` section

**Verifies:** error-recovery for AC3.6 (skipped memories surface at walk start with triage options)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Walk order`.

**Implementation:**

Add a `## Skipped-memory turn` section.

The section text:

````markdown
## Skipped-memory turn

For each entry in `<dated_dir>/SKIPPED.md`, the walk presents:

> ### Skipped memory: `<name>`
>
> This memory's Phase 3 evidence-retrieval subagent failed — no `## Evidence` was collected. Phase 4 did not judge it. You decide:
>
> - `keep` — leave it untouched in live `memory/`; treat as still valid (no audit cycle this time)
> - `prune` — drop the memory from live `memory/` (skipping evidence-driven judgement; do this only if you already know it's stale)
> - `retry` — re-dispatch Phase 3 for this memory only (a fresh Sonnet subagent gets the same windowed transcript)
>
> What would you like to do?

User responds with one of the three verbs (case-insensitive).

**On `keep`:**
- Mirror written as byte-for-byte copy of live (matches AC5.4 semantics: no live mutation, just stash the proposed state in the mirror).
- decisions.log line: `{"ts": <ISO>, "action": "keep", "stream": "skipped", "identifier": "<basefile>", "instruction": null}` where `<basefile>` is the memory's filename **including the `.md` extension** (e.g., `feedback_review-all-levels.md`). This matches the decisions.log identifier convention used by the memory stream — see Phase 5 Task 6 field table. Same convention everywhere keeps resume detection (Phase 5 Task 8) a single equality test, not a stream-specific normalisation.
- The `<basefile>` value is parsed cleanly from SKIPPED.md's strict `- <basefile>` lines (Phase 3 Task 6's Important-1 fix wrote them without annotations).

**On `prune`:**
- Mirror written as `<!-- PRUNE -->`.
- decisions.log line with `action: "prune"`, `stream: "skipped"`, `identifier: "<basefile>"` (same convention as keep).

**On `retry`:**

The retry verb composes by *delete-and-replay* against the existing Phase 3 + Phase 4 resume infrastructure. Phase 3's per-memory dispatch (Task 2) and Phase 4's judgement orchestration (Task 4) are already idempotent and scope work to entries with missing `## Evidence` or missing `## Disposition` respectively. Deleting this memory's artefacts is sufficient to make those existing loops re-process exactly this one entry; no new single-memory entry-point code needs to exist in Phase 3 or Phase 4.

```bash
# $basefile is the memory's filename WITH .md, parsed from SKIPPED.md (e.g. feedback_X.md)
name="${basefile%.md}"   # stripped form for derived filenames

# 1. Delete the (failed-or-stale) audit so Phase 3's missing-Evidence check redispatches.
rm -f "$DATED_DIR/$name.audit.md"

# 2. Delete the windowed substrate so it's regenerated fresh (cheap; jq runs again over the
#    same source files; lastAudited bound is unchanged).
rm -f "$DATED_DIR/.windowed/$name.jsonl"

# 3. Remove this memory's line from SKIPPED.md so Phase 3's regenerate-on-each-pass logic
#    doesn't re-list it before the retry has a chance to succeed. Preserve other lines.
if [ -f "$DATED_DIR/SKIPPED.md" ]; then
  grep -v "^- $basefile\$" "$DATED_DIR/SKIPPED.md" > "$DATED_DIR/SKIPPED.md.tmp" && \
    mv "$DATED_DIR/SKIPPED.md.tmp" "$DATED_DIR/SKIPPED.md"
  [ -s "$DATED_DIR/SKIPPED.md" ] || rm -f "$DATED_DIR/SKIPPED.md"
fi

# 4. Re-execute Phase 3's `## Pre-windowing transcripts` block AND `## Per-memory evidence
#    retrieval` orchestrator. The orchestrator's `## Evidence`-presence check (Phase 3 Task 2)
#    naturally scopes the dispatch to the just-deleted audit — every other memory's audit
#    file still exists with a populated `## Evidence`, so they are skipped. Only the just-
#    deleted entry triggers a new Sonnet subagent dispatch.

# 5. Re-execute Phase 4's `## Judgement orchestration` block. Its `## Disposition`-presence
#    check (Phase 4 Task 4) similarly scopes the work to the just-rewritten audit — every
#    other audit already has `## Disposition`, so Opus only judges the one new audit.
```

- **On success** (new `.audit.md` with both `## Evidence` populated by Phase 3 and `## Disposition` populated by Phase 4): re-enter the walk. The retried memory is no longer in `SKIPPED.md`; it falls into the regular memory-stream walk at its mtime-ordered position. Walk continues from there.
- **On failure** (the Phase 3 subagent fails a second time): Phase 3 Task 6's `SKIPPED.md` regeneration re-adds the entry. Print the failure and re-present the skipped-memory triage prompt so the user can fall back to `keep` or `prune`.

**No `decisions.log` line is written for a `retry` attempt itself** — `retry` is meta (it transitions the entry from "skipped" to "regular walk participant" OR loops back to triage). The decisions.log line is written only for the resulting `keep` / `prune` / per-existing-memory verb (`accept` / `reject` / `edit` / `prune`).

**Why this composes (vs. inventing single-memory entry points).** Phase 3 Task 1's `## Pre-windowing transcripts` iterates all memories, but writing one file per memory is idempotent — re-running it after re-creating one `<name>.jsonl` is wasted-but-cheap. Phase 3 Task 2 + Phase 4 Task 4 both already use missing-section checks as their "skip if already done" predicate; re-invoking them with one entry's marker file deleted is structurally the same as a partial resume after a crash. The retry path is thus the same code path as crash recovery, just with the implementer choosing which entry to re-trigger.

**Why surface first.** Skipped memories represent unresolved Phase 3 failures. Surfacing them before the rest of the walk means the user can attempt recovery while context is fresh. Burying them after the regular walk risks the user clicking through them inattentively at the end.
````

**Verification (operational):**

Force a skipped state on one memory (move its windowed file aside so the subagent has no input). After Phase 3+4 run, invoke `/dream` manually:
- Confirm the skipped-memory turn is the FIRST prompt.
- Choose `retry`; confirm Phase 3+4 re-runs for this memory only (other `.audit.md` mtimes unchanged).
- After retry succeeds, confirm `SKIPPED.md` no longer lists this memory, and the walk continues with it in mtime order.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: `## Per-existing-memory turn` section

**Verifies:** AC5.3 (blockquoted evidence + recommended disposition), AC5.4 (`accept`), AC5.5 (`prune`), AC5.6 (`edit`), implicitly AC5.8 (no live mutation)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Skipped-memory turn`.

**Implementation:**

Add a `## Per-existing-memory turn` section.

The section text:

````markdown
## Per-existing-memory turn

For each existing-memory entry the walk visits individually (skipping batched-keep-clean entries):

1. **Read** `<dated_dir>/<name>.audit.md`.
2. **Extract** the `## Evidence`, `## Code-artefact flags`, `## Changes`, and `## Disposition` sections.
3. **Present** to the user as chat blockquotes:

> ### Existing memory: `<name>` (recommended: `<disposition>`)
>
> #### Evidence
>
> > <quoted ## Evidence content, line-by-line>
>
> #### Code-artefact flags
>
> > <quoted ## Code-artefact flags content>
>
> #### Proposed changes
>
> > <quoted ## Changes content>
>
> Your call: `accept` / `reject` / `edit <instructions>` / `prune`

4. **Wait** for the user's response. Parse one of the four verbs (case-insensitive).

**Action → outcome mapping** (per DR5-1 table):

| Recommendation | `accept` | `reject` | `edit <x>` | `prune` |
|----------------|----------|----------|------------|---------|
| `keep` | mirror unchanged | (no-op; same as accept) | rewrite mirror per `<x>` | mirror = `<!-- PRUNE -->` |
| `edit` | mirror unchanged (Phase 4 already wrote it) | mirror = byte-for-byte copy of live (revert Opus's edit) | rewrite mirror per `<x>` (user overrides Opus) | mirror = `<!-- PRUNE -->` |
| `prune` | mirror = `<!-- PRUNE -->` (Phase 4 already wrote it) | mirror = byte-for-byte copy of live (don't prune) | rewrite mirror per `<x>` | mirror unchanged (re-affirm) |

**Edit instructions** are interpreted by you (Opus, in this session). The user might say `edit shorten the body to 3 paragraphs` or `edit rename scripts/foo.py to scripts/identity.py`. You apply the instruction to the current mirror body (which is the proposed-state body from Phase 4) and write the revised body back to the mirror.

**`## User edits` audit trail.** If the user's action deviates from the recommendation (`reject`, `edit`, or any verb other than the one Phase 4 recommended), append a `## User edits` section to the corresponding `.audit.md`:

```markdown
## User edits

- 2026-05-17T14:33:42Z — recommendation was `edit`; user chose `prune` (no instruction provided).
- 2026-05-17T14:33:50Z — recommendation was `keep`; user chose `edit reword the second paragraph to drop the example`. Mirror revised accordingly.
```

The `## User edits` section is APPEND-only (re-decisions append further lines). It is the audit trail for "why the dated-dir state diverges from Phase 4's recommendation".

**No live `memory/` writes** happen in this turn. AC5.8 — mtime snapshot taken at walk entry — is checked at walk-end; if any live-memory mtime differs, halt and surface the violation.

**Persistence order** (per user-approved DR5-3 deviation): **mirror update → `## User edits` append → decisions.log append**. All three writes complete before the next turn begins.
````

**Verification (operational):**

- Walk one keep-recommended memory; type `accept`; confirm decisions.log gets one line; no other file changes.
- Walk one edit-recommended memory; type `edit <new instruction>`; confirm the mirror body is rewritten, `## User edits` is appended, and decisions.log gets a line.
- Walk one prune-recommended memory; type `reject`; confirm the mirror is rewritten to byte-for-byte match the live memory (Phase 4's `<!-- PRUNE -->` is overwritten).
- After the walk, `diff` live `memory/<name>.md` against its previous-session mtime/contents to confirm AC5.8 (live unchanged).
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: `## Per-flagged-region turn` section

**Verifies:** AC6.1, AC6.2, AC6.3, AC6.4, AC6.5

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Per-existing-memory turn`.

**Implementation:**

Add a `## Per-flagged-region turn` section.

The section text:

````markdown
## Per-flagged-region turn

After all existing memories (including skipped triage and batched + individual turns), the walk visits `<dated_dir>/flagged/region-NNN.flagged.md` files in numeric order.

**Per-region resume check.** If `<dated_dir>/flagged/<region-id>.scaffold.md` exists at the start of a region's turn, the region had at least one prior `edit` iteration in a previous session. Use the persisted scaffold file as the starting scaffold (skip step 2's drafting). Task 7's mid-walk persistence documents the write of this file on every `edit` iteration; this section reads it on resume so prior edits are not lost. If the scaffold file is absent, fall through to step 2 (first-time draft).

For each flagged region:

1. **Read** the flagged file. Extract the `## Coverage`, `## Excerpt`, and `## Why memory-worthy` sections.
2. **Draft a memory scaffold** (you, Opus, in this session) — UNLESS the per-region resume check above located a persisted `<region-id>.scaffold.md`, in which case use that file's contents verbatim as the scaffold and skip the drafting heuristics below. The scaffold has:
   - `name`: a short-kebab-case slug derived from the excerpt's core claim. Pattern: `<type-prefix>_<topic-words>` to match existing memory naming (`feedback_review-all-levels`, `project_agent-teams-design-wip`).
   - `description`: one-line summary in the discovery-surface style (used by future `denubis-dream` runs and by Claude's session-start memory loading).
   - `type`: one of `feedback`, `project`, `user`, `reference` (FLAT — top-level frontmatter field, per the convention established in Phase 3).
   - body: a short prose draft grounded in the excerpt, mirroring the structure of existing same-`type` memories (e.g., feedback memories have the rule statement plus `**Why:**` + `**How to apply:**` lines; project memories have a status + key decisions section).
3. **Present** to the user as chat blockquotes:

> ### Flagged region: `region-NNN`
>
> #### Coverage
>
> > <quoted ## Coverage content>
>
> #### Excerpt
>
> > <quoted ## Excerpt blockquote>
>
> #### Why memory-worthy
>
> > <quoted ## Why memory-worthy content>
>
> #### Proposed scaffold
>
> ```markdown
> ---
> name: <draft-slug>
> description: <draft-description>
> type: <draft-type>
> ---
> <draft-body>
> ```
>
> Your call: `accept` / `edit <instructions>` / `dismiss`

4. **Parse** the user's response.

**On `accept`:**
- Write the scaffold to `<dated_dir>/promoted/<draft-slug>.md` (the slug becomes the filename; collision detection happens at finalisation per AC7.7).
- decisions.log line: `{"action": "accept", "stream": "flagged", "identifier": "region-NNN", "instruction": null}`.

**On `edit <instructions>`:**
- Revise the scaffold per the user's instructions (rename, rewrite, change type, restructure body — whatever the instruction says).
- **Persist the revised scaffold** to `<dated_dir>/flagged/<region-id>.scaffold.md` (atomic `.tmp + mv` write, same pattern as Phase 6). This survives mid-walk abandonment: the persistence happens as part of Task 7's mid-walk persistence sequence (substantive write → decisions.log append) BEFORE control returns to the user for the next iteration. On resume, the per-region resume check at the top of this section reads the persisted file so the user's prior edits are preserved across sessions.
- Re-present the revised scaffold with the same prompt (`accept / edit / dismiss`). The user can iterate as many times as they want; only the most recent accepted scaffold lands in `promoted/`.
- Each `edit` iteration is one decisions.log line — the last line per identifier wins (per AC5.11). The scaffold file is rewritten on every iteration so it always reflects the latest revision, not just the most recent decisions.log instruction.

**On `dismiss`:**
- Do NOT write to `promoted/`. The flagged file stays in `<dated_dir>/flagged/` but is discarded at finalisation.
- decisions.log line: `{"action": "dismiss", "stream": "flagged", "identifier": "region-NNN", "instruction": null}`.

**No live `memory/` writes** happen here either. Promoted scaffolds are moved from `<dated_dir>/promoted/` into live `memory/` only at finalisation.

**No `## User edits` audit trail** for flagged regions — the regions are pre-judgement (no auto-recommendation to deviate from). The decisions.log line carries the full action history.

**Why flagged comes last.** Existing memories are decision-bearing (the user is REVIEWING an audit). Flagged regions are creation-bearing (the user is AUTHORING new memories). Two distinct cognitive modes; surfacing all reviews first, then all creations, keeps the user in one mode at a time.
````

**Verification (operational):**

- After Phase 3 produces ≥1 flagged region, walk through it: confirm scaffold is presented with `name`, `description`, FLAT `type:`, and a body grounded in the excerpt.
- Type `edit add a paragraph noting the user's preference for ordering`; confirm the revised scaffold is presented next.
- Confirm `<dated_dir>/flagged/<region-id>.scaffold.md` exists after the edit iteration and its body matches the revised scaffold just presented (resume-survives-crash invariant).
- Kill the session before issuing `accept` / `dismiss`; re-invoke `/dream`. Confirm the per-region resume check fires (the same revised scaffold is re-presented, not the original drafted-from-flagged-file scaffold).
- Type `accept` on the revision; confirm `<dated_dir>/promoted/<slug>.md` exists with the revised content. (The `<region-id>.scaffold.md` file remains in `flagged/` until finalisation removes the dated dir — no cleanup is required mid-walk.)
- Type `dismiss` on another flagged region; confirm no `promoted/` file is written.
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: `## Decisions log` section

**Verifies:** AC5.9 (JSONL format), AC5.11 (last-write-wins)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Per-flagged-region turn`.

**Implementation:**

Add a `## Decisions log` section that pins the JSONL format and the append-only semantics.

The section text:

````markdown
## Decisions log

`<dated_dir>/decisions.log` is append-only JSONL. Every per-turn decision writes exactly one line. Each line is one JSON object:

```json
{"ts": "2026-05-17T14:33:42Z", "action": "edit", "stream": "memory", "identifier": "feedback_review.md", "instruction": "remove paragraph about git log"}
```

**Fields:**

| Field | Type | Notes |
|-------|------|-------|
| `ts` | string (ISO 8601 with `Z` suffix) | the moment the user's response was received |
| `action` | string | one of: `accept`, `reject`, `edit`, `prune` (memory stream); `accept`, `edit`, `dismiss` (flagged stream); `keep`, `prune` (skipped stream) |
| `stream` | string | one of: `memory`, `flagged`, `skipped` |
| `identifier` | string | for `memory`/`skipped`: the memory's filename including `.md` extension. For `flagged`: the region ID (`region-001`, `region-002`, …) |
| `instruction` | string or `null` | the user's edit instruction; `null` for non-edit actions; the FULL instruction including any embedded spaces/quotes/newlines (JSON escaping handles all of them) |

**Why JSONL (per design):** a space-separated format (e.g., `<ts> <action> <stream> <id> <instruction>`) breaks the moment an instruction contains a space, a quote, or a newline. JSONL lets `instruction` be an arbitrary string with no escaping ambiguity.

**Append-only.** Never rewrite or edit existing lines. Re-decisions append fresh lines. Finalisation uses last-line-per-identifier (per stream) semantics.

**Bash helper** (skill text doesn't need to re-derive this every turn — write a function once and reuse):

```bash
log_decision() {
  local ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local action="$1" stream="$2" identifier="$3" instruction="$4"
  if [ -z "$instruction" ]; then
    jq -nc --arg ts "$ts" --arg a "$action" --arg s "$stream" --arg id "$identifier" \
      '{ts: $ts, action: $a, stream: $s, identifier: $id, instruction: null}' \
      >> "$DATED_DIR"/decisions.log
  else
    jq -nc --arg ts "$ts" --arg a "$action" --arg s "$stream" --arg id "$identifier" --arg instr "$instruction" \
      '{ts: $ts, action: $a, stream: $s, identifier: $id, instruction: $instr}' \
      >> "$DATED_DIR"/decisions.log
  fi
}
```

The function uses `jq -nc` to construct each line — `jq` handles all string escaping correctly even for multi-line instructions with embedded quotes.
````

**Verification (operational):**

- After several walk turns, `wc -l decisions.log` equals the number of decisions made.
- Every line parses as JSON: `jq -e '.' decisions.log | head` succeeds with no errors.
- Force an instruction with embedded quotes and newlines (e.g., `edit add this paragraph: 'foo bar\nbaz "quoted"'`); confirm the resulting log line round-trips through `jq` cleanly.
- Re-decide one memory; confirm a second line appears with the same identifier.
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: `## Mid-walk persistence` section

**Verifies:** AC5.9 (decisions persist before next turn) + the user-approved persistence-order deviation

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Decisions log`.

**Implementation:**

Add a `## Mid-walk persistence` section.

The section text:

````markdown
## Mid-walk persistence

Every per-turn decision triggers up to THREE writes that complete before the next turn begins. The order is:

1. **Substantive write.** The dated-dir state that finalisation will apply (for terminal actions) OR the in-progress state preserved for resume (for the flagged stream's `edit` iteration, which is non-terminal). Stream- and action-specific:
   - **memory stream (`accept` / `reject` / `edit` / `prune`):** mirror update at `<dated_dir>/<name>.md` (the post-judgement mirror; finalisation transfers it to live `memory/`).
   - **flagged stream, `accept`:** write the scaffold to `<dated_dir>/promoted/<draft-slug>.md`.
   - **flagged stream, `edit`:** write the revised scaffold to `<dated_dir>/flagged/<region-id>.scaffold.md`. This is the per-iteration persistence path that Task 5's per-region resume check reads on re-entry; it is the ONLY way mid-edit state survives a session crash for flagged regions.
   - **flagged stream, `dismiss`:** no substantive write (the original `region-NNN.flagged.md` stays in place; dismissed at finalisation per design DR9).
   - **skipped stream (`keep` / `prune`):** no substantive write (skipped memories are decided-only-on-paper; finalisation reads decisions.log for the disposition).
2. **`## User edits` append** to the corresponding `.audit.md` (only when the user's action deviates from Phase 4's recommendation). Audit trail for "why does the mirror diverge from the recommendation?". Skipped-stream and flagged-stream turns have no `.audit.md` to append to — those skip step 2.
3. **decisions.log append.** The resume marker. Always last.

**Why this order (deviation from design):** the design's literal text orders log first, then mirror. That ordering has a resume-safety bug: a crash between the log-append and the mirror-update leaves the walk thinking the decision is applied (resume skips re-presenting) while the mirror is stale (finalisation applies wrong state). Mirror-first means a crash anywhere causes resume to re-present the entry — the user re-decides, but the system never silently applies an unintended state.

**All-or-nothing per turn.** If any of the three writes fails (disk full, permission error), halt the walk immediately and surface the failure to the user. Do not proceed to the next turn with partial persistence.

**No live `memory/` writes** at any step. Finalisation is the only point at which the mirror state transfers to live `memory/`. Phase 5's contract is "all changes live in the dated dir".
````

**Verification (operational):**

- Walk one memory with an `edit` action. Note the mtimes of mirror, `.audit.md`, and `decisions.log` files in `<dated_dir>`.
- Confirm mirror mtime < `.audit.md` mtime < `decisions.log` mtime (ordering preserved).
- Force a crash (kill the session) mid-edit of a hypothetical second memory; on re-invocation, confirm the second memory's mirror is stale and the walk re-presents it.
<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: `## Resume detection` section

**Verifies:** AC5.7 (resume from first not-yet-decided)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Mid-walk persistence`.

**Implementation:**

Add a `## Resume detection` section.

The section text:

````markdown
## Resume detection

On `/dream` re-invocation when a dated dir exists, parse `<dated_dir>/decisions.log` (if it exists; empty/missing = start from the first entry).

**"Decided" requires a TERMINAL action, not any line** (Important-4 fix). For the flagged stream, `edit` is iterative (the user keeps revising the scaffold until they're happy) — only `accept` and `dismiss` close out a flagged region. Treating any line as decided would skip mid-revision regions on resume. The terminal-action set is stream-specific:

| Stream | Terminal actions |
|--------|------------------|
| `memory` | `accept`, `reject`, `edit`, `prune` (each represents one user turn that completed; `edit` is terminal here because Opus applies the instruction and the turn ends) |
| `flagged` | `accept`, `dismiss` only (`edit` is iterative — re-presents the revised scaffold for further iteration; no terminal commitment yet) |
| `skipped` | `keep`, `prune` only (`retry` re-dispatches Phase 3 and writes no decisions.log line itself — only the resulting `keep`/`prune` or fall-through to a memory-stream entry is logged) |

```bash
# Build the decided-set: most recent TERMINAL decision per (stream, identifier).
# Non-terminal actions (flagged-stream 'edit') are ignored for the decided-set;
# they still append to decisions.log as audit trail, but don't satisfy resume.
if [ -f "$DATED_DIR"/decisions.log ]; then
  DECIDED_JSON=$(jq -s '
    def is_terminal(d):
      (d.stream == "memory"  and (d.action | IN("accept","reject","edit","prune"))) or
      (d.stream == "flagged" and (d.action | IN("accept","dismiss"))) or
      (d.stream == "skipped" and (d.action | IN("keep","prune")));
    reduce .[] as $d ({};
      if is_terminal($d) then .[$d.stream + ":" + $d.identifier] = $d else . end
    )
  ' "$DATED_DIR"/decisions.log)
else
  DECIDED_JSON="{}"
fi

# Per-stream membership check:
is_decided() {
  # $1 = stream, $2 = identifier
  echo "$DECIDED_JSON" | jq -e --arg key "${1}:${2}" '.[$key]' >/dev/null
}
```

**Identifier convention is consistent across all streams** (Important-1 fix): the identifier is the memory file's basename WITH the `.md` extension for `memory` and `skipped` streams (matches the Phase 5 Task 6 field table), and the region ID (e.g., `region-001`) for the `flagged` stream. SKIPPED.md is parsed cleanly to extract `<basefile>.md` (Phase 3 Task 6 writes strict `- <basefile>` lines). No stream-specific `.md` appending or annotation stripping is needed at the resume layer.

**Walk continues from the first undecided entry per stream** (in the order documented in `## Walk order`):

- **Skipped stream:** read `<dated_dir>/SKIPPED.md`; each line is `- <basefile>` (basename with `.md` extension, no annotation per Important-1 fix). Strip the `- ` prefix and trim whitespace to get the identifier directly. For each, skip if `is_decided skipped "$basefile"` returns 0; otherwise present the skipped-memory turn.
- **Memory stream:** walk `ls -tr <main_dir>/memory/*.md`; for each entry, take `$(basename ...)` (with `.md`), skip `MEMORY.md`, skip if also in the SKIPPED.md basefile list (already covered by skipped stream), skip if `is_decided memory "$basefile"`; otherwise present the per-existing-memory turn (after first deciding whether batched-keep-clean is feasible across the remaining undecided memories).
- **Flagged stream:** walk `<dated_dir>/flagged/region-*.flagged.md` sorted; for each, take the region ID (`region-NNN`, no `.flagged.md` extension), skip if `is_decided flagged region-NNN`; otherwise present the per-flagged-region turn.

**Re-decisions append fresh lines** (per AC5.11). The decided-set rebuild reads the LAST TERMINAL line per (stream, identifier), so a re-decision overrides earlier terminal choices for the same entry. If the user wants to re-decide an already-decided entry, they need to invoke a specific re-entry workflow (out of scope for Phase 5 — they can manually delete the relevant decisions.log lines and re-invoke `/dream`, or simply re-invoke and accept the previous decision via the batched-keep-clean prompt if it's still keep-clean).

**Batched-keep-clean and resume.** Resume re-evaluates batched-keep-clean over the still-undecided subset. If 5 of 7 keep-cleans were already accepted in a prior session and the remaining 2 are still keep-clean, resume offers a new batch of 2.

**Flagged-stream mid-edit resume** (Important-4 case in practice): a user starts a `region-NNN` turn, types `edit add a paragraph noting X`, sees the revised scaffold, then quits the session before typing `accept` or `dismiss`. Task 7 step 1's flagged-stream-`edit` write path persisted the revised scaffold to `<dated_dir>/flagged/region-NNN.scaffold.md` BEFORE the decisions.log line was appended. The decisions.log now has one line for `region-NNN` with `action: "edit"` — non-terminal. On resume, `is_decided flagged region-NNN` returns 1 (no terminal entry) → walk re-presents `region-NNN`; Task 5's per-region resume check finds `<dated_dir>/flagged/region-NNN.scaffold.md` and uses it as the starting scaffold (preserving the prior iteration's revisions). The user can continue iterating from where they left off; further `edit` instructions overwrite the same `.scaffold.md` file.
````

**Verification (operational):**

- Walk halfway through; `Ctrl-C` or kill the session.
- Re-invoke `/dream`. Confirm the walk preamble notes "X entries already decided" and the first prompt is for the next undecided entry in walk order.
- Continue to walk-end. Confirm decisions.log has one entry per memory + per flagged region (some entries may have multiple lines from re-decides — that's expected).
<!-- END_TASK_8 -->

<!-- START_TASK_9 -->
### Task 9: `## Walk-end detection + auto-finalise prompt` section

**Verifies:** AC5.10 (walk-end auto-prompt), AC5.8 (live mtime check at walk end)

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append after `## Resume detection`.

**Implementation:**

Add a `## Walk-end detection + auto-finalise prompt` section.

The section text:

````markdown
## Walk-end detection + auto-finalise prompt

After each turn's persistence completes, check coverage:

```bash
# All entries that should be decided. SKIPPED.md format (per Phase 3 Task 6's Important-1 fix):
# each line is exactly "- <basefile>" with the .md extension and NO annotation.
SKIPPED_ENTRIES=()
[ -f "$DATED_DIR"/SKIPPED.md ] && while IFS= read -r line; do
  # Strip leading "- " AND any trailing whitespace. Result: "<basefile>.md".
  entry="${line#- }"
  entry="${entry%"${entry##*[![:space:]]}"}"   # rtrim
  [ -n "$entry" ] && SKIPPED_ENTRIES+=("$entry")
done < "$DATED_DIR"/SKIPPED.md

MEMORY_ENTRIES=()
for f in "$MAIN_DIR"/memory/*.md; do
  bn=$(basename "$f")   # e.g. feedback_review-all-levels.md (WITH .md)
  [ "$bn" = "MEMORY.md" ] && continue
  # Skip if also in SKIPPED (already covered by skipped stream).
  # Both bn and SKIPPED_ENTRIES carry the .md extension — match cleanly.
  skip=false
  for s in "${SKIPPED_ENTRIES[@]}"; do
    [ "$bn" = "$s" ] && skip=true && break
  done
  $skip && continue
  MEMORY_ENTRIES+=("$bn")
done

FLAGGED_ENTRIES=()
for f in "$DATED_DIR"/flagged/region-*.flagged.md; do
  [ -e "$f" ] && FLAGGED_ENTRIES+=("$(basename "$f" .flagged.md)")
done

# All these must appear in decisions.log as a terminal action.
# Identifier convention (Important-1 fix): memory + skipped use <basefile>.md (with extension);
# flagged uses region-NNN (no extension). is_decided takes the identifier directly — no .md
# append/strip happens at the check layer.
ALL_DECIDED=true
for n in "${SKIPPED_ENTRIES[@]}"; do is_decided skipped "$n" || ALL_DECIDED=false; done
for n in "${MEMORY_ENTRIES[@]}"; do is_decided memory  "$n" || ALL_DECIDED=false; done
for n in "${FLAGGED_ENTRIES[@]}"; do is_decided flagged "$n" || ALL_DECIDED=false; done
```

If `ALL_DECIDED=true`, the walk has reached its end. Verify AC5.8 (live mtimes unchanged):

```bash
# Snapshot taken at walk entry: $LIVE_MTIME_BASELINE
LIVE_MTIME_NOW=$(stat -c '%Y' "$MAIN_DIR"/memory/*.md | sort | tr '\n' ' ')
if [ "$LIVE_MTIME_NOW" != "$LIVE_MTIME_BASELINE" ]; then
  echo "denubis-dream: AC5.8 VIOLATION — live memory/ mtimes changed during walk. HALT."
  echo "Baseline: $LIVE_MTIME_BASELINE"
  echo "Now:      $LIVE_MTIME_NOW"
  exit 1
fi
```

Then build and print the finalisation summary (per DR5-6 format):

```
denubis-dream: walk complete.
  X kept    (M batch-kept-clean + N individually accepted + R reject-reverted-to-live)
  Y edited  (P with user instructions, Q accepting Opus's edits unchanged)
  Z pruned
  W promoted from flagged regions
  V flagged regions dismissed
  S skipped memories: <names if any>

Apply to live memory/? [y/n]
```

Counts are derived from the most-recent decisions.log line per (stream, identifier). `reject` outcomes are counted in the `kept` total because their final mirror state equals live byte-for-byte — they appear as the `R` sub-count for transparency (an audit of "how many recommendations did the user discard?" is recoverable from the decisions.log, and the summary surfaces the aggregate without complicating the apply step). Per the user-approved deviation #2 in the phase header, `reject` is a meta-verb that resolves to a live-state mirror regardless of the recommendation it was applied against.

**If user answers `y`:** continue into Phase 6 finalisation in the same session.

**If user answers `n`:** dated dir persists. Re-invoking `/dream` enters the walk again; the user can re-decide any entry (re-decisions append fresh lines and override on finalise).

**No "finalise without walking everything" shortcut.** If `ALL_DECIDED=false`, the prompt doesn't fire — the walk continues from the first undecided entry. The design specifically forbids silently applying partial state.
````

**Verification (operational):**

- Walk to completion; confirm the summary prints with correct counts; confirm the `[y/n]` prompt fires.
- Answer `n`; confirm dated dir persists; re-invoke `/dream` and confirm the walk re-enters (the summary should print again when re-walked).
- Manually delete one decisions.log line for an existing memory; re-invoke `/dream`; confirm the walk re-presents that memory (resume detection finds it undecided again).
<!-- END_TASK_9 -->

<!-- START_TASK_10 -->
### Task 10: Replace Phase 4 pipeline stub + commit

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — replace Phase 4's trailing `## Pipeline status (Phase 4)` block.

**Implementation:**

Replace the Phase 4 stub with:

```markdown
## Pipeline status (Phase 5)

Reconciliation walk is in place: skipped memories triaged, existing memories walked mtime-ascending with batched keep-clean handling, flagged regions promoted with Opus-drafted scaffolds, decisions persist to JSONL between turns, abandoned walks resume cleanly, and walk-end auto-presents the finalise y/n prompt. Finalisation (Phase 6) lands next.

When invoked manually at this stage, the skill runs the full pipeline through the walk and prints the finalise summary; on `y`, the user sees:

> denubis-dream: finalisation not yet implemented. Dated dir persists at <path>; live `memory/` is unchanged.

On `n`, the dated dir persists for later re-entry.
```

**Single commit for the full Phase 5 set.**

```bash
git add plugins/denubis-dream/skills/dreaming/SKILL.md
git status
git commit -m "feat(dream): Phase 5 — reconciliation walk

Adds walk entry, three-stream walk order (skipped triage → existing
mtime-ascending with batched keep-clean → flagged numeric), per-stream
turn handlers (skipped: keep/prune/retry; existing: accept/reject/
edit/prune; flagged: accept/edit/dismiss), JSONL decisions.log (last-
write-wins per identifier), mid-walk persistence (mirror → ## User
edits → log; safer than design's literal log-first order), resume
detection via jq parse, and walk-end auto-finalise prompt with AC5.8
live-mtime invariant check.

Covers AC5.1 through AC5.11 and AC6.1 through AC6.5. Two
user-approved deviations from the design's literal text:
(1) persistence order is mirror-first not log-first (resume-safety);
(2) existing-memory turns offer a 4th verb 'reject' (meta: revert
mirror to live, discarding Phase 4 recommendation) on top of DR3's
keep/prune/edit. Both flagged in the Phase 5 header; design plan's
DR3 verb list to be patched in a separate design-plan commit."
```
<!-- END_TASK_10 -->
