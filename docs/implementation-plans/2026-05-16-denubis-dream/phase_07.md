# denubis-dream Implementation Plan — Phase 7: Cron integration documentation + UAT

**Goal:** The plugin documents how to register `/dream --autonomous` against any cron-style scheduler (with `/schedule` as the recommended path), provides a manual UAT checklist covering all 10 DoD criteria plus 5 design-specified integrity-critical edge cases, references the cron documentation from the skill itself, and bumps the plugin version 0.1.0 → 0.2.0 synced across plugin.json + marketplace.json + CHANGELOG.md.

**Architecture:** Pure documentation phase. cron-integration.md is scheduler-agnostic — anchors on the `/dream --autonomous` contract (single self-contained invocation, idempotent, AC9.3 no-op when dated dir exists) and recommends `/schedule` without enumerating its syntax (since `/schedule` is a Claude Code built-in whose surface is not in this repo to reverse-engineer; the user invokes `/schedule` itself for its own help). uat-checklist.md is one user-runnable verification document; each item is a Carnap-style "human DOES, JUDGES, FAILURE looks like" entry.

**Tech Stack:** Markdown documentation only.

**Scope:** Phase 7 of 7.

**Codebase verified:** 2026-05-17 (codebase-investigator confirmed `/schedule` is a Claude Code built-in, not a locally-installed plugin artefact — so cron-integration.md cannot quote its exact syntax and uses a scheduler-agnostic framing instead).

**Phase Type:** infrastructure (documentation only — no functional code; verification is via UAT checklist execution)

---

## Acceptance Criteria Coverage

This phase implements and verifies:

### denubis-dream.AC9: Cron integration
- **denubis-dream.AC9.1 Success:** When the `schedule` skill invokes `/dream --autonomous`, the autonomous pass produces the same dated artefact (mirror + `.audit.md` + `MEMORY.md` + `flagged/`) as manual invocation.
- **denubis-dream.AC9.2 Success:** Cron-mode `/dream --autonomous` exits without prompting after `MEMORY.md` regeneration. *(already implemented in Phase 4; Phase 7 documents it)*
- **denubis-dream.AC9.3 Success:** Cron-mode `/dream --autonomous` with an existing dated dir for today: prints the path + exits (no-op; no overwrite). *(already implemented in Phase 2; Phase 7 documents it)*
- **denubis-dream.AC9.4 Success:** `plugins/denubis-dream/docs/cron-integration.md` documents how to register a cron job via the `schedule` skill (example invocation, recommended cadence, troubleshooting).

### denubis-dream.AC10: Cross-cutting behaviours
- **denubis-dream.AC10.1 Success:** `/dream` performs no operations against memory directories of other projects — only the resolved main slug's `memory/` is touched. *(architecturally guaranteed by Phase 2 slug resolution + Phase 6 atomic writes scoped to `<MAIN_DIR>/memory/` only; UAT checklist verifies operationally)*
- **denubis-dream.AC10.2 Success:** Plugin version bumps follow the repo convention — `plugin.json` + `marketplace.json` + `CHANGELOG.md` synced in the same commit (per top-level `CLAUDE.md`).
- **denubis-dream.AC10.3 Success:** All 10 DoD criteria pass UAT via `plugins/denubis-dream/docs/uat-checklist.md` against either a fixture project or the live project before the plugin is declared releasable.

---

<!-- START_TASK_1 -->
### Task 1: Write `plugins/denubis-dream/docs/cron-integration.md`

**Verifies:** AC9.4

**Files:**
- Create: `plugins/denubis-dream/docs/cron-integration.md`

**Implementation:**

Write a scheduler-agnostic cron-integration doc. The doc has four sections:

1. **The `/dream --autonomous` contract** — what callers can rely on.
2. **Recommended path: Claude Code's `/schedule` built-in** — invoke `/schedule` for its own help; provide the prompt-string the user should schedule.
3. **Alternative: system-level scheduling** — for users who prefer crontab, systemd timers, or external schedulers, document how to wrap the invocation.
4. **Recommended cadence + troubleshooting.**

**File body:**

```markdown
# Cron integration for denubis-dream

`/dream --autonomous` is designed to be cron-friendly: it's a single self-contained invocation that produces an auditable artefact (the dated dir) without prompting, and re-invocation on the same day is a no-op. Any cron-style scheduler can drive it.

## The `/dream --autonomous` contract

When `/dream --autonomous` is invoked:

- **Input:** none required beyond the working directory (the slug is resolved from `git rev-parse --show-toplevel`). The plugin must be installed and the project must be inside a git repository (otherwise the command exits cleanly with an "unable to resolve project slug" message — see AC2.5).
- **Output (no dated dir exists for today):** the autonomous pass runs end-to-end (discovery → Sonnet retrieval → Opus judgement → MEMORY.md regeneration), producing `~/.claude/projects/<main-slug>/memory.dream-YYYY-MM-DD/` with mirrors, `.audit.md` files, `flagged/`, and the proposed `MEMORY.md`. Live `memory/` is unchanged.
- **Output (dated dir exists for today):** prints `denubis-dream: dated dir already exists for today: <path> — exiting cleanly (no-op)` and exits with status 0. This is AC9.3 — the cron-driven invocation must not overwrite an in-progress reconciliation.
- **No prompts.** Autonomous mode never asks the user anything. If a code path would normally prompt (e.g., the walk-end finalise confirmation), autonomous mode never reaches it (Phase 4's `## Autonomous exit` short-circuits before Phase 5 begins).
- **Exit code 0** in all success and no-op cases. Exit code non-zero only on hard errors (filesystem failures, missing tools, malformed transcripts) — the scheduler can use exit code to detect genuine failures.

## Recommended path: Claude Code's `/schedule` built-in

`/schedule` is the Claude Code built-in for cron-style scheduling. Invoke it interactively for its current syntax and feature surface:

```
/schedule
```

The exact registration syntax may evolve with Claude Code versions; this doc deliberately doesn't enumerate it. What `/schedule` needs from you for denubis-dream:

- **The prompt to schedule:** `/dream --autonomous`
- **A cron-style schedule:** for most projects, weekly is a sensible default (e.g., every Sunday at a low-activity hour). Daily is reasonable for high-activity projects; monthly for archive-style projects.
- **The working directory:** the project root (the schedule needs to launch the Claude Code session in the directory `/dream` will audit). If `/schedule` doesn't support a per-job working directory, you may need to wrap the invocation in a shell script that `cd`s first — see "Alternative" below.

## Alternative: system-level scheduling

If `/schedule` doesn't fit your workflow (no per-job working directory, you want centralised cron management, you prefer systemd timers), wrap `/dream --autonomous` in a shell script and schedule the script with your usual tooling.

Example wrapper (`~/bin/dream-myproject.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$HOME/path/to/myproject"
cd "$PROJECT_ROOT"

# Invoke Claude Code with the /dream --autonomous prompt.
# -p / --print runs Claude Code non-interactively and exits when the prompt
# completes. The prompt is passed as a positional argument (NOT as a flag —
# there is no `--prompt` option on the `claude` CLI).
#
# Verify your installed `claude` binary supports the non-interactive surface
# BEFORE relying on cron. Two tests:
#
#   1. Binary works at all:
#        claude --version
#      Expect a version string on stdout, exit code 0.
#
#   2. -p mode + prompt-positional works end-to-end:
#        claude -p 'reply with the single word OK'
#      Expect "OK" (or similar minimal text reply) on stdout, exit code 0.
#      If the command hangs (no exit) or errors with "unknown option",
#      consult `claude --help` for the current non-interactive flag in
#      your version.
#
# Note: NOT a good smoke test: `claude -p '/help'`. Slash-command builtins
# like /help are environment-specific in non-interactive mode and may print
# "isn't available in this environment" with exit 0 — a confusing signal.
# Test with a plain-language prompt that exercises the model end-to-end.

claude -p "/dream --autonomous"
```

Schedule with crontab:

```cron
# m h dom mon dow command
30 3 * * 0 $HOME/bin/dream-myproject.sh >> $HOME/.cache/dream-myproject.log 2>&1
```

(Every Sunday at 03:30, log stdout/stderr.)

## Recommended cadence

- **Active development projects:** weekly. Captures recent insights without burning subagent budget on near-empty windows.
- **High-activity projects (multi-session days):** daily. Catches memory-worthy moments while context is fresh.
- **Archive / quiet projects:** monthly or quarterly. The `.last-dream` corpus-window bound means cron-driven dreams are cheap when nothing's happened since last finalisation — most subagent dispatches return empty quickly.

The user can override cadence by running `/dream` manually any time — the cron-driven autonomous pass and the manual reconciliation walk are the same artefact lifecycle.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Scheduled run produces no dated dir, no log output | The scheduler is launching in a non-git directory; slug resolution exits at AC2.5 | Wrap the invocation in a shell script that `cd`s to the project root first (see Alternative above). |
| Dated dir created today, but you have no record of running `/dream` | Cron-driven autonomous pass succeeded silently; the dated dir is waiting for your next interactive `/dream` invocation to reconcile | Run `/dream` (no flag) when convenient — it'll open the reconciliation walk on the existing dated dir. |
| Same dated dir present for multiple days; the cron job seems to be running but producing no new artefacts | AC9.3 no-op: cron-driven `--autonomous` sees today's dated dir already exists and exits without overwriting | Either (a) reconcile the existing dated dir manually so finalisation removes it and tomorrow's cron run produces a fresh one, or (b) accept that the dated dir captured a moment in time and you don't want to overwrite it. |
| Live `memory/` files have grown stale `lastAudited` dates despite weekly cron | Cron is creating dated dirs but you're not reconciling them — finalisation never runs, so `lastAudited` never bumps | Run `/dream` interactively to walk the existing dated dir and finalise. |
| Scheduler reports non-zero exit code | Hard error — likely filesystem (disk full, permission), missing tool (jq absent), or malformed transcripts | Check the scheduler's captured stderr; the `/dream` skill prints specific abort messages for each error mode. |
| Wrapper script fails immediately with `error: unknown option '--prompt'` or similar | Stale wrapper from an earlier doc version: `--prompt` was never a valid Claude Code flag (the flag is `-p` / `--print`; the prompt itself is a positional argument) | Replace `claude --prompt "/dream --autonomous"` with `claude -p "/dream --autonomous"` (or check `claude --help` if the non-interactive flag in your version differs). |
| Wrapper script runs interactively instead of exiting | `-p` / `--print` flag missing — without it, `claude` opens an interactive session and the cron job hangs | Ensure the wrapper uses `claude -p "/dream --autonomous"`. Test with `claude -p '/help'` first to confirm non-interactive mode works in your installation. |

## See also

- `/dream` (manual interactive mode) — see `plugins/denubis-dream/skills/dreaming/SKILL.md`.
- Recommended cadence considerations — design DR9 (dated dir lifecycle) and DR14 (`.last-dream` corpus windowing).
- Plugin design — `docs/design-plans/2026-05-16-denubis-dream.md`.
```

**Verification (operational):**

- After the file is written, confirm it renders cleanly as Markdown (`grip` / GitHub preview / your editor).
- Read it as a user encountering `/dream` for the first time: does the contract section tell you what `--autonomous` guarantees? Does the `/schedule` section tell you what to type? Does the troubleshooting table cover the failure modes you'd hit?
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Write `plugins/denubis-dream/docs/uat-checklist.md`

**Verifies:** AC10.3 (10 DoD criteria via this checklist)

**Files:**
- Create: `plugins/denubis-dream/docs/uat-checklist.md`

**Implementation:**

Write a step-by-step manual verification doc. Two halves:

- **Part A: 10 DoD criteria** — one section per DoD criterion (from the design's Definition of Done). Each section has setup, action, expected, and pass/fail criteria.
- **Part B: 5 design-specified edge cases** — slug suffix-collision, decisions.log edge identifiers, atomic-write interrupt, mid-walk abandonment, corpus coverage check. Each has a concrete reproduction recipe.

**File body:**

```markdown
# denubis-dream UAT checklist

Manual verification for the `/dream` plugin against the 10 DoD criteria (design DoD #1–#10) plus 5 design-specified integrity-critical edge cases that automated tests would catch in a typical Python codebase but are tested manually here because design DR1 chose a pure-skill (no Python helpers) implementation.

This checklist is the AC10.3 release gate: all sections must pass before the plugin is declared releasable.

**Environment:** run against the live project (the repo this plugin lives in) OR a fixture project (a synthetic memory tree + synthetic transcript dir). The live project is more realistic but requires you to be comfortable applying audit changes to your own memories. A fixture project is safer for first runs.

---

## Part A: DoD criteria

### A.1 — Plugin exists in this repo (DoD #1)

**Setup:** none.

**Action:** `ls plugins/denubis-dream/.claude-plugin/plugin.json` ; `grep -q '"name": "denubis-dream"' .claude-plugin/marketplace.json` ; `grep -q '\[denubis-dream\] 0.2.0' CHANGELOG.md`.

**Expected:** all three commands succeed.

**Pass:** all three pass. **Fail:** any of the three is missing or refers to the wrong version.

### A.2 — `/dream` is discoverable and invocable (DoD #2)

**Setup:** open a fresh Claude Code session in this repo root.

**Action:** type `/plugin list` ; verify `denubis-dream` appears. Then type `/` and verify `dream` autocompletes.

**Expected:** `denubis-dream` is in the plugin list; `/dream` autocompletes with a sensible description; typing `/dream` and pressing Enter starts the skill (you should see the announcement).

**Pass:** all three. **Fail:** any of the three.

### A.3 — First-run autonomous produces dated dir, no live writes (DoD #3)

**Setup:** ensure no `~/.claude/projects/<main-slug>/memory.dream-$(date +%Y-%m-%d)/` exists. Snapshot live memory mtimes: `stat -c '%n %Y' ~/.claude/projects/<main-slug>/memory/*.md > /tmp/dream-uat-mtimes-before.txt`.

**Action:** `/dream --autonomous`.

**Expected:** the dated dir is created with full mirror + audit + flagged/ + MEMORY.md; live memory mtimes are unchanged: `stat -c '%n %Y' ~/.claude/projects/<main-slug>/memory/*.md > /tmp/dream-uat-mtimes-after.txt && diff /tmp/dream-uat-mtimes-before.txt /tmp/dream-uat-mtimes-after.txt` returns nothing.

**Pass:** dated dir populated, diff empty. **Fail:** dated dir missing, partial, or any live mtime changed.

### A.4 — Second cron invocation is no-op (DoD #4)

**Setup:** A.3 was successful and its dated dir still exists. Note the dated dir's mtime.

**Action:** `/dream --autonomous` again.

**Expected:** the command prints `denubis-dream: dated dir already exists for today: <path> — exiting cleanly (no-op)` and exits with status 0. The dated dir's mtime is unchanged (no overwriting happened).

**Pass:** message + clean exit + unchanged mtime. **Fail:** any overwrite, error, or omitted no-op message.

### A.5 — Cron-driven schedule produces the same artefact (DoD #5)

**Setup:** delete today's dated dir (so the next autonomous run produces a fresh one).

**Action:** invoke `/dream --autonomous` via **a real scheduler** — at least one of the recognised paths in `cron-integration.md`:
  - **Recommended:** `/schedule` built-in (interactive Claude Code session); register a one-time schedule that fires within the next 5 minutes.
  - **Alternative:** wrap `claude --prompt "/dream --autonomous"` in a shell script and register a one-shot crontab entry for a few minutes hence (`echo "$(date -d '+5 minutes' '+%M %H * * *') $HOME/bin/dream-uat.sh" | crontab -`).
  - **Equivalent:** any system scheduler the user actually intends to use in production (systemd timer, launchd, etc.).

**Why a real scheduler invocation is required and simulation is not accepted** (Minor-3 fix): the AC9.1 contract is that the scheduler-driven invocation produces the same artefact AS WHEN THE SCHEDULER INVOKES IT — including session-launch behaviour (working directory inheritance, environment variables, lack of interactive TTY, output capture). A "simulate by typing it" check verifies `/dream --autonomous` itself but not the scheduler→`/dream` interface, which is exactly what AC9.1 is about. The cron-integration.md troubleshooting table identifies several failure modes (non-git cwd, no TTY, output-not-captured) that only manifest under a real scheduler launch.

**Expected:** the scheduler-driven invocation produces the same dated dir structure as the manual A.3 case. Compare file lists (`ls -R` against the A.3 snapshot) — equivalent modulo timestamps.

**Pass:** scheduler-driven dated dir matches manual case AND was produced by a real scheduler launch (not simulated). **Fail:** the cron invocation produces a different structure, hits an error the manual case doesn't, or you skipped the real-scheduler step.

**Cleanup:** after the scheduled run fires, remove the one-shot schedule entry (`crontab -e` to delete the line; or `/schedule list` + `/schedule delete <id>` for the `/schedule` path).

### A.6 — Interactive `/dream` re-opens reconciliation (DoD #6)

**Setup:** A.5 was successful; the dated dir exists.

**Action:** `/dream` (no flag).

**Expected:** the walk starts (or the skipped-memory triage if there are skipped entries). Each turn quotes evidence as chat blockquotes. The user can `accept` / `reject` / `edit` / `prune` (memory turns) or `accept` / `edit` / `dismiss` (flagged turns). No live `memory/` mtimes change during the walk: re-snapshot mtimes pre- and post-walk and diff.

**Pass:** walk runs, dispositions update dated dir, live mtimes unchanged. **Fail:** walk doesn't start, dispositions don't persist, live mtimes change.

### A.7 — Finalising applies state to live memory + bumps lastAudited (DoD #7)

**Setup:** A.6 walk is in progress.

**Action:** complete the walk; type `y` at the walk-end finalise prompt.

**Expected:** live `memory/` updates (kept files unchanged, edited files reflect mirror, pruned files removed, promoted files added). Every surviving file's frontmatter `lastAudited` is today's date. Live `MEMORY.md` reflects pruned-files-removed + promoted-files-inserted. Dated dir is removed.

**Pass:** all expected mutations happened; dated dir is gone. **Fail:** any expected mutation missing, partial, or wrong.

### A.8 — No transcript UUIDs / line-ranges in live memory (DoD #8)

**Setup:** A.7 just completed.

**Action:** `grep -RE '(transcript [a-f0-9]+|L[0-9]+–[0-9]+)' ~/.claude/projects/<main-slug>/memory/`.

**Expected:** zero output.

**Pass:** zero output. **Fail:** any matching line.

### A.9 — `.gitignore` lists `memory.dream-*` (DoD #9)

**Setup:** none.

**Action:** `grep -q '^memory\.dream-\*$' .gitignore`.

**Expected:** match (exit 0).

**Pass:** match. **Fail:** missing.

### A.10 — Code-artefact grep validation at audit time (DoD #10)

**Setup:** identify a memory that names a code artefact in its body (e.g., a file path, function name).

**Action:** during A.3 or A.6, open the relevant `.audit.md` file in `<dated_dir>` and inspect its `## Code-artefact flags` section.

**Expected:** the section lists the artefact with either a HIT (path:line) or a MISS ("verify or edit"). The grep was actually run.

**Pass:** flags section is populated. **Fail:** flags section is missing, empty, or contains only generic prose.

---

## Part B: Design-specified edge cases

### B.1 — Slug-prefix scan against a deliberate suffix-collision

**Why:** the anchored regex (design DR7) is the only thing preventing evidence poisoning from a sibling project whose slug happens to start with the main slug. Without unit tests, manual UAT is the only way to verify the anchoring holds.

**Setup:**

```bash
# Create a fake sibling slug that would suffix-collide on an unanchored prefix scan
MAIN_SLUG=$(pwd | sed -E 's|^/||; s|/|-|g; s|^|-|')
mkdir -p ~/.claude/projects/"${MAIN_SLUG}-collisiontest"
touch ~/.claude/projects/"${MAIN_SLUG}-collisiontest"/fake-transcript.jsonl
```

**Action:** `/dream --autonomous`. After the run completes, inspect the dispatched per-memory subagent prompts (or the windowed `<dated_dir>/.windowed/*.jsonl` files) to confirm they did NOT include `fake-transcript.jsonl`'s content.

**Cleanup:** `rm -rf ~/.claude/projects/"${MAIN_SLUG}-collisiontest"`

**Pass:** the collision-test slug is excluded. **Fail:** its content appears in any windowed file.

### B.2 — decisions.log parsing under edge identifiers

**Why:** memory filenames contain underscores and dashes; user edit instructions can contain quotes, newlines, and other characters that break naive log formats.

**Setup:** start a walk (A.6 setup).

**Action:** in one per-existing-memory turn, type an edit instruction containing quotes and a newline:
```
edit revise the second paragraph to read "first, fix the bug;\nthen add the test."
```

After the turn, inspect the decisions.log line:
```bash
tail -1 <dated_dir>/decisions.log | jq -r '.instruction'
```

**Expected:** the printed instruction is the literal multi-line string with the embedded quotes preserved. The line parses as valid JSON.

**Pass:** correct round-trip. **Fail:** parse error, truncation, or escape-character corruption.

### B.3 — Atomic-write interrupt (mid-finalisation Ctrl-C)

**Why:** AC7.2 + AC7.10 are about graceful handling of mid-finalisation interruption. Without unit tests, manual interrupt verification is the only way to confirm `.tmp` orphan cleanup works.

**Setup:** complete a walk to walk-end; type `y` at the finalise prompt.

**Action:** during finalisation, press `Ctrl-C` after the first few mirror transfers but before the `.last-dream` write. (Practical hint: large memory sets give more time; for small sets, you may need to interrupt very quickly — easier to set up a fixture project with 50+ memories.)

**Verification step 1:** `find ~/.claude/projects/<main-slug>/memory/ -name '*.md.tmp'` may show one or more `.tmp` orphans (depending on where the interrupt landed).

**Verification step 2:** invoke `/dream` again; walk to walk-end (resume detection should pick up where you left off); type `y` at finalise.

**Verification step 3:** after the second finalisation: `find ~/.claude/projects/<main-slug>/memory/ -name '*.md.tmp'` returns zero results. The start-of-pass orphan cleanup (Phase 6 Task 1's `## Finalise entry` section, per the Important-2 ownership consolidation) should have removed the orphans.

**Expected:** orphans cleaned; final state is consistent (no half-applied memories).

**Pass:** zero orphans after the second finalisation; live `memory/` is consistent. **Fail:** orphans persist, or live `memory/` has half-applied changes.

### B.4 — Mid-walk abandonment + resume

**Why:** AC5.7 requires that abandoning the walk and re-invoking resumes from the first not-yet-decided entry. Resume detection is jq-based — manual verification is necessary because no unit test exercises the JSONL parsing.

**Setup:** start a walk (A.6 setup).

**Action:** decide on 3 entries (accept, edit, prune); then quit the session (Ctrl-D, Ctrl-C, or close the terminal). Open a new Claude Code session in the same project; type `/dream`.

**Expected:** the walk re-enters; the preamble reports "X entries already decided"; the first prompt is for the 4th entry (first not-yet-decided in walk order).

**Pass:** resume at the 4th entry. **Fail:** restart from the 1st, or jump to the wrong entry.

### B.5 — Corpus-wide subagent coverage header check

**Why:** AC3.5 + AC3.8 require the flagged-region subagent to report its scan window in the `## Coverage` header. Coverage truncation (silent context-window failure) is a recurring risk for first-dream runs against large corpora.

**Setup:** after A.3 (first dream — no `.last-dream`) OR a subsequent dream (post-finalise — `.last-dream` exists):

**Action:** if any `flagged/region-NNN.flagged.md` exists, open one and read its `## Coverage` header.

**Expected:**
- First dream: header says `Scanned N text-bearing lines since <unbounded — first dream>`.
- Subsequent dream: header says `Scanned N text-bearing lines since <ISO timestamp matching previous .last-dream>`.
- N is roughly equal to the line count you'd compute by `wc -l <dated_dir>/.windowed/_corpus.jsonl`.

**Pass:** header values match expected. **Fail:** header missing, claimed line count grossly off (truncation), bounding timestamp doesn't match `.last-dream`.

---

## Sign-off

All A.1–A.10 must pass. All B.1–B.5 must pass.

**Tester:** _________________  **Date:** _________________

**Plugin version under test:** _________________

**Notes / anomalies observed:**

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
```

**Verification (operational):**

- After writing, read the doc end-to-end. Each section should be runnable by the tester without referring back to the design plan or the implementation plan.
- Run yourself through one or two sections to confirm the recipes work as-written.
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add `## Cron integration` section to `skills/dreaming/SKILL.md`

**Verifies:** discoverability of cron-integration.md from the skill itself

**Files:**
- Modify: `plugins/denubis-dream/skills/dreaming/SKILL.md` — append a `## Cron integration` section after Phase 6's `## Pipeline status (Phase 6)` block.

**Implementation:**

Add a short section pointing at the doc.

```markdown
## Cron integration

To run `/dream --autonomous` on a recurring schedule (cron-style), see `docs/cron-integration.md` in this plugin's directory. The doc covers:

- The `/dream --autonomous` contract (single self-contained invocation, idempotent, no-op when dated dir exists).
- Using Claude Code's built-in `/schedule` skill as the recommended path.
- System-level alternatives (crontab, systemd timers) for users who prefer external scheduling.
- Recommended cadence and troubleshooting.
```

That's the whole section — pointer + brief contract summary. The doc itself carries the depth.
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Version bump 0.1.0 → 0.2.0 synced across plugin.json + marketplace.json + CHANGELOG.md

**Verifies:** AC10.2 (version-sync convention)

**Files:**
- Modify: `plugins/denubis-dream/.claude-plugin/plugin.json` — `version` field 0.1.0 → 0.2.0.
- Modify: `.claude-plugin/marketplace.json` — `denubis-dream` entry's `version` field 0.1.0 → 0.2.0.
- Modify: `CHANGELOG.md` — prepend `## [denubis-dream] 0.2.0` entry.

**Implementation:**

**Pre-condition:** the UAT checklist (Task 2) has been completed successfully end-to-end against the live project. Per `feedback_version-bumps-after-working.md` — don't bump during iteration; bump once when the feature is verified working.

**Step 1: bump plugin.json**

Open `plugins/denubis-dream/.claude-plugin/plugin.json` and change `"version": "0.1.0"` to `"version": "0.2.0"`.

**Step 2: bump marketplace.json**

Open `.claude-plugin/marketplace.json`. Find the `denubis-dream` entry in the `plugins` array. Change its `"version": "0.1.0"` to `"version": "0.2.0"`. The marketplace's own top-level `version` field stays at `2.0.0` (unchanged).

**Step 3: prepend CHANGELOG entry**

Open `CHANGELOG.md`. Prepend a new section immediately after the `# Changelog` heading, before the existing `## [denubis-dream] 0.1.0` entry:

```markdown
## [denubis-dream] 0.2.0

Full pipeline release. `/dream` audits per-project auto-memory against worktree-aggregated Claude Code transcripts end-to-end: autonomous-pass orchestration → Sonnet retrieval (per-memory evidence + corpus-wide flagged regions) → Opus judgement (five gates, diff-narrative changes, kept/edited/pruned dispositions) → manual reconciliation walk (mtime-ordered with batched keep-clean handling; promote workflow for flagged regions; JSONL decisions.log with resume detection) → atomic-write finalisation (mirror transfer with lastAudited bump, prune deletes, promoted moves with collision pre-flight, MEMORY.md type→section insertion, DoD #8 self-check, .last-dream timestamp, dated-dir cleanup). Cron-driven `/dream --autonomous` produces the same dated artefact as manual invocation and exits without prompting.

**New:**
- `## Mode detection`, `## Project slug resolution`, `## Discovery`, `## Dated dir creation`, `## No-op detection` in the skill.
- Pre-windowing transcripts via `jq` into stable `{ts, uuid, role, text}` JSONL shape.
- Per-memory and corpus-wide Sonnet subagents (`denubis-basic-agents:sonnet-general-purpose`).
- Opus judgement with five-gate semantics (holds / correct / useful / duplicate / supported) and diff-narrative changes.
- Reconciliation walk with three-stream order (skipped triage → existing mtime-ascending → flagged numeric) and JSONL decisions.log with last-write-wins resume.
- Atomic finalisation with `.tmp` + `mv` pattern, collision pre-flight, DoD #8 self-check, `.last-dream` inter-dream persistence, and dated-dir removal.
- `docs/cron-integration.md` — scheduler-agnostic registration guide.
- `docs/uat-checklist.md` — 10 DoD + 5 edge-case manual verification.

**Changed:**
- Plugin version 0.1.0 → 0.2.0 (post-UAT release).
```

**Step 4: single commit for the version bump + UAT doc set**

```bash
git add plugins/denubis-dream/docs/cron-integration.md \
        plugins/denubis-dream/docs/uat-checklist.md \
        plugins/denubis-dream/skills/dreaming/SKILL.md \
        plugins/denubis-dream/.claude-plugin/plugin.json \
        .claude-plugin/marketplace.json \
        CHANGELOG.md
git status
git commit -m "release(dream): 0.2.0 — full pipeline + cron integration + UAT

Adds scheduler-agnostic cron-integration.md anchored on the
/dream --autonomous contract, uat-checklist.md covering the 10 DoD
criteria + 5 design-specified integrity-critical edge cases (slug
suffix-collision, decisions.log edge identifiers, atomic-write
interrupt, mid-walk abandonment, corpus coverage check), and a brief
## Cron integration pointer in the skill itself.

Bumps version 0.1.0 → 0.2.0 across plugin.json, marketplace.json,
and CHANGELOG.md per repo convention. Marketplace top-level stays
at 2.0.0.

Covers AC9.1 through AC9.4 and AC10.1 through AC10.3. Pre-condition:
the UAT checklist completed successfully end-to-end against the live
project."
```

**Verification (operational):**

- After commit, the three version fields agree: `0.2.0` in plugin.json, `0.2.0` in the denubis-dream marketplace entry, and `## [denubis-dream] 0.2.0` at the top of CHANGELOG (after `# Changelog`).
- The marketplace top-level version is unchanged at `2.0.0`.
- A fresh `/plugin list` shows `denubis-dream 0.2.0`.
<!-- END_TASK_4 -->
