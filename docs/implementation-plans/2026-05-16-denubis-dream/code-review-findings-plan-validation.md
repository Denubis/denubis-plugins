# Code Review Findings — plan-validation

## Status: APPROVED WITH NOTES

**Critical: 0 | Important: 3 | Minor: 4**

---

## Verification

No code to lint or test — this is a plan-validation review against a design document.

---

## Plan Alignment

Design-to-plan phase mapping:

- Phase 1 (Plugin scaffolding): ✓ implemented — full task coverage, codebase-verified shape
- Phase 2 (Autonomous-pass orchestration): ✓ implemented — mode detection, slug resolution, discovery, dated dir, no-op detection
- Phase 3 (Sonnet retrieval subagents): ✓ implemented — pre-windowing, per-memory dispatch + prompt, corpus scanner + prompt, SKIPPED.md, resumable retrieval
- Phase 4 (Opus judgement): ✓ implemented — gate semantics, diff-narrative, disposition computation, judgement orchestration, mirror writing, MEMORY.md regeneration, autonomous exit
- Phase 5 (Reconciliation walk): ✓ implemented — walk entry, walk order, skipped-memory triage, per-memory turn, per-flagged-region turn, decisions log, mid-walk persistence, resume detection, walk-end auto-prompt
- Phase 6 (Finalisation): ✓ implemented — finalise entry, collision pre-flight, atomic write pattern, mirror transfer, promoted move, MEMORY.md replacement, DoD #8 self-check, .tmp orphan cleanup, .last-dream write, dated-dir removal
- Phase 7 (Cron integration + UAT): ✓ implemented — cron-integration.md, uat-checklist.md, SKILL.md cron section, version bump 0.1.0 → 0.2.0

AC coverage matrix:

- AC1.1–AC1.6: ✓ Phase 1
- AC2.1–AC2.5: ✓ Phase 2 (design typo AC1→AC2 noted and corrected)
- AC3.1–AC3.8: ✓ Phase 3
- AC4.1–AC4.6: ✓ Phase 4
- AC5.1–AC5.11: ✓ Phase 5
- AC6.1–AC6.5: ✓ Phase 5
- AC7.1–AC7.10: ✓ Phase 6
- AC8.1–AC8.4: ✓ Phase 6 (AC8.4 already landed in Phase 1)
- AC9.1–AC9.4: ✓ Phase 7
- AC10.1–AC10.3: ✓ Phase 7

DR coverage:

- DR1 (no Python helpers): ✓ honoured throughout; every deterministic op is Bash
- DR2 (audit existing + flag deltas, no Sonnet authoring): ✓ Phase 3 Sonnet never writes candidate frontmatter; Phase 5 promote is Opus + user accept loop
- DR3 (disjoint disposition vocab): ✓ Phase 5 — `keep/prune/edit` for memory, `accept/edit/dismiss` for flagged, `keep/prune/retry` for skipped
- DR4 (mirror + per-memory verdict file layout): ✓ Phase 3/4
- DR5 (diff-narrative .audit.md shape): ✓ Phase 4
- DR6 (code-grep as separate flagged-item category): ✓ Phase 3 Task 3
- DR7 (anchored slug-pattern scan): ✓ Phase 2 Task 3 — regex `^${MAIN_SLUG}$|^${MAIN_SLUG}--worktrees-.+$` matches design exactly
- DR8 (per-memory time windowing): ✓ Phase 3 Task 1
- DR9 (finalisation removes dated dir): ✓ Phase 6 Task 10
- DR10 (Opus drafts promote-scaffold): ✓ Phase 5 Task 5
- DR11 (explicit --autonomous flag): ✓ Phase 2 Task 1
- DR12 (continue straight into reconciliation after autonomous): ✓ Phase 4 Task 7, Phase 5 Task 1
- DR13 (walk order mtime ascending): ✓ Phase 5 Task 2
- DR14 (.last-dream artefact): ✓ Phase 3 Task 1 (read), Phase 6 Task 9 (write)

Documented deviations from design:

- `frontmatter.metadata.lastAudited` → `frontmatter.lastAudited` (flat): flagged in Phase 2 header, Phase 3 header + tasks, Phase 5 Task 5, Phase 6 AC table. Consistent throughout. ✓
- `model: claude-sonnet-4-6` → `subagent_type: denubis-basic-agents:sonnet-general-purpose`: flagged in Phase 3 header + Task 2. ✓
- Design typo Phase 2 "Done when" cites AC1 → corrected to AC2 in Phase 2. ✓
- Phase 5 persistence order (mirror-first, not log-first): flagged explicitly in Phase 5 header and Task 7. ✓
- `schedule` skill is a Claude Code built-in (no plugin file): Phase 7 explicitly adopts scheduler-agnostic framing and cites this as the reason. ✓

DoD criteria coverage in UAT checklist:

- DoD #1–#10: all covered in Part A of uat-checklist.md. ✓
- 5 design-specified edge cases: slug suffix-collision (B.1), decisions.log edge identifiers (B.2), atomic-write interrupt (B.3), mid-walk abandonment (B.4), corpus coverage header (B.5). ✓

---

## Issues

### Important (count: 3)

**Important-1: decisions.log `identifier` field inconsistency — skipped stream uses basename with extension, memory stream without**

- **Location:** Phase 5 Task 6 (`## Decisions log` section) — field spec says `identifier` for `memory`/`skipped` is "the memory's filename including `.md` extension". Phase 5 Task 8 (`## Resume detection`) — `is_decided` call uses `is_decided memory "$n"` where `$n` is derived from `ls -tr ... | xargs -n1 basename` which produces `<name>.md` WITH extension, but Phase 5 Task 4 (`## Per-existing-memory turn`) instructs writing `"identifier": "feedback_review.md"` (with `.md`), while Phase 5 Task 3 (`## Skipped-memory turn`) writes decisions.log lines with `stream: "skipped"` but references the skipped memory by name WITHOUT `.md` in the SKIPPED.md list (which writes `- <name>` without `.md` per Phase 3 Task 6). Resume detection in Task 8 then calls `is_decided skipped "$n.md"` — but `$n` comes from stripping the `- ` prefix from SKIPPED.md lines, which contain names WITHOUT `.md`. The end-to-end path is: SKIPPED.md lists `feedback_review` (no extension) → resume builds `is_decided skipped "feedback_review.md"` → but the log line written in Task 3 skipped-memory turn uses `"identifier": "<name>"` (no `.md`). Cross-checking Task 3's actual log-line example: `"stream": "skipped", "identifier": "<name>"` — undefined whether that includes `.md`. The decisions.log field table says "memory's filename including `.md` extension" for both memory and skipped, but the SKIPPED.md list format (per Phase 3 Task 6 `echo "- $name"`) strips the `.md` because `$name=$(basename "$memfile" .md)`. This is a latent inconsistency that will cause resume detection to silently treat skipped memories as undecided even after the user has triaged them.
- **Fix:** Normalise `identifier` for skipped entries to always include `.md` extension, and ensure: (1) SKIPPED.md entries are written with `.md` appended; (2) the skipped-memory turn log line uses the `.md` form; (3) resume detection's `is_decided skipped` call matches. Alternatively, normalise to no-extension throughout for the skipped stream and update SKIPPED.md writing and resume accordingly. Pick one convention and state it explicitly in the decisions.log field table.

**Important-2: `## .tmp orphan cleanup` placement inconsistency — start cleanup is documented in Task 8 but instructed to live in Task 1**

- **Location:** Phase 6 Task 8 (`## .tmp orphan cleanup` section), final paragraph: "Position the start cleanup at Phase 6 entry, NOT here. The skill text body should call the start cleanup right after Task 2's collision pre-flight." But Phase 6 Task 1 (`## Finalise entry` section) only documents a one-line banner and a filesystem device check (added in Task 3's note: "Add this filesystem check to the `## Finalise entry` banner section (Task 1)"). The start-of-pass .tmp cleanup is mentioned in Task 8 as belonging in Task 1 (or "right after Task 2's collision pre-flight"), but it's not in Task 1's documented content, and Task 2 doesn't mention it either. An implementer working task-by-task will write Task 1 without the start cleanup, write Task 2 without it, then reach Task 8 and need to go back. There is no task that owns the start cleanup's actual addition to the skill text.
- **Fix:** Add explicit implementation instructions for the start-of-pass cleanup to Task 1 or Task 2 (where it logically belongs). Currently Task 8 documents the section content but instructs the implementer to put the start cleanup elsewhere without that "elsewhere" having its own task.

**Important-3: Phase 6 `## MEMORY.md replacement` uses `mv` of the dated-dir MEMORY.md as source, destroying it before the dated dir is removed**

- **Location:** Phase 6 Task 6, Algorithm, final lines: `mv "$DATED_MEMORY" "$LIVE_MEMORY.tmp"` then `mv "$LIVE_MEMORY.tmp" "$LIVE_MEMORY"`. This moves `$DATED_MEMORY` out of the dated dir entirely (first `mv` removes it from `$DATED_DIR`). Later, if the self-check (Task 7) aborts finalisation after this move, the dated dir is preserved but `$DATED_DIR/MEMORY.md` is gone — it now lives at `$LIVE_MEMORY`. On re-entry with `/dream`, Phase 5 resume detection works from decisions.log (fine), but the dated-dir MEMORY.md is absent, and Phase 4's conservative regeneration won't re-run (the judgement phase is marked complete). The abort message says "dated dir preserved at $DATED_DIR" but the proposed MEMORY.md is no longer in it.
- **Fix:** Copy `$DATED_MEMORY` to `$LIVE_MEMORY.tmp` (not move), then `mv $LIVE_MEMORY.tmp $LIVE_MEMORY`. The dated-dir MEMORY.md remains intact for re-entry. Alternatively, accept the current move and document that MEMORY.md is intentionally not in the dated dir after Task 6 — but this contradicts the "dated dir preserved" abort message.

---

### Minor (count: 4)

**Minor-1: Phase 5 Task 9 walk-end detection — `SKIPPED_ENTRIES` membership test uses shell glob pattern matching that is fragile for names containing spaces**

- **Location:** Phase 5 Task 9, the `case " ${SKIPPED_ENTRIES[*]} " in *" ${bn%.md} "*)` pattern. Memory file names contain underscores and hyphens but not spaces; this particular shell glob pattern is safe for the current memory naming convention. However, the field spec for the decisions.log identifier explicitly says instructions can contain spaces. If a memory name ever contains a space (unlikely but not forbidden by the design), the pattern breaks. The risk is currently low.
- **Fix:** Replace the `case` glob with a function using `=` comparison in a loop, or ensure that the "memory names never contain spaces" constraint is documented explicitly as a precondition in the relevant skill section.

**Minor-2: Phase 6 Task 6 `## MEMORY.md replacement` awk script has a bug for the last section in the file**

- **Location:** Phase 6 Task 6, the awk insertion script. The awk logic sets `in_section=1` on the section heading and `inserted=0`. When the matching section is the LAST section in the file (no subsequent `^## ` heading follows it), the `END { if (in_section && !inserted) print line }` clause fires — which is correct for appending after the final bullet under the last section. However if the last section has no bullets at all (empty section), the line is appended immediately before `END`, which puts it after the section heading's line — correct. But if there are bullets, the `END` fires after the last bullet, also correct. This appears to work, but the awk pattern does not handle the case where the "last section" detection might also match the searched section again on subsequent iterations (the `$0 == sec` check would re-fire if the section heading appears twice — unusual but possible in a hand-curated MEMORY.md that has duplicate headings). Low risk; note for implementer.
- **Fix:** Document the assumption "section headings in MEMORY.md are unique" in the skill text, or add a `first-match-only` guard to the awk script.

**Minor-3: Phase 7 UAT checklist A.5 (DoD #5) relies on a simulation shortcut**

- **Location:** Phase 7 Task 2, section A.5: "For UAT, you can simulate by invoking the same command interactively while noting the timing." DoD #5 is specifically "Cron-driven `/dream` via the existing `schedule` skill produces the same dated artefact as manual invocation." The UAT checklist offers simulation as an acceptable substitute. This means the UAT can pass without ever having exercised the actual scheduler path, which is the behaviour the AC is designed to verify.
- **Fix:** Either require at least one real scheduler invocation (using `/schedule` or the crontab wrapper documented in cron-integration.md), or explicitly acknowledge in the checklist that A.5 is a "best-effort" gate with documented rationale for why simulation is acceptable (e.g., `/schedule` syntax evolves; the important thing is the `--autonomous` flag contract, which A.3/A.4 test directly).

**Minor-4: Phase 5 Task 5 `## Per-flagged-region turn` — on `edit` iterations, no decisions.log line is written for intermediate edits**

- **Location:** Phase 5 Task 5, "On `edit <instructions>`": "Each `edit` iteration is one decisions.log line — the last line per identifier wins (per AC5.11)." But Task 6's `log_decision` helper and the persistence-order in Task 7 (mirror → ## User edits → decisions.log) specify writing the log line as part of the three-write sequence. For flagged-region edit iterations where the user has not yet accepted (they're still editing), writing a decisions.log line per intermediate edit iteration creates lines with `action: "edit"` that look like finalised decisions. The resume detection in Task 8 treats any line as a "decided" entry, so a mid-iterate `edit` line would cause resume to skip that flagged region on re-entry, leaving it in an `edit` state with no `accept` or `dismiss` line — the finalisation would then have an ambiguous state for that region.
- **Fix:** Either (a) write decisions.log lines only on `accept` or `dismiss` for flagged regions (not on intermediate `edit` iterations), or (b) update resume detection to recognise `action: "edit"` on a flagged region as "not yet decided — re-present for accept/dismiss", or (c) document the intended behaviour explicitly in Task 8 resume detection.

---

## Consolidation Opportunities (within the plan)

- The "cascade fix" note (`frontmatter.metadata.lastAudited` → `frontmatter.lastAudited`) is repeated in the Phase 2 header, Phase 3 header, Phase 3 Task 1 skill text, and Phase 5 Task 5 note. The repetition is appropriate in individual phase docs for implementer clarity but could be consolidated into a single design-errata document cross-referenced from phases that apply the correction.
- The pipeline-status stub sections (one per phase, replaced by the next phase) are a useful scaffolding pattern. The plan consistently applies this pattern; no consolidation needed.

---

## Decision: APPROVED — CHANGES RECOMMENDED BEFORE EXECUTION

The plan provides comprehensive coverage of all 10 DoD criteria, all AC1.*–AC10.* acceptance criteria, and all 14 DRs. All five user-approved deviations from the design are explicitly flagged with rationale. The four-deviation flags (lastAudited flat, subagent_type, AC1→AC2 typo, persistence order, schedule skill built-in) are clear, consistent, and correctly applied across all phases they touch.

The three Important issues are subtle but consequential for correct behaviour: the `identifier` extension inconsistency will silently break walk resume for skipped memories; the start-cleanup task ownership gap will likely cause an implementer to miss the start-cleanup placement; the MEMORY.md `mv`-vs-`cp` issue leaves the dated dir in an inconsistent state on self-check abort. These should be addressed in the plan text before implementation begins, but they do not block the overall design soundness.

---

# Re-review — plan-validation (cycle 2)

**Prior findings file:** `code-review-findings-plan-validation.md` (cycle 1)

**Fixes applied:** Important-1, Important-2, Important-3 (renamed Important-4 from Minor-4), Minor-1 (cascaded from Important-1), Minor-2, Minor-3.

---

## Prior Findings Verification

### Important-1: decisions.log identifier inconsistency for skipped stream

**Status: Resolved.**

Phase 3 Task 6 now writes SKIPPED.md with strict `- <basefile>` lines where `<basefile>` includes the `.md` extension (e.g., `feedback_review-all-levels.md`). The comment in the code block explicitly states the format is strict and annotation-free. Phase 5 Task 3 documents the identifier convention matching the memory stream (basefile WITH `.md`), with an explicit note. Phase 5 Task 6 field table still says "memory's filename including `.md` extension" for both memory and skipped streams. Phase 5 Task 8 resume detection no longer appends `.md` to skipped identifiers — the is_decided call for the skipped stream uses the basefile directly as parsed from SKIPPED.md. Phase 5 Task 9 walk-end detection strips `- ` prefix and rtrim to get the basefile, then calls `is_decided skipped "$n"` with no extension manipulation. The full round-trip is consistent.

### Important-2: start-of-pass .tmp orphan cleanup ownership gap

**Status: Resolved.**

Phase 6 Task 1 (`## Finalise entry`) now explicitly owns both the filesystem same-device check AND the start-of-pass `.tmp` orphan cleanup. The skill text body for Task 1 includes the full `find ... -name '*.md.tmp' -delete` code with the comment "Owned by THIS task (Task 1) so the implementer doesn't miss it." Phase 6 Task 8 is renamed to "end-of-pass sanity" and its implementation note explicitly states "start-of-pass cleanup is owned by Task 1's `## Finalise entry` section." The Phase 6 header entry banner in Task 1 also references the updated operation sequence. An implementer working task-by-task will encounter the start cleanup at Task 1 and the end sanity at Task 8 — no ambiguity.

### Important-3: MEMORY.md mv destroys dated-dir source before self-check

**Status: Resolved.**

The fix is two-part and both parts are in place. Phase 6 Task 6 now uses `cp "$DATED_MEMORY" "$LIVE_MEMORY.tmp"` followed by `mv "$LIVE_MEMORY.tmp" "$LIVE_MEMORY"` — the comment explicitly calls out the Important-3 fix and explains why `cp` is used instead of the original `mv`. Phase 6 Task 7 has been restructured into a two-phase self-check: `## Pre-flight self-check` runs before any mirror transfer (on dated-dir proposed state), and `## Post-write self-check sanity` runs after MEMORY.md replacement (on live memory/). The pre-flight is the abort-cleanly checkpoint; the post-write sanity preserves the AC8.1 literal wording and catches edge cases. Task 1's entry banner is updated to reflect the new operation sequence.

### Important-4 (was Minor-4): flagged-region multi-edit resume

**Status: Resolved.**

Phase 5 Task 8 resume detection now has an explicit `is_terminal` jq predicate that distinguishes terminal from non-terminal actions per stream. The terminal-action table documents: for the flagged stream, only `accept` and `dismiss` are terminal — `edit` is not. The DECIDED_JSON jq program filters using `is_terminal($d)` before updating the map. The last paragraph of Task 8 includes a worked example for the "flagged-stream mid-edit resume" case, confirming the behaviour.

### Minor-1: glob fragility in SKIPPED membership test

**Status: Resolved (cascaded from Important-1 fix).**

Phase 5 Task 9 walk-end detection no longer uses the `case " ${SKIPPED_ENTRIES[*]} " in *...*` pattern. It uses an explicit for-loop with `[ "$bn" = "$s" ]` equality test. Since both `bn` and all entries in `SKIPPED_ENTRIES` carry the `.md` extension (consistent with the Important-1 fix), the comparison is a clean string equality with no glob fragility.

### Minor-2: MEMORY.md section-heading uniqueness assumption

**Status: Resolved.**

Phase 6 Task 6 now documents the uniqueness assumption explicitly: "The awk insertion above assumes section headings are unique in MEMORY.md. The awk uses `$0 == sec` as a heading match... if a heading appears twice, the awk inserts the link line after the FIRST occurrence's bullets only, leaving the second occurrence empty. Live MEMORY.md hand-curated by the user is overwhelmingly likely to satisfy this... the post-regeneration sanity check... catches the case where the awk insertion silently failed to fire."

### Minor-3: UAT A.5 simulation shortcut

**Status: Resolved.**

Phase 7 Task 2 A.5 now requires a real scheduler invocation and explicitly explains why simulation is not accepted. The action block lists three accepted paths (the `/schedule` built-in, a crontab one-shot, or any production scheduler). The rationale paragraph explains that simulation only exercises `/dream --autonomous` itself, not the scheduler→`/dream` interface, and cites the specific failure modes that only manifest under a real scheduler launch.

---

## New Diff Review (cycle 2)

No new diff to examine — the fixes are in-plan documents only. The following is a review of the fixes themselves for internal consistency and cascade correctness.

### Verification

No code to lint or test.

### Fix Consistency Check

**Important-1 cascade — identifier convention across all touch points:**

- Phase 3 Task 6: writes `- <basefile>` with `.md`. ✓
- Phase 5 Task 3: identifier in decisions.log is `<basefile>` with `.md`; example JSON shows `"identifier": "feedback_review-all-levels.md"` (implicit from "basefile WITH .md" convention). ✓
- Phase 5 Task 6 field table: "memory's filename including `.md` extension" for both memory and skipped streams. ✓
- Phase 5 Task 8 resume detection: skipped stream check uses `is_decided skipped "$basefile"` where `$basefile` comes from SKIPPED.md with `.md` intact. ✓
- Phase 5 Task 9 walk-end: `SKIPPED_ENTRIES` populated by stripping `- ` prefix only; entries retain `.md`; `is_decided skipped "$n"` calls are consistent. ✓

**Important-3 cascade — pre-flight check file-list construction:**

The pre-flight grep in Task 7's `SELFCHECK_FILES` loop iterates `"$DATED_DIR"/*.md` and excludes `.audit.md` and PRUNE-marked mirrors. This correctly excludes `MEMORY.md` from the mirror loop (since the inner `case` only continues on `.audit.md` — it does NOT skip MEMORY.md there) but then explicitly adds it separately: `MEMORY.md) SELFCHECK_FILES+=("$f"); continue ;;`. This means MEMORY.md IS included in the pre-flight grep. That is the stated intent. However, the loop iterates `$DATED_DIR/*.md` which would match `MEMORY.md` — but the `case` block handles it with `SELFCHECK_FILES+=("$f"); continue` so it's added and then skipped from the rest of the mirror-filtering logic. The logic is correct.

**Important-2 cascade — entry banner updated to include orphan cleanup:**

Phase 6 Task 1 entry banner now reads: "Operations: same-device check → collision check → orphan cleanup → pre-flight self-check → mirror transfer → prunes → promotes → MEMORY.md → post-write sanity → .tmp sanity → .last-dream → dated-dir cleanup." This correctly sequences the start-of-pass orphan cleanup BEFORE the pre-flight self-check. Internally consistent with where the cleanup code appears in Task 1. ✓

**Important-4 cascade — decisions.log edit lines still written for flagged stream:**

Phase 5 Task 5 still says "Each `edit` iteration is one decisions.log line — the last line per identifier wins (per AC5.11)." This means edit lines ARE written to decisions.log for flagged regions. Task 8 resume detection treats them as non-terminal (correct, per the `is_terminal` predicate that excludes `edit` from the flagged stream's terminal set). The Task 8 worked example confirms: "The decisions.log now has one line for `region-NNN` with `action: 'edit'` — non-terminal. On resume, `is_decided flagged region-NNN` returns 1 (no terminal entry) → walk re-presents." This is internally consistent, but note the subtle semantics: these edit lines in decisions.log serve as audit trail but don't satisfy the decided-set requirement — an implementer must understand that `is_decided` uses the terminal predicate, not mere presence in the log. This is documented adequately. ✓

---

## Issues (cycle 2)

### Minor (count: 1)

**Minor-5: UAT B.3 references "Phase 6 Task 8" for start-of-pass orphan cleanup — stale cross-reference after Important-2 fix**

- **Location:** Phase 7 Task 2, section B.3, Verification step 3: "The start-of-pass orphan cleanup (Phase 6 Task 8) should have removed the orphans." The Important-2 fix moved the start-of-pass cleanup to Task 1 (Finalise entry). Task 8 now owns only the end-of-pass sanity. This cross-reference is stale and will confuse a tester looking at Phase 6 Task 8 expecting to find the cleanup — it's in Task 1 instead.
- **Fix:** Change "Phase 6 Task 8" to "Phase 6 Task 1" in B.3 Verification step 3.

---

## Decision: APPROVED FOR MERGE

All six prior findings (Important-1, Important-2, Important-3, Important-4/Minor-4, Minor-1, Minor-2, Minor-3) are resolved. The fixes are internally consistent and the cascades are correct. The single new issue (Minor-5) is a stale cross-reference in the UAT checklist — a one-word fix that does not affect plan executability. The plan is ready for implementation.
