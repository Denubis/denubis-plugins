# Critical Peer Review: denubis-dream implementation plan

Reviewer: Opus 4.7 (1M context)
Date: 2026-05-17
Documents reviewed:
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/docs/implementation-plans/2026-05-16-denubis-dream/phase_01.md` through `phase_07.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/docs/implementation-plans/2026-05-16-denubis-dream/test-requirements.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/docs/implementation-plans/2026-05-16-denubis-dream/uat-requirements.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/docs/implementation-plans/2026-05-16-denubis-dream/code-review-findings-plan-validation.md`
- `/home/brian/people/Brian/brian-ed3d-plugins/.worktrees/denubis-dream/docs/design-plans/2026-05-16-denubis-dream.md`

Cross-checked against:
- Actual transcripts under `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/*.jsonl`
- Actual memory files under `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/`
- `denubis-bibliography` and `denubis-basic-agents` plugin shapes
- Existing `subagent_type` precedents under `plugins/*/skills/*/SKILL.md`
- `claude --help` flag surface
- Filesystem same-device assumption under `~/.claude/projects/`

---

## Hidden Assumptions

Load-bearing assumptions extracted from the plan, with evidence status. Bold = assumption that, if false, breaks downstream claims.

1. **The Phase 3 jq filter `(.message.content[0].text // .text // "")` captures the substantive content of the transcript corpus.** *Load-bearing.* If false, every per-memory subagent and the corpus-wide scanner see a tiny fraction of actual session content, and every AC3.* "evidence" claim degrades.
   **Evidence:** FALSIFIED on inspection of a real transcript file (see High-1).

2. **`subagent_type: denubis-basic-agents:sonnet-general-purpose` is a valid and repo-standard dispatch surface.** *Load-bearing for AC3.1.*
   **Evidence:** VERIFIED. The agent file exists at `plugins/denubis-basic-agents/agents/sonnet-general-purpose.md` with frontmatter `name: sonnet-general-purpose`, `model: sonnet`. The `denubis-basic-agents:<name>` qualified form has 20+ precedents across `denubis-plan-and-execute`, `denubis-extending-claude`, etc. Deviation #4 is safe.

3. **`memory/` and `memory.dream-*` are on the same filesystem (atomic `mv` invariant for AC7.2).** *Load-bearing for AC7.2.*
   **Evidence:** VERIFIED — both at dev `64512` on this machine. Phase 6 Task 1's same-device check (which actually verifies this at runtime) makes the assumption explicit and aborts on violation. Safe.

4. **Existing memory frontmatter convention is "flat lastAudited", not nested `metadata.lastAudited`.** *Load-bearing for the deviation #1 framing.*
   **Evidence:** PARTIALLY FALSIFIED — see Medium-3. NO memory file has *any* `lastAudited` field (flat or nested). The plan frames flat as "the existing convention". The actual existing convention is *absence*. First dream invents the field; the choice of shape is forward-looking, not codified by precedent. The deviation is still safe but the framing of "matches observable repo state" overclaims.

5. **`/dream` slash command can be invoked by `claude -p` / a cron wrapper.** *Load-bearing for AC9.1 and Phase 7's cron-integration.md wrapper example.*
   **Evidence:** PARTIALLY FALSIFIED — see High-3. The wrapper uses `claude --prompt`, which is not a flag in the installed `claude` binary. The flag is `-p` / `--print` and `prompt` is a positional.

6. **In-progress flagged-region scaffold revisions persist to disk so they survive mid-walk abandonment.** *Load-bearing for the Important-4 fix narrative in Phase 5 Task 8.*
   **Evidence:** FALSIFIED — see High-2. Mid-walk persistence (Task 7) only writes `promoted/<slug>.md` on `accept`. There is no persistence layer for intermediate `edit` revisions. The "lives in dated-dir state" claim in Task 8 has nothing backing it.

7. **`/schedule` is a Claude Code built-in.** *Load-bearing for Phase 7 cron-integration.md framing.*
   **Evidence:** Cited as a codebase-investigator finding. Cannot independently verify from the artefact list (not enumerable as a plugin file). Assumption inherited from the plan; not falsified. Acceptable at audit time.

8. **Phase 5 retry workflow can re-run Phase 3 + Phase 4 for a single memory.** *Load-bearing for AC3.6 recovery.*
   **Evidence:** PARTIALLY FALSIFIED — see Medium-1. Phase 3's per-memory dispatch section iterates `memory/*.md` and dispatches in parallel. Phase 4's judgement orchestration walks `<dated_dir>/*.audit.md`. Neither has a single-memory entry point. The "for this memory only" instruction is glue not specified.

9. **Phase 5 walks the disposition vocab the design DR3 specifies (`keep`/`prune`/`edit`).** *Load-bearing for DR3 consistency.*
   **Evidence:** FALSIFIED — see Medium-2. Phase 5 Task 4 introduces a 4th verb `reject` not in the design AC5.4-5.6, not in DR3, not flagged as a deviation.

---

## ACH Matrix

The audit found three competing diagnoses for "is this plan ready to execute". Rows are hypotheses; columns are pieces of evidence. `+` = consistent, `−` = inconsistent, `?` = not diagnostic.

| Evidence | H1: Plan is ready to execute as-is | H2: Plan is ready with marginal touch-ups | H3: Plan has at least one execution-blocking defect |
|----------|-----|-----|-----|
| Cycle-2 review verdict "APPROVED FOR MERGE" | + | + | + (does not contradict — reviewer scope was structural only) |
| Phase 3 jq filter drops 64% of timestamped message-bearing lines in real corpus | − | − | + |
| No SubAgent or Task tool needs validation of new shape | + | + | ? |
| Phase 5 introduces undocumented `reject` verb deviating from DR3 | − | + (small fix) | + (compounds with deviation tracking) |
| In-progress flagged-scaffold edits have no persistence path despite Task 8 claim | − | − | + |
| `claude --prompt` flag is fictional in cron-integration.md | − | + (one-word fix in doc) | + |
| Retry workflow doesn't compose with Phase 3/4 sections as written | − | + (add a sub-task) | + |
| Subagent_type precedent is verified | + | + | ? |
| Memory frontmatter convention claim slightly misframed | ? | + | ? |
| MEMORY.md `grep -qF` substring-matches longer headings | − | + | + (low impact) |
| Existing precedents (bibliography plugin shape, marketplace JSON, gitignore baseline) all verified | + | + | + (does not refute) |

**Decision rule:** The hypothesis surviving fewest strong contradictions. H1 has multiple decisive `−` marks (Phase 3 filter, persistence gap, retry composition, `claude --prompt`). H2 absorbs the document-level fixes but cannot absorb the Phase 3 filter — that is a behavioural defect, not a documentation defect. **H3 is best-supported.** The plan has at least one execution-blocking defect (the Phase 3 filter), several execution-degrading defects (persistence gap, retry composition, `claude --prompt`), and several minor inconsistencies.

Note: H3 does NOT mean the design is wrong. The design is sound. H3 means the implementation plan as written will produce a /dream that silently under-reads transcripts and several user-visible recovery paths that don't work as advertised.

---

## Findings

### High (count: 3)

**High-1: Phase 3 jq filter silently drops ~64% of timestamped message-bearing transcript lines, gutting AC3.2, AC3.4, AC3.5, AC3.8 in practice**

**Issue:** Phase 3 Task 1's pre-windowing filter is:
```jq
select(.timestamp != null) |
{ts, uuid, role, text: (.message.content[0].text // .text // "")} |
select(.text != "")
```
Applied to a real transcript file in the audited project (`~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d28fd3f2-dc3e-41fd-9e62-75bf79264cce.jsonl`, 960 lines), this filter survives **48 lines**. Direct profile of `.message.content[]` per timestamped line found:
- 503 timestamped lines whose `.message.content[0]` is NOT a text block (it's `tool_use`, `tool_result`, `thinking`, etc.)
- 234 timestamped lines with no `.message` at all (`attachment`, `permission-mode`, `ai-title`, `last-prompt`, `queue-operation`, `file-history-snapshot`, `system`)
- 48 timestamped lines that have `.message.content[0].text` populated

So the per-memory evidence subagent (AC3.2/AC3.4) and the corpus-wide flagged-region scanner (AC3.5/AC3.8) read **5% of the file** when the design intends them to "read the windowed corpus". Every other text-bearing structure — assistant tool calls (where most decisions happen), tool results (where evidence lives), assistant thinking blocks, multi-block assistant messages where text is at `content[1]` after a `tool_use` — is silently dropped.

**Evidence:** Reproduced directly (jq output, python profile, exit-code from `select`).

**GRADE factors:** *Risk of bias* — Phase 3's `## Codebase verified` claim says "JSONL transcript lines are NOT chronologically ordered, so windowing must filter; text-bearing fields vary per message type" but the actual filter shape `.message.content[0].text // .text // ""` does NOT actually handle the varying text-bearing-field-per-message-type case. The verification noted the variance but didn't translate it into the filter. *Indirectness* — the verification's evidence was the schema observation; the filter built from it was assumed-equivalent without per-line testing.

**Ripple:**
- AC3.2 "populated `## Evidence` section with `ev-NNN:` entries citing transcript short-UUIDs and line ranges" — the strongest evidence is in tool calls and tool results, all of which are excluded. Each `.audit.md`'s evidence section will reach into the 5% surviving text and miss the work.
- AC3.4/AC3.8 "windows transcripts since lastAudited" — windowing works fine; the filter happens to drop content the user expects to be in the window.
- AC3.5 "memory-worthy regions" — the corpus-wide subagent will surface ~zero useful flagged regions because the regions live in tool-use+tool-result conversation that doesn't survive the filter.
- Phase 4 judgement gates *holds*, *correct*, *useful*, *supported* all rely on `## Evidence` — every disposition decision will be made on a degraded evidence base.
- UAT B.5 ("Corpus coverage check") will report a `## Coverage` header citing `wc -l _corpus.jsonl` line count that is wildly under the corpus's real size. The user will likely conclude "the window is bounded correctly but somehow my actual work isn't showing up" — opaque failure.
- The `code-artefact flags` section is unaffected (it greps live code, not transcripts) — that AC keeps working.

**Corrected language / fix:** Replace the filter with one that extracts text from every text-bearing path the transcript format uses. Concrete shape:
```jq
select(.timestamp != null) |
. as $root |
{
  ts: .timestamp,
  uuid: .uuid,
  role: (.type // .role // "unknown"),
  text: (
    if (.message.content | type) == "string" then .message.content
    elif (.message.content | type) == "array" then
      [.message.content[]
        | (if .type == "text" then .text
           elif .type == "thinking" then .thinking
           elif .type == "tool_use" then ("[tool_use " + (.name // "?") + "] " + ((.input // {}) | tostring))
           elif .type == "tool_result" then ((.content // "") | if type == "string" then . else tostring end)
           else "" end)]
      | map(select(. != "")) | join("\n")
    else (.text // "") end
  )
} | select(.text != "")
```
Then re-run Phase 3 verification (Task 1) against a real transcript file and confirm survivor count is closer to message-bearing-line count than to 5%.

This requires a phase_03 revision (Task 1 jq block) and a corresponding fix to the `## Coverage` accounting in Task 5's prompt (the line count should now be much larger; the prompt's "Aim for 0-10 flagged regions" guidance may need to be re-tuned).

**Location:** `phase_03.md` lines 60-89 (Task 1, the `window_jsonl()` jq filter); cascades to Task 4's flagged-region scanner verification.

---

**High-2: Phase 5 in-progress flagged-region scaffold revisions have no persistence path, contradicting Task 8's resume claim**

**Issue:** Phase 5 Task 8's `## Resume detection` ends with a worked example for "Flagged-stream mid-edit resume":

> "The decisions.log now has one line for `region-NNN` with `action: 'edit'` — non-terminal. On resume, `is_decided flagged region-NNN` returns 1 (no terminal entry) → walk re-presents `region-NNN` with the **LATEST revised scaffold (which lives in dated-dir state from mid-walk persistence**, not redrawn from the original flagged file)."

But Task 5's `## Per-flagged-region turn` says of `edit`:
> "Revise the scaffold per the user's instructions… Re-present the revised scaffold with the same prompt (`accept / edit / dismiss`)."

It does NOT specify writing the revised scaffold to disk. And Task 7's `## Mid-walk persistence` Step 1 says:
> "**Mirror update** (or `promoted/<slug>.md` write for flagged-stream accepts). This is the substantive change…"

Explicitly only on `accepts`. No persistence layer for the `edit`-but-not-yet-accepted state.

Net: a user types `edit add X`, sees Opus's revised scaffold, then quits. Decisions.log has one `edit` line with `instruction: "add X"`. On resume, Task 5 reads the flagged file (original excerpt) and drafts the scaffold from that — there is no "latest revised scaffold" anywhere on disk. The Task 8 narrative is fiction.

The user-visible failure mode is subtle: the resume *does* re-present the flagged region (Task 8's terminal-action filter is correct on that point), but it re-presents the *original* scaffold, not the user's edits. The user re-types `edit add X` and gets the same result. Eventually they hit `accept`, but the iteration count just doubled.

**Evidence:** Direct read of phase_05.md Task 5 (no write-to-disk on `edit`), Task 7 (no persistence path for non-accept), Task 8 (asserts a "dated-dir state" that doesn't exist).

**GRADE factors:** *Inconsistency* — Task 8's narrative conflicts with Task 5 and Task 7. Cycle-2 reviewer caught the terminal-action filter (good) but didn't trace through the persistence implication.

**Ripple:**
- AC5.7 (resume from first not-yet-decided) — still technically met (Task 8's filter correctly returns "not decided"), but the resume semantics are degraded.
- AC6.4 (user can re-accept the revision) — technically met for in-session iteration; broken for cross-session iteration.
- The decisions.log audit trail is "complete" but unactionable for replay — the *latest instruction* is in the last `edit` line, but the *cumulative scaffold state* (Opus's revisions across iterations) is lost.

**Corrected language / fix:** Either (a) extend Task 7 mid-walk persistence to write `<dated_dir>/flagged/region-NNN.scaffold.md` on every edit iteration, and have Task 5 read it on resume if present; or (b) on resume, Task 5 replays all `edit` instructions from decisions.log against the original flagged excerpt to reconstruct the latest scaffold state; or (c) accept the degraded semantics and remove the misleading "lives in dated-dir state" claim from Task 8's worked example, replacing it with a frank "scaffold redrawn from the original flagged file; the user may need to re-issue the edit instruction".

Option (a) is closest to the user's apparent intent; option (c) is the cheapest doc-only fix; option (b) is fragile (multiple edit instructions interact non-commutatively).

**Location:** `phase_05.md` lines 528-529 (the worked example in Task 8), `phase_05.md` lines 338-342 (Task 5 `edit` handling that needed the persistence call), `phase_05.md` lines 447-450 (Task 7 mid-walk persistence that needed the third write path).

---

**High-3: `claude --prompt` in the cron-integration.md wrapper is not a valid flag; cron jobs following the doc will fail at the CLI parse step**

**Issue:** Phase 7 Task 1's `cron-integration.md` body (the "Alternative: system-level scheduling" section) provides this wrapper:

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$HOME/path/to/myproject"
cd "$PROJECT_ROOT"
claude --prompt "/dream --autonomous"
```

`claude --help` on this machine confirms `--prompt` is not a flag. The flag is `-p` / `--print`; `prompt` is a positional argument:

```
Usage: claude [options] [command] [prompt]
  prompt                              Your prompt
  -p, --print                         Print response and exit (useful for pipes). ...
```

A user following the documented wrapper gets a flag-parse error on every cron run. The scheduler reports non-zero exit; the user reads the troubleshooting table which says "Hard error — likely filesystem … missing tool … or malformed transcripts" — completely off the trail.

**Evidence:** Direct `claude --help` output (Bash command run during audit).

**GRADE factors:** *Indirectness* — the doc was written without verifying the CLI surface against the installed binary. UAT A.5 requires "a real scheduler launch", so the failure would surface at A.5; but the test sign-off boilerplate assumes A.5 passes, and the doc itself misleads any first-time user trying the wrapper.

**Ripple:**
- UAT A.5 will fail if the user follows the documented wrapper exactly. The user blames the plugin; the bug is in the doc.
- The cron-integration troubleshooting table is misleading (no entry covers "wrong CLI flag in this doc").
- Once fixed, the doc should also clarify that `-p` / `--print` requires the prompt to be a positional, and `/dream --autonomous` as a single argument is what gets sent. Worth confirming that the slash-command form survives the non-interactive `-p` path (an `--bare`-mode-style restriction could apply — but that's a separate verification).

**Corrected language / fix:** Replace `claude --prompt "/dream --autonomous"` with `claude -p "/dream --autonomous"` and add a note: "Verify your installed `claude` binary supports the `-p` flag with a slash-command prompt by running `claude -p '/help'` once before relying on cron." Also add a troubleshooting row for "CLI flag changed across Claude Code versions".

**Location:** `phase_07.md` line 100 (the wrapper script in cron-integration.md body).

---

### Medium (count: 5)

**Medium-1: Phase 5 retry workflow asserts re-running "Phase 3 for this memory only" and "Phase 4 for this memory only" without specifying the entry points**

- **Issue:** Phase 5 Task 3's `retry` branch says "Re-run Phase 3's per-memory dispatch for this single memory: re-run `## Pre-windowing transcripts` for this memory (cheap), then dispatch one Sonnet subagent." But Phase 3 Task 1's `## Pre-windowing transcripts` is a single Bash block that iterates ALL `memory/*.md` files (the `for memfile in "$MAIN_DIR"/memory/*.md; do` loop). The "this memory only" entry point doesn't exist in Phase 3 as written. Likewise Phase 4's `## Judgement orchestration` walks `<dated_dir>/*.audit.md` skipping ones with `## Disposition` — not a single-memory entry point.
- **Evidence:** Direct read of phase_03 Task 1 and phase_04 Task 4.
- **GRADE factors:** Implementation glue assumed; not specified. *Indirectness*: the "for this memory only" instruction is composed from sections written for batched operation. Implementer must parameterise both Phase 3's pre-windowing loop and Phase 4's judgement loop — neither phase factors that sub-procedure.
- **Ripple:** UAT B.4 / DR5-7 ("the `retry` verb doesn't actually re-dispatch the subagent") is exactly the failure path. AC3.6 recovery is degraded.
- **Corrected language / fix:** Add a `## Single-memory entry points` subsection (or two — one in Phase 3, one in Phase 4) explicitly factoring "windowing for one memory" and "judging one audit file" as named sub-procedures the retry workflow calls. Alternatively, accept that retry re-runs Phase 3 + Phase 4 for ALL memories (skipping already-judged ones via the existing resume logic) and document that — the cost is the per-memory subagent loop's parallelism (but it's already O(N) parallel dispatch; running it again is acceptable).
- **Location:** `phase_05.md` lines 183-186 (`retry` branch), `phase_03.md` lines 100-118 (pre-windowing per-memory loop), `phase_04.md` lines 207-218 (judgement orchestration loop).

**Medium-2: Phase 5 introduces an undocumented 4th verb `reject` for the memory stream, deviating from design DR3 and AC5.4-5.6 without being flagged as a deviation**

- **Issue:** Design AC5.4-5.6 specify verbs `accept` / `prune` / `edit <instructions>` for existing-memory turns. DR3 explicitly says "existing memories get `keep` / `prune` / `edit`". Phase 5 Task 4 prompts users with: "`accept` / `reject` / `edit <instructions>` / `prune`" — 4 verbs. The action-outcome table (Task 4) defines `reject` as "(no-op; same as accept)" when recommendation was `keep`, "mirror = byte-for-byte copy of live (revert Opus's edit)" when recommendation was `edit`, "mirror = byte-for-byte copy of live (don't prune)" when recommendation was `prune`. The Phase 5 header lists the "user-approved deviations" as ONE deviation (the persistence order). `reject` is a second deviation, not flagged.
- **Evidence:** Direct comparison of design AC5/DR3 vs phase_05.md Task 4.
- **GRADE factors:** *Reporting bias* — the cycle-2 review trumpeted "five user-approved deviations" but did not catch this sixth one. *Indirectness* — the new verb is functionally a synonym for the "revert" use case of `accept` against a non-`keep` recommendation, but a user who reads only the design wouldn't expect it.
- **Ripple:** decisions.log `action` enum in Task 6 lists `reject` as a valid action — silently extending the schema. Walk-end summary in Task 9 ("X kept / Y edited / Z pruned / W promoted / V flagged dismissed") doesn't include a `reject` bucket — a rejected memory is counted as kept (since the mirror reverts to live), but the summary text doesn't make that clear to the user.
- **Corrected language / fix:** Either (a) remove `reject` (collapse its semantics: `reject` of a `keep` recommendation IS `accept`; `reject` of `edit`/`prune` recommendations can be expressed as `edit <restore original>` — but that's awkward); or (b) explicitly flag `reject` as user-approved deviation #6 in the Phase 5 header with rationale, update DR3 verb list in a separate design-patch commit, and add a `reject → counts as kept` note to the walk-end summary in Task 9.
- **Location:** `phase_05.md` lines 244-248 (action-outcome mapping table), `phase_05.md` lines 387-393 (decisions.log action enum).

**Medium-3: Plan claims "existing convention is flat lastAudited" but no memory file has any `lastAudited` field; framing as "matches observable repo state" overclaims**

- **Issue:** Phase 2 header, Phase 3 header, Phase 3 Task 1 prose, Phase 5 Task 5 note, Phase 6 Task 3 prose all reference "the convention established in Phase 3" (flat `lastAudited:`). The actual repo state (audited): 12 memory files under `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/memory/`, NONE of which have a `lastAudited` field in any form. The phrase "matches observable repo state" in the Phase 3 commit message and the framing throughout the plan are factually overclaimed: the *observable* state is *absence*, not flat.
- **Evidence:** Audited all 12 memory files via awk for both `^lastAudited:` (flat) and `^metadata:` (nested) — zero hits across the board.
- **GRADE factors:** *Imprecision* — single observation (codebase-investigator's claim) extrapolated to a pattern. *Indirectness* — the user's general CLAUDE.md convention does use a flat shape, so flat is plausibly the right choice; but it's the user's stated preference, not an existing precedent. Deviation #1's rationale is mis-described.
- **Ripple:** First dream finds all 12 memories with no `lastAudited` → all 12 per-memory subagents fall into the "full corpus if absent" branch. With High-1 unfixed, "full corpus" still drops 95% of content. With High-1 fixed, "full corpus" means an unbounded scan of the entire transcript history — which Phase 3 acknowledges is the case for first-dream (`COVERAGE_BOUND = <unbounded — first dream>`), but the cost may exceed the subagent's context window. The 12-memory × full-corpus dispatch may face cumulative cost concerns the plan doesn't address.
- **Corrected language / fix:** Reframe deviation #1 from "matches existing convention" to "adopts the flat shape per the user's global CLAUDE.md convention; existing memory files have no lastAudited field at all (the field is invented by this plugin at first finalisation)". Update the four locations where this is asserted.
- **Location:** `phase_02.md` line 15 (header), `phase_03.md` lines 11-15 (header), `phase_03.md` lines 137-139 (Task 1 prose), `phase_05.md` lines 42-43 (Task 5 note), `phase_06.md` line 11 (Codebase verified).

**Medium-4: MEMORY.md section-heading detection uses `grep -qF "$section"` (substring), which can match longer headings as false positives**

- **Issue:** Phase 6 Task 6 uses `if grep -qF "$section" "$DATED_MEMORY"; then`. If the user's MEMORY.md has a section like `## Feedback Patterns` and the promoted type maps to `## Feedback`, the grep succeeds on the substring match — then the awk hands off to the section-heading awk which uses `$0 == sec` (exact-line match) and finds NO matching line — so the awk loop completes with `in_section=0` throughout, the `END { if (in_section && !inserted) ... }` clause doesn't fire, and the line is silently NOT inserted. The post-regeneration sanity check (link-count comparison) catches the count mismatch and halts — so the failure is loud rather than silent — but the abort message ("MEMORY.md regeneration link-count mismatch") doesn't surface the actual cause (grep-vs-awk match disagreement). The implementer will spend time diagnosing.
- **Evidence:** Direct read of the awk + grep block at phase_06.md lines 399-417.
- **GRADE factors:** *Imprecision* — grep-F is plain string match anywhere; awk `$0 == sec` is exact line. Two different match semantics within one decision path.
- **Ripple:** A reasonable hand-curated MEMORY.md could have multiple `## ` headings sharing prefixes. The fall-back path (append `## Promoted` at end) is robust but the inconsistent match semantics will surprise.
- **Corrected language / fix:** Replace `grep -qF "$section"` with `awk -v sec="$section" 'BEGIN{found=0} $0==sec{found=1; exit} END{exit !found}' "$DATED_MEMORY"` (or `grep -Fxq "$section"` for exact-line match). Match semantics align across the if-then halves.
- **Location:** `phase_06.md` line 399.

**Medium-5: Test-requirements.md's "Gaps: None identified" claim is internally inconsistent with the "Soft gaps worth naming" enumeration**

- **Issue:** test-requirements.md line 82 says "**Gaps: None identified at the AC-row level — every AC1.1 through AC10.3 maps to at least one of `op`, `insp`, or `uat`.**" — but then lines 84-89 enumerate three "soft gaps worth naming" (AC3.1, AC5.10, AC7.2) where verification is *weaker than one might wish*. AC3.1 is explicitly called out: "a buggy implementation that wrote `.audit.md` files without actually dispatching subagents would pass this inspection." That IS a gap — the AC is not verifiable as-stated. Calling it a "soft gap" while simultaneously asserting "no gaps identified" is rhetorical sleight-of-hand.
- **Evidence:** Direct read of test-requirements.md lines 80-89.
- **GRADE factors:** *Reporting bias* — the document privileges the strong claim ("no gaps") in the headline and downgrades the contradictory finding ("soft gaps") in subsequent prose.
- **Ripple:** A reviewer scanning the headline rather than the body would conclude AC coverage is exhaustive. The cycle-2 reviewer apparently did exactly this (the cycle-2 review's "AC coverage matrix" section ticks every row without engaging the soft-gap enumeration).
- **Corrected language / fix:** Change the headline to: "**Gaps:** three soft gaps identified at the verification-mechanism level — see below. No row is unmapped; three rows have verification mechanisms that would not catch the design's intended failure modes."
- **Location:** `test-requirements.md` lines 80-89.

---

### Low (count: 3)

**Low-1: Phase 1 plugin.json omits homepage/repository fields present in most other denubis plugins**

- The denubis-bibliography precedent (cited as the shape source) omits them. But denubis-basic-agents, denubis-plan-and-execute, and most others include them. Either align with bibliography (current state) or align with the majority. Minor stylistic inconsistency.
- **Location:** `phase_01.md` lines 47-58.

**Low-2: `[denubis-dream] 0.1.0` CHANGELOG entry text says "Plugin manifest at `plugins/denubis-dream/.claude-plugin/plugin.json`" — the path is fine but the prose reads like a single feature list when the entry is initial scaffolding**

- The entry is correctly placed and well-formed; the New section listing only the scaffolding artefacts is appropriate for a 0.1.0 entry. Adjustment optional.
- **Location:** `phase_01.md` lines 179-189.

**Low-3: Phase 7 task 4 CHANGELOG entry for 0.2.0 is dense paragraph that buries the user-relevant change in technical detail**

- The 0.2.0 entry text starts with "Full pipeline release." (good) then runs an 8-line paragraph listing every internal section. A typical user reading the CHANGELOG cares about behaviour, not section names. Optional simplification: cut the section-name enumeration and let the `**New:**` list carry the detail.
- **Location:** `phase_07.md` lines 447-461.

---

## "No issue found" sections (audited and cleared)

These areas were audited per the focus list and found defensible after independent verification.

**Architectural soft spot — subagent_type usage (Deviation #4):**
- `subagent_type: denubis-basic-agents:sonnet-general-purpose` is a valid, well-precedented dispatch surface. 20+ uses across `denubis-plan-and-execute`, `denubis-extending-claude`, and `denubis-research-agents`. The agent file exists with `model: sonnet` frontmatter. No issue.

**Architectural soft spot — Phase 6 two-phase self-check (Deviation #3):**
- The pre-flight on dated-dir + post-write sanity on live is correctly structured: the pre-flight excludes `.audit.md` files (which contain UUIDs as evidence by design), excludes `<!-- PRUNE -->` mirrors, includes the regenerated MEMORY.md. Both sections cite their distinct purposes (abort-cleanly vs. AC8.1 literal-wording). The `cp` (not `mv`) for MEMORY.md replacement correctly preserves the dated-dir source on abort. No issue beyond Medium-4's grep/awk match-semantics inconsistency.

**Architectural soft spot — Phase 6 same-filesystem invariant (AC7.2):**
- Verified `stat -c '%d'` returns the same dev for `memory/` and the parent of `memory.dream-*` on the audited machine. Phase 6 Task 1's runtime check makes the invariant explicit and aborts cleanly if violated. No issue.

**Architectural soft spot — Important-1 cascade (identifier convention for skipped stream):**
- Phase 3 Task 6 writes `- <basefile>` with `.md`; Phase 5 Task 3 references identifier as `<basefile>` with `.md`; Phase 5 Task 6 field table specifies `.md` for memory/skipped streams; Phase 5 Task 8 resume calls `is_decided` with the basefile-as-parsed (no extension manipulation); Phase 5 Task 9 strips `- ` prefix only. End-to-end consistent. No issue.

**Architectural soft spot — Phase 5 walk-end mtime baseline check (AC5.8):**
- The mtime snapshot at walk entry compared at walk end is the right shape. The sort+tr concatenation is a serialisation form that's robust to file order. No issue.

**Architectural soft spot — Phase 6 Important-2 (`.tmp` orphan cleanup ownership):**
- Phase 6 Task 1 explicitly owns start-of-pass cleanup with the `find ... -delete` block; Phase 6 Task 8 explicitly owns end-of-pass sanity with a different `find` that errors on fresh orphans. Both are positioned correctly in the operation sequence (the Task 1 banner lists them in order). No issue.

**Falsification of Deviation #5 (cron-integration is scheduler-agnostic):**
- The framing is correct given that `/schedule` is asserted to be a Claude Code built-in not enumerable as a plugin file. The doc handles the `/schedule` path with a "run it interactively for current syntax" reference. Acceptable framing, modulo High-3 (the wrapper script's CLI flag).

**Verification: AC1-AC2 deltas already correctly tracked.**
- The cycle-2 reviewer caught the design typo where Phase 2 "Done when" cites AC1. Phase 2's correction notes this. No issue.

---

## Verification

Independent checks performed:

- Read all 7 phase docs end to end.
- Read design-plan, test-requirements.md, uat-requirements.md, and the two-cycle code-review document end to end.
- Verified the actual `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/` slug structure against Phase 3's "codebase-investigator found" claims. Match.
- Verified the actual `memory/` directory contains 12 entries (no MEMORY.md+12 memories; matches Phase 5's "memory set is 12 entries" claim).
- Verified that NO existing memory file has any form of `lastAudited` field (counters the "matches observable repo state" framing).
- Ran the actual Phase 3 jq filter against a real transcript file (`d28fd3f2-dc3e-41fd-9e62-75bf79264cce.jsonl`); profiled with python the distribution of message-bearing-line shapes to confirm the silent-dropout claim.
- Verified `denubis-basic-agents:sonnet-general-purpose` is a real qualified agent surface with 20+ existing precedents under `plugins/*/skills/*/SKILL.md`.
- Verified `stat -c '%d'` returns the same dev for `memory/` and the dated-dir parent (same-filesystem invariant for AC7.2).
- Verified `claude --help` output for the `--prompt` flag claim (falsifies High-3).
- Cross-referenced the Important-1 cascade fix across Phase 3 Task 6, Phase 5 Tasks 3/6/8/9 — consistent.
- Cross-referenced the Important-3 cascade fix (cp vs mv for MEMORY.md) in Phase 6 Task 6 and Task 7 — consistent.
- Cross-referenced the design's DR3 verb list against Phase 5 Task 4 — found Medium-2 deviation.
- Cross-referenced Phase 5 Task 5/Task 7/Task 8 for flagged-stream persistence — found High-2 narrative-vs-implementation gap.
- Cross-referenced Phase 5 Task 3 (retry) against Phase 3 Task 2 (orchestrator) and Phase 4 Task 4 (orchestrator) — found Medium-1 composition gap.

---

## Strongest Hypothesis

**Among the findings: High-1 (Phase 3 jq filter) is the most decisive defect.** The filter is provably dropping 95% of relevant transcript content; this is reproducible with a one-line jq invocation against a file in the user's actual transcript dir. Without this fix, every Phase 3, 4, and 5 AC that depends on `## Evidence` content has a behavioural floor far below what the design intends. The cost of the fix is small (a more comprehensive jq filter); the cost of executing without the fix is shipping a `/dream` plugin that quietly produces vacuous audits.

This finding has both borders demonstrated:
- *Positive border* (mechanism triggers failure): the filter applied to a real file emits 48 of 960 lines, and the dropped lines are exactly the tool_use/tool_result/thinking lines where assistant work happens.
- *Negative border* (removing the mechanism prevents the failure): a more comprehensive filter would extract text from all four content-block types and would emit roughly 10×–15× as much content.

GRADE: **High** (demonstrated, on the production-path-equivalent — the filter is run via `jq` from Bash in the skill, exactly as it will be run by the implemented `/dream`).

---

## Weakest Hypothesis

**Medium-3 (lastAudited convention framing) is the weakest finding** — the deviation itself is safe; only the *justification narrative* is overclaimed. It survives because the user has approved deviation #1 explicitly, and "user's stated preference" is a valid grounding even if "matches existing convention" isn't accurate. Fix is editorial: reframe the rationale. No execution risk.

GRADE: **Low** (cosmetic inaccuracy in the deviation narrative; no behavioural consequence).

---

## Pre-Mortem

Assume the plan as-written is executed and the resulting `/dream` plugin ships at 0.2.0. Three alternative failure scenarios consistent with the evidence:

**Scenario A — silent under-audit (most likely):** User runs `/dream` weekly via cron. The dated dir gets created. The flagged-region scanner reports "0 regions" most weeks because the 5% of transcript content it sees doesn't contain durable claims (tool-use/tool-result blocks are where the discussion happens). Existing-memory audits get an `## Evidence` section that says "(no transcript evidence in window since lastAudited)" — every week. The user concludes the plugin is broken or that their work doesn't produce memory-worthy moments. They abandon the workflow. Root cause: High-1.

**Scenario B — recovery-path frustration (second most likely):** A Phase 3 subagent fails on one memory. The user types `retry` in the walk. The retry workflow tries to dispatch a single-memory subagent but the skill text composing the dispatch is unclear (Medium-1). Either Opus dispatches in a way that re-windows all memories (wasted compute) or fails to dispatch at all (drops into the "fall back to keep/prune" path). The user's sense of "retry as a first-class recovery" is degraded. Root cause: Medium-1.

**Scenario C — cron wrapper never works (third most likely):** First-time user reads cron-integration.md, copies the wrapper script, schedules it, comes back next week. The cron log has 7 days of "unknown flag: --prompt" failures. The user opens the troubleshooting table; the table doesn't cover this. The user blames the plugin or assumes `/dream --autonomous` is broken. Root cause: High-3.

**What the analysis dismissed too quickly?** The code-review cycle-2 verdict "APPROVED FOR MERGE" set a frame where remaining issues were assumed minor. The cycle-2 reviewer's scope was internal-consistency of the cycle-1 fixes — they did NOT re-audit against the actual codebase. The verification I performed (running jq against a real transcript, running claude --help) is exactly the kind of external falsification cycle-2 did not do. The "two-cycle review approved" credential should not be taken as a green light against external-validation findings.

---

## Fastest Next Test

**Single test, highest yield: run the Phase 3 jq filter against one real transcript file and count survivors.**

```bash
f=$(ls -t ~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/*.jsonl | head -1)
jq -c '
  select(.timestamp != null) |
  {ts: .timestamp,
   uuid: .uuid,
   role: (.type // .role // "unknown"),
   text: (.message.content[0].text // .text // "")}
  | select(.text != "")
' "$f" | wc -l
wc -l "$f"
```

If the survivor count is < 25% of the total line count, High-1 is reproduced and the fix is gated. The whole audit's most decisive finding rests on this one command's output.

Run before any phase implementation begins. Estimated time: 30 seconds.

---

## Overall Assessment

**Needs revision before execution.**

Specific requirements before this plan executes:
1. **Fix High-1.** Rewrite the Phase 3 Task 1 jq filter to extract text from all message-content block types (text, thinking, tool_use, tool_result, and the string-form of `message.content`). Re-verify against a real transcript file and update Task 1's "Done when" to specify the survivor-count expectation.
2. **Fix High-2.** Choose one of three options for in-progress flagged-scaffold persistence (recommended: option (a), persist to `<dated_dir>/flagged/region-NNN.scaffold.md` on every edit iteration). Update Task 5, Task 7, and Task 8 to be self-consistent.
3. **Fix High-3.** Replace `claude --prompt` with `claude -p` in cron-integration.md. Add a verification note about `-p` + slash-command surface stability.
4. **Resolve Medium-1.** Either (a) factor explicit single-memory entry points in Phase 3 and Phase 4, or (b) accept that retry re-runs full Phase 3+4 with resume skipping the already-done work.
5. **Resolve Medium-2.** Either remove the `reject` verb (collapsing semantics into `accept` against the recommendation's inverse) or flag it as user-approved deviation #6 with rationale and update DR3.
6. **Resolve Medium-3 / Medium-5.** Re-frame the lastAudited convention claim and the test-requirements.md "no gaps" headline. Doc-only fixes.
7. **Resolve Medium-4.** Replace `grep -qF` with exact-line `grep -Fxq` or awk equivalent in Phase 6 Task 6.

The Low findings are convenience-grade and can be done at the next pass.

**After these fixes, this plan is executable.** The architectural intent is sound; the cycle-1 and cycle-2 review caught real structural issues (Important-1, Important-2, Important-3, Important-4) that would otherwise have been silent. The defects this review found are external-validation defects — verifiable only against the actual runtime surface (the transcript format, the claude CLI, the live memory dir's actual frontmatter state). They wouldn't have surfaced in an internal-consistency pass.

Recommend halting per the project's HALT-when-things-feel-sideways rule before proceeding to execution: High-1 alone substantially changes the value proposition of the entire plugin until it's fixed.
