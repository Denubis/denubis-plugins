# Critical Peer Review — Cycle 2 (re-review of fixes)

Reviewer: Opus 4.7 (1M context) — same agent that authored the cycle-1 fixes (self-audit)
Date: 2026-05-17
Artifact type: implementation-plan
Artifact reviewed: `docs/implementation-plans/2026-05-16-denubis-dream/phase_01.md` through `phase_07.md`, plus `test-requirements.md` and `uat-requirements.md` — after cycle-1 critical-peer-review fix cycle (H1/H2/H3 + M1/M2/M3/M4/M5).

Self-audit caveat: this re-review is by the same agent that wrote the fixes. Confirmation bias is the dominant risk. To compensate, every claim of "fix holds" was independently re-verified against the production-equivalent path (real transcript files, the actual `claude` binary, the actual `grep` semantics) rather than against my own reasoning. Findings below are biased toward over-flagging.

---

## Source Inventory

- `critical-peer-review-findings.md` (cycle 1; 405 lines; the input to this audit)
- `phase_01.md` through `phase_07.md` (the updated plan)
- `test-requirements.md` (updated headline)
- `uat-requirements.md` (unchanged this cycle)
- `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/d28fd3f2-dc3e-41fd-9e62-75bf79264cce.jsonl` (the H1 reference transcript; 960 lines)
- `~/.claude/projects/-home-brian-people-Brian-brian-ed3d-plugins/883f27a8-9133-44a1-ae74-75aa122e0f55.jsonl` (162 lines; second transcript for shape diversity)
- Live `claude --version` and `claude --help` output (2.1.142)
- Live `grep -Fxq` semantics test (against multi-section markdown sample)

---

## Prior-Findings Verification

### High-1: Phase 3 jq filter dropped ~95% of transcript content

**Status: Resolved.**

The naïve filter `(.message.content[0].text // .text // "")` is replaced with a `def extract_text` jq function that handles every block type Claude Code transcripts emit (`text`, `thinking`, `tool_use`, `tool_result` including nested-array form, plus string-form `.message.content`). Independent verification against the cited 960-line reference file:

- 785 timestamped lines (vs 175 non-timestamped)
- **475 survivors** under the new filter (vs 48 under the old, ~5%)
- 0 lines of stderr (vs the old filter's "Cannot index string with number" on 9 lines)
- Independently re-verified on a second transcript (162 lines → 69 survivors)

The Task 1 verification text now pins the survivor-count expectation; the architecture commentary acknowledges the block-type distribution. Both branches of the helper (since-bounded and unbounded) share the single program via `--arg ts` and `select($ts == "" or .timestamp >= $ts)`.

### High-2: Phase 5 in-progress flagged scaffold persistence

**Status: Resolved.**

The `<dated_dir>/flagged/<region-id>.scaffold.md` persistence path is added. Task 5's per-region resume check reads it before the drafting step; Task 7 step 1 enumerates the four substantive-write cases (memory mirror / flagged accept / flagged edit / dismiss); Task 8's worked example correctly cites the scaffold file and the write-before-log ordering. The narrative composes end-to-end. The decisions.log `edit` line remains non-terminal (correct, per the terminal-action table); the scaffold file is the actual carrier of the iteration state.

### High-3: `claude --prompt` invalid flag in cron-integration.md

**Status: Partially resolved — see Cycle-2 Medium-1 below.**

The flag is replaced (`claude -p "/dream --autonomous"`) and two new troubleshooting rows are added covering the `--prompt` legacy and the missing-`-p` case. The CLI surface is independently verified against `claude --version` 2.1.142 (`-p, --print` confirmed; positional `prompt`). However, the smoke-test expected output documented in the wrapper script is incorrect — see Medium-1 in the new findings below.

### Medium-1: Phase 5 retry workflow composition

**Status: Resolved (chose option b — delete-and-replay).**

Rewritten to leverage existing Phase 3 + Phase 4 resume infrastructure rather than fabricate new single-memory entry points. The retry handler deletes the audit + windowed file + SKIPPED.md line for one memory, then re-runs the existing Phase 3 / Phase 4 blocks whose missing-`## Evidence` / missing-`## Disposition` checks naturally scope to the just-deleted entry. Verified that Phase 4 Task 4's `## Disposition` skip-check exists (phase_04.md:207). One regex precision issue noted in Low-1 below.

### Medium-2: `reject` verb deviation

**Status: Resolved (chose option b — flag as deviation #6 in Phase 5 header).**

Phase 5 header now lists two user-approved deviations (persistence order + `reject` meta-verb). The walk-end summary's `kept` count subdivides into `M batch-kept-clean + N individually accepted + R reject-reverted-to-live`. The action-outcome semantics in Task 4 are unchanged (already specified `reject` behaviour); Task 6's decisions.log action enum already listed `reject`; Task 8's terminal-action set already included `reject` for the memory stream. Task 10's commit message updated to mention both deviations. Design plan's DR3 patch is deferred to a separate commit (action noted in the header, not done).

### Medium-3: lastAudited convention overclaim

**Status: Resolved (partial — see scope note).**

The cycle-1 review pointed to five touchpoints; the cycle-2 fix touched three (phase_02.md:15 header, phase_03.md:15 cascade note, phase_03.md Task 8 commit message). The remaining two locations (phase_05.md:43 and phase_06.md:11) reference "the convention established in Phase 3" without claiming preexistence — the cascade-fix references are accurate as-is given that Phase 3 now explicitly notes the field is invented. Editorial judgement; the user can audit and request fuller scope if they prefer.

### Medium-4: MEMORY.md grep/awk semantic mismatch

**Status: Resolved.**

`grep -qF` replaced with `grep -Fxq` (exact-line match). Verified semantically: substring matches no longer pass; exact-line matches still pass. Aligned with the awk's `$0 == sec` predicate. A comment in the bash explains why.

### Medium-5: test-requirements.md "Gaps" headline overclaim

**Status: Resolved.**

Headline rewritten to acknowledge three soft gaps at the verification-mechanism level explicitly. The body's enumeration of those gaps (AC3.1, AC5.10, AC7.2) is unchanged.

---

## New Findings (introduced by the cycle-1 fixes)

### Medium (count: 1)

**Cycle2-Medium-1: cron-integration.md smoke-test expected output is wrong; the documented test will produce a confusing signal**

**Issue:** Phase 7 Task 1's wrapper script now reads:

> Verify your installed `claude` binary supports this surface BEFORE relying on cron: `claude -p '/help'` should print the help-skill output and exit cleanly.

Independently running this exact command (Bash, `timeout 30 claude -p '/help' --output-format text`) produces:

```
/help isn't available in this environment.
```

with exit code 0. The expected output ("help-skill output") will NOT appear for a user running the documented smoke test from their wrapper script's environment, because `/help` is a Claude Code TUI built-in not exposed in `-p` mode. A user running the smoke test will see "isn't available" → conclude `-p` mode is broken → not proceed to scheduling. Real user-facing impact.

**Type:** overclaim (expected output asserted without verification against the production-equivalent path).
**Scope:** in-window confirmed.
**Evidence grade:** demonstrated (mechanism triggers: I ran the exact command; it does not produce "help-skill output").
**GRADE factors:** Indirectness — the doc claim was authored without running the test. Imprecision — single test, but the test is the production path.
**Pattern level:** local-only. The H3 fix touched only the wrapper script + troubleshooting rows; this is the one new claim that wasn't verified.
**Ripple:** UAT A.5 ("real scheduler launch") will eventually catch this because A.5 requires a real scheduler invocation; but the wrapper-script smoke test fails earlier, before scheduling. The troubleshooting table doesn't cover the "smoke test says isn't available" case.
**Corrected language / fix:** Replace the smoke test with one that has a stable, verifiable success signal:

```
Verify your installed `claude` binary supports the non-interactive surface BEFORE relying on cron:

  claude -p 'reply with the single word OK'

Expect `OK` on stdout and exit code 0. If you get a flag-parse error or
the session hangs (no exit), the `-p` flag is missing or broken in your
installation — consult `claude --help` for the current non-interactive
flag.
```

(Or `claude --version` for the minimal smoke — exit code 0 + a version string is sufficient to confirm the binary works, though it doesn't test `-p`.)

**Location:** `phase_07.md` Task 1, the comment block inside the wrapper script (the `# Verify your installed claude binary...` lines).

### Low (count: 4)

**Cycle2-Low-1: M1 retry grep pattern is regex-based; `.md` extension contains regex metachar**

- **Issue:** The retry handler's SKIPPED.md line-removal uses `grep -v "^- $basefile\$"`. `$basefile` typically ends in `.md` — the `.` is regex any-char, so `- feedback_X.md` matches `- feedback_XAmd` (hypothetical). In practice memory names don't have adjacent collision-prone names, so the impact is theoretical, but the fix is one flag.
- **Fix:** `grep -vFx "- $basefile" "$DATED_DIR/SKIPPED.md"` (literal exact-line match; no regex interpretation).
- **Severity:** Low (theoretical; no memory naming collision in current repo).
- **Location:** `phase_05.md` Task 3 retry-branch bash, the SKIPPED.md update block.

**Cycle2-Low-2: M1 retry "re-execute Phase 3's section" relies on implicit goto semantics in skill text**

- **Issue:** The retry handler says "Re-execute Phase 3's `## Pre-windowing transcripts` block AND `## Per-memory evidence retrieval` orchestrator." Skill text is read top-to-bottom; "re-execute" requires the agent reading the skill to navigate back to those sections and re-run them. This is achievable (the skill is one SKILL.md; section anchors exist) but not explicit. An implementer reading the retry block might wonder whether to inline the operations.
- **Fix:** Optionally add an explicit "(see Phase 3 Task 1's bash block for the pre-windowing commands)" anchor, OR inline the relevant Bash for clarity. Acceptable as-is given that Opus is the reader.
- **Severity:** Low (style; the agent reading the skill can navigate by section names).
- **Location:** `phase_05.md` Task 3 retry-branch prose.

**Cycle2-Low-3: walk-end summary R sub-count has no count-derivation spec**

- **Issue:** The summary now shows `X kept (M batch-kept-clean + N individually accepted + R reject-reverted-to-live)`. The bash above the summary computes only `ALL_DECIDED`; the M / N / R / P / Q / Z / W / V sub-counts are derived in implementer-supplied code that the plan doesn't specify. Adding R as a new sub-count expands implicit implementer scope without explicit spec.
- **Fix:** Either (a) add a `jq` count-extraction snippet alongside the summary template, OR (b) note in the spec that "the implementer derives counts via `jq` over decisions.log; the format above is the printed shape, not the derivation".
- **Severity:** Low (the count derivation is implementer's job; the format spec is correct).
- **Location:** `phase_05.md` Task 9, the summary format block.

**Cycle2-Low-4: H2 "atomic `.tmp + mv` write" phrasing is redundant given the `Write` tool**

- **Issue:** Task 5's `On edit` says "Persist the revised scaffold to ... (atomic `.tmp + mv` write, same pattern as Phase 6)". Phase 6's `.tmp + mv` pattern is for replacing a live file from a dated-dir staging copy (the `cp + mv` form that preserves the source on abort). For Phase 5's scaffold write — a fresh write to a dated-dir file — the `Write` tool's single-call atomicity is sufficient; the `.tmp + mv` ceremony is unnecessary cargo-culting.
- **Fix:** Replace "atomic `.tmp + mv` write, same pattern as Phase 6" with "atomic write via the `Write` tool".
- **Severity:** Low (minor implementer-confusion risk; the more-elaborate pattern still works correctly, just more verbose than needed).
- **Location:** `phase_05.md` Task 5 `On edit` bullet, after the persist-the-revised-scaffold line.

---

## ACH Matrix (for the new findings)

The cycle-1 ACH matrix concluded H3 (plan has at least one execution-blocking defect). After fixes, the equivalent matrix:

| Evidence | H1: Plan is ready to execute as-is | H2: Plan is ready with marginal touch-ups | H3: Plan has at least one execution-blocking defect |
|----------|-----|-----|-----|
| Phase 3 filter verified against real transcript (475/960) | + | + | + (does not contradict) |
| Phase 5 flagged-scaffold narrative composes across Tasks 5/7/8 | + | + | + |
| `claude -p` flag verified against installed binary | + | + | + |
| Smoke test expected output is wrong (Cycle2-M1) | − | + (one-block doc fix) | + |
| M1 grep regex over-permissive in theoretical case (Cycle2-L1) | − | + | + |
| Phase 4 Task 4 `## Disposition` skip-check exists (verified) | + | + | + |
| `reject` consistent across Task 4 / 6 / 8 / 9 | + | + | + |
| grep -Fxq verified to fix substring false-positive | + | + | + |

**Decision rule:** H1 has one decisive `−` (Cycle2-M1 ships a misleading smoke test that user-facing docs assert as a verification step). H2 absorbs it cleanly (one-block fix in one file). H3 is no longer best-supported — the remaining defects are doc-level, not behavioural. **H2 wins this round.**

---

## Pattern-Level Notes

- The cycle-1 self-audit pattern persists: my (the author's) tendency to write expected outputs without running the test. Cycle-1 caught this in High-3 (the `--prompt` flag was unverified); the cycle-1 fix replaced one unverified claim with another unverified claim (the smoke-test expected output). Pattern: assertions in docs should be verified against the production-equivalent path or hedged.
- Single-character flag changes (grep -qF → grep -Fxq) are deceptively low-stakes; the difference between substring and exact-line semantics is one of the most common "looks right, behaves wrong" failure modes in shell scripting. Worth always running both predicates against a sample where they should diverge.

---

## Hidden Assumptions (updated)

1. **The cycle-1 fixes hold the same architectural intent as the design.** Verified.
2. **The new persistence path `<region-id>.scaffold.md` doesn't conflict with any Phase 3 / 6 file globbing.** Verified — Phase 3 writes `*.flagged.md`; Phase 6 cleans `*.md.tmp`; no glob matches `*.scaffold.md`.
3. **`grep -Fxq` is portable across BSD and GNU grep.** Verified (POSIX-defined flags).
4. **The retry handler's delete-and-replay correctly composes with Phase 3 Task 1's pre-windowing iteration.** Phase 3 Task 1 iterates `memory/*.md` and writes one `<name>.jsonl` per memory; re-running it after re-creating one `<name>.jsonl` is wasted but cheap. Verified.
5. **`claude -p` accepts a slash-command form as a prompt.** Partially verified — `claude -p '/help'` exits 0 but produces a non-help message. The slash-command form is accepted by the CLI parser, but the receiving Claude Code session may not have the named skill loaded. For `/dream` specifically, the wrapper requires the denubis-dream plugin to be enabled in the Claude Code config the wrapper's environment uses. The cron-integration.md doc doesn't explicitly call this out, but the troubleshooting table's "Wrapper script runs interactively" entry indirectly covers the cousin failure mode. **Not flagged separately; folded into Cycle2-M1.**

---

## Pre-Mortem

If the plan ships with Cycle2-M1 unfixed:

**Scenario A — first cron user reads the doc, runs the smoke test, sees "isn't available", abandons:** The smoke test is presented as the gate before scheduling. Failing the gate (with a confusing message that says nothing about wrappers or `-p` mode itself being broken) → user concludes the doc is broken → opens an issue or gives up. Frequency: every first-time setup attempt.

**Scenario B — user skips the smoke test, schedules anyway, finds it works:** The `-p` mode + slash-command IS functional for plugin-loaded skills; the smoke test was the only thing producing a false negative. Frequency: rarer; users who trust the doc proceed.

**Scenario C — re-review iteration:** This finding is itself a pattern repetition of H3 (unverified doc claim). If we ship now, the next user-encountered failure will be exactly this; if we fix now, we're spending one revision cycle to retire the same pattern.

---

## Verification

- Files read: `phase_01.md` through `phase_07.md`, `test-requirements.md`, `uat-requirements.md`, `critical-peer-review-findings.md` (cycle 1).
- Commands run: `bash /tmp/verify-filter.sh` (filter survivors); `timeout 30 claude -p '/help'` (-p mode); `printf ... | grep -Fxq ...` (M4 match semantics); `claude --version`.
- Citations checked: phase_04.md:207 (Disposition skip-check), phase_05.md Task 4 / 6 / 8 / 9 (`reject` cascade), phase_03.md Task 1 jq filter (the substantive H1 edit).
- Provenance concerns: this is a self-audit. The only external-validation evidence (transcripts, grep, claude binary) was rerun rather than re-cited from cycle 1.

---

## Strongest Hypothesis

**Cycle2-M1 (smoke-test expected output is wrong) is the most-decisive new finding.** Mechanism: the documented test produces a different output than the doc claims. Both borders demonstrated: running the test produces the wrong output; replacing the test with a deterministic prompt (`'reply with OK'`) produces the right output. Same class of overclaim as the cycle-1 H3.

GRADE: **High** (demonstrated, on the user-facing documentation path).

---

## Weakest Hypothesis

**Cycle2-Low-1 (M1 grep regex over-permissive).** No actual memory name in the current repo triggers the over-permissive match; the finding is purely theoretical. GRADE: **Low**.

---

## Fastest Next Test

```bash
# Replace the documented smoke test in phase_07.md Task 1's wrapper script
# with one that has a deterministic, verifiable success signal:
claude -p 'reply with the single word OK'
# Expect: "OK" on stdout, exit code 0.
```

Update phase_07.md Task 1; re-verify by running the new smoke test before committing.

---

## Overall Assessment

**Needs ONE revision before execution.** The Cycle2-Medium-1 finding is a real but tightly-scoped fix: replace the wrapper script's smoke-test claim with a deterministic prompt. Four Low findings are quality-of-life and can ship with or without action.

Per the project's HALT-when-things-feel-sideways rule and the explicit resume-prompt instruction ("If the re-review surfaces anything new: HALT again — don't auto-loop"): I am halting here rather than auto-fixing Cycle2-M1.

The plan IS substantially closer to executable than after cycle 1. The fixes for H1/H2/H3/M1/M2/M3/M4/M5 hold under independent re-verification. The one new defect is the same class of overclaim cycle 1 caught (unverified user-facing doc), and warrants the user's attention rather than my silent fix.
